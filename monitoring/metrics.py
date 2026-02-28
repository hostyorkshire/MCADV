import time
import threading
from collections import defaultdict, deque
from typing import Dict


class MetricsCollector:
    """Thread-safe collector for runtime metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._message_latencies: deque = deque(maxlen=1000)
        self._llm_response_times: deque = deque(maxlen=1000)
        self._errors: Dict[str, int] = defaultdict(int)
        self._active_sessions: int = 0
        self._start_time = time.time()

    def track_message_latency(self, duration: float) -> None:
        with self._lock:
            self._message_latencies.append(duration)

    def track_llm_response_time(self, duration: float) -> None:
        with self._lock:
            self._llm_response_times.append(duration)

    def track_error(self, error_type: str) -> None:
        with self._lock:
            self._errors[error_type] += 1

    def track_active_sessions(self, count: int) -> None:
        with self._lock:
            self._active_sessions = count

    def _avg(self, dq: deque) -> float:
        items = list(dq)
        return sum(items) / len(items) if items else 0.0

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds": time.time() - self._start_time,
                "active_sessions": self._active_sessions,
                "message_latency_avg": self._avg(self._message_latencies),
                "message_latency_count": len(self._message_latencies),
                "llm_response_time_avg": self._avg(self._llm_response_times),
                "llm_response_time_count": len(self._llm_response_times),
                "errors": dict(self._errors),
            }

    def get_prometheus_format(self) -> str:
        stats = self.get_stats()
        lines = [
            f'mcadv_uptime_seconds {stats["uptime_seconds"]:.2f}',
            f'mcadv_active_sessions {stats["active_sessions"]}',
            f'mcadv_message_latency_avg {stats["message_latency_avg"]:.6f}',
            f'mcadv_llm_response_time_avg {stats["llm_response_time_avg"]:.6f}',
        ]
        for etype, count in stats["errors"].items():
            lines.append(f'mcadv_errors_total{{type="{etype}"}} {count}')
        return '\n'.join(lines) + '\n'

    def reset(self) -> None:
        with self._lock:
            self._message_latencies.clear()
            self._llm_response_times.clear()
            self._errors.clear()
            self._active_sessions = 0
            self._start_time = time.time()
