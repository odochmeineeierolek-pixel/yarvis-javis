"""YAVIS – Oberfläche (PySide6): pulsierender Orb in Rot/Schwarz/Gelb, Spracheingabe, Einstellungen."""
import math, os, random, subprocess, sys, threading, time

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPointF
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QPen, QFont
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QDialog, QFormLayout, QComboBox, QCheckBox, QMessageBox, QListWidget, QDialogButtonBox)

from .config import Settings, VOICES, LOG_FILE
from .llm import Brain
from .memory import Memory
from .tools import build_registry
from .voice import Listener, Speaker, find_wake_word

RED, YELLOW, BLACK = QColor("#e10600"), QColor("#ffc400"), QColor("#0b0b0b")
EMO_STYLE = {  # (Farbe, Tempo, Intensität)
    "neutral": (YELLOW, 1.0, 1.0), "freundlich": (YELLOW, 1.0, 1.1), "lieb": (QColor("#ff9a3c"), 0.7, 1.1),
    "froehlich": (YELLOW, 1.5, 1.3), "traurig": (QColor("#8a6a00"), 0.5, 0.7), "boese": (RED, 1.8, 1.4),
}

STYLE = f"""
QWidget {{ background:{BLACK.name()}; color:#f2f2f2; font-family:'Segoe UI'; }}
QLineEdit {{ background:#161616; border:1px solid {RED.name()}; border-radius:14px; padding:10px 14px; font-size:14px; }}
QPushButton {{ background:#161616; border:1px solid {YELLOW.name()}; border-radius:12px; padding:8px 14px; }}
QPushButton:hover {{ background:{YELLOW.name()}; color:#000; }}
QPushButton#stop {{ border-color:{RED.name()}; }} QPushButton#stop:hover {{ background:{RED.name()}; color:#fff; }}
"""


class Orb(QWidget):
    def __init__(self):
        super().__init__()
        self.level, self.shown, self.t, self.emotion, self.state = 0.0, 0.0, 0.0, "neutral", "idle"
        self.setMinimumSize(420, 420)
        tm = QTimer(self); tm.timeout.connect(self.tick); tm.start(16)

    def tick(self):
        self.t += 0.016 * EMO_STYLE[self.emotion][1]
        self.shown += (self.level - self.shown) * 0.25
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        base = min(self.width(), self.height()) * 0.22
        col, _, inten = EMO_STYLE[self.emotion]
        breathe = 0.04 * math.sin(self.t * 2)
        r = base * (1 + breathe + 0.45 * self.shown * inten)
        for i in range(4, 0, -1):  # Ringe
            ring = QColor(RED if i % 2 else col); ring.setAlpha(int(70 / i + 60 * self.shown))
            p.setPen(QPen(ring, 2)); p.setBrush(Qt.NoBrush)
            wob = r * (1 + 0.18 * i + 0.05 * math.sin(self.t * (2 + i) + i))
            p.drawEllipse(c, wob, wob)
        g = QRadialGradient(c, r)
        g.setColorAt(0, col.lighter(130)); g.setColorAt(0.55, col); g.setColorAt(0.85, RED); g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setPen(Qt.NoPen); p.setBrush(g); p.drawEllipse(c, r, r)
        glow = QRadialGradient(c, r * 2.2)
        gc = QColor(RED); gc.setAlpha(int(40 + 90 * self.shown))
        glow.setColorAt(0.4, gc); glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(glow); p.drawEllipse(c, r * 2.2, r * 2.2)


class Bridge(QObject):
    level = Signal(float); emotion = Signal(str); status = Signal(str); log = Signal(str)
    confirm = Signal(str); heard = Signal(str)


class SettingsDialog(QDialog):
    def __init__(self, s, memory, parent=None):
        super().__init__(parent); self.s, self.memory = s, memory
        self.setWindowTitle("YAVIS – Einstellungen")
        f = QFormLayout(self)
        self.wake = QLineEdit(", ".join(s["wake_words"])); f.addRow("Aktivierungswörter (Komma):", self.wake)
        self.voice = QComboBox(); self.voice.addItems(VOICES); self.voice.setCurrentText(s["voice"]); f.addRow("Stimme:", self.voice)
        self.engine = QComboBox(); self.engine.addItems(["edge", "offline"]); self.engine.setCurrentText(s["tts_engine"])
        f.addRow("Sprach-Engine (edge = natürlicher, braucht Internet):", self.engine)
        self.neutral = QCheckBox("Neutral (keine Gefühle)"); self.neutral.setChecked(s["neutral"]); f.addRow(self.neutral)
        self.model = QLineEdit(s["model"]); f.addRow("Ollama-Modell:", self.model)
        self.whisper = QComboBox(); self.whisper.addItems(["base", "small", "medium"]); self.whisper.setCurrentText(s["whisper_model"])
        f.addRow("Hörgenauigkeit (small = gut, medium = besser/langsamer):", self.whisper)
        self.auto = QCheckBox("Mit Windows starten"); self.auto.setChecked(autostart_enabled()); f.addRow(self.auto)
        b = QPushButton("Gedächtnis ansehen / löschen"); b.clicked.connect(self.show_memory); f.addRow(b)
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); f.addRow(bb)

    def show_memory(self):
        d = QDialog(self); d.setWindowTitle("Gedächtnis"); l = QVBoxLayout(d); lw = QListWidget(); l.addWidget(lw)
        def fill():
            lw.clear()
            for i, t in self.memory.all(): lw.addItem(f"{i}: {t}")
        fill()
        def delsel():
            for it in lw.selectedItems(): self.memory.delete(int(it.text().split(":")[0]))
            fill()
        def delall():
            if QMessageBox.question(d, "Alles löschen?", "Wirklich das gesamte Gedächtnis löschen?") == QMessageBox.Yes:
                self.memory.clear(); fill()
        r = QHBoxLayout(); a = QPushButton("Auswahl löschen"); a.clicked.connect(delsel); c = QPushButton("Alles löschen"); c.clicked.connect(delall)
        r.addWidget(a); r.addWidget(c); l.addLayout(r); d.resize(480, 360); d.exec()

    def apply(self):
        s = self.s
        s["wake_words"] = [w.strip().lower() for w in self.wake.text().split(",") if w.strip()] or ["yavis"]
        s.update(voice=self.voice.currentText(), tts_engine=self.engine.currentText(), neutral=self.neutral.isChecked(),
                 model=self.model.text().strip() or s["model"], whisper_model=self.whisper.currentText())
        set_autostart(self.auto.isChecked()); s.save()


def _exe():
    return sys.executable if getattr(sys, "frozen", False) else f'"{sys.executable}" -m yavis'


def autostart_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as k:
            winreg.QueryValueEx(k, "YAVIS"); return True
    except Exception:
        return False


def set_autostart(on):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as k:
            if on: winreg.SetValueEx(k, "YAVIS", 0, winreg.REG_SZ, _exe())
            else:
                try: winreg.DeleteValue(k, "YAVIS")
                except FileNotFoundError: pass
    except Exception:
        pass


def log_action(text):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(f"{time.strftime('%F %T')} {text}\n")
    except Exception:
        pass


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YAVIS"); self.resize(560, 700); self.setStyleSheet(STYLE)
        self.s, self.memory = Settings(), Memory()
        self.bridge = Bridge()
        self.confirm_evt, self.confirm_ans = threading.Event(), [False]
        self.registry = build_registry(self.memory)
        self.brain = Brain(self.s, self.memory, self.registry, self.ask_confirm, lambda m: self.bridge.status.emit(m))
        self.speaker = Speaker(self.s, lambda x: self.bridge.level.emit(x))
        self.listener = Listener(self.s, lambda x: self.bridge.level.emit(x))
        self.last_interaction = 0.0
        self.busy = threading.Lock()

        self.orb = Orb()
        self.status = QLabel("Starte …"); self.status.setAlignment(Qt.AlignCenter); self.status.setFont(QFont("Segoe UI", 11))
        self.said = QLabel(""); self.said.setAlignment(Qt.AlignCenter); self.said.setWordWrap(True); self.said.setStyleSheet(f"color:{YELLOW.name()}")
        self.inp = QLineEdit(); self.inp.setPlaceholderText("Oder schreib hier …  (Sprache: sag „YAVIS …“)"); self.inp.returnPressed.connect(self.on_text)
        stop = QPushButton("■ Stopp"); stop.setObjectName("stop"); stop.clicked.connect(self.stop_all)
        mic = QPushButton("🎤 Zuhören an/aus"); mic.clicked.connect(self.toggle_mic)
        st = QPushButton("⚙ Einstellungen"); st.clicked.connect(self.open_settings)
        row = QHBoxLayout(); [row.addWidget(w) for w in (mic, st, stop)]
        lay = QVBoxLayout(self); lay.addWidget(self.orb, 1); lay.addWidget(self.status); lay.addWidget(self.said); lay.addWidget(self.inp); lay.addLayout(row)

        b = self.bridge
        b.level.connect(lambda v: setattr(self.orb, "level", v)); b.emotion.connect(lambda e: setattr(self.orb, "emotion", e))
        b.status.connect(self.status.setText); b.heard.connect(self.said.setText); b.confirm.connect(self.show_confirm)
        threading.Thread(target=self.boot, daemon=True).start()

    # --- Start: Ollama + Modell + Whisper vorbereiten ---
    def boot(self):
        b = self.bridge
        if not self.brain.ollama_ready():
            b.status.emit("Starte Ollama …")
            try:
                subprocess.Popen(["ollama", "serve"], creationflags=0x08000000)  # ohne Konsolenfenster
            except Exception:
                b.status.emit("Ollama fehlt – bitte von ollama.com installieren (kostenlos)."); return
            for _ in range(30):
                if self.brain.ollama_ready(): break
                time.sleep(1)
        self.ensure_model()
        b.status.emit("Lade Spracherkennung …")
        try: self.listener.load()
        except Exception as e:
            b.status.emit(f"Spracherkennung nicht verfügbar ({type(e).__name__}) – Textmodus aktiv."); return
        b.status.emit("Bereit – sag „YAVIS“")
        self.speak_async("Hallo Master. Ich bin bereit.", "freundlich")
        self.listen_loop()

    def ensure_model(self):
        import requests
        try:
            have = [m["name"] for m in requests.get("http://127.0.0.1:11434/api/tags", timeout=5).json().get("models", [])]
            if not any(h.startswith(self.s["model"]) for h in have):
                self.bridge.status.emit(f"Lade Modell {self.s['model']} (einmalig) …")
                requests.post("http://127.0.0.1:11434/api/pull", json={"name": self.s["model"], "stream": False}, timeout=3600)
        except Exception:
            pass

    # --- Zuhören ---
    def listen_loop(self):
        while True:
            if not self.s["listen_enabled"] or self.speaker.speaking:
                time.sleep(0.2); continue
            try:
                audio = self.listener.record_utterance(max_wait=30)
                if audio is None: continue
                text = self.listener.transcribe(audio)
            except Exception as e:
                self.bridge.status.emit(f"Mikrofonfehler: {type(e).__name__}"); time.sleep(2); continue
            if not text: continue
            follow = time.time() - self.last_interaction < self.s["followup_seconds"]
            cmd = find_wake_word(text, self.s["wake_words"])
            if cmd is None:
                if not follow: continue
                cmd = text
            if not cmd.strip():                       # nur "YAVIS" gesagt -> auf Befehl warten
                self.speak_async("Ja, Master?", "freundlich"); time.sleep(0.8)
                audio = self.listener.record_utterance(max_wait=8)
                if audio is None: continue
                cmd = self.listener.transcribe(audio)
                if not cmd.strip(): continue
            self.handle(cmd)

    def handle(self, text):
        if not self.busy.acquire(blocking=False): return
        try:
            self.bridge.heard.emit(f"„{text}“"); self.bridge.status.emit("Denke …")
            log_action(f"INPUT {text[:80]}")
            res = self.brain.ask(text)
            self.bridge.emotion.emit(res.get("emotion", "neutral"))
            self.bridge.heard.emit(res.get("speech", ""))
            self.bridge.status.emit("Spreche …")
            self.listener.paused.set()
            self.speaker.speak(res.get("speech", ""), res.get("emotion", "neutral"))
        finally:
            self.listener.paused.clear(); self.last_interaction = time.time()
            self.bridge.emotion.emit("neutral"); self.bridge.status.emit("Bereit – sag „YAVIS“"); self.busy.release()

    def speak_async(self, text, emo="neutral"):
        threading.Thread(target=lambda: self.speaker.speak(text, emo), daemon=True).start()

    def on_text(self):
        t = self.inp.text().strip(); self.inp.clear()
        if t: threading.Thread(target=self.handle, args=(t,), daemon=True).start()

    # --- Bestätigung kritischer Aktionen (aus Worker-Thread) ---
    def ask_confirm(self, desc):
        self.confirm_evt.clear(); self.bridge.confirm.emit(desc)
        return self.confirm_evt.wait(120) and self.confirm_ans[0]

    def show_confirm(self, desc):
        r = QMessageBox.question(self, "Bestätigung nötig", f"YAVIS möchte ausführen:\n\n{desc}\n\nErlauben?")
        self.confirm_ans[0] = (r == QMessageBox.Yes); self.confirm_evt.set()

    def stop_all(self):
        self.brain.stop_event.set(); self.speaker.stop(); self.bridge.status.emit("Gestoppt.")

    def toggle_mic(self):
        self.s["listen_enabled"] = not self.s["listen_enabled"]
        self.bridge.status.emit("Zuhören an" if self.s["listen_enabled"] else "Zuhören aus")

    def open_settings(self):
        d = SettingsDialog(self.s, self.memory, self)
        if d.exec(): d.apply(); self.bridge.status.emit("Einstellungen gespeichert.")


def main():
    app = QApplication(sys.argv)
    w = Main(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
