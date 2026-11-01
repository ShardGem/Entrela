"""Keep Python and native crash evidence across desktop launches."""

import faulthandler
import logging
from pathlib import Path
import sys

_stream = None


def enable_diagnostics():
    global _stream
    directory = Path.cwd() / "logs"
    try:
        directory.mkdir(exist_ok=True)
        _stream = (directory / "entrela-crash.log").open(
            "a", encoding="utf-8", buffering=1
        )
    except OSError:
        return
    from datetime import datetime, timezone

    _stream.write("\nEntrela launch " + datetime.now(timezone.utc).isoformat() + "\n")
    import platform
    from importlib.metadata import version, PackageNotFoundError

    _stream.write(
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
            _stream.write(package + ": " + version(package) + "\n")
        except PackageNotFoundError:
            pass
    _stream.flush()
    faulthandler.enable(file=_stream, all_threads=True)
    previous = sys.excepthook

    def report(kind, value, traceback):
        import traceback as traceback_module

        traceback_module.print_exception(kind, value, traceback, file=_stream)
        _stream.flush()
        previous(kind, value, traceback)

    sys.excepthook = report
    handler = logging.StreamHandler(_stream)
    handler.setLevel(logging.ERROR)
    logging.getLogger().addHandler(handler)
