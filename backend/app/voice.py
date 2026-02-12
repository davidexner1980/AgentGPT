from __future__ import annotations

import io
import os
import subprocess
import sys
from typing import Any

from .models import VoiceConfig


class VoicePipeline:
    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._whisper_model = None

    def _load_whisper(self) -> Any:
        if self._whisper_model is not None:
            return self._whisper_model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("faster-whisper is not installed") from exc
        self._whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
        return self._whisper_model

    def transcribe(self, audio_bytes: bytes) -> dict[str, Any]:
        model = self._load_whisper()
        audio_stream = io.BytesIO(audio_bytes)
        segments, info = model.transcribe(audio_stream, beam_size=5)
        transcript = "".join(segment.text for segment in segments)
        return {
            "text": transcript.strip(),
            "language": info.language,
            "segments": [
                {"start": segment.start, "end": segment.end, "text": segment.text}
                for segment in segments
            ],
        }

    def speak(self, text: str) -> bytes:
        if self.config.piper_path and self.config.piper_model:
            return self._speak_piper(text)
        if sys.platform.startswith("win"):
            return self._speak_sapi(text)
        raise RuntimeError("No TTS backend configured")

    def _speak_piper(self, text: str) -> bytes:
        if not self.config.piper_path or not self.config.piper_model:
            raise RuntimeError("Piper not configured")
        if not os.path.exists(self.config.piper_path):
            raise RuntimeError("Piper binary not found")
        process = subprocess.run(
            [self.config.piper_path, "--model", self.config.piper_model, "--output_file", "-"],
            input=text.encode("utf-8"),
            capture_output=True,
            check=False,
        )
        if process.returncode != 0:
            raise RuntimeError(process.stderr.decode("utf-8", errors="ignore"))
        return process.stdout

    def _speak_sapi(self, text: str) -> bytes:
        try:
            import pyttsx3
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("pyttsx3 not installed for SAPI fallback") from exc
        engine = pyttsx3.init()
        stream = io.BytesIO()
        engine.save_to_file(text, "output.wav")
        engine.runAndWait()
        if not os.path.exists("output.wav"):
            raise RuntimeError("Failed to synthesize speech")
        with open("output.wav", "rb") as handle:
            data = handle.read()
        os.remove("output.wav")
        return data
