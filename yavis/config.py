"""Einstellungen und Pfade. Alles liegt lokal in %APPDATA%\\YAVIS."""
import json, os
from pathlib import Path

DATA_DIR = Path(os.environ.get("APPDATA", Path.home() / ".yavis")) / "YAVIS"
NOTES_DIR = DATA_DIR / "Notizen"
for _d in (DATA_DIR, NOTES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
DB_FILE = DATA_DIR / "gedaechtnis.db"
LOG_FILE = DATA_DIR / "aktionen.log"

# Edge-Stimmen: kostenlos, brauchen Internet, klingen am natürlichsten.
VOICES = {
    "Frau – warm (Katja)": "de-DE-KatjaNeural",
    "Frau – sanft (Amala)": "de-DE-AmalaNeural",
    "Frau – mehrsprachig (Seraphina)": "de-DE-SeraphinaMultilingualNeural",
    "Mann – tief (Conrad)": "de-DE-ConradNeural",
    "Mann – klar (Killian)": "de-DE-KillianNeural",
    "Mann – mehrsprachig (Florian)": "de-DE-FlorianMultilingualNeural",
}

DEFAULTS = {
    "wake_words": ["yavis", "jarvis", "yavies"],
    "voice": "Frau – warm (Katja)",
    "tts_engine": "edge",          # "edge" (online, schön) oder "offline" (Windows-Stimme)
    "neutral": False,              # True = keine Gefühle
    "model": "qwen2.5:3b",         # klein = schnell. Größer: qwen2.5:7b
    "whisper_model": "small",      # "base" = schneller, "small" = genauer
    "followup_seconds": 10,        # nach einer Antwort ohne Aktivierungswort weiterreden
    "listen_enabled": True,
}


class Settings(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        try:
            self.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass

    def save(self):
        SETTINGS_FILE.write_text(json.dumps(self, ensure_ascii=False, indent=2), encoding="utf-8")
