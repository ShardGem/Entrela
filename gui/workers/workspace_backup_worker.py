"""Read, hash and stage workspace archives without blocking the interface."""
from PySide6.QtCore import QThread, Signal
from core.simulation import SimulationCancelled
from data.workspace_backup import create_workspace_backup, prepare_workspace_restore


class WorkspaceBackupWorker(QThread):
    completed = Signal(object)
    progress = Signal(int)
    cancelled = Signal()
    error = Signal(str)

    def __init__(self, mode, directory, archive, preferences=None, parent=None):
        super().__init__(parent)
        if mode not in ("export", "restore"):
            raise ValueError("Operação de backup desconhecida")
        self.mode, self.directory, self.archive = mode, directory, archive
        self.preferences = preferences or {}
        self.config = None

    def run(self):
        prepared = None
        try:
            callbacks = dict(progress=self.progress.emit, is_cancelled=self.isInterruptionRequested)
            if self.mode == "export":
                result = create_workspace_backup(self.directory, self.archive, self.preferences, **callbacks)
            else:
                result = prepared = prepare_workspace_restore(self.archive, self.directory, **callbacks)
            if self.isInterruptionRequested() and self.mode == "restore":
                prepared.abort()
                self.cancelled.emit()
            else:
                self.completed.emit(result)
        except SimulationCancelled:
            if prepared:
                prepared.abort()
            self.cancelled.emit()
        except Exception as exc:
            if prepared:
                prepared.abort()
            self.error.emit("Não foi possível concluir o backup: " + str(exc))
