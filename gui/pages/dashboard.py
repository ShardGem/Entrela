from core.types import system_label
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QHBoxLayout, QGridLayout, QPushButton
from gui.pages.base import PageBase
from gui.widgets.card import Card, MetricCard
from gui.widgets.button import PrimaryButton, SecondaryButton


class DashboardPage(PageBase):
    new_simulation = Signal()
    open_history = Signal()
    examples_requested = Signal()
    tutorial_requested = Signal()
    experiment_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Seu laboratório quântico",
            "Explore, simule e analise sistemas quânticos.",
            parent,
        )
        hero = QLabel("Do primeiro qubit a um\nexperimento reproduzível.")
        hero.setObjectName("HeroTitle")
        hero.setWordWrap(True)
        self.body().addWidget(hero)
        actions = QHBoxLayout()
        self._dashboard_actions = actions
        for text, description, signal in [
            (
                "Criar experimento",
                "Configure o sistema e investigue sua evolução.",
                self.new_simulation,
            ),
            (
                "Explorar exemplos",
                "Abra cópias editáveis de experimentos científicos.",
                self.examples_requested,
            ),
            (
                "Aprender fazendo",
                "Prepare, execute e reabra um estado de Bell.",
                self.tutorial_requested,
            ),
        ]:
            card = Card(text)
            label = QLabel(description)
            label.setWordWrap(True)
            card.add(label)
            button = PrimaryButton(text)
            button.clicked.connect(signal.emit)
            card.add(button)
            actions.addWidget(card, 1)
        self.body().addLayout(actions)
        grid = QGridLayout()
        self.card_sims = MetricCard("Registros", "0")
        self.card_last = MetricCard("Último modelo")
        self.card_fid = MetricCard("Última fidelidade")
        self.card_purity = MetricCard("Última pureza")
        for index, card in enumerate(
            [self.card_sims, self.card_last, self.card_fid, self.card_purity]
        ):
            grid.addWidget(card, index // 2, index % 2)
            grid.setColumnStretch(index, 1)
        self.body().addLayout(grid)
        self.recent = Card("Continue de onde parou")
        self.body().addWidget(self.recent)
        history = SecondaryButton("Abrir histórico completo")
        history.clicked.connect(self.open_history.emit)
        self.body().addWidget(history)
        self.body().addStretch()

    def update_stats(self, total, last_ham, avg_fid, avg_purity):
        self.card_sims.set_value(str(total))
        self.card_last.set_value(last_ham or "—")
        self.card_fid.set_value("—" if avg_fid is None else f"{avg_fid:.4f}")
        self.card_purity.set_value("—" if avg_purity is None else f"{avg_purity:.4f}")

    def load_recent(self, experiments):
        while self.recent.body().count() > 1:
            item = self.recent.body().takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        if not experiments:
            self.recent.add(
                QLabel("Seus experimentos aparecerão aqui. Comece por um exemplo.")
            )
        for exp in experiments:
            state = (
                "Falhou"
                if exp.result.error
                else ("ZNE" if exp.result.mitigation else "Concluído")
            )
            button = QPushButton(f"{system_label(exp.config)} · {exp.id} · {state}")
            button.clicked.connect(lambda _, i=exp.id: self.experiment_selected.emit(i))
            self.recent.add(button)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_dashboard_actions"):
            self._dashboard_actions.setDirection(
                QHBoxLayout.TopToBottom
                if self.width() < 850
                else QHBoxLayout.LeftToRight
            )
