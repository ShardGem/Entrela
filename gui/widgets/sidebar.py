"""Grouped navigation with an accessible accordion and a compact rail."""
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QFrame,QWidget,QVBoxLayout,QHBoxLayout,QPushButton,QLabel,QScrollArea
from gui.icons import get_icon,get_pixmap
from gui.theme import PALETTE


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
           ('analysis','Estudos científicos'),('library','Projetos e modelos'),('documentation','Exportar e documentar'),
           ('docs','Conceitos e tutoriais'),('settings','Preferências')]
    GROUPS=[('start','Começar','dashboard',('dashboard','examples','docs')),
            ('lab','Laboratório','simulation',('simulation','circuit','results','bloch')),
            ('research','Pesquisa','analysis',('analysis','mitigation','comparison')),
            ('organize','Organização','library',('history','library','documentation'))]

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('Sidebar')
        self.buttons={}
        self.group_buttons={}
        self.group_bodies={}
        self._compact=False
        self._active='dashboard'
        self._expanded='start'
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
        logo.setPixmap(get_pixmap('simulation',PALETTE.primary,28))
        logo.setFixedSize(30,30)
        brand.addWidget(logo)
        self.logo_title=QLabel('Entrela')
        self.logo_title.setObjectName('SidebarLogo')
        brand.addWidget(self.logo_title,1)
        outer.addLayout(brand)
        self.toggle=QPushButton()
        self.toggle.setObjectName('SidebarToggle')
        self.toggle.setMinimumHeight(38)
        self.toggle.setIconSize(QSize(22,22))
        self.toggle.clicked.connect(lambda:self.compact_requested.emit(not self._compact))
        outer.addWidget(self.toggle)
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
                button.clicked.connect(lambda checked=False,page=page:self._on_click(page))
                children.addWidget(button)
                self.buttons[page]=button
            self.group_bodies[key]=body
            layout.addWidget(body)
        layout.addStretch()
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll,1)
        self.buttons['settings']=NavButton('settings',labels['settings'])
        self.buttons['settings'].clicked.connect(lambda:self._on_click('settings'))
        outer.addWidget(self.buttons['settings'])

    def _expand(self,key):
        self._expanded=None if self._expanded==key else key
        self._refresh_groups()

    def _refresh_groups(self):
        for key,title,icon,items in self.GROUPS:
            expanded=key==self._expanded
            self.group_bodies[key].setVisible(expanded)
            button=self.group_buttons[key]
            button.setText('' if self._compact else title+'   '+('−' if expanded else '+'))
            button.setToolTip(title+(' — recolher' if expanded else ' — expandir'))
            button.setProperty('activeGroup',self._active in items)
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
            self._expanded=group
        self._refresh_groups()
        if key in self.buttons:
            self.scroll.ensureWidgetVisible(self.buttons[key]) if key!='settings' else None

    def set_compact(self,compact):
        self._compact=bool(compact)
        self.setFixedWidth(80 if compact else 268)
        self.logo_title.setVisible(not compact)
        self.toggle.setText('' if compact else '  Recolher navegação')
        self.toggle.setIcon(get_icon('menu',PALETTE.text_muted))
        self.toggle.setToolTip('Expandir navegação' if compact else 'Recolher navegação')
        self.toggle.setAccessibleName(self.toggle.toolTip())
        for key,label in self.ITEMS:
            button=self.buttons[key]
            button.setText('' if compact else '  '+label)
            button.setProperty('compact',bool(compact))
            button.style().unpolish(button)
            button.style().polish(button)
        for body in self.group_bodies.values():
            body.layout().setContentsMargins(0 if compact else 8,0,0,6)
        self._refresh_groups()

    def refresh_theme(self):
        if hasattr(self,'toggle'):
            self.logo.setPixmap(get_pixmap('simulation',PALETTE.primary,28))
            self.set_compact(self._compact)
            for button in self.buttons.values():
                button._refresh_icon()
