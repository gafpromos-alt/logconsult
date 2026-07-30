#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_sabba_precos_contratuais.py

Cria/recria a tabela `sabba_precos_contratuais` no banco analitico (logconsult.db)
com o historico de precos contratuais dos fluxos ferroviarios da PETROLEO SABBA S.A.,
minerado dos videos de tela do F-LINK (flink.vli.digital, tela "Precos Contratuais"),
um video por fluxo.

Uma linha por (item ferroviario x vigencia/reajuste/re-cadastro).

NAO EXECUTAR automaticamente sem revisao.

Fonte: F-LINK Precos Contratuais (IMG_0421, IMG_0422, IMG_0424, IMG_0425.MOV).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0421/0422/0424/0425.MOV) - SABBA"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    41350: dict(contrato="C_2022_24", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QAL", destino_nome="PATIO DE ACAILANDIA",
                produto="OLEO DIESEL", video="IMG_0421.MOV"),
    41348: dict(contrato="C_2022_24", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QAL", destino_nome="PATIO DE ACAILANDIA",
                produto="GASOLINA", video="IMG_0422.MOV"),
    41346: dict(contrato="C_2022_24", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QMA", destino_nome="PATIO DE MARABA",
                produto="OLEO DIESEL", video="IMG_0424.MOV"),
    41984: dict(contrato="RETORNO VG TANQUE", origem="QAL", origem_nome="PATIO DE ACAILANDIA",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0425.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada tupla:
#   (data_cadastro, ultima_atualizacao, vig_inicial, vig_final, valor_tr_antt,
#    tarifa_contrato, frete, manobra_origem, manobra_destino, direito_passagem)
# Datas em YYYY-MM-DD. Valores em R$/t. direito_passagem=None quando o servico
# nao existe no fluxo (SABBA nao tem DIREITO DE PASSAGEM em nenhum dos 4 itens).
# ---------------------------------------------------------------------------

DADOS = {}

# --- 41350 | C_2022_24 | QPM->QAL | OLEO DIESEL | IMG_0421.MOV ---
# 6 vigencias, todas com vigencia_final 31/03/2027 (fim do contrato) exceto uma
# janela curta (01/04-09/04/2026). Todas validam (frete+MO+MD=tarifa).
DADOS[41350] = [
    # data_cad      ult_atualiz    vig_ini      vig_fim      TR      tarifa   frete    MO     MD    DP
    ("2026-06-29", "2026-07-09", "2026-07-10", "2027-03-31", 168.85, 146.52, 80.07, 42.61, 23.84, None),
    ("2026-05-28", "2026-05-28", "2026-06-10", "2027-03-31", 168.85, 146.72, 119.56, 13.58, 13.58, None),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2027-03-31", 168.85, 148.24, 121.08, 13.58, 13.58, None),
    ("2026-04-13", "2026-04-13", "2026-04-10", "2027-03-31", 168.85, 147.99, 120.83, 13.58, 13.58, None),
    ("2026-04-13", "2026-04-13", "2026-04-01", "2026-04-09", 168.85, 144.60, 117.44, 13.58, 13.58, None),
    ("2026-03-27", "2026-03-27", "2026-03-10", "2027-03-31", 168.85, 146.51, 119.35, 13.58, 13.58, None),
]

# --- 41348 | C_2022_24 | QPM->QAL | GASOLINA | IMG_0422.MOV ---
# 6 vigencias, mesma estrutura do 41350 (mesmo TR ANTT, mesmo padrao MO=MD
# exceto a 1a linha). Todas validam.
DADOS[41348] = [
    ("2026-06-29", "2026-07-09", "2026-07-10", "2027-03-31", 168.85, 146.52, 80.07, 42.61, 23.84, None),
    ("2026-05-28", "2026-05-28", "2026-06-10", "2027-03-31", 168.85, 146.72, 123.44, 11.64, 11.64, None),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2027-03-31", 168.85, 148.24, 124.96, 11.64, 11.64, None),
    ("2026-04-13", "2026-04-13", "2026-04-10", "2027-03-31", 168.85, 147.99, 124.71, 11.64, 11.64, None),
    ("2026-04-13", "2026-04-13", "2026-04-01", "2026-04-09", 168.85, 144.60, 121.32, 11.64, 11.64, None),
    ("2026-03-27", "2026-03-27", "2026-03-10", "2027-03-31", 168.85, 146.51, 123.23, 11.64, 11.64, None),
]

# --- 41346 | C_2022_24 | QPM->QMA | OLEO DIESEL | IMG_0424.MOV ---
# 4 vigencias (video mais curto, termina em blur apos a 4a linha - nao ha mais
# linhas visiveis na tela antes do corte). TR ANTT proprio da rota (mais longa
# que QPM->QAL): 220,13.
DADOS[41346] = [
    ("2026-06-29", "2026-07-09", "2026-07-10", "2027-03-31", 220.13, 208.96, 146.70, 42.61, 19.65, None),
    ("2026-05-28", "2026-05-28", "2026-06-10", "2027-03-31", 220.13, 209.25, 182.09, 13.58, 13.58, None),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2027-03-31", 220.13, 211.40, 184.24, 13.58, 13.58, None),
    ("2026-04-14", "2026-04-14", "2026-04-10", "2027-03-31", 220.13, 211.05, 183.89, 13.58, 13.58, None),
]

# --- 41984 | RETORNO VG TANQUE | QAL->QPM | OLEO DIESEL | IMG_0425.MOV ---
# Item de RETORNO (vagao tanque vazio, sentido inverso QAL->QPM). Vigencia
# curta e deliberada: 08/05/2026-31/05/2026 (contrato "RETORNO VG TANQUE").
# Confirmado como item de preco valido: registro completo em "PRECOS
# CONTRATUAIS" com FRETE + MANOBRA ORIGEM + MANOBRA DESTINO somando exatamente
# a tarifa contrato (R$148,24). Unica vigencia visivel no video (nao ha
# rolagem para mais linhas).
DADOS[41984] = [
    ("2026-05-08", "2026-05-08", "2026-05-08", "2026-05-31", 168.85, 148.24, 121.08, 13.58, 13.58, None),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + MD + (DP ou 0) == tarifa_contrato (tolerancia 0,05)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            dc, ua, vi, vf, tr, tarifa, frete, mo, md, dp = ln
            soma = (frete or 0) + (mo or 0) + (md or 0) + (dp or 0)
            if abs(soma - tarifa) > 0.05:
                problemas.append(
                    f"item {item} vig {vi}: soma servicos {soma:.2f} "
                    f"!= tarifa_contrato {tarifa:.2f}"
                )
    return problemas


def main():
    problemas = validar(DADOS)
    if problemas:
        print("INCONSISTENCIAS DE SOMA (revisar antes de gravar):")
        for p in problemas:
            print("  -", p)
        raise SystemExit("Abortado: corrija as inconsistencias acima.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS sabba_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE sabba_precos_contratuais (
            item_ferroviario     INTEGER,
            contrato             TEXT,
            origem               TEXT,
            origem_nome          TEXT,
            destino              TEXT,
            destino_nome         TEXT,
            produto              TEXT,
            data_cadastro        TEXT,
            ultima_atualizacao   TEXT,
            vigencia_inicial     TEXT,
            vigencia_final       TEXT,
            valor_tr_antt        REAL,
            tarifa_contrato      REAL,
            frete_rs_t           REAL,
            manobra_origem_rs_t  REAL,
            manobra_destino_rs_t REAL,
            direito_passagem_rs_t REAL,
            fonte                TEXT
        )
        """
    )
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        for (dc, ua, vi, vf, tr, tarifa, frete, mo, md, dp) in linhas:
            cur.execute(
                """INSERT INTO sabba_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 dc, ua, vi, vf, tr, tarifa, frete, mo, md, dp, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM sabba_precos_contratuais").fetchone()[0]
    print(f"sabba_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
