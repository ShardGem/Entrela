"""One scientific engine for all UI modes, counts and snapshots."""

from time import perf_counter
from dataclasses import asdict, replace
from secrets import randbits
from importlib.metadata import version
import platform
import numpy as np
from qiskit.quantum_info import Statevector, DensityMatrix
from qiskit_aer import AerSimulator
from core.circuits import build_circuit, build_editor_circuit, _build_hamiltonian
from core.noise import build_noise_model
from core.metrics import fidelity, purity, energy_expectation
from core.types import Experiment, ExperimentResult
from core import __version__


class SimulationCancelled(Exception):
    pass


def run_experiment(config, progress=None, is_cancelled=None):
    config.validate()
    started = perf_counter()
    seed = config.seed if config.seed is not None else randbits(32)

    def checkpoint(percent):
        if is_cancelled and is_cancelled():
            raise SimulationCancelled()
        if progress:
            progress(percent)

    checkpoint(5)
    s, p = config.system, config.protocol
    arguments = dict(
        num_qubits=s.num_qubits,
        hamiltonian=s.hamiltonian,
        J=s.J,
        h=s.h,
        periodic=s.periodic,
        total_time=p.total_time,
        trotter_steps=p.trotter_steps,
        save_snapshots=p.save_snapshots,
        initial_state=s.initial_state,
        trotter_order=p.trotter_order,
        save_final=True,
    )
    kind = "density_matrix" if config.noise.enabled else "statevector"

    def build(snapshot_kind):
        if config.circuit is not None:
            return build_editor_circuit(
                config.circuit,
                snapshot_kind=snapshot_kind,
                save_snapshots=p.save_snapshots,
            )
        return build_circuit(**arguments, snapshot_kind=snapshot_kind)

    circuit, labels = build(kind)
    sim = AerSimulator(
        method=kind, noise_model=build_noise_model(config.noise), max_parallel_threads=2
    )
    checkpoint(20)
    execution = sim.run(circuit, shots=config.shots, seed_simulator=seed).result()
    if not execution.success:
        raise RuntimeError(str(execution.status))
    checkpoint(65)
    data = execution.data()
    cls = DensityMatrix if config.noise.enabled else Statevector
    states = [cls(data[label]) for label in labels]
    final = cls(data["final"])
    if config.noise.enabled:
        reference, _ = build("statevector")
        execution_ideal = (
            AerSimulator(method="statevector", max_parallel_threads=2)
            .run(reference, shots=1, seed_simulator=seed)
            .result()
        )
        if not execution_ideal.success:
            raise RuntimeError(str(execution_ideal.status))
        ideal_data = execution_ideal.data()
        ideal = Statevector(ideal_data["final"])
        ideal_states = [Statevector(ideal_data[label]) for label in labels]
    else:
        ideal, ideal_states = final, states
    checkpoint(90)
    operations = []
    for instruction, origin in zip(circuit.data, circuit.metadata["origins"]):
        if not instruction.operation.name.startswith("save_"):
            operations.append(
                dict(
                    **origin,
                    name=instruction.operation.name,
                    qubits=[circuit.find_bit(q).index for q in instruction.qubits],
                    parameters=[float(p) for p in instruction.operation.params],
                )
            )
    display = circuit.copy_empty_like()
    for instruction in circuit.data:
        if not instruction.operation.name.startswith("save_"):
            display.append(instruction)
    H = (
        None
        if config.circuit is not None
        else _build_hamiltonian(s.num_qubits, s.hamiltonian, s.J, s.h, s.periodic)
    )
    result = ExperimentResult(
        counts=execution.get_counts(),
        statevectors=states if not config.noise.enabled and labels else None,
        density_matrices=states if config.noise.enabled and labels else None,
        ideal_statevectors=ideal_states if labels else None,
        final_state=final,
        ideal_final_state=ideal,
        labels=labels,
        times=np.linspace(0, p.total_time, len(labels)).tolist() if labels else [],
        fidelity=fidelity(final, ideal),
        purity=purity(final),
        energy=None if H is None else energy_expectation(final, H),
        circuit_text=str(display.draw(output="text", fold=100)),
        circuit_depth=display.depth(),
        metadata={
            "entrela_version": __version__,
            "circuit_global_phase": float(circuit.global_phase),
            "experiment_kind": "circuit"
            if config.circuit is not None
            else "hamiltonian",
            "operations": operations,
            "effective_seed": seed,
            "requested_seed": config.seed,
            "method": kind,
            "python": platform.python_version(),
            "versions": {
                name: version(name)
                for name in (
                    "qiskit",
                    "qiskit-aer",
                    "numpy",
                    "scipy",
                    "PySide6",
                    "matplotlib",
                )
            },
            "fidelity_reference": "Mesmo circuito sem ruído"
            if config.circuit is not None
            else "Mesmo circuito Suzuki–Trotter sem ruído",
            "time_unit": "índice da porta (sem tempo físico)"
            if config.circuit is not None
            else "adimensional (ℏ=1)",
            "ising_convention": "+J ΣZZ +h ΣX",
            "bit_order": "q0 à direita",
            "thermal_gate_time_ns": 50.0,
            "reproduction": {
                "schema_version": 1,
                "config": asdict(replace(config, seed=seed)),
                "simulator": "AerSimulator",
                "simulation_method": kind,
                "mitigation_method": "none",
                "max_parallel_threads": 2,
                "platform": platform.platform(),
                "note": "Use a configuração com semente efetiva e as versões registradas. Semente não garante identidade entre versões ou plataformas.",
            },
        },
    )
    checkpoint(100)
    return Experiment(config, result, duration_s=perf_counter() - started)
