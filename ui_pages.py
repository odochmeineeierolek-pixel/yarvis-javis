"""Seiten der Oberfläche. Jede Seite bekommt das Hauptfenster `app` (Zugriff auf settings, memory, registry, music)."""
import os, time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QListWidget,
                               QTextBrowser, QPlainTextEdit, QFileDialog, QInputDialog, QMenu, QCheckBox, QScrollArea,
                               QSlider, QFrame, QMessageBox, QGroupBox, QListWidgetItem)

from .config import PERM_CATEGORIES, NOTES_DIR
from .ui_theme import (label, circle_icon, Clickable, GradFrame, Orb, RED, YEL, DIM)

TASK_CARDS = [  # Symbol, Farbe, Titel, Text, Eingabe-Vorlage
    ("💬", "#7a0a0a", "Chat & Fragen", "Erhalte fundierte Antworten, klär komplexe Themen oder lass dir neue Perspektiven geben.", "Erkläre mir: "),
    ("📄", "#6b5200", "Texte schreiben", "Von E-Mails über Blogartikel bis zu Berichten – ich unterstütze dich beim Schreiben.", "Schreibe einen Text über: "),
    ("</>", "#5c4500", "Code & Programmieren", "Schreibe, erkläre oder optimiere Code in vielen Sprachen.", "Schreibe Code für: "),
    ("🧠", "#7a0a0a", "Analysieren & Planen", "Daten auswerten, Strategien entwickeln, Projekte strukturieren.", "Hilf mir zu planen: "),
    ("💡", "#b00000", "Ideen & Kreativität", "Brainstorming, Konzepte, Design-Ideen und mehr.", "Gib mir Ideen für: "),
    ("🎓", "#6b5200", "Lernen & Erklären", "Komplexe Themen einfach erklärt – auf deinem Niveau.", "Erkläre einfach: "),
]
TEMPLATES = {"Angebot entwerfen": "Erstelle einen Entwurf für ein Angebot für: ",
             "Produktbeschreibung": "Schreibe eine Verkaufs-Produktbeschreibung für: ",
             "Preise recherchieren": "Recherchiere aktuelle Preise (mit Quellen) für: ",
             "E-Mail-Entwurf": "Schreibe einen E-Mail-Entwurf an: ",
             "Tagesplan": "Plane meinen Arbeitstag anhand meiner Aufgaben."}
CAT_ICON = {"Chat": ("💬", "#7a0a0a"), "Musik": ("♪", "#6b5200"), "Web": ("🌐", "#7a0a0a"), "Programm": ("▶", "#6b5200"), "Datei": ("📄", "#444")}


def panel(title=None, icon=None):
    f = Clickable(); f.setObjectName("panel")
    lay = QVBoxLayout(f); lay.setContentsMargins(14, 12, 14, 12); lay.setSpacing(6)
    if title:
        row = QHBoxLayout()
        row.addWidget(label((icon + "  " if icon else "") + title, 14, bold=True)); row.addStretch()
        lay.addLayout(row)
    return f, lay


def scroll(widget):
    s = QScrollArea(); s.setWidgetResizable(True); s.setWidget(widget)
    return s


class HomePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        root = QHBoxLayout(self); root.setContentsMargins(24, 16, 16, 12); root.setSpacing(20)
        # ---- Mitte ----
        mid = QVBoxLayout(); mid.setSpacing(12)
        hero = label(f"Hallo! Ich bin <span style='color:{RED}'>Ya</span><span style='color:{YEL}'>vis</span>.", 30, bold=True)
        hero.setAlignment(Qt.AlignCenter)
        sub = label("Was möchtest du heute erledigen, Master?", 16, "#aab0d8"); sub.setAlignment(Qt.AlignCenter)
        mid.addSpacing(10); mid.addWidget(hero); mid.addWidget(sub); mid.addSpacing(8)
        box = GradFrame(); bl = QVBoxLayout(box); bl.setContentsMargins(16, 12, 16, 10)
        self.inp = QLineEdit(); self.inp.setPlaceholderText("Stelle eine Frage, gib mir eine Aufgabe oder sag „YAVIS …“")
        self.inp.returnPressed.connect(self.send)
        bl.addWidget(self.inp)
        tb = QHBoxLayout()
        for txt, fn in (("📎", self.attach), ):
            b = QPushButton(txt); b.setObjectName("flat"); b.clicked.connect(fn); tb.addWidget(b)
        self.web = QPushButton("🌐 Websuche"); self.web.setCheckable(True); self.web.setObjectName("flat"); tb.addWidget(self.web)
        fb = QPushButton("📄 Datei"); fb.setObjectName("flat"); fb.clicked.connect(self.attach); tb.addWidget(fb)
        plus = QPushButton("+"); plus.setObjectName("flat"); plus.clicked.connect(lambda: self.template_menu(plus)); tb.addWidget(plus)
        tb.addStretch()
        go = QPushButton("➤"); go.setObjectName("send"); go.clicked.connect(self.send); tb.addWidget(go)
        bl.addLayout(tb)
        mid.addWidget(box)
        mid.addSpacing(6); mid.addWidget(label("✦  Beliebte Aufgaben", 14, bold=True))
        grid = QGridLayout(); grid.setSpacing(12)
        for i, (ic, col, title, text, tpl) in enumerate(TASK_CARDS):
            c = Clickable(); c.setObjectName("card"); c.setMinimumHeight(112)
            cl = QHBoxLayout(c); cl.setContentsMargins(14, 12, 14, 12); cl.setSpacing(12)
            cl.addWidget(circle_icon(ic, col, 46), 0, Qt.AlignTop)
            v = QVBoxLayout(); v.addWidget(label(title, 13, bold=True))
            d = label(text, 10, DIM); d.setWordWrap(True); v.addWidget(d); v.addStretch()
            cl.addLayout(v, 1); cl.addWidget(label("→", 14, YEL), 0, Qt.AlignTop)
            c.clicked.connect(lambda t=tpl: self.prefill(t))
            grid.addWidget(c, i // 2, i % 2)
        mid.addLayout(grid)
        mid.addSpacing(4); mid.addWidget(label("🕒  Zuletzt verwendet", 14, bold=True))
        self.recent, rl = panel(); self.recent_l = rl; mid.addWidget(self.recent); mid.addStretch()
        root.addLayout(mid, 1)
        # ---- Rechte Spalte ----
        right = QVBoxLayout(); right.setSpacing(12)
        q, ql = panel("Schnellzugriff", "⚡")
        for txt, ic, fn in (("Datei hochladen", "📄", self.attach), ("Websuche starten", "🌐", lambda: self.prefill("Suche im Web nach: ")),
                            ("Neues Projekt", "📁", app.new_project), ("Vorlage nutzen", "📋", lambda: self.template_menu(q)),
                            ("Automatisierung erstellen", "🔧", lambda: app.goto("auto"))):
            r = Clickable(); r.setObjectName("row"); rl2 = QHBoxLayout(r); rl2.setContentsMargins(4, 6, 4, 6)
            rl2.addWidget(label(ic, 15)); rl2.addWidget(label(txt, 12), 1); rl2.addWidget(label("›", 14))
            r.clicked.connect(fn); ql.addWidget(r)
        right.addWidget(q)
        self.proj, self.proj_l = panel("Projekte", "📁"); right.addWidget(self.proj)
        self.stat, self.stat_l = panel(); right.addWidget(self.stat)
        right.addStretch()
        ft = QHBoxLayout(); ft.addWidget(label("〰", 26, RED))
        v = QVBoxLayout(); v.addWidget(label("YAVIS", 13, YEL, True)); v.addWidget(label("Mehr als ein Chatbot.\nDein persönlicher KI-Assistent.", 10))
        ft.addLayout(v); ft.addStretch(); right.addLayout(ft)
        rw = QWidget(); rw.setLayout(right); rw.setFixedWidth(330)
        root.addWidget(rw)

    # --- Aktionen ---
    def prefill(self, text):
        self.inp.setText(text); self.inp.setFocus()

    def send(self):
        t = self.inp.text().strip()
        if not t:
            return
        if self.web.isChecked() and not t.lower().startswith("such"):
            t = "Suche im Web nach: " + t
        self.inp.clear(); self.app.goto("chat"); self.app.submit_text(t)

    def attach(self):
        path, _ = QFileDialog.getOpenFileName(self, "Datei auswählen (YAVIS darf sie lesen)")
        if path:
            self.app.ctx.granted.add(path)
            self.app.goto("chat"); self.app.submit_text(f"Lies die Datei {path} und fasse sie kurz zusammen.")

    def template_menu(self, anchor):
        m = QMenu(self)
        for k, v in TEMPLATES.items():
            m.addAction(k, lambda v=v: self.prefill(v))
        m.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    # --- Daten anzeigen ---
    @staticmethod
    def _clear(lay, keep=1):
        while lay.count() > keep:
            it = lay.takeAt(keep)
            if it.widget():
                it.widget().deleteLater()

    def refresh(self):
        a = self.app
        self._clear(self.recent_l, 0)
        hist = a.memory.recent_history(4)
        for text, cat, ts in hist or [("Noch nichts – sag „YAVIS“ …", "Chat", time.time())]:
            ic, col = CAT_ICON.get(cat, CAT_ICON["Chat"])
            r = QHBoxLayout(); r.addWidget(circle_icon(ic, col, 34))
            v = QVBoxLayout(); v.addWidget(label(text[:60], 12)); v.addWidget(label(cat, 10, DIM)); r.addLayout(v, 1)
            mins = int((time.time() - ts) / 60)
            r.addWidget(label("gerade eben" if mins < 1 else f"vor {mins} Min." if mins < 60 else f"vor {mins // 60} Std." if mins < 1440 else "früher", 10, DIM))
            w = QWidget(); w.setLayout(r); self.recent_l.addWidget(w)
        self._clear(self.proj_l, 1)
        hdr = QHBoxLayout(); hdr.addWidget(label("Meine Projekte", 12)); hdr.addStretch()
        all_ = QPushButton("Alle anzeigen →"); all_.setObjectName("flat"); all_.setStyleSheet(f"color:{YEL}; font-size:11px;")
        all_.clicked.connect(lambda: a.goto("projects")); hdr.addWidget(all_)
        w = QWidget(); w.setLayout(hdr); self.proj_l.addWidget(w)
        for pid, name, notes, col, icon, chats in a.memory.projects()[:4]:
            c = Clickable(); cl = QHBoxLayout(c); cl.setContentsMargins(0, 2, 0, 2)
            cl.addWidget(circle_icon(icon, col, 38))
            v = QVBoxLayout(); v.addWidget(label(name, 12, bold=(pid == a.settings.get("active_project"))))
            v.addWidget(label(f"{chats} Unterhaltungen", 10, DIM)); cl.addLayout(v, 1)
            c.clicked.connect(lambda p=pid: a.select_project(p)); self.proj_l.addWidget(c)
        self._clear(self.stat_l, 0)
        ok = a.ollama_ok
        hd = QHBoxLayout(); hd.addWidget(label("◎  Systemstatus", 14, bold=True)); hd.addStretch()
        hd.addWidget(label(("● " if ok else "● ") + ("Alles läuft" if ok else "Gehirn startet …"), 11, YEL if ok else RED))
        w = QWidget(); w.setLayout(hd); self.stat_l.addWidget(w)
        P = a.settings["perms"]
        for ic, name, on in (("✦", f"Gehirn ({a.settings['model']})", ok), ("🎤", "Spracherkennung", a.listener.model is not None),
                             ("🌐", "Websuche", P["web"]), ("📄", "Dateianalyse", P["files"]), ("♪", "Musik", P["music"]),
                             ("🔧", "Automatisierungen", P["tasks"])):
            r = QHBoxLayout(); r.addWidget(label(ic, 13)); r.addWidget(label(name, 11), 1)
            r.addWidget(label("Aktiv" if on else "Aus", 11, YEL if on else DIM))
            w = QWidget(); w.setLayout(r); self.stat_l.addWidget(w)


class ChatPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.last_user, self.last_reply = app, "", ""
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(label("Chat", 20, bold=True))
        self.view = QTextBrowser(); self.view.setOpenExternalLinks(True); lay.addWidget(self.view, 1)
        fb = QHBoxLayout()
        for txt, good in (("👍 Gut", True), ("👎 Schlecht", False)):
            b = QPushButton(txt); b.clicked.connect(lambda _, g=good: self.rate(g)); fb.addWidget(b)
        fb.addStretch(); lay.addLayout(fb)
        row = QHBoxLayout(); self.inp = QLineEdit(); self.inp.setPlaceholderText("Nachricht an YAVIS …")
        self.inp.returnPressed.connect(self.send); row.addWidget(self.inp, 1)
        go = QPushButton("➤"); go.setObjectName("send"); go.clicked.connect(self.send); row.addWidget(go); lay.addLayout(row)

    def send(self):
        t = self.inp.text().strip()
        if t:
            self.inp.clear(); self.app.submit_text(t)

    def add(self, role, text):
        if role == "user":
            self.last_user = text
        else:
            self.last_reply = text
        who, col = ("Du", YEL) if role == "user" else ("YAVIS", RED)
        self.view.append(f"<p><b style='color:{col}'>{who}:</b> {text}</p>")

    def rate(self, good):
        if self.last_reply:
            self.app.brain.feedback(self.last_user, self.last_reply, good)
            self.app.set_status("Danke, Master – gemerkt." if good else "Verstanden, ich mache es besser.")


class ProjectsPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(label("Projekte", 20, bold=True))
        lay.addWidget(label("Das aktive Projekt gibt YAVIS seine Notizen als Hintergrundwissen mit.", 11, DIM))
        row = QHBoxLayout(); self.list = QListWidget(); self.list.currentRowChanged.connect(self.show_notes); row.addWidget(self.list, 1)
        v = QVBoxLayout(); self.notes = QPlainTextEdit(); self.notes.setPlaceholderText("Notizen / Ziele / Kontext für dieses Projekt …"); v.addWidget(self.notes, 1)
        b = QHBoxLayout()
        for txt, fn, name in (("Notizen speichern", self.save, None), ("Als aktiv wählen", self.activate, "primary"), ("Neu", app.new_project, None), ("Löschen", self.delete, "danger")):
            x = QPushButton(txt); x.clicked.connect(fn)
            if name:
                x.setObjectName(name)
            b.addWidget(x)
        v.addLayout(b); row.addLayout(v, 2); lay.addLayout(row, 1)
        self.rows = []

    def refresh(self):
        self.rows = self.app.memory.projects(); self.list.clear()
        for pid, name, notes, col, icon, chats in self.rows:
            self.list.addItem(f"{icon}  {name}  ({chats})" + ("   ★ aktiv" if pid == self.app.settings.get("active_project") else ""))

    def cur(self):
        i = self.list.currentRow()
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def show_notes(self, _):
        c = self.cur(); self.notes.setPlainText(c[2] if c else "")

    def save(self):
        c = self.cur()
        if c:
            self.app.memory.set_project_notes(c[0], self.notes.toPlainText()); self.app.set_status("Notizen gespeichert.")

    def activate(self):
        c = self.cur()
        if c:
            self.app.select_project(c[0], go=False)

    def delete(self):
        c = self.cur()
        if c and QMessageBox.question(self, "Projekt löschen", f"'{c[1]}' wirklich löschen?") == QMessageBox.Yes:
            self.app.memory.delete_project(c[0]); self.app.refresh_all()


class FilesPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(label("Dateien", 20, bold=True))
        lay.addWidget(label("YAVIS sucht nur in den Ordnern, die du unter Einstellungen → Zugriff freigegeben hast.", 11, DIM))
        row = QHBoxLayout(); self.q = QLineEdit(); self.q.setPlaceholderText("Dateiname suchen …"); self.q.returnPressed.connect(self.search)
        row.addWidget(self.q, 1); b = QPushButton("Suchen"); b.setObjectName("primary"); b.clicked.connect(self.search); row.addWidget(b)
        a = QPushButton("Datei von YAVIS lesen lassen"); a.clicked.connect(app.pages["home"].attach); row.addWidget(a); lay.addLayout(row)
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(self.open_item); lay.addWidget(self.list, 1)
        lay.addWidget(label("Doppelklick öffnet die Datei. Unten: deine Notizen & Entwürfe.", 11, DIM))

    def search(self):
        self.list.clear()
        res = self.app.registry["search_files"].func(self.q.text()) if self.q.text().strip() else ""
        for line in res.split("\n"):
            if line and line != "Nichts gefunden.":
                self.list.addItem(line)

    def refresh(self):
        if not self.q.text().strip():
            self.list.clear()
            for p in sorted(NOTES_DIR.glob("*.txt"), key=lambda x: -x.stat().st_mtime)[:30]:
                self.list.addItem(str(p))

    def open_item(self, it):
        try:
            os.startfile(it.text())
        except Exception:
            pass


class KnowledgePage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(label("Wissen – was YAVIS über dich weiß", 20, bold=True))
        lay.addWidget(label("„fakt“ = von dir gemerkt · „gelernt“ = automatisch gelernt (harmlose Vorlieben) · „feedback“ = 👍/👎. Alles ist löschbar.", 11, DIM))
        self.list = QListWidget(); self.list.setSelectionMode(QListWidget.ExtendedSelection); lay.addWidget(self.list, 1)
        row = QHBoxLayout(); self.new = QLineEdit(); self.new.setPlaceholderText("Neue Info manuell merken …"); self.new.returnPressed.connect(self.add)
        row.addWidget(self.new, 1)
        for txt, fn, nm in (("Merken", self.add, "primary"), ("Auswahl löschen", self.delsel, None), ("Gelerntes löschen", lambda: self.clear("gelernt"), "danger"), ("ALLES löschen", lambda: self.clear(None), "danger")):
            b = QPushButton(txt); b.clicked.connect(fn)
            if nm:
                b.setObjectName(nm)
            row.addWidget(b)
        lay.addLayout(row)
        self.learn = QCheckBox("Automatisch dazulernen (nur harmlose Vorlieben, nie Passwörter/Zahlen/Adressen)")
        self.learn.setChecked(app.settings["auto_learn"]); self.learn.toggled.connect(self.set_learn); lay.addWidget(self.learn)

    def set_learn(self, v):
        self.app.settings["auto_learn"] = v; self.app.settings.save()

    def refresh(self):
        self.list.clear()
        for i, t, k in self.app.memory.all_full():
            it = QListWidgetItem(f"[{k}] {t}"); it.setData(Qt.UserRole, i); self.list.addItem(it)

    def add(self):
        if self.new.text().strip():
            self.app.memory.add(self.new.text()); self.new.clear(); self.refresh()

    def delsel(self):
        for it in self.list.selectedItems():
            self.app.memory.delete(it.data(Qt.UserRole))
        self.refresh()

    def clear(self, kind):
        if QMessageBox.question(self, "Löschen", "Wirklich löschen?") == QMessageBox.Yes:
            self.app.memory.clear(kind); self.refresh()


class ToolsPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        n = len(app.registry)
        lay.addWidget(label(f"Tools – {n} Funktionen", 20, bold=True))
        lay.addWidget(label("Schalte ganze Bereiche oder einzelne Funktionen ein/aus. Gesperrte Funktionen kann YAVIS nicht benutzen.", 11, DIM))
        inner = QWidget(); il = QVBoxLayout(inner)
        s = app.settings
        for cat, title in PERM_CATEGORIES.items():
            g = QGroupBox(); gl = QVBoxLayout(g)
            cb = QCheckBox(title); cb.setChecked(s["perms"].get(cat, False)); cb.setStyleSheet(f"font-weight:600; color:{YEL};")
            cb.toggled.connect(lambda v, c=cat: self.set_perm(c, v)); gl.addWidget(cb)
            for name, t in app.registry.items():
                if t.cat == cat:
                    x = QCheckBox(f"{name} – {t.desc}"); x.setChecked(name not in s["disabled_tools"])
                    x.toggled.connect(lambda v, nm=name: self.set_tool(nm, v)); gl.addWidget(x)
            il.addWidget(g)
        il.addStretch(); lay.addWidget(scroll(inner), 1)

    def set_perm(self, c, v):
        self.app.settings["perms"][c] = v; self.app.settings.save(); self.app.refresh_all()

    def set_tool(self, name, on):
        d = self.app.settings["disabled_tools"]
        if on and name in d:
            d.remove(name)
        elif not on and name not in d:
            d.append(name)
        self.app.settings.save()


class AutoPage(QWidget):
    """Routinen: Stichwort -> Folge von Aktionen. Zeilenformat: werkzeug: argument"""
    def __init__(self, app):
        super().__init__()
        self.app = app
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(label("Automatisierungen", 20, bold=True))
        lay.addWidget(label("Eine Routine startet per Stichwort (z. B. „arbeitsmodus“) mehrere Aktionen nacheinander. Eine Aktion pro Zeile: werkzeug: argument\n"
                            "Beispiel:  open_app: Visual Studio Code   |   open_website: youtube   |   play_music: Lofi", 11, DIM))
        row = QHBoxLayout(); self.list = QListWidget(); self.list.currentRowChanged.connect(self.show); row.addWidget(self.list, 1)
        v = QVBoxLayout()
        self.name = QLineEdit(); self.name.setPlaceholderText("Name"); self.trig = QLineEdit(); self.trig.setPlaceholderText("Stichwort, das du sagst")
        self.steps = QPlainTextEdit(); self.steps.setPlaceholderText("open_app: Chrome\nplay_music:")
        self.start = QCheckBox("Beim Start von YAVIS ausführen")
        for w in (self.name, self.trig, self.steps, self.start):
            v.addWidget(w)
        b = QHBoxLayout()
        for txt, fn, nm in (("Speichern", self.save, "primary"), ("Jetzt ausführen", self.run, None), ("Löschen", self.delete, "danger")):
            x = QPushButton(txt); x.clicked.connect(fn)
            if nm:
                x.setObjectName(nm)
            b.addWidget(x)
        v.addLayout(b); row.addLayout(v, 2); lay.addLayout(row, 1)
        lay.addWidget(label("Erinnerungen / Timer", 14, bold=True)); self.rem = QListWidget(); self.rem.setMaximumHeight(110); lay.addWidget(self.rem)
        self.rows = []

    def refresh(self):
        self.rows = self.app.memory.routines(); self.list.clear()
        for _, n, t, steps, o in self.rows:
            self.list.addItem(f"{n}   («{t}»)")
        self.rem.clear()
        from datetime import datetime
        for _, t, d in self.app.memory.reminders():
            self.rem.addItem(f"{datetime.fromtimestamp(d):%d.%m. %H:%M} – {t}")

    def show(self, i):
        if 0 <= i < len(self.rows):
            _, n, t, steps, o = self.rows[i]
            self.name.setText(n); self.trig.setText(t); self.start.setChecked(bool(o))
            lines = []
            for st in steps:
                a = st.get("args", {}); lines.append(f"{st['tool']}: {next(iter(a.values()), '')}")
            self.steps.setPlainText("\n".join(lines))

    def parse(self):
        out = []
        for line in self.steps.toPlainText().splitlines():
            if not line.strip():
                continue
            tool, _, arg = line.partition(":")
            tool, arg = tool.strip(), arg.strip()
            t = self.app.registry.get(tool)
            if not t:
                raise ValueError(f"Unbekanntes Werkzeug: {tool}")
            first = t.args.split(",")[0].strip()
            out.append({"tool": tool, "args": ({first: arg} if first and arg != "" else ({first: ""} if first else {}))})
        return out

    def save(self):
        try:
            steps = self.parse()
        except ValueError as e:
            QMessageBox.warning(self, "Fehler", str(e)); return
        if self.name.text().strip():
            self.app.memory.save_routine(self.name.text(), self.trig.text() or self.name.text(), steps, int(self.start.isChecked())); self.refresh()

    def run(self):
        try:
            steps = self.parse()
        except ValueError as e:
            QMessageBox.warning(self, "Fehler", str(e)); return
        import threading
        threading.Thread(target=lambda: [self.app.brain.run_tool(s["tool"], s["args"]) for s in steps], daemon=True).start()

    def delete(self):
        i = self.list.currentRow()
        if 0 <= i < len(self.rows):
            self.app.memory.delete_routine(self.rows[i][0]); self.refresh()


class MusicPage(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app, self.m = app, app.music
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        lay.addWidget(label("Musik", 20, bold=True))
        lay.addWidget(label("Sag: „YAVIS, spiel Musik“, „spiel <Titel>“, „pause“, „nächstes Lied“, „leiser“ – oder bediene den Player hier.", 11, DIM))
        self.now = label("Es läuft keine Musik.", 15, YEL, True); lay.addWidget(self.now)
        row = QHBoxLayout()
        for txt, cmd in (("⏮", "prev"), ("⏯", "toggle"), ("⏭", "next"), ("⏹", "stop")):
            b = QPushButton(txt); b.clicked.connect(lambda _, c=cmd: self.cmd(c)); row.addWidget(b)
        row.addWidget(label("🔊")); vol = QSlider(Qt.Horizontal); vol.setRange(0, 100); vol.setValue(app.settings["music_volume"])
        vol.valueChanged.connect(lambda v: self.m.send("volume", str(v))); row.addWidget(vol, 1); lay.addLayout(row)
        self.list = QListWidget(); self.list.itemDoubleClicked.connect(self.play_item); lay.addWidget(self.list, 1)
        r2 = QHBoxLayout()
        for txt, fn in (("📁 Musikordner hinzufügen", self.add_folder), ("🎵 Dateien hinzufügen", self.add_files), ("🔀 Zufallsmix", self.mix), ("🔄 Neu einlesen", self.refresh)):
            b = QPushButton(txt); b.clicked.connect(fn); r2.addWidget(b)
        lay.addLayout(r2)
        self.m.changed.connect(self.update_now)

    def cmd(self, c):
        if c == "toggle":
            c = "pause" if self.m.is_playing() else "resume"
        self.m.send(c, "")

    def update_now(self):
        self.now.setText("♪ " + self.m.status())

    def refresh(self):
        self.lib = self.m.library(force=True); self.list.clear()
        for p in self.lib[:1500]:
            self.list.addItem(Path(p).stem)

    def play_item(self, it):
        i = self.list.row(it); self.m.send("playlist", "\n".join(self.lib[i:i + 200] + self.lib[:i]))

    def mix(self):
        import random
        self.m.send("playlist", "\n".join(random.sample(self.lib, min(200, len(self.lib))))) if self.lib else None

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Musikordner wählen")
        if d and d not in self.app.settings["music_folders"]:
            self.app.settings["music_folders"].append(d); self.app.settings.save(); self.refresh()

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Musikdateien wählen", "", "Audio (*.mp3 *.wav *.flac *.ogg *.m4a *.wma *.aac)")
        if files:
            self.m.send("playlist", "\n".join(files))


class OrbPage(QWidget):
    def __init__(self, app):
        super().__init__()
        lay = QVBoxLayout(self); lay.setContentsMargins(24, 16, 24, 16)
        self.orb = Orb(); lay.addWidget(self.orb, 1)
        self.text = label("", 15, YEL); self.text.setAlignment(Qt.AlignCenter); self.text.setWordWrap(True); lay.addWidget(self.text)
