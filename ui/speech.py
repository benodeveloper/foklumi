import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

try:
    import config
    _CONFIG_MODEL = getattr(config, "PIPER_MODEL_DE", "")
except ImportError:
    _CONFIG_MODEL = ""

WIN_SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$v = $s.GetInstalledVoices() | Where-Object "
    "{ $_.VoiceInfo.Culture.Name -like 'de*' } | Select-Object -First 1;"
    "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) };"
    "$s.Rate = -2;"
    "$s.Speak($env:POMO_TEXT)"
)


class Speaker:
    """Speaks German text in a background thread. say() replaces anything
    that is playing; pass a list to speak several texts in a row."""

    def __init__(self, model_path: str = "", speed: float = 1.0):
        self._lock = threading.Lock()
        self._gen = 0
        self._procs = []
        self.engine = None
        self.problem = None
        self._piper = None
        self._model = None
        self._rate = 22050
        self.speed = speed
        self._model_hint = model_path
        self._detect()
        self.available = self.engine is not None    
        
        # ---------- setup ----------

    def _detect(self):
        model = (os.environ.get("PIPER_MODEL_DE") or self._model_hint
                 or _CONFIG_MODEL)
        model = os.path.expanduser(model) if model else ""
        piper = shutil.which("piper-tts") or shutil.which("piper")
        aplay = shutil.which("aplay")

        if piper and aplay and model and Path(model).is_file():
            self.engine = "piper"
            self._piper, self._model = piper, model
            self._rate = self._read_sample_rate(model)
            return

        reasons = []
        if not piper:
            reasons.append("piper-tts not found")
        if not aplay:
            reasons.append("aplay not found")
        if not model:
            reasons.append("PIPER_MODEL_DE not set in config.py")
        elif not Path(model).is_file():
            reasons.append(f"model file not found: {model}")
        piper_problem = "; ".join(reasons)

        if sys.platform.startswith("linux") and shutil.which("espeak-ng"):
            self.engine = "espeak"
        elif sys.platform == "darwin" and shutil.which("say"):
            self.engine = "say"
        elif sys.platform == "win32" and shutil.which("powershell"):
            self.engine = "powershell"
        else:
            self.problem = piper_problem or "no speech engine found"
            return
        print(f"[speech] Piper unavailable ({piper_problem}); "
              f"using fallback: {self.engine}")

    @staticmethod
    def _read_sample_rate(model: str) -> int:
        try:
            with open(model + ".json", encoding="utf-8") as f:
                return int(json.load(f)["audio"]["sample_rate"])
        except (OSError, KeyError, ValueError):
            return 22050

    # ---------- public API ----------

    def say(self, texts):
        if not self.available:
            return
        queue = [texts] if isinstance(texts, str) else list(texts)
        self.stop()
        with self._lock:
            gen = self._gen
        threading.Thread(target=self._run, args=(queue, gen),
                         daemon=True).start()

    def stop(self):
        with self._lock:
            self._gen += 1
            procs = list(self._procs)
        for p in procs:
            try:
                p.kill()
            except OSError:
                pass

    def reconfigure(self, model_path: str, speed: float):
        self.stop()
        self.speed = speed
        self._model_hint = model_path
        self.engine = None
        self.problem = None
        self._detect()
        self.available = self.engine is not None

    # ---------- worker thread ----------

    def _run(self, queue, gen):
        for text in queue:
            try:
                if not self._speak_one(text, gen):
                    return
            except OSError as e:
                print(f"[speech] error: {e}")
                return

    def _speak_one(self, text: str, gen: int) -> bool:
        """Returns False if this job was cancelled."""
        with self._lock:
            if gen != self._gen:
                return False
            procs = self._start(text)
            self._procs.extend(procs)
        try:
            if self.engine == "piper":
                piper, _aplay = procs
                try:
                    piper.stdin.write(text.encode("utf-8"))
                    piper.stdin.close()
                except (BrokenPipeError, OSError):
                    pass  # cancelled while writing
            for p in procs:
                p.wait()
        finally:
            with self._lock:
                for p in procs:
                    if p in self._procs:
                        self._procs.remove(p)
        return True

    def _start(self, text: str):
        quiet = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
        if self.engine == "piper":
            piper = subprocess.Popen(
                [self._piper, "-m", self._model, "--output-raw",
                 "--length-scale", f"{self.speed:.2f}"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL)
            aplay = subprocess.Popen(
                ["aplay", "-q", "-t", "raw", "-f", "S16_LE",
                 "-r", str(self._rate), "-c", "1"],
                stdin=piper.stdout, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            piper.stdout.close()  # so piper gets SIGPIPE if aplay dies
            return [piper, aplay]
        if self.engine == "espeak":
            return [subprocess.Popen(
                ["espeak-ng", "-v", "de", "-s", "130", text], **quiet)]
        if self.engine == "say":
            return [subprocess.Popen(
                ["say", "-v", "Anna", "-r", "140", text], **quiet)]
        env = dict(os.environ, POMO_TEXT=text)
        return [subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", WIN_SCRIPT],
            env=env, **quiet)]
