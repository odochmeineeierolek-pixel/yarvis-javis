"""YAVIS – Hauptfenster und Ablaufsteuerung."""
import subprocess, sys, threading, time

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QFrame,
                               QMessageBox, QInputDialog, QButtonGroup)

from .config import Settings, LOG_FILE
from .llm import Brain
from .memory import Memory
from .music import MusicController
from .tools import Ctx, build_registry
from .ui_pages import HomePage, ChatPage, ProjectsPage, FilesPage, KnowledgePage, ToolsPage, AutoPage, MusicPage, OrbPage
from .ui_settings import SettingsPage
from .ui_theme import QSS, LogoRing, label, RED, YEL, DIM
from .voice import Listener, Speaker, find_wake_word

NAV = [("home", "🏠", "Home"), ("chat", "💬", "Chat"), ("projects", "📁", "Projekte"), ("files", "📄", "Dateien"),
       ("knowledge", "📖", "Wissen"), ("tools", "🔧", "Tools"), ("music", "♪", "Musik"), ("auto", "⚡", "Automatisierungen"),
       ("settings", "⚙", "Einstellungen")]
QUOTE = "„Große Ideen entstehen nicht im Alleingang – sondern mit den richtigen Werkzeugen.“"
STOP_WORDS = {"stopp", "stop", "halt", "sei still", "ruhe", "abbrechen"}
CAT_BY_TOOL = {"Musik": ("play_music", "pause_music", "next_track", "prev_track", "stop_music", "resume_music", "music_volume"),
               "Web": ("open_website", "web_search", "youtube_search", "news", "weather", "wikipedia", "maps_search"),
               "Programm": ("open_app", "close_app", "open_system_tool"),
               "Datei": ("search_files", "open_file", "open_folder", "read_text_file", "list_dir")}


def log_action(text):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%F %T')} {text}\n")
    except Exception:
        pass


class Bridge(QObject):
    level = Signal(float); emotion = Signal(str); status = Signal(str); heard = Signal(str)
    chat = Signal(str, str); confirm = Signal(str); refresh = Signal()


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YAVIS"); self.resize(1380, 860); self.setStyleSheet(QSS)
        self.settings, self.memory = Settings(), Memory()
        self.music = MusicController(self.settings)
        self.ctx = Ctx(self.settings, self.memory, self.music)
        self.registry = build_registry(self.ctx)
        self.bridge = Bridge()
        self.confirm_evt, self.confirm_ans = threading.Event(), [False]
        self.brain = Brain(self.settings, self.memory, self.registry, self.ctx, self.ask_confirm, lambda m: self.bridge.status.emit(m))
        self.speaker = Speaker(self.settings, lambda x: self.bridge.level.emit(x))
        self.listener = Listener(self.settings, lambda x: self.bridge.level.emit(x))
        self.last_interaction, self.turn, self.ollama_ok = 0.0, 0, False
        self.busy = threading.Lock()
        self._build_ui()
        b = self.bridge
        b.level.connect(self._level); b.emotion.connect(self._emotion); b.status.connect(self.status.setText)
        b.heard.connect(self.pages["orb"].text.setText); b.chat.connect(lambda r, t: self.pages["chat"].add(r, t))
        b.confirm.connect(self.show_confirm); b.refresh.connect(self.refresh_all)
        self.rem_timer = QTimer(self); self.rem_timer.timeout.connect(self.check_reminders); self.rem_timer.start(4000)
        self.goto("home")
        threading.Thread(target=self.boot, daemon=True).start()

    # ---------- Aufbau ----------
    def _build_ui(self):
        root = QHBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        side = QFrame(); side.setObjectName("side"); side.setFixedWidth(250); side.setStyleSheet("QFrame#side{background:#080808; border-right:1px solid #1c1c1c;}")
        sl = QVBoxLayout(side); sl.setContentsMargins(14, 16, 14, 14); sl.setSpacing(4)
        self.logo = LogoRing(190); self.logo.clicked.connect(self.toggle_orb); sl.addWidget(self.logo, 0, Qt.AlignHCenter)
        self.status = label("Starte …", 11, DIM); self.status.setAlignment(Qt.AlignCenter); self.status.setWordWrap(True); sl.addWidget(self.status)
        sl.addSpacing(10)
        self.navgroup, self.navbtn = QButtonGroup(self), {}
        for key, ic, name in NAV:
            b = QPushButton(f"{ic}   {name}"); b.setObjectName("nav"); b.setCheckable(True); b.clicked.connect(lambda _, k=key: self.goto(k))
            self.navgroup.addButton(b); self.navbtn[key] = b; sl.addWidget(b)
        sl.addStretch()
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background:{YEL};"); sl.addWidget(line)
        q = label(QUOTE, 10, "#d8d8d8"); q.setWordWrap(True); q.setStyleSheet(f"color:#d8d8d8; font-style:italic; background:transparent;"); sl.addWidget(q)
        sl.addWidget(label("– YAVIS", 10, YEL))
        root.addWidget(side)
        col = QVBoxLayout(); col.setSpacing(0)
        top = QHBoxLayout(); top.setContentsMargins(24, 14, 20, 12)
        top.addWidget(label(f"<span style='color:#f2f2f2'>DEIN KI-ASSISTENT.</span><br><span style='color:#f2f2f2'>DENKT MIT. </span>"
                            f"<span style='color:{RED}'>HILFT. </span><span style='color:{YEL}'>SCHAFFT.</span>", 10, mono=True)); top.addStretch()
        self.model_lbl = label("● " + self.settings["model"], 12); self.model_lbl.setStyleSheet(f"color:#f2f2f2;")
        top.addWidget(self.model_lbl)
        for txt, fn, tip in (("🎤", self.toggle_mic, "Zuhören an/aus"), ("⚙", lambda: self.goto("settings"), "Einstellungen"),
                             ("🔔", self.show_reminders, "Erinnerungen"), ("👤", lambda: self.goto("knowledge"), "Was YAVIS über dich weiß")):
            b = QPushButton(txt); b.setObjectName("flat"); b.setToolTip(tip); b.clicked.connect(fn); top.addWidget(b)
        stop = QPushButton("■ Stopp"); stop.setObjectName("danger"); stop.clicked.connect(self.stop_all); top.addWidget(stop)
        col.addLayout(top)
        bar = QFrame(); bar.setFixedHeight(2); bar.setStyleSheet(f"background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 {RED},stop:1 {YEL});"); col.addWidget(bar)
        self.stack = QStackedWidget(); col.addWidget(self.stack, 1)
        root.addLayout(col, 1)
        self.pages = {}
        self.pages["home"] = HomePage(self)
        for key, cls in (("chat", ChatPage), ("projects", ProjectsPage), ("files", FilesPage), ("knowledge", KnowledgePage),
                         ("tools", ToolsPage), ("music", MusicPage), ("auto", AutoPage), ("settings", SettingsPage), ("orb", OrbPage)):
            self.pages[key] = cls(self)
        for p in self.pages.values():
            self.stack.addWidget(p)

    # ---------- Navigation / Anzeige ----------
    def goto(self, key):
        self.stack.setCurrentWidget(self.pages[key])
        if key in self.navbtn:
            self.navbtn[key].setChecked(True)
        else:
            self.navgroup.setExclusive(False)
            for b in self.navbtn.values():
                b.setChecked(False)
            self.navgroup.setExclusive(True)
        p = self.pages[key]
        if hasattr(p, "refresh"):
            p.refresh()

    def toggle_orb(self):
        self.goto("home" if self.stack.currentWidget() is self.pages["orb"] else "orb")

    def refresh_all(self):
        self.model_lbl.setText("● " + self.settings["model"])
        for p in self.pages.values():
            if hasattr(p, "refresh") and p is self.stack.currentWidget():
                p.refresh()

    def _level(self, v):
        self.logo.level = v; self.pages["orb"].orb.level = v

    def _emotion(self, e):
        self.pages["orb"].orb.emotion = e

    def set_status(self, t):
        self.bridge.status.emit(t)

    def new_project(self):
        name, ok = QInputDialog.getText(self, "Neues Projekt", "Name:")
        if ok and name.strip():
            self.memory.add_project(name); self.refresh_all()

    def select_project(self, pid, go=True):
        self.settings["active_project"] = pid; self.settings.save()
        p = self.memory.project(pid)
        self.set_status(f"Projekt aktiv: {p[1]}" if p else "")
        self.refresh_all()
        if go:
            self.goto("chat")

    def show_reminders(self):
        from datetime import datetime
        r = self.memory.reminders()
        QMessageBox.information(self, "Erinnerungen", "\n".join(f"{datetime.fromtimestamp(d):%d.%m. %H:%M} – {t}" for _, t, d in r) or "Keine offenen Erinnerungen.")

    # ---------- Start ----------
    def boot(self):
        b = self.bridge
        if not self.brain.ollama_ready():
            b.status.emit("Starte Ollama …")
            try:
                subprocess.Popen(["ollama", "serve"], creationflags=0x08000000)
            except Exception:
                b.status.emit("Ollama fehlt – bitte von ollama.com installieren (kostenlos).")
            for _ in range(30):
                if self.brain.ollama_ready():
                    break
                time.sleep(1)
        self.ollama_ok = self.brain.ollama_ready()
        if self.ollama_ok:
            self.ensure_model()
        b.refresh.emit()
        b.status.emit("Lade Spracherkennung …")
        try:
            self.listener.load()
        except Exception as e:
            b.status.emit(f"Spracherkennung nicht verfügbar ({type(e).__name__}) – Textmodus aktiv."); b.refresh.emit(); return
        b.refresh.emit()
        for _, name, trig, steps, on_start in self.memory.routines():
            if on_start:
                for st in steps:
                    self.brain.run_tool(st["tool"], st.get("args", {}))
        b.status.emit("Bereit – sag „YAVIS“")
        self.speak_async("Hallo Master. Ich bin bereit.", "freundlich")
        self.listen_loop()

    def ensure_model(self):
        import requests
        try:
            have = [m["name"] for m in requests.get("http://127.0.0.1:11434/api/tags", timeout=5).json().get("models", [])]
            if not any(h.startswith(self.settings["model"]) for h in have):
                self.bridge.status.emit(f"Lade Modell {self.settings['model']} (einmalig, einige Minuten) …")
                requests.post("http://127.0.0.1:11434/api/pull", json={"name": self.settings["model"], "stream": False}, timeout=7200)
        except Exception:
            pass

    # ---------- Zuhören ----------
    def listen_loop(self):
        s = self.settings
        while True:
            if not s["listen_enabled"] or self.speaker.speaking or self.busy.locked():
                time.sleep(0.2); continue
            try:
                audio = self.listener.record_utterance(max_wait=30)
                if audio is None:
                    continue
                text = self.listener.transcribe(audio)
            except Exception as e:
                self.bridge.status.emit(f"Mikrofonfehler: {type(e).__name__}"); time.sleep(2); continue
            if not text:
                continue
            follow = time.time() - self.last_interaction < s["followup_seconds"]
            cmd = find_wake_word(text, s["wake_words"])
            if cmd is None:
                if not follow:
                    continue
                cmd = text
            if not cmd.strip():
                self.speak_async("Ja, Master?", "freundlich"); time.sleep(0.8)
                audio = self.listener.record_utterance(max_wait=8)
                if audio is None:
                    continue
                cmd = self.listener.transcribe(audio)
                if not cmd.strip():
                    continue
            self.handle(cmd)

    # ---------- Verarbeiten ----------
    def submit_text(self, text):
        threading.Thread(target=self.handle, args=(text,), daemon=True).start()

    def handle(self, text):
        low = text.lower().strip(" .!?")
        if low in STOP_WORDS:
            self.stop_all(); return
        if not self.busy.acquire(blocking=False):
            return
        try:
            b = self.bridge
            b.chat.emit("user", text); b.heard.emit(f"„{text}“"); b.status.emit("Denke …")
            log_action(f"INPUT {text[:80]}")
            res = self.brain.ask(text)
            speech, emo = res.get("speech", ""), res.get("emotion", "neutral")
            tools = list(self.brain.last_tools)
            cat = next((c for c, names in CAT_BY_TOOL.items() if any(t in names for t in tools)), "Chat")
            self.memory.log_history(text, cat)
            pid = self.settings.get("active_project")
            if pid:
                self.memory.bump_project(pid)
            b.emotion.emit(emo); b.chat.emit("yavis", speech); b.heard.emit(speech); b.refresh.emit()
            b.status.emit("Spreche …")
            self.listener.paused.set()
            self.music.send("duck", "1")
            self.speaker.speak(speech, emo)
            self.music.send("duck", "0")
            self.turn += 1
            threading.Thread(target=self._learn, args=(text, speech), daemon=True).start()
        finally:
            self.listener.paused.clear(); self.last_interaction = time.time()
            self.bridge.emotion.emit("neutral"); self.bridge.status.emit("Bereit – sag „YAVIS“"); self.busy.release()

    def _learn(self, text, speech):
        added = self.brain.learn(text, speech)
        if added:
            log_action("GELERNT " + " | ".join(added))
            self.bridge.refresh.emit()

    def speak_async(self, text, emo="neutral"):
        def run():
            self.music.send("duck", "1"); self.speaker.speak(text, emo); self.music.send("duck", "0")
        threading.Thread(target=run, daemon=True).start()

    def check_reminders(self):
        for t in self.memory.due_reminders():
            self.set_status(f"Erinnerung: {t}")
            self.speak_async(f"Master, Erinnerung: {t}", "freundlich")

    # ---------- Bestätigung / Steuerung ----------
    def ask_confirm(self, desc):
        self.confirm_evt.clear(); self.bridge.confirm.emit(desc)
        return self.confirm_evt.wait(120) and self.confirm_ans[0]

    def show_confirm(self, desc):
        r = QMessageBox.question(self, "Bestätigung nötig", f"YAVIS möchte ausführen:\n\n{desc}\n\nErlauben?")
        self.confirm_ans[0] = (r == QMessageBox.Yes); self.confirm_evt.set()

    def stop_all(self):
        self.brain.stop_event.set(); self.speaker.stop(); self.set_status("Gestoppt.")

    def toggle_mic(self):
        self.settings["listen_enabled"] = not self.settings["listen_enabled"]
        self.set_status("Zuhören an" if self.settings["listen_enabled"] else "Zuhören aus")


def main():
    app = QApplication(sys.argv)
    w = Main(); w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
