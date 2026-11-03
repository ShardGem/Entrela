"""Paired digital-simulation study: Trotter approximation and configured noise."""

from dataclasses import asdict, replace
from datetime import datetime, timezone
from secrets import randbits

from core.analysis import analysis_provenance, analysis_run_record, checkpoint, exact_states
from core.metrics import fidelity
from core.simulation import run_experiment


def _gate_count(result):
    return sum(
        operation["name"] not in ("measure", "barrier")
        for operation in result.metadata.get("operations", [])
    )


def _run_record(experiment, condition, steps):
    """Serializable inputs, raw measurements and actual environment per run."""
    return dict(analysis_run_record(experiment), condition=condition, steps=steps)


def trotter_noise_study(
    experiment, steps=(1, 2, 4, 8, 16), progress=None, is_cancelled=None, *, seed=None
):
    """Compare ideal and configured-noise circuits against the same exact state.

    All simulations use the source's final time, Suzuki order, noise parameters,
    shots and effective seed. Only step count, snapshots and the ideal condition's
    noise-enabled flag change. Ensemble fidelities are not shot estimators.
    """
    config = experiment.config
    config.validate()
    if config.circuit is not None:
        raise ValueError("O estudo Trotter × ruído requer uma evolução por Hamiltoniano.")
    if experiment.result.error:
        raise ValueError("Abra uma execução concluída sem erro para realizar o estudo.")
    steps = list(steps)
    if (
        not steps
        or len(steps) > 10
        or any(type(step) is not int or not 1 <= step <= 200 for step in steps)
        or len(set(steps)) != len(steps)
    ):
        raise ValueError("Use de um a dez valores inteiros distintos entre 1 e 200.")
    checkpoint(is_cancelled, progress, 0)
    if seed is None:
        seed = experiment.result.metadata.get("effective_seed")
    if seed is None:
        seed = config.seed if config.seed is not None else randbits(32)
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError("Semente deve ser um inteiro entre 0 e 4294967295.")
    configs = []
    for step in steps:
        noisy = replace(
            config,
            protocol=replace(config.protocol, trotter_steps=step, save_snapshots=False),
            seed=seed,
        )
        ideal = replace(noisy, noise=replace(config.noise, enabled=False))
        # Validate every point before launching any simulation.
        noisy.validate()
        ideal.validate()
        configs.append((step, ideal, noisy))
    target = exact_states(config, [config.protocol.total_time])[0]
    checkpoint(is_cancelled, progress, 5)
    rows, runs = [], []
    for index, (step, ideal_config, noisy_config) in enumerate(configs):
        checkpoint(is_cancelled, progress, 5 + int(90 * index / len(configs)))
        ideal = run_experiment(ideal_config, is_cancelled=is_cancelled)
        checkpoint(is_cancelled, None, 0)
        noisy = run_experiment(noisy_config, is_cancelled=is_cancelled)
        f_ideal = fidelity(ideal.result.final_state, target)
        f_noisy = fidelity(noisy.result.final_state, target)
        rows.append(
            dict(
                steps=step,
                order=config.protocol.trotter_order,
                seed=seed,
                fidelity_ideal_exact=f_ideal,
                fidelity_noisy_exact=f_noisy,
                ideal_infidelity=max(0.0, 1 - f_ideal),
                noisy_infidelity=max(0.0, 1 - f_noisy),
                fidelity_noisy_ideal=noisy.result.fidelity,
                purity=noisy.result.purity,
                energy=noisy.result.energy,
                depth=noisy.result.circuit_depth,
                gate_count=_gate_count(noisy.result),
                ideal_runtime_s=ideal.duration_s,
                noisy_runtime_s=noisy.duration_s,
            )
        )
        runs.extend(
            [_run_record(ideal, "ideal", step), _run_record(noisy, "configured_noise", step)]
        )
    checkpoint(is_cancelled, progress, 100)
    best = min(rows, key=lambda row: row["noisy_infidelity"])
    return dict(
        kind="trotter_noise",
        source_id=experiment.id,
        config=asdict(config),
        options=dict(steps=steps,seed=seed),
        rows=rows,
        runs=runs,
        provenance={
            **analysis_provenance(experiment),
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_effective_seed": seed,
            "requested_steps": steps,
            "noise_enabled": config.noise.enabled,
            "exact_reference": "exp(−iHt) aplicado ao estado inicial ideal; mesmo tempo final",
            "approximation_reference": "Circuito Suzuki–Trotter sem ruído na mesma ordem e passos",
            "best_evaluated": {
                "steps": best["steps"],
                "noisy_infidelity": best["noisy_infidelity"],
                "scope": "Somente os passos efetivamente calculados; não é um ótimo global.",
            },
            "time_unit": "adimensional (ℏ=1)",
            "noise_scope": "Ruído por operação, inclusive preparação; térmico educativo de 50 ns por porta.",
        },
        note=(
            "Fidelidades do ensemble contra a mesma evolução exata. A curva ideal isola a "
            "aproximação Trotter; a curva ruidosa inclui aproximação e ruído, sem decomposição "
            "aditiva dos erros. Shots e sementes não estimam incerteza dessas fidelidades. "
            "O melhor ponto é restrito aos passos calculados; tempos são medições desta máquina."
            + (" O ruído da fonte está desligado; as curvas devem coincidir." if not config.noise.enabled else "")
        ),
    )
