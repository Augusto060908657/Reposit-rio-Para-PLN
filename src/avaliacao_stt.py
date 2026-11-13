"""Avalia o STT nos áudios gravados pelo grupo: WER (jiwer) por modelo, pessoa e condição, e tempo de transcrição.
Uso:  python -m src.avaliacao_stt --backend faster-whisper --modelos small medium
      python -m src.avaliacao_stt --backend sherpa --modelos base small medium   (CPU, Whisper ONNX int8)"""
import argparse, csv, os, subprocess

import soundfile as sf

from .config import BASE, RESULTADOS
from .metricas import wer
from .stt import STT

EXT = (".mp3", ".mp4", ".m4a", ".wav")


def _arquivo(a):
    for e in EXT:
        p = os.path.join(BASE, "audios_teste", a + e)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(a)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="faster-whisper")
    ap.add_argument("--modelos", nargs="+", default=["small", "medium"])
    ap.add_argument("--prefixo", default=None, help="prefixo do CSV de saída (padrão: stt_<modelo> / stt_fw_<modelo>)")
    a = ap.parse_args()
    refs = {int(r["numero"]): r for r in csv.DictReader(open(os.path.join(BASE, "dados", "referencias_stt.csv"), encoding="utf-8"))}
    itens = [(r["arquivo"], r["pessoa"], r["condicao"], n, False) for n, r in refs.items()]
    itens += [("audio_10_Karen_ruido_RETAKE2", "Karen", "ruido", 10, True),
              ("audio_12_Raio_limpo_RETAKE1", "Raio", "limpo", 12, True)]
    os.makedirs(RESULTADOS, exist_ok=True)
    for modelo in a.modelos:
        stt = STT(a.backend, modelo)
        stt.transcrever(_arquivo(itens[0][0]))                       # aquecimento
        linhas = []
        for arq, pessoa, cond, n, retake in itens:
            caminho = _arquivo(arq)
            texto, dt = stt.transcrever(caminho)
            dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                 "-of", "csv=p=0", caminho]).decode().strip())
            linhas.append(dict(modelo=modelo, arquivo=arq, numero=n, pessoa=pessoa, condicao=cond, retake=retake,
                               duracao_s=round(dur, 2), tempo_stt_s=round(dt, 3), wer=round(wer(refs[n]["referencia"], texto), 4),
                               referencia=refs[n]["referencia"], hipotese=texto))
        nome = a.prefixo or (f"stt_{modelo}" if a.backend == "sherpa" else f"stt_fw_{modelo}")
        with open(os.path.join(RESULTADOS, nome + ".csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)
        oficiais = [l["wer"] for l in linhas if not l["retake"]]
        print(f"{a.backend}/{modelo}: WER médio (conjunto oficial) = {sum(oficiais)/len(oficiais):.3f}")


if __name__ == "__main__":
    main()
