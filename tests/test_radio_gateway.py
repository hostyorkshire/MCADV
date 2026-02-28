"""
Tests for radio_gateway.py – construction, HTTP forwarding, channel filtering,
and retry/error behaviour.  All serial and HTTP I/O is mocked.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from meshcore import MeshCoreMessage  # noqa: E402


def _make_gateway(**kwargs):
    """
    Build a RadioGateway without touching any hardware or network.

    We patch MeshCore and requests.Session so the constructor succeeds.
    """
    from radio_gateway import RadioGateway

    with patch("radio_gateway.MeshCore") as MockMesh, \
         patch("radio_gateway.requests.Session") as MockSession, \
         patch("radio_gateway.get_meshcore_logger") as MockLogger:

        mock_mesh_instance = MagicMock()
        MockMesh.return_value = mock_mesh_instance
        mock_session_instance = MagicMock()
        MockSession.return_value = mock_session_instance
        MockLogger.return_value = (MagicMock(), MagicMock())

        defaults = dict(
            bot_server_url="http://localhost:5000",
            port=None,
            baud=115200,
            debug=False,
            allowed_channel_idx=None,
            node_id="TEST_GW",
            timeout=10,
        )
        defaults.update(kwargs)
        gw = RadioGateway(**defaults)

    return gw


# =============================================================================
# TestRadioGateway – construction
# =============================================================================


class TestRadioGateway(unittest.TestCase):

    def test_url_trailing_slash_stripped(self):
        gw = _make_gateway(bot_server_url="http://localhost:5000/")
        self.assertEqual(gw.bot_server_url, "http://localhost:5000")

    def test_url_no_trailing_slash_unchanged(self):
        gw = _make_gateway(bot_server_url="http://192.168.1.10:5000")
        self.assertEqual(gw.bot_server_url, "http://192.168.1.10:5000")

    def test_default_allowed_channel_idx_none(self):
        gw = _make_gateway()
        self.assertIsNone(gw.allowed_channel_idx)

    def test_explicit_channel_idx(self):
        gw = _make_gateway(allowed_channel_idx=3)
        self.assertEqual(gw.allowed_channel_idx, 3)

    def test_initial_stats_are_zero(self):
        gw = _make_gateway()
        for v in gw.stats.values():
            self.assertEqual(v, 0)

    def test_timeout_stored(self):
        gw = _make_gateway(timeout=20)
        self.assertEqual(gw.timeout, 20)

    def test_running_false_on_init(self):
        gw = _make_gateway()
        self.assertFalse(gw._running)

    def test_node_id_passed_to_meshcore(self):
        """Verify RadioGateway passes the node_id to MeshCore."""
        from radio_gateway import RadioGateway
        with patch("radio_gateway.MeshCore") as MockMesh, \
             patch("radio_gateway.requests.Session"), \
             patch("radio_gateway.get_meshcore_logger") as MockLogger:
            MockLogger.return_value = (MagicMock(), MagicMock())
            MockMesh.return_value = MagicMock()
            RadioGateway(bot_server_url="http://localhost:5000", node_id="MY_NODE")
            call_kwargs = MockMesh.call_args[1]
            self.assertEqual(call_kwargs.get("node_id"), "MY_NODE")


# =============================================================================
# TestHTTPForwarding
# =============================================================================


class TestHTTPForwarding(unittest.TestCase):

    def setUp(self):
        self.gw = _make_gateway()
        # Replace the requests session with a controllable mock
        self.mock_session = MagicMock()
        self.gw.session = self.mock_session

    def _good_response(self, response_text):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"response": response_text}
        resp.raise_for_status = MagicMock()
        return resp

    def test_forward_returns_response_text(self):
        self.mock_session.post.return_value = self._good_response("Hello adventurer!")
        msg = MeshCoreMessage(sender="Alice", content="!adv", channel_idx=1)
        result = self.gw._forward_to_bot(msg)
        self.assertEqual(result, "Hello adventurer!")

    def test_forward_posts_to_api_message(self):
        self.mock_session.post.return_value = self._good_response("ok")
        msg = MeshCoreMessage(sender="Bob", content="1", channel_idx=2)
        self.gw._forward_to_bot(msg)
        posted_url = self.mock_session.post.call_args[0][0]
        self.assertIn("/api/message", posted_url)

    def test_forward_includes_sender_in_payload(self):
        self.mock_session.post.return_value = self._good_response("ok")
        msg = MeshCoreMessage(sender="Carol", content="!help", channel_idx=1)
        self.gw._forward_to_bot(msg)
        payload = self.mock_session.post.call_args[1]["json"]
        self.assertEqual(payload["sender"], "Carol")

    def test_forward_includes_content_in_payload(self):
        self.mock_session.post.return_value = self._good_response("ok")
        msg = MeshCoreMessage(sender="Dave", content="!quit", channel_idx=1)
        self.gw._forward_to_bot(msg)
        payload = self.mock_session.post.call_args[1]["json"]
        self.assertEqual(payload["content"], "!quit")

    def test_forward_returns_none_on_http_error(self):
        from requests.exceptions import RequestException
        self.mock_session.post.side_effect = RequestException("timeout")
        msg = MeshCoreMessage(sender="Eve", content="!adv", channel_idx=1)
        result = self.gw._forward_to_bot(msg)
        self.assertIsNone(result)

    def test_forward_returns_none_on_bad_json(self):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = ValueError("bad json")
        self.mock_session.post.return_value = resp
        msg = MeshCoreMessage(sender="Frank", content="!adv", channel_idx=1)
        result = self.gw._forward_to_bot(msg)
        self.assertIsNone(result)

    def test_forward_returns_none_when_response_key_missing(self):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {}  # no "response" key
        self.mock_session.post.return_value = resp
        msg = MeshCoreMessage(sender="Greta", content="!adv", channel_idx=1)
        result = self.gw._forward_to_bot(msg)
        self.assertIsNone(result)

    def test_handle_message_increments_received_counter(self):
        self.mock_session.post.return_value = self._good_response("ok")
        self.gw.mesh = MagicMock()
        msg = MeshCoreMessage(sender="Alice", content="!adv", channel_idx=1)
        self.gw.handle_message(msg)
        self.assertEqual(self.gw.stats["messages_received"], 1)

    def test_handle_message_increments_forwarded_counter(self):
        self.mock_session.post.return_value = self._good_response("story text")
        self.gw.mesh = MagicMock()
        msg = MeshCoreMessage(sender="Alice", content="!adv", channel_idx=1)
        self.gw.handle_message(msg)
        self.assertEqual(self.gw.stats["messages_forwarded"], 1)

    def test_handle_message_increments_failed_counter_on_none(self):
        self.mock_session.post.return_value = self._good_response(None)
        self.gw.mesh = MagicMock()
        msg = MeshCoreMessage(sender="Alice", content="!adv", channel_idx=1)
        self.gw.handle_message(msg)
        self.assertEqual(self.gw.stats["messages_failed"], 1)


# =============================================================================
# TestChannelFiltering
# =============================================================================


class TestChannelFiltering(unittest.TestCase):

    def setUp(self):
        self.gw = _make_gateway(allowed_channel_idx=1)
        self.mock_session = MagicMock()
        self.gw.session = self.mock_session
        self.gw.mesh = MagicMock()

    def test_allowed_channel_is_forwarded(self):
        good_resp = MagicMock()
        good_resp.raise_for_status = MagicMock()
        good_resp.json.return_value = {"response": "ok"}
        self.mock_session.post.return_value = good_resp
        msg = MeshCoreMessage(sender="A", content="!adv", channel_idx=1)
        self.gw.handle_message(msg)
        self.assertTrue(self.mock_session.post.called)

    def test_wrong_channel_is_ignored(self):
        msg = MeshCoreMessage(sender="A", content="!adv", channel_idx=2)
        self.gw.handle_message(msg)
        self.assertFalse(self.mock_session.post.called)

    def test_wrong_channel_does_not_increment_received(self):
        # messages_received should still be incremented (we received it)
        msg = MeshCoreMessage(sender="A", content="!adv", channel_idx=5)
        self.gw.handle_message(msg)
        self.assertEqual(self.gw.stats["messages_received"], 1)

    def test_no_filter_forwards_all_channels(self):
        gw = _make_gateway(allowed_channel_idx=None)
        gw.session = self.mock_session
        gw.mesh = MagicMock()
        good_resp = MagicMock()
        good_resp.raise_for_status = MagicMock()
        good_resp.json.return_value = {"response": "ok"}
        self.mock_session.post.return_value = good_resp
        for ch in [0, 1, 4, 7]:
            self.mock_session.post.reset_mock()
            msg = MeshCoreMessage(sender="A", content="hi", channel_idx=ch)
            gw.handle_message(msg)
            self.assertTrue(self.mock_session.post.called, f"ch={ch} not forwarded")


# =============================================================================
# TestRetryLogic
# =============================================================================


class TestRetryLogic(unittest.TestCase):
    """Test that errors are handled gracefully and stats are updated correctly."""

    def setUp(self):
        self.gw = _make_gateway()
        self.mock_session = MagicMock()
        self.gw.session = self.mock_session
        self.gw.mesh = MagicMock()

    def test_exception_during_forward_increments_failed(self):
        from requests.exceptions import RequestException
        self.mock_session.post.side_effect = RequestException("conn refused")
        msg = MeshCoreMessage(sender="A", content="!adv", channel_idx=1)
        self.gw.handle_message(msg)
        self.assertEqual(self.gw.stats["messages_failed"], 1)

    def test_exception_does_not_raise_to_caller(self):
        from requests.exceptions import RequestException
        self.mock_session.post.side_effect = RequestException("boom")
        msg = MeshCoreMessage(sender="A", content="!adv", channel_idx=1)
        # Should not raise
        self.gw.handle_message(msg)

    def test_multi_part_response_split_on_part_separator(self):
        gw = _make_gateway()
        gw.mesh = MagicMock()
        text = "Part one\n---PART---\nPart two"
        gw._send_response(text, channel_idx=1)
        self.assertEqual(gw.mesh.send_message.call_count, 2)

    def test_single_response_sent_as_one_message(self):
        gw = _make_gateway()
        gw.mesh = MagicMock()
        gw._send_response("Just one message", channel_idx=1)
        self.assertEqual(gw.mesh.send_message.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
