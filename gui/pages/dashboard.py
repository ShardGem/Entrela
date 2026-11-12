from core.types import system_label
from data.workspace import experiment_title
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QHBoxLayout, QGridLayout, QPushButton, QWidget, QVBoxLayout
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
            "Investigue como o ruído afeta simulações quânticas e avalie a mitigação com dados reproduzíveis.",
            parent,
        )
        hero = QLabel("Prepare, investigue e reproduza.")
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
            button = PrimaryButton(text) if text == "Criar experimento" else SecondaryButton(text)
            button.clicked.connect(signal.emit)
            card.add(button)
            actions.addWidget(card, 1)
        self.body().addLayout(actions)
        workflow = Card("Como investigar no Entrela")
        flow = QGridLayout()
        flow.setHorizontalSpacing(20)
        flow.setVerticalSpacing(16)
        for index, (title, description) in enumerate([
            ("1 · Preparar", "Escolha um exemplo ou configure qubits, estado inicial e interações."),
            ("2 · Comparar", "Execute o mesmo sistema com e sem ruído. Preserve os parâmetros que deseja controlar."),
            ("3 · Analisar", "Inspecione fidelidade, pureza, energia e estados. Avalie o erro do observável ao aplicar ZNE."),
            ("4 · Reproduzir", "Reabra o histórico e exporte configuração, semente, versões e resultados para o seu estudo."),
        ]):
            step = QWidget()
            step.setStyleSheet("background: transparent;")
            step_layout = QVBoxLayout(step)
            step_layout.setContentsMargins(0, 0, 0, 0)
            heading = QLabel(title)
            heading.setObjectName("SectionTitle")
            heading.setWordWrap(True)
            explanation = QLabel(description)
            explanation.setWordWrap(True)
            step_layout.addWidget(heading)
            step_layout.addWidget(explanation)
            flow.addWidget(step, index // 2, index % 2)
        flow.setColumnStretch(0, 1)
        flow.setColumnStretch(1, 1)
        workflow.add_layout(flow)
        self.body().addWidget(workflow)

        self.concept_toggle = SecondaryButton("Primeira vez? Entenda qubits, ruído e mitigação")
        self.concept_toggle.setCheckable(True)
        self.concept_toggle.setAccessibleName("Mostrar conceitos essenciais")
        self.body().addWidget(self.concept_toggle)
        self.concepts = Card("Conceitos essenciais")
        for title, text in [
            ("Qubit e circuito", "Um qubit pode ser medido como 0 ou 1. O circuito prepara e transforma o estado antes da medição; as probabilidades dependem dessas operações."),
            ("Ruído e esfera de Bloch", "Ruído pode misturar o estado. A esfera mostra o estado local de cada qubit; um vetor curto também pode resultar de emaranhamento, sem ruído."),
            ("Fidelidade e pureza", "Fidelidade compara dois estados com uma referência explícita. Pureza mede mistura; um estado global puro pode ter qubits locais mistos."),
            ("Mitigação ZNE", "Executa versões com ruído amplificado e extrapola um observável. Não reconstrói um estado mitigado e pode aumentar o erro; a referência ideal permite verificar isso."),
        ]:
            label = QLabel(f"<b>{title}</b><br>{text}")
            label.setWordWrap(True)
            self.concepts.add(label)
        self.concepts.hide()
        self.concept_toggle.toggled.connect(self.concepts.setVisible)
        self.body().addWidget(self.concepts)
        grid = QGridLayout()
        self.card_sims = MetricCard("Registros", "0")
        self.card_last = MetricCard("Último modelo")
        self.card_fid = MetricCard("Última fidelidade")
        self.card_purity = MetricCard("Última pureza")
        for index, card in enumerate(
            [self.card_sims, self.card_last, self.card_fid, self.card_purity]
        ):
            grid.addWidget(card, index // 2, index % 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.body().addLayout(grid)
        self.recent = Card("Continue de onde parou")
        self.body().insertWidget(1, self.recent)
        history = SecondaryButton("Abrir histórico completo")
        history.clicked.connect(self.open_history.emit)
        self.body().addWidget(history)
        self.body().addStretch()
        self.annotations = {}
        self._recent_experiments = []

    def set_annotations(self, annotations):
        self.annotations = annotations or {}
        self.load_recent(self._recent_experiments)

    def update_stats(self, total, last_ham, avg_fid, avg_purity):
        self.card_sims.set_value(str(total))
        self.card_last.set_value(last_ham or "—")
        self.card_fid.set_value("—" if avg_fid is None else f"{avg_fid:.4f}")
        self.card_purity.set_value("—" if avg_purity is None else f"{avg_purity:.4f}")

    def load_recent(self, experiments):
        self._recent_experiments = list(experiments)
        while self.recent.body().count() > 1:
            item = self.recent.body().takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        if not self._recent_experiments:
            self.recent.add(
                QLabel("Seus experimentos aparecerão aqui. Comece por um exemplo.")
            )
        for exp in self._recent_experiments:
            state = (
                "Falhou"
                if exp.result.error
                else ("ZNE" if exp.result.mitigation else "Concluído")
            )
            button = QPushButton(f"{experiment_title(exp, self.annotations)} · {state}")
            button.setToolTip(f"Executado em {exp.created_at.astimezone().strftime('%d/%m/%Y às %H:%M')}")
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
