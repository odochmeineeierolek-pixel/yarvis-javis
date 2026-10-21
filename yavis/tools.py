"""Registrierte Werkzeuge. Keine freie Shell – nur diese Funktionen kann YAVIS ausführen."""
import difflib, os, time, webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

from .config import NOTES_DIR
from .permissions import is_safe_url

SITES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com",
    "github": "https://github.com", "netflix": "https://www.netflix.com",
    "twitch": "https://www.twitch.tv", "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.de", "ebay": "https://www.ebay.de",
    "kleinanzeigen": "https://www.kleinanzeigen.de", "gmail": "https://mail.google.com",
    "maps": "https://maps.google.com", "wikipedia": "https://de.wikipedia.org",
    "chatgpt": "https://chatgpt.com", "claude": "https://claude.ai",
}


def _start_menu_dirs():
    dirs = []
    for env in ("ProgramData", "APPDATA"):
        base = os.environ.get(env)
        if base:
            dirs.append(Path(base) / "Microsoft/Windows/Start Menu/Programs")
    return dirs


_index_cache = {"t": 0, "items": {}}


def app_index(force=False):
    """Alle Startmenü-Verknüpfungen (Programme, Steam-Spiele usw.): Name -> Pfad."""
    if not force and time.time() - _index_cache["t"] < 600 and _index_cache["items"]:
        return _index_cache["items"]
    items = {}
    for d in _start_menu_dirs():
        if d.exists():
            for p in d.rglob("*"):
                if p.suffix.lower() in (".lnk", ".url", ".exe"):
                    items[p.stem.lower()] = str(p)
    _index_cache.update(t=time.time(), items=items)
    return items


def match_app(name: str, items: dict):
    name = name.lower().strip()
    if name in items:
        return name
    for key in items:
        if name in key:
            return key
    close = difflib.get_close_matches(name, list(items), n=1, cutoff=0.6)
    return close[0] if close else None


def open_app(name: str) -> str:
    items = app_index()
    key = match_app(name, items)
    if not key:
        return f"Programm '{name}' nicht gefunden."
    os.startfile(items[key])  # nur Windows
    return f"'{key}' gestartet."


def open_website(target: str) -> str:
    t = target.strip()
    key = t.lower()
    if key in SITES:
        url = SITES[key]
    elif t.startswith(("http://", "https://")):
        url = t
    elif "." in t and " " not in t:
        url = "https://" + t
    else:
        url = "https://www.google.com/search?q=" + quote_plus(t)
    if not is_safe_url(url):
        return "Unsichere Adresse blockiert."
    webbrowser.open(url)
    return f"Geöffnet: {url}"


def web_search(query: str) -> str:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as d:
            res = list(d.text(query, region="de-de", max_results=5))
    except Exception as e:
        return f"Websuche nicht verfügbar: {e}"
    if not res:
        return "Keine Treffer."
    return "\n".join(f"- {r['title']}: {r['body'][:200]} (Quelle: {r['href']})" for r in res)


def search_files(name: str) -> str:
    roots = [Path.home() / n for n in ("Desktop", "Documents", "Downloads", "Pictures", "Videos")]
    found, q = [], name.lower()
    for r in roots:
        if not r.exists():
            continue
        for dp, _, fs in os.walk(r):
            for f in fs:
                if q in f.lower():
                    found.append(os.path.join(dp, f))
                    if len(found) >= 15:
                        return "\n".join(found)
    return "\n".join(found) if found else "Nichts gefunden."


def get_time() -> str:
    return datetime.now().strftime("%A, %d.%m.%Y, %H:%M Uhr")


def write_note(title: str, text: str) -> str:
    safe = "".join(c for c in title if c.isalnum() or c in " -_")[:60].strip() or "Notiz"
    path = NOTES_DIR / f"{safe}.txt"
    path.write_text(text, encoding="utf-8")
    return f"Notiz gespeichert: {path}"


def build_registry(memory):
    """name -> (funktion, Beschreibung). Nur diese Werkzeuge existieren für die KI."""
    return {
        "get_time": (lambda: get_time(), "Aktuelle Uhrzeit/Datum. Argumente: {}"),
        "open_app": (open_app, "Programm oder Spiel starten. Argumente: {\"name\": \"...\"}"),
        "open_website": (open_website, "Website im Browser öffnen, z.B. youtube. Argumente: {\"target\": \"...\"}"),
        "web_search": (web_search, "Websuche mit Quellen. Argumente: {\"query\": \"...\"}"),
        "search_files": (search_files, "Dateien in Desktop/Dokumente/Downloads suchen. Argumente: {\"name\": \"...\"}"),
        "write_note": (write_note, "Notiz speichern. Argumente: {\"title\": \"...\", \"text\": \"...\"}"),
        "remember": (lambda text: f"Gemerkt (#{memory.add(text)}).", "Info dauerhaft merken (nur wenn der Master es will). Argumente: {\"text\": \"...\"}"),
        "recall": (lambda query: "\n".join(t for _, t in memory.search(query)) or "Nichts gefunden.", "Im Gedächtnis suchen. Argumente: {\"query\": \"...\"}"),
    }
