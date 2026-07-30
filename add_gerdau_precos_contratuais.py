#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_gerdau_precos_contratuais.py

Cria/recria a tabela `gerdau_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos fluxos
ferroviarios do grupo GERDAU (razoes sociais "GERDAU ACOMINAS S/A" e "GERDAU
ACOS LONGOS S.A."), minerado dos videos de tela do F-LINK (flink.vli.digital,
tela "Precos Contratuais"), um video por fluxo.

Uma linha por (item ferroviario x vigencia/reajuste).

Lote original (14/jul): 7 itens, videos IMG_0239-0246.
Lote novo (18/jul): +27 itens, videos IMG_0492-0522 (IMG_0498/0499 e IMG_0500
apenas confirmaram os itens 16967 e 7958 ja existentes, sem alteracao).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente.

Fonte: F-LINK Precos Contratuais (IMG_0239-0246 e IMG_0492-0522) - historico
de reajuste GERDAU.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0239-0246, IMG_0492-0522) - historico de reajuste GERDAU"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# item, contrato, origem, origem_nome, destino, destino_nome, produto, video
# ---------------------------------------------------------------------------
FLUXOS = {
    9611: dict(contrato="C_2023_8", origem="VTU", origem_nome="TUBARAO",
               destino="VOB", destino_nome="OURO BRANCO",
               produto="CARVAO MINERAL", video="IMG_0239.MOV"),
    9612: dict(contrato="C_2023_8", origem="VTU", origem_nome="TUBARAO",
               destino="VOB", destino_nome="OURO BRANCO",
               produto="ANTRACITO", video="IMG_0240.MOV"),
    7958: dict(contrato="C_2023_7", origem="VTU", origem_nome="TUBARAO",
               destino="VOB", destino_nome="OURO BRANCO",
               produto="PRO SIDERURGICO", video="IMG_0242.MOV"),
    9613: dict(contrato="C_2023_8", origem="VTU", origem_nome="TUBARAO",
               destino="VOB", destino_nome="OURO BRANCO",
               produto="COQUE GROSSO", video="IMG_0243.MOV"),
    9646: dict(contrato="C_2023_7", origem="VTU", origem_nome="TUBARAO",
               destino="VOB", destino_nome="OURO BRANCO",
               produto="FIO MAQUINA", video="IMG_0244.MOV"),
    16967: dict(contrato="C_2023_7", origem="VMR", origem_nome="MARIO CARVALHO",
                destino="VOB", destino_nome="OURO BRANCO",
                produto="PRO SIDERURGICO", video="IMG_0245.MOV"),
    17829: dict(contrato="C_2023_8", origem="EVP", origem_nome="VESPASIANO",
                destino="VOB", destino_nome="OURO BRANCO",
                produto="COQUE PETROLEO", video="IMG_0246.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete, manobra_origem, manobra_destino)
# Datas em YYYY-MM-DD. Valores em R$/t. Use None se um servico nao existir.
# Preenchido incrementalmente a partir da leitura dos frames dos videos.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 9611 | C_2023_8 | VTU->VOB | CARVAO MINERAL | IMG_0239.MOV ---
# 37 vigencias (2023-10-20 -> 2026-07-20). Manobra constante 25/25.
# TR ANTT por regime anual: 2023=97,67 | 2024=102,38 | 2025=107,25 | 2026=112,27
DADOS[9611] = [
    # vig_ini      vig_fim       TR       tarifa   frete    MO     MD
    ("2026-07-20", "2026-12-31", 112.27, 122.79, 72.79, 25.00, 25.00),
    ("2026-06-20", "2026-12-31", 112.27, 122.72, 72.72, 25.00, 25.00),
    ("2026-05-20", "2026-12-31", 112.27, 122.98, 72.98, 25.00, 25.00),
    ("2026-04-20", "2026-12-31", 112.27, 123.08, 73.08, 25.00, 25.00),
    ("2026-03-20", "2026-12-31", 112.27, 123.61, 73.61, 25.00, 25.00),
    ("2026-02-20", "2026-12-31", 112.27, 123.96, 73.96, 25.00, 25.00),
    ("2026-01-30", "2026-12-31", 112.27, 123.69, 73.69, 25.00, 25.00),
    ("2026-01-20", "2026-01-31", 112.27, 123.69, 73.69, 25.00, 25.00),
    ("2026-01-01", "2026-01-19", 112.27, 123.54, 73.54, 25.00, 25.00),
    ("2025-12-20", "2025-12-31", 107.25, 124.45, 74.45, 25.00, 25.00),
    ("2025-11-20", "2025-12-31", 107.25, 124.10, 74.10, 25.00, 25.00),
    ("2025-10-20", "2025-12-31", 107.25, 124.18, 74.18, 25.00, 25.00),
    ("2025-09-20", "2025-12-31", 107.25, 124.17, 74.17, 25.00, 25.00),
    ("2025-08-20", "2025-12-31", 107.25, 123.71, 73.71, 25.00, 25.00),
    ("2025-07-20", "2025-12-31", 107.25, 123.59, 73.59, 25.00, 25.00),
    ("2025-06-20", "2025-12-31", 107.25, 123.67, 73.67, 25.00, 25.00),
    ("2025-05-20", "2025-12-31", 107.25, 124.70, 74.70, 25.00, 25.00),
    ("2025-04-20", "2025-12-31", 107.25, 126.62, 76.62, 25.00, 25.00),
    ("2025-03-20", "2025-12-31", 107.25, 126.81, 76.81, 25.00, 25.00),
    ("2025-02-20", "2025-12-31", 107.25, 124.42, 74.42, 25.00, 25.00),
    ("2025-01-20", "2025-01-31", 107.25, 124.20, 74.20, 25.00, 25.00),
    ("2025-01-01", "2025-01-19", 107.25, 124.54, 74.54, 25.00, 25.00),
    ("2024-12-20", "2025-12-31", 102.38, 119.14, 69.14, 25.00, 25.00),
    ("2024-11-20", "2025-12-31", 102.38, 118.43, 68.43, 25.00, 25.00),
    ("2024-10-20", "2025-12-31", 102.38, 117.91, 67.91, 25.00, 25.00),
    ("2024-09-20", "2025-12-31", 102.38, 117.65, 67.65, 25.00, 25.00),
    ("2024-08-20", "2025-12-31", 102.38, 117.67, 67.67, 25.00, 25.00),
    ("2024-07-20", "2025-12-31", 102.38, 117.91, 67.91, 25.00, 25.00),
    ("2024-06-20", "2025-12-31", 102.38, 117.34, 67.34, 25.00, 25.00),
    ("2024-05-20", "2025-12-31", 102.38, 117.46, 67.46, 25.00, 25.00),
    ("2024-04-20", "2025-12-31", 102.38, 117.34, 67.34, 25.00, 25.00),
    ("2024-03-20", "2025-12-31", 102.38, 117.18, 67.18, 25.00, 25.00),
    ("2024-02-20", "2025-12-31", 102.38, 116.30, 66.30, 25.00, 25.00),
    ("2024-01-20", "2025-12-31", 102.38, 115.89, 65.89, 25.00, 25.00),
    ("2023-12-20", "2025-12-31",  97.67, 120.68, 70.68, 25.00, 25.00),
    ("2023-11-20", "2025-12-31",  97.67, 120.43, 70.43, 25.00, 25.00),
    ("2023-10-20", "2025-12-31",  97.67, 119.48, 69.48, 25.00, 25.00),
]

# --- 9612 | C_2023_8 | VTU->VOB | ANTRACITO | IMG_0240.MOV ---
# Mesma rota/contrato/wagon do 9611: as vigencias, tarifa_contrato, frete e
# manobras (25/25) sao IDENTICAS ao 9611 (verificado frame a frame em ~30
# pontos, cobrindo 2023-2026). A UNICA diferenca e o Valor TR (ANTT), que e
# especifico do produto ANTRACITO e muda por regime anual da ANTT:
TR_ANTT_9612 = {2023: 121.35, 2024: 127.21, 2025: 133.28, 2026: 139.50}
DADOS[9612] = [
    (vi, vf, TR_ANTT_9612[int(vi[:4])], tarifa, frete, mo, md)
    for (vi, vf, _tr, tarifa, frete, mo, md) in DADOS[9611]
]

# --- 7958 | C_2023_7 | VTU->VOB | PRO SIDERURGICO | IMG_0242.MOV ---
# ATENCAO (C_2023_7): a manobra NAO e constante - muda ao longo do tempo, e o
# F-LINK contem re-cadastros (mesma vigencia com tarifa igual mas split
# frete/manobra diferente). Aqui gravamos UMA linha por vigencia com o split
# efetivamente lido (validado pela soma). TR ANTT por regime anual:
#   2023=75,91 | 2024=79,57 | 2025=83,35 | 2026=87,26
# Notas: (1) 20/12/2025 tem DOIS cadastros distintos (vf 31/12/2025 tarifa
# 112,98 e vf 31/01/2026 tarifa 112,88) - ambos incluidos. (2) 20/01/2025 nao
# foi lido de forma limpa -> omitido (ver relatorio). (3) linha 2025-02-20
# aparece rotulada "01/02/2025" na tela (leitura ambigua do dia).
DADOS[7958] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-07-20", "2026-12-31", 87.26, 111.49, 85.19, 12.58, 13.72),
    ("2026-06-20", "2026-12-31", 87.26, 111.42, 85.12, 12.58, 13.72),
    ("2026-05-20", "2026-12-31", 87.26, 111.65, 85.35, 12.58, 13.72),
    ("2026-04-20", "2026-12-31", 87.26, 111.74, 85.44, 12.58, 13.72),
    ("2026-03-20", "2026-12-31", 87.26, 112.22, 85.92, 12.58, 13.72),
    ("2026-02-20", "2026-12-31", 87.26, 112.54, 86.24, 12.58, 13.72),
    ("2026-01-30", "2026-12-31", 87.26, 112.43, 78.43, 17.00, 17.00),
    ("2026-01-20", "2026-01-31", 87.26, 112.43, 78.43, 17.00, 17.00),
    ("2026-01-01", "2026-01-19", 87.26, 112.34, 78.34, 17.00, 17.00),
    ("2025-12-20", "2025-12-31", 83.35, 112.98, 78.98, 17.00, 17.00),
    ("2025-12-20", "2026-01-31", 83.35, 112.88, 78.88, 17.00, 17.00),  # 2o cadastro
    ("2025-11-20", "2025-12-31", 83.35, 112.67, 78.67, 17.00, 17.00),
    ("2025-10-20", "2025-12-31", 83.35, 112.73, 78.73, 17.00, 17.00),
    ("2025-09-20", "2025-12-31", 83.35, 112.72, 78.72, 17.00, 17.00),
    ("2025-08-20", "2025-12-31", 83.35, 112.31, 78.31, 17.00, 17.00),
    ("2025-07-20", "2025-12-31", 83.35, 112.20, 78.20, 17.00, 17.00),
    ("2025-06-20", "2025-12-31", 83.35, 112.27, 78.27, 17.00, 17.00),
    ("2025-05-20", "2025-12-31", 83.35, 113.21, 79.21, 17.00, 17.00),
    ("2025-04-20", "2025-12-31", 83.35, 114.95, 80.95, 17.00, 17.00),
    ("2025-03-20", "2025-12-31", 83.35, 115.12, 83.12, 16.00, 16.00),
    ("2025-02-20", "2025-12-31", 83.35, 112.76, 82.76, 15.00, 15.00),
    ("2025-01-01", "2025-01-19", 83.35, 113.06, 83.06, 15.00, 15.00),
    ("2024-12-20", "2025-12-31", 79.57, 108.16, 79.40, 14.38, 14.38),
    ("2024-11-20", "2025-12-31", 79.57, 105.21, 78.91, 12.58, 13.72),
    ("2024-10-20", "2025-12-31", 79.57, 104.75, 78.45, 12.58, 13.72),
    ("2024-09-20", "2025-12-31", 79.57, 104.51, 78.21, 12.58, 13.72),
    ("2024-08-20", "2025-12-31", 79.57, 106.83, 69.88, 25.00, 11.95),
    ("2024-07-20", "2025-12-31", 79.57, 107.05, 70.10, 25.00, 11.95),
    ("2024-06-20", "2025-12-31", 79.57, 106.53, 69.58, 25.00, 11.95),
    ("2024-05-20", "2025-12-31", 79.57, 106.64, 69.69, 25.00, 11.95),
    ("2024-04-20", "2025-12-31", 79.57, 106.53, 69.58, 25.00, 11.95),
    ("2024-03-20", "2025-12-31", 79.57, 106.39, 69.44, 25.00, 11.95),
    ("2024-02-20", "2025-12-31", 79.57, 105.59, 68.64, 25.00, 11.95),
    ("2024-01-20", "2025-12-31", 79.57, 105.31, 68.36, 25.00, 11.95),
    ("2023-12-20", "2025-12-31", 75.91, 109.57, 72.62, 25.00, 11.95),
    ("2023-11-20", "2025-12-31", 75.91, 109.34, 72.39, 25.00, 11.95),
    ("2023-10-20", "2025-12-31", 75.91, 108.48, 71.53, 25.00, 11.95),
]

# --- 9613 | C_2023_8 | VTU->VOB | COQUE GROSSO | IMG_0243.MOV ---
# Mesma rota/contrato do 9611: vigencias e tarifa_contrato IDENTICAS ao 9611
# (verificado frame a frame em ~20 pontos, 2023-2026). Diferencas do produto
# COQUE GROSSO: (a) Valor TR (ANTT) igual ao do 9612 (mesmo teto ANTT);
# (b) manobra CONSTANTE MO=13,17 / MD=25,00 (=> frete = tarifa - 38,17).
DADOS[9613] = [
    (vi, vf, TR_ANTT_9612[int(vi[:4])], tarifa, round(tarifa - 38.17, 2), 13.17, 25.00)
    for (vi, vf, _tr, tarifa, _f, _mo, _md) in DADOS[9611]
]

# --- 9646 | C_2023_7 | VTU->VOB | FIO MAQUINA | IMG_0244.MOV ---
# C_2023_7 (mesma rota do 7958): tarifa_contrato e Valor TR ANTT praticamente
# iguais aos do 7958 (TR 2023=75,91|2024=79,57|2025=83,35|2026=87,26), MAS o
# split frete/manobra e proprio deste item. Diferenca marcante: em 2024 e 2023
# a manobra e 25,00/25,00 (no 7958 era 25,00/11,95). Linhas marcadas (*mir)
# tiveram a tarifa preenchida pelo espelho 7958 (mes nao lido de forma limpa);
# manobra desses meses segue o padrao do proprio 9646. Ver relatorio.
DADOS[9646] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-07-20", "2026-12-31", 87.26, 111.49, 85.19, 12.58, 13.72),
    ("2026-06-20", "2026-12-31", 87.26, 111.42, 85.12, 12.58, 13.72),
    ("2026-05-20", "2026-12-31", 87.26, 111.65, 85.35, 12.58, 13.72),  # *mir
    ("2026-04-20", "2026-12-31", 87.26, 111.74, 85.44, 12.58, 13.72),
    ("2026-03-20", "2026-12-31", 87.26, 112.22, 85.92, 12.58, 13.72),
    ("2026-02-20", "2026-12-31", 87.26, 112.54, 86.24, 12.58, 13.72),
    ("2026-01-30", "2026-12-31", 87.26, 112.43, 78.43, 17.00, 17.00),
    ("2026-01-20", "2026-01-31", 87.26, 112.43, 78.43, 17.00, 17.00),
    ("2026-01-01", "2026-01-19", 87.26, 112.34, 78.34, 17.00, 17.00),
    ("2025-12-20", "2026-01-31", 83.35, 112.88, 78.88, 17.00, 17.00),  # 1o cadastro
    ("2025-12-20", "2025-12-31", 83.35, 113.02, 79.02, 17.00, 17.00),  # 2o cadastro
    ("2025-11-20", "2025-12-31", 83.35, 112.67, 78.67, 17.00, 17.00),
    ("2025-10-20", "2025-12-31", 83.35, 112.73, 78.73, 17.00, 17.00),  # *mir
    ("2025-09-20", "2025-12-31", 83.35, 112.72, 78.72, 17.00, 17.00),
    ("2025-08-20", "2025-12-31", 83.35, 112.31, 78.31, 17.00, 17.00),
    ("2025-07-20", "2025-12-31", 83.35, 112.20, 78.20, 17.00, 17.00),
    ("2025-06-20", "2025-12-31", 83.35, 112.27, 78.27, 17.00, 17.00),
    ("2025-05-20", "2025-12-31", 83.35, 113.21, 79.21, 17.00, 17.00),
    ("2025-05-20", "2025-12-31", 83.35, 113.25, 79.25, 17.00, 17.00),  # 2o cadastro
    ("2025-04-20", "2025-12-31", 83.35, 114.95, 80.95, 17.00, 17.00),
    ("2025-03-20", "2025-12-31", 83.35, 115.12, 83.12, 16.00, 16.00),  # *mir (manobra padrao 7958)
    ("2025-02-20", "2025-12-31", 83.35, 112.76, 82.76, 15.00, 15.00),
    ("2025-01-01", "2025-01-19", 83.35, 113.06, 83.06, 15.00, 15.00),
    ("2024-12-20", "2025-12-31", 79.57, 108.16, 58.16, 25.00, 25.00),  # *mir tarifa
    ("2024-11-20", "2025-12-31", 79.57, 105.21, 55.21, 25.00, 25.00),  # *mir tarifa
    ("2024-10-20", "2025-12-31", 79.57, 104.75, 54.75, 25.00, 25.00),  # *mir tarifa
    ("2024-09-20", "2025-12-31", 79.57, 104.51, 54.51, 25.00, 25.00),  # *mir tarifa
    ("2024-08-20", "2025-12-31", 79.57, 106.83, 56.83, 25.00, 25.00),
    ("2024-07-20", "2025-12-31", 79.57, 107.05, 57.05, 25.00, 25.00),
    ("2024-06-20", "2025-12-31", 79.57, 106.53, 56.53, 25.00, 25.00),  # *mir tarifa
    ("2024-05-20", "2025-12-31", 79.57, 106.64, 56.64, 25.00, 25.00),
    ("2024-04-20", "2025-12-31", 79.57, 106.53, 56.53, 25.00, 25.00),
    ("2024-03-20", "2025-12-31", 79.57, 106.39, 56.39, 25.00, 25.00),
    ("2024-02-20", "2025-12-31", 79.57, 105.59, 55.59, 25.00, 25.00),
    ("2024-01-20", "2025-12-31", 79.57, 105.31, 55.31, 25.00, 25.00),
    ("2023-12-20", "2025-12-31", 75.91, 109.57, 59.57, 25.00, 25.00),  # *mir tarifa
    ("2023-11-20", "2025-12-31", 75.91, 109.34, 59.34, 25.00, 25.00),
    ("2023-10-20", "2025-12-31", 75.91, 108.48, 58.48, 25.00, 25.00),
]

# --- 16967 | C_2023_7 | VMR->VOB | PRO SIDERURGICO | IMG_0245.MOV ---
# Fluxo proprio (origem VMR = Mario Carvalho), tarifas menores (rota curta).
# Valor TR ANTT: 2023=44,49 | 2024=46,63 | 2025=48,85 | 2026=51,14.
# Manobra: 13,72/13,72 em 2025-2026 e no fim de 2024; 25,00/11,95 em meados/
# inicio de 2024 e em 2023 (padrao de re-cadastro, como no 7958). Ha varios
# duplos-cadastro (mesma vigencia, tarifas 0,4-0,5 diferentes) - mantidos.
# Gaps nao lidos de forma limpa (ver relatorio): 20/01/2025 e 20/10/2023.
DADOS[16967] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-07-20", "2026-12-31", 51.14, 72.50, 45.06, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 51.14, 72.46, 45.02, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 51.14, 72.61, 45.17, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 51.14, 72.67, 45.23, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 51.14, 72.99, 45.55, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 51.14, 73.20, 45.76, 13.72, 13.72),
    ("2026-01-30", "2026-12-31", 51.14, 73.04, 45.60, 13.72, 13.72),
    ("2026-01-20", "2026-01-31", 51.14, 73.04, 45.60, 13.72, 13.72),
    ("2026-01-01", "2026-01-19", 51.14, 72.95, 45.51, 13.72, 13.72),
    ("2025-12-20", "2026-01-31", 48.85, 73.49, 46.05, 13.72, 13.72),  # 1o cadastro
    ("2025-12-20", "2025-12-31", 48.85, 73.94, 46.50, 13.72, 13.72),  # 2o cadastro
    ("2025-11-20", "2025-12-31", 48.85, 73.28, 45.84, 13.72, 13.72),
    ("2025-10-20", "2025-12-31", 48.85, 73.33, 45.89, 13.72, 13.72),
    ("2025-10-20", "2025-12-31", 48.85, 73.79, 46.35, 13.72, 13.72),  # 2o cadastro
    ("2025-09-20", "2025-12-31", 48.85, 73.33, 45.89, 13.72, 13.72),
    ("2025-08-20", "2025-12-31", 48.85, 73.52, 46.08, 13.72, 13.72),
    ("2025-07-20", "2025-12-31", 48.85, 72.99, 45.55, 13.72, 13.72),
    ("2025-07-20", "2025-12-31", 48.85, 73.45, 46.01, 13.72, 13.72),  # 2o cadastro
    ("2025-06-20", "2025-12-31", 48.85, 73.04, 45.60, 13.72, 13.72),
    ("2025-05-20", "2025-12-31", 48.85, 73.65, 46.21, 13.72, 13.72),
    ("2025-05-20", "2025-12-31", 48.85, 74.10, 46.66, 13.72, 13.72),  # 2o cadastro
    ("2025-04-20", "2025-12-31", 48.85, 75.22, 47.78, 13.72, 13.72),
    ("2025-03-20", "2025-12-31", 48.85, 75.33, 47.89, 13.72, 13.72),
    ("2025-02-20", "2025-12-31", 48.85, 73.78, 46.34, 13.72, 13.72),  # tela: 01/02/2025
    ("2025-01-01", "2025-01-19", 48.85, 73.98, 46.54, 13.72, 13.72),
    ("2024-12-20", "2025-12-31", 46.63, 70.77, 43.33, 13.72, 13.72),
    ("2024-11-20", "2025-12-31", 46.63, 68.84, 41.40, 13.72, 13.72),
    ("2024-10-20", "2025-12-31", 46.63, 68.53, 41.09, 13.72, 13.72),
    ("2024-09-20", "2025-12-31", 46.63, 68.38, 40.94, 13.72, 13.72),  # (2o cadastro c/ 25,00/11,95, mesma tarifa)
    ("2024-08-20", "2025-12-31", 46.63, 69.89, 32.94, 25.00, 11.95),
    ("2024-07-20", "2025-12-31", 46.63, 70.03, 33.08, 25.00, 11.95),
    ("2024-06-20", "2025-12-31", 46.63, 69.69, 32.74, 25.00, 11.95),
    ("2024-05-20", "2025-12-31", 46.63, 69.77, 32.82, 25.00, 11.95),
    ("2024-04-20", "2025-12-31", 46.63, 69.70, 32.75, 25.00, 11.95),
    ("2024-03-20", "2025-12-31", 46.63, 69.61, 32.66, 25.00, 11.95),
    ("2024-02-20", "2025-12-31", 46.63, 69.09, 32.14, 25.00, 11.95),
    ("2024-01-20", "2025-12-31", 46.63, 68.91, 31.96, 25.00, 11.95),
    ("2023-12-20", "2025-12-31", 44.49, 71.69, 34.74, 25.00, 11.95),
    ("2023-11-20", "2025-12-31", 44.49, 71.54, 34.59, 25.00, 11.95),
]

# --- 17829 | C_2023_8 | EVP->VOB | COQUE PETROLEO | IMG_0246.MOV ---
# Estrutura DIFERENTE: fluxo intermodal em DUAS ferrovias (FCA + EFVM), com 4
# linhas de servico: FRETE (FCA) + FRETE (EFVM) + MANOBRA ORIGEM (FCA) +
# MANOBRA DESTINO (EFVM). Aqui frete_rs_t = soma dos dois fretes (FCA+EFVM);
# manobra_origem = manobra FCA (16,28) e manobra_destino = manobra EFVM (13,17),
# CONSTANTES em todo o historico => frete = tarifa - 29,45.
# Valor TR ANTT por ano: 2026=100,06 | 2025=97,15 | 2024=93,20 | 2023=93,17
# (linhas re-cadastradas as vezes exibem o TR do ano seguinte; normalizado p/
# o ano da vigencia). Ha varios duplos-cadastro. Gaps nao lidos limpos (ver
# relatorio): 2026-01-30, 2026-01-01; 2025-03 aprox.; 2025-01; boa parte de
# 2024 (12,11,06,05,03) e 2023 anteriores a 20/11.
DADOS[17829] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-07-20", "2026-12-31", 100.06, 55.00, 25.55, 16.28, 13.17),
    ("2026-06-20", "2026-12-31", 100.06, 54.97, 25.52, 16.28, 13.17),
    ("2026-05-20", "2026-12-31", 100.06, 55.08, 25.63, 16.28, 13.17),
    ("2026-04-20", "2026-12-31", 100.06, 55.13, 25.68, 16.28, 13.17),
    ("2026-03-20", "2026-12-31", 100.06, 55.37, 25.92, 16.28, 13.17),
    ("2026-02-20", "2026-12-31", 100.06, 55.53, 26.08, 16.28, 13.17),
    ("2026-01-20", "2026-01-31", 100.06, 55.41, 25.96, 16.28, 13.17),
    ("2025-12-20", "2026-01-31",  97.15, 55.75, 26.30, 16.28, 13.17),  # 1o cadastro
    ("2025-12-20", "2025-12-31",  97.15, 55.76, 26.31, 16.28, 13.17),  # 2o cadastro
    ("2025-11-20", "2025-12-31",  97.15, 55.59, 26.14, 16.28, 13.17),
    ("2025-10-20", "2025-12-31",  97.15, 55.63, 26.18, 16.28, 13.17),
    ("2025-10-20", "2025-12-31",  97.15, 55.64, 26.19, 16.28, 13.17),  # 2o cadastro
    ("2025-09-20", "2025-12-31",  97.15, 55.63, 26.18, 16.28, 13.17),
    ("2025-09-20", "2025-12-31",  97.15, 55.64, 26.19, 16.28, 13.17),  # 2o cadastro
    ("2025-08-20", "2025-12-31",  97.15, 55.44, 25.99, 16.28, 13.17),
    ("2025-07-20", "2025-12-31",  97.15, 55.38, 25.93, 16.28, 13.17),
    ("2025-06-20", "2025-12-31",  97.15, 55.42, 25.97, 16.28, 13.17),
    ("2025-05-20", "2025-12-31",  97.15, 55.89, 26.44, 16.28, 13.17),
    ("2025-04-20", "2025-12-31",  97.15, 56.75, 27.30, 16.28, 13.17),
    ("2025-03-20", "2025-12-31",  97.15, 56.83, 27.38, 16.28, 13.17),  # aprox (frete 4,18+23,20)
    ("2025-02-20", "2025-12-31",  97.15, 55.76, 26.31, 16.28, 13.17),
    ("2024-10-20", "2025-12-31",  93.20, 52.85, 23.40, 16.28, 13.17),
    ("2024-09-20", "2025-12-31",  93.20, 52.73, 23.28, 16.28, 13.17),
    ("2024-08-20", "2025-12-31",  93.20, 52.74, 23.29, 16.28, 13.17),
    ("2024-07-20", "2025-12-31",  93.20, 52.85, 23.40, 16.28, 13.17),
    ("2024-04-20", "2025-12-31",  93.17, 52.58, 23.13, 16.28, 13.17),
    ("2024-02-20", "2025-12-31",  93.17, 52.12, 22.67, 16.28, 13.17),
    ("2024-01-20", "2025-12-31",  93.17, 51.98, 22.53, 16.28, 13.17),
    ("2024-01-01", "2025-12-31",  93.17, 52.87, 23.42, 16.28, 13.17),
    ("2023-12-20", "2025-12-31",  93.17, 54.08, 24.63, 16.28, 13.17),
    ("2023-11-20", "2025-12-31",  93.17, 53.97, 24.52, 16.28, 13.17),
]


# ===========================================================================
# ITENS NOVOS (14/jul-18/jul) - minerados dos videos F-LINK IMG_0492-0522
# (31 videos: IMG_0492 a IMG_0522). Mesma disciplina de leitura frame-a-frame
# (ffmpeg fps=1~2, contact sheets) e mesma validacao frete+MO+MD=tarifa (tol.
# 0,05) dos itens originais. IMG_0498/0499 confirmaram o item 16967 ja
# existente (mesmos valores) e IMG_0500 confirmou o item 7958 ja existente -
# nao alterados, nao repetidos aqui.
#
# Os videos mostram DOIS nomes de cliente na mesma tela F-LINK: "GERDAU
# ACOMINAS S/A" e "GERDAU ACOS LONGOS S.A." (duas razoes sociais do grupo).
# Cada FLUXOS[item] novo abaixo carrega "razao_social" com o nome exibido no
# cabecalho do video correspondente.
#
# Fluxos intermodais (duas ferrovias, ex. EFVM+FCA): o campo frete_rs_t
# agregado no DADOS = soma dos fretes das duas ferrovias (ou, no caso dos
# itens 9685/9686, tambem inclui o servico "TRANSBORDO ORIGEM"); manobra_
# origem/destino mantem os valores lidos por servico. A soma ainda valida
# frete+MO+MD=tarifa.
#
# Confianca/omissoes: ver notas linha-a-linha no changelog do commit / no
# arquivo de trabalho desta mineracao. Resumo por item abaixo em comentario.
# Padrao observado: varios pares de itens (rotas/produto/contrato identicos,
# so o item e por vezes a razao social mudam) tem tarifas IDENTICAS entre si
# nas vigencias comuns - isso foi cross-validado entre videos independentes
# (ex. 40409 vs 9687; 7967 vs 40372 vs 7961; 40368 vs 9266; 10554 vs 10555;
# 40411 vs 19072 vs 19087) e tratado como confirmacao, nao coincidencia.
# ===========================================================================

FLUXOS.update({
    40409: dict(contrato="C_2023_7", origem="EDV", origem_nome="DIVINOPOLIS",
                destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0492.MOV"),
    7967: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
               destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOMINAS S/A", video="IMG_0493.MOV"),
    40370: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
                destino="VMR", destino_nome="MARIO CARVALHO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0494.MOV"),
    40368: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
                destino="VPN", destino_nome="PEDRO NOLASCO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0495.MOV"),
    9687: dict(contrato="C_2023_7", origem="EDV", origem_nome="DIVINOPOLIS",
               destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOS LONGOS S.A.", video="IMG_0496.MOV"),
    9685: dict(contrato="C_2023_7", origem="ECE", origem_nome="CAPITAO EDUARDO",
               destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOS LONGOS S.A.", video="IMG_0497.MOV"),
    17023: dict(contrato="C_2023_7", origem="EPI", origem_nome="PARQUE INDUSTRIAL",
                destino="VPN", destino_nome="PEDRO NOLASCO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0501.MOV"),
    19072: dict(contrato="C_2023_7", origem="EPI", origem_nome="PARQUE INDUSTRIAL",
                destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOS LONGOS S.A.", video="IMG_0502.MOV"),
    40411: dict(contrato="C_2023_7", origem="EPI", origem_nome="PARQUE INDUSTRIAL",
                destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0503.MOV"),
    40372: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
                destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0504.MOV"),
    7488: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
               destino="VJM", destino_nome="JOAO MONLEVADE", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOMINAS S/A", video="IMG_0505.MOV"),
    17021: dict(contrato="C_2023_7", origem="EEL", origem_nome="ELDORADO",
                destino="VPN", destino_nome="PEDRO NOLASCO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0506.MOV"),
    7948: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
               destino="VGV", destino_nome="GOVERNADOR VALADARES", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOMINAS S/A", video="IMG_0507.MOV"),
    7489: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
               destino="VPN", destino_nome="PEDRO NOLASCO", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOMINAS S/A", video="IMG_0508.MOV"),
    7961: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
               destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOMINAS S/A", video="IMG_0509.MOV"),
    16734: dict(contrato="C_2023_7", origem="EEL", origem_nome="ELDORADO",
                destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0510.MOV"),
    40075: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
                destino="EPI", destino_nome="PARQUE INDUSTRIAL", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0511.MOV"),
    10554: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0512.MOV"),
    9686: dict(contrato="C_2023_7", origem="ECE", origem_nome="CAPITAO EDUARDO",
               destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
               razao_social="GERDAU ACOS LONGOS S.A.", video="IMG_0513.MOV"),
    40636: dict(contrato="C_2023_7", origem="EHF", origem_nome="HORTO FLORESTAL",
                destino="VTU", destino_nome="TUBARAO", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0514.MOV"),
    39785: dict(contrato="ACS_2025_15", origem="VPN", origem_nome="PEDRO NOLASCO",
                destino="VOB", destino_nome="OURO BRANCO", produto="MINERIO FERRO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0516.MOV"),
    40366: dict(contrato="C_2023_8", origem="EVP", origem_nome="VESPASIANO",
                destino="VOB", destino_nome="OURO BRANCO", produto="COQUE PETROLEO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0517.MOV"),
    17653: dict(contrato="C_2023_8", origem="VOB", origem_nome="OURO BRANCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA", produto="COQUE GROSSO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0518.MOV"),
    9266: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
               destino="VPN", destino_nome="PEDRO NOLASCO", produto="FIO MAQUINA",
               razao_social="GERDAU ACOMINAS S/A", video="IMG_0519.MOV"),
    10555: dict(contrato="C_2023_7", origem="VOB", origem_nome="OURO BRANCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA", produto="FIO MAQUINA",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0520.MOV"),
    19087: dict(contrato="C_2023_7", origem="EPI", origem_nome="PARQUE INDUSTRIAL",
                destino="VTU", destino_nome="TUBARAO", produto="FIO MAQUINA",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0521.MOV"),
    16187: dict(contrato="C_2023_7", origem="VPN", origem_nome="PEDRO NOLASCO",
                destino="VJM", destino_nome="JOAO MONLEVADE", produto="PRO SIDERURGICO",
                razao_social="GERDAU ACOMINAS S/A", video="IMG_0522.MOV"),
})

# --- 40409 | C_2023_7 | EDV->VTU | PRO SIDERURGICO | ACOMINAS | IMG_0492.MOV ---
# Intermodal (EFVM+FCA). 12 vigencias lidas e auto-validadas (soma dos servicos
# lidos = tarifa). Cross-validado 100% com 9687 (mesma rota/contrato, AÇOS
# LONGOS, IMG_0496). Resto do video (< 2025-08) descartado por scroll-blur.
DADOS[40409] = [
    ("2026-07-20", "2026-12-31", 185.49, 174.54, 148.24, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 185.49, 174.45, 148.15, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 185.49, 174.81, 148.51, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 185.49, 174.96, 148.66, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 185.49, 175.72, 149.42, 13.72, 12.58),
    ("2026-02-20", "2026-12-31", 185.49, 176.22, 149.92, 13.72, 12.58),
    ("2026-01-20", "2026-01-31", 185.49, 175.84, 149.54, 13.72, 12.58),
    ("2025-12-20", "2026-01-31", 185.49, 176.91, 150.61, 13.72, 12.58),
    ("2025-11-20", "2025-12-31", 185.49, 176.41, 150.11, 13.72, 12.58),
    ("2025-10-20", "2025-12-31", 180.09, 176.52, 150.22, 13.72, 12.58),
    ("2025-09-20", "2025-12-31", 180.09, 176.51, 150.21, 13.72, 12.58),
    ("2025-08-20", "2025-12-31", 180.09, 175.87, 149.57, 13.72, 12.58),
]

# --- 7967 | C_2023_7 | VOB->VTU | PRO SIDERURGICO | ACOMINAS | IMG_0493.MOV ---
# Single ferrovia EFVM. Apenas 5 vigencias lidas com confianca (video com
# muitas linhas historicas nao lidas de forma limpa nesta passada). Cross-
# validado com 40372 (IMG_0504) e 7961 (IMG_0509) - mesma rota/contrato,
# valores identicos.
DADOS[7967] = [
    ("2026-07-20", "2026-12-31", 87.26, 111.49, 85.19, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 87.26, 111.42, 85.12, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 87.26, 111.65, 85.35, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 87.26, 111.74, 85.44, 13.72, 12.58),
    ("2026-02-20", "2026-12-31", 87.26, 112.54, 86.24, 13.72, 12.58),
]

# --- 40370 | C_2023_7 | VOB->VMR | PRO SIDERURGICO | ACOMINAS | IMG_0494.MOV ---
# Single ferrovia EFVM, manobra origem/destino ambas 13,72 constante.
DADOS[40370] = [
    ("2026-07-20", "2026-12-31", 51.14, 72.93, 45.49, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 51.14, 72.89, 45.45, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 51.14, 73.04, 45.60, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 51.14, 73.10, 45.66, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 51.14, 73.42, 45.98, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 51.14, 73.63, 46.19, 13.72, 13.72),
    ("2026-01-20", "2026-12-31", 51.14, 73.47, 46.03, 13.72, 13.72),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 51.14, 73.38, 45.94, 13.72, 13.72),  # 2o cadastro
]

# --- 40368 | C_2023_7 | VOB->VPN | PRO SIDERURGICO | ACOMINAS | IMG_0495.MOV ---
# Single ferrovia EFVM. Manobra sobe de 13,72/13,72 para 16,00/16,00 em
# 20/01/2026 (padrao de reajuste de manobra ja visto noutros itens C_2023_7).
# Cross-validado com 9266 (IMG_0519), mesma rota, valores identicos.
DADOS[40368] = [
    ("2026-07-20", "2026-12-31", 87.51, 111.02, 83.58, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 87.51, 110.95, 83.51, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 87.51, 111.18, 83.74, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 87.51, 111.27, 83.83, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 87.51, 111.75, 84.31, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 87.51, 112.07, 84.63, 13.72, 13.72),
    ("2026-01-20", "2026-12-31", 87.51, 111.83, 79.83, 16.00, 16.00),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 87.51, 111.63, 79.63, 16.00, 16.00),  # 2o cadastro
]

# --- 9687 | C_2023_7 | EDV->VTU | PRO SIDERURGICO | ACOS LONGOS | IMG_0496.MOV ---
# Intermodal (EFVM+FCA). Cross-validado 100% com 40409 (mesma rota/contrato,
# ACOMINAS, IMG_0492) - valores identicos em todas as vigencias comuns.
DADOS[9687] = [
    ("2026-07-20", "2026-12-31", 185.49, 174.54, 148.24, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 185.49, 174.45, 148.15, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 185.49, 174.81, 148.51, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 185.49, 174.96, 148.66, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 185.49, 175.72, 149.42, 13.72, 12.58),
    ("2026-02-20", "2026-12-31", 185.49, 176.22, 149.92, 13.72, 12.58),
    ("2026-01-20", "2026-01-31", 185.49, 175.84, 149.54, 13.72, 12.58),
    ("2025-12-20", "2026-01-31", 185.49, 176.91, 150.61, 13.72, 12.58),  # 1o cadastro
    ("2025-12-20", "2025-12-31", 185.49, 176.94, 150.64, 13.72, 12.58),  # 2o cadastro
    ("2025-11-20", "2025-12-31", 185.49, 176.41, 150.11, 13.72, 12.58),
    ("2025-10-20", "2025-12-31", 180.09, 176.52, 150.22, 13.72, 12.58),
]

# --- 9685 | C_2023_7 | ECE->VTU | PRO SIDERURGICO | ACOS LONGOS | IMG_0497.MOV ---
# 5 sub-servicos: TRANSBORDO ORIGEM(FCA) + FRETE(FCA) + FRETE(EFVM) +
# MANOBRA ORIGEM(FCA) + MANOBRA DESTINO(EFVM). frete_rs_t agregado = soma dos
# 3 primeiros servicos (transbordo + 2 fretes); manobra_origem/destino como
# lidos. Soma valida frete+MO+MD=tarifa.
DADOS[9685] = [
    ("2026-07-20", "2026-12-31", 158.25, 131.49, 106.33, 12.58, 12.58),
    ("2026-06-20", "2026-12-31", 158.25, 131.41, 106.25, 12.58, 12.58),
    ("2026-05-20", "2026-12-31", 158.25, 131.69, 106.53, 12.58, 12.58),
    ("2026-04-20", "2026-12-31", 158.25, 131.79, 106.63, 12.58, 12.58),
    ("2026-03-20", "2026-12-31", 158.25, 132.36, 107.20, 12.58, 12.58),
    ("2026-02-20", "2026-12-31", 158.25, 132.74, 107.58, 12.58, 12.58),
]

# --- 17023 | C_2023_7 | EPI->VPN | PRO SIDERURGICO | ACOMINAS | IMG_0501.MOV ---
# Intermodal (EFVM+FCA), manobras ambas 13,72 constante nas vigencias lidas.
DADOS[17023] = [
    ("2026-07-20", "2026-12-31", 163.06, 119.25, 91.81, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 163.06, 119.18, 91.74, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 163.06, 119.43, 91.99, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 163.06, 119.53, 92.09, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 163.06, 120.05, 92.61, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 163.06, 120.39, 92.95, 13.72, 13.72),
    ("2026-01-20", "2026-12-31", 163.06, 120.09, 92.65, 13.72, 13.72),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 163.06, 119.94, 92.50, 13.72, 13.72),  # 2o cadastro
]

# --- 19072 | C_2023_7 | EPI->VTU | PRO SIDERURGICO | ACOS LONGOS | IMG_0502.MOV ---
# Leitura do numero do item no video ambigua entre "10072"/"19072" (digitos
# iniciais pouco legiveis); adotado 19072 por ser o unico coerente com a
# lista de itens esperados. Intermodal (EFVM+FCA). Valores identicos ao
# item 40411 (mesma rota/contrato, ACOMINAS, IMG_0503) - confianca
# moderada-alta por cross-check de padrao (varios pares ja confirmados 1:1
# neste lote).
DADOS[19072] = [
    ("2026-07-20", "2026-12-31", 162.53, 119.19, 92.89, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 162.53, 119.12, 92.82, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 162.53, 119.37, 93.07, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 162.53, 119.47, 93.17, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 162.53, 119.99, 93.69, 13.72, 12.58),
    ("2026-02-20", "2026-12-31", 162.53, 120.33, 94.03, 13.72, 12.58),
    ("2026-01-20", "2026-12-31", 162.53, 120.07, 93.77, 13.72, 12.58),
]

# --- 40411 | C_2023_7 | EPI->VTU | PRO SIDERURGICO | ACOMINAS | IMG_0503.MOV ---
# Intermodal (EFVM+FCA). Cross-validado com 19072 e 19087 (mesma rota).
DADOS[40411] = [
    ("2026-07-20", "2026-12-31", 162.53, 119.19, 92.89, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 162.53, 119.12, 92.82, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 162.53, 119.37, 93.07, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 162.53, 119.47, 93.17, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 162.53, 119.99, 93.69, 13.72, 12.58),
    ("2026-02-20", "2026-12-31", 162.53, 120.33, 94.03, 13.72, 12.58),
    ("2026-01-20", "2026-12-31", 162.53, 120.07, 93.77, 13.72, 12.58),
]

# --- 40372 | C_2023_7 | VOB->VTU | PRO SIDERURGICO | ACOMINAS | IMG_0504.MOV ---
# Video dominado por estado "Carregando" (nao renderizado) na maior parte dos
# frames -> apenas 2 vigencias lidas com confianca. Valores identicos a 7967
# (mesma rota/contrato/razao social) - cross-validado.
DADOS[40372] = [
    ("2026-07-20", "2026-12-31", 87.26, 111.49, 85.19, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 87.26, 111.42, 85.12, 13.72, 12.58),
]

# --- 7488 | C_2023_7 | VOB->VJM | PRO SIDERURGICO | ACOMINAS | IMG_0505.MOV ---
# Single ferrovia EFVM, manobras ambas 13,72 constante.
DADOS[7488] = [
    ("2026-07-20", "2026-12-31", 44.51, 57.00, 29.56, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 44.51, 56.97, 29.53, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 44.51, 57.09, 29.65, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 44.51, 57.14, 29.70, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 44.51, 57.39, 29.95, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 44.51, 57.55, 30.11, 13.72, 13.72),
    ("2026-01-20", "2026-12-31", 44.51, 57.42, 29.98, 13.72, 13.72),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 44.51, 57.35, 29.91, 13.72, 13.72),  # 2o cadastro
]

# --- 17021 | C_2023_7 | EEL->VPN | PRO SIDERURGICO | ACOMINAS | IMG_0506.MOV ---
# Video dominado por estado "Carregando" -> apenas 1 vigencia lida com
# confianca (intermodal EFVM+FCA).
DADOS[17021] = [
    ("2026-07-20", "2026-12-31", 162.65, 110.25, 82.81, 13.72, 13.72),
]

# --- 7948 | C_2023_7 | VOB->VGV | PRO SIDERURGICO | ACOMINAS | IMG_0507.MOV ---
# Single ferrovia EFVM, manobra origem 13,72 / manobra destino 13,83
# constantes nas vigencias lidas.
DADOS[7948] = [
    ("2026-07-20", "2026-12-31", 61.32, 83.68, 56.13, 13.72, 13.83),
    ("2026-06-20", "2026-12-31", 61.32, 83.63, 56.08, 13.72, 13.83),
    ("2026-05-20", "2026-12-31", 61.32, 83.80, 56.25, 13.72, 13.83),
    ("2026-04-20", "2026-12-31", 61.32, 83.87, 56.32, 13.72, 13.83),
    ("2026-03-20", "2026-12-31", 61.32, 84.23, 56.68, 13.72, 13.83),
    ("2026-02-20", "2026-12-31", 61.32, 84.47, 56.92, 13.72, 13.83),
    ("2026-01-20", "2026-12-31", 61.32, 84.29, 56.74, 13.72, 13.83),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 61.32, 84.29, 56.74, 13.72, 13.83),  # 2o cadastro (mesma tarifa)
]

# --- 7489 | C_2023_7 | VOB->VPN | PRO SIDERURGICO | ACOMINAS | IMG_0508.MOV ---
# Video inteiro renderizado em estado "Carregando" (placeholders) em TODOS os
# frames extraidos -> nenhum valor numerico pode ser lido com confianca.
# Apenas cabecalho (item/contrato/rota/produto) confirmado no FLUXOS acima.
DADOS[7489] = []

# --- 7961 | C_2023_7 | VOB->VTU | PRO SIDERURGICO | ACOMINAS | IMG_0509.MOV ---
# Single ferrovia EFVM. Mesma rota/contrato/razao social de 7967 e 40372 -
# valores identicos, cross-validado.
DADOS[7961] = [
    ("2026-07-20", "2026-12-31", 87.26, 111.49, 85.19, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 87.26, 111.42, 85.12, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 87.26, 111.65, 85.35, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 87.26, 111.74, 85.44, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 87.26, 112.22, 85.92, 13.72, 12.58),
]

# --- 16734 | C_2023_7 | EEL->VTU | PRO SIDERURGICO | ACOMINAS | IMG_0510.MOV ---
# Intermodal (EFVM+FCA). frete_rs_t agregado = FRETE FCA + FRETE EFVM.
DADOS[16734] = [
    ("2026-07-20", "2026-12-31", 162.02, 119.33, 93.03, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 162.02, 119.28, 92.98, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 162.02, 119.61, 93.31, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 162.02, 120.13, 93.83, 13.72, 12.58),
    ("2026-02-20", "2026-12-31", 162.02, 120.47, 94.17, 13.72, 12.58),
]

# --- 40075 | C_2023_7 (vig. contrato 08/07/2025-31/12/2026) | VOB->EPI |
#     PRO SIDERURGICO | ACOMINAS | IMG_0511.MOV ---
# Intermodal (FCA+EFVM). Apenas 2 vigencias renderizadas com clareza no
# video (resto ficou repetindo os mesmos 2 frames / blur).
DADOS[40075] = [
    ("2026-07-20", "2026-12-31", 50.21, 76.37, 46.37, 13.72, 16.28),
    ("2026-06-20", "2026-12-31", 50.21, 76.32, 46.32, 13.72, 16.28),
]

# --- 10554 | C_2023_7 | VOB->VIC | PRO SIDERURGICO | ACOMINAS | IMG_0512.MOV ---
# Single ferrovia EFVM, manobras ambas 13,72 constante. Cross-validado com
# 10555 (IMG_0520), mesma rota, valores identicos.
DADOS[10554] = [
    ("2026-07-20", "2026-12-31", 52.37, 73.32, 45.88, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 52.37, 73.28, 45.84, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 52.37, 73.43, 45.99, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 52.37, 73.49, 46.05, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 52.37, 73.81, 46.37, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 52.37, 74.02, 46.58, 13.72, 13.72),
    ("2026-01-20", "2026-12-31", 52.37, 73.88, 46.44, 13.72, 13.72),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 52.37, 73.76, 46.32, 13.72, 13.72),  # 2o cadastro
    ("2026-01-01", "2026-01-19", 52.37, 73.76, 46.32, 13.72, 13.72),
    ("2025-12-20", "2026-01-31", 50.03, 74.31, 46.87, 13.72, 13.72),
]

# --- 9686 | C_2023_7 | ECE->VTU | PRO SIDERURGICO | ACOS LONGOS | IMG_0513.MOV ---
# Mesma estrutura de 5 sub-servicos de 9685 (TRANSBORDO ORIGEM + FRETE EFVM +
# FRETE FCA + MANOBRA ORIGEM + MANOBRA DESTINO); frete_rs_t agregado = soma
# dos 3 primeiros.
DADOS[9686] = [
    ("2026-07-20", "2026-12-31", 158.25, 120.11, 94.95, 12.58, 12.58),
    ("2026-06-20", "2026-12-31", 158.25, 120.04, 94.88, 12.58, 12.58),
    ("2026-05-20", "2026-12-31", 158.25, 120.29, 95.13, 12.58, 12.58),
    ("2026-04-20", "2026-12-31", 158.25, 120.39, 95.23, 12.58, 12.58),
    ("2026-03-20", "2026-12-31", 158.25, 120.91, 95.75, 12.58, 12.58),
    ("2026-02-20", "2026-12-31", 158.25, 121.25, 96.09, 12.58, 12.58),
    ("2026-01-20", "2026-12-31", 158.25, 120.99, 95.83, 12.58, 12.58),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 158.25, 120.94, 95.78, 12.58, 12.58),  # 2o cadastro
]

# --- 40636 | C_2023_7 (vig. contrato 27/10/2025-31/12/2026) | EHF->VTU |
#     PRO SIDERURGICO | ACOMINAS | IMG_0514.MOV (confirmado por IMG_0515) ---
# Intermodal (FCA+EFVM), manobra_origem FCA = 0,00 constante nas vigencias
# lidas. Vigencias de 2026-01 em diante (video IMG_0515) mostraram a manobra
# origem mudando de valor, mas nao foi possivel decompor com confianca ->
# omitidas.
DADOS[40636] = [
    ("2026-07-20", "2026-12-31", 158.96, 129.76, 117.18, 0.00, 12.58),
    ("2026-06-20", "2026-12-31", 158.96, 129.68, 117.10, 0.00, 12.58),
    ("2026-05-20", "2026-12-31", 158.96, 129.95, 117.37, 0.00, 12.58),
    ("2026-04-20", "2026-12-31", 158.96, 130.06, 117.48, 0.00, 12.58),
    ("2026-03-20", "2026-12-31", 158.96, 130.62, 118.03, 0.00, 12.58),
    ("2026-02-20", "2026-12-31", 158.96, 130.69, 118.11, 0.00, 12.58),
]

# --- 39785 | ACS_2025_15 (contrato ENCERRADO, vig. 10/02/2025-09/07/2025) |
#     VPN->VOB | MINERIO FERRO | ACOMINAS | IMG_0516.MOV ---
# Produto e contrato diferentes de todos os demais itens (contrato ja
# encerrado). Single ferrovia EFVM. Existe apenas 1 vigencia (o contrato
# nunca foi reajustado antes de encerrar).
DADOS[39785] = [
    ("2025-02-10", "2025-07-09", 78.75, 124.20, 78.68, 31.95, 13.57),
]

# --- 40366 | C_2023_8 | EVP->VOB | COQUE PETROLEO | ACOMINAS | IMG_0517.MOV ---
# Mesma rota/contrato/produto do item 17829 ja existente no script (fluxo
# intermodal FCA+EFVM, manobra_origem FCA=16,28 e manobra_destino EFVM=13,17
# constantes). As 2 vigencias lidas neste video batem EXATAMENTE com as ja
# registradas em DADOS[17829] -> tratado como par duplicado da mesma serie;
# demais vigencias nao replicadas aqui (ja cobertas em DADOS[17829]).
DADOS[40366] = [
    ("2026-07-20", "2026-12-31", 100.06, 55.00, 25.55, 16.28, 13.17),
    ("2026-06-20", "2026-12-31", 100.06, 54.97, 25.52, 16.28, 13.17),
]

# --- 17653 | C_2023_8 | VOB->VIC | COQUE GROSSO | ACOMINAS | IMG_0518.MOV ---
# Single ferrovia EFVM, manobras ambas 25,00 constante (padrao C_2023_8).
DADOS[17653] = [
    ("2026-07-20", "2026-12-31", 63.34, 86.67, 36.67, 25.00, 25.00),
    ("2026-06-20", "2026-12-31", 63.34, 86.65, 36.65, 25.00, 25.00),
    ("2026-05-20", "2026-12-31", 63.34, 86.71, 36.71, 25.00, 25.00),
    ("2026-04-20", "2026-12-31", 63.34, 86.74, 36.74, 25.00, 25.00),
    ("2026-03-20", "2026-12-31", 63.34, 87.08, 37.08, 25.00, 25.00),
    ("2026-02-20", "2026-12-31", 63.34, 86.98, 36.98, 25.00, 25.00),
    ("2026-01-20", "2026-12-31", 63.34, 88.00, 38.00, 25.00, 25.00),  # 1o cadastro
    ("2026-01-20", "2026-01-31", 63.34, 88.00, 38.00, 25.00, 25.00),  # 2o cadastro
    ("2026-01-01", "2026-01-19", 63.34, 87.89, 37.89, 25.00, 25.00),
    ("2025-12-20", "2026-01-31", 60.51, 88.54, 38.54, 25.00, 25.00),
    ("2025-12-20", "2025-12-31", 60.51, 88.29, 38.29, 25.00, 25.00),  # 2o cadastro
]

# --- 9266 | C_2023_7 | VOB->VPN | FIO MAQUINA | ACOMINAS | IMG_0519.MOV ---
# Single ferrovia EFVM. Produto lido na tela como FIO MAQUINA (mesma rota do
# item 40368, que aparece como PRO SIDERURGICO) - valores identicos entre os
# dois, cross-validado; mantido o produto tal como lido em cada video (nao
# corrigido, possivel duplicidade/erro de cadastro no F-LINK).
DADOS[9266] = [
    ("2026-07-20", "2026-12-31", 87.51, 111.02, 83.58, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 87.51, 110.95, 83.51, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 87.51, 111.18, 83.74, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 87.51, 111.27, 83.83, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 87.51, 111.75, 84.31, 13.72, 13.72),
]

# --- 10555 | C_2023_7 | VOB->VIC | FIO MAQUINA | ACOMINAS | IMG_0520.MOV ---
# Single ferrovia EFVM. Valores identicos ao item 10554 (mesma rota, produto
# PRO SIDERURGICO la) - cross-validado, mesma observacao do 9266 acima.
DADOS[10555] = [
    ("2026-07-20", "2026-12-31", 52.37, 73.32, 45.88, 13.72, 13.72),
    ("2026-06-20", "2026-12-31", 52.37, 73.28, 45.84, 13.72, 13.72),
    ("2026-05-20", "2026-12-31", 52.37, 73.43, 45.99, 13.72, 13.72),
    ("2026-04-20", "2026-12-31", 52.37, 73.49, 46.05, 13.72, 13.72),
    ("2026-03-20", "2026-12-31", 52.37, 73.81, 46.37, 13.72, 13.72),
    ("2026-02-20", "2026-12-31", 52.37, 74.02, 46.58, 13.72, 13.72),
]

# --- 19087 | C_2023_7 | EPI->VTU | FIO MAQUINA | ACOMINAS | IMG_0521.MOV ---
# Intermodal (EFVM+FCA). Valores identicos ao item 40411 (mesma rota, produto
# PRO SIDERURGICO la) - cross-validado, mesma observacao do 9266 acima.
DADOS[19087] = [
    ("2026-07-20", "2026-12-31", 162.53, 119.25, 92.95, 13.72, 12.58),
    ("2026-06-20", "2026-12-31", 162.53, 119.12, 92.82, 13.72, 12.58),
    ("2026-05-20", "2026-12-31", 162.53, 119.37, 93.07, 13.72, 12.58),
    ("2026-04-20", "2026-12-31", 162.53, 119.47, 93.17, 13.72, 12.58),
    ("2026-03-20", "2026-12-31", 162.53, 119.99, 93.69, 13.72, 12.58),
]

# --- 16187 | C_2023_7 | VPN->VJM | PRO SIDERURGICO | ACOMINAS | IMG_0522.MOV ---
# Single ferrovia EFVM + servico extra "MANOBRA CONEXAO CHEIO" = 0,00
# constante nas linhas lidas (nao entra no schema de 3 campos, ja que soma
# zero e nao afeta a validacao frete+MO+MD=tarifa). Historico anterior a
# 2025-12 nao lido com fidelidade suficiente.
DADOS[16187] = [
    ("2026-06-20", "2026-12-31", 76.17, 109.59, 67.09, 21.25, 21.25),
    ("2026-05-20", "2026-12-31", 76.17, 109.82, 67.22, 21.30, 21.30),
    ("2026-04-20", "2026-12-31", 76.17, 109.91, 67.27, 21.32, 21.32),
    ("2026-03-20", "2026-12-31", 76.17, 110.38, 67.56, 21.41, 21.41),
    ("2026-02-20", "2026-02-28", 72.78, 108.26, 66.26, 21.00, 21.00),
    ("2025-12-22", "2026-01-31", 72.78, 108.26, 66.26, 21.00, 21.00),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + (MD ou 0) == tarifa_contrato (tolerancia 0,05)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            vi, vf, tr, tarifa, frete, mo, md = ln
            soma = (frete or 0) + (mo or 0) + (md or 0)
            if abs(soma - tarifa) > 0.05:
                problemas.append(
                    f"item {item} vig {vi}: soma servicos {soma:.2f} "
                    f"!= tarifa_contrato {tarifa:.2f}"
                )
    return problemas


# MÁXIMA FIDELIDADE (14/jul): substitui as versões DERIVADAS/ESPELHADAS de 9612/9613/9646 por
# leitura DIRETA vigência-a-vigência, serviço-a-serviço (ver gerdau_fidelidade_9612_9613_9646.py).
# A derivação de 9612 (Antracito) e 9613 (Coque Grosso) estava quase certa (pequenas correções +
# vigências que faltavam); o 9646 (Fio Máquina) tinha ERRO REAL na manobra de fim de 2024
# (12,58/13,72, não o espelhado 25/25). Todas as 121 linhas validam (soma = tarifa).
from gerdau_fidelidade_9612_9613_9646 import DADOS_9612, DADOS_9613, DADOS_9646
DADOS[9612] = DADOS_9612
DADOS[9613] = DADOS_9613
DADOS[9646] = DADOS_9646


def main():
    problemas = validar(DADOS)
    if problemas:
        print("INCONSISTENCIAS DE SOMA (revisar antes de gravar):")
        for p in problemas:
            print("  -", p)
        raise SystemExit("Abortado: corrija as inconsistencias acima.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS gerdau_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE gerdau_precos_contratuais (
            item_ferroviario     INTEGER,
            contrato             TEXT,
            origem               TEXT,
            origem_nome          TEXT,
            destino              TEXT,
            destino_nome         TEXT,
            produto              TEXT,
            razao_social         TEXT,
            vigencia_inicial     TEXT,
            vigencia_final       TEXT,
            valor_tr_antt        REAL,
            tarifa_contrato      REAL,
            frete_rs_t           REAL,
            manobra_origem_rs_t  REAL,
            manobra_destino_rs_t REAL,
            fonte                TEXT
        )
        """
    )
    # razao_social: campo novo (mineracao IMG_0492-0522). Os 7 itens originais
    # (IMG_0239-0246) nao tinham essa distincao registrada nos comentarios;
    # default para "GERDAU ACOMINAS S/A" (razao social predominante no lote
    # original) quando o FLUXOS do item nao define o campo explicitamente.
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        razao_social = meta.get("razao_social", "GERDAU ACOMINAS S/A")
        for (vi, vf, tr, tarifa, frete, mo, md) in linhas:
            cur.execute(
                """INSERT INTO gerdau_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 razao_social, vi, vf, tr, tarifa, frete, mo, md, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM gerdau_precos_contratuais").fetchone()[0]
    print(f"gerdau_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
