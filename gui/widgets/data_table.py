"""Shared table behavior; scientific row order remains opt-in for sorting."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView, QTableWidgetItem, QMenu, QFileDialog, QMessageBox
import csv


class DataTableItem(QTableWidgetItem):
    """Sort numeric values and dates by their values, independent of presentation."""

    def __init__(self, text, sort_value=None):
        super().__init__(str(text))
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, DataTableItem) and self.sort_value is not None and other.sort_value is not None:
            return self.sort_value < other.sort_value
        return self.text().casefold() < other.text().casefold()


def table_row_height(table, density=None, font_size=None):
    """One density/typography rule shared by construction and appearance updates."""
    app = QApplication.instance()
    density = density or (app.property("entrelaDensity") if app else None) or "comfortable"
    if font_size is None:
        font = table.font()
        font_size = font.pixelSize()
        if font_size <= 0:
            font_size = font.pointSizeF() * table.logicalDpiY() / 72
    return max(28, round({"compact": 36, "comfortable": 44, "spacious": 52}.get(density, 44) * font_size / 15))


def configure_table(table, sortable=False, numeric_columns=()):
    """Apply consistent read-only table ergonomics without changing row semantics."""
    first_configuration = not bool(table.property("dataTable"))
    table.setProperty("dataTable", True)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    if first_configuration:
        table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(table_row_height(table))
    table.verticalHeader().setMinimumSectionSize(28)
    header = table.horizontalHeader()
    header.setMinimumSectionSize(72)
    # Reaplicar aparência não deve desfazer a distribuição definida pela página:
    # no histórico, o nome usa o espaço livre e Visualizar mantém sua largura.
    if first_configuration:
        header.setStretchLastSection(True)
        shortcut = QShortcut(QKeySequence(QKeySequence.Copy), table)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(lambda: copy_table(table))
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(lambda point: _menu(table, point))
    header.setHighlightSections(False)
    table.setSortingEnabled(sortable)
    for row in range(table.rowCount()):
        for column in numeric_columns:
            item = table.item(row, column)
            if item:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return table


def table_rows(table, selected=False):
    header_view = table.horizontalHeader()
    columns = [header_view.logicalIndex(i) for i in range(table.columnCount()) if not table.isColumnHidden(header_view.logicalIndex(i))]
    rows = sorted({index.row() for index in table.selectedIndexes()}) if selected else list(range(table.rowCount()))
    header = [table.horizontalHeaderItem(c).text() if table.horizontalHeaderItem(c) else '' for c in columns]
    return [header] + [[table.item(r, c).text() if table.item(r, c) else '' for c in columns] for r in rows]


def copy_table(table):
    rows = table_rows(table, selected=True)
    if len(rows) > 1:
        QApplication.clipboard().setText('\n'.join('\t'.join(row) for row in rows))


def _menu(table, point):
    menu = QMenu(table)
    copy = menu.addAction('Copiar linhas selecionadas', lambda: copy_table(table))
    copy.setEnabled(bool(table.selectedIndexes()))
    def export():
        path, _ = QFileDialog.getSaveFileName(table, 'Exportar a tabela exibida', 'tabela.csv', 'CSV (*.csv)')
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as stream:
                    csv.writer(stream).writerows(table_rows(table))
            except OSError as exc:
                QMessageBox.warning(table, 'Não foi possível exportar', f'Escolha uma pasta gravável e tente novamente.\n{exc}')
    menu.addAction('Exportar tabela exibida CSV…', export)
    menu.exec(table.viewport().mapToGlobal(point))
