"""Abas do laboratório sobre as instâncias e os estados já existentes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, QSignalBlocker, Signal, QEvent, QTimer
from PySide6.QtWidgets import QLabel, QMenu, QTabWidget, QTabBar, QComboBox, QVBoxLayout, QWidget

from gui.widgets.button import SecondaryButton
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.content_tabs import ContentTabs


class ExperimentWorkspace(QWidget):
    """Agrupa o trabalho, sem executar operações nem manter outra cópia dos dados."""

    page_selected = Signal(str)
    template_requested = Signal(str)
    recent_requested = Signal(str)
    configurations_requested = Signal()

    KEYS = ("simulation", "circuit", "results", "bloch")
    TABS = (("simulation", "Hamiltoniano", "Preparar uma evolução por Hamiltoniano."),
            ("circuit", "Circuito", "Construir ou consultar circuitos."),
            ("results", "Resultados", "Resultados calculados da execução selecionada."),
            ("bloch", "Estados", "Estado final e snapshots efetivamente registrados."))
    PREPARATION = (("simulation", "Evoluir por Hamiltoniano"), ("circuit:edit", "Montar circuito de portas"))
    RESULTS = (("results:graphs", "Resumo e gráficos"), ("bloch", "Estados quânticos"),
               ("circuit:inspect", "Circuito executado"), ("results:data", "Dados das medições"),
               ("results:interpretation", "Interpretar resultado"), ("results:metadata", "Origem e reprodutibilidade"),
               ("results:state", "Matriz do estado final"))

    def __init__(self, pages: Mapping[str, QWidget], parent=None):
        super().__init__(parent)
        self._selected_label_timer = QTimer(self)
        self._selected_label_timer.setSingleShot(True)
        self._selected_label_timer.setInterval(0)
        self._selected_label_timer.timeout.connect(self._fit_selected_label)
        keys = [key for key, _, _ in self.TABS]
        if any(key not in pages or not isinstance(pages[key], QWidget) for key in keys):
            raise ValueError("O laboratório precisa das quatro páginas existentes.")
        if len({id(pages[key]) for key in keys}) != len(keys):
            raise ValueError("Cada aba do laboratório precisa de uma página distinta.")
        self._keys = keys
        self._running = False
        self._route = "simulation"
        self._last_preparation = "simulation"
        self._last_result = "results:graphs"
        self._context_actions = []
        self._draft_names = {"simulation": "Hamiltoniano", "circuit:edit": "circuito de portas"}
        self.setObjectName("PageSurface")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.toolbar = QWidget()
        tools = FlowLayout(self.toolbar)
        tools.setContentsMargins(20, 2, 20, 6)
        self.stages = QTabBar()
        self.stages.setObjectName('WorkspaceStages')
        self.stages.setDrawBase(False)
        self.stages.addTab('Preparar')
        self.stages.addTab('Resultados')
        self.stages.setAccessibleName('Preparação ou consulta da execução')
        tools.addWidget(self.stages)
        self.stages.hide()
        self.view_selector = QComboBox()
        self.view_selector.setAccessibleName('Atividade do laboratório')
        self.view_selector.setMinimumContentsLength(17)
        self.view_selector.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        tools.addWidget(self.view_selector)
        self.draft_label = QLabel('Configuração em edição')
        self.draft_label.setObjectName('FieldHint')
        self.draft_label.setMaximumWidth(350)
        tools.addWidget(self.draft_label)
        self.templates_button = SecondaryButton("Configurações salvas")
        self.templates_button.setAccessibleName("Abrir configurações salvas")
        self.templates_button.setToolTip(
            "Reutilize parâmetros salvos do formulário de simulação. Carregar não executa a simulação."
        )
        self.templates_menu = QMenu(self.templates_button)
        self.templates_menu.setToolTipsVisible(True)
        self.templates_button.setMenu(self.templates_menu)
        tools.addWidget(self.templates_button)

        self.recent_button = SecondaryButton("Escolher execução")
        self.recent_button.setAccessibleName("Abrir execuções recentes")
        self.recent_button.setToolTip("Abra resultados de uma execução salva sem procurar outra tela.")
        self.recent_menu = QMenu(self.recent_button)
        self.recent_menu.setToolTipsVisible(True)
        self.recent_button.setMenu(self.recent_menu)
        tools.addWidget(self.recent_button)

        self.status_label = QLabel("Tarefa em andamento…")
        self.status_label.setTextFormat(Qt.PlainText)
        self.status_label.setObjectName("FieldHint")
        self.status_label.setAccessibleName("Estado do laboratório")
        self.status_label.hide()
        tools.addWidget(self.status_label)
        self.selected_label = QLabel("Nenhuma execução selecionada")
        self.selected_label.setObjectName("FieldHint")
        self.selected_label.setTextFormat(Qt.PlainText)
        self.selected_label.setWordWrap(False)
        self.selected_label.setMaximumWidth(440)
        self._selected_text = "Nenhuma execução selecionada"
        self.selected_label.setAccessibleName("Execução selecionada no laboratório")
        self.selected_label.setToolTip(
            "Resultados, estados 3D e caderno pertencem à execução selecionada. "
            "Os formulários de configuração e circuito são rascunhos independentes."
        )
        tools.addWidget(self.selected_label)
        root.addWidget(self.toolbar)

        self.tabs = ContentTabs()
        self.tabs.setObjectName("WorkbenchTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().hide()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.ElideRight)
        self.tabs.tabBar().setDrawBase(False)
        self.tabs.setAccessibleName("Etapas do laboratório")
        for key, title, explanation in self.TABS:
            index = self.tabs.addTab(pages[key], title)
            self.tabs.setTabToolTip(index, explanation)
            self.tabs.setTabWhatsThis(index, explanation)
        self.tabs.currentChanged.connect(self._selected)
        root.addWidget(self.tabs, 1)
        self.set_templates([])
        self.set_recent([])
        self.stages.currentChanged.connect(lambda index: self._apply_route(self._last_preparation if index == 0 else self._last_result, True))
        self.view_selector.currentIndexChanged.connect(lambda *_: self._apply_route(self.view_selector.currentData(), True))
        self._pages = pages
        self._apply_route('simulation')

    @property
    def current_page_key(self) -> str:
        return self._keys[self.tabs.currentIndex()]

    def select_page(self, key: str):
        if key not in self._keys:
            raise ValueError('Página fora do laboratório: ' + str(key))
        if key == 'circuit' and hasattr(self._pages[key], 'tabs'):
            route = 'circuit:edit' if self._pages[key].tabs.currentWidget() is self._pages[key].editor else 'circuit:inspect'
        elif key == 'results' and hasattr(self._pages[key], 'tabs'):
            page = self._pages[key]
            route = 'results:' + {page.results_tab:'graphs', page.table:'data', page.metadata:'metadata',
                                 page.interpretation:'interpretation', page.state_inspector:'state'}[page.tabs.currentWidget()]
        else:
            route = {'circuit':'circuit:edit', 'results':'results:graphs'}.get(key, key)
        self._apply_route(route)

    def _apply_route(self, route, emit=False):
        if not route or not hasattr(self, '_pages'):
            return
        key, _, detail = route.partition(':')
        preparation = route in ('simulation', 'circuit:edit')
        self._route = route
        if preparation:
            self._last_preparation = route
        else:
            self._last_result = route
        stage_block = QSignalBlocker(self.stages)
        self.stages.setCurrentIndex(0 if preparation else 1)
        del stage_block
        view_block = QSignalBlocker(self.view_selector)
        self.view_selector.clear()
        for value, label in self.PREPARATION if preparation else self.RESULTS:
            self.view_selector.addItem(label, value)
        self.view_selector.setCurrentIndex(self.view_selector.findData(route))
        del view_block
        if key == 'circuit' and hasattr(self._pages[key], 'tabs'):
            page = self._pages[key]
            page.tabs.tabBar().hide()
            page.tabs.setCurrentWidget(page.editor if detail == 'edit' else page.inspector)
        elif key == 'results' and hasattr(self._pages[key], 'tabs'):
            page = self._pages[key]
            page.tabs.tabBar().hide()
            page.tabs.setCurrentWidget({'graphs':page.results_tab, 'data':page.table, 'metadata':page.metadata,
                                       'interpretation':page.interpretation, 'state':page.state_inspector}[detail])
        blocker = QSignalBlocker(self.tabs)
        self.tabs.setCurrentIndex(self._keys.index(key))
        del blocker
        self._update_context_actions()
        if emit:
            self.page_selected.emit(key)

    def add_context_action(self, widget: QWidget, key: str):
        """Reutiliza uma ação existente na faixa comum, somente no seu contexto."""
        if key not in self._keys:
            raise ValueError("Página fora do laboratório: " + key)
        self.toolbar.layout().addWidget(widget)
        self._context_actions.append((widget, key))
        self._update_context_actions()

    def _update_context_actions(self):
        for widget, key in self._context_actions:
            widget.setVisible(key == self.current_page_key)
        preparation = self._route in ('simulation', 'circuit:edit')
        self.selected_label.setVisible(not preparation)
        self.draft_label.hide()
        self.view_selector.setVisible(self._route.startswith("results:") or self._route == "circuit:inspect")
        self.templates_button.setVisible(self._route == 'simulation')
        self.recent_button.setVisible(not preparation)
        context = 'Em edição: ' + self._draft_names.get(self._route, '')
        self.draft_label.setText(self.draft_label.fontMetrics().elidedText(context, Qt.ElideRight, 350))
        self.draft_label.setToolTip(context)

    def set_draft_name(self, kind, name):
        if kind not in self._draft_names:
            raise ValueError('Modalidade de preparação desconhecida')
        self._draft_names[kind] = name.strip() or ('Hamiltoniano' if kind == 'simulation' else 'circuito de portas')
        self._update_context_actions()

    def _selected(self, index: int):
        if 0 <= index < len(self._keys):
            self.select_page(self._keys[index])
            self.page_selected.emit(self._keys[index])

    @staticmethod
    def _menu_label(text: str) -> str:
        # Em menus Qt, && é a representação literal de &; não cria atalhos.
        return text.replace("&", "&&")

    def set_templates(self, entries: Sequence[Mapping[str, str]]):
        self.templates_menu.clear()
        for entry in entries:
            identifier, name = entry["id"], entry["name"]
            if not isinstance(identifier, str) or not isinstance(name, str):
                raise ValueError("Configuração salva precisa de identificador e nome textuais.")
            action = self.templates_menu.addAction(self._menu_label(name))
            action.setToolTip("Carregar uma cópia dos parâmetros na aba Configurar.")
            action.triggered.connect(
                lambda checked=False, key=identifier: self.template_requested.emit(key)
            )
        if not entries:
            empty = self.templates_menu.addAction("Nenhuma configuração salva")
            empty.setEnabled(False)
        self.templates_menu.addSeparator()
        manage = self.templates_menu.addAction("Salvar ou gerenciar configurações…")
        manage.triggered.connect(lambda checked=False: self.configurations_requested.emit())
        self.templates_button.setEnabled(not self._running)

    def set_recent(self, entries: Sequence[tuple[str, str]]):
        self.recent_menu.clear()
        for identifier, title in entries:
            if not isinstance(identifier, str) or not isinstance(title, str):
                raise ValueError("Execução recente precisa de identificador e nome textuais.")
            action = self.recent_menu.addAction(self._menu_label(title))
            action.setToolTip("Abrir os resultados desta execução salva.")
            action.triggered.connect(
                lambda checked=False, key=identifier: self.recent_requested.emit(key)
            )
        if not entries:
            empty = self.recent_menu.addAction("Nenhuma execução salva")
            empty.setEnabled(False)
        self.recent_button.setEnabled(not self._running)

    def set_running(self, running: bool):
        self._running = bool(running)
        self.templates_button.setEnabled(not running)
        self.recent_button.setEnabled(not running)
        self.status_label.setVisible(bool(running))

    def set_selected_experiment(self, title: str | None, kind: str | None):
        """Mostra o contexto recebido do controlador, sem armazenar o experimento."""
        explanation = (
            "Resultados, estados 3D e caderno pertencem à execução selecionada. "
            "Os formulários de configuração e circuito são rascunhos independentes; "
            "mudar de aba ou editar parâmetros não altera essa execução."
        )
        if not title:
            self._selected_text = "Nenhuma execução selecionada"
            self._fit_selected_label()
            self.selected_label.setAccessibleDescription(explanation)
            self.selected_label.setToolTip(explanation)
            return
        kinds = {"ham": "Hamiltoniano", "hamiltonian": "Hamiltoniano", "circuit": "Circuito de portas"}
        if kind not in kinds:
            raise ValueError("Tipo de execução desconhecido no laboratório.")
        context = f"{kinds[kind]} · {title}"
        self._selected_text = context
        self._fit_selected_label()
        self.selected_label.setAccessibleDescription("Execução selecionada: " + context + ". " + explanation)
        self.selected_label.setToolTip("Execução selecionada: " + context + "\n" + explanation)

    def _fit_selected_label(self):
        self.selected_label.setText(self.selected_label.fontMetrics().elidedText(self._selected_text, Qt.ElideRight, 430))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_pages"):
            self._update_context_actions()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "selected_label"):
            self._selected_label_timer.start()
