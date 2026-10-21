"""Einstellungsseite – alles einstellbar."""
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit, QPushButton, QComboBox,
                               QCheckBox, QSlider, QListWidget, QListWidgetItem, QGroupBox, QFileDialog, QSpinBox, QScrollArea)

from .config import VOICE_PRESETS
from .tools import app_index
from .ui_theme import label, YEL, DIM
from .voice import list_input_devices

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def exe_command():
    return sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" -m yavis'


def autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, "YAVIS")
            return True
    except Exception:
        return False


def set_autostart(on):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "YAVIS", 0, winreg.REG_SZ, exe_command())
            else:
                try:
                    winreg.DeleteValue(k, "YAVIS")
                except FileNotFoundError:
                    pass
    except Exception:
        pass


def slider(lo, hi, val, step=1):
    s = QSlider(Qt.Horizontal); s.setRange(lo, hi); s.setValue(val); s.setSingleStep(step)
    return s


class FolderList(QWidget):
    def __init__(self, folders, title):
        super().__init__()
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget(); self.list.setMaximumHeight(110); self.list.addItems(folders); v.addWidget(self.list)
        r = QHBoxLayout()
        a = QPushButton("+ Ordner hinzufügen"); a.clicked.connect(self.add); r.addWidget(a)
        d = QPushButton("− Entfernen"); d.clicked.connect(lambda: [self.list.takeItem(self.list.row(i)) for i in self.list.selectedItems()]); r.addWidget(d)
        v.addLayout(r)

    def add(self):
        p = QFileDialog.getExistingDirectory(self, "Ordner wählen")
        if p:
            self.list.addItem(p)

    def values(self):
        return [self.list.item(i).text() for i in range(self.list.count())]


class SettingsPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        s = app.settings
        outer = QVBoxLayout(self); outer.setContentsMargins(24, 16, 24, 16)
        top = QHBoxLayout(); top.addWidget(label("Einstellungen", 20, bold=True)); top.addStretch()
        save = QPushButton("💾 Speichern"); save.setObjectName("primary"); save.clicked.connect(self.save); top.addWidget(save); outer.addLayout(top)
        inner = QWidget(); L = QVBoxLayout(inner)

        # --- Stimme ---
        g = QGroupBox("Stimme"); f = QFormLayout(g)
        self.voice = QComboBox(); self.voice.addItems(list(VOICE_PRESETS) + ["Windows-Stimme (offline)"]); self.voice.setCurrentText(s["voice"]); f.addRow("Stimme:", self.voice)
        self.speed = slider(-30, 30, s["voice_speed"]); f.addRow("Tempo:", self.speed)
        self.pitch = slider(-20, 20, s["voice_pitch"]); f.addRow("Tonhöhe (tiefer ↔ höher):", self.pitch)
        self.engine = QComboBox(); self.engine.addItems(["edge", "offline"]); self.engine.setCurrentText(s["tts_engine"]); f.addRow("Engine (edge = natürlicher, braucht Internet):", self.engine)
        self.emotions = QCheckBox("Gefühle zeigen (freundlich, lieb, traurig, böse …)"); self.emotions.setChecked(s["emotions"]); f.addRow(self.emotions)
        self.neutral = QCheckBox("Neutral-Modus (überstimmt Gefühle)"); self.neutral.setChecked(s["neutral"]); f.addRow(self.neutral)
        t = QPushButton("▶ Stimme testen"); t.clicked.connect(self.test_voice); f.addRow(t)
        L.addWidget(g)

        # --- Hören ---
        g = QGroupBox("Zuhören"); f = QFormLayout(g)
        self.wake = QLineEdit(", ".join(s["wake_words"])); f.addRow("Aktivierungswörter (Komma):", self.wake)
        self.whisper = QComboBox(); self.whisper.addItems(["base", "small", "medium"]); self.whisper.setCurrentText(s["whisper_model"])
        f.addRow("Hörgenauigkeit (base schnell · small gut · medium beste, langsamer):", self.whisper)
        self.mic = QComboBox(); self.mic.addItem("Standard-Mikrofon", None)
        for i, n in list_input_devices():
            self.mic.addItem(n, i)
        idx = self.mic.findData(s["mic_device"]); self.mic.setCurrentIndex(max(0, idx)); f.addRow("Mikrofon:", self.mic)
        self.sens = slider(15, 60, int(s["sensitivity"] * 10)); f.addRow("Empfindlichkeit (links = hört mehr, rechts = weniger Störgeräusche):", self.sens)
        self.follow = QSpinBox(); self.follow.setRange(0, 60); self.follow.setValue(s["followup_seconds"]); f.addRow("Weiterreden ohne „YAVIS“ (Sekunden):", self.follow)
        L.addWidget(g)

        # --- Gehirn ---
        g = QGroupBox("Gehirn & Lernen"); f = QFormLayout(g)
        self.model = QLineEdit(s["model"]); f.addRow("Ollama-Modell (qwen2.5:3b schnell · qwen2.5:7b klüger):", self.model)
        self.city = QLineEdit(s["city"]); f.addRow("Standardort (Wetter):", self.city)
        self.learn = QCheckBox("Automatisch dazulernen"); self.learn.setChecked(s["auto_learn"]); f.addRow(self.learn)
        L.addWidget(g)

        # --- Programme ---
        g = QGroupBox("Programme & Spiele – welche darf YAVIS öffnen?"); v = QVBoxLayout(g)
        self.mode = QComboBox(); self.mode.addItems(["Alle erlauben (außer abgewählte)", "Nur angehakte erlauben"])
        self.mode.setCurrentIndex(0 if s["app_mode"] == "all" else 1); v.addWidget(self.mode)
        self.filter = QLineEdit(); self.filter.setPlaceholderText("Filtern …"); self.filter.textChanged.connect(self.apply_filter); v.addWidget(self.filter)
        self.apps = QListWidget(); self.apps.setMinimumHeight(220); v.addWidget(self.apps)
        rb = QPushButton("🔄 Programmliste neu einlesen"); rb.clicked.connect(self.load_apps); v.addWidget(rb)
        L.addWidget(g)

        # --- Zugriff ---
        g = QGroupBox("Zugriff auf Ordner (Dateisuche, Lesen, Öffnen)"); v = QVBoxLayout(g)
        self.folders = FolderList(s["folders"], "Ordner"); v.addWidget(self.folders)
        v.addWidget(label("Bereiche ein/aus (Internet, Tastatur, Zwischenablage …): Seite „Tools“.", 11, DIM))
        L.addWidget(g)

        # --- Musik / System ---
        g = QGroupBox("Musik & System"); v = QVBoxLayout(g)
        v.addWidget(label("Musikordner:", 12)); self.mfolders = FolderList(s["music_folders"], "Musik"); v.addWidget(self.mfolders)
        self.duck = QCheckBox("Musik leiser stellen, während YAVIS spricht"); self.duck.setChecked(s["duck_music"]); v.addWidget(self.duck)
        self.auto = QCheckBox("Mit Windows starten"); self.auto.setChecked(autostart_enabled()); v.addWidget(self.auto)
        L.addWidget(g)
        L.addStretch()
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(inner); outer.addWidget(sc, 1)
        self.load_apps()

    def load_apps(self):
        s = self.app.settings
        self.apps.clear()
        for key in sorted(app_index(force=True)):
            it = QListWidgetItem(key)
            allowed = (key in s["allowed_apps"]) if s["app_mode"] == "allowlist" else (key not in s["blocked_apps"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable); it.setCheckState(Qt.Checked if allowed else Qt.Unchecked)
            self.apps.addItem(it)
        if not self.apps.count():
            self.apps.addItem("(Keine Programme gefunden – läuft nur unter Windows)")

    def apply_filter(self, text):
        for i in range(self.apps.count()):
            self.apps.item(i).setHidden(text.lower() not in self.apps.item(i).text())

    def test_voice(self):
        self.apply(); self.app.speak_async("Hallo Master. So klinge ich. Gefällt dir das?", "freundlich")

    def apply(self):
        s = self.app.settings
        s.update(voice=self.voice.currentText(), voice_speed=self.speed.value(), voice_pitch=self.pitch.value(),
                 tts_engine=self.engine.currentText(), emotions=self.emotions.isChecked(), neutral=self.neutral.isChecked(),
                 wake_words=[w.strip().lower() for w in self.wake.text().split(",") if w.strip()] or ["yavis"],
                 whisper_model=self.whisper.currentText(), mic_device=self.mic.currentData(), sensitivity=self.sens.value() / 10,
                 followup_seconds=self.follow.value(), model=self.model.text().strip() or s["model"], city=self.city.text().strip() or s["city"],
                 auto_learn=self.learn.isChecked(), folders=self.folders.values(), music_folders=self.mfolders.values(),
                 duck_music=self.duck.isChecked(), app_mode="all" if self.mode.currentIndex() == 0 else "allowlist")
        checked, unchecked = [], []
        for i in range(self.apps.count()):
            it = self.apps.item(i)
            if it.flags() & Qt.ItemIsUserCheckable:
                (checked if it.checkState() == Qt.Checked else unchecked).append(it.text())
        if checked or unchecked:
            s["allowed_apps"], s["blocked_apps"] = checked, unchecked
        s.save(); set_autostart(self.auto.isChecked())

    def save(self):
        self.apply(); self.app.set_status("Einstellungen gespeichert."); self.app.refresh_all()
