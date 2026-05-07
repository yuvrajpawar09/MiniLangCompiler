"""
utils.py
--------
Utility helpers and constants used across the MiniLang compiler.
"""

# ---------- Color theme constants for the dark GUI ---------- #
THEME = {
    "bg":            "#1e1e2e",   # main background
    "panel":         "#252535",   # panel background
    "panel_alt":     "#2d2d44",   # alternate panel background
    "fg":            "#e0e0e0",   # default foreground text
    "accent":        "#7aa2f7",   # accent (buttons, highlights)
    "accent_alt":    "#bb9af7",   # secondary accent
    "success":       "#9ece6a",   # success / OK colour
    "warn":          "#e0af68",   # warning colour
    "error":         "#f7768e",   # error colour
    "keyword":       "#bb9af7",   # syntax-highlight keywords
    "string":        "#9ece6a",   # syntax-highlight strings
    "number":        "#ff9e64",   # syntax-highlight numbers
    "comment":       "#565f89",   # syntax-highlight comments
    "operator":      "#89ddff",   # syntax-highlight operators
    "border":        "#414868",   # widget borders
    "select":        "#3b3b5c",   # selection highlight
}

# Font families used in the GUI
FONT_MONO = ("Consolas", 11)
FONT_MONO_SMALL = ("Consolas", 10)
FONT_UI = ("Segoe UI", 10)
FONT_UI_BOLD = ("Segoe UI", 10, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")


def is_number(text: str) -> bool:
    """Return True if `text` represents an integer literal."""
    if not text:
        return False
    if text[0] in "+-":
        text = text[1:]
    return text.isdigit()


def is_identifier_start(ch: str) -> bool:
    """A MiniLang identifier may start with a letter or underscore."""
    return ch.isalpha() or ch == "_"


def is_identifier_part(ch: str) -> bool:
    """Subsequent characters of an identifier may be letters, digits, '_'."""
    return ch.isalnum() or ch == "_"


def safe_int(text: str):
    """Attempt to coerce `text` to int – return None on failure."""
    try:
        return int(text)
    except (ValueError, TypeError):
        return None
