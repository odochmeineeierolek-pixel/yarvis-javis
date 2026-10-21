"""Berechtigungslogik: nur registrierte Tools, Bestätigung für kritische Aktionen."""
from pathlib import Path
from urllib.parse import urlparse

# Diese Aktionen werden NIE ohne ausdrückliche Bestätigung des Masters ausgeführt.
CONFIRM_REQUIRED = {"delete_file", "send_message", "publish_listing", "buy", "pay", "install_software"}


def requires_confirmation(tool_name: str) -> bool:
    return tool_name in CONFIRM_REQUIRED


def is_safe_url(url: str) -> bool:
    try:
        return urlparse(url).scheme in {"http", "https"}
    except Exception:
        return False


def is_inside(path, roots) -> bool:
    """True, wenn path innerhalb eines erlaubten Verzeichnisses liegt (blockt ../-Tricks)."""
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
