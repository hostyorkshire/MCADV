#!/bin/bash
# Setup script for MCADV Radio Gateway (Pi Zero 2W)
# This script sets up the radio gateway component for distributed mode.

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================================="
echo "  MCADV Radio Gateway Setup (Distributed Mode)"
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

# Get bot server URL
echo -e "${YELLOW}Bot server URL configuration required${NC}"
echo "Enter the bot server URL (e.g., http://pi5.local:5000 or http://192.168.1.50:5000):"
read -r -p "Bot server URL: " BOT_SERVER_URL

if [ -z "$BOT_SERVER_URL" ]; then
    echo -e "${RED}Error: Bot server URL is required${NC}"
    exit 1
fi

# Install systemd service
echo ""
echo "Installing systemd service..."
INSTALLED_SERVICE="/etc/systemd/system/radio_gateway.service"
CURRENT_USER="$(whoami)"
INSTALL_DIR="$REPO_DIR"

# Create service file with user's configuration
cat > /tmp/radio_gateway.service << EOF
[Unit]
Description=MCADV Radio Gateway (Distributed Mode)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/radio_gateway.py \\
  --bot-server-url $BOT_SERVER_URL \\
  --port $DETECTED_PORT \\
  --baud 115200 \\
  --channel-idx 1
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo mv /tmp/radio_gateway.service "$INSTALLED_SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable radio_gateway
echo -e "${GREEN}✓ Service installed and enabled${NC}"
echo ""

# Summary
echo "======================================================="
echo -e "${GREEN}✓ Radio Gateway setup complete!${NC}"
echo "======================================================="
echo ""
echo "Start the gateway:    sudo systemctl start radio_gateway"
echo "Check status:         sudo systemctl status radio_gateway"
echo "View logs:            sudo journalctl -u radio_gateway -f"
echo ""
echo "Configuration:"
echo "  Bot server: $BOT_SERVER_URL"
echo "  Serial port: $DETECTED_PORT"
echo "  Channel: 1"
echo ""
echo -e "${YELLOW}Important:${NC} Make sure the bot server is running before starting the gateway!"
echo "On the bot server (Pi 4/5), run:"
echo "  python3 adventure_bot.py --distributed-mode"
echo ""
