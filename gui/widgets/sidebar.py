"""Navegação com grupos independentes e nomes visíveis nas duas larguras."""
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve, QEvent, QTimer
from PySide6.QtWidgets import QApplication,QFrame,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QToolButton,QLabel,QScrollArea
from gui.icons import get_icon
from gui.theme import PALETTE
from gui.branding import application_icon


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
    ITEMS=[('dashboard','Visão geral'),('examples','Exemplos prontos'),('simulation','Configurar experimento'),
           ('circuit','Editor de circuitos'),('results','Resultados'),('bloch','Estados em 3D'),
           ('mitigation','Mitigação de ruído'),('comparison','Comparar execuções'),('history','Histórico'),
           ('analysis','Análises e varreduras'),('library','Projetos e modelos'),('documentation','Exportar e documentar'),
           ('docs','Conceitos e tutoriais'),('settings','Preferências')]
    GROUPS=[('start','Começar','group-start',('dashboard','examples','docs')),
            ('lab','Laboratório','group-lab',('simulation','circuit','results','bloch')),
            ('research','Pesquisa','group-research',('analysis','mitigation','comparison')),
            ('organize','Acervo','group-organize',('history','library','documentation'))]
    DESCRIPTIONS={
        'analysis':'Varreduras de parâmetros e benchmark de mitigação.',
        'simulation':'Defina o sistema, a evolução temporal e o modelo de ruído.',
        'comparison':'Compare métricas, curvas temporais e estados de duas execuções.',
        'documentation':'Exporte dados, figuras, animações e relatórios científicos.',
    }

    def __init__(self,parent=None):
        super().__init__(parent)
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
        outer.setContentsMargins(12,16,12,12)
        outer.setSpacing(12)
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
        self.scroll=QScrollArea()
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content=QWidget()
        layout=QVBoxLayout(content)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(8)
        labels=dict(self.ITEMS)
        for key,title,icon,items in self.GROUPS:
            header=QPushButton()
            header.setObjectName('NavGroup')
            header.setMinimumHeight(44)
            header.setIconSize(QSize(22,22))
            header.setCursor(Qt.PointingHandCursor)
            header.setAccessibleName(title+' — expandir ou recolher grupo')
            header.clicked.connect(lambda checked=False,key=key:self._expand(key))
            layout.addWidget(header)
            self.group_buttons[key]=header
            body=QWidget()
            children=QVBoxLayout(body)
            children.setContentsMargins(8,0,0,6)
            children.setSpacing(4)
            for page in items:
                button=NavButton(page,labels[page])
                button.setToolTip(f'{title} · {labels[page]}\n{self.DESCRIPTIONS.get(page,labels[page])}')
                button.clicked.connect(lambda checked=False,page=page:self._on_click(page))
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
        self.buttons['settings']=NavButton('settings',labels['settings'])
        self.buttons['settings'].clicked.connect(lambda:self._on_click('settings'))
        outer.addWidget(self.buttons['settings'])

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
            button.setText(title+(' ' if self._compact else '   ')+('−' if expanded else '+'))
            button.setCheckable(True)
            button.setChecked(expanded)
            button.setToolTip(title+(' — recolher grupo' if expanded else ' — expandir grupo')+'\n'+' · '.join(dict(self.ITEMS)[page] for page in items))
            button.setAccessibleName(title+(' — grupo expandido' if expanded else ' — grupo recolhido'))
            button.setProperty('activeGroup',self._active in items)
            button.setProperty('compact',self._compact)
            button.setProperty('expanded',expanded)
            button.style().unpolish(button)
            button.style().polish(button)
            button.setIcon(get_icon(icon,PALETTE.primary if self._active in items else PALETTE.text_muted))
            button.setIconSize(QSize(24,24))

    def _on_click(self,key):
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
            self.scroll.ensureWidgetVisible(self.buttons[key]) if key!='settings' else None

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
            body.layout().setContentsMargins(0 if compact else 8,0,0,6)
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
            QTimer.singleShot(0, self._fit_width)

    def refresh_theme(self):
        if hasattr(self,'toggle'):
            self.logo.setPixmap(application_icon().pixmap(28,28))
            self.set_compact(self._compact)
            for button in self.buttons.values():
                button._refresh_icon()
