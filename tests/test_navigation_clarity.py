"""A navegação mantém destinos legíveis e grupos independentes."""
from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest

from gui.controllers.appearance import apply_appearance
from tests.qt_helpers import wait_until


def test_groups_start_open_and_navigation_preserves_independent_choices(window, qt_app):
    sidebar = window.sidebar
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())
    assert all(not header.icon().isNull() for header in sidebar.group_buttons.values())
    sidebar.group_buttons['records'].click()
    wait_until(lambda: sidebar.group_bodies['records'].isHidden())
    expanded = window.settings.value('layout/sidebar_sections')
    assert 'records' not in expanded and 'observe' in expanded
    assert all(not sidebar.group_bodies[key].isHidden() for key in ('lab', 'research'))
    window._show_page('comparison')
    assert sidebar.group_bodies['records'].isHidden()
    assert not sidebar.group_bodies['research'].isHidden()
    window._show_page('examples')
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())


def test_narrow_menu_preserves_visible_names_and_destinations(window, qt_app):
    sidebar = window.sidebar
    expected = dict(sidebar.ITEMS)
    full_width = sidebar.width()
    sidebar.set_compact(True)
    qt_app.processEvents()
    assert sidebar.width() < full_width
    assert 'Expandir navegação' == sidebar.toggle.accessibleName()
    for page, button in sidebar.buttons.items():
        assert ' '.join(button.text().split()) == expected[page]
        assert not button.icon().isNull()
    requested = QSignalSpy(sidebar.navigate)
    sidebar.buttons['simulation'].click()
    assert requested.count() == 1 and requested.at(0) == ['simulation']
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())
    sidebar.set_compact(False)
    assert all(button.text() == expected[key] for key, button in sidebar.buttons.items())
    assert sidebar.toggle.accessibleName() == 'Recolher navegação'


def test_navigation_stays_readable_after_theme_font_and_width_changes(window, qt_app):
    try:
        for theme, size in [('dark',15),('light',24),('dark',15)]:
            apply_appearance(window, theme, size)
            window.resize(1024,768)
            for _ in range(4):
                qt_app.processEvents()
            sidebar = window.sidebar
            assert sidebar.scroll.horizontalScrollBar().maximum() == 0
            for button in sidebar.buttons.values():
                available = button.width()-button.iconSize().width()-26
                assert all(button.fontMetrics().horizontalAdvance(line) <= available for line in button.text().splitlines())
                assert button.height() >= len(button.text().splitlines())*button.fontMetrics().height()
    finally:
        apply_appearance(window)



def test_group_focus_remains_clear_after_folding_the_active_section(window, qt_app):
    sidebar = window.sidebar
    window._show_page("simulation")
    prepare = sidebar.group_buttons["lab"]
    explore = sidebar.group_buttons["observe"]
    sidebar._focus_row(prepare)
    QTest.keyClick(prepare, Qt.Key_Left)
    assert sidebar.group_bodies["lab"].isHidden()
    assert prepare.property("activeSection")
    assert prepare.accessibleDescription() == "Área atual: Simulação"
    assert window.is_page_active("simulation")

    QTest.keyClick(prepare, Qt.Key_Down)
    assert qt_app.focusWidget() is explore
    QTest.keyClick(explore, Qt.Key_Right)
    assert qt_app.focusWidget() is sidebar.buttons["results"]
    QTest.keyClick(sidebar.buttons["results"], Qt.Key_Left)
    assert qt_app.focusWidget() is explore
    assert window.is_page_active("simulation")
