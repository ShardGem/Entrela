"""Prepare report plots and numerical tables outside the GUI thread."""

from PySide6.QtCore import QThread, Signal
from core.report import report_html


class ReportWorker(QThread):
    completed = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self, experiment, analysis=None, annotation=None, parent=None):
        super().__init__(parent)
        self.config = experiment.config
        self.experiment = experiment
        self.analysis = analysis
        self.annotation = annotation

    def run(self):
        try:
            self.progress.emit(5)
            if self.isInterruptionRequested():
                self.cancelled.emit()
                return
            html = report_html(self.experiment, self.analysis, self.annotation)
            if self.isInterruptionRequested():
                self.cancelled.emit()
                return
            self.progress.emit(100)
            self.completed.emit(html)
        except Exception as exc:
            self.error.emit("Não foi possível preparar o relatório: " + str(exc))
