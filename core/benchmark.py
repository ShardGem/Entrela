"""Controlled comparison of observable mitigation, with shared raw measurements.

ZNE variants estimate Z, never a mitigated density matrix. Z-parity verification
is applicable only when the ideal circuit is in a deterministic parity sector.
Its state metrics describe an exact simulated conditional ensemble, not tomography
from Z measurements. Compilation to u/cx is part of this benchmark's noise model.
"""

from dataclasses import asdict, replace
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import platform
from secrets import randbits
from time import perf_counter
from uuid import uuid4

import numpy as np
from qiskit.quantum_info import DensityMatrix, SparsePauliOp, Statevector
from qiskit_aer import AerSimulator

from core import __version__
from core.circuits import build_circuit, build_editor_circuit, _build_hamiltonian
from core.metrics import fidelity, purity, energy_expectation
from core.mitigation import (
    _expectation_z, _insert_identity_pairs, compile_unitary, fit_zne_samples,
)
from core.noise import build_noise_model
from core.simulation import SimulationCancelled
from core.types import integer


def _unitary(config):
    if config.circuit is not None:
        return build_editor_circuit(
            config.circuit, save_snapshots=False, save_final=False, measure=False,
        )[0]
    s, p = config.system, config.protocol
    return build_circuit(
        s.num_qubits, s.hamiltonian, s.J, s.h, s.periodic,
        p.total_time, p.trotter_steps, False,
        initial_state=s.initial_state, trotter_order=p.trotter_order,
        save_final=False, measure=False,
    )[0]


def _state_payload(state):
    return {"kind": "density_matrix", "real": state.data.real.tolist(),
            "imag": state.data.imag.tolist()}


def _row(method, label, **values):
    row = dict(
        method=method, label=label, status="available", reason="",
        estimate=None, stderr=None, absolute_error=None,
        fidelity=None, purity=None, energy=None,
        circuits=0, shots=0, retained_shots=None, acceptance=None,
        acquisition_s=0.0, processing_s=0.0, duration_s=0.0,
        shared_samples=[], state_metrics_source=None,
    )
    row.update(values)
    return row


def mitigation_benchmark(
    experiment, *, shots=None, seed=None, qubit=0,
    scale_factors=(1, 3, 5), progress=None, is_cancelled=None,
):
    """Return a JSON-ready analysis; cancellation happens between Aer operations.

    All rows use the same u/cx circuit and noise parameters. The baseline is
    recomputed rather than reusing the source's possibly different native basis.
    Three samples are shared by the two ZNE fits; baseline and parity use factor 1.
    Row costs are standalone-equivalent, and must not be summed as actual cost.
    """
    started = perf_counter()
    config = experiment.config
    config.validate()
    if experiment.result.error:
        raise ValueError("A execução de origem falhou; execute novamente antes do benchmark")
    shots = config.shots if shots is None else shots
    integer(shots, "Shots")
    if shots > 1_000_000:
        raise ValueError("Limite de 1.000.000 shots por fator")
    integer(qubit, "Qubit", 0)
    if qubit >= config.system.num_qubits:
        raise ValueError("Qubit fora do sistema")
    factors = list(scale_factors)
    if len(factors) < 3 or len(factors) > 5 or len(set(factors)) != len(factors) or 1 not in factors:
        raise ValueError("Use de três a cinco fatores distintos, incluindo 1")
    for factor in factors:
        integer(factor, "Fator")
        if factor % 2 != 1 or factor > 9:
            raise ValueError("Fatores devem ser ímpares entre 1 e 9")
    if seed is None:
        seed = experiment.result.metadata.get("effective_seed", config.seed)
    seed = randbits(32) if seed is None else seed
    integer(seed, "Semente", 0)
    if seed >= 2**32:
        raise ValueError("Semente deve estar entre 0 e 4294967295")

    def checkpoint(percent):
        if is_cancelled and is_cancelled():
            raise SimulationCancelled()
        if progress:
            progress(percent)

    checkpoint(0)
    native = compile_unitary(_unitary(config), seed)
    # Folding high-order Hamiltonians can otherwise create extremely large jobs.
    if len(native.data) * max(factors) > 100_000:
        raise ValueError("Benchmark excede 100.000 portas por circuito; reduza passos ou fatores")
    noise = build_noise_model(config.noise)
    ideal = Statevector.from_instruction(native)
    label = ["I"] * native.num_qubits
    label[-1 - qubit] = "Z"
    observable = SparsePauliOp("".join(label))
    ideal_z = float(np.real(ideal.expectation_value(observable)))
    H = None if config.circuit is not None else _build_hamiltonian(
        config.system.num_qubits, config.system.hamiltonian,
        config.system.J, config.system.h, config.system.periodic,
    )
    sim = AerSimulator(method="density_matrix", noise_model=noise, max_parallel_threads=2)
    samples, baseline_state = [], None
    for i, factor in enumerate(factors):
        checkpoint(5 + int(75 * i / len(factors)))
        folded = _insert_identity_pairs(native, (factor - 1) // 2)
        counts_by_gate = dict(folded.count_ops())
        depth = folded.depth()
        if factor == 1:
            folded.save_density_matrix(label="benchmark_final")
        folded.measure_all()
        sample_seed = (seed + i) % 2**32
        sample_start = perf_counter()
        execution = sim.run(folded, shots=shots, seed_simulator=sample_seed).result()
        acquisition = perf_counter() - sample_start
        if not execution.success:
            raise RuntimeError(str(execution.status))
        counts = dict(execution.get_counts())
        mean = _expectation_z(counts, native.num_qubits, qubit)
        sample = dict(
            scale_factor=factor, effective_seed=sample_seed, shots=shots,
            counts=counts, estimate=mean,
            stderr=float(np.sqrt(max(0.0, 1 - mean**2) / shots)),
            acquisition_s=acquisition, gate_counts=counts_by_gate, depth=depth,
        )
        if factor == 1:
            baseline_state = DensityMatrix(execution.data()["benchmark_final"])
            sample["state"] = _state_payload(baseline_state)
        samples.append(sample)
    checkpoint(85)
    baseline = next(s for s in samples if s["scale_factor"] == 1)
    row_start = perf_counter()
    rows = [_row(
        "none", "Sem mitigação", estimate=baseline["estimate"],
        stderr=baseline["stderr"], absolute_error=abs(baseline["estimate"] - ideal_z),
        fidelity=fidelity(baseline_state, ideal), purity=purity(baseline_state),
        energy=None if H is None else energy_expectation(baseline_state, H),
        circuits=1, shots=shots, retained_shots=shots, acceptance=1.0,
        acquisition_s=baseline["acquisition_s"], shared_samples=[1],
        state_metrics_source="ensemble simulado na base compilada u/cx",
    )]
    rows[0]["processing_s"] = perf_counter() - row_start
    rows[0]["duration_s"] = rows[0]["acquisition_s"] + rows[0]["processing_s"]
    fits = {}
    for method in ("linear", "quadratic"):
        row_start = perf_counter()
        fit = fit_zne_samples(
            factors, [s["estimate"] for s in samples], [s["stderr"] for s in samples], method,
        )
        fits[method] = fit
        processing = perf_counter() - row_start
        acquisition = sum(s["acquisition_s"] for s in samples)
        rows.append(_row(
            "zne_" + method, "ZNE " + ("linear" if method == "linear" else "quadrática"),
            estimate=fit["extrapolated"], stderr=fit["extrapolated_stderr"],
            absolute_error=abs(fit["extrapolated"] - ideal_z),
            circuits=len(factors), shots=shots * len(factors),
            acquisition_s=acquisition, processing_s=processing,
            duration_s=acquisition + processing, shared_samples=list(factors),
            reason="Estima Z; não reconstrói estado mitigado. Os ajustes compartilham as mesmas amostras.",
        ))
    # Diagonal projector onto a known deterministic Z-parity sector. q0 is LSB.
    row_start = perf_counter()
    parity = np.asarray([(-1) ** index.bit_count() for index in range(2**native.num_qubits)])
    parity_mean = float(np.dot(ideal.probabilities(), parity))
    symmetry = dict(observable="Z" * native.num_qubits, ideal_expectation=parity_mean,
                    tolerance=1e-10, sector=None, ensemble_acceptance=None)
    verification = _row("symmetry_parity", "Verificação de paridade Z", status="unavailable")
    if abs(abs(parity_mean) - 1) > symmetry["tolerance"]:
        verification["reason"] = "O estado ideal não tem paridade Z determinística; pós-seleção não se aplica."
    else:
        sector = 1 if parity_mean > 0 else -1
        symmetry["sector"] = sector
        selected = {bits: count for bits, count in baseline["counts"].items()
                    if (-1) ** bits.replace(" ", "").count("1") == sector}
        retained = sum(selected.values())
        mask = (parity == sector).astype(float)
        projected = baseline_state.data * np.outer(mask, mask)
        probability = float(np.trace(projected).real)
        symmetry["ensemble_acceptance"] = probability
        symmetry["retained_counts"] = selected
        if retained == 0 or probability <= 1e-15:
            verification["reason"] = "Nenhum shot foi aceito no setor de paridade; aumente shots ou reduza ruído."
        else:
            conditional = DensityMatrix(projected / probability)
            mean = _expectation_z(selected, native.num_qubits, qubit)
            verification.update(
                status="available", estimate=mean,
                stderr=float(np.sqrt(max(0.0, 1 - mean**2) / retained)),
                absolute_error=abs(mean - ideal_z),
                fidelity=fidelity(conditional, ideal), purity=purity(conditional),
                energy=None if H is None else energy_expectation(conditional, H),
                state_metrics_source="ensemble condicionado simulado; não é tomografia das contagens",
                reason="Pós-seleção no setor ideal de paridade Z. Pode descartar shots e não detecta todo erro.",
            )
        verification.update(
            circuits=1, shots=shots, retained_shots=retained, acceptance=retained / shots,
            acquisition_s=baseline["acquisition_s"], shared_samples=[1],
        )
    verification["processing_s"] = perf_counter() - row_start
    verification["duration_s"] = verification["acquisition_s"] + verification["processing_s"]
    rows.append(verification)
    checkpoint(98)
    operations = [dict(name=ins.operation.name,
                       qubits=[native.find_bit(q).index for q in ins.qubits],
                       parameters=[float(v) for v in ins.operation.params])
                  for ins in native.data]
    native_document = dict(num_qubits=native.num_qubits,
                           global_phase=float(native.global_phase), operations=operations)
    replay_config = asdict(replace(config, seed=seed, shots=shots))
    fingerprint = sha256(json.dumps(
        dict(config=replay_config, native_circuit=native_document,
             scale_factors=factors, qubit=qubit), sort_keys=True, allow_nan=False,
    ).encode("utf-8")).hexdigest()
    result = dict(
        kind="mitigation_benchmark", schema_version=1,
        id=uuid4().hex, created_at=datetime.now(timezone.utc).isoformat(),
        source_id=experiment.id, config=replay_config,
        rows=rows, samples=samples, fits=fits, symmetry=symmetry,
        ideal_observable=ideal_z, qubit=qubit, scale_factors=factors,
        provenance=dict(
            fingerprint=fingerprint, effective_seed=seed,
            requested_seed=config.seed,
            seed_policy="seed_simulator=(effective_seed+índice_do_fator) mod 2³²",
            entrela_version=__version__, python=platform.python_version(),
            platform=platform.platform(),
            versions={name: version(name) for name in ("qiskit", "qiskit-aer", "numpy", "scipy")},
            source_versions=dict(experiment.result.metadata.get("versions", {})),
            simulator=dict(name="AerSimulator", method="density_matrix", max_parallel_threads=2),
            noise=asdict(config.noise), native_basis=["u", "cx"], optimization_level=0,
            native_circuit=native_document, folding="local U (U† U)^k; sem otimização após folding",
            thermal_gate_time_ns=50.0,
            fidelity_reference="Mesmo circuito compilado em u/cx sem ruído; não evolução exata exp(-iHt)",
            uncertainty="Erro padrão de amostragem; exclui viés de extrapolação e incerteza do modelo.",
        ),
        actual_cost=dict(circuits=len(factors), shots=len(factors) * shots,
                         acquisition_s=sum(s["acquisition_s"] for s in samples)),
        duration_s=perf_counter() - started,
        note=("ZNE linear e quadrática são variantes da mesma técnica e compartilham amostras. "
              "Verificação de paridade é uma segunda técnica somente quando aplicável. "
              "O setor de paridade é inferido da simulação ideal; uso em hardware exige justificar a simetria independentemente. "
              "Custos por linha equivalem ao uso isolado: não somar linhas compartilhadas. "
              "O benchmark recompila em u/cx e recalcula o baseline; a decomposição pode mudar "
              "o canal de ruído em relação à execução de origem. Semente não garante identidade entre versões/plataformas."),
    )
    checkpoint(100)
    return result
