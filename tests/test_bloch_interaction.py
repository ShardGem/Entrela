"""Click/Shift gestures, expanded viewport and synchronized metrics."""

from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest
from mpl_toolkits.mplot3d import proj3d
from core.examples import create_example_config
from core.simulation import run_experiment
from core.analysis import temporal_analysis


@pytest.fixture
def populated(window, qt_app):
    record = run_experiment(
        replace(create_example_config("depolarizing-bell"), shots=64)
    )
    window._current_experiment = record
    window._display_experiment(record)
    window._show_page("bloch")
    for _ in range(5):
        qt_app.processEvents()
    window.page_bloch.canvas.draw()
    return window.page_bloch


def test_click_selects_qubit_without_moving_camera(populated):
    page = populated
    canvas = page.canvas
    before = canvas.camera_state()
    x, y, _ = proj3d.proj_transform(*canvas._sphere_centers[1], canvas.ax.get_proj())
    px, py = canvas.ax.transData.transform((x, y))
    event = SimpleNamespace(
        inaxes=canvas.ax, x=px, y=py, button=1, modifiers=frozenset(), key=None
    )
    canvas._on_press(event)
    canvas._end_drag(event)
    assert canvas.selected_qubit == 1
    assert "q1" in page.selection_label.text()
    assert canvas.camera_state() == before
    assert canvas.focus == -1
    page.focus_selected.click()
    assert canvas.focus == 1


def test_background_click_preserves_selection(populated):
    canvas = populated.canvas
    canvas.select_qubit(0)
    # Outside both projected spheres, but inside the axes viewport.
    event = SimpleNamespace(
        inaxes=canvas.ax,
        x=canvas.ax.bbox.x0 + 2,
        y=canvas.ax.bbox.y0 + 2,
        button=1,
        modifiers=frozenset(),
        key=None,
    )
    canvas._on_press(event)
    canvas._end_drag(event)
    assert canvas.selected_qubit == 0


def test_shift_drag_pans_without_rotation_or_accidental_selection(populated):
    canvas = populated.canvas
    before = (canvas.ax.elev, canvas.ax.azim)
    canvas._on_press(
        SimpleNamespace(
            inaxes=canvas.ax,
            x=250,
            y=200,
            button=1,
            modifiers=frozenset({"shift"}),
            key="shift",
        )
    )
    canvas._on_motion(SimpleNamespace(inaxes=canvas.ax, x=280, y=230))
    canvas._end_drag(SimpleNamespace(inaxes=canvas.ax, x=280, y=230, button=1))
    assert (canvas.ax.elev, canvas.ax.azim) == before
    assert np.linalg.norm(canvas._pan) > 0
    assert canvas.selected_qubit == -1


def test_expanded_scene_restores_panels_camera_and_snapshot(populated, qt_app):
    page = populated
    page.slider.setValue(2)
    page.canvas.set_zoom(1.8)
    page.canvas.set_view(30, 40)
    before = page.canvas.camera_state()
    page.set_maximized(True)
    qt_app.processEvents()
    assert (
        not page.camera_scroll.isVisible()
        and not page.info_scroll.isVisible()
        and not page.metrics.isVisible()
    )
    assert page.current_frame == 2 and page.canvas.camera_state() == before
    page.set_maximized(False)
    qt_app.processEvents()
    assert page.inspector.isVisible() and page.camera_scroll.isVisible()
    page.inspector_selector.setCurrentIndex(2)
    assert page.info_scroll.isVisible()
    assert page.current_frame == 2 and page.canvas.camera_state() == before


def test_embedded_metrics_cursor_and_timeline_are_bidirectional(
    populated, window, qt_app
):
    page = populated
    data = temporal_analysis(window._current_experiment)
    page.metrics.set_rows(data["rows"])
    page.slider.setValue(3)
    assert page.metrics.index == 3
    assert page.metrics._marker.get_xdata() == [data["rows"][3]["time"]] * 2
    assert "Snapshot 4" in page.metrics.summary.text()
    page.metrics._clicked(
        SimpleNamespace(
            inaxes=page.metrics.canvas.fig.axes[0], xdata=data["rows"][1]["time"]
        )
    )
    assert page.current_frame == 1 and page.snapshot_spin.value() == 2
