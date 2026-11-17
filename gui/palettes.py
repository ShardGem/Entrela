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
    "bg": "#0c1524", "bg_elevated": "#121f32", "surface": "#1a2a40",
    "surface_hover": "#21344d", "surface_active": "#29415b",
    "border": "#2c405a", "border_strong": "#637f9e",
    "text": "#e5eef9", "text_muted": "#adc0d7", "text_dim": "#9fb5cf",
    "primary": "#86baff", "primary_hover": "#b0d2ff", "primary_pressed": "#659fea",
    "primary_muted": "#203750", "primary_faint": "#203750",
    "info": "#86baff", "info_bg": "#203750", "q1": "#86baff",
}

THEMES = {"dark": DARK, "light": LIGHT, "navy": NAVY}
THEME_CHOICES = (
    ("Grafite · padrão Entrela", "dark"),
    ("Claro científico", "light"),
    ("Azul escuro", "navy"),
    ("Automático · acompanhar o sistema", "auto"),
)
THEME_DESCRIPTIONS = {
    "dark": "Grafite: superfícies neutras, painéis contínuos e azul para destacar ações, foco e seleção.",
    "light": "Claro científico: fundo claro e destaque azul para leitura de parâmetros, tabelas e resultados.",
    "navy": "Azul escuro: superfícies azuladas e destaque azul suave para explorar circuitos e visualizações.",
    "auto": "Automático: alterna entre Grafite e Claro científico conforme a aparência do sistema operacional.",
}
