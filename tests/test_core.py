import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APPDATA"] = tempfile.mkdtemp()

from yavis import permissions as P, tools as T, llm, memory as M
from yavis.voice import find_wake_word


class Permissions(unittest.TestCase):
    def test_confirm(self):
        for n in ("buy", "pay", "send_message", "delete_file", "publish_listing"):
            self.assertTrue(P.requires_confirmation(n))
        self.assertFalse(P.requires_confirmation("get_time"))

    def test_path_escape(self):
        root = tempfile.mkdtemp()
        self.assertTrue(P.is_inside(Path(root) / "a.txt", [root]))
        self.assertFalse(P.is_inside(Path(root) / ".." / "x", [root]))

    def test_urls(self):
        self.assertTrue(P.is_safe_url("https://youtube.com"))
        self.assertFalse(P.is_safe_url("file:///C:/Windows"))
        self.assertFalse(P.is_safe_url("javascript:alert(1)"))


class Tools(unittest.TestCase):
    def test_match_app(self):
        items = {"google chrome": "a", "steam": "b", "visual studio code": "c"}
        self.assertEqual(T.match_app("chrome", items), "google chrome")
        self.assertEqual(T.match_app("stema", items), "steam")
        self.assertIsNone(T.match_app("zzzzqqq", items))

    def test_note_name_sanitized(self):
        r = T.write_note("../../evil", "x")
        self.assertIn("Notizen", r)
        self.assertNotIn("..", Path(r.split(": ", 1)[1]).name)

    def test_registry_only_known(self):
        mem = M.Memory(Path(tempfile.mkdtemp()) / "m.db")
        reg = T.build_registry(mem)
        self.assertNotIn("shell", reg)
        self.assertIn("open_app", reg)


class Brain(unittest.TestCase):
    def _brain(self, confirm):
        mem = M.Memory(Path(tempfile.mkdtemp()) / "m.db")
        return llm.Brain({"neutral": False, "model": "x"}, mem, T.build_registry(mem), confirm)

    def test_parse(self):
        d = llm.parse_reply('Hier: {"speech":"Hallo Master","emotion":"lieb","tool":null,"args":{}}')
        self.assertEqual(d["emotion"], "lieb")
        self.assertEqual(llm.parse_reply("kein json")["emotion"], "neutral")
        self.assertEqual(llm.parse_reply('{"speech":"x","emotion":"quatsch"}')["emotion"], "neutral")

    def test_unknown_tool_and_bad_args(self):
        b = self._brain(lambda d: True)
        self.assertIn("Unbekannt", b.run_tool("rm_rf", {}))
        self.assertIn("Ungültig", b.run_tool("get_time", {"x": 1}))

    def test_remember_roundtrip(self):
        b = self._brain(lambda d: True)
        b.run_tool("remember", {"text": "Master mag Kaffee"})
        self.assertIn("Kaffee", b.run_tool("recall", {"query": "Kaffee"}))


class Wake(unittest.TestCase):
    def test_wake(self):
        w = ["yavis", "jarvis"]
        self.assertEqual(find_wake_word("Yavis öffne YouTube", w), "öffne youtube")
        self.assertEqual(find_wake_word("Jarvis, wie spät ist es?", w), "wie spät ist es")
        self.assertEqual(find_wake_word("Davis öffne", w), "öffne")  # Erkennungsfehler toleriert
        self.assertIsNone(find_wake_word("hallo wie geht es", w))


if __name__ == "__main__":
    unittest.main()
