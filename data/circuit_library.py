"""Named circuit drafts with append-only revisions and atomic local persistence."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json
import os
import re
import tempfile

from core.circuit_document import CircuitDocument


@dataclass(frozen=True)
class CircuitRevision:
    identifier: str
    name: str
    description: str
    version: int
    created_at: str
    document: CircuitDocument


class CircuitLibrary:
    """A library entry is independent of executed experiment records."""

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, identifier):
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-f0-9]{32}", identifier):
            raise ValueError("Identificador de circuito inválido")
        return self.directory / (identifier + ".json")

    def _read(self, identifier):
        path = self._path(identifier)
        if path.stat().st_size > 8_000_000:
            raise ValueError("Biblioteca de circuito excede 8 MB")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("schema_version") != 1 or raw.get("id") != identifier:
            raise ValueError("Formato de biblioteca de circuito inválido")
        revisions = raw.get("revisions")
        if not isinstance(revisions, list) or not revisions or len(revisions) > 200:
            raise ValueError("Revisões de circuito inválidas")
        for version, item in enumerate(revisions, 1):
            if not isinstance(item, dict) or item.get("version") != version:
                raise ValueError("Sequência de revisões inválida")
            self._text(item.get("name"), "Nome", 120, required=True)
            self._text(item.get("description"), "Descrição", 4000)
            if not isinstance(item.get("created_at"), str):
                raise ValueError("Data de revisão inválida")
            datetime.fromisoformat(item["created_at"])
            CircuitDocument.from_dict(item.get("document"))
        return raw

    @staticmethod
    def _text(value, field, limit, required=False):
        if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
            raise ValueError(f"{field}: use {'1 a ' if required else 'até '}{limit} caracteres")
        return value.strip()

    def save(self, name, document, description="", identifier=None):
        name = self._text(name, "Nome", 120, required=True)
        description = self._text(description, "Descrição", 4000)
        document.validate()
        if identifier is None:
            identifier = uuid4().hex
            raw = {"schema_version": 1, "id": identifier, "revisions": []}
        else:
            raw = self._read(identifier)
        if len(raw["revisions"]) >= 200:
            raise ValueError("Limite de 200 revisões; duplique o circuito para continuar")
        entry = dict(version=len(raw["revisions"]) + 1, name=name, description=description,
                     created_at=datetime.now(timezone.utc).isoformat(), document=document.to_dict())
        raw["revisions"].append(entry)
        text = json.dumps(raw, ensure_ascii=False, indent=2, allow_nan=False)
        if len(text.encode("utf-8")) > 8_000_000:
            raise ValueError("Biblioteca de circuito excede 8 MB; duplique o circuito")
        descriptor, temporary = tempfile.mkstemp(prefix=".circuit-", suffix=".tmp", dir=self.directory)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(identifier))
        finally:
            Path(temporary).unlink(missing_ok=True)
        return self._revision(identifier, entry)

    @staticmethod
    def _revision(identifier, item):
        return CircuitRevision(identifier, item["name"], item["description"], item["version"],
                               item["created_at"], CircuitDocument.from_dict(item["document"]))

    def revisions(self, identifier):
        return [self._revision(identifier, item) for item in self._read(identifier)["revisions"]]

    def entries(self):
        """Return latest revisions, skipping malformed foreign files."""
        entries = []
        for path in self.directory.glob("*.json"):
            try:
                raw = self._read(path.stem)
                entries.append(self._revision(path.stem, raw["revisions"][-1]))
            except (OSError, ValueError, TypeError, KeyError):
                continue
        return sorted(entries, key=lambda item: item.created_at, reverse=True)
