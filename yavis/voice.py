"""Spracherkennung (faster-whisper, lokal) und Sprachausgabe (Edge-Stimmen / Windows-Offline-Stimme)."""
import asyncio, ctypes, difflib, os, re, tempfile, threading, time
import numpy as np

from .config import VOICES

SR = 16000

# Gefühl -> (Tempo, Tonhöhe) für Edge-TTS
EMOTION_PROSODY = {
    "neutral": ("+0%", "+0Hz"), "freundlich": ("+3%", "+2Hz"), "lieb": ("-6%", "+4Hz"),
    "froehlich": ("+10%", "+6Hz"), "traurig": ("-14%", "-6Hz"), "boese": ("+8%", "-8Hz"),
}


def find_wake_word(text: str, wake_words):
    """Gibt den Text NACH dem Aktivierungswort zurück, oder None. Toleriert Erkennungsfehler."""
    t = re.sub(r"[^\w\säöüß]", " ", text.lower())
    words = t.split()
    for i, w in enumerate(words):
        for ww in wake_words:
            if w == ww or difflib.SequenceMatcher(None, w, ww).ratio() >= 0.8:
                return " ".join(words[i + 1:])
    return None


class Listener:
    def __init__(self, settings, level_cb=lambda x: None):
        self.s, self.level_cb = settings, level_cb
        self.model = None
        self.paused = threading.Event()   # pausiert, solange YAVIS spricht
        self.noise = 0.01

    def load(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(self.s["whisper_model"], device="cpu", compute_type="int8")

    def record_utterance(self, max_wait=None, max_len=20):
        """Nimmt auf, bis Stille. Gibt float32-Array oder None zurück."""
        import sounddevice as sd
        frames, pre, started, silent, t0 = [], [], False, 0, time.time()
        block = int(SR * 0.1)
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=block) as st:
            while True:
                data, _ = st.read(block)
                if self.paused.is_set():
                    frames, started, silent = [], False, 0
                    continue
                chunk = data[:, 0]
                lvl = float(np.sqrt(np.mean(chunk ** 2)))
                self.level_cb(min(1.0, lvl * 12))
                if not started:
                    self.noise = 0.95 * self.noise + 0.05 * lvl
                thr = max(0.012, self.noise * 3)
                if lvl > thr:
                    started, silent = True, 0
                elif started:
                    silent += 1
                if started:
                    if pre:
                        frames, pre = pre + frames, []   # kurzer Vorlauf, damit der Anfang nicht fehlt
                    frames.append(chunk)
                    if silent >= 8 or len(frames) > max_len * 10:   # 0,8 s Stille
                        break
                elif max_wait and time.time() - t0 > max_wait:
                    return None
                else:
                    pre = (pre + [chunk])[-3:]
        audio = np.concatenate(frames) if frames else None
        return audio if audio is not None and len(audio) > SR * 0.3 else None

    def transcribe(self, audio) -> str:
        prompt = "YAVIS, Master. " + ", ".join(self.s["wake_words"]) + "."
        segs, _ = self.model.transcribe(audio, language="de", beam_size=5, vad_filter=True,
                                        initial_prompt=prompt, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs).strip()


class Speaker:
    def __init__(self, settings, level_cb=lambda x: None):
        self.s, self.level_cb = settings, level_cb
        self._stop = threading.Event()
        self.speaking = False

    def stop(self):
        self._stop.set()
        ctypes.windll.winmm.mciSendStringW("close yavis", None, 0, None) if os.name == "nt" else None

    def speak(self, text: str, emotion="neutral"):
        if not text.strip():
            return
        self._stop.clear()
        self.speaking = True
        pulse = threading.Thread(target=self._pulse, daemon=True)
        pulse.start()
        try:
            if self.s["tts_engine"] == "edge":
                try:
                    self._speak_edge(text, emotion)
                    return
                except Exception:
                    pass  # kein Internet -> Offline-Stimme
            self._speak_offline(text, emotion)
        finally:
            self.speaking = False
            self.level_cb(0)

    def _pulse(self):  # Orb-Bewegung beim Sprechen (Sprechrhythmus-Simulation)
        t = 0.0
        while self.speaking:
            t += 0.09
            self.level_cb(0.35 + 0.3 * abs(np.sin(t * 3.1)) + 0.25 * np.random.rand())
            time.sleep(0.05)

    def _speak_edge(self, text, emotion):
        import edge_tts
        voice = VOICES.get(self.s["voice"], "de-DE-KatjaNeural")
        rate, pitch = EMOTION_PROSODY.get("neutral" if self.s["neutral"] else emotion, ("+0%", "+0Hz"))
        path = os.path.join(tempfile.gettempdir(), "yavis_tts.mp3")

        async def gen():
            await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(path)
        asyncio.run(gen())
        if self._stop.is_set():
            return
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close yavis", None, 0, None)
        mci(f'open "{path}" type mpegvideo alias yavis', None, 0, None)
        mci("play yavis", None, 0, None)
        buf = ctypes.create_unicode_buffer(32)
        while not self._stop.is_set():
            mci("status yavis mode", buf, 32, None)
            if buf.value != "playing":
                break
            time.sleep(0.05)
        mci("close yavis", None, 0, None)

    def _speak_offline(self, text, emotion):
        import pyttsx3
        eng = pyttsx3.init()
        want_male = self.s["voice"].startswith("Mann")
        for v in eng.getProperty("voices"):
            n = v.name.lower()
            if ("german" in n or "deutsch" in n or "de-de" in n) and (("stefan" in n or "markus" in n) == want_male):
                eng.setProperty("voice", v.id)
                break
        eng.setProperty("rate", 175)
        eng.say(text)
        eng.runAndWait()
