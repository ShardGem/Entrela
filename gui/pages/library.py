from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel, QLineEdit, QComboBox, QPlainTextEdit, QFormLayout,
    QGroupBox, QVBoxLayout,
)
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
            "Dê nomes às execuções, registre hipóteses e reutilize configurações.",
            parent,
        )
        self.context = QLabel("Abra uma execução para organizar seus resultados.")
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)

        self.annotation_group = QGroupBox("Execução selecionada")
        form = QFormLayout(self.annotation_group)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.run_title = QLineEdit()
        self.run_title.setMaxLength(160)
        self.run_title.setPlaceholderText("Ex.: Bell · despolarização 5% · referência")
        self.run_title.setToolTip("Nome de apresentação. O identificador técnico e os resultados permanecem preservados.")
        self.project = QLineEdit()
        self.project.setPlaceholderText("Ex.: TCC — estudo de ruído")
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Bell, referência, capítulo 4")
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(160)
        self.notes.setPlaceholderText("Hipótese, observações, limitações e próximos passos…")
        for label, widget in [
            ("Nome da execução", self.run_title),
            ("Projeto", self.project),
            ("Tags (vírgulas)", self.tags),
            ("Descrição e observações", self.notes),
        ]:
            widget.setAccessibleName(label)
            form.addRow(label, widget)
        self.save_annotation = SecondaryButton("Salvar identificação e observações")
        self.save_annotation.clicked.connect(
            lambda: self.annotation_requested.emit(
                self.project.text(), self.notes.toPlainText(),
                [x.strip() for x in self.tags.text().split(",") if x.strip()],
            )
        )
        form.addRow(self.save_annotation)
        self.body().addWidget(self.annotation_group)

        templates_group = QGroupBox("Modelos pessoais de configuração")
        templates_layout = QVBoxLayout(templates_group)
        help_label = QLabel("Modelos guardam os parâmetros do formulário atual para novos experimentos. Resultados e estados não são copiados.")
        help_label.setWordWrap(True)
        templates_layout.addWidget(help_label)
        template_form = QFormLayout()
        template_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Nome do modelo a salvar")
        self.templates = QComboBox()
        template_form.addRow("Nome do modelo", self.name)
        template_form.addRow("Modelos salvos", self.templates)
        templates_layout.addLayout(template_form)
        for text, callback in [
            ("Salvar configuração atual como modelo", lambda: self.template_save_requested.emit(self.name.text())),
            ("Carregar modelo no formulário", lambda: self.template_load_requested.emit(self.templates.currentText())),
            ("Excluir modelo selecionado", lambda: self.template_delete_requested.emit(self.templates.currentText())),
        ]:
            button = SecondaryButton(text)
            button.clicked.connect(callback)
            templates_layout.addWidget(button)
        self.body().addWidget(templates_group)
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
        self.run_title.setText(annotation.get("title", ""))
        self.project.setText(annotation.get("project", ""))
        self.notes.setPlainText(annotation.get("notes", ""))
        self.tags.setText(", ".join(annotation.get("tags", [])))
        self.annotation_group.setEnabled(bool(identifier))
        self.context.setText(
            "Identificador técnico: " + identifier
            if identifier
            else "Modelos usam o formulário atual. Abra uma execução para nomear e anotar resultados."
        )
