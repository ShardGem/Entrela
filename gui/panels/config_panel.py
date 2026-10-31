"""Guided and advanced presentations of the SAME controls and domain configuration."""
from PySide6.QtCore import Signal,QSignalBlocker
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QScrollArea,
    QPushButton,QLabel,QSpinBox,QDoubleSpinBox,QComboBox,QCheckBox,QLineEdit)
from core.types import ExperimentConfig,SystemConfig,SimulationProtocol,NoiseConfig

SECTIONS=(
    ("system","Sistema","Escolha de 1 a 6 qubits e um estado inicial. Bell requer dois qubits."),
    ("hamiltonian","Hamiltoniano","Ising usa H=+J ΣZZ+h ΣX. J positivo favorece antialinhamento no termo ZZ."),
    ("evolution","Evolução","O tempo é adimensional, com ℏ=1. Mais passos reduzem erro de aproximação, mas adicionam portas."),
    ("noise","Ruído","O simulador usa matrizes densidade para representar o ensemble ruidoso. T₂ deve ser ≤ 2T₁."),
    ("execution","Execução","Shots são amostras de medição. A semente permite reproduzir a amostragem na mesma versão."),
)

class ConfigPanel(QWidget):
    simulacao_acionada=Signal()
    ajuda_acionada=Signal(str)
    parametros_alterados=Signal()
    mode_changed=Signal(str)
    section_changed=Signal(str)

    def __init__(self,parent=None):
        super().__init__(parent)
        self.current_mode,self.current_section="guided","system"
        root=QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        self.mode_combo=QComboBox()
        self.mode_combo.addItem("Guiado — aprenda enquanto configura","guided")
        self.mode_combo.addItem("Avançado — todos os parâmetros","advanced")
        root.addWidget(self.mode_combo)
        nav=QHBoxLayout()
        self.section_buttons={}
        for key,title,_ in SECTIONS:
            button=QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(lambda _,k=key:self.set_section(k))
            nav.addWidget(button)
            self.section_buttons[key]=button
        root.addLayout(nav)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        container=QWidget()
        body=QVBoxLayout(container)
        self.sections={}
        self.descriptions=[]
        forms={}
        for key,title,description in SECTIONS:
            widget=QWidget()
            layout=QVBoxLayout(widget)
            heading=QLabel(title)
            heading.setObjectName("SectionTitle")
            layout.addWidget(heading)
            explanation=QLabel(description)
            explanation.setWordWrap(True)
            explanation.setObjectName("LeadText")
            layout.addWidget(explanation)
            self.descriptions.append(explanation)
            form=QFormLayout()
            layout.addLayout(form)
            forms[key]=form
            self.sections[key]=widget
            body.addWidget(widget)
        def spin(name,label,key,lo,hi,value,integer=False,step=.1,suffix=""):
            widget=QSpinBox() if integer else QDoubleSpinBox()
            if not integer:widget.setDecimals(6)
            widget.setRange(lo,hi)
            widget.setValue(value)
            widget.setSingleStep(int(step) if integer else step)
            widget.setSuffix(suffix)
            widget.setAccessibleName(label)
            setattr(self,name,widget)
            forms[key].addRow(self._help(label),widget)
            return widget
        spin("spin_qubits","Qubits","system",1,6,2,True,1)
        self.combo_initial=QComboBox()
        for title,value in [("|0…0⟩","zero"),("|+…+⟩","plus"),("Bell (2 qubits)","bell")]:
            self.combo_initial.addItem(title,value)
        forms["system"].addRow(self._help("Estado inicial"),self.combo_initial)
        self.combo_ham=QComboBox()
        self.combo_ham.addItems(["Ising","Heisenberg","XY","XXZ"])
        forms["hamiltonian"].addRow(self._help("Hamiltoniano"),self.combo_ham)
        spin("spin_J","J — acoplamento","hamiltonian",-5.,5.,1.)
        spin("spin_h","h — campo","hamiltonian",-5.,5.,.5)
        self.check_periodic=QCheckBox("Condições periódicas")
        forms["hamiltonian"].addRow(self.check_periodic)
        spin("spin_tempo","Tempo total (ℏ=1)","evolution",.001,10.,1.)
        spin("spin_passos","Passos Trotter","evolution",1,200,4,True,1)
        self.combo_order=QComboBox()
        for order in (2,4):self.combo_order.addItem(str(order),order)
        forms["evolution"].addRow(self._help("Ordem Suzuki"),self.combo_order)
        self.check_snaps=QCheckBox("Salvar estados ao longo do tempo")
        forms["evolution"].addRow(self.check_snaps)
        self.check_ruido=QCheckBox("Ativar ruído")
        self.check_ruido.setChecked(True)
        forms["noise"].addRow(self.check_ruido)
        self.combo_modelo=QComboBox()
        self.combo_modelo.addItems(["Despolarizador","Térmico (T1/T2)"])
        forms["noise"].addRow(self._help("Modelo de ruído"),self.combo_modelo)
        spin("spin_p1","Despolarização 1q","noise",0.,1.,.01,step=.005)
        spin("spin_p2","Despolarização 2q","noise",0.,1.,.05,step=.01)
        spin("spin_t1","T₁","noise",.001,1000.,50.,suffix=" µs")
        spin("spin_t2","T₂","noise",.001,2000.,30.,suffix=" µs")
        self.validation_message=QLabel()
        self.validation_message.setWordWrap(True)
        forms["noise"].addRow(self.validation_message)
        self.btn_fix_t2=QPushButton("Usar o máximo permitido para T₂")
        self.btn_fix_t2.clicked.connect(lambda:self.spin_t2.setValue(2*self.spin_t1.value()))
        forms["noise"].addRow(self.btn_fix_t2)
        spin("spin_shots","Shots","execution",1,1_000_000,8192,True,1024)
        self.input_seed=QLineEdit("42")
        self.input_seed.setPlaceholderText("Automática (campo vazio)")
        forms["execution"].addRow(self._help("Semente"),self.input_seed)
        body.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll,1)
        bottom=QHBoxLayout()
        self.btn_back=QPushButton("Anterior")
        self.btn_next=QPushButton("Próxima etapa")
        self.btn_back.clicked.connect(lambda:self._step(-1))
        self.btn_next.clicked.connect(lambda:self._step(1))
        bottom.addWidget(self.btn_back)
        bottom.addWidget(self.btn_next)
        root.addLayout(bottom)
        self.btn_executar=QPushButton("Executar simulação")
        self.btn_executar.setObjectName("PrimaryButton")
        self.btn_executar.clicked.connect(self.simulacao_acionada.emit)
        root.addWidget(self.btn_executar)
        self.mode_combo.currentIndexChanged.connect(lambda:self.set_mode(self.mode_combo.currentData()))
        for widget in self.findChildren(QSpinBox)+self.findChildren(QDoubleSpinBox):
            widget.valueChanged.connect(self._changed)
        for widget in (self.combo_initial,self.combo_ham,self.combo_order,self.combo_modelo):
            widget.currentIndexChanged.connect(self._changed)
        for widget in (self.check_periodic,self.check_snaps,self.check_ruido):
            widget.toggled.connect(self._changed)
        self.input_seed.textChanged.connect(self._changed)
        self._changed()
        self._present()

    def _help(self,text):
        widget=QWidget()
        layout=QHBoxLayout(widget)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(QLabel(text))
        button=QPushButton("?")
        button.setObjectName("HelpButton")
        button.setFixedSize(26,26)
        button.setAccessibleName("Ajuda: "+text)
        button.clicked.connect(lambda:self.ajuda_acionada.emit(text))
        layout.addWidget(button)
        return widget

    def set_mode(self,mode):
        if mode not in ("guided","advanced"):raise ValueError("Modo inválido")
        changed=mode!=self.current_mode
        self.current_mode=mode
        blocker=QSignalBlocker(self.mode_combo)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(mode))
        del blocker
        self._present()
        if changed:self.mode_changed.emit(mode)

    def set_section(self,key):
        if key not in self.sections:raise ValueError("Etapa inválida")
        self.current_section=key
        self._present()
        self.section_changed.emit(key)

    def _step(self,delta):
        keys=[x[0] for x in SECTIONS]
        self.set_section(keys[max(0,min(len(keys)-1,keys.index(self.current_section)+delta))])

    def _present(self):
        for key,widget in self.sections.items():
            widget.setVisible(self.current_mode=="advanced" or key==self.current_section)
            self.section_buttons[key].setChecked(key==self.current_section)
        for label in self.descriptions:label.setVisible(self.current_mode=="guided")
        self.btn_back.setVisible(self.current_mode=="guided")
        self.btn_next.setVisible(self.current_mode=="guided")
        self.btn_back.setEnabled(self.current_section!="system")
        self.btn_next.setEnabled(self.current_section!="execution")

    def _noise_config(self):
        return NoiseConfig(self.check_ruido.isChecked(),"Termico" if self.combo_modelo.currentIndex() else "Despolarizador",
                           self.spin_p1.value(),self.spin_p2.value(),self.spin_t1.value(),self.spin_t2.value())

    def _changed(self,*_):
        self.spin_h.setEnabled(self.combo_ham.currentText()=="Ising")
        noise=self._noise_config()
        thermal=noise.enabled and noise.kind=="Termico"
        for widget in (self.spin_t1,self.spin_t2):widget.setEnabled(thermal)
        for widget in (self.spin_p1,self.spin_p2):widget.setEnabled(noise.enabled and not thermal)
        try:noise.validate();message=""
        except ValueError as exc:message=str(exc)
        self.validation_message.setText(message)
        self.btn_fix_t2.setVisible(thermal and noise.t2_us>2*noise.t1_us)
        self.section_buttons["noise"].setToolTip(message or "Modelo fisicamente válido")
        self.parametros_alterados.emit()

    def get_config(self):
        seed=self.input_seed.text().strip()
        if seed and (not seed.isascii() or not seed.isdecimal()):raise ValueError("Semente deve ser um inteiro de 0 a 4294967295")
        config=ExperimentConfig(
            SystemConfig(self.spin_qubits.value(),self.combo_ham.currentText(),self.spin_J.value(),
                         self.spin_h.value(),self.check_periodic.isChecked(),self.combo_initial.currentData()),
            SimulationProtocol(self.spin_tempo.value(),self.spin_passos.value(),self.check_snaps.isChecked(),
                               self.combo_order.currentData()),self._noise_config(),self.spin_shots.value(),
            int(seed) if seed else None)
        config.validate()
        return config

    def load_config(self,config):
        config.validate()
        controls=self.findChildren(QSpinBox)+self.findChildren(QDoubleSpinBox)+self.findChildren(QComboBox)+self.findChildren(QCheckBox)+[self.input_seed]
        blockers=[QSignalBlocker(w) for w in controls]
        for widget,value in [
            (self.spin_qubits,config.system.num_qubits),(self.spin_J,config.system.J),(self.spin_h,config.system.h),
            (self.spin_tempo,config.protocol.total_time),(self.spin_passos,config.protocol.trotter_steps),
            (self.spin_shots,config.shots),(self.spin_p1,config.noise.p1),(self.spin_p2,config.noise.p2),
            (self.spin_t1,config.noise.t1_us),(self.spin_t2,config.noise.t2_us)]:
            widget.setRange(min(widget.minimum(),value),max(widget.maximum(),value))
            widget.setValue(value)
        self.combo_ham.setCurrentText("Ising" if config.system.hamiltonian=="Custom" else config.system.hamiltonian)
        self.combo_initial.setCurrentIndex(self.combo_initial.findData(config.system.initial_state))
        self.check_periodic.setChecked(config.system.periodic)
        self.combo_order.setCurrentIndex(self.combo_order.findData(config.protocol.trotter_order))
        self.check_snaps.setChecked(config.protocol.save_snapshots)
        self.check_ruido.setChecked(config.noise.enabled)
        self.combo_modelo.setCurrentIndex(1 if config.noise.kind=="Termico" else 0)
        self.input_seed.setText("" if config.seed is None else str(config.seed))
        del blockers
        self._changed()

    def coletar_tudo(self):
        return {"qubits":self.spin_qubits.value(),"hamiltoniano":self.combo_ham.currentText(),
                "J":self.spin_J.value(),"h":self.spin_h.value(),"periodic":self.check_periodic.isChecked(),
                "tempo":self.spin_tempo.value(),"passos":self.spin_passos.value(),
                "salvar_snaps":self.check_snaps.isChecked(),"ruido_ativo":self.check_ruido.isChecked(),
                "modelo_ruido":self.combo_modelo.currentText(),"p1":self.spin_p1.value(),"p2":self.spin_p2.value(),
                "t1":self.spin_t1.value(),"t2":self.spin_t2.value(),"shots":self.spin_shots.value(),
                "seed":self.input_seed.text()}
