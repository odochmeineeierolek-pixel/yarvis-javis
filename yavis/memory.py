"""Lokales, dauerhaftes Gedächtnis (SQLite). Nur freigegebene Infos."""
import sqlite3, time
from .config import DB_FILE


class Memory:
    def __init__(self, path=DB_FILE):
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY, text TEXT NOT NULL, created REAL)")
        self.db.commit()

    def add(self, text: str) -> int:
        text = text.strip()[:500]
        if not text:
            raise ValueError("Leerer Eintrag")
        cur = self.db.execute("INSERT INTO memories(text, created) VALUES(?,?)", (text, time.time()))
        self.db.commit()
        return cur.lastrowid

    def all(self):
        return self.db.execute("SELECT id, text FROM memories ORDER BY id").fetchall()

    def search(self, query: str, limit=10):
        return self.db.execute("SELECT id, text FROM memories WHERE text LIKE ? LIMIT ?",
                               (f"%{query.strip()}%", limit)).fetchall()

    def delete(self, mem_id: int):
        self.db.execute("DELETE FROM memories WHERE id=?", (mem_id,))
        self.db.commit()

    def clear(self):
        self.db.execute("DELETE FROM memories")
        self.db.commit()
