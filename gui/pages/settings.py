from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QSpinBox, QComboBox, QCheckBox
from gui.pages.base import PageBase
from gui.widgets.card import Card
from gui.widgets.button import SecondaryButton


class SettingsPage(PageBase):
    appearance_changed = Signal()
    restore_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Configurações",
            "Preferências visuais independentes dos resultados científicos.",
            parent,
        )
        card = Card("Ambiente de trabalho")
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.spin_shots = QSpinBox()
        self.spin_shots.setRange(1, 1_000_000)
        self.spin_shots.setValue(8192)
        self.theme = QComboBox()
        self.theme.addItem("Escuro", "dark")
        self.theme.addItem("Claro", "light")
        self.font_size = QSpinBox()
        self.font_size.setRange(11, 20)
        self.font_size.setValue(13)
        self.presentation = QCheckBox(
            "Modo apresentação: fonte maior e navegação compacta (F11)"
        )
        self.compact = QCheckBox("Navegação compacta")
        for label, w in [
            ("Shots para novos experimentos", self.spin_shots),
            ("Tema", self.theme),
            ("Tamanho de fonte", self.font_size),
            ("Apresentação", self.presentation),
            ("Navegação", self.compact),
        ]:
            form.addRow(label, w)
        card.add_layout(form)
        self.body().addWidget(card)
        note = QLabel(
            "Velocidade, loop, rastros e foco ficam nos controles de Evolução 3D e são lembrados entre sessões. Restaurar a visão reinicia a câmera."
        )
        note.setWordWrap(True)
        self.body().addWidget(note)
        reset = SecondaryButton("Restaurar preferências visuais")
        reset.clicked.connect(self.restore_requested.emit)
        self.body().addWidget(reset)
        self.body().addStretch()
        self.theme.currentIndexChanged.connect(
            lambda *_: self.appearance_changed.emit()
        )
        self.font_size.valueChanged.connect(lambda *_: self.appearance_changed.emit())
        self.presentation.toggled.connect(lambda *_: self.appearance_changed.emit())
        self.compact.toggled.connect(lambda *_: self.appearance_changed.emit())
