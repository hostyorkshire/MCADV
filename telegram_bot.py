#!/usr/bin/env python3
"""
MCADV Telegram Bot

A Telegram bot interface for playing MCADV Choose Your Own Adventure games.
Connects to MCADV HTTP API to provide interactive story experiences.
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict

import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
MCADV_SERVER_URL = os.getenv("MCADV_SERVER_URL", "http://localhost:5000")
SESSION_FILE = Path("telegram_sessions.json")

# Emojis for numbered choices
CHOICE_EMOJIS = ["1️⃣", "2️⃣", "3️⃣"]

# Per-theme emojis used in the theme selection keyboard
THEME_EMOJIS = {
    "fantasy": "⚔️",
    "medieval": "🏰",
    "scifi": "🚀",
    "horror": "👻",
    "dark_fantasy": "🌑",
    "urban_fantasy": "🏙️",
    "steampunk": "⚙️",
    "dieselpunk": "🔧",
    "cyberpunk": "🤖",
    "post_apocalypse": "☢️",
    "dystopian": "🏚️",
    "space_opera": "🌌",
    "cosmic_horror": "🐙",
    "occult": "🔮",
    "ancient": "🏛️",
    "renaissance": "🎨",
    "victorian": "🎩",
    "wild_west": "🤠",
    "comedy": "😂",
    "noir": "🕵️",
    "mystery": "🔍",
    "romance": "💕",
    "slice_of_life": "☕",
    "grimdark": "💀",
    "wholesome": "🌸",
    "high_school": "🎒",
    "college": "🎓",
    "corporate": "💼",
    "pirate": "🏴‍☠️",
    "expedition": "🗺️",
    "anime": "🎌",
    "superhero": "🦸",
    "fairy_tale": "🧚",
    "mythology": "⚡",
}

logger = logging.getLogger(__name__)


class MCADVTelegramBot:
    """Telegram bot for MCADV adventures."""

    def __init__(self, token: str, server_url: str):
        self.token = token
        self.server_url = server_url.rstrip("/")
        self.updater = Updater(token=token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        # session_key (user_N or group_N) -> session dict
        self.sessions: Dict[str, Dict] = {}

        self._load_sessions()
        self._register_handlers()

    # ------------------------------------------------------------------
    # Handler registration
    # ------------------------------------------------------------------

    def _register_handlers(self):
        """Register all command and callback handlers."""
        self.dispatcher.add_handler(CommandHandler("start", self.cmd_start))
        self.dispatcher.add_handler(CommandHandler("help", self.cmd_help))
        self.dispatcher.add_handler(CommandHandler("play", self.cmd_play))
        self.dispatcher.add_handler(CommandHandler("themes", self.cmd_themes))
        self.dispatcher.add_handler(CommandHandler("status", self.cmd_status))
        self.dispatcher.add_handler(CommandHandler("quit", self.cmd_quit))
        self.dispatcher.add_handler(CommandHandler("about", self.cmd_about))
        self.dispatcher.add_handler(CallbackQueryHandler(self.button_callback))
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_text))

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def cmd_start(self, update: Update, context: CallbackContext):
        """Handle /start command."""
        text = (
            "⚔️ *Welcome to MCADV Adventures\\!* ⚔️\n\n"
            "I'm your adventure companion, bringing Choose Your Own Adventure "
            "stories to Telegram\\!\n\n"
            "*Quick Start:*\n"
            "• /play \\- Start a new adventure\n"
            "• /themes \\- Browse available themes\n"
            "• /help \\- Learn how to play\n\n"
            "Ready for an adventure\\? Type /play to begin\\! 🗡️✨"
        )
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    def cmd_help(self, update: Update, context: CallbackContext):
        """Handle /help command."""
        text = (
            "📖 *How to Play MCADV*\n\n"
            "*Commands:*\n"
            "• /play \\[theme\\] \\- Start a new adventure\n"
            "• /themes \\- List available themes\n"
            "• /status \\- Show current adventure status\n"
            "• /quit \\- End your current adventure\n"
            "• /about \\- About MCADV\n\n"
            "*During an adventure:*\n"
            "Tap the numbered buttons to make your choices\\. "
            "Your decisions shape the story\\!\n\n"
            "*Example:*\n"
            "`/play fantasy` \\- Start a fantasy adventure"
        )
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    def cmd_play(self, update: Update, context: CallbackContext):
        """Handle /play command to start adventure."""
        args = context.args
        theme = args[0].lower() if args else "fantasy"

        session_key = self._session_key(update)
        result = self.start_adventure(session_key, theme)

        if result.get("error"):
            update.message.reply_text(result["message"])
            return

        story = result.get("story", "")
        choices = result.get("choices", [])

        text, keyboard = self.format_story_message(story, choices)
        sent = update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)

        # Store the message_id so we can edit it on subsequent choices
        self.sessions[session_key]["message_id"] = sent.message_id
        self._save_sessions()

    def cmd_themes(self, update: Update, context: CallbackContext):
        """Handle /themes command to list available themes."""
        # Ask the server for health (themes come from adventure_bot constants)
        themes = self._fetch_themes()
        if not themes:
            update.message.reply_text("❌ Could not fetch themes from server. Please try again later.")
            return

        keyboard = _create_theme_keyboard(themes)
        update.message.reply_text(
            "🎭 *Choose Your Adventure Theme:*",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

    def cmd_status(self, update: Update, context: CallbackContext):
        """Handle /status command."""
        session_key = self._session_key(update)
        session = self.sessions.get(session_key)

        if not session or session.get("status") != "active":
            update.message.reply_text(
                "📭 No active adventure. Use /play to start one\\!", parse_mode=ParseMode.MARKDOWN_V2
            )
            return

        theme = session.get("theme", "unknown")
        text = (
            f"📊 *Adventure Status*\n\n"
            f"🎭 Theme: {_escape_md(theme.replace('_', ' ').title())}\n"
            f"✅ Status: Active\n\n"
            f"Use the buttons in the story to continue, or /quit to end\\."
        )
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    def cmd_quit(self, update: Update, context: CallbackContext):
        """Handle /quit command."""
        session_key = self._session_key(update)
        self.quit_adventure(session_key)
        update.message.reply_text(
            "🛑 Adventure ended\\. Type /play to start a new one\\!", parse_mode=ParseMode.MARKDOWN_V2
        )

    def cmd_about(self, update: Update, context: CallbackContext):
        """Handle /about command."""
        text = (
            "ℹ️ *About MCADV*\n\n"
            "MCADV is a Choose Your Own Adventure bot that runs on Meshtastic "
            "mesh networks and now Telegram\\!\n\n"
            "🔗 Powered by AI\\-generated stories or built\\-in story trees\\.\n"
            "⚔️ Dozens of themes available\\.\n"
            "👥 Supports both private and group chats\\.\n\n"
            "Type /play to begin your adventure\\!"
        )
        update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

    # ------------------------------------------------------------------
    # Callback / text handlers
    # ------------------------------------------------------------------

    def button_callback(self, update: Update, context: CallbackContext):
        """Handle inline keyboard button presses."""
        query = update.callback_query
        try:
            query.answer()
            data = query.data

            session_key = self._session_key(update)

            if data == "quit":
                self.quit_adventure(session_key)
                query.edit_message_text(
                    "🛑 Adventure ended\\. Type /play to start a new one\\!", parse_mode=ParseMode.MARKDOWN_V2
                )
                return

            if data.startswith("theme_"):
                theme = data[len("theme_") :]
                result = self.start_adventure(session_key, theme)
                if result.get("error"):
                    query.edit_message_text(result["message"])
                    return

                story = result.get("story", "")
                choices = result.get("choices", [])
                text, keyboard = self.format_story_message(story, choices)
                query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
                self.sessions[session_key]["message_id"] = query.message.message_id
                self._save_sessions()
                return

            if data.startswith("choice_"):
                choice_num = int(data[len("choice_") :])
                result = self.make_choice(session_key, choice_num)
                if result.get("error"):
                    query.edit_message_text(result["message"])
                    return

                story = result.get("story", "")
                choices = result.get("choices", [])
                text, keyboard = self.format_story_message(story, choices)
                query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
                return

        except Exception as e:
            logger.error(f"Callback error: {e}")
            try:
                query.answer("❌ An error occurred. Please try again.")
            except Exception:
                pass

    def handle_text(self, update: Update, context: CallbackContext):
        """Handle plain text messages (numeric choices as fallback)."""
        content = update.message.text.strip()
        session_key = self._session_key(update)
        session = self.sessions.get(session_key)

        if not session or session.get("status") != "active":
            update.message.reply_text("Type /play to start an adventure\\!", parse_mode=ParseMode.MARKDOWN_V2)
            return

        if content in ("1", "2", "3"):
            result = self.make_choice(session_key, int(content))
            if result.get("error"):
                update.message.reply_text(result["message"])
                return

            story = result.get("story", "")
            choices = result.get("choices", [])
            text, keyboard = self.format_story_message(story, choices)
            update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN_V2)
        else:
            update.message.reply_text(
                "Use the buttons below to make your choice, or type 1, 2, or 3\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
            )

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def start_adventure(self, session_key: str, theme: str = "fantasy") -> dict:
        """Start a new adventure via API."""
        # Derive a numeric channel_idx from the session_key so each session is isolated
        channel_idx = _session_key_to_channel(session_key)
        try:
            response = requests.post(
                f"{self.server_url}/api/message",
                json={"sender": "telegram_user", "content": f"!adv {theme}", "channel_idx": channel_idx},
                timeout=10,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")
            story, choices = _parse_story_response(raw)

            self.sessions[session_key] = {
                "session_key": session_key,
                "theme": theme,
                "status": "active",
                "channel_idx": channel_idx,
            }
            self._save_sessions()
            return {"story": story, "choices": choices}

        except requests.ConnectionError:
            return {"error": True, "message": "❌ Cannot connect to adventure server\\. Please try again later\\."}
        except requests.Timeout:
            return {"error": True, "message": "⏱️ Server timeout\\. Please try again\\."}
        except Exception as e:
            logger.error(f"API error in start_adventure: {e}")
            return {"error": True, "message": f"❌ An error occurred\\: {_escape_md(str(e))}"}

    def make_choice(self, session_key: str, choice: int) -> dict:
        """Make a choice via API."""
        session = self.sessions.get(session_key)
        if not session:
            return {"error": True, "message": "❌ No active adventure\\. Use /play to start one\\."}

        channel_idx = session.get("channel_idx", _session_key_to_channel(session_key))
        try:
            response = requests.post(
                f"{self.server_url}/api/message",
                json={"sender": "telegram_user", "content": str(choice), "channel_idx": channel_idx},
                timeout=10,
            )
            response.raise_for_status()
            raw = response.json().get("response", "")
            story, choices = _parse_story_response(raw)

            if not choices or "THE END" in raw:
                self.sessions[session_key]["status"] = "finished"
                self._save_sessions()

            return {"story": story, "choices": choices}

        except requests.ConnectionError:
            return {"error": True, "message": "❌ Cannot connect to adventure server\\. Please try again later\\."}
        except requests.Timeout:
            return {"error": True, "message": "⏱️ Server timeout\\. Please try again\\."}
        except Exception as e:
            logger.error(f"API error in make_choice: {e}")
            return {"error": True, "message": f"❌ An error occurred\\: {_escape_md(str(e))}"}

    def quit_adventure(self, session_key: str):
        """Quit current adventure."""
        session = self.sessions.get(session_key)
        if session:
            channel_idx = session.get("channel_idx", _session_key_to_channel(session_key))
            try:
                requests.post(
                    f"{self.server_url}/api/message",
                    json={"sender": "telegram_user", "content": "!quit", "channel_idx": channel_idx},
                    timeout=5,
                )
            except Exception as e:
                logger.debug(f"Quit request failed (non-critical): {e}")
            del self.sessions[session_key]
            self._save_sessions()

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def format_story_message(self, story: str, choices: list) -> tuple:
        """Format story text and create inline keyboard."""
        # Highlight "THE END"
        display = story
        if "THE END" in display:
            display = display.replace("THE END", "*THE END* 🎉")

        display = _escape_md(display)
        # Re-apply bold markers that we embedded before escaping
        display = display.replace("\\*THE END\\* 🎉", "*THE END* 🎉")

        header = "📜 *Your Adventure*\n\n"

        if choices:
            text = header + display + "\n\n🎯 *What will you do?*"
            keyboard = _create_choice_keyboard(choices)
        else:
            text = header + display
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Play Again", callback_data="theme_fantasy")]])

        return text, keyboard

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _load_sessions(self):
        """Load sessions from JSON file."""
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, "r") as f:
                    self.sessions = json.load(f)
                logger.info(f"Loaded {len(self.sessions)} sessions")
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")
                self.sessions = {}

    def _save_sessions(self):
        """Save sessions to JSON file."""
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump(self.sessions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    # ------------------------------------------------------------------
    # Session key helpers
    # ------------------------------------------------------------------

    def _session_key(self, update: Update) -> str:
        """Generate session key (user or group)."""
        chat = update.effective_chat
        if chat.type == "private":
            return f"user_{update.effective_user.id}"
        return f"group_{chat.id}"

    def _is_group_chat(self, update: Update) -> bool:
        """Check if message is from a group chat."""
        return update.effective_chat.type in ("group", "supergroup")

    # ------------------------------------------------------------------
    # Theme discovery
    # ------------------------------------------------------------------

    def _fetch_themes(self) -> list:
        """Fetch available themes from the MCADV server health endpoint."""
        # The server doesn't expose a /themes endpoint, so we return the
        # known theme list directly (mirrors VALID_THEMES in adventure_bot.py).
        return list(THEME_EMOJIS.keys())

    # ------------------------------------------------------------------
    # Bot lifecycle
    # ------------------------------------------------------------------

    def run(self):
        """Start the bot."""
        logger.info("Starting MCADV Telegram Bot...")
        self.updater.start_polling()
        self.updater.idle()


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _session_key_to_channel(session_key: str) -> int:
    """Convert a session key string to a stable integer channel index.

    Uses the absolute value of hash() for determinism within a process.
    The channel_idx is only used server-side to namespace sessions, so any
    unique integer per user/group is fine.
    """
    return abs(hash(session_key)) % (10**9)


def _split_choices(text: str) -> list:
    """Extract choice labels from a string formatted as '1:A 2:B 3:C'.

    Uses a simple split on digit-colon tokens instead of a backtracking regex.
    """
    if not text:
        return []
    # Split on occurrences of "N:" (digit followed by colon)
    tokens = re.split(r"\s*\d+:", text)
    # First token is whatever comes before "1:" — discard it
    choices = [t.strip() for t in tokens[1:] if t.strip()]
    return choices


def _parse_story_response(raw: str) -> tuple:
    """Parse the MCADV API response into (story_text, choices_list).

    The adventure_bot formats responses as::

        Story text here.
        1:Choice A 2:Choice B 3:Choice C

    or, for the end of the story, just story text with no choices.
    """
    if not raw:
        return "", []

    # Split on the last newline to separate story from choices
    parts = raw.rsplit("\n", 1)
    if len(parts) == 2:
        story_part, choices_part = parts
    else:
        story_part = raw
        choices_part = ""

    # Parse "1:ChoiceA 2:ChoiceB 3:ChoiceC" by splitting on "N:" separators.
    # This avoids backtracking-prone regexes.
    choices = _split_choices(choices_part.strip() if choices_part else "")

    # Fallback: if no choices found in the last line, check the full text.
    if not choices and re.search(r"\d+:[^\s]", raw):
        choices = _split_choices(raw)
        if choices:
            # Remove the choice portion (last "N:..." segment) from the story text.
            idx = raw.rfind("\n")
            story_part = raw[:idx].strip() if idx != -1 else ""

    return story_part.strip(), choices


def _create_choice_keyboard(choices: list) -> InlineKeyboardMarkup:
    """Create inline keyboard with choice buttons."""
    keyboard = []
    for i, choice in enumerate(choices):
        emoji = CHOICE_EMOJIS[i] if i < len(CHOICE_EMOJIS) else f"{i+1}."
        keyboard.append([InlineKeyboardButton(f"{emoji} {choice}", callback_data=f"choice_{i+1}")])

    keyboard.append([InlineKeyboardButton("❌ Quit Adventure", callback_data="quit")])
    return InlineKeyboardMarkup(keyboard)


def _create_theme_keyboard(themes: list) -> InlineKeyboardMarkup:
    """Create inline keyboard for theme selection."""
    keyboard = []
    for theme in themes:
        emoji = THEME_EMOJIS.get(theme, "📖")
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{emoji} {theme.replace('_', ' ').title()}",
                    callback_data=f"theme_{theme}",
                )
            ]
        )
    return InlineKeyboardMarkup(keyboard)


def _escape_md(text: str) -> str:
    """Escape special MarkdownV2 characters in text."""
    # Characters that must be escaped in MarkdownV2
    special = r"_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Main entry point."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        raise SystemExit(1)

    server_url = os.getenv("MCADV_SERVER_URL", "http://localhost:5000")
    bot = MCADVTelegramBot(token=token, server_url=server_url)
    bot.run()


if __name__ == "__main__":
    main()
