#!/bin/bash
# MCADV - Interactive Full Setup Script
# Menu-driven configuration assistant for the MeshCore Adventure Bot
# Run as your normal user (not root). The script will ask for sudo when needed.

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script and repo directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$SCRIPT_DIR"
cd "$REPO_DIR"

# Configuration variables (will be set by user choices)
SETUP_VENV=""
SERIAL_PORT=""
BAUD_RATE="115200"
USE_CHANNEL=""
CHANNEL_NAME=""
LLM_BACKEND="offline"
OLLAMA_URL="http://localhost:11434"
OLLAMA_MODEL="llama3.2:1b"
ENABLE_ANNOUNCE="no"
ENABLE_DEBUG="no"
INSTALL_SERVICE="no"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠  $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ  $1${NC}"
}

# Function to display menu and get user choice
show_menu() {
    local title="$1"
    shift
    local options=("$@")
    
    echo ""
    echo -e "${BLUE}${title}${NC}"
    echo ""
    
    local i=1
    for option in "${options[@]}"; do
        echo "  $i) $option"
        ((i++))
    done
    echo ""
}

# Function to get user input with validation
get_input() {
    local prompt="$1"
    local default="$2"
    local result
    
    if [ -n "$default" ]; then
        read -p "$(echo -e ${CYAN}$prompt [${default}]: ${NC})" result
        result="${result:-$default}"
    else
        read -p "$(echo -e ${CYAN}$prompt: ${NC})" result
    fi
    
    echo "$result"
}

# Function to get yes/no input
get_yes_no() {
    local prompt="$1"
    local default="$2"
    local result
    
    if [ "$default" = "yes" ]; then
        read -p "$(echo -e ${CYAN}$prompt [Y/n]: ${NC})" result
        result="${result:-y}"
    else
        read -p "$(echo -e ${CYAN}$prompt [y/N]: ${NC})" result
        result="${result:-n}"
    fi
    
    case "$result" in
        [Yy]|[Yy][Ee][Ss]) echo "yes" ;;
        *) echo "no" ;;
    esac
}

# ============================================================================
# Setup Steps
# ============================================================================

verify_not_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "Do not run this script as root."
        echo "Run as your normal user; it will ask for sudo when needed."
        exit 1
    fi
}

detect_serial_ports() {
    local ports=()
    
    for port in /dev/ttyUSB* /dev/ttyACM* /dev/ttyAMA*; do
        if [ -e "$port" ]; then
            ports+=("$port")
        fi
    done
    
    echo "${ports[@]}"
}

setup_python_environment() {
    print_header "Step 1: Python Environment Setup"
    
    print_info "The bot requires Python 3.7+ with a virtual environment."
    echo ""
    
    if [ -d "$REPO_DIR/venv" ]; then
        print_warning "Virtual environment already exists at $REPO_DIR/venv"
        local recreate=$(get_yes_no "Do you want to recreate it?" "no")
        
        if [ "$recreate" = "yes" ]; then
            echo "Removing existing virtual environment..."
            rm -rf "$REPO_DIR/venv"
            SETUP_VENV="yes"
        else
            SETUP_VENV="no"
            print_info "Using existing virtual environment"
        fi
    else
        SETUP_VENV="yes"
    fi
    
    if [ "$SETUP_VENV" = "yes" ]; then
        echo "Creating Python virtual environment..."
        python3 -m venv "$REPO_DIR/venv" || {
            print_error "Failed to create virtual environment"
            print_info "Try: sudo apt install python3-venv"
            exit 1
        }
        print_success "Virtual environment created"
        
        echo ""
        echo "Installing Python dependencies..."
        "$REPO_DIR/venv/bin/pip" install --upgrade pip >/dev/null 2>&1
        "$REPO_DIR/venv/bin/pip" install -r "$REPO_DIR/requirements.txt" || {
            print_error "Failed to install dependencies"
            exit 1
        }
        print_success "Dependencies installed (requests, pyserial, flask)"
    fi
    
    # Create logs directory
    mkdir -p "$REPO_DIR/logs"
    print_success "Logs directory ready"
    
    echo ""
    read -p "Press Enter to continue..."
}

configure_serial_port() {
    print_header "Step 2: Serial Port Configuration"
    
    print_info "The bot needs a serial connection to your MeshCore LoRa radio."
    echo ""
    
    # Detect available ports
    local detected_ports=($(detect_serial_ports))
    
    if [ ${#detected_ports[@]} -eq 0 ]; then
        print_warning "No serial ports detected."
        echo ""
        print_info "Options:"
        echo "  1) Skip (use terminal mode for testing)"
        echo "  2) Enter port manually (e.g., /dev/ttyUSB0)"
        echo ""
        local choice=$(get_input "Your choice" "1")
        
        if [ "$choice" = "2" ]; then
            SERIAL_PORT=$(get_input "Enter serial port path" "/dev/ttyUSB0")
        else
            SERIAL_PORT=""
            print_info "No serial port configured (terminal mode only)"
        fi
    else
        echo "Detected serial ports:"
        local i=1
        for port in "${detected_ports[@]}"; do
            echo "  $i) $port"
            ((i++))
        done
        echo "  $i) Enter manually"
        echo "  $((i+1))) Skip (terminal mode only)"
        echo ""
        
        local choice=$(get_input "Select port" "1")
        
        if [ "$choice" = "$i" ]; then
            SERIAL_PORT=$(get_input "Enter serial port path" "/dev/ttyUSB0")
        elif [ "$choice" = "$((i+1))" ]; then
            SERIAL_PORT=""
            print_info "No serial port configured (terminal mode only)"
        elif [ "$choice" -ge 1 ] && [ "$choice" -lt "$i" ]; then
            SERIAL_PORT="${detected_ports[$((choice-1))]}"
            print_success "Selected: $SERIAL_PORT"
        else
            print_error "Invalid choice"
            exit 1
        fi
    fi
    
    if [ -n "$SERIAL_PORT" ]; then
        echo ""
        local change_baud=$(get_yes_no "Change baud rate? (default: 115200)" "no")
        if [ "$change_baud" = "yes" ]; then
            BAUD_RATE=$(get_input "Enter baud rate" "115200")
        fi
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

configure_channel() {
    print_header "Step 3: Channel Configuration"
    
    print_info "You can restrict the bot to only respond on a specific channel."
    echo ""
    echo "Examples:"
    echo "  - Leave blank: Bot responds to all messages"
    echo "  - 'adventure': Bot only responds on the 'adventure' channel"
    echo "  - 'games': Bot only responds on the 'games' channel"
    echo ""
    
    local use_channel=$(get_yes_no "Do you want to restrict to a specific channel?" "no")
    
    if [ "$use_channel" = "yes" ]; then
        USE_CHANNEL="yes"
        CHANNEL_NAME=$(get_input "Enter channel name" "adventure")
        print_success "Bot will only respond on channel: $CHANNEL_NAME"
    else
        USE_CHANNEL="no"
        print_info "Bot will respond to all channels"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

configure_llm_backend() {
    print_header "Step 4: LLM Backend Configuration"
    
    print_info "Choose how the bot generates adventure stories:"
    echo ""
    echo "  1) Offline Mode (Default)"
    echo "     - Uses built-in story trees"
    echo "     - No internet or LLM needed"
    echo "     - Fast and reliable"
    echo ""
    echo "  2) Ollama (Local LLM)"
    echo "     - AI-generated unique stories"
    echo "     - Requires Ollama server (local or LAN)"
    echo "     - More flexible but slower"
    echo ""
    
    local choice=$(get_input "Select backend" "1")
    
    case "$choice" in
        1)
            LLM_BACKEND="offline"
            print_success "Using offline mode (built-in stories)"
            ;;
        2)
            LLM_BACKEND="ollama"
            echo ""
            print_info "Ollama Configuration"
            echo ""
            OLLAMA_URL=$(get_input "Enter Ollama server URL" "http://localhost:11434")
            
            echo ""
            echo "Recommended models:"
            echo "  - llama3.2:1b (fast, 1.3GB, good for Pi 4/5)"
            echo "  - llama3.2:3b (medium, 3.2GB, Pi 5)"
            echo "  - llama3.1:8b (best quality, 4.9GB, Jetson/PC)"
            echo ""
            OLLAMA_MODEL=$(get_input "Enter model name" "llama3.2:1b")
            
            print_success "Ollama configured: $OLLAMA_URL with model $OLLAMA_MODEL"
            print_info "Make sure Ollama is running and the model is pulled!"
            ;;
        *)
            print_error "Invalid choice, using offline mode"
            LLM_BACKEND="offline"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
}

configure_bot_behavior() {
    print_header "Step 5: Bot Behavior Settings"
    
    print_info "Configure additional bot behaviors:"
    echo ""
    
    # Announcements
    local announce=$(get_yes_no "Enable periodic announcements? (every 3 hours)" "no")
    ENABLE_ANNOUNCE="$announce"
    
    if [ "$announce" = "yes" ]; then
        print_info "Bot will announce itself every 3 hours"
    fi
    
    echo ""
    
    # Debug mode
    local debug=$(get_yes_no "Enable debug logging?" "no")
    ENABLE_DEBUG="$debug"
    
    if [ "$debug" = "yes" ]; then
        print_info "Debug logging enabled (verbose output)"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

configure_systemd_service() {
    print_header "Step 6: Systemd Service Installation"
    
    print_info "Install the bot as a systemd service to run automatically at boot."
    echo ""
    print_warning "Note: Requires sudo privileges"
    echo ""
    
    local install=$(get_yes_no "Install systemd service?" "yes")
    INSTALL_SERVICE="$install"
    
    echo ""
    read -p "Press Enter to continue..."
}

show_configuration_summary() {
    print_header "Configuration Summary"
    
    echo "Review your configuration:"
    echo ""
    echo -e "${CYAN}Python Environment:${NC}"
    echo "  Virtual environment: $REPO_DIR/venv"
    echo "  Status: $([ "$SETUP_VENV" = "yes" ] && echo "Created/Updated" || echo "Existing")"
    echo ""
    
    echo -e "${CYAN}Serial Port:${NC}"
    if [ -n "$SERIAL_PORT" ]; then
        echo "  Port: $SERIAL_PORT"
        echo "  Baud rate: $BAUD_RATE"
    else
        echo "  Not configured (terminal mode only)"
    fi
    echo ""
    
    echo -e "${CYAN}Channel:${NC}"
    if [ "$USE_CHANNEL" = "yes" ]; then
        echo "  Restricted to: $CHANNEL_NAME"
    else
        echo "  All channels (no restriction)"
    fi
    echo ""
    
    echo -e "${CYAN}LLM Backend:${NC}"
    if [ "$LLM_BACKEND" = "ollama" ]; then
        echo "  Mode: Ollama (AI-generated)"
        echo "  URL: $OLLAMA_URL"
        echo "  Model: $OLLAMA_MODEL"
    else
        echo "  Mode: Offline (built-in stories)"
    fi
    echo ""
    
    echo -e "${CYAN}Bot Behavior:${NC}"
    echo "  Announcements: $([ "$ENABLE_ANNOUNCE" = "yes" ] && echo "Enabled" || echo "Disabled")"
    echo "  Debug logging: $([ "$ENABLE_DEBUG" = "yes" ] && echo "Enabled" || echo "Disabled")"
    echo ""
    
    echo -e "${CYAN}Systemd Service:${NC}"
    echo "  Install: $([ "$INSTALL_SERVICE" = "yes" ] && echo "Yes" || echo "No")"
    echo ""
}

build_command_line() {
    local cmd="$REPO_DIR/run_adventure_bot.sh"
    
    # Add serial port
    if [ -n "$SERIAL_PORT" ]; then
        cmd="$cmd --port $SERIAL_PORT --baud $BAUD_RATE"
    else
        cmd="$cmd --terminal"
    fi
    
    # Add channel
    if [ "$USE_CHANNEL" = "yes" ]; then
        cmd="$cmd --channel $CHANNEL_NAME"
    fi
    
    # Add LLM backend
    if [ "$LLM_BACKEND" = "ollama" ]; then
        cmd="$cmd --ollama-url $OLLAMA_URL --model $OLLAMA_MODEL"
    fi
    
    # Add announcements
    if [ "$ENABLE_ANNOUNCE" = "yes" ]; then
        cmd="$cmd --announce"
    fi
    
    # Add debug
    if [ "$ENABLE_DEBUG" = "yes" ]; then
        cmd="$cmd --debug"
    fi
    
    echo "$cmd"
}

install_systemd_service() {
    if [ "$INSTALL_SERVICE" != "yes" ]; then
        return
    fi
    
    print_header "Installing Systemd Service"
    
    local service_file="$REPO_DIR/scripts/adventure_bot.service"
    local installed_service="/etc/systemd/system/adventure_bot.service"
    local current_user="$(whoami)"
    
    if [ ! -f "$service_file" ]; then
        print_error "Service file not found: $service_file"
        return
    fi
    
    # Build the ExecStart command
    local exec_cmd="$REPO_DIR/venv/bin/python3 $REPO_DIR/adventure_bot.py"
    
    if [ -n "$SERIAL_PORT" ]; then
        exec_cmd="$exec_cmd --port $SERIAL_PORT --baud $BAUD_RATE"
    fi
    
    if [ "$USE_CHANNEL" = "yes" ]; then
        exec_cmd="$exec_cmd --channel $CHANNEL_NAME"
    fi
    
    if [ "$LLM_BACKEND" = "ollama" ]; then
        exec_cmd="$exec_cmd --ollama-url $OLLAMA_URL --model $OLLAMA_MODEL"
    fi
    
    if [ "$ENABLE_ANNOUNCE" = "yes" ]; then
        exec_cmd="$exec_cmd --announce"
    fi
    
    if [ "$ENABLE_DEBUG" = "yes" ]; then
        exec_cmd="$exec_cmd --debug"
    fi
    
    echo "Creating systemd service file..."
    
    # Create a customized service file
    cat > /tmp/adventure_bot.service <<EOF
[Unit]
Description=MCADV - MeshCore Adventure Bot
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$REPO_DIR
ExecStart=$exec_cmd
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Install the service
    sudo mv /tmp/adventure_bot.service "$installed_service"
    sudo chmod 644 "$installed_service"
    sudo systemctl daemon-reload
    sudo systemctl enable adventure_bot
    
    print_success "Systemd service installed and enabled"
    echo ""
    print_info "Service commands:"
    echo "  Start:  sudo systemctl start adventure_bot"
    echo "  Stop:   sudo systemctl stop adventure_bot"
    echo "  Status: sudo systemctl status adventure_bot"
    echo "  Logs:   sudo journalctl -u adventure_bot -f"
}

test_configuration() {
    print_header "Test Configuration"
    
    print_info "You can test your configuration now."
    echo ""
    
    local cmd=$(build_command_line)
    echo "The bot will run with this command:"
    echo ""
    echo -e "${YELLOW}$cmd${NC}"
    echo ""
    
    if [ -z "$SERIAL_PORT" ]; then
        print_info "Terminal mode: You can type messages to test the bot"
        echo "Try: !adv fantasy"
    else
        print_warning "Radio mode: The bot will listen on $SERIAL_PORT"
    fi
    
    echo ""
    local run_test=$(get_yes_no "Run a test now?" "yes")
    
    if [ "$run_test" = "yes" ]; then
        echo ""
        echo "Starting bot... (Press Ctrl+C to stop)"
        echo ""
        sleep 2
        eval "$cmd"
    fi
}

# ============================================================================
# Main Menu
# ============================================================================

show_welcome() {
    clear
    echo ""
    echo -e "${GREEN}================================================${NC}"
    echo -e "${GREEN}  MCADV - Full Interactive Setup${NC}"
    echo -e "${GREEN}  MeshCore Adventure Bot Configuration${NC}"
    echo -e "${GREEN}================================================${NC}"
    echo ""
    echo "This script will guide you through configuring the"
    echo "MeshCore Adventure Bot with a menu-driven interface."
    echo ""
    echo "You can configure:"
    echo "  ✓ Python environment and dependencies"
    echo "  ✓ Serial port and hardware settings"
    echo "  ✓ Channel restrictions"
    echo "  ✓ LLM backend (Offline or Ollama)"
    echo "  ✓ Bot behavior (announcements, debug)"
    echo "  ✓ Systemd service installation"
    echo ""
    read -p "Press Enter to begin setup..."
}

run_full_setup() {
    verify_not_root
    show_welcome
    
    # Run setup steps
    setup_python_environment
    configure_serial_port
    configure_channel
    configure_llm_backend
    configure_bot_behavior
    configure_systemd_service
    
    # Show summary
    show_configuration_summary
    
    echo ""
    local confirm=$(get_yes_no "Proceed with this configuration?" "yes")
    
    if [ "$confirm" != "yes" ]; then
        print_warning "Setup cancelled"
        exit 0
    fi
    
    # Install systemd service if requested
    install_systemd_service
    
    # Final summary
    print_header "Setup Complete!"
    
    print_success "MCADV is configured and ready to use!"
    echo ""
    
    if [ "$INSTALL_SERVICE" = "yes" ]; then
        echo "The bot is installed as a systemd service."
        echo ""
        echo "To start the bot:"
        echo "  sudo systemctl start adventure_bot"
        echo ""
        echo "To check status:"
        echo "  sudo systemctl status adventure_bot"
        echo ""
        echo "To view logs:"
        echo "  sudo journalctl -u adventure_bot -f"
    else
        echo "To run the bot manually:"
        echo ""
        echo -e "${YELLOW}$(build_command_line)${NC}"
    fi
    
    echo ""
    echo "Bot commands for users:"
    echo "  !adv [theme]  - Start adventure (fantasy/scifi/horror)"
    echo "  1 / 2 / 3     - Make choices"
    echo "  !quit         - End adventure"
    echo "  !help         - Show help"
    echo ""
    
    print_info "For more information, see:"
    echo "  - README.md - Quick start guide"
    echo "  - SETUP.md - Virtual environment details"
    echo "  - guides/OLLAMA_SETUP.md - LLM setup guide"
    echo ""
    
    # Offer to test
    test_configuration
}

# ============================================================================
# Entry Point
# ============================================================================

run_full_setup
