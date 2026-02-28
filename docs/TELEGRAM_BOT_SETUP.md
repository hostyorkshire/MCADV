# Telegram Bot Setup Guide

## Step 1: Create Your Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "MCADV Adventure Bot")
4. Choose a username (must end in 'bot', e.g., `mcadv_adventure_bot`)
5. BotFather will give you a **token** - copy this!

**Example token:** `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

## Step 2: Configure the Bot

1. Set bot commands for better UX by sending `/setcommands` to BotFather, then paste:

   ```
   start - Start the bot and see welcome message
   play - Start a new adventure
   themes - Browse available adventure themes
   status - Check current adventure status
   quit - End current adventure
   help - Show how to play
   about - About MCADV
   ```

2. Set bot description with `/setdescription`, then paste:

   ```
   Choose Your Own Adventure bot! Start epic interactive stories in Telegram. Type /play to begin your adventure! ⚔️
   ```

3. Optionally set a bot profile picture with `/setuserpic`.

## Step 3: Run the Bot

### Option A: Local Development

```bash
# Make sure MCADV server is running
python adventure_bot.py --http-port 5000

# In another terminal, install Telegram dependencies and start the bot
pip install -r requirements-telegram.txt
export TELEGRAM_BOT_TOKEN="your_token_here"
python telegram_bot.py
```

### Option B: Docker

```bash
# Copy and edit the example environment file
cp .env.example .env
# Set TELEGRAM_BOT_TOKEN in .env

# Run with docker-compose
docker-compose -f docker-compose.telegram.yml up
```

### Option C: Production Server (systemd)

```bash
# Edit the service file with your token and paths
sudo cp telegram_bot.service /etc/systemd/system/
sudo systemctl enable telegram_bot
sudo systemctl start telegram_bot
```

## Step 4: Test Your Bot

1. Open Telegram
2. Search for your bot username (e.g., @mcadv_adventure_bot)
3. Click **Start** or send `/start`
4. Try `/play` to start an adventure!

## Troubleshooting

### Bot doesn't respond

- Check that the bot token is correct in your environment
- Check that the MCADV server is running: `curl http://localhost:5000/api/health`
- Check logs: `tail -f telegram_bot.log`

### "Cannot connect to adventure server"

- Make sure `MCADV_SERVER_URL` points to your running MCADV instance
- Test the server directly: `curl http://localhost:5000/api/health`

### Rate limiting

Telegram has rate limits. If you hit them:

- Wait 1 minute before sending more messages
- Consider switching to webhook mode for high-traffic bots

## Advanced: Webhook Mode

For production deployments, use webhooks instead of polling:

```python
# In telegram_bot.py, replace updater.start_polling() with:
updater.start_webhook(
    listen="0.0.0.0",
    port=8443,
    url_path=TELEGRAM_BOT_TOKEN,
    webhook_url=f"https://yourdomain.com/{TELEGRAM_BOT_TOKEN}",
)
```

## Security Best Practices

1. **Never commit your token** — use environment variables or a `.env` file
2. **Use HTTPS** for webhooks in production
3. **Monitor logs** for suspicious activity
4. **Set rate limits** in your bot code if needed

## Updating Your Bot

```bash
# Stop the bot
sudo systemctl stop telegram_bot

# Pull latest code
git pull

# Install any new dependencies
pip install -r requirements-telegram.txt

# Restart bot
sudo systemctl start telegram_bot
```
