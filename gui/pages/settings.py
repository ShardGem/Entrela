"""Workspace preferences, independent of scientific experiment parameters."""

from PySide6.QtCore import Signal, QSignalBlocker, Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QSpinBox, QComboBox, QCheckBox
from gui.pages.base import PageBase
from gui.widgets.card import Card
from gui.widgets.button import SecondaryButton


class SettingsPage(PageBase):
    appearance_changed = Signal()
    restore_requested = Signal()
    backup_requested = Signal()
    restore_backup_requested = Signal()
    DEFAULTS = {
        "theme": "dark", "font_size": 15, "accent": "cyan",
        "density": "comfortable", "reduce_motion": False,
        "high_contrast": False, "completion_notifications": True,
        "export_dpi": 300, "presentation": False, "compact": False,
    }

    def __init__(self, parent=None):
        super().__init__("Preferências", "Adapte a área de trabalho sem alterar os resultados dos experimentos.", parent)
        self.theme = self._combo((('Escuro', 'dark'), ('Claro', 'light'), ('Automático · acompanhar o sistema', 'auto')))
        self.accent = self._combo((('Ciano · Entrela', 'cyan'), ('Azul', 'blue'), ('Violeta', 'violet'), ('Verde', 'green')))
        self.density = self._combo((('Compacta', 'compact'), ('Confortável', 'comfortable'), ('Ampla', 'spacious')))
        self.font_size = QSpinBox()
        self.font_size.setRange(11, 24)
        self.font_size.setSuffix(' px')
        self.font_size.setToolTip('Tamanho base da interface. Títulos e textos auxiliares acompanham esta escala.')
        self.theme.setToolTip('O modo automático acompanha a preferência de cores informada pelo sistema operacional.')
        self.density.setToolTip('Ajusta os espaços de botões, formulários e tabelas. Não altera a escala dos dados.')
        self.presentation = QCheckBox('Fonte maior e navegação compacta · F11 para tela cheia')
        self.compact = QCheckBox('Usar menu mais estreito, mantendo os nomes dos itens')
        self._card('Aparência', [
            ('Tema', self.theme), ('Cor de destaque', self.accent),
            ('Tamanho do texto', self.font_size), ('Densidade', self.density),
            ('Navegação', self.compact), ('Apresentação', self.presentation),
        ])
        self.reduce_motion = QCheckBox('Reduzir animações da interface')
        self.reduce_motion.setToolTip('Desativa transições de navegação e animações decorativas. A reprodução científica continua disponível nos controles 3D.')
        self.high_contrast = QCheckBox('Aumentar contraste de textos e contornos')
        self._card('Acessibilidade', [('Movimento', self.reduce_motion), ('Contraste', self.high_contrast)])
        self.spin_shots = QSpinBox()
        self.spin_shots.setRange(1, 1_000_000)
        self.spin_shots.setValue(8192)
        self.spin_shots.setToolTip('Número inicial de amostras ao criar um experimento. A configuração de cada execução continua registrada separadamente.')
        self.completion_notifications = QCheckBox('Mostrar aviso ao concluir uma execução')
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
        self.body().addWidget(backup)
        note = QLabel('Velocidade, repetição, rastros e foco dos qubits ficam nos controles de Estados em 3D e são lembrados entre sessões. As preferências são salvas automaticamente.')
        note.setWordWrap(True)
        self.body().addWidget(note)
        reset = SecondaryButton('Restaurar preferências padrão')
        reset.setToolTip('Restaura a aparência e a visualização. Os experimentos salvos são preservados.')
        reset.clicked.connect(self.restore_requested.emit)
        self.body().addWidget(reset)
        self.body().addStretch()
        self.apply_values(self.DEFAULTS)
        for name in self.DEFAULTS:
            widget = getattr(self, name)
            signal = widget.currentIndexChanged if isinstance(widget, QComboBox) else widget.valueChanged if isinstance(widget, QSpinBox) else widget.toggled
            signal.connect(lambda *_: self.appearance_changed.emit())

    @staticmethod
    def _combo(items):
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        return combo

    def _card(self, title, rows):
        card = Card(title)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        form.setVerticalSpacing(12)
        for label, widget in rows:
            widget.setAccessibleName(label)
            form.addRow(label, widget)
        card.add_layout(form)
        self.body().addWidget(card)

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
