"""Lokale Datenbank: Gedächtnis, Aufgaben, Erinnerungen, Projekte, Verlauf, Routinen."""
import json, sqlite3, threading, time
from .config import DB_FILE

DEFAULT_PROJECTS = [("Arbeitsalltag", "#e10600", "📅"), ("Lernziele", "#c9a000", "🎓"),
                    ("Reiseplanung", "#ff2d2d", "✈"), ("Health & Fitness", "#ffc400", "♥")]


class Memory:
    def __init__(self, path=DB_FILE):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.lock = threading.RLock()
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, text TEXT NOT NULL, kind TEXT DEFAULT 'fakt', created REAL);
        CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, text TEXT, done INTEGER DEFAULT 0, created REAL);
        CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY, text TEXT, due REAL, fired INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY, name TEXT, notes TEXT DEFAULT '', color TEXT, icon TEXT, chats INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY, text TEXT, cat TEXT, created REAL);
        CREATE TABLE IF NOT EXISTS routines(id INTEGER PRIMARY KEY, name TEXT UNIQUE, trigger TEXT, steps TEXT, on_start INTEGER DEFAULT 0);
        """)
        try:
            self.db.execute("ALTER TABLE memories ADD COLUMN kind TEXT DEFAULT 'fakt'")
        except sqlite3.OperationalError:
            pass
        if not self._q("SELECT 1 FROM projects LIMIT 1"):
            for n, c, i in DEFAULT_PROJECTS:
                self._q("INSERT INTO projects(name,color,icon) VALUES(?,?,?)", (n, c, i))
        if not self._q("SELECT 1 FROM routines LIMIT 1"):
            self.save_routine("Guten Morgen", "guten morgen", [{"tool": "daily_briefing", "args": {}}])
            self.save_routine("Entspannen", "entspannen", [{"tool": "play_music", "args": {"query": ""}}])

    def _q(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args)
            self.db.commit()
            return cur.fetchall() if cur.description else cur.lastrowid

    # --- Gedächtnis ---
    def add(self, text: str, kind="fakt") -> int:
        text = text.strip()[:500]
        if not text:
            raise ValueError("Leerer Eintrag")
        return self._q("INSERT INTO memories(text,kind,created) VALUES(?,?,?)", (text, kind, time.time()))

    def all(self, kind=None):
        if kind:
            return self._q("SELECT id,text FROM memories WHERE kind=? ORDER BY id", (kind,))
        return self._q("SELECT id,text FROM memories WHERE kind!='feedback' ORDER BY id")

    def all_full(self):
        return self._q("SELECT id,text,kind FROM memories ORDER BY id")

    def search(self, query, limit=10):
        return self._q("SELECT id,text FROM memories WHERE text LIKE ? LIMIT ?", (f"%{query.strip()}%", limit))

    def delete(self, mem_id):
        self._q("DELETE FROM memories WHERE id=?", (mem_id,))

    def delete_matching(self, text) -> int:
        rows = self.search(text, 50)
        for i, _ in rows:
            self.delete(i)
        return len(rows)

    def clear(self, kind=None):
        self._q("DELETE FROM memories" + (" WHERE kind=?" if kind else ""), (kind,) if kind else ())

    # --- Aufgaben ---
    def add_task(self, text):
        return self._q("INSERT INTO tasks(text,created) VALUES(?,?)", (text.strip()[:300], time.time()))

    def tasks(self, open_only=True):
        return self._q("SELECT id,text,done FROM tasks" + (" WHERE done=0" if open_only else "") + " ORDER BY id")

    def complete_task(self, text) -> int:
        rows = self._q("SELECT id FROM tasks WHERE done=0 AND text LIKE ?", (f"%{text.strip()}%",))
        for (i,) in rows:
            self._q("UPDATE tasks SET done=1 WHERE id=?", (i,))
        return len(rows)

    # --- Erinnerungen ---
    def add_reminder(self, text, due_ts):
        return self._q("INSERT INTO reminders(text,due) VALUES(?,?)", (text.strip()[:200], due_ts))

    def due_reminders(self, now=None):
        now = now or time.time()
        rows = self._q("SELECT id,text FROM reminders WHERE fired=0 AND due<=?", (now,))
        for i, _ in rows:
            self._q("UPDATE reminders SET fired=1 WHERE id=?", (i,))
        return [t for _, t in rows]

    def reminders(self):
        return self._q("SELECT id,text,due FROM reminders WHERE fired=0 ORDER BY due")

    def clear_reminders(self):
        self._q("DELETE FROM reminders WHERE fired=0")

    # --- Projekte ---
    def projects(self):
        return self._q("SELECT id,name,notes,color,icon,chats FROM projects ORDER BY id")

    def add_project(self, name, color="#e10600", icon="📁"):
        return self._q("INSERT INTO projects(name,color,icon) VALUES(?,?,?)", (name.strip()[:60], color, icon))

    def delete_project(self, pid):
        self._q("DELETE FROM projects WHERE id=?", (pid,))

    def set_project_notes(self, pid, notes):
        self._q("UPDATE projects SET notes=? WHERE id=?", (notes[:2000], pid))

    def bump_project(self, pid):
        self._q("UPDATE projects SET chats=chats+1 WHERE id=?", (pid,))

    def project(self, pid):
        r = self._q("SELECT id,name,notes FROM projects WHERE id=?", (pid,))
        return r[0] if r else None

    # --- Verlauf ---
    def log_history(self, text, cat="Chat"):
        self._q("INSERT INTO history(text,cat,created) VALUES(?,?,?)", (text[:120], cat, time.time()))

    def recent_history(self, n=4):
        return self._q("SELECT text,cat,created FROM history ORDER BY id DESC LIMIT ?", (n,))

    # --- Routinen ---
    def save_routine(self, name, trigger, steps, on_start=0):
        self._q("INSERT OR REPLACE INTO routines(name,trigger,steps,on_start) VALUES(?,?,?,?)",
                (name.strip(), trigger.strip().lower(), json.dumps(steps, ensure_ascii=False), int(on_start)))

    def routines(self):
        return [(i, n, t, json.loads(s), o) for i, n, t, s, o in
                self._q("SELECT id,name,trigger,steps,on_start FROM routines ORDER BY id")]

    def delete_routine(self, rid):
        self._q("DELETE FROM routines WHERE id=?", (rid,))
