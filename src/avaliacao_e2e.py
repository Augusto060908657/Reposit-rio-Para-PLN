"""Teste ponta a ponta: 10 conversas (>= 3 turnos), áudio -> STT -> LLM -> fala -> TTS, com latência por etapa.
Se existir o áudio real do turno em dados/audios_conversas/<CID>_t<N>.(wav|mp3|m4a|mp4), ele é usado. Caso
contrário, a fala do usuário é sintetizada com o Piper (voz artificial) só para exercitar o pipeline.
Uso:  python -m src.avaliacao_e2e [--stt-modelo small] [--llm qwen2.5:7b]"""
import argparse, csv, os, tempfile, collections

from .config import BASE, KB_DIR, LLM_HOST, RAG_SCORE_MIN, RAG_TOP_K, RESULTADOS
from .dialogo import Dialogo
from .llm import OllamaChat
from .pipeline import Assistente
from .rag import BaseConhecimento
from .stt import STT
from .tts import TTS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stt-modelo", default="medium")
    ap.add_argument("--stt-backend", default="faster-whisper")
    ap.add_argument("--llm", default="qwen2.5:7b")
    a = ap.parse_args()
    conversas = collections.OrderedDict()
    for r in csv.DictReader(open(os.path.join(BASE, "dados", "roteiros_conversas.csv"), encoding="utf-8")):
        conversas.setdefault(r["id"], []).append(r["fala_do_usuario"])
    tts = TTS()
    kb = BaseConhecimento(KB_DIR, RAG_TOP_K, RAG_SCORE_MIN)
    ass = Assistente(STT(a.stt_backend, a.stt_modelo), Dialogo(OllamaChat(a.llm, LLM_HOST), kb, salvar_registros=False),
                     tts, pasta_audio_saida=tempfile.mkdtemp(), log_csv=os.path.join(RESULTADOS, "e2e_latencia.csv"))
    if os.path.exists(ass.log_csv):
        os.remove(ass.log_csv)
    tmp = tempfile.mkdtemp()
    transcritos = []
    for cid, falas in conversas.items():
        ass.nova_conversa()
        for n, fala in enumerate(falas, 1):
            real = next((os.path.join(BASE, "dados", "audios_conversas", f"{cid}_t{n}{e}") for e in (".wav", ".mp3", ".m4a", ".mp4")
                         if os.path.exists(os.path.join(BASE, "dados", "audios_conversas", f"{cid}_t{n}{e}"))), None)
            origem = "real" if real else "sintetico"
            if not real:
                real = os.path.join(tmp, f"{cid}_t{n}.wav")
                tts.sintetizar(fala, real)
            r = ass.turno_audio(real, apagar_audio=False, conversa=cid)
            transcritos.append(f"[{cid} t{n} | áudio {origem}] USUÁRIO (roteiro): {fala}\n   STT: {r['transcricao']}\n   ZELADOR: {r['resposta']}\n"
                               f"   tempos: stt {r['stt_s']:.2f}s llm {r['llm_s']:.2f}s tts {r['tts_s']:.2f}s total {r['total_s']:.2f}s\n")
    with open(os.path.join(RESULTADOS, "e2e_conversas.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(transcritos))
    print("Concluído. Veja resultados/e2e_latencia.csv e resultados/e2e_conversas.txt")


if __name__ == "__main__":
    main()
