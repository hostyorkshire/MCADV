#!/usr/bin/env python3
"""
MCADV Adventure Bot

A text adventure bot that runs on Meshtastic mesh networks or HTTP.
Supports collaborative storytelling where multiple users can participate in the same adventure.
"""

import argparse
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Set

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

from meshcore import MeshCoreMessage

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_MSG_LEN = 230
SESSION_EXPIRY_SECONDS = 3600  # 1 hour
INACTIVITY_RESET_SECONDS = 86400  # 24 hours
SESSION_FILE = Path("adventure_sessions.json")

VALID_THEMES = [
    "fantasy",
    "medieval",
    "scifi",
    "horror",
    "dark_fantasy",
    "urban_fantasy",
    "steampunk",
    "dieselpunk",
    "cyberpunk",
    "post_apocalypse",
    "dystopian",
    "space_opera",
    "cosmic_horror",
    "occult",
    "ancient",
    "renaissance",
    "victorian",
    "wild_west",
    "comedy",
    "noir",
    "mystery",
    "romance",
    "slice_of_life",
    "grimdark",
    "wholesome",
    "high_school",
    "college",
    "corporate",
    "pirate",
    "expedition",
    "anime",
    "superhero",
    "fairy_tale",
    "mythology",
]

# =============================================================================
# STORY TREES
# =============================================================================

_FANTASY_STORY = {
    "start": {
        "text": "You stand at a crossroads. A path to the north leads into a dark forest. To the east, a mountain trail. To the south, a village.",
        "choices": ["North", "East", "South"],
        "next": {"A": "forest", "B": "mountain", "C": "village"},
    },
    "forest": {
        "text": "The forest is thick and eerie. You hear rustling in the bushes.",
        "choices": ["Investigate", "Keep walking", "Turn back"],
        "next": {"A": "creature", "B": "clearing", "C": "start"},
    },
    "creature": {
        "text": "A friendly sprite appears! It offers you a magical amulet. THE END",
        "choices": [],
        "next": {},
    },
    "clearing": {
        "text": "You find a peaceful clearing with a sparkling pond. THE END",
        "choices": [],
        "next": {},
    },
    "mountain": {
        "text": "The mountain path is steep. Halfway up, you encounter a cave.",
        "choices": ["Enter cave", "Continue climbing", "Go back"],
        "next": {"A": "cave", "B": "summit", "C": "start"},
    },
    "cave": {
        "text": "Inside the cave, you find ancient treasure! THE END",
        "choices": [],
        "next": {},
    },
    "summit": {
        "text": "You reach the summit and see a breathtaking view of the realm. THE END",
        "choices": [],
        "next": {},
    },
    "village": {
        "text": "The village is bustling. A merchant offers you a quest.",
        "choices": ["Accept quest", "Decline", "Browse market"],
        "next": {"A": "quest", "B": "start", "C": "market"},
    },
    "quest": {
        "text": "The merchant thanks you! Your adventure begins. THE END",
        "choices": [],
        "next": {},
    },
    "market": {
        "text": "You browse the market and find interesting wares. THE END",
        "choices": [],
        "next": {},
    },
    "road": {
        "text": "On the road, a troll demands payment!",
        "choices": ["Pay toll", "Fight", "Run away"],
        "next": {"A": "road_pay", "B": "road_fight", "C": "start"},
    },
    "road_pay": {
        "text": "The troll lets you pass safely. THE END",
        "choices": [],
        "next": {},
    },
    "road_fight": {
        "text": "You bravely defeat the troll! THE END",
        "choices": [],
        "next": {},
    },
}

_SCIFI_STORY = {
    "start": {
        "text": "You wake up on a colony ship. Alarms blare. The AI reports: engine failure, alien contact, or mutiny.",
        "choices": ["Check engines", "Investigate signal", "Find crew"],
        "next": {"A": "engines", "B": "signal", "C": "crew"},
    },
    "engines": {
        "text": "The engine room is damaged. You can repair it or seal the breach.",
        "choices": ["Repair", "Seal breach", "Return"],
        "next": {"A": "repaired", "B": "sealed", "C": "start"},
    },
    "repaired": {
        "text": "Engines restored! The ship is saved. THE END",
        "choices": [],
        "next": {},
    },
    "sealed": {
        "text": "Breach sealed. Life support stabilized. THE END",
        "choices": [],
        "next": {},
    },
    "signal": {
        "text": "An alien vessel approaches. They seem curious.",
        "choices": ["Attempt contact", "Prepare weapons", "Hide"],
        "next": {"A": "contact", "B": "weapons", "C": "hide"},
    },
    "contact": {
        "text": "The aliens are friendly! They offer aid. THE END",
        "choices": [],
        "next": {},
    },
    "weapons": {
        "text": "A tense standoff, but no shots fired. THE END",
        "choices": [],
        "next": {},
    },
    "hide": {
        "text": "You hide successfully. The aliens leave. THE END",
        "choices": [],
        "next": {},
    },
    "crew": {
        "text": "You find the crew arguing. There's tension.",
        "choices": ["Mediate", "Take command", "Observe"],
        "next": {"A": "mediate", "B": "command", "C": "observe"},
    },
    "mediate": {
        "text": "Your diplomacy prevents a mutiny! THE END",
        "choices": [],
        "next": {},
    },
    "command": {
        "text": "You assert authority. Order is restored. THE END",
        "choices": [],
        "next": {},
    },
    "observe": {
        "text": "You watch and learn valuable information. THE END",
        "choices": [],
        "next": {},
    },
}

_HORROR_STORY = {
    "start": {
        "text": "You arrive at an abandoned manor at dusk. The front door creaks open. You hear whispers.",
        "choices": ["Enter", "Investigate grounds", "Leave"],
        "next": {"A": "enter", "B": "grounds", "C": "escape"},
    },
    "enter": {
        "text": "Inside, a grand staircase looms. Shadows move on the walls.",
        "choices": ["Go upstairs", "Check basement", "Search ground floor"],
        "next": {"A": "upstairs", "B": "basement", "C": "ground_floor"},
    },
    "upstairs": {
        "text": "You find a locked room. A key lies on a dusty table.",
        "choices": ["Use key", "Leave it", "Go back"],
        "next": {"A": "locked_room", "B": "enter", "C": "enter"},
    },
    "locked_room": {
        "text": "Inside, you discover the truth about the manor. THE END",
        "choices": [],
        "next": {},
    },
    "basement": {
        "text": "The basement is dark and damp. Something moves in the shadows.",
        "choices": ["Approach", "Run", "Stay still"],
        "next": {"A": "approach", "B": "escape", "C": "still"},
    },
    "approach": {
        "text": "It's just a rat. You breathe a sigh of relief. THE END",
        "choices": [],
        "next": {},
    },
    "still": {
        "text": "The shadow passes. You're safe... for now. THE END",
        "choices": [],
        "next": {},
    },
    "ground_floor": {
        "text": "You find a journal detailing the manor's dark history.",
        "choices": ["Read it", "Ignore it", "Take it"],
        "next": {"A": "read", "B": "enter", "C": "take"},
    },
    "read": {
        "text": "The journal reveals terrible secrets. THE END",
        "choices": [],
        "next": {},
    },
    "take": {
        "text": "You take the journal and leave with evidence. THE END",
        "choices": [],
        "next": {},
    },
    "grounds": {
        "text": "The grounds are overgrown. You find an old cemetery.",
        "choices": ["Explore", "Return to manor", "Leave"],
        "next": {"A": "cemetery", "B": "start", "C": "escape"},
    },
    "cemetery": {
        "text": "The graves are ancient. One is freshly disturbed. THE END",
        "choices": [],
        "next": {},
    },
    "escape": {
        "text": "You flee the manor and never return. THE END",
        "choices": [],
        "next": {},
    },
}

# Map theme names to their story trees
FALLBACK_STORIES = {
    "fantasy": _FANTASY_STORY,
    "scifi": _SCIFI_STORY,
    "horror": _HORROR_STORY,
}

# For themes without custom stories, use fantasy as default
for theme in VALID_THEMES:
    if theme not in FALLBACK_STORIES:
        FALLBACK_STORIES[theme] = _FANTASY_STORY

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def _is_valid_uuid(value: str) -> bool:
    """Return True if *value* is a valid UUID string (case-insensitive)."""
    return bool(_UUID_RE.match(value))


# =============================================================================
# ADVENTURE BOT CLASS
# =============================================================================


class AdventureBot:
    """
    Adventure Bot for collaborative storytelling on Meshtastic mesh networks.

    Multiple users on the same channel share the same adventure story.
    Sessions are tracked by channel, not by individual users.
    """

    def __init__(
        self,
        debug: bool = False,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama2",
        http_host: str = "0.0.0.0",
        http_port: int = 5000,
        distributed_mode: bool = False,
        admin_users: Optional[List[str]] = None,
    ):
        self.debug = debug
        self.ollama_url = ollama_url
        self.model = model
        self.http_host = http_host
        self.http_port = http_port
        self.distributed_mode = distributed_mode
        self.admin_users: List[str] = admin_users or []

        self._sessions: Dict[str, Dict] = {}
        self._session_lock = Lock()
        self._last_story_activity = time.time()
        self._quit_votes: Dict[str, Set[str]] = {}
        self._vote_threshold: int = 3

        # Set up logging first
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        self.logger = logging.getLogger(__name__)

        # Load existing sessions
        self._load_sessions()

        # Set up Flask app for HTTP mode
        self.app = Flask(__name__)

        # Enable CORS for web interface
        if os.getenv("WEB_INTERFACE_ENABLED", "true").lower() == "true":
            allowed_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*").split(",")
            CORS(self.app, origins=allowed_origins)

        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes for HTTP mode."""

        @self.app.route("/api/message", methods=["POST"])
        def message_endpoint():
            try:
                data = request.get_json(silent=False)
                if data is None:
                    return jsonify({"error": "Invalid JSON or missing Content-Type header"}), 400
            except BadRequest as e:
                return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400

            msg = MeshCoreMessage(
                sender=data.get("sender", "user"),
                content=data.get("content", ""),
                channel_idx=data.get("channel_idx", 1),
            )
            response = self.handle_message(msg)
            return jsonify({"response": response})

        @self.app.route("/api/health", methods=["GET"])
        def health():
            mode = "distributed" if self.distributed_mode else "http"
            return jsonify({"status": "healthy", "mode": mode})

        @self.app.route("/api/themes", methods=["GET"])
        def themes():
            return jsonify({"themes": VALID_THEMES})

        @self.app.route("/api/adventure/start", methods=["POST"])
        def adventure_start():
            try:
                data = request.get_json(silent=False) or {}
            except BadRequest as e:
                return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400

            theme = data.get("theme", "fantasy")
            if theme not in VALID_THEMES:
                return jsonify({"error": f"Invalid theme. Valid themes: {', '.join(VALID_THEMES)}"}), 400

            # Use provided session_id or generate a new one
            raw_id = data.get("session_id")
            if raw_id is None:
                raw_id = str(uuid.uuid4())
            # Validate UUID format if provided
            if not _is_valid_uuid(raw_id):
                return jsonify({"error": "Invalid session_id format (must be UUID)"}), 400

            session_key = self._session_key_web(raw_id)
            self._clear_session(session_key)
            self._update_session(
                session_key,
                {"status": "active", "theme": theme, "node": "start", "history": []},
            )
            self._last_story_activity = time.time()

            story_text = self._generate_story(session_key, None, theme)
            session = self._get_session(session_key)
            choices = self._get_current_choices(session_key, theme)
            status = session.get("status", "active")

            return jsonify(
                {
                    "session_id": raw_id,
                    "story": story_text,
                    "choices": choices,
                    "status": status,
                }
            )

        @self.app.route("/api/adventure/choice", methods=["POST"])
        def adventure_choice():
            try:
                data = request.get_json(silent=False) or {}
            except BadRequest as e:
                return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400

            raw_id = data.get("session_id", "")
            choice = str(data.get("choice", ""))

            if not raw_id or not _is_valid_uuid(raw_id):
                return jsonify({"error": "Invalid or missing session_id (must be UUID)"}), 400

            if choice not in ("1", "2", "3"):
                return jsonify({"error": "Choice must be 1, 2, or 3"}), 400

            session_key = self._session_key_web(raw_id)
            session = self._get_session(session_key)
            if not session or session.get("status") != "active":
                return jsonify({"error": "No active adventure for this session"}), 404

            theme = session.get("theme", "fantasy")
            self._last_story_activity = time.time()

            story_text = self._generate_story(session_key, choice, theme)
            session = self._get_session(session_key)
            status = session.get("status", "active")
            choices = self._get_current_choices(session_key, theme) if status == "active" else []

            if status == "finished":
                self._clear_session(session_key)

            return jsonify({"story": story_text, "choices": choices, "status": status})

        @self.app.route("/api/adventure/status", methods=["GET"])
        def adventure_status():
            raw_id = request.args.get("session_id", "")
            if not raw_id or not _is_valid_uuid(raw_id):
                return jsonify({"error": "Invalid or missing session_id (must be UUID)"}), 400

            session_key = self._session_key_web(raw_id)
            session = self._get_session(session_key)
            if not session:
                return jsonify({"status": "none", "theme": None, "history_length": 0})

            return jsonify(
                {
                    "status": session.get("status", "none"),
                    "theme": session.get("theme"),
                    "history_length": len(session.get("history", [])),
                }
            )

        @self.app.route("/api/adventure/quit", methods=["POST"])
        def adventure_quit():
            try:
                data = request.get_json(silent=False) or {}
            except BadRequest as e:
                return jsonify({"error": f"Failed to parse JSON: {str(e)}"}), 400

            raw_id = data.get("session_id", "")
            if not raw_id or not _is_valid_uuid(raw_id):
                return jsonify({"error": "Invalid or missing session_id (must be UUID)"}), 400

            session_key = self._session_key_web(raw_id)
            self._clear_session(session_key)
            return jsonify({"message": "Adventure ended", "status": "quit"})

    def _session_key(self, message: MeshCoreMessage) -> str:
        """
        Generate session key based on channel.

        In collaborative mode, all users on the same channel share the same story.
        """
        return f"channel_{message.channel_idx}"

    def _session_key_web(self, session_id: str) -> str:
        """Generate session key for web users."""
        return f"web_{session_id}"

    def _is_web_session(self, session_key: str) -> bool:
        """Check if session is from web interface."""
        return session_key.startswith("web_")

    def _get_current_choices(self, session_key: str, theme: str) -> List[str]:
        """Return the list of available choices for the current story node."""
        session = self._get_session(session_key)
        current_node = session.get("node", "start")
        story_tree = FALLBACK_STORIES.get(theme, _FANTASY_STORY)
        node_data = story_tree.get(current_node, {})
        return node_data.get("choices", [])

    def _is_admin(self, sender: str) -> bool:
        """Check if a sender is an admin. If no admins configured, everyone is admin."""
        if not self.admin_users:
            return True
        return sender in self.admin_users

    def _get_session(self, session_key: str) -> Dict:
        """Get session data for a session key."""
        with self._session_lock:
            return self._sessions.get(session_key, {}).copy()

    def _update_session(self, session_key: str, data: Dict):
        """Update session data, merging with existing data."""
        with self._session_lock:
            if session_key not in self._sessions:
                self._sessions[session_key] = {}
            self._sessions[session_key].update(data)
            self._sessions[session_key]["last_active"] = time.time()
        self._save_sessions()

    def _clear_session(self, session_key: str):
        """Clear a session."""
        with self._session_lock:
            if session_key in self._sessions:
                del self._sessions[session_key]
            self._quit_votes.pop(session_key, None)
        self._save_sessions()

    def _expire_sessions(self):
        """Remove expired sessions."""
        now = time.time()
        with self._session_lock:
            expired = [
                key
                for key, session in self._sessions.items()
                if now - session.get("last_active", 0) > SESSION_EXPIRY_SECONDS
            ]
            for key in expired:
                del self._sessions[key]
                self._quit_votes.pop(key, None)
                self.logger.info(f"Expired session: {key}")

    def _save_sessions(self, force: bool = False):
        """Save sessions to disk (batched to reduce I/O)."""
        if force or len(self._sessions) > 0:
            with self._session_lock:
                try:
                    with open(SESSION_FILE, "w") as f:
                        json.dump(self._sessions, f)
                except (OSError, json.JSONEncodeError) as e:
                    self.logger.error(f"Failed to save sessions: {e}")

    def _load_sessions(self):
        """Load sessions from disk."""
        if SESSION_FILE.exists():
            try:
                with open(SESSION_FILE, "r") as f:
                    self._sessions = json.load(f)
                self.logger.info(f"Loaded {len(self._sessions)} sessions")
            except (OSError, json.JSONDecodeError, ValueError) as e:
                self.logger.error(f"Failed to load sessions: {e}")
                self._sessions = {}

    def _format_story_message(self, text: str, choices: List[str]) -> str:
        """Format a story message with lettered choices."""
        if not choices:
            return text

        choice_text = " ".join([f"{chr(65+i)}:{c}" for i, c in enumerate(choices)])
        return f"{text}\n{choice_text}"

    def _get_fallback_story(self, session_key: str, choice: Optional[str], theme: str) -> str:
        """
        Navigate the fallback story tree based on choice.

        Returns formatted story text with choices.
        """
        session = self._get_session(session_key)
        current_node = session.get("node", "start")

        # Get the story tree for this theme
        story_tree = FALLBACK_STORIES.get(theme, _FANTASY_STORY)

        # If a choice was made, navigate to next node
        if choice and current_node in story_tree:
            node_data = story_tree[current_node]
            next_nodes = node_data.get("next", {})
            if choice in next_nodes:
                current_node = next_nodes[choice]
            else:
                # Invalid choice, reset to start
                current_node = "start"

        # Get current node data
        if current_node not in story_tree:
            current_node = "start"

        node_data = story_tree[current_node]
        text = node_data["text"]
        choices_list = node_data["choices"]

        # Update session with new node
        self._update_session(session_key, {"node": current_node})

        # Check if this is a terminal node (THE END)
        if not choices_list or "THE END" in text:
            self._update_session(session_key, {"status": "finished"})

        return self._format_story_message(text, choices_list)

    def _call_ollama(self, session_key: str, choice: Optional[str], theme: str) -> Optional[str]:
        """
        Call Ollama API to generate story content.

        Returns None if Ollama is unavailable or fails.
        """
        session = self._get_session(session_key)
        history = session.get("history", [])

        # Build prompt
        prompt = f"You are a {theme} adventure game master. "

        if not history:
            prompt += "Start a new adventure. Describe the opening scene and give 3 choices labeled A, B, C."
        else:
            prompt += f"The player chose option {choice}. Continue the story. "
            prompt += f"Previous: {history[-1] if history else ''}. "
            prompt += "Provide 3 new choices labeled A, B, C, or end with 'THE END'."

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=10,
            )
            if response.status_code == 200:
                result = response.json().get("response", "")
                return result if result else None
            return None
        except Exception as e:
            self.logger.debug(f"Ollama call failed: {e}")
            return None

    def _generate_story(self, session_key: str, choice: Optional[str], theme: str) -> str:
        """
        Generate story content, trying Ollama first, then falling back to tree.
        """
        # Try Ollama first
        llm_result = self._call_ollama(session_key, choice, theme)

        if llm_result:
            # Check if story ended
            if "THE END" in llm_result:
                self._update_session(session_key, {"status": "finished"})

            # Update history
            session = self._get_session(session_key)
            history = session.get("history", [])
            history.append(llm_result)
            self._update_session(session_key, {"history": history})

            return llm_result

        # Fallback to story tree
        return self._get_fallback_story(session_key, choice, theme)

    def _bot_reset(self) -> str:
        """Reset all sessions (called by system, not users)."""
        with self._session_lock:
            self._sessions.clear()
            self._quit_votes.clear()
        self._save_sessions(force=True)
        return "Resetting all adventures due to 24 hours of inactivity."

    def handle_message(self, message: MeshCoreMessage) -> Optional[str]:
        """
        Handle incoming message and return response.

        Returns None if no response should be sent.
        """
        content = message.content.strip()
        session_key = self._session_key(message)

        # Expire old sessions periodically
        self._expire_sessions()

        # Help command
        if content in ["!help", "help"]:
            themes_list = ", ".join(VALID_THEMES[:5]) + "..."
            return (
                f"MCADV Adventure Bot Commands:\n"
                f"!adv [theme] - Start adventure (default: fantasy)\n"
                f"!start [theme] - Start adventure\n"
                f"A/B/C - Make a choice\n"
                f"!quit - End adventure [ADMIN ONLY]\n"
                f"!vote - Vote to end adventure (3 votes needed)\n"
                f"!status - Check status\n"
                f"Themes: {themes_list}"
            )

        # Start adventure (!adv or !start)
        if content.startswith("!adv") or content.startswith("!start"):
            parts = content.split(maxsplit=1)
            theme = parts[1] if len(parts) > 1 else "fantasy"

            # Validate theme
            if theme not in VALID_THEMES:
                theme = "fantasy"

            # Clear existing session and start new one
            self._clear_session(session_key)
            self._update_session(
                session_key,
                {"status": "active", "theme": theme, "node": "start", "history": []},
            )

            # Update activity timestamp
            self._last_story_activity = time.time()

            # Generate opening
            return self._generate_story(session_key, None, theme)

        # Quit/end command
        if content in ["!quit", "!end"]:
            if self._is_admin(message.sender):
                self._clear_session(session_key)
                return "🛑 Admin ended adventure. Type !adv to start new."
            return "⛔ Only admins can use !quit. Use !vote to vote for ending."

        # Vote to end command
        if content == "!vote":
            session = self._get_session(session_key)
            if not session or session.get("status") != "active":
                return "⛔ No active adventure to vote on."
            with self._session_lock:
                if session_key not in self._quit_votes:
                    self._quit_votes[session_key] = set()
                self._quit_votes[session_key].add(message.sender)
                vote_count = len(self._quit_votes[session_key])
            if vote_count >= self._vote_threshold:
                self._clear_session(session_key)
                return "🗳️ Vote threshold reached! Adventure ended. Type !adv to start new."
            return f"🗳️ Voted to end adventure ({vote_count}/{self._vote_threshold} votes needed)"

        # Status command
        if content == "!status":
            session = self._get_session(session_key)
            if session:
                theme = session.get("theme", "unknown")
                status = session.get("status", "unknown")
                return f"Status: {status}, Theme: {theme}"
            return "No active adventure. Type !adv to start."

        # Reset command (user-invoked) - silently ignored
        if content == "!reset":
            return None

        # Check for letter choice (A/B/C, case-insensitive)
        if content.upper() in ["A", "B", "C"]:
            choice = content.upper()
            session = self._get_session(session_key)

            if not session or session.get("status") != "active":
                return "No active adventure. Type !adv to start."

            theme = session.get("theme", "fantasy")

            # Update activity timestamp
            self._last_story_activity = time.time()

            # Generate next part of story
            result = self._generate_story(session_key, choice, theme)

            # Check if adventure finished
            if self._get_session(session_key).get("status") == "finished":
                self._clear_session(session_key)

            return result

        # Unknown message - no response
        return None

    def run_http_server(self) -> None:
        """Run the bot as an HTTP server."""
        if self.distributed_mode:
            self.logger.info("Running in distributed mode (HTTP only, no direct radio connection)")
        self.logger.info(f"Starting HTTP server on {self.http_host}:{self.http_port}")
        self.app.run(host=self.http_host, port=self.http_port)


# =============================================================================
# MAIN
# =============================================================================


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCADV Adventure Bot")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument(
        "--distributed-mode",
        action="store_true",
        help="Run as HTTP server only (no direct radio connection) for distributed architecture",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Ollama API URL",
    )
    parser.add_argument("--model", default="llama2", help="Ollama model name")
    parser.add_argument("--http-host", default="0.0.0.0", help="HTTP server host")
    parser.add_argument("--http-port", type=int, default=5000, help="HTTP server port")
    parser.add_argument(
        "--admin-users",
        default=os.environ.get("ADMIN_USERS", ""),
        help="Comma-separated admin node IDs (e.g., !a1b2c3d4,!e5f6g7h8). Also reads ADMIN_USERS env var.",
    )

    args = parser.parse_args()

    raw_admin = args.admin_users or ""
    admin_users = [u.strip() for u in raw_admin.split(",") if u.strip()]

    bot = AdventureBot(
        debug=args.debug,
        ollama_url=args.ollama_url,
        model=args.model,
        http_host=args.http_host,
        http_port=args.http_port,
        distributed_mode=args.distributed_mode,
        admin_users=admin_users,
    )

    bot.run_http_server()


if __name__ == "__main__":
    main()
