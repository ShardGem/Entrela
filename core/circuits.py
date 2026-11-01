"""Hamiltonian convention: Ising H=+J ΣZZ+h ΣX; q0 is rightmost."""

from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.synthesis import SuzukiTrotter
from qiskit_aer.library import SaveStatevector, SaveDensityMatrix
from core.types import SystemConfig, SimulationProtocol


def _build_hamiltonian(num_qubits, hamiltonian, J, h, periodic):
    SystemConfig(num_qubits, hamiltonian, J, h, periodic).validate()
    terms, coefficients = [], []

    def add(operators, coefficient):
        label = ["I"] * num_qubits
        for qubit, operator in operators:
            label[num_qubits - 1 - qubit] = operator
        terms.append("".join(label))
        coefficients.append(coefficient)

    pairs = [(i, i + 1) for i in range(num_qubits - 1)]
    if periodic and num_qubits > 2:
        pairs.append((num_qubits - 1, 0))
    if hamiltonian in ("Ising", "Custom"):
        for a, b in pairs:
            add([(a, "Z"), (b, "Z")], J)
        for i in range(num_qubits):
            add([(i, "X")], h)
    else:
        for a, b in pairs:
            for operator in ("X", "Y"):
                add([(a, operator), (b, operator)], J)
            if hamiltonian in ("Heisenberg", "XXZ"):
                add([(a, "Z"), (b, "Z")], J if hamiltonian == "Heisenberg" else 0.5 * J)
    return SparsePauliOp(
        terms or ["I" * num_qubits], coeffs=coefficients or [0.0]
    ).simplify()


def _build_decomposed_step(H, dt, num_qubits, order=2):
    circuit = QuantumCircuit(num_qubits)
    circuit.append(
        PauliEvolutionGate(H, time=dt, synthesis=SuzukiTrotter(order=order)),
        circuit.qubits,
    )
    return circuit.decompose(reps=4)


def build_circuit(
    num_qubits,
    hamiltonian,
    J,
    h,
    periodic,
    total_time,
    trotter_steps,
    save_snapshots,
    *,
    snapshot_kind="statevector",
    initial_state="zero",
    trotter_order=2,
    save_final=False,
    measure=True,
):
    SystemConfig(num_qubits, hamiltonian, J, h, periodic, initial_state).validate()
    SimulationProtocol(
        total_time, trotter_steps, save_snapshots, trotter_order
    ).validate()
    if snapshot_kind not in ("statevector", "density_matrix"):
        raise ValueError("Tipo de snapshot inválido")
    H = _build_hamiltonian(num_qubits, hamiltonian, J, h, periodic)
    circuit = QuantumCircuit(num_qubits, num_qubits if measure else 0)
    if initial_state == "plus":
        circuit.h(range(num_qubits))
    elif initial_state == "bell":
        circuit.h(0)
        circuit.cx(0, 1)
    origins = [dict(stage="preparation", step=0) for _ in circuit.data]
    save = SaveDensityMatrix if snapshot_kind == "density_matrix" else SaveStatevector
    labels = []

    def snapshot(label):
        circuit.append(save(num_qubits, label=label), circuit.qubits)
        origins.append(
            dict(
                stage="snapshot",
                step=int(label[1:]) if label.startswith("t") else trotter_steps,
            )
        )

    if save_snapshots:
        snapshot("t0")
        labels.append("t0")
    step = _build_decomposed_step(
        H, total_time / trotter_steps, num_qubits, trotter_order
    )
    for i in range(1, trotter_steps + 1):
        circuit.compose(step, inplace=True)
        origins.extend(dict(stage="evolution", step=i) for _ in step.data)
        if save_snapshots:
            snapshot(f"t{i}")
            labels.append(f"t{i}")
    if save_final:
        snapshot("final")
    if measure:
        circuit.measure(range(num_qubits), range(num_qubits))
        origins.extend(
            dict(stage="measurement", step=trotter_steps) for _ in range(num_qubits)
        )
    circuit.metadata = {"origins": origins}
    return circuit, labels
