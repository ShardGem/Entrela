"""Explicit numerical checks of a reproduction, separate from shot identity."""
from dataclasses import asdict, replace
from hashlib import sha256
import json

import numpy as np
from qiskit.quantum_info import DensityMatrix

from core.types import finite


def input_fingerprint(config, effective_seed, operations):
    payload = dict(config=asdict(replace(config, seed=effective_seed)), operations=operations)
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def compare_reproduction(source, reproduced, *, atol=1e-9):
    finite(atol, "Tolerância")
    if atol <= 0:
        raise ValueError("Tolerância deve ser positiva")
    expected = replace(source.config, seed=source.result.metadata.get("effective_seed", source.config.seed))
    actual = replace(reproduced.config, seed=reproduced.result.metadata.get("effective_seed", reproduced.config.seed))
    same_config = expected == actual
    differences = {}
    for key in ("fidelity", "purity", "energy"):
        a, b = getattr(source.result, key), getattr(reproduced.result, key)
        differences[key] = None if a is None or b is None else abs(float(a)-float(b))
    a, b = source.result.final_state, reproduced.result.final_state
    state_error = None
    if a is not None and b is not None and a.dim == b.dim:
        state_error = float(np.max(np.abs(DensityMatrix(a).data-DensityMatrix(b).data)))
    environments = {}
    for key in ("entrela_version", "python", "platform", "method", "versions"):
        previous = source.result.metadata.get(key)
        current = reproduced.result.metadata.get(key)
        if key == "platform":
            previous = source.result.metadata.get("reproduction", {}).get("platform")
            current = reproduced.result.metadata.get("reproduction", {}).get("platform")
        if previous != current:
            environments[key] = dict(original=previous, reproduced=current)
    available = state_error is not None
    matched = (same_config and available and state_error <= atol and
               all(value is None or value <= atol for value in differences.values()))
    return dict(schema_version=1, source_id=source.id, status="matched" if matched else "different" if available else "unavailable",
                same_configuration=same_config, absolute_tolerance=atol,
                density_matrix_max_absolute_difference=state_error, metric_absolute_differences=differences,
                counts_match=source.result.counts == reproduced.result.counts,
                environment_differences=environments,
                note="A verificação compara o estado e as métricas numéricas. Igualdade de contagens é informada separadamente; sementes não garantem amostras idênticas entre versões ou plataformas.")


def scientific_context(experiment):
    result, config = experiment.result, experiment.config
    reference = "mesmo circuito sem ruído" if config.circuit else "mesmo circuito Suzuki–Trotter sem ruído"
    lines = ["Referência da fidelidade: " + reference + "."]
    if config.circuit is None:
        lines.append("A fidelidade ao circuito ideal não mede o erro de Trotter. Consulte a referência exata em Análises.")
    lines.append("Probabilidades e métricas do estado são calculadas do ensemble. A seed afeta as contagens amostradas; não representa incerteza do modelo de ruído.")
    if config.noise.enabled and config.noise.kind == "Termico":
        lines.append(f"Hipóteses térmicas: {config.noise.gate_time_1q_ns:g} ns por porta 1q e {config.noise.gate_time_2q_ns:g} ns por porta 2q. O tempo do Hamiltoniano é adimensional; não há calibração de hardware.")
    if result.mitigation:
        lines.append("ZNE extrapola ⟨Z⟩; fidelidade e pureza deste registro pertencem ao estado da execução de origem.")
    return "\n".join(lines)


def compare_mitigation_reproduction(source, analysis, *, atol=1e-9):
    finite(atol,"Tolerância")
    if atol <= 0:
        raise ValueError("Tolerância deve ser positiva")
    original = source.result.mitigation or {}
    settings = ("method","qubit","shots","scale_factors","seed")
    same = all(original.get(key)==analysis.get(key) for key in settings)
    errors = {}
    for key in ("measured","stderr","coefficients","extrapolated","extrapolated_stderr"):
        if original.get(key) is None or analysis.get(key) is None:
            errors[key] = None
            continue
        a,b = np.asarray(original[key],float),np.asarray(analysis[key],float)
        errors[key] = float(np.max(np.abs(a-b))) if a.shape == b.shape else None
    available = all(value is not None for value in errors.values())
    matched = same and available and all(value <= atol for value in errors.values())
    return dict(schema_version=1,kind="zne",source_id=source.id,status="matched" if matched else "different" if available else "unavailable",
                same_configuration=same,absolute_tolerance=atol,metric_absolute_differences=errors,
                counts_match=[sample.get("counts") for sample in original.get("samples",[])] == [sample.get("counts") for sample in analysis.get("samples",[])],
                note="Comparação da estimativa ZNE, amostras e ajuste. As métricas de estado permanecem as da fonte; não representam um estado mitigado.")
