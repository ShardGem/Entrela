from PySide6.QtCore import Signal, QSignalBlocker
from PySide6.QtWidgets import (
    QLabel, QLineEdit, QComboBox, QPlainTextEdit, QFormLayout,
    QFrame, QVBoxLayout, QTabWidget, QWidget, QMessageBox,
)
from gui.pages.base import PageBase
from gui.widgets.button import SecondaryButton
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.collapsible import CollapsibleSection
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.dialogs import FeedbackLabel


class LibraryPage(PageBase):
    configurations_requested = Signal()
    draft_changed = Signal()
    loaded = Signal(str)
    template_save_requested = Signal(str)
    template_load_requested = Signal(str)
    annotation_requested = Signal(str, str, list)
    template_delete_requested = Signal(str)
    navigation_requested = Signal(str)
    project_history_requested = Signal(str)
    view_preferences_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Caderno e configurações",
            "Anote os resultados de uma execução ou reutilize os parâmetros do formulário de simulação.",
            parent,
        )
        self.context = QLabel("Abra uma execução para organizar seus resultados.")
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)
        self.select_execution = SecondaryButton("Selecionar uma execução", icon="history")
        self.select_execution.setToolTip("Abra uma execução do histórico para nomear seus resultados e registrar sua interpretação.")
        self.select_execution.clicked.connect(lambda: self.navigation_requested.emit("history"))
        self.add_action(self.select_execution)
        self.tabs = ContentTabs()
        self.body().addWidget(self.tabs, 1)

        self.annotation_group = QWidget()
        group_layout = QVBoxLayout(self.annotation_group)
        annotation_help = QLabel("Este caderno acompanha uma execução. Salvar registra identificação e interpretação; os valores científicos da execução são preservados.")
        annotation_help.setWordWrap(True)
        annotation_help.setObjectName("FieldHint")
        group_layout.addWidget(annotation_help)
        self.sections = {}
        identification = QWidget()
        form = QFormLayout(identification)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.run_title = QLineEdit()
        self.run_title.setMaxLength(160)
        self.run_title.setPlaceholderText("Ex.: Bell · despolarização 5% · referência")
        self.run_title.setToolTip("Nome de apresentação. O identificador técnico e os resultados permanecem preservados.")
        self.project = QLineEdit()
        self.project.setPlaceholderText("Ex.: TCC — estudo de ruído")
        self.project.setToolTip("Use o mesmo nome para agrupar execuções de um estudo. Projeto é um agrupamento do histórico, não um circuito nem uma configuração executável.")
        self.tags = QLineEdit()
        self.tags.setPlaceholderText("Bell, referência, capítulo 4")
        self.tags.setToolTip("Separe por vírgulas. Etiquetas ajudam a encontrar execuções pela busca do histórico.")
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
        self._add_section(group_layout, "identification", "Identificação", identification, expanded=True)
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
        self._add_section(group_layout, "planning", "Plano científico", planning, expanded=False)
        notes_page = QWidget()
        notes_layout = QVBoxLayout(notes_page)
        notes_layout.addWidget(QLabel("Anotações de interpretação e acompanhamento"))
        notes_layout.addWidget(self.notes)
        self._add_section(group_layout, "notes", "Interpretação e anotações", notes_page, expanded=True)
        self.save_annotation = SecondaryButton("Salvar caderno")
        self.save_annotation.setToolTip("Salva nome, plano científico e anotações da execução selecionada.")
        self.save_annotation.clicked.connect(
            lambda: self.annotation_requested.emit(
                self.project.text(), self.notes.toPlainText(),
                [x.strip() for x in self.tags.text().split(",") if x.strip()],
            )
        )
        annotation_actions = FlowLayout()
        annotation_actions.addWidget(self.save_annotation)
        self.project_history = SecondaryButton("Ver execuções deste projeto")
        self.project_history.setToolTip("Busca no histórico as execuções já salvas com o nome deste projeto.")
        self.project_history.clicked.connect(self._request_project_history)
        annotation_actions.addWidget(self.project_history)
        self.notebook_actions_bar = QFrame()
        self.notebook_actions_bar.setObjectName("ExecutionBar")
        self.notebook_actions_bar.setContentsMargins(20, 8, 20, 12)
        self.notebook_actions_bar.setLayout(annotation_actions)
        self._root.addWidget(self.notebook_actions_bar)
        self.tabs.addTab(self.annotation_group, "Caderno da execução")

        templates_group = QWidget()
        self.templates_group = templates_group
        templates_layout = QVBoxLayout(templates_group)
        help_label = QLabel("Salve os parâmetros do formulário de simulação para usá-los em outra execução: sistema, evolução, ruído, medições e semente. Abrir um resultado ou editar um circuito de portas não muda essa fonte.")
        help_label.setWordWrap(True)
        help_label.setObjectName("FieldHint")
        templates_layout.addWidget(help_label)
        self.configuration_source = QLabel("Fonte: formulário de parâmetros da simulação.")
        self.configuration_source.setWordWrap(True)
        templates_layout.addWidget(self.configuration_source)
        template_form = QFormLayout()
        template_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Ex.: Ising — referência ideal")
        self.name.setAccessibleName("Nome da configuração a salvar")
        self.name.setToolTip("Dê um nome aos parâmetros do formulário. Salvar com um nome existente pede confirmação para atualizá-lo.")
        self.templates = QComboBox()
        self.templates.setAccessibleName("Configurações salvas do formulário")
        self.templates.setToolTip("Escolha os parâmetros que deseja usar em uma nova simulação.")
        template_form.addRow("Nome da configuração", self.name)
        template_form.addRow("Configurações salvas", self.templates)
        templates_layout.addLayout(template_form)
        template_actions = FlowLayout()
        for attribute, text, callback in [
            ("save_template", "Salvar parâmetros", self._request_template_save),
            ("load_template", "Usar na simulação", lambda: self.template_load_requested.emit(self.templates.currentText())),
            ("delete_template", "Excluir configuração", lambda: self.template_delete_requested.emit(self.templates.currentText())),
        ]:
            button = SecondaryButton(text)
            setattr(self, attribute, button)
            button.clicked.connect(callback)
            template_actions.addWidget(button)
        self.save_template.setToolTip("Guarda os parâmetros que estão no formulário de simulação. Não salva resultados nem as portas em edição.")
        self.load_template.setToolTip("Preenche o formulário para edição. A simulação só começa quando você clicar em Executar.")
        self.delete_template.setToolTip("Remove a configuração pessoal selecionada. As execuções já salvas são preservadas.")
        templates_layout.addLayout(template_actions)
        circuit_help = QLabel("Circuitos com portas e suas revisões ficam na biblioteca do editor. Exemplos prontos são demonstrações da galeria; configurações salvas são seus parâmetros pessoais.")
        circuit_help.setWordWrap(True)
        circuit_help.setObjectName("FieldHint")
        templates_layout.addWidget(circuit_help)
        self.open_circuits = SecondaryButton("Abrir editor de circuitos")
        self.open_circuits.clicked.connect(lambda: self.navigation_requested.emit("circuit"))
        templates_layout.addWidget(self.open_circuits)
        templates_layout.addStretch()
        self.tabs.addTab(templates_group, "Configurações salvas")
        self.message = FeedbackLabel()
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.identifier = None
        self._notebook_title = ""
        self._loading = False
        self._template_names = set()
        self.name.textChanged.connect(self._update_actions)
        self.templates.currentIndexChanged.connect(self._update_actions)
        self.project.textChanged.connect(self._update_actions)
        self.tabs.currentChanged.connect(self._refresh_context)
        self.tabs.currentChanged.connect(lambda *_: self.view_preferences_changed.emit())
        for widget in (self.run_title,self.project,self.tags,self.categories,self.description,
                       self.notes,self.objective,self.hypothesis,self.methodology):
            widget.textChanged.connect(self._edited)
        self.annotation_group.setEnabled(False)
        self._update_actions()

    def _add_section(self, layout, key, title, content, *, expanded):
        section = CollapsibleSection(title, expanded=expanded)
        section.set_summary("")
        section.content_layout.addWidget(content)
        section.expanded_changed.connect(lambda *_: self.view_preferences_changed.emit())
        self.sections[key] = section
        layout.addWidget(section)

    def collect_view_preferences(self):
        return dict(tab=self.tabs.currentIndex(), expanded=[key for key, section in self.sections.items() if section.is_expanded])

    def apply_view_preferences(self, values):
        if not isinstance(values, dict):
            return
        blockers = [QSignalBlocker(self.tabs), *(QSignalBlocker(section) for section in self.sections.values())]
        expanded = values.get("expanded")
        if isinstance(expanded, list) and all(isinstance(key, str) for key in expanded):
            for key, section in self.sections.items():
                section.set_expanded(key in expanded, animate=False)
        tab = values.get("tab")
        if type(tab) is int and 0 <= tab < self.tabs.count():
            self.tabs.setCurrentIndex(tab)
        del blockers
        self._refresh_context()

    def show_notebook(self):
        self.tabs.setCurrentWidget(self.annotation_group)

    def show_configurations(self):
        if self.tabs.indexOf(self.templates_group) >= 0:
            self.tabs.setCurrentWidget(self.templates_group)
        self.configurations_requested.emit()

    def set_configuration_context(self, text):
        """Describe the SAME simulation form used by the existing save signal."""
        self.configuration_source.setText("Fonte: formulário de parâmetros da simulação. " + text)

    def set_unavailable(self, message):
        """Do not leave an old notebook editable after its source cannot be read."""
        self.identifier = None
        self.annotation_group.setEnabled(False)
        self.templates_group.setEnabled(False)
        self.context.setText("Caderno e configurações indisponíveis. O arquivo foi preservado.")
        self.message.setText(message)
        self._update_actions()

    def _refresh_context(self, *_):
        self.notebook_actions_bar.setVisible(self.tabs.currentWidget() is self.annotation_group)
        if not self.templates_group.isEnabled():
            self.context.setText("Caderno e configurações indisponíveis. O arquivo foi preservado.")
        elif self.tabs.currentWidget() is self.templates_group:
            self.context.setText("Configurações salvas: parâmetros do formulário de simulação. Usar uma configuração não executa o experimento.")
        elif self.identifier:
            self.context.setText("Caderno: " + self._notebook_title)
        else:
            self.context.setText("Selecione uma execução salva para registrar identificação, plano e anotações.")

    def _update_actions(self, *_):
        self.save_annotation.setEnabled(bool(self.identifier) and self.annotation_group.isEnabled())
        self.save_template.setEnabled(bool(self.name.text().strip()))
        selected = self.templates.currentText() in self._template_names
        self.load_template.setEnabled(selected)
        self.delete_template.setEnabled(selected)
        self.project_history.setEnabled(bool(self.identifier and self.project.text().strip()))

    def _request_project_history(self):
        project = self.project.text().strip()
        if self.identifier and project:
            self.project_history_requested.emit(project)

    def _request_template_save(self):
        name = self.name.text().strip()
        if not name:
            self.message.setText("Informe um nome para guardar os parâmetros do formulário.")
            return
        if name in self._template_names:
            answer = QMessageBox.question(
                self, "Atualizar configuração salva?",
                f"A configuração '{name}' já existe. Deseja substituí-la pelos parâmetros atuais do formulário? As execuções salvas serão preservadas.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
        self.template_save_requested.emit(name)

    def request_template_save(self, name=None):
        """Reuse overwrite protection from an integrated configuration toolbar."""
        if name is not None:
            self.name.setText(name)
        self._request_template_save()

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
        self._template_names = set(data["templates"])
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
        self.templates_group.setEnabled(True)
        self._notebook_title = annotation.get("title") or title or "execução selecionada"
        self._refresh_context()
        self._loading = False
        self._update_actions()
        self.loaded.emit(identifier or "")
