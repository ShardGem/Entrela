"""ZNE of Z using local unitary folding on u/cx, without post-fold optimization."""

from secrets import randbits
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector, SparsePauliOp
from core.types import integer
from core.simulation import SimulationCancelled


def _insert_identity_pairs(circuit, extra_pairs):
    integer(extra_pairs, "Pares", 0)
    folded = circuit.copy_empty_like()
    for instruction in circuit.data:
        op = instruction.operation
        folded.append(instruction)
        if op.name == "barrier":
            continue
        if op.name not in ("u", "cx", "h", "x", "y", "z", "rx", "ry", "rz", "cz"):
            raise ValueError("Porta não suportada para folding")
        for _ in range(extra_pairs):
            folded.append(op.inverse(), instruction.qubits)
            folded.append(op, instruction.qubits)
    return folded


def _expectation_z(counts, num_qubits, qubit=0):
    integer(qubit, "Qubit", 0)
    if qubit >= num_qubits:
        raise ValueError("Qubit fora do sistema")
    shots, total = 0, 0
    for bits, count in counts.items():
        integer(count, "Contagem", 0)
        bits = bits.replace(" ", "").zfill(num_qubits)
        if len(bits) != num_qubits or set(bits) - {"0", "1"}:
            raise ValueError("Bitstring inválida")
        shots += count
        total += (1 if bits[-1 - qubit] == "0" else -1) * count
    if not shots:
        raise ValueError("Não há medições")
    return total / shots


def compile_unitary(circuit, seed):
    """Compile once before folding; keep global phase and remove unused clbits."""
    for instruction in circuit.data:
        op = instruction.operation
        if op.name in ("measure", "reset") or op.name.startswith("save_") or op.num_clbits:
            raise ValueError("ZNE requer circuito unitário sem medições ou snapshots")
    compiled = transpile(
        circuit, basis_gates=["u", "cx"], optimization_level=0,
        seed_transpiler=seed,
    )
    native = QuantumCircuit(compiled.num_qubits)
    native.global_phase = compiled.global_phase
    for instruction in compiled.data:
        native.append(instruction.operation, [compiled.find_bit(q).index for q in instruction.qubits])
    return native


def fit_zne_samples(factors, measured, errors, method):
    """Unweighted polynomial fit; propagated error covers independent shot sampling."""
    if method not in ("linear", "quadratic"):
        raise ValueError("Ajuste não suportado")
    degree = 1 if method == "linear" else 2
    xs = np.asarray(factors, float)
    if len(xs) < degree + 1 or len(set(factors)) != len(factors):
        raise ValueError("Pontos insuficientes ou repetidos")
    weights = np.linalg.pinv(np.vander(xs, degree + 1))[-1]
    coefficients = np.polyfit(xs, measured, degree)
    return dict(
        coefficients=coefficients.tolist(),
        residuals=(np.asarray(measured) - np.polyval(coefficients, xs)).tolist(),
        degrees_of_freedom=len(factors) - degree - 1,
        extrapolated=float(coefficients[-1]),
        extrapolated_stderr=float(np.sqrt(np.sum(weights**2 * np.square(errors)))),
    )


def run_zne(
    circuit_without_measure,
    noise_model,
    scale_factors=None,
    shots=8192,
    method="linear",
    *,
    seed=None,
    qubit=0,
    progress=None,
    is_cancelled=None,
):
    integer(shots, "Shots")
    if shots > 1_000_000:
        raise ValueError("Limite de 1.000.000 shots por fator")
    integer(qubit, "Qubit", 0)
    if qubit >= circuit_without_measure.num_qubits:
        raise ValueError("Qubit inválido")
    if seed is not None:
        integer(seed, "Semente", 0)
        if seed >= 2**32:
            raise ValueError("Semente inválida")
    seed = seed if seed is not None else randbits(32)
    if method not in ("linear", "quadratic"):
        raise ValueError("Ajuste não suportado")
    degree = 1 if method == "linear" else 2
    factors = list([1, 3, 5] if scale_factors is None else scale_factors)
    if (
        len(factors) < degree + 1
        or len(factors) > 5
        or len(set(factors)) != len(factors)
        or 1 not in factors
    ):
        raise ValueError("Forneça pontos distintos, incluindo fator 1")
    for factor in factors:
        integer(factor, "Fator")
        if factor % 2 != 1 or factor > 9:
            raise ValueError("Fatores efetivos devem ser ímpares entre 1 e 9")
    native = compile_unitary(circuit_without_measure, seed)
    if len(native.data) * max(factors) > 100_000:
        raise ValueError("Limite de 100.000 portas por circuito dobrado; reduza passos ou fatores")
    if noise_model is not None and not set(noise_model.noise_instructions).intersection(
        native.count_ops()
    ):
        raise ValueError("O modelo de ruído não atua nas portas deste circuito")
    sim = AerSimulator(
        method="density_matrix", noise_model=noise_model, max_parallel_threads=2
    )
    measured, errors, gate_counts, samples = [], [], [], []
    for i, factor in enumerate(factors):
        if is_cancelled and is_cancelled():
            raise SimulationCancelled()
        if progress:
            progress(10 + int(80 * i / len(factors)))
        folded = _insert_identity_pairs(native, (factor - 1) // 2)
        gate_counts.append(dict(folded.count_ops()))
        folded.measure_all()
        sample_seed = (seed + i) % 2**32
        execution = sim.run(
            folded, shots=shots, seed_simulator=sample_seed
        ).result()
        if not execution.success:
            raise RuntimeError(str(execution.status))
        counts = dict(execution.get_counts())
        samples.append(dict(scale_factor=factor, effective_seed=sample_seed, shots=shots,
                            counts=counts, gate_counts=gate_counts[-1]))
        mean = _expectation_z(counts, native.num_qubits, qubit)
        measured.append(mean)
        errors.append(float(np.sqrt(max(0.0, 1 - mean**2) / shots)))
    if is_cancelled and is_cancelled():
        raise SimulationCancelled()
    fit = fit_zne_samples(factors, measured, errors, method)
    label = ["I"] * native.num_qubits
    label[-1 - qubit] = "Z"
    ideal = float(
        np.real(
            Statevector.from_instruction(native).expectation_value(
                SparsePauliOp("".join(label))
            )
        )
    )
    extrapolated = fit["extrapolated"]
    baseline = measured[factors.index(1)]
    return dict(
        **fit,
        ideal_observable=ideal,
        baseline_absolute_error=abs(baseline - ideal),
        extrapolated_absolute_error=abs(extrapolated - ideal),
        success=True,
        measured=measured,
        stderr=errors,
        scale_factors=factors,
        method=method,
        qubit=qubit,
        folded_gate_counts=gate_counts,
        samples=samples,
        native_circuit=dict(
            num_qubits=native.num_qubits,
            global_phase=float(native.global_phase),
            operations=[dict(
                name=ins.operation.name,
                qubits=[native.find_bit(q).index for q in ins.qubits],
                parameters=[float(v) for v in ins.operation.params],
            ) for ins in native.data],
        ),
        optimization_level=0,
        folding="local U (U† U)^k; sem otimização após folding",
        native_basis=["u", "cx"],
        shots=shots,
        seed=seed,
    )
