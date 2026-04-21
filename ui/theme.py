"""Color + font constants. Call apply_mode('dark'|'light') to switch."""

_LIGHT = dict(
    BG="#F5F5F5", CARD="#FFFFFF", PRIMARY="#1565C0",
    SUCCESS="#2E7D32", WARNING="#F57F17", ERROR="#C62828",
    PENDING="#9E9E9E", RUNNING="#1976D2",
    TEXT="#212121", TEXT_SUB="#757575",
    LOG_BG="#1E1E1E", LOG_FG="#D4D4D4",
    ENTRY_BG="#FFFFFF", ENTRY_FG="#212121",
    HEADER_BG="#1565C0", HEADER_FG="#FFFFFF",
)
_DARK = dict(
    BG="#1E1E2E", CARD="#2A2A3E", PRIMARY="#5C7AEA",
    SUCCESS="#4CAF50", WARNING="#FFA726", ERROR="#EF5350",
    PENDING="#616161", RUNNING="#42A5F5",
    TEXT="#E0E0E0", TEXT_SUB="#9E9E9E",
    LOG_BG="#121212", LOG_FG="#CCCCCC",
    ENTRY_BG="#2C2C3E", ENTRY_FG="#E0E0E0",
    HEADER_BG="#0D1117", HEADER_FG="#E0E0E0",
)

_mode = "light"
_c = dict(_LIGHT)


def apply_mode(mode: str) -> None:
    global _mode, _c
    _mode = mode
    _c = dict(_DARK if mode == "dark" else _LIGHT)


def is_dark() -> bool:
    return _mode == "dark"


# Accessors (always reflect current mode)
def BG()         -> str: return _c["BG"]
def CARD()       -> str: return _c["CARD"]
def PRIMARY()    -> str: return _c["PRIMARY"]
def SUCCESS()    -> str: return _c["SUCCESS"]
def WARNING()    -> str: return _c["WARNING"]
def ERROR()      -> str: return _c["ERROR"]
def PENDING()    -> str: return _c["PENDING"]
def RUNNING()    -> str: return _c["RUNNING"]
def TEXT()       -> str: return _c["TEXT"]
def TEXT_SUB()   -> str: return _c["TEXT_SUB"]
def LOG_BG()     -> str: return _c["LOG_BG"]
def LOG_FG()     -> str: return _c["LOG_FG"]
def ENTRY_BG()   -> str: return _c["ENTRY_BG"]
def ENTRY_FG()   -> str: return _c["ENTRY_FG"]
def HEADER_BG()  -> str: return _c["HEADER_BG"]
def HEADER_FG()  -> str: return _c["HEADER_FG"]

FONT_TITLE  = ("Segoe UI", 14, "bold")
FONT_LABEL  = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_MONO   = ("Consolas", 9)
FONT_SMALL  = ("Segoe UI", 8)

STATUS_COLORS = {
    "pending":  "#9E9E9E",
    "running":  "#1976D2",
    "done":     "#2E7D32",
    "failed":   "#C62828",
}
STATUS_ICONS = {
    "pending":  "○",
    "running":  "►",
    "done":     "✓",
    "failed":   "✗",
}
