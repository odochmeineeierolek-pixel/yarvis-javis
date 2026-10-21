import os, sys, tempfile, time, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["APPDATA"] = tempfile.mkdtemp()

from yavis import permissions as P, tools as T, llm, memory as M
from yavis.config import Settings, VOICE_PRESETS, PERM_CATEGORIES
from yavis.fastpath import route
from yavis.voice import find_wake_word, prosody


def make():
    s, mem = Settings(), M.Memory(Path(tempfile.mkdtemp()) / "m.db")
    ctx = T.Ctx(s, mem)
    reg = T.build_registry(ctx)
    return s, mem, ctx, reg, llm.Brain(s, mem, reg, ctx, lambda d: True)


class Permissions(unittest.TestCase):
    def test_confirm(self):
        for n in ("buy", "pay", "send_message", "delete_file", "publish_listing", "shutdown_pc", "restart_pc", "close_app"):
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

    def test_app_modes(self):
        s = Settings()
        s["blocked_apps"] = ["steam"]
        self.assertFalse(P.app_allowed("steam", s)); self.assertTrue(P.app_allowed("chrome", s))
        s["app_mode"], s["allowed_apps"] = "allowlist", ["chrome"]
        self.assertTrue(P.app_allowed("chrome", s)); self.assertFalse(P.app_allowed("steam", s))

    def test_dangerous_defaults_off(self):
        s = Settings()
        self.assertFalse(s["perms"]["control"]); self.assertFalse(s["perms"]["clipboard"])


class Tools(unittest.TestCase):
    def test_registry(self):
        _, _, _, reg, _ = make()
        self.assertGreaterEqual(len(reg), 60)
        for bad in ("shell", "run_command", "exec", "cmd"):
            self.assertNotIn(bad, reg)
        for t in reg.values():
            self.assertIn(t.cat, PERM_CATEGORIES)

    def test_match(self):
        items = {"google chrome": 1, "steam": 2, "visual studio code": 3}
        self.assertEqual(T.match_name("chrome", items), "google chrome")
        self.assertEqual(T.match_name("stema", items), "steam")
        self.assertIsNone(T.match_name("zzzzqqq", items))

    def test_calc(self):
        self.assertEqual(T.safe_calc("12*7+3"), 87); self.assertEqual(T.safe_calc("2 plus 3 mal 4"), 14)
        with self.assertRaises(Exception): T.safe_calc("__import__('os').system('x')")
        with self.assertRaises(Exception): T.safe_calc("9**9999")

    def test_music_scan(self):
        d = tempfile.mkdtemp(); (Path(d) / "a.mp3").write_text("x"); (Path(d) / "b.txt").write_text("x")
        self.assertEqual(len(T.scan_music([d])), 1)

    def test_files_sandbox(self):
        s, _, ctx, reg, _ = make()
        s["folders"] = [tempfile.mkdtemp()]
        outside = Path(tempfile.mkdtemp()) / "geheim.txt"; outside.write_text("x")
        self.assertIn("nicht", reg["read_text_file"].func(str(outside)))
        inside = Path(s["folders"][0]) / "ok.txt"; inside.write_text("hallo")
        self.assertEqual(reg["read_text_file"].func(str(inside)), "hallo")
        ctx.granted.add(str(outside))
        self.assertEqual(reg["read_text_file"].func(str(outside)), "x")

    def test_hotkey_allowlist(self):
        _, _, _, reg, _ = make()
        self.assertIn("nicht erlaubt", reg["press_hotkey"].func("ctrl+alt+delete"))

    def test_reminders_tasks(self):
        _, mem, _, reg, _ = make()
        reg["set_timer"].func(0.01, "Nudeln"); time.sleep(0.05)
        self.assertEqual(mem.due_reminders(), ["Nudeln ist abgelaufen"]); self.assertEqual(mem.due_reminders(), [])
        reg["add_task"].func("Steuer machen"); self.assertIn("Steuer", reg["list_tasks"].func())
        reg["complete_task"].func("Steuer"); self.assertIn("Keine", reg["list_tasks"].func())
        self.assertIn("HH:MM", reg["set_reminder"].func("x", at="25:99"))

    def test_voice_switch(self):
        s, _, _, reg, _ = make()
        reg["switch_voice"].func("butler"); self.assertEqual(s["voice"], "Butler – gediegen")
        reg["switch_voice"].func("mama"); self.assertTrue(s["voice"].startswith("Mama"))


class Brain(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(llm.parse_reply('Hier: {"speech":"Hallo","emotion":"lieb","tool":null,"args":{}}')["emotion"], "lieb")
        self.assertEqual(llm.parse_reply("kein json")["emotion"], "neutral")
        self.assertEqual(llm.parse_reply('{"speech":"x","emotion":"quatsch"}')["emotion"], "neutral")

    def test_run_tool_rules(self):
        s, mem, _, reg, b = make()
        self.assertIn("Unbekannt", b.run_tool("rm_rf", {}))
        self.assertIn("Ungültig", b.run_tool("get_time", {"x": 1}))
        s["perms"]["control"] = False
        self.assertIn("ausgeschaltet", b.run_tool("type_text", {"text": "hi"}))
        s["disabled_tools"].append("get_time")
        self.assertIn("ausgeschaltet", b.run_tool("get_time", {}))

    def test_confirmation_refused(self):
        s, mem, ctx, reg, _ = make()
        b = llm.Brain(s, mem, reg, ctx, lambda d: False)
        self.assertIn("abgelehnt", b.run_tool("shutdown_pc", {}))

    def test_prompt_only_enabled_tools(self):
        s, mem, _, reg, _ = make()
        s["perms"]["web"] = False
        p = llm.build_system_prompt(reg, s, mem)
        self.assertNotIn("- web_search(", p); self.assertIn("- get_time(", p)

    def test_remember_roundtrip(self):
        _, _, _, _, b = make()
        b.run_tool("remember", {"text": "Master mag Kaffee"})
        self.assertIn("Kaffee", b.run_tool("recall", {"query": "Kaffee"}))

    def test_fastpath_runs_without_llm(self):
        _, _, _, _, b = make()
        b.ctx.s["perms"]["system"] = True
        r = b.ask("Wie spät ist es?")
        self.assertIn("Es ist", r["speech"]); self.assertEqual(b.last_tools, ["get_time"])

    def test_routine(self):
        _, mem, _, _, b = make()
        mem.save_routine("Test", "testroutine", [{"tool": "flip_coin", "args": {}}])
        self.assertIn("Routine Test", b.ask("testroutine")["speech"])

    def test_learn_filters_sensitive(self):
        _, mem, _, _, b = make()
        b._chat = lambda *a, **k: '{"facts":["Master hört gern Rock","Passwort ist 123456","Master hört gern Rock"]}'
        added = b.learn("Ich höre abends gern Rock und mein Passwort ist 123456", "ok")
        self.assertEqual(added, ["Master hört gern Rock"])


class Fastpath(unittest.TestCase):
    def test_routes(self):
        self.assertEqual(route("öffne youtube")["tool"], "open_website")
        self.assertEqual(route("öffne den Chrome")["args"], {"name": "chrome"})
        self.assertEqual(route("Spiel Musik")["tool"], "play_music")
        self.assertEqual(route("spiel Metallica")["args"], {"query": "metallica"})
        self.assertEqual(route("pause")["tool"], "pause_music")
        self.assertEqual(route("nächstes Lied")["tool"], "next_track")
        self.assertEqual(route("stelle einen timer auf fünf minuten")["args"], {"seconds": 300})
        self.assertEqual(route("such auf youtube nach lofi")["args"], {"query": "lofi"})
        self.assertEqual(route("öffne downloads")["tool"], "open_folder")
        self.assertIsNone(route("erzähl mir einen witz"))


class Voice(unittest.TestCase):
    def test_wake(self):
        w = ["yavis", "jarvis"]
        self.assertEqual(find_wake_word("Yavis öffne YouTube", w), "öffne youtube")
        self.assertEqual(find_wake_word("Davis öffne", w), "öffne")
        self.assertIsNone(find_wake_word("hallo wie geht es", w))

    def test_prosody_and_voices(self):
        self.assertGreaterEqual(len(VOICE_PRESETS), 12)
        s = Settings(); s["voice"], s["emotions"], s["neutral"] = "Butler – gediegen", True, False
        v, r, p = prosody(s, "traurig")
        self.assertEqual(v, "de-DE-ConradNeural"); self.assertEqual((r, p), ("-24%", "-16Hz"))
        s["neutral"] = True
        self.assertEqual(prosody(s, "boese")[1:], ("-10%", "-10Hz"))


class Memory(unittest.TestCase):
    def test_kinds_and_projects(self):
        mem = M.Memory(Path(tempfile.mkdtemp()) / "m.db")
        mem.add("a", "gelernt"); mem.add("n", "feedback"); mem.add("f")
        self.assertEqual([t for _, t in mem.all()], ["a", "f"])
        mem.clear("gelernt"); self.assertEqual([t for _, t in mem.all()], ["f"])
        self.assertEqual(len(mem.projects()), 4); self.assertTrue(mem.routines())


if __name__ == "__main__":
    unittest.main()
