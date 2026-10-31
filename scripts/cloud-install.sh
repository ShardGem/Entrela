#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"'
python3 -m venv /workspace/.venvs/entrela
export PIP_CACHE_DIR=/workspace/.cache/entrela/pip
/workspace/.venvs/entrela/bin/python -m pip install --disable-pip-version-check --progress-bar off -r requirements.txt
/workspace/.venvs/entrela/bin/python -m pip install --disable-pip-version-check --no-deps -e .
/workspace/.venvs/entrela/bin/python -m pip check
