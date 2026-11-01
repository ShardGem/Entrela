r"""Exercise real Qt layouts and Bloch navigation; run in a separate process.

Example on Windows: .venv\Scripts\python.exe scripts/bloch_smoke.py
QT_SCALE_FACTOR may be set before launch to exercise display scaling.
"""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from core.examples import create_example_config
from core.simulation import run_experiment
from data.repository import ExperimentRepository
from gui.main_window import MainWindow
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    app = QApplication([])
    with TemporaryDirectory(prefix="entrela-bloch-") as directory:
        window = MainWindow(
            ExperimentRepository(Path(directory) / "runs"),
            QSettings(str(Path(directory) / "prefs.ini"), QSettings.IniFormat),
        )
        window.resize(1024, 768)
        window.show()
        try:
            for n in (1, 2, 6):
                base = create_example_config("bell")
                config = replace(
                    base,
                    shots=64,
                    system=replace(
                        base.system, num_qubits=n, initial_state="plus", J=1.0, h=0.5
                    ),
                    noise=replace(base.noise, enabled=True),
                    protocol=replace(base.protocol, trotter_steps=4),
                )
                experiment = run_experiment(config)
                window._current_experiment = experiment
                window._display_experiment(experiment)
                window._show_page("bloch")
                page = window.page_bloch
                canvas = page.canvas
                for width, height in (
                    (1024, 768),
                    (1440, 900),
                    (1100, 780),
                    (1024, 768),
                ):
                    window.resize(width, height)
                    # Let initial polish/layout/paint requests settle.
                    for _ in range(12):
                        app.processEvents()
                    size = (canvas.width(), canvas.height())
                    projection = canvas.ax.get_proj().copy()
                    limits = np.array(
                        [
                            canvas.ax.get_xlim(),
                            canvas.ax.get_ylim(),
                            canvas.ax.get_zlim(),
                        ]
                    )
                    for _ in range(30):
                        app.processEvents()
                    assert size == (canvas.width(), canvas.height()), (
                        "Canvas grew while idle"
                    )
                    np.testing.assert_array_equal(canvas.ax.get_proj(), projection)
                    np.testing.assert_array_equal(
                        [
                            canvas.ax.get_xlim(),
                            canvas.ax.get_ylim(),
                            canvas.ax.get_zlim(),
                        ],
                        limits,
                    )
                for percent in (50, 100, 175, 300, 100):
                    page.zoom_slider.setValue(percent)
                    app.processEvents()
                    assert canvas.zoom == percent / 100
                    assert page.zoom_label.text() == f"{percent}%"
                page.focus_combo.setCurrentIndex(page.focus_combo.findData(n - 1))
                canvas.set_view(35, -45)
                canvas.set_zoom(1.5)
                canvas.pan(0.1, dz=0.1)
                before = canvas.ax.get_proj().copy()
                page._toggle_play()
                for _ in range(len(experiment.result.states) + 1):
                    page._on_tick()
                    app.processEvents()
                assert not page.playing
                np.testing.assert_array_equal(before, canvas.ax.get_proj())
                page.visual_tabs.setCurrentIndex(1)
                app.processEvents()
                page.visual_tabs.setCurrentIndex(0)
                app.processEvents()
                canvas.reset_camera()
                page.focus_combo.setCurrentIndex(0)
                if args.screenshots:
                    args.screenshots.mkdir(parents=True, exist_ok=True)
                    window.resize(1440, 1000)
                    for _ in range(12):
                        app.processEvents()
                    window.grab().save(str(args.screenshots / f"bloch-{n}q.png"))
                window._show_page("results")
                app.processEvents()
                window._show_page("bloch")
                app.processEvents()
            print(
                json.dumps(
                    {
                        "status": "PASS",
                        "scale": os.environ.get("QT_SCALE_FACTOR", "1"),
                        "qubits": [1, 2, 6],
                        "checks": [
                            "stable layout",
                            "idle camera",
                            "vertical zoom",
                            "focus",
                            "playback",
                            "tabs",
                            "navigation",
                        ],
                    }
                )
            )
        finally:
            window._unsaved_result = False
            window.close()
            app.processEvents()


if __name__ == "__main__":
    main()
