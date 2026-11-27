"""Load one full scientific record on demand, without decoding the history."""
from PySide6.QtCore import QThread,Signal


class DetailWorker(QThread):
    completed=Signal(object)
    error=Signal(str)
    cancelled=Signal()
    progress=Signal(int)

    def __init__(self,repository,identifier,config,parent=None):
        super().__init__(parent)
        self.repository=repository
        self.identifier=identifier
        self.config=config

    def run(self):
        try:
            if self.isInterruptionRequested():
                self.cancelled.emit()
                return
            self.progress.emit(10)
            record=self.repository.load(self.identifier)
            if self.isInterruptionRequested():
                self.cancelled.emit()
                return
            self.progress.emit(100)
            self.completed.emit(record)
        except Exception as exc:
            self.error.emit("Não foi possível carregar os detalhes: "+str(exc))
