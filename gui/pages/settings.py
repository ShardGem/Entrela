from PySide6.QtWidgets import QFormLayout,QLabel,QSpinBox
from gui.pages.base import PageBase
from gui.widgets.card import Card
class SettingsPage(PageBase):
    def __init__(self,parent=None):
        super().__init__("Configurações","Preferências aplicadas a novas configurações.",parent)
        card=Card("Simulação")
        form=QFormLayout()
        self.spin_shots=QSpinBox()
        self.spin_shots.setRange(1,1_000_000)
        self.spin_shots.setValue(8192)
        form.addRow("Shots padrão",self.spin_shots)
        card.add_layout(form)
        self.body().addWidget(card)
        self.body().addWidget(QLabel("Tema escuro · Entrela"))
        self.body().addStretch()
