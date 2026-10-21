"""Spracherkennung (faster-whisper, lokal) und Sprachausgabe (Edge-Stimmen / Windows-Offline-Stimme)."""
import asyncio, ctypes, difflib, os, queue, re, tempfile, threading, time
import numpy as np

from .config import VOICE_PRESETS, MALE_VOICES

SR = 16000
EMOTION_PROSODY = {  # Gefühl -> (Tempo %, Tonhöhe Hz)
    "neutral": (0, 0), "freundlich": (3, 2), "lieb": (-6, 4), "froehlich": (10, 6), "traurig": (-14, -6), "boese": (8, -8)}


def _num(s):
    return int(re.sub(r"[^\d+-]", "", s) or 0)


def prosody(settings, emotion):
    """Preset + Gefühl + Regler -> (rate, pitch) im Edge-Format."""
    voice, r, p = VOICE_PRESETS.get(settings["voice"], ("de-DE-KatjaNeural", "+0%", "+0Hz"))
    er, ep = (0, 0) if (settings["neutral"] or not settings["emotions"]) else EMOTION_PROSODY.get(emotion, (0, 0))
    rate = max(-50, min(50, _num(r) + er + int(settings["voice_speed"])))
    pitch = max(-40, min(40, _num(p) + ep + int(settings["voice_pitch"])))
    return voice, f"{rate:+d}%", f"{pitch:+d}Hz"


def find_wake_word(text: str, wake_words):
    """Text NACH dem Aktivierungswort oder None. Toleriert Erkennungsfehler."""
    words = re.sub(r"[^\w\säöüß]", " ", text.lower()).split()
    for i, w in enumerate(words):
        for ww in wake_words:
            if w == ww or difflib.SequenceMatcher(None, w, ww).ratio() >= 0.8:
                return " ".join(words[i + 1:])
    return None


def list_input_devices():
    try:
        import sounddevice as sd
        return [(i, d["name"]) for i, d in enumerate(sd.query_devices()) if d["max_input_channels"] > 0]
    except Exception:
        return []


class Listener:
    def __init__(self, settings, level_cb=lambda x: None):
        self.s, self.level_cb = settings, level_cb
        self.model = None
        self.paused = threading.Event()
        self.noise = 0.01

    def load(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(self.s["whisper_model"], device="cpu", compute_type="int8")

    def record_utterance(self, max_wait=None, max_len=20):
        import sounddevice as sd
        frames, pre, started, silent, t0 = [], [], False, 0, time.time()
        block = int(SR * 0.1)
        with sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=block, device=self.s["mic_device"]) as st:
            while True:
                data, _ = st.read(block)
                if self.paused.is_set():
                    frames, pre, started, silent = [], [], False, 0
                    continue
                chunk = data[:, 0]
                lvl = float(np.sqrt(np.mean(chunk ** 2)))
                self.level_cb(min(1.0, lvl * 12))
                if not started:
                    self.noise = 0.95 * self.noise + 0.05 * lvl
                if lvl > max(0.012, self.noise * float(self.s["sensitivity"])):
                    started, silent = True, 0
                elif started:
                    silent += 1
                if started:
                    if pre:
                        frames, pre = pre + frames, []
                    frames.append(chunk)
                    if silent >= 7 or len(frames) > max_len * 10:
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
        return " ".join(x.text.strip() for x in segs).strip()


class Speaker:
    def __init__(self, settings, level_cb=lambda x: None):
        self.s, self.level_cb = settings, level_cb
        self._stop = threading.Event()
        self.speaking = False

    def stop(self):
        self._stop.set()
        if os.name == "nt":
            ctypes.windll.winmm.mciSendStringW("close yavis", None, 0, None)

    def speak(self, text, emotion="neutral"):
        if not text.strip():
            return
        self._stop.clear()
        self.speaking = True
        threading.Thread(target=self._pulse, daemon=True).start()
        try:
            if self.s["tts_engine"] == "edge" and self.s["voice"] != "Windows-Stimme (offline)":
                try:
                    self._speak_edge(text, emotion)
                    return
                except Exception:
                    pass
            self._speak_offline(text)
        finally:
            self.speaking = False
            self.level_cb(0)

    def _pulse(self):
        t = 0.0
        while self.speaking:
            t += 0.09
            self.level_cb(0.35 + 0.3 * abs(np.sin(t * 3.1)) + 0.25 * np.random.rand())
            time.sleep(0.05)

    @staticmethod
    async def _gen(text, voice, rate, pitch, path):
        import edge_tts
        await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(path)

    def _speak_edge(self, text, emotion):
        """Satzweise erzeugen und abspielen: Der erste Satz startet sofort (schnelle Antwort)."""
        voice, rate, pitch = prosody(self.s, emotion)
        parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]
        q = queue.Queue()

        def producer():
            for i, part in enumerate(parts):
                if self._stop.is_set():
                    break
                path = os.path.join(tempfile.gettempdir(), f"yavis_{os.getpid()}_{i}.mp3")
                try:
                    asyncio.run(self._gen(part, voice, rate, pitch, path))
                    q.put(path)
                except Exception as e:
                    q.put(e)
                    return
            q.put(None)
        threading.Thread(target=producer, daemon=True).start()
        first = True
        while True:
            item = q.get()
            if item is None or self._stop.is_set():
                break
            if isinstance(item, Exception):
                if first:
                    raise item
                break
            first = False
            self._play(item)

    def _play(self, path):
        mci = ctypes.windll.winmm.mciSendStringW
        mci("close yavis", None, 0, None)
        mci(f'open "{path}" type mpegvideo alias yavis', None, 0, None)
        mci("play yavis", None, 0, None)
        buf = ctypes.create_unicode_buffer(32)
        while not self._stop.is_set():
            mci("status yavis mode", buf, 32, None)
            if buf.value != "playing":
                break
            time.sleep(0.04)
        mci("close yavis", None, 0, None)

    def _speak_offline(self, text):
        import pyttsx3
        eng = pyttsx3.init()
        male = self.s["voice"] in MALE_VOICES
        for v in eng.getProperty("voices"):
            n = v.name.lower()
            if ("german" in n or "deutsch" in n or "de-de" in n) and (("stefan" in n or "markus" in n) == male):
                eng.setProperty("voice", v.id)
                break
        eng.setProperty("rate", 175 + int(self.s["voice_speed"]))
        eng.say(text)
        eng.runAndWait()
