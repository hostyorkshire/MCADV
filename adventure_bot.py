#!/usr/bin/env python3
"""
MCADV - MeshCore Adventure Bot
AI-powered Choose Your Own Adventure bot for the MeshCore LoRa network.

Commands (send on the configured channel):
  !adv [theme]   - Start a new adventure (themes: fantasy, scifi, horror)
  !start [theme] - Alias for !adv
  1 / 2 / 3      - Make a choice in your current adventure
  !quit / !end   - End your current adventure
  !help          - Show available commands

LLM backend:
  1. Ollama  - local self-hosted LLM via --ollama-url (can be on your network)
  2. Offline - built-in branching story trees, no internet required

Messages longer than 200 characters are split across multiple LoRa transmissions.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from logging_config import get_adventure_bot_logger, log_startup_info
from meshcore import MeshCore, MeshCoreMessage

# Lazy import for requests - only loaded when LLM backends are used
# This speeds up startup when running in offline mode
_requests = None
_RequestException = None


def _ensure_requests():
    """Lazy import requests module only when needed for LLM calls"""
    global _requests, _RequestException
    if _requests is None:
        try:
            import requests as req
            from requests.exceptions import RequestException as ReqEx
            _requests = req
            _RequestException = ReqEx
        except ImportError:
            print("Warning: requests not found. LLM backends unavailable. Install with: pip install requests")
            # Create a dummy exception class so code doesn't crash
            _RequestException = Exception
    return _requests, _RequestException


# ---------------------------------------------------------------------------
# Message length limit
# The MeshCore binary protocol frame fits up to ~230 bytes of text payload,
# but keeping to 200 leaves comfortable headroom for node-name prefixes and
# multi-hop path overhead.
#
# Note: When messages are transmitted on a channel, MeshCore firmware prepends
# the node_id in the format "node_id: content". For this bot with node_id="MCADV",
# the overhead is 7 characters ("MCADV: "). The _send_reply() method automatically
# accounts for this overhead when splitting long messages.
# ---------------------------------------------------------------------------
MAX_MSG_LEN = 200


# ---------------------------------------------------------------------------
# Session persistence
# ---------------------------------------------------------------------------
SESSION_FILE = Path(__file__).parent / "logs" / "sessions.json"
SESSION_EXPIRY_SECONDS = 7200  # 2 hours of inactivity

# ---------------------------------------------------------------------------
# Periodic announcement
# ---------------------------------------------------------------------------
ANNOUNCE_INTERVAL = 3 * 60 * 60  # 3 hours
ANNOUNCE_MESSAGE = "📖 MCADV: AI story bot! !adv to start. Reply 1/2/3 to choose. !help for info."

# ---------------------------------------------------------------------------
# LLM prompt
# The prompt is deliberately terse so that even small/quantised models
# produce something usable within the 160-char budget.
# ---------------------------------------------------------------------------
STORY_SYSTEM_PROMPT = (
    "You are a Choose Your Own Adventure storyteller for LoRa radio. "
    "STRICT FORMAT - total response under 160 chars: "
    "[scene, max 100 chars] then newline then [1:OptA 2:OptB 3:OptC] "
    "each option max 18 chars. No markdown. "
    "To end a story write 'THE END' instead of options."
)

# ---------------------------------------------------------------------------
# Built-in offline story trees
# Used when no LLM is available. Each node:
#   text    – story text shown to the player
#   choices – list of 0-3 choice labels (empty = terminal / THE END)
#   next    – dict mapping "1"/"2"/"3" to the next node id
#
# All formatted messages (text + choices line) must fit in MAX_MSG_LEN.
# ---------------------------------------------------------------------------

_FANTASY_STORY: Dict = {
    "start": {
        "text": "You wake at a crossroads at dusk. Strange sounds fill the air.",
        "choices": ["Take the road", "Enter forest", "Make camp"],
        "next": {"1": "road", "2": "forest", "3": "camp"},
    },
    "road": {
        "text": "A bridge ahead. A troll demands: 'Pay or fight!'",
        "choices": ["Pay the toll", "Fight him", "Sneak past"],
        "next": {"1": "road_pay", "2": "road_fight", "3": "road_sneak"},
    },
    "road_pay": {
        "text": "The troll reveals a shortcut to a hidden city. THE END",
        "choices": [],
        "next": {},
    },
    "road_fight": {
        "text": "You defeat the troll! Under the bridge: a chest of gold. THE END",
        "choices": [],
        "next": {},
    },
    "road_sneak": {
        "text": "You fall into the river and wash up at a distant shore. THE END",
        "choices": [],
        "next": {},
    },
    "forest": {
        "text": "Ancient trees tower above. A faint blue light blinks deeper in.",
        "choices": ["Follow the light", "Climb a tree", "Turn back"],
        "next": {"1": "forest_light", "2": "forest_climb", "3": "start"},
    },
    "forest_light": {
        "text": "The light leads to a fairy ring. What do you do?",
        "choices": ["Step inside", "Watch only", "Destroy it"],
        "next": {"1": "fairy_in", "2": "fairy_watch", "3": "fairy_destroy"},
    },
    "fairy_in": {
        "text": "You step in and become champion of a magical realm. THE END",
        "choices": [],
        "next": {},
    },
    "fairy_watch": {
        "text": "Fairies dance till dawn then gift you a wishing stone. THE END",
        "choices": [],
        "next": {},
    },
    "fairy_destroy": {
        "text": "Destroying the ring frees a banshee. You flee and survive. THE END",
        "choices": [],
        "next": {},
    },
    "forest_climb": {
        "text": "From the treetop you spy a dragon's nest with glittering eggs.",
        "choices": ["Take an egg", "Note location", "Descend fast"],
        "next": {"1": "dragon_egg", "2": "dragon_note", "3": "dragon_run"},
    },
    "dragon_egg": {
        "text": "You grab an egg. The mother dragon returns and adopts you. THE END",
        "choices": [],
        "next": {},
    },
    "dragon_note": {
        "text": "You sell the nest location to a wizard for a fortune. THE END",
        "choices": [],
        "next": {},
    },
    "dragon_run": {
        "text": "The dragon spots you but drops a gift in thanks. THE END",
        "choices": [],
        "next": {},
    },
    "camp": {
        "text": "By the fire you find a map and a torn journal.",
        "choices": ["Read the map", "Read journal", "Sleep"],
        "next": {"1": "camp_map", "2": "camp_journal", "3": "camp_sleep"},
    },
    "camp_map": {
        "text": "The map marks a dragon lair 2 miles east. You go and claim the hoard. THE END",
        "choices": [],
        "next": {},
    },
    "camp_journal": {
        "text": "The journal reveals you are the chosen one. Your quest begins. THE END",
        "choices": [],
        "next": {},
    },
    "camp_sleep": {
        "text": "A wizard visits your dreams and grants you a magic sword. THE END",
        "choices": [],
        "next": {},
    },
}

_SCIFI_STORY: Dict = {
    "start": {
        "text": "Your colony ship drifts off course. Red alarms flash.",
        "choices": ["Go to bridge", "Check engines", "Wake captain"],
        "next": {"1": "bridge", "2": "engines", "3": "captain"},
    },
    "bridge": {
        "text": "Stars show you're near an uncharted system. A signal blinks.",
        "choices": ["Follow signal", "Plot safe course", "Send SOS"],
        "next": {"1": "signal", "2": "safe_course", "3": "sos"},
    },
    "engines": {
        "text": "A coolant leak hisses. The reactor is at 12%. Time is short.",
        "choices": ["Fix the leak", "Reroute power", "Evacuate now"],
        "next": {"1": "fix_leak", "2": "reroute", "3": "evac_pod"},
    },
    "captain": {
        "text": "The captain's pod is empty. A blood smear leads aft.",
        "choices": ["Follow smear", "Lock bulkheads", "Arm yourself"],
        "next": {"1": "smear", "2": "lockdown", "3": "armed"},
    },
    "signal": {
        "text": "The signal guides you to a derelict with spare fuel. You survive. THE END",
        "choices": [],
        "next": {},
    },
    "safe_course": {
        "text": "You plot a course home. Fuel runs out but a rescue ship finds you. THE END",
        "choices": [],
        "next": {},
    },
    "sos": {
        "text": "A nearby freighter answers. You're towed to safety. THE END",
        "choices": [],
        "next": {},
    },
    "fix_leak": {
        "text": "You seal the leak. Power restored. The ship limps to a station. THE END",
        "choices": [],
        "next": {},
    },
    "reroute": {
        "text": "Clever rerouting buys 10 hours. You make it to an asteroid base. THE END",
        "choices": [],
        "next": {},
    },
    "evac_pod": {
        "text": "You launch in an escape pod and drift for days before rescue. THE END",
        "choices": [],
        "next": {},
    },
    "smear": {
        "text": "You find the captain held by a rogue AI. You free them. THE END",
        "choices": [],
        "next": {},
    },
    "lockdown": {
        "text": "Lockdown traps you but you crawl through vents to escape. THE END",
        "choices": [],
        "next": {},
    },
    "armed": {
        "text": "Armed, you confront a malfunctioning android and shut it down. THE END",
        "choices": [],
        "next": {},
    },
}

_HORROR_STORY: Dict = {
    "start": {
        "text": "You wake alone in an old manor. The front door is locked.",
        "choices": ["Search upstairs", "Find a window", "Check cellar"],
        "next": {"1": "upstairs", "2": "window", "3": "cellar"},
    },
    "upstairs": {
        "text": "A corridor stretches ahead. A door at the end creaks open.",
        "choices": ["Enter the room", "Call out", "Retreat"],
        "next": {"1": "enter_room", "2": "call_out", "3": "start"},
    },
    "window": {
        "text": "Outside: thick fog and silent figures standing still.",
        "choices": ["Smash window", "Watch figures", "Find a key"],
        "next": {"1": "smash", "2": "watch", "3": "find_key"},
    },
    "cellar": {
        "text": "Damp steps descend into darkness. Something breathes below.",
        "choices": ["Descend slowly", "Throw a torch", "Seal the door"],
        "next": {"1": "descend", "2": "torch", "3": "seal"},
    },
    "enter_room": {
        "text": "A ghost shows you a hidden exit. You escape unharmed. THE END",
        "choices": [],
        "next": {},
    },
    "call_out": {
        "text": "Your echoed name panics you into finding the exit. THE END",
        "choices": [],
        "next": {},
    },
    "smash": {
        "text": "You smash through and sprint. The figures don't follow. THE END",
        "choices": [],
        "next": {},
    },
    "watch": {
        "text": "The figures vanish at dawn. You find the door unlocked. THE END",
        "choices": [],
        "next": {},
    },
    "find_key": {
        "text": "A brass key unlocks the front door. You escape into morning. THE END",
        "choices": [],
        "next": {},
    },
    "descend": {
        "text": "A smuggler's passage leads under the wall to freedom. THE END",
        "choices": [],
        "next": {},
    },
    "torch": {
        "text": "The torch reveals only a cat. Relieved, you find an exit. THE END",
        "choices": [],
        "next": {},
    },
    "seal": {
        "text": "Sealing the door reveals a hidden panel with the front door key. THE END",
        "choices": [],
        "next": {},
    },
}

# Map theme names to their story trees
FALLBACK_STORIES: Dict[str, Dict] = {
    "fantasy": _FANTASY_STORY,
    "scifi": _SCIFI_STORY,
    "horror": _HORROR_STORY,
}

VALID_THEMES: List[str] = list(FALLBACK_STORIES.keys())


# ---------------------------------------------------------------------------
# AdventureBot
# ---------------------------------------------------------------------------


class _TerminalMeshStub:
    """Stub mesh object for terminal mode"""
    def __init__(self):
        self.node_id = "MCADV"
        self.send_message = lambda *args, **kwargs: None


class AdventureBot:
    """
    AI-powered Choose Your Own Adventure bot for MeshCore LoRa.

    Uses MeshCore's API for all radio communication.  Story generation is
    attempted via Ollama, then OpenAI, then Groq, before falling back to the
    built-in offline story trees.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baud: int = 115200,
        debug: bool = False,
        allowed_channel: Optional[str] = None,
        announce: bool = False,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2:1b",
        terminal: bool = False,
        distributed_mode: bool = False,
    ):
        self.allowed_channel = allowed_channel
        self.announce = announce
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.terminal = terminal
        self.distributed_mode = distributed_mode

        self._running = False

        # Logging
        self.logger, self.error_logger = get_adventure_bot_logger(debug=debug)

        # Per-user sessions
        self._sessions: Dict = {}
        self._sessions_dirty = False  # Track if sessions need saving
        self._last_session_save = time.time()  # For batched saves
        self._load_sessions()

        # HTTP session for connection pooling (faster LLM calls)
        # Only created when first LLM call is made
        self._http_session = None

        # MeshCore handles all LoRa serial I/O (not used in terminal or distributed mode)
        if not terminal and not distributed_mode:
            self.mesh = MeshCore(
                node_id="MCADV",
                debug=debug,
                serial_port=port,
                baud_rate=baud,
            )
            self.mesh.register_handler("text", self.handle_message)
            # Set channel filtering if channel name is provided
            if self.allowed_channel is not None:
                self.mesh.set_channel_filter(self.allowed_channel)
        elif terminal:
            # Terminal mode needs a stub mesh object for send_message mocking
            self.mesh = _TerminalMeshStub()
        else:
            # Distributed mode has no mesh connection
            self.mesh = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _session_key(self, message: MeshCoreMessage) -> str:
        """Return the session key: the message sender."""
        return message.sender

    def _send_reply(self, text: str, channel_idx: int) -> None:
        """
        Send a reply via MeshCore, splitting into multiple messages if needed.

        Messages longer than the effective payload size are split across multiple
        LoRa transmissions with markers (1/N, 2/N, etc.) to indicate the part number.

        The effective payload size accounts for:
        - MAX_MSG_LEN (200 chars) - the LoRa payload limit
        - Node name prefix overhead (e.g., "MCADV: " = 7 chars)
        - Part indicator suffix (dynamically calculated based on number of parts)
        """
        # In terminal mode, mesh is None, so we need to handle that
        if self.mesh is None:
            # Terminal mode - no mesh, so just print directly (handled by terminal mode)
            return
            
        # Calculate overhead from the node_id prefix added by MeshCore firmware
        # Format is "node_id: content", so overhead is len(node_id) + 2
        node_name_overhead = len(self.mesh.node_id) + 2  # +2 for ": "

        # Available space for our content in a single message
        effective_max_len = MAX_MSG_LEN - node_name_overhead

        # Check if message fits in a single transmission
        if len(text) <= effective_max_len:
            self.mesh.send_message(text, "text", channel_idx=channel_idx)
            return

        # Split message into multiple parts
        # First, estimate the number of parts needed to calculate suffix space
        # Start with worst case assumption of " (999/999)" = 11 chars for very long messages
        suffix_space = 11
        chunk_size = effective_max_len - suffix_space

        # Calculate actual number of chunks needed
        chunks = []
        remaining = text
        while remaining:
            chunks.append(remaining[:chunk_size])
            remaining = remaining[chunk_size:]

        total_parts = len(chunks)

        # If we have fewer parts than expected, we can reclaim some space
        # e.g., if total_parts < 100, we only need " (99/99)" = 8 chars
        if total_parts < 100:
            actual_suffix_space = len(f" ({total_parts}/{total_parts})")
            if actual_suffix_space < suffix_space:
                # Recalculate with the actual suffix space
                chunk_size = effective_max_len - actual_suffix_space
                chunks = []
                remaining = text
                while remaining:
                    chunks.append(remaining[:chunk_size])
                    remaining = remaining[chunk_size:]
                total_parts = len(chunks)

        # Send each chunk with part indicator
        for i, chunk in enumerate(chunks, 1):
            msg = f"{chunk} ({i}/{total_parts})"
            self.mesh.send_message(msg, "text", channel_idx=channel_idx)
            # Small delay between messages to avoid overwhelming the LoRa radio.
            # This is intentionally blocking since messages must be sent sequentially.
            if i < total_parts:
                time.sleep(0.1)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def _load_sessions(self) -> None:
        """Load sessions from disk on startup."""
        try:
            if SESSION_FILE.exists():
                with open(SESSION_FILE) as f:
                    self._sessions = json.load(f)
        except (json.JSONDecodeError, OSError):
            self._sessions = {}

    def _save_sessions(self, force: bool = False) -> None:
        """
        Persist sessions to disk with batching to reduce I/O.

        Sessions are only saved if:
        - force=True, or
        - They're marked dirty AND at least 5 seconds have passed since last save

        This reduces disk writes on Pi's SD card.
        """
        if not force and not self._sessions_dirty:
            return

        # Batch saves: only write if enough time has passed
        now = time.time()
        if not force and (now - self._last_session_save) < 5:
            return

        try:
            SESSION_FILE.parent.mkdir(exist_ok=True)
            with open(SESSION_FILE, "w") as f:
                json.dump(self._sessions, f, indent=2)
            self._sessions_dirty = False
            self._last_session_save = now
        except OSError as e:
            self.error_logger.error(f"Failed to save sessions: {e}")

    def _expire_sessions(self) -> None:
        """Remove sessions that have been inactive for SESSION_EXPIRY_SECONDS."""
        now = time.time()
        expired = [
            key
            for key, data in self._sessions.items()
            if now - data.get("last_active", 0) > SESSION_EXPIRY_SECONDS
        ]
        if expired:
            for key in expired:
                del self._sessions[key]
            self._sessions_dirty = True
            self._save_sessions()  # Save immediately after cleanup

    def _get_session(self, key: str) -> dict:
        """Return the session dict for key, or an empty dict if none exists."""
        return self._sessions.get(key, {})

    def _update_session(self, key: str, data: dict) -> None:
        """Merge data into the session for key and mark for persistence."""
        session = self._sessions.get(key, {})
        session.update(data)
        session["last_active"] = time.time()
        self._sessions[key] = session
        self._sessions_dirty = True
        # Batched save will happen in main loop or on shutdown

    def _clear_session(self, key: str) -> None:
        """
        Remove the session for key and save immediately.

        Force save to ensure quit/end commands take effect right away.
        """
        if key in self._sessions:
            del self._sessions[key]
            self._sessions_dirty = True
            self._save_sessions(force=True)  # Force save when clearing

    # ------------------------------------------------------------------
    # Story formatting
    # ------------------------------------------------------------------

    def _format_story_message(self, text: str, choices: List[str]) -> str:
        """
        Combine story text and labelled choices into a single message.

        Format:  <text>\\n1:Choice A 2:Choice B 3:Choice C

        Terminal nodes (empty choices) return just the text.
        Long messages will be split by _send_reply() when transmitted.
        """
        if not choices:
            return text
        choice_line = " ".join(f"{i + 1}:{c}" for i, c in enumerate(choices))
        return f"{text}\n{choice_line}"
    # ------------------------------------------------------------------
    # LLM backends
    # ------------------------------------------------------------------

    def _get_http_session(self):
        """
        Get or create HTTP session for connection pooling.

        Reusing connections improves performance and reduces latency
        for repeated LLM API calls. Lazy creation ensures no overhead
        when running in offline mode.
        """
        if self._http_session is None:
            requests, _ = _ensure_requests()
            if requests is not None:
                self._http_session = requests.Session()
        return self._http_session

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Call a local or remote Ollama server.

        Configure via --ollama-url (e.g. http://192.168.1.50:11434 for a
        server on your LAN) and --model (e.g. llama3.2:1b, tinyllama).
        Returns the generated text or None on any failure.
        """
        requests, RequestException = _ensure_requests()
        if requests is None:
            return None
        session = self._get_http_session()
        if session is None:
            return None
        try:
            resp = session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{STORY_SYSTEM_PROMPT}\n\n{prompt}",
                    "stream": False,
                    "options": {"num_predict": 80, "temperature": 0.8},
                },
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json().get("response", "").strip() or None
        except (RequestException, KeyError, ValueError) as e:
            self.logger.debug(f"Ollama unavailable: {e}")
            return None

    # ------------------------------------------------------------------
    # Offline fallback story tree
    # ------------------------------------------------------------------

    def _get_fallback_story(self, key: str, choice: Optional[str], theme: str) -> str:
        """
        Advance the built-in story tree and return the formatted message.

        Updates the session's current node.  Marks the session finished when
        the player reaches a terminal node (no choices).
        """
        tree = FALLBACK_STORIES.get(theme, _FANTASY_STORY)
        session = self._get_session(key)
        current_node_id = session.get("node", "start")

        if choice is None:
            node_id = "start"
        else:
            current_node = tree.get(current_node_id, tree["start"])
            node_id = current_node.get("next", {}).get(choice, "start")

        node = tree.get(node_id, tree["start"])
        is_terminal = not node["choices"]
        self._update_session(key, {"node": node_id, "status": "finished" if is_terminal else "active"})
        return self._format_story_message(node["text"], node["choices"])

    # ------------------------------------------------------------------
    # Story generation (LLM with fallback)
    # ------------------------------------------------------------------

    def _generate_story(self, key: str, choice: Optional[str], theme: str) -> str:
        """
        Generate the next story segment.

        Tries Ollama first, then falls back to the built-in offline story tree.
        choice=None starts a new adventure; "1"/"2"/"3" continues an existing one.
        """
        session = self._get_session(key)
        history: List[str] = session.get("history", [])

        if choice is None:
            prompt = f"Start a {theme} CYOA adventure."
            new_history: List[str] = []
        else:
            # Provide context from the last three story beats
            history_str = " → ".join(history[-3:]) if history else "the beginning"
            # Retrieve choice label from fallback tree for richer LLM context
            tree = FALLBACK_STORIES.get(theme, _FANTASY_STORY)
            current_node = session.get("node", "start")
            choices_list = tree.get(current_node, {}).get("choices", [])
            choice_int = int(choice) - 1
            choice_text = choices_list[choice_int] if 0 <= choice_int < len(choices_list) else choice
            prompt = f"Story so far: {history_str}. Player chose: {choice_text}. Continue."
            new_history = history + [f"chose {choice}"]

        story = self._call_ollama(prompt)

        if story:
            is_terminal = "THE END" in story.upper()
            self._update_session(key, {
                "history": new_history[-5:],
                "theme": theme,
                "status": "finished" if is_terminal else "active",
            })
            return story

        # Ollama unavailable – use built-in story tree
        self.logger.info(f"Ollama unavailable, using offline story tree for session {key!r}")
        return self._get_fallback_story(key, choice, theme)

    # ------------------------------------------------------------------
    # Message handler (called by MeshCore for every incoming text message)
    # ------------------------------------------------------------------

    def handle_message(self, message: MeshCoreMessage) -> Optional[str]:
        """
        Dispatch an incoming MeshCore channel message to the right command.

        This is the single entry point registered with MeshCore.  It is also
        called directly by unit tests (no radio hardware required).

        In distributed mode, returns the response text instead of sending via mesh.
        """
        content = message.content.strip()
        channel_idx = message.channel_idx if message.channel_idx is not None else 0
        content_lower = content.lower()

        # Channel filtering is handled by meshcore.py when allowed_channel is set
        # via set_channel_filter() during initialization

        self._expire_sessions()
        key = self._session_key(message)

        response = None

        # ---- !help -------------------------------------------------------
        if content_lower in ("!help", "help"):
            response = "MCADV: !adv[theme] start, 1/2/3 choose, !quit end. Themes: fantasy scifi horror"

        # ---- !adv / !start [theme] ---------------------------------------
        elif content_lower.startswith(("!adv", "!start")):
            parts = content.split(maxsplit=1)
            raw_theme = parts[1].strip().lower() if len(parts) > 1 else "fantasy"
            theme = raw_theme if raw_theme in VALID_THEMES else "fantasy"
            self.logger.info(f"New adventure for {key!r}: theme={theme!r}")
            self._update_session(key, {"status": "active", "node": "start", "history": [], "theme": theme})
            response = self._generate_story(key, choice=None, theme=theme)

        # ---- !quit / !end ------------------------------------------------
        elif content_lower in ("!quit", "!end", "!stop"):
            self._clear_session(key)
            response = "Adventure ended. Type !adv to start a new one."

        # ---- choice: 1, 2, or 3 ------------------------------------------
        elif content in ("1", "2", "3"):
            session = self._get_session(key)
            if not session or session.get("status") != "active":
                response = "No active adventure. Type !adv to start."
            else:
                theme = session.get("theme", "fantasy")
                self.logger.info(f"Session {key!r} chose option {content}")
                response = self._generate_story(key, choice=content, theme=theme)
                if self._get_session(key).get("status") == "finished":
                    self._clear_session(key)

        # ---- !status / !state --------------------------------------------
        elif content_lower in ("!status", "!state"):
            session = self._get_session(key)
            if session and session.get("status") == "active":
                theme = session.get("theme", "fantasy")
                response = f"Adventure active ({theme}). Enter 1, 2 or 3."
            else:
                response = "No active adventure. Type !adv to start."

        # Send response
        if response:
            if self.distributed_mode:
                # In distributed mode, return response instead of sending
                return response
            else:
                # In direct mode, send via mesh
                self._send_reply(response, channel_idx)

        return response if self.distributed_mode else None

    # ------------------------------------------------------------------
    # Main run loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Connect to MeshCore and run the bot until Ctrl-C."""
        if self.distributed_mode:
            self._run_http_server()
        else:
            self._run_direct_mode()

    def _run_direct_mode(self) -> None:
        """Run in direct mode with MeshCore radio connection."""
        log_startup_info(self.logger, "MCADV Adventure Bot", "1.0.0")

        self.mesh.start()
        self._running = True

        if self.allowed_channel is not None:
            msg = f"MCADV running on channel '{self.allowed_channel}'."
        else:
            msg = "MCADV running on all channels. Type !adv to start."
        print(msg)
        self.logger.info(msg)
        print("Press Ctrl+C to stop.\n", flush=True)

        last_announce = time.time()
        if self.announce:
            if self.allowed_channel is not None:
                self.mesh.send_message(ANNOUNCE_MESSAGE, "text", channel=self.allowed_channel)
            else:
                self.mesh.send_message(ANNOUNCE_MESSAGE, "text", channel_idx=0)

        try:
            while self._running:
                time.sleep(1)
                # Check if sessions need saving (batched internally with 5s minimum interval)
                self._save_sessions()
                if self.announce and (time.time() - last_announce >= ANNOUNCE_INTERVAL):
                    if self.allowed_channel is not None:
                        self.mesh.send_message(ANNOUNCE_MESSAGE, "text", channel=self.allowed_channel)
                    else:
                        self.mesh.send_message(ANNOUNCE_MESSAGE, "text", channel_idx=0)
                    last_announce = time.time()
        except KeyboardInterrupt:
            print("\nStopping...")
            self.logger.info("Stopping...")
        finally:
            self._running = False
            self._save_sessions(force=True)  # Final save on shutdown
            self.mesh.stop()
            print("MCADV stopped.")
            self.logger.info("MCADV stopped.")

    def _run_http_server(self) -> None:
        """Run in distributed mode with HTTP server."""
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            print("Error: Flask not found. Install with: pip install flask")
            sys.exit(1)

        app = Flask(__name__)

        @app.route('/api/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({"status": "ok", "mode": "distributed"})

        @app.route('/api/message', methods=['POST'])
        def handle_api_message():
            """Handle incoming message from radio gateway."""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                # Create a MeshCoreMessage from the JSON data
                message = MeshCoreMessage(
                    sender=data.get("sender", "unknown"),
                    content=data.get("content", ""),
                    channel_idx=data.get("channel_idx", 0),
                    timestamp=data.get("timestamp"),
                )

                # Process the message and get response
                response_text = self.handle_message(message)

                if response_text:
                    return jsonify({"response": response_text})
                else:
                    return jsonify({"response": ""})

            except Exception as e:
                self.error_logger.exception("Error handling API message")
                return jsonify({"error": str(e)}), 500

        log_startup_info(self.logger, "MCADV Adventure Bot (Distributed Mode)", "1.0.0")
        print(f"HTTP server starting on {self.http_host}:{self.http_port}")
        self.logger.info(f"HTTP server starting on {self.http_host}:{self.http_port}")
        print("Press Ctrl+C to stop.\n", flush=True)

        # Start background thread for session saves
        import threading

        def session_saver():
            while self._running:
                time.sleep(5)
                self._save_sessions()

        self._running = True
        saver_thread = threading.Thread(target=session_saver, daemon=True)
        saver_thread.start()

        try:
            app.run(host=self.http_host, port=self.http_port, threaded=True)
        except KeyboardInterrupt:
            print("\nStopping...")
            self.logger.info("Stopping...")
        finally:
            self._running = False
            self._save_sessions(force=True)
            print("MCADV stopped.")
            self.logger.info("MCADV stopped.")

    def run_terminal(self) -> None:
        """
        Run the bot in terminal mode for testing/playing without LoRa hardware.

        This mode allows you to interact with the adventure bot directly from the
        command line. All commands work the same as on the radio network:
        - !adv [theme] - Start a new adventure
        - 1/2/3 - Make choices
        - !quit - End your adventure
        - !help - Show help
        - !status - Check your adventure status
        """
        log_startup_info(self.logger, "MCADV Adventure Bot (Terminal Mode)", "1.0.0")

        print("\n" + "=" * 70)
        print("  MCADV - Choose Your Own Adventure (Terminal Mode)")
        print("=" * 70)
        print("\nWelcome! You can test and play adventures from the terminal.")
        print("\nAvailable commands:")
        print("  !adv [theme]  - Start a new adventure (themes: fantasy, scifi, horror)")
        print("  !start [theme]- Alias for !adv")
        print("  1 / 2 / 3     - Make a choice")
        print("  !status       - Show your current adventure state")
        print("  !quit         - End your adventure")
        print("  !help         - Show help")
        print("  exit          - Exit terminal mode")
        print("\nType '!adv' to begin your adventure!")
        print("=" * 70 + "\n")

        self._running = True

        # Create a fake message for terminal mode - sender is "Terminal"
        terminal_channel = 0

        # Store terminal replies to display
        terminal_replies = []

        def terminal_send_message(text: str, msg_type: str = "text", channel_idx: int = 0):
            """Capture outgoing messages and display them in terminal"""
            terminal_replies.append(text)

        # Replace mesh.send_message with our terminal handler
        original_send = self.mesh.send_message
        self.mesh.send_message = terminal_send_message

        try:
            while self._running:
                # Display any pending replies from the bot
                while terminal_replies:
                    reply = terminal_replies.pop(0)
                    print(f"\n📖 {reply}\n")

                # Get user input
                try:
                    user_input = input("You> ").strip()
                except EOFError:
                    # Handle Ctrl+D
                    break

                if not user_input:
                    continue

                # Check for exit command
                if user_input.lower() == "exit":
                    break

                # Create a fake MeshCoreMessage from terminal input
                msg = MeshCoreMessage(
                    sender="Terminal",
                    content=user_input,
                    channel_idx=terminal_channel,
                )

                # Process the message through the normal handler
                self.handle_message(msg)

        except KeyboardInterrupt:
            print("\n\nExiting terminal mode...")
        finally:
            self._running = False
            self._save_sessions(force=True)
            self.mesh.send_message = original_send  # Restore original
            print("\nGoodbye! Thanks for playing MCADV.\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCADV – MeshCore Choose Your Own Adventure Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
LLM backend (tries in order until one succeeds):
  1. Ollama  – local/LAN server via --ollama-url  (e.g. http://192.168.1.x:11434)
  2. Offline – built-in story trees, no internet needed

Story themes:  fantasy (default)  scifi  horror

Examples:
  # Terminal mode (no radio hardware needed):
  python adventure_bot.py --terminal

  # Radio mode (requires LoRa hardware):
  python adventure_bot.py -p /dev/ttyUSB0 --channel adventure
  python adventure_bot.py -p /dev/ttyUSB0 --ollama-url http://192.168.1.50:11434
  python adventure_bot.py -p /dev/ttyUSB0 --announce
""",
    )
    parser.add_argument("-p", "--port", help="Serial port (e.g. /dev/ttyUSB0). Auto-detects if omitted.")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug output")
    parser.add_argument("-a", "--announce", action="store_true", help="Send periodic announcements every 3 hours")
    parser.add_argument(
        "-t",
        "--terminal",
        action="store_true",
        help="Run in terminal mode (no radio hardware needed, for testing/playing)",
    )
    parser.add_argument(
        "-c",
        "--channel",
        type=str,
        help="Only respond to messages from this channel name (e.g. 'adventure'). Channel names are consistent across devices.",
    )
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        help="Ollama API base URL (default: http://localhost:11434 or $OLLAMA_URL)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("OLLAMA_MODEL", "llama3.2:1b"),
        help="Ollama model name (default: llama3.2:1b or $OLLAMA_MODEL)",
    )

    args = parser.parse_args()

    bot = AdventureBot(
        port=args.port,
        baud=args.baud,
        debug=args.debug,
        allowed_channel=args.channel,
        announce=args.announce,
        ollama_url=args.ollama_url,
        model=args.model,
        terminal=args.terminal,
    )

    # Run in terminal mode or radio mode
    if args.terminal:
        bot.run_terminal()
    else:
        bot.run()


if __name__ == "__main__":
    main()
