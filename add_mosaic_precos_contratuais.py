#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_mosaic_precos_contratuais.py

Cria/recria a tabela `mosaic_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste de 2 itens ferroviarios da VALE FERTILIZANTES SA
(canon.py -> "MOSAIC"), minerados dos videos de tela do F-LINK (flink.vli.digital, tela
"Item Ferroviario > Preco", secao "PRECOS CONTRATUAIS").

Uma linha por (item ferroviario x vigencia inicial).

Fonte: F-LINK Precos Contratuais (IMG_0532.MOV e IMG_0533.MOV) - MOSAIC (Vale Fertilizantes).
Estes 2 itens preenchem uma lacuna conhecida: MOSAIC so tinha abertura de manobra para
FERTILIZANTES/GESSO/MINERIO FERRO; ENXOFRE e o "fosfato" (ROCHA FOS UMIDA) nao tinham
nenhuma tarifa aberta na base (so volume).

Disciplina de mineracao:
  1. Cliente/item/contrato confirmados pelo cabecalho de cada video (Numero do Item
     Ferroviario, Contrato/Acordo, Estacao Origem/Destino, Produto).
  2. So foram gravadas linhas onde TODOS os campos (TR, tarifa contrato, tarifa
     faturamento, servicos) estavam legiveis e SEM ambiguidade entre frames (varios
     trechos dos videos tem motion-blur/double-exposure durante o scroll da tabela;
     linhas ambiguas foram OMITIDAS, nunca adivinhadas).
  3. "Vigencia Final" e um campo de UI (date-input) que fica com valor "congelado"/stale
     em varios frames por bug de renderizacao do F-LINK — NAO foi usado; so
     vigencia_inicial (texto estatico, confiavel) foi capturada.
  4. DESCARGA e um servico real e distinto de FRETE/MANOBRA nestes 2 itens (sempre
     ferrovia FCA) — coluna propria `descarga_rs_t`.
  5. DIREITO DE PASSAGEM aparece em 2 ferrovias (MRS e ALLMP) so no item 39890 (ENXOFRE);
     o item 39889 (ROCHA FOS UMIDA) nao tem nenhuma linha de Direito de Passagem nos
     frames capturados.

NAO EXECUTAR sem revisao. A conversa principal revisa, aplica e conecta ao Painel do
Cliente via connect_mosaic_precos.py.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0532-0533.MOV) - historico de reajuste MOSAIC (Vale Fertilizantes)"

# ---------------------------------------------------------------------------
# Metadados de cada item (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    39890: dict(contrato="C_010_2020.1", origem="IUF", origem_nome="TUF",
                destino="ZVF", destino_nome="VALEFERTIL",
                produto="ENXOFRE", video="IMG_0532.MOV"),
    39889: dict(contrato="C_010_2020.1", origem="ELC", origem_nome="CATALAO",
                destino="ZVF", destino_nome="VALEFERTIL",
                produto="ROCHA FOS UMIDA", video="IMG_0533.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item: (vigencia_inicial, tr, tarifa_contrato, tarifa_faturamento,
#                   descarga, frete, manobra_origem, manobra_destino, dp_mrs, dp_allmp)
# dp_mrs/dp_allmp = None quando o servico nao aparece no item.
# Datas em DD/MM/AAAA. Valores em R$/t.
# ---------------------------------------------------------------------------
DADOS = {}

# --- 39890 | ENXOFRE | IUF-TUF -> ZVF-VALEFERTIL | IMG_0532.MOV ---
DADOS[39890] = [
    ("01/07/2026", 145.23, 142.41, 142.41, 14.50, 107.75, 4.15, 4.15, 2.67, 9.19),
    ("01/06/2026", 145.23, 142.34, 142.34, 14.50, 107.68, 4.15, 4.15, 2.67, 9.19),
    ("01/05/2026", 145.23, 140.95, 140.95, 14.50, 106.29, 4.15, 4.15, 2.67, 9.19),
    ("01/04/2026", 145.23, 140.78, 140.78, 14.50, 106.12, 4.15, 4.15, 2.67, 9.19),
    ("01/03/2026", 145.23, 141.15, 141.15, 14.50, 106.49, 4.15, 4.15, 2.67, 9.19),
    ("01/02/2026", 145.23, 126.71, 126.71, 14.50, 91.95, 4.15, 4.15, 2.67, 9.29),
    ("01/12/2025", 145.23, 126.61, 141.11, 14.50, 106.35, 4.15, 4.15, 2.67, 9.29),
    ("01/11/2025", 145.23, 126.52, 141.02, 14.50, 106.28, 4.15, 4.15, 2.67, 9.29),
    ("01/11/2025", 145.23, 126.44, 140.94, 14.50, 106.18, 4.15, 4.15, 2.67, 9.29),
    ("01/09/2025", 141.00, 126.51, 141.01, 14.50, 106.25, 4.15, 4.15, 2.67, 9.29),
    ("01/08/2025", 141.00, 126.01, 140.51, 14.50, 107.25, 4.15, 4.15, 2.67, 9.29),
    ("01/06/2025", 141.00, 126.04, 140.54, 13.00, 107.42, 4.15, 4.15, 2.53, 9.29),
    ("01/07/2025", 141.00, 125.92, 140.42, 13.00, 107.30, 4.15, 4.15, 2.53, 9.29),
    ("01/06/2025", 141.00, 122.26, 135.26, 13.00, 102.14, 4.15, 4.15, 2.53, 9.29),
    ("01/05/2025", 141.00, 123.33, 136.33, 13.00, 103.24, 4.15, 4.15, 2.53, 9.26),
    ("30/04/2025", 141.00, 125.17, 125.17, 13.00, 92.08, 4.15, 4.15, 2.53, 9.26),
]

# --- 39889 | ROCHA FOS UMIDA | ELC-CATALAO -> ZVF-VALEFERTIL | IMG_0533.MOV ---
# (sem Direito de Passagem neste item nos frames capturados)
DADOS[39889] = [
    ("01/07/2026", 76.10, 85.39, 85.39, 14.50, 62.59, 4.15, 4.15, None, None),
    ("01/05/2026", 76.10, 84.58, 84.58, 14.50, 61.78, 4.15, 4.15, None, None),
    ("01/02/2026", 76.10, 70.22, 70.22, 14.50, 47.42, 4.15, 4.15, None, None),
    ("01/01/2026", 76.10, 70.17, 84.67, 14.50, 61.87, 4.15, 4.15, None, None),
    ("01/12/2025", 76.10, 70.17, 84.67, 14.50, 61.87, 4.15, 4.15, None, None),
    ("01/11/2025", 76.10, 70.12, 84.62, 14.50, 61.82, 4.15, 4.15, None, None),
    ("01/11/2025", 76.10, 70.08, 84.58, 14.50, 61.78, 4.15, 4.15, None, None),
    ("01/10/2025", 73.89, 70.16, 84.66, 14.50, 61.86, 4.15, 4.15, None, None),
    ("01/09/2025", 73.89, 70.12, 84.62, 14.50, 61.82, 4.15, 4.15, None, None),
    ("01/08/2025", 73.89, 69.84, 84.34, 14.50, 63.04, 4.15, 4.15, None, None),
    ("01/06/2025", 73.89, 69.86, 84.36, 14.50, 63.06, 4.15, 4.15, None, None),
    ("01/06/2025", 73.89, 68.91, 83.41, 14.50, 62.11, 4.15, 4.15, None, None),
    ("01/06/2025", 73.89, 68.41, 81.41, 13.00, 60.11, 4.15, 4.15, None, None),
    ("01/05/2025", 73.89, 69.01, 82.01, 13.00, 60.71, 4.15, 4.15, None, None),
    ("30/04/2025", 73.89, 70.04, 70.04, 13.00, 48.74, 4.15, 4.15, None, None),
]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS mosaic_precos_contratuais")
    cur.execute("""
        CREATE TABLE mosaic_precos_contratuais (
            item_ferroviario INTEGER,
            contrato TEXT,
            origem TEXT,
            origem_nome TEXT,
            destino TEXT,
            destino_nome TEXT,
            produto TEXT,
            vigencia_inicial TEXT,
            valor_tr_antt REAL,
            tarifa_contrato REAL,
            tarifa_faturamento REAL,
            descarga_rs_t REAL,
            frete_rs_t REAL,
            manobra_origem_rs_t REAL,
            manobra_destino_rs_t REAL,
            direito_passagem_mrs_rs_t REAL,
            direito_passagem_allmp_rs_t REAL,
            fonte TEXT
        )
    """)

    n = 0
    for item, meta in FLUXOS.items():
        for row in DADOS.get(item, []):
            (vi, tr, tarifa, tarifa_fat, descarga, frete, mo, md, dp_mrs, dp_allmp) = row
            cur.execute(
                """INSERT INTO mosaic_precos_contratuais
                   (item_ferroviario, contrato, origem, origem_nome, destino, destino_nome,
                    produto, vigencia_inicial, valor_tr_antt, tarifa_contrato,
                    tarifa_faturamento, descarga_rs_t, frete_rs_t, manobra_origem_rs_t,
                    manobra_destino_rs_t, direito_passagem_mrs_rs_t,
                    direito_passagem_allmp_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"], vi, tr, tarifa,
                 tarifa_fat, descarga, frete, mo, md, dp_mrs, dp_allmp, FONTE))
            n += 1

    con.commit()
    print(f"mosaic_precos_contratuais: {n} linhas inseridas ({len(FLUXOS)} itens ferroviarios).")
    con.close()


if __name__ == "__main__":
    main()
