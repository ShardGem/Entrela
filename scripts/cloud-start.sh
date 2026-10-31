#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR=/workspace/.cache/entrela/matplotlib
export XDG_CACHE_HOME=/workspace/.cache/entrela
export XDG_CONFIG_HOME=/workspace/.config/entrela
export ENTRELA_DATA_DIR="${ENTRELA_DATA_DIR:-/workspace/.local/share/entrela/experiments}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-2}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-2}"
mkdir -p "$MPLCONFIGDIR" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME"
if [[ -z "${DISPLAY:-}" && -z "${WAYLAND_DISPLAY:-}" ]]; then
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
fi
exec /workspace/.venvs/entrela/bin/python app.py
