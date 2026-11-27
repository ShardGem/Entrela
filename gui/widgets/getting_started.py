"""Introdução opcional: orienta a navegação sem criar dados de demonstração."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QFrame, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from gui.branding import application_icon
from gui.design_system import Surface
from gui.widgets.button import GhostButton, PrimaryButton, SecondaryButton
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.preparation_preview import PreparationPreview


TOPICS = (
    ("Começar", "Escolha por onde começar",
     "Você não precisa conhecer todas as ferramentas para fazer seu primeiro experimento.",
     "<b>Projetos</b> organizam uma investigação. Na <b>Biblioteca</b>, os exemplos explicam "
     "o objetivo e o que observar. Criar uma cópia deixa o exemplo pronto para você editar.",
     "O tutorial de Bell acompanha um experimento real: você configura, executa, interpreta e reabre os resultados.",
     (("dashboard", "Ver projetos"), ("examples", "Escolher um exemplo"))),
    ("Preparar", "Da ideia à execução",
     "Em Preparar, escolha Simulação para evoluir um sistema por Hamiltoniano ou Circuitos para montar portas.",
     "A configuração que você edita é um <b>rascunho</b>. Revise sistema, evolução e ruído antes de clicar em "
     "<b>Executar</b>. Uma <b>execução</b> guarda os parâmetros usados e os resultados calculados.",
     "Shots é o número de amostras de medição. A semente permite repetir a amostragem no mesmo ambiente. "
     "Para começar, use os valores de um exemplo e altere um parâmetro por vez.",
     (("simulation", "Abrir simulação"), ("circuit", "Abrir editor de circuitos"))),
    ("Observar", "Entenda o que foi calculado",
     "Depois de executar, Resultados reúne medições, evolução e estado global. Estados 3D mostra os qubits na esfera de Bloch.",
     "<b>Contagens</b> são amostras; <b>probabilidades calculadas</b> vêm do estado simulado. "
     "Confira a referência indicada ao ler uma fidelidade. A esfera de Bloch descreve cada qubit localmente, não o estado global.",
     "Prévia ideal de Bell: H cria superposição e CX correlaciona os qubits. A previsão é 50% em 00 e 50% em 11; "
     "contagens de uma execução finita podem variar. O desenho abaixo é explicativo, sem executar uma simulação.",
     (("results", "Abrir resultados"), ("bloch", "Ver estados 3D"))),
    ("Guardar", "Registre e continue sua investigação",
     "Use o Histórico para reencontrar uma execução e o Caderno para escrever o que você observou.",
     "No <b>Histórico</b>, o olho abre os detalhes. <b>Abrir resultados</b> consulta o registro; "
     "<b>Usar configuração</b> cria uma base editável para outro teste. No <b>Caderno</b>, reúna anotações, evidências e relatórios.",
     "Ao comparar, escolha duas execuções e confira o critério de compatibilidade. Para documentar, use Exportar "
     "no contexto da execução: o formato depende dos dados disponíveis. Tudo aqui é simulação computacional.",
     (("history", "Ver histórico"), ("notebook", "Abrir caderno"))),
)


def _label(text, role=None):
    label = QLabel(text)
    label.setWordWrap(True)
    if role:
        label.setObjectName(role)
    return label


class GettingStartedGuide(QWidget):
    destination_requested = Signal(str)
    tutorial_requested = Signal()
    welcome_requested = Signal()
    progress_changed = Signal(int, bool)
    opened = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.step = 0
        self.completed = False
        self._result_name = ""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)
        self.progress = _label("", 'FieldHint')
        self.progress.setAccessibleName('Progresso do guia de uso')
        root.addWidget(self.progress)
        steps = FlowLayout()
        self.step_buttons = QButtonGroup(self)
        for index, (short_title, *_) in enumerate(TOPICS):
            button = SecondaryButton(f'{index + 1} · {short_title}')
            button.setObjectName('GuideStep')
            button.setCheckable(True)
            button.setAccessibleName(f'Tópico {index + 1} de {len(TOPICS)}: {short_title}')
            self.step_buttons.addButton(button, index)
            steps.addWidget(button)
        self.step_buttons.idClicked.connect(self.select_step)
        root.addLayout(steps)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content = Surface(role='StudioPanel')
        self.heading = self.content.add(_label('', 'ResumeTitle'))
        self.heading.setFocusPolicy(Qt.StrongFocus)
        self.lead = self.content.add(_label(''))
        self.explanation = self.content.add(_label(''))
        self.tip = self.content.add(_label('', 'FieldHint'))
        self.preview = self.content.add(PreparationPreview())
        self.preview.set_preparation(2, 'bell')
        self.result_hint = self.content.add(_label('', 'FieldHint'))
        self.result_hint.setTextFormat(Qt.PlainText)
        links = FlowLayout()
        self.route_buttons = {}
        for *_, actions in TOPICS:
            for key, text in actions:
                button = SecondaryButton(text, icon='arrow-right')
                button.setAccessibleName(text)
                button.clicked.connect(lambda _checked=False, route=key: self.destination_requested.emit(route))
                self.route_buttons[key] = button
                links.addWidget(button)
        self.content.body().addLayout(links)
        self.practice = SecondaryButton('Fazer o tutorial de Bell', icon='play')
        self.practice.setAccessibleName('Fazer o primeiro experimento com o tutorial de Bell')
        self.practice.setToolTip('Prepara o rascunho do tutorial. Alterações existentes usam a confirmação do aplicativo.')
        self.practice.clicked.connect(self.tutorial_requested.emit)
        self.content.body().addWidget(self.practice, 0, Qt.AlignLeft)
        self.content.body().addStretch(1)
        self.scroll.setWidget(self.content)
        root.addWidget(self.scroll, 1)

        controls = FlowLayout()
        self.back = SecondaryButton('Voltar', icon='arrow-left')
        self.next = PrimaryButton('Próximo tópico', icon='arrow-right')
        self.welcome = GhostButton('Apresentação inicial', icon='help')
        self.welcome.setToolTip('Rever as opções de início e escolher se a apresentação aparece ao abrir o Entrela.')
        self.back.clicked.connect(lambda: self.select_step(self.step - 1))
        self.next.clicked.connect(self.advance)
        self.welcome.clicked.connect(self.welcome_requested.emit)
        for button in (self.back, self.next, self.welcome):
            controls.addWidget(button)
        root.addLayout(controls)
        self.set_result('')
        self._render()

    def restore(self, step=0, completed=False):
        self.step = max(0, min(int(step), len(TOPICS) - 1))
        self.completed = bool(completed)
        self._render()

    def select_step(self, step):
        self.step = max(0, min(step, len(TOPICS) - 1))
        self._render()
        self.scroll.verticalScrollBar().setValue(0)
        self.progress_changed.emit(self.step, self.completed)

    def advance(self):
        if self.step < len(TOPICS) - 1:
            self.select_step(self.step + 1)
        elif self.completed:
            self.completed = False
            self.select_step(0)
        else:
            self.completed = True
            self._render()
            self.progress_changed.emit(self.step, True)

    def set_result(self, name):
        self._result_name = name
        for key in ('results', 'bloch'):
            self.route_buttons[key].setEnabled(bool(name))
            self.route_buttons[key].setToolTip('Consultar a execução selecionada.' if name else 'Execute uma simulação para consultar seus resultados.')
        self.result_hint.setText('Execução selecionada: ' + name if name else 'Execute uma simulação para consultar suas medições em Resultados e Estados 3D.')

    def _render(self):
        _, title, lead, explanation, tip, actions = TOPICS[self.step]
        self.heading.setText(title)
        self.lead.setText(lead)
        self.explanation.setText(explanation)
        self.tip.setText(tip)
        self.step_buttons.button(self.step).setChecked(True)
        self.back.setEnabled(self.step > 0)
        self.next.setText('Próximo tópico' if self.step < len(TOPICS) - 1 else 'Rever guia' if self.completed else 'Concluir guia')
        self.progress.setText('Guia consultado · Você pode rever os tópicos ou praticar com Bell.' if self.completed
                              else f'Guia de uso · tópico {self.step + 1} de {len(TOPICS)} · no seu ritmo')
        self.preview.setVisible(self.step == 2)
        self.result_hint.setVisible(self.step == 2)
        self.practice.setVisible(self.step in (0, 3))
        visible_routes = {key for key, _ in actions}
        for key, button in self.route_buttons.items():
            button.setVisible(key in visible_routes)

    def showEvent(self, event):
        super().showEvent(event)
        self.opened.emit()


class WelcomeDialog(QDialog):
    """Uma escolha dispensável, com conteúdo rolável e saídas sempre visíveis."""

    def __init__(self, repeat=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Boas-vindas ao Entrela')
        self.setAccessibleName('Apresentação inicial opcional do Entrela')
        self.choice = None
        self.resize(720, 650)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)
        brand = _label('Entrela · laboratório quântico', 'Eyebrow')
        root.addWidget(brand)
        root.addWidget(_label('Comece no seu ritmo', 'ResumeTitle'))
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = Surface(role='FlatSection')
        content.body().setContentsMargins(0, 0, 8, 0)
        content.add(_label('Prepare experimentos, execute simulações e entenda seus resultados. Escolha um caminho; você pode mudar de ideia a qualquer momento.'))
        self.actions = {}
        for key, text, description, icon in (
            ('guide', 'Conhecer o Entrela', 'Um guia das telas e do caminho entre preparar, observar e guardar resultados.', 'arrow-right'),
            ('tutorial', 'Meu primeiro experimento', 'Tutorial de Bell: prepare, execute, interprete e reabra os seus próprios resultados.', 'play'),
            ('examples', 'Explorar exemplos prontos', 'Veja o objetivo de cada exemplo antes de criar uma cópia editável.', 'book-stack'),
        ):
            button = PrimaryButton(text, icon=icon) if key == 'guide' else SecondaryButton(text, icon=icon)
            button.setAutoDefault(False)
            button.setAccessibleName(text)
            button.setAccessibleDescription(description)
            button.clicked.connect(lambda _checked=False, route=key: self._choose(route))
            self.actions[key] = button
            content.add(button)
            content.add(_label(description, 'FieldHint'))
        content.add(_label('Prefere explorar por conta própria? Tudo fica disponível depois em Aprender → Primeiros passos e no botão Buscar.', 'FieldHint'))
        area.setWidget(content)
        root.addWidget(area, 1)
        self.repeat = QCheckBox('Mostrar esta apresentação ao iniciar')
        self.repeat.setChecked(repeat)
        root.addWidget(self.repeat)
        self.skip = SecondaryButton('Explorar por conta própria')
        self.skip.setAutoDefault(False)
        self.skip.setAccessibleName('Dispensar a apresentação e explorar por conta própria')
        self.skip.clicked.connect(self.reject)
        root.addWidget(self.skip)
        self.setWindowIcon(application_icon())

    def _choose(self, route):
        self.choice = route
        self.accept()
