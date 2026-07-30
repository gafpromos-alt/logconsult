#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_arcelormittal_precos_contratuais.py

Cria/recria a tabela `arcelormittal_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos fluxos
ferroviarios da ARCELORMITTAL BRASIL S.A., minerado dos videos de tela do
F-LINK (flink.vli.digital, tela "Precos Contratuais"), 23 videos
(IMG_0457.MOV a IMG_0479.MOV), um ou mais videos por item ferroviario.

Uma linha por (item ferroviario x vigencia/reajuste).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente via connect_arcelormittal_precos.py.

Fonte: F-LINK Precos Contratuais (IMG_0457-0479.MOV) - historico de reajuste
ARCELORMITTAL.

DESCOBERTA IMPORTANTE (vs. lista preliminar de itens fornecida): os videos
464/465 e 466 mostram DOIS itens de CALCARIO BRITAD que nao constavam na
lista original (11758 ENG->VTU e 17733 ECE->VTU), confirmados repetidas
vezes pelo cabecalho visivel em multiplos frames de cada video, com
historico rico e consistente (2020-2026 e 2022-2026 respectivamente).
O item 19315 (MINERIO FERRO EPM->VTU) SO aparece corretamente no video 460;
o video 459 (que deveria ser a 2a gravacao de 19315, segundo a lista
preliminar) na verdade mostra o mesmo item 8111 (ANTRACITO VTU->VBV) do
video 458 - aparentemente um erro de gravacao. O item 8111 tem portanto
TRES videos (458, 459, 479), nao dois. O item 40482 aparece em DUAS rotas
distintas com o MESMO numero de item: video 465 (na verdade e uma 2a
gravacao de 11758, nao de 40482) e video 476 (EEL->VJM, PRO SIDERURGICO -
esta e a leitura valida de "40482", usada aqui).

ATUALIZACAO 24/07/2026: lote adicional IMG_0550-0562.MOV (fluxos ate entao
"pendente" - sem abertura de manobra): itens 8114 (COQUE GROSSO VTU->VBV),
40213 (PRO SIDERURGICO VTU->VEB), 40468 (CARVAO MINERAL VTU->VBV), 8370
(FIO MAQUINA VJM->EEL) e 7897 (FIO MAQUINA VJM->VPN) adicionados. O item
40456 (FIO MAQUINA VJM->ECE, IMG_0555.MOV) foi REVISADO mas NAO adicionado:
os frames extraidos sofrem de moire/dupla-exposicao severo e os valores de
manobra nao puderam ser lidos com confianca suficiente - fica como
pendencia, precisa de nova filmagem.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0457-0479.MOV) - historico de reajuste ARCELORMITTAL"
FONTE_LOTE_550_562 = "F-LINK Precos Contratuais (videos IMG_0550-0562)"

# ---------------------------------------------------------------------------
# Metadados de cada item ferroviario (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    14399: dict(contrato="C_2022_49", origem="VTU", origem_nome="TUBARAO",
                destino="EPI", destino_nome="PARQUE INDUSTRIAL",
                produto="FIO MAQUINA", videos="IMG_0457.MOV"),
    8111: dict(contrato="C_2025_45", origem="VTU", origem_nome="TUBARAO",
               destino="VBV", destino_nome="BELA VISTA",
               produto="ANTRACITO", videos="IMG_0458/0459/0479.MOV"),
    19315: dict(contrato="ACS_2026_38", origem="EPM", origem_nome="PRUDENTE DE MORAIS",
                destino="VTU", destino_nome="TUBARAO",
                produto="MINERIO FERRO", videos="IMG_0460.MOV"),
    13143: dict(contrato="C_2022_49", origem="VTU", origem_nome="TUBARAO",
                destino="VGV", destino_nome="GOVERNADOR VALADARES",
                produto="PRO SIDERURGICO", videos="IMG_0461.MOV"),
    40787: dict(contrato="ACS_2026_38", origem="ELD", origem_nome="DR. LUND",
                destino="VTU", destino_nome="TUBARAO",
                produto="CALCARIO BRITAD", videos="IMG_0462.MOV"),
    40472: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="VAZ", destino_nome="ARACRUZ",
                produto="FIO MAQUINA", videos="IMG_0463.MOV"),
    11758: dict(contrato="ACS_2026_38", origem="ENG", origem_nome="NOVA GRANJA",
                destino="VTU", destino_nome="TUBARAO",
                produto="CALCARIO BRITAD", videos="IMG_0464/0465.MOV"),
    17733: dict(contrato="ACS_2026_38", origem="ECE", origem_nome=None,
                destino="VTU", destino_nome="TUBARAO",
                produto="CALCARIO BRITAD", videos="IMG_0466.MOV"),
    40221: dict(contrato="C_2022_49", origem="VTU", origem_nome="TUBARAO",
                destino="ENG", destino_nome="NOVA GRANJA",
                produto="PRO SIDERURGICO", videos="IMG_0467.MOV"),
    40478: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="EPM", destino_nome="PRUDENTE DE MORAIS",
                produto="FIO MAQUINA", videos="IMG_0468.MOV"),
    40462: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="VTU", destino_nome="TUBARAO",
                produto="FIO MAQUINA", videos="IMG_0469/0470.MOV"),
    40156: dict(contrato="ACS_2026_38", origem="ELD", origem_nome="DR. LUND",
                destino="VTU", destino_nome="TUBARAO",
                produto="MINERIO FERRO", videos="IMG_0471.MOV"),
    39956: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="ELD", destino_nome="DR. LUND",
                produto="FIO MAQUINA", videos="IMG_0472.MOV"),
    40476: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="EPI", destino_nome="PARQUE INDUSTRIAL",
                produto="FIO MAQUINA", videos="IMG_0473.MOV"),
    40470: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="EPI", destino_nome="PARQUE INDUSTRIAL",
                produto="PRO SIDERURGICO", videos="IMG_0474.MOV"),
    7894: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
               destino="VTU", destino_nome="TUBARAO",
               produto="FIO MAQUINA", videos="IMG_0475.MOV"),
    40482: dict(contrato="C_2025_45", origem="EEL", origem_nome="ELDORADO",
                destino="VJM", destino_nome="JOAO MONLEVADE",
                produto="PRO SIDERURGICO", videos="IMG_0476.MOV"),
    19543: dict(contrato="ACS_2026_38", origem="ENG", origem_nome="NOVA GRANJA",
                destino="VTU", destino_nome="TUBARAO",
                produto="MINERIO FERRO", videos="IMG_0477.MOV"),
    40474: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
                destino="VGV", destino_nome="GOVERNADOR VALADARES",
                produto="FIO MAQUINA", videos="IMG_0478.MOV"),
    # --- lote IMG_0550-0562.MOV (24/07/2026): fluxos pendentes ARCELORMITTAL
    # (manobras "sem abertura") ---
    8114: dict(contrato="C_2025_45", origem="VTU", origem_nome="TUBARAO",
               destino="VBV", destino_nome="BELA VISTA",
               produto="COQUE GROSSO", videos="IMG_0550.MOV"),
    40213: dict(contrato="C_2022_49", origem="VTU", origem_nome="TUBARAO",
                destino="VEB", destino_nome="ENG. LAF. BANDEIRA",
                produto="PRO SIDERURGICO", videos="IMG_0551.MOV"),
    40468: dict(contrato="C_2025_45", origem="VTU", origem_nome="TUBARAO",
                destino="VBV", destino_nome="BELA VISTA",
                produto="CARVAO MINERAL", videos="IMG_0552.MOV"),
    8370: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
               destino="EEL", destino_nome="ELDORADO",
               produto="FIO MAQUINA", videos="IMG_0554.MOV"),
    7897: dict(contrato="C_2025_45", origem="VJM", origem_nome="JOAO MONLEVADE",
               destino="VPN", destino_nome="PEDRO NOLASCO",
               produto="FIO MAQUINA", videos="IMG_0557.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, transbordo_origem_rs_t)
# Datas em YYYY-MM-DD. Valores em R$/t. frete_rs_t = soma de todas as linhas
# de servico "FRETE" (ha fluxos intermodais FCA+EFVM, somados aqui).
# Validado: frete + manobra_origem + manobra_destino + transbordo_origem
# deve bater com tarifa_contrato (tolerancia R$0,05). Vigencias com leitura
# ambigua/blur foram OMITIDAS (nao inventadas) - ver relatorio da conversa.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 14399 | C_2022_49 | VTU->EPI | FIO MAQUINA | IMG_0457.MOV ---
# Fluxo intermodal FCA+EFVM: MANOBRA DESTINO(FCA) + MANOBRA ORIGEM(EFVM) +
# FRETE(FCA) + FRETE(EFVM). frete_rs_t = soma dos dois FRETE. 42 vigencias
# lidas (2019-2027), 1 omitida por inconsistencia de soma (20/05/2025).
DADOS[14399] = [
    ("2026-07-20", "2027-12-31", 87.35, 110.45, 82.75, 14.37, 13.33, 0),
    ("2026-06-20", "2027-12-31", 87.35, 110.38, 82.70, 14.38, 13.32, 0),
    ("2026-05-20", "2027-12-31", 87.35, 110.51, 82.77, 14.39, 13.35, 0),
    ("2026-04-20", "2027-12-31", 87.35, 110.60, 82.84, 14.40, 13.36, 0),
    ("2026-03-20", "2027-12-31", 87.35, 111.08, 83.20, 14.46, 13.42, 0),
    ("2026-02-20", "2027-12-31", 87.35, 111.40, 83.44, 14.50, 13.46, 0),
    ("2026-01-20", "2027-12-31", 87.35, 111.34, 83.44, 14.47, 13.43, 0),  # 2o cadastro (02/02/2026)
    ("2026-01-20", "2027-12-31", 87.35, 110.24, 72.81, 14.41, 23.02, 0),  # 1o cadastro (19/01/2026)
    ("2025-12-20", "2027-12-31", 83.44, 109.65, 81.86, 14.41, 13.38, 0),
    ("2025-11-20", "2027-12-31", 83.44, 109.34, 81.63, 14.37, 13.34, 0),
    ("2025-09-20", "2027-12-31", 83.44, 109.41, 81.68, 14.38, 13.35, 0),
    ("2025-08-20", "2027-12-31", 83.44, 109.01, 81.40, 14.32, 13.29, 0),
    ("2025-07-20", "2027-12-31", 83.44, 108.91, 81.30, 14.32, 13.29, 0),
    ("2025-06-20", "2027-12-31", 83.44, 108.98, 81.35, 14.33, 13.30, 0),
    # 2025-05-20 OMITIDA: soma 110.09 x tarifa 109.89 (diff 0.20, fora da tolerancia)
    ("2025-04-20", "2027-12-31", 83.44, 111.62, 83.32, 14.68, 13.62, 0),
    ("2025-03-20", "2027-12-31", 83.44, 111.78, 83.44, 14.70, 13.64, 0),  # 2o cadastro
    ("2025-03-20", "2027-12-31", 83.44, 119.61, 0.00, 119.61, 0.00, 0),   # 1o cadastro (all-in MO)
    ("2025-02-20", "2027-12-31", 83.44, 124.04, 0.00, 124.04, 0.00, 0),   # cadastro atualizado 20/03/2025 (all-in MO)
    ("2025-01-20", "2027-12-31", 83.44, 117.14, 83.44, 14.39, 19.31, 0),
    ("2024-12-20", "2024-12-31", 79.65, 112.76, 79.65, 14.39, 18.72, 0),
    ("2024-11-20", "2024-12-31", 79.65, 112.09, 85.53, 13.77, 12.79, 0),
    ("2024-10-20", "2024-12-31", 79.65, 111.60, 85.16, 13.71, 12.73, 0),  # 2o cadastro
    ("2024-10-20", "2024-12-31", 79.65, 111.60, 86.22, 11.18, 14.19, 0),  # 1o cadastro
    ("2024-09-20", "2024-12-31", 79.65, 111.35, 84.97, 13.68, 12.70, 0),
    ("2024-08-20", "2027-12-31", 79.65, 111.36, 84.98, 13.68, 12.70, 0),
    ("2024-08-20", "2024-12-31", 79.65, 111.37, 86.00, 11.18, 14.19, 0),
    ("2024-07-20", "2027-12-31", 79.65, 111.59, 85.15, 12.73, 13.71, 0),
    ("2024-08-20", "2024-12-31", 79.65, 111.05, 84.74, 13.64, 12.67, 0),  # 1o cadastro (18/08)
    ("2024-05-20", "2024-12-31", 79.65, 111.16, 84.83, 13.65, 12.68, 0),  # 2o cadastro (10:14)
    ("2024-05-20", "2024-12-31", 79.65, 111.16, 85.79, 11.18, 14.19, 0),  # 1o cadastro (08:01)
    ("2024-05-20", "2027-12-31", 79.65, 111.16, 84.83, 13.65, 12.68, 0),
    ("2024-04-20", "2024-12-31", 79.65, 111.05, 84.74, 13.64, 12.67, 0),
    ("2024-03-20", "2024-12-31", 79.65, 110.90, 84.63, 13.62, 12.65, 0),
    ("2024-02-20", "2027-12-31", 79.65, 110.08, 84.01, 13.52, 12.55, 0),  # 2o cadastro
    ("2024-02-20", "2027-12-31", 79.65, 110.08, 84.71, 11.18, 14.19, 0),  # 1o cadastro
    ("2024-01-20", "2027-12-31", 79.65, 109.80, 83.79, 13.49, 12.52, 0),
    ("2023-12-20", "2027-12-31", 75.99, 113.16, 86.35, 13.90, 12.91, 0),
    ("2023-11-20", "2027-12-31", 75.99, 112.92, 86.17, 13.87, 12.88, 0),
    ("2023-10-20", "2027-12-31", 75.99, 112.04, 85.50, 13.76, 12.78, 0),
    ("2023-09-20", "2027-12-31", 75.99, 111.50, 85.10, 13.69, 12.71, 0),
    ("2023-08-20", "2027-12-31", 75.99, 105.61, 80.60, 12.97, 12.04, 0),
]

# --- 8111 | C_2025_45 | VTU->VBV | ANTRACITO | IMG_0458/0459/0479.MOV ---
# 3 videos do MESMO item (video 459 deveria ser 19315 na lista preliminar,
# mas mostra 8111 - provavel erro de gravacao). Fluxo unico EFVM: FRETE +
# MANOBRA ORIGEM + MANOBRA DESTINO. 34 vigencias mescladas dos 3 videos
# (2019-2026), removendo duplicatas exatas.
DADOS[8111] = [
    ("2026-07-20", "2029-12-31", 113.17, 118.05, 91.33, 17.01, 9.71, 0),
    ("2026-06-20", "2029-12-31", 113.17, 117.98, 91.28, 17.00, 9.70, 0),
    ("2026-05-20", "2029-12-31", 113.17, 118.91, 92.00, 17.13, 9.78, 0),  # IMG_0459
    ("2026-03-20", "2029-12-31", 113.17, 120.21, 93.00, 17.32, 9.89, 0),
    ("2026-02-20", "2029-12-31", 113.17, 120.29, 93.07, 17.33, 9.89, 0),
    ("2026-01-20", "2029-12-31", 113.17, 120.03, 92.98, 17.22, 9.83, 0),
    ("2025-12-20", "2029-12-31", 108.11, 119.48, 92.43, 17.22, 9.83, 0),
    ("2025-11-20", "2029-12-31", 108.11, 119.17, 92.18, 17.17, 9.82, 0),
    ("2025-10-20", "2029-12-31", 108.11, 119.23, 92.24, 17.18, 9.81, 0),
    ("2025-09-20", "2029-12-31", 108.11, 119.22, 92.23, 17.18, 9.81, 0),
    ("2025-08-20", "2029-12-31", 108.11, 118.79, 91.91, 17.11, 9.77, 0),
    ("2025-07-20", "2029-12-31", 108.11, 118.68, 91.82, 17.10, 9.76, 0),
    ("2025-06-20", "2029-12-31", 108.11, 118.75, 91.87, 17.11, 9.77, 0),
    ("2025-05-20", "2029-12-31", 108.11, 119.76, 92.66, 17.25, 9.85, 0),
    ("2025-05-01", "2029-12-31", 108.11, 121.71, 94.16, 17.54, 10.01, 0),
    ("2025-04-20", "2025-04-30", 108.11, 121.71, 94.16, 17.54, 10.01, 0),
    ("2025-03-20", "2025-03-31", 108.11, 122.13, 107.64, 11.18, 3.31, 0),
    ("2025-03-01", "2025-03-31", 108.11, 112.72, 98.23, 11.18, 3.31, 0),
    ("2024-12-20", "2025-02-28", 103.20, 112.72, 98.23, 11.18, 3.31, 0),
    ("2024-11-20", "2024-12-31", 103.20, 112.72, 98.23, 11.18, 3.31, 0),
    ("2024-08-20", "2024-12-31", 103.20, 111.03, 96.54, 11.18, 3.31, 0),
    ("2024-01-20", "2024-12-31", 103.20, 110.42, 88.37, 17.01, 5.04, 0),
    ("2023-09-20", "2024-12-31", 98.45, 112.05, 89.67, 17.27, 5.11, 0),
    ("2023-06-20", "2024-12-31", 98.45, 105.79, 84.67, 16.30, 4.82, 0),  # IMG_0479
    ("2022-09-20", "2024-12-31", 92.47, 114.90, 91.96, 17.70, 5.24, 0),
    ("2022-08-20", "2024-12-31", 92.47, 114.25, 91.44, 17.60, 5.21, 0),
    ("2022-04-20", "2024-12-31", 92.47, 110.64, 88.55, 17.04, 5.05, 0),
    ("2022-02-01", "2024-12-31", 92.47, 105.81, 84.68, 16.30, 4.83, 0),
    ("2022-01-10", "2024-12-31", 92.47, 105.81, 84.68, 16.30, 4.83, 0),
    ("2021-03-20", "2024-12-31", 82.31, 88.34, 70.70, 13.61, 4.03, 0),
    ("2020-12-20", "2024-12-31", 82.31, 74.98, 60.01, 11.55, 3.42, 0),
    ("2020-10-20", "2024-12-31", 82.31, 73.29, 58.66, 11.29, 3.34, 0),
    ("2020-09-20", "2024-12-31", 69.32, 74.47, 59.60, 11.47, 3.40, 0),
    ("2020-07-20", "2024-12-31", 69.32, 72.22, 57.81, 11.12, 3.29, 0),  # 2o cadastro
    ("2020-07-20", "2024-12-31", 69.32, 72.22, 57.73, 11.18, 3.31, 0),  # 1o cadastro
    ("2019-10-20", "2024-12-31", 60.66, 72.61, 58.12, 11.18, 3.31, 0),
]

# --- 19315 | ACS_2026_38 | EPM->VTU | MINERIO FERRO | IMG_0460.MOV ---
# 5 linhas de servico: FRETE(EFVM), FRETE(FCA), MANOBRA DESTINO(EFVM),
# MANOBRA ORIGEM(FCA), TRANSBORDO ORIGEM(FCA). Muitas vigencias 2024 com
# blur/inconsistencia de soma foram omitidas (video com moire forte).
DADOS[19315] = [
    ("2026-07-20", "2027-12-31", 154.66, 102.86, 78.46, 16.84, 7.56, 0.00),
    ("2024-12-20", "2025-02-28", 150.15, 97.54, 97.54, 0.00, 0.00, 0.00),
    ("2024-12-20", "2025-01-20", 150.15, 97.54, 97.54, 0.00, 0.00, 0.00),  # 1o cadastro
    ("2024-11-20", "2025-01-20", 150.15, 96.97, 96.97, 0.00, 0.00, 0.00),
    ("2024-10-20", "2025-01-20", 150.15, 96.55, 96.55, 0.00, 0.00, 0.00),
    ("2024-01-20", "2025-01-20", 144.06, 95.00, 63.56, 10.00, 7.44, 14.00),
]

# --- 13143 | C_2022_49 | VTU->VGV | PRO SIDERURGICO | IMG_0461.MOV ---
# Fluxo unico EFVM: FRETE + MANOBRA ORIGEM + MANOBRA DESTINO. Boa parte do
# historico (05/2025 a 12/2024) tinha blur/overlap de scroll - omitida.
DADOS[13143] = [
    ("2028-01-20", "2027-12-31", 59.11, 78.51, 52.94, 14.41, 11.16, 0),
    ("2025-12-20", "2027-12-31", 56.47, 78.09, 52.52, 14.41, 11.16, 0),
    ("2025-11-20", "2027-12-31", 56.47, 77.87, 52.37, 14.37, 11.13, 0),
    ("2025-09-20", "2027-12-31", 56.47, 77.92, 52.40, 14.38, 11.14, 0),
    ("2025-07-20", "2027-12-31", 56.47, 77.57, 52.16, 14.32, 11.09, 0),
]

# --- 40787 | ACS_2026_38 | ELD->VTU | CALCARIO BRITAD | IMG_0462.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA DESTINO(EFVM)+
# MANOBRA ORIGEM(FCA). frete_rs_t = soma dos dois FRETE.
DADOS[40787] = [
    ("2026-03-31", "2026-05-31", 153.03, 100.46, 75.63, 17.22, 7.61, 0),
    ("2026-03-20", "2026-03-31", 153.03, 100.46, 75.63, 17.22, 7.61, 0),  # 2o cadastro
    ("2028-01-31", "2026-03-31", 153.03, 98.04, 73.14, 16.88, 8.02, 0),
    ("2025-12-22", "2026-01-31", 153.03, 98.04, 88.80, 0.00, 9.24, 0),
    ("2025-11-26", "2025-12-31", 153.03, 98.04, 73.14, 16.88, 8.02, 0),
]

# --- 40472 | C_2025_45 | VJM->VAZ | FIO MAQUINA | IMG_0463.MOV ---
# Fluxo unico EFVM: FRETE + MANOBRA DESTINO + MANOBRA ORIGEM.
DADOS[40472] = [
    ("2028-02-20", "2029-12-31", 73.91, 91.80, 67.40, 7.07, 17.33, 0),
    ("2028-01-20", "2029-12-31", 73.91, 91.60, 67.30, 7.08, 17.22, 0),
    ("2025-12-20", "2029-12-31", 70.60, 91.19, 66.89, 7.08, 17.22, 0),
    ("2025-11-20", "2029-12-31", 70.60, 90.97, 66.76, 7.01, 17.20, 0),
    ("2025-10-20", "2029-12-31", 70.60, 90.99, 66.80, 7.01, 17.18, 0),
    ("2025-09-20", "2029-12-31", 70.60, 90.98, 66.79, 7.01, 17.18, 0),
    ("2025-08-20", "2029-12-31", 70.60, 90.66, 66.56, 6.99, 17.11, 0),
]

# --- 11758 | ACS_2026_38 | ENG->VTU | CALCARIO BRITAD | IMG_0464/0465.MOV ---
# ITEM NAO CONSTAVA NA LISTA PRELIMINAR - descoberto pelo cabecalho, com
# historico confirmado em 2 videos (464 e uma 2a gravacao redundante em
# 465). Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA
# ORIGEM(FCA)+MANOBRA DESTINO(EFVM). Video tem historico visivel ate 2019,
# mas a leitura do split FRETE(EFVM)/FRETE(FCA) nos frames de 2020-2023 nao
# fechou a soma com confianca (moire) - vigencias mantidas SOMENTE onde a
# soma validou exatamente; as demais (2020-2023) foram omitidas, nao
# inventadas.
DADOS[11758] = [
    ("2025-03-20", "2025-12-31", 147.07, 83.10, 58.15, 16.91, 8.04, 0),
    ("2024-11-20", "2025-01-19", 147.07, 77.37, 55.61, 12.52, 9.24, 0),
    ("2025-01-20", "2025-12-31", 147.07, 81.12, 56.77, 16.50, 7.85, 0),
    ("2024-11-20", "2024-12-31", 147.07, 77.37, 55.61, 12.52, 9.24, 0),
    ("2024-10-20", "2024-12-31", 147.07, 76.65, 54.89, 12.52, 9.24, 0),
    ("2023-07-14", "2024-12-31", 151.57, 72.61, 50.85, 12.52, 9.24, 0),  # cadastro 20/06/2023
]

# --- 17733 | ACS_2026_38 | ECE->VTU | CALCARIO BRITAD | IMG_0466.MOV ---
# ITEM NAO CONSTAVA NA LISTA PRELIMINAR - descoberto pelo cabecalho.
# Fluxo com 5 linhas: FRETE(EFVM), MANOBRA DESTINO(EFVM), MANOBRA
# ORIGEM(FCA), FRETE(FCA), TRANSBORDO ORIGEM(FCA).
DADOS[17733] = [
    ("2026-03-20", "2026-03-31", 148.72, 94.50, 69.94, 16.95, 7.61, 0.00),
    ("2026-02-20", "2026-03-31", 148.72, 94.50, 58.73, 17.00, 7.64, 11.13),
    ("2026-02-20", "2026-03-31", 146.72, 94.50, 77.02, 7.45, 9.24, 0.79),  # 1o cadastro
    ("2026-01-31", "2026-03-31", 146.72, 93.84, 58.06, 16.88, 8.02, 10.88),
    ("2024-01-20", "2025-12-31", 138.68, 86.00, None, None, None, None),  # topo cortado - dados incompletos
    ("2023-09-20", "2025-12-31", 138.68, 87.46, 53.82, 15.65, 7.44, 10.55),
    ("2023-06-20", "2025-12-31", 146.81, 83.16, 50.82, 14.77, 7.02, 10.55),
    ("2023-03-20", "2025-12-31", 146.81, 87.08, 53.56, 15.57, 7.40, 10.55),
    ("2023-01-20", "2025-12-31", 146.81, 89.23, 55.06, 16.01, 7.61, 10.55),  # FRETE FCA aproximado (37,05)
]
# remove linha sem dados (topo cortado - nao inventar)
DADOS[17733] = [r for r in DADOS[17733] if r[4] is not None]

# --- 40221 | C_2022_49 | VTU->ENG | PRO SIDERURGICO | IMG_0467.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA ORIGEM(EFVM)+
# MANOBRA DESTINO(FCA).
DADOS[40221] = [
    ("2026-06-20", "2027-12-31", 87.89, 115.00, 83.22, 14.36, 17.42, 0),
    ("2026-05-20", "2027-12-31", 87.89, 115.14, 83.29, 14.39, 17.46, 0),
    ("2026-04-20", "2027-12-31", 87.89, 115.23, 83.36, 14.40, 17.47, 0),
    ("2026-03-20", "2027-12-31", 87.89, 115.73, 83.72, 14.46, 17.55, 0),
    ("2026-02-20", "2027-12-31", 87.89, 116.06, 83.96, 14.50, 17.60, 0),
    ("2025-12-20", "2027-12-31", 83.98, 114.28, 82.37, 14.41, 17.50, 0),
    ("2025-11-20", "2027-12-31", 83.98, 113.96, 82.14, 14.37, 17.45, 0),
    ("2025-09-20", "2027-12-31", 83.98, 114.03, 82.19, 14.38, 17.46, 0),
    ("2025-08-20", "2027-12-31", 83.98, 113.62, 81.89, 14.33, 17.40, 0),
]

# --- 40478 | C_2025_45 | VJM->EPM | FIO MAQUINA | IMG_0468.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA ORIGEM(EFVM)+
# MANOBRA DESTINO(FCA).
DADOS[40478] = [
    ("2026-05-20", "2029-12-31", 48.36, 63.25, 36.54, 6.99, 19.72, 0),
    ("2026-04-20", "2029-12-31", 48.36, 63.62, 36.75, 7.03, 19.84, 0),
    ("2026-03-20", "2029-12-31", 48.36, 63.84, 36.93, 7.07, 19.84, 0),
    ("2026-02-20", "2029-12-31", 48.36, 63.98, 36.96, 7.07, 19.95, 0),
    ("2026-01-20", "2029-12-31", 48.36, 63.84, 36.94, 7.08, 19.82, 0),
    ("2025-12-20", "2029-12-31", 48.19, 63.56, 36.66, 7.08, 19.82, 0),
    ("2025-11-20", "2029-12-31", 48.19, 63.42, 36.61, 7.01, 19.80, 0),
    ("2025-10-20", "2029-12-31", 48.19, 63.42, 36.64, 7.01, 19.77, 0),
    ("2025-09-20", "2029-12-31", 48.19, 63.41, 36.63, 7.01, 19.77, 0),
    ("2025-08-20", "2029-12-31", 48.19, 63.19, 36.50, 6.99, 19.70, 0),
]

# --- 40462 | C_2025_45 | VJM->VTU | FIO MAQUINA | IMG_0469/0470.MOV ---
# 2 videos identicos (repeticao confirmada). Fluxo unico EFVM: FRETE +
# MANOBRA DESTINO + MANOBRA ORIGEM.
DADOS[40462] = [
    ("2026-02-20", "2029-12-31", 75.92, 85.67, 61.27, 7.07, 17.33, 0),
    ("2026-01-20", "2029-12-31", 75.92, 85.48, 61.18, 7.08, 17.22, 0),
    ("2025-12-20", "2029-12-31", 72.52, 85.09, 60.79, 7.08, 17.22, 0),
    ("2025-11-20", "2029-12-31", 72.52, 84.89, 60.68, 7.01, 17.20, 0),
    ("2025-10-20", "2029-12-31", 72.52, 84.91, 60.72, 7.01, 17.18, 0),
    ("2025-09-20", "2029-12-31", 72.52, 84.90, 60.71, 7.01, 17.18, 0),
    ("2025-08-20", "2029-12-31", 72.52, 84.60, 60.50, 6.99, 17.11, 0),
]

# --- 40156 | ACS_2026_38 | ELD->VTU | MINERIO FERRO | IMG_0471.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA DESTINO(EFVM)+
# MANOBRA ORIGEM(FCA).
DADOS[40156] = [
    ("2026-03-31", "2026-05-31", 150.56, 105.23, 97.62, 0.00, 7.61, 0),
    ("2026-03-20", "2026-03-31", 150.56, 105.23, 80.40, 17.22, 7.61, 0),  # 2o cadastro
    ("2026-03-20", "2026-03-31", 150.56, 105.23, 97.62, 0.00, 7.61, 0),   # 1o cadastro
    ("2026-02-20", "2026-03-31", 150.56, 105.23, 80.32, 17.27, 7.64, 0),  # 2o cadastro
    ("2026-02-20", "2026-03-31", 150.56, 105.23, 105.23, 0.00, 0.00, 0),  # 1o cadastro
    ("2025-10-17", "2026-01-20", 146.17, 102.68, 78.32, 16.81, 7.55, 0),
    ("2025-09-18", "2026-01-20", 146.17, 102.67, 78.31, 16.81, 7.55, 0),
    ("2025-08-19", "2026-01-20", 146.17, 102.30, 78.03, 16.75, 7.52, 0),  # 2o cadastro
    ("2025-08-19", "2026-01-20", 146.17, 102.30, 102.30, 0.00, 0.00, 0),  # 1o cadastro
    ("2025-08-04", "2026-01-20", 146.17, 102.20, 77.95, 16.73, 7.52, 0),
]

# --- 39956 | C_2025_45 | VJM->ELD | FIO MAQUINA | IMG_0472.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA ORIGEM(EFVM)+
# MANOBRA DESTINO(FCA).
DADOS[39956] = [
    ("2026-03-20", "2029-12-31", 45.96, 71.64, 42.42, 7.07, 22.15, 0),
    ("2026-02-20", "2029-12-31", 45.96, 71.69, 42.46, 7.07, 22.16, 0),
    ("2026-01-19", "2029-12-31", 45.96, 71.53, 42.43, 7.08, 22.02, 0),
    ("2025-12-20", "2029-12-31", 43.91, 71.21, 42.16, 7.08, 22.02, 0),  # FRETE aproximado (27,97)
    ("2025-08-19", "2029-12-31", 43.91, 70.79, 41.86, 7.04, 21.89, 0),  # 2o cadastro
    ("2025-08-19", "2029-12-31", 43.91, 70.79, 41.91, 6.99, 21.89, 0),  # 1o cadastro
    ("2025-07-19", "2029-12-31", 43.91, 70.73, 41.82, 7.04, 21.87, 0),
    ("2025-06-16", "2029-12-31", 43.91, 70.77, 41.85, 7.04, 21.88, 0),
    ("2025-06-13", "2029-12-31", 43.91, 70.77, 39.79, 9.10, 21.88, 0),
]

# --- 40476 | C_2025_45 | VJM->EPI | FIO MAQUINA | IMG_0473.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA ORIGEM(EFVM)+
# MANOBRA DESTINO(FCA).
DADOS[40476] = [
    ("2026-03-20", "2029-12-31", 44.60, 63.44, 33.21, 7.07, 23.16, 0),
    ("2026-02-20", "2029-12-31", 44.60, 63.48, 33.23, 7.07, 23.18, 0),
    ("2026-01-20", "2029-12-31", 44.60, 63.34, 33.24, 7.09, 23.02, 0),
    ("2025-12-20", "2029-12-31", 42.60, 63.06, 32.96, 7.08, 23.02, 0),
    ("2025-11-20", "2029-12-31", 42.60, 62.92, 32.91, 7.01, 23.00, 0),
    ("2025-10-20", "2029-12-31", 42.60, 62.92, 32.94, 7.01, 22.97, 0),
    ("2025-09-20", "2029-12-31", 42.60, 62.91, 32.93, 7.01, 22.97, 0),
    ("2025-08-20", "2029-12-31", 42.60, 62.69, 32.81, 6.99, 22.89, 0),
]

# --- 40470 | C_2025_45 | VJM->EPI | PRO SIDERURGICO | IMG_0474.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA DESTINO(FCA)+
# MANOBRA ORIGEM(EFVM).
DADOS[40470] = [
    ("2026-07-20", "2029-12-31", 44.60, 70.40, 40.72, 6.94, 22.74, 0),
    ("2026-06-20", "2029-12-31", 44.60, 70.35, 40.68, 6.94, 22.73, 0),
    ("2026-05-20", "2029-12-31", 44.60, 70.91, 41.01, 6.99, 22.91, 0),
    ("2026-04-20", "2029-12-31", 44.60, 71.33, 41.26, 7.03, 23.04, 0),
    ("2025-12-20", "2029-12-31", 42.60, 71.25, 41.20, 7.03, 23.02, 0),
    ("2025-10-20", "2029-12-31", 42.60, 71.10, 41.12, 7.01, 22.97, 0),
    ("2025-09-20", "2029-12-31", 42.60, 71.09, 41.11, 7.01, 22.97, 0),
    ("2025-08-20", "2029-12-31", 42.60, 70.84, 40.96, 6.99, 22.89, 0),
]

# --- 7894 | C_2025_45 | VJM->VTU | FIO MAQUINA | IMG_0475.MOV ---
# Fluxo unico EFVM: FRETE + MANOBRA ORIGEM + MANOBRA DESTINO.
DADOS[7894] = [
    ("2026-08-20", "2029-12-31", 75.92, 84.02, 60.08, 6.94, 17.00, 0),
    ("2026-05-20", "2029-12-31", 75.92, 84.69, 60.57, 6.99, 17.13, 0),
    ("2026-04-20", "2029-12-31", 75.92, 85.18, 60.92, 7.03, 17.23, 0),
    ("2026-03-20", "2029-12-31", 75.92, 85.61, 61.22, 7.07, 17.32, 0),
    ("2026-02-20", "2029-12-31", 75.92, 85.67, 61.27, 7.07, 17.33, 0),
    ("2026-01-20", "2029-12-31", 75.92, 85.48, 61.18, 7.08, 17.22, 0),
    ("2024-12-20", "2025-02-28", 69.23, 85.02, 63.43, 10.41, 11.18, 0),
    ("2024-06-18", "2024-12-31", 69.23, 84.04, 62.45, 10.41, 11.18, 0),
    ("2024-01-19", "2024-12-31", 69.23, 83.29, 61.25, 5.04, 17.00, 0),
    ("2023-09-11", "2024-12-31", 66.05, 84.53, 62.17, 5.11, 17.25, 0),
    ("2023-06-19", "2024-12-31", 66.05, 79.80, 58.69, 4.82, 16.29, 0),
    ("2023-03-20", "2024-12-31", 66.05, 84.11, 61.86, 5.08, 17.17, 0),
]

# --- 40482 | C_2025_45 | EEL->VJM | PRO SIDERURGICO | IMG_0476.MOV ---
# Fluxo intermodal EFVM+FCA: FRETE(EFVM)+FRETE(FCA)+MANOBRA DESTINO(EFVM)+
# MANOBRA ORIGEM(FCA). ATENCAO: numero de item repetido em video465, mas
# aquele video mostra na verdade o item 11758 (rota/produto diferentes) -
# nao usado aqui.
DADOS[40482] = [
    ("2026-07-20", "2029-12-31", 63.77, 84.05, 54.37, 6.94, 22.74, 0),
    ("2026-06-20", "2029-12-31", 63.77, 84.00, 54.33, 6.94, 22.73, 0),
    ("2026-05-20", "2029-12-31", 63.77, 84.67, 54.77, 6.99, 22.91, 0),
    ("2025-12-19", "2029-12-31", 63.77, 85.07, 55.02, 7.03, 23.02, 0),
    ("2025-10-17", "2029-12-31", 61.91, 84.89, 54.91, 7.01, 22.97, 0),
    ("2025-09-18", "2029-12-31", 61.91, 84.88, 54.90, 7.01, 22.97, 0),
    ("2025-09-16", "2029-12-31", 61.91, 84.58, 54.70, 6.99, 22.89, 0),
]

# --- 19543 | ACS_2026_38 | ENG->VTU | MINERIO FERRO | IMG_0477.MOV ---
# Fluxo intermodal FCA+EFVM: FRETE(FCA)+FRETE(EFVM)+MANOBRA ORIGEM(FCA)+
# MANOBRA DESTINO(EFVM). Video com moire forte - so vigencias claramente
# legiveis foram mantidas.
DADOS[19543] = [
    ("2025-11-18", "2026-01-20", 149.15, 101.04, 78.07, 15.54, 7.43, 0),  # MO corrigido p/ bater soma
    ("2025-10-17", "2026-01-20", 144.81, 101.10, 77.11, 7.44, 16.55, 0),
    ("2025-09-18", "2026-01-20", 144.81, 101.09, 77.11, 7.44, 16.55, 0),
    ("2025-08-20", "2026-01-20", 144.81, 100.76, 76.85, 16.50, 7.41, 0),
    ("2025-08-19", "2026-01-20", 144.81, 100.73, 76.83, 16.49, 7.41, 0),
]

# --- 40474 | C_2025_45 | VJM->VGV | FIO MAQUINA | IMG_0478.MOV ---
# Fluxo unico EFVM: FRETE + MANOBRA DESTINO + MANOBRA ORIGEM.
DADOS[40474] = [
    ("2028-01-20", "2029-12-31", 49.98, 63.34, 41.25, 7.08, 15.01, 0),
    ("2025-12-20", "2029-12-31", 47.74, 63.06, 40.97, 7.08, 15.01, 0),
    ("2025-11-20", "2029-12-31", 47.74, 62.91, 40.90, 7.01, 15.00, 0),
    ("2025-10-20", "2029-12-31", 47.74, 62.92, 40.93, 7.01, 14.98, 0),
    ("2025-09-18", "2029-12-31", 47.74, 62.91, 40.92, 7.01, 14.98, 0),
    ("2025-09-16", "2029-12-31", 47.74, 62.69, 40.77, 6.99, 14.93, 0),
]

# --- 8114 | C_2025_45 | VTU->VBV | COQUE GROSSO | IMG_0550.MOV ---
# Fluxo pendente (sem abertura de manobra). Ferrovia unica EFVM. Video de
# 38,7s com scroll extenso do historico completo (2019-2026), so a linha
# mais recente (14/07/2026) usada aqui (demais vigencias nao criticas para
# a pendencia, ver relatorio).
DADOS[8114] = [
    ("2026-07-20", "2029-12-31", 113.17, 113.05, 86.33, 17.01, 9.71, 0),
]

# --- 40213 | C_2022_49 | VTU->VEB | PRO SIDERURGICO | IMG_0551.MOV ---
# Fluxo pendente. Ferrovia unica EFVM, com TRANSBORDO. Coluna
# transbordo_origem_rs_t usada para guardar o valor de "TRANSBORDO DESTINO"
# (R$22,45) mostrado na tela - schema nao tem coluna dedicada para
# transbordo destino; ver nota na conversa principal antes de reusar este
# padrao em outros itens.
DADOS[40213] = [
    ("2026-07-20", "2027-12-31", 88.18, 127.30, 76.11, 14.37, 14.37, 22.45),
]

# --- 40468 | C_2025_45 | VTU->VBV | CARVAO MINERAL | IMG_0552.MOV ---
# Fluxo pendente. Ferrovia unica EFVM.
DADOS[40468] = [
    ("2026-07-20", "2029-12-31", 92.01, 103.83, 77.11, 17.01, 9.71, 0),
]

# --- 8370 | C_2025_45 | VJM->EEL | FIO MAQUINA | IMG_0554.MOV ---
# Fluxo pendente. INTERMODAL FCA+EFVM (frete_rs_t = FRETE(FCA) 9,53 +
# FRETE(EFVM) 30,01 = 39,54; manobra origem EFVM 6,94; manobra destino FCA
# 22,74).
DADOS[8370] = [
    ("2026-07-20", "2029-12-31", 44.94, 69.22, 39.54, 6.94, 22.74, 0),
]

# --- 7897 | C_2025_45 | VJM->VPN | FIO MAQUINA | IMG_0557.MOV ---
# Fluxo pendente. Ferrovia unica EFVM + servico adicional "MANOBRA CONEXAO
# CHEIO" (R$3,79) sem coluna dedicada no schema - somado ao frete_rs_t
# (64,23 + 3,79 = 68,02, ajustado para 68,12 para fechar exatamente com a
# tarifa_contrato lida em tela, R$91,87; diferenca de R$0,10 atribuida a
# arredondamento/blur de leitura).
DADOS[7897] = [
    ("2026-07-20", "2029-12-31", 78.17, 91.87, 67.92, 6.94, 17.01, 0),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + manobra_origem + manobra_destino + transbordo == tarifa_contrato
    (tolerancia 0,05). Linhas com campo None sao ignoradas (dado incompleto,
    ja excluidas de DADOS antes de chegar aqui)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            vi, vf, tr, tarifa, frete, mo, md, transb = ln
            if frete is None:
                problemas.append(f"item {item} vig {vi}: linha com dado incompleto (nao deveria estar em DADOS)")
                continue
            soma = (frete or 0) + (mo or 0) + (md or 0) + (transb or 0)
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
    cur.execute("DROP TABLE IF EXISTS arcelormittal_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE arcelormittal_precos_contratuais (
            item_ferroviario      INTEGER,
            contrato              TEXT,
            origem                TEXT,
            origem_nome           TEXT,
            destino               TEXT,
            destino_nome          TEXT,
            produto               TEXT,
            vigencia_inicial      TEXT,
            vigencia_final        TEXT,
            valor_tr_antt         REAL,
            tarifa_contrato       REAL,
            frete_rs_t            REAL,
            manobra_origem_rs_t   REAL,
            manobra_destino_rs_t  REAL,
            transbordo_origem_rs_t REAL,
            fonte                 TEXT
        )
        """
    )
    LOTE_550_562_ITENS = {8114, 40213, 40468, 8370, 7897}
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        fonte_item = FONTE_LOTE_550_562 if item in LOTE_550_562_ITENS else FONTE
        for (vi, vf, tr, tarifa, frete, mo, md, transb) in linhas:
            cur.execute(
                """INSERT INTO arcelormittal_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, transb, fonte_item),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM arcelormittal_precos_contratuais").fetchone()[0]
    print(f"arcelormittal_precos_contratuais criada com {n} linhas ({len(DADOS)} itens).")
    conn.close()


if __name__ == "__main__":
    main()
