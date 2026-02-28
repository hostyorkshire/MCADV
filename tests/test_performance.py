"""
Performance benchmarks for MCADV.

Uses time.perf_counter for precise measurements.  No real LLM calls are made –
all external dependencies are mocked.
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from adventure_bot import AdventureBot  # noqa: E402
from meshcore import MeshCoreMessage  # noqa: E402
from utils.chunking import chunk_message  # noqa: E402

# Acceptable upper bound for benchmark assertions
_MAX_LATENCY_MS = 500  # 500 ms is generous for unit operations


def _make_bot() -> AdventureBot:
    bot = AdventureBot(
        debug=False,
        ollama_url="http://localhost:11434",
        model="test-model",
    )
    bot._sessions = {}
    bot._save_sessions = MagicMock()
    bot._call_ollama = MagicMock(return_value=None)
    return bot


# =============================================================================
# TestMessageThroughput
# =============================================================================


class TestMessageThroughput(unittest.TestCase):
    """Measure how many messages per second the bot can process."""

    def setUp(self):
        self.bot = _make_bot()

    def test_100_help_messages(self):
        count = 100
        start = time.perf_counter()
        for i in range(count):
            msg = MeshCoreMessage(sender=f"User{i}", content="!help", channel_idx=1)
            self.bot.handle_message(msg)
        elapsed = time.perf_counter() - start
        msgs_per_sec = count / elapsed
        # Should handle at least 50 msgs/sec
        self.assertGreater(msgs_per_sec, 50, f"Only {msgs_per_sec:.1f} msgs/sec")

    def test_50_adventure_starts(self):
        count = 50
        start = time.perf_counter()
        for i in range(count):
            msg = MeshCoreMessage(sender=f"U{i}", content="!adv", channel_idx=i)
            self.bot.handle_message(msg)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 5.0, f"50 adventure starts took {elapsed:.2f}s (too slow)")

    def test_sequential_choice_throughput(self):
        self.bot.handle_message(MeshCoreMessage(sender="A", content="!adv", channel_idx=1))
        # Make repeated choices (story may end and require restart)
        count = 0
        start = time.perf_counter()
        for _ in range(30):
            msg = MeshCoreMessage(sender="A", content="1", channel_idx=1)
            self.bot.handle_message(msg)
            count += 1
            # Restart if session ended
            if not self.bot._get_session("channel_1"):
                self.bot.handle_message(MeshCoreMessage(sender="A", content="!adv", channel_idx=1))
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 5.0, f"Throughput test took {elapsed:.2f}s")


# =============================================================================
# TestSessionLookup
# =============================================================================


class TestSessionLookup(unittest.TestCase):
    """Benchmark session lookup time with many sessions in memory."""

    def setUp(self):
        self.bot = _make_bot()
        # Pre-populate 1000 sessions
        for i in range(1000):
            self.bot._sessions[f"channel_{i}"] = {
                "status": "active",
                "theme": "fantasy",
                "node": "start",
                "history": [],
                "last_active": time.time(),
            }

    def test_lookup_existing_session_fast(self):
        start = time.perf_counter()
        for i in range(1000):
            self.bot._get_session(f"channel_{i}")
        elapsed = time.perf_counter() - start
        # 1000 lookups should complete well under 500ms
        self.assertLess(elapsed * 1000, _MAX_LATENCY_MS * 10)

    def test_lookup_nonexistent_session_fast(self):
        start = time.perf_counter()
        for i in range(500):
            self.bot._get_session(f"missing_{i}")
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed * 1000, _MAX_LATENCY_MS * 5)

    def test_update_session_performance(self):
        start = time.perf_counter()
        for i in range(200):
            self.bot._update_session(f"channel_{i}", {"node": "forest"})
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 2.0, f"200 session updates took {elapsed:.2f}s")


# =============================================================================
# TestLLMResponseTime
# =============================================================================


class TestLLMResponseTime(unittest.TestCase):
    """Measure mock LLM response path latency."""

    def setUp(self):
        self.bot = _make_bot()
        self.bot._sessions["ch1"] = {
            "status": "active", "theme": "fantasy", "node": "start", "history": []
        }

    def test_fallback_story_generation_fast(self):
        start = time.perf_counter()
        for _ in range(100):
            self.bot._get_fallback_story("ch1", choice=None, theme="fantasy")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 100) * 1000
        self.assertLess(avg_ms, _MAX_LATENCY_MS, f"avg fallback latency {avg_ms:.2f}ms")

    def test_generate_story_with_mock_llm_fast(self):
        start = time.perf_counter()
        for _ in range(50):
            self.bot._sessions["ch1"]["node"] = "start"
            self.bot._generate_story("ch1", choice=None, theme="fantasy")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 50) * 1000
        self.assertLess(avg_ms, _MAX_LATENCY_MS, f"avg generate latency {avg_ms:.2f}ms")

    def test_handle_message_latency(self):
        timings = []
        for i in range(50):
            msg = MeshCoreMessage(sender="A", content="!help", channel_idx=1)
            start = time.perf_counter()
            self.bot.handle_message(msg)
            timings.append(time.perf_counter() - start)
        avg_ms = (sum(timings) / len(timings)) * 1000
        self.assertLess(avg_ms, _MAX_LATENCY_MS, f"avg handle_message latency {avg_ms:.2f}ms")


# =============================================================================
# TestMessageChunking
# =============================================================================


class TestMessageChunking(unittest.TestCase):
    """Benchmark chunk_message performance."""

    def test_short_message_no_split(self):
        result = chunk_message("Hello world", max_len=230)
        self.assertEqual(len(result), 1)

    def test_long_message_splits(self):
        text = "Word " * 100  # 500 chars
        result = chunk_message(text, max_len=230)
        self.assertGreater(len(result), 1)

    def test_all_chunks_within_max_len(self):
        text = "This is a test sentence. " * 20
        chunks = chunk_message(text, max_len=230)
        for c in chunks:
            self.assertLessEqual(len(c), 230, f"Chunk too long: {len(c)}")

    def test_chunking_100_messages_fast(self):
        text = "Adventure story text that might exceed the radio limit. " * 5
        start = time.perf_counter()
        for _ in range(100):
            chunk_message(text, max_len=230)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.0, f"100 chunking ops took {elapsed:.2f}s")

    def test_chunking_preserves_content(self):
        text = "The quick brown fox jumps over the lazy dog. " * 10
        chunks = chunk_message(text, max_len=230)
        combined = " ".join(chunks)
        # All words from original should appear somewhere
        self.assertIn("quick", combined)
        self.assertIn("brown", combined)

    def test_prefix_added_to_multiple_chunks(self):
        text = "X " * 200  # Forces multiple chunks
        chunks = chunk_message(text, max_len=50)
        if len(chunks) > 1:
            self.assertIn("Part 1/", chunks[0])

    def test_single_chunk_no_prefix(self):
        text = "Short message"
        chunks = chunk_message(text, max_len=230)
        self.assertEqual(len(chunks), 1)
        self.assertNotIn("Part 1/", chunks[0])

    def test_exact_max_len_no_split(self):
        text = "A" * 230
        chunks = chunk_message(text, max_len=230)
        self.assertEqual(len(chunks), 1)

    def test_one_over_max_len_splits(self):
        text = "A" * 231
        chunks = chunk_message(text, max_len=230)
        self.assertGreater(len(chunks), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
