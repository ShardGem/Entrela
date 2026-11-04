"""Camera controls with one-way synchronization from the rendered camera."""

from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QSlider,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QWidget,
    QToolButton,
)
from gui.widgets.button import GhostButton, SecondaryButton


class BlochCameraPanel(QFrame):
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setObjectName("Card")
        self.setMinimumWidth(215)
        body = QVBoxLayout(self)
        body.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Câmera 3D")
        title.setObjectName("SectionTitle")
        body.addWidget(title)
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("MetricValue")
        self.zoom_label.setAlignment(Qt.AlignCenter)
        self.zoom_label.setAccessibleName("Nível de zoom atual")
        body.addWidget(self.zoom_label)
        zoom_row = QHBoxLayout()
        zoom_column = QVBoxLayout()
        maximum = QLabel("300%")
        maximum.setAlignment(Qt.AlignCenter)
        minimum = QLabel("50%")
        minimum.setAlignment(Qt.AlignCenter)
        self.zoom_slider = QSlider(Qt.Vertical)
        self.zoom_slider.setRange(
            round(canvas.MIN_ZOOM * 100), round(canvas.MAX_ZOOM * 100)
        )
        self.zoom_slider.setValue(100)
        self.zoom_slider.setSingleStep(5)
        self.zoom_slider.setPageStep(25)
        self.zoom_slider.setTickPosition(QSlider.NoTicks)
        self.zoom_slider.setFixedWidth(40)
        self.zoom_slider.setTickInterval(50)
        self.zoom_slider.setMinimumHeight(110)
        self.zoom_slider.setMaximumHeight(140)
        self.zoom_slider.setAccessibleName("Zoom da câmera em porcentagem")
        self.zoom_slider.valueChanged.connect(
            lambda value: canvas.set_zoom(value / 100)
        )
        zoom_column.addWidget(maximum)
        zoom_column.addWidget(self.zoom_slider, 1, Qt.AlignHCenter)
        zoom_column.addWidget(minimum)
        zoom_row.addLayout(zoom_column, 1)
        buttons = QVBoxLayout()
        for text, tooltip, callback in [
            ("+", "Aproximar", lambda: canvas.zoom_by(1.1)),
            ("100%", "Zoom original", lambda: canvas.set_zoom(1.0)),
            ("−", "Afastar", lambda: canvas.zoom_by(1 / 1.1)),
        ]:
            button = SecondaryButton(text)
            button.setToolTip(tooltip)
            button.setAccessibleName(tooltip)
            button.clicked.connect(callback)
            buttons.addWidget(button)
        zoom_row.addLayout(buttons, 1)
        body.addLayout(zoom_row)
        self.fit_button = SecondaryButton("Enquadrar cena")
        self.fit_button.setToolTip(
            "Ajustar os qubits visíveis ao retângulo, preservando a orientação"
        )
        self.fit_button.clicked.connect(canvas.fit_scene)
        body.addWidget(self.fit_button)
        reset = SecondaryButton("Restaurar câmera")
        reset.setToolTip("Mostrar todos os qubits e restaurar zoom, posição, orientação e perspectiva.")
        reset.clicked.connect(canvas.reset_camera)
        body.addWidget(reset)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.focus_combo = QComboBox()
        self.focus_combo.addItem("Todos os qubits", -1)
        self.projection = QComboBox()
        self.projection.addItem("Perspectiva", "persp")
        self.projection.addItem("Ortográfica", "ortho")
        self.projection.currentIndexChanged.connect(
            lambda: canvas.set_projection(self.projection.currentData())
        )
        self.elevation = QSpinBox()
        self.elevation.setRange(-90, 90)
        self.elevation.setSuffix("°")
        self.elevation.setKeyboardTracking(False)
        self.azimuth = QSpinBox()
        self.azimuth.setRange(-180, 180)
        self.azimuth.setSuffix("°")
        self.azimuth.setKeyboardTracking(False)
        self.elevation.valueChanged.connect(
            lambda value: canvas.set_view(value, canvas.ax.azim)
        )
        self.azimuth.valueChanged.connect(
            lambda value: canvas.set_view(canvas.ax.elev, value)
        )
        orientation = QWidget()
        orientation_body = QVBoxLayout(orientation)
        orientation_body.setContentsMargins(0, 0, 0, 0)
        orientation_form = QFormLayout()
        orientation_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        for text, widget in [
            ("Foco", self.focus_combo),
            ("Projeção", self.projection),
            ("Elevação", self.elevation),
            ("Azimute", self.azimuth),
        ]:
            widget.setAccessibleName(text + " da câmera")
            (
                orientation_form if widget in (self.elevation, self.azimuth) else form
            ).addRow(text, widget)
        body.addLayout(form)
        self.orientation_toggle = QToolButton()
        self.orientation_toggle.setText("Orientação e posição")
        self.orientation_toggle.setCheckable(True)
        self.orientation_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.orientation_toggle.setArrowType(Qt.RightArrow)
        self.orientation_toggle.toggled.connect(orientation.setVisible)
        self.orientation_toggle.toggled.connect(
            lambda opened: self.orientation_toggle.setArrowType(
                Qt.DownArrow if opened else Qt.RightArrow
            )
        )
        body.addWidget(self.orientation_toggle)
        orientation_body.addLayout(orientation_form)
        body.addWidget(orientation)
        orientation.hide()
        presets = QHBoxLayout()
        for label, elev, azim in [
            ("3D", 22, -60),
            ("Frente", 0, -90),
            ("Topo", 90, -90),
        ]:
            button = GhostButton(label)
            button.setToolTip("Vista " + label)
            button.clicked.connect(lambda _, e=elev, a=azim: canvas.set_view(e, a))
            presets.addWidget(button)
        orientation_body.addLayout(presets)
        pan = QGridLayout()
        for text, tip, row, col, callback in [
            ("↑", "Mover para cima", 0, 1, lambda: canvas.pan(dz=0.2)),
            ("←", "Mover à esquerda", 1, 0, lambda: canvas.pan(-0.2)),
            ("◎", "Centralizar sem mudar zoom", 1, 1, canvas.center_camera),
            ("→", "Mover à direita", 1, 2, lambda: canvas.pan(0.2)),
            ("↓", "Mover para baixo", 2, 1, lambda: canvas.pan(dz=-0.2)),
        ]:
            button = GhostButton(text)
            button.setAccessibleName(tip)
            button.setToolTip(tip)
            button.clicked.connect(callback)
            pan.addWidget(button, row, col)
        orientation_body.addLayout(pan)
        self.mouse_lock = QCheckBox("Bloquear câmera pelo mouse")
        self.mouse_lock.toggled.connect(
            lambda locked: canvas.set_mouse_enabled(not locked)
        )
        body.addWidget(self.mouse_lock)
        label = QLabel("Visualização")
        label.setObjectName("SectionTitle")
        body.addWidget(label)
        self.options_layout = QVBoxLayout()
        body.addLayout(self.options_layout)
        note = QLabel(
            "Roda: zoom · arrastar: girar.\nBotão central: mover.\nA câmera não altera os estados."
        )
        note.setWordWrap(True)
        note.setObjectName("SectionSubtitle")
        body.addWidget(note)
        body.addStretch()
        canvas.camera_changed.connect(self.sync_from_camera)
        self.sync_from_camera()

    def sync_from_camera(self):
        # Programmatic feedback must not call set_zoom/set_view again.
        widgets = (
            self.zoom_slider,
            self.elevation,
            self.azimuth,
            self.projection,
            self.focus_combo,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        zoom = self.canvas.zoom
        self.zoom_label.setText(f"{zoom * 100:.0f}%")
        self.zoom_slider.setValue(round(zoom * 100))
        self.elevation.setValue(round(self.canvas.ax.elev))
        self.azimuth.setValue(round((self.canvas.ax.azim + 180) % 360 - 180))
        self.projection.setCurrentIndex(
            self.projection.findData(self.canvas.projection)
        )
        index = self.focus_combo.findData(self.canvas.focus)
        if index >= 0:
            self.focus_combo.setCurrentIndex(index)
        del blockers
