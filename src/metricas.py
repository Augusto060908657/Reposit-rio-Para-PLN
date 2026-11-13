"""Funções de métrica compartilhadas pelos scripts de avaliação."""
import re, unicodedata
import jiwer
from num2words import num2words


def normaliza_wer(t):
    """Normalização usada no WER: minúsculas, números por extenso (CEP dígito a dígito), sem pontuação."""
    t = t.lower()
    t = re.sub(r"\b(\d{5})-?(\d{3})\b", lambda m: " ".join(num2words(int(d), lang="pt_BR") for d in m.group(1) + m.group(2)), t)
    t = re.sub(r"\d+(?:[.]\d{3})*", lambda m: num2words(int(m.group(0).replace(".", "")), lang="pt_BR"), t)
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def wer(referencia, hipotese):
    return jiwer.wer(normaliza_wer(referencia), normaliza_wer(hipotese))


def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


def acerto_palavras_chave(resposta, palavras_chave):
    """palavras_chave: grupos separados por ';' (todos devem aparecer); alternativas por '|' (qualquer uma serve)."""
    r = sem_acento(resposta)
    return all(any(sem_acento(alt.strip()) in r for alt in grupo.split("|") if alt.strip())
               for grupo in palavras_chave.split(";") if grupo.strip())
