"""Inspect an existing simulated state, with explicit basis and bipartition."""
import numpy as np
from PySide6.QtCore import Qt, QSignalBlocker
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                              QTabWidget, QTableWidget, QTableWidgetItem)
from core.state_inspection import inspect_state
from gui.widgets.plot_canvas import MplCanvas, style_axes
from gui.widgets.data_table import configure_table


class StateInspector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = self._ideal = None
        self._context = ""
        self._dirty = False
        self.quantities = None
        self._matrix_axes = []
        self._table_dirty = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        self.summary = QLabel("Nenhum estado disponível.")
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.PlainText)
        self.summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.summary)
        row = QHBoxLayout()
        self.partition_label = QLabel("Bipartição A | B")
        row.addWidget(self.partition_label)
        self.partition = QComboBox()
        self.partition.setAccessibleName("Bipartição do estado global")
        self.partition.setToolTip("Escolha os qubits do subsistema A. B contém os demais qubits; q0 é o bit à direita.")
        self.partition.currentIndexChanged.connect(self._partition_changed)
        row.addWidget(self.partition, 1)
        layout.addLayout(row)
        self.partition_summary = QLabel()
        self.partition_summary.setWordWrap(True)
        self.partition_summary.setTextFormat(Qt.PlainText)
        layout.addWidget(self.partition_summary)
        self.tabs = QTabWidget()
        self.canvas = MplCanvas(height=3)
        self.tabs.addTab(self.canvas, "Matriz densidade")
        self.matrix_table = QTableWidget()
        self.matrix_table.setEditTriggers(QTableWidget.NoEditTriggers)
        configure_table(self.matrix_table)
        self.tabs.addTab(self.matrix_table, "Valores de ρ")
        self.spectrum = QLabel()
        self.spectrum.setWordWrap(True)
        self.spectrum.setTextFormat(Qt.PlainText)
        self.spectrum.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.tabs.addTab(self.spectrum, "Espectro")
        self.tabs.currentChanged.connect(self._fill_current_detail)
        layout.addWidget(self.tabs, 1)
        note = QLabel("Estado calculado pelo simulador; não é tomografia experimental. Coerência ℓ₁ é a soma dos módulos fora da diagonal na base computacional. Negatividade zero não prova separabilidade em geral. Passe o mouse sobre as células para consultar os valores com mais precisão.")
        note.setWordWrap(True)
        note.setObjectName("FieldHint")
        layout.addWidget(note)
        self.canvas.set_value_lookup(self._matrix_value)

    def set_state(self, state, ideal=None, context=""):
        if state is self._state and ideal is self._ideal and context == self._context:
            return
        self._state, self._ideal, self._context = state, ideal, context
        self._dirty = True
        if self.isVisible():
            self._render()

    def showEvent(self, event):
        super().showEvent(event)
        if self._dirty:
            self._render()

    def _partition_changed(self):
        self._dirty = True
        if self.isVisible():
            self._render()

    def _render(self):
        self._dirty = False
        if self._state is None:
            self.quantities = None
            self.summary.setText("Nenhum estado disponível.")
            self.tabs.hide()
            self.partition.hide()
            self.partition_label.hide()
            self.partition_summary.clear()
            return
        try:
            n = self._state.num_qubits
            if self.partition.property("qubits") != n:
                blocker = QSignalBlocker(self.partition)
                self.partition.clear()
                if n and n > 1:
                    for mask in range(1, 2 ** n - 1):
                        # Keep both orientations: reduced purity of A and B
                        # may differ when the global state is mixed.
                        selected = tuple(q for q in range(n) if mask & (1 << q))
                        other = tuple(q for q in range(n) if q not in selected)
                        label = lambda qubits: ", ".join(f"q{q}" for q in qubits)
                        self.partition.addItem(label(selected) + " | " + label(other), selected)
                self.partition.setProperty("qubits", n)
                del blocker
            data = inspect_state(self._state, self._ideal, self.partition.currentData())
        except (ValueError, TypeError, AttributeError) as exc:
            self.quantities = None
            self.summary.setText("Não foi possível inspecionar o estado: " + str(exc))
            self.tabs.hide()
            self.partition.hide()
            self.partition_label.hide()
            self.partition_summary.clear()
            return
        self.quantities = data
        self.tabs.show()
        self.partition.setVisible(n > 1)
        self.partition_label.setVisible(n > 1)
        fidelity = f" · Fidelidade ao circuito ideal {data['fidelity']:.8g}" if data['fidelity'] is not None else ""
        self.summary.setText(self._context + "\n" + f"Pureza global {data['purity']:.8g} · Entropia global {data['entropy_bits']:.8g} bits\nCoerência ℓ₁ {data['coherence_l1']:.8g}" + fidelity)
        part = data['partition']
        self.partition_summary.setText((f"Pureza de A {part['purity_a']:.8g} · Entropia de A {part['entropy_a_bits']:.8g} bits\nNegatividade A|B {part['negativity']:.8g} · Informação mútua {part['mutual_information_bits']:.8g} bits") if part else "Um qubit não admite bipartição em subsistemas de qubits.")
        rho = data['density_matrix']
        dim = len(rho)
        labels = [format(i, f"0{n}b") for i in range(dim)]
        self._table_dirty = True
        self._fill_current_detail()
        self.spectrum.setText("Autovalores de ρ (ordem decrescente):\n" + "\n".join(f"λ{index + 1} = {value:.17g}" for index, value in enumerate(data['eigenvalues'])))
        self.canvas.fig.clear()
        self._matrix_axes = []
        limit = max(float(np.abs(rho.real).max()), float(np.abs(rho.imag).max()), 1e-15)
        for index, (values, title) in enumerate(((rho.real, "Re(ρ)"), (rho.imag, "Im(ρ)"))):
            ax = style_axes(self.canvas.fig.add_subplot(1, 2, index + 1))
            self._matrix_axes.append(ax)
            picture = ax.imshow(values, cmap="RdBu_r", vmin=-limit, vmax=limit, interpolation="nearest")
            ax.set_title(title)
            ax.set_xlabel("Coluna · estado computacional")
            ax.set_ylabel("Linha")
            step = max(1, dim // 8)
            ticks = list(range(0, dim, step))
            ax.set_xticks(ticks, [labels[i] for i in ticks], rotation=90)
            ax.set_yticks(ticks, [labels[i] for i in ticks])
            colorbar = self.canvas.fig.colorbar(picture, ax=ax)
            style_axes(colorbar.ax)
        self.canvas.draw_idle()

    def _fill_current_detail(self, *_):
        if not self.quantities or not self._table_dirty or self.tabs.currentWidget() is not self.matrix_table:
            return
        self._table_dirty = False
        rho = self.quantities['density_matrix']
        dim, n = len(rho), self.quantities['num_qubits']
        labels = [format(i, f"0{n}b") for i in range(dim)]
        self.matrix_table.setUpdatesEnabled(False)
        try:
            self.matrix_table.setRowCount(dim)
            self.matrix_table.setColumnCount(dim)
            self.matrix_table.setHorizontalHeaderLabels(labels)
            self.matrix_table.setVerticalHeaderLabels(labels)
            for i in range(dim):
                for j in range(dim):
                    value = complex(rho[i, j])
                    item = QTableWidgetItem(f"{value.real:.6g}{value.imag:+.6g}i")
                    item.setToolTip(f"ρ[{labels[i]}, {labels[j]}] = {value.real:.17g}{value.imag:+.17g}i")
                    self.matrix_table.setItem(i, j, item)
            self.matrix_table.resizeColumnsToContents()
        finally:
            self.matrix_table.setUpdatesEnabled(True)

    def _matrix_value(self, event):
        if event.inaxes not in self._matrix_axes or not self.quantities or event.xdata is None or event.ydata is None:
            return None
        rho = self.quantities['density_matrix']
        i, j = int(round(event.ydata)), int(round(event.xdata))
        if 0 <= i < len(rho) and 0 <= j < len(rho):
            value = complex(rho[i, j])
            return f"ρ[{i}, {j}] = {value.real:.17g}{value.imag:+.17g}i"
