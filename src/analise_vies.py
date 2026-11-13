"""Análise de viés do STT: compara o WER entre pessoas, condição (limpo x ruído) e, se preenchido,
perfis (gênero, faixa etária, sotaque) em dados/perfil_vozes.csv. Usa só o conjunto oficial (sem regravações)."""
import csv, glob, os

import pandas as pd

from .config import BASE, RESULTADOS


def carregar(prefixo="stt_"):
    arqs = [f for f in glob.glob(os.path.join(RESULTADOS, prefixo + "*.csv")) if "vies" not in f]
    if not arqs:
        return pd.DataFrame()
    df = pd.concat([pd.read_csv(f) for f in arqs], ignore_index=True)
    df = df[df["retake"] == False]                                    # noqa: E712
    perfil = os.path.join(BASE, "dados", "perfil_vozes.csv")
    if os.path.exists(perfil):
        p = pd.read_csv(perfil).fillna("")
        df = df.merge(p, on="pessoa", how="left")
    return df


def tabelas(df):
    t = {}
    t["por_modelo"] = df.groupby("modelo").agg(audios=("wer", "size"), wer_medio=("wer", "mean"),
                                                wer_mediano=("wer", "median"), tempo_stt_medio_s=("tempo_stt_s", "mean")).round(3)
    t["por_condicao"] = df.pivot_table(index="modelo", columns="condicao", values="wer", aggfunc="mean").round(3)
    t["por_pessoa"] = df.pivot_table(index="pessoa", columns="modelo", values="wer", aggfunc="mean").round(3)
    t["pessoa_condicao"] = df.pivot_table(index=["modelo", "pessoa"], columns="condicao", values="wer", aggfunc="mean").round(3)
    for col in ("genero", "faixa_etaria", "sotaque"):
        if col in df.columns and (df[col] != "").any():
            t[f"por_{col}"] = df[df[col] != ""].pivot_table(index=col, columns="modelo", values="wer", aggfunc="mean").round(3)
    return t


if __name__ == "__main__":
    df = carregar()
    if df.empty:
        raise SystemExit("Sem resultados de STT em resultados/. Rode avaliacao_stt primeiro.")
    t = tabelas(df)
    with open(os.path.join(RESULTADOS, "vies_stt.txt"), "w", encoding="utf-8") as f:
        for nome, tab in t.items():
            f.write(f"== {nome} ==\n{tab.to_string()}\n\n")
    print(open(os.path.join(RESULTADOS, "vies_stt.txt"), encoding="utf-8").read())
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ax = t["por_pessoa"].plot(kind="bar", figsize=(7, 3.6), rot=0)
    ax.set_ylabel("WER médio"); ax.set_xlabel(""); ax.set_title("WER por pessoa e modelo Whisper")
    plt.tight_layout(); plt.savefig(os.path.join(RESULTADOS, "fig_wer_pessoa.png"), dpi=160)
