"""Immutable protocol revisions, separate from execution results."""

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from uuid import uuid4
from core.types import config_from_dict
from core.export import _atomic_text
from data.analyses import KINDS


class ProtocolRepository:
    def __init__(self, directory):
        self.directory = Path(directory)

    def save(self, source, kind, options, fields):
        if kind not in KINDS:
            raise ValueError("Tipo de análise não suportado no protocolo.")
        title = fields.get("title", "").strip()
        if not title or len(title) > 160:
            raise ValueError("Informe um nome de protocolo de até 160 caracteres.")
        for key in ("question", "hypothesis", "controls", "evidence_ref"):
            if not isinstance(fields.get(key, ""), str) or len(fields.get(key, "")) > 10000:
                raise ValueError("Texto do protocolo inválido ou muito longo.")
        source.config.validate()
        config = asdict(source.config)
        config["seed"] = source.result.metadata.get("effective_seed", config["seed"])
        identifier = uuid4().hex
        data = dict(schema_version=1, protocol_id=identifier,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    source_id=source.id, config=config, kind=kind, options=options,
                    fields={key: fields.get(key, "") for key in ("title", "question", "hypothesis", "controls", "evidence_ref")},
                    source_versions=source.result.metadata.get("versions", {}))
        payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)
        self.directory.mkdir(parents=True, exist_ok=True)
        _atomic_text(self.directory / (identifier + ".json"), payload)
        return data

    def load(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise ValueError("Identificador de protocolo inválido.")
        data = json.loads((self.directory / (identifier + ".json")).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or data.get("protocol_id") != identifier or data.get("kind") not in KINDS:
            raise ValueError("Protocolo inválido ou versão desconhecida.")
        config_from_dict(data["config"])
        if not isinstance(data.get("fields"), dict) or not isinstance(data.get("options"), dict):
            raise ValueError("Campos do protocolo inválidos.")
        if not isinstance(data["fields"].get("title"),str) or not data["fields"]["title"].strip():
            raise ValueError("Nome de protocolo ausente.")
        return data

    def list_all(self):
        result = []
        self.errors = []
        for path in sorted(self.directory.glob("*.json"), reverse=True):
            try:
                result.append(self.load(path.stem))
            except (OSError, ValueError, KeyError, TypeError) as exc:
                self.errors.append(f"{path.name}: {exc}")
        return sorted(result, key=lambda item: item["created_at"], reverse=True)
