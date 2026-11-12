from PySide6.QtCore import QSettings
from gui.main_window import MainWindow
from data.repository import ExperimentRepository


def test_groups_do_not_navigate_until_page_chosen(window):
    sidebar=window.sidebar
    before=window._current_page
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())
    sidebar.group_buttons['work'].click()
    assert window._current_page==before
    from tests.qt_helpers import wait_until
    wait_until(lambda: sidebar.group_bodies['work'].isHidden())
    assert not sidebar.group_bodies['resources'].isHidden()
    sidebar.buttons['analysis'].click()
    assert window._current_page=='analysis'
    assert sidebar.buttons['analysis'].isChecked()
    window._show_page('documentation')
    assert not sidebar.group_bodies['resources'].isHidden()
    assert not sidebar.group_bodies['work'].isHidden()
    window._open_commands()
    window.command_palette.search.setText('varreduras')
    from PySide6.QtCore import Qt
    assert any(window.command_palette.list.item(i).data(Qt.UserRole)=='page:analysis' for i in range(window.command_palette.list.count()))
    window.command_palette.close()


def test_compact_navigation_keeps_labels_and_group_selection(window):
    window._show_page('analysis')
    sidebar=window.sidebar
    sidebar.set_compact(True)
    assert sidebar.buttons['analysis'].accessibleName()=='Investigar'
    assert not sidebar.buttons['analysis'].icon().isNull()
    assert not sidebar.group_bodies['work'].isHidden()
    sidebar.set_compact(False)
    assert 'Investigar' in sidebar.buttons['analysis'].text()
    assert sidebar.buttons['analysis'].isChecked()


def test_readability_migrates_previous_default_once(qt_app,tmp_path):
    settings=QSettings(str(tmp_path/'old.ini'),QSettings.IniFormat)
    settings.setValue('appearance/font',13)
    first=MainWindow(ExperimentRepository(tmp_path/'runs'),settings)
    assert first.page_settings.font_size.value()==15
    first.page_settings.font_size.setValue(13)
    first.close()
    second=MainWindow(ExperimentRepository(tmp_path/'runs'),settings)
    assert second.page_settings.font_size.value()==13
    second.close()
