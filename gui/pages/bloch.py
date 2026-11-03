"""Snapshot viewer: the camera never changes scientific state."""

from __future__ import annotations
from collections import OrderedDict
from hashlib import blake2b
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QSignalBlocker
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QGridLayout,
    QTabWidget,
    QSpinBox,
)
from qiskit.quantum_info import DensityMatrix, partial_trace
from gui.pages.base import PageBase
from gui.widgets.card import EmptyState
from gui.widgets.button import PrimaryButton, GhostButton
from gui.theme import PALETTE
from gui.widgets.plot_canvas import MplCanvas
from gui.widgets.bloch_canvas import BlochCanvas
from gui.widgets.bloch_controls import BlochCameraPanel
from gui.widgets.snapshot_metrics import SnapshotMetrics
from PySide6.QtGui import QShortcut, QKeySequence


def interpolate_statevectors(svs, steps_per_pair=20):
    return list(svs)


def get_bloch_vector(state, qubit_index, num_qubits):
    from core.metrics import bloch_vector
    return bloch_vector(state, qubit_index)


def purity_from_bloch(bvec):
    return (1 + float(np.dot(bvec, bvec))) / 2


class QubitInfoPanel(QLabel):
    def __init__(self, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.setObjectName("Card")
        self.setMargin(10)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setMinimumWidth(150)

    def update_values(self, bvec):
        x, y, z = bvec
        self.setText(
            f"Qubit {self.index}\nPureza local {purity_from_bloch(bvec):.5f}\n"
            f"r = ({x:+.4f}, {y:+.4f}, {z:+.4f})\n"
            f"ρ = [ {(1 + z) / 2:.4f}, {x / 2:+.4f}{-y / 2:+.4f}i ;\n"
            f"       {x / 2:+.4f}{y / 2:+.4f}i, {(1 - z) / 2:.4f} ]"
        )


class BlochPage(PageBase):
    frame_changed = Signal(int)
    preferences_changed = Signal()
    temporal_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(
            "Evolução 3D",
            "Snapshots reais · câmera independente · q0 à direita no histograma.",
            parent,
        )
        self.original_svs = []
        self.interpolated_svs = []
        self.precomputed_bloch = []
        self.ideal_bloch = []
        # Cache only small derived arrays, never copies of the scientific states.
        # Content keys also make a deliberately modified state invalidate safely.
        self._derived_cache = OrderedDict()
        self._derived_cache_limit = 512
        self.snapshot_probabilities = []
        self.ideal_probabilities = []
        self._probability_plot_key = None
        self.current_frame = 0
        self.num_qubits = 2
        self.playing = False
        self.speed_factor = 1.0
        self.times = None
        self._refreshing = False
        self._maximized = False
        self.time_unit = "adimensional (ℏ=1)"
        self.timer = QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self._on_tick)
        self._empty = EmptyState(
            "bloch",
            "Nenhuma evolução disponível",
            "Ative os snapshots e execute uma simulação.",
        )
        self.body().addWidget(self._empty)
        self._content = QWidget()
        layout = QVBoxLayout(self._content)
        controls = QHBoxLayout()
        self.btn_play = PrimaryButton("Iniciar")
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_stop = GhostButton("Parar")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_prev = GhostButton("‹")
        self.btn_prev.setToolTip("Snapshot anterior")
        self.btn_prev.clicked.connect(self._prev)
        self.btn_next = GhostButton("›")
        self.btn_next.setToolTip("Próximo snapshot")
        self.btn_next.clicked.connect(self._next)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1x", "2x", "4x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._update_speed)
        self.loop = QCheckBox("Repetir")
        self.loop.toggled.connect(lambda *_: self.preferences_changed.emit())
        self.trails = QCheckBox("Rastros")
        self.trails.setChecked(True)
        self.trails.toggled.connect(self._refresh_ui)
        self.trails.toggled.connect(lambda *_: self.preferences_changed.emit())
        self.overlay = QCheckBox("Ideal")
        self.overlay.setChecked(True)
        self.overlay.toggled.connect(self._refresh_ui)
        for w in (self.btn_play, self.btn_stop, self.btn_prev, self.btn_next):
            controls.addWidget(w)
        self.selection_label = QLabel("Clique numa esfera para selecionar")
        self.selection_label.setWordWrap(True)
        controls.addWidget(self.selection_label, 1)
        self.maximize_button = GhostButton("Ampliar área 3D")
        self.maximize_button.setCheckable(True)
        self.maximize_button.toggled.connect(self.set_maximized)
        controls.addWidget(self.maximize_button)
        controls.addWidget(QLabel("Velocidade"))
        controls.addWidget(self.speed_combo)
        controls.addWidget(self.loop)
        layout.addLayout(controls)
        self.canvas = BlochCanvas()
        self.canvas.qubit_selected.connect(self._select_qubit)
        self.camera_panel = BlochCameraPanel(self.canvas)
        self.focus_combo = self.camera_panel.focus_combo
        self.focus_combo.currentIndexChanged.connect(self._focus)
        self.focus_selected = GhostButton("Focar selecionado")
        self.focus_selected.setEnabled(False)
        self.focus_selected.clicked.connect(
            lambda: self.focus_combo.setCurrentIndex(
                self.focus_combo.findData(self.canvas.selected_qubit)
            )
        )
        self.camera_panel.options_layout.addWidget(self.focus_selected)
        self.zoom_slider = self.camera_panel.zoom_slider
        self.zoom_label = self.camera_panel.zoom_label
        self.axes_check = QCheckBox("Eixos X, Y, Z")
        self.axes_check.setChecked(True)
        self.axes_check.toggled.connect(self.canvas.set_axes_visible)
        for w in (self.overlay, self.trails, self.axes_check):
            self.camera_panel.options_layout.addWidget(w)
        self.probabilities_canvas = MplCanvas(height=4)
        self.visual_tabs = QTabWidget()
        self.visual_tabs.addTab(self.canvas, "Esferas de Bloch")
        self.visual_tabs.addTab(self.probabilities_canvas, "Probabilidades no instante")
        self.visual_tabs.currentChanged.connect(self._refresh_ui)
        stage = QHBoxLayout()
        stage.addWidget(self.visual_tabs, 1)
        self.camera_scroll = QScrollArea()
        self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setMinimumWidth(235)
        self.camera_scroll.setMaximumWidth(260)
        self.camera_scroll.setWidget(self.camera_panel)
        stage.addWidget(self.camera_scroll)
        layout.addLayout(stage, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider)
        self.frame_label = QLabel()
        frame_row = QHBoxLayout()
        frame_row.addWidget(self.frame_label, 1)
        frame_row.addWidget(QLabel("Ir ao snapshot"))
        self.snapshot_spin = QSpinBox()
        self.snapshot_spin.setRange(1, 1)
        self.snapshot_spin.setKeyboardTracking(False)
        self.snapshot_spin.setAccessibleName("Snapshot selecionado")
        self.snapshot_spin.valueChanged.connect(
            lambda value: self.slider.setValue(value - 1)
        )
        frame_row.addWidget(self.snapshot_spin)
        layout.addLayout(frame_row)
        self._info_container = QWidget()
        QGridLayout(self._info_container)
        self._qubit_panels = []
        info_scroll = QScrollArea()
        self.info_scroll = info_scroll
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(self._info_container)
        info_scroll.setFixedHeight(145)
        layout.addWidget(info_scroll)
        note = QLabel(
            "Pureza local baixa pode indicar correlações/emaranhamento: em Bell ideal, cada qubit tem pureza ½. A linha tracejada representa o mesmo circuito sem ruído."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.scene_note = note
        self.metrics = SnapshotMetrics()
        self.metrics.analyze_requested.connect(self.temporal_requested.emit)
        self.metrics.snapshot_selected.connect(self.slider.setValue)
        layout.addWidget(self.metrics)
        escape = QShortcut(QKeySequence("Esc"), self)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(lambda: self.set_maximized(False))
        self._escape = escape
        self.body().addWidget(self._content, 1)
        self._content.hide()

    def load_statevectors(
        self,
        statevectors,
        times=None,
        ideal_statevectors=None,
        time_unit="adimensional (ℏ=1)",
    ):
        self._pause()
        self.time_unit = time_unit
        self.metrics.clear("Índice da porta" if "porta" in time_unit else "Tempo (ℏ=1)")
        self.selection_label.setText("Clique numa esfera para selecionar")
        self.focus_selected.setEnabled(False)
        self.original_svs = list(statevectors or [])
        self.interpolated_svs = list(self.original_svs)
        self.precomputed_bloch = []
        self.ideal_bloch = []
        self.snapshot_probabilities = []
        self.ideal_probabilities = []
        self._probability_plot_key = None
        self.ideal_states = list(ideal_statevectors or [])
        if len(self.ideal_states) != len(self.original_svs):
            self.ideal_states = []
        self.times = (
            times
            if times is not None and len(times) == len(self.original_svs)
            else None
        )
        self._empty.setVisible(not bool(self.original_svs))
        self._content.setVisible(bool(self.original_svs))
        if not self.original_svs:
            return
        self.num_qubits = self.original_svs[0].num_qubits
        for state in self.original_svs:
            vectors, probabilities = self._derived_snapshot(state)
            self.precomputed_bloch.append(vectors)
            self.snapshot_probabilities.append(probabilities)
        for state in self.ideal_states:
            vectors, probabilities = self._derived_snapshot(state)
            self.ideal_bloch.append(vectors)
            self.ideal_probabilities.append(probabilities)
        old_focus = self.focus_combo.currentData()
        self.canvas.setup(self.num_qubits)
        self.focus_combo.blockSignals(True)
        self.focus_combo.clear()
        self.focus_combo.addItem("Todos os qubits", -1)
        for q in range(self.num_qubits):
            self.focus_combo.addItem(f"Focar qubit {q}", q)
        self.focus_combo.setCurrentIndex(max(0, self.focus_combo.findData(old_focus)))
        self.focus_combo.blockSignals(False)
        self.canvas.set_focus(self.focus_combo.currentData())
        layout = self._info_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._qubit_panels = []
        for q in range(self.num_qubits):
            panel = QubitInfoPanel(q)
            layout.addWidget(panel, q // 3, q % 3)
            self._qubit_panels.append(panel)
        self.slider.blockSignals(True)
        self.slider.setMaximum(len(self.precomputed_bloch) - 1)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.snapshot_spin.setRange(1, len(self.precomputed_bloch))
        self.current_frame = 0
        self._refresh_ui()

    def _derived_snapshot(self, state):
        data = np.asarray(state.data)
        key = (
            data.shape,
            data.dtype.str,
            blake2b(data.tobytes(), digest_size=20).digest(),
        )
        cached = self._derived_cache.get(key)
        if cached is None:
            vectors = np.asarray([
                get_bloch_vector(state, q, state.num_qubits)
                for q in range(state.num_qubits)
            ])
            probabilities = np.asarray(state.probabilities()).copy()
            vectors.setflags(write=False)
            probabilities.setflags(write=False)
            cached = (vectors, probabilities)
            self._derived_cache[key] = cached
            while len(self._derived_cache) > self._derived_cache_limit:
                self._derived_cache.popitem(last=False)
        self._derived_cache.move_to_end(key)
        return cached

    def _focus(self, *_):
        self.canvas.set_focus(
            self.focus_combo.currentData()
            if self.focus_combo.currentData() is not None
            else -1
        )
        self._refresh_ui()
        self.preferences_changed.emit()

    def _refresh_ui(self, *_):
        if not self.precomputed_bloch or self._refreshing:
            return
        self._refreshing = True
        try:
            self._render_snapshot()
        finally:
            self._refreshing = False

    def _render_snapshot(self):
        idx = self.current_frame
        blocker = QSignalBlocker(self.snapshot_spin)
        self.snapshot_spin.setValue(idx + 1)
        del blocker
        self.frame_label.setText(
            f"Snapshot {idx + 1} / {len(self.precomputed_bloch)}"
            + (
                f" · {'porta' if 'porta' in self.time_unit else 't'}={self.times[idx]:.6g} ({self.time_unit})"
                if self.times is not None
                else ""
            )
            + " · reprodução didática"
        )
        self.slider.blockSignals(True)
        self.slider.setValue(idx)
        self.slider.blockSignals(False)
        self.canvas.update_frame(
            self.precomputed_bloch[idx],
            False,
            self.ideal_bloch[idx]
            if self.overlay.isChecked() and self.ideal_bloch
            else None,
            self.precomputed_bloch[max(0, idx - 79) : idx + 1]
            if self.trails.isChecked()
            else [],
        )
        for q, panel in enumerate(self._qubit_panels):
            panel.update_values(self.precomputed_bloch[idx][q])
            panel.setVisible(self.canvas.focus in (-1, q))
        plot_key = (idx, self.overlay.isChecked(), PALETTE.primary, PALETTE.q2, PALETTE.surface, PALETTE.text)
        if self.visual_tabs.currentIndex() == 1 and plot_key != self._probability_plot_key:
            ax = self.probabilities_canvas.reset_axes()
            probabilities = self.snapshot_probabilities[idx]
            positions = np.arange(len(probabilities))
            ax.bar(
                positions - 0.18,
                probabilities,
                width=0.36,
                color=PALETTE.primary,
                label="Simulado",
            )
            if self.overlay.isChecked() and self.ideal_probabilities:
                ax.bar(
                    positions + 0.18,
                    self.ideal_probabilities[idx],
                    width=0.36,
                    color=PALETTE.q2,
                    label="Circuito ideal",
                )
            ax.set_xticks(
                positions,
                [format(i, f"0{self.num_qubits}b") for i in positions],
                rotation=90 if len(positions) > 8 else 0,
            )
            ax.set_ylim(0, 1.05)
            ax.set_ylabel("Probabilidade")
            ax.set_xlabel("Bitstring (q0 à direita)")
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
            self.probabilities_canvas.draw_idle()
            self._probability_plot_key = plot_key
        self.metrics.select_snapshot(idx)
        self.frame_changed.emit(idx)

    def _on_tick(self):
        if not self.precomputed_bloch:
            return
        if self.current_frame >= len(self.precomputed_bloch) - 1:
            if self.loop.isChecked():
                self.current_frame = 0
            else:
                self._pause()
                return
        else:
            self.current_frame += 1
        self._refresh_ui()
        if (
            self.current_frame == len(self.precomputed_bloch) - 1
            and not self.loop.isChecked()
        ):
            self._pause()

    def _pause(self):
        self.timer.stop()
        self.playing = False
        self.btn_play.setText("Iniciar")

    def _toggle_play(self):
        if self.playing:
            self._pause()
        elif self.precomputed_bloch:
            if self.current_frame == len(self.precomputed_bloch) - 1:
                self.current_frame = 0
                self._refresh_ui()
            self.playing = True
            self.timer.start()
            self.btn_play.setText("Pausar")

    def _stop(self):
        self._pause()
        self.current_frame = 0
        self._refresh_ui()

    def _prev(self):
        self._pause()
        self.current_frame = max(0, self.current_frame - 1)
        self._refresh_ui()

    def _next(self):
        self._pause()
        self.current_frame = min(
            max(0, len(self.precomputed_bloch) - 1), self.current_frame + 1
        )
        self._refresh_ui()

    def _on_slider(self, value):
        self.current_frame = value
        self._refresh_ui()

    def _update_speed(self, text):
        self.speed_factor = float(text.replace("x", ""))
        self.timer.setInterval(round(350 / self.speed_factor))
        self.preferences_changed.emit()

    def hideEvent(self, event):
        self._pause()
        self.canvas._end_drag()
        if self._maximized:
            self.set_maximized(False)
        super().hideEvent(event)

    def set_maximized(self, enabled):
        enabled = bool(enabled)
        if self._maximized == enabled:
            return
        self._maximized = enabled
        blocker = QSignalBlocker(self.maximize_button)
        self.maximize_button.setChecked(enabled)
        del blocker
        self.maximize_button.setText(
            "Restaurar painéis" if enabled else "Ampliar área 3D"
        )
        for widget in (
            self._header,
            self.camera_scroll,
            self.info_scroll,
            self.scene_note,
            self.metrics,
        ):
            widget.setVisible(not enabled)

    def _select_qubit(self, index):
        self.selection_label.setText(f"Qubit q{index} selecionado")
        self.focus_selected.setEnabled(True)
        self.canvas.select_qubit(index)
        for q, panel in enumerate(self._qubit_panels):
            panel.setStyleSheet(
                "border: 2px solid " + getattr(PALETTE, f"q{q + 1}") + ";"
                if q == index
                else ""
            )
        if index < len(self._qubit_panels):
            self.info_scroll.ensureWidgetVisible(self._qubit_panels[index])
