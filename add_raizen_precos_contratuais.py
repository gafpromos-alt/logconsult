#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_raizen_precos_contratuais.py

Cria/recria a tabela `raizen_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos fluxos
ferroviarios da RAIZEN COMBUSTIVEIS SA, minerado dos videos de tela do
F-LINK (flink.vli.digital, tela "Item Ferroviario > Preco", secao
"PRECOS CONTRATUAIS"). Um video por item ferroviario (alguns itens tem
video duplicado/re-gravado, usado apenas para conferencia cruzada).

Uma linha por (item ferroviario x vigencia/reajuste).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente.

Fonte: F-LINK Precos Contratuais (IMG_0405 a IMG_0420.MOV, exceto 415 -
nao fornecido) - historico de reajuste RAIZEN, contrato C_2022_24.

Cliente confirmado no cabecalho de tela (video 412): RAIZEN COMBUSTIVEIS SA.
Vigencia do contrato (todos os itens): 01/04/2022 a 31/03/2027.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0405-0420.MOV, exceto 415) - historico de reajuste RAIZEN"
VIGENCIA_CONTRATO = ("2022-04-01", "2027-03-31")
CONTRATO = "C_2022_24"

# ---------------------------------------------------------------------------
# Metadados de cada item ferroviario (confirmados no cabecalho de cada video
# e cruzados com a tela "Formalizacao" - lista mestre de itens RAIZEN, video
# 418, frames finais)
# ---------------------------------------------------------------------------
ITENS = {
    41353: dict(origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", ferrovias="FNS+EFC(DP)", video="IMG_0405.MOV"),
    41355: dict(origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="OLEO DIESEL", ferrovias="FNS+EFC(DP)", video="IMG_0407.MOV"),
    41352: dict(origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="ALCOOL", ferrovias="FNS+EFC(DP)", video="IMG_0414.MOV"),
    41369: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VPN", destino_nome="PEDRO NOLASCO",
                produto="OLEO DIESEL", ferrovias="FCA+EFVM", video="IMG_0406.MOV"),
    41358: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VOV", destino_nome="GOVERNADOR VALADARES",
                produto="OLEO DIESEL", ferrovias="FCA+EFVM", video="IMG_0410.MOV"),
    41356: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VGV", destino_nome="GOVERNADOR VALADARES",
                produto="GASOLINA", ferrovias="FCA+EFVM", video="IMG_0412.MOV"),
    41367: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VPN", destino_nome="PEDRO NOLASCO",
                produto="GASOLINA", ferrovias="FCA+EFVM", video="IMG_0413.MOV"),
    41360: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="GASOLINA", ferrovias="FCA+EFVM", video="IMG_0416.MOV"),
    41362: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="OLEO DIESEL", ferrovias="FCA+EFVM", video="IMG_0417.MOV"),
    41373: dict(origem="VPN", origem_nome="PEDRO NOLASCO",
                destino="VTU", destino_nome="TUBARAO",
                produto="OLEO DIESEL", ferrovias="EFVM", video="IMG_0418.MOV"),
    40059: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VTU", destino_nome="TUBARAO",
                produto="OLEO DIESEL", ferrovias="FCA+EFVM",
                video="IMG_0419.MOV",
                obs="item legado (substituido por 41362 na mesma rota)"),
    40063: dict(origem="EYU", origem_nome="EMBIRUCU",
                destino="VPN", destino_nome="PEDRO NOLASCO",
                produto="OLEO DIESEL", ferrovias="FCA+EFVM",
                video="IMG_0420.MOV",
                obs="item legado (substituido por 41369 na mesma rota)"),
}

# Videos IMG_0408, 0409, 0411 sao re-gravacoes (mesmo item/mesma tela) dos
# itens 41369, 41355 e 41358 respectivamente - usados apenas para conferencia
# cruzada dos valores, nao geram linhas adicionais.

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (data_cadastro, vigencia_inicial, vigencia_final, valor_tr_antt,
#    tarifa_contrato, tarifa_faturamento, frete_rs_t, frete_detalhe,
#    manobra_origem_rs_t, manobra_destino_rs_t, direito_passagem_rs_t)
# Datas em YYYY-MM-DD (ou YYYY-MM-DD HH:MM:SS para data_cadastro). Valores em
# R$/t. direito_passagem_rs_t = None quando o item nao tem esse servico.
# frete_rs_t = soma de todas as linhas de FRETE (1 ou 2 trechos, conforme
# frete_detalhe). Validado: frete + MO + MD + (DP ou 0) == tarifa_contrato.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 41353 | PPN->QPM | OLEO DIESEL | FNS + direito de passagem EFC ---
DADOS[41353] = [
    ("2026-08-29 11:15:47", "2026-07-10", "2027-03-31", 856.32, 101.99, 101.99, 47.09, "FNS 47,09", 0.01, 42.61, 12.28),
    ("2026-06-08 09:19:59", "2026-03-10", "2026-04-09", 856.32, 101.98, 101.98, 26.67, "FNS 26,67", 20.42, 42.61, 12.28),
    ("2026-05-28 11:01:11", "2026-06-10", "2027-03-31", 856.32, 102.13, 102.13, 26.82, "FNS 26,82", 20.42, 42.61, 12.28),
    ("2026-04-29 14:17:05", "2026-05-10", "2027-03-31", 856.32, 103.18, 103.18, 27.87, "FNS 27,87", 20.42, 42.61, 12.28),
    ("2026-04-10 10:30:54", "2026-04-01", "2026-04-09", 856.32, 100.65, 100.65, 25.34, "FNS 25,34", 20.42, 42.61, 12.28),
    ("2026-04-10 09:17:11", "2026-04-10", "2027-03-31", 856.32, 103.01, 103.01, 27.70, "FNS 27,70", 20.42, 42.61, 12.28),
    ("2026-03-23 09:10:58", "2026-03-10", "2027-03-31", 856.32, 101.98, 101.98, 24.37, "FNS 24,37", 20.42, 42.61, 14.58),
]

# --- 41355 | QPM->PPN | OLEO DIESEL | FNS + direito de passagem EFC ---
# (rota reversa do 41353; ha 2 re-cadastros de curtissima vigencia em 06/2026)
DADOS[41355] = [
    ("2026-07-13 15:47:20", "2026-06-10", "2026-06-30", 856.32, 272.33, 272.33, 197.02, "FNS 197,02", 42.61, 20.42, 12.28),
    ("2026-07-13 15:45:37", "2026-06-01", "2026-06-09", 856.32, 275.09, 275.09, 199.78, "FNS 199,78", 42.61, 20.42, 12.28),
    ("2026-06-29 11:15:42", "2026-07-10", "2027-03-31", 856.32, 266.77, 266.77, 191.46, "FNS 191,46", 42.61, 20.42, 12.28),
    ("2026-05-28 11:01:08", "2026-06-10", "2027-03-31", 856.32, 267.13, 267.13, 227.69, "FNS 227,69", 13.58, 13.58, 12.28),
    ("2026-04-29 14:16:58", "2026-05-10", "2027-03-31", 856.32, 269.89, 269.89, 230.45, "FNS 230,45", 13.58, 13.58, 12.28),
    ("2026-04-15 18:21:14", "2026-03-10", "2026-03-31", 856.32, 271.95, 271.95, 232.51, "FNS 232,51", 13.58, 13.58, 12.28),
    ("2026-04-10 10:35:19", "2026-04-01", "2026-04-09", 856.32, 263.27, 263.27, 223.83, "FNS 223,83", 13.58, 13.58, 12.28),
    ("2026-04-10 09:17:04", "2026-04-10", "2027-03-31", 856.32, 269.44, 269.44, 230.00, "FNS 230,00", 13.58, 13.58, 12.28),
    ("2026-03-23 09:16:37", "2026-03-10", "2027-03-31", 856.32, 266.75, 266.75, 225.01, "FNS 225,01", 13.58, 13.58, 14.58),
]

# --- 41352 | PPN->QPM | ALCOOL | FNS + direito de passagem EFC ---
# (mesma rota do 41353; mesmo padrao de valores, DP menor: 11,54 vs 12,28)
DADOS[41352] = [
    ("2026-06-29 11:16:25", "2026-07-10", "2027-03-31", 635.41, 101.99, 101.99, 47.83, "FNS 47,83", 0.01, 42.61, 11.54),
    ("2026-06-08 09:17:24", "2026-03-10", "2026-04-09", 635.41, 101.98, 101.98, 27.41, "FNS 27,41", 20.42, 42.61, 11.54),
    ("2026-05-28 11:01:32", "2026-06-10", "2027-03-31", 635.41, 102.13, 102.13, 27.56, "FNS 27,56", 20.42, 42.61, 11.54),
    ("2026-04-29 14:17:49", "2026-05-10", "2027-03-31", 635.41, 103.18, 103.18, 28.61, "FNS 28,61", 20.42, 42.61, 11.54),
    ("2026-04-10 10:29:38", "2026-04-01", "2026-04-09", 635.41, 100.65, 100.65, 26.08, "FNS 26,08", 20.42, 42.61, 11.54),
    ("2026-04-10 09:17:12", "2026-04-10", "2027-03-31", 635.41, 103.01, 103.01, 28.44, "FNS 28,44", 20.42, 42.61, 11.54),
    ("2026-03-23 09:09:03", "2026-03-10", "2027-03-31", 635.41, 101.98, 101.98, 24.37, "FNS 24,37", 20.42, 42.61, 14.58),
]

# --- 41369 | EYU->VPN | OLEO DIESEL | FCA + EFVM ---
DADOS[41369] = [
    ("2026-06-29", "2026-07-10", "2027-03-31", 189.41, 239.96, 239.96, 179.38, "EFVM 168,90 + FCA 10,48", 25.00, 35.58, None),
    ("2026-05-28", "2026-06-10", "2027-03-31", 189.41, 239.82, 239.82, 179.24, "EFVM 168,77 + FCA 10,47", 25.00, 35.58, None),
    ("2026-04-29", "2026-05-10", "2027-03-31", 189.41, 240.31, 240.31, 179.73, "EFVM 169,23 + FCA 10,50", 25.00, 35.58, None),
    ("2026-04-10 10:12", "2026-04-01", "2026-04-09", 189.41, 241.55, 241.55, 180.97, "EFVM 170,40 + FCA 10,57", 25.00, 35.58, None),
    ("2026-04-10 09:15", "2026-04-10", "2027-03-31", 189.41, 240.51, 240.51, 179.93, "EFVM 169,42 + FCA 10,51", 25.00, 35.58, None),
    ("2026-03-10", "2026-03-10", "2027-03-31", 189.41, 244.74, 244.74, 184.16, "EFVM 173,41 + FCA 10,75", 25.00, 35.58, None),
]

# --- 41358 | EYU->VOV (Governador Valadares) | OLEO DIESEL | FCA + EFVM ---
DADOS[41358] = [
    ("2026-06-29 11:15:33", "2026-07-10", "2027-03-31", 122.88, 96.43, 96.43, 46.43, "EFVM 41,26 + FCA 5,17", 25.00, 25.00, None),
    ("2026-05-28 11:00:59", "2026-06-10", "2027-03-31", 122.88, 96.37, 96.37, 55.24, "EFVM 49,09 + FCA 6,15", 25.00, 16.13, None),
    ("2026-04-29 14:16:53", "2026-05-10", "2027-03-31", 122.88, 96.57, 96.57, 55.44, "EFVM 49,27 + FCA 6,17", 25.00, 16.13, None),
    ("2026-04-10 10:00:44", "2026-04-01", "2026-04-09", 122.88, 97.07, 97.07, 55.94, "EFVM 49,71 + FCA 6,23", 25.00, 16.13, None),
    ("2026-04-10 09:17:00", "2026-04-10", "2027-03-31", 122.88, 96.65, 96.65, 55.52, "EFVM 49,34 + FCA 6,18", 25.00, 16.13, None),
    ("2026-03-10 15:24:21", "2026-03-10", "2027-03-31", 122.88, 98.35, 98.35, 57.22, "EFVM 50,85 + FCA 6,37", 25.00, 16.13, None),
]

# --- 41356 | EYU->VGV (Governador Valadares) | GASOLINA | FCA + EFVM ---
DADOS[41356] = [
    ("2026-06-29 11:16:18", "2026-07-10", "2027-03-31", 136.41, 96.43, 96.43, 46.43, "EFVM 41,26 + FCA 5,17", 25.00, 25.00, None),
    ("2026-05-28 11:01:29", "2026-06-10", "2027-03-31", 136.41, 96.37, 96.37, 57.55, "EFVM 51,14 + FCA 6,41", 25.00, 13.82, None),
    ("2026-04-29 14:17:47", "2026-05-10", "2027-03-31", 136.41, 96.57, 96.57, 57.75, "EFVM 51,32 + FCA 6,43", 25.00, 13.82, None),
    ("2026-04-10 09:44:35", "2026-04-01", "2026-04-09", 136.41, 97.07, 97.07, 58.25, "EFVM 51,77 + FCA 6,48", 25.00, 13.82, None),
    ("2026-04-10 09:17:08", "2026-04-10", "2027-03-31", 136.41, 96.65, 96.65, 57.83, "EFVM 51,39 + FCA 6,44", 25.00, 13.82, None),
    ("2026-03-10 15:23:16", "2026-03-10", "2027-03-31", 136.41, 98.35, 98.35, 59.53, "EFVM 52,90 + FCA 6,63", 25.00, 13.82, None),
]

# --- 41367 | EYU->VPN | GASOLINA | FCA + EFVM ---
DADOS[41367] = [
    ("2026-06-29 11:16:29", "2026-07-10", "2027-03-31", 209.54, 239.96, 239.96, 179.38, "EFVM 168,90 + FCA 10,48", 25.00, 35.58, None),
    ("2026-05-28 11:01:36", "2026-06-10", "2027-03-31", 209.54, 239.82, 239.82, 179.24, "EFVM 168,77 + FCA 10,47", 25.00, 35.58, None),
    ("2026-04-29 14:17:52", "2026-05-10", "2027-03-31", 209.54, 240.31, 240.31, 179.73, "EFVM 169,23 + FCA 10,50", 25.00, 35.58, None),
    ("2026-04-10 10:10:07", "2026-04-01", "2026-04-09", 209.54, 241.55, 241.55, 180.97, "EFVM 170,40 + FCA 10,57", 25.00, 35.58, None),
    ("2026-04-10 09:17:09", "2026-04-10", "2027-03-31", 209.54, 240.51, 240.51, 179.93, "EFVM 169,42 + FCA 10,51", 25.00, 35.58, None),
    ("2026-03-10 15:47:12", "2026-03-10", "2027-03-31", 209.54, 244.74, 244.74, 184.16, "EFVM 173,41 + FCA 10,75", 25.00, 35.58, None),
]

# --- 41360 | EYU->VTU (Tubarao) | GASOLINA | FCA + EFVM ---
DADOS[41360] = [
    ("2026-06-29 11:15:44", "2026-07-10", "2027-03-31", 208.88, 239.96, 239.96, 179.38, "EFVM 168,85 + FCA 10,53", 25.00, 35.58, None),
    ("2026-05-28 11:01:09", "2026-06-10", "2027-03-31", 208.88, 239.82, 239.82, 179.24, "EFVM 168,72 + FCA 10,52", 25.00, 35.58, None),
    ("2026-04-29 14:17:00", "2026-05-10", "2027-03-31", 208.88, 240.31, 240.31, 179.73, "EFVM 169,18 + FCA 10,55", 25.00, 35.58, None),
    ("2026-04-10 10:03:40", "2026-04-01", "2026-04-09", 208.88, 241.55, 241.55, 180.97, "EFVM 170,35 + FCA 10,62", 25.00, 35.58, None),
    ("2026-04-10 09:16:40", "2026-04-10", "2027-03-31", 208.88, 240.51, 240.51, 179.93, "EFVM 169,37 + FCA 10,56", 25.00, 35.58, None),
    ("2026-03-10 15:43:04", "2026-03-10", "2027-03-31", 208.88, 244.74, 244.74, 184.16, "EFVM 173,35 + FCA 10,81", 25.00, 35.58, None),
]

# --- 41362 | EYU->VTU (Tubarao) | OLEO DIESEL | FCA + EFVM ---
# (mesma tarifa/frete do 41360; so o Valor TR ANTT do produto difere)
DADOS[41362] = [
    ("2026-06-29 11:16:14", "2026-07-10", "2027-03-31", 189.81, 239.96, 239.96, 179.38, "EFVM 168,85 + FCA 10,53", 25.00, 35.58, None),
    ("2026-05-28 11:01:27", "2026-06-10", "2027-03-31", 189.81, 239.82, 239.82, 179.24, "EFVM 168,72 + FCA 10,52", 25.00, 35.58, None),
    ("2026-04-29 14:17:44", "2026-05-10", "2027-03-31", 189.81, 240.31, 240.31, 179.73, "EFVM 169,18 + FCA 10,55", 25.00, 35.58, None),
    ("2026-04-10 10:05:31", "2026-04-01", "2026-04-09", 189.81, 241.55, 241.55, 180.97, "EFVM 170,35 + FCA 10,62", 25.00, 35.58, None),
    ("2026-04-10 09:16:58", "2026-04-10", "2027-03-31", 189.81, 240.51, 240.51, 179.93, "EFVM 169,37 + FCA 10,56", 25.00, 35.58, None),
    ("2026-03-10 15:44:39", "2026-03-10", "2027-03-31", 189.81, 244.74, 244.74, 184.16, "EFVM 173,35 + FCA 10,81", 25.00, 35.58, None),
]

# --- 41373 | VPN->VTU (Tubarao) | OLEO DIESEL | EFVM (unico trecho) ---
DADOS[41373] = [
    ("2026-06-29 11:15:31", "2026-07-10", "2027-03-31", 38.48, 55.81, 55.81, 20.22, "EFVM 20,22", 0.01, 35.58, None),
    ("2026-05-28 11:00:57", "2026-06-10", "2027-03-31", 38.48, 55.78, 55.78, 5.20, "EFVM 5,20", 15.00, 35.58, None),
    ("2026-04-29 14:16:50", "2026-05-10", "2027-03-31", 38.48, 55.89, 55.89, 5.31, "EFVM 5,31", 15.00, 35.58, None),
    ("2026-04-10 10:21:18", "2026-04-01", "2026-04-09", 38.48, 56.18, 56.18, 5.60, "EFVM 5,60", 15.00, 35.58, None),
    ("2026-04-10 09:16:56", "2026-04-10", "2027-03-31", 38.48, 55.94, 55.94, 5.36, "EFVM 5,36", 15.00, 35.58, None),
    ("2026-03-10 15:53:59", "2026-03-10", "2027-03-31", 38.48, 56.92, 56.92, 6.34, "EFVM 6,34", 15.00, 35.58, None),
]

# --- 40059 | EYU->VTU | OLEO DIESEL | FCA + EFVM | item legado (1 vigencia) ---
DADOS[40059] = [
    ("2025-07-11 20:39:05", "2025-07-10", "2027-03-31", 183.31, 243.03, 243.03, 182.45, "EFVM 171,74 + FCA 10,71", 25.00, 35.58, None),
]

# --- 40063 | EYU->VPN | OLEO DIESEL | FCA + EFVM | item legado (1 vigencia) ---
DADOS[40063] = [
    ("2025-07-11 20:52:47", "2025-07-10", "2027-03-31", 183.89, 243.03, 243.03, 182.45, "EFVM 171,79 + FCA 10,66", 25.00, 35.58, None),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + MD + (DP ou 0) == tarifa_contrato (tolerancia 0,05)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            (data_cad, vi, vf, tr, tarifa, tarifa_fat, frete, frete_det,
             mo, md, dp) = ln
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
    cur.execute("DROP TABLE IF EXISTS raizen_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE raizen_precos_contratuais (
            item_ferroviario      INTEGER,
            contrato              TEXT,
            origem                TEXT,
            origem_nome           TEXT,
            destino               TEXT,
            destino_nome          TEXT,
            produto                TEXT,
            data_cadastro          TEXT,
            vigencia_inicial       TEXT,
            vigencia_final         TEXT,
            valor_tr_antt          REAL,
            tarifa_contrato        REAL,
            tarifa_faturamento     REAL,
            frete_rs_t             REAL,
            frete_detalhe          TEXT,
            manobra_origem_rs_t    REAL,
            manobra_destino_rs_t   REAL,
            direito_passagem_rs_t  REAL,
            fonte                  TEXT
        )
        """
    )
    for item, linhas in DADOS.items():
        meta = ITENS[item]
        for (data_cad, vi, vf, tr, tarifa, tarifa_fat, frete, frete_det,
             mo, md, dp) in linhas:
            cur.execute(
                """INSERT INTO raizen_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, CONTRATO, meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 data_cad, vi, vf, tr, tarifa, tarifa_fat, frete, frete_det,
                 mo, md, dp, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM raizen_precos_contratuais").fetchone()[0]
    nitens = cur.execute("SELECT COUNT(DISTINCT item_ferroviario) FROM raizen_precos_contratuais").fetchone()[0]
    print(f"raizen_precos_contratuais criada com {n} linhas ({nitens} itens ferroviarios).")
    conn.close()


if __name__ == "__main__":
    main()
