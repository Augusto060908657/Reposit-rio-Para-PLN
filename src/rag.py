"""Base de conhecimento do tema com RAG leve (TF-IDF). Sem download de modelos de embedding, gratuito e rápido."""
import glob, os, re, unicodedata
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PARADAS = ["a", "o", "as", "os", "de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos", "um", "uma",
           "e", "ou", "que", "para", "por", "com", "se", "eu", "meu", "minha", "isso", "esse", "essa", "ele",
           "ela", "como", "qual", "quem", "onde", "faco", "fazer", "posso", "pode", "ao", "aos", "ja", "mais"]


def _sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


_PARADAS_SA = {_sem_acento(p) for p in PARADAS}


def _stem(w):
    for suf in ("coes", "oes", "res", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)] if suf != "res" else w[:-2]
    return w


def analisador(texto):
    palavras = re.findall(r"[a-z0-9]+", _sem_acento(texto.lower()))
    return [_stem(w) for w in palavras if w not in _PARADAS_SA and len(w) > 1]


class BaseConhecimento:
    def __init__(self, pasta, top_k=4, score_min=0.05):
        self.top_k, self.score_min = top_k, score_min
        self.chunks, self.fixo = [], ""
        for arq in sorted(glob.glob(os.path.join(pasta, "*.md"))):
            linhas = [l.strip() for l in open(arq, encoding="utf-8").read().splitlines() if l.strip()]
            titulo = linhas[0].lstrip("# ").strip()
            corpo = [l for l in linhas[1:]]
            if os.path.basename(arq).startswith("00_"):
                self.fixo = " ".join(corpo)           # contexto sempre presente (papel e limites do assistente)
                continue
            for l in corpo:
                self.chunks.append(dict(fonte=os.path.basename(arq), titulo=titulo, texto=f"{titulo}: {l}"))
        self.vet = TfidfVectorizer(analyzer=analisador, sublinear_tf=True)
        self.matriz = self.vet.fit_transform([c["texto"] for c in self.chunks])

    def recuperar(self, consulta):
        sims = cosine_similarity(self.vet.transform([consulta]), self.matriz)[0]
        idx = sims.argsort()[::-1][: self.top_k]
        return [(float(sims[i]), self.chunks[i]) for i in idx if sims[i] >= self.score_min]

    def contexto(self, consulta):
        achados = self.recuperar(consulta)
        partes = [f"[Papel do assistente] {self.fixo}"]
        if achados:
            partes += [f"[{c['fonte']}] {c['texto']}" for _, c in achados]
        else:
            partes.append("(Nenhuma informação da base de conhecimento é relevante para esta pergunta.)")
        return "\n".join(partes), achados
