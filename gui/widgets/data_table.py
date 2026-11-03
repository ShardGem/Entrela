"""Shared table behavior; scientific row order remains opt-in for sorting."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView, QTableWidgetItem


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
    table.setProperty("dataTable", True)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(table_row_height(table))
    table.verticalHeader().setMinimumSectionSize(28)
    header = table.horizontalHeader()
    header.setMinimumSectionSize(72)
    header.setStretchLastSection(True)
    header.setHighlightSections(False)
    table.setSortingEnabled(sortable)
    for row in range(table.rowCount()):
        for column in numeric_columns:
            item = table.item(row, column)
            if item:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return table
