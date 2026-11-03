"""Atomic storage for derived scientific artifacts, separate from source runs."""

import json
import os
from pathlib import Path
import tempfile


KINDS = {"temporal", "convergence", "sweep", "trotter_noise", "mitigation_benchmark", "heatmap", "zne_stability", "equal_budget"}


def validate_analysis(data, source_id=None):
    if not isinstance(data, dict) or data.get("kind") not in KINDS:
        raise ValueError("Tipo de análise não reconhecido.")
    if source_id is not None and data.get("source_id") != source_id:
        raise ValueError("Esta análise pertence a outra execução.")
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows or len(rows) > 10000:
        raise ValueError("A análise deve conter de 1 a 10.000 linhas.")
    if any(not isinstance(row, dict) or set(row) != set(rows[0]) for row in rows):
        raise ValueError("As linhas da análise devem usar as mesmas colunas.")
    if not isinstance(data.get("note"), str):
        raise ValueError("A análise precisa registrar suas referências e limitações.")
    # Reject non-finite values before storing or plotting an external artifact.
    json.dumps(data, allow_nan=False)
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
