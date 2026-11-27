"""Project landing and overview, backed only by persisted work and executions."""
from PySide6.QtCore import QEvent, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QLabel, QListWidget, QListWidgetItem, QMenu, QSplitter,
    QStyle, QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout, QWidget,
)
from gui.pages.base import PageBase
from gui.widgets.card import MetricCard
from gui.design_system import LAYOUT, Surface
from gui.theme import PALETTE
from gui.widgets.button import GhostButton, PrimaryButton, SecondaryButton
from gui.widgets.flow_layout import FlowLayout
from data.workspace import experiment_title
from core.types import system_label


class _RecordRow(QStyledItemDelegate):
    """Título e contexto secundário no mesmo item selecionável."""

    def sizeHint(self, option, index):
        lines = 2 if "\n" in str(index.data()) else 1
        return QSize(0, lines * option.fontMetrics.height() + 16)

    def paint(self, painter, option, index):
        row = QStyleOptionViewItem(option)
        self.initStyleOption(row, index)
        title, _, detail = str(index.data(Qt.DisplayRole) or "").partition("\n")
        selected = bool(row.state & QStyle.State_Selected)
        hovered = bool(row.state & QStyle.State_MouseOver)
        title_font = QFont(row.font)
        title_font.setWeight(QFont.DemiBold)
        detail_font = QFont(row.font)
        detail_font.setPixelSize(max(11, row.fontMetrics.height() - 5))
        title_height = QFontMetrics(title_font).height()
        detail_height = QFontMetrics(detail_font).height() if detail else 0
        text_rect = row.rect.adjusted(10, 0, -10, 0)
        top = text_rect.y() + (text_rect.height() - title_height - detail_height) // 2

        painter.save()
        painter.setClipRect(row.rect, Qt.IntersectClip)
        if selected or hovered:
            painter.fillRect(row.rect, QColor(PALETTE.primary_faint if selected else PALETTE.bg))
        painter.setPen(QColor(PALETTE.primary if row.state & QStyle.State_HasFocus else PALETTE.border))
        painter.drawLine(row.rect.bottomLeft(), row.rect.bottomRight())
        if row.state & QStyle.State_HasFocus:
            painter.drawRect(row.rect.adjusted(0, 0, -1, -1))
        for text, font, y, height, color in (
            (title, title_font, top, title_height, PALETTE.primary if selected else PALETTE.text),
            (detail, detail_font, top + title_height, detail_height, PALETTE.text_muted),
        ):
            if text:
                painter.setFont(font)
                painter.setPen(QColor(color))
                visible = QFontMetrics(font).elidedText(text, Qt.ElideRight, text_rect.width())
                painter.drawText(QRect(text_rect.x(), y, text_rect.width(), height),
                                 Qt.AlignLeft | Qt.AlignVCenter, visible)
        painter.restore()


class DashboardPage(PageBase):
    new_simulation = Signal()
    new_circuit = Signal()
    open_history = Signal()
    examples_requested = Signal()
    tutorial_requested = Signal()
    experiment_selected = Signal(str)
    project_selected = Signal(str)
    project_create_requested = Signal()
    all_projects_requested = Signal()
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
        actions = FlowLayout(spacing=8)
        self.create_project = SecondaryButton('Criar projeto', icon='project-folder')
        self.create_project.clicked.connect(self.project_create_requested.emit)
        self.new_experiment = SecondaryButton('Novo experimento', icon='plus')
        creation = QMenu(self.new_experiment)
        creation.addAction('Evolução por Hamiltoniano', self.new_simulation.emit)
        creation.addAction('Circuito livre de portas', self.new_circuit.emit)
        self.new_experiment.setMenu(creation)
        self.all_projects = SecondaryButton('Todos os projetos')
        self.all_projects.clicked.connect(self.all_projects_requested.emit)
        self.all_projects.hide()
        self.show_works = SecondaryButton('Ver experimentos')
        self.show_works.clicked.connect(self._toggle_work_list)
        self.show_works.hide()
        for button in (self.all_projects, self.create_project, self.new_experiment, self.show_works):
            actions.addWidget(button)
        self.body().addLayout(actions)
        self.dashboard_splitter = QSplitter(Qt.Horizontal)
        self.dashboard_splitter.setChildrenCollapsible(False)
        self.dashboard_splitter.setHandleWidth(LAYOUT.handle_width)
        self.project_surface = Surface('Investigações', role='ProjectCard')
        self.project_list = QListWidget()
        self.project_list.setObjectName("WorkspaceList")
        self.project_list.setAccessibleName('Projetos recentes')
        self.project_list.setWordWrap(True)
        self.project_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.project_list.itemActivated.connect(lambda item: self.project_selected.emit(item.data(Qt.UserRole)))
        self.project_list.itemClicked.connect(lambda item: self.project_selected.emit(item.data(Qt.UserRole)))
        self.project_surface.add(self.project_list)
        self.projects_column = QWidget()
        projects_layout = QVBoxLayout(self.projects_column)
        projects_layout.setContentsMargins(0, 0, 0, 0)
        projects_layout.addWidget(self.project_surface, 0, Qt.AlignTop)
        projects_layout.addStretch()
        self.dashboard_splitter.addWidget(self.projects_column)
        self.overview = Surface(role='FlatSection')
        self.overview.body().setContentsMargins(8, 0, 0, 0)
        self.overview.body().setSpacing(18)
        self.resume_card = Surface(role='ProjectResume')
        self.resume_role = QLabel('Experimento em andamento')
        self.resume_role.setObjectName('Eyebrow')
        self.resume_card.add(self.resume_role)
        self.resume_title = QLabel()
        self.resume_title.setObjectName('ResumeTitle')
        self.resume_title.setTextFormat(Qt.PlainText)
        self.resume_title.setWordWrap(True)
        self.resume_card.add(self.resume_title)
        self.resume_description = QLabel('Abra um modelo editável, execute uma simulação e registre suas observações. Os dados são calculados localmente.')
        self.resume_description.setWordWrap(True); self.resume_description.setObjectName('FieldHint')
        self.resume_card.add(self.resume_description)
        self.resume = PrimaryButton('Abrir na bancada', icon='arrow-right')
        self.resume.clicked.connect(self._resume)
        self.resume_card.body().addWidget(self.resume, 0, Qt.AlignLeft)
        self.overview.add(self.resume_card)
        self.question = QLabel(); self.question.setWordWrap(True); self.question.setObjectName('SectionSubtitle')
        self.question.setTextFormat(Qt.PlainText)
        self.resume_card.body().insertWidget(2, self.question)
        self.works_label = QLabel('Experimentos'); self.works_label.setObjectName('PanelTitle'); self.overview.add(self.works_label)
        self.works = QListWidget()
        self.works.setObjectName("WorkspaceList")
        self.works.setMinimumHeight(150)
        self.works.setAccessibleName('Experimentos do projeto')
        self.works.itemActivated.connect(lambda item: self.work_selected.emit(item.data(Qt.UserRole)))
        self.works.itemClicked.connect(lambda item: self.work_selected.emit(item.data(Qt.UserRole)))
        self.overview.add(self.works)
        self.recent = Surface('Execuções recentes', role='ProjectCard')
        self.recent_list = QListWidget()
        self.recent_list.setObjectName("WorkspaceList")
        self.recent_list.setAccessibleName('Execuções recentes com sua modalidade e data')
        self.recent_list.setMinimumHeight(150)
        self.recent_list.itemActivated.connect(lambda item: self.experiment_selected.emit(item.data(Qt.UserRole)))
        self.recent_list.itemClicked.connect(lambda item: self.experiment_selected.emit(item.data(Qt.UserRole)))
        self.recent.add(self.recent_list)
        self.overview.add(self.recent)
        links = FlowLayout()
        self.notebook = SecondaryButton('Abrir caderno', icon='book')
        self.notebook.clicked.connect(self.notebook_requested.emit)
        self.ideal = SecondaryButton('Comparar com a referência ideal', icon='comparison')
        self.ideal.clicked.connect(self.ideal_requested.emit)
        self.first_use = Surface('Seu primeiro experimento')
        start_actions = FlowLayout()
        for key, text, name, icon, signal in [
            ('examples_button', 'Abrir exemplos', 'Escolher um exemplo da biblioteca', 'book-stack', self.examples_requested),
            ('tutorial_button', 'Iniciar tutorial de Bell', 'Iniciar tutorial de Bell', 'play', self.tutorial_requested),
        ]:
            button = SecondaryButton(text, icon=icon)
            button.setAccessibleName(name)
            setattr(self, key, button)
            button.clicked.connect(signal.emit)
            start_actions.addWidget(button)
        self.first_use.body().addLayout(start_actions)
        self.overview.add(self.first_use)
        self.concept_toggle = GhostButton('Como interpretar os resultados', icon='help')
        self.concept_toggle.setCheckable(True)
        self.first_use.body().addWidget(self.concept_toggle, 0, Qt.AlignLeft)
        self.concepts = QLabel('Contagens são amostras das probabilidades. A esfera de Bloch representa o estado local de cada qubit.\nPureza global e pureza local são medidas distintas. A fidelidade depende da referência indicada.\nZNE extrapola um observável; não reconstrói um estado mitigado.')
        self.concepts.setWordWrap(True); self.concepts.hide()
        self.first_use.add(self.concepts)
        self.concept_toggle.toggled.connect(self.concepts.setVisible)
        self.recent.body().addWidget(self.ideal, 0, Qt.AlignLeft)
        history = GhostButton('Ver histórico', icon='history')
        history.clicked.connect(self.open_history.emit)
        links.addWidget(history)
        links.addWidget(self.notebook)
        self.overview.body().addLayout(links)
        self.overview.body().addStretch()
        self.dashboard_splitter.addWidget(self.overview)
        self.dashboard_splitter.setStretchFactor(1, 1)
        self.dashboard_splitter.setSizes([300, 840])
        self.body().addWidget(self.dashboard_splitter, 1)
        for view in (self.project_list, self.works, self.recent_list):
            view.setItemDelegate(_RecordRow(view))
            view.setMouseTracking(True)
        self._render()

    def set_mode(self, mode):
        self.mode = mode
        self._render()

    def _size_lists(self):
        scale = max(1, self.font().pixelSize()/15)
        for view, limit in ((self.project_list, 7), (self.works, 5), (self.recent_list, 4)):
            rows = sum(view.sizeHintForRow(i) for i in range(min(view.count(), limit)))
            view.setFixedHeight(max(round(44 * scale), rows + 4))
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
        self.question.setVisible(bool(self.question.text()))
        self.ideal_pair = ideal_pair
        self.ideal.setVisible(bool(ideal_pair))
        if ideal_pair:
            self.ideal.setToolTip('A: ' + ideal_pair[2] + '\nB: ' + ideal_pair[3] + '\nReferência: mesmo circuito sem ruído; não é evolução exata.')
        self.all_projects.setVisible(project is not None)
        self.projects_column.setVisible(project is None)
        self.create_project.setVisible(project is None)
        self.notebook.setEnabled(bool(project))
        self._render()

    def _toggle_work_list(self):
        self.set_mode('overview' if self.mode == 'experiments' else 'experiments')

    def _resume(self):
        if self._works:
            self.work_selected.emit(self._works[0]['id'])

    def _render(self):
        if not hasattr(self, 'recent_list'): return
        self.works.clear()
        for work in self._works:
            kind = 'Circuito livre' if work['kind'] == 'circuit' else 'Hamiltoniano'
            status = 'Rascunho em edição' if not work.get('executions') else 'Rascunho · execução disponível'
            item = QListWidgetItem(f"{work['title']}\n{kind} · {status}")
            item.setData(Qt.UserRole, work['id']); item.setToolTip(item.text()); self.works.addItem(item)
        show_works = bool(self._works) and self.mode == 'experiments'
        self.new_experiment.setVisible(bool(self._works) and self.project_name is not None)
        self.show_works.setVisible(bool(self._works))
        self.show_works.setText('Ver resumo' if show_works else 'Ver experimentos')
        self.works_label.setVisible(show_works); self.works.setVisible(show_works)
        self.resume_title.setText(self._works[0]['title'] if self._works else 'Comece uma investigação')
        self.resume_role.setVisible(bool(self._works))
        self.resume_card.setVisible(not show_works)
        if self._works:
            work = self._works[0]
            self.resume_description.setText(('Circuito livre' if work['kind'] == 'circuit' else 'Evolução por Hamiltoniano') + ' · ' + ('Última execução disponível; o rascunho permanece editável.' if work.get('executions') else 'Rascunho em edição · ainda sem execução.'))
        self.resume.setText('Abrir na bancada' if self._works else 'Novo experimento')
        self.resume.setMenu(None if self._works else self.new_experiment.menu())
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
        self.first_use.setVisible(not self._works and not records)
        if not self._works:
            self.resume_description.setText('Crie um experimento ou abra um modelo editável da biblioteca.')
        self._size_lists()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'dashboard_splitter'):
            self.dashboard_splitter.setOrientation(Qt.Vertical if self.width() < 900 * max(1, self.font().pixelSize()/15) else Qt.Horizontal)
