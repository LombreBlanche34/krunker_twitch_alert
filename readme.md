# 🎥 Krunker Twitch Alert

This project is a real-time Twitch chat monitoring bot with a web interface for viewing and managing alerts. It detects sensitive keywords, logs chat messages to a database, and sends alert notifications to Discord.

---

## ⚙️ Features

- Automatically connects to the chat of streamers currently live in a specific Twitch category (`Krunker` by default).
- Detects messages containing predefined keywords.
- Sends styled alerts via Discord Webhook.
- Web interface (Flask) to:
  - View recent messages.
  - Search by message content, streamer, sender, or date.
  - Add or remove alert keywords.
  - Display activity charts (most active streamers or senders).

⚠️ Note: The first 10 minutes of a stream are not considered as stopped because Twitch's API frequently produces false positives during this period, repeatedly reporting streamers as offline or online.
---

## 🧰 Technologies Used

- Python (asyncio, websockets, requests)
- Twitch API & IRC WebSocket
- Flask (web dashboard)
- SQLite (local database)
- Discord Webhooks
- python-dotenv

---

## 🏁 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/LombreBlanche34/krunker_twitch_alert.git
cd krunker_twitch_alert
pip install -r requirements.txt
```

### 2. Environment Setup (.env Configuration)

```env
ACCESS_TOKEN_TMI=oauth:your_twitch_chat_token
USERNAME=your_twitch_bot_username
CLIENT_ID=your_twitch_client_id
CLIENT_SECRET=your_twitch_client_secret
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_id
DATABASE=chat.db
```

### 3. Starting
```bash
py bot.py
py app.py
```

![panel](https://github.com/LombreBlanche34/krunker_twitch_alert/blob/main/img/panel.png)
![console](https://github.com/LombreBlanche34/krunker_twitch_alert/blob/main/img/console.png)
