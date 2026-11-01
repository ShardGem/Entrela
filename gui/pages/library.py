from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QComboBox, QPlainTextEdit, QFormLayout
from gui.pages.base import PageBase
from gui.widgets.button import SecondaryButton


class LibraryPage(PageBase):
    template_save_requested = Signal(str)
    template_load_requested = Signal(str)
    annotation_requested = Signal(str, str, list)
    template_delete_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Projetos e modelos",
            "Organize hipóteses e guarde configurações pessoais.",
            parent,
        )
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.name = QLineEdit()
        self.templates = QComboBox()
        self.project = QLineEdit()
        self.tags = QLineEdit()
        self.notes = QPlainTextEdit()
        self.notes.setPlaceholderText(
            "Hipótese, observações, limitações e próximos passos…"
        )
        self.context = QLabel("Abra uma execução para anotar seus resultados.")
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)
        for label, w in [
            ("Nome do modelo", self.name),
            ("Modelos salvos", self.templates),
            ("Projeto da execução", self.project),
            ("Tags (vírgulas)", self.tags),
            ("Notas", self.notes),
        ]:
            form.addRow(label, w)
        self.body().addLayout(form)
        for text, callback in [
            (
                "Salvar configuração do formulário como modelo",
                lambda: self.template_save_requested.emit(self.name.text()),
            ),
            (
                "Carregar modelo no formulário",
                lambda: self.template_load_requested.emit(self.templates.currentText()),
            ),
            (
                "Excluir modelo selecionado",
                lambda: self.template_delete_requested.emit(
                    self.templates.currentText()
                ),
            ),
            (
                "Salvar projeto, notas e tags",
                lambda: self.annotation_requested.emit(
                    self.project.text(),
                    self.notes.toPlainText(),
                    [x.strip() for x in self.tags.text().split(",") if x.strip()],
                ),
            ),
        ]:
            b = SecondaryButton(text)
            b.clicked.connect(callback)
            self.body().addWidget(b)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.body().addStretch()

    def load(self, data, identifier=None):
        selected = self.templates.currentText()
        self.templates.clear()
        self.templates.addItems(sorted(data["templates"]))
        if self.templates.findText(selected) >= 0:
            self.templates.setCurrentText(selected)
        annotation = data["annotations"].get(identifier, {})
        self.project.setText(annotation.get("project", ""))
        self.notes.setPlainText(annotation.get("notes", ""))
        self.tags.setText(", ".join(annotation.get("tags", [])))
        self.context.setText(
            "Execução " + identifier
            if identifier
            else "Modelos usam o formulário atual. Abra uma execução para anotar resultados."
        )
