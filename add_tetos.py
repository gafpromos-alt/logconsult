# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Parâmetros do Teto ANTT no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Extrai os parâmetros dos simuladores tarifários da ANTT (EFVM, FNS, RMN, FCA) e
grava em logconsult.db → tabela tetos_parametros (formato longo: 1 linha por
ferrovia × produto × faixa de distância).

Mecânica ANTT:  teto (R$/t) = PARCELA_FIXA + rate(faixa da distância) × distância
  - EFVM/FNS: rate único (uma faixa, até ∞)
  - RMN/FCA:  rate decrescente por faixa de distância (aplicado à distância total)

Uso:  python3 add_tetos.py
"""
import sqlite3, pathlib, warnings
import pandas as pd
warnings.simplefilter("ignore")

BASE = pathlib.Path(__file__).resolve().parent
SIM = BASE.parent / "02_Regulatorio_Tetos" / "Simuladores_Teto"
DB = BASE / "logconsult.db"

def rows_single(df, ferrovia, col_prod, col_rate, col_fixo="FIXO"):
    out = []
    for _, r in df.iterrows():
        prod = str(r.get(col_prod, "")).strip()
        if not prod or prod.lower() == "nan": continue
        fixo = r.get(col_fixo); rate = r.get(col_rate)
        if pd.isna(rate): continue
        out.append((ferrovia, prod.upper(), float(fixo) if pd.notna(fixo) else 0.0,
                    None, float(rate), str(r.get("VIGÊNCIA", ""))[:10],
                    str(r.get("DECISÃO", r.get("DECISÃO SUFER", "")))))
    return out

def rows_banded(df, ferrovia, bands):
    """bands: lista de (col, limite_sup_km|None)."""
    out = []
    for _, r in df.iterrows():
        prod = str(r.get("PRODUTO", "")).strip()
        if not prod or prod.lower() == "nan": continue
        fixo = float(r["FIXO"]) if pd.notna(r.get("FIXO")) else 0.0
        vig = str(r.get("VIGÊNCIA", ""))[:10]; dec = str(r.get("DECISÃO", ""))
        for col, lim in bands:
            rate = r.get(col)
            if pd.isna(rate): continue
            out.append((ferrovia, prod.upper(), fixo, lim, float(rate), vig, dec))
    return out

def main():
    recs = []
    # EFVM — rate único na coluna 'ÚNICA', produto em 'MERCADORIA'
    efvm = pd.read_excel(SIM / "Simulador Tarifário EFVM_2025.xlsx", sheet_name="PRODUTOS")
    recs += rows_single(efvm, "EFVM", "MERCADORIA", "ÚNICA")
    # FNS — rate único em 'VARIÁVEL'. Atualizado p/ vigência 2026-01-22 (Decisão SUFER 2/2026,
    # reajuste ANTT publicado 12/02/2026) — arquivo 2025 mantido na pasta como histórico.
    fns = pd.read_excel(SIM / "Simulador Tarifário FNS - 2026.xlsx", sheet_name="PRODUTOS")
    recs += rows_single(fns, "FNS", "PRODUTO", "VARIÁVEL")
    # RMN — faixas 0-400 / 401-800 / 801-1600 / >1600
    rmn = pd.read_excel(SIM / "Simulador Tarifário RMN 2025.xlsx", sheet_name="PRODUTOS")
    recs += rows_banded(rmn, "RMN", [("0_A_400", 400), ("401_A_800", 800),
                                     ("801_A_1600", 1600), ("ACIMA_1600", None)])
    # FCA — faixas 0-500 / 501-1000 / 1001-2000 / >2000
    fca = pd.read_excel(SIM / "Simulador Tarifário FCA - 2025.xls", sheet_name="PRODUTOS")
    recs += rows_banded(fca, "FCA", [("0_A_500", 500), ("501_A_1000", 1000),
                                     ("1001_A_2000", 2000), ("ACIMA_2000", None)])

    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS tetos_parametros")
    cur.execute("""CREATE TABLE tetos_parametros(
        ferrovia TEXT, produto TEXT, fixo REAL, banda_ate_km REAL, rate REAL,
        vigencia TEXT, decisao TEXT)""")
    cur.executemany("INSERT INTO tetos_parametros VALUES (?,?,?,?,?,?,?)", recs)
    con.commit()
    print(f"tetos_parametros: {len(recs)} linhas")
    for fer, in cur.execute("SELECT DISTINCT ferrovia FROM tetos_parametros"):
        n = cur.execute("SELECT COUNT(DISTINCT produto) FROM tetos_parametros WHERE ferrovia=?", (fer,)).fetchone()[0]
        print(f"  {fer}: {n} produtos")
    # sanity: teto FNS Grãos e Farelos @ 704 km
    row = cur.execute("SELECT fixo,rate FROM tetos_parametros WHERE ferrovia='FNS' AND produto LIKE 'GRÃOS%'").fetchone()
    if row: print(f"  check FNS Grãos@704km: R$ {row[0]+row[1]*704:.2f}/t")
    con.close()

if __name__ == "__main__":
    main()
