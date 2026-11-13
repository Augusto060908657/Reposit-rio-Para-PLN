"""Gera relatorio_zelador.pdf com os resultados reais encontrados em resultados/*.csv.
Seções sem resultado aparecem como PENDENTE (execute o notebook no Colab e rode este script de novo).
Uso: python -m src.gerar_relatorio"""
import csv, datetime, glob, os

import pandas as pd
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .analise_vies import carregar, tabelas
from .config import BASE, RESULTADOS

AZUL, CINZA, AMARELO = colors.HexColor("#1F3A5F"), colors.HexColor("#F2F4F7"), colors.HexColor("#FFF1D6")
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=AZUL, fontSize=15, spaceBefore=12, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=AZUL, fontSize=12, spaceBefore=8, spaceAfter=4)
B = ParagraphStyle("b", parent=ss["Normal"], fontSize=10, leading=14, alignment=4, spaceAfter=5)
S = ParagraphStyle("s", parent=B, fontSize=8.5, leading=11, alignment=0)
TIT = ParagraphStyle("t", parent=ss["Title"], textColor=AZUL, fontSize=22, leading=26)
HC = ParagraphStyle("hc", parent=S, textColor=colors.white, fontName="Helvetica-Bold")
PEND = "PENDENTE: este resultado depende da execução do notebook no Colab (GPU T4). Depois de rodar a seção indicada, execute <font face='Courier'>python -m src.gerar_relatorio</font> para preencher esta tabela."


def p(t, st=B): return Paragraph(t, st)


def tabela(linhas, cab, larg=None, zebra=True):
    dados = [[Paragraph(str(c), HC) for c in cab]] + [[Paragraph(str(c), S) for c in l] for l in linhas]
    t = Table(dados, colWidths=larg, repeatRows=1)
    est = [("BACKGROUND", (0, 0), (-1, 0), AZUL), ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if zebra:
        est.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CINZA]))
    t.setStyle(TableStyle(est))
    return t


def aviso(txt):
    t = Table([[Paragraph(txt, S)]], colWidths=[17 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), AMARELO), ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E0A800")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def pct(x): return f"{100 * x:.1f}%".replace(".", ",")
def seg(x): return f"{x:.2f}".replace(".", ",")


def diagrama():
    d = Drawing(480, 255)
    def caixa(x, y, w, h, txt, cor="#DDE5F0", sub=None):
        d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=colors.HexColor(cor), strokeColor=AZUL, strokeWidth=1))
        d.add(String(x + w / 2, y + h / 2 + (3 if sub else -3), txt, textAnchor="middle", fontSize=8, fontName="Helvetica-Bold", fillColor=AZUL))
        if sub:
            d.add(String(x + w / 2, y + h / 2 - 8, sub, textAnchor="middle", fontSize=6.5, fillColor=colors.HexColor("#444444")))
    def seta(x1, y1, x2, y2):
        d.add(Line(x1, y1, x2, y2, strokeColor=AZUL, strokeWidth=1.2))
        if abs(x2 - x1) >= abs(y2 - y1):
            s = 1 if x2 > x1 else -1
            d.add(Polygon([x2, y2, x2 - 6 * s, y2 + 3, x2 - 6 * s, y2 - 3], fillColor=AZUL, strokeColor=AZUL))
        else:
            s = 1 if y2 > y1 else -1
            d.add(Polygon([x2, y2, x2 - 3, y2 - 6 * s, x2 + 3, y2 - 6 * s], fillColor=AZUL, strokeColor=AZUL))
    caixa(5, 195, 85, 40, "1. Captura", sub="microfone ou upload")
    caixa(120, 195, 85, 40, "2. STT", sub="Whisper (faster-whisper)")
    caixa(235, 195, 110, 40, "3. Diálogo", sub="memória + salvaguardas")
    caixa(375, 195, 100, 40, "4. LLM", sub="Qwen2.5 (Ollama)")
    caixa(235, 130, 110, 40, "RAG", cor="#E6F2E6", sub="base de conhecimento SP156")
    caixa(375, 130, 100, 40, "5. Adaptação p/ fala", sub="sem markdown, números")
    caixa(375, 65, 100, 40, "6. TTS", sub="Piper pt-BR")
    caixa(235, 65, 110, 40, "7. Alto-falante", sub="resposta falada")
    caixa(5, 5, 300, 40, "Interface Gradio", cor="#FFF1D6", sub="transcrição e resposta em texto + painel de latência por etapa")
    caixa(330, 5, 145, 40, "LGPD", cor="#FDE2E2", sub="consentimento, áudio apagado")
    seta(90, 215, 120, 215); seta(205, 215, 235, 215); seta(345, 215, 375, 215)
    seta(265, 195, 265, 170); seta(315, 170, 315, 195)
    seta(425, 195, 425, 170); seta(425, 130, 425, 105); seta(375, 85, 345, 85)
    seta(290, 65, 290, 45); seta(47, 45, 47, 195)
    d.add(String(240, 242, "Fluxo de cada turno da conversa (módulos independentes)", textAnchor="middle", fontSize=8.5, fillColor=AZUL))
    return d


def cabecalho_rodape(c, doc):
    c.saveState(); c.setFont("Helvetica", 8); c.setFillColor(colors.grey)
    c.drawString(2 * cm, 1.2 * cm, "GS 2027 PLN - CitizenTech - Zelador | Octavio Augusto Ramalho Brandão Pires, RM 555696")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    c.restoreState()


def le(nome):
    f = os.path.join(RESULTADOS, nome)
    return pd.read_csv(f) if os.path.exists(f) else None


def main():
    doc = SimpleDocTemplate(os.path.join(BASE, "relatorio_zelador.pdf"), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm, title="Relatório - Zelador, assistente de voz de zeladoria urbana",
                            author="Octavio Augusto Ramalho Brandão Pires")
    e = []
    e += [Spacer(1, 3 * cm), p("Zelador: assistente de voz para relatar problemas urbanos", TIT), Spacer(1, 6),
          p("<b>CitizenTech | GS 2027 | PLN: Assistente de Voz</b>", ParagraphStyle("c", parent=B, alignment=1, fontSize=12)),
          Spacer(1, 18), p("Autor: Octavio Augusto Ramalho Brandão Pires<br/>RM 555696<br/>Trabalho individual", ParagraphStyle("c2", parent=B, alignment=1, fontSize=12, leading=18)),
          p(f"Relatório gerado em {datetime.date.today():%d/%m/%Y}", ParagraphStyle("c3", parent=B, alignment=1)), Spacer(1, 24)]
    e.append(aviso("<b>Como ler este relatório.</b> Todos os números são resultados reais, lidos dos arquivos em <font face='Courier'>resultados/</font>. "
                   "O STT foi medido com os 24 áudios gravados pelo grupo. As seções que dependem da GPU do Colab (LLM, TTS e ponta a ponta) "
                   "aparecem como PENDENTE até o notebook ser executado, e nenhum número foi estimado ou inventado."))
    e.append(PageBreak())

    # 1 problema, persona, ODS
    e += [p("1. Problema, persona e ODS", H1),
          p("Milhões de brasileiros têm dificuldade com interfaces de texto: pessoas idosas, com baixa alfabetização, com deficiência visual ou motora, "
            "ou com as mãos ocupadas. Em São Paulo, o pedido de serviços de zeladoria (tapa-buraco, poda de árvore, iluminação, bueiros) é feito pelo SP156 "
            "por telefone, portal, aplicativo ou WhatsApp, o que exige saber qual serviço pedir e como descrevê-lo. O Zelador é um protótipo de assistente "
            "de voz que escuta o cidadão, entende o problema relatado, faz as perguntas que faltam (tipo, local e gravidade), confirma os dados e "
            "gera um protocolo <b>simulado</b>, orientando a fazer o pedido oficial no SP156."),
          p("<b>Persona (fictícia, baseada no perfil descrito no enunciado).</b> Dona Helena, 68 anos, moradora da Zona Leste, usa o celular só para ligações e "
            "mensagens de voz. Vê um buraco grande em frente à padaria e uma árvore com galhos nos fios, mas não sabe qual órgão procurar nem consegue "
            "preencher formulários. Com o Zelador ela fala o problema como falaria a um vizinho e ouve a orientação de volta."),
          p("<b>ODS relacionado.</b> ODS 11, Cidades e Comunidades Sustentáveis, em especial a meta 11.7 (espaços públicos seguros, inclusivos e acessíveis) "
            "e a participação cidadã na gestão da cidade (11.3). Secundariamente, o ODS 10 (redução das desigualdades), por ampliar o acesso de quem não "
            "consegue usar interfaces de texto."),
          p("<b>Limites do protótipo.</b> O Zelador não é um serviço da Prefeitura e não envia pedidos reais. O protocolo gerado (formato ZU-AAAAMMDD-NNNN) "
            "é simulado e salvo localmente sem dados pessoais. O foco do trabalho é a cadeia de voz (STT, LLM, TTS) e a avaliação de cada componente.")]

    # 2 arquitetura
    e += [p("2. Arquitetura", H1), diagrama(),
          p("Cada etapa é um módulo Python separado em <font face='Courier'>src/</font> (stt.py, dialogo.py, rag.py, guardrails.py, llm.py, fala.py, tts.py, "
            "pipeline.py, app_gradio.py), de modo que o STT, o LLM ou a voz possam ser trocados sem reescrever o resto. O pipeline mede o tempo de cada etapa "
            "e grava em CSV o tempo total da pergunta até o áudio da resposta estar pronto."),
          tabela([["Captura", "Gradio: botão de microfone e upload de arquivo (wav, mp3, m4a, mp4)"],
                  ["STT", "faster-whisper (GPU T4 no Colab), idioma fixo pt, VAD ligado"],
                  ["Salvaguardas", "regras fixas para emergências, saúde e apoio emocional: respondem sem depender do LLM"],
                  ["Memória", "últimas 10 mensagens enviadas ao LLM; permite perguntas como 'e onde eu faço isso?'"],
                  ["RAG", "TF-IDF sobre 44 trechos de 12 arquivos da base de conhecimento (SP156, buraco, árvore, iluminação, bueiro, entulho, calçada, semáforo, água, protocolo, emergências, LGPD)"],
                  ["LLM", "Qwen2.5 via Ollama, system prompt com papel, tom, limites e regra de dizer 'não sei'"],
                  ["Registro do pedido", "ao confirmar, o LLM extrai tipo, local e gravidade em JSON; o código gera o protocolo simulado e a frase final"],
                  ["Adaptação para fala", "remove markdown e emojis; escreve números, datas, telefones, CEP e siglas de forma pronunciável; quebra frases longas"],
                  ["TTS", "Piper, voz sintética pt-BR pronta (nenhuma clonagem de voz)"],
                  ["Interface", "transcrição e resposta em texto junto do áudio, mais o painel de latência por etapa"]],
                 ["Módulo", "Como funciona"], [3.5 * cm, 13.5 * cm])]

    # 3 justificativas
    e += [p("3. Justificativa das escolhas", H1),
          p("<b>Local (Colab), sem API.</b> Custo: tudo gratuito, sem chave de API nem cobrança por requisição. Privacidade: o áudio é dado pessoal e, "
            "processado no próprio ambiente do grupo, não é enviado a terceiros. Latência: a GPU T4 do Colab dá tempos aceitáveis para um protótipo, mas depende da "
            "internet para abrir o Colab e baixar os modelos na primeira execução. Disponibilidade: o Colab gratuito pode limitar a GPU em horários de pico."),
          p("<b>RAG em vez de só contexto no prompt ou fine-tuning.</b> A base é pequena (cerca de 1.200 palavras) e muda com frequência (canais, prazos), então "
            "fine-tuning seria caro e ficaria desatualizado. O RAG por TF-IDF não exige baixar modelo de embeddings, é rápido, determinístico e deixa claro "
            "de qual arquivo veio cada informação. O limite do TF-IDF é depender das mesmas palavras (sem entender sinônimos), o que aparece como limitação."),
          p("<b>Modelos.</b> STT: Whisper (base, small e medium comparados). LLM: Qwen2.5-7B-Instruct como principal e Qwen2.5-3B-Instruct como comparação, "
            "por serem multilíngues, rodarem no Ollama e caberem na T4. TTS: Piper pt_BR-faber-medium, leve, local e sem clonagem.")]

    # 4 resultados STT
    e.append(p("4. Resultados", H1))
    e.append(p("4.1 STT: WER nos áudios gravados pelo grupo", H2))
    df = carregar()
    todos = None
    if df.empty:
        e.append(aviso(PEND))
    else:
        t = tabelas(df)
        n_aud = int(df[df.modelo == df.modelo.iloc[0]].shape[0])
        pessoas = sorted(df.pessoa.unique())
        e.append(p(f"Conjunto: {n_aud} áudios oficiais, {len(pessoas)} vozes ({', '.join(pessoas)}), {int((df[df.modelo == df.modelo.iloc[0]].condicao == 'ruido').sum())} com ruído "
                   "de fundo real. O WER foi calculado com <font face='Courier'>jiwer</font> depois de normalizar a caixa, a pontuação e os números (por exemplo, 520 vira "
                   "'quinhentos e vinte' e o CEP é lido dígito a dígito). Duas regravações (áudios 10 e 12) ficaram fora do conjunto oficial para não escolher a melhor tomada."))
        ordem = [m for m in ["base", "small", "medium"] if m in df.modelo.unique()]
        pm = t["por_modelo"].reindex(ordem)
        pc = t["por_condicao"].reindex(ordem)
        linhas = [[m, int(pm.loc[m, "audios"]), pct(pm.loc[m, "wer_medio"]), pct(pm.loc[m, "wer_mediano"]),
                   pct(pc.loc[m, "limpo"]), pct(pc.loc[m, "ruido"]), seg(pm.loc[m, "tempo_stt_medio_s"])] for m in ordem]
        e.append(tabela(linhas, ["Whisper", "Áudios", "WER médio", "WER mediano", "WER limpo", "WER ruído", "Tempo médio (s)"], [2.4*cm, 2*cm, 2.4*cm, 2.6*cm, 2.4*cm, 2.4*cm, 2.8*cm]))
        e.append(Spacer(1, 4))
        e.append(aviso("<b>Ambiente da medição.</b> Whisper em formato ONNX int8 (sherpa-onnx), em CPU de 1 núcleo, no mesmo conjunto de áudios. "
                       "Os tempos são <b>muito maiores</b> do que seriam na GPU T4 do Colab com faster-whisper, e servem apenas para comparar os tamanhos entre si. "
                       "O notebook repete a avaliação com faster-whisper na T4 (<font face='Courier'>python -m src.avaliacao_stt</font>), e os WER podem variar um pouco entre os dois motores."))
        fw = [m for m in ["small", "medium"] if os.path.exists(os.path.join(RESULTADOS, f"stt_fw_{m}.csv"))]
        # escolha final
        if "small" in ordem and "medium" in ordem:
            ws, wm = pm.loc["small", "wer_medio"], pm.loc["medium", "wer_medio"]
            ts, tm = pm.loc["small", "tempo_stt_medio_s"], pm.loc["medium", "tempo_stt_medio_s"]
            if wm < ws - 0.015:
                esc = (f"<b>Escolha final do STT: Whisper medium</b>, que reduz o WER médio de {pct(ws)} para {pct(wm)}. O custo é um tempo médio de transcrição "
                       f"{tm / ts:.1f} vezes maior que o do small nesta CPU. Na T4, com faster-whisper em float16, esse tempo cai bastante, e para um assistente de voz "
                       "a qualidade da transcrição pesa mais, porque um erro de endereço compromete o pedido.")
            else:
                esc = (f"<b>Escolha final do STT: Whisper small</b>. O medium não melhora o WER de forma relevante ({pct(wm)} contra {pct(ws)}) e custa "
                       f"{tm / ts:.1f} vezes mais tempo, então o small tem a melhor relação entre qualidade e latência.")
            e.append(Spacer(1, 4)); e.append(p("<b>Comparação e escolha.</b> Critério: menor WER; se a diferença for menor que 1,5 ponto percentual, vence o mais rápido. " + esc))
        e.append(p("4.2 STT: WER por pessoa e análise de viés", H2))
        pp = t["por_pessoa"].reindex(columns=ordem)
        e.append(tabela([[i] + [pct(pp.loc[i, m]) for m in ordem] for i in pp.index], ["Pessoa"] + [f"WER {m}" for m in ordem], None))
        fig = os.path.join(RESULTADOS, "fig_wer_pessoa.png")
        if os.path.exists(fig):
            e += [Spacer(1, 4), Image(fig, width=13 * cm, height=6.7 * cm)]
        ref = ordem[-1]
        mx, mn = pp[ref].idxmax(), pp[ref].idxmin()
        cond = pc.loc[ref]
        e.append(p(f"<b>Leitura.</b> No modelo {ref}, a voz com maior WER foi a de {mx} ({pct(pp.loc[mx, ref])}) e a com menor foi a de {mn} ({pct(pp.loc[mn, ref])}). "
                   f"Entre as condições, o WER foi {pct(cond['limpo'])} nos áudios limpos e {pct(cond['ruido'])} nos ruidosos. "
                   "Cada pessoa tem apenas 4 áudios e a diferença entre vozes mistura efeitos de voz, sotaque, microfone do celular, distância da boca e volume de gravação "
                   "(por exemplo, algumas gravações tiveram volume médio bem mais baixo). Por isso os resultados <b>não permitem concluir</b> que o modelo discrimina "
                   "um gênero, idade ou sotaque. O perfil das vozes (gênero, faixa etária, sotaque) não foi coletado (gênero, faixa etária e sotaque não foram declarados), "
                   "portanto a análise por perfil não foi feita."))
        pior = df[df.modelo == ref].sort_values("wer", ascending=False).head(5)
        e.append(p(f"Maiores erros do modelo {ref} (referência x transcrição):", S))
        e.append(tabela([[r.arquivo.replace("audio_", ""), pct(r.wer), r.referencia, r.hipotese] for r in pior.itertuples()],
                        ["Áudio", "WER", "Referência", "Transcrição"], [3.2 * cm, 1.5 * cm, 6 * cm, 6.3 * cm]))
        e.append(p("Os erros se concentram em nomes de ruas e termos do domínio (por exemplo, 'entulho', 'Vergueiro', 'Oscar Freire'), o que sugere melhorar o STT com "
                   "uma lista de termos urbanos no prompt inicial do Whisper ou com correção por fuzzy matching contra nomes de ruas."))

    # LLM
    e.append(p("4.3 LLM: 30 perguntas com resposta esperada", H2))
    llm = {f: pd.read_csv(f) for f in sorted(glob.glob(os.path.join(RESULTADOS, "llm_*.csv"))) if "stub" not in f}
    if not llm:
        e.append(aviso(PEND + " (seção 4 do notebook)."))
        e.append(p("Composição do conjunto: 15 perguntas do tema, 5 de continuação (com os turnos anteriores injetados na memória), 5 fora do escopo "
                   "(devem ser recusadas) e 5 de emergência, saúde e jurídico (devem encaminhar ao órgão competente). O critério automático busca palavras-chave "
                   "definidas em <font face='Courier'>dados/perguntas_llm.csv</font> e a planilha permite a correção manual."))
    else:
        linhas = []
        for f, d in llm.items():
            m = d.modelo.iloc[0]
            def acc(tipo): s = d[d.tipo == tipo]; return pct(s.correta_auto.mean())
            linhas.append([m, acc("tema"), acc("continuacao"), acc("fora_escopo"), acc("limite"), pct(d.correta_auto.mean()), seg(d[d.tratada_por == "llm"].tempo_s.mean())])
        e.append(tabela(linhas, ["Modelo", "Tema", "Continuação", "Fora do escopo (recusa)", "Emergência/limites", "Total", "Tempo médio por resposta (s)"]))
        e.append(p("Critério automático por palavras-chave, conferido na planilha. As perguntas de emergência são tratadas por regras fixas (iguais nos dois modelos)."))

    e.append(p("4.4 TTS: naturalidade e clareza (3 avaliadores)", H2))
    tl = le("tts_latencia.csv")
    if tl is None:
        e.append(aviso(PEND + " (seção 5 do notebook e planilha planilha_avaliacao_TTS.xlsx)."))
    else:
        e.append(p(f"Latência média do TTS: {seg(tl.tts_s.mean())} s por resposta (fator de tempo real médio {seg(tl.fator_tempo_real.mean())}). "
                   "As notas de naturalidade e clareza (1 a 5) são dadas por 3 pessoas em planilha_avaliacao_TTS.xlsx."))
        e.append(aviso("PENDENTE: preencher as notas dos 3 avaliadores na planilha e informar aqui as médias."))

    e.append(p("4.5 Ponta a ponta: 10 conversas e latência", H2))
    ee = le("e2e_latencia.csv")
    if ee is None:
        e.append(aviso(PEND + " (seção 6 do notebook)."))
    else:
        cols = ["stt_s", "rag_s", "llm_s", "fala_s", "tts_s", "total_ate_audio_s"]
        m = ee[cols].mean()
        e.append(tabela([[seg(m[c]) for c in cols]], ["STT (s)", "RAG (s)", "LLM (s)", "Fala (s)", "TTS (s)", "Total até o áudio (s)"]))
        e.append(p(f"{ee.conversa.nunique()} conversas, {len(ee)} turnos. O 'total até o áudio' é o tempo da pergunta até a resposta falada estar pronta para tocar."))

    # ética
    e += [p("5. Ética, segurança e LGPD", H1),
          tabela([["Consentimento", "Aviso de privacidade e caixa de aceite antes do primeiro uso; microfone e envio ficam bloqueados até o aceite."],
                  ["Retenção mínima", "O áudio é apagado logo após a transcrição (os testes de avaliação usam áudios do próprio grupo, com autorização por escrito de cada voz). O texto da conversa fica só na memória da sessão. O protocolo simulado guarda tipo, local e gravidade, sem nome nem CPF."],
                  ["Nuvem", "Nenhum áudio vai a API externa. O Colab é do próprio grupo; se o Colab for usado, o processamento ocorre nele."],
                  ["Limites", "Recusa assuntos fora da zeladoria. Saúde, emergência e jurídico: encaminha ao SAMU 192, Bombeiros 193, Polícia 190, Defesa Civil 199 ou advogado/Defensoria, por regras fixas para os casos críticos."],
                  ["Alucinação", "O prompt exige usar só o contexto e dizer 'não sei' quando faltar informação (por exemplo, prazos do tapa-buraco não são informados)."],
                  ["Clonagem de voz", "Não há clonagem. O TTS usa voz sintética pronta do Piper."],
                  ["Viés do STT", "Análise do WER por pessoa e condição na seção 4.2. Limitada a 6 vozes; não permite generalizar."]],
                 ["Tema", "Como foi tratado"], [3.3 * cm, 13.7 * cm])]

    # limitações
    e += [p("6. Limitações e melhorias futuras", H1),
          p("<b>Limitações.</b> (1) Protótipo: não integra a API real do SP156; o protocolo é simulado. (2) Base de conhecimento pequena e escrita à mão, com prazos que podem mudar; "
            "deve ser conferida no SP156. (3) RAG por TF-IDF não entende sinônimos. (4) Pouca amostra de voz (6 pessoas, 24 áudios) e ruído ambiente não controlado. "
            "(5) Erros de STT em nomes de ruas e números afetam o endereço. (6) Respostas do LLM podem variar entre execuções. (7) Os números de STT deste relatório foram medidos em CPU com Whisper ONNX; "
            "a latência real na T4 deve ser medida no notebook."),
          p("<b>Melhorias.</b> Integração com a API do SP156; geocodificação do endereço e confirmação lida em voz alta; envio de foto por WhatsApp; vocabulário de ruas de São Paulo no STT; "
            "embeddings multilíngues no RAG; streaming do LLM e do TTS por frase para reduzir a latência percebida; testes com mais vozes, sotaques e idades; versão offline em celular.")]

    # modelos e licenças
    e += [p("7. Modelos, versões e licenças", H1),
          tabela([["Whisper (OpenAI) base, small, medium", "pesos originais; ONNX int8 via sherpa-onnx nas medições; faster-whisper no Colab", "MIT"],
                  ["Qwen2.5-7B-Instruct e 3B (Ollama)", "tags qwen2.5:7b e qwen2.5:3b", "7B: Apache-2.0; 3B: licença própria da Qwen (confirmar no model card)"],
                  ["Piper pt_BR-faber-medium", "voz sintética", "conferir no model card do rhasspy/piper-voices; a biblioteca piper-tts tem licença conforme a versão instalada"],
                  ["Ollama, Gradio, jiwer, scikit-learn", "bibliotecas", "MIT, Apache-2.0, Apache-2.0 e BSD"],
                  ["Base de conhecimento", "texto próprio, com base nas páginas das Subprefeituras e do SP156 em prefeitura.sp.gov.br", "uso acadêmico"]],
                 ["Componente", "Versão ou uso", "Licença (conferir antes de publicar)"], [5 * cm, 6 * cm, 6 * cm]),
          p("As licenças acima são as conhecidas pelo autor e devem ser conferidas nas páginas oficiais antes de qualquer publicação.", S)]
    doc.build(e, onFirstPage=cabecalho_rodape, onLaterPages=cabecalho_rodape)
    print("relatorio_zelador.pdf gerado")


if __name__ == "__main__":
    main()
