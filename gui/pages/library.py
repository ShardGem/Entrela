from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel, QLineEdit, QComboBox, QPlainTextEdit, QFormLayout,
    QGroupBox, QVBoxLayout, QTabWidget, QWidget,
)
from gui.pages.base import PageBase
from gui.widgets.button import SecondaryButton


class LibraryPage(PageBase):
    draft_changed = Signal()
    loaded = Signal(str)
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
        group_layout = QVBoxLayout(self.annotation_group)
        tabs = QTabWidget()
        identification = QWidget()
        form = QFormLayout(identification)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.run_title = QLineEdit()
        self.run_title.setMaxLength(160)
        self.run_title.setPlaceholderText("Ex.: Bell · despolarização 5% · referência")
        self.run_title.setToolTip("Nome de apresentação. O identificador técnico e os resultados permanecem preservados.")
        self.project = QLineEdit()
        self.project.setPlaceholderText("Ex.: TCC — estudo de ruído")
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Bell, referência, capítulo 4")
        self.categories = QLineEdit()
        self.categories.setPlaceholderText("Ex.: decoerência, mitigação")
        self.categories.setToolTip("Categorias organizam linhas de pesquisa; etiquetas descrevem detalhes da execução.")
        self.description = QPlainTextEdit()
        self.description.setMaximumHeight(100)
        self.description.setPlaceholderText("Descreva o que foi investigado e por que esta execução foi realizada.")
        self.notes = QPlainTextEdit()
        self.notes.setMaximumHeight(160)
        self.notes.setPlaceholderText("Registre observações posteriores, limitações e próximos passos. Os resultados brutos permanecem preservados.")
        for label, widget in [
            ("Nome da execução", self.run_title),
            ("Descrição", self.description),
            ("Projeto", self.project),
            ("Categorias (vírgulas)", self.categories),
            ("Etiquetas (vírgulas)", self.tags),
        ]:
            widget.setAccessibleName(label)
            form.addRow(label, widget)
        tabs.addTab(identification, "Identificação")
        planning = QWidget()
        planning_form = QFormLayout(planning)
        planning_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.objective = QPlainTextEdit()
        self.hypothesis = QPlainTextEdit()
        self.methodology = QPlainTextEdit()
        for label, field, example in (
            ("Objetivo científico", self.objective, "Ex.: medir a perda de fidelidade conforme aumenta a probabilidade de erro."),
            ("Hipótese", self.hypothesis, "Ex.: aumentar a profundidade reduz o erro de Trotter, mas amplia o efeito do ruído."),
            ("Metodologia e controles", self.methodology, "Ex.: manter Hamiltoniano, estado inicial e tempo; variar somente p₂ e registrar shots e seed."),
        ):
            field.setMaximumHeight(105)
            field.setAccessibleName(label)
            field.setPlaceholderText(example)
            field.setToolTip(example)
            planning_form.addRow(label, field)
        tabs.addTab(planning, "Plano científico")
        notes_page = QWidget()
        notes_layout = QVBoxLayout(notes_page)
        notes_layout.addWidget(QLabel("Anotações de interpretação e acompanhamento"))
        notes_layout.addWidget(self.notes)
        tabs.addTab(notes_page, "Anotações")
        group_layout.addWidget(tabs)
        self.save_annotation = SecondaryButton("Salvar identificação e observações")
        self.save_annotation.clicked.connect(
            lambda: self.annotation_requested.emit(
                self.project.text(), self.notes.toPlainText(),
                [x.strip() for x in self.tags.text().split(",") if x.strip()],
            )
        )
        group_layout.addWidget(self.save_annotation)
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
        self.identifier = None
        self._loading = False
        for widget in (self.run_title,self.project,self.tags,self.categories,self.description,
                       self.notes,self.objective,self.hypothesis,self.methodology):
            widget.textChanged.connect(self._edited)

    def _edited(self, *_):
        if not self._loading:
            self.draft_changed.emit()

    def draft_payload(self):
        return dict(self.annotation_payload(), project=self.project.text(), notes=self.notes.toPlainText(),
                    tags=[value.strip() for value in self.tags.text().split(",") if value.strip()])

    def restore_draft(self, state):
        self._loading = True
        try:
            for key,name in (("title","run_title"),("project","project")):
                getattr(self,name).setText(state.get(key,""))
            for key in ("description","notes","objective","hypothesis","methodology"):
                getattr(self,key).setPlainText(state.get(key,""))
            for key in ("tags","categories"):
                getattr(self,key).setText(", ".join(state.get(key,[])))
        finally:
            self._loading = False
        self.message.setText("Anotações em edição recuperadas. Salve para incorporá-las ao caderno do experimento.")

    def annotation_payload(self):
        """Additional annotation fields; the legacy three-argument signal is stable."""
        return {
            "title": self.run_title.text(),
            "description": self.description.toPlainText(),
            "objective": self.objective.toPlainText(),
            "hypothesis": self.hypothesis.toPlainText(),
            "methodology": self.methodology.toPlainText(),
            "categories": [value.strip() for value in self.categories.text().split(",") if value.strip()],
        }

    def load(self, data, identifier=None, title=None):
        self._loading = True
        self.identifier = identifier
        selected = self.templates.currentText()
        self.templates.clear()
        self.templates.addItems(sorted(data["templates"]))
        if self.templates.findText(selected) >= 0:
            self.templates.setCurrentText(selected)
        annotation = data["annotations"].get(identifier, {})
        self.run_title.setText(annotation.get("title", ""))
        self.project.setText(annotation.get("project", ""))
        self.notes.setPlainText(annotation.get("notes", ""))
        self.description.setPlainText(annotation.get("description", ""))
        self.objective.setPlainText(annotation.get("objective", ""))
        self.hypothesis.setPlainText(annotation.get("hypothesis", ""))
        self.methodology.setPlainText(annotation.get("methodology", ""))
        self.categories.setText(", ".join(annotation.get("categories", [])))
        self.tags.setText(", ".join(annotation.get("tags", [])))
        self.annotation_group.setEnabled(bool(identifier))
        self.context.setText(
            "Organizando: " + (annotation.get("title") or title or "execução selecionada")
            if identifier
            else "Modelos usam o formulário atual. Abra uma execução para nomear e anotar resultados."
        )
        self._loading = False
        self.loaded.emit(identifier or "")
