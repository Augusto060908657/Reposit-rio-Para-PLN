"""Gera o notebook do Colab (CitizenTech_Zelador_Colab.ipynb). Uso: python -m src.gerar_notebook"""
import json, os

from .config import BASE


def md(t): return {"cell_type": "markdown", "metadata": {}, "source": t.strip("\n").splitlines(True)}
def code(t): return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": t.strip("\n").splitlines(True)}


C = [
md("""
# Zelador: assistente de voz de zeladoria urbana (CitizenTech, GS 2027 PLN)
**Autor:** Octavio Augusto Ramalho Brandão Pires, RM 555696

Fluxo: microfone → **STT** (faster-whisper) → **LLM** (Qwen2.5 via Ollama, com RAG e memória) → **adaptação para fala** → **TTS** (Piper) → alto-falante.

**Como usar no Colab:** menu *Ambiente de execução → Alterar tipo → GPU T4*, depois *Executar tudo*. Tudo é gratuito e roda no próprio Colab, sem API paga.

> **Aviso LGPD:** voz é dado pessoal. O áudio do cidadão é apagado logo depois de transcrito e nada é enviado a APIs externas.
"""),
md("## 0. Obter o projeto\nSe a pasta `src` ainda não existe, envie o arquivo `CitizenTech_Zeladoria_Voz.zip` (ou defina `REPO_URL` com o link do GitHub)."),
code("""
import os, zipfile, subprocess
REPO_URL = ""   # ex.: "https://github.com/seu-usuario/CitizenTech_Zeladoria_Voz.git"
if not os.path.exists("src/pipeline.py"):
    if REPO_URL:
        subprocess.run(["git", "clone", REPO_URL, "projeto"], check=True); os.chdir("projeto")
    else:
        from google.colab import files
        up = files.upload()
        nome = next(iter(up)); zipfile.ZipFile(nome).extractall(".")
        pasta = [d for d in os.listdir(".") if os.path.exists(os.path.join(d, "src", "pipeline.py"))]
        if pasta: os.chdir(pasta[0])
print("Pasta do projeto:", os.getcwd()); print(os.listdir("."))
"""),
md("## 1. Instalação (pip, ffmpeg, Ollama)"),
code("""
!pip install -q -r requirements.txt
!apt-get -qq install -y ffmpeg zstd > /dev/null
!curl -fsSL https://ollama.com/install.sh | sh > /dev/null 2>&1
import subprocess, time, requests
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(30):
    try: requests.get("http://localhost:11434"); break
    except Exception: time.sleep(2)
print("Ollama no ar")
"""),
code("""
# Modelos do LLM (comparação do LLM: 7B x 3B) e voz do TTS
!ollama pull qwen2.5:7b
!ollama pull qwen2.5:3b
import os, urllib.request
os.makedirs("modelos/piper", exist_ok=True)
base = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/"
for f in ["pt_BR-faber-medium.onnx", "pt_BR-faber-medium.onnx.json"]:
    if not os.path.exists("modelos/piper/" + f): urllib.request.urlretrieve(base + f, "modelos/piper/" + f)
print(os.listdir("modelos/piper"))
"""),
md("## 2. Teste rápido de cada módulo"),
code("""
from src.fala import adaptar_para_fala
print(adaptar_para_fala("**Claro!** Ligue 156 ou use o app SP156. Seu protocolo é ZU-20261112-0001, CEP 01301-000. 😊"))
"""),
code("""
from src.config import KB_DIR
from src.rag import BaseConhecimento
kb = BaseConhecimento(KB_DIR, 5, 0.12)
print(len(kb.chunks), "trechos na base de conhecimento")
for s, c in kb.recuperar("Como peço o conserto de um buraco?")[:3]: print(round(s, 2), c["texto"][:110])
"""),
code("""
from src.pipeline import Assistente
from src.stt import STT; from src.tts import TTS
from src.llm import OllamaChat; from src.dialogo import Dialogo
zel = Assistente(STT("faster-whisper", "medium"), Dialogo(OllamaChat("qwen2.5:7b"), kb), TTS(), pasta_audio_saida="/tmp/zel")
r = zel.turno_texto("Oi, quero relatar um buraco enorme na rua Augusta, perto do número quinhentos e vinte.")
print(r["resposta"]); print({k: round(v, 2) for k, v in r.items() if k.endswith("_s")})
from IPython.display import Audio; Audio(r["audio"])
"""),
md("## 3. Avaliação do STT (WER com `jiwer`, 24 áudios, 6 vozes, 6 com ruído) e comparação small × medium"),
code("""
!python -m src.avaliacao_stt --backend faster-whisper --modelos small medium
!python -m src.analise_vies
"""),
md("## 4. Avaliação do LLM (30 perguntas: 15 do tema, 5 de continuação, 5 fora do escopo, 5 de emergência/limites)"),
code("""
!python -m src.avaliacao_llm --modelos qwen2.5:7b qwen2.5:3b
"""),
md("## 5. Avaliação do TTS (10 respostas; as notas de naturalidade e clareza vêm de 3 pessoas)"),
code("""
!python -m src.avaliacao_tts
from IPython.display import Audio, display
import glob
for f in sorted(glob.glob("resultados/tts_amostras/*.wav")): print(os.path.basename(f)); display(Audio(f))
"""),
md("## 6. Teste ponta a ponta (10 conversas com 3 ou mais turnos) e latência por etapa"),
code("""
!python -m src.avaliacao_e2e --stt-modelo medium --llm qwen2.5:7b
import pandas as pd
d = pd.read_csv("resultados/e2e_latencia.csv")
print(d[["stt_s", "rag_s", "llm_s", "fala_s", "tts_s", "total_ate_audio_s"]].mean().round(2))
"""),
md("## 7. Demonstração com microfone e upload (Gradio). Use esta célula para gravar o vídeo"),
code("""
from src.app_gradio import criar_app
criar_app("faster-whisper", "medium", "qwen2.5:7b").launch(share=True, debug=True)
"""),
md("## 8. Gerar planilhas e relatório com os números reais e baixar tudo"),
code("""
!python -m src.gerar_planilhas
!python -m src.gerar_relatorio
!zip -r -q resultados_colab.zip resultados planilhas relatorio_zelador.pdf
from google.colab import files; files.download("resultados_colab.zip")
"""),
]
nb = {"cells": C, "metadata": {"accelerator": "GPU", "colab": {"provenance": [], "gpuType": "T4"},
      "kernelspec": {"display_name": "Python 3", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
if __name__ == "__main__":
    with open(os.path.join(BASE, "CitizenTech_Zelador_Colab.ipynb"), "w", encoding="utf-8") as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)
    print("notebook gerado")
