#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_cmoc_precos_contratuais.py

Cria/recria a tabela `cmoc_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste de 3 itens ferroviarios da CMOC BRASIL MINERACAO
INDUSTRIA E PARTICIPACOES LTDA (canon.py -> "CMOC"), minerados dos videos de tela do F-LINK
(flink.vli.digital, tela "Item Ferroviario > Preco", secao "PRECOS CONTRATUAIS").

Uma linha por (item ferroviario x vigencia inicial).

Fonte: F-LINK Precos Contratuais (IMG_0534/0535/0536.MOV) - CMOC.

Estes 3 itens ja existiam como fluxos CURADOS (planilha antiga "LogConsult (tarifas por
cliente).xlsx") em projeto_fluxo_tarifas: "ROCHA EYC IFA", "ENXOFRE IUF EYC",
"ENXOFRE ICZ EYC". Os dados aqui minerados ENRIQUECEM/RECONCILIAM esses 3 fluxos com a
situacao tarifaria real reajuste-a-reajuste (2022-2026), nao criam fluxos novos:
  - item 12020 (ROCHA FOSF SECA, EYC-POSTO FOSFAGO -> IFA-FABRICA)  == "ROCHA EYC IFA"
  - item 12019 (ENXOFRE, IUF-TUF -> EYC-POSTO FOSFAGO)              == "ENXOFRE IUF EYC"
  - item 12018 (ENXOFRE, ICZ-CONCEICAOZINHA -> EYC-POSTO FOSFAGO)   == "ENXOFRE ICZ EYC"

Disciplina de mineracao:
  1. Cliente/item/contrato confirmados pelo cabecalho de cada video (Numero do Item
     Ferroviario, Contrato/Acordo, Estacao Origem/Destino, Produto). Contrato unico
     C_2025_60 (vigencia 29/07/2019 a 31/05/2027) para os 3 itens.
  2. So foram gravadas linhas onde TODOS os campos necessarios estavam legiveis e SEM
     ambiguidade entre frames — a tabela tem varios trechos com motion-blur/
     double-exposure durante o scroll (sobretudo fev-dez/2025 e 2024 no item 12020, e
     marco/2025 e 2022 no item 12019); linhas ambiguas foram OMITIDAS, nunca adivinhadas.
  3. "Vigencia Final" e um campo de UI (date-input) que fica "congelado"/stale em varios
     frames — NAO foi usado; so vigencia_inicial (texto estatico, confiavel) foi
     capturada.
  4. Item 12019 (ENXOFRE IUF EYC) tem um servico adicional LIMPEZA DE VAGAO, sempre
     R$0,00 em todas as linhas observadas.
  5. Direito de Passagem aparece em 2 ferrovias (MRS e ALLMP) nos 3 itens.

NAO EXECUTAR sem revisao. A conversa principal revisa, aplica e conecta ao Painel do
Cliente via connect_cmoc_precos.py (que faz UPDATE dos 3 fluxos curados, nao INSERT).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0534-0536.MOV) - historico de reajuste CMOC"
CONTRATO = "C_2025_60"

# ---------------------------------------------------------------------------
# Metadados de cada item (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    12020: dict(origem="EYC", origem_nome="POSTO FOSFAGO", destino="IFA", destino_nome="FABRICA",
                produto="ROCHA FOSF SECA", fluxo_curado="ROCHA EYC IFA",
                tem_limpeza=False, video="IMG_0534.MOV"),
    12019: dict(origem="IUF", origem_nome="TUF", destino="EYC", destino_nome="POSTO FOSFAGO",
                produto="ENXOFRE", fluxo_curado="ENXOFRE IUF EYC",
                tem_limpeza=True, video="IMG_0535.MOV"),
    12018: dict(origem="ICZ", origem_nome="CONCEICAOZINHA", destino="EYC", destino_nome="POSTO FOSFAGO",
                produto="ENXOFRE", fluxo_curado="ENXOFRE ICZ EYC",
                tem_limpeza=False, video="IMG_0536.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item: (vigencia_inicial, tr, tarifa_contrato, manobra_destino, manobra_origem,
#                   frete, dp_allmp, dp_mrs, limpeza_vagao)
# limpeza_vagao = None quando o item nao tem esse servico.
# Datas em DD/MM/AAAA. Valores em R$/t.
# ---------------------------------------------------------------------------
DADOS = {}

# --- 12020 | ROCHA FOSF SECA | EYC-POSTO FOSFAGO -> IFA-FABRICA | IMG_0534.MOV ---
DADOS[12020] = [
    ("01/07/2026", 157.91, 198.41, 29.77, 17.45, 139.33, 9.19, 2.67, None),
    ("01/06/2026", 157.91, 204.37, 29.77, 17.45, 145.29, 9.19, 2.67, None),
    ("11/05/2026", 157.91, 199.70, 29.77, 17.45, 140.62, 9.19, 2.67, None),
    ("11/04/2026", 157.91, 199.70, 30.82, 18.07, 138.95, 9.19, 2.67, None),
    ("11/07/2025", 153.31, 192.90, 29.77, 17.45, 133.86, 9.29, 2.53, None),
    ("01/06/2025", 153.31, 192.90, 29.77, 17.45, 133.86, 9.29, 2.53, None),
    ("10/05/2025", 153.31, 188.35, 29.07, 17.04, 130.45, 9.26, 2.53, None),
    ("10/04/2025", 153.31, 192.90, 29.77, 17.45, 133.89, 9.26, 2.53, None),
    ("01/04/2025", 153.31, 192.90, 29.77, 17.45, 133.89, 9.26, 2.53, None),
    ("11/09/2023", 147.09, 185.38, 20.58, 20.58, 133.00, 8.91, 2.31, None),
    ("11/08/2023", 158.01, 174.53, 9.15, 9.15, 145.01, 8.91, 2.31, None),
    ("11/07/2023", 158.01, 174.53, 9.15, 9.15, 145.01, 8.91, 2.31, None),
    ("11/09/2022", 145.40, 201.89, 28.23, 28.24, 133.91, 7.25, 4.26, None),
    ("11/07/2022", 145.40, 208.03, 31.30, 31.31, 133.91, 7.25, 4.26, None),
    ("11/06/2022", 145.40, 198.28, 26.43, 26.43, 133.91, 7.25, 4.26, None),
    ("01/05/2022", 145.40, 192.63, 23.61, 23.60, 133.91, 7.25, 4.26, None),
]

# --- 12019 | ENXOFRE | IUF-TUF -> EYC-POSTO FOSFAGO | IMG_0535.MOV --- (tem LIMPEZA DE VAGAO)
DADOS[12019] = [
    ("11/02/2026", 189.49, 176.70, 17.45, 4.15, 143.14, 9.29, 2.67, 0.00),
    ("11/01/2026", 189.49, 176.70, 17.45, 4.15, 143.14, 9.29, 2.67, 0.00),
    ("11/11/2025", 189.49, 176.70, 17.45, 4.15, 143.14, 9.29, 2.67, 0.00),
    ("11/07/2025", 183.97, 176.70, 17.45, 4.15, 143.28, 9.29, 2.53, 0.00),
    ("11/02/2025", 183.97, 159.21, 17.45, 4.15, 125.82, 9.26, 2.53, 0.00),
    ("11/01/2025", 183.97, 159.21, 17.45, 4.15, 125.82, 9.26, 2.53, 0.00),
    ("11/12/2024", 183.97, 159.21, 17.45, 4.15, 126.36, 8.72, 2.53, 0.00),
    ("11/11/2024", 183.97, 159.21, 17.45, 4.15, 126.36, 8.72, 2.53, 0.00),
    ("01/04/2024", 176.51, 159.21, 7.45, 7.45, 133.15, 8.72, 2.44, 0.00),
    ("11/05/2024", 176.51, 159.21, 7.45, 7.45, 133.15, 8.72, 2.44, 0.00),
    ("11/08/2023", 189.61, 153.78, 7.45, 7.45, 127.66, 8.91, 2.31, 0.00),
    ("11/07/2023", 189.61, 153.78, 7.45, 7.45, 127.66, 8.91, 2.31, 0.00),
    ("11/06/2023", 189.61, 153.78, 7.45, 7.45, 128.05, 8.52, 2.31, 0.00),
]

# --- 12018 | ENXOFRE | ICZ-CONCEICAOZINHA -> EYC-POSTO FOSFAGO | IMG_0536.MOV ---
DADOS[12018] = [
    ("11/10/2025", 185.53, 190.65, 17.45, 9.92, 151.32, 9.29, 2.67, None),
    ("11/09/2025", 185.53, 190.65, 17.45, 9.92, 151.32, 9.29, 2.67, None),
    ("11/07/2025", 185.53, 190.65, 17.45, 9.92, 151.46, 9.29, 2.53, None),
    ("01/06/2025", 185.53, 190.65, 17.45, 9.92, 151.46, 9.29, 2.53, None),
    ("11/02/2025", 185.53, 173.50, 17.45, 9.92, 134.34, 9.26, 2.53, None),
    ("11/01/2025", 185.53, 173.50, 17.45, 9.92, 134.34, 9.26, 2.53, None),
    ("11/12/2024", 185.53, 173.50, 17.45, 9.92, 134.88, 8.72, 2.53, None),
    ("11/11/2024", 185.53, 173.50, 17.45, 9.92, 134.88, 8.72, 2.53, None),
    ("11/08/2023", 191.21, 167.57, 7.45, 7.45, 141.45, 8.91, 2.31, None),
    ("11/07/2023", 191.21, 167.57, 7.45, 7.45, 141.45, 8.91, 2.31, None),
    ("11/06/2023", 191.21, 167.57, 7.45, 7.45, 141.84, 8.52, 2.31, None),
    ("11/05/2023", 191.21, 178.57, 7.45, 7.45, 152.84, 8.52, 2.31, None),
    ("11/08/2022", 175.96, 193.85, 18.02, 18.01, 146.31, 7.25, 4.26, None),
    ("11/07/2022", 175.96, 199.75, 20.97, 20.96, 146.31, 7.25, 4.26, None),
    ("11/06/2022", 175.96, 190.38, 16.28, 16.28, 146.31, 7.25, 4.26, None),
    ("01/05/2022", 175.96, 184.00, 16.28, 16.28, 140.89, 7.25, 4.26, None),
]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS cmoc_precos_contratuais")
    cur.execute("""
        CREATE TABLE cmoc_precos_contratuais (
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
            manobra_destino_rs_t REAL,
            manobra_origem_rs_t REAL,
            frete_rs_t REAL,
            direito_passagem_allmp_rs_t REAL,
            direito_passagem_mrs_rs_t REAL,
            limpeza_vagao_rs_t REAL,
            fonte TEXT
        )
    """)

    n = 0
    for item, meta in FLUXOS.items():
        for row in DADOS.get(item, []):
            (vi, tr, tarifa, md, mo, frete, dp_allmp, dp_mrs, limpeza) = row
            cur.execute(
                """INSERT INTO cmoc_precos_contratuais
                   (item_ferroviario, contrato, origem, origem_nome, destino, destino_nome,
                    produto, fluxo_curado, vigencia_inicial, valor_tr_antt, tarifa_contrato,
                    manobra_destino_rs_t, manobra_origem_rs_t, frete_rs_t,
                    direito_passagem_allmp_rs_t, direito_passagem_mrs_rs_t,
                    limpeza_vagao_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, CONTRATO, meta["origem"], meta["origem_nome"], meta["destino"],
                 meta["destino_nome"], meta["produto"], meta["fluxo_curado"], vi, tr, tarifa,
                 md, mo, frete, dp_allmp, dp_mrs, limpeza, FONTE))
            n += 1

    con.commit()
    print(f"cmoc_precos_contratuais: {n} linhas inseridas ({len(FLUXOS)} itens ferroviarios).")
    con.close()


if __name__ == "__main__":
    main()
