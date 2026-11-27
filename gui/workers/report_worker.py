"""Prepare report plots and numerical tables outside the GUI thread."""

from PySide6.QtCore import QThread, Signal
from core.report import report_html
from core.documentation import export_pdf
from core.simulation import SimulationCancelled


class ReportWorker(QThread):
    completed = Signal(str)
    error = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self, experiment, analysis=None, annotation=None, parent=None, *,
                 pdf_path=None, options=None, raster_dpi=300):
        super().__init__(parent)
        self.config = experiment.config
        self.experiment = experiment
        self.analysis = analysis
        self.annotation = annotation
        self.pdf_path = pdf_path
        self.options = options
        self.raster_dpi = raster_dpi

    def run(self):
        try:
            self.progress.emit(5)
            if self.isInterruptionRequested():
                self.cancelled.emit()
                return
            if self.pdf_path is not None:
                export_pdf([self.experiment], self.pdf_path,
                           analyses=[self.analysis] if self.analysis else (),
                           annotations={self.experiment.id: self.annotation or {}},
                           options=self.options, raster_dpi=self.raster_dpi,
                           progress=self.progress.emit,
                           is_cancelled=self.isInterruptionRequested)
                self.completed.emit(str(self.pdf_path))
                return
            html = report_html(self.experiment, self.analysis, self.annotation)
            if self.isInterruptionRequested():
                self.cancelled.emit()
                return
            self.progress.emit(100)
            self.completed.emit(html)
        except SimulationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit("Não foi possível preparar o relatório: " + str(exc))
