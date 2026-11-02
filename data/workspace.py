"""Named personal templates and project annotations, separate from scientific records."""

from pathlib import Path
import json, os, tempfile
from dataclasses import asdict
from core.types import config_from_dict


class WorkspaceLibrary:
    def __init__(self, directory):
        self.path = Path(directory) / "workspace.json"

    def read(self):
        if not self.path.exists():
            return {"version": 1, "templates": {}, "projects": {}, "annotations": {}}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if (
            not isinstance(raw, dict)
            or raw.get("version") != 1
            or any(
                not isinstance(raw.get(k), dict)
                for k in ("templates", "projects", "annotations")
            )
        ):
            raise ValueError("Biblioteca pessoal inválida; arquivo preservado.")
        return raw

    def _write(self, raw):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as f:
                temporary = Path(f.name)
                json.dump(raw, f, ensure_ascii=False, indent=2, allow_nan=False)
                f.flush()
                os.fsync(f.fileno())
            temporary.replace(self.path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def save_template(self, name, config):
        if not name.strip():
            raise ValueError("Informe um nome para o modelo.")
        config.validate()
        raw = self.read()
        raw["templates"][name.strip()] = asdict(config)
        self._write(raw)

    def template(self, name):
        return config_from_dict(self.read()["templates"][name])

    def annotate(self, identifier, project, notes, tags, title=None):
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Identificador de execução inválido.")
        if title is not None and (not isinstance(title, str) or len(title) > 160):
            raise ValueError("O nome da execução deve ter até 160 caracteres.")
        raw = self.read()
        if project.strip():
            raw["projects"].setdefault(project.strip(), {"description": ""})
        raw["annotations"][identifier] = {
            "title": (
                title.strip() if title is not None
                else raw["annotations"].get(identifier, {}).get("title", "")
            ),
            "project": project.strip(),
            "notes": notes,
            "tags": list(tags),
        }
        self._write(raw)

    def delete_template(self, name):
        raw = self.read()
        raw["templates"].pop(name, None)
        self._write(raw)


def experiment_title(experiment, annotations=None):
    """Presentation name; the immutable technical ID remains the lookup key."""
    annotation = (annotations or {}).get(experiment.id, {})
    title = annotation.get("title", "").strip()
    if title:
        return title
    from core.types import system_label

    return f"{system_label(experiment.config)} · {experiment.created_at.astimezone():%d/%m %H:%M}"
