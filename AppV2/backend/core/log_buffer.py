"""In-memory ring buffer for application logs (admin monitoring / SSE stream)."""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from typing import Any

# Singleton used by logging handler and /api/admin/logs/stream
app_log_buffer: "InMemoryLogBuffer | None" = None


def get_app_log_buffer() -> "InMemoryLogBuffer":
    global app_log_buffer
    if app_log_buffer is None:
        app_log_buffer = InMemoryLogBuffer()
    return app_log_buffer


class InMemoryLogBuffer:
    """Thread-safe ring buffer of (sequence, display_line, optional metadata for UI)."""

    def __init__(self, max_lines: int = 8000) -> None:
        self._max = max_lines
        self._entries: deque[tuple[int, str, dict[str, Any] | None]] = deque(maxlen=max_lines)
        self._lock = threading.Lock()
        self._seq = 0

    def append_line(self, line: str, meta: dict[str, Any] | None = None) -> int:
        with self._lock:
            self._seq += 1
            ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            formatted = f"{ts} | {line}"
            seq = self._seq
            self._entries.append((seq, formatted, meta))
            return seq

    def snapshot(self) -> list[tuple[int, str, dict[str, Any] | None]]:
        with self._lock:
            return list(self._entries)

    def since(self, after_seq: int) -> list[tuple[int, str, dict[str, Any] | None]]:
        with self._lock:
            return [(s, ln, m) for s, ln, m in self._entries if s > after_seq]

    @property
    def last_sequence(self) -> int:
        with self._lock:
            return self._seq


class RingBufferLogHandler(logging.Handler):
    """Logging handler that writes formatted records to InMemoryLogBuffer."""

    def __init__(self, buffer: InMemoryLogBuffer) -> None:
        super().__init__()
        self._buffer = buffer
        fmt = "%(levelname)s [%(name)s] %(message)s"
        self.setFormatter(logging.Formatter(fmt))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            wf_kind = getattr(record, "wf_kind", None)
            wf_agent = getattr(record, "wf_agent", None)
            if wf_kind is None:
                wf_kind = "backend"
            meta: dict[str, Any] = {
                "kind": wf_kind,
                "agent": wf_agent,
                "level": record.levelname,
            }
            wf_phase = getattr(record, "wf_phase", None)
            if wf_phase:
                meta["phase"] = wf_phase
            wf_sub = getattr(record, "wf_submission_id", None)
            if wf_sub:
                meta["submission_id"] = wf_sub
            wf_asg = getattr(record, "wf_assignment_id", None)
            if wf_asg:
                meta["assignment_id"] = wf_asg
            self._buffer.append_line(msg, meta)
        except Exception:
            self.handleError(record)


def json_sse_event(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def attach_ring_buffer_handler(level: int = logging.INFO) -> RingBufferLogHandler:
    """Attach handler to root logger; idempotent (skips if already attached)."""
    buf = get_app_log_buffer()
    root = logging.getLogger()
    for h in root.handlers:
        if isinstance(h, RingBufferLogHandler):
            return h
    handler = RingBufferLogHandler(buf)
    handler.setLevel(level)
    root.addHandler(handler)
    return handler
