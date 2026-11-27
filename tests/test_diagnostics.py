"""Installed desktops may launch from directories they cannot write."""
import logging
from pathlib import Path
import subprocess
import sys

import pytest

from gui import diagnostics


@pytest.fixture
def diagnostic_session(monkeypatch, tmp_path):
    # Avoid replacing pytest's native fatal-error handler in this process.
    enabled = []
    monkeypatch.setattr(diagnostics.faulthandler, "enable", lambda **kw: enabled.append(kw))
    monkeypatch.setattr(diagnostics.faulthandler, "disable", lambda: None)
    directory = tmp_path / "user-data" / "Entrela" / "logs"
    monkeypatch.setattr(diagnostics, "diagnostics_directory", lambda: directory)
    yield directory, enabled
    diagnostics._close_diagnostics()


def test_logs_use_user_directory_without_writing_to_launch_folder(diagnostic_session, monkeypatch, tmp_path):
    directory, enabled = diagnostic_session
    launch = tmp_path / "installation"
    launch.mkdir()
    monkeypatch.chdir(launch)
    assert diagnostics.enable_diagnostics() == directory
    assert not (launch / "logs").exists()
    native = directory / "entrela-crash.log"
    assert "Python:" in native.read_text(encoding="utf-8")
    assert "PySide6:" in native.read_text(encoding="utf-8")
    assert enabled == [{"file": diagnostics._stream, "all_threads": True}]
    logging.getLogger("entrela.worker").error("Falha de gravação de teste")
    assert "Falha de gravação de teste" in (directory / "entrela.log").read_text(encoding="utf-8")


def test_repeated_setup_is_idempotent_and_keeps_previous_exception_hook(diagnostic_session, monkeypatch):
    directory, enabled = diagnostic_session
    previous_calls = []
    monkeypatch.setattr(sys, "excepthook", lambda *args: previous_calls.append(args))
    diagnostics.enable_diagnostics()
    stream = diagnostics._stream
    hook = sys.excepthook
    diagnostics.enable_diagnostics()
    assert len(enabled) == 1
    assert diagnostics._stream is stream
    assert sys.excepthook is hook
    assert logging.getLogger().handlers.count(diagnostics._handler) == 1
    error = RuntimeError("Falha não tratada de teste")
    hook(type(error), error, None)
    assert previous_calls == [(RuntimeError, error, None)]
    assert "Falha não tratada de teste" in (directory / "entrela.log").read_text(encoding="utf-8")


def test_log_rotation_keeps_native_stream_open_and_limits_python_backups(diagnostic_session, monkeypatch):
    directory, enabled = diagnostic_session
    monkeypatch.setattr(diagnostics, "MAX_LOG_BYTES", 256)
    directory.mkdir(parents=True)
    native = directory / "entrela-crash.log"
    native.write_text("histórico" * 100, encoding="utf-8")
    diagnostics.enable_diagnostics()
    assert native.with_name(native.name + ".1").read_text(encoding="utf-8") == "histórico" * 100
    for number in range(30):
        logging.getLogger("entrela.worker").error("evento %s %s", number, "x" * 100)
    assert (directory / "entrela.log.3").exists()
    assert not (directory / "entrela.log.4").exists()
    assert "evento 29" in (directory / "entrela.log").read_text(encoding="utf-8")
    assert not diagnostics._stream.closed
    diagnostics._stream.write("native-handler-still-open\n")
    diagnostics._stream.flush()
    assert "native-handler-still-open" in native.read_text(encoding="utf-8")


def test_unavailable_log_storage_does_not_replace_hooks(diagnostic_session):
    directory, enabled = diagnostic_session
    directory.parent.mkdir(parents=True)
    directory.write_text("a file occupies the path", encoding="utf-8")
    original_hook = sys.excepthook
    original_handlers = list(logging.getLogger().handlers)
    assert diagnostics.enable_diagnostics() is None
    assert sys.excepthook is original_hook
    assert logging.getLogger().handlers == original_handlers
    assert not enabled


def test_failed_initial_write_does_not_prevent_startup(diagnostic_session, monkeypatch):
    _, enabled = diagnostic_session
    original_hook = sys.excepthook
    original_handlers = list(logging.getLogger().handlers)
    def fail(stream):
        raise OSError("Disco cheio")
    monkeypatch.setattr(diagnostics, "_write_launch_metadata", fail)
    assert diagnostics.enable_diagnostics() is None
    assert sys.excepthook is original_hook
    assert logging.getLogger().handlers == original_handlers
    assert not enabled
    assert diagnostics._stream is None


def test_default_path_is_user_scoped(monkeypatch, tmp_path):
    monkeypatch.setattr(diagnostics.QStandardPaths, "writableLocation", lambda kind: str(tmp_path / "profile"))
    assert diagnostics.diagnostics_directory() == tmp_path / "profile" / "Entrela" / "logs"
    monkeypatch.setattr(diagnostics.QStandardPaths, "writableLocation", lambda kind: "")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    assert diagnostics.diagnostics_directory() == tmp_path / "home" / ".entrela" / "logs"


def test_native_and_unhandled_exception_evidence_in_real_process(tmp_path):
    code = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from gui import diagnostics
diagnostics.diagnostics_directory = lambda: Path(sys.argv[2])
diagnostics.enable_diagnostics()
diagnostics.enable_diagnostics()
diagnostics.faulthandler.dump_traceback(file=diagnostics._stream)
raise RuntimeError('diagnostic-process-check')
"""
    folder = tmp_path / "profile" / "logs"
    result = subprocess.run(
        [sys.executable, "-c", code, str(Path(diagnostics.__file__).resolve().parents[1]), str(folder)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "diagnostic-process-check" in result.stderr
    assert "diagnostic-process-check" in (folder / "entrela.log").read_text(encoding="utf-8")
    native = (folder / "entrela-crash.log").read_text(encoding="utf-8")
    assert "Current thread" in native
    assert native.count("Entrela launch") == 1
    assert not (tmp_path / "logs").exists()
