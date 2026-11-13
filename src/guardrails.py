"""Salvaguardas determinísticas: emergências, saúde e apoio emocional nunca dependem só do LLM."""
import re, unicodedata


def _norm(t):
    t = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", t)


CRITICOS = [
    ("saude", r"sangr|ferid[oa]|desmai|inconscient|infarto|dor (forte )?no peito|falta de ar|nao (esta )?respir|engasg|afog|convuls|overdose",
     "Isso parece uma emergência de saúde. Eu não posso ajudar com isso. Ligue agora para o SAMU, 192, ou para os Bombeiros, 193. Se puder, peça para alguém ficar com a pessoa até a ajuda chegar."),
    ("gas", r"cheiro (forte )?de gas|vazamento de gas|gas vazando",
     "Cheiro de gás é perigoso. Afaste-se do local, não acenda fogo nem ligue aparelhos elétricos e ligue agora para os Bombeiros, 193."),
    ("eletrico", r"(fio|cabo|poste).{0,40}(caiu|caido|solto|faisca|soltando|pegando fogo)|faisca|choque eletrico",
     "Fio caído ou soltando faísca é muito perigoso. Mantenha distância, não encoste em nada que esteja perto e ligue agora para os Bombeiros, 193."),
    ("fogo", r"incendio|pegando fogo|fogo (no|na|em)",
     "Isso é uma emergência. Afaste-se e ligue agora para os Bombeiros, 193."),
    ("emocional", r"suicid|me matar|quero morrer|tirar a minha vida|acabar com a minha vida",
     "Sinto muito que você esteja passando por isso. Você não está sozinho. Ligue agora para o CVV, 188, a qualquer hora, ou para o SAMU, 192, se estiver em perigo. Se quiser, posso ficar por aqui enquanto você pede ajuda."),
]
ALERTAS = [
    ("risco_arvore", r"(arvore|galho|muro|poste).{0,40}(prestes a cair|vai cair|esta caindo|caiu em cima|caindo)",
     "Atenção: se há risco imediato para pessoas ou carros, afaste-se e ligue para a Defesa Civil, 199, ou para os Bombeiros, 193."),
    ("risco_enchente", r"enchente|inundacao|deslizamento|desabamento|desabou",
     "Atenção: em risco de enchente, deslizamento ou desabamento, ligue para a Defesa Civil, 199, ou para os Bombeiros, 193."),
]


def verificar(texto):
    """Retorna (nivel, texto): 'critico' (resposta fixa, sem LLM), 'alerta' (prefixo de segurança) ou ('ok', '')."""
    t = _norm(texto)
    for nome, padrao, resposta in CRITICOS:
        if re.search(padrao, t):
            return "critico", resposta
    for nome, padrao, resposta in ALERTAS:
        if re.search(padrao, t):
            return "alerta", resposta
    return "ok", ""
