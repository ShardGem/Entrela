"""Abas do laboratório sobre as instâncias e os estados já existentes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt, QSignalBlocker, Signal, QEvent, QTimer
from PySide6.QtWidgets import QLabel, QMenu, QTabWidget, QVBoxLayout, QWidget

from gui.widgets.button import SecondaryButton
from gui.widgets.flow_layout import FlowLayout


class ExperimentWorkspace(QWidget):
    """Agrupa o trabalho, sem executar operações nem manter outra cópia dos dados."""

    page_selected = Signal(str)
    template_requested = Signal(str)
    recent_requested = Signal(str)
    configurations_requested = Signal()

    KEYS = ("simulation", "circuit", "results", "bloch", "library")

    TABS = (
        (
            "simulation", "Configurar",
            "Edite o rascunho de uma evolução por Hamiltoniano. Este formulário é independente do editor de portas e não altera a execução selecionada.",
        ),
        (
            "circuit", "Circuitos",
            "Inspecione a execução ou edite um circuito livre de portas. O editor tem parâmetros próprios, independentes do rascunho Hamiltoniano.",
        ),
        (
            "results", "Resultados",
            "Consulte os resultados calculados da execução selecionada. Editar parâmetros não altera esse registro.",
        ),
        (
            "bloch", "Estados 3D",
            "Explore os snapshots salvos na execução. Ative o registro de estados antes de executar para gerá-los.",
        ),
        (
            "library", "Caderno",
            "Anote a execução selecionada e reutilize configurações salvas, preservando os resultados originais.",
        ),
    )

    def __init__(self, pages: Mapping[str, QWidget], parent=None):
        super().__init__(parent)
        self._selected_label_timer = QTimer(self)
        self._selected_label_timer.setSingleShot(True)
        self._selected_label_timer.setInterval(0)
        self._selected_label_timer.timeout.connect(self._fit_selected_label)
        keys = [key for key, _, _ in self.TABS]
        if any(key not in pages or not isinstance(pages[key], QWidget) for key in keys):
            raise ValueError("O laboratório precisa das cinco páginas existentes.")
        if len({id(pages[key]) for key in keys}) != len(keys):
            raise ValueError("Cada aba do laboratório precisa de uma página distinta.")
        self._keys = keys
        self._running = False
        self._context_actions = []
        self.setObjectName("PageSurface")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.toolbar = QWidget()
        tools = FlowLayout(self.toolbar)
        tools.setContentsMargins(20, 8, 20, 8)
        self.templates_button = SecondaryButton("Parâmetros salvos")
        self.templates_button.setAccessibleName("Abrir configurações salvas")
        self.templates_button.setToolTip(
            "Reutilize parâmetros salvos do formulário de simulação. Carregar não executa a simulação."
        )
        self.templates_menu = QMenu(self.templates_button)
        self.templates_menu.setToolTipsVisible(True)
        self.templates_button.setMenu(self.templates_menu)
        tools.addWidget(self.templates_button)

        self.recent_button = SecondaryButton("Execuções recentes")
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

        self.tabs = QTabWidget()
        self.tabs.setObjectName("WorkbenchTabs")
        self.tabs.setDocumentMode(True)
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

    @property
    def current_page_key(self) -> str:
        return self._keys[self.tabs.currentIndex()]

    def select_page(self, key: str):
        """Seleciona uma aba a pedido do controlador, sem emitir outra navegação."""
        if key not in self._keys:
            raise ValueError("Página fora do laboratório: " + str(key))
        blocker = QSignalBlocker(self.tabs)
        self.tabs.setCurrentIndex(self._keys.index(key))
        del blocker
        self._update_context_actions()

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
        self.selected_label.setVisible(self.current_page_key not in ("simulation", "circuit"))

    def _selected(self, index: int):
        if 0 <= index < len(self._keys):
            self._update_context_actions()
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

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "selected_label"):
            self._selected_label_timer.start()
