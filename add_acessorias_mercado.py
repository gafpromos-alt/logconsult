# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Acessórias públicas das ferrovias no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Extrai as tabelas de operações acessórias publicadas nos sites das concessionárias
(VLI, RUMO, MRS, Vale — divulgação obrigatória, Res. ANTT 6.031/2023) e grava em
logconsult.db → tabela acessorias_mercado (1 linha por ferrovia × malha × mercadoria
× serviço, com mínimo/média/máximo/desvio observados na base de cada concessionária).

Fontes (baixadas em 2026-07-10, arquivos em 02_Regulatorio_Tetos/Tabelas_Acessorias/):
  - VLI (FCA/FNS): Tabelas-Acessorias-VLI-2026.xlsx — abas "FCA 25"/"FNS 2025",
    bloco único por malha, serviços em grupos de 4 colunas (Mínimo/Média/Máximo/Desvio).
  - RUMO (RMN/RMC/RMP/RMS): RUMO-Acessorias-2026.xlsx — aba "Acessórias a partir out24",
    blocos repetidos por malha (mesmo layout de grupo de 4 colunas por serviço).
  - MRS (rede, sem quebra por malha/mercadoria): MRS-Acessorios-2026.xls — aba única
    "Taxas Acessórias", 1 linha por serviço (Amarração/Manobra/Transbordo/...).
  - Vale (EFVM/EFC — as duas ferrovias próprias da Vale, não operadas pela VLI):
    Vale-EFVM-Acessorias-2024.xlsx (aba "EFVM 2024", serviços Manobra/Baldeação/Transbordo)
    e Vale-EFC-Acessorias-2024.xlsx (aba "EFC 2024", serviços Manobra/Baldeação/Transbordo/
    Carregamento) — mesmo layout de bloco único por malha do VLI, baixados de vale.com
    (link "Ancillary Services" em vale.com/logistics, seção EFVM/EFC).

Uso:  python3 add_acessorias_mercado.py
"""
import sqlite3, pathlib
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent
TAB = BASE.parent / "02_Regulatorio_Tetos" / "Tabelas_Acessorias"
DB = BASE / "logconsult.db"
DATA_COLETA = "2026-07-10"


def parse_blocos(path, sheet, malha_fixa=None, malhas_validas=None):
    """Bloco genérico (VLI, RUMO, Vale): [linha malha opcional] linha 'Mercadoria' com
    nomes de serviço a cada 4 colunas (merged, propaga p/ direita) -> subheader
    Mínimo/Média/Máximo/Desvio -> linhas de dado até a mercadoria ficar vazia.
    A coluna onde "Mercadoria" aparece varia entre planilhas (col1 na VLI/RUMO, col0 na
    Vale — sem coluna em branco à esquerda) — detecta a posição em vez de fixar índice."""
    df = pd.read_excel(path, sheet_name=sheet, header=None)
    out, i, n = [], 0, len(df)
    while i < n:
        row = df.iloc[i]
        malha = malha_fixa
        if malhas_validas and row[1] in malhas_validas:
            malha = row[1]
            i += 1
            row = df.iloc[i]
        merc_col = next((c for c in range(len(row))
                          if isinstance(row[c], str) and row[c].strip().lower() == "mercadoria"), None)
        if merc_col is not None:
            unidade_col = merc_col + 1
            servicos, last_serv = {}, None
            for c in range(merc_col + 2, len(row)):
                v = row[c]
                if isinstance(v, str) and v.strip():
                    last_serv = v.strip()
                if last_serv:
                    servicos.setdefault(last_serv, []).append(c)
            i += 2
            while i < n:
                r = df.iloc[i]
                merc = r[merc_col]
                if not isinstance(merc, str) or not merc.strip():
                    break
                unidade = r[unidade_col]
                for serv, cols in servicos.items():
                    cols4 = cols[:4]
                    if len(cols4) < 4:
                        continue
                    vmin, vmed, vmax, vdev = [r[c] for c in cols4]
                    if pd.isna(vmin) and pd.isna(vmed) and pd.isna(vmax):
                        continue
                    out.append(dict(malha=malha, mercadoria=merc.strip(), unidade=unidade, servico=serv,
                                     valor_min=vmin, valor_medio=vmed, valor_max=vmax, desvio=vdev))
                i += 1
        else:
            i += 1
    return pd.DataFrame(out)


def parse_mrs(path):
    """MRS: 1 aba única, sem quebra por malha/mercadoria — 1 linha por serviço."""
    df = pd.read_excel(path, sheet_name="Taxas Acessórias", header=None)
    out, i, n = [], 4, len(df)
    while i < n:
        r = df.iloc[i]
        serv = r[1]
        if not isinstance(serv, str) or not serv.strip():
            break
        out.append(dict(malha="Rede MRS", mercadoria=None, unidade="R$/Ton", servico=serv.strip(),
                         valor_min=r[4], valor_medio=r[5], valor_max=r[3], desvio=r[6]))
        i += 1
    return pd.DataFrame(out)


def main():
    vli = pd.concat([
        parse_blocos(TAB / "Tabelas-Acessorias-VLI-2026.xlsx", "FCA 25", malha_fixa="FCA"),
        parse_blocos(TAB / "Tabelas-Acessorias-VLI-2026.xlsx", "FNS 2025", malha_fixa="FNS"),
    ], ignore_index=True)
    vli["ferrovia"] = "VLI"
    vli["fonte"] = "Site VLI — Tabela de Tarifas Acessórias"

    rumo = parse_blocos(TAB / "RUMO-Acessorias-2026.xlsx", "Acessórias a partir out24",
                         malhas_validas={"RMN", "RMC", "RMP", "RMS", "RMO"})
    rumo["ferrovia"] = "RUMO"
    rumo["fonte"] = "Site RUMO — Tabela de Tarifas e Operações Acessórias"

    mrs = parse_mrs(TAB / "MRS-Acessorios-2026.xls")
    mrs["ferrovia"] = "MRS"
    mrs["fonte"] = "Site MRS — Relação de Operações Acessórias"

    vale = pd.concat([
        parse_blocos(TAB / "Vale-EFVM-Acessorias-2024.xlsx", "EFVM 2024", malha_fixa="EFVM"),
        parse_blocos(TAB / "Vale-EFC-Acessorias-2024.xlsx", "EFC 2024", malha_fixa="EFC"),
    ], ignore_index=True)
    vale["ferrovia"] = "VALE"
    vale["fonte"] = "Site Vale — Tabela de Tarifas Acessórias (EFVM/EFC)"

    acess = pd.concat([vli, rumo, mrs, vale], ignore_index=True)
    acess["mercadoria"] = acess["mercadoria"].str.upper().where(acess["mercadoria"].notna(), None)
    acess["servico"] = acess["servico"].str.strip()
    for c in ["valor_min", "valor_medio", "valor_max", "desvio"]:
        acess[c] = pd.to_numeric(acess[c], errors="coerce").round(2)
    acess["data_coleta"] = DATA_COLETA
    acess = acess[["ferrovia", "malha", "mercadoria", "unidade", "servico",
                    "valor_min", "valor_medio", "valor_max", "desvio", "fonte", "data_coleta"]]

    con = sqlite3.connect(DB)
    acess.to_sql("acessorias_mercado", con, if_exists="replace", index=False)
    con.commit()

    print(f"acessorias_mercado: {len(acess)} linhas")
    for fer, g in acess.groupby("ferrovia"):
        malhas = sorted(g["malha"].dropna().unique())
        print(f"  {fer}: {len(g)} linhas | malhas: {malhas} | serviços: {sorted(g['servico'].unique())}")
    # sanity: VLI FCA Manobra Açúcar
    row = acess[(acess.ferrovia == "VLI") & (acess.malha == "FCA") &
                (acess.mercadoria == "AÇÚCAR") & (acess.servico == "Manobra")]
    if len(row):
        r0 = row.iloc[0]
        print(f"  check VLI/FCA/Açúcar/Manobra: mín R$ {r0.valor_min} · média R$ {r0.valor_medio} · máx R$ {r0.valor_max}")
    con.close()


if __name__ == "__main__":
    main()
