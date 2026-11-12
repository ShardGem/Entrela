"""Navegação com grupos independentes e nomes visíveis nas duas larguras."""
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer
from PySide6.QtWidgets import QApplication,QFrame,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QToolButton,QLabel,QScrollArea
from gui.icons import get_icon
from gui.theme import PALETTE
from gui.branding import application_icon
from gui.navigation import NAV_ITEMS, NAV_GROUPS, NAV_ACTIONS


class NavButton(QPushButton):
    def __init__(self,icon_name,label,parent=None):
        super().__init__(parent)
        self.icon_name=icon_name
        self.label=label
        self.setObjectName('NavButton')
        self.setCheckable(True)
        self.setAutoExclusive(False)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setAccessibleName(label)
        self.setToolTip(label)
        self.setText('  '+label)
        self._refresh_icon()

    def _refresh_icon(self):
        self.setIcon(get_icon(self.icon_name,PALETTE.primary if self.isChecked() else PALETTE.text_muted))
        self.setIconSize(QSize(22,22))

    def setChecked(self,checked):
        super().setChecked(checked)
        self._refresh_icon()


class Sidebar(QFrame):
    navigate=Signal(str)
    compact_requested=Signal(bool)
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
        'library': 'Registre identificação, projeto, hipóteses e interpretação da execução selecionada.',
        'configurations': 'Reutilize parâmetros salvos do formulário Hamiltoniano. Abrir uma configuração não executa a simulação.',
        'documentation': 'Organize evidências e exporte dados, figuras, animações e relatórios científicos.',
        'examples': 'Explore modelos prontos e abra cópias editáveis para aprender e experimentar.',
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
        outer.setContentsMargins(12,12,12,12)
        outer.setSpacing(8)
        brand=QHBoxLayout()
        logo=QLabel()
        self.logo=logo
        logo.setPixmap(application_icon().pixmap(28,28))
        logo.setFixedSize(30,30)
        brand.addWidget(logo)
        self.logo_title=QLabel('Entrela')
        self.logo_title.setObjectName('SidebarLogo')
        brand.addWidget(self.logo_title,1)
        outer.addLayout(brand)
        navigation = QHBoxLayout()
        caption = QLabel('Navegação')
        self.navigation_caption = caption
        caption.setObjectName('SectionSubtitle')
        navigation.addWidget(caption,1)
        self.toggle=QToolButton()
        self.toggle.setObjectName('SidebarToggle')
        self.toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.toggle.setCursor(Qt.PointingHandCursor)
        self.toggle.setMinimumHeight(38)
        self.toggle.setIconSize(QSize(22,22))
        self.toggle.clicked.connect(lambda:self.compact_requested.emit(not self._compact))
        navigation.addWidget(self.toggle)
        outer.addLayout(navigation)
        self.buttons['dashboard'] = self._make_button('dashboard')
        outer.addWidget(self.buttons['dashboard'])
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
            header.setMinimumHeight(30)
            header.setIconSize(QSize(22,22))
            header.setCursor(Qt.PointingHandCursor)
            header.setAccessibleName(title+' — expandir ou recolher grupo')
            header.clicked.connect(lambda checked=False,key=key:self._expand(key))
            layout.addWidget(header)
            self.group_buttons[key]=header
            body=QWidget()
            children=QVBoxLayout(body)
            children.setContentsMargins(8,0,0,0)
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
        self.buttons['settings'] = self._make_button('settings')
        outer.addWidget(self.buttons['settings'])

    def _make_button(self, key, group=None):
        label = dict(self.ITEMS)[key]
        icon = {'library': 'annotations'}.get(key, key)
        button = NavButton(icon, label)
        if key in NAV_ACTIONS:
            button.setCheckable(False)
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
            button.setIcon(get_icon('chevron-down' if expanded else 'next', PALETTE.primary if self._active in items else PALETTE.text_muted))
            button.setIconSize(QSize(16,16))

    def _on_click(self,key):
        if key not in NAV_ACTIONS:
            self.set_active(key)
        self.navigate.emit(key)

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
        self.logo_title.show()
        self.navigation_caption.setVisible(not compact)
        self.toggle.setText('Expandir menu' if compact else 'Recolher')
        self.toggle.setIcon(get_icon('expand' if compact else 'collapse',PALETTE.text_muted))
        self.toggle.setToolTip('Expandir navegação' if compact else 'Recolher navegação')
        self.toggle.setAccessibleName(self.toggle.toolTip())
        for key,label in self.ITEMS:
            button=self.buttons[key]
            button.setText(label)
            button.setProperty('compact',bool(compact))
            button.style().unpolish(button)
            button.style().polish(button)
        for body in self.group_bodies.values():
            body.layout().setContentsMargins(0 if compact else 8,0,0,0)
        self._refresh_groups()
        self._fit_width()

    def _fit_width(self):
        if self._compact:
            word_width = max(button.fontMetrics().horizontalAdvance(word)
                             for button in self.buttons.values() for word in button.label.split())
            heading_width = max(button.sizeHint().width() for button in self.group_buttons.values())
            width = max(184, word_width+92, heading_width+40)
            self.setFixedWidth(width)
            for button in self.buttons.values():
                lines = ['']
                for word in button.label.split():
                    candidate = (lines[-1]+' '+word).strip()
                    if lines[-1] and button.fontMetrics().horizontalAdvance(candidate) > width-92:
                        lines.append(word)
                    else:
                        lines[-1] = candidate
                button.setText('\n'.join(lines))
                button.setMinimumHeight(max(44, len(lines)*button.fontMetrics().height()+16))
        else:
            for button in self.buttons.values():
                button.setText(button.label)
                button.setMinimumHeight(44)
            text_width = max(button.sizeHint().width() for button in self.buttons.values())
            self.setFixedWidth(max(280, text_width+32))

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange) and getattr(self, 'group_buttons', None):
            self._width_timer.start()

    def refresh_theme(self):
        if hasattr(self,'toggle'):
            self.logo.setPixmap(application_icon().pixmap(28,28))
            self.set_compact(self._compact)
            for button in self.buttons.values():
                button._refresh_icon()
