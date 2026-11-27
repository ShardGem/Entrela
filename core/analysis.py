"""Bounded scientific analyses with independent exact time evolution."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
from importlib.metadata import version
import platform
from secrets import randbits
import numpy as np
from scipy.linalg import eigh
from qiskit import QuantumCircuit
from qiskit.quantum_info import (
    Statevector,
    DensityMatrix,
    partial_trace,
    entropy,
    negativity,
    SparsePauliOp,
)
from core.circuits import _build_hamiltonian
from core.metrics import fidelity, purity, energy_expectation
from core.simulation import run_experiment, SimulationCancelled
from core import __version__


def analysis_provenance(experiment=None):
    """Record the environment doing the calculations, separate from old sources."""
    provenance = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_environment": {
            "entrela_version": __version__,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "versions": {name: version(name) for name in ("numpy", "scipy", "qiskit", "qiskit-aer")},
        },
    }
    if experiment is not None:
        metadata = experiment.result.metadata
        provenance["source_environment"] = {
            key: metadata.get(key)
            for key in ("entrela_version", "python", "versions", "method")
        }
        provenance["source_effective_seed"] = metadata.get("effective_seed")
    return provenance


def analysis_run_record(experiment):
    """Complete effective inputs and raw measurements of a generated point."""
    return {
        "id": experiment.id,
        "created_at": experiment.created_at.isoformat(),
        "config": asdict(experiment.config),
        "counts": dict(experiment.result.counts or {}),
        "metadata": experiment.result.metadata,
        "duration_s": experiment.duration_s,
    }


def initial_state(system):
    circuit = QuantumCircuit(system.num_qubits)
    if system.initial_state == "plus":
        circuit.h(range(system.num_qubits))
    elif system.initial_state == "bell":
        circuit.h(0)
        circuit.cx(0, 1)
    return Statevector.from_instruction(circuit)


def exact_states(config, times):
    config.validate()
    if config.circuit is not None:
        raise ValueError(
            "Evolução exata por Hamiltoniano não se aplica ao circuito livre"
        )
    H = _build_hamiltonian(
        config.system.num_qubits,
        config.system.hamiltonian,
        config.system.J,
        config.system.h,
        config.system.periodic,
    )
    eigenvalues, basis = eigh(H.to_matrix())
    coefficients = basis.conj().T @ initial_state(config.system).data
    return [
        Statevector(basis @ (np.exp(-1j * eigenvalues * time) * coefficients))
        for time in times
    ]


def checkpoint(cancelled, progress, percent):
    if cancelled and cancelled():
        raise SimulationCancelled()
    if progress:
        progress(percent)


def temporal_analysis(experiment, progress=None, is_cancelled=None):
    c, r = experiment.config, experiment.result
    if not r.states or not r.times:
        raise ValueError("Esta análise requer snapshots com tempos registrados.")
    checkpoint(is_cancelled, progress, 0)
    exact = exact_states(c, r.times) if c.circuit is None else [None] * len(r.states)
    H = _build_hamiltonian(
        c.system.num_qubits,
        c.system.hamiltonian,
        c.system.J,
        c.system.h,
        c.system.periodic,
    )
    if c.circuit is not None:
        H = None
    rows = []
    for i, (time, state, target) in enumerate(zip(r.times, r.states, exact)):
        checkpoint(is_cancelled, progress, int(100 * i / len(r.states)))
        rho = DensityMatrix(state)
        ideal = (
            r.ideal_statevectors[i]
            if r.ideal_statevectors
            else (state if not c.noise.enabled else None)
        )
        row = dict(
            snapshot=i,
            time=time,
            fidelity=None if ideal is None else fidelity(state, ideal),
            purity=purity(state),
            energy=None if H is None else energy_expectation(state, H),
            fidelity_exact=None if target is None else fidelity(state, target),
            trotter_infidelity=None
            if ideal is None or target is None
            else max(0.0, 1 - fidelity(ideal, target)),
        )
        for q in range(c.system.num_qubits):
            label = ["I"] * c.system.num_qubits
            label[-1 - q] = "Z"
            row[f"Z{q}"] = float(
                np.real(rho.expectation_value(SparsePauliOp("".join(label))))
            )
            reduced = partial_trace(
                rho, [j for j in range(c.system.num_qubits) if j != q]
            )
            row[f"entropy_q{q}"] = float(entropy(reduced, base=2))
        for q in range(c.system.num_qubits - 1):
            label = ["I"] * c.system.num_qubits
            label[-1 - q] = label[-2 - q] = "Z"
            row[f"Z{q}Z{q + 1}"] = float(
                np.real(rho.expectation_value(SparsePauliOp("".join(label))))
            )
        if c.system.num_qubits > 1:
            row["negativity_q0_rest"] = max(0.0, float(negativity(rho, [0])))
        rows.append(row)
    return dict(
        kind="temporal",
        source_id=experiment.id,
        rows=rows,
        config=asdict(c),
        provenance=analysis_provenance(experiment),
        note="Entropia reduzida quantifica emaranhamento somente para estado global puro. Negatividade: bipartição q0|resto; zero não exclui todo emaranhamento em sistemas maiores.",
    )


def convergence_analysis(
    config, steps=(1, 2, 4, 8, 16), progress=None, is_cancelled=None
):
    steps = list(steps)
    if (
        not steps
        or len(steps) > 10
        or any(type(n) is not int or not 1 <= n <= 200 for n in steps)
    ):
        raise ValueError("Use até dez valores inteiros entre 1 e 200.")
    exact = exact_states(config, [config.protocol.total_time])[0]
    rows, runs = [], []
    for i, n in enumerate(steps):
        checkpoint(is_cancelled, progress, int(100 * i / len(steps)))
        cfg = replace(
            config,
            protocol=replace(config.protocol, trotter_steps=n, save_snapshots=False),
            noise=replace(config.noise, enabled=False),
            shots=1,
            seed=42,
        )
        exp = run_experiment(cfg, is_cancelled=is_cancelled)
        runs.append(analysis_run_record(exp))
        rows.append(
            dict(
                steps=n,
                order=config.protocol.trotter_order,
                infidelity=max(0.0, 1 - fidelity(exp.result.final_state, exact)),
                depth=exp.result.circuit_depth,
            )
        )
    return dict(
        kind="convergence",
        rows=rows,
        config=asdict(config),
        runs=runs,
        provenance=analysis_provenance(),
        note="Aproximação Trotter ideal contra exp(−iHt), sem ruído e sem erro de amostragem na fidelidade.",
    )


def parameter_sweep(
    config, parameter, values, seeds=None, progress=None, is_cancelled=None
):
    if config.circuit is not None and parameter in ("J", "h", "trotter_steps"):
        raise ValueError(
            "Este parâmetro pertence a uma evolução por Hamiltoniano, não ao circuito livre"
        )
    values = list(values)
    if not values or len(values) > 20:
        raise ValueError("Use de 1 a 20 pontos.")
    seeds = list(
        seeds
        if seeds is not None
        else [config.seed if config.seed is not None else randbits(32)]
    )
    if not seeds or len(seeds) > 5 or len(values) * len(seeds) > 50:
        raise ValueError("Limite de 50 execuções e cinco sementes.")
    if parameter not in ("J", "h", "p1", "p2", "t1_us", "t2_us", "trotter_steps"):
        raise ValueError("Parâmetro não suportado.")
    configs = []
    for value in values:
        if not np.isfinite(value):
            raise ValueError("Valores devem ser finitos.")
        kwargs = {"protocol": replace(config.protocol, save_snapshots=False)}
        if parameter in ("J", "h"):
            kwargs["system"] = replace(config.system, **{parameter: value})
        elif parameter == "trotter_steps":
            if int(value) != value:
                raise ValueError("Passos devem ser inteiros.")
            kwargs["protocol"] = replace(
                config.protocol, trotter_steps=int(value), save_snapshots=False
            )
        else:
            kind = "Termico" if parameter in ("t1_us", "t2_us") else "Despolarizador"
            kwargs["noise"] = replace(
                config.noise, enabled=True, kind=kind, **{parameter: value}
            )
        for seed in seeds:
            cfg = replace(config, seed=seed, **kwargs)
            cfg.validate()
            configs.append((value, cfg))
    rows, runs = [], []
    for i, (value, cfg) in enumerate(configs):
        checkpoint(is_cancelled, progress, int(100 * i / len(configs)))
        exp = run_experiment(cfg, is_cancelled=is_cancelled)
        runs.append(analysis_run_record(exp))
        r = exp.result
        rows.append(
            dict(
                parameter=parameter,
                value=value,
                seed=r.metadata["effective_seed"],
                fidelity=r.fidelity,
                purity=r.purity,
                energy=r.energy,
                sampled_Z0=sum(
                    (1 if bits[-1] == "0" else -1) * count
                    for bits, count in r.counts.items()
                )
                / cfg.shots,
            )
        )
    return dict(
        kind="sweep",
        rows=rows,
        parameter=parameter,
        seeds=seeds,
        config=asdict(config),
        runs=runs,
        provenance=analysis_provenance(),
        note="Fidelidade/pureza/energia derivam do ensemble e não variam com a semente. Z0 amostrado varia; seeds não estimam incerteza do modelo de ruído.",
    )
