"""Einstellungen und Pfade. Alles liegt lokal in %APPDATA%\\YAVIS."""
import json, os, copy
from pathlib import Path

DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / ".yavis")) / "YAVIS"
NOTES_DIR = DATA_DIR / "Notizen"
DRAFTS_DIR = DATA_DIR / "Entwuerfe"
for _d in (DATA_DIR, NOTES_DIR, DRAFTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
DB_FILE = DATA_DIR / "gedaechtnis.db"
LOG_FILE = DATA_DIR / "aktionen.log"

# Name -> (Edge-Stimme, Tempo, Tonhöhe). Edge-Stimmen sind kostenlos, brauchen aber Internet.
VOICE_PRESETS = {
    "Mama – mütterlich & warm": ("de-DE-KatjaNeural", "-8%", "-2Hz"),
    "Assistentin – klar & freundlich": ("de-DE-KatjaNeural", "+0%", "+0Hz"),
    "Freundin – jung & locker": ("de-DE-SeraphinaMultilingualNeural", "+6%", "+3Hz"),
    "Sanfte Stimme": ("de-DE-AmalaNeural", "-6%", "+0Hz"),
    "Österreicherin": ("de-AT-IngridNeural", "+0%", "+0Hz"),
    "Schweizerin": ("de-CH-LeniNeural", "+0%", "+0Hz"),
    "Mann – ruhig & tief": ("de-DE-ConradNeural", "-6%", "-6Hz"),
    "Butler – gediegen": ("de-DE-ConradNeural", "-10%", "-10Hz"),
    "Held – kräftig": ("de-DE-KillianNeural", "+0%", "-8Hz"),
    "Kumpel – locker": ("de-DE-KillianNeural", "+8%", "+0Hz"),
    "Mann – jung & frisch": ("de-DE-FlorianMultilingualNeural", "+6%", "+2Hz"),
    "Österreicher": ("de-AT-JonasNeural", "+0%", "+0Hz"),
    "Schweizer": ("de-CH-JanNeural", "+0%", "+0Hz"),
}

MALE_VOICES = {"Mann – ruhig & tief", "Butler – gediegen", "Held – kräftig", "Kumpel – locker",
               "Mann – jung & frisch", "Österreicher", "Schweizer"}

PERM_CATEGORIES = {
    "apps": "Programme & Spiele starten/beenden",
    "web": "Internet, Websuche, Wetter, Nachrichten",
    "files": "Dateien suchen, lesen, öffnen, erstellen",
    "music": "Musik abspielen",
    "system": "System (Lautstärke, Screenshot, Sperren, Einstellungen)",
    "control": "Tastatur & Fenster steuern (mächtig – standardmäßig AUS)",
    "memory": "Gedächtnis & automatisches Lernen",
    "clipboard": "Zwischenablage (standardmäßig AUS)",
    "tasks": "Aufgaben, Notizen, Erinnerungen, Routinen",
}


def _default_folders():
    h = Path.home()
    return [str(h / n) for n in ("Desktop", "Documents", "Downloads", "Pictures", "Videos", "Music")]


DEFAULTS = {
    "wake_words": ["yavis", "jarvis", "yavies"],
    "voice": "Assistentin – klar & freundlich",
    "voice_speed": 0, "voice_pitch": 0,
    "tts_engine": "edge",
    "neutral": False, "emotions": True,
    "model": "qwen2.5:3b", "whisper_model": "small",
    "followup_seconds": 10, "listen_enabled": True,
    "mic_device": None, "sensitivity": 3.0,
    "auto_learn": True, "city": "Essen",
    "perms": {"apps": True, "web": True, "files": True, "music": True, "system": True,
              "control": False, "memory": True, "clipboard": False, "tasks": True},
    "disabled_tools": [],
    "app_mode": "all",              # "all" (außer blocked_apps) oder "allowlist" (nur allowed_apps)
    "blocked_apps": [], "allowed_apps": [],
    "folders": _default_folders(),
    "music_folders": [str(Path.home() / "Music")],
    "music_volume": 70, "duck_music": True,
    "active_project": None,
}


class Settings(dict):
    def __init__(self):
        super().__init__(copy.deepcopy(DEFAULTS))
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            perms = data.pop("perms", {})
            self.update(data)
            self["perms"].update(perms)
        except Exception:
            pass
        if self["voice"] not in VOICE_PRESETS and self["voice"] != "Windows-Stimme (offline)":
            self["voice"] = DEFAULTS["voice"]

    def save(self):
        SETTINGS_FILE.write_text(json.dumps(self, ensure_ascii=False, indent=2), encoding="utf-8")
