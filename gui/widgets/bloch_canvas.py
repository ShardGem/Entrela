"""Bloch scene and bounded camera. Drawing and playback never move the camera."""

import math
import numpy as np
from PySide6.QtCore import Signal
from matplotlib.backend_bases import MouseEvent, MouseButton
from matplotlib.figure import Figure
from gui.theme import PALETTE
from gui.widgets.figure_canvas import StableFigureCanvas


class BlochCanvas(StableFigureCanvas):
    camera_changed = Signal()
    MIN_ZOOM = 0.5
    MAX_ZOOM = 3.0

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 5), facecolor=PALETTE.bg)
        super().__init__(self.fig, parent, minimum=(240, 280))
        self.ax = self.fig.add_subplot(111, projection="3d")
        self.fig.subplots_adjust(0, 0, 1, 1)
        self._sphere_centers = []
        self._line_handles = []
        self._ideal_handles = []
        self._trail_lines = []
        self._trail_data = []
        self._axis_artists = []
        self._qubit_artists = []
        self.axes_visible = True
        self.mouse_enabled = True
        self.zoom = 1.0
        self.focus = -1
        self._pan = np.zeros(3)
        self._applying_camera = False
        self._drag = None
        self.projection = "persp"
        self._configure_axes()
        self.mpl_connect("scroll_event", self._on_scroll)
        self.mpl_connect("button_press_event", self._on_press)
        self.mpl_connect("motion_notify_event", self._on_motion)
        self.mpl_connect("button_release_event", self._end_drag)
        self.mpl_connect("figure_leave_event", self._end_drag)
        self.setToolTip(
            "Roda: zoom · arrastar com botão esquerdo: girar · botão central: mover"
        )

    def _configure_axes(self):
        self.ax.set_axis_off()
        self.ax.set_facecolor(PALETTE.bg)
        # A single controller owns zoom, pan and rotation, including mouse input.
        self.ax.mouse_init(rotate_btn=[], pan_btn=[], zoom_btn=[])
        self.ax.set_autoscale_on(False)

    def setup(self, num_qubits):
        if not 1 <= num_qubits <= 6:
            raise ValueError("São suportados de 1 a 6 qubits")
        self.ax.clear()
        self._configure_axes()
        columns = min(3, num_qubits)
        rows = int(np.ceil(num_qubits / columns))
        self._sphere_centers = [
            (
                (q % columns - (columns - 1) / 2) * 3.5,
                0.0,
                ((rows - 1) / 2 - q // columns) * 3.5,
            )
            for q in range(num_qubits)
        ]
        self._line_handles = []
        self._ideal_handles = []
        self._trail_lines = []
        self._trail_data = []
        self._axis_artists = []
        self._qubit_artists = []
        u, v = np.meshgrid(np.linspace(0, 2 * np.pi, 24), np.linspace(0, np.pi, 16))
        for q, c in enumerate(self._sphere_centers):
            color = getattr(PALETTE, f"q{q + 1}")
            artists = []
            wire = self.ax.plot_wireframe(
                c[0] + np.cos(u) * np.sin(v),
                c[1] + np.sin(u) * np.sin(v),
                c[2] + np.cos(v),
                color=PALETTE.border_strong,
                linewidth=0.5,
                alpha=0.65,
            )
            artists.append(wire)
            axes_start = len(self._axis_artists)
            for axis, label in enumerate("XYZ"):
                end = np.array(c)
                end[axis] += 1.3
                self._axis_artists.extend(
                    self.ax.plot(*zip(c, end), color=PALETTE.text_dim, linewidth=0.7)
                )
                self._axis_artists.append(
                    self.ax.text(*end, label, color=PALETTE.text_muted, fontsize=9)
                )
            artists.extend(self._axis_artists[axes_start:])
            artists.append(
                self.ax.text(c[0], c[1], c[2] - 1.45, f"q{q}", color=color, ha="center")
            )
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
                linewidth=1.8,
                label="Circuito ideal" if q == 0 else None,
            )
            (trail,) = self.ax.plot([], [], [], color=color, alpha=0.55, linewidth=1.2)
            self._line_handles.append(line)
            self._ideal_handles.append(ideal)
            self._trail_lines.append(trail)
            self._trail_data.append([])
            artists.extend((line, ideal, trail))
            self._qubit_artists.append(artists)
        self.ax.legend(
            loc="upper left",
            bbox_to_anchor=(0.01, 0.99),
            bbox_transform=self.fig.transFigure,
            facecolor=PALETTE.surface,
            labelcolor=PALETTE.text,
            fontsize=9,
        )
        self.set_axes_visible(self.axes_visible)
        self.focus = -1
        self.reset_camera()

    def _bounds(self):
        centers = np.array(self._sphere_centers or [(0.0, 0.0, 0.0)], dtype=float)
        if 0 <= self.focus < len(centers):
            return centers[self.focus].copy(), np.full(3, 1.7)
        low, high = centers.min(axis=0) - 1.8, centers.max(axis=0) + 1.8
        return (low + high) / 2, (high - low) / 2

    def _apply_camera(self):
        if self._applying_camera:
            return
        self._applying_camera = True
        try:
            if not math.isfinite(self.zoom):
                self.zoom = 1.0
            self.zoom = float(np.clip(self.zoom, self.MIN_ZOOM, self.MAX_ZOOM))
            center, base_half = self._bounds()
            pan = np.asarray(self._pan, dtype=float)
            if pan.shape != (3,) or not np.all(np.isfinite(pan)):
                pan = np.zeros(3)
            self._pan = np.clip(pan, -base_half * 0.6, base_half * 0.6)
            center += self._pan
            half = base_half / self.zoom
            # Do not emit axis-limit callbacks back into the camera controller.
            self.ax.set_xlim(
                center[0] - half[0], center[0] + half[0], emit=False, auto=False
            )
            self.ax.set_ylim(
                center[1] - half[1], center[1] + half[1], emit=False, auto=False
            )
            self.ax.set_zlim(
                center[2] - half[2], center[2] + half[2], emit=False, auto=False
            )
            # set_box_aspect normalizes its ndarray argument in-place.
            self.ax.set_box_aspect(base_half.copy(), zoom=1.45)
            self.ax.set_proj_type(self.projection)
            self._sync_visibility()
        finally:
            self._applying_camera = False
        self.camera_changed.emit()
        self.draw_idle()

    def set_zoom(self, value):
        value = float(value)
        if not math.isfinite(value):
            return
        value = float(np.clip(value, self.MIN_ZOOM, self.MAX_ZOOM))
        if math.isclose(value, self.zoom, abs_tol=1e-12):
            return
        self.zoom = value
        self._apply_camera()

    def zoom_by(self, factor):
        if not self._sphere_centers or not math.isfinite(factor) or factor <= 0:
            return
        self.set_zoom(self.zoom * factor)

    def _on_scroll(self, event):
        if self.mouse_enabled and event.inaxes is self.ax:
            step = float(getattr(event, "step", 0))
            if math.isfinite(step):
                self.zoom_by(math.exp(0.12 * float(np.clip(step, -4, 4))))

    def wheelEvent(self, event):
        # Pixel deltas are not wheel notches: normalize precision touchpads too.
        if not self.mouse_enabled:
            event.ignore()
            return
        x, y = self.mouseEventCoords(event)
        if not self.ax.bbox.contains(x, y):
            event.ignore()
            return
        angle, pixel = event.angleDelta().y(), event.pixelDelta().y()
        steps = angle / 120 if angle else pixel / 120
        if not steps:
            event.ignore()
            return
        MouseEvent("scroll_event", self, x, y, step=steps, guiEvent=event)._process()
        event.accept()

    def _on_press(self, event):
        if (
            self.mouse_enabled
            and event.inaxes is self.ax
            and event.button in (MouseButton.LEFT, MouseButton.MIDDLE)
        ):
            self._drag = (event.button, event.x, event.y)

    def _on_motion(self, event):
        if self._drag is None or not self.mouse_enabled:
            return
        button, x, y = self._drag
        if event.inaxes is not self.ax:
            self._end_drag()
            return
        dx, dy = event.x - x, event.y - y
        self._drag = (button, event.x, event.y)
        if not dx and not dy:
            return
        width, height = self.get_width_height(physical=True)
        if button == MouseButton.LEFT:
            self.set_view(
                self.ax.elev - dy * 180 / max(1, height),
                self.ax.azim - dx * 180 / max(1, width),
            )
        else:
            az, el = np.deg2rad([self.ax.azim, self.ax.elev])
            right = np.array([-np.sin(az), np.cos(az), 0.0])
            up = np.array(
                [-np.sin(el) * np.cos(az), -np.sin(el) * np.sin(az), np.cos(el)]
            )
            _, half = self._bounds()
            self._pan -= (
                (dx * right + dy * up) * 2 * max(half) / self.zoom / max(1, height)
            )
            self._apply_camera()

    def _end_drag(self, event=None):
        self._drag = None

    def set_mouse_enabled(self, enabled):
        self.mouse_enabled = bool(enabled)
        self._end_drag()

    def set_focus(self, index):
        self.focus = index if -1 <= index < len(self._sphere_centers) else -1
        self.zoom = 1.0
        self._pan = np.zeros(3)
        self._apply_camera()

    def pan(self, dx=0, dz=0):
        self._pan += np.array([dx, 0.0, dz])
        self._apply_camera()

    def center_camera(self):
        self._pan = np.zeros(3)
        self._apply_camera()

    def set_view(self, elev, azim):
        if not all(math.isfinite(float(x)) for x in (elev, azim)):
            return
        self.ax.view_init(
            elev=float(np.clip(elev, -90, 90)), azim=(azim + 180) % 360 - 180, roll=0
        )
        self._apply_camera()

    def set_projection(self, kind):
        if kind not in ("persp", "ortho"):
            return
        self.projection = kind
        self._apply_camera()

    def set_axes_visible(self, visible):
        self.axes_visible = bool(visible)
        self._sync_visibility()
        self.draw_idle()

    def reset_camera(self):
        self._end_drag()
        self.zoom = 1.0
        self._pan = np.zeros(3)
        self.projection = "persp"
        self.ax.view_init(elev=22, azim=-60, roll=0)
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
            self._trail_data[q] = self._trail_data[q][-80:]
            points = self._trail_data[q]
            self._trail_lines[q].set_data_3d(*zip(*points) if points else ([], [], []))
        self.draw_idle()

    def camera_state(self):
        return dict(
            zoom=self.zoom,
            pan=self._pan.tolist(),
            elev=float(self.ax.elev),
            azim=float(self.ax.azim),
            projection=self.projection,
        )

    def restore_camera(
        self,
        *,
        zoom=1.0,
        pan=(0.0, 0.0, 0.0),
        elev=22.0,
        azim=-60.0,
        projection="persp",
    ):
        self._end_drag()
        self.zoom = float(zoom) if math.isfinite(float(zoom)) else 1.0
        self._pan = np.asarray(pan, dtype=float)
        if not all(math.isfinite(float(x)) for x in (elev, azim)):
            elev, azim = 22.0, -60.0
        self.ax.view_init(
            elev=float(np.clip(elev, -90, 90)), azim=(azim + 180) % 360 - 180, roll=0
        )
        self.projection = projection if projection in ("persp", "ortho") else "persp"
        self._apply_camera()

    def _sync_visibility(self):
        axes = set(self._axis_artists)
        for q, artists in enumerate(self._qubit_artists):
            for artist in artists:
                artist.set_visible(
                    self.focus in (-1, q) and (self.axes_visible or artist not in axes)
                )
        legend = self.ax.get_legend()
        if legend and legend.get_lines():
            legend.get_lines()[0].set_color(
                getattr(PALETTE, f"q{max(0, self.focus) + 1}")
            )
