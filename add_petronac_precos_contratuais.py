#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_petronac_precos_contratuais.py

Cria/recria a tabela `petronac_precos_contratuais` no banco analitico (logconsult.db)
com o historico de precos contratuais dos fluxos ferroviarios da PETRONAC COMBUSTIVEIS,
minerado dos videos de tela do F-LINK (flink.vli.digital, tela "Precos Contratuais").

Uma linha por (item ferroviario x vigencia/reajuste/re-cadastro).

NAO EXECUTAR automaticamente sem revisao.

Fonte: F-LINK Precos Contratuais (IMG_0444, IMG_0445, IMG_0446, IMG_0447, IMG_0448.MOV).

IMPORTANTE - COBERTURA PARCIAL: contrato C_2022_21 (vigencia 01/12/2012-31/12/2027) e
reajustado ~mensalmente desde 2023, com dezenas de re-cadastros por item. Os videos 444-448
tem 12-22s de rolagem cada (75-131 frames a 6fps) cobrindo o historico completo 2023-2027.
Devido ao volume de linhas e a trechos de rolagem com "scroll-blur"/dupla-exposicao (ver
disciplina do projeto: descartar frames borrados), foram transcritas e validadas
(soma dos servicos = tarifa_contrato, tolerancia R$0,05) TODAS as vigencias legiveis nos
frames nitidos revisados - uma amostra ampla e representativa cobrindo 2023 a 2026/2027 para
cada item, mas nao necessariamente 100% dos re-cadastros mensais existentes no video (alguns
meses intermediarios ficaram em trechos de rolagem irremediavelmente borrados e foram
OMITIDOS, nunca inventados). Ver relatorio da mineracao para detalhes por item.

Item 39838 (video IMG_0449.MOV, mesma rota PPN->QPM, OLEO DIESEL) foi EXCLUIDO desta
mineracao: os campos "Cliente" e "Contrato/Acordo" no cabecalho do video vieram em branco
(nao apenas ilegiveis - o rotulo aparece mas o valor abaixo dele nao carregou), impossivel
confirmar tratar-se da PETRONAC.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0444/0445/0446/0447/0448.MOV) - PETRONAC (cobertura parcial, ver notas no script)"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    7548: dict(contrato="C_2022_21", origem="QPM", origem_nome="PONTA DA MADEIRA",
               destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
               produto="GASOLINA", video="IMG_0444.MOV"),
    18169: dict(contrato="C_2022_21", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="ALCOOL", video="IMG_0445.MOV"),
    7547: dict(contrato="C_2022_21", origem="QPM", origem_nome="PONTA DA MADEIRA",
               destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
               produto="OLEO DIESEL", video="IMG_0446.MOV"),
    18038: dict(contrato="C_2022_21", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0447.MOV + IMG_0448.MOV (mesmo item, 2a passada)"),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada tupla:
#   (data_cadastro, ultima_atualizacao, vig_inicial, vig_final, valor_tr_antt,
#    tarifa_contrato, frete, manobra_origem, manobra_destino, direito_passagem)
# Datas em YYYY-MM-DD. Valores em R$/t. Ordem de servicos no F-LINK varia por item
# (MANOBRA DESTINO antes de MANOBRA ORIGEM em alguns itens) - normalizado aqui.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 7548 | C_2022_21 | QPM->PPN | GASOLINA | IMG_0444.MOV ---
# Item mais mineirado do lote: 20 vigencias validadas cobrindo 2023-2027.
# Servicos: DIREITO DE PASSAGEM (EFC) + FRETE/MANOBRA ORIGEM/MANOBRA DESTINO (FNS).
DADOS[7548] = [
    ("2026-07-08", "2026-07-08", "2026-07-10", "2027-12-31", 856.32, 221.75, 146.09, 44.05, 21.11, 10.50),
    ("2026-06-08", "2026-06-08", "2026-03-10", "2026-04-09", 856.32, 218.84, 145.31, 42.61, 20.42, 10.50),
    ("2026-05-28", "2026-05-28", "2026-06-10", "2026-12-31", 856.32, 222.06, 148.53, 42.61, 20.42, 10.50),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2026-12-31", 856.32, 224.35, 150.82, 42.61, 20.42, 10.50),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2026-12-31", 856.32, 224.35, 150.82, 42.61, 20.42, 10.50),  # re-cadastro (mesmo dia)
    ("2026-04-09", "2026-04-09", "2026-04-10", "2027-12-31", 856.32, 223.98, 150.45, 42.61, 20.42, 10.50),
    ("2026-02-05", "2026-02-05", "2026-02-10", "2026-12-31", 856.32, 219.38, 146.28, 42.61, 20.42, 10.07),
    ("2025-03-03", "2025-03-03", "2025-03-10", "2025-12-31", 866.72, 221.72, 146.95, 44.05, 21.11, 9.61),
    ("2025-02-05", "2025-02-05", "2025-02-10", "2025-12-31", 866.72, 222.43, 147.45, 44.19, 21.18, 9.61),
    ("2025-01-03", "2025-01-03", "2025-01-10", "2025-12-31", 811.08, 220.39, 210.78, 0.00, 0.00, 9.61),
    ("2024-12-06", "2024-12-06", "2024-12-10", "2025-12-31", 811.08, 218.03, 144.34, 43.32, 20.76, 9.61),
    ("2024-10-31", "2024-10-31", "2024-10-31", "2025-12-31", 811.08, 214.14, 141.50, 42.61, 20.42, 9.61),
    ("2024-10-01", "2024-10-01", "2024-10-10", "2024-10-31", 811.08, 214.14, 141.50, 42.61, 20.42, 9.61),
    ("2024-02-01", "2024-02-01", "2024-02-10", "2024-10-31", 811.08, 214.14, 181.68, 11.64, 11.64, 9.18),
    ("2023-12-29", "2023-12-29", "2024-01-10", "2024-10-31", 838.76, 219.62, 187.16, 11.64, 11.64, 9.18),
    ("2023-11-30", "2023-11-30", "2023-12-10", "2024-10-31", 838.76, 224.55, 192.09, 11.64, 11.64, 9.18),
    ("2023-11-13", "2023-11-13", "2023-11-10", "2024-10-31", 838.76, 224.55, 192.09, 11.64, 11.64, 9.18),  # re-cadastro
    ("2023-11-13", "2023-11-13", "2023-11-01", "2024-10-31", 838.76, 220.00, 187.54, 11.64, 11.64, 9.18),
    ("2023-09-28", "2023-10-31", "2023-10-10", "2024-10-31", 838.76, 196.38, 163.92, 11.64, 11.64, 9.18),
]

# --- 18169 | C_2022_21 | PPN->QPM | ALCOOL | IMG_0445.MOV ---
# Ordem de servicos na tela: MANOBRA DESTINO, MANOBRA ORIGEM, FRETE, DIREITO DE PASSAGEM.
# 12 vigencias validadas (2023-2026); gaps de meses intermediarios com scroll-blur
# persistente foram omitidos (nao inventados).
DADOS[18169] = [
    ("2026-07-08", "2026-07-08", "2026-07-10", "2027-12-31", 635.41, 111.39, 57.23, 0.01, 42.61, 11.54),
    ("2025-02-05", "2025-02-05", "2025-02-10", "2025-12-31", 843.14, 111.74, 38.16, 20.42, 42.61, 10.55),
    ("2025-01-03", "2025-01-03", "2025-01-10", "2025-12-31", 601.85, 110.71, 100.16, 0.00, 0.00, 10.55),
    ("2024-12-08", "2024-12-08", "2024-12-10", "2025-12-31", 601.85, 109.52, 55.66, 0.00, 43.31, 10.55),
    ("2024-10-31", "2024-10-31", "2024-10-31", "2025-12-31", 601.85, 102.79, 29.21, 20.42, 42.61, 10.55),
    ("2024-10-01", "2024-10-01", "2024-10-10", "2024-10-31", 601.85, 102.79, 29.21, 20.42, 42.61, 10.55),  # re-cadastro
    ("2024-08-30", "2024-08-30", "2024-09-10", "2024-10-31", 601.85, 102.79, 29.21, 20.42, 42.61, 10.55),  # re-cadastro (mesmo padrao)
    ("2024-02-01", "2024-02-01", "2024-02-10", "2024-10-31", 801.85, 102.79, 66.82, 12.94, 12.94, 10.09),
    ("2023-12-29", "2023-12-29", "2024-01-10", "2024-10-31", 622.39, 105.42, 69.45, 12.94, 12.94, 10.09),
    ("2023-11-30", "2023-11-30", "2023-12-10", "2024-10-31", 622.39, 107.79, 71.82, 12.94, 12.94, 10.09),
    ("2023-11-13", "2023-11-13", "2023-11-10", "2024-10-31", 622.39, 107.79, 71.82, 12.94, 12.94, 10.09),  # re-cadastro
    ("2023-11-13", "2023-11-13", "2023-11-01", "2024-10-31", 622.39, 105.60, 69.63, 12.94, 12.94, 10.09),
]

# --- 7547 | C_2022_21 | QPM->PPN | OLEO DIESEL | IMG_0446.MOV ---
# 16 vigencias validadas (2023-2026).
DADOS[7547] = [
    ("2026-07-08", "2026-07-08", "2026-07-10", "2027-12-31", 856.32, 221.75, 146.44, 42.61, 20.42, 12.28),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2026-12-31", 856.32, 224.35, 149.04, 42.61, 20.42, 12.28),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2026-12-31", 856.32, 224.35, 149.04, 42.61, 20.42, 12.28),  # re-cadastro
    ("2026-04-09", "2026-04-09", "2026-04-10", "2027-12-31", 856.32, 223.98, 148.67, 42.61, 20.42, 12.28),
    ("2026-02-27", "2026-02-27", "2026-03-10", "2026-12-31", 856.32, 218.84, 141.23, 42.61, 20.42, 14.58),
    ("2026-02-05", "2026-02-05", "2026-02-10", "2026-12-31", 856.32, 219.38, 144.57, 42.61, 20.42, 11.78),
    ("2026-01-30", "2026-01-30", "2026-02-10", "2026-12-31", 856.32, 219.38, 144.57, 42.61, 20.42, 11.78),  # re-cadastro
    ("2025-05-08", "2025-05-08", "2025-05-10", "2025-12-31", 866.72, 217.65, 142.46, 43.24, 20.72, 11.23),
    ("2025-04-08", "2025-04-08", "2025-04-10", "2025-12-31", 866.72, 220.70, 144.61, 43.85, 21.01, 11.23),
    ("2025-03-03", "2025-03-03", "2025-03-10", "2025-12-31", 866.72, 221.72, 145.33, 44.05, 21.11, 11.23),
    ("2025-02-05", "2025-02-05", "2025-02-10", "2025-12-31", 866.72, 222.43, 148.17, 42.61, 20.42, 11.23),
    ("2025-01-03", "2025-01-03", "2025-01-10", "2025-12-31", 811.08, 220.39, 209.16, 0.00, 0.00, 11.23),
    ("2023-11-30", "2023-11-30", "2023-12-10", "2024-10-31", 838.76, 224.55, 186.65, 13.58, 13.58, 10.74),
    ("2023-11-13", "2023-11-13", "2023-11-10", "2024-10-31", 838.76, 224.55, 186.65, 13.58, 13.58, 10.74),  # re-cadastro
    ("2023-11-13", "2023-11-13", "2023-11-01", "2024-10-31", 838.76, 220.00, 182.10, 13.58, 13.58, 10.74),
    ("2023-09-28", "2023-10-31", "2023-10-10", "2024-10-31", 838.76, 196.38, 158.48, 13.58, 13.58, 10.74),
]

# --- 18038 | C_2022_21 | PPN->QPM | OLEO DIESEL | IMG_0447.MOV + IMG_0448.MOV ---
# Mesmo item ferroviario capturado em 2 videos (2a passada complementou linhas nao
# lidas na 1a). Ordem de servicos na tela: MANOBRA DESTINO, MANOBRA ORIGEM, FRETE,
# DIREITO DE PASSAGEM. 25 vigencias validadas (2023-2026).
DADOS[18038] = [
    ("2026-07-08", "2026-07-08", "2026-07-10", "2027-12-31", 856.32, 111.39, 56.50, 0.00, 42.61, 12.28),
    ("2026-05-28", "2026-05-28", "2026-06-10", "2026-12-31", 856.32, 111.54, 36.23, 20.42, 42.61, 12.28),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2026-12-31", 856.32, 112.69, 37.38, 20.42, 42.61, 12.28),
    ("2026-04-29", "2026-04-29", "2026-05-10", "2026-12-31", 856.32, 112.69, 37.38, 20.42, 42.61, 12.28),  # re-cadastro
    ("2026-04-09", "2026-04-09", "2026-04-10", "2027-12-31", 856.32, 112.51, 37.20, 20.42, 42.61, 12.28),
    ("2026-02-27", "2026-02-27", "2026-03-10", "2026-12-31", 856.32, 109.93, 32.32, 20.42, 42.61, 14.58),
    ("2025-12-08", "2025-12-08", "2025-12-10", "2025-12-31", 866.72, 110.48, 55.01, 0.00, 43.69, 11.78),
    ("2025-11-10", "2025-11-10", "2025-11-10", "2025-12-31", 866.72, 109.77, 34.96, 20.42, 42.61, 11.78),
    ("2025-09-29", "2025-09-29", "2025-10-10", "2025-12-31", 866.72, 109.17, 54.21, 0.00, 43.18, 11.78),
    ("2025-08-28", "2025-08-28", "2025-09-10", "2025-12-31", 866.72, 109.16, 54.21, 0.00, 43.17, 11.78),
    ("2025-07-30", "2025-07-30", "2025-08-10", "2025-12-31", 866.72, 108.49, 53.80, 0.00, 42.91, 11.78),
    ("2025-07-04", "2025-07-04", "2025-07-10", "2025-12-31", 866.72, 108.40, 53.75, 0.00, 42.87, 11.78),
    ("2025-01-03", "2025-01-03", "2025-01-10", "2025-12-31", 811.08, 110.71, 99.48, 0.00, 0.00, 11.23),
    ("2024-12-08", "2024-12-08", "2024-12-10", "2025-12-31", 811.08, 109.52, 54.98, 0.00, 43.31, 11.23),
    ("2024-10-31", "2024-10-31", "2024-10-31", "2025-12-31", 811.08, 102.79, 28.53, 20.42, 42.61, 11.23),
    ("2024-10-01", "2024-10-01", "2024-10-10", "2024-10-31", 811.08, 102.79, 28.53, 20.42, 42.61, 11.23),  # re-cadastro
    ("2024-08-30", "2024-08-30", "2024-09-10", "2024-10-31", 811.08, 102.79, 64.40, 13.58, 13.58, 11.23),  # re-cadastro
    ("2024-07-31", "2024-07-31", "2024-08-10", "2024-10-31", 811.08, 102.79, 64.40, 13.58, 13.58, 11.23),
    ("2024-07-01", "2024-07-01", "2024-07-10", "2024-10-31", 811.08, 102.79, 64.40, 13.58, 13.58, 11.23),
    ("2024-06-04", "2024-06-04", "2024-08-10", "2024-10-31", 811.08, 102.79, 64.40, 13.58, 13.58, 11.23),  # re-cadastro
    ("2024-05-02", "2024-05-02", "2024-05-10", "2024-10-31", 811.08, 102.79, 64.40, 13.58, 13.58, 11.23),
    ("2023-12-29", "2023-12-29", "2024-01-10", "2024-10-31", 838.76, 105.42, 67.52, 13.58, 13.58, 10.74),
    ("2023-11-30", "2023-11-30", "2023-12-10", "2024-10-31", 838.76, 107.79, 69.89, 13.58, 13.58, 10.74),
    ("2023-11-13", "2023-11-13", "2023-11-10", "2024-10-31", 838.76, 107.79, 69.89, 13.58, 13.58, 10.74),  # re-cadastro
    ("2023-11-13", "2023-11-13", "2023-11-01", "2024-10-31", 838.76, 105.60, 67.70, 13.58, 13.58, 10.74),
    ("2023-09-28", "2023-10-31", "2023-10-10", "2024-10-31", 838.76, 98.19, 60.29, 13.58, 13.58, 10.74),
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
    cur.execute("DROP TABLE IF EXISTS petronac_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE petronac_precos_contratuais (
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
                """INSERT INTO petronac_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 dc, ua, vi, vf, tr, tarifa, frete, mo, md, dp, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM petronac_precos_contratuais").fetchone()[0]
    print(f"petronac_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
