from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QBoxLayout

from gui.widgets.job_monitor import JobMonitor


def test_completion_actions_stay_reachable_with_large_text(qt_app):
    monitor = JobMonitor()
    font = QFont(monitor.font())
    font.setPixelSize(24)
    monitor.setFont(font)
    monitor.resize(650, 220)
    opened = []
    monitor.open_requested.connect(opened.append)
    monitor.completed_result('saved-run', 'Investigação de ruído e passos de evolução')
    qt_app.processEvents()
    assert monitor._layout.direction() == QBoxLayout.TopToBottom
    for button in (monitor.open_result, monitor.dismiss):
        point = button.mapTo(monitor, button.rect().bottomRight())
        assert monitor.rect().contains(point)
    monitor.open_result.setFocus(Qt.TabFocusReason)
    assert monitor.open_result.hasFocus()
    monitor.open_result.click()
    assert opened == ['saved-run']
    monitor.dismiss.click()
    assert monitor.isHidden()
    monitor.close()


def test_running_monitor_reflows_without_losing_progress_or_cancel(qt_app):
    monitor = JobMonitor()
    font = QFont(monitor.font())
    font.setPixelSize(24)
    monitor.setFont(font)
    monitor.resize(1200, 130)
    cancelled = []
    monitor.cancel_requested.connect(lambda: cancelled.append(True))
    monitor.start('Simulação', 'Modelo de Ising')
    monitor.set_progress(37)
    qt_app.processEvents()
    assert monitor._layout.direction() == QBoxLayout.LeftToRight
    monitor.resize(420, 180)
    qt_app.processEvents()
    assert monitor._layout.direction() == QBoxLayout.TopToBottom
    assert monitor.progress.value() == 37
    monitor.cancel.click()
    assert cancelled == [True]
    monitor.cancelling()
    assert not monitor.cancel.isEnabled()
    monitor.finish()
    assert monitor.isHidden()
    monitor.close()
