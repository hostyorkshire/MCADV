#!/usr/bin/env python3
"""
MeshCore - Core library for mesh radio network communication
This module provides the core functionality for communicating via MeshCore mesh radio network.
"""

import html
import json
import threading
import time
from typing import Any, Callable, Dict, Optional

from logging_config import get_meshcore_logger

# MeshCore companion radio binary protocol constants (USB/serial framing)
# Reference: https://github.com/meshcore-dev/MeshCore/wiki/Companion-Radio-Protocol
_FRAME_OUT = 0x3E  # '>' radio→app outbound frame start byte
_FRAME_IN = 0x3C  # '<' app→radio inbound frame start byte
_CMD_APP_START = 1  # Initialize companion radio session
_CMD_GET_DEVICE_TIME = 5  # Request current device time (RTC)
_CMD_SYNC_NEXT_MSG = 10  # Fetch next queued message
_CMD_SEND_CHAN_MSG = 3  # Send a channel (flood) text message
_RESP_CURR_TIME = 9  # Response: current device time (4-byte UNIX timestamp)
_PUSH_SEND_CONFIRMED = 0x82  # Push: outgoing message ACK confirmed by mesh (ack_code 4B + round_trip 4B)
_PUSH_MSG_WAITING = 0x83  # Push: a new message has been queued
_PUSH_CHAN_MSG = 0x88  # Push: inline channel message delivery (0x80 | RESP_CHANNEL_MSG)
_RESP_CONTACT_MSG = 7  # Response: direct (contact) message received
_RESP_CHANNEL_MSG = 8  # Response: channel message received
_RESP_NO_MORE_MSGS = 10  # Response: message queue is empty
_RESP_CONTACT_MSG_V3 = 16  # V3 variant of contact message (includes SNR)
_RESP_CHANNEL_MSG_V3 = 17  # V3 variant of channel message (includes SNR)
_MAX_FRAME_SIZE = 300  # Maximum valid frame payload size in bytes

# Channel message format constants
_OLD_FORMAT_HEADER_SIZE = 8  # code(1) + channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4)
# code(1) + SNR(1) + reserved(2) + channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4)
_V3_FORMAT_HEADER_SIZE = 11
_MIN_REALISTIC_SNR = 20  # Minimum typical SNR value for radio signals (dB)
_MAX_REALISTIC_SNR = 60  # Maximum typical SNR value for radio signals (dB)
_MAX_VALID_CHANNEL_IDX = 7  # Maximum valid channel index (0-7)

try:
    import serial
    from serial import SerialException
    from serial.tools import list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    # Provide a fallback so SerialException can be caught safely without pyserial installed

    class SerialException(Exception):  # type: ignore[no-redef]
        pass


class MeshCoreMessage:
    """Represents a message in the MeshCore network"""

    def __init__(
        self,
        sender: str,
        content: str,
        message_type: str = "text",
        timestamp: Optional[float] = None,
        channel: Optional[str] = None,
        channel_idx: Optional[int] = None,
    ):
        self.sender = sender
        self.content = content
        self.message_type = message_type
        self.timestamp = timestamp or time.time()
        self.channel = channel
        self.channel_idx = channel_idx  # Raw channel index from LoRa (0-7)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        data = {"sender": self.sender, "content": self.content, "type": self.message_type, "timestamp": self.timestamp}
        if self.channel:
            data["channel"] = self.channel
        if self.channel_idx is not None:
            data["channel_idx"] = self.channel_idx
        return data

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MeshCoreMessage":
        """Create message from dictionary"""
        return cls(
            sender=data.get("sender", "unknown"),
            content=data.get("content", ""),
            message_type=data.get("type", "text"),
            timestamp=data.get("timestamp"),
            channel=data.get("channel"),
            channel_idx=data.get("channel_idx"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MeshCoreMessage":
        """Create message from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


# Standard serial baud rates accepted for preflight validation
VALID_BAUD_RATES = {110, 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 38400, 57600, 115200, 128000, 256000}


def normalize_channel_name(channel: Optional[str], warn: bool = True) -> Optional[str]:
    """
    Normalize a channel name by removing hash prefix if present.

    Channel names in Python should NOT include the hash (#) prefix.
    The hash is only used in the MeshCore app UI for display.

    Args:
        channel: Channel name, potentially with hash prefix
        warn: If True, prints a warning when hash is detected (default: True)

    Returns:
        Channel name without hash prefix, or None if channel is None

    Examples:
        normalize_channel_name("wxtest") → "wxtest"
        normalize_channel_name("#wxtest") → "wxtest" (with warning)
        normalize_channel_name(None) → None
    """
    if channel is None:
        return None

    if channel.startswith("#"):
        normalized = channel[1:]  # Remove the hash
        if warn:
            print(f"⚠ Warning: Channel name '{channel}' includes hash (#) prefix.")
            print("  The hash is only used in MeshCore app UI, not in Python code.")
            print(f"  Using normalized name: '{normalized}'")
            print(f"  To remove this warning, use '{normalized}' directly.")
        return normalized

    return channel


def find_serial_ports(debug: bool = False) -> list:
    """
    Find available USB serial ports for LoRa modules.

    Returns a list of available serial port device paths, prioritizing
    common LoRa/FTDI USB-to-serial adapters.

    Args:
        debug: Enable debug output

    Returns:
        List of available serial port paths (e.g., ['/dev/ttyUSB0', '/dev/ttyACM0'])
    """
    if not SERIAL_AVAILABLE:
        if debug:
            print("pyserial is not installed. Cannot detect serial ports.")
        return []

    try:
        ports = list_ports.comports()
        available = []

        for port in ports:
            # Common USB serial devices used for LoRa modules:
            # - ttyUSB* (FTDI, CP210x, CH340 USB-to-serial adapters)
            # - ttyACM* (Arduino, some ESP32 boards)
            # - ttyAMA* (Raspberry Pi UART)
            device = port.device
            if any(pattern in device for pattern in ["ttyUSB", "ttyACM", "ttyAMA"]):
                available.append(device)
                if debug:
                    desc = port.description or "Unknown"
                    print(f"Found serial port: {device} ({desc})")

        # Sort to provide consistent ordering (ttyUSB0 before ttyUSB1, etc.)
        available.sort()
        return available

    except Exception as e:
        if debug:
            print(f"Error detecting serial ports: {e}")
        return []


class MeshCore:
    """Main MeshCore communication handler"""

    def __init__(self, node_id: str, debug: bool = False, serial_port: Optional[str] = None, baud_rate: int = 9600):
        """
        Initialize MeshCore

        Args:
            node_id: Unique identifier for this node
            debug: Enable debug output
            serial_port: Serial port for LoRa module (e.g., /dev/ttyUSB0). When None,
                         the node operates in simulation mode (no actual radio transmission).
            baud_rate: Baud rate for LoRa serial connection (default: 9600)
        """
        self.node_id = node_id
        self.debug = debug
        self.message_handlers = {}
        self.running = False
        self.channel_filter = None  # None means listen to all channels

        # Set up logging
        self.logger, self.error_logger = get_meshcore_logger(debug=debug)

        # Channel name to channel_idx mapping for LoRa transmission
        # Allows different named channels to use different channel indices
        self._channel_map = {}  # channel_name -> channel_idx
        self._reverse_channel_map = {}  # channel_idx -> channel_name
        self._next_channel_idx = 1  # 0 is reserved for default/no-channel

        # Track active channels with timestamps for expiration (72 hours)
        # Format: {channel_idx: last_used_timestamp}
        self._active_channels = {}  # Dict mapping channel_idx to last used timestamp
        self._channel_expiry_hours = 72  # Channels expire after 72 hours of inactivity

        # LoRa serial connection
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self._serial = None
        self._listener_thread = None

    # Maximum length for logged content to prevent log spam
    _MAX_LOG_LENGTH = 200

    def _sanitize_for_log(self, text: str) -> str:
        """
        Sanitize text for safe logging by removing control characters and
        limiting length. This prevents terminal corruption from garbled/encrypted data.
        """
        if not text:
            return text

        # Remove control characters except newline, tab, carriage return
        sanitized = "".join(char if (ord(char) >= 32 or char in "\n\t\r") else f"\\x{ord(char):02x}" for char in text)

        # Limit length to prevent log spam
        if len(sanitized) > self._MAX_LOG_LENGTH:
            sanitized = sanitized[: self._MAX_LOG_LENGTH] + f"... ({len(sanitized) - self._MAX_LOG_LENGTH} more chars)"

        return sanitized

    def log(self, message: str):
        """Log messages"""
        self.logger.info(message)

    def set_channel_filter(self, channels):
        """
        Configure channel filtering for the bot.

        This method sets up channel name to channel_idx mappings and enables
        filtering of incoming messages. When channel_filter is set:
        - The bot ONLY accepts messages from the specified channel(s)
        - Messages from other channels are ignored
        - The bot replies on the same channel_idx where each message came from

        When channel_filter is None (default):
        - The bot accepts messages from ALL channels
        - The bot replies on the same channel_idx where each message came from

        This is used for:
        1. Filtering which channels the bot responds to
        2. Bot-initiated broadcasts (e.g., scheduled announcements, alerts)

        Args:
            channels: Channel name (str), list of channel names, or None
        """
        # Normalize input to a list or None
        if channels is None:
            self.channel_filter = None
        elif isinstance(channels, str):
            self.channel_filter = [channels]
        elif isinstance(channels, list):
            self.channel_filter = channels if channels else None
        else:
            raise TypeError(f"channels must be str, list, or None, not {type(channels).__name__}")

        # Pre-populate channel mappings for broadcast channels
        if self.channel_filter:
            for channel in self.channel_filter:
                if channel not in self._channel_map:
                    self._get_channel_idx(channel)

            channel_str = ", ".join(f"'{ch}'" for ch in self.channel_filter)
            self.log(f"Channel filter enabled: {channel_str} (only accepts messages from these channels)")
        else:
            self.log("Channel filter disabled: accepts messages from all channels")

    def _get_channel_idx(self, channel: Optional[str]) -> int:
        """
        Get or assign a channel_idx for the given channel name.

        Args:
            channel: Channel name, or None for the default channel

        Returns:
            Channel index (0-7) to use for LoRa transmission

        Raises:
            ValueError: If more than 7 named channels are used
        """
        if channel is None:
            return 0  # Default channel (typically uses well-known PSK)

        # Return existing mapping or create a new one
        if channel not in self._channel_map:
            if self._next_channel_idx > 7:
                raise ValueError(
                    f"Maximum of 7 named channels exceeded. Cannot add channel '{channel}'. "
                    f"Existing channels: {list(self._channel_map.keys())}"
                )
            self._channel_map[channel] = self._next_channel_idx
            self._reverse_channel_map[self._next_channel_idx] = channel
            self.log(f"Mapped channel '{channel}' to channel_idx {self._next_channel_idx}")
            self._next_channel_idx += 1

        return self._channel_map[channel]

    def _get_channel_name(self, channel_idx: int) -> Optional[str]:
        """
        Get the Python channel name for a given channel_idx.

        Args:
            channel_idx: Channel index (0-7) from LoRa transmission

        Returns:
            Channel name if mapped, None if channel_idx is 0 or unmapped
        """
        if channel_idx == 0:
            return None  # Default channel (no specific channel name)

        # O(1) lookup using reverse mapping dictionary
        return self._reverse_channel_map.get(channel_idx)

    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a handler for a specific message type

        Args:
            message_type: Type of message to handle
            handler: Callback function to handle the message
        """
        self.message_handlers[message_type] = handler
        self.log(f"Registered handler for message type: {message_type}")

    def send_message(
        self, content: str, message_type: str = "text", channel: Optional[str] = None, channel_idx: Optional[int] = None
    ) -> MeshCoreMessage:
        """
        Send a message via MeshCore network

        Args:
            content: Message content
            message_type: Type of message
            channel: Optional channel name to broadcast to
            channel_idx: Optional raw channel index (0-7) to use directly.
                        When provided, takes precedence over channel name mapping.
                        This allows direct replies on the exact channel_idx received from.

        Returns:
            MeshCoreMessage object
        """
        message = MeshCoreMessage(
            sender=self.node_id, content=content, message_type=message_type, channel=channel, channel_idx=channel_idx
        )

        # Determine which channel_idx to use:
        # 1. If channel_idx is explicitly provided, use it directly (for replies)
        # 2. Otherwise, map the channel name to a channel_idx
        if channel_idx is not None:
            actual_channel_idx = channel_idx
        else:
            actual_channel_idx = self._get_channel_idx(channel)

        # Track active channel when sending messages (works in both real and simulation mode)
        self._active_channels[actual_channel_idx] = time.time()
        self.save_active_channels()

        channel_info = f" on channel '{channel}'" if channel else ""
        if channel_idx is not None:
            channel_info += f" (idx={channel_idx})"
        self.log(f"Sending message{channel_info}: {message.to_json()}")

        if self._serial and self._serial.is_open:
            # Transmit over LoRa using the MeshCore companion radio binary protocol.
            # CMD_SEND_CHANNEL_TXT_MSG: code(1) + txt_type(1) + channel_idx(1)
            #                           + timestamp uint32_LE(4) + text
            try:
                ts_bytes = int(time.time()).to_bytes(4, "little")
                cmd_data = bytes([_CMD_SEND_CHAN_MSG, 0, actual_channel_idx]) + ts_bytes + content.encode("utf-8")
                frame = bytes([_FRAME_IN]) + len(cmd_data).to_bytes(2, "little") + cmd_data
                self._serial.write(frame)
                self.log(f"LoRa TX channel msg (idx={actual_channel_idx}): {content}")
                # After sending, sync to allow the companion radio to process and respond
                self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))
            except SerialException as e:
                msg = f"LoRa TX error: {e}"
                self.log(msg)
                self.error_logger.error(msg)
        else:
            # Simulation mode - no radio hardware attached
            self.log("Simulation mode: message not transmitted over radio")

        return message

    def receive_message(self, message: MeshCoreMessage):
        """
        Receive and process a message

        Args:
            message: MeshCoreMessage object to process
        """
        channel_info = f" on channel '{message.channel}'" if message.channel else ""
        if message.channel_idx is not None:
            channel_info += f" (channel_idx={message.channel_idx})"
        self.log(f"Received message from {message.sender}{channel_info}: {message.content}")

        # Apply channel filtering if configured
        if self.channel_filter is not None:
            # Only filter when the message carries an explicit channel name.
            # Binary-protocol frames only carry a numeric channel_idx; the bot's
            # internal name→idx mapping is independent of the physical radio's
            # channel-slot assignment, so idx-based filtering is unreliable and
            # would silently drop messages from any channel whose physical slot
            # doesn't happen to match the bot-internal index (e.g. #weather).
            # For those messages (message.channel is None) we accept unconditionally
            # and rely on the radio hardware to enforce channel membership.
            if message.channel is not None and message.channel not in self.channel_filter:
                self.log(f"Ignoring message: channel '{message.channel}' " f"not in filter {self.channel_filter}")
                return

        # Check if we have a handler for this message type
        if message.message_type in self.message_handlers:
            handler = self.message_handlers[message.message_type]
            handler(message)
        else:
            self.log(f"No handler for message type: {message.message_type}")

    def _connect_serial(self):
        """Open the serial port for the LoRa module"""
        if not SERIAL_AVAILABLE:
            self.log("pyserial is not installed. Install with: pip install pyserial")
            return
        # Preflight: reject baud rates that are not in the known-valid set
        if self.baud_rate not in VALID_BAUD_RATES:
            self.log(f"Invalid baud rate {self.baud_rate}. " f"Valid rates: {sorted(VALID_BAUD_RATES)}")
            return

        # Check if specified port exists, and auto-detect if not
        port_to_use = self.serial_port
        try:
            # Try the specified port first
            self._serial = serial.Serial(
                port_to_use,
                self.baud_rate,
                timeout=1,
                rtscts=False,
                dsrdtr=False,
            )
            # Deassert RTS and DTR to prevent unintended resets on ESP32/Arduino
            # LoRa devices that use these lines as a reset trigger.
            self._serial.rts = False
            self._serial.dtr = False
            self.log(f"LoRa connected on {port_to_use} at {self.baud_rate} baud")
            # Initialise MeshCore companion radio protocol session.
            # CMD_APP_START frame payload layout (protocol reference §App Commands):
            #   byte 0:   command code = 0x01 (CMD_APP_START)
            #   byte 1:   app_ver = 0x03  (request V3 message format with SNR field)
            #   bytes 2-7: reserved = 6 ASCII spaces (as used by official meshcore-py)
            #   bytes 8+: app_name = "MCADV" (identifies this bot to the companion radio)
            self._send_command(b"\x01\x03      MCADV")
            # Allow companion radio time to process CMD_APP_START initialization.
            # After a radio reboot, the companion radio needs a brief moment to
            # initialize its session before it can handle subsequent commands.
            time.sleep(0.1)
        except SerialException as e:
            msg = f"Failed to open serial port {port_to_use}: {e}"
            self.log(msg)
            self.error_logger.error(msg)

            # Try to auto-detect an available port
            self.log("Attempting to auto-detect available serial ports...")
            available_ports = find_serial_ports(debug=self.debug)

            if available_ports:
                self.log(f"Found {len(available_ports)} available port(s): {', '.join(available_ports)}")
                # Try each available port
                for candidate_port in available_ports:
                    if candidate_port == port_to_use:
                        # Already tried this one
                        continue
                    try:
                        self.log(f"Trying to connect to {candidate_port}...")
                        self._serial = serial.Serial(
                            candidate_port,
                            self.baud_rate,
                            timeout=1,
                            rtscts=False,
                            dsrdtr=False,
                        )
                        self._serial.rts = False
                        self._serial.dtr = False
                        self.log(f"LoRa connected on {candidate_port} at {self.baud_rate} baud (auto-detected)")
                        self.serial_port = candidate_port  # Update to the working port
                        self._send_command(b"\x01\x03      MCADV")
                        time.sleep(0.1)
                        return  # Successfully connected
                    except SerialException as e2:
                        msg = f"Failed to connect to {candidate_port}: {e2}"
                        self.log(msg)
                        self.error_logger.error(msg)
                        continue

                # If we get here, none of the ports worked
                self.log("Failed to connect to any available serial ports")
                self._serial = None
            else:
                self.log("No serial ports found. Check USB connections.")
                self._serial = None

    def _start_listener(self):
        """Start background thread to listen for incoming LoRa messages"""
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True, name="lora-listener")
        self._listener_thread.start()
        self.log("LoRa listener thread started")
        # Now that the listener thread is running, drain any messages that
        # queued while we were offline. This must happen AFTER the listener
        # thread starts to ensure responses are properly received.
        self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

    def _listen_loop(self):
        """
        Background loop: read data from the LoRa serial port and dispatch messages.

        Handles both the MeshCore companion radio binary framing protocol
        (frames starting with 0x3E '>') and legacy newline-delimited JSON for
        simulation / inter-Python-node communication.
        """
        while self.running and self._serial and self._serial.is_open:
            try:
                # Try to peek at first byte for real serial connections (binary protocol detection)
                # For mocks/tests, fall back to readline() for compatibility
                raw = None
                first_byte = None

                try:
                    # Check if data is available (real serial only)
                    if self._serial.in_waiting > 0:
                        # Read first byte to determine frame type
                        first_byte = self._serial.read(1)
                        if not first_byte:
                            continue

                        # ----------------------------------------------------------------
                        # MeshCore companion radio binary protocol
                        # Frame format (outbound, radio→app):
                        #   0x3E ('>')  - frame start
                        #   uint16 LE   - payload length
                        #   bytes       - payload (first byte = response/push code)
                        # ----------------------------------------------------------------
                        if first_byte[0] == _FRAME_OUT:
                            # Read the length header (2 bytes, little-endian)
                            length_bytes = self._serial.read(2)
                            if len(length_bytes) < 2:
                                self.log("Binary frame incomplete: missing length header")
                                continue

                            length = int.from_bytes(length_bytes, "little")
                            if length == 0 or length > _MAX_FRAME_SIZE:
                                self.log(f"Binary frame length {length} out of range, skipping")
                                continue

                            # Read the exact payload bytes
                            payload = self._serial.read(length)
                            if len(payload) < length:
                                self.log(f"Binary frame incomplete: expected {length} bytes, got {len(payload)}")
                                continue

                            # Parse the complete binary frame
                            self._parse_binary_frame(payload)
                            continue

                        # For non-binary frames, read rest of line
                        rest_of_line = self._serial.readline()
                        raw = first_byte + rest_of_line
                except (TypeError, AttributeError):
                    # Mock/test object - use readline() directly
                    pass

                # Use readline() if we haven't read data yet (mock/test or no data available)
                if raw is None:
                    raw = self._serial.readline()
                    if not raw:
                        continue

                    # Check if this is a binary frame that came via readline() (from tests/mocks)
                    if raw and len(raw) > 0 and raw[0] == _FRAME_OUT:
                        if len(raw) < 3:
                            self.log("Binary frame too short to contain a length header")
                            continue
                        length = int.from_bytes(raw[1:3], "little")
                        if length == 0 or length > _MAX_FRAME_SIZE:
                            self.log(f"Binary frame length {length} out of range, skipping")
                            continue
                        payload = raw[3 : 3 + length]
                        if not payload:
                            continue
                        self._parse_binary_frame(payload)
                        continue

                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                # Remove embedded control characters (e.g. \r, \x00) that can
                # corrupt terminal output when raw LoRa radio frames are received.
                line = "".join(c for c in line if c.isprintable())
                if not line:
                    continue
                # Decode HTML entities (e.g. &gt; -> >, &amp; -> &) that may be present
                # in data from certain LoRa systems or transport layers
                line = html.unescape(line)
                # Only attempt JSON parsing for lines that look like JSON objects.
                # Raw LoRa frames from non-MeshCore devices are silently skipped.
                # Additional validation: must start with { AND end with }
                if not (line.startswith("{") and line.endswith("}")):
                    # Silently skip non-JSON data (binary protocol responses, radio noise, etc.)
                    continue
                # Log only after validating it looks like JSON to avoid logging garbled data
                self.log(f"LoRa RX: {line}")
                try:
                    message = MeshCoreMessage.from_json(line)
                    self.receive_message(message)
                except (json.JSONDecodeError, KeyError) as e:
                    msg = f"Could not parse LoRa message: {e} | raw: {line}"
                    self.log(msg)
                    self.error_logger.error(msg)
            except SerialException as e:
                msg = f"LoRa serial read error: {e}"
                self.log(msg)
                self.error_logger.error(msg)
                break

    # ------------------------------------------------------------------
    # MeshCore companion radio binary protocol helpers
    # ------------------------------------------------------------------

    def _send_command(self, cmd_data: bytes):
        """
        Send a binary command frame to the companion radio.

        Inbound frame format (app→radio):  0x3C + uint16_LE(len) + payload
        """
        if self._serial and self._serial.is_open:
            frame = bytes([_FRAME_IN]) + len(cmd_data).to_bytes(2, "little") + cmd_data
            try:
                self._serial.write(frame)
                self.log(f"LoRa CMD: {cmd_data.hex()}")
            except SerialException as e:
                msg = f"LoRa CMD error: {e}"
                self.log(msg)
                self.error_logger.error(msg)

    def _parse_channel_message(self, payload: bytes):
        """
        Parse channel message payload and extract channel_idx and text.
        Handles both old format and V3 format (with SNR).
        Validates channel_idx to detect encrypted/garbled messages.

        Format Detection Heuristics:
        - If payload >= 12 bytes and SNR (byte 1) is in realistic range (20-60 dB)
          and channel_idx (byte 4) is valid (0-7), use V3 format
        - If payload >= 12 bytes and byte 1 > 7 (impossible as channel_idx in old format)
          and byte 4 is valid channel_idx, use V3 format
        - If payload >= 12 bytes and bytes 2-3 (reserved in V3) are both 0x00
          and byte 4 is a valid channel_idx, use V3 format
        - Otherwise, use old format

        Encryption Detection:
        - After parsing, check if raw message bytes contain reasonable printable characters
        - Encrypted messages will have mostly non-printable/control characters in raw bytes

        V3 format: code(1) + SNR(1) + reserved(2) + channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4) + text
        Old format: code(1) + channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4) + text

        Returns:
            tuple: (channel_idx, text) or (None, None) if parsing fails or message is encrypted
        """
        # Minimum 8 bytes required for old format header
        if len(payload) < _OLD_FORMAT_HEADER_SIZE:
            return (None, None)

        # Try V3 format if payload is long enough (minimum 12 bytes for V3 header + text)
        if len(payload) >= _V3_FORMAT_HEADER_SIZE + 1:
            snr_value = payload[1]
            reserved1 = payload[2]
            reserved2 = payload[3]
            v3_channel_idx = payload[4]
            old_channel_idx = payload[1]

            # Check if this looks like V3 format using multiple heuristics
            use_v3_format = False

            # Heuristic 1: SNR in realistic range AND valid channel_idx = V3 format
            if _MIN_REALISTIC_SNR <= snr_value <= _MAX_REALISTIC_SNR and 0 <= v3_channel_idx <= _MAX_VALID_CHANNEL_IDX:
                use_v3_format = True

            # Heuristic 2: Old format would be invalid (channel_idx > 7), but V3 is valid
            # This handles cases where the old format interpretation doesn't make sense
            elif old_channel_idx > _MAX_VALID_CHANNEL_IDX and 0 <= v3_channel_idx <= _MAX_VALID_CHANNEL_IDX:
                use_v3_format = True

            # Heuristic 3: Reserved bytes are 0x00 AND valid channel_idx at position 4 = V3 format
            # This handles V3 messages with low SNR values (0-7) that could be confused with
            # old format channel_idx. The reserved bytes being 0x00 is a strong V3 indicator.
            # However, exclude SNR=0 as it's unrealistic (signals need some SNR to be received)
            elif (
                reserved1 == 0x00
                and reserved2 == 0x00
                and snr_value > 0
                and 0 <= v3_channel_idx <= _MAX_VALID_CHANNEL_IDX
            ):
                use_v3_format = True

            # If any heuristic matched, parse as V3 format
            if use_v3_format:
                channel_idx = v3_channel_idx
                text_bytes = payload[_V3_FORMAT_HEADER_SIZE:]
                # Check if raw bytes are encrypted (mostly non-printable/control characters)
                if not self._is_valid_message_bytes(text_bytes):
                    return (None, None)
                text = text_bytes.decode("utf-8", "ignore")
                return (channel_idx, text)

        # Fall back to old format
        channel_idx = payload[1]
        # Validate channel_idx is in valid range (0-7)
        # Invalid indices indicate encrypted/garbled messages
        if not (0 <= channel_idx <= _MAX_VALID_CHANNEL_IDX):
            return (None, None)
        text_bytes = payload[_OLD_FORMAT_HEADER_SIZE:]
        # Check if raw bytes are encrypted (mostly non-printable/control characters)
        if not self._is_valid_message_bytes(text_bytes):
            return (None, None)
        text = text_bytes.decode("utf-8", "ignore")
        return (channel_idx, text)

    def _is_valid_message_bytes(self, data: bytes) -> bool:
        """
        Check if raw message bytes appear to be valid text (not encrypted/garbled).

        Encrypted messages typically contain many non-printable control characters.
        Valid messages should have mostly printable ASCII/UTF-8 bytes.

        This checks the RAW bytes before UTF-8 decoding to avoid losing information
        about invalid byte sequences that would be stripped by decode("utf-8", "ignore").

        Args:
            data: The raw message bytes (after header)

        Returns:
            True if bytes appear to be valid text, False if likely encrypted/garbled
        """
        if not data:
            return False

        # First, try to decode as UTF-8 to check for valid encoding
        # Encrypted/garbled data often has invalid UTF-8 sequences
        try:
            decoded = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            # If it can't be decoded as valid UTF-8, it's likely encrypted/garbled
            return False

        # Count printable ASCII characters in the decoded string
        # Encrypted data, even if it happens to decode as UTF-8, will have
        # many control characters or unprintable Unicode characters
        printable_count = 0
        control_count = 0
        for char in decoded:
            char_code = ord(char)
            # Printable ASCII (space through ~) or newline/tab/carriage return
            if 32 <= char_code <= 126 or char_code in (9, 10, 13):
                printable_count += 1
            # Control characters (excluding whitespace)
            elif char_code < 32 or char_code == 127:
                control_count += 1
            # For non-ASCII Unicode characters (> 127), count as printable if they're
            # in commonly used Unicode ranges. We use 0x1000 (4096) as the threshold
            # which covers most Latin, Cyrillic, Greek, and other common scripts
            # while excluding more exotic Unicode blocks that are unlikely in normal text.
            elif char_code < 0x1000:
                printable_count += 1

        # Reject if too many control characters
        if len(decoded) > 0 and control_count / len(decoded) > 0.1:
            return False

        # Require at least 70% printable characters
        if len(decoded) > 0:
            printable_ratio = printable_count / len(decoded)
            return printable_ratio >= 0.70

        return False

    def _parse_binary_frame(self, payload: bytes):
        """
        Dispatch a received companion radio frame payload based on its code byte.

        Handles push notifications and message-delivery responses.
        After each received message the next queued message is requested so
        that the entire message queue is drained automatically.
        """
        code = payload[0]

        if code == 0x00:
            # NOP/keepalive frame from companion radio - ignore silently
            pass

        elif code == _CMD_APP_START:
            # CMD_APP_START echo/acknowledgment from companion radio.
            # The radio may echo this command during session initialization.
            # No action needed - session is already initialized.
            self.log("MeshCore: APP_START acknowledged by companion radio")

        elif code == _CMD_GET_DEVICE_TIME:
            # Companion radio requests current device time.
            # Respond with RESP_CURR_TIME containing 4-byte UNIX timestamp.
            self.log("MeshCore: device time requested, responding…")
            timestamp = int(time.time()).to_bytes(4, "little")
            response = bytes([_RESP_CURR_TIME]) + timestamp
            self._send_command(response)

        elif code == _PUSH_SEND_CONFIRMED:
            # Outgoing message was acknowledged by the mesh network.
            # Payload: ack_code(4) + round_trip_ms(4). No further action needed.
            self.log("MeshCore: send confirmed by mesh network")

        elif code == _PUSH_MSG_WAITING:
            # Companion radio signals that a new message has been received;
            # request it immediately.
            self.log("MeshCore: message waiting, fetching…")
            self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

        elif code == _PUSH_CHAN_MSG:
            # 0x88 = 0x80 | RESP_CHANNEL_MSG: the companion radio pushes an incoming
            # channel message directly (without waiting for CMD_SYNC_NEXT_MSG).
            # Payload layout is identical to RESP_CHANNEL_MSG (0x08):
            # channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4) + text
            self.log("MeshCore: channel message received (push)")
            if len(payload) >= 8:
                # Use _parse_channel_message to handle both V3 format and validate channel_idx
                channel_idx, text = self._parse_channel_message(payload)
                if channel_idx is not None:
                    self.log(f"Binary frame: PUSH_CHAN_MSG on channel_idx {channel_idx}")
                    self._dispatch_channel_message(text, channel_idx)
                else:
                    # Invalid channel_idx or encrypted message - log and skip
                    self.log("Binary frame: PUSH_CHAN_MSG with invalid/encrypted data, skipping")
            else:
                self.log(f"Binary frame: PUSH_CHAN_MSG payload too short ({len(payload)} bytes)")
            # Drain any further queued messages
            self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

        elif code == _RESP_CHANNEL_MSG:
            # RESP_CODE_CHANNEL_MSG_RECV:
            # channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4) + text
            if len(payload) >= 8:
                # Use _parse_channel_message to handle both V3 format and validate channel_idx
                channel_idx, text = self._parse_channel_message(payload)
                if channel_idx is not None:
                    self.log(f"Binary frame: CHANNEL_MSG on channel_idx {channel_idx}")
                    self._dispatch_channel_message(text, channel_idx)
                else:
                    # Invalid channel_idx or encrypted message - log and skip
                    self.log("Binary frame: CHANNEL_MSG with invalid/encrypted data, skipping")
            else:
                self.log(f"Binary frame: CHANNEL_MSG payload too short ({len(payload)} bytes)")
            # Fetch the next queued message
            self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

        elif code == _RESP_CHANNEL_MSG_V3:
            # RESP_CODE_CHANNEL_MSG_RECV_V3 (includes SNR prefix):
            # SNR(1) + reserved(2) + channel_idx(1) + path_len(1) + txt_type(1) + timestamp(4) + text
            if len(payload) >= 12:
                # Use _parse_channel_message to handle V3 format properly and validate
                channel_idx, text = self._parse_channel_message(payload)
                if channel_idx is not None:
                    self.log(f"Binary frame: CHANNEL_MSG_V3 on channel_idx {channel_idx}")
                    self._dispatch_channel_message(text, channel_idx)
                else:
                    # Invalid channel_idx or encrypted message - log and skip
                    self.log("Binary frame: CHANNEL_MSG_V3 with invalid/encrypted data, skipping")
            else:
                self.log(f"Binary frame: CHANNEL_MSG_V3 payload too short ({len(payload)} bytes)")
            self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

        elif code == _RESP_CONTACT_MSG:
            # RESP_CODE_CONTACT_MSG_RECV:
            # pubkey_prefix(6) + path_len(1) + txt_type(1) + timestamp(4) + text
            if len(payload) >= 13:
                sender = payload[1:7].hex()
                text = payload[13:].decode("utf-8", "ignore")
                msg = MeshCoreMessage(sender=sender, content=text, message_type="text")
                self.receive_message(msg)
            self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

        elif code == _RESP_CONTACT_MSG_V3:
            # RESP_CODE_CONTACT_MSG_RECV_V3:
            # SNR(1) + reserved(2) + pubkey_prefix(6) + path_len(1) + txt_type(1) + timestamp(4) + text
            if len(payload) >= 16:
                sender = payload[4:10].hex()
                text = payload[16:].decode("utf-8", "ignore")
                msg = MeshCoreMessage(sender=sender, content=text, message_type="text")
                self.receive_message(msg)
            self._send_command(bytes([_CMD_SYNC_NEXT_MSG]))

        elif code == _RESP_NO_MORE_MSGS:
            self.log("MeshCore: message queue empty")

        else:
            self.log(f"MeshCore: unhandled frame code {code:#04x}")

    def _dispatch_channel_message(self, text: str, channel_idx: int = 0):
        """
        Create and dispatch a MeshCoreMessage from a received channel text.

        MeshCore firmware prepends the sender's advertised name to the channel
        message text in the format ``"sender_name: message_text"``.  This
        method splits on the first ``": "`` to expose a clean *sender* and
        *content* to the registered message handlers.

        Args:
            text: The message text (may include "sender: " prefix)
            channel_idx: The channel index from the LoRa frame (0-7)
        """
        # Track active channel with timestamp
        self._active_channels[channel_idx] = time.time()
        # Save active channels for dashboard display
        self.save_active_channels()

        colon = text.find(": ")
        if colon > 0:
            sender = text[:colon]
            content = text[colon + 2 :]
        else:
            sender = "channel"
            content = text

        # Map channel_idx back to Python channel name
        channel_name = self._get_channel_name(channel_idx)

        # Sanitize sender and content for logging to prevent terminal corruption
        safe_sender = self._sanitize_for_log(sender)
        safe_content = self._sanitize_for_log(content)

        channel_info = f" on channel '{channel_name}'" if channel_name else f" on channel_idx {channel_idx}"
        self.log(f"LoRa RX channel msg from {safe_sender}{channel_info}: {safe_content}")
        msg = MeshCoreMessage(
            sender=sender, content=content, message_type="text", channel=channel_name, channel_idx=channel_idx
        )

        self.receive_message(msg)

    def start(self):
        """Start the MeshCore listener"""
        self.running = True
        if self.serial_port:
            self._connect_serial()
            if self._serial and self._serial.is_open:
                self._start_listener()
        # Initialize channels.json for dashboard (even if empty initially)
        self.save_active_channels()
        self.log("MeshCore started")

    def stop(self):
        """Stop the MeshCore listener"""
        self.running = False
        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=2)
        if self._serial and self._serial.is_open:
            self._serial.close()
            self.log(f"LoRa serial port {self.serial_port} closed")
        self.log("MeshCore stopped")

    def is_running(self) -> bool:
        """Check if MeshCore is running"""
        return self.running

    def _cleanup_expired_channels(self):
        """
        Remove channels that haven't been used in the last 72 hours.

        This prevents the active channels list from growing indefinitely with
        stale channels that are no longer in use.
        """
        import time

        current_time = time.time()
        expiry_seconds = self._channel_expiry_hours * 3600

        # Find expired channels
        expired = [
            channel_idx
            for channel_idx, last_used in self._active_channels.items()
            if current_time - last_used > expiry_seconds
        ]

        # Remove expired channels
        for channel_idx in expired:
            del self._active_channels[channel_idx]
            if self.debug and expired:
                channel_name = self._get_channel_name(channel_idx)
                channel_info = f"'{channel_name}'" if channel_name else f"idx={channel_idx}"
                self.log(f"Expired channel {channel_info} (inactive for {self._channel_expiry_hours}+ hours)")

    def get_active_channels(self):
        """
        Get list of active channels with their names.

        Automatically removes channels that haven't been used in 72 hours.

        Returns:
            list: List of dicts with 'channel_idx', 'channel_name', and 'last_used' keys.
                  Example: [{'channel_idx': 0, 'channel_name': None, 'last_used': 1234567890.0},
                           {'channel_idx': 1, 'channel_name': 'weather', 'last_used': 1234567891.0}]
        """
        # Clean up expired channels before returning
        self._cleanup_expired_channels()

        channels = []
        for channel_idx in sorted(self._active_channels.keys()):
            channel_name = self._get_channel_name(channel_idx)
            channels.append(
                {
                    "channel_idx": channel_idx,
                    "channel_name": channel_name,
                    "last_used": self._active_channels[channel_idx],
                }
            )
        return channels

    def save_active_channels(self, filename: str = None):
        """
        Save active channels to a JSON file for dashboard display.

        Args:
            filename: Path to save the channels data (default: <script_dir>/logs/channels.json)
        """
        import json
        import os
        from datetime import datetime
        from pathlib import Path

        # Use absolute path based on script location to avoid working directory issues
        if filename is None:
            filename = str(Path(__file__).parent / "logs" / "channels.json")

        channels = self.get_active_channels()
        data = {"channels": channels, "last_updated": datetime.now().isoformat()}

        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            if self.debug:
                self.log(f"Saved {len(channels)} active channel(s) to {filename}")
        except (IOError, OSError) as e:
            # Log error instead of failing silently - helps diagnose dashboard issues
            self.error_logger.error(f"Failed to save active channels to {filename}: {e}")


if __name__ == "__main__":
    # Example usage
    mesh = MeshCore("node_001", debug=True)

    def text_handler(message: MeshCoreMessage):
        channel_info = f" on channel '{message.channel}'" if message.channel else ""
        print(f"Text message from {message.sender}{channel_info}: {message.content}")

    mesh.register_handler("text", text_handler)
    mesh.start()

    # Send a test message without channel
    msg1 = mesh.send_message("Hello, MeshCore!", "text")

    # Send a test message with channel
    msg2 = mesh.send_message("Weather broadcast", "text", channel="weather")

    # Simulate receiving the messages
    mesh.receive_message(msg1)
    mesh.receive_message(msg2)

    # Test channel filtering
    print("\nSetting channel filter to 'weather'...")
    mesh.set_channel_filter("weather")

    mesh.receive_message(msg1)  # Should be ignored
    mesh.receive_message(msg2)  # Should be processed

    mesh.stop()
