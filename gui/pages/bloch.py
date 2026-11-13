"""Snapshot viewer: the camera never changes scientific state."""

from __future__ import annotations
from collections import OrderedDict
from hashlib import blake2b
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QSignalBlocker, QEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QComboBox,
    QCheckBox,
    QScrollArea,
    QSplitter,
    QGridLayout,
    QTabWidget,
    QSpinBox,
    QPlainTextEdit,
    QSizePolicy,
    QFrame,
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
from gui.widgets.flow_layout import FlowLayout
from gui.widgets.state_inspector import StateInspector
from gui.widgets.content_tabs import ContentTabs
from gui.widgets.collapsible import CollapsibleSection
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
        self._camera_layout_timer = QTimer(self)
        self._camera_layout_timer.setSingleShot(True)
        self._camera_layout_timer.setInterval(0)
        self._camera_layout_timer.timeout.connect(self._fit_camera)
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
        self._probability_bars = []
        self._probability_annotation = None
        self._experiment = None
        self.current_frame = 0
        self.num_qubits = 2
        self.playing = False
        self.speed_factor = 1.0
        self.times = None
        self._refreshing = False
        self._maximized = False
        self._camera_auto = True
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
        self.transport = QFrame()
        self.transport.setObjectName("TransportBar")
        controls = FlowLayout(self.transport)
        controls.setContentsMargins(10, 8, 10, 8)
        self.btn_play = PrimaryButton("Reproduzir")
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_stop = GhostButton("Reiniciar")
        self.btn_stop.setToolTip("Volta ao primeiro snapshot; a câmera mantém sua posição.")
        self.btn_stop.clicked.connect(self._stop)
        self.btn_prev = GhostButton("Anterior")
        self.btn_prev.setToolTip("Snapshot anterior")
        self.btn_prev.clicked.connect(self._prev)
        self.btn_next = GhostButton("Próximo")
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
        self.selection_label.setObjectName("FieldHint")
        self.maximize_button = GhostButton("Ampliar área 3D")
        self.maximize_button.setCheckable(True)
        self.maximize_button.toggled.connect(self.set_maximized)
        controls.addWidget(self.maximize_button)
        self.camera_toggle = GhostButton("Inspetor")
        self.camera_toggle.setCheckable(True)
        self.camera_toggle.setChecked(True)
        self.camera_toggle.setToolTip("Mostrar ou recolher o painel de câmera, etapas, qubits e métricas.")
        self.camera_toggle.setAccessibleName("Mostrar controles da câmera e visualização")
        self.camera_toggle.clicked.connect(self._camera_chosen)
        self.camera_toggle.toggled.connect(lambda *_: self._visual_mode_changed(self.visual_tabs.currentIndex()))
        controls.addWidget(self.camera_toggle)
        controls.add_group(QLabel("Velocidade"), self.speed_combo)
        controls.addWidget(self.loop)
        layout.addWidget(self.selection_label)
        self.canvas = BlochCanvas()
        self.canvas.qubit_selected.connect(self._select_qubit)
        self.camera_panel = BlochCameraPanel(self.canvas)
        self.focus_combo = self.camera_panel.focus_combo
        self.focus_combo.currentIndexChanged.connect(self._focus)
        self.focus_selected = GhostButton("Focar selecionado")
        self.focus_selected.setEnabled(False)
        self.focus_selected.clicked.connect(self._toggle_focus)
        self.canvas.focus_changed.connect(self._sync_focus)
        self.camera_panel.options_layout.addWidget(self.focus_selected)
        self.zoom_slider = self.camera_panel.zoom_slider
        self.zoom_label = self.camera_panel.zoom_label
        self.axes_check = QCheckBox("Eixos X, Y, Z")
        self.axes_check.setChecked(True)
        self.axes_check.toggled.connect(self.canvas.set_axes_visible)
        for w in (self.overlay, self.trails, self.axes_check):
            self.camera_panel.options_layout.addWidget(w)
        self.probabilities_canvas = MplCanvas(height=4)
        self.probabilities_canvas.mpl_connect("motion_notify_event", self._hover_probability)
        self.probabilities_canvas.mpl_connect("figure_leave_event", self._hover_probability)
        self.visual_tabs = ContentTabs()
        self.visual_tabs.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.visual_tabs.setUsesScrollButtons(True)
        self.visual_tabs.setElideMode(Qt.ElideRight)
        self.visual_tabs.addTab(self.canvas, "Esferas de Bloch")
        self.visual_tabs.addTab(self.probabilities_canvas, "Probabilidades no instante")
        self.state_inspector = StateInspector()
        self.visual_tabs.addTab(self.state_inspector, "Estado global")
        self.visual_tabs.currentChanged.connect(self._refresh_ui)
        self.visual_tabs.currentChanged.connect(self._visual_mode_changed)
        self.stage_splitter = QSplitter(Qt.Horizontal)
        self.stage_splitter.setChildrenCollapsible(False)
        self.stage_splitter.setHandleWidth(3)
        self.stage_splitter.addWidget(self.visual_tabs)
        self.inspector = QWidget()
        inspector_layout = QVBoxLayout(self.inspector)
        inspector_layout.setContentsMargins(8, 0, 0, 0)
        self.inspector_selector = QComboBox()
        self.inspector_selector.setAccessibleName("Conteúdo do inspetor da visualização")
        inspector_layout.addWidget(self.inspector_selector)
        self.inspector_tabs = ContentTabs()
        self.inspector_tabs.tabBar().hide()
        inspector_layout.addWidget(self.inspector_tabs, 1)
        self.inspector.setMinimumWidth(280)
        self.inspector.setMaximumWidth(430)
        self.camera_scroll = QScrollArea()
        self.camera_scroll.setWidgetResizable(True)
        self.camera_scroll.setMinimumWidth(235)

        self.camera_scroll.setWidget(self.camera_panel)
        self.inspector_tabs.addTab(self.camera_scroll, "Câmera e visualização")
        self.stage_splitter.addWidget(self.inspector)
        self.stage_splitter.setStretchFactor(0, 1)
        self.stage_splitter.setStretchFactor(1, 0)
        self.stage_splitter.setSizes([900, 320])
        layout.addWidget(self.stage_splitter, 1)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider)
        self.frame_label = QLabel()
        self.frame_label.setWordWrap(True)
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
        layout.addWidget(self.transport)
        self.timeline_detail = QPlainTextEdit()
        self.timeline_detail.setReadOnly(True)
        self.timeline_detail.setMinimumHeight(150)
        self.timeline_detail.setAccessibleName("Transformação e estados do snapshot")
        self.timeline_detail.setPlaceholderText("Carregue um experimento para inspecionar as etapas.")
        self.details_section = CollapsibleSection("Etapa, qubits e métricas", expanded=False)
        self.details_section.set_summary("Consulte a transformação, os estados locais e as métricas do instante selecionado.")
        self.details_section.expanded_changed.connect(lambda *_: self.preferences_changed.emit())
        self.details_section.content_layout.addWidget(self.timeline_detail)
        self._info_container = QWidget()
        QGridLayout(self._info_container)
        self._qubit_panels = []
        info_scroll = QScrollArea()
        self.info_scroll = info_scroll
        info_scroll.setWidgetResizable(True)
        info_scroll.setWidget(self._info_container)
        info_scroll.setFixedHeight(145)

        note = QLabel(
            "Pureza local baixa pode indicar correlações/emaranhamento: em Bell ideal, cada qubit tem pureza ½. A linha tracejada representa o mesmo circuito sem ruído."
        )
        note.setWordWrap(True)
        self.details_section.content_layout.addWidget(note)
        self.scene_note = note
        self.metrics = SnapshotMetrics()
        self.metrics.analyze_requested.connect(self.temporal_requested.emit)
        self.metrics.snapshot_selected.connect(self.slider.setValue)
        self.inspector_tabs.addTab(self.details_section, "Etape selecionada")
        self.inspector_tabs.setTabText(1, "Etapa selecionada")
        self.inspector_tabs.addTab(info_scroll, "Estados locais dos qubits")
        self.inspector_tabs.addTab(self.metrics, "Métricas temporais")
        info_scroll.setMinimumHeight(150)
        info_scroll.setMaximumHeight(16777215)
        for i in range(self.inspector_tabs.count()):
            self.inspector_selector.addItem(self.inspector_tabs.tabText(i))
        self.inspector_selector.currentIndexChanged.connect(self._inspector_changed)
        escape = QShortcut(QKeySequence("Esc"), self)
        escape.setContext(Qt.WidgetWithChildrenShortcut)
        escape.activated.connect(lambda: self.set_maximized(False))
        self._escape = escape
        self.body().addWidget(self._content, 1)
        self._content.hide()

    def refresh_theme(self):
        if hasattr(self, "camera_scroll"):
            self._camera_layout_timer.start()

    def _visual_mode_changed(self, index):
        global_state = self.visual_tabs.widget(index) is self.state_inspector
        self.inspector.setVisible(not self._maximized and self.camera_toggle.isChecked())
        self.camera_toggle.setVisible(not self._maximized)
        self.selection_label.setVisible(not global_state)
        self.maximize_button.setText("Restaurar painéis" if self._maximized else "Ampliar visualização")

    def _inspector_changed(self, index):
        self.inspector_tabs.setCurrentIndex(index)
        if index == 1:
            self.details_section.set_expanded(True, animate=False)
        self.preferences_changed.emit()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.FontChange, QEvent.StyleChange):
            self.refresh_theme()

    def _fit_camera(self):
        self.camera_panel.ensurePolished()
        width = max(235, self.camera_panel.minimumSizeHint().width()+24)
        self.camera_scroll.setMinimumWidth(width)
        self.inspector.setMinimumWidth(min(430, max(280, width + 8)))
        if self._camera_auto:
            self.camera_toggle.setChecked(self.width() >= 1100 * max(1, self.font().pixelSize() / 15))
        self._visual_mode_changed(self.visual_tabs.currentIndex())

    def _camera_chosen(self, *_):
        self._camera_auto = False
        self.preferences_changed.emit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_camera_layout_timer'):
            self._camera_layout_timer.start()

    def collect_view_preferences(self):
        return {'camera': 'auto' if self._camera_auto else self.camera_toggle.isChecked(),
                'details': self.details_section.is_expanded, 'inspector': self.inspector_selector.currentIndex()}

    def apply_view_preferences(self, mapping):
        mapping = mapping if isinstance(mapping, dict) else {}
        camera = mapping.get('camera', 'auto')
        self._camera_auto = type(camera) is not bool
        blockers = [QSignalBlocker(self.camera_toggle), QSignalBlocker(self.details_section)]
        self.camera_toggle.setChecked(camera if type(camera) is bool else True)
        self.details_section.set_expanded(mapping.get('details') is True, animate=False)
        del blockers
        index = mapping.get("inspector", 0)
        if type(index) is int and 0 <= index < self.inspector_tabs.count():
            blocker = QSignalBlocker(self.inspector_selector)
            self.inspector_selector.setCurrentIndex(index)
            self.inspector_tabs.setCurrentIndex(index)
            del blocker
        self.refresh_theme()

    def load_statevectors(
        self,
        statevectors,
        times=None,
        ideal_statevectors=None,
        time_unit="adimensional (ℏ=1)",
    ):
        self._pause()
        self._experiment = None
        self.final_only = False
        self.timeline_detail.clear()
        self.time_unit = time_unit
        self.metrics.clear("Índice da porta" if "porta" in time_unit else "Tempo (ℏ=1)")
        self.selection_label.setText("Clique numa esfera para selecionar")
        self.focus_selected.setEnabled(False)
        self.original_svs = list(statevectors or [])
        self.state_inspector.set_state(None)
        self.interpolated_svs = list(self.original_svs)
        self.precomputed_bloch = []
        self.ideal_bloch = []
        self.snapshot_probabilities = []
        self.ideal_probabilities = []
        self._probability_plot_key = None
        self._probability_bars = []
        self._probability_annotation = None
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
        canvas_blocker = QSignalBlocker(self.canvas)
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
            layout.addWidget(panel, q, 0)
            self._qubit_panels.append(panel)
        self.slider.blockSignals(True)
        self.slider.setMaximum(len(self.precomputed_bloch) - 1)
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.snapshot_spin.setRange(1, len(self.precomputed_bloch))
        self.current_frame = 0
        del canvas_blocker
        self.camera_panel.sync_from_camera()
        self._sync_focus(self.canvas.focus, persist=False)

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

    def _toggle_focus(self):
        self.canvas.set_focus(-1 if self.canvas.focus >= 0 else self.canvas.selected_qubit)

    def _sync_focus(self, index, persist=True):
        blocker = QSignalBlocker(self.focus_combo)
        self.focus_combo.setCurrentIndex(max(0, self.focus_combo.findData(index)))
        del blocker
        self._select_qubit(index)
        self._refresh_ui()
        if persist:
            self.preferences_changed.emit()

    def set_experiment(self, experiment):
        """Describe actual stored transitions, never interpolate invented states."""
        self._experiment = experiment
        final_only = not experiment.result.states and bool(self.original_svs)
        self.final_only = final_only
        for control in (self.btn_play, self.btn_prev, self.btn_next, self.btn_stop, self.slider, self.snapshot_spin, self.speed_combo, self.loop):
            control.setEnabled(not final_only)
        if final_only:
            self.frame_label.setText("Estado final · esta execução não armazenou etapas intermediárias")
            self.timeline_detail.setPlainText("Estado final calculado da execução selecionada. Não há snapshots intermediários armazenados; nenhuma trajetória é inferida.")
        else:
            self._render_timeline()

    @staticmethod
    def _state_description(state):
        data = np.asarray(state.data)
        if data.ndim == 1:
            values = np.array2string(data[:8], precision=8, suppress_small=True, max_line_width=100)
            return "ψ = " + values + (" … (primeiras 8 amplitudes)" if data.size > 8 else "")
        probabilities = np.real(np.diag(data))
        return (f"ρ: traço={np.trace(data).real:.12g}; Tr(ρ²)={np.trace(data @ data).real:.12g}; "
                + "diagonal=" + np.array2string(probabilities[:8], precision=8, suppress_small=True)
                + (" … (primeiras 8 probabilidades)" if data.shape[0] > 8 else ""))

    def _render_timeline(self):
        experiment = self._experiment
        if experiment is None or not self.original_svs:
            return
        if getattr(self, 'final_only', False):
            self.timeline_detail.setPlainText("Estado final calculado. Esta execução não armazenou etapas intermediárias; nenhuma trajetória é inferida.\n" + self._state_description(self.original_svs[0]))
            return
        index = self.current_frame
        config = experiment.config
        if index == 0:
            heading = ("Estado inicial |0…0⟩ com a fase global do circuito."
                       if config.circuit is not None else "Estado após a preparação, antes da evolução de Trotter.")
        elif config.circuit is not None and index <= len(config.circuit.gates):
            from core.circuit_document import GATE_HELP
            gate = config.circuit.gates[index - 1]
            heading = (f"Porta lógica {index}: {gate.name.upper()} · qubits "
                       + ", ".join(f"q{q}" for q in gate.qubits)
                       + (f" · parâmetros={gate.parameters!r} rad" if gate.parameters else "")
                       + "\n" + GATE_HELP[gate.name]
                       + "\nIdeal: |ψ′⟩=U|ψ⟩ ou ρ′=UρU†. Com ruído, canais são aplicados às operações nativas.")
        else:
            operations = [op for op in experiment.result.metadata.get("operations", [])
                          if op.get("stage") == "evolution" and op.get("step") == index]
            dt = config.protocol.total_time / config.protocol.trotter_steps
            heading = (f"Camada Suzuki–Trotter {index} · Δt={dt:.12g} (ℏ=1) · "
                       f"{len(operations)} operações nativas.\n"
                       "Ideal: |ψ′⟩=U_ST(Δt)|ψ⟩; com ruído, a camada inclui canais. "
                       "Os snapshots delimitam camadas completas; não há estados intermediários por porta.")
        rows = [heading]
        if index > 0:
            rows.append("Antes: " + self._state_description(self.original_svs[index - 1]))
        rows.append("Depois: " + self._state_description(self.original_svs[index]))
        if index > 0:
            delta = self.snapshot_probabilities[index] - self.snapshot_probabilities[index - 1]
            rows.append(f"Maior alteração absoluta de probabilidade: {np.max(np.abs(delta)):.12g}. "
                        "Valores mostrados são numéricos; snapshots completos podem ser exportados.")
        self.timeline_detail.setPlainText("\n".join(rows))

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
        if getattr(self, "final_only", False):
            self.frame_label.setText("Estado final · sem etapas intermediárias armazenadas")
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
            bars = ax.bar(
                positions - 0.18,
                probabilities,
                width=0.36,
                color=PALETTE.primary,
                label="Simulado",
            )
            self._probability_bars = [(bar, int(i), float(value), "Simulado")
                                      for bar, i, value in zip(bars, positions, probabilities)]
            if self.overlay.isChecked() and self.ideal_probabilities:
                bars = ax.bar(
                    positions + 0.18,
                    self.ideal_probabilities[idx],
                    width=0.36,
                    color=PALETTE.q2,
                    label="Circuito ideal",
                )
                self._probability_bars.extend((bar, int(i), float(value), "Circuito ideal")
                                              for bar, i, value in zip(bars, positions, self.ideal_probabilities[idx]))
            ax.set_xticks(
                positions,
                [format(i, f"0{self.num_qubits}b") for i in positions],
                rotation=90 if len(positions) > 8 else 0,
            )
            ax.set_ylim(0, 1.05)
            ax.set_ylabel("Probabilidade")
            ax.set_xlabel("Bitstring (q0 à direita)")
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
            self._probability_annotation = ax.annotate(
                "", xy=(0, 0), xytext=(10, 12), textcoords="offset points",
                bbox={"boxstyle": "round,pad=.5", "fc": PALETTE.surface, "ec": PALETTE.border_strong},
                color=PALETTE.text, zorder=20,
            )
            self._probability_annotation.set_visible(False)
            self.probabilities_canvas.draw_idle()
            self._probability_plot_key = plot_key
        self.metrics.select_snapshot(idx)
        self.state_inspector.set_state(
            self.original_svs[idx],
            self.ideal_states[idx] if self.ideal_states else None,
            f"Snapshot {idx + 1} de {len(self.original_svs)} · estado simulado",
        )
        self._render_timeline()
        self.frame_changed.emit(idx)

    def _hover_probability(self, event):
        annotation = self._probability_annotation
        if annotation is None:
            return
        visible = annotation.get_visible()
        if getattr(event, "inaxes", None) is annotation.axes:
            for bar, index, value, series in self._probability_bars:
                if bar.contains(event)[0]:
                    bitstring = format(index, f"0{self.num_qubits}b")
                    time = (f"\nCoordenada: {self.times[self.current_frame]:.17g} ({self.time_unit})"
                            if self.times is not None else "")
                    annotation.set_text(
                        f"{series} · |{bitstring}⟩\nProbabilidade: {value:.17g}\n"
                        f"Percentual: {100 * value:.17g}%\nSnapshot {self.current_frame + 1}" + time
                    )
                    annotation.xy = (bar.get_x() + bar.get_width() / 2, value)
                    annotation.set_visible(True)
                    self.probabilities_canvas.draw_idle()
                    return
        annotation.set_visible(False)
        if visible:
            self.probabilities_canvas.draw_idle()

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
        self.btn_play.setText("Reproduzir")

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
        self._header.setVisible(not enabled and not getattr(self, "_embedded_heading", False))
        self._visual_mode_changed(self.visual_tabs.currentIndex())

    def _select_qubit(self, index):
        valid = 0 <= index < len(self._qubit_panels)
        self.selection_label.setText(f"Qubit q{index} selecionado" if valid else "Clique numa esfera para selecionar")
        self.focus_selected.setText("Mostrar todos os qubits" if self.canvas.focus >= 0 else "Focar selecionado")
        self.focus_selected.setEnabled(valid or self.canvas.focus >= 0)
        self.canvas.select_qubit(index)
        for q, panel in enumerate(self._qubit_panels):
            panel.setStyleSheet(
                "border: 2px solid " + getattr(PALETTE, f"q{q + 1}") + ";"
                if q == index
                else ""
            )
        if valid:
            self.info_scroll.ensureWidgetVisible(self._qubit_panels[index])
