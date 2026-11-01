from PySide6.QtCore import QThread, Signal


class StorageWorker(QThread):
    completed = Signal(str)
    error = Signal(str)

    def __init__(self, repository, experiment, parent=None):
        super().__init__(parent)
        self.repository = repository
        self.experiment = experiment

    def run(self):
        try:
            self.repository.save(self.experiment)
            self.completed.emit(self.experiment.id)
        except Exception as exc:
            self.error.emit(str(exc))
