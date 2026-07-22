# -*- coding: utf-8 -*-
import os
import sys
import json
import socket
import threading
import time
import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import discord
from discord.ext import tasks

# --- НАСТРОЙКИ ИЗ ОКРУЖЕНИЯ ---
DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TEXT_CHANNEL_NAME = "месенджер-макс-общатся"
VOICE_CHANNEL_NAME = "войс-месенджера-макс"

IRC_PORT = 6667
HTTP_PORT = int(os.getenv("PORT", 10000))
IRC_CHANNEL = "#secret"
IRC_NICK = "DiscordBridge"

# --- ГЛОБАЛЬНОЕ СОСТОЯНИЕ ---
irc_clients = {}      # socket -> nick
irc_channels = {IRC_CHANNEL: set()}
discord_bot = None
voice_client = None
state_lock = threading.Lock()

# --- КОНВЕРТАЦИЯ АУДИО (8000Hz 8-bit Mono <-> 48000Hz 16-bit Stereo) ---
def convert_8k_to_48k(data_8bit):
    """Конвертирует 8kHz 8-bit mono в 48kHz 16-bit stereo"""
    out = bytearray()
    for b in data_8bit:
        val = (b - 128) * 256
        val = max(-32768, min(32767, val))
        sample_bytes = val.to_bytes(2, byteorder='little', signed=True)
        for _ in range(6):
            out.extend(sample_bytes * 2) # Стерео
    return bytes(out)

def convert_48k_to_8k(data_48k):
    """Конвертирует 48kHz 16-bit stereo в 8kHz 8-bit mono"""
    out = bytearray()
    for i in range(0, len(data_48k), 24): # Децимация 48k -> 8k
        if i + 1 < len(data_48k):
            val = int.from_bytes(data_48k[i:i+2], byteorder='little', signed=True)
            val_8 = (val // 256) + 128
            out.append(max(0, min(255, val_8)))
    return bytes(out)

class IRCAudioSource(discord.AudioSource):
    """Источник аудио для Discord из IRC"""
    def __init__(self):
        self.buffer = bytearray()
        self.lock = threading.Lock()
    
    def add_data(self, data):
        """Добавить аудиоданные"""
        with self.lock:
            self.buffer.extend(convert_8k_to_48k(data))
    
    def read(self):
        """Прочитать 20мс аудио"""
        required = 3840 # 20мс аудио 48kHz Stereo 16-bit
        with self.lock:
            if len(self.buffer) < required:
                return b'\x00' * required
            data = bytes(self.buffer[:required])
            del self.buffer[:required]
        return data
    
    def is_opus(self):
        return False

audio_source = IRCAudioSource()

# --- ЛОГИКА IRC СЕРВЕРА ---
def broadcast_irc(msg, exclude_sock=None):
    """Отправить сообщение всем IRC клиентам"""
    raw_msg = (msg + "\r\n").encode('utf-8', errors='ignore')
    with state_lock:
        for sock in list(irc_clients.keys()):
            if sock != exclude_sock:
                try:
                    sock.send(raw_msg)
                except Exception as e:
                    pass

def forward_to_discord_text(nick, text):
    """Перенаправить сообщение в Discord"""
    if discord_bot and discord_bot.is_ready():
        for channel in discord_bot.get_all_channels():
            if channel.name == TEXT_CHANNEL_NAME and isinstance(channel, discord.TextChannel):
                try:
                    discord_bot.loop.create_task(channel.send(f"**<{nick}>** {text}"))
                except:
                    pass
                break

def handle_irc_client(sock):
    """Обработать IRC клиента"""
    buffer = ""
    nick = "guest"
    try:
        while True:
            data = sock.recv(16384).decode('utf-8', errors='ignore')
            if not data: 
                break
            buffer += data
            
            while "\r\n" in buffer:
                line, buffer = buffer.split("\r\n", 1)
                if not line: 
                    continue
                
                parts = line.strip().split(" ", 2)
                if not parts: 
                    continue
                
                cmd = parts[0].upper()
                
                if cmd == "NICK":
                    if len(parts) > 1:
                        nick = parts[1]
                        with state_lock:
                            irc_clients[sock] = nick
                
                elif cmd == "USER":
                    sock.send(f":irc.local 001 {nick} :Welcome to MaxMessenger!\r\n".encode('utf-8'))
                
                elif cmd == "JOIN":
                    if len(parts) > 1:
                        chan = parts[1]
                        with state_lock:
                            if chan not in irc_channels:
                                irc_channels[chan] = set()
                            irc_channels[chan].add(sock)
                        broadcast_irc(f":{nick}!u@h JOIN {chan}", exclude_sock=None)
                
                elif cmd == "PRIVMSG":
                    if len(parts) >= 3:
                        target = parts[1]
                        text = parts[2]
                        if text.startswith(":"):
                            text = text[1:]
                        
                        if text.startswith("VOICE:"):
                            hex_voice = text[6:]
                            try:
                                audio_source.add_data(bytes.fromhex(hex_voice))
                            except:
                                pass
                            broadcast_irc(f":{nick}!u@h PRIVMSG {target} :{text}", exclude_sock=sock)
                        else:
                            broadcast_irc(f":{nick}!u@h PRIVMSG {target} :{text}", exclude_sock=sock)
                            forward_to_discord_text(nick, text)
                
                elif cmd == "PING":
                    pong_msg = f"PONG {parts[1] if len(parts) > 1 else 'irc.local'}\r\n"
                    sock.send(pong_msg.encode('utf-8'))
                
                elif cmd == "QUIT":
                    return
    
    except Exception as e:
        pass
    finally:
        with state_lock:
            if sock in irc_clients:
                del irc_clients[sock]
            for channel in irc_channels.values():
                channel.discard(sock)
        try:
            broadcast_irc(f":{nick}!u@h QUIT :Disconnected")
        except:
            pass
        try:
            sock.close()
        except:
            pass

def start_irc_server():
    """Запустить IRC сервер"""
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(('0.0.0.0', IRC_PORT))
    server_sock.listen(100)
    print(f"[IRC] Server running on port {IRC_PORT}")
    while True:
        try:
            client_sock, addr = server_sock.accept()
            threading.Thread(target=handle_irc_client, args=(client_sock,), daemon=True).start()
        except Exception as e:
            pass

# --- ВЕБ-СЕРВЕР ДЛЯ РАЗДАЧИ ПОРТОВ ---
class PortHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        try:
            with open("/tmp/bore_port", "r") as f:
                bore_port = f.read().strip()
        except:
            bore_port = "0"
        response = {"port": bore_port, "host": "bore.pub"}
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        pass  # Отключаем логи

def start_http_server():
    """Запустить HTTP сервер"""
    httpd = HTTPServer(('0.0.0.0', HTTP_PORT), PortHandler)
    print(f"[HTTP] Server running on port {HTTP_PORT}")
    httpd.serve_forever()

# --- DISCORD БОТ ---
if DISCORD_TOKEN:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.guild_messages = True
    intents.voice_states = True
    
    discord_bot = discord.Bot(intents=intents)

    class DiscordToIRCSink(discord.sinks.Sink):
        """Sink для преобразования Discord аудио в IRC"""
        def __init__(self):
            super().__init__()
        
        @discord.sinks.Filters.callback
        async def write(self, data, user):
            try:
                pcm_8bit = convert_48k_to_8k(data)
                if len(pcm_8bit) > 0:
                    hex_data = pcm_8bit.hex().upper()
                    broadcast_irc(f":{user.name}!d@h PRIVMSG {IRC_CHANNEL} :VOICE:{hex_data}")
            except:
                pass

    @discord_bot.event
    async def on_message(message):
        if message.author.bot: 
            return
        if message.channel.name == TEXT_CHANNEL_NAME:
            broadcast_irc(f":{message.author.name}!d@h PRIVMSG {IRC_CHANNEL} :{message.clean_content}")

    @discord_bot.event
    async def on_ready():
        print(f"[DISCORD] Bot logged in as {discord_bot.user.name}")
        
        voice_channel = None
        for channel in discord_bot.get_all_channels():
            if channel.name == VOICE_CHANNEL_NAME and isinstance(channel, discord.VoiceChannel):
                voice_channel = channel
                break
        
        if voice_channel:
            global voice_client
            try:
                if voice_client and voice_client.is_connected():
                    await voice_client.disconnect()
                
                voice_client = await voice_channel.connect()
                voice_client.play(audio_source)
                voice_client.start_recording(DiscordToIRCSink(), lambda sink: None)
                print(f"[DISCORD] Connected to Voice: {VOICE_CHANNEL_NAME}")
            except Exception as e:
                print(f"[DISCORD] Voice Connect Error: {e}")

    def start_discord_bot():
        """Запустить Discord бота"""
        discord_bot.run(DISCORD_TOKEN)
else:
    print("[DISCORD] DISCORD_BOT_TOKEN not set. Bot disabled.")

# --- MAIN ---
if __name__ == "__main__":
    print("=" * 50)
    print("UNIFIED IRC/DISCORD SERVER")
    print("=" * 50)
    
    threading.Thread(target=start_irc_server, daemon=True).start()
    threading.Thread(target=start_http_server, daemon=True).start()
    
    if DISCORD_TOKEN:
        start_discord_bot()
    else:
        while True:
            time.sleep(3600)
