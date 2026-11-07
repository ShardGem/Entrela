"""Atomic storage for derived scientific artifacts, separate from source runs."""

import json
import math
import os
from pathlib import Path
import re
import tempfile


KINDS = {"temporal", "convergence", "sweep", "trotter_noise", "mitigation_benchmark", "heatmap", "zne_stability", "equal_budget"}

# Campos utilizados como coordenadas ou séries pelos gráficos. Outras colunas
# textuais e metadados continuam permitidos para preservar análises históricas.
NUMERIC_COLUMNS = {
    "snapshot", "time", "steps", "order", "value", "seed", "x", "y",
    "fidelity", "fidelity_exact", "purity", "energy", "infidelity",
    "trotter_infidelity", "fidelity_ideal_exact", "fidelity_noisy_exact",
    "fidelity_noisy_ideal", "ideal_infidelity", "noisy_infidelity",
    "depth", "gate_count", "estimate", "stderr", "absolute_error",
    "circuits", "shots", "retained_shots", "acceptance", "duration_s",
    "acquisition_s", "processing_s", "ideal_runtime_s", "noisy_runtime_s",
    "mean_estimate", "bias", "sample_variance", "mse", "rmse",
    "mean_absolute_error", "stderr_mean", "out_of_range", "shots_setting",
    "repetitions", "shots_per_method", "circuits_per_method",
    "mean_reported_stderr", "degrees_of_freedom", "mean_acquisition_s",
    "mean_processing_s", "mean_duration_s", "acquisition_group_s",
    "sampled_Z0", "negativity_q0_rest",
}


def _number(value, label, *, minimum=None):
    try:
        finite = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{label} deve ser um número finito.")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} deve ser maior ou igual a {minimum}.")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} deve ser texto não vazio.")


def _validate_render_fields(data):
    """Valida o necessário à visualização, sem exigir metadados de reprodução."""
    kind = data["kind"]
    required = {
        "temporal": ("time",), "convergence": ("steps",), "sweep": ("value",),
        "trotter_noise": ("steps", "ideal_infidelity", "noisy_infidelity"),
        "heatmap": ("x", "y"), "zne_stability": (), "equal_budget": (),
        "mitigation_benchmark": (),
    }[kind]
    for index, row in enumerate(data["rows"], 1):
        for key in required:
            if key not in row:
                raise ValueError(f"A análise {kind} precisa da coluna {key}.")
            _number(row[key], f"Linha {index}, {key}")
        for key, value in row.items():
            numeric = key in NUMERIC_COLUMNS or re.fullmatch(r"(?:Z\d+(?:Z\d+)?|entropy_q\d+)", key)
            if (numeric and value is not None) or type(value) in (int, float):
                _number(value, f"Linha {index}, {key}", minimum=0 if key == "stderr" else None)
        if kind in ("zne_stability", "equal_budget", "mitigation_benchmark"):
            _text(row.get("method"), f"Linha {index}, método")
        if kind == "mitigation_benchmark":
            _text(row.get("label"), f"Linha {index}, nome do método")
            _text(row.get("status"), f"Linha {index}, estado do método")
    if kind == "heatmap":
        options = data.get("options", {})
        _text(options.get("x_parameter"), "Parâmetro do eixo X")
        _text(options.get("y_parameter"), "Parâmetro do eixo Y")
    if kind == "mitigation_benchmark":
        cost = data.get("actual_cost")
        if not isinstance(cost, dict):
            raise ValueError("O benchmark precisa registrar o custo efetivamente adquirido.")
        for key in ("circuits", "shots", "acquisition_s"):
            _number(cost.get(key), f"Custo {key}", minimum=0)
        _number(data.get("ideal_observable"), "Observável ideal")


def validate_analysis(data, source_id=None):
    if not isinstance(data, dict) or not isinstance(data.get("kind"), str) or data["kind"] not in KINDS:
        raise ValueError("Tipo de análise não reconhecido.")
    if source_id is not None and data.get("source_id") != source_id:
        raise ValueError("Esta análise pertence a outra execução.")
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise ValueError("A análise deve conter de 1 a 10.000 linhas.")
    if any(not isinstance(row, dict) or set(row) != set(rows[0]) for row in rows):
        raise ValueError("As linhas da análise devem usar as mesmas colunas.")
    if any(not isinstance(key, str) or not key for key in rows[0]):
        raise ValueError("As colunas da análise devem ter nomes de texto.")
    if not isinstance(data.get("note"), str):
        raise ValueError("A análise precisa registrar suas referências e limitações.")
    for key in ("config", "provenance", "options", "protocol"):
        if key in data and not isinstance(data[key], dict):
            raise ValueError(f"O campo {key} da análise deve ser um objeto.")
    for key in ("source_id", "analysis_id", "id", "created_at"):
        if key in data:
            _text(data[key], f"Campo {key}")
    protocol_fields = data.get("protocol", {}).get("fields", {})
    if not isinstance(protocol_fields, dict) or any(not isinstance(value, str) for value in protocol_fields.values()):
        raise ValueError("Os campos do protocolo devem conter textos.")
    _validate_render_fields(data)
    # Reject non-finite values before storing or plotting an external artifact.
    try:
        json.dumps(data, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("A análise deve conter dados JSON finitos.") from exc
    return data


def save_analysis(data, filepath):
    validate_analysis(data)
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path


def load_analysis(filepath, source_id):
    data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    return validate_analysis(data, source_id)
