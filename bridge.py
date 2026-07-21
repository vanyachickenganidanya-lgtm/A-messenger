import os
import sys
import asyncio
import discord
from discord.ext import commands
import socket

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
IRC_SERVER = "127.0.0.1"
IRC_PORT = 6667
IRC_CHANNEL = "#secret"
IRC_NICK = "DiscordBridge"

if not DISCORD_TOKEN or not DISCORD_CHANNEL_ID:
    print("Discord Token or Channel ID not provided. Bridge disabled.")
    sys.exit(0)

DISCORD_CHANNEL_ID = int(DISCORD_CHANNEL_ID)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

irc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

def send_irc(msg):
    try:
        irc_sock.send(f"{msg}\r\n".encode("utf-8"))
    except Exception as e:
        print(f"Error sending to IRC: {e}")

async def irc_to_discord():
    await bot.wait_until_ready()
    channel = bot.get_channel(DISCORD_CHANNEL_ID)
    if not channel:
        print(f"Discord channel {DISCORD_CHANNEL_ID} not found.")
        return

    buffer = ""
    while True:
        try:
            data = irc_sock.recv(4096).decode("utf-8", errors="ignore")
            if not data:
                break
            buffer += data
            while "\r\n" in buffer:
                line, buffer = buffer.split("\r\n", 1)
                
                if " PRIVMSG " in line:
                    parts = line.split(" PRIVMSG ", 1)
                    nick = parts[0].split("!")[0][1:]
                    target_msg = parts[1].split(" :", 1)
                    text = target_msg[1] if len(target_msg) > 1 else ""
                    
                    # Не пересылаем голосовые пакеты и сообщения самого бота
                    if nick != IRC_NICK and not text.startswith("VOICE:"):
                        await channel.send(f"**<{nick}>** {text}")
        except Exception as e:
            await asyncio.sleep(1)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.id == DISCORD_CHANNEL_ID:
        clean_content = message.clean_content
        send_irc(f"PRIVMSG {IRC_CHANNEL} :<{message.author.name}> {clean_content}")

@bot.event
async def on_ready():
    print(f"Logged in to Discord as {bot.user.name}")
    try:
        irc_sock.connect((IRC_SERVER, IRC_PORT))
        send_irc(f"NICK {IRC_NICK}")
        send_irc(f"USER {IRC_NICK} 0 * :{IRC_NICK}")
        send_irc(f"JOIN {IRC_CHANNEL}")
        bot.loop.create_task(irc_to_discord())
    except Exception as e:
        print(f"Failed to connect to local IRC: {e}")

bot.run(DISCORD_TOKEN)
