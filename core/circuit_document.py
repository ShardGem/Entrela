"""Portable, validated unitary circuit documents backed by Qiskit gates."""

from dataclasses import dataclass, asdict
import ast
import math
import operator
import re
from qiskit import QuantumCircuit, qasm2
from qiskit.circuit.library import (
    HGate,
    XGate,
    YGate,
    ZGate,
    SGate,
    SdgGate,
    TGate,
    TdgGate,
    SXGate,
    IGate,
    RXGate,
    RYGate,
    RZGate,
    PhaseGate,
    UGate,
    CXGate,
    CYGate,
    CZGate,
    CHGate,
    SwapGate,
    RXXGate,
    RYYGate,
    RZZGate,
    CCXGate,
)

GATES = {
    "h": (HGate, 1, 0),
    "x": (XGate, 1, 0),
    "y": (YGate, 1, 0),
    "z": (ZGate, 1, 0),
    "s": (SGate, 1, 0),
    "sdg": (SdgGate, 1, 0),
    "t": (TGate, 1, 0),
    "tdg": (TdgGate, 1, 0),
    "sx": (SXGate, 1, 0),
    "id": (IGate, 1, 0),
    "rx": (RXGate, 1, 1),
    "ry": (RYGate, 1, 1),
    "rz": (RZGate, 1, 1),
    "p": (PhaseGate, 1, 1),
    "u": (UGate, 1, 3),
    "cx": (CXGate, 2, 0),
    "cy": (CYGate, 2, 0),
    "cz": (CZGate, 2, 0),
    "ch": (CHGate, 2, 0),
    "swap": (SwapGate, 2, 0),
    "rxx": (RXXGate, 2, 1),
    "ryy": (RYYGate, 2, 1),
    "rzz": (RZZGate, 2, 1),
    "ccx": (CCXGate, 3, 0),
}
MAX_GATES = 200


def parse_angle(text):
    """Small arithmetic language, never Python evaluation or function calls."""
    text = text.strip().replace("π", "pi").replace("−", "-").replace(",", ".")
    if len(text) > 128:
        raise ValueError("Ângulo muito longo")
    try:
        tree = ast.parse(text, mode="eval")
        if len(list(ast.walk(tree))) > 40:
            raise ValueError("Expressão muito longa")

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) in (int, float):
                return float(node.value)
            if isinstance(node, ast.Name) and node.id == "pi":
                return math.pi
            if isinstance(node, ast.UnaryOp) and isinstance(
                node.op, (ast.USub, ast.UAdd)
            ):
                return (-1 if isinstance(node.op, ast.USub) else 1) * visit(
                    node.operand
                )
            if isinstance(node, ast.BinOp) and type(node.op) in (
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
            ):
                return {
                    ast.Add: operator.add,
                    ast.Sub: operator.sub,
                    ast.Mult: operator.mul,
                    ast.Div: operator.truediv,
                }[type(node.op)](visit(node.left), visit(node.right))
            raise ValueError("Use números, pi e operações +, −, *, /")

        value = visit(tree.body)
        if not math.isfinite(value):
            raise ValueError("Ângulo deve ser finito")
        return value
    except (SyntaxError, TypeError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Ângulo inválido; exemplo: pi/2") from exc


@dataclass(frozen=True)
class CircuitGate:
    name: str
    qubits: tuple[int, ...]
    parameters: tuple[float, ...] = ()


@dataclass(frozen=True)
class CircuitDocument:
    num_qubits: int = 2
    gates: tuple[CircuitGate, ...] = ()
    global_phase: float = 0.0

    def validate(self):
        if type(self.num_qubits) is not int or not 1 <= self.num_qubits <= 6:
            raise ValueError("Use de 1 a 6 qubits")
        if (
            not isinstance(self.global_phase, (int, float))
            or isinstance(self.global_phase, bool)
            or not math.isfinite(self.global_phase)
        ):
            raise ValueError("Fase global inválida")
        if not isinstance(self.gates, tuple) or len(self.gates) > MAX_GATES:
            raise ValueError(f"O editor executa até {MAX_GATES} portas")
        for gate in self.gates:
            if (
                not isinstance(gate, CircuitGate)
                or not isinstance(gate.name, str)
                or gate.name not in GATES
            ):
                raise ValueError("Porta não suportada no editor")
            _, arity, nparams = GATES[gate.name]
            if len(gate.qubits) != arity or len(set(gate.qubits)) != arity:
                raise ValueError("Escolha qubits diferentes para cada conexão")
            if any(
                type(q) is not int or not 0 <= q < self.num_qubits for q in gate.qubits
            ):
                raise ValueError("Qubit fora do circuito")
            if len(gate.parameters) != nparams or any(
                isinstance(x, bool)
                or not isinstance(x, (int, float))
                or not math.isfinite(x)
                for x in gate.parameters
            ):
                raise ValueError("Parâmetros da porta inválidos")

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, raw):
        try:
            if not isinstance(raw, dict) or set(raw) - {
                "num_qubits",
                "gates",
                "global_phase",
            }:
                raise ValueError("Documento de circuito inválido")
            doc = cls(
                raw["num_qubits"],
                tuple(
                    CircuitGate(
                        g["name"], tuple(g["qubits"]), tuple(g.get("parameters", ()))
                    )
                    for g in raw.get("gates", [])
                ),
                raw.get("global_phase", 0.0),
            )
            doc.validate()
            return doc
        except (KeyError, TypeError, AttributeError) as exc:
            raise ValueError("Documento de circuito inválido") from exc

    def to_quantum_circuit(self, measure=False):
        self.validate()
        circuit = QuantumCircuit(self.num_qubits, self.num_qubits if measure else 0)
        circuit.global_phase = self.global_phase
        for gate in self.gates:
            circuit.append(GATES[gate.name][0](*gate.parameters), list(gate.qubits))
        if measure:
            circuit.measure(range(self.num_qubits), range(self.num_qubits))
        return circuit

    @classmethod
    def from_quantum_circuit(cls, circuit):
        gates = []
        measured = False
        measurements = []
        for inst in circuit.data:
            name = inst.operation.name
            qs = tuple(circuit.find_bit(q).index for q in inst.qubits)
            if name == "measure":
                measured = True
                measurements.append((qs[0], circuit.find_bit(inst.clbits[0]).index))
                continue
            if name == "barrier":
                continue
            if measured:
                raise ValueError("O editor suporta medições somente ao final")
            if inst.operation.num_clbits or getattr(inst.operation, "condition", None):
                raise ValueError("Controle clássico não suportado no editor")
            params = tuple(float(p) for p in inst.operation.params)
            if name == "u3":
                name = "u"
            elif name == "u2":
                name = "u"
                params = (math.pi / 2, *params)
            elif name == "u1":
                name = "p"
            gates.append(CircuitGate(name, qs, params))
        if measurements and (
            len(measurements) != circuit.num_qubits
            or set(measurements) != {(q, q) for q in range(circuit.num_qubits)}
        ):
            raise ValueError("Use medição final de todos os qubits, q[i] → c[i]")
        doc = cls(circuit.num_qubits, tuple(gates), float(circuit.global_phase))
        doc.validate()
        return doc

    def to_qasm(self):
        return f"// entrela_global_phase: {self.global_phase!r}\n" + qasm2.dumps(
            self.to_quantum_circuit(measure=True)
        )

    @classmethod
    def from_qasm(cls, text):
        if len(text) > 200_000:
            raise ValueError("Arquivo QASM excede 200 kB")
        try:
            circuit = qasm2.loads(
                text, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS
            )
            phase = re.search(r"^// entrela_global_phase: (.+)$", text, re.MULTILINE)
            if phase:
                circuit.global_phase = parse_angle(phase[1])
            return cls.from_quantum_circuit(circuit)
        except Exception as exc:
            raise ValueError("OpenQASM 2 não suportado: " + str(exc)) from exc


GATE_HELP = {
    "h": "Hadamard: transforma |0⟩ em |+⟩ e |1⟩ em |−⟩; troca as bases X/Z.",
    "x": "Pauli X: troca |0⟩ e |1⟩.",
    "y": "Pauli Y: inversão com fase.",
    "z": "Pauli Z: muda o sinal de |1⟩.",
    "s": "Porta de fase π/2.",
    "sdg": "Inversa da porta S.",
    "t": "Porta de fase π/4.",
    "tdg": "Inversa da porta T.",
    "sx": "Raiz quadrada da porta X.",
    "id": "Identidade: preserva o estado ideal.",
    "rx": "Rotação no eixo X; ângulo em radianos.",
    "ry": "Rotação no eixo Y; ângulo em radianos.",
    "rz": "Rotação no eixo Z; ângulo em radianos.",
    "p": "Fase relativa aplicada à componente |1⟩.",
    "u": "Porta universal U(θ, φ, λ) de um qubit.",
    "cx": "X controlado: primeiro qubit é o controle, segundo é o alvo.",
    "cy": "Y controlado: primeiro qubit é o controle, segundo é o alvo.",
    "cz": "Z controlado: primeiro qubit é o controle, segundo é o alvo.",
    "ch": "Hadamard controlado: primeiro qubit é o controle, segundo é o alvo.",
    "swap": "Troca os estados dos dois qubits.",
    "rxx": "Rotação conjunta exp(−i θ XX/2).",
    "ryy": "Rotação conjunta exp(−i θ YY/2).",
    "rzz": "Rotação conjunta exp(−i θ ZZ/2).",
    "ccx": "Toffoli: dois primeiros qubits controlam X no terceiro.",
    "measure": "Medição na base Z, registrada no bit clássico correspondente.",
}
