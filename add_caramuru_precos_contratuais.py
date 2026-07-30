#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_caramuru_precos_contratuais.py

Cria/recria a tabela `caramuru_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos 2 fluxos
ferroviarios da CARAMURU ALIMENTOS SA, minerado dos videos de tela do F-LINK
(flink.vli.digital, tela "Item Ferroviario > Preco"), um video por fluxo:

  - item 40501 | MILHO | ETB (Term Integrador Araguari) -> VTU (Tubarao)
    | contrato C_2026_14 | video IMG_0530.MOV (17,5s)
  - item 10763 | FARELO DE SOJA | EPO (Ipameri) -> ISN (Santos)
    | contrato C_2026_14 | video IMG_0531.MOV (34,2s)

Diferenca de schema em relacao ao script de referencia (GERDAU): os itens
GERDAU so tinham 2 servicos fixos (manobra origem/destino). Os itens da
CARAMURU tem servicos variaveis por vigencia e por ferrovia (o item 40501 e
intermodal FCA+EFVM com Frete duplo e Transbordo Origem; o item 10763 tem
Direito de Passagem em 2 ferrovias distintas - MRS e ALLMP/ALLMN - alem de
Utilizacao de Patio/MRS, que e sempre R$0,00 nas vigencias mineradas). Por
isso, ao inves da tupla fixa da GERDAU, cada vigencia aqui e um dict com uma
sub-chave "servicos" = {"NOME_SERVICO|FERROVIA": valor_rs_t, ...}, que
preserva a granularidade por ferrovia vista na tela.

Disciplina de mineracao (mesma dos lotes GERDAU): frames extraidos com ffmpeg
(fps=10, alguns trechos fps=25 para resolver ambiguidades de scroll), lidos
em sequencia, cada vigencia validada por soma dos servicos = Tarifa
Contrato/Faturamento (tolerancia R$0,05). Todas as ~43 vigencias abaixo
bateram exato (diferenca R$0,00) na soma dos servicos lidos.

Gaps conhecidos (nao sao omissao de leitura - o F-LINK simplesmente nao tem
vigencia cadastrada nesse intervalo, confirmado olhando os cadastros
adjacentes frame a frame): item 40501 nao tem vigencia 01/01/2026-31/01/2026
(pula de 01/02/2026-15/02/2026 direto para 01/12/2025-31/12/2025); item 10763
nao tem vigencia de janeiro/2025 (pula de 01/02/2025-28/02/2025 direto para
01/12/2024-31/12/2024).

Re-cadastros duplicados (mesma vigencia, mais de uma data de cadastro, por
vezes com tarifa diferente): mantidos como linhas separadas, igual ao padrao
GERDAU, EXCETO cadastros idênticos byte-a-byte (mesmos valores, apenas
timestamp de cadastro repetido em segundos - tratados como um unico registro
re-salvo, nao como reajuste real).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente (script connect_caramuru_precos.py,
a ser criado separadamente seguindo o padrao de connect_gerdau_precos.py).

Fonte: F-LINK Item Ferroviario > Preco (IMG_0530.MOV, IMG_0531.MOV) -
historico de reajuste CARAMURU ALIMENTOS SA.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Item Ferroviario > Preco (IMG_0530.MOV, IMG_0531.MOV) - historico de reajuste CARAMURU ALIMENTOS SA"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    40501: dict(
        cliente="CARAMURU ALIMENTOS SA",
        contrato="C_2026_14",
        vigencia_contrato_ini="2024-01-01",
        vigencia_contrato_fim="2030-12-31",
        origem="ETB", origem_nome="TERM INTEGRADOR ARAGUARI",
        destino="VTU", destino_nome="TUBARAO",
        produto="MILHO",
        video="IMG_0530.MOV",
    ),
    10763: dict(
        cliente="CARAMURU ALIMENTOS SA",
        contrato="C_2026_14",
        vigencia_contrato_ini="2018-01-24",
        vigencia_contrato_fim="2030-12-31",
        origem="EPO", origem_nome="IPAMERI",
        destino="ISN", destino_nome="SANTOS",
        produto="FARELO DE SOJA",
        video="IMG_0531.MOV",
    ),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada elemento de DADOS[item] e um dict:
#   {
#     "vig_ini": "YYYY-MM-DD", "vig_fim": "YYYY-MM-DD",
#     "tr_antt": float, "tarifa_contrato": float, "tarifa_faturamento": float,
#     "servicos": {"NOME_SERVICO|FERROVIA": valor_rs_t, ...},
#     "obs": "opcional, ex. numero do cadastro quando ha re-cadastro duplicado",
#   }
# Valores em R$/t. Datas em YYYY-MM-DD.
# ---------------------------------------------------------------------------

DADOS = {}

# ===========================================================================
# 40501 | C_2026_14 | ETB->VTU | MILHO | IMG_0530.MOV
# Intermodal FCA+EFVM. 13 linhas = 11 vigencias distintas (2 vigencias com
# re-cadastro duplicado: 01-15/02/2026 e 01-30/09/2025). GAP confirmado: sem
# vigencia de janeiro/2026 (pula de 01-15/02/2026 para 01/12/2025-31/12/2025).
# Todas as 13 linhas validadas: soma dos servicos = Tarifa Contrato/
# Faturamento, diferenca R$0,00 em todas.
# ===========================================================================
DADOS[40501] = [
    dict(vig_ini="2026-07-01", vig_fim="2026-07-31", tr_antt=260.90,
         tarifa_contrato=182.48, tarifa_faturamento=182.48,
         servicos={"FRETE|FCA": 71.45, "FRETE|EFVM": 59.53,
                   "MANOBRA DESTINO|EFVM": 21.90, "MANOBRA ORIGEM|FCA": 14.60,
                   "TRANSBORDO ORIGEM|FCA": 15.00}),
    dict(vig_ini="2026-06-01", vig_fim="2026-06-30", tr_antt=260.90,
         tarifa_contrato=178.41, tarifa_faturamento=178.41,
         servicos={"FRETE|FCA": 69.68, "FRETE|EFVM": 58.05,
                   "MANOBRA DESTINO|EFVM": 21.41, "MANOBRA ORIGEM|FCA": 14.27,
                   "TRANSBORDO ORIGEM|FCA": 15.00}),
    dict(vig_ini="2026-05-01", vig_fim="2026-05-31", tr_antt=260.90,
         tarifa_contrato=178.88, tarifa_faturamento=178.88,
         servicos={"FRETE|FCA": 69.88, "FRETE|EFVM": 58.22,
                   "MANOBRA DESTINO|EFVM": 21.47, "MANOBRA ORIGEM|FCA": 14.31,
                   "TRANSBORDO ORIGEM|FCA": 15.00}),
    dict(vig_ini="2026-04-01", vig_fim="2026-04-30", tr_antt=260.90,
         tarifa_contrato=196.51, tarifa_faturamento=196.51,
         servicos={"FRETE|FCA": 77.58, "FRETE|EFVM": 64.63,
                   "MANOBRA DESTINO|EFVM": 23.58, "MANOBRA ORIGEM|FCA": 15.72,
                   "TRANSBORDO ORIGEM|FCA": 15.00}),
    dict(vig_ini="2026-03-01", vig_fim="2026-03-31", tr_antt=260.90,
         tarifa_contrato=197.09, tarifa_faturamento=197.09,
         servicos={"FRETE|FCA": 77.83, "FRETE|EFVM": 64.84,
                   "MANOBRA DESTINO|EFVM": 23.65, "MANOBRA ORIGEM|FCA": 15.77,
                   "TRANSBORDO ORIGEM|FCA": 15.00}),
    dict(vig_ini="2026-02-18", vig_fim="2026-02-28", tr_antt=260.90,
         tarifa_contrato=147.39, tarifa_faturamento=147.39,
         servicos={"FRETE|FCA": 56.14, "FRETE|EFVM": 46.77,
                   "MANOBRA DESTINO|EFVM": 17.69, "MANOBRA ORIGEM|FCA": 11.79,
                   "TRANSBORDO ORIGEM|FCA": 15.00}),
    dict(vig_ini="2026-02-01", vig_fim="2026-02-15", tr_antt=260.90,
         tarifa_contrato=147.39, tarifa_faturamento=147.39,
         servicos={"FRETE|FCA": 54.50, "FRETE|EFVM": 45.41,
                   "MANOBRA DESTINO|EFVM": 17.69, "MANOBRA ORIGEM|FCA": 11.79,
                   "TRANSBORDO ORIGEM|FCA": 18.00},
         obs="1o cadastro (10/02/2026)"),
    dict(vig_ini="2026-02-01", vig_fim="2026-02-15", tr_antt=260.90,
         tarifa_contrato=147.29, tarifa_faturamento=147.29,
         servicos={"FRETE|FCA": 54.46, "FRETE|EFVM": 45.38,
                   "MANOBRA DESTINO|EFVM": 17.67, "MANOBRA ORIGEM|FCA": 11.78,
                   "TRANSBORDO ORIGEM|FCA": 18.00},
         obs="2o cadastro (09/02/2026)"),
    # GAP: sem vigencia 01/01/2026-31/01/2026 no F-LINK.
    dict(vig_ini="2025-12-01", vig_fim="2025-12-31", tr_antt=260.90,
         tarifa_contrato=120.93, tarifa_faturamento=120.93,
         servicos={"FRETE|FCA": 42.96, "FRETE|EFVM": 35.79,
                   "MANOBRA DESTINO|EFVM": 14.51, "MANOBRA ORIGEM|FCA": 9.67,
                   "TRANSBORDO ORIGEM|FCA": 18.00}),
    dict(vig_ini="2025-11-01", vig_fim="2025-11-30", tr_antt=260.90,
         tarifa_contrato=125.82, tarifa_faturamento=125.82,
         servicos={"FRETE|FCA": 45.09, "FRETE|EFVM": 37.56,
                   "MANOBRA DESTINO|EFVM": 15.10, "MANOBRA ORIGEM|FCA": 10.07,
                   "TRANSBORDO ORIGEM|FCA": 18.00}),
    dict(vig_ini="2025-10-01", vig_fim="2025-10-31", tr_antt=253.30,
         tarifa_contrato=136.39, tarifa_faturamento=136.39,
         servicos={"FRETE|FCA": 49.70, "FRETE|EFVM": 41.41,
                   "MANOBRA DESTINO|EFVM": 16.37, "MANOBRA ORIGEM|FCA": 10.91,
                   "TRANSBORDO ORIGEM|FCA": 18.00}),
    dict(vig_ini="2025-09-01", vig_fim="2025-09-30", tr_antt=253.30,
         tarifa_contrato=143.72, tarifa_faturamento=143.72,
         servicos={"FRETE|FCA": 52.90, "FRETE|EFVM": 44.07,
                   "MANOBRA DESTINO|EFVM": 17.25, "MANOBRA ORIGEM|FCA": 11.50,
                   "TRANSBORDO ORIGEM|FCA": 18.00},
         obs="2o cadastro / final (22/09/2025)"),
    dict(vig_ini="2025-09-01", vig_fim="2025-09-30", tr_antt=253.30,
         tarifa_contrato=130.43, tarifa_faturamento=130.43,
         servicos={"FRETE|FCA": 47.10, "FRETE|EFVM": 39.25,
                   "MANOBRA DESTINO|EFVM": 15.65, "MANOBRA ORIGEM|FCA": 10.43,
                   "TRANSBORDO ORIGEM|FCA": 18.00},
         obs="1o cadastro (19/09/2025)"),
]

# ===========================================================================
# 10763 | C_2026_14 | EPO->ISN | FARELO DE SOJA | IMG_0531.MOV
# Direito de Passagem em 2 ferrovias (MRS + ALLMP) + Utilizacao de Patio/MRS
# (sempre R$0,00 nas vigencias mineradas) + Frete/FCA + Manobra Origem/
# Destino FCA. 30 linhas = 25 vigencias distintas (5 vigencias com
# re-cadastro duplicado: 01-15/02/2026 x1 dup, 01-28/02/2025 x2 dup extras,
# 01-30/09/2025, 01-31/08/2024, 01-31/12/2024 registrado 3x identico -
# colapsado em 1 linha por nao representar reajuste real).
# GAP confirmado: sem vigencia de janeiro/2025 (pula de 01-28/02/2025 direto
# para 01/12/2024-31/12/2024). Vigencias mais antigas (ago-dez/2024) cobrem
# periodos multi-mes (ex. 01/11/2024-31/12/2024) que foram depois fatiados
# por re-cadastros mais recentes com vigencia mensal - ambos preservados.
# Todas as 30 linhas validadas: soma dos servicos = Tarifa Contrato/
# Faturamento, diferenca R$0,00 em todas.
# ===========================================================================
DADOS[10763] = [
    dict(vig_ini="2026-07-01", vig_fim="2026-07-31", tr_antt=231.64,
         tarifa_contrato=254.16, tarifa_faturamento=254.16,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.19, "FRETE|FCA": 213.70,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2026-06-01", vig_fim="2026-06-30", tr_antt=231.64,
         tarifa_contrato=266.95, tarifa_faturamento=266.95,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.19, "FRETE|FCA": 195.09,
                   "MANOBRA ORIGEM|FCA": 30.00, "MANOBRA DESTINO|FCA": 30.00}),
    dict(vig_ini="2026-05-01", vig_fim="2026-05-31", tr_antt=231.64,
         tarifa_contrato=267.52, tarifa_faturamento=267.52,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.19, "FRETE|FCA": 195.66,
                   "MANOBRA ORIGEM|FCA": 30.00, "MANOBRA DESTINO|FCA": 30.00}),
    dict(vig_ini="2026-04-01", vig_fim="2026-04-30", tr_antt=231.64,
         tarifa_contrato=288.71, tarifa_faturamento=288.71,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.19, "FRETE|FCA": 216.85,
                   "MANOBRA ORIGEM|FCA": 30.00, "MANOBRA DESTINO|FCA": 30.00}),
    dict(vig_ini="2026-03-01", vig_fim="2026-03-31", tr_antt=231.64,
         tarifa_contrato=290.01, tarifa_faturamento=290.01,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 218.05,
                   "MANOBRA ORIGEM|FCA": 30.00, "MANOBRA DESTINO|FCA": 30.00}),
    dict(vig_ini="2026-02-16", vig_fim="2026-02-28", tr_antt=231.64,
         tarifa_contrato=176.12, tarifa_faturamento=176.12,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 135.56,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="cadastro 14/02/2026"),
    dict(vig_ini="2026-02-01", vig_fim="2026-02-15", tr_antt=231.64,
         tarifa_contrato=176.12, tarifa_faturamento=176.12,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 135.56,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="1o cadastro (10/02/2026)"),
    dict(vig_ini="2026-02-01", vig_fim="2026-02-15", tr_antt=231.64,
         tarifa_contrato=175.74, tarifa_faturamento=175.74,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 135.18,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="2o cadastro (09/02/2026)"),
    dict(vig_ini="2026-01-01", vig_fim="2026-01-31", tr_antt=231.64,
         tarifa_contrato=154.81, tarifa_faturamento=154.81,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 114.25,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-12-01", vig_fim="2025-12-31", tr_antt=231.64,
         tarifa_contrato=154.81, tarifa_faturamento=154.81,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 114.25,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="mesma tarifa de jan/2026, cadastro 28/11/2025"),
    dict(vig_ini="2025-11-01", vig_fim="2025-11-30", tr_antt=231.64,
         tarifa_contrato=154.36, tarifa_faturamento=154.36,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 113.80,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-10-01", vig_fim="2025-10-31", tr_antt=224.98,
         tarifa_contrato=200.79, tarifa_faturamento=200.79,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 160.23,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-09-01", vig_fim="2025-09-30", tr_antt=224.90,
         tarifa_contrato=194.67, tarifa_faturamento=194.67,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 154.11,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="2o cadastro / final (28/09/2025)"),
    dict(vig_ini="2025-09-01", vig_fim="2025-09-30", tr_antt=224.90,
         tarifa_contrato=214.51, tarifa_faturamento=214.51,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 173.95,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="1o cadastro (10/09/2025)"),
    dict(vig_ini="2025-08-01", vig_fim="2025-08-31", tr_antt=224.90,
         tarifa_contrato=239.34, tarifa_faturamento=239.34,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.67,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 198.78,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-07-01", vig_fim="2025-07-31", tr_antt=224.90,
         tarifa_contrato=239.11, tarifa_faturamento=239.11,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 198.69,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-06-01", vig_fim="2025-06-30", tr_antt=224.90,
         tarifa_contrato=247.80, tarifa_faturamento=247.80,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.29, "FRETE|FCA": 207.38,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-05-01", vig_fim="2025-05-31", tr_antt=224.90,
         tarifa_contrato=249.91, tarifa_faturamento=249.91,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.26, "FRETE|FCA": 209.52,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30}),
    dict(vig_ini="2025-04-01", vig_fim="2025-04-30", tr_antt=224.90,
         tarifa_contrato=262.62, tarifa_faturamento=262.62,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.26, "FRETE|FCA": 210.83,
                   "MANOBRA ORIGEM|FCA": 20.00, "MANOBRA DESTINO|FCA": 20.00}),
    dict(vig_ini="2025-03-01", vig_fim="2025-03-31", tr_antt=224.90,
         tarifa_contrato=263.03, tarifa_faturamento=263.03,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.26, "FRETE|FCA": 211.24,
                   "MANOBRA ORIGEM|FCA": 20.00, "MANOBRA DESTINO|FCA": 20.00}),
    dict(vig_ini="2025-02-01", vig_fim="2025-02-28", tr_antt=224.90,
         tarifa_contrato=206.65, tarifa_faturamento=206.65,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.26, "FRETE|FCA": 166.26,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="3o cadastro / final (19/02/2025)"),
    dict(vig_ini="2025-02-01", vig_fim="2025-02-28", tr_antt=224.90,
         tarifa_contrato=187.54, tarifa_faturamento=187.54,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.26, "FRETE|FCA": 147.15,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="2o cadastro (18/02/2025)"),
    dict(vig_ini="2025-02-01", vig_fim="2025-02-28", tr_antt=224.90,
         tarifa_contrato=170.19, tarifa_faturamento=170.19,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 9.26, "FRETE|FCA": 129.80,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="1o cadastro (14/02/2025)"),
    # GAP: sem vigencia de janeiro/2025 no F-LINK.
    dict(vig_ini="2024-12-01", vig_fim="2024-12-31", tr_antt=224.90,
         tarifa_contrato=148.32, tarifa_faturamento=148.32,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 108.47,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="cadastro 05/12/2024; mesmos valores re-registrados 05/12 e "
             "29/11/2024 (colapsados nesta linha, sem reajuste real entre eles)"),
    dict(vig_ini="2024-11-01", vig_fim="2024-12-31", tr_antt=224.90,
         tarifa_contrato=147.43, tarifa_faturamento=147.43,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 107.58,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="cadastro 30/10/2024; vigencia bimestral depois fatiada pelo "
             "cadastro de dez/2024 acima"),
    dict(vig_ini="2024-10-01", vig_fim="2024-12-31", tr_antt=224.90,
         tarifa_contrato=190.82, tarifa_faturamento=190.82,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 150.97,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="cadastro 30/09/2024; vigencia trimestral depois fatiada pelos "
             "cadastros mais recentes acima"),
    dict(vig_ini="2024-09-01", vig_fim="2024-12-31", tr_antt=215.77,
         tarifa_contrato=203.41, tarifa_faturamento=203.41,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 163.56,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="cadastro 30/08/2024; vigencia 4 meses depois fatiada pelos "
             "cadastros mais recentes acima"),
    dict(vig_ini="2024-08-01", vig_fim="2024-12-31", tr_antt=215.77,
         tarifa_contrato=227.83, tarifa_faturamento=227.83,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.53,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 187.98,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="2o cadastro / final (01/08/2024)"),
    dict(vig_ini="2024-08-01", vig_fim="2024-12-31", tr_antt=215.77,
         tarifa_contrato=227.83, tarifa_faturamento=227.83,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.44,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 188.07,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="1o cadastro (30/07/2024) - mesma tarifa total, split "
             "DP MRS/frete ligeiramente diferente do 2o cadastro"),
    dict(vig_ini="2024-07-01", vig_fim="2024-07-31", tr_antt=215.77,
         tarifa_contrato=228.30, tarifa_faturamento=228.30,
         servicos={"UTILIZACAO DE PATIO|MRS": 0.00, "DIREITO DE PASSAGEM|MRS": 2.44,
                   "DIREITO DE PASSAGEM|ALLMP": 8.72, "FRETE|FCA": 188.54,
                   "MANOBRA ORIGEM|FCA": 14.30, "MANOBRA DESTINO|FCA": 14.30},
         obs="cadastro 28/06/2024 - ultima vigencia visivel no video "
             "(fim da gravacao, nao ha certeza de que seja a mais antiga "
             "do historico completo do item)"),
]


def main():
    if not os.path.exists(DB_PATH):
        raise SystemExit(f"Banco nao encontrado: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("DROP TABLE IF EXISTS caramuru_precos_contratuais")
    cur.execute("""
        CREATE TABLE caramuru_precos_contratuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            item_ferroviario INTEGER NOT NULL,
            contrato TEXT NOT NULL,
            vigencia_contrato_ini TEXT,
            vigencia_contrato_fim TEXT,
            origem TEXT NOT NULL,
            origem_nome TEXT NOT NULL,
            destino TEXT NOT NULL,
            destino_nome TEXT NOT NULL,
            produto TEXT NOT NULL,
            vigencia_inicial TEXT NOT NULL,
            vigencia_final TEXT NOT NULL,
            valor_tr_antt REAL,
            tarifa_contrato REAL NOT NULL,
            tarifa_faturamento REAL NOT NULL,
            servico TEXT NOT NULL,
            ferrovia TEXT NOT NULL,
            valor_rs_t REAL NOT NULL,
            obs TEXT,
            video_fonte TEXT NOT NULL,
            fonte TEXT NOT NULL
        )
    """)

    total_linhas = 0
    total_vigencias = 0
    for item, vigencias in DADOS.items():
        meta = FLUXOS[item]
        total_vigencias += len(vigencias)
        for v in vigencias:
            soma = round(sum(v["servicos"].values()), 2)
            if abs(soma - v["tarifa_faturamento"]) > 0.05:
                raise SystemExit(
                    f"VALIDACAO FALHOU: item {item} vig {v['vig_ini']}-{v['vig_fim']}: "
                    f"soma servicos={soma} != tarifa_faturamento={v['tarifa_faturamento']}"
                )
            for servico_ferrovia, valor in v["servicos"].items():
                servico, ferrovia = servico_ferrovia.split("|")
                cur.execute("""
                    INSERT INTO caramuru_precos_contratuais (
                        cliente, item_ferroviario, contrato,
                        vigencia_contrato_ini, vigencia_contrato_fim,
                        origem, origem_nome, destino, destino_nome, produto,
                        vigencia_inicial, vigencia_final,
                        valor_tr_antt, tarifa_contrato, tarifa_faturamento,
                        servico, ferrovia, valor_rs_t, obs,
                        video_fonte, fonte
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    meta["cliente"], item, meta["contrato"],
                    meta["vigencia_contrato_ini"], meta["vigencia_contrato_fim"],
                    meta["origem"], meta["origem_nome"],
                    meta["destino"], meta["destino_nome"], meta["produto"],
                    v["vig_ini"], v["vig_fim"],
                    v["tr_antt"], v["tarifa_contrato"], v["tarifa_faturamento"],
                    servico, ferrovia, valor, v.get("obs"),
                    meta["video"], FONTE,
                ))
                total_linhas += 1

    conn.commit()
    print(f"OK: {total_vigencias} vigencias ({total_linhas} linhas servico x ferrovia) "
          f"inseridas em caramuru_precos_contratuais para {len(DADOS)} itens.")
    conn.close()


if __name__ == "__main__":
    main()
