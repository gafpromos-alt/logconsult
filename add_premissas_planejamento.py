# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Premissas de Planejamento (VLI) no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: "2026-VLI_BOOK_Orçamento_20206_V1.35.xlsx" (07_Dados VLI) — book interno de
orçamento/planejamento da VLI com 157 abas (corredores, ferrovia, portos, terminais,
material rodante, manutenção etc.). Dado o volume, este primeiro corte ingere as abas
de escopo GERAL (matrizes de volume por corredor/ativo, cenário 2026-Orçamento) — as
~150 abas restantes são detalhamento operacional por corredor específico (material
rodante, ciclo de vagão, giro/TT, alocação de locomotiva, faixa VP etc.) e ficam de
fora deste corte; ver relatório de escopo enviado ao usuário.

Abas ingeridas (todas cenário "2026 - Orçamento", header em linha variável — cada
aba tem 2-3 linhas de título antes do cabeçalho real, tratado por sheet):
  - "Ferrovia - Base Vol. TU"  -> premissa_ferrovia_vol_tu   (2743 linhas, por fluxo)
  - "Ferrovia - Base Vol. TKU" -> premissa_ferrovia_vol_tku  (por fluxo, TKU=t*km)
  - "Porto - Base Vol. TU"     -> premissa_porto_vol_tu      (por fluxo de porto)
  - "Terminal - Base Vol. TU"  -> premissa_terminal_vol_tu   (por terminal)
  - "Ferrovia - Vol. Consolidado" -> premissa_ferrovia_vol_consolidado (MTKU por ativo/mês)

Uso:  python3 add_premissas_planejamento.py
"""
import pathlib
import sqlite3

import numpy as np
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent
VLI = BASE.parent / "07_Dados VLI"
DB = BASE / "logconsult.db"
XLSX = VLI / "2026-VLI_BOOK_Orçamento_20206_V1.35.xlsx"

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
MESES_COL = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _read(sheet, header):
    df = pd.read_excel(XLSX, sheet_name=sheet, header=header)
    df = df.drop(columns=[c for c in df.columns if str(c).startswith("Unnamed")], errors="ignore")
    df = df.dropna(how="all")
    return df


def _meses_rename(df):
    return df.rename(columns=dict(zip(MESES, MESES_COL)))


def ferrovia_vol_tu():
    df = _read("Ferrovia - Base Vol. TU", header=5)
    df = df.rename(columns={
        "Corredor": "corredor", "Fluxo ": "fluxo", "Segmento Comercial": "segmento",
        "Produto Agrupado (N2)": "produto", "Cliente": "cliente", "Mercadoria": "mercadoria",
        "Origem": "origem", "Destino": "destino", "Tráfego": "trafego", "Total": "total_tu",
        "Ativo de origem": "ativo_origem", "Ativo de destino": "ativo_destino",
    })
    df = _meses_rename(df)
    df = df[df["corredor"].notna()]
    for c in MESES_COL + ["total_tu"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(1)
    cols = ["corredor", "fluxo", "segmento", "produto", "cliente", "mercadoria", "origem",
            "destino", "trafego"] + MESES_COL + ["total_tu", "ativo_origem", "ativo_destino"]
    return df[cols]


def ferrovia_vol_tku():
    df = _read("Ferrovia - Base Vol. TKU", header=5)
    df = df.rename(columns={
        "Corredor": "corredor", "Fluxo gestão": "fluxo", "Segmentos": "segmento",
        "Produto gestão": "produto", "Cliente gestão": "cliente", "Origem": "origem",
        "Destino": "destino", "Ferrovia": "ferrovia", "Total": "total_tku",
    })
    df = _meses_rename(df)
    df = df[df["corredor"].notna()]
    for c in MESES_COL + ["total_tku"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(0)
    cols = ["corredor", "fluxo", "segmento", "produto", "cliente", "origem", "destino",
            "ferrovia"] + MESES_COL + ["total_tku"]
    return df[cols]


def porto_vol_tu():
    df = _read("Porto - Base Vol. TU", header=5)
    df = df.rename(columns={
        "Corredor": "corredor", "Fluxo": "fluxo", "Segmento Comercial": "segmento",
        "Mercadoria": "mercadoria", "Cliente": "cliente", "Porto": "porto", "Total": "total_tu",
    })
    df = _meses_rename(df)
    df = df[df["corredor"].notna()]
    for c in MESES_COL + ["total_tu"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(1)
    cols = ["corredor", "fluxo", "segmento", "mercadoria", "cliente", "porto"] + MESES_COL + ["total_tu"]
    return df[cols]


def terminal_vol_tu():
    df = _read("Terminal - Base Vol. TU", header=5)
    df = df.rename(columns={
        "TERMINAIS": "terminal", "ORIGEM": "origem", "DESTINO": "destino",
        "PRODUTO": "produto", "Total": "total_tu",
    })
    df = _meses_rename(df)
    df = df[df["terminal"].notna()]
    for c in MESES_COL + ["total_tu"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).round(1)
    cols = ["terminal", "origem", "destino", "produto"] + MESES_COL + ["total_tu"]
    return df[cols]


def vol_consolidado():
    """Aba tem 3 blocos empilhados (unidades diferentes): Ferrovia (MTKU), Portos (TU),
    Terminais (TU) — cada um com seu próprio cabeçalho "Ativo"/mês. Detecta os blocos
    pelas linhas-título ("Acompanhamento Volume Mensal ...") e re-lê cada um com o
    cabeçalho correto, descartando linhas de seção/"Total" para não duplicar."""
    raw = pd.read_excel(XLSX, sheet_name="Ferrovia - Vol. Consolidado", header=None)
    col1 = raw[1].astype(str)
    starts = sorted(col1[col1.str.contains("Acompanhamento Volume Mensal", na=False)].index.tolist())
    unidades = {"Ferrovia": "MTKU", "Portos": "TU", "Terminais": "TU"}
    blocos = []
    for i, start in enumerate(starts):
        titulo = col1[start]
        label = "Ferrovia" if "Ferrovia" in titulo else ("Portos" if "Portos" in titulo else "Terminais")
        header_row = start + 1
        end = starts[i + 1] if i + 1 < len(starts) else len(raw)
        block = raw.iloc[header_row:end].copy()
        block.columns = raw.iloc[header_row]
        block = block.iloc[1:]
        block = block.rename(columns={block.columns[1]: "ativo", "Total": "total"})
        block = _meses_rename(block)
        block = block[["ativo"] + MESES_COL + ["total"]]
        block = block[block["ativo"].notna()]
        block = block[~block["ativo"].astype(str).str.contains("Total|Acompanhamento", na=False)]
        block = block[block["ativo"] != label]  # linha-título repetida como valor (ex.: "Portos")
        for c in MESES_COL + ["total"]:
            block[c] = pd.to_numeric(block[c], errors="coerce").fillna(0).round(2)
        block["grupo"] = label
        block["unidade"] = unidades[label]
        blocos.append(block)
    out = pd.concat(blocos, ignore_index=True)
    return out[["grupo", "unidade", "ativo"] + MESES_COL + ["total"]]


def main():
    tabelas = {
        "premissa_ferrovia_vol_tu": ferrovia_vol_tu(),
        "premissa_ferrovia_vol_tku": ferrovia_vol_tku(),
        "premissa_porto_vol_tu": porto_vol_tu(),
        "premissa_terminal_vol_tu": terminal_vol_tu(),
        "premissa_vol_consolidado": vol_consolidado(),
    }
    con = sqlite3.connect(DB)
    for nome, df in tabelas.items():
        df.to_sql(nome, con, if_exists="replace", index=False)
        print(f"{nome}: {len(df)} linhas")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
