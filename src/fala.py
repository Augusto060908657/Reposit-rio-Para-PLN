"""Adaptação do texto para fala: sem markdown, sem emojis, frases curtas e números/siglas pronunciáveis."""
import re
from num2words import num2words

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
DIGITOS = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
# números de serviço falados dígito a dígito (como a população fala ao telefone)
TELEFONES = {"156", "188", "190", "192", "193", "195", "199"}
SIGLAS = {"SUS": "S U S", "CPF": "C P F", "RG": "R G", "LGPD": "L G P D", "CET": "C E T",
          "ONU": "Onu", "ODS": "O D S", "SAMU": "Samu", "CVV": "C V V", "SP": "S P", "ZU": "Z U",
          "CEP": "cép", "WhatsApp": "uatsapp", "app": "aplicativo", "APP": "aplicativo"}
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200d]+", flags=re.UNICODE)


def _n(x):
    return num2words(int(x), lang="pt_BR")


def _digitos(s):
    return " ".join(DIGITOS[int(c)] for c in s if c.isdigit())


def remover_markdown(t):
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)           # links
    t = re.sub(r"https?://\S+", "", t)
    t = re.sub(r"^\s{0,3}#{1,6}\s*", "", t, flags=re.M)        # títulos
    t = re.sub(r"^\s*[-*•]\s+", "", t, flags=re.M)             # marcadores
    t = re.sub(r"^\s*\d+[.)]\s+", "", t, flags=re.M)           # listas numeradas
    t = re.sub(r"[*_`~>|]+", "", t)
    return t


def _protocolo(m):
    ano, mes, dia, seq = m.group(1)[:4], m.group(1)[4:6], m.group(1)[6:8], m.group(2)
    return f"Z U, {_digitos(ano)}, {_digitos(mes)}, {_digitos(dia)}, número {_digitos(seq)}"


def numeros_por_extenso(t):
    t = re.sub(r"\bZU-(\d{8})-(\d{3,5})\b", _protocolo, t)
    t = re.sub(r"\bSP\s?156\b", "S P um cinco seis", t)
    t = re.sub(r"\b(\d{5})-(\d{3})\b", lambda m: _digitos(m.group(1)) + ", " + _digitos(m.group(2)), t)  # CEP
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b",
               lambda m: f"{_n(m.group(1))} de {MESES[int(m.group(2)) - 1]} de {_n(m.group(3))}"
               if 1 <= int(m.group(2)) <= 12 else m.group(0), t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})\b",
               lambda m: f"{_n(m.group(1))} do {_n(m.group(2))}" if 1 <= int(m.group(2)) <= 12 else m.group(0), t)
    t = re.sub(r"\b(\d{1,2})h(\d{2})\b", lambda m: f"{_n(m.group(1))} horas e {_n(m.group(2))}", t)
    t = re.sub(r"\b(\d{1,2}):(\d{2})\b", lambda m: f"{_n(m.group(1))} horas e {_n(m.group(2))}", t)
    t = re.sub(r"\b(\d{1,2})h\b", lambda m: f"{_n(m.group(1))} horas", t)
    t = re.sub(r"R\$\s?(\d+)(?:,(\d{2}))?",
               lambda m: _n(m.group(1)) + " reais" + (f" e {_n(m.group(2))} centavos" if m.group(2) and int(m.group(2)) else ""), t)
    t = re.sub(r"\b(\d+),(\d+)\b", lambda m: f"{_n(m.group(1))} vírgula {_digitos(m.group(2))}", t)
    t = re.sub(r"\s?%", " por cento", t)
    t = re.sub(r"\b(\d+)\s?km\b", lambda m: f"{_n(m.group(1))} quilômetros", t)
    t = re.sub(r"\bkm\b", "quilômetros", t)
    t = re.sub(r"\b[nN][º°o]\.?\s?(?=\d)", "número ", t)
    t = re.sub(r"\b\d{3}\b", lambda m: _digitos(m.group(0)) if m.group(0) in TELEFONES else _n(m.group(0)), t)
    t = re.sub(r"\b\d+(?:\.\d{3})*\b", lambda m: _n(m.group(0).replace(".", "")), t)
    return t


def siglas(t):
    for k, v in SIGLAS.items():
        t = re.sub(rf"\b{k}\b", v, t)
    return t


def frases_curtas(t, max_palavras=22):
    """Divide em frases; frases longas são quebradas em vírgulas ou conectivos para soarem naturais."""
    saida = []
    for frase in re.split(r"(?<=[.!?])\s+", t.strip()):
        frase = frase.strip()
        if not frase:
            continue
        if len(frase.split()) <= max_palavras:
            saida.append(frase)
            continue
        partes = re.split(r",\s+", frase)
        atual = ""
        for p in partes:
            if len((atual + " " + p).split()) > max_palavras and atual:
                saida.append(atual.rstrip(",") + ".")
                atual = p[:1].upper() + p[1:]
            else:
                atual = (atual + ", " + p) if atual else p
        if atual:
            saida.append(atual if atual[-1] in ".!?" else atual + ".")
    return " ".join(saida)


def adaptar_para_fala(texto):
    t = EMOJI.sub("", texto)
    t = remover_markdown(t)
    t = t.replace("\n", ". ")
    t = re.sub(r"\.\s*\.", ".", t)
    t = numeros_por_extenso(t)
    t = siglas(t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([,.!?])", r"\1", t)
    t = frases_curtas(t)
    return t if not t or t[-1] in ".!?" else t + "."
