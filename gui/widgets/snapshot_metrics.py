"""Snapshot metrics and a discrete, synchronized temporal cursor."""

import numpy as np
from PySide6.QtCore import Signal, QSignalBlocker
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QToolButton,
    QWidget,
)
from gui.widgets.button import SecondaryButton
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE


class SnapshotMetrics(QFrame):
    analyze_requested = Signal()
    snapshot_selected = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.rows = []
        self.index = 0
        self.time_unit = "Tempo (ℏ=1)"
        self._marker = None
        self._busy = False
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        tools = QHBoxLayout()
        self.summary = QLabel(
            "Métricas do snapshot: calcule a análise para inspecionar."
        )
        self.summary.setWordWrap(True)
        tools.addWidget(self.summary, 1)
        self.calculate = SecondaryButton("Calcular métricas")
        self.calculate.clicked.connect(self.analyze_requested.emit)
        tools.addWidget(self.calculate)
        self.toggle = QToolButton()
        self.toggle.setText("Gráfico")
        self.toggle.setCheckable(True)
        tools.addWidget(self.toggle)
        root.addLayout(tools)
        self.chart = QWidget()
        body = QVBoxLayout(self.chart)
        body.setContentsMargins(0, 0, 0, 0)
        self.series = QComboBox()
        body.addWidget(self.series)
        self.canvas = MplCanvas(height=2)
        self.canvas.setMinimumHeight(170)
        body.addWidget(self.canvas)
        root.addWidget(self.chart)
        self.chart.hide()
        self.toggle.toggled.connect(self._toggle)
        self.series.currentIndexChanged.connect(self._plot)
        self.canvas.mpl_connect("button_press_event", self._clicked)

    def clear(self, time_unit):
        self.rows = []
        self.time_unit = time_unit
        self._marker = None
        self.series.clear()
        self.summary.setText(
            "Métricas do snapshot: calcule a análise para inspecionar."
        )
        self.toggle.setChecked(False)
        self.canvas.reset_axes()
        self.canvas.draw_idle()

    def set_busy(self, busy):
        self._busy = busy
        self.calculate.setEnabled(not busy)
        self.calculate.setText("Processando…" if busy else "Calcular métricas")

    def set_rows(self, rows):
        self.rows = list(rows)
        blocker = QSignalBlocker(self.series)
        self.series.clear()
        for name, key in [
            ("Fidelidade ao circuito ideal", "fidelity"),
            ("Pureza global", "purity"),
            ("Energia ⟨H⟩", "energy"),
        ]:
            if any(row.get(key) is not None for row in rows):
                self.series.addItem(name, key)
        del blocker
        self._plot()
        self.select_snapshot(self.index)
        self.toggle.setChecked(True)

    def select_snapshot(self, index):
        self.index = index
        if not self.rows or not 0 <= index < len(self.rows):
            return
        row = self.rows[index]

        def value(key):
            return "—" if row.get(key) is None else f"{row[key]:.6g}"

        self.summary.setText(
            f"Snapshot {index + 1} · F={value('fidelity')} · Pureza={value('purity')} · Energia={value('energy')}"
        )
        if self._marker is not None:
            self._marker.set_xdata([row["time"], row["time"]])
            self.canvas.draw_idle()

    def _plot(self, *_):
        if not self.rows:
            return
        key = self.series.currentData()
        if not key:
            return
        ax = self.canvas.reset_axes()
        ax.plot(
            [r["time"] for r in self.rows],
            [np.nan if r.get(key) is None else r[key] for r in self.rows],
            "o-",
            color=PALETTE.primary,
            markersize=3,
        )
        ax.set_xlabel(self.time_unit)
        ax.set_ylabel(self.series.currentText())
        index = min(self.index, len(self.rows) - 1)
        self._marker = ax.axvline(
            self.rows[index]["time"], color=PALETTE.q2, linestyle="--", linewidth=1
        )
        self.canvas.draw_idle()

    def _clicked(self, event):
        if self.rows and event.inaxes is not None and event.xdata is not None:
            index = min(
                range(len(self.rows)),
                key=lambda i: abs(self.rows[i]["time"] - event.xdata),
            )
            self.snapshot_selected.emit(index)

    def _toggle(self, opened):
        self.chart.setVisible(opened)
        if opened and not self.rows and not self._busy:
            self.analyze_requested.emit()
