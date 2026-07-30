#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_alz_precos_contratuais.py

Cria/recria a tabela `alz_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste de 2 itens ferroviarios da AMAGGI LOUIS DREYFUS
ZEN-NOH GRAOS S.A. (canon.py -> "ALZ"), minerados dos videos de tela do F-LINK
(flink.vli.digital, tela "Item Ferroviario > Preco", secao "PRECOS CONTRATUAIS").

Fonte: F-LINK Precos Contratuais (IMG_0538/0539/0540.MOV) - ALZ, rota PIN->QPM.

Itens:
  - 41821 (SOJA, contrato C_2022_31_B, IMG_0538.MOV) - video CURTO (10 frames), so 4
    vigencias visiveis, SEM a coluna TRANSBORDO ORIGEM aberta separadamente (o "Frete"
    aparece jah somado ao transbordo). Os MESMOS 4 periodos (04-07/2026) reaparecem no
    item 18287 (abaixo) COM a abertura de transbordo separada e valores que batem
    exatamente (ex.: frete 173,76 = transbordo 15,00 + frete 158,76). Por isso este item
    NAO foi usado como fonte principal — os dados de 18287 sao estritamente mais
    detalhados e cobrem os mesmos periodos. Item 41821 fica documentado aqui só como nota,
    sem linhas duplicadas na tabela.
  - 18287 (SOJA, contrato C_2022_11_6, IMG_0539.MOV) - item PRINCIPAL usado p/ SOJA:
    17 vigencias, 07/2026 a 06/2024, com abertura TRANSBORDO ORIGEM + FRETE + MANOBRA
    ORIGEM/DESTINO + DIREITO DE PASSAGEM (ferrovia EFC).
  - 18353 (MILHO, contrato C_2022_31_6, IMG_0540.MOV) - item MILHO: 13 vigencias, 07/2026
    a 05/2024.

Disciplina de mineracao:
  1. Cliente/item/contrato confirmados pelo cabecalho de cada video.
  2. Vigencia_final NAO foi usada (mesmo padrao de add_cmoc_precos_contratuais.py — campo
     de UI que fica stale/nao confiavel em varios frames); so vigencia_inicial (texto
     estatico) foi capturada.
  3. Linhas com valores CONFLITANTES entre cadastros duplicados para a MESMA vigencia
     inicial foram OMITIDAS por inteiro (nunca adivinhado qual e a versao "vigente"):
       - item 18287: vigencia 01/07/2024 apareceu com frete R$121,23/R$121,23/R$118,30
         em 3 cadastros distintos (12/07, 30/06, 04/07/2024) — CONFLITO, linha omitida.
       - item 18353 (MILHO): mesmo conflito na vigencia 01/07/2024 — linha omitida.
  4. Cadastros duplicados com valores IDENTICOS para a mesma vigencia (ex.: 3 cadastros
     para 01/12/2024 no item 18287, todos com tarifa R$189,56) foram colapsados em 1 linha.
  5. Vigencia "31/08/2024" (item 18287) e "31/08/2024" (item 18353) com Vigencia Final
     30/09/2024: a Vigencia Inicial fora do padrao mensal (esperado seria 01/09/2024) foi
     confirmada em AMBOS os itens com os MESMOS valores — tratada como anomalia real do
     F-LINK (nao erro de leitura), mantida como lida.

NAO EXECUTAR sem revisao. A conversa principal revisa, aplica e conecta ao Painel do
Cliente via connect_alz_precos.py (que faz UPDATE dos 2 fluxos curados "SOJA PIN QPM" e
"MILHO PIN QPM", nao INSERT de fluxo novo).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0538-0540.MOV) - historico de reajuste ALZ"
CONTRATO_SOJA = "C_2022_11_6"
CONTRATO_MILHO = "C_2022_31_6"

FLUXOS = {
    18287: dict(origem="PIN", origem_nome="PATIO INTEGRADOR PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="SOJA",
                contrato=CONTRATO_SOJA, fluxo_curado="SOJA PIN QPM", video="IMG_0539.MOV"),
    18353: dict(origem="PIN", origem_nome="PATIO INTEGRADOR PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="MILHO",
                contrato=CONTRATO_MILHO, fluxo_curado="MILHO PIN QPM", video="IMG_0540.MOV"),
}

# Colunas por linha: (vigencia_inicial, tr, tarifa_contrato, transbordo_origem, frete,
#                      manobra_origem, manobra_destino, direito_passagem_efc)
# Datas DD/MM/AAAA. Valores R$/t.
DADOS = {}

# --- 18287 | SOJA | PIN -> QPM | IMG_0539.MOV ---
DADOS[18287] = [
    ("01/07/2026", 211.82, 235.67, 15.00, 158.76, 18.85, 28.28, 14.78),
    ("01/06/2026", 211.82, 229.16, 15.00, 153.55, 18.33, 27.50, 14.78),
    ("01/05/2026", 211.82, 237.59, 15.00, 160.29, 19.01, 28.51, 14.78),
    ("01/04/2026", 211.82, 245.53, 15.00, 166.65, 19.64, 29.46, 14.78),
    ("16/03/2026", 211.82, 244.93, 15.00, 166.17, 19.59, 29.39, 14.78),
    ("01/03/2026", 211.82, 244.93, 15.00, 166.17, 19.59, 29.39, 14.78),
    ("01/04/2025", 214.39, 250.25, 18.00, 148.73, 35.00, 35.00, 13.52),
    ("01/03/2025", 214.39, 251.32, 18.00, 149.80, 35.00, 35.00, 13.52),
    ("01/12/2024", 200.63, 189.56, 13.54, 92.50, 35.00, 35.00, 13.52),
    ("01/11/2024", 200.63, 188.12, 13.54, 91.06, 35.00, 35.00, 13.52),
    ("01/10/2024", 200.63, 196.41, 13.54, 99.35, 35.00, 35.00, 13.52),
    ("31/08/2024", 200.63, 238.86, 13.54, 141.80, 35.00, 35.00, 13.52),
    ("01/08/2024", 200.63, 268.08, 13.54, 121.02, 60.00, 60.00, 13.52),
    ("01/06/2024", 200.63, 237.85, 13.54, 90.79, 60.00, 60.00, 13.52),
    # 01/07/2024 OMITIDA: frete conflitante entre 3 cadastros (121.23/121.23/118.30).
]

# --- 18353 | MILHO | PIN -> QPM | IMG_0540.MOV ---
DADOS[18353] = [
    ("01/07/2026", 211.82, 227.01, 15.00, 151.83, 18.16, 27.24, 14.78),
    ("01/06/2026", 211.82, 229.16, 15.00, 153.55, 18.33, 27.50, 14.78),
    ("01/05/2026", 211.82, 237.59, 15.00, 160.29, 19.01, 28.51, 14.78),
    ("01/04/2026", 211.82, 245.53, 15.00, 166.65, 19.64, 29.46, 14.78),
    ("16/03/2026", 211.82, 244.93, 15.00, 166.17, 19.59, 29.39, 14.78),
    ("01/03/2026", 211.82, 244.93, 15.00, 166.17, 19.59, 29.39, 14.78),
    ("01/03/2025", 214.39, 251.32, 18.00, 149.80, 35.00, 35.00, 13.52),
    ("01/12/2024", 200.63, 189.56, 13.54, 92.50, 35.00, 35.00, 13.52),
    ("01/11/2024", 200.63, 188.12, 13.54, 91.06, 35.00, 35.00, 13.52),
    ("01/10/2024", 200.63, 196.41, 13.54, 99.35, 35.00, 35.00, 13.52),
    ("31/08/2024", 200.63, 238.86, 13.54, 141.80, 35.00, 35.00, 13.52),
    ("01/08/2024", 200.63, 268.08, 13.54, 121.02, 60.00, 60.00, 13.52),
    ("01/05/2024", 200.63, 238.42, 13.54, 91.36, 60.00, 60.00, 13.52),
    # 01/07/2024 OMITIDA: frete conflitante entre 3 cadastros (121.23/121.23/118.30) —
    # mesmo conflito observado no item 18287 (SOJA), mesma vigencia.
]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS alz_precos_contratuais")
    cur.execute("""
        CREATE TABLE alz_precos_contratuais (
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
            transbordo_origem_rs_t REAL,
            frete_rs_t REAL,
            manobra_origem_rs_t REAL,
            manobra_destino_rs_t REAL,
            direito_passagem_efc_rs_t REAL,
            fonte TEXT
        )
    """)

    n = 0
    for item, meta in FLUXOS.items():
        for row in DADOS.get(item, []):
            (vi, tr, tarifa, transb, frete, mo, md, dp) = row
            cur.execute(
                """INSERT INTO alz_precos_contratuais
                   (item_ferroviario, contrato, origem, origem_nome, destino, destino_nome,
                    produto, fluxo_curado, vigencia_inicial, valor_tr_antt, tarifa_contrato,
                    transbordo_origem_rs_t, frete_rs_t, manobra_origem_rs_t,
                    manobra_destino_rs_t, direito_passagem_efc_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"], meta["destino"],
                 meta["destino_nome"], meta["produto"], meta["fluxo_curado"], vi, tr, tarifa,
                 transb, frete, mo, md, dp, FONTE))
            n += 1

    con.commit()
    print(f"alz_precos_contratuais: {n} linhas inseridas ({len(FLUXOS)} itens ferroviarios).")
    con.close()


if __name__ == "__main__":
    main()
