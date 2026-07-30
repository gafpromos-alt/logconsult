#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_petrobahia_precos_contratuais.py

Cria/recria a tabela `petrobahia_precos_contratuais` no banco analitico (logconsult.db)
com o historico de precos contratuais dos fluxos ferroviarios da PETROBAHIA S A, minerado
dos videos de tela do F-LINK (flink.vli.digital, tela "Precos Contratuais"), um video por
fluxo.

Uma linha por (item ferroviario x vigencia/reajuste/re-cadastro).

NAO EXECUTAR automaticamente sem revisao.

Fonte: F-LINK Precos Contratuais (IMG_0439, IMG_0440, IMG_0441, IMG_0442, IMG_0443.MOV).

Nota sobre DIREITO DE PASSAGEM: todos os 5 fluxos da PETROBAHIA (contrato ACS_2026_21,
FNS+EFC) tem um 4o servico "DIREITO DE PASSAGEM" (ferrovia EFC) alem de
FRETE/MANOBRA ORIGEM/MANOBRA DESTINO (ferrovia FNS). Ele soma normalmente na tarifa
contrato: frete + manobra_origem + manobra_destino + direito_passagem = tarifa_contrato.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0439/0440/0441/0442/0443.MOV) - PETROBAHIA"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    42030: dict(contrato="ACS_2026_21", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPT", destino_nome="PATIO DE PALMEIRANTES",
                produto="GASOLINA", video="IMG_0439.MOV"),
    41184: dict(contrato="ACS_2026_21", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="GASOLINA", video="IMG_0440.MOV"),
    42033: dict(contrato="ACS_2026_21", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0441.MOV"),
    40769: dict(contrato="ACS_2026_21", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="OLEO DIESEL", video="IMG_0442.MOV"),
    42029: dict(contrato="ACS_2026_21", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPT", destino_nome="PATIO DE PALMEIRANTES",
                produto="OLEO DIESEL", video="IMG_0443.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada tupla:
#   (data_cadastro, ultima_atualizacao, vig_inicial, vig_final, valor_tr_antt,
#    tarifa_contrato, frete, manobra_origem, manobra_destino, direito_passagem)
# Datas em YYYY-MM-DD. Valores em R$/t.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 42030 | QPM->PPT | GASOLINA | IMG_0439.MOV --- (3 vigencias, video curto)
DADOS[42030] = [
    ("2026-06-30", "2026-06-30", "2026-07-01", "2026-10-20", 682.32, 182.31, 136.76, 21.87, 13.18, 10.50),
    ("2026-05-28", "2026-05-28", "2026-06-01", "2026-10-20", 682.32, 182.55, 129.44, 42.61, 0.00, 10.50),
    ("2026-05-14", "2026-05-14", "2026-04-23", "2026-10-20", 682.32, 184.33, 139.78, 21.87, 12.18, 10.50),
]

# --- 41184 | QPM->PPN | GASOLINA | IMG_0440.MOV --- (8 vigencias, com re-cadastros)
DADOS[41184] = [
    ("2026-06-30", "2026-06-30", "2026-07-01", "2026-10-20", 856.32, 194.96, 150.41, 21.87, 12.18, 10.50),
    ("2026-06-02", "2026-06-02", "2026-04-01", "2026-04-22", 856.32, 171.23, 97.70, 42.61, 20.42, 10.50),
    ("2026-06-02", "2026-06-02", "2026-03-01", "2026-04-22", 856.32, 167.30, 93.77, 42.61, 20.42, 10.50),
    ("2026-05-28", "2026-05-28", "2026-06-01", "2026-10-20", 856.32, 195.22, 121.69, 42.61, 20.42, 10.50),
    ("2026-05-14", "2026-05-14", "2026-04-23", "2026-10-20", 856.32, 197.12, 152.57, 21.87, 12.18, 10.50),
    # re-cadastros: mesmas vigencias que as duas linhas acima, mas com split
    # frete/manobra/direito-de-passagem diferente (DP 14.58 em vez de 10.50)
    ("2026-03-30", "2026-03-30", "2026-04-01", "2026-04-22", 856.32, 171.23, 111.43, 31.31, 13.91, 14.58),
    ("2026-02-27", "2026-02-27", "2026-03-01", "2026-04-22", 856.32, 167.30, 108.54, 30.59, 13.59, 14.58),
    ("2026-02-12", "2026-02-12", "2026-02-01", "2026-04-22", 856.32, 167.71, 111.65, 30.66, 13.62, 11.78),
]

# --- 42033 | PPN->QPM | OLEO DIESEL | IMG_0441.MOV --- (3 vigencias, video curto)
DADOS[42033] = [
    ("2026-06-30", "2026-06-30", "2026-07-01", "2026-10-20", 856.32, 132.26, 98.11, 0.00, 21.87, 12.28),
    ("2026-05-28", "2026-05-28", "2026-06-01", "2026-10-20", 856.32, 132.43, 98.28, 0.00, 21.87, 12.28),
    ("2026-05-14", "2026-05-14", "2026-04-23", "2026-10-20", 856.32, 133.72, 99.57, 0.00, 21.87, 12.28),
]

# --- 40769 | QPM->PPN | OLEO DIESEL | IMG_0442.MOV --- (11 vigencias, o video
# mais extenso da PETROBAHIA - historia completa desde 22/10/2025)
DADOS[40769] = [
    ("2026-06-30", "2026-06-30", "2026-07-01", "2026-10-20", 856.32, 194.96, 148.63, 21.87, 12.18, 12.28),
    ("2026-06-02", "2026-06-02", "2026-04-01", "2026-04-22", 856.32, 171.23, 95.92, 42.61, 20.42, 12.28),
    ("2026-06-02", "2026-06-02", "2026-03-01", "2026-04-22", 856.32, 167.30, 91.99, 42.61, 20.42, 12.28),
    ("2026-05-28", "2026-05-28", "2026-06-01", "2026-10-20", 856.32, 195.22, 119.91, 42.61, 20.42, 12.28),
    ("2026-05-14", "2026-05-14", "2026-04-23", "2026-10-20", 856.32, 197.12, 150.79, 21.87, 12.18, 12.28),
    ("2026-03-30", "2026-03-30", "2026-04-01", "2026-04-22", 856.32, 171.23, 111.43, 31.31, 13.91, 14.58),
    ("2026-02-27", "2026-02-27", "2026-03-01", "2026-04-22", 856.32, 167.30, 108.54, 30.59, 13.59, 14.58),
    ("2026-01-30", "2026-01-30", "2026-02-01", "2026-04-22", 856.32, 167.71, 111.65, 30.66, 13.62, 11.78),
    ("2026-01-09", "2026-01-09", "2026-01-01", "2026-04-22", 866.72, 167.76, 111.68, 30.67, 13.63, 11.78),
    ("2025-12-01", "2025-12-01", "2025-12-01", "2026-04-22", 866.72, 168.14, 111.96, 30.74, 13.66, 11.78),
    ("2025-11-19", "2025-11-19", "2025-10-22", "2026-04-22", 866.72, 167.20, 111.27, 30.57, 13.58, 11.78),
]

# --- 42029 | QPM->PPT | OLEO DIESEL | IMG_0443.MOV --- (3 vigencias, video curto)
DADOS[42029] = [
    ("2026-06-30", "2026-06-30", "2026-07-01", "2026-10-20", 682.32, 182.31, 134.98, 21.87, 13.18, 12.28),
    ("2026-05-28", "2026-05-28", "2026-06-01", "2026-10-20", 682.32, 182.55, 127.66, 42.61, 0.00, 12.28),
    ("2026-05-14", "2026-05-14", "2026-04-23", "2026-10-20", 682.32, 184.33, 138.00, 21.87, 12.18, 12.28),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + MD + DP == tarifa_contrato (tolerancia 0,05)."""
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
    cur.execute("DROP TABLE IF EXISTS petrobahia_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE petrobahia_precos_contratuais (
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
                """INSERT INTO petrobahia_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 dc, ua, vi, vf, tr, tarifa, frete, mo, md, dp, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM petrobahia_precos_contratuais").fetchone()[0]
    print(f"petrobahia_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
