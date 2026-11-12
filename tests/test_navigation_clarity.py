"""A navegação mantém destinos legíveis e grupos independentes."""
from PySide6.QtTest import QSignalSpy

from gui.controllers.appearance import apply_appearance
from tests.qt_helpers import wait_until


def test_groups_start_open_and_navigation_preserves_independent_choices(window, qt_app):
    sidebar = window.sidebar
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())
    sidebar.group_buttons['resources'].click()
    wait_until(lambda: sidebar.group_bodies['resources'].isHidden())
    assert all(not sidebar.group_bodies[key].isHidden() for key in ('work',))
    window._show_page('comparison')
    assert sidebar.group_bodies['resources'].isHidden()
    assert not sidebar.group_bodies['work'].isHidden()
    window._show_page('examples')
    assert all(not body.isHidden() for body in sidebar.group_bodies.values())


def test_narrow_menu_preserves_visible_names_and_destinations(window, qt_app):
    sidebar = window.sidebar
    expected = dict(sidebar.ITEMS)
    full_width = sidebar.width()
    sidebar.set_compact(True)
    qt_app.processEvents()
    assert sidebar.width() < full_width
    assert sidebar.toggle.text() == 'Expandir menu'
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
    assert sidebar.toggle.text() == 'Recolher'


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
