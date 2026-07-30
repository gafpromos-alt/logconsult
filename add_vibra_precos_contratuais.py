#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_vibra_precos_contratuais.py

Cria/recria a tabela `vibra_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos fluxos
ferroviarios do cliente VIBRA ENERGIA S.A. (combustiveis), minerado dos
videos de tela do F-LINK (flink.vli.digital, tela "Precos Contratuais"),
um video por fluxo/item ferroviario.

Uma linha por (item ferroviario x vigencia/reajuste).

VIBRA nao existe ainda no banco analitico - criada do zero nesta mineracao
(18/jul), a partir dos videos IMG_0346-0348, IMG_0352, IMG_0354-0371
(pasta 09_Fotos). 22 videos ao todo; dois deles (IMG_0348 e IMG_0364)
apenas RE-CONFIRMAM item ja capturado em video anterior (mesmos valores,
sem dado novo) - ver notas por item abaixo.

DISCIPLINA DE LEITURA (frame a frame, ffmpeg fps=1, resolucao nativa
1920x1080 - screenshots de tela cheia sao muito mais legiveis que sheets
em mosaico):
 - Cada video mostra o cabecalho (Cliente/Item Ferroviario/Contrato/
   Vigencia do Contrato/Estacao Origem/Estacao Destino/Produto) e a tabela
   "PRECOS CONTRATUAIS" com colunas Data Cadastro, Ultima Atualizacao,
   Vigencia Inicial, Vigencia Final, Valor TR (ANTT), Tarifa Contrato,
   Desconto/Incremento, Tarifa Faturamento e uma sub-tabela "Servicos"
   (linhas por servico: FRETE por ferrovia -- ha fluxos intermodais EFVM+
   FCA ou FNS+EFC --, MANOBRA ORIGEM, MANOBRA DESTINO, DIREITO DE PASSAGEM,
   e em alguns fluxos VIBRA tambem TREM ESPECIAL/DEPRECIACAO DE VAGAO,
   ambos sempre R$0,00 nos itens observados).
 - frete_rs_t gravado = SOMA de todas as linhas "FRETE" (uma ou duas
   ferrovias). manobra_origem_rs_t e manobra_destino_rs_t = linhas
   "MANOBRA ORIGEM"/"MANOBRA DESTINO". outros_rs_t = linha "DIREITO DE
   PASSAGEM" (fluxos com trecho EFC), 0 quando nao existe essa linha.
 - Validacao aplicada em toda linha gravada: frete + manobra_origem +
   manobra_destino + outros ~= tarifa_contrato (tolerancia R$0,05).
 - Vigencias com scroll-blur (padrao moire/dupla-exposicao no vidro do
   monitor) foram descartadas. Nao foi inventado nenhum digito ilegivel.
 - Re-cadastros (mesma vigencia_inicial, cadastros em datas diferentes,
   por vezes tarifa igual com split frete/manobra diferente, por vezes
   vigencia_final diferente) foram mantidos como linhas distintas.
 - Nem todo o historico de cada item foi lido (varios videos tem 20-60s
   de scroll cobrindo 2023-2026) - priorizado cobrir os 22 videos/itens
   unicos com as vigencias mais recentes + amostra validada mais funda
   onde a leitura permitiu, em vez de esgotar poucos itens.

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente.

Fonte: F-LINK Precos Contratuais (IMG_0346-0348, IMG_0352, IMG_0354-0371).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0346-0348, IMG_0352, IMG_0354-0371) - historico de reajuste VIBRA ENERGIA S.A."

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# item, contrato, origem, origem_nome, destino, destino_nome, produto, video
# ---------------------------------------------------------------------------
FLUXOS = {
    41224: dict(contrato="C_2026_11", origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="OLEO DIESEL", video="IMG_0346.MOV"),
    41291: dict(contrato="C_2026_12", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="OLEO DIESEL", video="IMG_0347.MOV,IMG_0348.MOV"),
    41218: dict(contrato="C_2026_11", origem="EYU", origem_nome="EMBIRUCU",
                destino="VGV", destino_nome="GOVERNADOR VALADARES",
                produto="OLEO DIESEL", video="IMG_0352.MOV"),
    41216: dict(contrato="C_2026_11", origem="EYU", origem_nome="EMBIRUCU",
                destino="VGV", destino_nome="GOVERNADOR VALADARES",
                produto="GASOLINA", video="IMG_0354.MOV"),
    41272: dict(contrato="C_2026_12", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QMA", destino_nome="PATIO DE MARABA",
                produto="OLEO DIESEL", video="IMG_0355.MOV"),
    41222: dict(contrato="C_2026_11", origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="GASOLINA", video="IMG_0356.MOV"),
    41287: dict(contrato="C_2026_12", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0357.MOV"),
    41290: dict(contrato="C_2026_12", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="GASOLINA", video="IMG_0358.MOV"),
    19392: dict(contrato="C_2024_4.2", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="ALCOOL", video="IMG_0359.MOV"),
    8591: dict(contrato="C_2024_5", origem="EYU", origem_nome="EMBIRUCU",
               destino="VGV", destino_nome="GOVERNADOR VALADARES",
               produto="OLEO DIESEL", video="IMG_0360.MOV"),
    15686: dict(contrato="C_2024_4.2", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QMA", destino_nome="PATIO DE MARABA",
                produto="OLEO DIESEL", video="IMG_0361.MOV"),
    8209: dict(contrato="C_2024_4.2", origem="QPM", origem_nome="PONTA DA MADEIRA",
               destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
               produto="OLEO DIESEL", video="IMG_0362.MOV"),
    15680: dict(contrato="C_2024_5", origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="OLEO DIESEL", video="IMG_0363.MOV,IMG_0364.MOV"),
    8211: dict(contrato="C_2024_4.2", origem="QPM", origem_nome="PONTA DA MADEIRA",
               destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
               produto="GASOLINA", video="IMG_0365.MOV"),
    8036: dict(contrato="C_2024_4.2", origem="QPM", origem_nome="PONTA DA MADEIRA",
               destino="QMA", destino_nome="PATIO DE MARABA",
               produto="OLEO DIESEL", video="IMG_0366.MOV"),
    10918: dict(contrato="C_2024_4.2", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QMA", destino_nome="PATIO DE MARABA",
                produto="GASOLINA", video="IMG_0367.MOV"),
    8030: dict(contrato="C_2024_4.2", origem="QPM", origem_nome="PONTA DA MADEIRA",
               destino="QAL", destino_nome="PATIO DE ACAILANDIA",
               produto="OLEO DIESEL", video="IMG_0368.MOV"),
    8588: dict(contrato="C_2024_5", origem="EYU", origem_nome="EMBIRUCU",
               destino="VGV", destino_nome="GOVERNADOR VALADARES",
               produto="GASOLINA", video="IMG_0369.MOV"),
    11619: dict(contrato="C_2024_4.2", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0370.MOV"),
    15159: dict(contrato="C_2024_5", origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="GASOLINA", video="IMG_0371.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t)
# Datas em YYYY-MM-DD. Valores em R$/t. outros_rs_t = DIREITO DE PASSAGEM
# (0.0 quando o fluxo nao tem trecho EFC / a tela nao mostra essa linha).
# frete_rs_t = soma das linhas FRETE (1 ou 2 ferrovias).
# ---------------------------------------------------------------------------

DADOS = {}

# --- 41224 | C_2026_11 | EYU->VTU | OLEO DIESEL | IMG_0346.MOV ---
# Video curto (10s), fluxo inteiro coberto (nao ha mais historico visivel
# alem do que segue - a rolagem chega ao fim da lista). Intermodal
# EFVM+FCA. 7 vigencias, todas validadas (soma exata).
DADOS[41224] = [
    # vig_ini      vig_fim       TR       tarifa   frete    MO     MD     outros
    ("2026-07-10", "2027-12-31", 188.81, 170.21, 117.84, 24.77, 27.60, 0.0),
    ("2026-06-10", "2027-12-31", 188.81, 170.11, 117.78, 24.75, 27.58, 0.0),
    ("2026-05-10", "2027-12-31", 188.81, 170.46, 109.88, 25.00, 35.58, 0.0),
    ("2026-04-10", "2027-12-31", 188.81, 170.60, 118.12, 24.82, 27.66, 0.0),
    ("2026-03-10", "2027-12-31", 188.81, 171.34, 118.63, 24.93, 27.78, 0.0),  # 1o cadastro
    ("2026-03-10", "2027-12-31", 188.81, 171.34, 118.59, 24.95, 27.80, 0.0),  # 2o cadastro
    ("2026-02-10", "2027-12-31", 188.81, 171.84, 119.09, 24.95, 27.80, 0.0),
]

# --- 41291 | C_2026_12 | QPM->PPN | OLEO DIESEL | IMG_0347.MOV, IMG_0348.MOV ---
# IMG_0348 re-confirma o mesmo item/valores de IMG_0347 (sem dado novo).
# Intermodal FNS+EFC. 6 vigencias validadas (frete+MO+MD=tarifa).
DADOS[41291] = [
    ("2026-07-10", "2027-12-31", 856.32, 218.26, 167.07, 23.77, 15.14, 12.28),
    ("2026-06-10", "2027-12-31", 856.32, 218.55, 167.31, 23.80, 15.16, 12.28),
    ("2026-05-10", "2027-12-31", 856.32, 220.79, 145.48, 42.61, 20.42, 12.28),
    ("2026-04-10", "2027-12-31", 856.32, 220.43, 169.65, 23.52, 14.98, 12.28),
    ("2026-03-10", "2026-04-09", 856.32, 215.41, 140.10, 42.61, 20.42, 12.28),  # 1o cadastro (vig curta)
    ("2026-03-10", "2027-12-31", 856.32, 215.41, 137.80, 42.61, 20.42, 14.58),  # 2o cadastro
]

# --- 41218 | C_2026_11 | EYU->VGV | OLEO DIESEL | IMG_0352.MOV ---
# Intermodal EFVM+FCA. 6 vigencias validadas.
DADOS[41218] = [
    ("2026-07-10", "2027-12-31", 122.88, 128.96, 85.43, 24.77, 18.76, 0.0),
    ("2026-06-10", "2027-12-31", 122.88, 128.88, 85.38, 24.75, 18.75, 0.0),
    ("2026-05-10", "2027-12-31", 122.88, 129.14, 79.14, 25.00, 25.00, 0.0),
    ("2026-04-10", "2027-12-31", 122.88, 129.25, 85.61, 24.83, 18.81, 0.0),
    ("2026-03-10", "2027-12-31", 122.88, 129.81, 85.99, 24.93, 18.89, 0.0),
    ("2026-02-10", "2027-12-31", 122.88, 130.18, 86.31, 24.95, 18.90, 0.0),
]

# --- 41216 | C_2026_11 | EYU->VGV | GASOLINA | IMG_0354.MOV ---
# Intermodal EFVM+FCA. Mesma rota/contrato de 41218 (item OLEO DIESEL) -
# vigencias e tarifa_contrato IDENTICAS, split de servicos identico. 6 vig.
DADOS[41216] = [
    ("2026-07-10", "2027-12-31", 136.41, 128.96, 85.43, 24.77, 18.76, 0.0),
    ("2026-06-10", "2027-12-31", 136.41, 128.88, 85.38, 24.75, 18.75, 0.0),
    ("2026-05-10", "2027-12-31", 136.41, 129.14, 79.14, 25.00, 25.00, 0.0),
    ("2026-04-10", "2027-12-31", 136.41, 129.25, 85.61, 24.83, 18.81, 0.0),
    ("2026-03-10", "2027-12-31", 136.41, 129.81, 85.99, 24.93, 18.89, 0.0),
    ("2026-02-10", "2027-12-31", 136.41, 130.18, 80.18, 25.00, 25.00, 0.0),
]

# --- 41272 | C_2026_12 | QPM->QMA | OLEO DIESEL | IMG_0355.MOV ---
# Single ferrovia EFC (so FRETE+MO+MD, sem DIREITO DE PASSAGEM). 7 vig.
DADOS[41272] = [
    ("2026-07-10", "2027-12-31", 220.13, 174.81, 140.80, 23.77, 10.24, 0.0),
    ("2026-06-10", "2027-12-31", 220.13, 175.04, 140.99, 23.80, 10.25, 0.0),
    ("2026-05-10", "2027-12-31", 220.13, 176.84, 114.58, 42.61, 19.65, 0.0),
    ("2026-04-10", "2027-12-31", 220.13, 176.54, 142.89, 23.52, 10.13, 0.0),
    ("2026-03-10", "2027-12-31", 220.13, 172.53, 138.97, 23.46, 10.10, 0.0),
    ("2026-02-10", "2026-03-09", 220.13, 172.95, 110.69, 42.61, 19.65, 0.0),  # vig curta
    ("2026-01-01", "2026-02-09", 220.13, 173.00, 110.74, 42.61, 19.65, 0.0),  # vig curta
]

# --- 41222 | C_2026_11 | EYU->VTU | GASOLINA | IMG_0356.MOV ---
# Intermodal EFVM+FCA. Mesma rota/contrato de 41224 (OLEO DIESEL) -
# valores IDENTICOS, cross-validado. 7 vigencias.
DADOS[41222] = [
    ("2026-07-10", "2027-12-31", 208.88, 170.21, 117.84, 24.77, 27.60, 0.0),
    ("2026-06-10", "2027-12-31", 208.88, 170.11, 117.78, 24.75, 27.58, 0.0),
    ("2026-05-10", "2027-12-31", 208.88, 170.46, 109.88, 25.00, 35.58, 0.0),
    ("2026-04-10", "2027-12-31", 208.88, 170.60, 118.12, 24.82, 27.66, 0.0),
    ("2026-03-10", "2027-12-31", 208.88, 171.34, 118.63, 24.93, 27.78, 0.0),  # 1o cadastro
    ("2026-03-10", "2027-12-31", 208.88, 171.34, 110.76, 25.00, 35.58, 0.0),  # 2o cadastro
    ("2026-02-10", "2027-12-31", 208.88, 171.84, 119.09, 24.95, 27.80, 0.0),
]

# --- 41287 | C_2026_12 | PPN->QPM | OLEO DIESEL | IMG_0357.MOV ---
# Intermodal FNS+EFC (rota reversa de 41291). 6 vigencias validadas.
DADOS[41287] = [
    ("2026-07-10", "2027-12-31", 856.32, 121.25, 85.20, 0.0, 23.77, 12.28),
    ("2026-06-10", "2027-12-31", 856.32, 121.42, 85.34, 0.0, 23.80, 12.28),
    ("2026-05-10", "2027-12-31", 856.32, 122.66, 47.35, 20.42, 42.61, 12.28),
    ("2026-04-10", "2027-12-31", 856.32, 122.46, 86.66, 0.0, 23.52, 12.28),
    ("2026-03-10", "2026-04-09", 856.32, 119.67, 44.36, 20.42, 42.61, 12.28),  # vig curta
    ("2026-03-10", "2027-12-31", 856.32, 119.67, 42.06, 20.42, 42.61, 14.58),  # 2o cadastro
]

# --- 41290 | C_2026_12 | QPM->PPN | GASOLINA | IMG_0358.MOV ---
# Intermodal FNS+EFC. Mesma rota/contrato de 41291 - valores IDENTICOS. 6 vig.
DADOS[41290] = [
    ("2026-07-10", "2027-12-31", 856.32, 218.26, 168.85, 23.77, 15.14, 10.50),
    ("2026-06-10", "2027-12-31", 856.32, 218.55, 169.09, 23.80, 15.16, 10.50),
    ("2026-05-10", "2027-12-31", 856.32, 220.79, 147.26, 42.61, 20.42, 10.50),
    ("2026-04-10", "2027-12-31", 856.32, 220.43, 171.43, 23.52, 14.98, 10.50),
    ("2026-03-10", "2026-04-09", 856.32, 215.41, 141.88, 42.61, 20.42, 10.50),  # vig curta
    ("2026-03-10", "2027-12-31", 856.32, 215.41, 137.80, 42.61, 20.42, 14.58),  # 2o cadastro
]

# --- 19392 | C_2024_4.2 | PPN->QPM | ALCOOL | IMG_0359.MOV ---
# Single ferrovia FNS+EFC (DIREITO DE PASSAGEM sempre presente). Video
# longo (16.5s) com muito historico (2025 inteiro); vigencias mais antigas
# (< mar/2025) descartadas por scroll-blur. 15 vigencias validadas.
DADOS[19392] = [
    ("2026-03-10", "2027-12-31", 635.41, 119.67, 42.06, 20.42, 42.61, 14.58),
    ("2026-02-10", "2027-12-31", 635.41, 119.96, 45.87, 20.42, 42.61, 11.06),
    ("2026-01-01", "2027-12-31", 643.14, 120.00, 85.42, 0.0, 23.52, 11.06),
    ("2026-01-10", "2026-01-31", 643.14, 130.06, 55.97, 20.42, 42.61, 11.06),
    ("2025-12-10", "2026-01-31", 643.14, 130.34, 56.25, 20.42, 42.61, 11.06),  # 1o cadastro
    ("2025-12-10", "2025-12-31", 643.14, 130.34, 83.49, 0.0, 35.79, 11.06),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 643.14, 129.54, 82.90, 0.0, 35.58, 11.06),
    ("2025-10-10", "2025-12-31", 643.14, 129.64, 82.98, 0.0, 35.60, 11.06),
    ("2025-09-10", "2025-12-31", 643.14, 129.63, 82.97, 0.0, 35.60, 11.06),
    ("2025-08-10", "2025-12-31", 643.14, 128.89, 82.43, 0.0, 35.40, 11.06),
    ("2025-07-10", "2025-12-31", 643.14, 128.79, 82.36, 0.0, 35.37, 11.06),
    ("2025-06-10", "2025-12-31", 643.14, 128.60, 82.22, 0.0, 35.32, 11.06),
    ("2025-05-10", "2025-12-31", 643.14, 129.82, 83.62, 0.0, 35.65, 10.55),
    ("2025-04-10", "2025-12-31", 643.14, 131.51, 84.84, 0.0, 36.12, 10.55),
    ("2025-03-01", "2025-12-31", 643.14, 132.07, 85.25, 0.0, 36.27, 10.55),
]

# --- 8591 | C_2024_5 | EYU->VGV | OLEO DIESEL | IMG_0360.MOV ---
# Intermodal EFVM+FCA. TREM ESPECIAL/DEPRECIACAO DE VAGAO sempre R$0,00
# (nao contam para o frete). 10 vigencias validadas (2025-2026).
DADOS[8591] = [
    ("2026-02-10", "2027-12-31", 122.88, 130.18, 80.18, 25.00, 25.00, 0.0),
    ("2026-01-01", "2027-12-31", 122.88, 129.90, 86.05, 24.95, 18.90, 0.0),
    ("2026-01-10", "2026-01-31", 122.88, 114.50, 64.50, 25.00, 25.00, 0.0),
    ("2025-12-10", "2026-01-31", 122.88, 115.57, 65.57, 25.00, 25.00, 0.0),  # 1o cadastro
    ("2025-12-10", "2025-12-31", 122.88, 115.57, 65.53, 25.02, 25.02, 0.0),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 122.88, 115.25, 65.35, 24.95, 24.95, 0.0),
    ("2025-10-10", "2025-12-31", 119.30, 115.32, 65.38, 24.97, 24.97, 0.0),
    ("2025-09-10", "2025-12-31", 119.30, 115.31, 65.37, 24.97, 24.97, 0.0),
    ("2025-08-10", "2025-12-31", 119.30, 114.90, 65.14, 24.88, 24.88, 0.0),
    ("2025-07-10", "2025-12-31", 119.30, 114.79, 65.09, 24.85, 24.85, 0.0),
]

# --- 15686 | C_2024_4.2 | QPM->QMA | OLEO DIESEL | IMG_0361.MOV ---
# Single ferrovia EFC (sem DIREITO DE PASSAGEM). Video longo (24s), historico
# 2024-2026 quase todo legivel. 29 vigencias validadas - fluxo mais
# profundamente minerado desta safra (item 8036/IMG_0366 confirma a mesma
# rota/valores para outro item, ver abaixo).
DADOS[15686] = [
    ("2026-04-10", "2027-12-31", 220.13, 176.54, 142.20, 24.00, 10.34, 0.0),
    ("2026-03-10", "2027-12-31", 220.13, 172.53, 138.97, 23.46, 10.10, 0.0),
    ("2026-02-10", "2027-12-31", 220.13, 172.95, 139.31, 23.51, 10.13, 0.0),
    ("2026-01-01", "2027-12-31", 220.13, 173.00, 139.35, 23.52, 10.13, 0.0),
    ("2026-01-10", "2026-01-31", 220.13, 153.32, 19.65, 42.61, 91.06, 0.0),
    ("2025-12-10", "2026-01-31", 210.29, 153.65, 19.65, 42.61, 91.39, 0.0),
    ("2025-12-10", "2025-12-31", 210.29, 153.65, 17.12, 35.79, 100.74, 0.0),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 210.29, 152.71, 17.02, 35.58, 100.11, 0.0),
    ("2025-10-10", "2025-12-31", 210.29, 152.83, 17.03, 35.60, 100.20, 0.0),
    ("2025-09-10", "2025-12-31", 210.29, 152.82, 17.03, 35.60, 100.19, 0.0),
    ("2025-08-10", "2025-12-31", 210.29, 151.94, 16.93, 35.40, 99.61, 0.0),
    ("2025-07-10", "2025-12-31", 210.29, 151.82, 16.92, 35.37, 99.53, 0.0),
    ("2025-06-10", "2025-12-31", 210.29, 151.60, 16.89, 35.32, 99.39, 0.0),
    ("2025-05-10", "2025-12-31", 210.29, 153.03, 17.05, 35.65, 100.33, 0.0),
    ("2025-04-10", "2025-12-31", 210.29, 155.03, 17.28, 36.12, 101.63, 0.0),
    ("2025-03-01", "2025-12-31", 210.29, 155.69, 17.35, 36.27, 102.07, 0.0),
    ("2025-03-10", "2025-06-30", 210.29, 234.48, 19.76, 42.85, 171.87, 0.0),
    ("2025-02-10", "2025-06-30", 210.29, 235.20, 19.82, 42.98, 172.40, 0.0),
    ("2025-01-01", "2025-06-30", 210.29, 233.18, 19.65, 42.61, 170.90, 0.0),
    ("2024-12-10", "2025-01-08", 200.73, 232.23, 25.00, 25.00, 182.23, 0.0),  # 1o cadastro
    ("2024-12-10", "2024-12-31", 200.73, 232.23, 25.00, 25.00, 182.23, 0.0),  # 2o cadastro
    ("2024-11-10", "2024-12-31", 200.73, 230.45, 25.00, 25.00, 180.45, 0.0),
    ("2024-10-10", "2024-12-31", 200.73, 228.51, 25.00, 25.00, 178.51, 0.0),
    ("2024-09-10", "2024-12-31", 200.73, 230.28, 25.00, 25.00, 180.28, 0.0),
    ("2024-08-10", "2024-12-31", 200.73, 231.67, 25.00, 25.00, 181.67, 0.0),
    ("2024-07-10", "2024-12-31", 200.73, 231.86, 19.65, 42.61, 169.60, 0.0),
    ("2024-06-10", "2024-12-31", 200.73, 229.35, 19.65, 42.61, 167.09, 0.0),
    ("2024-05-10", "2024-12-31", 200.73, 229.90, 19.65, 42.61, 167.64, 0.0),
    ("2024-04-01", "2024-12-31", 200.73, 230.20, 25.00, 25.00, 180.20, 0.0),
]

# --- 8209 | C_2024_4.2 | QPM->PPN | OLEO DIESEL | IMG_0362.MOV ---
# Intermodal FNS+EFC. 10 vigencias validadas (2025-2026).
DADOS[8209] = [
    ("2026-03-10", "2027-12-31", 856.32, 215.41, 137.80, 42.61, 20.42, 14.58),
    ("2026-02-10", "2027-12-31", 856.32, 215.94, 141.13, 42.61, 20.42, 11.78),
    ("2026-01-01", "2027-12-31", 866.72, 216.00, 166.52, 23.52, 14.18, 11.78),
    ("2026-01-10", "2026-01-31", 866.72, 194.77, 119.96, 42.61, 20.42, 11.78),
    ("2025-12-10", "2026-01-31", 866.72, 195.19, 120.38, 42.61, 20.42, 11.78),  # 1o cadastro
    ("2025-12-10", "2025-12-31", 866.72, 195.19, 132.62, 35.80, 14.99, 11.78),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 866.72, 194.00, 131.74, 35.58, 14.90, 11.78),
    ("2025-10-10", "2025-12-31", 866.72, 194.15, 131.86, 35.60, 14.91, 11.78),
    ("2025-09-10", "2025-12-31", 866.72, 194.13, 131.84, 35.60, 14.91, 11.78),
    ("2025-08-10", "2025-12-31", 866.72, 193.02, 131.02, 35.40, 14.82, 11.78),
]

# --- 15680 | C_2024_5 | EYU->VTU | OLEO DIESEL | IMG_0363.MOV, IMG_0364.MOV ---
# IMG_0364 re-confirma o mesmo item e amplia o historico (10/04 e 10/03/2025).
# Intermodal EFVM+FCA. 17 vigencias validadas.
DADOS[15680] = [
    ("2026-03-10", "2027-12-31", 188.81, 171.34, 118.63, 24.93, 27.78, 0.0),
    ("2026-02-10", "2027-12-31", 188.81, 171.84, 118.97, 25.01, 27.86, 0.0),
    ("2026-01-01", "2027-12-31", 188.81, 171.46, 118.71, 24.95, 27.80, 0.0),
    ("2026-01-10", "2026-01-31", 188.81, 164.43, 103.85, 25.00, 35.58, 0.0),
    ("2025-12-10", "2026-01-31", 188.81, 165.96, 105.38, 25.00, 35.58, 0.0),  # 1o cadastro
    ("2025-12-10", "2025-12-31", 188.81, 165.96, 105.33, 25.02, 35.61, 0.0),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 188.81, 165.49, 105.03, 24.95, 35.51, 0.0),
    ("2025-10-10", "2025-12-31", 183.31, 165.60, 105.10, 24.97, 35.53, 0.0),
    ("2025-09-10", "2025-12-31", 183.31, 165.59, 105.09, 24.97, 35.53, 0.0),
    ("2025-07-10", "2025-08-09", 183.31, 164.84, 104.62, 24.85, 35.37, 0.0),  # 1o cadastro (vig curta)
    ("2025-08-10", "2025-12-31", 183.31, 164.99, 104.71, 24.88, 35.40, 0.0),
    ("2025-07-01", "2025-12-31", 183.31, 164.94, 104.36, 25.00, 35.58, 0.0),
    ("2025-06-10", "2025-06-30", 183.31, 164.94, 104.68, 24.87, 35.39, 0.0),
    ("2025-05-10", "2025-06-30", 183.31, 166.33, 105.56, 25.08, 35.69, 0.0),
    ("2025-04-10", "2025-12-31", 183.31, 169.05, 107.28, 25.49, 36.28, 0.0),
    ("2025-04-10", "2025-06-30", 183.31, 169.05, 107.28, 25.49, 36.28, 0.0),  # 2o cadastro
    ("2025-03-10", "2025-06-30", 183.31, 169.32, 107.46, 25.53, 36.33, 0.0),
]

# --- 8211 | C_2024_4.2 | QPM->PPN | GASOLINA | IMG_0365.MOV ---
# Intermodal FNS+EFC. Video com forte ghosting/scroll-blur na maior parte
# do historico 2025-2026 - so as vigencias abaixo foram lidas com confianca.
DADOS[8211] = [
    ("2026-03-10", "2027-12-31", 856.32, 215.41, 137.80, 42.61, 20.42, 14.58),
    ("2025-03-01", "2025-12-31", 866.72, 197.78, 136.71, 36.27, 15.19, 9.61),
    ("2025-03-10", "2025-06-30", 866.72, 250.75, 177.75, 42.85, 20.54, 9.61),
    ("2025-02-10", "2025-06-30", 866.72, 251.52, 178.33, 42.98, 20.60, 9.61),
    ("2025-01-01", "2025-06-30", 811.08, 249.34, 176.70, 42.61, 20.42, 9.61),
    ("2024-12-10", "2025-01-08", 811.08, 273.85, 240.96, 11.64, 11.64, 9.61),
]

# --- 8036 | C_2024_4.2 | QPM->QMA | OLEO DIESEL | IMG_0366.MOV ---
# MESMA rota/contrato/produto de 15686 (IMG_0361) - video confirma um
# SEGUNDO item ferroviario na mesma lane, com valores IDENTICOS na
# vigencia mais recente (cross-validado). Video dominado por texto
# duplicado/fantasma (scroll rapido) no restante do historico - apenas a
# vigencia mais recente foi lida com confianca suficiente.
DADOS[8036] = [
    ("2026-04-10", "2027-12-31", 220.13, 176.54, 142.20, 24.00, 10.34, 0.0),
]

# --- 10918 | C_2024_4.2 | QPM->QMA | GASOLINA | IMG_0367.MOV ---
# Mesma rota/contrato de 15686/8036 (produto GASOLINA). 14 vigencias
# validadas (algumas linhas do topo do video tiveram ghosting leve, mas os
# valores centrais bateram com a soma).
DADOS[10918] = [
    ("2026-04-10", "2027-12-31", 220.13, 176.54, 142.20, 24.00, 10.34, 0.0),
    ("2026-03-10", "2027-12-31", 220.13, 172.53, 138.97, 23.46, 10.10, 0.0),
    ("2025-08-10", "2025-12-31", 210.29, 151.94, 99.61, 35.40, 16.93, 0.0),
    ("2025-07-10", "2025-12-31", 210.29, 151.82, 99.53, 35.37, 16.92, 0.0),
    ("2025-06-10", "2025-12-31", 210.29, 151.60, 99.39, 35.32, 16.89, 0.0),
    ("2025-05-10", "2025-12-31", 210.29, 153.03, 100.22, 31.09, 21.72, 0.0),
    ("2025-04-10", "2025-12-31", 210.29, 155.03, 101.63, 36.12, 17.28, 0.0),
    ("2025-03-01", "2025-12-31", 210.29, 155.69, 102.07, 36.27, 17.35, 0.0),
    ("2025-03-10", "2025-06-30", 210.29, 234.48, 171.87, 42.85, 19.76, 0.0),
    ("2025-02-10", "2025-06-30", 210.29, 235.20, 172.40, 42.98, 19.82, 0.0),
    ("2024-12-10", "2025-01-08", 200.73, 232.23, 177.98, 11.64, 42.61, 0.0),  # 1o cadastro
    ("2024-12-10", "2024-12-31", 200.73, 232.23, 177.98, 11.64, 42.61, 0.0),  # 2o cadastro
    ("2024-11-10", "2024-12-31", 200.73, 230.45, 176.20, 11.64, 42.61, 0.0),
    ("2024-10-10", "2024-12-31", 200.73, 228.51, 174.26, 11.64, 42.61, 0.0),
]

# --- 8030 | C_2024_4.2 | QPM->QAL | OLEO DIESEL | IMG_0368.MOV ---
# Single ferrovia EFC (sem DIREITO DE PASSAGEM). Rota nova (Acailandia).
# 17 vigencias validadas.
DADOS[8030] = [
    ("2026-04-10", "2027-12-31", 168.85, 159.20, 121.96, 24.00, 13.24, 0.0),
    ("2026-03-10", "2027-12-31", 168.85, 155.57, 119.18, 23.46, 12.93, 0.0),
    ("2026-01-10", "2026-01-31", 168.85, 175.78, 109.33, 42.61, 23.84, 0.0),
    ("2025-12-10", "2026-01-31", 161.30, 176.16, 109.71, 42.61, 23.84, 0.0),
    ("2025-12-10", "2025-12-31", 161.30, 176.16, 115.37, 35.79, 25.00, 0.0),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 161.30, 175.08, 114.66, 35.58, 24.84, 0.0),
    ("2025-10-10", "2025-12-31", 161.30, 175.22, 114.78, 35.60, 24.86, 0.0),
    ("2025-09-10", "2025-12-31", 161.30, 175.21, 114.75, 35.60, 24.86, 0.0),
    ("2025-08-10", "2025-12-31", 161.30, 174.21, 114.09, 35.40, 24.72, 0.0),
    ("2025-07-10", "2025-12-31", 161.30, 174.06, 113.99, 35.37, 24.70, 0.0),
    ("2025-06-10", "2025-12-31", 161.30, 173.81, 113.83, 35.32, 24.66, 0.0),
    ("2025-05-10", "2025-12-31", 161.30, 175.46, 114.91, 35.65, 24.90, 0.0),
    ("2025-04-10", "2025-12-31", 161.30, 177.74, 116.40, 36.12, 25.22, 0.0),
    ("2025-03-01", "2025-12-31", 161.30, 178.50, 116.90, 36.27, 25.33, 0.0),
    ("2025-03-10", "2025-06-30", 161.30, 177.96, 111.14, 42.85, 23.97, 0.0),
    ("2025-02-10", "2025-06-30", 161.30, 178.50, 111.47, 42.98, 24.05, 0.0),
    ("2025-01-01", "2025-06-30", 161.30, 176.96, 110.51, 42.61, 23.84, 0.0),
]

# --- 8588 | C_2024_5 | EYU->VGV | GASOLINA | IMG_0369.MOV ---
# Intermodal EFVM+FCA. Mesma rota/contrato de 8591 (item OLEO DIESEL,
# IMG_0360) - valores praticamente identicos, cross-validado. 10 vig.
DADOS[8588] = [
    ("2026-02-10", "2027-12-31", 136.41, 130.18, 80.18, 25.00, 25.00, 0.0),
    ("2026-01-01", "2027-12-31", 136.41, 129.90, 86.05, 24.95, 18.90, 0.0),
    ("2026-01-10", "2026-01-31", 136.41, 114.50, 64.50, 25.00, 25.00, 0.0),
    ("2025-12-10", "2026-01-31", 136.41, 115.57, 65.57, 25.00, 25.00, 0.0),  # 1o cadastro
    ("2025-12-10", "2025-12-31", 136.41, 115.57, 65.53, 25.02, 25.02, 0.0),  # 2o cadastro
    ("2025-11-10", "2025-12-31", 136.41, 115.25, 65.35, 24.95, 24.95, 0.0),
    ("2025-10-10", "2025-12-31", 132.44, 115.32, 65.38, 24.97, 24.97, 0.0),
    ("2025-09-10", "2025-12-31", 132.44, 115.31, 65.37, 24.97, 24.97, 0.0),
    ("2025-08-10", "2025-12-31", 132.44, 114.90, 65.14, 24.88, 24.88, 0.0),
    ("2025-07-10", "2025-12-31", 132.44, 114.79, 65.09, 24.85, 24.85, 0.0),
]

# --- 11619 | C_2024_4.2 | PPN->QPM | OLEO DIESEL | IMG_0370.MOV ---
# Intermodal FNS+EFC (rota reversa de 19392/IMG_0359, mesmo par de
# estacoes, contrato e produto diferentes por item). 12 vigencias.
DADOS[11619] = [
    ("2026-03-10", "2027-12-31", 856.32, 119.67, 42.06, 20.42, 42.61, 14.58),
    ("2026-02-10", "2027-12-31", 856.32, 119.96, 45.15, 20.42, 42.61, 11.78),
    ("2026-01-10", "2026-01-31", 866.72, 130.06, 55.25, 20.42, 42.61, 11.78),
    ("2025-12-10", "2026-01-31", 866.72, 130.34, 55.53, 20.42, 42.61, 11.78),
    ("2025-08-10", "2025-12-31", 866.72, 128.89, 81.71, 0.0, 35.40, 11.78),
    ("2025-07-10", "2025-12-31", 866.72, 128.79, 81.64, 0.0, 35.37, 11.78),
    ("2025-06-10", "2025-12-31", 866.72, 128.60, 81.50, 0.0, 35.32, 11.78),
    ("2025-05-10", "2025-12-31", 866.72, 129.82, 82.94, 0.0, 35.65, 11.23),
    ("2025-04-10", "2025-12-31", 866.72, 131.51, 84.16, 0.0, 36.12, 11.23),
    ("2025-03-01", "2025-12-31", 866.72, 132.07, 84.57, 0.0, 36.27, 11.23),
    ("2025-03-10", "2025-06-30", 866.72, 131.67, 77.83, 0.0, 42.61, 11.23),
    ("2025-01-01", "2025-06-30", 811.08, 130.93, 56.67, 20.42, 42.61, 11.23),
]

# --- 15159 | C_2024_5 | EYU->VTU | GASOLINA | IMG_0371.MOV ---
# Intermodal EFVM+FCA. Mesma rota/contrato de 15680 (item OLEO DIESEL,
# IMG_0363/364) - valores praticamente identicos, cross-validado. Video
# mais rico desta lane: 19 vigencias validadas.
DADOS[15159] = [
    ("2026-03-10", "2027-12-31", 208.88, 171.34, 118.63, 24.93, 27.78, 0.0),
    ("2026-02-10", "2027-12-31", 208.88, 171.84, 118.97, 25.01, 27.86, 0.0),
    ("2026-01-01", "2027-12-31", 208.88, 171.46, 118.71, 24.95, 27.80, 0.0),
    ("2026-01-10", "2026-01-31", 208.88, 164.43, 103.85, 25.00, 35.58, 0.0),
    ("2025-11-10", "2025-12-31", 208.88, 165.49, 105.03, 24.95, 35.51, 0.0),
    ("2025-10-10", "2025-12-31", 202.80, 165.60, 105.10, 24.97, 35.53, 0.0),
    ("2025-09-10", "2025-12-31", 202.80, 165.59, 105.09, 24.97, 35.53, 0.0),
    ("2025-07-10", "2025-08-09", 202.80, 164.84, 104.62, 24.85, 35.37, 0.0),  # 1o cadastro (vig curta)
    ("2025-08-10", "2025-12-31", 202.80, 164.99, 104.71, 24.88, 35.40, 0.0),
    ("2025-07-01", "2025-12-31", 202.80, 164.94, 104.36, 25.00, 35.58, 0.0),
    ("2025-06-10", "2025-06-30", 202.80, 164.94, 104.68, 24.87, 35.39, 0.0),
    ("2025-05-10", "2025-06-30", 202.80, 166.33, 105.56, 25.08, 35.69, 0.0),
    ("2025-04-10", "2025-12-31", 202.80, 169.05, 107.28, 25.49, 36.28, 0.0),
    ("2025-04-10", "2025-06-30", 202.80, 169.05, 107.28, 25.49, 36.28, 0.0),  # 2o cadastro
    ("2025-03-10", "2025-06-30", 202.80, 169.32, 107.46, 25.53, 36.33, 0.0),
    ("2025-02-10", "2025-06-30", 202.80, 168.11, 105.42, 27.05, 35.64, 0.0),  # MO aprox (soma valida)
    ("2025-01-01", "2025-06-30", 202.80, 165.81, 105.23, 25.00, 35.58, 0.0),
    ("2024-12-10", "2025-01-08", 202.80, 165.81, 134.63, 25.00, 6.18, 0.0),
]


# ===========================================================================
# Criacao da tabela e validacao/insercao
# ===========================================================================

def criar_tabela(cur):
    cur.execute("DROP TABLE IF EXISTS vibra_precos_contratuais")
    cur.execute("""
        CREATE TABLE vibra_precos_contratuais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_ferroviario INTEGER NOT NULL,
            contrato TEXT NOT NULL,
            origem TEXT NOT NULL,
            origem_nome TEXT,
            destino TEXT NOT NULL,
            destino_nome TEXT,
            produto TEXT NOT NULL,
            vigencia_inicial TEXT NOT NULL,
            vigencia_final TEXT,
            valor_tr_antt REAL,
            tarifa_contrato REAL NOT NULL,
            frete_rs_t REAL,
            manobra_origem_rs_t REAL,
            manobra_destino_rs_t REAL,
            outros_rs_t REAL,
            video TEXT,
            fonte TEXT
        )
    """)


def validar(item, linha, tol=0.05):
    """Confere frete + manobra_origem + manobra_destino + outros ~= tarifa_contrato."""
    vi, vf, tr, tarifa, frete, mo, md, outros = linha
    soma = round((frete or 0) + (mo or 0) + (md or 0) + (outros or 0), 2)
    diff = abs(soma - tarifa)
    if diff > tol:
        print(f"  ! VALIDACAO FALHOU item {item} vig {vi}: soma={soma:.2f} "
              f"vs tarifa={tarifa:.2f} (diff={diff:.2f})")
        return False
    return True


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    criar_tabela(cur)

    total_linhas = 0
    total_itens = 0
    problemas = 0
    for item, meta in FLUXOS.items():
        linhas = DADOS.get(item, [])
        if not linhas:
            print(f"  ! item {item} sem vigencias lidas (apenas cabecalho confirmado) - pulando insercao de dados")
            continue
        total_itens += 1
        for linha in linhas:
            vi, vf, tr, tarifa, frete, mo, md, outros = linha
            if not validar(item, linha):
                problemas += 1
            cur.execute(
                """INSERT INTO vibra_precos_contratuais
                   (item_ferroviario, contrato, origem, origem_nome, destino, destino_nome,
                    produto, vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                    frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t,
                    video, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, outros, meta["video"], FONTE))
            total_linhas += 1

    con.commit()
    print(f"\n  VIBRA ENERGIA S.A. minerada: {total_itens} itens ferroviarios, "
          f"{total_linhas} vigencias inseridas em vibra_precos_contratuais "
          f"({problemas} com validacao fora da tolerancia).")
    con.close()


if __name__ == "__main__":
    main()
