"""Keep desktop diagnostics in user storage, including read-only installations.

Python errors rotate while the application runs. The native crash stream rotates
between launches so faulthandler never keeps a descriptor closed by a rollover.
"""

import atexit
import faulthandler
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from PySide6.QtCore import QStandardPaths

_stream = None
_handler = None
_previous_hook = None
_hook = None
_directory = None
MAX_LOG_BYTES = 2 * 1024 * 1024
LOG_BACKUPS = 3


def diagnostics_directory():
    """GenericDataLocation is independent of an application already existing."""
    base = QStandardPaths.writableLocation(QStandardPaths.GenericDataLocation)
    if base:
        return Path(base) / "Entrela" / "logs"
    return Path.home() / ".entrela" / "logs"


def _rotate_native_log(path):
    if not path.exists() or path.stat().st_size < MAX_LOG_BYTES:
        return
    for number in range(LOG_BACKUPS, 0, -1):
        source = path if number == 1 else path.with_name(path.name + f".{number - 1}")
        if source.exists():
            source.replace(path.with_name(path.name + f".{number}"))


def _close_diagnostics():
    global _stream, _handler, _previous_hook, _hook, _directory
    if _stream is not None:
        faulthandler.disable()
        _stream.close()
    if _handler is not None:
        logging.getLogger().removeHandler(_handler)
        _handler.close()
    if _hook is not None and sys.excepthook is _hook:
        sys.excepthook = _previous_hook
    _stream = _handler = _previous_hook = _hook = _directory = None


def _write_launch_metadata(stream):
    from datetime import datetime, timezone

    stream.write("\nEntrela launch " + datetime.now(timezone.utc).isoformat() + "\n")
    import platform
    from importlib.metadata import version, PackageNotFoundError

    stream.write(
        "Python: "
        + sys.version.replace("\n", " ")
        + "\nPlatform: "
        + platform.platform()
        + "\n"
    )
    for package in (
        "PySide6",
        "shiboken6",
        "matplotlib",
        "numpy",
        "qiskit",
        "qiskit-aer",
    ):
        try:
            stream.write(package + ": " + version(package) + "\n")
        except PackageNotFoundError:
            pass
    stream.flush()


def enable_diagnostics():
    """Return the log directory, or None when storage cannot be opened.

    Calling this twice does not add handlers or wrap an existing exception hook
    again. Diagnostic failures must not prevent the desktop from starting.
    """
    global _stream, _handler, _previous_hook, _hook, _directory
    if _stream is not None and not _stream.closed:
        return _directory
    directory = diagnostics_directory()
    native = directory / "entrela-crash.log"
    stream = handler = None
    try:
        directory.mkdir(parents=True, exist_ok=True)
        _rotate_native_log(native)
        stream = native.open("a", encoding="utf-8", buffering=1)
        handler = RotatingFileHandler(
            directory / "entrela.log", maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUPS, encoding="utf-8",
        )
        handler.setLevel(logging.ERROR)
        formatter = logging.Formatter("%(asctime)s UTC %(levelname)s %(name)s: %(message)s")
        formatter.converter = time.gmtime
        handler.setFormatter(formatter)
        _write_launch_metadata(stream)
        faulthandler.enable(file=stream, all_threads=True)
    except (OSError, RuntimeError):
        if stream is not None:
            stream.close()
        if handler is not None:
            handler.close()
        return None
    _stream, _handler, _directory = stream, handler, directory
    _previous_hook = previous = sys.excepthook

    def report(kind, value, traceback):
        try:
            record = logging.LogRecord(
                "entrela", logging.ERROR, "", 0, "Exceção não tratada", (),
                (kind, value, traceback),
            )
            handler.handle(record)
        except (OSError, RuntimeError):
            # A full disk must not mask the original unhandled exception.
            pass
        finally:
            previous(kind, value, traceback)

    _hook = sys.excepthook = report
    logging.getLogger().addHandler(handler)
    atexit.register(_close_diagnostics)
    return directory
