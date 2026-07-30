# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade) no banco, Produto=MILHO
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro, "Competitividade",
09_Fotos/IMG_0222.MOV, 428s) — mesmo relatório-fonte de add_market_share.py (Soja), só troca
o filtro Produto para MILHO. A sequência de microrregiões cicladas no vídeo é DIFERENTE da de
Soja (pula BA Oeste Norte e MT Nordeste, inclui outras como RJ/SC) — não presumir mesma ordem.

Cobertura: MA Sul, Nacional (agregado "Todos"), PI Sul, MG Triangulo, MT Nordeste Sul, MT
Medio Norte, MS Sul, MT Norte, PA Nordeste, PB, PR, RJ, PA Sudeste. Regiões novas (MT Sudeste,
MG Outros) foram para add_market_share_milho2.py (rodada 2). Ainda não transcritas: TO Centro,
GO Leste/Noroeste/Sudoeste, AC, AL, AM, MS Norte, SC + outros estados do grupo OUTROS +
dimensão Porto no final do vídeo (~t=320-428s).

IMPORTANTE: este script só faz INSERT (não DROP) nas tabelas market_share_volume/
market_share_player — deve rodar DEPOIS de add_market_share.py (que cria as tabelas com os
dados de Soja). Rodar sozinho sem add_market_share.py antes vai falhar (tabela não existe).

Uso:  python3 add_market_share.py && python3 add_market_share_milho.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0222.MOV, Produto=MILHO) — transcrição manual dos rótulos numéricos das "
         "barras. Cobertura: Nacional + 11 regiões (de ~25-30 regiões + dimensão Porto no vídeo-fonte).")

# ---------------------------------------------------------------- VOLUME MOVIMENTADO (t)
# escopo -> {ano: {mes(1-12): valor|None}}
# Meses ausentes da lista (não None, simplesmente fora do range) = categoria não exibida
# pelo PowerBI-fonte (volume zero/nulo naquele mês) — ver maio/2025 e abril/2026 de MA Sul.
VOLUME = {
    "MA Sul": {
        2024: [25738, 548, 95, 82, 304, 18525, 172503, 221049, 191189, 138004, 60257, 13887],
        2025: [28996, 1603, 1042, 352, 0, 95, 45017, 50630, 64087, 23351, 9819, 503],
        2026: [369, 152, 1048, 0, 241, 146, 1374, None, None, None, None, None],
    },
}
# Agregado nacional (Microrregião="Todos") — dado real (não render-lag), único frame com
# legendário completo (ADM/HBSA/HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI NORTE/VLI SUL).
# CORRIGIDO jul/2026 (rodada 4): a transcrição original tinha 2024/2025 deslocados 1 mês pra
# trás — releitura com zoom do frame limpo t=8s (dropdown fechado) usando centragem horizontal
# do rótulo sobre a barra + regra "rótulo fica ACIMA do topo da própria barra". Barras sem
# rótulo (colisão com vizinha alta) = None. 2026 já estava certo (confirmado no mesmo frame).
VOLUME["Nacional"] = {
    2024: [1559895, 284314, None, 342858, None, 2031108, 4770675, 4988225, None, None, 3695495, 2356750],
    2025: [1092238, None, 381280, None, 348871, 1554567, 5605269, 6600511, None, 5603681, None, 4321380],
    2026: [1253424, 916613, 713029, 313416, 434998, 1588435, 942113, None, None, None, None, None],
}
# PI Sul: eixos verificados (IMG_0222 t57, 13/jul/26): 2024 sem abr/mai/jul; 2026 so
# jan/mai/jul -> ausentes = zero real. 2025 set-dez tampados pelo dropdown -> None.
VOLUME["PI Sul"] = {
    2024: [19988, 1032, 89, 0, 0, 318, 0, 24172, 59786, 27217, 64687, 52402],
    2025: [1883, 262, 639, 252, 600, 966, 330, 51, None, None, None, None],
    2026: [38735, 0, 0, 0, 59, 0, 53, None, None, None, None, None],
}
VOLUME["MG Triangulo"] = {
    2024: [149, 353, 216, 895, 2640, 3648, 1410, 4285, 5448, 2082, 8365, 16819],
    2025: [12385, 2100, 761, 1576, 3975, 698, 12008, None, None, None, None, None],
    2026: [4235, 373, 2178, 156, 961, 1095, 1560, None, None, None, None, None],
}
# CORRIGIDO+COMPLETADO jul/2026 (rodada 5, frame limpo t=145s, centragem rótulo→barra):
# 2024 SET estava com o valor de OUT (433.728 é OUT; SET sem rótulo por colisão);
# 2025 ganhou a cauda set/out/dez (ago e nov sem rótulo por colisão -> None);
# 2026 ganhou jan-mai (o vídeo é de jul/2026, o histórico todo está lá).
VOLUME["MT Nordeste Sul"] = {
    2024: [63915, 743, 800, 533, 2251, 12819, 222030, 337245, None, 433728, 270133, 168061],
    2025: [12320, 4041, 567, 256, 2875, 39484, 260595, None, 352725, 507041, None, 492092],
    2026: [61090, 2861, 1301, 1387, 627, 41563, 80004, None, None, None, None, None],
}
VOLUME["MT Medio Norte"] = {
    2024: [462470, 46165, 61530, None, 368177, 685807, 1009134, None, 991828, None, 689564, 348675],
    2025: [40377, 7044, 4826, 8922, 51138, 362377, 804914, 1100153, 927416, 1055820, None, None],
    2026: [220272, 5619, 5271, 49361, 158806, 369396, 243140, None, None, None, None, None],
}
# COMPLETADO jul/2026 (rodada 5, frame t=221s): OUT/2024=64.873 (rótulo perdido na 1ª passada);
# cauda 2025 ago-dez lida (out sem rótulo por colisão -> None).
VOLUME["MS Sul"] = {
    2024: [193765, 40320, 23268, 29142, 36158, 37281, 12500, 13367, 45121, 64873, 20447, 21297],
    2025: [33004, 54562, 38664, 32578, 51977, 157626, 464951, 376189, 160361, 170633, 218904, 151106],
    2026: [122998, 87047, 38060, 3862, 3718, 16527, 4245, None, None, None, None, None],
}
# CORRIGIDO+COMPLETADO jul/2026 (rodada 5, frame t=227s, centragem rótulo→barra): 2024 tinha
# shift — 884.077 é SET (não AGO) e 515.787 é OUT (não SET); AGO/NOV sem rótulo por colisão.
# 2025 ganhou ago/out/dez (set e nov sem rótulo -> None).
VOLUME["MT Norte"] = {
    2024: [260202, 4879, 9182, 44363, 46305, 559492, 1301498, None, 884077, 515787, None, 185951],
    2025: [19250, 4170, 4544, 2086, 5169, 465636, 1426487, 1622316, None, 759440, None, 478117],
    2026: [96135, 5653, 1811, 33320, 58803, 805749, 314715, None, None, None, None, None],
}
VOLUME["PA Nordeste"] = {
    2024: [102, 48, None, 50, None, 138, 4793, 9123, None, 6028, 2438, None],
    2025: [None, 208, None, None, None, 3207, 4034, 6955, None, None, 940, None],
    2026: [146, None, 32, None, None, 1640, 668, None, None, None, None, None],
}
# PB: eixos verificados (IMG_0222 t250): 2024 so outubro; 2025 vazio; 2026 so maio.
VOLUME["PB"] = {
    2024: [0, 0, 0, 0, 0, 0, 0, 0, 0, 49, 0, 0],
    2025: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    2026: [0, 0, 0, 0, 2, 0, 0, None, None, None, None, None],
}
# CORRIGIDO+COMPLETADO jul/2026 (rodada 5, frame t=263s, centragem rótulo→barra): 1ª passada
# tinha empacotado os rótulos em meses consecutivos ignorando barras sem rótulo (colisão) —
# 2024: 35.118=ABR, 80.527=MAI, 199.438=JUN, 296.596=AGO, 488.906=OUT, 394.608=DEZ
# (MAR/JUL/SET/NOV sem rótulo). 2025: 33.595=ABR (MAR sem rótulo); cauda ago-dez lida
# (out sem rótulo). 2026 conferido no frame — estava certo.
VOLUME["PR"] = {
    2024: [242006, 100919, None, 35118, 80527, 199438, None, 296596, None, 488906, None, 394608],
    2025: [495084, 184646, None, 33595, 150014, 241861, 601183, 757885, 886145, None, 754479, 311919],
    2026: [222479, 122506, 154842, 104139, 100202, 46504, 11438, None, None, None, None, None],
}
VOLUME["RJ"] = {
    2024: [None, None, 9, 89, None, None, None, None, None, None, None, None],
    2025: [None, None, None, None, None, 33, 31, None, None, None, None, None],
}
# PA Sudeste: achado bônus durante re-scan de PI Sul (t~48-52s do vídeo, 4 frames
# idênticos = janela estável). Não estava na lista original de regiões cobertas.
VOLUME["PA Sudeste"] = {
    2024: [None, 94, None, None, None, None, 45183, 45539, 22361, 6823, 814, 188],
    2025: [None, None, 178, None, None, None, 6008, 56131, 50330, 19204, 47645, 17893],
    2026: [403, 179, 467, 2, None, 32737, 7231, None, None, None, None, None],
}

# ---------------------------------------------------------- MARKET SHARE POR PLAYER (%)
MS = {
    "MA Sul": {
        2024: {
            1: {"RODOVIARIO": 69, "OP_NORTE": 31},
            2: {"RODOVIARIO": 64, "OP_NORTE": 36},
            3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 52, "OP_NORTE": 48},
            5: {"OP_NORTE": 100},
            6: {"OP_NORTE": 99},
            7: {"RODOVIARIO": 18, "OP_NORTE": 82},
            8: {"RODOVIARIO": 55, "OP_NORTE": 45},
            9: {"RODOVIARIO": 48, "OP_NORTE": 52},
            10: {"RODOVIARIO": 56, "OP_NORTE": 44},
            11: {"RODOVIARIO": 51, "OP_NORTE": 49},
            12: {"RODOVIARIO": 34, "OP_NORTE": 66},
        },
        2025: {
            1: {"RODOVIARIO": 100},
            2: {"RODOVIARIO": 61, "OP_NORTE": 32},
            3: {"RODOVIARIO": 85, "RUMO": 15},
            4: {"RODOVIARIO": 89, "OP_NORTE": 11},
            6: {"RODOVIARIO": 52, "OP_NORTE": 48},
            7: {"RODOVIARIO": 54, "OP_NORTE": 46},
            8: {"RODOVIARIO": 90, "OP_NORTE": 10},
            9: {"RODOVIARIO": 99},
            10: {"RODOVIARIO": 70, "OP_NORTE": 30},
            11: {"OP_NORTE": 94},
            12: {"RODOVIARIO": 31, "RUMO": 23, "OP_NORTE": 47},
        },
        2026: {
            1: {"RODOVIARIO": 100},
            2: {"RODOVIARIO": 100},
            3: {"RODOVIARIO": 100},
            5: {"RODOVIARIO": 100},
            6: {"RODOVIARIO": 66, "OP_NORTE": 34},
            7: {"OP_NORTE": 100},
        },
    },
    "RJ": {
        2024: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}},
        2025: {6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
    },
    "PB": {
        2024: {10: {"RUMO": 100}},
        2026: {5: {"OP_SUL": 100}},
    },
    "PI Sul": {
        2024: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100},
            6: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100},
            10: {"RODOVIARIO": 89, "OP_NORTE": 11},
            11: {"RODOVIARIO": 94, "OP_NORTE": 6},
            12: {"RODOVIARIO": 68, "OP_NORTE": 32},
        },
        2025: {
            1: {"RODOVIARIO": 94, "OP_NORTE": 6},
            2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100},
            5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100},
            8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100},
            11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2026: {
            1: {"RODOVIARIO": 100},
            5: {"RODOVIARIO": 86, "OP_NORTE": 14},
            7: {"RODOVIARIO": 100},
        },
    },
    "MT Medio Norte": {
        # Legendário disputado (HBSA/HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI SUL) — só % com
        # rótulo explícito gravado; frações finas sem rótulo (colisão de barra densa) omitidas.
        2024: {
            1: {"RUMO": 51, "RODOVIARIO": 12, "HBSA": 37},
            2: {"RUMO": 57, "RODOVIARIO": 15, "HBSA": 28},
            3: {"RUMO": 57, "RODOVIARIO": 8, "HBSA": 34},
            4: {"RUMO": 30, "HBSA": 68},
            5: {"HBSA": 86},
            6: {"RUMO": 17, "RODOVIARIO": 8, "HBSA": 73},
            7: {"RUMO": 43, "HBSA": 51},
            8: {"RUMO": 62, "HBSA": 35},
            9: {"RUMO": 64, "RODOVIARIO": 11, "HBSA": 24},
            10: {"RUMO": 78, "HBSA": 17},
            11: {"RUMO": 80, "HBSA": 13},
            12: {"RUMO": 66, "HBSA": 31},
        },
        2025: {
            1: {"HBSA": 10, "RODOVIARIO": 75, "RUMO": 11},
            2: {"RODOVIARIO": 90},
            3: {"HBSA": 80, "RUMO": 20},
            4: {"HBSA": 79, "RUMO": 18},
            5: {"RUMO": 97},
            6: {"HBSA": 50, "RODOVIARIO": 14, "RUMO": 34},
            7: {"HBSA": 32, "RUMO": 59},
            8: {"HBSA": 43, "RUMO": 52},
            9: {"HBSA": 29, "RUMO": 68},
            10: {"HBSA": 40, "RUMO": 59},
            11: {"HBSA": 53, "RUMO": 45},
            12: {"HBSA": 49, "RUMO": 46},
        },
        2026: {
            1: {"RUMO": 40, "HBSA": 54},
            2: {"RUMO": 53, "HBSA": 42},
            3: {"OP_SUL": 7, "RUMO": 90},
            4: {"RUMO": 16, "HBSA": 81},
            5: {"RUMO": 9, "HBSA": 84},
            6: {"RUMO": 16, "HBSA": 74},
            7: {"RUMO": 29, "HBSA": 66},
        },
    },
    "MT Nordeste Sul": {
        # Legendário: ADM/HBSA/RODOVIARIO/RUMO/VLI NORTE/VLI SUL — só % com rótulo explícito.
        2024: {
            1: {"RUMO": 60, "RODOVIARIO": 38},
            2: {"RUMO": 36, "RODOVIARIO": 64},
            3: {"RUMO": 63, "RODOVIARIO": 31},
            4: {"RUMO": 91, "RODOVIARIO": 9},
            5: {"OP_NORTE": 13, "RODOVIARIO": 80},
            6: {"OP_SUL": 13, "RUMO": 66, "OP_NORTE": 17},
            7: {"OP_NORTE": 9, "RUMO": 76, "RODOVIARIO": 10},
            8: {"RUMO": 65, "RODOVIARIO": 24},
            9: {"OP_SUL": 10, "RUMO": 63, "RODOVIARIO": 19},
            10: {"RUMO": 71, "RODOVIARIO": 22},
            11: {"OP_NORTE": 13, "RUMO": 60, "RODOVIARIO": 22},
            12: {"RUMO": 88},
        },
        2025: {
            1: {"RUMO": 34, "RODOVIARIO": 65},
            2: {"OP_SUL": 8, "RODOVIARIO": 87},
            3: {"RUMO": 86, "RODOVIARIO": 14},
            4: {"RUMO": 72, "RODOVIARIO": 28},
            5: {"OP_SUL": 87, "RUMO": 11},
            6: {"OP_SUL": 10, "RUMO": 26, "RODOVIARIO": 64},
            7: {"RUMO": 69, "RODOVIARIO": 23},
            8: {"OP_SUL": 14, "RUMO": 67, "RODOVIARIO": 17},
            9: {"OP_SUL": 14, "RUMO": 70, "RODOVIARIO": 13},
            10: {"RUMO": 90},
            11: {"OP_SUL": 31, "RUMO": 63},
            12: {"OP_SUL": 20, "OP_NORTE": 9, "RUMO": 63},
        },
        2026: {
            1: {"OP_SUL": 36, "RUMO": 45, "RODOVIARIO": 16},
            2: {"OP_SUL": 15, "OP_NORTE": 7, "RUMO": 61, "RODOVIARIO": 18},
            3: {"RUMO": 94},
            4: {"OP_NORTE": 7, "RUMO": 87},
            5: {"OP_SUL": 7, "RUMO": 93},
            6: {"RUMO": 63, "RODOVIARIO": 36},
            7: {"RUMO": 95},
        },
    },
    "PR": {
        2024: {
            1: {"RODOVIARIO": 81},
            2: {"RUMO": 44, "RODOVIARIO": 56},
            3: {"RUMO": 68, "RODOVIARIO": 32},
            4: {"RUMO": 72, "RODOVIARIO": 28},
            5: {"RUMO": 46, "RODOVIARIO": 54},
            6: {"RUMO": 67, "RODOVIARIO": 33},
            7: {"RUMO": 93, "RODOVIARIO": 7},
            8: {"RUMO": 69, "RODOVIARIO": 31},
            9: {"RUMO": 40, "RODOVIARIO": 60},
            10: {"RUMO": 49, "RODOVIARIO": 51},
            11: {"RUMO": 63, "RODOVIARIO": 37},
            12: {"RUMO": 47, "RODOVIARIO": 53},
        },
        2025: {
            1: {"RUMO": 10, "RODOVIARIO": 90},
            2: {"RUMO": 11, "RODOVIARIO": 89},
            3: {"RUMO": 17, "RODOVIARIO": 83},
            4: {"RUMO": 80, "RODOVIARIO": 20},
            5: {"RODOVIARIO": 93},
            6: {"RUMO": 11, "RODOVIARIO": 89},
            7: {"RUMO": 45, "RODOVIARIO": 55},
            8: {"RUMO": 54, "RODOVIARIO": 46},
            9: {"RUMO": 39, "RODOVIARIO": 61},
            10: {"RUMO": 42, "RODOVIARIO": 58},
            11: {"RUMO": 38, "RODOVIARIO": 62},
            12: {"RUMO": 57, "RODOVIARIO": 43},
        },
        2026: {
            1: {"RUMO": 50, "RODOVIARIO": 50},
            2: {"RUMO": 18, "RODOVIARIO": 82},
            3: {"RUMO": 14, "RODOVIARIO": 86},
            4: {"RUMO": 15, "RODOVIARIO": 85},
            5: {"RODOVIARIO": 95},
            6: {"RUMO": 36, "RODOVIARIO": 64},
            7: {"RUMO": 75, "RODOVIARIO": 25},
        },
    },
    "MT Norte": {
        # Legendário: HBSA/RODOVIARIO/RUMO/VLI NORTE/VLI SUL — só % com rótulo explícito.
        2024: {
            1: {"HBSA": 84},
            2: {"RUMO": 24, "RODOVIARIO": 22, "HBSA": 51},
            3: {"RUMO": 28, "HBSA": 69},
            4: {"HBSA": 89},
            5: {"HBSA": 92},
            6: {"RODOVIARIO": 19, "HBSA": 80},
            7: {"RODOVIARIO": 10, "HBSA": 83},
            8: {"RODOVIARIO": 16, "HBSA": 82},
            9: {"RUMO": 30, "RODOVIARIO": 8, "HBSA": 62},
            10: {"RUMO": 57, "RODOVIARIO": 17, "HBSA": 26},
            11: {"RUMO": 42, "RODOVIARIO": 13, "HBSA": 45},
            12: {"RUMO": 38, "HBSA": 60},
        },
        2025: {
            1: {"RUMO": 44, "RODOVIARIO": 13, "HBSA": 42},
            2: {"RUMO": 15, "HBSA": 79},
            3: {"RUMO": 10, "HBSA": 90},
            4: {"RUMO": 15, "RODOVIARIO": 51, "HBSA": 34},
            5: {"RODOVIARIO": 29, "HBSA": 65},
            6: {"RUMO": 8, "HBSA": 87},
            7: {"RUMO": 17, "HBSA": 79},
            8: {"RUMO": 21, "HBSA": 75},
            9: {"RUMO": 24, "HBSA": 74},
            10: {"RUMO": 21, "HBSA": 75},
            11: {"RUMO": 13, "HBSA": 82},
            12: {"RUMO": 23, "HBSA": 70},
        },
        2026: {
            1: {"RUMO": 19, "OP_SUL": 40, "HBSA": 40},
            2: {"RUMO": 18, "OP_SUL": 10, "HBSA": 71},
            3: {"RUMO": 51, "HBSA": 43},
            4: {"HBSA": 99},
            5: {"HBSA": 99},
            6: {"HBSA": 97},
            7: {"RODOVIARIO": 7, "HBSA": 89},
        },
    },
    "PA Nordeste": {
        # Legendário: HBSA/RODOVIARIO (2 players). Meses ausentes do eixo (mar/mai/set/dez 2024
        # etc.) = categoria não exibida (volume zero), consistente com VOLUME já gravado.
        2024: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100},
            6: {"RODOVIARIO": 64, "HBSA": 36},
            7: {"RODOVIARIO": 97},
            8: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100},
        },
        2025: {
            2: {"RODOVIARIO": 100},
            6: {"HBSA": 100},
            7: {"HBSA": 100},
            8: {"RODOVIARIO": 37, "HBSA": 56},
            9: {"RODOVIARIO": 35, "HBSA": 57},
            11: {"RODOVIARIO": 95},
            12: {"RODOVIARIO": 100},
        },
        2026: {
            1: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
            7: {"RODOVIARIO": 35, "HBSA": 65},
        },
    },
    "PA Sudeste": {
        2024: {
            2: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100},
            8: {"RODOVIARIO": 95},
            9: {"OP_NORTE": 32, "RODOVIARIO": 68},
            10: {"RODOVIARIO": 99},
            11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2025: {
            3: {"RODOVIARIO": 100},
            7: {"OP_NORTE": 67, "RODOVIARIO": 33},
            8: {"OP_NORTE": 57, "RODOVIARIO": 43},
            9: {"OP_NORTE": 51, "RODOVIARIO": 49},
            10: {"OP_NORTE": 85, "RODOVIARIO": 15},
            11: {"OP_NORTE": 20, "RODOVIARIO": 80},
            12: {"OP_NORTE": 84, "RODOVIARIO": 16},
        },
        2026: {
            1: {"OP_NORTE": 12, "RODOVIARIO": 88},
            2: {"OP_NORTE": 100}, 3: {"OP_NORTE": 100}, 4: {"OP_NORTE": 100},
            6: {"RODOVIARIO": 100},
            7: {"RODOVIARIO": 97},
        },
    },
    "MG Triangulo": {
        # Legendário: ADM/RODOVIARIO/RUMO/VLI SUL (4 players na legenda). Alguns meses (fev-abr/
        # 2024, jun/2026) mostram um segmento azul sem correspondente na legenda — sem rótulo de
        # player confiável, omitido (não inventar atribuição).
        2024: {
            1: {"RUMO": 33, "RODOVIARIO": 67},
            2: {"OP_SUL": 32, "RODOVIARIO": 46},
            3: {"RUMO": 19, "RODOVIARIO": 66},
            4: {"RODOVIARIO": 85},
            5: {"OP_SUL": 100},
            6: {"OP_SUL": 99},
            7: {"OP_SUL": 23, "RUMO": 11, "RODOVIARIO": 66},
            8: {"RODOVIARIO": 96},
            9: {"OP_SUL": 29, "RODOVIARIO": 66},
            10: {"OP_SUL": 41, "RODOVIARIO": 55},
            11: {"OP_SUL": 26, "RUMO": 9, "RODOVIARIO": 65},
            12: {"RODOVIARIO": 93},
        },
        2025: {
            1: {"RODOVIARIO": 97},
            2: {"RODOVIARIO": 97},
            3: {"OP_SUL": 90, "RODOVIARIO": 10},
            4: {"OP_SUL": 94},
            5: {"OP_SUL": 23, "RUMO": 42, "RODOVIARIO": 35},
            6: {"OP_SUL": 68, "RODOVIARIO": 32},
            7: {"RODOVIARIO": 91},
            8: {"RUMO": 8, "RODOVIARIO": 84},
            9: {"RODOVIARIO": 94},
            10: {"OP_SUL": 10, "RODOVIARIO": 90},
            11: {"OP_SUL": 80, "RODOVIARIO": 17},
            12: {"OP_SUL": 77, "RODOVIARIO": 21},
        },
        2026: {
            1: {"OP_SUL": 22, "RUMO": 14, "RODOVIARIO": 64},
            2: {"OP_SUL": 26, "RUMO": 41, "RODOVIARIO": 33},
            3: {"OP_SUL": 84, "RODOVIARIO": 16},
            4: {"OP_SUL": 54, "RODOVIARIO": 46},
            5: {"OP_SUL": 100},
            6: {"OP_SUL": 89},
            7: {"OP_SUL": 69, "RUMO": 31},
        },
    },
    "MS Sul": {
        2024: {
            1: {"RUMO": 73, "RODOVIARIO": 27},
            2: {"RUMO": 40, "RODOVIARIO": 60},
            3: {"RUMO": 75, "RODOVIARIO": 25},
            4: {"RUMO": 93},
            5: {"RUMO": 78, "RODOVIARIO": 22},
            6: {"RUMO": 57, "RODOVIARIO": 43},
            7: {"RUMO": 82, "RODOVIARIO": 18},
            8: {"RUMO": 80, "RODOVIARIO": 20},
            9: {"RUMO": 69, "RODOVIARIO": 31},
            10: {"RUMO": 70, "RODOVIARIO": 30},
            11: {"RUMO": 79, "RODOVIARIO": 20},
            12: {"RUMO": 49, "RODOVIARIO": 51},
        },
        2025: {
            1: {"RODOVIARIO": 87, "RUMO": 13},
            2: {"RODOVIARIO": 72, "RUMO": 28},
            3: {"RODOVIARIO": 28, "RUMO": 72},
            4: {"RODOVIARIO": 30, "RUMO": 70},
            5: {"RODOVIARIO": 57, "RUMO": 43},
            6: {"RODOVIARIO": 52, "RUMO": 48},
            7: {"RODOVIARIO": 36, "RUMO": 64},
            8: {"RODOVIARIO": 41, "RUMO": 59},
            9: {"RODOVIARIO": 31, "RUMO": 69},
            10: {"RODOVIARIO": 38, "RUMO": 62},
            11: {"RODOVIARIO": 27, "RUMO": 73},
            12: {"RODOVIARIO": 20, "RUMO": 80},
        },
        2026: {
            1: {"RUMO": 88, "RODOVIARIO": 12},
            2: {"RUMO": 54, "RODOVIARIO": 46},
            3: {"RUMO": 57, "RODOVIARIO": 43},
            4: {"RUMO": 99},
            5: {"RUMO": 98},
            6: {"RUMO": 99},
            7: {"RUMO": 99},
        },
    },
    "Nacional": {
        # Agregado (Microrregião="Todos"), legendário completo de 7 players — só % com rótulo
        # explícito gravado; faixas finas sem rótulo (ADM/HBSA/HIDRO PORTO VELHO residuais em
        # colisão de barra densa) omitidas, consistente com o resto do arquivo.
        2024: {
            1: {"HBSA": 25, "RODOVIARIO": 29, "RUMO": 42},
            2: {"RODOVIARIO": 43, "RUMO": 49},
            3: {"HBSA": 12, "RODOVIARIO": 27, "RUMO": 58},
            4: {"HBSA": 35, "HIDRO PORTO VELHO": 8, "RUMO": 48},
            5: {"HBSA": 46, "RODOVIARIO": 30, "RUMO": 16},
            6: {"HBSA": 49, "RODOVIARIO": 19, "RUMO": 22},
            7: {"HBSA": 36, "RODOVIARIO": 15, "RUMO": 36, "OP_NORTE": 9},
            8: {"HBSA": 26, "RODOVIARIO": 24, "RUMO": 37, "OP_NORTE": 8},
            9: {"HBSA": 16, "RODOVIARIO": 29, "RUMO": 41, "OP_NORTE": 11},
            10: {"RODOVIARIO": 30, "RUMO": 51, "OP_NORTE": 11},
            11: {"HBSA": 9, "RODOVIARIO": 20, "RUMO": 55, "OP_NORTE": 12},
            12: {"HBSA": 9, "RODOVIARIO": 21, "RUMO": 58},
        },
        2025: {
            1: {"RODOVIARIO": 80, "RUMO": 16},
            2: {"RODOVIARIO": 82, "RUMO": 17},
            3: {"RODOVIARIO": 66, "RUMO": 30},
            4: {"RODOVIARIO": 16, "RUMO": 73},
            5: {"RODOVIARIO": 54, "RUMO": 42},
            6: {"HBSA": 40, "RODOVIARIO": 34, "RUMO": 19},
            7: {"HBSA": 27, "RODOVIARIO": 24, "RUMO": 36},
            8: {"HBSA": 25, "RODOVIARIO": 25, "RUMO": 36},
            9: {"HBSA": 23, "RODOVIARIO": 24, "RUMO": 39},
            10: {"HBSA": 17, "RODOVIARIO": 22, "RUMO": 45, "OP_NORTE": 8},
            11: {"HBSA": 21, "RODOVIARIO": 19, "RUMO": 42},
            12: {"HBSA": 19, "RODOVIARIO": 15, "RUMO": 47, "OP_SUL": 8},
        },
        2026: {
            1: {"HBSA": 13, "RODOVIARIO": 36, "RUMO": 43},
            2: {"RODOVIARIO": 77, "RUMO": 21},
            3: {"RODOVIARIO": 78, "RUMO": 20},
            4: {"HBSA": 23, "RODOVIARIO": 52, "RUMO": 23},
            5: {"HBSA": 44, "RODOVIARIO": 33, "RUMO": 21},
            6: {"HIDRO PORTO VELHO": 8, "HBSA": 68, "RODOVIARIO": 12, "RUMO": 11},
            7: {"HBSA": 50, "HIDRO PORTO VELHO": 9, "RODOVIARIO": 15, "RUMO": 25},
        },
    },
}

PRODUTO = "Milho"


def main():
    vol_rows = []
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                vol_rows.append((escopo, PRODUTO, ano, MESES[i], float(v), FONTE))

    ms_rows = []
    for escopo, anos in MS.items():
        for ano, meses in anos.items():
            for mes, players in meses.items():
                for player, pct in players.items():
                    ms_rows.append((escopo, PRODUTO, ano, MESES[mes - 1], player, float(pct), FONTE))

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executemany("INSERT INTO market_share_volume VALUES (?,?,?,?,?,?)", vol_rows)
    cur.executemany("INSERT INTO market_share_player VALUES (?,?,?,?,?,?,?)", ms_rows)
    con.commit()

    print(f"market_share_volume (milho): {len(vol_rows)} linhas")
    print(f"market_share_player (milho): {len(ms_rows)} linhas")
    for escopo in VOLUME:
        n = sum(1 for r in vol_rows if r[0] == escopo)
        print(f"  {escopo}: {n} meses com volume lido")
    con.close()


if __name__ == "__main__":
    main()
