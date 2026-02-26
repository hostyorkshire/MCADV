#!/bin/bash
# MCADV – Setup script for Raspberry Pi Zero
# Run once as your normal user (not root). The script will ask for sudo
# when it needs elevated privileges.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "================================================"
echo "  MCADV – MeshCore Adventure Bot Setup"
echo "================================================"
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

# Install Python dependencies into the virtual environment
echo "Installing Python dependencies..."
"$REPO_DIR/venv/bin/pip" install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Create logs directory
mkdir -p logs
echo -e "${GREEN}✓ logs/ directory created${NC}"
echo ""

# Detect serial port
echo "Detecting MeshCore radio serial port..."
DETECTED_PORT=""
for port in /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyACM0 /dev/ttyAMA0; do
    if [ -e "$port" ]; then
        DETECTED_PORT="$port"
        echo -e "${GREEN}✓ Found serial port: $port${NC}"
        break
    fi
done
if [ -z "$DETECTED_PORT" ]; then
    echo -e "${YELLOW}⚠  No serial port auto-detected.${NC}"
    echo "   Connect your MeshCore radio and specify --port manually."
    DETECTED_PORT="/dev/ttyUSB0"
fi
echo ""

# Install systemd service
echo "Installing systemd service..."
SERVICE_FILE="$SCRIPT_DIR/adventure_bot.service"
INSTALLED_SERVICE="/etc/systemd/system/adventure_bot.service"
CURRENT_USER="$(whoami)"
INSTALL_DIR="$REPO_DIR"

# Substitute real paths and username into the service file
sed \
    -e "s#/home/pi/MCADV#$INSTALL_DIR#g" \
    -e "s#User=pi#User=$CURRENT_USER#g" \
    "$SERVICE_FILE" | sudo tee "$INSTALLED_SERVICE" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable adventure_bot
echo -e "${GREEN}✓ Service installed and enabled${NC}"
echo ""

# Summary
echo "================================================"
echo -e "${GREEN}✓ MCADV setup complete!${NC}"
echo "================================================"
echo ""
echo "Start the bot now:    sudo systemctl start adventure_bot"
echo "Check status:         sudo systemctl status adventure_bot"
echo "View logs:            sudo journalctl -u adventure_bot -f"
echo ""
echo "LLM options (edit $INSTALLED_SERVICE):"
echo "  Offline (default) – built-in story trees, no internet needed"
echo "  Ollama (LAN)      – --ollama-url http://<server-ip>:11434"
echo "  Groq (free cloud) – --groq-key gsk_..."
echo "  OpenAI            – --openai-key sk_..."
echo ""
echo "Players on the channel can type:"
echo "  !adv            – start a fantasy adventure"
echo "  !adv scifi      – start a sci-fi adventure"
echo "  !adv horror     – start a horror adventure"
echo "  1 / 2 / 3       – make a choice"
echo "  !quit           – end the adventure"
echo "  !help           – show commands"
echo ""
