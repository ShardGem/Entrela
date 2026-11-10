"""Cooperative local-process locks, shared by threads and app instances.

The small lock file remains on disk: deleting it after unlocking would allow
another process to lock an obsolete inode. Operating systems release locks
automatically if an application exits unexpectedly.
"""

from contextlib import contextmanager
import errno
import math
import os
from pathlib import Path
import threading
import time


class FileLockTimeout(TimeoutError):
    """Another local operation kept a data file busy beyond the allowed time."""


class _LockState:
    def __init__(self):
        self.mutex = threading.RLock()
        self.depth = 0


_states = {}
_states_mutex = threading.Lock()


def _reset_after_fork():
    global _states, _states_mutex
    _states = {}
    _states_mutex = threading.Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_after_fork)


def _try_os_lock(descriptor):
    if os.name == "nt":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_os(descriptor):
    if os.name == "nt":
        import msvcrt

        os.lseek(descriptor, 0, os.SEEK_SET)
        msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)


@contextmanager
def file_lock(path, *, timeout=5.0):
    """Hold an exclusive lock, reentrant in the same thread, with a deadline.

    This coordinates cooperating processes on a local filesystem. It does not
    implement network synchronization or multiuser conflict resolution.
    """
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        raise ValueError("O tempo de espera do bloqueio deve ser finito e não negativo.")
    path = Path(path).resolve()
    with _states_mutex:
        state = _states.setdefault(str(path), _LockState())
    deadline = time.monotonic() + timeout

    def busy():
        return FileLockTimeout(
            errno.ETIMEDOUT,
            "Os dados estão em uso por outra operação. Tente novamente em alguns instantes.",
            str(path),
        )

    if not state.mutex.acquire(timeout=max(0.0, deadline - time.monotonic())):
        raise busy()
    descriptor = None
    locked = False
    try:
        if state.depth:
            state.depth += 1
            try:
                yield
            finally:
                state.depth -= 1
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        if not os.fstat(descriptor).st_size:
            os.write(descriptor, b"\0")
        while True:
            try:
                _try_os_lock(descriptor)
                locked = True
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise busy() from exc
                time.sleep(min(0.025, remaining))
        state.depth = 1
        try:
            yield
        finally:
            state.depth = 0
    finally:
        try:
            if locked:
                _unlock_os(descriptor)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            state.mutex.release()


@contextmanager
def directory_lock(directory, *, timeout=5.0):
    """Serialize transactions belonging to a single persistent directory."""
    with file_lock(Path(directory) / ".entrela.lock", timeout=timeout):
        yield
