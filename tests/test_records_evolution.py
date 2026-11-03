"""Regression cases for identity-safe catalogue actions and comparison lifecycle."""
from dataclasses import replace

import pytest
from PySide6.QtCore import Qt

from core.examples import create_example_config
from core.simulation import run_experiment
from core.comparison import prepare_comparison
from data.workspace import WorkspaceLibrary
from gui.pages.history import HistoryPage
from gui.pages.comparison import ComparisonPage
from gui.pages.library import LibraryPage
from tests.qt_helpers import wait_until


@pytest.fixture
def experiment():
    return run_experiment(replace(create_example_config("bell"), shots=32, seed=17))


def test_annotations_extend_without_mutating_results_or_erasing_planning(qt_app, tmp_path, experiment):
    library = WorkspaceLibrary(tmp_path)
    library.annotate(experiment.id, "TCC", "Primeira nota", ["Bell"], title="Controle", description="Referência ideal", objective="Avaliar ruído", hypothesis="F cai", methodology="Manter circuito", categories=["ruído", "ruído"])
    library.annotate(experiment.id, "TCC", "Atualizada", ["controle"])
    saved = library.read()["annotations"][experiment.id]
    assert saved["title"] == "Controle"
    assert saved["objective"] == "Avaliar ruído"
    assert saved["categories"] == ["ruído"]
    page = LibraryPage()
    page.load(library.read(), experiment.id)
    assert page.annotation_payload()["methodology"] == "Manter circuito"
    page.close()


def test_sorted_history_buttons_target_actual_record_and_reject_stale_details(qt_app, experiment):
    other = replace(experiment, id="other-experiment")
    page = HistoryPage()
    page.annotations = {experiment.id: {"title": "Zeta"}, other.id: {"title": "Alfa"}}
    page.load([experiment, other])
    page.table.sortItems(1, Qt.AscendingOrder)
    selected = []
    page.detail_requested.connect(selected.append)
    page.table.cellWidget(0, 9).click()
    assert selected == [other.id]
    assert page.selected_identifier == other.id
    assert page.detail_title.text() == "Alfa"
    opened = []
    page.experiment_selected.connect(opened.append)
    page._open(0, 1)
    assert opened == [other.id]
    page.set_detail(experiment)
    assert page.detail_title.text() == "Alfa"
    assert experiment.id not in page.summary.toPlainText()
    page.status_filter.setCurrentIndex(3)
    assert page.table.rowCount() == 0
    assert "Nenhum" in page.page_label.text()
    page.close()


def test_comparison_tabs_lazy_load_and_clear_previous_scientific_results(qt_app, experiment):
    other = replace(experiment, id="other-experiment")
    page = ComparisonPage()
    page.load([experiment, other])
    requested = []
    page.prepare_requested.connect(lambda a,b: requested.append((a,b)))
    assert all(page.tabs.isTabEnabled(i) for i in (1,2,4))
    page.tabs.setCurrentIndex(1)
    wait_until(lambda: bool(requested))
    assert requested == [(experiment.id, other.id)]
    page.set_full_data(prepare_comparison([experiment, other]))
    assert page.full_data is not None
    assert page.curve_canvas.fig.axes[0].lines
    # Changing the pair to an incompatible identical selection removes stale curves.
    page.second_run.setCurrentIndex(0)
    assert page.full_data is None
    assert not any(axis.lines for axis in page.curve_canvas.fig.axes)
    assert not page.btn_prepare.isEnabled()
    assert "diferentes" in page.message.text()
    assert "Nenhuma" not in page.observable_canvas.fig.axes[0].texts[0].get_text()
    page.close()


def test_zne_tab_explains_absence_instead_of_disabling(qt_app, experiment):
    page = ComparisonPage()
    page.load([experiment, replace(experiment, id="repeat")])
    page.tabs.setCurrentIndex(4)
    assert page.tabs.currentIndex() == 4
    assert "Nenhuma das execuções contém" in page.observable_canvas.fig.axes[0].texts[0].get_text()
    page.close()


def test_comparison_preferences_restore_without_preloading_and_retain_focus(qt_app, experiment):
    page = ComparisonPage()
    other = replace(experiment, id="repeat")
    page.load([experiment, other])
    requested = []
    page.prepare_requested.connect(lambda *args: requested.append(args))
    preferences = {"hist_layout": 1, "tab": 2, "camera_sync": False, "focus": 1}
    page.apply_view_preferences(preferences)
    qt_app.processEvents()
    assert not requested
    assert page.collect_view_preferences() == preferences
    page.set_full_data(prepare_comparison([experiment, other]))
    assert page.focus.currentData() == 1
    assert all(scene.focus == 1 for scene in page.scenes)
    page.close()


def test_shared_table_row_height_scales_with_typography(qt_app):
    from PySide6.QtWidgets import QTableWidget
    from gui.widgets.data_table import configure_table, table_row_height
    table = QTableWidget()
    font = table.font()
    font.setPixelSize(24)
    table.setFont(font)
    configure_table(table)
    assert table.verticalHeader().defaultSectionSize() == table_row_height(table)
    assert table_row_height(table, "comfortable", 24) == 70
    assert table_row_height(table, "spacious", 24) > table_row_height(table, "compact", 24)
    table.close()


def test_history_primary_columns_and_view_action_fit_small_desktop(window, experiment, qt_app):
    page = window.page_history
    page.load([experiment])
    window._show_page("history")
    window.resize(1024, 768)
    qt_app.processEvents()
    assert page.table.columnWidth(1) >= 180
    action_rect = page.table.visualRect(page.table.model().index(0, 9))
    assert action_rect.right() <= page.table.viewport().width()
    assert page.table.horizontalScrollBar().maximum() == 0
    assert page.table.isColumnHidden(4)
    page.column_actions[4].setChecked(True)
    assert not page.table.isColumnHidden(4)


def test_history_sort_orders_all_pages_before_pagination(qt_app, experiment):
    page = HistoryPage()
    records = [replace(experiment, id=f"run-{index}") for index in range(105)]
    page.annotations = {record.id: {"title": f"Nome {104-index:03}"} for index,record in enumerate(records)}
    page.load(records)
    page.table.sortItems(1, Qt.AscendingOrder)
    assert page.table.item(0, 1).text() == "Nome 000"
    assert page.table.item(99, 1).text() == "Nome 099"
    page.next.click()
    assert page.table.item(0, 1).text() == "Nome 100"
    assert page.table.rowCount() == 5
    page.close()
