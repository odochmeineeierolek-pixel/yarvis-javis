"""Alle Werkzeuge von YAVIS. Nur registrierte Funktionen sind aufrufbar – keine freie Shell."""
import ast, difflib, math, operator, os, random, re, subprocess, sys, time, webbrowser
from collections import namedtuple
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, quote_plus

from .config import NOTES_DIR, DRAFTS_DIR, VOICE_PRESETS
from .permissions import is_safe_url, is_inside, app_allowed, ALLOWED_HOTKEYS

Tool = namedtuple("Tool", "func args desc cat")

SITES = {
    "youtube": "https://www.youtube.com", "google": "https://www.google.com", "github": "https://github.com",
    "netflix": "https://www.netflix.com", "twitch": "https://www.twitch.tv", "spotify": "https://open.spotify.com",
    "amazon": "https://www.amazon.de", "ebay": "https://www.ebay.de", "kleinanzeigen": "https://www.kleinanzeigen.de",
    "gmail": "https://mail.google.com", "maps": "https://maps.google.com", "wikipedia": "https://de.wikipedia.org",
    "chatgpt": "https://chatgpt.com", "claude": "https://claude.ai", "instagram": "https://www.instagram.com",
    "tiktok": "https://www.tiktok.com", "facebook": "https://www.facebook.com", "whatsapp": "https://web.whatsapp.com",
    "discord": "https://discord.com/app", "reddit": "https://www.reddit.com", "paypal": "https://www.paypal.com",
    "disney plus": "https://www.disneyplus.com", "prime video": "https://www.primevideo.com",
}
SYSTEM_TOOLS = {"rechner": "calc.exe", "taschenrechner": "calc.exe", "editor": "notepad.exe", "notepad": "notepad.exe",
                "explorer": "explorer.exe", "paint": "mspaint.exe", "aufgabenmanager": "taskmgr.exe",
                "snipping tool": "snippingtool.exe", "einstellungen": "ms-settings:"}
WIN_SETTINGS = {"wlan": "ms-settings:network-wifi", "bluetooth": "ms-settings:bluetooth", "sound": "ms-settings:sound",
                "anzeige": "ms-settings:display", "apps": "ms-settings:appsfeatures", "update": "ms-settings:windowsupdate",
                "datenschutz": "ms-settings:privacy", "akku": "ms-settings:batterysaver", "mikrofon": "ms-settings:privacy-microphone"}
FOLDER_ALIASES = {"downloads": "Downloads", "desktop": "Desktop", "schreibtisch": "Desktop", "dokumente": "Documents",
                  "bilder": "Pictures", "musik": "Music", "videos": "Videos"}
MUSIC_EXT = (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".wma", ".aac")
TEXT_EXT = (".txt", ".md", ".csv", ".json", ".log", ".py", ".html", ".xml", ".ini")
MEDIA_KEYS = {"playpause": 0xB3, "next": 0xB0, "prev": 0xB1, "stop": 0xB2, "vol_up": 0xAF, "vol_down": 0xAE, "mute": 0xAD}
JUNK = ("uninstall", "deinstall", "readme", "release notes", "license", "lizenz")


# ---------- Hilfsfunktionen (ohne Windows testbar) ----------
def _start_menu_dirs():
    return [Path(os.environ[e]) / "Microsoft/Windows/Start Menu/Programs" for e in ("ProgramData", "APPDATA") if os.environ.get(e)]


_cache = {"t": 0, "items": {}}


def app_index(force=False):
    """Startmenü-Verknüpfungen (Programme + Spiele): Name -> Pfad."""
    if not force and time.time() - _cache["t"] < 600 and _cache["items"]:
        return _cache["items"]
    items = {}
    for d in _start_menu_dirs():
        if d.exists():
            for p in d.rglob("*"):
                if p.suffix.lower() in (".lnk", ".url", ".exe") and not any(j in p.stem.lower() for j in JUNK):
                    items[p.stem.lower()] = str(p)
    _cache.update(t=time.time(), items=items)
    return items


def match_name(name, names, cutoff=0.6):
    name = name.lower().strip()
    if name in names:
        return name
    for k in names:
        if name in k:
            return k
    close = difflib.get_close_matches(name, list(names), n=1, cutoff=cutoff)
    return close[0] if close else None


def scan_music(folders, limit=5000):
    out = []
    for f in folders:
        for dp, _, fs in os.walk(f):
            for n in fs:
                if n.lower().endswith(MUSIC_EXT):
                    out.append(os.path.join(dp, n))
                    if len(out) >= limit:
                        return out
    return out


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.Mod: operator.mod, ast.USub: operator.neg, ast.FloorDiv: operator.floordiv}


def safe_calc(expr: str):
    expr = expr.lower().replace(",", ".").replace("×", "*").replace("÷", "/").replace("^", "**")
    expr = re.sub(r"\bmal\b", "*", expr)
    expr = re.sub(r"\bgeteilt durch\b", "/", expr)
    expr = re.sub(r"\bplus\b", "+", expr)
    expr = re.sub(r"\bminus\b", "-", expr)

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            a, b = ev(n.left), ev(n.right)
            if isinstance(n.op, ast.Pow) and abs(b) > 100:
                raise ValueError("Exponent zu groß")
            return _OPS[type(n.op)](a, b)
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            return _OPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("sqrt", "abs", "round"):
            return {"sqrt": math.sqrt, "abs": abs, "round": round}[n.func.id](*[ev(a) for a in n.args])
        raise ValueError("Nicht erlaubt")
    return ev(ast.parse(expr.strip(), mode="eval").body)


def parse_time_hhmm(s):
    m = re.match(r"^(\d{1,2})[:.](\d{2})$", s.strip())
    if not m or int(m[1]) > 23 or int(m[2]) > 59:
        raise ValueError("Zeit bitte als HH:MM")
    now = datetime.now()
    t = now.replace(hour=int(m[1]), minute=int(m[2]), second=0, microsecond=0)
    return (t if t > now else t + timedelta(days=1)).timestamp()


class Ctx:
    """Gemeinsamer Zustand für alle Werkzeuge."""
    def __init__(self, settings, memory, music=None):
        self.s, self.memory, self.music = settings, memory, music
        self.runner = None          # wird vom Brain gesetzt (für Routinen)
        self.granted = set()        # Dateien, die der Master selbst ausgewählt hat

    def roots(self):
        return [Path(f) for f in self.s["folders"]] + [NOTES_DIR, DRAFTS_DIR]


def _ok_path(ctx, p):
    return str(p) in ctx.granted or is_inside(p, ctx.roots())


def build_registry(ctx):
    R, s, mem = {}, ctx.s, ctx.memory

    def tool(cat, args, desc):
        def deco(f):
            R[f.__name__] = Tool(f, args, desc, cat)
            return f
        return deco

    # ===== System =====
    @tool("system", "", "Aktuelle Uhrzeit und Datum")
    def get_time():
        return datetime.now().strftime("%A, %d.%m.%Y, %H:%M Uhr")

    @tool("system", "", "CPU, RAM, Festplatte, Akku")
    def system_info():
        import psutil
        r = f"CPU {psutil.cpu_percent(0.3):.0f}%, RAM {psutil.virtual_memory().percent:.0f}%, " \
            f"Festplatte {psutil.disk_usage(os.path.abspath(os.sep)).percent:.0f}% belegt"
        b = psutil.sensors_battery()
        return r + (f", Akku {b.percent:.0f}%" + (" (lädt)" if b.power_plugged else "") if b else "")

    @tool("system", "action", "Medientasten: playpause,next,prev,stop,vol_up,vol_down,mute (vol 5 Stufen)")
    def media_key(action, times=1):
        if action not in MEDIA_KEYS:
            return "Unbekannte Taste."
        import ctypes
        n = 5 if action.startswith("vol") and int(times) == 1 else int(times)
        for _ in range(min(n, 20)):
            ctypes.windll.user32.keybd_event(MEDIA_KEYS[action], 0, 0, 0)
            ctypes.windll.user32.keybd_event(MEDIA_KEYS[action], 0, 2, 0)
        return "Erledigt."

    @tool("system", "", "Screenshot in Bilder/YAVIS speichern")
    def screenshot():
        from PIL import ImageGrab
        d = Path.home() / "Pictures" / "YAVIS"
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"screenshot_{datetime.now():%Y%m%d_%H%M%S}.png"
        ImageGrab.grab().save(p)
        return f"Screenshot gespeichert: {p}"

    @tool("system", "", "Bildschirm sperren")
    def lock_screen():
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return "Bildschirm gesperrt."

    @tool("system", "", "PC herunterfahren (30 s Verzögerung, braucht Bestätigung)")
    def shutdown_pc():
        subprocess.run(["shutdown", "/s", "/t", "30"], creationflags=0x08000000)
        return "Fährt in 30 Sekunden herunter."

    @tool("system", "", "PC neu starten (30 s Verzögerung, braucht Bestätigung)")
    def restart_pc():
        subprocess.run(["shutdown", "/r", "/t", "30"], creationflags=0x08000000)
        return "Startet in 30 Sekunden neu."

    @tool("system", "", "Herunterfahren/Neustart abbrechen")
    def cancel_shutdown():
        subprocess.run(["shutdown", "/a"], creationflags=0x08000000)
        return "Abgebrochen."

    @tool("system", "name", "Windows-Werkzeug öffnen: rechner, editor, explorer, paint, aufgabenmanager, snipping tool, einstellungen")
    def open_system_tool(name):
        k = match_name(name, SYSTEM_TOOLS)
        if not k:
            return "Unbekanntes Werkzeug."
        os.startfile(SYSTEM_TOOLS[k])
        return f"{k} geöffnet."

    @tool("system", "name", "Windows-Einstellungsseite öffnen: wlan, bluetooth, sound, anzeige, apps, update, datenschutz, akku, mikrofon")
    def open_windows_setting(name):
        k = match_name(name, WIN_SETTINGS)
        if not k:
            return "Unbekannte Einstellung."
        os.startfile(WIN_SETTINGS[k])
        return f"Einstellungen '{k}' geöffnet."

    @tool("system", "name", "Stimme wechseln (z.B. Mama, Butler, Held, Frau, Mann, Österreicher)")
    def switch_voice(name):
        low = name.lower()
        key = next((k for k in VOICE_PRESETS if low in k.lower()), None)
        if not key:
            m = difflib.get_close_matches(low, [k.lower() for k in VOICE_PRESETS], n=1, cutoff=0.4)
            key = next((k for k in VOICE_PRESETS if m and k.lower() == m[0]), None)
        if key not in VOICE_PRESETS:
            return "Diese Stimme gibt es nicht. Verfügbar: " + ", ".join(VOICE_PRESETS)
        s["voice"] = key
        s.save()
        return f"Stimme gewechselt: {key}"

    @tool("system", "on", "Neutralmodus an/aus (on=true: keine Gefühle)")
    def set_neutral_mode(on):
        s["neutral"] = str(on).lower() in ("true", "1", "ja", "an", "on")
        s.save()
        return "Neutralmodus " + ("an." if s["neutral"] else "aus.")

    # ===== Programme =====
    @tool("apps", "name", "Programm oder Spiel starten")
    def open_app(name):
        items = app_index()
        key = match_name(name, items)
        if not key:
            return f"Programm '{name}' nicht gefunden."
        if not app_allowed(key, s):
            return f"'{key}' ist in den Einstellungen nicht freigegeben."
        os.startfile(items[key])
        return f"'{key}' gestartet."

    @tool("apps", "name", "Laufendes Programm beenden (braucht Bestätigung)")
    def close_app(name):
        import psutil
        n = 0
        for p in psutil.process_iter(["name"]):
            pn = (p.info["name"] or "").lower()
            if name.lower().replace(" ", "") in pn.replace(" ", "") and pn not in ("explorer.exe", "yavis.exe", "system"):
                try:
                    p.terminate()
                    n += 1
                except Exception:
                    pass
        return f"{n} Prozess(e) beendet." if n else "Nichts gefunden."

    @tool("apps", "", "Laufende Programme (Top 10)")
    def list_running_apps():
        import psutil
        seen = {}
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                seen[p.info["name"]] = seen.get(p.info["name"], 0) + p.info["memory_info"].rss
            except Exception:
                pass
        return ", ".join(n for n, _ in sorted(seen.items(), key=lambda x: -x[1])[:10])

    # ===== Internet =====
    def _web(url):
        if not is_safe_url(url):
            return "Unsichere Adresse blockiert."
        webbrowser.open(url)
        return f"Geöffnet: {url}"

    @tool("web", "target", "Website öffnen (youtube, github, netflix … oder Adresse/Suchbegriff)")
    def open_website(target):
        t, k = target.strip(), target.strip().lower()
        if k in SITES:
            return _web(SITES[k])
        if t.startswith(("http://", "https://")):
            return _web(t)
        if "." in t and " " not in t:
            return _web("https://" + t)
        return _web("https://www.google.com/search?q=" + quote_plus(t))

    @tool("web", "query", "YouTube-Suche im Browser öffnen")
    def youtube_search(query):
        return _web("https://www.youtube.com/results?search_query=" + quote_plus(query))

    @tool("web", "query", "Ort/Route auf Google Maps")
    def maps_search(query):
        return _web("https://www.google.com/maps/search/" + quote_plus(query))

    @tool("web", "query", "Websuche mit Quellen (Preise, Fakten, Aktuelles)")
    def web_search(query):
        try:
            from duckduckgo_search import DDGS
            with DDGS() as d:
                res = list(d.text(query, region="de-de", max_results=5))
        except Exception as e:
            return f"Websuche nicht verfügbar: {e}"
        return "\n".join(f"- {r['title']}: {r['body'][:200]} (Quelle: {r['href']})" for r in res) or "Keine Treffer."

    @tool("web", "query", "Aktuelle Nachrichten (query optional)")
    def news(query=""):
        try:
            from duckduckgo_search import DDGS
            with DDGS() as d:
                res = list(d.news(query or "Nachrichten Deutschland", region="de-de", max_results=5))
        except Exception as e:
            return f"Nachrichten nicht verfügbar: {e}"
        return "\n".join(f"- {r['title']} ({r.get('source', '')}, {r['url']})" for r in res) or "Keine Treffer."

    @tool("web", "city", "Wetter (city optional, sonst Standardort)")
    def weather(city=""):
        import requests
        c = city or s["city"]
        try:
            r = requests.get(f"https://wttr.in/{quote(c)}?format=%C,+%t,+gefühlt+%f,+Wind+%w&lang=de", timeout=8)
            return f"{c}: {r.text.strip()}"
        except Exception as e:
            return f"Wetter nicht verfügbar: {e}"

    @tool("web", "topic", "Kurzinfo aus Wikipedia")
    def wikipedia(topic):
        import requests
        try:
            o = requests.get("https://de.wikipedia.org/w/api.php", timeout=8, params={
                "action": "opensearch", "search": topic, "limit": 1, "format": "json"}).json()
            if not o[1]:
                return "Nichts gefunden."
            r = requests.get("https://de.wikipedia.org/api/rest_v1/page/summary/" + quote(o[1][0].replace(" ", "_")), timeout=8).json()
            return f"{r.get('title')}: {r.get('extract', '')[:600]} (Quelle: {o[3][0]})"
        except Exception as e:
            return f"Wikipedia nicht verfügbar: {e}"

    # ===== Alltag / Rechnen =====
    @tool("tasks", "expression", "Rechnen, z.B. 12*7+3 oder sqrt(81)")
    def calculate(expression):
        try:
            v = safe_calc(expression)
            return str(round(v, 6) if isinstance(v, float) else v)
        except Exception as e:
            return f"Kann ich nicht berechnen ({e})."

    @tool("tasks", "date", "Tage bis zu einem Datum (TT.MM.JJJJ)")
    def days_until(date):
        try:
            d = datetime.strptime(date.strip(), "%d.%m.%Y").date()
        except ValueError:
            return "Datum bitte als TT.MM.JJJJ."
        return f"{(d - datetime.now().date()).days} Tage."

    @tool("tasks", "min,max", "Zufallszahl")
    def random_number(min=1, max=100):
        return str(random.randint(int(min), int(max)))

    @tool("tasks", "sides,count", "Würfeln")
    def roll_dice(sides=6, count=1):
        return ", ".join(str(random.randint(1, max(2, int(sides)))) for _ in range(min(int(count), 10)))

    @tool("tasks", "", "Münzwurf")
    def flip_coin():
        return random.choice(["Kopf", "Zahl"])

    @tool("tasks", "seconds,label", "Timer stellen (Sekunden)")
    def set_timer(seconds, label="Timer"):
        mem.add_reminder(f"{label} ist abgelaufen", time.time() + float(seconds))
        return f"Timer läuft: {int(float(seconds))} Sekunden."

    @tool("tasks", "text,minutes,at", "Erinnerung in N Minuten ODER um HH:MM")
    def set_reminder(text, minutes=None, at=None):
        try:
            due = parse_time_hhmm(at) if at else time.time() + float(minutes) * 60
        except Exception as e:
            return f"Fehler: {e}"
        mem.add_reminder(text, due)
        return f"Erinnerung gesetzt: {text} ({datetime.fromtimestamp(due):%H:%M} Uhr)."

    @tool("tasks", "", "Offene Erinnerungen")
    def list_reminders():
        r = mem.reminders()
        return "\n".join(f"{datetime.fromtimestamp(d):%d.%m. %H:%M} – {t}" for _, t, d in r) or "Keine Erinnerungen."

    @tool("tasks", "", "Alle offenen Erinnerungen löschen")
    def cancel_reminders():
        mem.clear_reminders()
        return "Erinnerungen gelöscht."

    @tool("tasks", "text", "Aufgabe hinzufügen")
    def add_task(text):
        mem.add_task(text)
        return "Aufgabe notiert."

    @tool("tasks", "", "Offene Aufgaben")
    def list_tasks():
        return "\n".join(f"- {t}" for _, t, _ in mem.tasks()) or "Keine offenen Aufgaben."

    @tool("tasks", "text", "Aufgabe als erledigt markieren")
    def complete_task(text):
        return f"{mem.complete_task(text)} Aufgabe(n) erledigt."

    @tool("tasks", "title,text", "Notiz speichern")
    def write_note(title, text):
        safe = "".join(c for c in title if c.isalnum() or c in " -_")[:60].strip() or "Notiz"
        (NOTES_DIR / f"{safe}.txt").write_text(text, encoding="utf-8")
        return f"Notiz '{safe}' gespeichert."

    @tool("tasks", "title", "Notiz lesen")
    def read_note(title):
        names = {p.stem.lower(): p for p in NOTES_DIR.glob("*.txt")}
        k = match_name(title, names)
        return names[k].read_text(encoding="utf-8")[:3000] if k else "Notiz nicht gefunden."

    @tool("tasks", "", "Alle Notizen auflisten")
    def list_notes():
        return ", ".join(p.stem for p in NOTES_DIR.glob("*.txt")) or "Keine Notizen."

    @tool("tasks", "query", "In Notizen suchen")
    def search_notes(query):
        hits = [p.stem for p in NOTES_DIR.glob("*.txt") if query.lower() in p.read_text(encoding="utf-8", errors="ignore").lower() or query.lower() in p.stem.lower()]
        return ", ".join(hits) or "Nichts gefunden."

    @tool("tasks", "title,text", "Entwurf speichern (Angebot, Produktbeschreibung, Mail …)")
    def save_draft(title, text):
        safe = "".join(c for c in title if c.isalnum() or c in " -_")[:60].strip() or "Entwurf"
        (DRAFTS_DIR / f"{safe}.txt").write_text(text, encoding="utf-8")
        return f"Entwurf '{safe}' gespeichert (nichts wurde veröffentlicht oder gesendet)."

    @tool("tasks", "name", "Routine ausführen (Folge von Aktionen)")
    def run_routine(name):
        for _, n, trig, steps, _ in mem.routines():
            if name.lower() in (n.lower(), trig):
                out = [f"{st['tool']}: {ctx.runner(st['tool'], st.get('args', {}))}" for st in steps] if ctx.runner else []
                return f"Routine '{n}' fertig. " + " | ".join(out)
        return "Routine nicht gefunden."

    @tool("tasks", "", "Tagesüberblick: Zeit, Wetter, Aufgaben, Erinnerungen")
    def daily_briefing():
        r = [get_time(), weather() if s["perms"].get("web") else "", "Aufgaben: " + list_tasks(), "Erinnerungen: " + list_reminders()]
        return "\n".join(x for x in r if x)

    # ===== Dateien =====
    @tool("files", "name", "Dateien nach Name suchen")
    def search_files(name):
        found, q = [], name.lower()
        for r in ctx.roots():
            if not r.exists():
                continue
            for dp, _, fs in os.walk(r):
                for f in fs:
                    if q in f.lower():
                        found.append(os.path.join(dp, f))
                        if len(found) >= 15:
                            return "\n".join(found)
        return "\n".join(found) or "Nichts gefunden."

    @tool("files", "name", "Datei öffnen (Name oder Pfad, nur in freigegebenen Ordnern)")
    def open_file(name):
        p = Path(name)
        if not p.exists():
            hits = search_files(name).split("\n")
            p = Path(hits[0]) if hits and hits[0] and Path(hits[0]).exists() else p
        if not p.exists() or not _ok_path(ctx, p):
            return "Datei nicht gefunden oder nicht freigegeben."
        os.startfile(str(p))
        return f"Geöffnet: {p.name}"

    @tool("files", "name", "Ordner öffnen: downloads, desktop, dokumente, bilder, musik, videos")
    def open_folder(name):
        k = FOLDER_ALIASES.get(name.lower().strip())
        p = Path.home() / k if k else Path(name)
        if not p.exists() or not _ok_path(ctx, p):
            return "Ordner nicht gefunden oder nicht freigegeben."
        os.startfile(str(p))
        return f"Ordner {p.name} geöffnet."

    @tool("files", "name", "Inhalt eines Ordners auflisten")
    def list_dir(name):
        k = FOLDER_ALIASES.get(name.lower().strip())
        p = Path.home() / k if k else Path(name)
        if not p.is_dir() or not _ok_path(ctx, p):
            return "Ordner nicht gefunden oder nicht freigegeben."
        return ", ".join(sorted(x.name for x in p.iterdir())[:40]) or "Leer."

    @tool("files", "path", "Textdatei lesen (txt, md, csv, json …) zum Zusammenfassen")
    def read_text_file(path):
        p = Path(path)
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT or not _ok_path(ctx, p):
            return "Datei nicht lesbar oder nicht freigegeben."
        return p.read_text(encoding="utf-8", errors="ignore")[:4000]

    # ===== Zwischenablage / Steuerung =====
    @tool("clipboard", "", "Zwischenablage lesen")
    def clipboard_read():
        import pyperclip
        return pyperclip.paste()[:2000] or "Leer."

    @tool("clipboard", "text", "Text in die Zwischenablage kopieren")
    def clipboard_write(text):
        import pyperclip
        pyperclip.copy(text)
        return "Kopiert."

    @tool("control", "keys", "Tastenkombination drücken (nur erlaubte, z.B. win+d, alt+tab, ctrl+s)")
    def press_hotkey(keys):
        k = keys.lower().replace(" ", "").replace("windows", "win").replace("strg", "ctrl")
        if k not in ALLOWED_HOTKEYS:
            return "Diese Tastenkombination ist nicht erlaubt."
        import pyautogui
        pyautogui.hotkey(*[{"plus": "+", "minus": "-"}.get(x, x) for x in k.split("+")])
        return "Gedrückt."

    @tool("control", "text", "Text in das aktive Fenster tippen")
    def type_text(text):
        import pyautogui, pyperclip
        old = pyperclip.paste()
        pyperclip.copy(text[:2000])
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyperclip.copy(old)
        return "Getippt."

    # ===== Musik =====
    @tool("music", "query", "Musik abspielen (Titel/Künstler aus der Bibliothek; leer = Zufallsmix)")
    def play_music(query=""):
        lib = ctx.music.library() if ctx.music else []
        if not lib:
            return "Keine Musik gefunden. Bitte Musikordner unter Musik/Einstellungen hinzufügen."
        if query.strip():
            q = query.lower()
            hits = [p for p in lib if q in p.lower()]
            if not hits:
                names = {Path(p).stem.lower(): p for p in lib}
                k = match_name(query, names, 0.5)
                hits = [names[k]] if k else []
            if not hits:
                return f"Nichts zu '{query}' in deiner Musik gefunden."
            ctx.music.send("playlist", "\n".join(hits[:200]))
            return f"Spiele {Path(hits[0]).stem}."
        mix = random.sample(lib, min(len(lib), 200))
        ctx.music.send("playlist", "\n".join(mix))
        return "Spiele deinen Musikmix."

    for nm, cmd, d in (("pause_music", "pause", "Musik pausieren"), ("resume_music", "resume", "Musik fortsetzen"),
                       ("next_track", "next", "Nächstes Lied"), ("prev_track", "prev", "Vorheriges Lied"),
                       ("stop_music", "stop", "Musik stoppen")):
        def mk(cmd=cmd, nm=nm):
            def f():
                if not ctx.music:
                    return "Kein Musikplayer."
                ctx.music.send(cmd, "")
                return "Okay."
            f.__name__ = nm
            return f
        R[nm] = Tool(mk(), "", d, "music")

    @tool("music", "percent", "Musiklautstärke 0-100")
    def music_volume(percent):
        v = max(0, min(100, int(float(percent))))
        s["music_volume"] = v
        ctx.music.send("volume", str(v))
        return f"Musiklautstärke {v}%."

    @tool("music", "", "Was läuft gerade?")
    def music_status():
        return ctx.music.status() if ctx.music else "Kein Musikplayer."

    # ===== Gedächtnis =====
    @tool("memory", "text", "Etwas dauerhaft merken (nur wenn der Master es will)")
    def remember(text):
        return f"Gemerkt (#{mem.add(text)})."

    @tool("memory", "query", "Im Gedächtnis suchen")
    def recall(query):
        return "\n".join(t for _, t in mem.search(query)) or "Nichts gefunden."

    @tool("memory", "text", "Gemerkte Info vergessen")
    def forget(text):
        return f"{mem.delete_matching(text)} Eintrag/Einträge vergessen."

    return R
