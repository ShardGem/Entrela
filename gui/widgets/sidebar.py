"""Destinos do laboratório, com seções independentes e acesso por teclado."""

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget

from gui.branding import application_icon
from gui.icons import get_icon, get_pixmap
from gui.navigation import NAV_GROUPS, NAV_ICONS, NAV_ITEMS, NAV_LABELS
from gui.theme import PALETTE


class NavButton(QPushButton):
    def __init__(self, icon_name, label, parent=None):
        super().__init__(label, parent)
        self.icon_name = icon_name
        self.label = label
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(34)
        self.setAccessibleName(label)
        self.setIconSize(QSize(16, 16))
        self.toggled.connect(self.refresh_theme)
        self.refresh_theme()

    def refresh_theme(self):
        color = PALETTE.chrome_accent if self.isChecked() else PALETTE.chrome_muted
        self.setIcon(get_icon(self.icon_name, color))


class _SectionToggle(QPushButton):
    def __init__(self, title):
        super().__init__(title)
        self.setObjectName("NavGroup")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(25)

    def paintEvent(self, event):
        super().paintEvent(event)
        glyph = "chevron-down" if self.isChecked() else "next"
        pixmap = get_pixmap(glyph, PALETTE.chrome_muted, 13)
        painter = QPainter(self)
        painter.drawPixmap(self.width() - 23, (self.height() - 13) // 2, pixmap)


class Sidebar(QFrame):
    navigate = Signal(str)
    compact_requested = Signal(bool)
    search_requested = Signal()
    help_requested = Signal()
    new_requested = Signal()
    sections_changed = Signal(list)

    ITEMS = NAV_ITEMS
    GROUPS = NAV_GROUPS
    DESCRIPTIONS = {
        'dashboard': 'Retome o experimento em andamento ou abra uma investigação.',
        'simulation': 'Configure o sistema e execute uma evolução por Hamiltoniano.',
        'circuit': 'Monte e teste circuitos de portas.',
        'results': 'Consulte medições, evolução e estado global da execução.',
        'bloch': 'Inspecione os estados locais e navegue entre snapshots.',
        'analysis': 'Investigue a precisão, o ruído e a sensibilidade a parâmetros.',
        'mitigation': 'Extrapole a estimativa de um observável por ZNE.',
        'comparison': 'Compare duas execuções compatíveis.',
        'history': 'Pesquise e reabra execuções salvas.',
        'notebook': 'Registre anotações, reúna evidências e exporte relatórios.',
        'catalog': 'Explore exemplos, modelos e circuitos reutilizáveis.',
        'docs': 'Consulte conceitos e instruções do laboratório.',
        'settings': 'Ajuste aparência, acessibilidade, exportação e backup.',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.buttons = {}
        self.group_buttons = {}
        self.group_bodies = {}
        self._compact = False
        self._active = "dashboard"
        self._expanded_groups = {key for key, _, _ in self.GROUPS}
        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.timeout.connect(self._fit_width)
        self._build()
        self.refresh_theme()
        self.set_active("dashboard")

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 7, 11, 4)
        outer.setSpacing(4)
        self.brand_box = QWidget()
        brand = QHBoxLayout(self.brand_box)
        brand.setContentsMargins(3, 2, 0, 8)
        brand.setSpacing(8)
        self.logo = QLabel()
        self.logo.setFixedSize(27, 27)
        self.logo.setAlignment(Qt.AlignCenter)
        brand.addWidget(self.logo)
        self.logo_title = QLabel("Entrela")
        self.logo_title.setObjectName("SidebarLogo")
        brand.addWidget(self.logo_title, 1)
        self.toggle = QToolButton()
        self.toggle.setObjectName("SidebarToggle")
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setMinimumSize(28, 31)
        self.toggle.setIconSize(QSize(16, 16))
        self.toggle.clicked.connect(lambda: self.compact_requested.emit(not self._compact))
        brand.addWidget(self.toggle)
        outer.addWidget(self.brand_box)

        self.search = NavButton("search", "Buscar")
        self.search.setObjectName("SearchButton")
        self.search.setCheckable(False)
        self.search.setToolTip("Buscar telas, ações e experimentos (Ctrl+K)")
        self.search.clicked.connect(self.search_requested.emit)
        search_layout = QHBoxLayout(self.search)
        search_layout.setContentsMargins(0, 0, 8, 0)
        search_layout.addStretch()
        self.search_key = QLabel(QKeySequence("Ctrl+K").toString(QKeySequence.NativeText))
        self.search_key.setObjectName("NavShortcut")
        self.search_key.setAttribute(Qt.WA_TransparentForMouseEvents)
        search_layout.addWidget(self.search_key, 0, Qt.AlignVCenter)
        outer.addWidget(self.search)
        outer.addSpacing(5)

        projects_row = QHBoxLayout()
        projects_row.setSpacing(3)
        self.buttons["dashboard"] = self._make_button("dashboard")
        projects_row.addWidget(self.buttons["dashboard"], 1)
        self.new_button = QToolButton()
        self.new_button.setObjectName("SidebarToggle")
        self.new_button.setIconSize(QSize(16, 16))
        self.new_button.setMinimumSize(29, 31)
        self.new_button.setToolTip("Novo experimento (Ctrl+N)")
        self.new_button.setAccessibleName("Novo experimento")
        self.new_button.clicked.connect(self.new_requested.emit)
        projects_row.addWidget(self.new_button)
        outer.addLayout(projects_row)

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        groups = QVBoxLayout(content)
        groups.setContentsMargins(0, 0, 0, 0)
        groups.setSpacing(4)
        for key, title, items in self.GROUPS:
            header = _SectionToggle(title)
            header.clicked.connect(lambda checked, section=key: self._toggle_section(section, checked))
            self.group_buttons[key] = header
            groups.addWidget(header)

            body = QWidget()
            children = QVBoxLayout(body)
            children.setContentsMargins(0, 0, 0, 3)
            children.setSpacing(1)
            for page in items:
                button = self._make_button(page)
                children.addWidget(button)
                self.buttons[page] = button
            self.group_bodies[key] = body
            groups.addWidget(body)
        groups.addStretch()
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)

        rule = QFrame()
        rule.setObjectName("SidebarDivider")
        rule.setFixedHeight(1)
        outer.addWidget(rule)
        self.buttons["docs"] = self._make_button("docs")
        outer.addWidget(self.buttons["docs"])
        self.help_button = NavButton("help", "Ajuda contextual")
        self.help_button.setCheckable(False)
        self.help_button.setToolTip("Ajuda da área em uso (F1)")
        self.help_button.clicked.connect(self.help_requested.emit)
        outer.addWidget(self.help_button)
        self.buttons["settings"] = self._make_button("settings")
        outer.addWidget(self.buttons["settings"])

    def _make_button(self, key):
        label = NAV_LABELS[key]
        button = NavButton(NAV_ICONS.get(key, key), label)
        button.setToolTip(label + "\n" + self.DESCRIPTIONS[key])
        button.setAccessibleDescription(self.DESCRIPTIONS[key])
        button.clicked.connect(lambda checked=False: self._on_click(key))
        return button

    def _toggle_section(self, key, opened):
        if opened:
            self._expanded_groups.add(key)
        else:
            self._expanded_groups.discard(key)
        self._refresh_sections()
        self.sections_changed.emit(sorted(self._expanded_groups))

    def restore_sections(self, expanded):
        if isinstance(expanded, str):
            expanded = [expanded]
        if isinstance(expanded, list):
            self._expanded_groups = {key for key, _, _ in self.GROUPS if key in expanded}
            self._refresh_sections()

    def _refresh_sections(self):
        for key, title, items in self.GROUPS:
            opened = key in self._expanded_groups
            header = self.group_buttons[key]
            header.setChecked(opened)
            header.setAccessibleName(f"{title} · {'expandido' if opened else 'recolhido'}")
            header.setToolTip(('Recolher ' if opened else 'Expandir ') + title)
            self.group_bodies[key].setVisible(opened)

    def _on_click(self, key):
        self.navigate.emit(key)
        self.buttons[key].setChecked(key == self._active)

    def set_active(self, key):
        self._active = key
        for page, button in self.buttons.items():
            button.setChecked(page == key)
        for group, _, items in self.GROUPS:
            if key in items:
                self._expanded_groups.add(group)
                break
        self._refresh_sections()
        if key in self.buttons and self.scroll.isAncestorOf(self.buttons[key]):
            self.scroll.ensureWidgetVisible(self.buttons[key])

    def set_compact(self, compact):
        self._compact = bool(compact)
        self._refresh_controls()

    def _refresh_controls(self):
        self.toggle.setIcon(get_icon("expand" if self._compact else "collapse", PALETTE.chrome_muted))
        label = "Expandir navegação" if self._compact else "Recolher navegação"
        self.toggle.setToolTip(label)
        self.toggle.setAccessibleName(label)
        self.new_button.setIcon(get_icon("plus", PALETTE.chrome_muted))
        self.search_key.setVisible(not self._compact)
        self.new_button.setVisible(not self._compact)
        self._fit_width()

    def _fit_width(self):
        buttons = (*self.buttons.values(), self.help_button)
        margins = self.layout().contentsMargins()
        horizontal = margins.left() + margins.right()
        scrollbar = self.scroll.verticalScrollBar().sizeHint().width()
        if self._compact:
            word_width = max(
                button.fontMetrics().horizontalAdvance(word)
                for button in buttons for word in button.label.split()
            )
            headers = max(button.sizeHint().width() for button in self.group_buttons.values())
            width = max(157, word_width + 42 + horizontal + scrollbar, headers + horizontal + scrollbar)
            available = width - horizontal - scrollbar - 42
            for button in buttons:
                lines = [""]
                for word in button.label.split():
                    candidate = (lines[-1] + " " + word).strip()
                    if lines[-1] and button.fontMetrics().horizontalAdvance(candidate) > available:
                        lines.append(word)
                    else:
                        lines[-1] = candidate
                button.setText("\n".join(lines))
                button.setMinimumHeight(max(34, len(lines) * button.fontMetrics().height() + 10))
        else:
            for button in buttons:
                button.setText(button.label)
                button.setMinimumHeight(34)
            width = max(221, max(button.sizeHint().width() for button in buttons) + horizontal + scrollbar)
        self.setFixedWidth(width)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "search"):
            self._width_timer.start(0)

    def refresh_theme(self):
        self.logo.setPixmap(application_icon().pixmap(22, 22))
        self._refresh_controls()
        for header in self.group_buttons.values():
            header.update()
