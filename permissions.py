"""Berechtigungslogik: nur registrierte Tools, Rechte-Kategorien, Bestätigung für kritische Aktionen."""
from pathlib import Path
from urllib.parse import urlparse

# Diese Aktionen werden NIE ohne ausdrückliche Bestätigung des Masters ausgeführt.
CONFIRM_REQUIRED = {"delete_file", "send_message", "publish_listing", "buy", "pay", "install_software",
                    "shutdown_pc", "restart_pc", "close_app"}

ALLOWED_HOTKEYS = {"win+d", "alt+tab", "win+tab", "ctrl+c", "ctrl+v", "ctrl+x", "ctrl+z", "ctrl+y", "ctrl+a",
                   "ctrl+s", "ctrl+t", "ctrl+w", "ctrl+n", "ctrl+f", "ctrl+l", "ctrl+shift+t", "f5", "f11",
                   "win+up", "win+down", "win+left", "win+right", "enter", "esc", "space", "win+shift+s",
                   "printscreen", "ctrl+plus", "ctrl+minus"}


def requires_confirmation(tool_name: str) -> bool:
    return tool_name in CONFIRM_REQUIRED


def tool_enabled(tool, name, settings) -> bool:
    return bool(settings["perms"].get(tool.cat, False)) and name not in settings["disabled_tools"]


def app_allowed(key: str, settings) -> bool:
    if settings["app_mode"] == "allowlist":
        return key in settings["allowed_apps"]
    return key not in settings["blocked_apps"]


def is_safe_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in {"http", "https"}
    except Exception:
        return False


def is_inside(path, roots) -> bool:
    try:
        p = Path(path).resolve()
    except Exception:
        return False
    for r in roots:
        try:
            p.relative_to(Path(r).resolve())
            return True
        except ValueError:
            continue
    return False
