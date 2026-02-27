#!/bin/bash
# Setup script for MCADV Bot Server (Distributed Mode)
# This script sets up the bot server component for distributed mode.
# The bot server runs on Pi 4/5, Jetson, or Ubuntu PC.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================================="
echo "  MCADV Bot Server Setup (Distributed Mode)"
echo "======================================================="
echo ""

# Verify we are NOT running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Do not run this script as root.${NC}"
    echo "Run as your normal user; it will ask for sudo when needed."
    exit 1
fi

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv "$REPO_DIR/venv"
echo -e "${GREEN}✓ Virtual environment created at $REPO_DIR/venv${NC}"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
"$REPO_DIR/venv/bin/pip" install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✓ logs/ directory created${NC}"
echo ""

# Install systemd service
echo "Installing systemd service..."
INSTALLED_SERVICE="/etc/systemd/system/mcadv_bot_server.service"
CURRENT_USER="$(whoami)"
INSTALL_DIR="$REPO_DIR"

# Create service file
cat > /tmp/mcadv_bot_server.service << 'EOF'
[Unit]
Description=MCADV Bot Server (Distributed Mode)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=USER_PLACEHOLDER
WorkingDirectory=INSTALL_DIR_PLACEHOLDER
# Distributed mode - runs HTTP server on port 5000, no direct radio connection
ExecStart=INSTALL_DIR_PLACEHOLDER/venv/bin/python3 INSTALL_DIR_PLACEHOLDER/adventure_bot.py \
  --distributed-mode \
  --http-port 5000 \
  --channel-idx 1
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# -------------------------------------------------------------------------
# LLM OPTIONS – uncomment ONE of the blocks below to enable AI story generation
# -------------------------------------------------------------------------

# Option A: Ollama on same machine (recommended for Pi 4/5/Jetson)
# Make sure Ollama is installed: curl -fsSL https://ollama.com/install.sh | sh
# Then pull a model: ollama pull llama3.2:1b
# ExecStart=INSTALL_DIR_PLACEHOLDER/venv/bin/python3 INSTALL_DIR_PLACEHOLDER/adventure_bot.py \
#   --distributed-mode --http-port 5000 --channel-idx 1 \
#   --ollama-url http://localhost:11434 --model llama3.2:1b

# Option B: Ollama on another machine on your LAN
# ExecStart=INSTALL_DIR_PLACEHOLDER/venv/bin/python3 INSTALL_DIR_PLACEHOLDER/adventure_bot.py \
#   --distributed-mode --http-port 5000 --channel-idx 1 \
#   --ollama-url http://192.168.1.100:11434 --model llama3.2:1b

# Option C: Groq cloud API (free tier, needs internet)
# Sign up at https://console.groq.com and get an API key
# ExecStart=INSTALL_DIR_PLACEHOLDER/venv/bin/python3 INSTALL_DIR_PLACEHOLDER/adventure_bot.py \
#   --distributed-mode --http-port 5000 --channel-idx 1 \
#   --groq-key gsk_YOUR_KEY_HERE

# Option D: OpenAI API (paid, needs internet)
# ExecStart=INSTALL_DIR_PLACEHOLDER/venv/bin/python3 INSTALL_DIR_PLACEHOLDER/adventure_bot.py \
#   --distributed-mode --http-port 5000 --channel-idx 1 \
#   --openai-key sk_YOUR_KEY_HERE

[Install]
WantedBy=multi-user.target
EOF

# Substitute user and install directory
sed \
    -e "s#INSTALL_DIR_PLACEHOLDER#$INSTALL_DIR#g" \
    -e "s#USER_PLACEHOLDER#$CURRENT_USER#g" \
    /tmp/mcadv_bot_server.service | sudo tee "$INSTALLED_SERVICE" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable mcadv_bot_server
echo -e "${GREEN}✓ Service installed and enabled${NC}"
echo ""

# Summary
echo "======================================================="
echo -e "${GREEN}✓ Bot Server setup complete!${NC}"
echo "======================================================="
echo ""
echo "Start the server:     sudo systemctl start mcadv_bot_server"
echo "Check status:         sudo systemctl status mcadv_bot_server"
echo "View logs:            sudo journalctl -u mcadv_bot_server -f"
echo ""
echo "The server will listen on:"
echo "  HTTP port: 5000"
echo "  All interfaces (0.0.0.0)"
echo ""
echo "LLM options (edit $INSTALLED_SERVICE):"
echo "  Offline (default) – built-in story trees, no internet needed"
echo "  Ollama (local)    – --ollama-url http://localhost:11434"
echo "  Ollama (LAN)      – --ollama-url http://<server-ip>:11434"
echo "  Groq (free cloud) – --groq-key gsk_..."
echo "  OpenAI            – --openai-key sk_..."
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. (Optional) Install and configure Ollama for local LLM"
echo "2. Start the bot server: sudo systemctl start mcadv_bot_server"
echo "3. On Pi Zero 2W, run: bash scripts/setup_radio_gateway.sh"
echo "4. Configure the gateway with this server's URL"
echo ""
