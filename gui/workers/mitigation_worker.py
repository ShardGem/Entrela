from time import perf_counter
from PySide6.QtCore import QThread,Signal
from core.circuits import build_circuit
from core.noise import build_noise_model
from core.mitigation import run_zne
from core.simulation import SimulationCancelled

class MitigationWorker(QThread):
    completed=Signal(dict)
    progress=Signal(int)
    error=Signal(str)
    cancelled=Signal()
    def __init__(self,config,qubit=0,method="linear",shots=8192,parent=None):
        super().__init__(parent)
        self.config,self.qubit,self.method,self.shots=config,qubit,method,shots
    def run(self):
        try:
            self.config.validate()
            started=perf_counter()
            s,p=self.config.system,self.config.protocol
            circuit,_=build_circuit(s.num_qubits,s.hamiltonian,s.J,s.h,s.periodic,
                p.total_time,p.trotter_steps,False,initial_state=s.initial_state,
                trotter_order=p.trotter_order,measure=False)
            result=run_zne(circuit,build_noise_model(self.config.noise),shots=self.shots,
                method=self.method,seed=self.config.seed,qubit=self.qubit,
                progress=self.progress.emit,is_cancelled=self.isInterruptionRequested)
            result["duration_s"]=perf_counter()-started
            if self.isInterruptionRequested():self.cancelled.emit()
            else:self.completed.emit(result)
        except SimulationCancelled:self.cancelled.emit()
        except Exception as exc:self.error.emit(f"{type(exc).__name__}: {exc}")
