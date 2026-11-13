"""Avalia o LLM nas 30 perguntas (15 do tema, 5 de continuação, 5 fora do escopo, 5 de emergência/limites).
Uso:  python -m src.avaliacao_llm --modelos qwen2.5:7b qwen2.5:3b      (precisa do Ollama com os modelos baixados)
      python -m src.avaliacao_llm --stub                                (teste de código; resultados NÃO são válidos)"""
import argparse, csv, json, os

from .config import BASE, KB_DIR, LLM_HOST, RAG_SCORE_MIN, RAG_TOP_K, RESULTADOS
from .dialogo import Dialogo
from .llm import OllamaChat, StubLLM
from .metricas import acerto_palavras_chave
from .rag import BaseConhecimento


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", nargs="+", default=["qwen2.5:7b", "qwen2.5:3b"])
    ap.add_argument("--stub", action="store_true")
    a = ap.parse_args()
    perguntas = list(csv.DictReader(open(os.path.join(BASE, "dados", "perguntas_llm.csv"), encoding="utf-8")))
    kb = BaseConhecimento(KB_DIR, RAG_TOP_K, RAG_SCORE_MIN)
    for modelo in (["stub"] if a.stub else a.modelos):
        llm = StubLLM() if a.stub else OllamaChat(modelo, LLM_HOST)
        linhas = []
        for p in perguntas:
            d = Dialogo(llm, kb, salvar_registros=False)
            d.definir_historico([tuple(x) for x in json.loads(p["contexto"])])
            resp, info = d.responder(p["pergunta"])
            linhas.append(dict(modelo=modelo, id=p["id"], tipo=p["tipo"], pergunta=p["pergunta"],
                               resposta_esperada=p["resposta_esperada"], resposta=resp,
                               tratada_por="salvaguarda" if info["nivel_seguranca"] == "critico" else "llm",
                               tempo_s=round(info["total_s"], 2),
                               correta_auto=int(acerto_palavras_chave(resp, p["palavras_chave"])), correta_manual=""))
        out = os.path.join(RESULTADOS, f"llm_{modelo.replace(':', '_')}.csv")
        os.makedirs(RESULTADOS, exist_ok=True)
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
            w.writeheader()
            w.writerows(linhas)
        for tipo in ["tema", "continuacao", "fora_escopo", "limite"]:
            sel = [l for l in linhas if l["tipo"] == tipo]
            print(f"{modelo} | {tipo}: {sum(l['correta_auto'] for l in sel)}/{len(sel)}")
        print(f"{modelo} | total: {sum(l['correta_auto'] for l in linhas)}/{len(linhas)}  -> {out}")


if __name__ == "__main__":
    main()
