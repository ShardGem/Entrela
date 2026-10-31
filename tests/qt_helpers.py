from PySide6.QtCore import QEventLoop,QTimer
def wait_until(predicate,timeout=15000):
    if predicate():return
    loop=QEventLoop()
    poll,deadline=QTimer(),QTimer()
    deadline.setSingleShot(True)
    def check():
        if predicate():loop.quit()
    poll.timeout.connect(check)
    deadline.timeout.connect(loop.quit)
    poll.start(5)
    deadline.start(timeout)
    loop.exec()
    poll.stop()
    deadline.stop()
    assert predicate(),"GUI operation timed out"
def execute(window):
    errors=[]
    window.page_simulation.btn_run.click()
    worker=window._current_worker
    assert worker is not None
    worker.error.connect(errors.append)
    assert not window.page_simulation.btn_run.isEnabled()
    assert not window.page_simulation.config_panel.btn_executar.isEnabled()
    wait_until(lambda:window._current_worker is None)
    assert not errors,errors
    assert window.page_simulation.btn_run.isEnabled()
    return window._current_experiment
