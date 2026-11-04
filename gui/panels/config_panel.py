"""Guided and advanced presentations of the SAME controls and domain configuration."""

from PySide6.QtCore import Signal, QSignalBlocker, QEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QScrollArea,
    QPushButton,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QLineEdit,
)
from core.types import ExperimentConfig, SystemConfig, SimulationProtocol, NoiseConfig

from gui.widgets.scientific_input import ScientificSpinBox

SECTIONS = (
    (
        "system",
        "Sistema",
        "Escolha de 1 a 6 qubits e um estado inicial. Bell requer dois qubits.",
    ),
    (
        "hamiltonian",
        "Hamiltoniano",
        "Ising usa H=+J ΣZZ+h ΣX. J positivo favorece antialinhamento no termo ZZ.",
    ),
    (
        "evolution",
        "Evolução",
        "O tempo é adimensional, com ℏ=1. Mais passos reduzem erro de aproximação, mas adicionam portas.",
    ),
    (
        "noise",
        "Ruído",
        "O simulador usa matrizes densidade para representar o ensemble ruidoso. T₂ deve ser ≤ 2T₁.",
    ),
    (
        "execution",
        "Execução",
        "Shots são amostras de medição. A semente permite reproduzir a amostragem na mesma versão.",
    ),
)

# Short explanations are shared by field tooltips and keyboard-accessible help.
# They describe the selected configuration; no simulation runs while editing.
PARAMETER_HELP = {
    "Qubits": "Quantidade de sistemas de dois níveis. Cada qubit pode ser medido como 0 ou 1; o espaço de estados dobra a cada qubit.",
    "Estado inicial": "Ponto de partida antes da evolução: zero, superposição uniforme ou o par emaranhado de Bell.",
    "Hamiltoniano": "Modelo que define as interações e a evolução do sistema. Custom mantém compatibilidade com Ising; não é um editor de Hamiltonianos.",
    "J — acoplamento": "Intensidade das interações entre vizinhos. No termo +J ZZ do Ising, J positivo favorece antialinhamento; o sinal faz parte do modelo.",
    "h — campo": "Intensidade do campo transversal no Ising. Ele pode mudar as populações da base Z. Não é aplicado aos outros modelos deste formulário.",
    "Tempo total (ℏ=1)": "Duração adimensional da evolução. Não corresponde ao tempo real de execução nem aos tempos T₁/T₂ do canal térmico.",
    "Passos Trotter": "Divide a evolução em etapas. Mais etapas podem reduzir a aproximação, mas aumentam o número de portas sujeitas ao ruído.",
    "Ordem Suzuki": "Ordem da aproximação de Suzuki–Trotter. Ordem 4 usa mais operações; sua vantagem depende do modelo e do ruído.",
    "Modelo de ruído": "Despolarizador mistura o estado; térmico descreve relaxamento e perda de coerência. São modelos educativos por porta, não calibrações de hardware.",
    "Despolarização 1q": "Parâmetro p₁ do canal despolarizador aplicado a cada porta de um qubit. Zero desliga esse canal; valores maiores aumentam a mistura.",
    "Despolarização 2q": "Parâmetro p₂ do canal despolarizador aplicado a cada porta de dois qubits. Pode ser diferente de p₁.",
    "T₁": "Tempo de relaxamento da população em microssegundos. Valores maiores significam relaxamento mais lento para a mesma duração de porta.",
    "T₂": "Tempo de perda de coerência em microssegundos. Deve satisfazer T₂ ≤ 2T₁; maior T₂ significa perda de coerência mais lenta.",
    "Shots": "Número de amostras de medição. Mais shots reduzem a flutuação das contagens, mas não corrigem ruído nem alteram as métricas calculadas do estado.",
    "Semente": "Controla a amostragem aleatória. Vazio gera uma semente registrada no resultado. Reutilizar a mesma semente não cria uma observação independente.",
}


class ConfigPanel(QWidget):
    simulacao_acionada = Signal()
    ajuda_acionada = Signal(str)
    parametros_alterados = Signal()
    mode_changed = Signal(str)
    section_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode, self.current_section = "guided", "system"
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Guiado — aprenda enquanto configura", "guided")
        self.mode_combo.addItem("Avançado — todos os parâmetros", "advanced")
        self.mode_combo.setAccessibleName("Modo de configuração")
        root.addWidget(self.mode_combo)
        self.mode_explanation = QLabel()
        self.mode_explanation.setWordWrap(True)
        self.mode_explanation.setObjectName("LeadText")
        root.addWidget(self.mode_explanation)
        self.section_nav = QWidget()
        nav = QGridLayout(self.section_nav)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(4)
        self._section_layout = nav
        self._section_columns = 0
        self.section_buttons = {}
        for key, title, _ in SECTIONS:
            button = QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(lambda _, k=key: self.set_section(k))
            nav.addWidget(button, 0, len(self.section_buttons))
            self.section_buttons[key] = button
        root.addWidget(self.section_nav)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        body = QVBoxLayout(container)
        self.sections = {}
        self.descriptions = []
        forms = {}
        for key, title, description in SECTIONS:
            widget = QWidget()
            layout = QVBoxLayout(widget)
            heading = QLabel(title)
            heading.setObjectName("SectionTitle")
            layout.addWidget(heading)
            explanation = QLabel(description)
            explanation.setWordWrap(True)
            explanation.setObjectName("LeadText")
            layout.addWidget(explanation)
            self.descriptions.append(explanation)
            form = QFormLayout()
            form.setRowWrapPolicy(QFormLayout.WrapLongRows)
            layout.addLayout(form)
            forms[key] = form
            self.sections[key] = widget
            body.addWidget(widget)

        def spin(name, label, key, lo, hi, value, integer=False, step=0.1, suffix=""):
            widget = QSpinBox() if integer else ScientificSpinBox()
            widget.setRange(lo, hi)
            widget.setValue(value)
            widget.setSingleStep(int(step) if integer else step)
            widget.setSuffix(suffix)
            widget.setAccessibleName(label)
            widget.setToolTip(PARAMETER_HELP.get(label, ""))
            widget.setWhatsThis(PARAMETER_HELP.get(label, ""))
            setattr(self, name, widget)
            forms[key].addRow(self._help(label), widget)
            return widget

        spin("spin_qubits", "Qubits", "system", 1, 6, 2, True, 1)
        self.combo_initial = QComboBox()
        for title, value in [
            ("|0…0⟩", "zero"),
            ("|+…+⟩", "plus"),
            ("Bell (2 qubits)", "bell"),
        ]:
            self.combo_initial.addItem(title, value)
        forms["system"].addRow(self._help("Estado inicial"), self.combo_initial)
        self.initial_preview = QLabel()
        self.initial_preview.setObjectName("LeadText")
        self.initial_preview.setWordWrap(True)
        self.initial_preview.setAccessibleName("Prévia descritiva do estado inicial")
        forms["system"].addRow(self.initial_preview)
        self.combo_ham = QComboBox()
        self.combo_ham.addItems(["Ising", "Heisenberg", "XY", "XXZ", "Custom"])
        forms["hamiltonian"].addRow(self._help("Hamiltoniano"), self.combo_ham)
        spin("spin_J", "J — acoplamento", "hamiltonian", -5.0, 5.0, 1.0)
        spin("spin_h", "h — campo", "hamiltonian", -5.0, 5.0, 0.5)
        self.check_periodic = QCheckBox("Condições periódicas")
        self.check_periodic.setToolTip("Fecha a cadeia ligando o último qubit ao primeiro quando há mais de dois qubits. Desmarcado mantém as extremidades abertas.")
        forms["hamiltonian"].addRow(self.check_periodic)
        spin("spin_tempo", "Tempo total (ℏ=1)", "evolution", 0.001, 10.0, 1.0)
        spin("spin_passos", "Passos Trotter", "evolution", 1, 200, 4, True, 1)
        self.combo_order = QComboBox()
        for order in (2, 4):
            self.combo_order.addItem(str(order), order)
        forms["evolution"].addRow(self._help("Ordem Suzuki"), self.combo_order)
        self.check_snaps = QCheckBox("Salvar estados ao longo do tempo")
        self.check_snaps.setToolTip("Guarda o estado inicial e o fim de cada passo Trotter para a evolução 3D e análises. Aumenta o uso de memória e o arquivo exportado.")
        forms["evolution"].addRow(self.check_snaps)
        self.check_ruido = QCheckBox("Ativar ruído")
        self.check_ruido.setToolTip("Compare uma execução ideal e outra ruidosa com os mesmos parâmetros. O ruído incide também nas portas de preparação.")
        self.check_ruido.setChecked(True)
        forms["noise"].addRow(self.check_ruido)
        self.combo_modelo = QComboBox()
        self.combo_modelo.addItems(["Despolarizador", "Térmico (T1/T2)"])
        forms["noise"].addRow(self._help("Modelo de ruído"), self.combo_modelo)
        spin("spin_p1", "Despolarização 1q", "noise", 0.0, 1.0, 0.01, step=0.005)
        spin("spin_p2", "Despolarização 2q", "noise", 0.0, 1.0, 0.05, step=0.01)
        spin("spin_t1", "T₁", "noise", 0.001, 1000.0, 50.0, suffix=" µs")
        spin("spin_t2", "T₂", "noise", 0.001, 2000.0, 30.0, suffix=" µs")
        spin("spin_gate1", "Duração de porta 1q", "noise", 0.001, 1e6, 50.0, suffix=" ns")
        spin("spin_gate2", "Duração de porta 2q", "noise", 0.001, 1e6, 50.0, suffix=" ns")
        for field in (self.spin_gate1,self.spin_gate2):
            field.setToolTip("Tempo de exposição ao canal T₁/T₂ por operação nativa. É uma hipótese do modelo, independente do tempo adimensional do Hamiltoniano e de calibração de hardware.")
        self.validation_message = QLabel()
        self.validation_message.setWordWrap(True)
        forms["noise"].addRow(self.validation_message)
        self.btn_fix_t2 = QPushButton("Usar o máximo permitido para T₂")
        self.btn_fix_t2.clicked.connect(
            lambda: self.spin_t2.setValue(2 * self.spin_t1.value())
        )
        forms["noise"].addRow(self.btn_fix_t2)
        spin("spin_shots", "Shots", "execution", 1, 1_000_000, 8192, True, 1024)
        self.input_seed = QLineEdit("42")
        self.input_seed.setPlaceholderText("Automática (campo vazio)")
        self.input_seed.setAccessibleName("Semente aleatória")
        self.input_seed.setToolTip(PARAMETER_HELP["Semente"])
        forms["execution"].addRow(self._help("Semente"), self.input_seed)
        for combo, label in ((self.combo_initial, "Estado inicial"), (self.combo_ham, "Hamiltoniano"), (self.combo_order, "Ordem Suzuki"), (self.combo_modelo, "Modelo de ruído")):
            combo.setAccessibleName(label)
            combo.setToolTip(PARAMETER_HELP[label])
            combo.setWhatsThis(PARAMETER_HELP[label])
        body.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, 1)
        bottom = QHBoxLayout()
        self.btn_back = QPushButton("Anterior")
        self.btn_next = QPushButton("Próxima etapa")
        self.btn_back.clicked.connect(lambda: self._step(-1))
        self.btn_next.clicked.connect(lambda: self._step(1))
        bottom.addWidget(self.btn_back)
        bottom.addWidget(self.btn_next)
        root.addLayout(bottom)
        self.btn_executar = QPushButton("Executar simulação")
        self.btn_executar.setObjectName("PrimaryButton")
        self.btn_executar.clicked.connect(self.simulacao_acionada.emit)
        root.addWidget(self.btn_executar)
        self.mode_combo.currentIndexChanged.connect(
            lambda: self.set_mode(self.mode_combo.currentData())
        )
        for widget in self.findChildren(QSpinBox) + self.findChildren(QDoubleSpinBox):
            widget.valueChanged.connect(self._changed)
        for widget in (
            self.combo_initial,
            self.combo_ham,
            self.combo_order,
            self.combo_modelo,
        ):
            widget.currentIndexChanged.connect(self._changed)
        for widget in (self.check_periodic, self.check_snaps, self.check_ruido):
            widget.toggled.connect(self._changed)
        self.input_seed.textChanged.connect(self._changed)
        self._changed()
        self._present()

    def _help(self, text):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(text)
        label.setWordWrap(True)
        layout.addWidget(label, 1)
        button = QPushButton("?")
        button.setObjectName("HelpButton")
        button.setFixedSize(26, 26)
        button.setAccessibleName("Ajuda: " + text)
        button.setToolTip(PARAMETER_HELP.get(text, "Abrir explicação no manual."))
        widget.setToolTip(PARAMETER_HELP.get(text, ""))
        button.clicked.connect(lambda: self.ajuda_acionada.emit(text))
        layout.addWidget(button)
        return widget

    def set_mode(self, mode):
        if mode not in ("guided", "advanced"):
            raise ValueError("Modo inválido")
        changed = mode != self.current_mode
        self.current_mode = mode
        blocker = QSignalBlocker(self.mode_combo)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(mode))
        del blocker
        self._present()
        if changed:
            self.mode_changed.emit(mode)

    def set_section(self, key):
        if key not in self.sections:
            raise ValueError("Etapa inválida")
        self.current_section = key
        self._present()
        self.section_changed.emit(key)

    def _step(self, delta):
        keys = [x[0] for x in SECTIONS]
        self.set_section(
            keys[max(0, min(len(keys) - 1, keys.index(self.current_section) + delta))]
        )

    def _present(self):
        guided = self.current_mode == "guided"
        self.section_nav.setVisible(guided)
        self.mode_explanation.setText(
            "Uma etapa por vez. Navegue livremente e use ? para entender cada parâmetro."
            if guided else
            "Visão completa por categoria. Os valores são os mesmos do modo Guiado; use ? para consultar as referências."
        )
        for key, widget in self.sections.items():
            widget.setVisible(
                self.current_mode == "advanced" or key == self.current_section
            )
            self.section_buttons[key].setChecked(key == self.current_section)
        for label in self.descriptions:
            label.setVisible(self.current_mode == "guided")
        self.btn_back.setVisible(self.current_mode == "guided")
        self.btn_next.setVisible(self.current_mode == "guided")
        self.btn_back.setEnabled(self.current_section != "system")
        self.btn_next.setEnabled(self.current_section != "execution")

    def _noise_config(self):
        return NoiseConfig(
            self.check_ruido.isChecked(),
            "Termico" if self.combo_modelo.currentIndex() else "Despolarizador",
            self.spin_p1.value(),
            self.spin_p2.value(),
            self.spin_t1.value(),
            self.spin_t2.value(),
            self.spin_gate1.value(),
            self.spin_gate2.value(),
        )

    def _changed(self, *_):
        initial = self.combo_initial.currentData()
        n = self.spin_qubits.value()
        preview = {
            "zero": f"Prévia ideal da preparação: {n} qubits em |0⟩. Antes de evoluir, uma medição em Z retorna apenas zeros.",
            "plus": "Prévia ideal da preparação: cada qubit aponta para +X na esfera de Bloch. Antes de evoluir, os resultados em Z têm probabilidades iguais.",
            "bell": "Prévia ideal da preparação: (|00⟩ + |11⟩)/√2. O par é emaranhado; cada vetor de Bloch local é nulo, embora o estado global seja puro.",
        }[initial]
        if initial == "bell" and n != 2:
            preview = "O exemplo de Bell requer exatamente dois qubits. Ajuste Qubits para 2 antes de executar."
        self.initial_preview.setText(preview)
        self.spin_h.setEnabled(self.combo_ham.currentText() in ("Ising", "Custom"))
        noise = self._noise_config()
        thermal = noise.enabled and noise.kind == "Termico"
        for widget in (self.spin_t1, self.spin_t2, self.spin_gate1, self.spin_gate2):
            widget.setEnabled(thermal)
        for widget in (self.spin_p1, self.spin_p2):
            widget.setEnabled(noise.enabled and not thermal)
        try:
            noise.validate()
            message = ""
        except ValueError as exc:
            message = str(exc)
        self.validation_message.setText(message)
        self.btn_fix_t2.setVisible(thermal and noise.t2_us > 2 * noise.t1_us)
        self.section_buttons["noise"].setToolTip(message or "Modelo fisicamente válido")
        self.parametros_alterados.emit()

    def get_config(self):
        seed = self.input_seed.text().strip()
        if seed and (not seed.isascii() or not seed.isdecimal()):
            raise ValueError("Semente deve ser um inteiro de 0 a 4294967295")
        config = ExperimentConfig(
            SystemConfig(
                self.spin_qubits.value(),
                self.combo_ham.currentText(),
                self.spin_J.value(),
                self.spin_h.value(),
                self.check_periodic.isChecked(),
                self.combo_initial.currentData(),
            ),
            SimulationProtocol(
                self.spin_tempo.value(),
                self.spin_passos.value(),
                self.check_snaps.isChecked(),
                self.combo_order.currentData(),
            ),
            self._noise_config(),
            self.spin_shots.value(),
            int(seed) if seed else None,
        )
        config.validate()
        return config

    def load_config(self, config):
        config.validate()
        controls = (
            self.findChildren(QSpinBox)
            + self.findChildren(QDoubleSpinBox)
            + self.findChildren(QComboBox)
            + self.findChildren(QCheckBox)
            + [self.input_seed]
        )
        blockers = [QSignalBlocker(w) for w in controls]
        for widget, value in [
            (self.spin_qubits, config.system.num_qubits),
            (self.spin_J, config.system.J),
            (self.spin_h, config.system.h),
            (self.spin_tempo, config.protocol.total_time),
            (self.spin_passos, config.protocol.trotter_steps),
            (self.spin_shots, config.shots),
            (self.spin_p1, config.noise.p1),
            (self.spin_p2, config.noise.p2),
            (self.spin_t1, config.noise.t1_us),
            (self.spin_t2, config.noise.t2_us),
            (self.spin_gate1, config.noise.gate_time_1q_ns),
            (self.spin_gate2, config.noise.gate_time_2q_ns),
        ]:
            widget.setRange(min(widget.minimum(), value), max(widget.maximum(), value))
            widget.setValue(value)
        self.combo_ham.setCurrentText(config.system.hamiltonian)
        self.combo_initial.setCurrentIndex(
            self.combo_initial.findData(config.system.initial_state)
        )
        self.check_periodic.setChecked(config.system.periodic)
        self.combo_order.setCurrentIndex(
            self.combo_order.findData(config.protocol.trotter_order)
        )
        self.check_snaps.setChecked(config.protocol.save_snapshots)
        self.check_ruido.setChecked(config.noise.enabled)
        self.combo_modelo.setCurrentIndex(1 if config.noise.kind == "Termico" else 0)
        self.input_seed.setText("" if config.seed is None else str(config.seed))
        del blockers
        self._changed()

    def _arrange_sections(self):
        if not hasattr(self, "_section_layout"):
            return
        buttons = list(self.section_buttons.values())
        widest = max((button.sizeHint().width() for button in buttons), default=100)
        columns = max(1, min(len(buttons), (max(1, self.width()) + 4) // (widest + 4)))
        if columns == self._section_columns:
            return
        for column in range(max(self._section_columns, columns)):
            self._section_layout.setColumnStretch(column, 0)
        for index, button in enumerate(buttons):
            self._section_layout.removeWidget(button)
            self._section_layout.addWidget(button, index // columns, index % columns)
        for column in range(columns):
            self._section_layout.setColumnStretch(column, 1)
        self._section_columns = columns

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_sections()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._arrange_sections()

    def coletar_tudo(self):
        return {
            "qubits": self.spin_qubits.value(),
            "hamiltoniano": self.combo_ham.currentText(),
            "J": self.spin_J.value(),
            "h": self.spin_h.value(),
            "periodic": self.check_periodic.isChecked(),
            "tempo": self.spin_tempo.value(),
            "passos": self.spin_passos.value(),
            "salvar_snaps": self.check_snaps.isChecked(),
            "ruido_ativo": self.check_ruido.isChecked(),
            "modelo_ruido": self.combo_modelo.currentText(),
            "p1": self.spin_p1.value(),
            "p2": self.spin_p2.value(),
            "t1": self.spin_t1.value(),
            "t2": self.spin_t2.value(),
            "gate1": self.spin_gate1.value(),
            "gate2": self.spin_gate2.value(),
            "shots": self.spin_shots.value(),
            "seed": self.input_seed.text(),
        }
