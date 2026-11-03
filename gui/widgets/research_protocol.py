"""A research plan records intent separately from calculated evidence."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QHBoxLayout, QWidget
from gui.widgets.button import SecondaryButton


class ProtocolPanel(QGroupBox):
    save_requested = Signal()
    load_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__("Protocolo experimental e referência no TCC", parent)
        self.loaded = None
        self.setCheckable(True)
        self.setChecked(False)
        outer = QVBoxLayout(self)
        self.content = QWidget()
        form = QFormLayout(self.content)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.fields = {}
        for key, label, placeholder in [
            ("title", "Nome do protocolo", "Ex.: estabilidade ZNE — Bell"),
            ("question", "Pergunta científica", "Que efeito deseja investigar?"),
            ("hypothesis", "Hipótese", "O que espera observar e por quê?"),
            ("controls", "Controles e métricas", "Parâmetros fixos, variável estudada e critério de avaliação"),
            ("evidence_ref", "Referência no texto", "Ex.: Capítulo 4 · Tabela 5 · Figura 4.2"),
        ]:
            edit = QLineEdit()
            edit.setMaxLength(160 if key == "title" else 10000)
            edit.setPlaceholderText(placeholder)
            edit.setAccessibleName(label)
            self.fields[key] = edit
            form.addRow(label, edit)
        self.saved = QComboBox()
        self.saved.setMinimumContentsLength(14)
        self.saved.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        form.addRow("Revisões salvas", self.saved)
        buttons = QHBoxLayout()
        self.save_button = SecondaryButton("Salvar nova revisão")
        self.load_button = SecondaryButton("Carregar protocolo")
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.load_button)
        form.addRow(buttons)
        outer.addWidget(self.content)
        self.content.setVisible(False)
        self.toggled.connect(self.content.setVisible)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.load_button.clicked.connect(lambda: self.load_requested.emit(self.saved.currentData() or ""))

    def context(self):
        fields = {key: edit.text().strip() for key, edit in self.fields.items()}
        unchanged=self.loaded is not None and fields==self.loaded["fields"]
        return dict(protocol_id=self.loaded.get("protocol_id") if unchanged else None,
                    derived_from_protocol_id=self.loaded.get("protocol_id") if self.loaded and not unchanged else None,fields=fields)

    def set_protocol(self, data):
        self.loaded = data
        for key, edit in self.fields.items():
            edit.setText(data["fields"].get(key, ""))
        self.setChecked(True)

    def set_saved(self, records):
        selected = self.saved.currentData()
        self.saved.clear()
        for item in records:
            self.saved.addItem(item["fields"]["title"] + " · " + item["created_at"][:16], item["protocol_id"])
        index = self.saved.findData(selected)
        if index >= 0:
            self.saved.setCurrentIndex(index)
