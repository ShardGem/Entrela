from core.types import system_label
from data.workspace import experiment_title
from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QLabel, QHBoxLayout, QGridLayout, QPushButton, QWidget, QVBoxLayout, QSplitter
from gui.pages.base import PageBase
from gui.widgets.card import Card, MetricCard, MetricGrid
from gui.design_system import Surface
from gui.widgets.collapsible import CollapsibleSection
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
        hero = QLabel("Seu espaço de investigação")
        hero.setObjectName("HeroTitle")
        hero.setWordWrap(True)
        self.body().addWidget(hero)
        overview = QLabel("Prepare sistemas, observe sua evolução e reúna evidências reproduzíveis.")
        overview.setWordWrap(True)
        overview.setObjectName("SectionSubtitle")
        self.body().addWidget(overview)
        self.card_sims = MetricCard("Execuções salvas", "0")
        self.card_last = MetricCard("Último modelo")
        self.card_fid = MetricCard("Última fidelidade")
        self.card_purity = MetricCard("Última pureza")
        self.body().addWidget(MetricGrid([self.card_sims, self.card_last, self.card_fid, self.card_purity]))
        self.dashboard_splitter = QSplitter(Qt.Horizontal)
        self.dashboard_splitter.setHandleWidth(3)
        self.recent = Surface("Continue de onde parou")
        self.dashboard_splitter.addWidget(self.recent)
        quick = Surface("Começar uma investigação")
        for text, description, signal in [
            ("Criar experimento", "Configure uma evolução ou monte um circuito de portas.", self.new_simulation),
            ("Explorar exemplos", "Abra modelos editáveis com objetivos e previsões explicados.", self.examples_requested),
            ("Aprender fazendo", "Percorra o tutorial verificável de um estado de Bell.", self.tutorial_requested),
        ]:
            button = PrimaryButton(text) if text == "Criar experimento" else SecondaryButton(text)
            button.clicked.connect(signal.emit)
            quick.add(button)
            hint = QLabel(description); hint.setWordWrap(True); hint.setObjectName("FieldHint")
            quick.add(hint)
        workflow = CollapsibleSection("Como conduzir um estudo")
        steps = QLabel("1 · Prepare o estado e o protocolo.\n2 · Execute e preserve os resultados.\n3 · Compare referências, ruído e observáveis.\n4 · Documente e reproduza as evidências.")
        steps.setWordWrap(True)
        workflow.content_layout.addWidget(steps)
        quick.add(workflow)
        self.concept_toggle = SecondaryButton("Conceitos essenciais")
        self.concept_toggle.setCheckable(True)
        self.concept_toggle.setAccessibleName("Mostrar conceitos essenciais")
        quick.add(self.concept_toggle)
        self.concepts = Card("Interpretar os resultados")
        for text in (
            "O circuito transforma o estado antes da medição; as contagens são amostras de suas probabilidades.",
            "A esfera de Bloch representa cada estado local. Vetores curtos também podem resultar de emaranhamento.",
            "Fidelidade usa uma referência explícita. Pureza global e pureza local têm interpretações diferentes.",
            "ZNE extrapola observáveis e pode aumentar o erro; não reconstrói um estado mitigado.",
        ):
            paragraph=QLabel(text); paragraph.setWordWrap(True); self.concepts.add(paragraph)
        self.concepts.hide()
        self.concept_toggle.toggled.connect(self.concepts.setVisible)
        quick.add(self.concepts)
        quick.body().addStretch()
        self.dashboard_splitter.addWidget(quick)
        self.dashboard_splitter.setStretchFactor(0, 1)
        self.dashboard_splitter.setSizes([800, 380])
        self.body().addWidget(self.dashboard_splitter, 1)
        history = SecondaryButton("Abrir histórico completo", icon="history")
        history.clicked.connect(self.open_history.emit)
        self.body().addWidget(history, 0, Qt.AlignLeft)
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
        if hasattr(self, "dashboard_splitter"):
            self.dashboard_splitter.setOrientation(Qt.Vertical if self.width() < 900 * max(1, self.font().pixelSize()/15) else Qt.Horizontal)
        if hasattr(self, "_dashboard_actions"):
            self._dashboard_actions.setDirection(
                QHBoxLayout.TopToBottom
                if self.width() < 850
                else QHBoxLayout.LeftToRight
            )
