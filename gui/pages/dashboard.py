"""Project landing and overview, backed only by persisted work and executions."""
from PySide6.QtCore import Signal, Qt, QTimer, QEvent
from PySide6.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QSplitter, QMenu
from gui.pages.base import PageBase
from gui.widgets.card import MetricCard
from gui.design_system import Surface
from gui.widgets.button import PrimaryButton, SecondaryButton
from data.workspace import experiment_title
from core.types import system_label


class DashboardPage(PageBase):
    new_simulation = Signal()
    new_circuit = Signal()
    open_history = Signal()
    examples_requested = Signal()
    tutorial_requested = Signal()
    experiment_selected = Signal(str)
    project_selected = Signal(str)
    project_create_requested = Signal()
    work_selected = Signal(str)
    notebook_requested = Signal()
    ideal_requested = Signal()

    def __init__(self, parent=None):
        super().__init__('Projetos', parent=parent)
        self.annotations = {}
        self._recent_experiments = []
        self.project_name = None
        self.mode = "overview"
        self._list_size_timer = QTimer(self)
        self._list_size_timer.setSingleShot(True)
        self._list_size_timer.timeout.connect(self._size_lists)
        self._works = []
        # Compatibility values are retained but no empty KPI strip occupies the landing.
        for attr, title in [('card_sims', 'Execuções'), ('card_last', 'Modelo'), ('card_fid', 'Fidelidade'), ('card_purity', 'Pureza')]:
            card = MetricCard(title, parent=self); card.hide(); setattr(self, attr, card)
        actions = QHBoxLayout()
        self.intro = QLabel('Escolha uma investigação ou comece por um exemplo. Cada resultado preserva sua configuração de origem.')
        self.intro.setWordWrap(True); self.intro.setObjectName('SectionSubtitle')
        self.body().addWidget(self.intro)
        self.create_project = PrimaryButton('Criar projeto', icon='plus')
        self.create_project.clicked.connect(self.project_create_requested.emit)
        self.new_experiment = SecondaryButton('Novo experimento', icon='plus')
        creation = QMenu(self.new_experiment)
        creation.addAction('Evolução por Hamiltoniano', self.new_simulation.emit)
        creation.addAction('Circuito livre de portas', self.new_circuit.emit)
        self.new_experiment.setMenu(creation)
        actions.addWidget(self.create_project); actions.addWidget(self.new_experiment); actions.addStretch()
        self.body().addLayout(actions)
        self.dashboard_splitter = QSplitter(Qt.Horizontal)
        self.dashboard_splitter.setChildrenCollapsible(False)
        self.dashboard_splitter.setHandleWidth(3)
        self.project_surface = Surface('Suas investigações')
        self.project_list = QListWidget()
        self.project_list.setAccessibleName('Projetos recentes')
        self.project_list.setMinimumHeight(180)
        self.project_list.setWordWrap(True)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_list.itemActivated.connect(lambda item: self.project_selected.emit(item.data(Qt.UserRole)))
        self.project_list.itemClicked.connect(lambda item: self.project_selected.emit(item.data(Qt.UserRole)))
        self.project_surface.add(self.project_list)
        self.dashboard_splitter.addWidget(self.project_surface)
        self.overview = Surface('Retomar o trabalho')
        self.resume_title = QLabel('Comece com uma pergunta científica')
        self.resume_title.setObjectName('PanelTitle'); self.resume_title.setWordWrap(True)
        self.overview.add(self.resume_title)
        self.resume_description = QLabel('Abra um modelo editável, execute uma simulação e registre suas observações. Os dados são calculados localmente.')
        self.resume_description.setWordWrap(True); self.resume_description.setObjectName('FieldHint')
        self.overview.add(self.resume_description)
        self.resume = PrimaryButton('Abrir na bancada', icon='arrow-right')
        self.resume.clicked.connect(self._resume)
        self.overview.add(self.resume)
        self.question = QLabel(); self.question.setWordWrap(True); self.question.setObjectName('SectionSubtitle')
        self.overview.add(self.question)
        self.works_label = QLabel('Experimentos'); self.works_label.setObjectName('PanelTitle'); self.overview.add(self.works_label)
        self.works = QListWidget()
        self.works.setMinimumHeight(150)
        self.works.setAccessibleName('Experimentos do projeto')
        self.works.itemActivated.connect(lambda item: self.work_selected.emit(item.data(Qt.UserRole)))
        self.works.itemClicked.connect(lambda item: self.work_selected.emit(item.data(Qt.UserRole)))
        self.overview.add(self.works)
        self.recent = Surface('Execuções recentes')
        self.recent_list = QListWidget()
        self.recent_list.setAccessibleName('Execuções recentes com sua modalidade e data')
        self.recent_list.setMinimumHeight(150)
        self.recent_list.itemActivated.connect(lambda item: self.experiment_selected.emit(item.data(Qt.UserRole)))
        self.recent_list.itemClicked.connect(lambda item: self.experiment_selected.emit(item.data(Qt.UserRole)))
        self.recent.add(self.recent_list)
        self.overview.add(self.recent)
        links = QHBoxLayout()
        self.notebook = SecondaryButton('Abrir caderno', icon='book')
        self.notebook.clicked.connect(self.notebook_requested.emit)
        self.ideal = SecondaryButton('Comparar com a referência ideal', icon='comparison')
        self.ideal.clicked.connect(self.ideal_requested.emit)
        links.addWidget(self.notebook); links.addWidget(self.ideal)
        self.overview.body().addLayout(links)
        self.overview.body().addStretch()
        self.dashboard_splitter.addWidget(self.overview)
        self.dashboard_splitter.setStretchFactor(1, 1)
        self.dashboard_splitter.setSizes([360, 900])
        self.body().addWidget(self.dashboard_splitter, 1)
        self.first_use = Surface('Seu primeiro experimento')
        for text, signal in [('Escolher um exemplo da biblioteca', self.examples_requested), ('Iniciar tutorial de Bell', self.tutorial_requested), ('Consultar histórico completo', self.open_history)]:
            button = SecondaryButton(text)
            button.clicked.connect(signal.emit); self.first_use.add(button)
        self.body().addWidget(self.first_use)
        self.concept_toggle = SecondaryButton('Como interpretar os resultados')
        self.concept_toggle.setCheckable(True)
        self.first_use.add(self.concept_toggle)
        self.concepts = QLabel('Contagens são amostras das probabilidades. A esfera de Bloch representa o estado local de cada qubit.\nPureza global e pureza local são medidas distintas. A fidelidade depende da referência indicada.\nZNE extrapola um observável; não reconstrói um estado mitigado.')
        self.concepts.setWordWrap(True); self.concepts.hide()
        self.first_use.add(self.concepts)
        self.concept_toggle.toggled.connect(self.concepts.setVisible)
        self._render()

    def set_mode(self, mode):
        self.mode = mode
        self._render()

    def _size_lists(self):
        scale = max(1, self.font().pixelSize()/15)
        for view, limit in ((self.works, 5 if self.mode == 'experiments' else 2), (self.recent_list, 3)):
            row = max(round(48*scale), view.sizeHintForRow(0))
            height = max(round(70*scale), min(max(1, view.count()), limit)*row + 16)
            view.setMinimumHeight(0)
            view.setMaximumHeight(height)
            view.setFixedHeight(height)
            view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            view.setTextElideMode(Qt.ElideRight)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, 'works'):
            self._list_size_timer.start(0)

    def set_annotations(self, annotations):
        self.annotations = annotations or {}; self._render()

    def update_stats(self, total, last_ham, avg_fid, avg_purity):
        self.card_sims.set_value(str(total)); self.card_last.set_value(last_ham or '—')
        self.card_fid.set_value('—' if avg_fid is None else f'{avg_fid:.4f}')
        self.card_purity.set_value('—' if avg_purity is None else f'{avg_purity:.4f}')

    def load_recent(self, experiments):
        self._recent_experiments = list(experiments); self._render()

    def load_projects(self, projects, works, project=None, metadata=None, ideal_pair=None):
        self.project_name = project
        self._works = list(works)
        self.project_list.clear()
        for entry in sorted(projects, key=lambda p: p.get('updated_at', ''), reverse=True):
            item = QListWidgetItem(entry['name'] + ('\n' + entry.get('description', '') if entry.get('description') else ''))
            item.setData(Qt.UserRole, entry['name']); item.setToolTip(item.text()); self.project_list.addItem(item)
        item = QListWidgetItem('Sem projeto\nExecuções e rascunhos ainda não associados')
        item.setData(Qt.UserRole, ''); self.project_list.addItem(item)
        self.question.setText((metadata or {}).get('objective') or (metadata or {}).get('description', ''))
        self.ideal_pair = ideal_pair
        self.ideal.setVisible(bool(ideal_pair))
        if ideal_pair:
            self.ideal.setToolTip('A: ' + ideal_pair[2] + '\nB: ' + ideal_pair[3] + '\nReferência: mesmo circuito sem ruído; não é evolução exata.')
        self.project_surface.setVisible(project is None)
        self.intro.setVisible(project is None)
        self.create_project.setVisible(project is None)
        self.notebook.setEnabled(bool(project))
        self._render()

    def _resume(self):
        if self._works:
            self.work_selected.emit(self._works[0]['id'])
        else:
            self.new_simulation.emit()

    def _render(self):
        if not hasattr(self, 'recent_list'): return
        self.works.clear()
        for work in self._works:
            kind = 'Circuito livre' if work['kind'] == 'circuit' else 'Hamiltoniano'
            status = 'Rascunho em edição' if not work.get('executions') else 'Rascunho · execução disponível'
            item = QListWidgetItem(f"{work['title']}\n{kind} · {status}")
            item.setData(Qt.UserRole, work['id']); item.setToolTip(item.text()); self.works.addItem(item)
        show_works = bool(self._works) and (self.mode == 'experiments' or len(self._works) > 1)
        self.works_label.setVisible(show_works); self.works.setVisible(show_works)
        self.resume_title.setText(self._works[0]['title'] if self._works else 'Comece uma investigação')
        if self._works:
            work = self._works[0]
            self.resume_description.setText(('Circuito livre' if work['kind'] == 'circuit' else 'Evolução por Hamiltoniano') + ' · ' + ('Última execução disponível; o rascunho permanece editável.' if work.get('executions') else 'Rascunho em edição · ainda sem execução.'))
        self.resume.setText('Abrir na bancada' if self._works else 'Criar experimento')
        self.recent_list.clear()
        records = [e for e in self._recent_experiments if self.project_name is None or self.annotations.get(e.id, {}).get('project', '') == self.project_name]
        for exp in records[:8]:
            label = experiment_title(exp, self.annotations)
            modality = 'ZNE · observável' if exp.result.mitigation else system_label(exp.config)
            status = 'Falhou' if exp.result.error else 'Concluída'
            metrics = ''
            if exp.result.fidelity is not None and not exp.result.mitigation:
                metrics = f" · F ao circuito sem ruído {exp.result.fidelity:.4f}"
            item = QListWidgetItem(f"{label}\n{modality} · {status} · {exp.created_at.astimezone().strftime('%d/%m/%Y %H:%M')}" + metrics)
            item.setData(Qt.UserRole, exp.id); item.setToolTip(item.text()); self.recent_list.addItem(item)
        self.recent.setVisible(bool(records))
        self.first_use.setVisible(not self._works or self.project_name is None)
        self._size_lists()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'dashboard_splitter'):
            self.dashboard_splitter.setOrientation(Qt.Vertical if self.width() < 900 * max(1, self.font().pixelSize()/15) else Qt.Horizontal)
