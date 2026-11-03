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

    def annotate(
        self, identifier, project, notes, tags, title=None, *,
        description=None, objective=None, hypothesis=None, methodology=None,
        categories=None,
    ):
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("Identificador de execução inválido.")
        if title is not None and (not isinstance(title, str) or len(title) > 160):
            raise ValueError("O nome da execução deve ter até 160 caracteres.")
        for label, value in (("Projeto", project), ("Observações", notes)):
            if not isinstance(value, str):
                raise ValueError(f"{label} deve ser texto.")
        if not isinstance(tags, (list, tuple)) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError("Etiquetas devem ser uma lista de textos.")
        extras = dict(description=description, objective=objective, hypothesis=hypothesis, methodology=methodology)
        for key, value in extras.items():
            if value is not None and (not isinstance(value, str) or len(value) > 20_000):
                raise ValueError("Os campos científicos devem conter até 20.000 caracteres.")
        if categories is not None and (
            not isinstance(categories, (list, tuple))
            or any(not isinstance(value, str) for value in categories)
        ):
            raise ValueError("Categorias devem ser uma lista de textos.")
        raw = self.read()
        if project.strip():
            raw["projects"].setdefault(project.strip(), {"description": ""})
        annotation = dict(raw["annotations"].get(identifier, {}))
        annotation.update({
            "title": (
                title.strip() if title is not None
                else raw["annotations"].get(identifier, {}).get("title", "")
            ),
            "project": project.strip(),
            "notes": notes,
            "tags": list(dict.fromkeys(tag.strip() for tag in tags if tag.strip())),
        })
        for key, value in extras.items():
            if value is not None:
                annotation[key] = value.strip()
        if categories is not None:
            annotation["categories"] = list(dict.fromkeys(value.strip() for value in categories if value.strip()))
        raw["annotations"][identifier] = annotation
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
