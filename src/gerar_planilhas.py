"""Gera as planilhas de avaliação (.xlsx) com fórmulas: STT (dados reais dos CSVs), LLM (30 perguntas) e TTS (3 avaliadores).
Pode ser rodado de novo depois do Colab para incluir os novos resultados.   Uso: python -m src.gerar_planilhas"""
import csv, glob, os

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .config import BASE, RESULTADOS

F = "Arial"
CAB = PatternFill("solid", fgColor="1F3A5F")
ENT = PatternFill("solid", fgColor="FFF2CC")      # células para preencher
OUT = os.path.join(BASE, "planilhas")


def _cab(ws, linha, titulos, larguras=None):
    for i, t in enumerate(titulos, 1):
        c = ws.cell(row=linha, column=i, value=t)
        c.font, c.fill = Font(name=F, bold=True, color="FFFFFF"), CAB
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(larguras or [], 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _fonte(ws):
    for row in ws.iter_rows():
        for c in row:
            if c.font.name != F:
                c.font = Font(name=F, bold=c.font.bold, color=c.font.color, size=c.font.size)
            c.alignment = Alignment(wrap_text=True, vertical="top", horizontal=c.alignment.horizontal)


def stt():
    arqs = sorted(f for f in glob.glob(os.path.join(RESULTADOS, "stt_*.csv")) if "vies" not in f)
    if not arqs:
        return
    linhas = [r for f in arqs for r in csv.DictReader(open(f, encoding="utf-8"))]
    wb = Workbook()
    ws = wb.active
    ws.title = "Dados"
    _cab(ws, 1, ["Modelo", "Arquivo", "Pessoa", "Condição", "Regravação?", "Duração (s)", "Tempo STT (s)", "WER", "Referência", "Transcrição do modelo"],
         [10, 30, 10, 10, 11, 11, 12, 8, 55, 55])
    for i, r in enumerate(linhas, 2):
        ws.append([r["modelo"], r["arquivo"], r["pessoa"], r["condicao"], "sim" if r["retake"] == "True" else "nao",
                   float(r["duracao_s"]), float(r["tempo_stt_s"]), float(r["wer"]), r["referencia"], r["hipotese"]])
    n = len(linhas) + 1
    for i in range(2, n + 1):
        ws.cell(row=i, column=8).number_format = "0.0%"
    ws.freeze_panes = "A2"
    rs = wb.create_sheet("Resumo")
    modelos = sorted({r["modelo"] for r in linhas}, key=lambda m: ["base", "small", "medium"].index(m) if m in ("base", "small", "medium") else 9)
    pessoas = sorted({r["pessoa"] for r in linhas})
    rs["A1"] = "WER (Word Error Rate) calculado com jiwer sobre o conjunto oficial (regravações excluídas). Fórmulas sobre a aba Dados."
    rs["A1"].font = Font(name=F, italic=True)
    _cab(rs, 3, ["Modelo", "Áudios", "WER médio", "WER limpo", "WER ruído", "Tempo STT médio (s)"], [14, 10, 12, 12, 12, 18])
    for i, m in enumerate(modelos, 4):
        rs.cell(row=i, column=1, value=m)
        base = f"Dados!$A$2:$A${n},$A{i},Dados!$E$2:$E${n},\"nao\""
        rs.cell(row=i, column=2, value=f"=COUNTIFS({base})")
        rs.cell(row=i, column=3, value=f"=AVERAGEIFS(Dados!$H$2:$H${n},{base})")
        rs.cell(row=i, column=4, value=f"=AVERAGEIFS(Dados!$H$2:$H${n},{base},Dados!$D$2:$D${n},\"limpo\")")
        rs.cell(row=i, column=5, value=f"=AVERAGEIFS(Dados!$H$2:$H${n},{base},Dados!$D$2:$D${n},\"ruido\")")
        rs.cell(row=i, column=6, value=f"=AVERAGEIFS(Dados!$G$2:$G${n},{base})")
        for c in (3, 4, 5):
            rs.cell(row=i, column=c).number_format = "0.0%"
        rs.cell(row=i, column=6).number_format = "0.00"
    l0 = 5 + len(modelos)
    _cab(rs, l0, ["Pessoa"] + [f"WER {m}" for m in modelos])
    for j, p in enumerate(pessoas, l0 + 1):
        rs.cell(row=j, column=1, value=p)
        for k, m in enumerate(modelos, 2):
            c = rs.cell(row=j, column=k, value=f"=AVERAGEIFS(Dados!$H$2:$H${n},Dados!$A$2:$A${n},\"{m}\",Dados!$C$2:$C${n},$A{j},Dados!$E$2:$E${n},\"nao\")")
            c.number_format = "0.0%"
    for ws_ in (ws, rs):
        _fonte(ws_)
    os.makedirs(OUT, exist_ok=True)
    wb.save(os.path.join(OUT, "planilha_avaliacao_STT.xlsx"))


def llm():
    perguntas = list(csv.DictReader(open(os.path.join(BASE, "dados", "perguntas_llm.csv"), encoding="utf-8")))
    res = {}
    for f in sorted(glob.glob(os.path.join(RESULTADOS, "llm_*.csv"))):
        if "stub" in f:
            continue
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        res[rows[0]["modelo"]] = {r["id"]: r for r in rows}
    modelos = list(res) or ["modelo_A", "modelo_B"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Perguntas"
    cab = ["ID", "Tipo", "Pergunta", "Resposta esperada"]
    for m in modelos:
        cab += [f"Resposta {m}", f"Auto {m} (1/0)", f"Manual {m} (1/0)", f"Final {m}"]
    _cab(ws, 1, cab, [5, 12, 40, 40] + [45, 10, 10, 10] * len(modelos))
    for i, p in enumerate(perguntas, 2):
        linha = [int(p["id"]), p["tipo"], p["pergunta"], p["resposta_esperada"]]
        for k, m in enumerate(modelos):
            r = res.get(m, {}).get(p["id"])
            auto, man = get_column_letter(6 + 4 * k), get_column_letter(7 + 4 * k)
            linha += [r["resposta"] if r else "", int(r["correta_auto"]) if r else None, None,
                      f'=IF({man}{i}<>"",{man}{i},IF({auto}{i}<>"",{auto}{i},""))']
        ws.append(linha)
        for k in range(len(modelos)):
            ws.cell(row=i, column=7 + 4 * k).fill = ENT
    ws.freeze_panes = "C2"
    rs = wb.create_sheet("Resumo")
    rs["A1"] = ("A coluna Final usa a nota manual quando preenchida e, se não, a automática (palavras-chave). "
                "Células amarelas = preencher. Auto/Manual: 1 = correta, 0 = incorreta.")
    rs["A1"].font = Font(name=F, italic=True)
    _cab(rs, 3, ["Modelo", "Tema (15)", "Continuação (5)", "Fora do escopo (5)", "Emergência/limites (5)", "Total (30)"], [24, 14, 16, 18, 22, 12])
    for k, m in enumerate(modelos):
        i = 4 + k
        fin = get_column_letter(9 + 4 * k)
        rs.cell(row=i, column=1, value=m)
        for j, tipo in enumerate(["tema", "continuacao", "fora_escopo", "limite"], 2):
            rs.cell(row=i, column=j, value=f'=IFERROR(SUMIFS(Perguntas!${fin}$2:${fin}$31,Perguntas!$B$2:$B$31,"{tipo}")/COUNTIF(Perguntas!$B$2:$B$31,"{tipo}"),"")').number_format = "0%"
        rs.cell(row=i, column=6, value=f'=IFERROR(SUM(Perguntas!${fin}$2:${fin}$31)/30,"")').number_format = "0%"
    for ws_ in (ws, rs):
        _fonte(ws_)
    wb.save(os.path.join(OUT, "planilha_avaliacao_LLM.xlsx"))


def tts():
    frases = list(csv.DictReader(open(os.path.join(BASE, "dados", "frases_tts.csv"), encoding="utf-8")))
    wb = Workbook()
    ws = wb.active
    ws.title = "Avaliação TTS"
    ws["A1"] = "Ouça cada áudio em resultados/tts_amostras e dê notas de 1 (péssimo) a 5 (excelente). Preencha só as células amarelas."
    ws["A1"].font = Font(name=F, bold=True)
    ws["A2"] = "Naturalidade: quão parecida com fala humana soa a voz. Clareza: quão fácil é entender cada palavra, número e sigla."
    ws["A2"].font = Font(name=F, italic=True)
    tit = ["ID", "Texto falado"]
    for av in ("Avaliador 1", "Avaliador 2", "Avaliador 3"):
        tit += [f"{av} naturalidade", f"{av} clareza"]
    tit += ["Média naturalidade", "Média clareza"]
    _cab(ws, 4, tit, [8, 60, 12, 10, 12, 10, 12, 10, 14, 12])
    ws.append(["EXEMPLO", "(linha de exemplo do formato, não entra na média)", 4, 5, 3, 4, 4, 4, "=AVERAGE(C5,E5,G5)", "=AVERAGE(D5,F5,H5)"])
    for i, f in enumerate(frases, 6):
        ws.append([f["id"], f["resposta_do_assistente"], None, None, None, None, None, None,
                   f"=IF(COUNT(C{i},E{i},G{i})=0,\"\",AVERAGE(C{i},E{i},G{i}))", f"=IF(COUNT(D{i},F{i},H{i})=0,\"\",AVERAGE(D{i},F{i},H{i}))"])
        for c in range(3, 9):
            ws.cell(row=i, column=c).fill = ENT
        for c in (9, 10):
            ws.cell(row=i, column=c).number_format = "0.00"
    ws.append([])
    r = ws.max_row + 1
    ws.cell(row=r, column=2, value="NOTA MÉDIA GERAL (10 respostas)").font = Font(name=F, bold=True)
    ws.cell(row=r, column=9, value="=IF(COUNT(I6:I15)=0,\"\",AVERAGE(I6:I15))").number_format = "0.00"
    ws.cell(row=r, column=10, value="=IF(COUNT(J6:J15)=0,\"\",AVERAGE(J6:J15))").number_format = "0.00"
    ws.cell(row=r + 2, column=2, value="Avaliadores (nome ou apelido, perfil resumido):")
    for i in range(3):
        ws.cell(row=r + 3 + i, column=2, value=f"Avaliador {i + 1}: ").fill = ENT
    _fonte(ws)
    wb.save(os.path.join(OUT, "planilha_avaliacao_TTS.xlsx"))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    stt(); llm(); tts()
    print("Planilhas em", OUT)
