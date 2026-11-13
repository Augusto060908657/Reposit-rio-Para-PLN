"""TTS (texto para voz) em português do Brasil com Piper (voz sintética pronta; nenhuma clonagem de voz)."""
import os, subprocess, time, wave

from .config import PIPER_VOZ


class TTS:
    def __init__(self, modelo_onnx=PIPER_VOZ):
        self.modelo = modelo_onnx
        self.voz = None
        try:
            from piper import PiperVoice
            self.voz = PiperVoice.load(modelo_onnx)
        except Exception as e:                     # cai para a linha de comando `piper`
            self.erro_api = str(e)

    def sintetizar(self, texto, saida_wav):
        """Gera o .wav e retorna os segundos gastos."""
        os.makedirs(os.path.dirname(os.path.abspath(saida_wav)), exist_ok=True)
        t0 = time.perf_counter()
        if self.voz is not None:
            with wave.open(saida_wav, "wb") as wf:
                if hasattr(self.voz, "synthesize_wav"):
                    self.voz.synthesize_wav(texto, wf)
                else:
                    self.voz.synthesize(texto, wf)
        else:
            subprocess.run(["piper", "--model", self.modelo, "--output_file", saida_wav],
                           input=texto.encode("utf-8"), check=True)
        return time.perf_counter() - t0
