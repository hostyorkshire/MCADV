# MCADV Terminal Client

A standalone terminal interface for playing MCADV adventures with rich formatting
and ASCII art. Connects to any MCADV HTTP server (local or remote).

## Installation

### From Source

```bash
# Clone repository
git clone https://github.com/hostyorkshire/MCADV.git
cd MCADV

# Install dependencies
pip install -r requirements-terminal.txt

# Run client
python terminal_client.py play
```

### Using Standalone Executable

Download the latest release for your platform from the GitHub Releases page:

- Windows: `mcadv-cli.exe`
- Linux: `mcadv-cli`
- macOS: `mcadv-cli`

```bash
# Make executable (Linux/macOS)
chmod +x mcadv-cli

# Run
./mcadv-cli play
```

## Usage

### Start Adventure

```bash
python terminal_client.py play
```

### Start with a Specific Theme

```bash
python terminal_client.py play --theme fantasy
```

### Connect to Remote Server

```bash
python terminal_client.py --server http://example.com:5000 play
```

### List Available Themes

```bash
python terminal_client.py themes
```

### Check Server Status

```bash
python terminal_client.py health
```

### View/Update Configuration

```bash
# View current config
python terminal_client.py config

# Set default server URL
python terminal_client.py config --server-url http://myserver:5000

# Set default theme
python terminal_client.py config --theme scifi
```

### View Saved History

```bash
python terminal_client.py history
```

## Commands During Gameplay

| Command   | Description                 |
|-----------|-----------------------------|
| `1` / `2` / `3` | Make a choice         |
| `history` | View choices made so far    |
| `status`  | Show adventure status       |
| `help`    | Show available commands     |
| `quit`    | End adventure (with prompt) |

## Configuration

Config file location: `~/.mcadv/config.json`

```json
{
  "server_url": "http://localhost:5000",
  "theme_preference": "fantasy",
  "enable_sound": false,
  "enable_animations": true,
  "color_scheme": "default"
}
```

## Adventure History

Your choice history is automatically saved to `~/.mcadv/history.json` after
each completed (or quit) adventure.

## Building a Standalone Executable

### Linux / macOS

```bash
chmod +x build_executable.sh
./build_executable.sh
# Output: dist/mcadv-cli
```

### Windows

```batch
build_executable.bat
:: Output: dist\mcadv-cli.exe
```

## Troubleshooting

### Cannot connect to server

Make sure the MCADV server is running:

```bash
python adventure_bot.py --http-port 5000
```

### Colors not displaying correctly

Your terminal may not support ANSI colors. Recommended terminals:

- **Windows:** Windows Terminal or PowerShell 7+
- **Linux/macOS:** Most modern terminals work out of the box (xterm-256color)

The client automatically falls back to plain text if color is not supported.

## Dependencies

- [click](https://click.palletsprojects.com/) — CLI framework
- [rich](https://github.com/Textualize/rich) — Rich terminal formatting
- [requests](https://docs.python-requests.org/) — HTTP client
