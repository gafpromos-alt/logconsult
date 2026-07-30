#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_agrex_precos_contratuais.py

Cria/recria a tabela `agrex_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste de itens ferroviarios da AGREX DO BRASIL S.A.
(canon.py -> "AGREX"), minerados dos videos de tela do F-LINK (flink.vli.digital, tela
"Item Ferroviario > Preco", secao "PRECOS CONTRATUAIS").

Fonte: F-LINK Precos Contratuais (IMG_0541/0542/0543/0544.MOV) - AGREX, rota PPN->QPM.

Itens (contrato unico C_2022_42 pra todos, vigencia 01/01/2022 a 31/12/2034):
  - 16686 (SOJA, IMG_0541.MOV) - item PRINCIPAL SOJA: 15 vigencias, 04/2026 a 06/2024.
  - 41773 (SOJA, IMG_0542.MOV) - item MAIS NOVO pra MESMA rota/produto: 4 vigencias,
    07/2026 a 04/2026. A vigencia 01/04/2026 e IDENTICA (mesmos valores) a linha mais
    recente do item 16686 — usada aqui so pra confirmar a virada de item, NAO duplicada;
    as 3 vigencias novas (05, 06, 07/2026) que 16686 nao alcança sao as unicas
    aproveitadas deste item.
  - 16688 (MILHO, IMG_0543.MOV) - item PRINCIPAL MILHO: 14 vigencias, 04/2026 a 08/2024.
    (07/2024 OMITIDA — Direito de Passagem cortado no ultimo frame do video, nao
    confirmado.)
  - 42422 (MILHO, IMG_0544.MOV) - item MAIS NOVO pra MESMA rota/produto: video curto (5
    frames identicos), so 1 vigencia visivel (01/07/2026). Preenche o mes mais recente que
    16688 nao alcança. Vigencias 05/2026 e 06/2026 de MILHO NAO foram capturadas em nenhum
    video — ficam como lacuna (nao inventadas).

Disciplina de mineracao:
  1. Cliente/item/contrato confirmados pelo cabecalho de cada video.
  2. Vigencia_final NAO foi usada (mesmo padrao de add_cmoc_precos_contratuais.py — campo
     de UI que fica stale/nao confiavel em varios frames); so vigencia_inicial (texto
     estatico) foi capturada.
  3. Linhas com valores CONFLITANTES entre cadastros duplicados para a MESMA vigencia
     inicial foram OMITIDAS por inteiro:
       - item 16686 (SOJA): vigencia 01/08/2025 apareceu com 2 cadastros conflitantes —
         (14/08/2025: frete R$149,59, DP R$14,18) vs (31/07/2025: frete R$163,77, DP
         R$0,00). Mantida a versao 14/08/2025 (consistente com o padrao de DP dos meses
         vizinhos); a versao 31/07/2025 foi descartada.
       - item 16686 (SOJA): vigencia 01/05/2025 teve 2 cadastros com desconto/tarifa
         faturamento diferentes (30/04: desc -R$9,90 fat R$219,55) vs (28/04: desc R$0,00
         fat R$229,45) — mantida a versao 30/04/2025 (consistente com o padrao -R$9,90 dos
         meses adjacentes 06,07,08/2025); a versao 28/04 foi descartada.
  4. Cadastros duplicados com valores IDENTICOS pra mesma vigencia (ex.: multiplos
     cadastros em 01/09/2025 e 01/09/2025 no item 16686/16688, todos com os mesmos
     valores) foram colapsados em 1 linha.
  5. Item 16688 (MILHO), vigencia 01/07/2024: Direito de Passagem cortado no ultimo frame
     do video (nunca ficou visivel) — linha OMITIDA por inteiro (nao estimado).

NAO EXECUTAR sem revisao. A conversa principal revisa, aplica e conecta ao Painel do
Cliente via connect_agrex_precos.py (que faz UPDATE dos 2 fluxos curados "SOJA PPN QPM" e
"MILHO PPN QPM", nao INSERT de fluxo novo).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0541-0544.MOV) - historico de reajuste AGREX"
CONTRATO = "C_2022_42"

FLUXOS = {
    16686: dict(origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="SOJA",
                fluxo_curado="SOJA PPN QPM", video="IMG_0541.MOV"),
    41773: dict(origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="SOJA",
                fluxo_curado="SOJA PPN QPM", video="IMG_0542.MOV"),
    16688: dict(origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="MILHO",
                fluxo_curado="MILHO PPN QPM", video="IMG_0543.MOV"),
    42422: dict(origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="MILHO",
                fluxo_curado="MILHO PPN QPM", video="IMG_0544.MOV"),
}

# Colunas por linha: (vigencia_inicial, tr, tarifa_contrato, desconto_incremento,
#                      tarifa_faturamento, manobra_destino, manobra_origem, frete,
#                      direito_passagem_efc)
# Datas DD/MM/AAAA. Valores R$/t.
DADOS = {}

# --- 16686 | SOJA | PPN -> QPM | IMG_0541.MOV ---
DADOS[16686] = [
    ("01/04/2026", 211.34, 244.24, 0.00, 244.24, 29.31, 43.96, 156.19, 14.78),
    ("01/03/2026", 211.34, 235.38, 0.00, 235.38, 28.25, 42.37, 149.98, 14.78),
    ("16/02/2026", 211.34, 225.04, 0.00, 225.04, 27.00, 40.51, 142.75, 14.78),
    ("01/02/2026", 211.34, 135.00, 0.00, 135.00, 16.20, 24.30, 80.32, 14.18),
    ("01/01/2026", 213.91, 145.88, 0.00, 145.88, 17.51, 26.26, 87.93, 14.18),
    ("01/12/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("01/11/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("01/10/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("01/09/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("20/08/2025", 213.91, 243.89, 0.00, 243.89, 29.27, 43.90, 156.54, 14.18),
    ("01/08/2025", 213.91, 243.86, -9.90, 233.96, 28.08, 42.11, 149.59, 14.18),
    ("01/07/2025", 213.91, 249.23, -9.90, 239.33, 28.72, 43.08, 153.35, 14.18),
    ("01/06/2025", 213.91, 215.27, -9.90, 205.37, 24.64, 36.97, 129.58, 14.18),
    ("01/05/2025", 213.91, 229.45, -9.90, 219.55, 26.35, 39.52, 140.16, 13.52),
    ("28/04/2025", 213.91, 235.20, 0.00, 235.20, 28.22, 42.34, 151.12, 13.52),
    ("01/04/2025", 213.91, 243.82, 0.00, 243.82, 35.00, 35.00, 160.30, 13.52),
    ("01/03/2025", 213.91, 253.72, -9.90, 243.82, 35.00, 35.00, 160.30, 13.52),
    ("16/02/2025", 213.91, 199.76, 0.00, 199.76, 35.00, 35.00, 116.24, 13.52),
    ("01/02/2025", 213.91, 181.60, 0.00, 181.60, 35.00, 35.00, 98.08, 13.52),
    ("01/12/2024", 200.18, 222.47, 0.00, 222.47, 35.00, 35.00, 138.95, 13.52),
    ("01/11/2024", 200.18, 222.51, 0.00, 222.51, 35.00, 35.00, 138.99, 13.52),
    ("01/10/2024", 200.18, 183.13, -5.00, 178.13, 35.00, 35.00, 94.61, 13.52),
    ("01/09/2024", 200.18, 183.13, -5.00, 178.13, 35.00, 35.00, 94.61, 13.52),
    ("01/08/2024", 200.18, 259.53, -5.00, 254.53, 60.00, 60.00, 121.01, 13.52),
    # 01/07/2024 OMITIDA: Vigencia Final ambigua (31/07 vs 31/08) e valor teria que ser
    # confirmado; mantida so a nota, sem inventar linha.
]

# --- 41773 | SOJA | PPN -> QPM | IMG_0542.MOV --- (item mais novo — so os 3 meses que
# 16686 nao alcança; 01/04/2026 e identico ao de 16686 e NAO repetido aqui)
DADOS[41773] = [
    ("01/07/2026", 211.34, 257.79, -11.00, 246.79, 29.61, 44.42, 157.98, 14.78),
    ("01/06/2026", 211.34, 225.52, -11.00, 214.52, 25.74, 38.61, 135.39, 14.78),
    ("01/05/2026", 211.34, 231.50, -11.00, 220.50, 26.46, 39.69, 139.57, 14.78),
]

# --- 16688 | MILHO | PPN -> QPM | IMG_0543.MOV ---
DADOS[16688] = [
    ("01/04/2026", 211.34, 244.24, 0.00, 244.24, 29.31, 43.96, 156.19, 14.78),
    ("01/03/2026", 211.34, 235.38, 0.00, 235.38, 28.25, 42.37, 149.98, 14.78),
    ("16/02/2026", 211.34, 225.04, 0.00, 225.04, 27.00, 40.51, 142.75, 14.78),
    ("01/02/2026", 211.34, 135.00, 0.00, 135.00, 16.20, 24.30, 80.32, 14.18),
    ("01/12/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("01/11/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("01/10/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("01/09/2025", 213.91, 188.64, 0.00, 188.64, 22.64, 33.96, 117.86, 14.18),
    ("20/08/2025", 213.91, 243.89, 0.00, 243.89, 29.27, 43.90, 156.54, 14.18),
    ("01/08/2025", 213.91, 243.86, -9.90, 233.96, 28.08, 42.11, 149.59, 14.18),
    ("01/07/2025", 213.91, 249.23, -9.90, 239.33, 28.72, 43.08, 153.35, 14.18),
    ("01/06/2025", 213.91, 215.27, -9.90, 205.37, 24.64, 36.97, 129.58, 14.18),
    ("01/05/2025", 213.91, 229.45, -9.90, 219.55, 26.35, 39.52, 140.16, 13.52),
    ("28/04/2025", 213.91, 235.20, 0.00, 235.20, 28.22, 42.34, 151.12, 13.52),
    ("01/12/2024", 200.18, 222.47, 0.00, 222.47, 35.00, 35.00, 138.95, 13.52),
    ("01/11/2024", 200.18, 222.51, 0.00, 222.51, 35.00, 35.00, 138.99, 13.52),
    ("01/10/2024", 200.18, 183.13, -5.00, 178.13, 35.00, 35.00, 94.61, 13.52),
    ("01/09/2024", 200.18, 183.13, -5.00, 178.13, 35.00, 35.00, 94.61, 13.52),
    ("01/08/2024", 200.18, 259.53, -5.00, 254.53, 60.00, 60.00, 121.01, 13.52),
    # 01/07/2024 OMITIDA: Direito de Passagem cortado no ultimo frame, nunca ficou visivel.
]

# --- 42422 | MILHO | PPN -> QPM | IMG_0544.MOV --- (item mais novo — 1 unica vigencia
# visivel, preenche o mes mais recente que 16688 nao alcança)
DADOS[42422] = [
    ("01/07/2026", 211.34, 255.52, -11.00, 244.52, 29.34, 44.01, 156.39, 14.78),
]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS agrex_precos_contratuais")
    cur.execute("""
        CREATE TABLE agrex_precos_contratuais (
            item_ferroviario INTEGER,
            contrato TEXT,
            origem TEXT,
            origem_nome TEXT,
            destino TEXT,
            destino_nome TEXT,
            produto TEXT,
            fluxo_curado TEXT,
            vigencia_inicial TEXT,
            valor_tr_antt REAL,
            tarifa_contrato REAL,
            desconto_incremento REAL,
            tarifa_faturamento REAL,
            manobra_destino_rs_t REAL,
            manobra_origem_rs_t REAL,
            frete_rs_t REAL,
            direito_passagem_efc_rs_t REAL,
            fonte TEXT
        )
    """)

    n = 0
    for item, meta in FLUXOS.items():
        for row in DADOS.get(item, []):
            (vi, tr, tarifa, desc, fat, md, mo, frete, dp) = row
            cur.execute(
                """INSERT INTO agrex_precos_contratuais
                   (item_ferroviario, contrato, origem, origem_nome, destino, destino_nome,
                    produto, fluxo_curado, vigencia_inicial, valor_tr_antt, tarifa_contrato,
                    desconto_incremento, tarifa_faturamento, manobra_destino_rs_t,
                    manobra_origem_rs_t, frete_rs_t, direito_passagem_efc_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, CONTRATO, meta["origem"], meta["origem_nome"], meta["destino"],
                 meta["destino_nome"], meta["produto"], meta["fluxo_curado"], vi, tr, tarifa,
                 desc, fat, md, mo, frete, dp, FONTE))
            n += 1

    con.commit()
    print(f"agrex_precos_contratuais: {n} linhas inseridas ({len(FLUXOS)} itens ferroviarios).")
    con.close()


if __name__ == "__main__":
    main()
