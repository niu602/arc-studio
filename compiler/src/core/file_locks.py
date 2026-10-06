"""Process-wide file-granularity locks for concurrent agent filesystem writes.

ARC's IMPLEMENT stage runs several TDD agents in parallel. Each agent writes
through deepagents' ``FilesystemBackend``, whose async methods
(``awrite``/``aedit``/``adelete``) dispatch the synchronous ``write``/``edit``/
``delete`` implementations via ``asyncio.to_thread``. Concurrent workers can
therefore touch the same file from different OS threads at the same time.

``FileLockRegistry`` exposes a process-wide singleton that maps a normalized
absolute path to a ``threading.Lock``. Write paths are locked before mutation so
overlapping edits to shared files (for example the app shell edited by several
requirement nodes) serialize deterministically instead of corrupting each other.
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class FileLockRegistry:
    """Thread-safe registry of per-file ``threading.Lock`` objects."""

    _instance: "FileLockRegistry | None" = None
    _instance_guard = threading.Lock()

    def __init__(self) -> None:
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self._test_condition = threading.Condition()
        self._active_tests = 0

    @classmethod
    def instance(cls) -> "FileLockRegistry":
        with cls._instance_guard:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @staticmethod
    def normalize(path: str | Path) -> str:
        """Normalize a path to a stable, case-folded lock key.

        ``normcase`` lowercases and normalizes separators on Windows (so
        ``README.md`` and ``readme.md`` share one lock) and is a no-op on POSIX.
        """
        return os.path.normcase(os.path.normpath(str(path)))

    def lock_for(self, key: str) -> threading.Lock:
        """Return (creating if needed) the lock for a normalized key."""
        with self._guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._locks[key] = lock
            return lock

    @contextmanager
    def acquire(self, path: str | Path) -> Iterator[None]:
        """Acquire the lock guarding ``path`` for the duration of the block."""
        lock = self.lock_for(self.normalize(path))
        lock.acquire()
        try:
            yield
        finally:
            lock.release()

    # -- Test barrier -------------------------------------------------------
    # While a test command (vitest / playwright) is running, agent filesystem
    # writes must pause so a test never reads a file mid-mutation. Writes run
    # inside ``asyncio.to_thread`` worker threads, so blocking them on a
    # ``threading.Condition`` does not stall the asyncio event loop.

    def mark_test_running(self) -> None:
        """Record that a test command started (reference-counted)."""
        with self._test_condition:
            self._active_tests += 1

    def mark_test_idle(self) -> None:
        """Record that a test command finished, waking any blocked writers."""
        with self._test_condition:
            self._active_tests = max(0, self._active_tests - 1)
            if self._active_tests == 0:
                self._test_condition.notify_all()

    def wait_if_test_running(self) -> None:
        """Block (in the calling thread) until no test command is active."""
        with self._test_condition:
            while self._active_tests > 0:
                self._test_condition.wait()
