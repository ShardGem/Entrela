"""Perfis visuais da interface, independentes dos parâmetros científicos."""

from dataclasses import asdict

from gui.theme import Palette

DARK = asdict(Palette())
LIGHT = {
    **DARK,
    "bg": "#f4f4f4", "bg_elevated": "#ffffff", "surface": "#e8e8e8",
    "surface_hover": "#e0e0e0", "surface_active": "#d0e2ff",
    "border": "#c6c6c6", "border_strong": "#6f6f6f",
    "primary": "#0f62fe", "primary_hover": "#0353e9", "primary_pressed": "#002d9c",
    "primary_muted": "#d0e2ff", "primary_faint": "#edf5ff",
    "primary_on": "#ffffff", "text_on_primary": "#ffffff",
    "text": "#161616", "text_muted": "#393939", "text_dim": "#525252",
    "success": "#11763f", "success_bg": "#e0f4e8",
    "warning": "#925400", "warning_bg": "#fff0ce",
    "danger": "#bb293e", "danger_bg": "#ffe7eb",
    "info": "#1b6f94", "info_bg": "#e0f0f6",
    "q1": "#1b6f94", "q2": "#7043c5", "q3": "#11763f",
    "q4": "#925400", "q5": "#bb293e", "q6": "#2258bc",
}
NAVY = {
    **DARK,
    "bg": "#101823", "bg_elevated": "#172332", "surface": "#203045",
    "surface_hover": "#263c55", "surface_active": "#2c4763",
    "border": "#30435a", "border_strong": "#6684a2",
    "text": "#EAF6FA", "text_muted": "#b9cfd9", "text_dim": "#9FBAC8",
    "primary": "#88D1E8", "primary_hover": "#b2e4f2", "primary_pressed": "#69b8d1",
    "primary_muted": "#244762", "primary_faint": "#1e354c",
    "primary_on": "#0b202b", "text_on_primary": "#0b202b",
    "action_bg": "#88D1E8", "action_hover": "#b2e4f2", "action_pressed": "#69b8d1", "action_on": "#0b202b",
    "info": "#88D1E8", "info_bg": "#203c49", "q1": "#88D1E8", "q2": "#a9a7df",
    "q3": "#91bbce", "q4": "#d6bf95",
}

THEMES = {"dark": DARK, "light": LIGHT, "navy": NAVY}
THEME_CHOICES = (
    ("Grafite", "dark"),
    ("Claro científico", "light"),
    ("Azul Entrela · padrão", "navy"),
    ("Automático · acompanhar o sistema", "auto"),
)
THEME_DESCRIPTIONS = {
    "dark": "Grafite: superfícies neutras, painéis contínuos e azul para destacar ações, foco e seleção.",
    "light": "Claro científico: fundo claro e destaque azul para leitura de parâmetros, tabelas e resultados.",
    "navy": "Azul Entrela: superfícies azul-marinho foscas e ciano suave para destacar a ação principal.",
    "auto": "Automático: alterna entre Grafite e Claro científico conforme a aparência do sistema operacional.",
}
