"""Abas do laboratório sobre as instâncias e os estados já existentes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, QSignalBlocker, Signal
from PySide6.QtWidgets import QMenu, QTabBar, QVBoxLayout, QWidget

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
        self.templates_button = SecondaryButton("Configurações salvas")
        self.templates_button.setAccessibleName("Abrir configurações salvas")
        self.templates_button.setToolTip(
            "Reutilize parâmetros salvos do formulário de simulação. Carregar não executa a simulação."
        )
        self.templates_menu = QMenu(self.templates_button)
        self.templates_menu.setToolTipsVisible(True)
        self.templates_button.setMenu(self.templates_menu)

        self.recent_button = SecondaryButton("Execuções…")
        self.recent_button.setAccessibleName("Abrir execuções recentes")
        self.recent_button.setToolTip("Abra resultados de uma execução salva sem procurar outra tela.")
        self.recent_menu = QMenu(self.recent_button)
        self.recent_menu.setToolTipsVisible(True)
        self.recent_button.setMenu(self.recent_menu)

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
        self._pages = pages
        if hasattr(pages["results"], "results_tab"):
            pages["results"].results_tab.chart_views.hide()
        self.observation_tabs = QTabBar()
        self.observation_tabs.setObjectName('ObservationTabs')
        self.observation_tabs.setDrawBase(False)
        self.observation_tabs.setExpanding(False)
        self.observation_tabs.setUsesScrollButtons(True)
        self.observation_tabs.setAccessibleName('Visualizações da execução')
        for text in ('Medições', 'Evolução', 'Bloch', 'Estado global', 'Dados'):
            self.observation_tabs.addTab(text)
        tools.addWidget(self.observation_tabs)
        details = SecondaryButton('Mais visualizações')
        menu = QMenu(details)
        menu.addAction('Medições e evolução lado a lado', self._paired_charts)
        menu.addSeparator()
        self._detail_actions = {}
        for route, title in self.RESULTS:
            if route in ('circuit:inspect', 'results:interpretation', 'results:metadata'):
                action = menu.addAction(title, lambda checked=False, key=route: self._apply_route(key, True))
                action.setCheckable(True)
                self._detail_actions[route] = action
        details.setMenu(menu)
        tools.addWidget(details)
        tools.addWidget(self.recent_button)
        root.insertWidget(0, self.toolbar)
        self.observation_tabs.tabBarClicked.connect(self._observation_clicked)
        self.observation_tabs.currentChanged.connect(self._observation_selected)
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

    def _observation_clicked(self, index):
        if index >= 0 and index == self.observation_tabs.currentIndex():
            self._observation_selected(index)

    def _observation_selected(self, index):
        if index < 0:
            return
        if index in (0, 1):
            self._pages['results'].results_tab.chart_views.setCurrentIndex(index)
            self._apply_route('results:graphs', True)
        else:
            self._apply_route({2:'bloch', 3:'results:state', 4:'results:data'}[index], True)

    def _paired_charts(self):
        self._pages['results'].results_tab.chart_views.setCurrentIndex(2)
        self._apply_route('results:graphs', True)

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
        self.toolbar.setVisible(not preparation)
        for route, action in self._detail_actions.items():
            action.setChecked(self._route == route)
        chart_views = getattr(self._pages['results'], 'results_tab', None)
        chart_index = chart_views.chart_views.currentIndex() if chart_views else 0
        route_index = {
            'bloch': 2, 'results:state': 3, 'results:data': 4,
            'results:graphs': chart_index if chart_index < 2 else 0,
        }.get(self._route, -1)
        with QSignalBlocker(self.observation_tabs):
            current = self.observation_tabs.currentIndex()
            if route_index >= 0:
                self.observation_tabs.setCurrentIndex(route_index)
            elif current >= 0:
                self.observation_tabs.setCurrentIndex(0)

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

    def set_selected_experiment(self, title: str | None, kind: str | None):
        if title:
            kinds = {"ham": "Hamiltoniano", "hamiltonian": "Hamiltoniano", "circuit": "Circuito de portas"}
            if kind not in kinds:
                raise ValueError("Tipo de execução desconhecido no laboratório.")
            self.recent_button.setToolTip(f"Execução selecionada: {title} · {kinds[kind]}")
        else:
            self.recent_button.setToolTip("Abra um resultado salvo para explorar a execução.")
