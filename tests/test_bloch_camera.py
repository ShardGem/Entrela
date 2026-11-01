"""Camera bounds, native Qt input, and the layout feedback regression."""

import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from dataclasses import replace

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication
from core.examples import create_example_config
from core.simulation import run_experiment


@pytest.fixture
def scene(window, qt_app):
    experiment = run_experiment(replace(create_example_config("bell"), shots=64))
    window._current_experiment = experiment
    window._display_experiment(experiment)
    window._show_page("bloch")
    for _ in range(5):
        qt_app.processEvents()
    return window.page_bloch


def test_canvas_layout_hints_do_not_follow_last_rendered_size(scene, qt_app):
    for canvas in (scene.canvas, scene.probabilities_canvas):
        preferred = canvas.sizeHint()
        minimum = canvas.minimumSizeHint()
        canvas.resize(1150, 720)
        assert canvas.sizeHint() == preferred
        assert canvas.minimumSizeHint() == minimum
        canvas.resize(360, 280)
        assert canvas.sizeHint() == preferred


def test_zoom_slider_is_bidirectional_without_signal_feedback(scene):
    changes = []
    scene.canvas.camera_changed.connect(lambda: changes.append(scene.canvas.zoom))
    scene.zoom_slider.setValue(175)
    assert changes == [1.75]
    assert scene.canvas.zoom == 1.75
    scene.canvas.zoom_by(1.1)
    assert len(changes) == 2
    assert scene.zoom_slider.value() == 193
    assert scene.zoom_label.text() == "193%"
    for _ in range(30):
        scene._refresh_ui()
    assert len(changes) == 2


@pytest.mark.parametrize("step", [1e8, -1e8, float("nan"), float("inf")])
def test_wheel_bursts_stay_finite_and_bounded(scene, step):
    scene.canvas._on_scroll(SimpleNamespace(inaxes=scene.canvas.ax, step=step))
    assert 0.5 <= scene.canvas.zoom <= 3
    assert np.isfinite(scene.canvas.ax.get_proj()).all()
    assert scene.zoom_slider.value() == round(scene.canvas.zoom * 100)


def test_precision_touchpad_pixels_do_not_become_wheel_notches(scene):
    canvas = scene.canvas
    point = QPointF(canvas.width() / 2, canvas.height() / 2)
    event = QWheelEvent(
        point,
        QPointF(canvas.mapToGlobal(point.toPoint())),
        QPoint(0, 15),
        QPoint(0, 0),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.ScrollUpdate,
        False,
    )
    QApplication.sendEvent(canvas, event)
    assert 1 < canvas.zoom < 1.05
    scene.camera_panel.mouse_lock.setChecked(True)
    before = canvas.ax.get_proj().copy()
    event = QWheelEvent(
        point,
        QPointF(canvas.mapToGlobal(point.toPoint())),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.NoScrollPhase,
        False,
    )
    QApplication.sendEvent(canvas, event)
    np.testing.assert_array_equal(canvas.ax.get_proj(), before)


def test_camera_operations_leave_scientific_states_and_playback_unchanged(scene):
    states = [state.data.copy() for state in scene.original_svs]
    canvas = scene.canvas
    scene.zoom_slider.setValue(250)
    canvas.set_view(40, -45)
    canvas.pan(1000, dz=-1000)
    _, half = canvas._bounds()
    assert np.all(np.abs(canvas._pan) <= half * 0.6)
    before = canvas.camera_state()
    projection = canvas.ax.get_proj().copy()
    scene._toggle_play()
    for _ in range(10):
        scene._on_tick()
    assert not scene.playing
    assert canvas.camera_state() == before
    np.testing.assert_array_equal(projection, canvas.ax.get_proj())
    for original, state in zip(states, scene.original_svs):
        np.testing.assert_array_equal(original, state.data)


def test_rotation_pan_projection_and_reset_sync_panel(scene):
    canvas = scene.canvas
    canvas.set_zoom(2.0)
    canvas.set_view(35, 120)
    canvas.set_projection("ortho")
    assert scene.camera_panel.elevation.value() == 35
    assert scene.camera_panel.azimuth.value() == 120
    assert scene.camera_panel.projection.currentData() == "ortho"
    canvas._on_press(SimpleNamespace(inaxes=canvas.ax, button=1, x=200, y=200))
    canvas._on_motion(SimpleNamespace(inaxes=canvas.ax, x=250, y=240))
    assert canvas.ax.azim != 120
    canvas._end_drag()
    stopped = canvas.camera_state()
    canvas._on_motion(SimpleNamespace(inaxes=canvas.ax, x=300, y=280))
    assert canvas.camera_state() == stopped
    canvas.reset_camera()
    assert canvas.zoom == 1.0
    assert scene.zoom_slider.value() == 100
    assert scene.camera_panel.projection.currentData() == "persp"
    assert scene.camera_panel.elevation.value() == 22
    assert scene.camera_panel.azimuth.value() == -60
    np.testing.assert_array_equal(canvas._pan, [0, 0, 0])


def test_snapshot_spin_and_hide_pause_playback(scene, window, qt_app):
    scene._toggle_play()
    scene.snapshot_spin.setValue(3)
    assert scene.current_frame == scene.slider.value() == 2
    scene.slider.setValue(1)
    assert scene.snapshot_spin.value() == 2
    window._show_page("results")
    qt_app.processEvents()
    assert not scene.playing
    assert not scene.timer.isActive()


def test_invalid_persisted_camera_is_bounded(scene):
    scene.canvas.restore_camera(
        zoom=float("nan"),
        pan=[float("inf"), 0, 0],
        elev=999,
        azim=1000,
        projection="invalid",
    )
    assert scene.canvas.zoom == 1
    assert scene.camera_panel.projection.currentData() == "persp"
    assert np.isfinite(scene.canvas.ax.get_proj()).all()
    assert abs(scene.canvas.ax.elev) <= 90


def test_camera_preferences_roundtrip(scene, window, qt_app):
    from gui.main_window import MainWindow

    experiment = window._current_experiment
    window.repository.save(experiment)
    scene.focus_combo.setCurrentIndex(1)
    scene.canvas.set_zoom(1.8)
    scene.canvas.set_view(40, 100)
    scene.canvas.pan(0.2, dz=-0.1)
    scene.canvas.set_projection("ortho")
    expected = scene.canvas.camera_state()
    repo, settings = window.repository, window.settings
    window.close()
    other = MainWindow(repo, settings)
    try:
        other._open_experiment(experiment.id)
        assert other.page_bloch.canvas.camera_state() == expected
        assert not other.page_bloch._qubit_panels[0].isHidden()
        assert other.page_bloch._qubit_panels[1].isHidden()
        assert other.page_bloch.zoom_slider.value() == 180
        assert other.page_bloch.camera_panel.projection.currentData() == "ortho"
    finally:
        other.close()


@pytest.mark.parametrize("scale", ["1", "1.25", "1.5", "2"])
def test_bloch_layout_and_camera_in_separate_process(scale):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-X", "faulthandler", str(root / "scripts/bloch_smoke.py")],
        cwd=root,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "QT_SCALE_FACTOR": scale},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    assert '"status": "PASS"' in result.stdout


def test_focus_isolates_qubit_and_axes_option_does_not_hide_state(scene):
    scene.focus_combo.setCurrentIndex(scene.focus_combo.findData(1))
    assert not any(artist.get_visible() for artist in scene.canvas._qubit_artists[0])
    assert scene.canvas._line_handles[1].get_visible()
    scene.axes_check.setChecked(False)
    assert not any(artist.get_visible() for artist in scene.canvas._axis_artists)
    assert scene.canvas._line_handles[1].get_visible()
    scene.focus_combo.setCurrentIndex(0)
    assert all(line.get_visible() for line in scene.canvas._line_handles)


def test_orientation_panel_expands_without_changing_camera(scene, qt_app):
    before = scene.canvas.camera_state()
    scene.camera_panel.orientation_toggle.click()
    qt_app.processEvents()
    assert scene.camera_panel.elevation.isVisible()
    assert scene.canvas.camera_state() == before
    scene.camera_panel.orientation_toggle.click()
    qt_app.processEvents()
    assert not scene.camera_panel.elevation.isVisible()
    assert scene.canvas.camera_state() == before


@pytest.mark.parametrize("width,height", [(1200, 400), (400, 800)])
def test_rectangular_viewport_uses_full_canvas_without_stretching_sphere(
    qt_app, width, height
):
    from gui.widgets.bloch_canvas import BlochCanvas
    from mpl_toolkits.mplot3d import proj3d

    canvas = BlochCanvas()
    canvas.setup(1)
    canvas.resize(width, height)
    canvas.set_projection("ortho")
    canvas.set_view(0, -90)
    canvas.draw()
    np.testing.assert_allclose(canvas.ax.bbox.bounds, canvas.fig.bbox.bounds, atol=1e-8)
    points = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    x, y, _ = proj3d.proj_transform(*points.T, canvas.ax.get_proj())
    screen = canvas.ax.transData.transform(np.column_stack((x, y)))
    assert np.linalg.norm(screen[1] - screen[0]) == pytest.approx(
        np.linalg.norm(screen[2] - screen[0]), rel=1e-10
    )
    canvas.close()


@pytest.mark.parametrize("num_qubits", [1, 2, 6])
@pytest.mark.parametrize("projection", ["persp", "ortho"])
def test_fit_scene_contains_visible_geometry_after_large_zoom(
    qt_app, num_qubits, projection
):
    from gui.widgets.bloch_canvas import BlochCanvas
    from mpl_toolkits.mplot3d import proj3d

    canvas = BlochCanvas()
    canvas.setup(num_qubits)
    canvas.resize(1000, 420)
    canvas.set_projection(projection)
    canvas.set_view(35, 75)
    canvas.set_zoom(3)
    canvas.pan(0.5, dz=0.5)
    canvas.draw()
    canvas.fit_scene()
    canvas.draw()
    points = canvas.scene_corners()
    x, y, _ = proj3d.proj_transform(*points.T, canvas.ax.get_proj())
    screen = canvas.ax.transData.transform(np.column_stack((x, y)))
    bbox = canvas.ax.bbox
    assert np.all(screen[:, 0] > bbox.x0 + 5)
    assert np.all(screen[:, 0] < bbox.x1 - 5)
    assert np.all(screen[:, 1] > bbox.y0 + 5)
    assert np.all(screen[:, 1] < bbox.y1 - 5)
    assert canvas.projection == projection
    assert canvas.ax.elev == 35 and canvas.ax.azim == 75
    canvas.close()


def test_zoom_draws_beyond_old_square_clip_in_wide_canvas(qt_app):
    from gui.widgets.bloch_canvas import BlochCanvas
    from matplotlib.colors import to_rgba
    from gui.theme import PALETTE

    canvas = BlochCanvas()
    canvas.setup(1)
    canvas.resize(1200, 400)
    canvas.set_projection("ortho")
    canvas.set_view(0, -90)
    canvas.set_zoom(3)
    canvas.draw()
    pixels = np.asarray(canvas.buffer_rgba())
    # Exclude legend/top edge. A centered 400px square would clip this region.
    region = pixels[100:300, 260:380, :3]
    bg = np.array(to_rgba(PALETTE.bg)[:3]) * 255
    assert np.any(np.linalg.norm(region.astype(float) - bg, axis=2) > 15)
    canvas.close()
