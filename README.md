# Zelador: assistente de voz de zeladoria urbana (CitizenTech, GS 2027 PLN)

**Autor:** Octavio Augusto Ramalho Brandão Pires, RM 555696 (trabalho individual)

O cidadão **fala** um problema urbano (buraco, árvore, lâmpada queimada, bueiro, entulho, calçada, semáforo), o assistente entende com um LLM, faz as perguntas que faltam, confirma e gera um **protocolo simulado**, orientando o pedido oficial no SP156. Tema: zeladoria urbana em São Paulo. ODS 11 (meta 11.7), secundariamente ODS 10. Protótipo acadêmico: não envia pedidos reais.

## Arquitetura
`microfone/upload → STT (Whisper) → diálogo (memória + salvaguardas + RAG) → LLM (Qwen2.5 via Ollama) → adaptação para fala → TTS (Piper) → alto-falante`, com interface Gradio (texto + áudio) e latência por etapa. Cada etapa é um módulo em `src/`. Diagrama e justificativas: `relatorio_zelador.pdf`.

| Módulo | Arquivo |
|---|---|
| STT | `src/stt.py` (faster-whisper ou Whisper ONNX/sherpa-onnx) |
| Diálogo, memória, protocolo | `src/dialogo.py` |
| Base de conhecimento (RAG TF-IDF) | `src/rag.py`, `dados/base_conhecimento/` |
| Emergências e limites | `src/guardrails.py` |
| LLM (Ollama) | `src/llm.py` |
| Adaptação para fala | `src/fala.py` |
| TTS (Piper) | `src/tts.py` |
| Pipeline e latência | `src/pipeline.py` |
| Interface | `src/app_gradio.py` |
| LGPD | `src/lgpd.py`, aviso em `src/config.py` |

## Como executar (Colab, GPU T4)
1. Abra `CitizenTech_Zelador_Colab.ipynb` no Google Colab e escolha *Ambiente de execução → Alterar tipo → GPU T4*.
2. Execute as células na ordem. A seção 0 pede o arquivo `CitizenTech_Zeladoria_Voz.zip` (ou use `REPO_URL` com o link do GitHub).
3. Seções 3 a 6: avaliações de STT, LLM, TTS e ponta a ponta. Seção 7: demo com microfone (Gradio). Seção 8: planilhas e relatório com os números.

Execução local: `pip install -r requirements.txt`, instale ffmpeg e Ollama (`ollama pull qwen2.5:7b qwen2.5:3b`), baixe a voz Piper para `modelos/piper/` e rode `python -m src.app_gradio`.

## Modelos, versões e licenças (conferir antes de publicar)
| Componente | Uso | Licença |
|---|---|---|
| Whisper base, small, medium (OpenAI) | STT. Medições do relatório: ONNX int8 (sherpa-onnx). Colab: faster-whisper | MIT |
| Qwen2.5-7B-Instruct e 3B (`qwen2.5:7b`, `qwen2.5:3b`, Ollama) | LLM | 7B: Apache-2.0; 3B: licença própria da Qwen |
| Piper `pt_BR-faber-medium` | TTS (voz sintética pronta, sem clonagem) | ver model card do rhasspy/piper-voices |
| Gradio, jiwer, scikit-learn, Ollama | interface, WER, RAG, servidor do LLM | Apache-2.0, Apache-2.0, BSD, MIT |

## Resultados já medidos (STT, 24 áudios, 6 vozes, 6 com ruído)
| Whisper | WER médio | WER limpo | WER ruído | Tempo médio (CPU 1 núcleo) |
|---|---|---|---|---|
| base | 25,1% | 23,8% | 28,8% | 3,8 s |
| small | 9,6% | 10,3% | 7,3% | 13,5 s |
| **medium (escolhido)** | **4,8%** | 4,0% | 7,3% | 55,1 s |

Os tempos são de CPU e só servem para comparar os tamanhos. LLM, TTS e ponta a ponta são medidos no Colab (aparecem como PENDENTE no relatório até lá).

## Material de teste
- `audios_teste/`: 24 áudios oficiais + 2 regravações (`_RETAKE`). `dados/referencias_stt.csv`: frases de referência.
- `dados/perguntas_llm.csv`: 30 perguntas com resposta esperada. `dados/roteiros_conversas.csv`: 10 conversas. `dados/frases_tts.csv`: 10 respostas para o TTS.
- `planilhas/`: STT (com fórmulas), LLM (30 perguntas) e TTS (3 avaliadores). `resultados/`: CSVs e figura do STT.
- `roteiro_video.md`: roteiro do vídeo. `dados/modelo_autorizacao_voz.txt`: modelo de autorização de voz.

## LGPD
Aviso e aceite antes do uso, áudio apagado logo após a transcrição, nada enviado a APIs externas, sem pedir CPF ou dados pessoais, regras fixas para emergências, resposta "não sei" quando falta informação e nenhuma clonagem de voz.
