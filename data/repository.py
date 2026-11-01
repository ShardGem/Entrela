"""Versioned, validated JSON with atomic writes and legacy read support."""

from dataclasses import asdict, fields
from datetime import datetime
from pathlib import Path
import json, os, re, tempfile
import numpy as np
from qiskit.quantum_info import Statevector, DensityMatrix
from core.types import Experiment, ExperimentResult, config_from_dict, finite, integer

STATE_LISTS = ("statevectors", "density_matrices", "ideal_statevectors")
SINGLE_STATES = ("final_state", "ideal_final_state")


def encode_state(state):
    if state is None:
        return None
    if not isinstance(state, (Statevector, DensityMatrix)) or not state.is_valid():
        raise ValueError("Estado quântico inválido")
    return {
        "kind": "density_matrix" if isinstance(state, DensityMatrix) else "statevector",
        "real": state.data.real.tolist(),
        "imag": state.data.imag.tolist(),
    }


def decode_state(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Estado deve ser um objeto")
    if raw["kind"] not in ("statevector", "density_matrix"):
        raise ValueError("Representação de estado desconhecida")
    real, imag = (
        np.asarray(raw["real"], dtype=float),
        np.asarray(raw["imag"], dtype=float),
    )
    if real.shape != imag.shape:
        raise ValueError("Dimensões real e imaginária incompatíveis")
    cls = DensityMatrix if raw["kind"] == "density_matrix" else Statevector
    try:
        state = cls(real + 1j * imag)
    except Exception as exc:
        raise ValueError("Dimensões de estado inválidas") from exc
    if not state.is_valid():
        raise ValueError("Estado inválido no arquivo")
    return state


def validate_result(config, result):
    if not isinstance(result.metadata, dict):
        raise ValueError("Metadados devem ser um objeto")
    if not isinstance(result.circuit_text, str) or (
        result.error is not None and not isinstance(result.error, str)
    ):
        raise ValueError("Texto de resultado inválido")
    integer(result.circuit_depth, "Profundidade", 0)
    for key in (*STATE_LISTS, "times", "labels"):
        value = getattr(result, key)
        if value is not None and not isinstance(value, list):
            raise ValueError(f"{key} deve ser uma lista")
    if result.labels is not None:
        if any(not isinstance(x, str) for x in result.labels) or len(
            set(result.labels)
        ) != len(result.labels):
            raise ValueError("Rótulos de snapshots inválidos")
        if result.states and len(result.labels) != len(result.states):
            raise ValueError("Rótulos e estados incompatíveis")
    if result.ideal_statevectors and len(result.ideal_statevectors) != len(
        result.states
    ):
        raise ValueError("Referência ideal e snapshots incompatíveis")
    if result.counts is not None and not isinstance(result.counts, dict):
        raise ValueError("Contagens devem ser um objeto")
    operations = result.metadata.get("operations", [])
    if not isinstance(operations, list):
        raise ValueError("Operações devem ser uma lista")
    for op in operations:
        if (
            not isinstance(op, dict)
            or not isinstance(op.get("name"), str)
            or op.get("stage") not in ("preparation", "evolution", "measurement")
        ):
            raise ValueError("Operação de circuito inválida")
        integer(op.get("step"), "Passo de operação", 0)
        if op["step"] > config.protocol.trotter_steps:
            raise ValueError("Passo fora da evolução")
        if not isinstance(op.get("qubits"), list) or not isinstance(
            op.get("parameters"), list
        ):
            raise ValueError("Parâmetros de operação inválidos")
        for q in op["qubits"]:
            integer(q, "Qubit de operação", 0)
            if q >= config.system.num_qubits:
                raise ValueError("Qubit de operação fora do sistema")
        for value in op["parameters"]:
            finite(value, "Parâmetro de porta")
    seed = result.metadata.get("effective_seed")
    if seed is not None:
        integer(seed, "Semente efetiva", 0)
        if seed >= 2**32:
            raise ValueError("Semente efetiva inválida")
    expected = 2**config.system.num_qubits
    for key in STATE_LISTS:
        for state in getattr(result, key) or []:
            cls = DensityMatrix if key == "density_matrices" else Statevector
            if (
                not isinstance(state, cls)
                or state.dim != expected
                or not state.is_valid()
            ):
                raise ValueError("Snapshot incompatível com o sistema")
    for key in SINGLE_STATES:
        state = getattr(result, key)
        if state is not None and (state.dim != expected or not state.is_valid()):
            raise ValueError("Estado final incompatível com o sistema")
    if result.statevectors and result.density_matrices:
        raise ValueError("Snapshots devem ter representação única")
    if result.times is not None and result.states:
        if len(result.times) != len(result.states):
            raise ValueError("Tempos e estados têm comprimentos diferentes")
        for value in result.times:
            finite(value, "Tempo")
        if any(
            value < 0 or value > config.protocol.total_time + 1e-8
            for value in result.times
        ):
            raise ValueError("Tempo fora da evolução")
        if any(a >= b for a, b in zip(result.times, result.times[1:])):
            raise ValueError("Tempos não ordenados")
    if result.counts is not None:
        for bits, count in result.counts.items():
            if (
                not isinstance(bits, str)
                or len(bits) != config.system.num_qubits
                or set(bits) - {"0", "1"}
            ):
                raise ValueError("Bitstring inválida")
            integer(count, "Contagem", 0)
        if sum(result.counts.values()) != config.shots:
            raise ValueError("Contagens diferem dos shots")
    for key in ("fidelity", "purity", "energy"):
        value = getattr(result, key)
        if value is not None:
            finite(value, key)
            if key != "energy" and not -1e-8 <= value <= 1 + 1e-8:
                raise ValueError("Métrica fora do intervalo físico")
    if result.mitigation is not None:
        m = result.mitigation
        if not isinstance(m, dict):
            raise ValueError("Análise ZNE deve ser um objeto")
        if m.get("success") is not True or m.get("method") not in (
            "linear",
            "quadratic",
        ):
            raise ValueError("Análise ZNE inválida")
        integer(m["qubit"], "Qubit", 0)
        if m["qubit"] >= config.system.num_qubits:
            raise ValueError("Qubit fora do sistema")
        fs, ys, es = m["scale_factors"], m["measured"], m["stderr"]
        if any(not isinstance(a, list) for a in (fs, ys, es)):
            raise ValueError("Pontos ZNE devem ser listas")
        if "coefficients" in m:
            degree = 1 if m["method"] == "linear" else 2
            if (
                not isinstance(m["coefficients"], list)
                or len(m["coefficients"]) != degree + 1
            ):
                raise ValueError("Coeficientes ZNE inválidos")
            for value in m["coefficients"]:
                finite(value, "Coeficiente")
        for key in (
            "ideal_observable",
            "baseline_absolute_error",
            "extrapolated_absolute_error",
        ):
            if key in m:
                finite(m[key], key)
        if "degrees_of_freedom" in m:
            integer(m["degrees_of_freedom"], "Graus de liberdade", 0)
        if (
            len(fs) != len(ys)
            or len(fs) != len(es)
            or len(set(fs)) != len(fs)
            or 1 not in fs
        ):
            raise ValueError("Pontos ZNE incompatíveis")
        if len(fs) < (2 if m["method"] == "linear" else 3):
            raise ValueError("Poucos pontos ZNE")
        for f in fs:
            integer(f, "Fator")
            if f % 2 != 1:
                raise ValueError("Fatores devem ser ímpares")
        for y in ys:
            finite(y, "Observável")
            if not -1 <= y <= 1:
                raise ValueError("Z medido fora de [-1,1]")
        for e in [*es, m["extrapolated_stderr"]]:
            finite(e, "Erro padrão")
            if e < 0:
                raise ValueError("Erro padrão negativo")
        finite(m["extrapolated"], "Extrapolação")
        integer(m["shots"], "Shots")
        if not isinstance(m["source_experiment_id"], str):
            raise ValueError("Fonte ZNE inválida")


class ExperimentRepository:
    def __init__(self, base_dir=None):
        self.base_dir = Path(
            base_dir
            if base_dir is not None
            else os.environ.get(
                "ENTRELA_DATA_DIR", Path.home() / ".entrela" / "experiments"
            )
        )
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.load_errors = []

    def _path(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", identifier
        ):
            raise ValueError("Identificador inválido")
        return self.base_dir / f"{identifier}.json"

    def save(self, experiment):
        path = self._path(experiment.id)
        payload = self._serialize(experiment)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.base_dir,
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                json.dump(
                    payload, stream, ensure_ascii=False, indent=2, allow_nan=False
                )
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
        self._save_summary(experiment, path)
        return path

    def _save_summary(self, experiment, path):
        # Derived cache; original JSON remains the source of truth.
        try:
            folder = self.base_dir / ".summaries"
            folder.mkdir(exist_ok=True)
            raw = self._summary_payload(experiment)
            stat = path.stat()
            payload = {
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "experiment": raw,
            }
            target = folder / path.name
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=folder, suffix=".tmp", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(payload, stream, ensure_ascii=False, allow_nan=False)
            temporary.replace(target)
        except OSError:
            if "temporary" in locals():
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _summary_payload(experiment):
        result = experiment.result
        return dict(
            schema_version=2,
            id=experiment.id,
            created_at=experiment.created_at.isoformat(),
            duration_s=experiment.duration_s,
            tags=experiment.tags,
            config=asdict(experiment.config),
            result={
                key: getattr(result, key)
                for key in (
                    "counts",
                    "fidelity",
                    "purity",
                    "energy",
                    "error",
                    "mitigation",
                )
            },
        )

    def list_summaries(self):
        """Read small derived records; decode state arrays only when opening a run."""
        records = []
        self.load_errors = []
        for path in sorted(
            self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                cache = self.base_dir / ".summaries" / path.name
                stat = path.stat()
                payload = None
                if cache.exists():
                    try:
                        saved = json.loads(cache.read_text(encoding="utf-8"))
                        if (
                            saved.get("mtime_ns") == stat.st_mtime_ns
                            and saved.get("size") == stat.st_size
                        ):
                            payload = saved["experiment"]
                    except (ValueError, KeyError, TypeError):
                        pass
                if payload is None:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(raw, dict) or raw.get("id") != path.stem:
                        raise ValueError("Identificador incompatível")
                    result = raw.get("result", {})
                    if not isinstance(result, dict) or not isinstance(
                        result.get("metadata", {}), dict
                    ):
                        raise ValueError("Resultado/metadados inválidos")
                    payload = {key: raw[key] for key in ("id", "created_at", "config")}
                    payload.update(
                        schema_version=raw.get("schema_version", 1),
                        duration_s=raw.get("duration_s", 0),
                        tags=raw.get("tags", []),
                        result={
                            key: result[key]
                            for key in (
                                "counts",
                                "fidelity",
                                "purity",
                                "energy",
                                "error",
                                "mitigation",
                            )
                            if key in result
                        },
                    )
                    exp = self._deserialize(payload)
                    self._save_summary(exp, path)
                records.append(self._deserialize(payload))
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
                self.load_errors.append(f"{path.name}: {exc}")
        return records

    def load(self, identifier):
        raw = json.loads(self._path(identifier).read_text(encoding="utf-8"))
        if raw["id"] != identifier:
            raise ValueError("Identificador do arquivo incompatível")
        return self._deserialize(raw)

    def list_all(self, limit=None):
        self.load_errors = []
        records = []
        for path in sorted(
            self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
        ):
            try:
                records.append(self.load(path.stem))
            except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
                self.load_errors.append(f"{path.name}: {exc}")
            if limit is not None and len(records) >= limit:
                break
        return records

    def delete(self, identifier):
        path = self._path(identifier)
        if not path.exists():
            return False
        path.unlink()
        (self.base_dir / ".summaries" / path.name).unlink(missing_ok=True)
        return True

    @staticmethod
    def _serialize(exp):
        finite(exp.duration_s, "Duração")
        if exp.duration_s < 0:
            raise ValueError("Duração negativa")
        if not isinstance(exp.tags, list) or any(
            not isinstance(x, str) for x in exp.tags
        ):
            raise ValueError("Tags inválidas")
        exp.config.validate()
        validate_result(exp.config, exp.result)
        result = {f.name: getattr(exp.result, f.name) for f in fields(ExperimentResult)}
        for key in STATE_LISTS:
            result[key] = (
                [encode_state(s) for s in result[key]]
                if result[key] is not None
                else None
            )
        for key in SINGLE_STATES:
            result[key] = encode_state(result[key])
        return dict(
            schema_version=2,
            config=asdict(exp.config),
            result=result,
            id=exp.id,
            created_at=exp.created_at.isoformat(),
            duration_s=exp.duration_s,
            tags=exp.tags,
        )

    @staticmethod
    def _deserialize(raw):
        if not isinstance(raw, dict):
            raise ValueError("Arquivo deve conter um objeto")
        schema = raw.get("schema_version", 1)
        if type(schema) is not int or schema not in (1, 2):
            raise ValueError("Versão de arquivo desconhecida")
        if not isinstance(raw, dict):
            raise ValueError("Arquivo deve conter um objeto")
        identifier = raw.get("id")
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", identifier
        ):
            raise ValueError("Identificador inválido")
        duration = raw.get("duration_s", 0.0)
        finite(duration, "Duração")
        if duration < 0:
            raise ValueError("Duração negativa")
        tags = raw.get("tags", [])
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError("Tags devem ser uma lista de textos")
        if not isinstance(raw.get("result", {}), dict):
            raise ValueError("Resultado inválido")
        config = config_from_dict(raw["config"])
        result = dict(raw.get("result", {}))
        if schema == 2:
            for key in STATE_LISTS:
                result[key] = (
                    [decode_state(s) for s in result[key]]
                    if result.get(key) is not None
                    else None
                )
            for key in SINGLE_STATES:
                result[key] = (
                    decode_state(result[key]) if result.get(key) is not None else None
                )
        elif result.get("statevectors"):
            raise ValueError("Estados legados não reconhecidos")
        result = ExperimentResult(**result)
        validate_result(config, result)
        created = datetime.fromisoformat(raw["created_at"])
        if created.tzinfo is None:
            from datetime import timezone

            created = created.replace(tzinfo=timezone.utc)
        return Experiment(
            config,
            result,
            id=raw["id"],
            created_at=created,
            duration_s=raw.get("duration_s", 0.0),
            tags=raw.get("tags", []),
        )
