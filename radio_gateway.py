#!/usr/bin/env python3
"""
Radio Gateway for MCADV Distributed Mode

This script runs on Pi Zero 2W and handles LoRa radio communication only.
All bot logic and LLM processing happens on a separate server (Pi 4/5, Jetson, or PC).

Architecture:
  Player → LoRa → Pi Zero 2W (this script) → HTTP → Bot Server (adventure_bot.py)

The gateway:
  1. Receives messages from LoRa radio via MeshCore
  2. Forwards them to the bot server via HTTP POST
  3. Receives responses from the bot server
  4. Sends responses back via LoRa radio

This keeps the Pi Zero 2W lightweight (~15MB RAM) while offloading
all compute-intensive operations to a more powerful device.
"""

import argparse
import sys
import threading
import time
from typing import Optional

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    print("Error: requests module not found. Install with: pip install requests")
    sys.exit(1)

from logging_config import get_meshcore_logger, log_startup_info
from meshcore import MeshCore, MeshCoreMessage


class RadioGateway:
    """
    LoRa radio gateway that forwards messages to a bot server via HTTP.

    This runs on Pi Zero 2W and handles only radio I/O, keeping memory
    usage minimal. All game logic and LLM processing happens on the bot server.
    """

    def __init__(
        self,
        bot_server_url: str,
        port: Optional[str] = None,
        baud: int = 115200,
        debug: bool = False,
        allowed_channel_idx: Optional[int] = None,
        node_id: str = "GATEWAY",
        timeout: int = 30,
    ):
        """
        Initialize the radio gateway.

        Args:
            bot_server_url: URL of the bot server (e.g., http://pi5.local:5000)
            port: Serial port for LoRa radio (auto-detects if None)
            baud: Baud rate for serial communication
            debug: Enable debug logging
            allowed_channel_idx: Only forward messages from this channel (None = all channels)
            node_id: MeshCore node identifier for this gateway
            timeout: HTTP request timeout in seconds
        """
        self.bot_server_url = bot_server_url.rstrip("/")
        self.allowed_channel_idx = allowed_channel_idx
        self.timeout = timeout
        self._running = False

        # Logging
        self.logger, self.error_logger = get_meshcore_logger(debug=debug)

        # HTTP session for connection pooling (faster requests)
        self.session = requests.Session()

        # MeshCore handles all LoRa serial I/O
        self.mesh = MeshCore(
            node_id=node_id,
            debug=debug,
            serial_port=port,
            baud_rate=baud,
        )
        self.mesh.register_handler("text", self.handle_message)

        # Stats for monitoring
        self.stats = {
            "messages_received": 0,
            "messages_forwarded": 0,
            "messages_failed": 0,
            "responses_sent": 0,
        }

    def handle_message(self, message: MeshCoreMessage) -> None:
        """
        Handle incoming message from LoRa radio.

        Forwards the message to the bot server and sends the response back via LoRa.
        """
        self.stats["messages_received"] += 1

        # Filter by channel if configured
        if self.allowed_channel_idx is not None:
            if message.channel_idx != self.allowed_channel_idx:
                self.logger.debug(
                    f"Ignoring message on channel_idx={message.channel_idx} "
                    f"(only listening to {self.allowed_channel_idx})"
                )
                return

        sender = message.sender
        content = message.content
        channel_idx = message.channel_idx if message.channel_idx is not None else 0

        self.logger.info(f"[{sender}@ch{channel_idx}] {content}")

        try:
            # Forward message to bot server
            response_text = self._forward_to_bot(message)

            if response_text:
                self.stats["messages_forwarded"] += 1
                # Send response back via LoRa
                self._send_response(response_text, channel_idx)
                self.stats["responses_sent"] += 1
            else:
                self.stats["messages_failed"] += 1
                self.logger.warning(f"No response from bot server for message from {sender}")

        except Exception as e:
            self.stats["messages_failed"] += 1
            self.error_logger.exception(f"Error handling message from {sender}")
            self.logger.error(f"Error handling message: {e}")

    def _forward_to_bot(self, message: MeshCoreMessage) -> Optional[str]:
        """
        Forward a message to the bot server via HTTP POST.

        Returns the bot's response text, or None if the request failed.
        """
        url = f"{self.bot_server_url}/api/message"
        payload = {
            "sender": message.sender,
            "content": message.content,
            "channel_idx": message.channel_idx if message.channel_idx is not None else 0,
            "timestamp": message.timestamp,
        }

        try:
            self.logger.debug(f"Forwarding to bot server: {url}")
            response = self.session.post(
                url,
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            return data.get("response")

        except RequestException as e:
            self.error_logger.exception("HTTP request to bot server failed")
            self.logger.error(f"Failed to contact bot server: {e}")
            return None
        except (KeyError, ValueError) as e:
            self.error_logger.exception("Invalid response from bot server")
            self.logger.error(f"Invalid response from bot server: {e}")
            return None

    def _send_response(self, text: str, channel_idx: int) -> None:
        """
        Send a response back to the LoRa network.

        The bot server handles message splitting if needed, so we just
        send whatever we receive. However, if we get a response that looks
        like it has multiple parts, we send them separately.
        """
        # Check if response is a multi-part message (indicated by newline-separated parts)
        # The bot server may return multiple messages that need to be sent separately
        if "\n---PART---\n" in text:
            # Multi-part response - send each part separately with a small delay
            parts = text.split("\n---PART---\n")
            for i, part in enumerate(parts):
                if part.strip():
                    self.mesh.send_message(part.strip(), "text", channel_idx=channel_idx)
                    if i < len(parts) - 1:
                        time.sleep(0.5)  # Small delay between parts
        else:
            # Single message
            self.mesh.send_message(text, "text", channel_idx=channel_idx)

    def _poll_broadcasts(self) -> None:
        """Poll the bot server for any bot-initiated broadcast messages."""
        try:
            resp = self.session.get(
                f"{self.bot_server_url}/api/broadcast",
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("message"):
                    channel_idx = data.get("channel_idx", 0)
                    self._send_response(data["message"], channel_idx)
        except Exception as e:
            self.logger.debug(f"Broadcast poll error: {e}")

    def run(self) -> None:
        """Start the gateway and run until Ctrl+C."""
        log_startup_info(self.logger, "MCADV Radio Gateway", "1.0.0")

        # Test connection to bot server
        try:
            test_url = f"{self.bot_server_url}/api/health"
            self.logger.info(f"Testing connection to bot server: {test_url}")
            response = self.session.get(test_url, timeout=5)
            response.raise_for_status()
            self.logger.info("✓ Connected to bot server successfully")
        except RequestException as e:
            self.logger.warning(f"Cannot reach bot server at {self.bot_server_url}: {e}")
            self.logger.warning("Gateway will start anyway, but messages will fail until server is available")

        self.mesh.start()
        self._running = True

        if self.allowed_channel_idx is not None:
            msg = f"Radio gateway running on channel_idx={self.allowed_channel_idx}"
        else:
            msg = "Radio gateway running on all channels"

        print(msg)
        print(f"Bot server: {self.bot_server_url}")
        self.logger.info(msg)
        self.logger.info(f"Bot server: {self.bot_server_url}")
        print("Press Ctrl+C to stop.\n", flush=True)

        last_stats_time = time.time()

        # Start broadcast polling in a background thread
        def broadcast_poller():
            while self._running:
                self._poll_broadcasts()
                time.sleep(30)

        broadcast_thread = threading.Thread(target=broadcast_poller, daemon=True)
        broadcast_thread.start()

        try:
            while self._running:
                time.sleep(1)

                # Log stats every 5 minutes
                if time.time() - last_stats_time >= 300:
                    self.logger.info(
                        f"Stats: received={self.stats['messages_received']}, "
                        f"forwarded={self.stats['messages_forwarded']}, "
                        f"failed={self.stats['messages_failed']}, "
                        f"sent={self.stats['responses_sent']}"
                    )
                    last_stats_time = time.time()

        except KeyboardInterrupt:
            print("\nStopping...")
            self.logger.info("Stopping...")
        finally:
            self._running = False
            self.session.close()
            self.mesh.stop()
            print("Radio gateway stopped.")
            self.logger.info(
                f"Final stats: received={self.stats['messages_received']}, "
                f"forwarded={self.stats['messages_forwarded']}, "
                f"failed={self.stats['messages_failed']}, "
                f"sent={self.stats['responses_sent']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCADV Radio Gateway – LoRa to HTTP bridge for distributed mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This gateway runs on Pi Zero 2W and forwards LoRa messages to the bot server.
The bot server (adventure_bot.py) must be running with --distributed-mode.

Examples:
  python radio_gateway.py --bot-server-url http://pi5.local:5000
  python radio_gateway.py --bot-server-url http://192.168.1.50:5000 --channel-idx 1
  python radio_gateway.py -p /dev/ttyUSB0 --bot-server-url http://pi5.local:5000 --debug
""",
    )

    parser.add_argument(
        "--bot-server-url",
        required=True,
        help="URL of the bot server (e.g., http://pi5.local:5000 or http://192.168.1.50:5000)"
    )
    parser.add_argument(
        "-p", "--port",
        help="Serial port for LoRa radio (e.g., /dev/ttyUSB0). Auto-detects if omitted."
    )
    parser.add_argument(
        "-b", "--baud",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)"
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "-c", "--channel-idx",
        type=int,
        help="Only forward messages from this channel index (e.g., 1)"
    )
    parser.add_argument(
        "--node-id",
        default="GATEWAY",
        help="MeshCore node identifier (default: GATEWAY)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP request timeout in seconds (default: 30)"
    )

    args = parser.parse_args()

    # Create and run gateway
    gateway = RadioGateway(
        bot_server_url=args.bot_server_url,
        port=args.port,
        baud=args.baud,
        debug=args.debug,
        allowed_channel_idx=args.channel_idx,
        node_id=args.node_id,
        timeout=args.timeout,
    )

    gateway.run()


if __name__ == "__main__":
    main()
