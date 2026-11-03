from PySide6.QtCore import QThread,Signal
from core.documentation import export_documentation,export_animation,export_pdf
from core.simulation import SimulationCancelled
from data.analyses import load_analysis


class DocumentationWorker(QThread):
    completed=Signal(str)
    progress=Signal(int)
    cancelled=Signal()
    error=Signal(str)

    def __init__(self,experiments,path,kind,repository=None,annotations=None,protocols=(),
                 include_analyses=True,include_gif=True,max_frames=30,frame_ms=350,parent=None,*,live_analyses=()):
        super().__init__(parent)
        self.experiments=experiments
        self.config=experiments[0].config
        self.path=path
        self.kind=kind
        self.repository=repository
        self.annotations=annotations or {}
        self.protocols=protocols
        self.include_analyses=include_analyses
        self.include_gif=include_gif
        self.max_frames=max_frames
        self.frame_ms=frame_ms
        self.live_analyses=live_analyses

    def run(self):
        try:
            analyses=[]
            if self.include_analyses and self.repository is not None and self.kind!="gif":
                for exp in self.experiments:
                    for path in sorted((self.repository.base_dir/".analyses"/exp.id).glob("*.json")):
                        if self.isInterruptionRequested():
                            raise SimulationCancelled()
                        analyses.append(load_analysis(path,exp.id))
            if self.include_analyses:
                from data.analyses import validate_analysis
                ids={e.id for e in self.experiments}
                existing={data.get("analysis_id") or data.get("id") for data in analyses}
                for data in self.live_analyses:
                    identity=data.get("analysis_id") or data.get("id")
                    if data.get("source_id") in ids and (identity is None or identity not in existing):
                        validate_analysis(data,data["source_id"])
                        analyses.append(data)
                        existing.add(identity)
            callbacks=dict(progress=self.progress.emit,is_cancelled=self.isInterruptionRequested)
            if self.kind=="gif":
                export_animation(self.experiments,self.path,self.max_frames,self.frame_ms,**callbacks)
            elif self.kind=="pdf":
                export_pdf(self.experiments,self.path,analyses,self.annotations,**callbacks)
            else:
                export_documentation(self.experiments,self.path,analyses,self.annotations,self.protocols,
                                     self.include_gif,self.max_frames,self.frame_ms,**callbacks)
            self.completed.emit(str(self.path))
        except SimulationCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.error.emit("Falha ao documentar; dados de origem preservados: "+str(exc))
