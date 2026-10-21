"""Musikplayer (Qt Multimedia). Befehle kommen thread-sicher per Signal von den Werkzeugen."""
import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

from .tools import scan_music


class MusicController(QObject):
    command = Signal(str, str)
    changed = Signal()

    def __init__(self, settings):
        super().__init__()
        self.s = settings
        self.player, self.out = QMediaPlayer(), QAudioOutput()
        self.player.setAudioOutput(self.out)
        self.queue, self.idx, self.ducked = [], -1, False
        self._lib, self._lib_t = [], 0.0
        self._apply_volume()
        self.player.mediaStatusChanged.connect(self._on_status)
        self.command.connect(self._on_command)

    # --- von jedem Thread aufrufbar ---
    def send(self, cmd, arg=""):
        self.command.emit(cmd, arg)

    def library(self, force=False):
        if force or time.time() - self._lib_t > 120:
            self._lib, self._lib_t = scan_music(self.s["music_folders"]), time.time()
        return self._lib

    def status(self):
        if 0 <= self.idx < len(self.queue):
            state = "Pause" if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState else "Spielt"
            return f"{state}: {Path(self.queue[self.idx]).stem}"
        return "Es läuft keine Musik."

    def is_playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    # --- nur im Hauptthread ---
    def _apply_volume(self):
        self.out.setVolume(self.s["music_volume"] / 100 * (0.25 if self.ducked else 1.0))

    def _play(self):
        if 0 <= self.idx < len(self.queue):
            self.player.setSource(QUrl.fromLocalFile(self.queue[self.idx]))
            self.player.play()
            self.changed.emit()

    def _on_status(self, st):
        if st == QMediaPlayer.MediaStatus.EndOfMedia:
            self._on_command("next", "")

    def _on_command(self, cmd, arg):
        if cmd == "playlist":
            self.queue, self.idx = [p for p in arg.split("\n") if p], 0
            self._play()
        elif cmd == "pause":
            self.player.pause()
        elif cmd == "resume":
            self.player.play()
        elif cmd == "next" and self.queue:
            self.idx = (self.idx + 1) % len(self.queue)
            self._play()
        elif cmd == "prev" and self.queue:
            self.idx = (self.idx - 1) % len(self.queue)
            self._play()
        elif cmd == "stop":
            self.player.stop()
            self.queue, self.idx = [], -1
        elif cmd == "volume":
            self.s["music_volume"] = int(arg)
            self._apply_volume()
        elif cmd == "duck":
            self.ducked = (arg == "1") and self.s["duck_music"]
            self._apply_volume()
        self.changed.emit()
