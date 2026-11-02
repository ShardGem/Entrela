"""Portable scientific data exports; JSON never executes user code."""

import csv, io, json, tempfile, zipfile
from pathlib import Path
from data.repository import ExperimentRepository


def export_counts_csv(counts, filepath):
    path = Path(filepath)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Bitstring", "Counts"])
        writer.writerows(sorted(counts.items()))
    return path


def _json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def _atomic_text(path, text):
    """Stage beside the destination so replacement stays on the same filesystem."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="", dir=path.parent,
            prefix="." + path.name + ".", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _experiment_csv(experiment, annotation=None):
    # Reuse the versioned serializer: no duplicate scientific persistence schema.
    raw = ExperimentRepository._serialize(experiment)
    config, result = raw["config"], raw["result"]
    metadata, mitigation = result["metadata"], result.get("mitigation")
    counts = result.get("counts") or {}
    total = sum(counts.values())
    identity = {
        "experiment_id": experiment.id,
        "title": (annotation or {}).get("title") or experiment.id,
        "created_at": experiment.created_at.isoformat(),
        "duration_s": experiment.duration_s,
        "requested_seed": config.get("seed"),
        "effective_seed": metadata.get("effective_seed"),
        "simulator_method": metadata.get("method"),
        "noise_model": config["noise"]["kind"] if config["noise"]["enabled"] else "Desligado",
        "mitigation_method": (mitigation or {}).get("method"),
        "shots": config["shots"],
        "fidelity": result.get("fidelity"),
        "purity": result.get("purity"),
        "energy": result.get("energy"),
        "config_json": _json_text(config),
        "metadata_json": _json_text(metadata),
        "mitigation_json": _json_text(mitigation),
        "annotation_json": _json_text(annotation),
    }
    table = io.StringIO(newline="")
    writer = csv.DictWriter(table, fieldnames=[*identity, "bitstring", "counts", "frequency"])
    writer.writeheader()
    for bits, count in sorted(counts.items()):
        writer.writerow(dict(identity, bitstring=bits, counts=count,
                             frequency=count / total if total else None))
    if not counts:
        writer.writerow(dict(identity, bitstring=None, counts=None, frequency=None))
    return table.getvalue()


def export_experiment_csv(experiment, filepath, annotation=None):
    """Export observations with complete inputs, provenance and source metrics.

    Complex quantum states remain available in the full experiment JSON. Source
    fidelity/purity are never relabeled as mitigated-state metrics.
    """
    path = Path(filepath)
    _atomic_text(path, _experiment_csv(experiment, annotation))
    return path


def export_analysis(data, filepath):
    """Export a complete JSON, or CSV plus its adjacent provenance manifest.

    Every non-row field is retained in ``name.metadata.json``, including raw
    benchmark samples, effective configurations, seeds and per-run environments.
    """
    path = Path(filepath)
    if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
        raise ValueError("A análise deve conter uma lista de linhas.")
    # Validate serialization before touching either output.
    payload = _json_text(data)
    if path.suffix.lower() == ".json":
        _atomic_text(path, payload)
        return path
    if path.suffix.lower() != ".csv":
        raise ValueError("Escolha uma extensão .csv ou .json para a análise.")
    rows = data["rows"]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("A análise deve conter linhas não vazias em formato de objeto.")
    columns = list(dict.fromkeys(key for row in rows for key in row))
    if not columns or any(not isinstance(key, str) for key in columns):
        raise ValueError("As colunas da análise devem ter nomes textuais.")
    table = io.StringIO(newline="")
    writer = csv.DictWriter(table, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: _json_text(value) if isinstance(value, (dict, list)) else value
                         for key, value in row.items()})
    manifest = {key: value for key, value in data.items() if key != "rows"}
    manifest["csv_export"] = {
        "filename": path.name, "row_count": len(rows), "columns": columns,
        "note": "Preserve este arquivo junto ao CSV para manter configurações e proveniência.",
    }
    _atomic_text(path.with_suffix(".metadata.json"), _json_text(manifest))
    _atomic_text(path, table.getvalue())
    return path


def export_figure(fig, filepath, dpi=150):
    path = Path(filepath)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    return path


def export_experiment_json(experiment, filepath):
    path = Path(filepath)
    path.write_text(
        json.dumps(
            ExperimentRepository._serialize(experiment),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        ),
        encoding="utf-8",
    )
    return path


def import_experiment_json(filepath):
    try:
        raw = json.loads(Path(filepath).read_text(encoding="utf-8"))
        return ExperimentRepository._deserialize(raw)
    except (KeyError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("Arquivo de experimento inválido ou incompleto") from exc


def export_run_bundle(experiment, filepath, annotation=None, analysis=None):
    path = Path(filepath)
    payload = json.dumps(
        ExperimentRepository._serialize(experiment),
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )
    table = io.StringIO(newline="")
    writer = csv.writer(table)
    writer.writerow(["Bitstring", "Counts"])
    writer.writerows(sorted((experiment.result.counts or {}).items()))
    # Optional additions preserve the original three-member bundle contract.
    manifest = None
    if annotation is not None or analysis is not None:
        manifest = _json_text({
            "experiment_id": experiment.id,
            "created_at": experiment.created_at.isoformat(),
            "title": (annotation or {}).get("title") or experiment.id,
            "annotation": annotation,
            "experiment_file": "experimento.json",
            "scientific_csv": "resultados.csv",
            "analysis_file": "analyses.json" if analysis is not None else None,
            "note": "O JSON do experimento preserva o esquema e os estados completos. Anotações não alteram os resultados científicos.",
        })
    analysis_payload = _json_text(analysis) if analysis is not None else None
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("experimento.json", payload)
        archive.writestr("contagens.csv", table.getvalue())
        archive.writestr("circuito.txt", experiment.result.circuit_text)
        if manifest is not None:
            archive.writestr("manifest.json", manifest)
            archive.writestr("resultados.csv", _experiment_csv(experiment, annotation))
        if analysis_payload is not None:
            archive.writestr("analyses.json", analysis_payload)
    return path


def result_interpretation(experiment):
    result, config = experiment.result, experiment.config
    if result.error:
        return (
            "A execução falhou. Nenhuma conclusão científica foi gerada: "
            + result.error
        )
    lines = []
    if result.fidelity is not None and config.circuit is not None:
        lines.append(
            f"Fidelidade {result.fidelity:.4f} ao mesmo circuito sem ruído. O eixo da evolução é o índice da porta; não há Hamiltoniano nem tempo físico definido."
        )
    elif result.fidelity is not None:
        lines.append(
            f"Fidelidade {result.fidelity:.4f} em relação ao mesmo circuito Suzuki–Trotter sem ruído. "
            "Essa comparação não mede o erro de aproximação de Trotter."
        )
    if result.purity is not None:
        lines.append(
            f"Pureza global: {result.purity:.4f}. A pureza de cada qubit pode ser diferente da global."
        )
    counts = result.counts or {}
    total = sum(counts.values())
    if (
        config.system.initial_state == "bell"
        and config.system.num_qubits == 2
        and config.system.J == 0
        and config.system.h == 0
        and total
    ):
        correlation = (counts.get("00", 0) + counts.get("11", 0)) / total
        lines.append(
            f"{correlation:.1%} das {total} medições ficaram em 00 ou 11. "
            "A distribuição em uma única base, isoladamente, não comprova emaranhamento."
        )
        if counts.get("01", 0) + counts.get("10", 0):
            lines.append(
                "Há medições 01/10: a correlação perfeita do Bell ideal foi reduzida."
            )
    if total:
        lines.append(
            f"Amostragem: {total} shots. Erro padrão máximo de uma frequência binomial: {0.5 / total**0.5:.2%}."
        )
    if result.mitigation:
        lines.append(
            "A análise ZNE estima um observável. Os valores de fidelidade e pureza acima pertencem à simulação original."
        )
    return (
        "\n\n".join(lines) or "Não há dados suficientes para interpretar este registro."
    )
