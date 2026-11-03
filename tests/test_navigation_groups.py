from PySide6.QtCore import QSettings
from gui.main_window import MainWindow
from data.repository import ExperimentRepository


def test_groups_do_not_navigate_until_page_chosen(window):
    sidebar=window.sidebar
    before=window._current_page
    sidebar.group_buttons['research'].click()
    assert window._current_page==before
    assert not sidebar.group_bodies['research'].isHidden()
    assert sidebar.group_bodies['start'].isHidden()
    sidebar.buttons['comparison'].click()
    assert window._current_page=='comparison'
    assert sidebar.buttons['comparison'].isChecked()
    window._show_page('documentation')
    assert not sidebar.group_bodies['organize'].isHidden()
    assert sidebar.group_bodies['research'].isHidden()
    window._open_commands()
    window.command_palette.search.setText('estudos')
    from PySide6.QtCore import Qt
    assert any(window.command_palette.list.item(i).data(Qt.UserRole)=='page:analysis' for i in range(window.command_palette.list.count()))
    window.command_palette.close()


def test_compact_navigation_keeps_labels_and_group_selection(window):
    window._show_page('analysis')
    sidebar=window.sidebar
    sidebar.set_compact(True)
    assert sidebar.buttons['analysis'].accessibleName()=='Estudos científicos'
    assert not sidebar.buttons['analysis'].icon().isNull()
    assert not sidebar.group_bodies['research'].isHidden()
    sidebar.set_compact(False)
    assert 'Estudos científicos' in sidebar.buttons['analysis'].text()
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
