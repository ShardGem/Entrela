"""Workspace preferences, independent of scientific experiment parameters."""

from PySide6.QtCore import Signal, QSignalBlocker, Qt, QEvent
from PySide6.QtWidgets import QFormLayout, QLabel, QSpinBox, QComboBox, QCheckBox, QScrollArea, QWidget, QVBoxLayout, QFrame, QListWidget, QSplitter, QMenu
from gui.pages.base import PageBase
from gui.widgets.card import Card
from gui.widgets.button import SecondaryButton
from gui.widgets.content_tabs import ContentTabs
from gui.palettes import THEME_CHOICES, THEME_DESCRIPTIONS


class SettingsPage(PageBase):
    appearance_changed = Signal()
    restore_requested = Signal()
    layout_reset_requested = Signal()
    backup_requested = Signal()
    restore_backup_requested = Signal()
    DEFAULTS = {
        "theme": "dark", "font_size": 15, "accent": "theme",
        "density": "comfortable", "reduce_motion": False,
        "high_contrast": False, "completion_notifications": True,
        "export_dpi": 300, "presentation": False, "compact": False,
    }

    def __init__(self, parent=None):
        super().__init__("Preferências", "Adapte a área de trabalho sem alterar os resultados dos experimentos.", parent)
        self._forms = []
        self.category = QComboBox()
        self.category.setAccessibleName('Categoria das preferências')
        self.category.setMinimumContentsLength(10)
        self.category.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.sections = ContentTabs()
        self.sections.tabBar().hide()
        self.category.hide()
        self.category_list = QListWidget()
        self.category_list.setObjectName("PreferenceCategories")
        self.category_list.setAccessibleName("Categorias das preferências")
        self.category_list.setWordWrap(True)
        self.category_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.category_list.setTextElideMode(Qt.ElideNone)
        self.category_list.setResizeMode(QListWidget.Adjust)
        self.category_list.setMinimumWidth(170)
        self.category_list.setMaximumWidth(250)
        self.preferences_splitter = QSplitter(Qt.Horizontal)
        self.preferences_splitter.setHandleWidth(3)
        self.preferences_splitter.addWidget(self.category_list)
        self.preferences_splitter.addWidget(self.sections)
        self.preferences_splitter.setStretchFactor(1, 1)
        self.body().addWidget(self.category)
        self.body().addWidget(self.preferences_splitter, 1)
        self.category_list.currentRowChanged.connect(self.category.setCurrentIndex)
        self.category.currentIndexChanged.connect(self.category_list.setCurrentRow)
        self.category.currentIndexChanged.connect(self.sections.setCurrentIndex)
        self.theme = self._combo(THEME_CHOICES)
        self.accent = self._combo((('Padrão do tema', 'theme'), ('Ciano · Entrela', 'cyan'), ('Azul', 'blue'), ('Violeta', 'violet'), ('Verde', 'green')))
        self.theme_description = QLabel()
        self.theme_description.setWordWrap(True)
        self.theme_description.setObjectName('FieldHint')
        self.theme.currentIndexChanged.connect(self._describe_theme)
        self.density = self._combo((('Compacta', 'compact'), ('Confortável', 'comfortable'), ('Ampla', 'spacious')))
        self.font_size = QSpinBox()
        self.font_size.setRange(11, 24)
        self.font_size.setSuffix(' px')
        self.font_size.setToolTip('Tamanho base da interface. Títulos e textos auxiliares acompanham esta escala.')
        self.theme.setToolTip('O modo automático acompanha a preferência de cores informada pelo sistema operacional.')
        self.accent.setToolTip('Padrão do tema usa o ciano do Grafite ou o azul dos temas Claro científico e Azul escuro. As demais opções personalizam o destaque.')
        self.density.setToolTip('Ajusta os espaços de botões, formulários e tabelas. Não altera a escala dos dados.')
        self.presentation = QCheckBox('Modo de apresentação')
        self.presentation.setToolTip('Usa fonte maior e navegação compacta. F11 alterna a tela cheia.')
        self.compact = QCheckBox('Menu estreito com nomes')
        self.compact.setToolTip('Reduz a largura da navegação e preserva os nomes completos dos itens.')
        self._card('Aparência', [
            ('Tema', self.theme), ('Sobre o tema', self.theme_description), ('Cor de destaque', self.accent),
            ('Tamanho do texto', self.font_size), ('Densidade', self.density),
            ('Navegação', self.compact), ('Apresentação', self.presentation),
        ])
        self.reduce_motion = QCheckBox('Reduzir animações')
        self.reduce_motion.setToolTip('Desativa transições de navegação e animações decorativas. A reprodução científica continua disponível nos controles 3D.')
        self.high_contrast = QCheckBox('Aumentar contraste')
        self.high_contrast.setToolTip('Aumenta o contraste de textos e contornos nos temas disponíveis.')
        self._card('Acessibilidade', [('Movimento', self.reduce_motion), ('Contraste', self.high_contrast)])
        self.spin_shots = QSpinBox()
        self.spin_shots.setRange(1, 1_000_000)
        self.spin_shots.setValue(8192)
        self.spin_shots.setToolTip('Número inicial de amostras ao criar um experimento. A configuração de cada execução continua registrada separadamente.')
        self.completion_notifications = QCheckBox('Avisar ao concluir')
        self._card('Execução e avisos', [('Shots para novos experimentos', self.spin_shots), ('Notificações', self.completion_notifications)])
        self.export_dpi = QSpinBox()
        self.export_dpi.setRange(150, 600)
        self.export_dpi.setSingleStep(50)
        self.export_dpi.setSuffix(' DPI')
        self.export_dpi.setToolTip('Resolução de figuras rasterizadas. Texto e gráficos vetoriais em PDF/SVG preservam a resolução independente.')
        self._card('Exportação', [('Resolução de imagens', self.export_dpi)])
        backup = Card('Backup do espaço de trabalho')
        description = QLabel('Guarde experimentos, circuitos, análises, protocolos, anotações, rascunhos e preferências em um único ZIP. Restaurar substitui o espaço atual após uma prévia e confirmação.')
        description.setWordWrap(True)
        backup.add(description)
        self.backup_button = SecondaryButton('Criar backup completo', icon='export')
        self.restore_backup_button = SecondaryButton('Inspecionar e restaurar backup', icon='history')
        self.backup_button.clicked.connect(self.backup_requested.emit)
        self.restore_backup_button.clicked.connect(self.restore_backup_requested.emit)
        backup.add(self.backup_button)
        backup.add(self.restore_backup_button)
        self.backup_message = QLabel('Backups completos são diferentes dos pacotes de estudo usados em Documentação.')
        self.backup_message.setWordWrap(True)
        self.backup_message.setTextFormat(Qt.PlainText)
        backup.add(self.backup_message)
        self._add_category(backup, "Dados e backup")
        note = QLabel('Velocidade, repetição, rastros e foco dos qubits ficam nos controles de Estados em 3D e são lembrados entre sessões. As preferências são salvas automaticamente.')
        note.setWordWrap(True)
        backup.add(note)
        reset = SecondaryButton('Restaurar preferências padrão')
        reset.setToolTip('Restaura a aparência e a visualização. Os experimentos salvos são preservados.')
        reset.clicked.connect(self.restore_requested.emit)
        reset.setParent(self)
        reset.hide()
        self.restore_menu_button = SecondaryButton('Restaurar')
        restore_menu = QMenu(self.restore_menu_button)
        restore_menu.addAction('Preferências padrão', reset.click)
        self.restore_menu_button.setMenu(restore_menu)
        self.add_action(self.restore_menu_button)
        self.reset_layout_button = SecondaryButton('Restaurar disposição dos painéis')
        self.reset_layout_button.setToolTip('Restaura os tamanhos dos painéis e as categorias de navegação. Mantém parâmetros, circuitos e execuções.')
        self.reset_layout_button.clicked.connect(self.layout_reset_requested.emit)
        self.reset_layout_button.setParent(self)
        self.reset_layout_button.hide()
        restore_menu.addAction("Disposição dos painéis", self.reset_layout_button.click)
        self.apply_values(self.DEFAULTS)
        for name in self.DEFAULTS:
            widget = getattr(self, name)
            signal = widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.valueChanged if isinstance(widget, QSpinBox) else widget.toggled
            signal.connect(lambda *_: self.appearance_changed.emit())
        self._arrange_preferences()

    def _arrange_preferences(self):
        if not hasattr(self, 'preferences_splitter'):
            return
        narrow = self.width() < 1050 * max(1, self.font().pixelSize() / 15)
        self.category.setVisible(narrow)
        self.category_list.setVisible(not narrow)
        for form in self._forms:
            form.setRowWrapPolicy(QFormLayout.WrapAllRows if narrow else QFormLayout.WrapLongRows)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_preferences()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self._arrange_preferences()

    def _describe_theme(self, *_):
        self.theme_description.setText(THEME_DESCRIPTIONS.get(self.theme.currentData(), THEME_DESCRIPTIONS['dark']))

    @staticmethod
    def _combo(items):
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        return combo

    def _card(self, title, rows):
        card = Card(title)
        form = QFormLayout()
        self._forms.append(form)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setVerticalSpacing(12)
        for label, widget in rows:
            widget.setAccessibleName(label)
            form.addRow(label, widget)
        card.add_layout(form)
        self._add_category(card, title)

    def _add_category(self, content, title):
        content.setMaximumWidth(920)
        area = QScrollArea()
        area.setFrameShape(QFrame.NoFrame)
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.addWidget(content)
        layout.addStretch()
        area.setWidget(holder)
        self.sections.addTab(area, title)
        self.category.addItem(title)
        self.category_list.addItem(title)
        if self.category_list.currentRow() < 0:
            self.category_list.setCurrentRow(0)

    def collect_values(self):
        values = {}
        for name in self.DEFAULTS:
            widget = getattr(self, name)
            values[name] = widget.currentData() if isinstance(widget, QComboBox) else widget.value() if isinstance(widget, QSpinBox) else widget.isChecked()
        return values

    def apply_values(self, values):
        """Apply persisted values without emitting partially restored preferences."""
        blockers = [QSignalBlocker(getattr(self, name)) for name in self.DEFAULTS]
        for name, default in self.DEFAULTS.items():
            widget = getattr(self, name)
            value = values.get(name, default)
            if isinstance(widget, QComboBox):
                index = widget.findData(value)
                widget.setCurrentIndex(index if index >= 0 else widget.findData(default))
            elif isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(value))
                except (ValueError, TypeError, OverflowError):
                    widget.setValue(default)
            else:
                widget.setChecked(value.lower() in ('true', '1', 'yes') if isinstance(value, str) else bool(value))
        del blockers
        self._describe_theme()
