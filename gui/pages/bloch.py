"""Página Evolução 3D — esferas de Bloch animadas com painel de estado."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QComboBox,
    QFrame, QGridLayout
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from qiskit.quantum_info import Statevector, partial_trace, DensityMatrix

from gui.pages.base import PageBase
from gui.widgets.card import Card, EmptyState
from gui.widgets.button import PrimaryButton, GhostButton
from gui.icons import get_icon, get_pixmap
from gui.theme import PALETTE, SPACING, FONT_MONO


# ============================================================
# Interpolação de statevectors
# ============================================================
def interpolate_statevectors(svs, steps_per_pair=20):
    """Compatibility helper: return real snapshots, never fabricate physical evolution."""
    return list(svs)


# ============================================================
# Vetor de Bloch de um qubit
# ============================================================
def get_bloch_vector(state, qubit_index: int, num_qubits: int):
    traced_out = [i for i in range(num_qubits) if i != qubit_index]
    rho = partial_trace(state, traced_out)

    if isinstance(rho, Statevector):
        rho = DensityMatrix(rho)

    rho_mat = rho.data
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)

    bx = float(np.real(np.trace(rho_mat @ X)))
    by = float(np.real(np.trace(rho_mat @ Y)))
    bz = float(np.real(np.trace(rho_mat @ Z)))
    return np.array([bx, by, bz])


def purity_from_bloch(bvec: np.ndarray) -> float:
    """P = (1 + |r|²)/2 para 1 qubit."""
    return (1.0 + float(np.dot(bvec, bvec))) / 2.0


# ============================================================
# Painel de info de um qubit
# ============================================================
class QubitInfoPanel(QFrame):
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.index = index

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        dot = QLabel()
        dot.setFixedSize(8, 8)
        color = PALETTE.q1 if index == 0 else PALETTE.q2
        dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
        title = QLabel(f"Qubit {index}")
        title.setStyleSheet(
            f"color: {PALETTE.text}; font-size: 13px; font-weight: 600;"
        )
        header.addWidget(dot)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(4)

        def add_row(row: int, key: str):
            k = QLabel(key)
            k.setStyleSheet(f"color: {PALETTE.text_dim}; font-size: 11px;")
            v = QLabel("—")
            v.setStyleSheet(
                f"color: {PALETTE.text}; font-size: 12px; font-family: {FONT_MONO};"
            )
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            grid.addWidget(k, row, 0)
            grid.addWidget(v, row, 1, alignment=Qt.AlignRight)
            return v

        self.val_purity = add_row(0, "Pureza")
        self.val_rx = add_row(1, "r·x")
        self.val_ry = add_row(2, "r·y")
        self.val_rz = add_row(3, "r·z")
        self.val_r = add_row(4, "|r|")

        layout.addLayout(grid)

    def update_values(self, bvec: np.ndarray):
        pur = purity_from_bloch(bvec)
        r_norm = float(np.linalg.norm(bvec))

        if pur > 0.95:
            color = PALETTE.success
        elif pur > 0.7:
            color = PALETTE.warning
        else:
            color = PALETTE.danger

        self.val_purity.setText(f"{pur:.3f}")
        self.val_purity.setStyleSheet(
            f"color: {color}; font-size: 12px; font-family: {FONT_MONO}; "
            f"font-weight: 600;"
        )
        self.val_rx.setText(f"{bvec[0]:+.3f}")
        self.val_ry.setText(f"{bvec[1]:+.3f}")
        self.val_rz.setText(f"{bvec[2]:+.3f}")
        self.val_r.setText(f"{r_norm:.3f}")


# ============================================================
# Canvas de Bloch
# ============================================================
class BlochCanvas(FigureCanvas):
    def __init__(self, parent=None):
        fig = Figure(figsize=(10, 6), dpi=100, facecolor=PALETTE.bg)
        super().__init__(fig)
        self.setParent(parent)
        self.fig = fig
        self.ax = fig.add_subplot(111, projection="3d")
        self.ax.set_facecolor(PALETTE.bg)
        for pane in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            pane.pane.fill = False
            pane.pane.set_edgecolor(PALETTE.border)
        self.ax.grid(False)
        self.ax.set_axis_off()
        self.fig.subplots_adjust(0, 0, 1, 1)

        self._line_handles = []
        self._trail_lines = []
        self._trail_data = []
        self._sphere_centers = []

    def clear_scene(self):
        self.ax.clear()
        self.ax.set_axis_off()
        self.ax.set_facecolor(PALETTE.bg)
        for pane in (self.ax.xaxis, self.ax.yaxis, self.ax.zaxis):
            pane.pane.fill = False
            pane.pane.set_edgecolor(PALETTE.border)
        self.ax.grid(False)
        self.fig.subplots_adjust(0, 0, 1, 1)
        self._line_handles = []
        self._trail_lines = []
        self._trail_data = []
        self._sphere_centers = []

    def setup(self, num_qubits: int):
        self.clear_scene()

        if num_qubits == 1:
            self._sphere_centers = [(0, 0, 0)]
        else:
            offset = (num_qubits - 1) * 1.9
            self._sphere_centers = [
                (i * 3.8 - offset, 0, 0) for i in range(num_qubits)
            ]

        min_x = min(c[0] for c in self._sphere_centers) - 2.2
        max_x = max(c[0] for c in self._sphere_centers) + 2.2
        self.ax.set_xlim(min_x, max_x)
        self.ax.set_ylim(-1.8, 1.8)
        self.ax.set_zlim(-1.8, 1.8)
        self.ax.set_box_aspect((max_x - min_x, 3.6, 3.6))

        for i, center in enumerate(self._sphere_centers):
            self._draw_sphere(center)
            self._draw_axes(center)

            self.ax.text(
                center[0], center[1] - 2.0, center[2] - 0.1,
                f"Qubit {i}",
                fontsize=10,
                color=PALETTE.text_muted,
                ha="center",
            )

            color = PALETTE.q1 if i == 0 else PALETTE.q2
            line, = self.ax.plot(
                [center[0], center[0]],
                [center[1], center[1]],
                [center[2], center[2] + 1],
                color=color, linewidth=2.5, solid_capstyle="round",
            )
            self._line_handles.append(line)

            trail, = self.ax.plot(
                [], [], [],
                "--", color=PALETTE.text_dim, alpha=0.5, linewidth=1,
            )
            self._trail_lines.append(trail)
            self._trail_data.append([])

        self.ax.view_init(elev=22, azim=-60)
        self.draw_idle()

    def _draw_sphere(self, center):
        u = np.linspace(0, 2 * np.pi, 24)
        v = np.linspace(0, np.pi, 16)
        x = center[0] + np.outer(np.cos(u), np.sin(v))
        y = center[1] + np.outer(np.sin(u), np.sin(v))
        z = center[2] + np.outer(np.ones(np.size(u)), np.cos(v))

        self.ax.plot_surface(
            x, y, z,
            color=PALETTE.primary, alpha=0.06,
            linewidth=0, antialiased=True,
        )
        self.ax.plot_wireframe(
            x, y, z,
            color=PALETTE.border_strong,
            linewidth=0.4, alpha=0.5,
        )

    def _draw_axes(self, center):
        L = 1.35
        for (dx, dy, dz), label in [
            ((L, 0, 0), "X"),
            ((0, L, 0), "Y"),
            ((0, 0, L), "Z"),
        ]:
            self.ax.plot(
                [center[0], center[0] + dx],
                [center[1], center[1] + dy],
                [center[2], center[2] + dz],
                color=PALETTE.text_dim, linewidth=0.8, alpha=0.7,
            )
            self.ax.text(
                center[0] + dx * 1.08,
                center[1] + dy * 1.08,
                center[2] + dz * 1.08,
                label,
                fontsize=8,
                color=PALETTE.text_dim,
                ha="center", va="center",
            )

    def update_frame(self, bloch_vectors, record_trail=True):
        if not self._line_handles:
            return

        for i, center in enumerate(self._sphere_centers):
            bvec = bloch_vectors[i]

            self._line_handles[i].set_data_3d(
                [center[0], center[0] + bvec[0]],
                [center[1], center[1] + bvec[1]],
                [center[2], center[2] + bvec[2]],
            )

            if record_trail:
                point = (
                    center[0] + bvec[0],
                    center[1] + bvec[1],
                    center[2] + bvec[2],
                )
                self._trail_data[i].append(point)
                if len(self._trail_data[i]) > 80:
                    self._trail_data[i].pop(0)

                if self._trail_data[i]:
                    xs, ys, zs = zip(*self._trail_data[i])
                    self._trail_lines[i].set_data_3d(xs, ys, zs)

        self.draw_idle()


# ============================================================
# Página principal
# ============================================================
class BlochPage(PageBase):
    def __init__(self, parent=None):
        super().__init__(
            "Evolução 3D",
            "Trajetória dos qubits na esfera de Bloch ao longo do tempo.",
        )

        self.original_svs = []
        self.interpolated_svs = []
        self.precomputed_bloch = []
        self.current_frame = 0
        self.num_qubits = 2
        self.playing = False
        self.speed_factor = 1.0
        self._accumulator = 0.0

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._on_tick)

        self._build()

    def _build(self):
        self._empty = EmptyState(
            "bloch",
            "Nenhuma evolução disponível",
            "Execute uma simulação com snapshots ativados para visualizar "
            "a evolução dos qubits.",
        )
        self.body().addWidget(self._empty)
        self.body().addStretch()

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(SPACING.lg)

        # Barra de controles
        controls_card = Card()
        controls_row = QHBoxLayout()
        controls_row.setSpacing(SPACING.sm)

        self.btn_play = PrimaryButton("Iniciar", icon="play")
        self.btn_play.clicked.connect(self._toggle_play)

        self.btn_stop = GhostButton("Parar", icon="stop")
        self.btn_stop.clicked.connect(self._stop)

        self.btn_prev = GhostButton("", icon="prev")
        self.btn_prev.setToolTip("Frame anterior")
        self.btn_prev.clicked.connect(self._prev)

        self.btn_next = GhostButton("", icon="next")
        self.btn_next.setToolTip("Próximo frame")
        self.btn_next.clicked.connect(self._next)

        controls_row.addWidget(self.btn_play)
        controls_row.addWidget(self.btn_stop)
        controls_row.addSpacing(8)
        controls_row.addWidget(self.btn_prev)
        controls_row.addWidget(self.btn_next)
        controls_row.addStretch()

        speed_lbl = QLabel("Velocidade")
        speed_lbl.setStyleSheet(
            f"color: {PALETTE.text_muted}; font-size: 12px;"
        )
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1x", "2x", "4x"])
        self.speed_combo.setCurrentText("1x")
        self.speed_combo.currentTextChanged.connect(self._update_speed)
        self.speed_combo.setFixedWidth(80)

        controls_row.addWidget(speed_lbl)
        controls_row.addWidget(self.speed_combo)

        controls_card.add_layout(controls_row)
        content_layout.addWidget(controls_card)

        # Canvas + painel lateral
        canvas_row = QHBoxLayout()
        canvas_row.setSpacing(SPACING.lg)

        self.canvas = BlochCanvas()
        canvas_row.addWidget(self.canvas, 4)

        self._info_container = QWidget()
        info_layout = QVBoxLayout(self._info_container)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(SPACING.md)

        info_title = QLabel("Estado atual")
        info_title.setStyleSheet(
            f"color: {PALETTE.text}; font-size: 14px; font-weight: 600;"
        )
        info_layout.addWidget(info_title)

        self._qubit_panels: list[QubitInfoPanel] = []
        info_layout.addStretch()

        canvas_row.addWidget(self._info_container, 1)
        content_layout.addLayout(canvas_row, 1)

        # Slider de progresso
        slider_card = Card()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider)

        self.frame_label = QLabel("Frame 0 / 0")
        self.frame_label.setStyleSheet(
            f"color: {PALETTE.text_muted}; font-size: 12px; "
            f"font-family: {FONT_MONO}; min-width: 120px;"
        )
        self.frame_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(SPACING.md)
        slider_row.addWidget(self.slider, 1)
        slider_row.addWidget(self.frame_label)

        slider_card.add_layout(slider_row)
        content_layout.addWidget(slider_card)

        self.body().addWidget(self._content, 1)
        self._content.setVisible(False)

    def load_statevectors(self, statevectors, times=None):
        self.timer.stop()
        self.playing = False
        self.btn_play.setText("Iniciar")
        self.btn_play.setIcon(get_icon("play", color=PALETTE.primary_on, size=16))
        self.original_svs = list(statevectors or [])
        self.precomputed_bloch = []
        self.times = times if times is not None and len(times) == len(self.original_svs) else None

        if not statevectors:
            self.interpolated_svs = []
            self._content.setVisible(False)
            self._empty.setVisible(True)
            return

        dim = statevectors[0].dim
        self.num_qubits = int(np.log2(dim))

        self.interpolated_svs = interpolate_statevectors(
            self.original_svs, steps_per_pair=20
        )

        self.precomputed_bloch = []
        for sv in self.interpolated_svs:
            bloch_list = [
                get_bloch_vector(sv, q, self.num_qubits)
                for q in range(self.num_qubits)
            ]
            self.precomputed_bloch.append(bloch_list)

        self.canvas.setup(self.num_qubits)
        self._rebuild_info_panels()

        self.slider.blockSignals(True)
        self.slider.setMaximum(len(self.precomputed_bloch) - 1)
        self.slider.setValue(0)
        self.slider.blockSignals(False)

        self.current_frame = 0
        self._accumulator = 0.0

        first = self.precomputed_bloch[0]
        self.canvas.update_frame(first, record_trail=True)

        self._empty.setVisible(False)
        self._content.setVisible(True)

        self._refresh_ui()

    def _rebuild_info_panels(self):
        self._qubit_panels.clear()

        layout = self._info_container.layout()
        while layout.count() > 2:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        for i in range(self.num_qubits):
            panel = QubitInfoPanel(i)
            layout.insertWidget(layout.count() - 1, panel)
            self._qubit_panels.append(panel)

    def _refresh_ui(self):
        if not self.precomputed_bloch:
            return

        idx = int(self.current_frame)
        bloch_list = self.precomputed_bloch[idx]

        time_label = f" · t={self.times[idx]:.4g}" if self.times is not None else ""
        self.frame_label.setText(f"Snapshot {idx + 1} / {len(self.precomputed_bloch)}{time_label}")

        self.slider.blockSignals(True)
        self.slider.setValue(idx)
        self.slider.blockSignals(False)

        self.canvas.update_frame(bloch_list, record_trail=True)

        for i, panel in enumerate(self._qubit_panels):
            panel.update_values(bloch_list[i])

    def _on_tick(self):
        if not self.precomputed_bloch:
            return

        self._accumulator += self.speed_factor
        advanced = False
        while self._accumulator >= 1.0:
            self.current_frame = (self.current_frame + 1) % len(self.precomputed_bloch)
            self._accumulator -= 1.0
            advanced = True

        if advanced:
            self._refresh_ui()

    def _toggle_play(self):
        if self.playing:
            self.timer.stop()
            self.btn_play.setText("Iniciar")
            self.btn_play.setIcon(get_icon("play", color=PALETTE.primary_on, size=16))
        else:
            self.timer.start()
            self.btn_play.setText("Pausar")
            self.btn_play.setIcon(get_icon("pause", color=PALETTE.primary_on, size=16))
        self.playing = not self.playing

    def _stop(self):
        self.timer.stop()
        self.playing = False
        self._accumulator = 0.0
        self.btn_play.setText("Iniciar")
        self.btn_play.setIcon(get_icon("play", color=PALETTE.primary_on, size=16))
        self.current_frame = 0
        self._refresh_ui()

    def _prev(self):
        if not self.precomputed_bloch:
            return
        self.current_frame = (self.current_frame - 1) % len(self.precomputed_bloch)
        self._refresh_ui()

    def _next(self):
        if not self.precomputed_bloch:
            return
        self.current_frame = (self.current_frame + 1) % len(self.precomputed_bloch)
        self._refresh_ui()

    def _on_slider(self, value: int):
        if self.playing:
            return
        self.current_frame = value
        self._refresh_ui()

    def _update_speed(self, text: str):
        try:
            self.speed_factor = float(text.replace("x", ""))
        except ValueError:
            self.speed_factor = 1.0
        if self.speed_factor <= 0:
            self.speed_factor = 1.0
