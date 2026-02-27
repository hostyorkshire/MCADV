"""Centralized command definitions and validation for MCADV Adventure Bot."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BotCommand:
    name: str
    aliases: List[str]
    description: str
    usage: str
    requires_arg: bool = False


HELP_CMD = BotCommand(
    name="!help",
    aliases=["help"],
    description="Show available commands",
    usage="!help",
)

START_CMD = BotCommand(
    name="!adv",
    aliases=["!start"],
    description="Start a new adventure",
    usage="!adv [theme]",
    requires_arg=False,
)

QUIT_CMD = BotCommand(
    name="!quit",
    aliases=["!end"],
    description="End the current adventure",
    usage="!quit",
)

STATUS_CMD = BotCommand(
    name="!status",
    aliases=[],
    description="Check current adventure status",
    usage="!status",
)

RESET_CMD = BotCommand(
    name="!reset",
    aliases=[],
    description="Bot-only reset command (silently ignored for users)",
    usage="!reset",
)

USER_COMMANDS = [HELP_CMD, START_CMD, QUIT_CMD, STATUS_CMD]
BOT_COMMANDS = [RESET_CMD]


def is_valid_choice(text: str) -> bool:
    """Return True if text is a valid story choice (1, 2, or 3)."""
    return text.strip() in ["1", "2", "3"]


def parse_start_command(content: str) -> Optional[str]:
    """Parse a start command and return the theme, or None if not a start command.

    Returns the theme string (defaults to 'fantasy' if not specified).
    """
    if content.startswith("!adv") or content.startswith("!start"):
        parts = content.split(maxsplit=1)
        return parts[1] if len(parts) > 1 else "fantasy"
    return None


def get_command_type(text: str) -> Optional[str]:
    """Return command type string or None if not a recognized command."""
    text = text.strip()
    if text in [HELP_CMD.name] + HELP_CMD.aliases:
        return "help"
    if text.startswith(START_CMD.name) or text.startswith(START_CMD.aliases[0]):
        return "start"
    if text in [QUIT_CMD.name] + QUIT_CMD.aliases:
        return "quit"
    if text == STATUS_CMD.name:
        return "status"
    if text == RESET_CMD.name:
        return "reset"
    if is_valid_choice(text):
        return "choice"
    return None
