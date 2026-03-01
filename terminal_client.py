#!/usr/bin/env python3
"""
MCADV Terminal Client

A standalone terminal interface for playing MCADV adventures.
Connects to MCADV HTTP server and provides a rich CLI experience.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import click
import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

DEFAULT_CONFIG: Dict = {
    "server_url": "http://localhost:5000",
    "theme_preference": "fantasy",
    "enable_sound": False,
    "enable_animations": True,
    "color_scheme": "default",
}

CONFIG_PATH = Path.home() / ".mcadv" / "config.json"
HISTORY_PATH = Path.home() / ".mcadv" / "history.json"

# Number-emoji mapping for choices (supports up to 9 options)
_NUMBER_EMOJI = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]

# ASCII art banner
_BANNER = r"""
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   ███╗   ███╗ ██████╗ █████╗ ██████╗ ██╗   ██╗              ║
║   ████╗ ████║██╔════╝██╔══██╗██╔══██╗██║   ██║              ║
║   ██╔████╔██║██║     ███████║██║  ██║██║   ██║              ║
║   ██║╚██╔╝██║██║     ██╔══██║██║  ██║╚██╗ ██╔╝              ║
║   ██║ ╚═╝ ██║╚██████╗██║  ██║██████╔╝ ╚████╔╝               ║
║   ╚═╝     ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝   ╚═══╝                ║
║                                                               ║
║        ⚔  Meshcore Adventures - Terminal Edition  ⚔          ║
║                 Choose Your Own Adventure                     ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
"""

# Themes known to the bot (used when server listing is unavailable)
_KNOWN_THEMES = [
    ("fantasy", "Classic sword-and-sorcery adventure", "gold1"),
    ("scifi", "Space exploration and cyberpunk", "cyan"),
    ("horror", "Dark and terrifying survival", "red"),
]


def load_config() -> Dict:
    """Load configuration from ~/.mcadv/config.json."""
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            # Fill in any missing keys with defaults
            for key, value in DEFAULT_CONFIG.items():
                cfg.setdefault(key, value)
            return cfg
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: Dict) -> None:
    """Save configuration to ~/.mcadv/config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def load_history() -> List[Dict]:
    """Load adventure history from ~/.mcadv/history.json."""
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def save_history(history: List[Dict]) -> None:
    """Save adventure history to ~/.mcadv/history.json."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history, f, indent=2)


# ---------------------------------------------------------------------------
# Cross-platform helpers
# ---------------------------------------------------------------------------


def detect_terminal() -> str:
    """Detect terminal type for optimal rendering."""
    if sys.platform == "win32":
        return "windows"
    term = os.environ.get("TERM", "")
    if term:
        return term
    return "unknown"


def supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    return sys.stdout.isatty() and detect_terminal() != "unknown"


# ---------------------------------------------------------------------------
# Main client class
# ---------------------------------------------------------------------------


class MCADVTerminalClient:
    """Terminal client for MCADV adventures."""

    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url.rstrip("/")
        self.session_id: Optional[str] = None
        self.history: List[Dict] = load_history()
        self._current_adventure: List[Dict] = []

        # Respect terminal capabilities
        if not supports_color():
            self.console = Console(force_terminal=False, no_color=True)
        else:
            self.console = Console()

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def display_banner(self) -> None:
        """Display ASCII art banner."""
        self.console.print(Text(_BANNER, style="bold gold1"))

    def display_help(self) -> None:
        """Show available commands during gameplay."""
        table = Table(title="⚔ Available Commands", box=box.ROUNDED, style="yellow")
        table.add_column("Command", style="bold green")
        table.add_column("Description", style="cyan")

        table.add_row("1 / 2 / 3", "Make a choice")
        table.add_row("history", "View previous choices")
        table.add_row("status", "Show adventure status")
        table.add_row("help", "Show this help")
        table.add_row("quit", "End adventure (with confirmation)")

        self.console.print(table)

    def display_story(self, story: str, choices: List[str]) -> None:
        """Display story text and choices with rich formatting."""
        # Story panel
        story_text = Text(f"\n  {story}\n", style="cyan")
        self.console.print(
            Panel(
                story_text,
                title="[bold cyan]📜 Your Adventure[/bold cyan]",
                border_style="cyan",
                box=box.HEAVY,
            )
        )

        if not choices:
            return

        # Choices panel
        choices_text = Text()
        for i, choice in enumerate(choices):
            emoji = _NUMBER_EMOJI[i] if i < len(_NUMBER_EMOJI) else f"{i + 1}."
            choices_text.append(f"\n  {emoji}  {choice}\n", style="yellow")

        self.console.print(
            Panel(
                choices_text,
                title="[bold yellow]⚔ Your Choices[/bold yellow]",
                border_style="yellow",
                box=box.HEAVY,
            )
        )

    # ------------------------------------------------------------------
    # Server communication
    # ------------------------------------------------------------------

    def check_server(self) -> bool:
        """Check if the server is reachable."""
        try:
            resp = requests.get(f"{self.server_url}/api/health", timeout=5)
            return resp.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def _send_message(self, content: str) -> str:
        """Send a message to the server and return the text response."""
        payload = {
            "sender": "terminal_user",
            "content": content,
            "channel_idx": 1,
        }
        with self.console.status("[bold yellow]⏳ Consulting the ancient scrolls...", spinner="dots"):
            resp = requests.post(
                f"{self.server_url}/api/message",
                json=payload,
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def list_themes(self) -> List[Dict]:
        """Return available themes (uses built-in list as fallback)."""
        themes = []
        for name, desc, color in _KNOWN_THEMES:
            themes.append({"name": name, "description": desc, "color": color})
        return themes

    def start_adventure(self, theme: str) -> str:
        """Start a new adventure by sending the theme to the server."""
        return self._send_message(f"!start {theme}")

    def make_choice(self, choice: int) -> str:
        """Make a numbered choice and get the next story segment."""
        return self._send_message(str(choice))

    def quit_adventure(self) -> None:
        """End the current adventure and save history."""
        if self._current_adventure:
            self.history.append(
                {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "session": self._current_adventure,
                }
            )
            save_history(self.history)
        self._current_adventure = []
        self.session_id = None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response: str):
        """
        Parse a server response into (story_text, choices).

        The server returns free-form text.  We do a simple heuristic split:
        lines that start with a digit followed by '.' or ')' are choices.
        Everything else is story text.
        """
        lines = response.strip().splitlines()
        story_lines: List[str] = []
        choices: List[str] = []

        for line in lines:
            stripped = line.strip()
            # Detect choice lines: "1. ...", "1) ...", "1: ..."
            if len(stripped) >= 3 and stripped[0].isdigit() and stripped[1] in ".):":
                choices.append(stripped[2:].strip())
            else:
                story_lines.append(line)

        story = "\n".join(story_lines).strip()
        return story, choices

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------

    def play(self, theme: Optional[str] = None) -> None:
        """Main game loop."""
        self.display_banner()

        # Server connectivity check
        if not self.check_server():
            self.console.print(f"[bold red]❌ Cannot connect to MCADV server at {self.server_url}![/bold red]")
            self.console.print("[red]Make sure the server is running:[/red]")
            self.console.print("[yellow]  python adventure_bot.py --http-port 5000[/yellow]")
            sys.exit(1)

        self.console.print(f"[bold magenta]✅ Connected to server: {self.server_url}[/bold magenta]\n")

        # Theme selection
        if theme is None:
            themes = self.list_themes()
            table = Table(title="Available Themes", box=box.ROUNDED)
            table.add_column("#", style="bold white", width=4)
            table.add_column("Theme", style="bold")
            table.add_column("Description")
            for i, t in enumerate(themes, 1):
                table.add_row(str(i), f"[{t['color']}]{t['name']}[/]", t["description"])
            self.console.print(table)

            theme_names = [t["name"] for t in themes]
            theme = Prompt.ask(
                "\n[bold yellow]Choose a theme[/bold yellow]",
                choices=theme_names,
                default=theme_names[0],
            )

        self.console.print(f"\n[bold magenta]🏰 Starting a [bold]{theme}[/bold] adventure...[/bold magenta]\n")

        # Start adventure
        try:
            response = self.start_adventure(theme)
        except requests.ConnectionError:
            self.console.print("[bold red]❌ Lost connection to the server.[/bold red]")
            sys.exit(1)
        except requests.Timeout:
            self.console.print("[bold red]⏱️ Server timeout![/bold red]")
            sys.exit(1)
        except Exception as e:  # pylint: disable=broad-except
            self.console.print(f"[bold red]Error: {e}[/bold red]")
            sys.exit(1)

        story, choices = self._parse_response(response)
        self._current_adventure.append({"story": story, "choices": choices})
        self.display_story(story, choices)

        # Check for immediate game-over
        if not choices:
            self._finish_game()
            return

        # Main loop
        valid_choices = [str(i + 1) for i in range(len(choices))]
        while True:
            choice_input = (
                Prompt.ask(
                    "[bold yellow]⚔ What will you do?[/bold yellow]",
                    default=valid_choices[0] if valid_choices else "quit",
                )
                .strip()
                .lower()
            )

            if choice_input == "quit":
                if Confirm.ask("[bold red]Are you sure you want to quit?[/bold red]", default=False):
                    self.console.print("[bold magenta]⚔ Farewell, brave adventurer![/bold magenta]")
                    self.quit_adventure()
                    return
                continue

            if choice_input == "help":
                self.display_help()
                continue

            if choice_input == "history":
                self._display_session_history()
                continue

            if choice_input == "status":
                self._display_status(len(self._current_adventure))
                continue

            if choice_input not in valid_choices:
                self.console.print(
                    f"[bold red]Invalid choice. Enter {'/'.join(valid_choices)}, "
                    "quit, help, history, or status.[/bold red]"
                )
                continue

            # Send choice to server
            try:
                response = self.make_choice(int(choice_input))
            except requests.ConnectionError:
                self.console.print("[bold red]❌ Lost connection to the server.[/bold red]")
                self.quit_adventure()
                return
            except requests.Timeout:
                self.console.print("[bold red]⏱️ Server timeout! Try again.[/bold red]")
                continue
            except Exception as e:  # pylint: disable=broad-except
                self.console.print(f"[bold red]Error: {e}[/bold red]")
                continue

            story, choices = self._parse_response(response)
            self._current_adventure.append({"story": story, "choices": choices, "choice_made": choice_input})
            self.display_story(story, choices)

            # No choices remaining → game over
            if not choices:
                self._finish_game()
                return

            valid_choices = [str(i + 1) for i in range(len(choices))]

    def _finish_game(self) -> None:
        """Handle end-of-adventure."""
        self.console.print(
            Panel(
                "[bold green]🎉  THE END  🎉\n\nYour adventure is complete![/bold green]",
                border_style="green",
                box=box.DOUBLE,
            )
        )
        self.quit_adventure()

    def _display_session_history(self) -> None:
        """Display choices made in the current session."""
        if not self._current_adventure:
            self.console.print("[yellow]No adventure history yet.[/yellow]")
            return
        table = Table(title="📜 Session History", box=box.ROUNDED, style="cyan")
        table.add_column("Step", style="bold white", width=6)
        table.add_column("Choice Made", style="yellow")
        for i, entry in enumerate(self._current_adventure, 1):
            choice = entry.get("choice_made", "start")
            table.add_row(str(i), choice)
        self.console.print(table)

    def _display_status(self, steps: int) -> None:
        """Display current adventure status."""
        self.console.print(
            Panel(
                f"[cyan]Server:[/cyan]  {self.server_url}\n[cyan]Steps:[/cyan]   {steps}",
                title="[bold magenta]ℹ Adventure Status[/bold magenta]",
                border_style="magenta",
                box=box.ROUNDED,
            )
        )


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--server",
    default=None,
    help="MCADV server URL (overrides config file)",
)
@click.pass_context
def cli(ctx: click.Context, server: Optional[str]) -> None:
    """MCADV Terminal Client - Choose Your Own Adventure in the Terminal."""
    config = load_config()
    url = server or config.get("server_url", DEFAULT_CONFIG["server_url"])
    ctx.ensure_object(dict)
    ctx.obj = MCADVTerminalClient(server_url=url)


@cli.command()
@click.option("--theme", default=None, help="Adventure theme (fantasy/scifi/horror)")
@click.pass_obj
def play(client: MCADVTerminalClient, theme: Optional[str]) -> None:
    """Start playing an adventure."""
    client.play(theme=theme)


@cli.command()
@click.pass_obj
def themes(client: MCADVTerminalClient) -> None:
    """List available adventure themes."""
    client.display_banner()
    theme_list = client.list_themes()
    table = Table(title="🏰 Available Themes", box=box.ROUNDED)
    table.add_column("#", style="bold white", width=4)
    table.add_column("Theme", style="bold")
    table.add_column("Description")
    for i, t in enumerate(theme_list, 1):
        table.add_row(str(i), f"[{t['color']}]{t['name']}[/]", t["description"])
    client.console.print(table)


@cli.command()
@click.pass_obj
def health(client: MCADVTerminalClient) -> None:
    """Check server health."""
    client.console.print(f"[bold cyan]Checking server: {client.server_url}[/bold cyan]")
    if client.check_server():
        client.console.print("[bold green]✅ Server is healthy and reachable![/bold green]")
    else:
        client.console.print(f"[bold red]❌ Cannot reach server at {client.server_url}[/bold red]")
        sys.exit(1)


@cli.command("config")
@click.option("--server-url", default=None, help="Set default server URL")
@click.option("--theme", default=None, help="Set default theme preference")
def configure(server_url: Optional[str], theme: Optional[str]) -> None:
    """View or update configuration."""
    console = Console()
    cfg = load_config()

    if server_url:
        cfg["server_url"] = server_url
    if theme:
        cfg["theme_preference"] = theme

    if server_url or theme:
        save_config(cfg)
        console.print("[bold green]✅ Configuration saved.[/bold green]")

    table = Table(title="⚙ Current Configuration", box=box.ROUNDED, style="cyan")
    table.add_column("Key", style="bold yellow")
    table.add_column("Value", style="white")
    for key, value in cfg.items():
        table.add_row(key, str(value))
    console.print(table)


@cli.command("history")
def show_history() -> None:
    """Show saved adventure history."""
    console = Console()
    hist = load_history()
    if not hist:
        console.print("[yellow]No saved adventure history found.[/yellow]")
        return

    console.print(f"[bold cyan]📜 Found {len(hist)} saved adventure(s):[/bold cyan]\n")
    for i, session in enumerate(hist, 1):
        console.print(f"[bold yellow]Adventure {i}[/bold yellow] — {session.get('timestamp', 'unknown')}")
        for j, entry in enumerate(session.get("session", []), 1):
            choice = entry.get("choice_made", "start")
            console.print(f"  Step {j}: choice = {choice}")
        console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cli()
