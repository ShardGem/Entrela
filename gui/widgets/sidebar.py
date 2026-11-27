"""Destinos do laboratório, com seções independentes e acesso por teclado."""

from PySide6.QtCore import QEvent, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QToolButton, QVBoxLayout, QWidget

from gui.branding import application_icon
from gui.icons import get_icon, get_pixmap
from gui.navigation import NAV_GROUPS, NAV_ICONS, NAV_ITEMS, NAV_LABELS
from gui.theme import PALETTE
from gui.widgets.button import PrimaryButton


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
        self.setIcon(get_icon(self.icon_name, self._icon_color()))

    def _icon_color(self):
        return PALETTE.chrome_accent if self.isChecked() else PALETTE.chrome_muted


class _SectionToggle(NavButton):
    def __init__(self, icon_name, title):
        self._active_section = False
        super().__init__(icon_name, title)
        self.setObjectName("NavGroup")
        self.setMinimumHeight(33)

    def set_active_section(self, active):
        if self._active_section != active:
            self._active_section = active
            self.setProperty("activeSection", active)
            self.style().unpolish(self)
            self.style().polish(self)
            self.refresh_theme()

    def _icon_color(self):
        return PALETTE.chrome_accent if self._active_section else PALETTE.chrome_muted

    def refresh_theme(self):
        super().refresh_theme()
        glyph = "chevron-down" if self.isChecked() else "chevron-right"
        self._chevron = get_pixmap(glyph, self._icon_color(), 14)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.drawPixmap(self.width() - 24, (self.height() - 14) // 2, self._chevron)


class Sidebar(QFrame):
    navigate = Signal(str)
    compact_requested = Signal(bool)
    search_requested = Signal()
    help_requested = Signal()
    sections_changed = Signal(list)

    ITEMS = NAV_ITEMS
    GROUPS = NAV_GROUPS
    CHILD_INDENT = 14
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
        self._expanded_groups = {key for key, *_ in self.GROUPS}
        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.timeout.connect(self._fit_width)
        self._build()
        for button in self._rows():
            button.installEventFilter(self)
        self.refresh_theme()
        self.set_active("dashboard")

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 9, 11, 6)
        outer.setSpacing(3)
        self.brand_box = QWidget()
        brand = QHBoxLayout(self.brand_box)
        brand.setContentsMargins(0, 2, 0, 10)
        brand.setSpacing(8)
        self.logo = QLabel()
        self.logo.setObjectName("SidebarMark")
        self.logo.setFixedSize(32, 32)
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

        self.new_button = PrimaryButton("Novo experimento", icon="plus")
        self.new_button.setMinimumHeight(40)
        self.new_button.setIconSize(QSize(16, 16))
        self.new_button.setAccessibleName(self.new_button.text())
        self.new_button.setAccessibleDescription("Escolha o tipo de experimento. Atalho Ctrl+N.")
        self.new_button.setToolTip("Escolher entre evolução por Hamiltoniano e circuito de portas (Ctrl+N)")
        outer.addWidget(self.new_button)
        outer.addSpacing(4)

        self.search = NavButton("search", "Buscar")
        self.search.setObjectName("SearchButton")
        self.search.setCheckable(False)
        self.search.setToolTip("Buscar telas, ações, conceitos e experimentos")
        self.search.clicked.connect(self.search_requested.emit)
        outer.addWidget(self.search)
        outer.addSpacing(6)
        self._add_divider(outer)
        outer.addSpacing(3)

        self.buttons["dashboard"] = self._make_button("dashboard")
        outer.addWidget(self.buttons["dashboard"])

        self.scroll = QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        groups = QVBoxLayout(content)
        groups.setContentsMargins(0, 0, 0, 0)
        groups.setSpacing(3)
        for key, title, icon, items in self.GROUPS:
            header = _SectionToggle(icon, title)
            header.clicked.connect(lambda checked, section=key: self._toggle_section(section, checked))
            self.group_buttons[key] = header
            groups.addWidget(header)

            body = QWidget()
            branch = QHBoxLayout(body)
            branch.setContentsMargins(8, 0, 0, 5)
            branch.setSpacing(self.CHILD_INDENT - 9)
            guide = QFrame()
            guide.setObjectName("SidebarDivider")
            guide.setFixedWidth(1)
            branch.addWidget(guide)
            children = QVBoxLayout()
            branch.addLayout(children, 1)
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

        self._add_divider(outer)
        self.buttons["docs"] = self._make_button("docs")
        outer.addWidget(self.buttons["docs"])
        self.help_button = NavButton("help", "Ajuda contextual")
        self.help_button.setCheckable(False)
        self.help_button.setToolTip("Ajuda da área em uso (F1)")
        self.help_button.clicked.connect(self.help_requested.emit)
        outer.addWidget(self.help_button)
        self.buttons["settings"] = self._make_button("settings")
        outer.addWidget(self.buttons["settings"])

    @staticmethod
    def _add_divider(layout):
        rule = QFrame()
        rule.setObjectName("SidebarDivider")
        rule.setFixedHeight(1)
        layout.addWidget(rule)

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
            self._expanded_groups = {key for key, *_ in self.GROUPS if key in expanded}
            self._refresh_sections()

    def _refresh_sections(self):
        for key, title, _, items in self.GROUPS:
            opened = key in self._expanded_groups
            active = self._active in items
            header = self.group_buttons[key]
            header.setChecked(opened)
            header.set_active_section(active)
            header.setAccessibleName(f"{title} · {'expandido' if opened else 'recolhido'}")
            current = "Área atual: " + NAV_LABELS[self._active] if active else ""
            header.setAccessibleDescription(current)
            instruction = ("Recolher " if opened else "Expandir ") + title
            header.setToolTip(instruction + ("\n" + current if active else ""))
            self.group_bodies[key].setVisible(opened)

    def _on_click(self, key):
        self.navigate.emit(key)
        self.buttons[key].setChecked(key == self._active)

    def set_active(self, key):
        self._active = key
        for page, button in self.buttons.items():
            button.setChecked(page == key)
        for group, _, _, items in self.GROUPS:
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
        self._fit_width()

    def _rows(self):
        yield self.new_button
        yield self.search
        yield self.buttons["dashboard"]
        for key, _, _, items in self.GROUPS:
            yield self.group_buttons[key]
            for page in items:
                yield self.buttons[page]
        yield self.buttons["docs"]
        yield self.help_button
        yield self.buttons["settings"]

    def eventFilter(self, watched, event):
        if event.type() != QEvent.KeyPress or event.modifiers() != Qt.NoModifier:
            return super().eventFilter(watched, event)

        key = event.key()
        if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Home, Qt.Key_End):
            rows = [row for row in self._rows() if row.isVisibleTo(self) and row.isEnabled()]
            if watched in rows:
                position = rows.index(watched)
                index = {
                    Qt.Key_Up: max(0, position - 1),
                    Qt.Key_Down: min(len(rows) - 1, position + 1),
                    Qt.Key_Home: 0, Qt.Key_End: len(rows) - 1,
                }[key]
                self._focus_row(rows[index])
                return True

        if key in (Qt.Key_Left, Qt.Key_Right):
            for group, _, _, items in self.GROUPS:
                header = self.group_buttons[group]
                if watched is header:
                    opened = group in self._expanded_groups
                    if key == Qt.Key_Right and opened:
                        self._focus_row(self.buttons[items[0]])
                    elif opened != (key == Qt.Key_Right):
                        self._toggle_section(group, not opened)
                    return True
                if key == Qt.Key_Left and watched in (self.buttons[item] for item in items):
                    self._focus_row(header)
                    return True
        return super().eventFilter(watched, event)

    def _focus_row(self, row):
        row.setFocus(Qt.ShortcutFocusReason)
        if self.scroll.isAncestorOf(row):
            self.scroll.ensureWidgetVisible(row, 0, 4)

    def _fit_width(self):
        margins = self.layout().contentsMargins()
        horizontal = margins.left() + margins.right()
        scrollbar = self.scroll.verticalScrollBar().sizeHint().width()
        rows = [(self.help_button, 0)]
        rows += [(button, self.CHILD_INDENT + scrollbar if self.scroll.isAncestorOf(button) else 0)
                 for button in self.buttons.values()]
        headers = max(button.sizeHint().width() for button in self.group_buttons.values()) + scrollbar
        self.new_button.setText(self.new_button.accessibleName())
        create_width = self.new_button.sizeHint().width()

        if self._compact:
            longest = max(
                extra + button.fontMetrics().horizontalAdvance(word)
                for button, extra in rows for word in button.label.split()
            )
            width = max(166, longest + horizontal + 42, headers + horizontal)
            if width < create_width + horizontal:
                self.new_button.setText(self.new_button.text().replace(" ", "\n", 1))
                width = max(width, self.new_button.sizeHint().width() + horizontal)
            for button, extra in rows:
                available = width - horizontal - extra - 42
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
            for button, _ in rows:
                button.setText(button.label)
                button.setMinimumHeight(34)
            required = max(button.sizeHint().width() + extra for button, extra in rows)
            width = max(225, max(required, headers, create_width) + horizontal + 2)
        self.setFixedWidth(width)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and hasattr(self, "search"):
            self._width_timer.start(0)

    def refresh_theme(self):
        self.logo.setPixmap(application_icon().pixmap(22, 22))
        self._refresh_controls()
        for header in self.group_buttons.values():
            header.refresh_theme()
