"""Plain-language labels and existing learning circuits for the editor."""
from dataclasses import dataclass

from core.learning import CONCEPT_BY_KEY


GATE_NAMES = {
    "h": ("H", "Hadamard"), "x": ("X", "Inversão"),
    "y": ("Y", "Pauli Y"), "z": ("Z", "Pauli Z"),
    "s": ("S", "Fase de 90°"), "sdg": ("S†", "Inversa de S"),
    "t": ("T", "Fase de 45°"), "tdg": ("T†", "Inversa de T"),
    "sx": ("√X", "Raiz de X"), "id": ("I", "Identidade"),
    "rx": ("RX", "Rotação em X"), "ry": ("RY", "Rotação em Y"),
    "rz": ("RZ", "Rotação em Z"), "p": ("P", "Fase relativa"),
    "u": ("U", "Rotação geral"), "cx": ("CX", "X controlado"),
    "cy": ("CY", "Y controlado"), "cz": ("CZ", "Z controlado"),
    "ch": ("CH", "H controlado"), "swap": ("SWAP", "Trocar estados"),
    "rxx": ("RXX", "Rotação conjunta XX"), "ryy": ("RYY", "Rotação conjunta YY"),
    "rzz": ("RZZ", "Rotação conjunta ZZ"), "ccx": ("CCX", "Toffoli"),
}

ANGLE_HELP = "Ângulo em radianos. pi/2 = 90°; pi = 180°; -pi/4 = −45°. Também aceita decimais, como 0,5."
PHASE_HELP = "Fase global em radianos: multiplica o estado inteiro pela mesma fase e não altera probabilidades de medição. Pode permanecer em 0."


@dataclass(frozen=True)
class CircuitTemplate:
    key: str
    title: str
    instruction: str
    prediction: str

    @property
    def document(self):
        return CONCEPT_BY_KEY[self.key].demonstration


TEMPLATES = (
    CircuitTemplate("superposicao", "Criar superposição", "1 qubit · H em q0.", "Ideal em Z: 0 e 1 com 50% cada."),
    CircuitTemplate("bell", "Criar um par de Bell", "2 qubits · H em q0; depois CX com controle q0 e alvo q1.", "Ideal em Z: 00 e 11 com 50% cada."),
    CircuitTemplate("qubit", "Inverter um qubit", "1 qubit · X em q0 troca |0⟩ por |1⟩.", "Ideal em Z: resultado 1 com 100%."),
    CircuitTemplate("interferencia", "Observar interferência", "1 qubit · H, depois Z, depois H em q0.", "Ideal em Z: resultado 1 com 100%."),
    CircuitTemplate("bloch", "Girar o estado na esfera", "1 qubit · H e depois RZ(pi/2) em q0.", "Ideal: vetor de Bloch em +Y; 0 e 1 com 50% cada em Z."),
)

QUICK_START = (
    "Leia o circuito da esquerda para a direita. Cada linha é um qubit, começando em q0, e cada bloco é uma porta. "
    "O estado inicial é |0…0⟩.\n\n"
    "Para criar um par de Bell: escolha 2 qubits, adicione H e mantenha q0; adicione CX, escolha controle q0 e alvo q1 "
    "e clique em Aplicar alterações. Você também pode carregar esse circuito em Modelos prontos.\n\n"
    "Clique em uma porta para editar seus qubits e ângulos no painel ao lado. As alterações de campos só entram no desenho "
    "ao clicar em Aplicar alterações. Desfazer recupera a edição anterior.\n\n"
    "Dê um nome e use Salvar revisão para guardá-lo na biblioteca. Executar circuito gera os resultados; nenhum modelo é executado "
    "automaticamente. As medições finais são feitas na base Z. Nos resultados, q0 fica à direita: em 01, q0=1 e q1=0."
)
