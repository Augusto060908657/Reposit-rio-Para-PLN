"""Pipeline completo: áudio -> STT -> LLM (com memória e RAG) -> adaptação para fala -> TTS, com latência por etapa."""
import csv, datetime, os, time, uuid

from .config import RESULTADOS
from .fala import adaptar_para_fala

CAMPOS_LOG = ["data_hora", "conversa", "turno", "stt_s", "rag_s", "llm_s", "fala_s", "tts_s",
              "total_ate_audio_s", "seguranca", "protocolo", "duracao_audio_s"]


class Assistente:
    def __init__(self, stt, dialogo, tts, pasta_audio_saida="/tmp/zelador_saida", log_csv=None):
        self.stt, self.dialogo, self.tts = stt, dialogo, tts
        self.pasta = pasta_audio_saida
        self.log_csv = log_csv
        self.turno = 0
        self.conversa = uuid.uuid4().hex[:8]

    def nova_conversa(self):
        self.dialogo.reset()
        self.turno, self.conversa = 0, uuid.uuid4().hex[:8]

    def _log(self, linha):
        if not self.log_csv:
            return
        os.makedirs(os.path.dirname(os.path.abspath(self.log_csv)), exist_ok=True)
        novo = not os.path.exists(self.log_csv)
        with open(self.log_csv, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS_LOG)
            if novo:
                w.writeheader()
            w.writerow({k: linha.get(k, "") for k in CAMPOS_LOG})

    def turno_audio(self, caminho_audio, apagar_audio=True, conversa=None):
        """Retorna dict com transcrição, resposta (tela), texto falado, caminho do áudio e tempos por etapa.
        LGPD: o áudio de entrada é apagado logo após a transcrição (apagar_audio=True)."""
        t_total = time.perf_counter()
        texto, t_stt = self.stt.transcrever(caminho_audio)
        if apagar_audio:
            try:
                os.remove(caminho_audio)
            except OSError:
                pass
        return self._resto(texto, t_stt, t_total, conversa)

    def turno_texto(self, texto, conversa=None):
        return self._resto(texto, 0.0, time.perf_counter(), conversa)

    def _resto(self, texto, t_stt, t_total, conversa):
        self.turno += 1
        resposta, info = self.dialogo.responder(texto) if texto.strip() else (
            "Não consegui ouvir bem. Pode repetir, por favor?", dict(rag_s=0, llm_s=0, protocolo=None, nivel_seguranca="ok"))
        t0 = time.perf_counter()
        falado = adaptar_para_fala(resposta)
        t_fala = time.perf_counter() - t0
        os.makedirs(self.pasta, exist_ok=True)
        wav = os.path.join(self.pasta, f"resp_{uuid.uuid4().hex[:8]}.wav")
        t_tts = self.tts.sintetizar(falado, wav)
        total = time.perf_counter() - t_total
        r = dict(transcricao=texto, resposta=resposta, texto_falado=falado, audio=wav, stt_s=t_stt,
                 rag_s=info.get("rag_s", 0), llm_s=info.get("llm_s", 0), fala_s=t_fala, tts_s=t_tts,
                 total_s=total, seguranca=info.get("nivel_seguranca"), protocolo=info.get("protocolo"))
        self._log(dict(data_hora=datetime.datetime.now().isoformat(timespec="seconds"),
                       conversa=conversa or self.conversa, turno=self.turno, stt_s=round(t_stt, 3),
                       rag_s=round(r["rag_s"], 3), llm_s=round(r["llm_s"], 3), fala_s=round(t_fala, 4),
                       tts_s=round(t_tts, 3), total_ate_audio_s=round(total, 3),
                       seguranca=r["seguranca"], protocolo=r["protocolo"] or ""))
        return r
