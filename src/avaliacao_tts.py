"""Sintetiza as 10 respostas de teste com Piper e mede a latência do TTS. A nota de naturalidade e clareza
(1 a 5) é dada por pelo menos 3 pessoas na planilha planilha_avaliacao_TTS.xlsx.
Uso:  python -m src.avaliacao_tts"""
import csv, os, wave

from .config import BASE, RESULTADOS
from .fala import adaptar_para_fala
from .tts import TTS


def main():
    frases = list(csv.DictReader(open(os.path.join(BASE, "dados", "frases_tts.csv"), encoding="utf-8")))
    pasta = os.path.join(RESULTADOS, "tts_amostras")
    os.makedirs(pasta, exist_ok=True)
    tts = TTS()
    linhas = []
    for f in frases:
        falado = adaptar_para_fala(f["resposta_do_assistente"])
        wav = os.path.join(pasta, f"{f['id']}.wav")
        t = tts.sintetizar(falado, wav)
        with wave.open(wav) as w:
            dur = w.getnframes() / w.getframerate()
        linhas.append(dict(id=f["id"], texto_original=f["resposta_do_assistente"], texto_falado=falado,
                           tts_s=round(t, 3), duracao_audio_s=round(dur, 2), fator_tempo_real=round(t / dur, 3)))
    with open(os.path.join(RESULTADOS, "tts_latencia.csv"), "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)
    print("Amostras geradas em", pasta, "- ouça e preencha a planilha de avaliação (3 pessoas).")


if __name__ == "__main__":
    main()
