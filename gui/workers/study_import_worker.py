"""Read, hash and stage study packages away from the Qt GUI thread."""
from PySide6.QtCore import QThread, Signal
from core.simulation import SimulationCancelled
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig
from data.study_package import prepare_study_import


class StudyImportWorker(QThread):
    completed = Signal(object)
    cancelled = Signal()
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, path, repository, parent=None):
        super().__init__(parent)
        self.path, self.repository = path, repository
        self.config = ExperimentConfig(SystemConfig(), SimulationProtocol(), NoiseConfig(False))

    def run(self):
        prepared = None
        try:
            prepared = prepare_study_import(self.path, self.repository, progress=self.progress.emit,
                                           is_cancelled=self.isInterruptionRequested)
            if self.isInterruptionRequested():
                prepared.abort()
                self.cancelled.emit()
            else:
                self.completed.emit(prepared)
        except SimulationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            if prepared:
                prepared.abort()
            self.error.emit("Não foi possível importar o estudo; dados anteriores preservados: " + str(exc))
