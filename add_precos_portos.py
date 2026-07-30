# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Preços de portos (VLI × mercado) no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Duas fontes:
  1) VLI interna: "Volumes e Tarifas 26_25_24.xlsx" (07_Dados VLI) — linhas Modal='Porto'
     (elevação portuária faturada pela VLI), agregadas por porto × ano × mês.
     preço R$/t = REC-TOTAL / VOL-TU. Só 3 clusters de porto (por UF Origem): ES→Vitória,
     SP→Santos, MA→São Luís/Itaqui — a base não tem terminal/produto discriminado
     ("Terminais - 1/2" vêm 100% "Não Classificado" nas linhas de Porto).
  2) Mercado externo: tabela pública "Elevações Portuárias S.A." (RUMO, Porto de Santos) —
     preço fixo por mercadoria (Açúcar/Grãos), sem granularidade mensal. Referência estática,
     último reajuste abr/2021 (reajuste anual por IGP-M, não capturado aqui) — comparação
     direcional, não atualizada mês a mês como a série da VLI.

Uso:  python3 add_precos_portos.py
"""
import sqlite3, pathlib
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent
VLI = BASE.parent / "07_Dados VLI"
DB = BASE / "logconsult.db"

UF_PORTO = {"ES": "Vitória", "SP": "Santos", "MA": "São Luís/Itaqui"}

# fonte externa estática — RUMO "Elevações Portuárias S.A." (Porto de Santos), baixado de
# rumolog.com/wp-content/uploads/2021/11/RUMO_TABELA-DE-PRECOS-DOS-SERVICOS_ELEVACOES-PORTUARIAS.pdf
RUMO_ELEVACAO = [
    ("Santos", "AÇÚCAR", 50.00, "2021-04", "RUMO — Elevações Portuárias S.A. (imposto incluso; reajuste anual IGP-M, não atualizado desde abr/2021)"),
    ("Santos", "GRÃOS (SOJA E MILHO)", 41.88, "2021-04", "RUMO — Elevações Portuárias S.A. (imposto incluso; reajuste anual IGP-M, não atualizado desde abr/2021)"),
]


def main():
    df = pd.read_excel(VLI / "Volumes e Tarifas 26_25_24.xlsx", sheet_name="Planilha1")
    porto = df[df["Modal"] == "Porto"].copy()
    porto["porto"] = porto["Origem"].map(UF_PORTO).fillna(porto["Origem"])
    porto["panorama_tipo"] = porto["Panorama"].str.contains("Real", case=False).map({True: "realizado", False: "orcamento"})

    vli_serie = (porto.groupby(["porto", "Ano", "Mês", "panorama_tipo"], as_index=False)
                 .agg(rec=("REC-TOTAL", "sum"), vol=("VOL-TU", "sum")))
    vli_serie = vli_serie[vli_serie["vol"] > 0]
    vli_serie["preco_rs_t"] = (vli_serie["rec"] / vli_serie["vol"]).round(2)
    vli_serie = vli_serie.rename(columns={"Ano": "ano", "Mês": "mes"})
    vli_serie = vli_serie[["porto", "ano", "mes", "panorama_tipo", "vol", "preco_rs_t"]].sort_values(["porto", "ano", "mes"])
    vli_serie["vol"] = vli_serie["vol"].round(1)

    rumo = pd.DataFrame(RUMO_ELEVACAO, columns=["porto", "mercadoria", "preco_rs_t", "data_ref", "fonte"])

    con = sqlite3.connect(DB)
    vli_serie.to_sql("precos_portos_vli", con, if_exists="replace", index=False)
    rumo.to_sql("precos_portos_mercado", con, if_exists="replace", index=False)
    con.commit()

    print(f"precos_portos_vli: {len(vli_serie)} linhas")
    for porto_nome, g in vli_serie.groupby("porto"):
        print(f"  {porto_nome}: {len(g)} meses ({g.ano.min()}-{g.ano.max()}), "
              f"média realizado R$ {g[g.panorama_tipo=='realizado']['preco_rs_t'].mean():.2f}/t")
    print(f"precos_portos_mercado: {len(rumo)} linhas (referência externa RUMO)")
    con.close()


if __name__ == "__main__":
    main()
