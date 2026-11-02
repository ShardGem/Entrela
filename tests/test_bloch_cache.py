"""Derived cache preserves state and invalidates on content or display changes."""

import numpy as np
from qiskit.quantum_info import Statevector
from gui.pages.bloch import BlochPage


def test_reopened_states_reuse_derivatives_and_mutation_invalidates(qt_app, monkeypatch):
    import gui.pages.bloch as bloch

    original = bloch.get_bloch_vector
    calls = []

    def traced(*args):
        calls.append(True)
        return original(*args)

    monkeypatch.setattr(bloch, "get_bloch_vector", traced)
    page = BlochPage()
    state = Statevector.from_label("0")
    before = state.data.copy()
    page.load_statevectors([state], [0], [state])
    assert len(calls) == 1  # Ideal and simulated use the same scientific state.
    np.testing.assert_array_equal(state.data, before)
    page.load_statevectors([Statevector(before.copy())], [0])
    assert len(calls) == 1
    state.data[:] = [0, 1]
    page.load_statevectors([state], [0])
    assert len(calls) == 2
    np.testing.assert_allclose(page.precomputed_bloch[0][0], [0, 0, -1])
    np.testing.assert_array_equal(state.data, [0, 1])
    assert not page.precomputed_bloch[0].flags.writeable
    page.close()


def test_derived_cache_evicts_old_snapshots(qt_app):
    page = BlochPage()
    page._derived_cache_limit = 2
    for theta in (0.1, 0.2, 0.3, 0.4):
        page._derived_snapshot(Statevector([np.cos(theta), np.sin(theta)]))
    assert len(page._derived_cache) == 2
    page.close()


def test_same_probability_view_does_not_rebuild_plot(qt_app, monkeypatch):
    page = BlochPage()
    page.load_statevectors([Statevector.from_label("0")], [0])
    calls = []
    original = page.probabilities_canvas.reset_axes

    def counted(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(page.probabilities_canvas, "reset_axes", counted)
    page.visual_tabs.setCurrentIndex(1)
    assert len(calls) == 1
    page._refresh_ui()
    page._refresh_ui()
    assert len(calls) == 1
    page.overlay.setChecked(False)
    assert len(calls) == 2
    page.load_statevectors([Statevector.from_label("1")], [0])
    assert len(calls) == 3
    np.testing.assert_allclose(
        [bar.get_height() for bar in page.probabilities_canvas.fig.axes[0].patches],
        [0, 1],
    )
    page.close()
