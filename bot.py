import asyncio
import re
import requests
import sqlite3
import time
import websockets
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
ACCESS_TOKEN_TMI = os.getenv('ACCESS_TOKEN_TMI')
USERNAME = os.getenv('USERNAME')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
CATEGORY_ID = '508391'
DATABASE = os.getenv('DATABASE')

# Discord Webhook URL
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL')

# ANSI color codes
COLOR_GREEN = '\033[92m'
COLOR_PURPLE = '\033[95m'
COLOR_RED = '\033[91m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'

def get_seconds_elapsed(start_time):
    started_at = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    elapsed = datetime.now(timezone.utc) - started_at
    return int(elapsed.total_seconds())

def get_access_token(client_id, client_secret):
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.post(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return data['access_token'], data['expires_in']
    else:
        print(f"Error while requesting access token: {response.status_code}")
        return None, None

def get_streamers(category_id, client_id, access_token):
    url = f'https://api.twitch.tv/helix/streams?game_id={category_id}'
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}',
        'Cache-Control': 'no-cache'
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        streams = data.get('data', [])
        return {stream['user_name']: stream['started_at'] for stream in streams}
    else:
        print(f"Error while requesting Twitch API: {response.status_code}")
        return {}

def log_message(conn, sender, host, message):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (sender, host, message)
        VALUES (?, ?, ?)
    ''', (sender, host, message))
    conn.commit()

def send_discord_alert(sender, host, message):
    """Send an alert to Discord via webhook."""
    print(f"{COLOR_BLUE}Sending alert to Discord for message: {message}{COLOR_RESET}")
    embed = {
        "title": "New message detected",
        "color": 0x3498db,
        "fields": [
            {"name": "Sent by", "value": sender, "inline": True},
            {"name": "Message", "value": message, "inline": False},
            {"name": "Stream link", "value": f"[Watch {host}](https://www.twitch.tv/{host})", "inline": True}
        ],
    }
    payload = {
        "embeds": [embed]
    }
    response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"Failed to send Discord alert: {response.status_code}, {response.text}")

def check_alerts_and_notify(conn, sender, host, message):
    """Check if the message contains any alert keywords and notify Discord if it does."""
    keywords = [row[0] for row in conn.execute("SELECT keyword FROM alerts")]
    for keyword in keywords:
        if keyword.lower() in message.lower():
            print(f"{COLOR_PURPLE}Alert keyword '{keyword}' detected in message: {message}{COLOR_RESET}")
            send_discord_alert(sender, host, message)

async def listen_to_chat(streamer_name, conn):
    uri = "wss://irc-ws.chat.twitch.tv:443"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                await websocket.send(f"PASS {ACCESS_TOKEN_TMI}")
                await websocket.send(f"NICK {USERNAME}")
                await websocket.send(f"JOIN #{streamer_name}")
                print(f"{COLOR_GREEN}Connected to chat for {streamer_name}.{COLOR_RESET}")

                while True:
                    message = await websocket.recv()
                    sender, host, chat_message = parse_chat_message(message)
                    if sender and host and chat_message:
                        print(f"{COLOR_PURPLE}[{host}] - [{sender}]: {chat_message}{COLOR_RESET}")
                        log_message(conn, sender, host, chat_message)
                        check_alerts_and_notify(conn, sender, host, chat_message)
        except Exception as e:
            print(f"{COLOR_RED}An error occurred for {streamer_name}: {e}. Retrying in 10 seconds...{COLOR_RESET}")
            await asyncio.sleep(10)

def parse_chat_message(message):
    pattern = r':(\w+)!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #(\w+) :(.+)'
    match = re.match(pattern, message)
    if match:
        return match.groups()
    return None, None, None

async def main():
    # Initialize the database
    with sqlite3.connect(DATABASE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                host TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL
            )
        ''')

    ACCESS_TOKEN, EXPIRES_IN = get_access_token(CLIENT_ID, CLIENT_SECRET)
    token_expiration_time = time.time() + EXPIRES_IN if ACCESS_TOKEN else 0

    if ACCESS_TOKEN:
        current_streams = {}
        active_tasks = {}
        stream_start_times = {}

        with sqlite3.connect(DATABASE) as conn:
            while True:
                if time.time() > token_expiration_time:
                    ACCESS_TOKEN, EXPIRES_IN = get_access_token(CLIENT_ID, CLIENT_SECRET)
                    token_expiration_time = time.time() + EXPIRES_IN

                new_streams = get_streamers(CATEGORY_ID, CLIENT_ID, ACCESS_TOKEN)

                new_streamers = set(new_streams.keys()) - set(current_streams.keys())
                gone_streamers = set(current_streams.keys()) - set(new_streams.keys())

                if new_streamers:
                    print(f"{COLOR_GREEN}+ New streamers live:{COLOR_RESET}")
                    for streamer in new_streamers:
                        if streamer not in active_tasks:
                            seconds_elapsed = get_seconds_elapsed(new_streams[streamer])
                            print(f"{COLOR_GREEN}Streamer name: {streamer}, live for {seconds_elapsed} seconds{COLOR_RESET}")
                            task = asyncio.create_task(listen_to_chat(streamer, conn))
                            active_tasks[streamer] = task
                        else:
                            seconds_elapsed = get_seconds_elapsed(new_streams[streamer])
                            print(f"{COLOR_GREEN}Streamer name: {streamer}, live for {seconds_elapsed} seconds{COLOR_RESET}")
                        stream_start_times[streamer] = new_streams[streamer]

                if gone_streamers:
                    print(f"{COLOR_RED}- Streamers who left:{COLOR_RESET}")
                    for streamer in gone_streamers:
                        uptime = get_seconds_elapsed(stream_start_times.get(streamer, datetime.now(timezone.utc).isoformat()))
                        if uptime < 600:
                            print(f"{COLOR_RED}The streamer {streamer} left before 600 seconds, but we continue listening to their chat. Uptime: {uptime} seconds{COLOR_RESET}")
                        else:
                            print(f"{COLOR_RED}Streamer name: {streamer}, Uptime: {uptime} seconds{COLOR_RESET}")
                            if streamer in active_tasks:
                                active_tasks[streamer].cancel()
                                del active_tasks[streamer]
                                del stream_start_times[streamer]

                current_streams = new_streams

                await asyncio.sleep(5)

    else:
        print("Unable to obtain a valid access token.")

if __name__ == '__main__':
    asyncio.run(main())
