"""A delivered result does not replace native QThread.finished."""
from PySide6.QtCore import QThread, Signal
from core.simulation import run_experiment, SimulationCancelled

class SimulationWorker(QThread):
    completed = Signal(object)
    error = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self,config,parent=None):
        super().__init__(parent)
        self.config = config

    def run(self):
        try:
            result = run_experiment(self.config,self.progress.emit,self.isInterruptionRequested)
            if self.isInterruptionRequested():
                self.cancelled.emit()
            else:
                self.completed.emit(result)
        except SimulationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")
