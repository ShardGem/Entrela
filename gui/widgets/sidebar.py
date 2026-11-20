"""Navegação com grupos independentes e nomes visíveis nas duas larguras."""
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer
from PySide6.QtWidgets import QApplication,QFrame,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QToolButton,QLabel,QScrollArea
from gui.icons import get_icon
from gui.theme import PALETTE
from gui.branding import application_icon
from gui.navigation import NAV_ITEMS, NAV_GROUPS


class NavButton(QPushButton):
    def __init__(self,icon_name,label,parent=None):
        super().__init__(parent)
        self.icon_name=icon_name
        self.label=label
        self.setObjectName('NavButton')
        self.setCheckable(True)
        self.setAutoExclusive(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(38)
        self.setAccessibleName(label)
        self.setToolTip(label)
        self.setText('  '+label)
        self._refresh_icon()

    def _refresh_icon(self):
        self.setIcon(get_icon(self.icon_name, PALETTE.chrome_accent if self.isChecked() else PALETTE.chrome_muted))
        self.setIconSize(QSize(18,18))

    def setChecked(self,checked):
        super().setChecked(checked)
        self._refresh_icon()


class Sidebar(QFrame):
    navigate=Signal(str)
    compact_requested=Signal(bool)
    search_requested=Signal()
    help_requested=Signal()
    ITEMS = NAV_ITEMS
    GROUPS = NAV_GROUPS
    DESCRIPTIONS = {
        'dashboard': 'Retome uma execução recente ou comece um novo experimento.',
        'simulation': 'Defina estado inicial, Hamiltoniano, evolução, ruído e medições para executar uma simulação.',
        'circuit': 'Monte e edite portas, use modelos e salve revisões do circuito antes de executar.',
        'results': 'Consulte gráficos, dados, métricas e reprodutibilidade da execução selecionada.',
        'bloch': 'Inspecione esferas de Bloch, probabilidades e estado global nos snapshots ou no estado final calculado.',
        'analysis': 'Faça estudos e varreduras de ruído, parâmetros e precisão de Trotter a partir de uma execução.',
        'mitigation': 'Configure ZNE para extrapolar um observável e avaliar seu erro e sua incerteza.',
        'comparison': 'Compare métricas, gráficos e estados de duas execuções compatíveis.',
        'history': 'Pesquise, inspecione e reabra execuções salvas, ou selecione duas para comparar.',
        'notebook': 'Registre anotações, reúna evidências e exporte relatórios.',
        'catalog': 'Explore exemplos, configurações salvas e circuitos reutilizáveis.',
        'docs': 'Consulte conceitos, exemplos explicados, manual e referências científicas.',
        'settings': 'Ajuste aparência, acessibilidade, exportação e backup do espaço de trabalho.',
    }

    def __init__(self,parent=None):
        super().__init__(parent)
        self._width_timer = QTimer(self)
        self._width_timer.setSingleShot(True)
        self._width_timer.setInterval(0)
        self._width_timer.timeout.connect(self._fit_width)
        self.setObjectName('Sidebar')
        self.buttons={}
        self.group_buttons={}
        self.group_bodies={}
        self._animations={}
        self._compact=False
        self._active='dashboard'
        self._expanded_groups={key for key,_,_,_ in self.GROUPS}
        self._build()
        self.set_compact(False)
        self.set_active('dashboard')

    def _build(self):
        outer=QVBoxLayout(self)
        outer.setContentsMargins(11, 5, 10, 1)
        outer.setSpacing(4)
        self.brand_box = QWidget()
        brand=QHBoxLayout(self.brand_box)
        logo=QLabel()
        self.logo=logo
        logo.setObjectName("SidebarMark")
        logo.setPixmap(application_icon().pixmap(23, 23))
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(34, 34)
        brand.addWidget(logo)
        self.logo_title=QLabel('Entrela')
        self.logo_title.setObjectName('SidebarLogo')
        brand.addWidget(self.logo_title,1)
        outer.addWidget(self.brand_box)
        brand.setContentsMargins(3, 5, 0, 12)
        self.toggle=QToolButton()
        self.toggle.setObjectName('SidebarToggle')
        self.toggle.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setMinimumSize(28, 34)
        self.toggle.setIconSize(QSize(17,17))
        self.toggle.clicked.connect(lambda:self.compact_requested.emit(not self._compact))
        brand.addWidget(self.toggle)
        self.search = NavButton('search', 'Buscar')
        self.search.setObjectName("SearchButton")
        self.search.setCheckable(False)
        self.search.setToolTip('Buscar funções, experimentos e conceitos (Ctrl+K)')
        self.search.clicked.connect(self.search_requested.emit)
        outer.addWidget(self.search)
        self.scroll=QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget()
        layout=QVBoxLayout(content)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(4)
        for key,title,icon,items in self.GROUPS:
            header=QPushButton()
            header.setObjectName('NavGroup')
            header.setMinimumHeight(26)
            header.setIconSize(QSize(22,22))
            header.setCursor(Qt.PointingHandCursor)
            header.setAccessibleName(title+' — expandir ou recolher grupo')
            header.clicked.connect(lambda checked=False,key=key:self._expand(key))
            layout.addWidget(header)
            self.group_buttons[key]=header
            body=QWidget()
            children=QVBoxLayout(body)
            children.setContentsMargins(0, 0, 0, 0)
            children.setSpacing(2)
            for page in items:
                button = self._make_button(page, title)
                children.addWidget(button)
                self.buttons[page]=button
            self.group_bodies[key]=body
            animation=QPropertyAnimation(body,b'maximumHeight',self)
            animation.setDuration(180)
            animation.setEasingCurve(QEasingCurve.InOutCubic)
            animation.finished.connect(lambda key=key:self._finish_animation(key))
            self._animations[key]=animation
            layout.addWidget(body)
        layout.addStretch()
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll,1)
        self.buttons['docs'] = self._make_button('docs')
        outer.addWidget(self.buttons['docs'])
        self.help_button = NavButton('help', 'Ajuda contextual')
        self.help_button.setCheckable(False)
        self.help_button.setToolTip('Ajuda da área em uso (F1)')
        self.help_button.clicked.connect(self.help_requested.emit)
        outer.addWidget(self.help_button)
        self.buttons['settings'] = self._make_button('settings')
        outer.addWidget(self.buttons['settings'])

    def _make_button(self, key, group=None):
        label = dict(self.ITEMS)[key]
        icon = {'notebook': 'annotations', 'catalog': 'examples'}.get(key, key)
        button = NavButton(icon, label)
        context = f'{group} · {label}' if group else label
        button.setToolTip(context + '\n' + self.DESCRIPTIONS[key])
        button.setAccessibleDescription(self.DESCRIPTIONS[key])
        button.clicked.connect(lambda checked=False, key=key: self._on_click(key))
        return button

    def _expand(self,key):
        if key in self._expanded_groups:
            self._expanded_groups.remove(key)
        else:
            self._expanded_groups.add(key)
        self._refresh_groups(animate=True)

    def _finish_animation(self,key):
        body=self.group_bodies[key]
        expanded=key in self._expanded_groups
        body.setVisible(expanded)
        body.setMaximumHeight(16777215 if expanded else 0)

    def _refresh_groups(self,animate=False):
        app=QApplication.instance()
        motion=self.isVisible() and not bool(app.property('entrelaReduceMotion') if app else False)
        for key,title,icon,items in self.GROUPS:
            expanded=key in self._expanded_groups
            body=self.group_bodies[key]
            animation=self._animations[key]
            current=body.height() if body.isVisible() else 0
            changed=bool(body.property('expanded'))!=expanded
            animation.stop()
            body.setProperty('expanded',expanded)
            if animate and changed and motion:
                body.setVisible(True)
                body.setMaximumHeight(current)
                animation.setStartValue(current)
                animation.setEndValue(body.sizeHint().height() if expanded else 0)
                animation.start()
            else:
                self._finish_animation(key)
            button=self.group_buttons[key]
            button.setText(title)
            button.setCheckable(True)
            button.setChecked(expanded)
            button.setToolTip(title+(' — recolher grupo' if expanded else ' — expandir grupo')+'\n'+' · '.join(dict(self.ITEMS)[page] for page in items))
            button.setAccessibleName(title+(' — grupo expandido' if expanded else ' — grupo recolhido'))
            button.setProperty('activeGroup',self._active in items)
            button.setProperty('compact',self._compact)
            button.setProperty('expanded',expanded)
            button.style().unpolish(button)
            button.style().polish(button)
            button.setIcon(get_icon('chevron-down' if expanded else 'next', PALETTE.chrome_accent if self._active in items else PALETTE.chrome_muted))
            button.setIconSize(QSize(16,16))

    def _on_click(self,key):
        self.navigate.emit(key)
        self.buttons[key].setChecked(key == self._active)

    def set_active(self,key):
        self._active=key
        for page,button in self.buttons.items():
            button.setChecked(page==key)
        group=next((name for name,_,_,items in self.GROUPS if key in items),None)
        if group:
            self._expanded_groups.add(group)
        self._refresh_groups()
        if key in self.buttons:
            if self.scroll.isAncestorOf(self.buttons[key]):
                self.scroll.ensureWidgetVisible(self.buttons[key])

    def set_compact(self,compact):
        self._compact=bool(compact)
        self.toggle.setIcon(get_icon('expand' if compact else 'collapse',PALETTE.chrome_muted))
        self.toggle.setToolTip('Expandir navegação' if compact else 'Recolher navegação')
        self.toggle.setAccessibleName(self.toggle.toolTip())
        for button in (*self.buttons.values(), self.search, self.help_button):
            button.setText(button.label)
            button.setProperty('compact',bool(compact))
            button.style().unpolish(button)
            button.style().polish(button)
        self._refresh_groups()
        self._fit_width()

    def _fit_width(self):
        if self._compact:
            word_width = max(button.fontMetrics().horizontalAdvance(word)
                             for button in self.buttons.values() for word in button.label.split())
            heading_width = max(button.sizeHint().width() for button in self.group_buttons.values())
            margins = self.layout().contentsMargins()
            gutters = 46 + margins.left() + margins.right() + self.scroll.verticalScrollBar().sizeHint().width()
            width = max(155, word_width + gutters, heading_width + 20)
            self.setFixedWidth(width)
            for button in self.buttons.values():
                lines = ['']
                for word in button.label.split():
                    candidate = (lines[-1]+' '+word).strip()
                    if lines[-1] and button.fontMetrics().horizontalAdvance(candidate) > width - gutters:
                        lines.append(word)
                    else:
                        lines[-1] = candidate
                button.setText('\n'.join(lines))
                button.setMinimumHeight(max(38, len(lines)*button.fontMetrics().height()+12))
        else:
            for button in self.buttons.values():
                button.setText(button.label)
                button.setMinimumHeight(38)
            text_width = max(button.sizeHint().width() for button in self.buttons.values())
            margins = self.layout().contentsMargins()
            self.setFixedWidth(max(218, text_width + margins.left() + margins.right() + 12))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and getattr(self, 'group_buttons', None):
            self._width_timer.start()

    def refresh_theme(self):
        if hasattr(self,'toggle'):
            self.logo.setPixmap(application_icon().pixmap(23, 23))
            self.set_compact(self._compact)
            for button in self.buttons.values():
                button._refresh_icon()
            self.search._refresh_icon()
            self.help_button._refresh_icon()
