from PySide6.QtCore import QThread, Signal
from core.comparison import prepare_comparison
from core.simulation import SimulationCancelled


class ComparisonWorker(QThread):
    completed=Signal(object)
    error=Signal(str)
    progress=Signal(int)
    cancelled=Signal()

    def __init__(self,repository,identifiers,config,parent=None):
        super().__init__(parent)
        self.repository=repository
        self.identifiers=identifiers
        self.config=config

    def run(self):
        try:
            experiments=[]
            for identifier in self.identifiers:
                if self.isInterruptionRequested():
                    raise SimulationCancelled()
                experiments.append(self.repository.load(identifier))
            result=prepare_comparison(experiments,self.progress.emit,self.isInterruptionRequested)
            if self.isInterruptionRequested():
                raise SimulationCancelled()
            self.completed.emit(result)
        except SimulationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit("Não foi possível preparar a comparação: "+str(exc))
