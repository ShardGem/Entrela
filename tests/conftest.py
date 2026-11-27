import gc
import os,tempfile
from pathlib import Path
import pytest
cache=Path(tempfile.gettempdir())/"entrela-test-cache"
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ.setdefault("MPLCONFIGDIR",str(cache/"matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME",str(cache))
os.environ.setdefault("XDG_CONFIG_HOME",str(cache/"config"))
os.environ.setdefault("OMP_NUM_THREADS","2")
os.environ.setdefault("OPENBLAS_NUM_THREADS","2")
for name in ("MPLCONFIGDIR","XDG_CACHE_HOME","XDG_CONFIG_HOME"):Path(os.environ[name]).mkdir(parents=True,exist_ok=True)
@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication
    app=QApplication.instance() or QApplication([])
    yield app
    app.closeAllWindows()
    app.processEvents()
@pytest.fixture
def window(qt_app,tmp_path,monkeypatch):
    import sys
    from PySide6.QtCore import QSettings
    from gui.main_window import MainWindow
    from data.repository import ExperimentRepository
    from tests.qt_helpers import wait_until
    errors=[]
    monkeypatch.setattr(sys,"excepthook",lambda *args:errors.append(args))
    widget=MainWindow(ExperimentRepository(tmp_path/"runs"),QSettings(str(tmp_path/"prefs.ini"),QSettings.IniFormat))
    widget.show()
    qt_app.processEvents()
    yield widget
    if widget._current_worker:
        widget._cancel_simulation()
        wait_until(lambda:widget._current_worker is None)
    widget._unsaved_result=False
    widget.close()
    widget.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qt_app.processEvents()
    gc.collect()
    assert not errors,errors
