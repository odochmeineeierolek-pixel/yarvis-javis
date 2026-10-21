"""Schnellpfad: häufige Befehle werden OHNE KI erkannt und sofort ausgeführt (extrem schnell)."""
import re

from .tools import SITES

NUM = {"einen": 1, "eine": 1, "einer": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "fuenf": 5, "sechs": 6, "sieben": 7,
       "acht": 8, "neun": 9, "zehn": 10, "fünfzehn": 15, "zwanzig": 20, "dreißig": 30, "vierzig": 40, "fünfzig": 50, "sechzig": 60}
TLD = re.compile(r"^[\w-]+\.(de|com|net|org|tv|io|eu|at|ch)$")
FOLDERS = "downloads|desktop|schreibtisch|dokumente|bilder|musik|videos"


def _n(w):
    w = w.strip().lower()
    return int(w) if w.isdigit() else NUM.get(w)


def _unit_seconds(u):
    return 1 if u.startswith("sek") else 60 if u.startswith("min") else 3600


def route(text: str):
    """-> {"tool","args","say"} oder None. say: Vorlage mit {result}; None = KI formuliert die Antwort."""
    t = re.sub(r"[.!?,]+$", "", text.lower().strip())
    t = re.sub(r"^(bitte|kannst du|könntest du|kannst du mir|mach mal)\s+", "", t)
    if not t:
        return None
    if re.search(r"wie (spät|viel uhr)|uhrzeit|welche zeit", t):
        return {"tool": "get_time", "args": {}, "say": "Es ist {result}, Master."}
    if re.fullmatch(r"(mach |stell )?(den )?(screenshot|bildschirmfoto)( machen)?", t) or t == "screenshot":
        return {"tool": "screenshot", "args": {}, "say": "Screenshot gemacht, Master."}
    if t in ("lauter", "mach lauter", "mach es lauter"):
        return {"tool": "media_key", "args": {"action": "vol_up"}, "say": "Lauter, Master."}
    if t in ("leiser", "mach leiser", "mach es leiser"):
        return {"tool": "media_key", "args": {"action": "vol_down"}, "say": "Leiser, Master."}
    if t in ("stumm", "stumm schalten", "ton aus"):
        return {"tool": "media_key", "args": {"action": "mute"}, "say": "Okay, Master."}
    if re.search(r"\bwetter\b", t) and len(t) < 40:
        m = re.search(r"wetter (?:in|für) ([\wäöüß\- ]+)", t)
        return {"tool": "weather", "args": {"city": m[1]} if m else {}, "say": "{result}, Master."}
    if re.fullmatch(r"(was gibt.s )?(neues|nachrichten|news)", t) or t in ("was gibt es neues", "aktuelle nachrichten"):
        return {"tool": "news", "args": {}, "say": None}
    m = re.search(r"timer (?:auf|für) (\w+) (sekunden?|minuten?|stunden?)", t)
    if m and _n(m[1]):
        return {"tool": "set_timer", "args": {"seconds": _n(m[1]) * _unit_seconds(m[2])}, "say": "Timer läuft, Master."}
    m = re.search(r"erinnere mich in (\w+) (minuten?|stunden?) (?:an|daran,?)\s+(.+)", t)
    if m and _n(m[1]):
        return {"tool": "set_reminder", "args": {"text": m[3], "minutes": _n(m[1]) * (1 if m[2].startswith("min") else 60)},
                "say": "Ich erinnere dich, Master."}
    # --- Musik ---
    if re.fullmatch(r"(spiel|spiele|starte|mach)( mal)?( bitte)?( etwas| irgendwas| irgendeine)? ?(musik|was)( an)?", t) or t in ("musik an", "musik abspielen"):
        return {"tool": "play_music", "args": {"query": ""}, "say": "{result}"}
    if re.fullmatch(r"(musik )?(pause|pausiere( die musik)?|musik pausieren)", t):
        return {"tool": "pause_music", "args": {}, "say": "Pausiert, Master."}
    if t in ("weiter", "musik weiter", "weiter spielen", "fortsetzen"):
        return {"tool": "resume_music", "args": {}, "say": "Weiter geht's, Master."}
    if re.fullmatch(r"(nächstes|nächster|nächstes lied|skip|überspringen|nächster titel|nächstes lied bitte)", t):
        return {"tool": "next_track", "args": {}, "say": "Okay, Master."}
    if re.fullmatch(r"(vorheriges lied|vorheriger titel|zurück)", t):
        return {"tool": "prev_track", "args": {}, "say": "Okay, Master."}
    if re.fullmatch(r"(musik aus|stoppe( die)? musik|musik stoppen|musik beenden)", t):
        return {"tool": "stop_music", "args": {}, "say": "Musik aus, Master."}
    # --- YouTube / Web ---
    m = re.search(r"(?:suche|such)(?: auf| bei| in)? youtube (?:nach )?(.+)|youtube (?:suche|such) (.+)|(?:spiel|spiele) (.+) auf youtube", t)
    if m:
        q = next(g for g in m.groups() if g)
        return {"tool": "youtube_search", "args": {"query": q}, "say": "Ich suche auf YouTube, Master."}
    m = re.fullmatch(r"(?:spiel|spiele|play)(?: mal)?(?: bitte)? (.+)", t)
    if m:
        return {"tool": "play_music", "args": {"query": m[1]}, "say": "{result}"}
    m = re.search(r"^(?:suche|such|google|recherchiere)(?: im (?:web|internet))?(?: nach)? (.+)", t)
    if m and not re.match(r"datei|notiz", m[1]):
        return {"tool": "web_search", "args": {"query": m[1]}, "say": None}
    # --- Öffnen ---
    m = re.fullmatch(rf"(?:öffne|starte|zeig)(?: mir)?(?: bitte)?(?: meinen| den| die| das)? ?({FOLDERS})(?: ordner)?", t)
    if m:
        return {"tool": "open_folder", "args": {"name": m[1]}, "say": "Ordner geöffnet, Master."}
    m = re.fullmatch(r"(?:öffne|starte|start|öffnen|starten)(?: mir)?(?: bitte)?(?: den| die| das)? (.+)", t) or \
        re.fullmatch(r"(?:mach|mache)(?: mir)? (.+?) auf", t)
    if m:
        target = m[1].strip()
        if target in SITES or TLD.match(target):
            return {"tool": "open_website", "args": {"target": target}, "say": "Mache ich, Master."}
        return {"tool": "open_app", "args": {"name": target}, "say": "{result}"}
    if t in SITES:     # nur "youtube" gesagt
        return {"tool": "open_website", "args": {"target": t}, "say": "Mache ich, Master."}
    if re.fullmatch(r"(sperre|sperr)( den)?( pc| bildschirm| computer)?", t):
        return {"tool": "lock_screen", "args": {}, "say": "Gesperrt, Master."}
    return None
