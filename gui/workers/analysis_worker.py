from PySide6.QtCore import QThread, Signal
from core.analysis import temporal_analysis, convergence_analysis, parameter_sweep
from core.simulation import SimulationCancelled
from core.benchmark import mitigation_benchmark
from core.study import trotter_noise_study


class AnalysisWorker(QThread):
    completed = Signal(object)
    error = Signal(str)
    cancelled = Signal()
    progress = Signal(int)

    def __init__(self, config, kind, source=None, options=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.kind = kind
        self.source = source
        self.options = options or {}

    def run(self):
        try:
            callback = {
                "temporal": temporal_analysis,
                "convergence": convergence_analysis,
                "sweep": parameter_sweep,
                "mitigation_benchmark": mitigation_benchmark,
                "trotter_noise": trotter_noise_study,
            }[self.kind]
            result = callback(
                self.source if self.kind in ("temporal", "mitigation_benchmark", "trotter_noise") else self.config,
                **self.options,
                progress=self.progress.emit,
                is_cancelled=self.isInterruptionRequested,
            )
            if self.isInterruptionRequested():
                raise SimulationCancelled()
            self.completed.emit(result)
        except SimulationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit(str(exc))
