"""Gerência do diálogo: system prompt, memória, RAG, salvaguardas, coleta do pedido e protocolo simulado."""
import datetime, json, os, re, time, unicodedata

from . import guardrails
from .config import HISTORICO_MAX_MENSAGENS, REGISTROS

SYSTEM_PROMPT = """Você é o Zelador, assistente de voz de zeladoria urbana da cidade de São Paulo (protótipo acadêmico). \
Você ajuda o cidadão a relatar problemas na rua, como buraco, árvore, lâmpada queimada, bueiro entupido, entulho, \
calçada quebrada e semáforo, e a pedir o serviço pelo SP156.

REGRAS:
1. Responda em português do Brasil, em tom acolhedor e simples, com no máximo três frases curtas. Sua resposta será \
falada em voz alta: não use listas, markdown, emojis, tabelas nem links.
2. Use SOMENTE as informações do CONTEXTO abaixo. Se a resposta não estiver no contexto, diga que não sabe e sugira o SP156. \
Nunca invente prazos, telefones, órgãos, leis ou números de protocolo.
3. Se o assunto não for zeladoria urbana (por exemplo previsão do tempo, receitas, finanças, esportes, programação), \
recuse com gentileza, diga que só ajuda com problemas urbanos e ofereça ajuda com isso.
4. Saúde, questões jurídicas e emergências: não dê diagnóstico nem opinião jurídica. Oriente procurar um profissional ou \
o órgão competente (SAMU 192, Bombeiros 193, Polícia 190, Defesa Civil 199, advogado ou Defensoria Pública).
5. Para relatar um problema, descubra uma coisa por vez: o tipo do problema, o local (rua e número ou referência), \
a gravidade e detalhes úteis. Quando já souber tipo e local, resuma em uma frase e pergunte: Posso registrar o pedido?
6. Não peça nome, CPF, telefone nem outros dados pessoais.
7. Se o cidadão perguntar algo que dependa da conversa anterior (por exemplo "e onde eu faço isso?"), use o histórico.

CONTEXTO:
{contexto}
"""

PROMPT_EXTRACAO = """Leia a conversa e extraia os dados do pedido de zeladoria. Responda SOMENTE com um JSON neste formato:
{"tipo": "buraco|arvore|iluminacao|bueiro|entulho|calcada|semaforo|vazamento|outro", "endereco": "rua e número ou referência", \
"gravidade": "baixa|media|alta", "detalhes": "uma frase curta"}
Use null para o que não foi dito. Não invente informações."""

RE_CONFIRMA = re.compile(r"^\s*(sim|pode|isso( mesmo)?|confirm|claro|com certeza|ok|certo|pode registrar|pode confirmar)\b", re.I)
RE_PERGUNTA_CONFIRMACAO = re.compile(r"(posso registrar|posso confirmar|confirma|est[aá] correto|correto\?|quer que eu registre)", re.I)
TIPOS_NOME = {"buraco": "buraco na via", "arvore": "árvore", "iluminacao": "iluminação pública", "bueiro": "bueiro",
              "entulho": "entulho", "calcada": "calçada", "semaforo": "semáforo", "vazamento": "vazamento de água",
              "outro": "problema urbano"}


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


class Dialogo:
    def __init__(self, llm, base_conhecimento, pasta_registros=REGISTROS, salvar_registros=True):
        self.llm, self.kb = llm, base_conhecimento
        self.pasta, self.salvar = pasta_registros, salvar_registros
        self.historico = []          # lista de dicts {role, content}; guardada só em memória

    def reset(self):
        self.historico = []

    def definir_historico(self, turnos):
        """Usado nos testes de continuação: injeta turnos anteriores [(papel, texto), ...]."""
        self.historico = [{"role": r, "content": t} for r, t in turnos]

    # ---------- protocolo simulado (sem dados pessoais) ----------
    def _registrar(self, dados):
        os.makedirs(self.pasta, exist_ok=True)
        arq = os.path.join(self.pasta, "protocolos.jsonl")
        n = sum(1 for _ in open(arq, encoding="utf-8")) + 1 if os.path.exists(arq) else 1
        agora = datetime.datetime.now()
        protocolo = f"ZU-{agora:%Y%m%d}-{n:04d}"
        registro = dict(protocolo=protocolo, data_hora=agora.isoformat(timespec="seconds"), simulado=True, **dados)
        if self.salvar:
            with open(arq, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return protocolo, registro

    def _extrair_dados(self):
        msgs = [{"role": "system", "content": PROMPT_EXTRACAO}] + self.historico[-HISTORICO_MAX_MENSAGENS:]
        try:
            bruto, t = self.llm.chat(msgs, json_only=True)
            m = re.search(r"\{.*\}", bruto, flags=re.S)
            d = json.loads(m.group(0))
        except Exception:
            return None, 0.0
        if not d.get("tipo") or not d.get("endereco"):
            return None, 0.0
        gravidade = d.get("gravidade") if d.get("gravidade") in ("baixa", "media", "alta") else "media"
        return dict(tipo=d["tipo"], endereco=str(d["endereco"]), gravidade=gravidade, detalhes=d.get("detalhes") or ""), t

    # ---------- turno ----------
    def responder(self, texto):
        t_ini = time.perf_counter()
        info = dict(rag_s=0.0, llm_s=0.0, protocolo=None, nivel_seguranca="ok", fontes=[])
        nivel, aviso = guardrails.verificar(texto)
        info["nivel_seguranca"] = nivel
        if nivel == "critico":
            self.historico += [{"role": "user", "content": texto}, {"role": "assistant", "content": aviso}]
            info["total_s"] = time.perf_counter() - t_ini
            return aviso, info

        # confirmação do pedido: extrai os dados e gera protocolo simulado
        ultimo_assistente = next((m["content"] for m in reversed(self.historico) if m["role"] == "assistant"), "")
        if RE_CONFIRMA.search(texto) and RE_PERGUNTA_CONFIRMACAO.search(ultimo_assistente):
            dados, t = self._extrair_dados()
            info["llm_s"] += t
            if dados:
                protocolo, _ = self._registrar(dados)
                info["protocolo"] = protocolo
                resp = (f"Pronto. Registrei neste protótipo o pedido de {TIPOS_NOME.get(dados['tipo'], dados['tipo'])} "
                        f"em {dados['endereco']}, com gravidade {dados['gravidade']}. O protocolo é {protocolo}. "
                        f"Como isto é uma demonstração, faça também o pedido oficial pelo SP156, telefone 156.")
                self.historico += [{"role": "user", "content": texto}, {"role": "assistant", "content": resp}]
                info["total_s"] = time.perf_counter() - t_ini
                return resp, info

        # RAG: usa a pergunta atual e a anterior do cidadão (para perguntas de continuação)
        t0 = time.perf_counter()
        anteriores = [m["content"] for m in self.historico if m["role"] == "user"][-1:]
        contexto, achados = self.kb.contexto(" ".join(anteriores + [texto]))
        info["rag_s"] = time.perf_counter() - t0
        info["fontes"] = sorted({c["fonte"] for _, c in achados})

        msgs = ([{"role": "system", "content": SYSTEM_PROMPT.format(contexto=contexto)}]
                + self.historico[-HISTORICO_MAX_MENSAGENS:] + [{"role": "user", "content": texto}])
        resposta, t = self.llm.chat(msgs)
        info["llm_s"] += t
        if nivel == "alerta":
            resposta = f"{aviso} {resposta}"
        self.historico += [{"role": "user", "content": texto}, {"role": "assistant", "content": resposta}]
        info["total_s"] = time.perf_counter() - t_ini
        return resposta, info
