"""Publica somente arquivos verificados e permite retomar um release em rascunho."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def validated_assets(directory: Path, tag: str) -> list[Path]:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Use uma tag de versão no formato v0.27.0.")
    version = tag[1:]
    binaries = [f"Entrela-{version}-windows-x64-setup.exe",
                f"Entrela-{version}-windows-x64-portatil.zip"]
    receipts = ["verificacao-portatil.json", "verificacao-instalado.json"]
    names = binaries + ["SHA256SUMS.txt", "dependencias-build.txt"] + receipts
    files = [directory / name for name in names]
    for path in files:
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise ValueError(f"Arquivo obrigatório ausente ou vazio: {path.name}")
    checksums = {}
    for line in (directory / "SHA256SUMS.txt").read_text(encoding="utf-8-sig").splitlines():
        digest, name = line.split(maxsplit=1)
        if name in checksums or not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
            raise ValueError("A lista de hashes contém uma entrada inválida.")
        checksums[name] = digest.lower()
    if set(checksums) != set(binaries):
        raise ValueError("Os hashes precisam identificar exatamente o instalador e o portátil.")
    for name in binaries:
        with (directory / name).open("rb") as source:
            digest = hashlib.file_digest(source, "sha256").hexdigest()
        if digest != checksums[name]:
            raise ValueError(f"O hash não corresponde ao arquivo {name}.")
    for name in receipts:
        receipt = json.loads((directory / name).read_text(encoding="utf-8-sig"))
        if not (receipt.get("success") is True and receipt.get("frozen") is True
                and receipt.get("version") == version and receipt.get("qt_platform") == "windows"
                and len(receipt.get("checks", [])) >= 7):
            raise ValueError(f"A verificação nativa está incompleta: {name}")
    return files


def publish(directory: Path, tag: str, repository: str, notes: Path) -> None:
    files = validated_assets(directory, tag)
    view = subprocess.run(["gh", "release", "view", tag, "--repo", repository,
                           "--json", "isDraft,tagName"], text=True, capture_output=True)
    if view.returncode == 0:
        release = json.loads(view.stdout)
        if release["tagName"] != tag:
            raise ValueError("O release consultado não corresponde à tag solicitada.")
        if not release["isDraft"]:
            print(f"O release {tag} já está publicado; os arquivos foram preservados.")
            return
    elif "release not found" in view.stderr.lower() or "404" in view.stderr:
        subprocess.run(["gh", "release", "create", tag, "--repo", repository, "--draft",
                        "--verify-tag", "--title", f"Entrela {tag} · Windows x64",
                        "--notes-file", str(notes)], check=True)
    else:
        raise RuntimeError(f"Não foi possível consultar o release: {view.stderr.strip()}")
    # Logs vazios são diagnósticos locais, não anexos do release. O GitHub
    # rejeita uploads com Content-Length zero. A lista explícita evita isso.
    subprocess.run(["gh", "release", "upload", tag, "--repo", repository, "--clobber",
                    *(str(path) for path in files)], check=True)
    subprocess.run(["gh", "release", "edit", tag, "--repo", repository,
                    "--draft=false", "--latest"], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    options = parser.parse_args()
    publish(options.assets, options.tag, options.repository,
            Path("docs/releases") / f"{options.tag}.md")
