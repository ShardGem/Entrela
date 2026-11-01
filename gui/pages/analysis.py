"""Scientific tools operate on the selected run, preserving its result."""

import csv, json
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QComboBox,
    QLineEdit,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
)
from gui.pages.base import PageBase
from gui.widgets.button import PrimaryButton, SecondaryButton
from gui.widgets.plot_canvas import MplCanvas
from gui.theme import PALETTE


class AnalysisPage(PageBase):
    requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(
            "Análises científicas",
            "Separe ruído, aproximação numérica e amostragem.",
            parent,
        )
        self.experiment = None
        self.data = None
        self.series = []
        self._running = False
        self.context = QLabel("Abra uma execução para começar.")
        self.context.setWordWrap(True)
        self.body().addWidget(self.context)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.form = form
        self.kind = QComboBox()
        for name, key in [
            ("Métricas temporais e correlações", "temporal"),
            ("Convergência Suzuki–Trotter", "convergence"),
            ("Varredura de parâmetros", "sweep"),
        ]:
            self.kind.addItem(name, key)
        self.parameter = QComboBox()
        self.parameter.addItems(
            ["p1", "p2", "J", "h", "t1_us", "t2_us", "trotter_steps"]
        )
        self.values = QLineEdit("0, 0.01, 0.03, 0.05, 0.1")
        self.values.setPlaceholderText("Valores separados por vírgula; ponto decimal")
        self.steps = QLineEdit("1, 2, 4, 8, 16")
        self.seeds = QLineEdit("")
        self.seeds.setPlaceholderText(
            "Vazio: seed efetiva da fonte; até 5 seeds separadas por vírgula"
        )
        for label, w in [
            ("Análise", self.kind),
            ("Parâmetro da varredura", self.parameter),
            ("Valores da varredura", self.values),
            ("Sementes da varredura", self.seeds),
            ("Passos para convergência", self.steps),
        ]:
            form.addRow(label, w)
        self.body().addLayout(form)
        self.saved = QComboBox()
        self.saved.addItem("Análises salvas desta execução", None)
        self.saved.currentIndexChanged.connect(self._open_saved)
        self.body().addWidget(self.saved)
        self.btn_run = PrimaryButton("Calcular análise")
        self.btn_run.clicked.connect(self._request)
        self.body().addWidget(self.btn_run)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.body().addWidget(self.message)
        self.series_combo = QComboBox()
        self.series_combo.currentIndexChanged.connect(self._plot)
        self.body().addWidget(self.series_combo)
        self.canvas = MplCanvas(height=3)
        self.canvas.setMinimumHeight(260)
        self.body().addWidget(self.canvas)
        self.canvas.mpl_connect("button_press_event", self._plot_clicked)
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(180)
        self.table.cellClicked.connect(self._select)
        self.body().addWidget(self.table)
        self.export_button = SecondaryButton("Exportar CSV / JSON")
        self.export_button.clicked.connect(self._export)
        self.export_button.setEnabled(False)
        self.add_action(self.export_button)
        self.kind.currentIndexChanged.connect(self._update_controls)
        self._update_controls()
        self.set_running(False)

    def _update_controls(self, *_):
        kind = self.kind.currentData()
        for w in (self.parameter, self.values, self.seeds):
            self.form.setRowVisible(w, kind == "sweep")
        self.form.setRowVisible(self.steps, kind == "convergence")

    def load_experiment(self, experiment):
        self.experiment = experiment
        self.data = None
        self.table.setRowCount(0)
        self.series_combo.clear()
        self.canvas.reset_axes()
        self.canvas.draw_idle()
        self.context.setText("Fonte: " + experiment.id + " · configuração preservada")
        self.message.clear()
        self.export_button.setEnabled(False)
        self.set_running(self._running)

    def set_saved(self, paths):
        self.saved.blockSignals(True)
        self.saved.clear()
        self.saved.addItem("Análises salvas desta execução", None)
        for label, path in paths:
            self.saved.addItem(label, str(path))
        self.saved.blockSignals(False)

    def _open_saved(self, *_):
        path = self.saved.currentData()
        if not path:
            return
        try:
            from pathlib import Path

            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if (
                data.get("source_id") != self.experiment.id
                or data.get("kind") not in ("temporal", "convergence", "sweep")
                or not data.get("rows")
            ):
                raise ValueError("Análise incompatível com esta execução.")
            self.show_analysis(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.message.setText("Não foi possível abrir a análise: " + str(exc))

    def _plot_clicked(self, event):
        if (
            self.data
            and self.data["kind"] == "temporal"
            and event.inaxes
            and event.xdata is not None
        ):
            row = min(
                range(len(self.data["rows"])),
                key=lambda i: abs(self.data["rows"][i]["time"] - event.xdata),
            )
            self.table.selectRow(row)
            self.parent_window_frame(row)

    def _request(self):
        try:
            kind = self.kind.currentData()
            options = {}
            if kind == "convergence":
                options = {
                    "steps": [int(x.strip()) for x in self.steps.text().split(",")]
                }
            elif kind == "sweep":
                options = {
                    "parameter": self.parameter.currentText(),
                    "values": [float(x.strip()) for x in self.values.text().split(",")],
                    "seeds": [int(x.strip()) for x in self.seeds.text().split(",")]
                    if self.seeds.text().strip()
                    else None,
                }
            self.requested.emit(kind, options)
        except ValueError:
            self.message.setText(
                "Revise os valores: use vírgula entre pontos e ponto como separador decimal."
            )

    def show_analysis(self, data):
        self.data = data
        rows = data["rows"]
        self.message.setText(data["note"])
        self.table.setColumnCount(len(rows[0]))
        self.table.setHorizontalHeaderLabels([field_label(key) for key in rows[0]])
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row.values()):
                self.table.setItem(
                    i,
                    j,
                    QTableWidgetItem(
                        "—"
                        if value is None
                        else (
                            format(value, ".9g")
                            if isinstance(value, float)
                            else str(value)
                        )
                    ),
                )
        self.series_combo.blockSignals(True)
        self.series_combo.clear()
        self.series = [
            k
            for k, v in rows[0].items()
            if isinstance(v, (int, float))
            and k not in ("snapshot", "time", "steps", "order", "value", "seed")
        ]
        for key in self.series:
            self.series_combo.addItem(field_label(key), key)
            self.series_combo.blockSignals(False)
            self._plot()
            self.export_button.setEnabled(True)

    def _plot(self, *_):
        if not self.data:
            return
        rows = self.data["rows"]
        key = self.series_combo.currentData()
        if not key:
            return
        xkey = {"temporal": "time", "convergence": "steps", "sweep": "value"}[
            self.data["kind"]
        ]
        ax = self.canvas.reset_axes()
        if self.data["kind"] == "sweep":
            for seed in sorted(set(row["seed"] for row in rows)):
                selected = [r for r in rows if r["seed"] == seed]
                ax.plot(
                    [r[xkey] for r in selected],
                    [r[key] for r in selected],
                    "o-",
                    label=f"seed {seed}",
                    alpha=0.8,
                )
            ax.legend(facecolor=PALETTE.surface, labelcolor=PALETTE.text)
        else:
            ax.plot(
                [r[xkey] for r in rows],
                [np_nan(r.get(key)) for r in rows],
                "o-",
                color=PALETTE.primary,
            )
        ax.set_xlabel(field_label(xkey))
        ax.set_ylabel(field_label(key))
        self.canvas.draw_idle()

    def _select(self, row, column):
        if self.data and self.data["kind"] == "temporal":
            self.parent_window_frame(row)

    def parent_window_frame(self, row):
        window = self.window()
        if hasattr(window, "page_bloch"):
            window.page_bloch.slider.setValue(row)

    def select_frame(self, row):
        if (
            self.data
            and self.data["kind"] == "temporal"
            and row < self.table.rowCount()
        ):
            self.table.selectRow(row)

    def _export(self):
        if not self.data:
            return
        path, kind = QFileDialog.getSaveFileName(
            self, "Exportar análise", "analise.csv", "CSV (*.csv);;JSON (*.json)"
        )
        if not path:
            return
        try:
            if "JSON" in kind:
                from pathlib import Path

                Path(path).write_text(
                    json.dumps(
                        self.data, ensure_ascii=False, indent=2, allow_nan=False
                    ),
                    encoding="utf-8",
                )
            else:
                with open(path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=list(self.data["rows"][0]))
                    writer.writeheader()
                    writer.writerows(self.data["rows"])
            self.message.setText("Análise exportada.")
        except OSError as exc:
            self.message.setText(str(exc))

    def set_running(self, running):
        self._running = running
        for w in (
            self.kind,
            self.parameter,
            self.values,
            self.steps,
            self.seeds,
            self.btn_run,
        ):
            w.setEnabled(self.experiment is not None and not running)
        self.btn_run.setText("Calculando…" if running else "Calcular análise")


def np_nan(value):
    return float("nan") if value is None else value


def field_label(key):
    if key.startswith("entropy_q"):
        return "Entropia de q" + key.removeprefix("entropy_q") + " (bits)"
    return {
        "snapshot": "Snapshot",
        "time": "Tempo (ℏ=1)",
        "fidelity": "Fidelidade ao circuito ideal",
        "purity": "Pureza global",
        "energy": "Energia ⟨H⟩",
        "fidelity_exact": "Fidelidade à evolução exata",
        "trotter_infidelity": "Erro de Trotter (1−F ideal/exato)",
        "negativity_q0_rest": "Negatividade q0 | resto",
        "steps": "Passos Trotter",
        "infidelity": "Infidelidade à evolução exata",
        "depth": "Profundidade",
        "order": "Ordem Suzuki",
        "seed": "Semente",
        "sampled_Z0": "⟨Z0⟩ amostrado",
        "value": "Valor do parâmetro",
    }.get(key, key)
