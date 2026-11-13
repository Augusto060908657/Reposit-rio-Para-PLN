"""Interface Gradio: consentimento, microfone (apertar para falar) e upload, transcrição + resposta em texto,
áudio da resposta e painel de latência."""
import os, tempfile

import gradio as gr

from .config import AVISO_CONSENTIMENTO, LLM_HOST, LLM_MODELO, RESULTADOS, RAG_SCORE_MIN, RAG_TOP_K, STT_MODELO, KB_DIR
from .dialogo import Dialogo
from .llm import OllamaChat
from .pipeline import Assistente
from .rag import BaseConhecimento
from .stt import STT
from .tts import TTS


def criar_app(stt_backend="faster-whisper", stt_modelo=STT_MODELO, llm_modelo=LLM_MODELO):
    stt = STT(stt_backend, stt_modelo)
    kb = BaseConhecimento(KB_DIR, RAG_TOP_K, RAG_SCORE_MIN)
    dialogo = Dialogo(OllamaChat(llm_modelo, LLM_HOST), kb)
    saida = tempfile.mkdtemp(prefix="zelador_")
    zelador = Assistente(stt, dialogo, TTS(), pasta_audio_saida=saida,
                         log_csv=os.path.join(RESULTADOS, "latencia_demo.csv"))

    def ao_aceitar(aceito):
        return gr.update(interactive=bool(aceito)), gr.update(interactive=bool(aceito))

    def enviar(audio, chat, aceito):
        chat = chat or []
        if not aceito:
            chat.append({"role": "assistant", "content": "Antes de usar, aceite o aviso de privacidade."})
            return chat, None, "", None
        if not audio:
            chat.append({"role": "assistant", "content": "Não recebi nenhum áudio. Grave ou envie um arquivo."})
            return chat, None, "", None
        r = zelador.turno_audio(audio, apagar_audio=True)          # retenção mínima: apaga o áudio após o STT
        chat += [{"role": "user", "content": r["transcricao"] or "(não entendi o áudio)"},
                 {"role": "assistant", "content": r["resposta"]}]
        lat = (f"**Latência (s)**: STT {r['stt_s']:.2f} | RAG {r['rag_s']:.3f} | LLM {r['llm_s']:.2f} | "
               f"adaptação {r['fala_s']:.3f} | TTS {r['tts_s']:.2f} | **total até o áudio {r['total_s']:.2f}**")
        return chat, r["audio"], lat, None

    def nova():
        zelador.nova_conversa()
        return [], None, "", None

    with gr.Blocks(title="Zelador - Assistente de voz de zeladoria urbana", delete_cache=(120, 120)) as app:
        gr.Markdown("# Zelador: relate problemas urbanos falando\nProtótipo acadêmico CitizenTech (ODS 11).")
        gr.Markdown(AVISO_CONSENTIMENTO)
        aceito = gr.Checkbox(label="Li o aviso e aceito que meu áudio seja gravado e processado", value=False)
        with gr.Row():
            with gr.Column():
                audio = gr.Audio(sources=["microphone", "upload"], type="filepath", interactive=False,
                                 label="Fale (microfone) ou envie um arquivo de áudio")
                btn = gr.Button("Enviar", variant="primary", interactive=False)
                novo = gr.Button("Nova conversa (apaga o histórico)")
            with gr.Column():
                chat = gr.Chatbot(label="Conversa (transcrição e resposta em texto)", type="messages", height=380)
                resp_audio = gr.Audio(label="Resposta falada", autoplay=True, interactive=False)
                lat = gr.Markdown()
        aceito.change(ao_aceitar, aceito, [audio, btn])
        btn.click(enviar, [audio, chat, aceito], [chat, resp_audio, lat, audio])
        novo.click(nova, None, [chat, resp_audio, lat, audio])
    return app


if __name__ == "__main__":
    criar_app().launch(share=True)
