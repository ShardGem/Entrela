"""Snapshot viewer: the camera never changes scientific state."""

from __future__ import annotations
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
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
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from qiskit.quantum_info import Statevector, DensityMatrix, partial_trace
from gui.pages.base import PageBase
from gui.widgets.card import EmptyState
from gui.widgets.button import PrimaryButton, GhostButton
from gui.theme import PALETTE
from gui.widgets.plot_canvas import MplCanvas


def interpolate_statevectors(svs, steps_per_pair=20):
    return list(svs)


def get_bloch_vector(state, qubit_index, num_qubits):
    rho = DensityMatrix(
        partial_trace(state, [q for q in range(num_qubits) if q != qubit_index])
    ).data
    return np.array(
        [2 * rho[0, 1].real, -2 * rho[0, 1].imag, (rho[0, 0] - rho[1, 1]).real], float
    )


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


class BlochCanvas(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(9, 5), facecolor=PALETTE.bg)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setMinimumSize(240, 280)
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.fig.subplots_adjust(0, 0, 1, 1)
        self._sphere_centers = []
        self._line_handles = []
        self._ideal_handles = []
        self._trail_lines = []
        self._trail_data = []
        self.zoom = 1.0
        self.focus = -1
        self._pan = np.zeros(3)
        self.mpl_connect("scroll_event", self._on_scroll)
        self.setToolTip(
            "Roda: zoom · arrastar: rotação · botão central: pan · Restaurar visão: reset"
        )

    def setup(self, num_qubits):
        self.ax.clear()
        self.ax.set_axis_off()
        self.ax.set_facecolor(PALETTE.bg)
        columns = min(3, num_qubits)
        rows = int(np.ceil(num_qubits / columns))
        self._sphere_centers = [
            (
                (q % columns - (columns - 1) / 2) * 3.5,
                0,
                ((rows - 1) / 2 - q // columns) * 3.5,
            )
            for q in range(num_qubits)
        ]
        self._line_handles = []
        self._ideal_handles = []
        self._trail_lines = []
        self._trail_data = []
        u, v = np.meshgrid(np.linspace(0, 2 * np.pi, 24), np.linspace(0, np.pi, 16))
        for q, c in enumerate(self._sphere_centers):
            color = getattr(PALETTE, f"q{q + 1}")
            x = c[0] + np.cos(u) * np.sin(v)
            y = c[1] + np.sin(u) * np.sin(v)
            z = c[2] + np.cos(v)
            self.ax.plot_wireframe(
                x, y, z, color=PALETTE.border_strong, linewidth=0.4, alpha=0.45
            )
            for axis, label in enumerate("XYZ"):
                end = np.array(c, float)
                end[axis] += 1.3
                self.ax.plot(*zip(c, end), color=PALETTE.text_dim, linewidth=0.6)
                self.ax.text(*end, label, color=PALETTE.text_muted, fontsize=9)
            self.ax.text(c[0], c[1], c[2] - 1.45, f"q{q}", color=color, ha="center")
            (line,) = self.ax.plot(
                [],
                [],
                [],
                color=color,
                linewidth=3,
                label="Simulado" if q == 0 else None,
            )
            (ideal,) = self.ax.plot(
                [],
                [],
                [],
                "--",
                color=PALETTE.text,
                linewidth=1.5,
                label="Circuito ideal" if q == 0 else None,
            )
            (trail,) = self.ax.plot([], [], [], color=color, alpha=0.5, linewidth=1)
            self._line_handles.append(line)
            self._ideal_handles.append(ideal)
            self._trail_lines.append(trail)
            self._trail_data.append([])
        self.ax.legend(
            loc="upper left", facecolor=PALETTE.surface, labelcolor=PALETTE.text
        )
        self.focus = -1
        self.reset_camera()

    def _bounds(self):
        centers = np.array(self._sphere_centers or [(0, 0, 0)])
        if 0 <= self.focus < len(centers):
            return centers[self.focus].copy(), np.array([1.7] * 3)
        low = centers.min(axis=0) - 1.8
        high = centers.max(axis=0) + 1.8
        return (low + high) / 2, (high - low) / 2

    def _apply_camera(self):
        center, half = self._bounds()
        center += self._pan
        half = half / self.zoom
        self.ax.set_xlim(center[0] - half[0], center[0] + half[0])
        self.ax.set_ylim(center[1] - half[1], center[1] + half[1])
        self.ax.set_zlim(center[2] - half[2], center[2] + half[2])
        self.ax.set_box_aspect(half, zoom=1.55)
        self.draw_idle()

    def zoom_by(self, factor):
        if not self._sphere_centers:
            return
        self.zoom = float(np.clip(self.zoom * factor, 0.5, 3.0))
        self._apply_camera()

    def _on_scroll(self, event):
        if event.inaxes is self.ax:
            # Capture native pan before applying bounded zoom around the selected sphere.
            center, _ = self._bounds()
            self._pan = (
                np.array(
                    [
                        np.mean(self.ax.get_xlim()),
                        np.mean(self.ax.get_ylim()),
                        np.mean(self.ax.get_zlim()),
                    ]
                )
                - center
            )
            self.zoom_by(np.exp(0.12 * getattr(event, "step", 0)))

    def set_focus(self, index):
        self.focus = index
        self.zoom = 1.0
        self._pan = np.zeros(3)
        self._apply_camera()

    def pan(self, dx=0, dz=0):
        _, half = self._bounds()
        self._pan = np.clip(self._pan + np.array([dx, 0, dz]), -half, half)
        self._apply_camera()

    def reset_camera(self):
        self.zoom = 1.0
        self._pan = np.zeros(3)
        self.ax.view_init(elev=22, azim=-60)
        self._apply_camera()

    def clear_trails(self):
        self._trail_data = [[] for _ in self._sphere_centers]
        for line in self._trail_lines:
            line.set_data_3d([], [], [])

    def update_frame(
        self, bloch_vectors, record_trail=True, ideal_vectors=None, history=None
    ):
        for q, c in enumerate(self._sphere_centers):
            end = np.array(c) + bloch_vectors[q]
            self._line_handles[q].set_data_3d(*zip(c, end))
            if ideal_vectors is not None:
                self._ideal_handles[q].set_data_3d(
                    *zip(c, np.array(c) + ideal_vectors[q])
                )
            else:
                self._ideal_handles[q].set_data_3d([], [], [])
            if history is not None:
                self._trail_data[q] = [
                    tuple(np.array(c) + frame[q]) for frame in history
                ]
            elif record_trail:
                self._trail_data[q].append(tuple(end))
            points = self._trail_data[q][-80:]
            self._trail_lines[q].set_data_3d(*zip(*points) if points else ([], [], []))
        self.draw_idle()


class BlochPage(PageBase):
    frame_changed = Signal(int)
    preferences_changed = Signal()

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
        self.current_frame = 0
        self.num_qubits = 2
        self.playing = False
        self.speed_factor = 1.0
        self.times = None
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
        for w in (
            self.btn_play,
            self.btn_stop,
            self.btn_prev,
            self.btn_next,
            self.speed_combo,
            self.loop,
            self.trails,
            self.overlay,
        ):
            controls.addWidget(w)
        layout.addLayout(controls)
        camera = QHBoxLayout()
        self.focus_combo = QComboBox()
        self.focus_combo.addItem("Todos os qubits", -1)
        self.focus_combo.currentIndexChanged.connect(self._focus)
        camera.addWidget(self.focus_combo)
        for text, callback in [
            ("+", lambda: self.canvas.zoom_by(1.2)),
            ("−", lambda: self.canvas.zoom_by(1 / 1.2)),
            ("←", lambda: self.canvas.pan(-0.25)),
            ("→", lambda: self.canvas.pan(0.25)),
            ("↑", lambda: self.canvas.pan(dz=0.25)),
            ("↓", lambda: self.canvas.pan(dz=-0.25)),
            ("Restaurar visão", lambda: self.canvas.reset_camera()),
        ]:
            button = GhostButton(text)
            button.clicked.connect(callback)
            camera.addWidget(button)
        layout.addLayout(camera)
        self.canvas = BlochCanvas()
        self.probabilities_canvas = MplCanvas(height=4)
        self.visual_tabs = QTabWidget()
        self.visual_tabs.addTab(self.canvas, "Esferas de Bloch")
        self.visual_tabs.addTab(self.probabilities_canvas, "Probabilidades no instante")
        self.visual_tabs.currentChanged.connect(self._refresh_ui)
        layout.addWidget(self.visual_tabs, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider)
        self.frame_label = QLabel()
        layout.addWidget(self.frame_label)
        self._info_container = QWidget()
        QGridLayout(self._info_container)
        self._qubit_panels = []
        info_scroll = QScrollArea()
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(self._info_container)
        info_scroll.setFixedHeight(145)
        layout.addWidget(info_scroll)
        note = QLabel(
            "Pureza local baixa pode indicar correlações/emaranhamento: em Bell ideal, cada qubit tem pureza ½. A linha tracejada representa o mesmo circuito sem ruído."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        self.body().addWidget(self._content, 1)
        self._content.hide()

    def load_statevectors(self, statevectors, times=None, ideal_statevectors=None):
        self._pause()
        self.original_svs = list(statevectors or [])
        self.interpolated_svs = list(self.original_svs)
        self.precomputed_bloch = []
        self.ideal_bloch = []
        self.ideal_states = list(ideal_statevectors or [])
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
            self.precomputed_bloch.append(
                [
                    get_bloch_vector(state, q, self.num_qubits)
                    for q in range(self.num_qubits)
                ]
            )
        if ideal_statevectors and len(ideal_statevectors) == len(statevectors):
            self.ideal_bloch = [
                [
                    get_bloch_vector(s, q, self.num_qubits)
                    for q in range(self.num_qubits)
                ]
                for s in ideal_statevectors
            ]
        self.canvas.setup(self.num_qubits)
        old_focus = self.focus_combo.currentData()
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
        self.current_frame = 0
        self._refresh_ui()

    def _focus(self, *_):
        self.canvas.set_focus(
            self.focus_combo.currentData()
            if self.focus_combo.currentData() is not None
            else -1
        )
        self._refresh_ui()
        self.preferences_changed.emit()

    def _refresh_ui(self, *_):
        if not self.precomputed_bloch:
            return
        idx = self.current_frame
        self.frame_label.setText(
            f"Snapshot {idx + 1} / {len(self.precomputed_bloch)}"
            + (f" · t={self.times[idx]:.6g} (ℏ=1)" if self.times is not None else "")
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
        if self.visual_tabs.currentIndex() == 1:
            ax = self.probabilities_canvas.reset_axes()
            probabilities = self.original_svs[idx].probabilities()
            positions = np.arange(len(probabilities))
            ax.bar(
                positions - 0.18,
                probabilities,
                width=0.36,
                color=PALETTE.primary,
                label="Simulado",
            )
            if self.overlay.isChecked() and getattr(self, "ideal_states", None):
                ax.bar(
                    positions + 0.18,
                    self.ideal_states[idx].probabilities(),
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
