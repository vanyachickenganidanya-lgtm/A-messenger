# bridge.py
import os
import sys
import asyncio
import discord
import socket

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
IRC_SERVER = "127.0.0.1"
IRC_PORT = 6667
IRC_CHANNEL = "#secret"
IRC_NICK = "DiscordBridge"

TEXT_CHANNEL_NAME = "месенджер-макс-общатся"
VOICE_CHANNEL_NAME = "войс-месенджера-макс"

if not DISCORD_TOKEN:
    print("DISCORD_BOT_TOKEN not provided.")
    sys.exit(0)

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

irc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
voice_client = None

# Конвертация 8000Hz 8-bit mono в 48000Hz 16-bit stereo для Discord
def convert_8k_to_48k(data_8bit):
    out = bytearray()
    for b in data_8bit:
        val = (b - 128) * 256
        val = max(-32768, min(32767, val))
        sample_bytes = val.to_bytes(2, byteorder='little', signed=True)
        for _ in range(6):
            out.extend(sample_bytes * 2) # L + R
    return bytes(out)

# Конвертация обратно для рации C++
def convert_48k_to_8k(data_48k):
    out = bytearray()
    for i in range(0, len(data_48k), 24): # decimate
        if i + 1 < len(data_48k):
            val = int.from_bytes(data_48k[i:i+2], byteorder='little', signed=True)
            val_8 = (val // 256) + 128
            out.append(max(0, min(255, val_8)))
    return bytes(out)

class IRCAudioSource(discord.AudioSource):
    def __init__(self):
        self.buffer = bytearray()

    def add_data(self, data):
        self.buffer.extend(convert_8k_to_48k(data))

    def read(self):
        required = 3840 # 20ms of 48k stereo 16bit
        if len(self.buffer) < required:
            return b'\x00' * required
        data = bytes(self.buffer[:required])
        del self.buffer[:required]
        return data

audio_source = IRCAudioSource()

def send_irc(msg):
    try:
        irc_sock.send(f"{msg}\r\n".encode("utf-8"))
    except Exception as e:
        print(f"IRC send error: {e}")

class DiscordToIRCSink(discord.sinks.Sink):
    def __init__(self):
        super().__init__()
    @discord.sinks.Filters.callback
    async def write(self, data, user):
        # Чтение голоса из дискорда -> отправка в рацию C++
        pcm_8bit = convert_48k_to_8k(data)
        if len(pcm_8bit) > 0:
            hex_data = pcm_8bit.hex().upper()
            send_irc(f"PRIVMSG {IRC_CHANNEL} :VOICE:{hex_data}")

async def irc_reader():
    await bot.wait_until_ready()
    # Ищем текстовый канал по имени
    text_channel = None
    for channel in bot.get_all_channels():
        if channel.name == TEXT_CHANNEL_NAME and isinstance(channel, discord.TextChannel):
            text_channel = channel
            break
            
    buffer = ""
    while True:
        try:
            data = irc_sock.recv(16384).decode("utf-8", errors="ignore")
            if not data:
                await asyncio.sleep(1)
                continue
            buffer += data
            while "\r\n" in buffer:
                line, buffer = buffer.split("\r\n", 1)
                if " PRIVMSG " in line:
                    parts = line.split(" PRIVMSG ", 1)
                    nick = parts[0].split("!")[0][1:]
                    target_msg = parts[1].split(" :", 1)
                    text = target_msg[1] if len(target_msg) > 1 else ""
                    
                    if nick != IRC_NICK:
                        if text.startswith("VOICE:"):
                            # Проигрываем голос в Discord Voice
                            hex_data = text.split("VOICE:", 1)[1]
                            audio_source.add_data(bytes.fromhex(hex_data))
                        else:
                            # Пересылаем текст в Discord Chat
                            if text_channel:
                                await text_channel.send(f"**<{nick}>** {text}")
        except Exception as e:
            await asyncio.sleep(1)

@bot.event
async def on_message(message):
    if message.author.name == IRC_NICK or message.author.bot:
        return
    if message.channel.name == TEXT_CHANNEL_NAME:
        send_irc(f"PRIVMSG {IRC_CHANNEL} :<{message.author.name}> {message.clean_content}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    
    # Коннект к IRC
    irc_sock.connect((IRC_SERVER, IRC_PORT))
    send_irc(f"NICK {IRC_NICK}")
    send_irc(f"USER {IRC_NICK} 0 * :{IRC_NICK}")
    send_irc(f"JOIN {IRC_CHANNEL}")
    
    # Ищем голосовой канал
    voice_channel = None
    for channel in bot.get_all_channels():
        if channel.name == VOICE_CHANNEL_NAME and isinstance(channel, discord.VoiceChannel):
            voice_channel = channel
            break
            
    if voice_channel:
        global voice_client
        voice_client = await voice_channel.connect()
        # Включаем чтение и запись звука
        voice_client.play(audio_source)
        voice_client.start_recording(DiscordToIRCSink(), lambda sink: None)
        print("Connected to Voice Channel!")
        
    bot.loop.create_task(irc_reader())

bot.run(DISCORD_TOKEN)
