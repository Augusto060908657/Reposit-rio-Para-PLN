"""Configurações centrais do projeto CitizenTech - Zelador (assistente de voz de zeladoria urbana)."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_DIR = os.path.join(BASE, "dados", "base_conhecimento")
RESULTADOS = os.path.join(BASE, "resultados")
REGISTROS = os.path.join(BASE, "registros")           # protocolos simulados (sem dados pessoais)
MODELOS_DIR = os.environ.get("MODELOS_DIR", os.path.join(BASE, "modelos"))

# Modelos padrão (todos gratuitos e executados localmente / no Colab)
STT_MODELO = os.environ.get("STT_MODELO", "medium")                 # faster-whisper: base | small | medium (padrão: medium, escolhido pelo menor WER)
LLM_MODELO = os.environ.get("LLM_MODELO", "qwen2.5:7b")            # Ollama
LLM_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
PIPER_VOZ = os.environ.get("PIPER_VOZ", os.path.join(MODELOS_DIR, "piper", "pt_BR-faber-medium.onnx"))

HISTORICO_MAX_MENSAGENS = 10   # memória da conversa enviada ao LLM (últimas N mensagens)
RAG_TOP_K = 5
RAG_SCORE_MIN = 0.12

AVISO_CONSENTIMENTO = (
    "Aviso de privacidade (LGPD): sua voz é um dado pessoal. Ao usar este protótipo, você concorda que o "
    "áudio será gravado e processado para ser transformado em texto. O processamento acontece neste computador "
    "ou no Colab do grupo, sem enviar o áudio a nenhuma API externa. O áudio é apagado logo depois da "
    "transcrição e o texto da conversa não é guardado depois do atendimento. Não informe CPF, telefone ou outros "
    "dados pessoais. Este assistente é um protótipo acadêmico e não registra pedidos reais: para valer, o pedido "
    "deve ser feito no SP156."
)
