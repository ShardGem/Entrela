"""Diálogos de tarefas contextuais sobre os componentes e sinais existentes."""
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QScrollArea, QFrame, QDialogButtonBox


class FeedbackLabel(QLabel):
    changed = Signal(str)

    def setText(self, text):
        super().setText(text)
        self.changed.emit(text)


class ConfigurationsDialog(QDialog):
    def __init__(self, library, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Configurações salvas · Entrela')
        self.resize(800, 610)
        layout = QVBoxLayout(self)
        title = QLabel('Reutilizar parâmetros do Hamiltoniano')
        title.setObjectName('SectionTitle')
        layout.addWidget(title)
        area = QScrollArea()
        area.setFrameShape(QFrame.NoFrame)
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        group = library.templates_group
        library.tabs.removeTab(library.tabs.indexOf(group))
        area.setWidget(group)
        layout.addWidget(area, 1)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.PlainText)
        library.message.changed.connect(self.message.setText)
        layout.addWidget(self.message)
        close = QDialogButtonBox(QDialogButtonBox.Close)
        close.button(QDialogButtonBox.Close).setText('Fechar')
        close.rejected.connect(self.reject)
        library.open_circuits.clicked.connect(self.accept)
        layout.addWidget(close)
