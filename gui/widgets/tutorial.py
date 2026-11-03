"""Action-gated Bell tutorial; only real workspace state can unlock progress."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QProgressBar
STEPS=(
    ("Dois qubits","Altere o número de qubits para 2.","system"),
    ("Prepare Bell","Escolha Bell em Estado inicial.","system"),
    ("Referência ideal","Desative o ruído e mantenha J=0 e h=0.","noise"),
    ("Registre a evolução","Ative Salvar estados ao longo do tempo.","evolution"),
    ("Execute","Clique em Executar simulação e aguarde o resultado real.","execution"),
    ("Interprete","Abra Resultados. Observe a distribuição 00/11 e a interpretação.","execution"),
    ("Reabra","Abra Histórico, use Visualizar para consultar a execução deste tutorial e depois Abrir para reabrir seus resultados.","execution"))

class BellTutorial(QWidget):
    section_requested=Signal(str)
    progress_changed=Signal()
    completed=Signal()
    paused=Signal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.active=False
        self.started=False
        self.finished=False
        self.step=0
        self.experiment=None
        self.config=None
        self.page=""
        self.opened_id=None
        layout=QVBoxLayout(self)
        self.progress=QProgressBar()
        self.progress.setRange(0,7)
        layout.addWidget(self.progress)
        self.title=QLabel()
        self.title.setObjectName("SectionTitle")
        self.title.setWordWrap(True)
        self.body=QLabel()
        self.body.setWordWrap(True)
        self.feedback=QLabel()
        self.feedback.setWordWrap(True)
        for w in (self.title,self.body,self.feedback):layout.addWidget(w)
        locate=QPushButton("Ir para a configuração")
        locate.clicked.connect(lambda:self.section_requested.emit(STEPS[self.step][2]))
        layout.addWidget(locate)
        row=QHBoxLayout()
        self.btn_back=QPushButton("Voltar")
        self.btn_next=QPushButton("Continuar")
        self.btn_next.setObjectName("PrimaryButton")
        self.btn_back.clicked.connect(self.back)
        self.btn_next.clicked.connect(self.advance)
        row.addWidget(self.btn_back)
        row.addWidget(self.btn_next)
        layout.addLayout(row)
        pause=QPushButton("Pausar tutorial")
        pause.clicked.connect(self.pause)
        layout.addWidget(pause)
        layout.addStretch()
        self.refresh()
    @property
    def run_id(self):return self.experiment.id if self.experiment else None
    @staticmethod
    def matches(cfg):
        return bool(cfg and cfg.system.num_qubits==2 and cfg.system.initial_state=="bell" and cfg.system.J==0
                    and cfg.system.h==0 and cfg.system.hamiltonian in ("Ising","Custom")
                    and not cfg.noise.enabled and cfg.protocol.save_snapshots)
    def start(self,step=0,experiment=None):
        self.active=True
        self.started=True
        self.finished=False
        self.step=max(0,min(int(step),6))
        self.experiment=experiment
        self.opened_id=None
        self.refresh()
        self.section_requested.emit(STEPS[self.step][2])
    def update_context(self,config,page):
        self.config,self.page=config,page
        self.refresh()
    def record_run(self,experiment):
        if self.active and self.step>=4 and not experiment.result.error and self.matches(experiment.config):
            self.experiment=experiment
            self.opened_id=None
            self.progress_changed.emit()
        self.refresh()
    def record_open(self,identifier):
        if self.active and self.step==6 and identifier==self.run_id:self.opened_id=identifier
        self.refresh()
    def ready(self):
        c=self.config
        if self.step==0:return bool(c and c.system.num_qubits==2)
        if self.step==1:return bool(c and c.system.num_qubits==2 and c.system.initial_state=="bell")
        if self.step==2:return bool(c and c.system.num_qubits==2 and c.system.initial_state=="bell"
                                    and c.system.J==0 and c.system.h==0 and not c.noise.enabled)
        if self.step==3:return self.matches(c)
        if self.step==4:return self.experiment is not None
        if self.step==5:return bool(self.experiment and self.page=="results")
        return bool(self.run_id and self.opened_id==self.run_id)
    def refresh(self):
        if self.finished:
            return
        title,body,_=STEPS[self.step]
        self.title.setText(f"{self.step+1} de 7 · {title}")
        self.body.setText(body)
        self.progress.setValue(self.step)
        self.btn_back.setEnabled(self.step>0)
        self.btn_next.setText("Concluir" if self.step==6 else "Continuar")
        self.btn_next.setEnabled(self.ready())
        if self.experiment:
            counts=self.experiment.result.counts or {}
            total=sum(counts.values())
            correlated=(counts.get("00",0)+counts.get("11",0))/total if total else 0
            self.feedback.setText(f"Seu Bell: {total} medições; {correlated:.1%} em 00 ou 11.")
        else:self.feedback.setText("Ação reconhecida." if self.ready() else "Realize a ação para continuar.")
    def advance(self):
        if not self.active or not self.ready():return
        if self.step==6:
            self.active=False
            self.finished=True
            self.progress.setValue(7)
            self.title.setText("Seu primeiro experimento está completo")
            self.body.setText("Você preparou, executou, analisou e reabriu um estado de Bell.")
            self.btn_next.setEnabled(False)
            self.completed.emit()
        else:
            self.step+=1
            self.refresh()
            self.section_requested.emit(STEPS[self.step][2])
        self.progress_changed.emit()
    def back(self):
        if self.step>0:
            self.step-=1
            self.refresh()
            self.section_requested.emit(STEPS[self.step][2])
            self.progress_changed.emit()
    def pause(self):
        self.active=False
        self.paused.emit()
        self.progress_changed.emit()
