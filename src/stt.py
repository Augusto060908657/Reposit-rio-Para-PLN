"""STT (voz para texto): faster-whisper (padrão, GPU no Colab) ou Whisper ONNX via sherpa-onnx (CPU)."""
import os, time

from .config import MODELOS_DIR


class STT:
    def __init__(self, backend="faster-whisper", modelo="small", device="auto", sherpa_dir=None):
        self.backend, self.modelo = backend, modelo
        if backend == "faster-whisper":
            from faster_whisper import WhisperModel
            if device == "auto":
                try:
                    import torch
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except Exception:
                    device = "cpu"
            try:
                self.m = WhisperModel(modelo, device=device, compute_type="float16" if device == "cuda" else "int8")
            except Exception:                    # GPU/cuDNN indisponível: usa CPU
                device = "cpu"
                self.m = WhisperModel(modelo, device="cpu", compute_type="int8")
            self.device = device
        elif backend == "sherpa":
            import sherpa_onnx
            d = os.path.join(sherpa_dir or MODELOS_DIR, f"sherpa-onnx-whisper-{modelo}")
            self.m = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=f"{d}/{modelo}-encoder.int8.onnx", decoder=f"{d}/{modelo}-decoder.int8.onnx",
                tokens=f"{d}/{modelo}-tokens.txt", language="pt", task="transcribe", num_threads=4)
        else:
            raise ValueError("backend deve ser 'faster-whisper' ou 'sherpa'")

    def transcrever(self, caminho):
        """Retorna (texto, segundos gastos)."""
        t0 = time.perf_counter()
        if self.backend == "faster-whisper":
            segs, _ = self.m.transcribe(caminho, language="pt", beam_size=5, vad_filter=True)
            texto = " ".join(s.text.strip() for s in segs).strip()
        else:
            import subprocess, tempfile, soundfile as sf
            with tempfile.TemporaryDirectory() as tmp:
                wav = os.path.join(tmp, "a.wav")
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", caminho, "-ac", "1", "-ar", "16000", wav], check=True)
                x, sr = sf.read(wav, dtype="float32")
            s = self.m.create_stream()
            s.accept_waveform(sr, x)
            self.m.decode_stream(s)
            texto = s.result.text.strip()
        return texto, time.perf_counter() - t0
