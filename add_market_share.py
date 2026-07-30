# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade) no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro, "Competitividade",
09_Fotos/IMG_0221.MOV, 437s) — Produto=SOJA. O relatório-fonte tem uma visão Nacional
("Microrregião: Todos") e depois cicla por dezenas de microrregiões/estados individuais
(GO LESTE, GO SUDOESTE, GO NORTE, GO NORDESTE, MT NORDESTE, TO SUL, BA OESTE SUL, MG
NOROESTE, AC, AL, AM, AP, CE, ES, PA..., cerca de 35-40 no total) — cada uma com o mesmo
par de gráficos: "Volume Movimentado" (barras mensais, 3 cenários/anos) e "Market Share por
Player" (barras 100% empilhadas mensais, por transportador).

Cobertura: Nacional (agregado "Todos") + corredor NORTE completo (BA Oeste Norte, MA Sul,
MT Nordeste, PA Sudeste, PI Sul, TO Centro, TO Leste, TO Sul) + corredor SUL completo (Go
Leste, Go Norte, Go Sudoeste, MG Noroeste, MG Triangulo, MT Medio Norte, MT Nordeste Sul,
MT Sudeste) + OUTROS (AC, AL, AM, BA Oeste Sul, BA Outros, CE, ES, MA Outros, MG Outros,
MS Norte, MS Sul, MT Norte, MT Oeste, PA Nordeste, PA Outros, PI Outros, PR, RJ, RO) — ~34
regiões no total, cobertura equivalente à de Farelo de Soja. GO Noroeste, RN e alguns
estados (PB, PE, RS, SC, SE, SP) não aparecem com dado próprio no vídeo-fonte (volume
zero ou não capturados nos ~340s cobertos antes do vídeo pivotar para a dimensão Porto).
Cada valor abaixo foi lido direto do rótulo numérico da barra (frame full-res); quando a
barra não tinha rótulo visível (PowerBI esconde rótulos que colidiriam em barras próximas
em altura, ou o dropdown de Microrregião ocluiu o gráfico), o mês fica None — não foi
estimado.

Uso:  python3 add_market_share.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0221.MOV) — transcrição manual dos rótulos numéricos das barras. "
         "Cobertura: Nacional + corredor NORTE + corredor SUL + OUTROS (~34 regiões, "
         "equivalente à cobertura de Farelo de Soja).")

# ATUALIZADO jul/2026 (IMG_0229.MOV de 13/07 — "Modo de foco" = ano em fullscreen, 12 rótulos,
# zero colisão; fonte definitiva): anos completos em Nacional/24, MT Nordeste/25, PI Sul/25,
# TO Sul/24+25, GO Leste/25, MT Nordeste Sul/25, MT Oeste/24, MS Sul/25.
# ---------------------------------------------------------------- VOLUME MOVIMENTADO (t)
# escopo -> {ano: {mes(1-12): valor|None}}
VOLUME = {
    "Nacional": {
        2024: [4298338, 9784526, 11219958, 11777246, 10596506, 9617959, 6786545, 5339033, 4384262, 3336488, 1904728, 1356581],
        # 2025 jul-dez: rótulos ocultos pelo dropdown em todos os frames do 6399; set=6680881 e
        # nov=3803328 (leitura antiga do 0229) REMOVIDOS — 5 frames limpos do 6399 (t35/50/77/86/104)
        # mostram barras set-dez pequenas (~1,6M), incompatíveis com esses valores (render-lag no 0229).
        2025: [3323040, 11960994, 14301553, 12467007, 9749852, 7365636, None, None, None, None, None, None],
        2026: [4970515, 11837598, 15665303, 14477609, 14015575, 11855302, 3638767, None, None, None, None, None],
    },
}
VOLUME["GO Leste"] = {
    2024: [41795, 184669, 447073, 621492, 384771, 327673, 107150, None, None, 18607, 24804, 27073],
    2025: [59085, 461051, 658432, 495156, 415312, 348165, 320561, 351192, 264906, 198963, 155682, 108453],
    2026: [24208, 297262, 623823, 606163, 557821, 500603, 151001, None, None, None, None, None],
}
VOLUME["GO Sudoeste"] = {
    2024: [340756, 1329390, 1031529, 758044, 909563, 882057, 431458, 234545, None, 158170, None, 67209],
    2025: [169980, 1806773, 1587413, 1009239, 1104142, 883086, 394093, 330927, 399164, 381008, 345072, 144039],
    2026: [60933, 1106366, 1651404, 950063, 966020, 1136762, 329558, None, None, None, None, None],
}
VOLUME["BA Oeste Norte"] = {
    2024: [145091, 54777, 228951, 197649, 314286, 320605, 338126, 294305, 362044, 331827, 223266, 21801],
    2025: [67762, 202624, 224349, 281701, 307146, 258502, 298221, 466051, 569741, 557421, 213973, 63505],
    2026: [90220, 215568, 326782, 358134, 411123, 433342, 150081, None, None, None, None, None],
}
VOLUME["MA Sul"] = {
    2024: [36357, 255252, 380944, 337216, 360955, 317314, 273091, 180108, 131455, 98061, 6034, 6881],
    2025: [20260, 388083, 405115, 360212, 387802, 273642, 200468, 149567, 249151, 213016, 48412, 23414],
    2026: [6861, 190417, 534712, 369274, 327299, 381080, 93985, None, None, None, None, None],
}
# MT Nordeste: 2025 ago-dez do gráfico Volume ficaram atrás do dropdown "Microrregião"
# aberto no vídeo-fonte (oclusão de UI, não gap de rótulo); Market Share 2025 não foi
# afetado (painel mais abaixo, fora da área do dropdown). Reconferido: dropdown
# permanece aberto durante toda a janela de exibição da região (t~60-66s) — nenhum
# frame limpo encontrado antes da transição para BA OESTE NORTE (t~67s). Gap permanente.
VOLUME["MT Nordeste"] = {
    2024: [172572, 570571, 508613, 348706, 407673, 311031, 138068, None, 92195, None, 72165, 30990],
    2025: [75317, 746547, 524448, 509783, 627781, 506292, 211224, 104646, 185237, 179537, 167241, 83230],
    2026: [437269, 765973, 504871, 573437, 672086, 434205, 52121, None, None, None, None, None],
}
# PA Sudeste: vídeo-fonte só mostra jan-nov nos gráficos de 2024/2025 (sem dez).
VOLUME["PA Sudeste"] = {
    2024: [8094, 108764, 195970, 147363, 98635, 96746, 38080, 14565, 6246, 341, 29, None],
    2025: [479, 105091, 207157, 152229, 116681, 147315, None, 95910, 45080, 7395, 1016, None],
    2026: [46971, 195071, 221487, 150404, 147124, 123259, 37530, None, None, None, None, None],
}
VOLUME["PI Sul"] = {
    2024: [571, 9365, 235222, 226389, 184323, 210527, 285574, 284289, 214753, 68743, 26930, 3376],
    2025: [12699, 87231, 248445, 231353, 117139, 145500, 125892, 158909, 187634, 167254, 17997, 8559],
    2026: [11159, 69842, 249081, 185552, 150888, 163724, 71971, None, None, None, None, None],
}
VOLUME["TO Centro"] = {
    2024: [2588, 73770, 144984, 93609, 86242, 48238, 18861, 17693, 3843, 4202, None, 134],
    2025: [5097, 108347, 165403, 113566, 72100, 69853, 57130, 37548, 21631, 27095, 17085, 343],
    2026: [11201, 155641, 179624, 88535, 84010, 88030, 27084, None, None, None, None, None],
}
VOLUME["TO Leste"] = {
    2024: [923, 50811, 62503, 51685, 48716, 34005, 6729, 2710, 4125, 586, 0, 0],
    2025: [8013, 94336, 45183, 20180, 41446, 46806, 14995, 18221, 10024, 8587, 0, 67],
    2026: [1246, 47620, 66233, 34082, 39335, 21712, 11038, None, None, None, None, None],
}
# --- Corredor NORTE, cont. (regiões adicionais capturadas na rodada de fechamento de gap) ---
VOLUME["TO Sul"] = {
    2024: [1750, 120400, 299382, 321486, 244550, 171786, 105438, 91370, 75401, 59829, 43016, 40234],
    2025: [10771, 291144, 484420, 393438, 275092, 195405, 193080, 147772, 153345, 129778, 23937, 5731],
    2026: [18067, 262880, 371421, 396671, 258393, 177178, 48772, None, None, None, None, None],
}
# --- Corredor SUL ---
VOLUME["GO Norte"] = {
    2024: [71, 16481, 131194, 209957, 96652, 77876, 74670, 28165, 7658, 7842, 16700, 9604],
    2025: [4829, 48783, 215060, 186705, 139958, 105784, 74358, 83418, 72178, 15352, 9527, 17039],
    2026: [20977, 26593, 93179, 191326, 112334, 84452, 24300, None, None, None, None, None],
}
# MG Triangulo 2025: completado via modo de foco do IMG_6399.MOV (t41, 12 rótulos).
# MT Nordeste Sul 2025: ago-dez seguem atrás do dropdown "Microrregião" do vídeo-fonte.
VOLUME["MG Triangulo"] = {
    2024: [26701, 277428, 405849, 461792, 332320, 360985, 288165, 203609, 65001, 15827, 4297, 7382],
    2025: [5146, 267300, 568122, 441146, 292932, 213147, 197879, 198238, 158162, 116324, 57801, 61326],
    2026: [18291, 235388, 595014, 519657, 400655, 347563, 131385, None, None, None, None, None],
}
VOLUME["MT Nordeste Sul"] = {
    2024: [72010, 589266, 507608, 560034, 601868, 417167, 178724, 163768, 79378, 72385, 19764, 39665],
    2025: [60889, 647683, 849039, 718009, 927784, 665857, 345004, 271261, 231903, 377337, 228884, 103017],
    2026: [162427, 841968, 915472, 758514, 900939, 781966, 151700, None, None, None, None, None],
}
VOLUME["MG Noroeste"] = {
    2024: [33408, 61696, 140399, 235557, 196587, None, 63651, 33370, None, 8710, 9741, 5932],
    2025: [10083, 105340, 190471, 218574, None, 148431, 120353, 156963, 187853, 92826, 39227, 81333],
    2026: [31282, 144260, 206974, 288606, 344864, 307615, 92575, None, None, None, None, None],
}
VOLUME["MT Medio Norte"] = {
    2024: [741263, 966440, 696045, 795273, 753629, 448884, 129947, 59717, 100247, 115741, 87243, 134634],
    2025: [708839, 1183423, 796794, 1149460, 1146672, 690726, 233676, 190357, 303144, 450867, 287939, None],
    2026: [1403802, 1239066, 947845, 1035362, 1251125, 666893, 146651, None, None, None, None, None],
}
# MT Sudeste 2024/2025: vários meses sem rótulo numérico por barras densas/próximas em
# altura (PowerBI omite o rótulo, não é oclusão) — bar presente mas valor não lido.
VOLUME["MT Sudeste"] = {
    2024: [265562, 565579, 395294, 335161, 395993, None, 226023, None, 133300, None, 81933, 85334],
    2025: [234893, 577214, 541956, 425008, 516393, 553505, 294101, 395728, 230302, 276731, 256599, 336266],
    2026: [299026, 599708, 722494, 536548, 629402, 682351, 203227, None, None, None, None, None],
}
# --- OUTROS: estados com volume residual/esporádico (vídeo só mostra os meses com dado) ---
VOLUME["AC"] = {
    2024: [0, 101, 1755, 476, 0, 0, 0, 0, 0, 0, 0, 0],
    2025: [0, 35, 1270, 1642, 148, 0, 0, 0, 0, 0, 0, 0],
    2026: [0, 852, 1984, 917, 339, 0, 0, None, None, None, None, None],
}
VOLUME["AL"] = {
    2024: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    2025: [25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    2026: [0, 0, 0, 0, 0, 0, 0, None, None, None, None, None],
}
VOLUME["AM"] = {
    2024: [54, 1030, 931, 0, 0, 47, 0, 0, 0, 0, 0, 0],
    2025: [0, 271, 779, 756, 827, 0, 0, 0, 0, 0, 0, 0],
    2026: [294, 1656, 194, 0, 0, 0, 0, None, None, None, None, None],
}
VOLUME["BA Outros"] = {
    2024: [0, 0, 229, 0, 2544, 48, 0, 0, 1500, 0, 0, 0],
    2025: [0, 0, 96, 749, 247, 1326, 720, 552, 350, 0, 0, 0],
    2026: [0, 0, 263, 386, 69, 756, 1261, None, None, None, None, None],
}
VOLUME["ES"] = {
    2024: [127, 95, 64, 127, 191, 64, 223, 318, 32, 382, 159, 64],
    2025: [64, 877, 746, 227, 223, 191, 700, 382, 159, 286, 288, 194],
    2026: [374, 496, 0, 34, 0, 0, 0, None, None, None, None, None],
}
# MA Outros: nov ficou sem valor legível nos 3 anos (bar presente, rótulo não capturado).
VOLUME["MA Outros"] = {
    2024: [151, 541, 5539, 68450, 282802, 249502, 166707, 126040, 65409, 18675, 5964, 86],
    2025: [3203, 2998, 12396, 111918, 350169, 278627, 199990, 102769, 21368, None, 3369, 3329],
    2026: [191, 2196, 16071, 133353, 297622, 336258, 120113, None, None, None, None, None],
}
VOLUME["MS Norte"] = {
    2024: [24355, 113941, 150194, 196928, 158343, None, 67234, 32334, 19671, 16382, 1237, 374],
    2025: [7078, 103488, 188242, 166228, 137841, 109816, None, 52689, 64609, 50557, 26497, 35076],
    2026: [26284, 105999, 269974, 177009, 151424, 164570, 50309, None, None, None, None, None],
}
# MT Norte 2025: abr sem rótulo (barra densa) e ago-dez atrás do dropdown de Microrregião.
VOLUME["MT Norte"] = {
    2024: [384104, 1140304, None, 1074228, 816882, 363891, 54170, 23573, 10142, 29958, 8722, 15111],
    # 2025 CORRIGIDO+COMPLETO jul/2026 (IMG_0229 t~384s, "Modo de foco" fullscreen do ano —
    # 12 barras, 12 rótulos, zero colisão): a 1ª passada tinha empacotado os rótulos
    # (mar era 1.342.810, não 1.372.175; abr/mai existiam e foram pulados).
    2025: [243042, 1387984, 1342810, 1372175, 1261741, 807528, 234888, 126702, 175293, 180690, 126037, 110107],
    2026: [669054, 1415701, 1414152, 1253913, 1157589, 568086, 90886, None, None, None, None, None],
}
VOLUME["PA Nordeste"] = {
    2024: [985, 3437, 23715, 166284, 224345, 273453, 181270, 47283, 5426, 228, 91, 2],
    2025: [1, 2510, 31987, 144455, 205020, 164930, 238483, 140269, 68768, 2021, 2372, 1],
    2026: [726, 9381, 29764, 176610, 241689, 143236, 42587, None, None, None, None, None],
}
VOLUME["PI Outros"] = {
    2024: [0, 52, 8315, 31729, 5200, 2514, 4855, 11279, 7519, 1069, 542, 0],
    2025: [0, 0, 0, 13000, 2541, 1614, 7651, 6695, 0, 0, 0, 0],
    2026: [0, 0, 4846, 1631, 750, 2165, 1728, None, None, None, None, None],
}
VOLUME["PR"] = {
    2024: [927090, None, 1214684, 940915, None, 1253469, 1071642, 1274677, 904948, 283921, None, 217527],
    2025: [629598, 1147727, 1621808, 804242, 774716, 777781, 1367871, 1083420, 829665, 758996, 656522, None],
    2026: [599924, 1244654, 1559447, 1074155, 957194, 947191, 349020, None, None, None, None, None],
}
VOLUME["RJ"] = {
    2024: [0, 0, 1071, 314, 0, 0, 1, 0, 0, 0, 0, 0],
    2025: [0, 0, 19, 0, 0, 49, 385, 10, 0, 0, 0, 0],
    2026: [0, 331, 1118, 276, 0, 589, 130, None, None, None, None, None],
}
# BA Oeste Sul: set/2024 sem rótulo (colisão); 2025 ago-nov completados via foco do IMG_6399 (t147).
VOLUME["BA Oeste Sul"] = {
    2024: [10233, 19433, 48517, 34776, 69188, 46899, 91272, 96631, None, 102611, 27551, 6493],
    2025: [30494, 53094, 65403, 53544, 58437, 55134, 92037, 105506, 136802, 144574, 31399, 559],
    2026: [37118, 63637, 77912, 95128, 105618, 105381, 55241, None, None, None, None, None],
}
# CE: só 2 meses aparecem no vídeo; julho tem rótulo parcialmente cortado pelo dropdown
# (dígitos ilegíveis) — omitido por precaução.
VOLUME["CE"] = {
    2024: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    2025: [0, 0, 0, 0, 0, 40, None, 0, 0, 0, 0, 0],
    2026: [0, 0, 0, 0, 0, 0, 0, None, None, None, None, None],
}
# MG Outros: ago/2024 e jul-dez/2025 sem rótulo legível (barra densa / texto sobreposto).
VOLUME["MG Outros"] = {
    2024: [36381, 188196, 355729, None, 259475, 156363, 97078, 46926, 10379, 1063, 714, 2892],
    2025: [1696, 145944, 487089, 424774, 266855, 166389, None, 70613, 39151, 20215, 15810, 20529],
    2026: [9430, 113344, 399224, 481655, 348433, 228067, 71224, None, None, None, None, None],
}
VOLUME["MS Sul"] = {
    # CORRIGIDO jul/2026 (IMG_0229 t~376s, centragem rótulo→barra): 1ª passada empacotou —
    # jun/24 era 562.794 (rótulo pulado); em 2025, 468.389=MAI, 271.388=JUL, 130.049=AGO,
    # 235.940=OUT (abr/jun/set/nov sem rótulo por colisão -> None).
    2024: [195554, 807816, 673937, 461959, None, 562794, 362154, 233741, None, 34176, 860, 162],
    2025: [299383, 661129, 412788, 364686, 468389, 449394, 271388, 130049, 183982, 235940, 203022, 183275],
    2026: [121289, 953470, 735298, 536986, 614892, 722247, 210488, None, None, None, None, None],
}
VOLUME["MT Oeste"] = {
    2024: [352464, 427501, 476694, 531253, 493520, 376517, 146370, 57228, 87076, 107854, 41250, 73462],
    2025: [136969, 465269, 532419, 625147, 703447, 480716, 183596, 186064, 204430, 275129, 235936, None],
    2026: [545032, 741661, 709289, 740152, 716966, 615024, 201883, None, None, None, None, None],
}
VOLUME["PA Outros"] = {
    2024: [10625, 97280, 145462, 166707, None, 142132, 84028, 23365, 2799, 194, 16, 0],
    2025: [14059, 121150, 183326, None, 160534, None, 98525, 59837, 50051, 6639, 2512, 2955],
    2026: [55116, 171755, 229879, 240892, 221782, 173984, 42454, None, None, None, None, None],
}
# RO: 100% HIDRO PORTO VELHO em quase todos os meses (ver MS abaixo); out/2025 ilegível
# (fragmento de rótulo sobreposto por outro elemento da tela).
VOLUME["RO"] = {
    2024: [32669, 86093, 106102, 70796, 41223, 18894, 4474, 1519, 0, 1, 142, 973],
    2025: [14832, 148496, 168845, 131577, 110072, 35408, 8894, 2262, 197, 9244, 776, 1916],
    2026: [40792, 200454, 343842, 162769, 182188, 53469, 4851, None, None, None, None, None],
}
# AL, ES, CE: dados pontuais (1-2 meses no vídeo-fonte), 100% de um único player.

# ---------------------------------------------------------- MARKET SHARE POR PLAYER (%)
# escopo -> {ano: {mes(1-12): {player: pct|omitido se não rotulado}}}
MS = {
    "Nacional": {
        2024: {
            1: {"HBSA": 15, "RODOVIARIO": 46, "RUMO": 25},
            2: {"HBSA": 14, "RODOVIARIO": 39, "RUMO": 30},
            3: {"HBSA": 11, "RODOVIARIO": 45, "RUMO": 27, "OP_NORTE": 8},
            4: {"HBSA": 11, "RODOVIARIO": 45, "RUMO": 28, "OP_NORTE": 10},
            5: {"HBSA": 8, "RODOVIARIO": 44, "RUMO": 30, "OP_NORTE": 10},
            6: {"RODOVIARIO": 53, "RUMO": 27, "OP_NORTE": 9},
            7: {"RODOVIARIO": 60, "RUMO": 22, "OP_NORTE": 9},
            8: {"RODOVIARIO": 66, "RUMO": 19, "OP_NORTE": 10},
            9: {"RODOVIARIO": 64, "RUMO": 21, "OP_NORTE": 11},
            10: {"RODOVIARIO": 61, "RUMO": 25, "OP_NORTE": 11},
            11: {"RODOVIARIO": 63, "RUMO": 23, "OP_NORTE": 10},
            12: {"RODOVIARIO": 53, "RUMO": 38},
        },
        2025: {
            1: {"HBSA": 13, "RODOVIARIO": 54, "RUMO": 27},
            2: {"HBSA": 15, "RODOVIARIO": 42, "RUMO": 25},
            3: {"HBSA": 10, "RODOVIARIO": 48, "RUMO": 24, "OP_SUL": 8},
            4: {"HBSA": 10, "RODOVIARIO": 44, "RUMO": 26, "OP_NORTE": 8, "OP_SUL": 8},
            5: {"HBSA": 10, "RODOVIARIO": 41, "RUMO": 29, "OP_NORTE": 8},
            6: {"RODOVIARIO": 41, "RUMO": 30, "OP_NORTE": 10, "OP_SUL": 9},
            7: {"RODOVIARIO": 58, "RUMO": 20, "OP_NORTE": 8, "OP_SUL": 10},
            8: {"RODOVIARIO": 60, "RUMO": 19, "OP_SUL": 11},
            9: {"RODOVIARIO": 52, "RUMO": 23, "OP_NORTE": 11, "OP_SUL": 12},
            10: {"RODOVIARIO": 46, "RUMO": 29, "OP_NORTE": 11, "OP_SUL": 12},
            11: {"RODOVIARIO": 38, "RUMO": 36, "OP_NORTE": 11, "OP_SUL": 13},
            12: {"RODOVIARIO": 44, "RUMO": 31, "OP_SUL": 15},
        },
        2026: {
            1: {"HBSA": 15, "RODOVIARIO": 34, "RUMO": 34, "OP_NORTE": 7},
            2: {"HBSA": 12, "RODOVIARIO": 37, "RUMO": 31, "OP_NORTE": 8, "OP_SUL": 7},
            3: {"HBSA": 11, "RODOVIARIO": 42, "RUMO": 28, "OP_SUL": 9},
            4: {"HBSA": 10, "RODOVIARIO": 44, "RUMO": 26, "OP_NORTE": 6, "OP_SUL": 10},
            5: {"RUMO": 29, "OP_NORTE": 8, "OP_SUL": 8},
            6: {"RODOVIARIO": 43, "RUMO": 31, "OP_NORTE": 9, "OP_SUL": 8},
            7: {"RODOVIARIO": 47, "RUMO": 29, "OP_NORTE": 3, "OP_SUL": 11},
        },
    },
    "GO Leste": {
        2024: {
            1: {"RODOVIARIO": 46, "RUMO": 25, "HBSA": 15},
            2: {"RODOVIARIO": 39, "RUMO": 30, "HBSA": 14},
            3: {"RODOVIARIO": 45, "RUMO": 27, "OP_NORTE": 8, "HBSA": 11},
            4: {"RODOVIARIO": 45, "RUMO": 28, "OP_NORTE": 10, "HBSA": 11},
            5: {"RODOVIARIO": 44, "RUMO": 30, "OP_NORTE": 10, "HBSA": 8},
            6: {"RODOVIARIO": 53, "RUMO": 27, "OP_NORTE": 9},
            7: {"RODOVIARIO": 60, "RUMO": 22, "OP_NORTE": 9},
            8: {"RODOVIARIO": 66, "RUMO": 19, "OP_NORTE": 10},
            9: {"RODOVIARIO": 64, "RUMO": 21, "OP_NORTE": 11},
            10: {"RODOVIARIO": 61, "RUMO": 25, "OP_NORTE": 11},
            11: {"RODOVIARIO": 63, "RUMO": 23, "OP_NORTE": 10},
            12: {"RUMO": 57, "OP_SUL": 42},
        },
        2025: {
            1: {"RODOVIARIO": 75, "OP_SUL": 17},
            2: {"RODOVIARIO": 49, "OP_SUL": 46},
            3: {"RODOVIARIO": 55, "OP_SUL": 42},
            4: {"RODOVIARIO": 42, "OP_SUL": 57},
            5: {"RODOVIARIO": 48, "OP_SUL": 47},
            6: {"RODOVIARIO": 40, "OP_SUL": 59},
            7: {"RODOVIARIO": 32, "OP_SUL": 67},
            8: {"RODOVIARIO": 27, "OP_SUL": 70},
            9: {"RODOVIARIO": 22, "OP_SUL": 78},
            10: {"RODOVIARIO": 20, "OP_SUL": 80},
            11: {"RODOVIARIO": 21, "OP_SUL": 79},
            12: {"RODOVIARIO": 28, "OP_SUL": 72},
        },
        2026: {
            1: {"RODOVIARIO": 91, "OP_SUL": 9},
            2: {"RODOVIARIO": 33, "OP_SUL": 63},
            3: {"RODOVIARIO": 30, "RUMO": 10, "OP_SUL": 60},
            4: {"RODOVIARIO": 39, "RUMO": 6, "OP_SUL": 54},
            5: {"RODOVIARIO": 46, "RUMO": 8, "OP_SUL": 46},
            6: {"RODOVIARIO": 48, "RUMO": 9, "OP_SUL": 43},
            7: {"RODOVIARIO": 40, "OP_SUL": 56},
        },
    },
    "GO Sudoeste": {
        2024: {
            1: {"RODOVIARIO": 52, "RUMO": 30, "OP_SUL": 18},
            2: {"RODOVIARIO": 42, "RUMO": 33, "OP_SUL": 25},
            3: {"RODOVIARIO": 29, "RUMO": 49, "OP_SUL": 22},
            4: {"RODOVIARIO": 27, "RUMO": 52, "OP_SUL": 21},
            5: {"RODOVIARIO": 29, "RUMO": 55, "OP_SUL": 16},
            6: {"RODOVIARIO": 33, "RUMO": 57, "OP_SUL": 10},
            7: {"RODOVIARIO": 18, "RUMO": 73, "OP_SUL": 10},
            8: {"RODOVIARIO": 14, "RUMO": 66, "OP_SUL": 20},
            9: {"RODOVIARIO": 8, "RUMO": 77, "OP_SUL": 15},
            10: {"RUMO": 78, "OP_SUL": 21},
            11: {"RUMO": 72, "OP_SUL": 24},
            12: {"RUMO": 94},
        },
        2025: {
            1: {"RODOVIARIO": 53, "RUMO": 40},
            2: {"RODOVIARIO": 41, "RUMO": 44, "OP_SUL": 15},
            3: {"RODOVIARIO": 34, "RUMO": 47, "OP_SUL": 18},
            4: {"RODOVIARIO": 21, "RUMO": 51, "OP_SUL": 29},
            5: {"RODOVIARIO": 30, "RUMO": 52, "OP_SUL": 18},
            6: {"RODOVIARIO": 21, "RUMO": 62, "OP_SUL": 17},
            7: {"RODOVIARIO": 17, "RUMO": 55, "OP_SUL": 29},
            8: {"RODOVIARIO": 24, "RUMO": 46, "OP_SUL": 30},
            9: {"RODOVIARIO": 11, "RUMO": 55, "OP_SUL": 34},
            10: {"RUMO": 61, "OP_SUL": 34},
            11: {"RODOVIARIO": 15, "RUMO": 47, "OP_SUL": 36},
            12: {"RODOVIARIO": 10, "OP_NORTE": 12, "OP_SUL": 78},
        },
        2026: {
            1: {"RODOVIARIO": 65, "RUMO": 23, "OP_SUL": 11},
            2: {"RODOVIARIO": 32, "RUMO": 48, "OP_SUL": 20},
            3: {"RODOVIARIO": 25, "RUMO": 53, "OP_SUL": 22},
            4: {"RODOVIARIO": 26, "RUMO": 50, "OP_SUL": 24},
            5: {"RODOVIARIO": 25, "RUMO": 59, "OP_SUL": 16},
            6: {"RODOVIARIO": 28, "RUMO": 54, "OP_SUL": 19},
            7: {"RODOVIARIO": 17, "RUMO": 48, "OP_SUL": 34},
        },
    },
    "BA Oeste Norte": {
        2024: {
            1: {"RODOVIARIO": 85, "OP_NORTE": 15},
            2: {"RODOVIARIO": 65, "OP_NORTE": 35},
            3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 85, "OP_NORTE": 15},
            5: {"RODOVIARIO": 59, "OP_NORTE": 41},
            6: {"RODOVIARIO": 40, "OP_NORTE": 60},
            7: {"RODOVIARIO": 33, "OP_NORTE": 67},
            8: {"RODOVIARIO": 32, "OP_NORTE": 68},
            9: {"RODOVIARIO": 39, "OP_NORTE": 59},
            10: {"RODOVIARIO": 46, "OP_NORTE": 54},
            11: {"RODOVIARIO": 41, "OP_NORTE": 59},
            12: {"RODOVIARIO": 65, "OP_NORTE": 35},
        },
        2025: {
            1: {"RODOVIARIO": 77, "OP_NORTE": 23},
            2: {"RODOVIARIO": 90, "OP_NORTE": 10},
            3: {"RODOVIARIO": 100},
            5: {"RODOVIARIO": 100},
            6: {"RODOVIARIO": 96},
            7: {"RODOVIARIO": 93},
            8: {"RODOVIARIO": 78, "OP_NORTE": 22},
            9: {"RODOVIARIO": 54, "OP_NORTE": 46},
            10: {"RODOVIARIO": 65, "OP_NORTE": 35},
            11: {"RODOVIARIO": 29, "OP_NORTE": 71},
            12: {"OP_NORTE": 99},
        },
        2026: {
            1: {"RODOVIARIO": 69, "OP_NORTE": 31},
            2: {"RODOVIARIO": 95},
            3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 100},
            5: {"RODOVIARIO": 88, "OP_NORTE": 12},
            6: {"RODOVIARIO": 84, "OP_NORTE": 16},
            7: {"RODOVIARIO": 69, "OP_NORTE": 31},
        },
    },
    "MA Sul": {
        2024: {
            1: {"RODOVIARIO": 26, "OP_NORTE": 74},
            2: {"RODOVIARIO": 47, "OP_NORTE": 53},
            3: {"RODOVIARIO": 61, "OP_NORTE": 39},
            4: {"RODOVIARIO": 63, "OP_NORTE": 37},
            5: {"RODOVIARIO": 41, "OP_NORTE": 59},
            6: {"RODOVIARIO": 43, "OP_NORTE": 57},
            7: {"RODOVIARIO": 51, "OP_NORTE": 49},
            8: {"RODOVIARIO": 54, "OP_NORTE": 46},
            9: {"RODOVIARIO": 57, "OP_NORTE": 43},
            10: {"RODOVIARIO": 59, "OP_NORTE": 41},
            11: {"RODOVIARIO": 75, "OP_NORTE": 25},
            12: {"OP_NORTE": 99},
        },
        2025: {
            1: {"RODOVIARIO": 53, "OP_NORTE": 47},
            2: {"RODOVIARIO": 61, "OP_NORTE": 39},
            3: {"RODOVIARIO": 70, "OP_NORTE": 30},
            4: {"RODOVIARIO": 67, "OP_NORTE": 33},
            5: {"RODOVIARIO": 49, "OP_NORTE": 51},
            6: {"RODOVIARIO": 48, "OP_NORTE": 52},
            7: {"RODOVIARIO": 60, "OP_NORTE": 40},
            8: {"RODOVIARIO": 62, "OP_NORTE": 38},
            9: {"RODOVIARIO": 47, "OP_NORTE": 53},
            10: {"RODOVIARIO": 35, "OP_NORTE": 65},
            11: {"RODOVIARIO": 37, "OP_NORTE": 63},
            12: {"RODOVIARIO": 30, "OP_NORTE": 70},
        },
        2026: {
            1: {"OP_NORTE": 97},
            2: {"RODOVIARIO": 62, "OP_NORTE": 38},
            3: {"RODOVIARIO": 67, "OP_NORTE": 33},
            4: {"RODOVIARIO": 52, "OP_NORTE": 48},
            5: {"RODOVIARIO": 39, "OP_NORTE": 61},
            6: {"RODOVIARIO": 37, "OP_NORTE": 63},
            7: {"RODOVIARIO": 50, "OP_NORTE": 50},
        },
    },
    "MT Nordeste": {
        2024: {
            1: {"RODOVIARIO": 42, "OP_NORTE": 46, "OP_SUL": 9},
            2: {"RODOVIARIO": 38, "OP_NORTE": 51},
            3: {"RODOVIARIO": 28, "RUMO": 19, "OP_NORTE": 50},
            4: {"RODOVIARIO": 27, "RUMO": 21, "OP_NORTE": 51},
            5: {"RODOVIARIO": 26, "RUMO": 16, "OP_NORTE": 54},
            6: {"RODOVIARIO": 31, "RUMO": 24, "OP_NORTE": 42},
            7: {"RODOVIARIO": 34, "RUMO": 31, "OP_NORTE": 35},
            8: {"RODOVIARIO": 34, "RUMO": 19, "OP_NORTE": 47},
            9: {"RODOVIARIO": 36, "OP_NORTE": 62},
            10: {"RODOVIARIO": 43, "OP_NORTE": 56},
            11: {"RUMO": 78, "OP_NORTE": 22},
            12: {"RUMO": 98},
        },
        2025: {
            1: {"RODOVIARIO": 81, "RUMO": 11, "OP_NORTE": 8},
            2: {"RODOVIARIO": 51, "OP_NORTE": 45},
            3: {"RODOVIARIO": 48, "OP_NORTE": 43},
            4: {"RODOVIARIO": 34, "OP_NORTE": 55},
            5: {"RODOVIARIO": 27, "RUMO": 17, "OP_NORTE": 51},
            6: {"RODOVIARIO": 21, "RUMO": 15, "OP_NORTE": 59},
            7: {"RODOVIARIO": 20, "RUMO": 15, "OP_NORTE": 43, "OP_SUL": 22},
            8: {"RODOVIARIO": 25, "RUMO": 10, "OP_NORTE": 34, "OP_SUL": 30},
            9: {"RODOVIARIO": 19, "RUMO": 9, "OP_NORTE": 59, "OP_SUL": 13},
            10: {"RUMO": 18, "OP_NORTE": 72},
            11: {"RUMO": 8, "OP_NORTE": 87},
            12: {"RODOVIARIO": 26, "OP_NORTE": 70},
        },
        2026: {
            1: {"RODOVIARIO": 30, "OP_NORTE": 61},
            2: {"RODOVIARIO": 43, "RUMO": 9, "OP_NORTE": 44},
            3: {"RODOVIARIO": 61, "RUMO": 11, "OP_NORTE": 24},
            4: {"RODOVIARIO": 60, "RUMO": 9, "OP_NORTE": 28},
            5: {"RODOVIARIO": 37, "RUMO": 11, "OP_NORTE": 44},
            6: {"RODOVIARIO": 39, "RUMO": 10, "OP_NORTE": 41},
            7: {"RODOVIARIO": 73, "RUMO": 11, "OP_NORTE": 13},
        },
    },
    "PA Sudeste": {
        2024: {
            1: {"RODOVIARIO": 38, "OP_NORTE": 62},
            2: {"RODOVIARIO": 75, "OP_NORTE": 25},
            3: {"RODOVIARIO": 80, "OP_NORTE": 20},
            4: {"RODOVIARIO": 58, "OP_NORTE": 42},
            5: {"RODOVIARIO": 53, "OP_NORTE": 47},
            6: {"RODOVIARIO": 32, "OP_NORTE": 68},
            7: {"RODOVIARIO": 44, "OP_NORTE": 56},
            8: {"RODOVIARIO": 40, "OP_NORTE": 60},
            9: {"RODOVIARIO": 77, "OP_NORTE": 21},
            10: {"RODOVIARIO": 56, "RUMO": 32, "OP_NORTE": 13},
            11: {"RUMO": 100},
        },
        2025: {
            1: {"RODOVIARIO": 100},
            2: {"RODOVIARIO": 90, "OP_NORTE": 10},
            3: {"RODOVIARIO": 68, "OP_NORTE": 32},
            4: {"RODOVIARIO": 54, "OP_NORTE": 46},
            5: {"RODOVIARIO": 42, "OP_NORTE": 58},
            6: {"RODOVIARIO": 37, "OP_NORTE": 63},
            7: {"RODOVIARIO": 39, "OP_NORTE": 61},
            8: {"RODOVIARIO": 27, "OP_NORTE": 73},
            9: {"RODOVIARIO": 12, "OP_NORTE": 88},
            10: {"RODOVIARIO": 40, "OP_NORTE": 60},
            11: {"OP_NORTE": 100},
        },
        2026: {
            1: {"RODOVIARIO": 77, "OP_NORTE": 23},
            2: {"RODOVIARIO": 71, "OP_NORTE": 29},
            3: {"RODOVIARIO": 84, "OP_NORTE": 16},
            4: {"RODOVIARIO": 72, "OP_NORTE": 28},
            5: {"RODOVIARIO": 68, "OP_NORTE": 32},
            6: {"RODOVIARIO": 43, "OP_NORTE": 57},
            7: {"RODOVIARIO": 28, "OP_NORTE": 72},
        },
    },
    "PI Sul": {
        2024: {
            1: {"RODOVIARIO": 100},
            2: {"RODOVIARIO": 89, "OP_NORTE": 11},
            3: {"RODOVIARIO": 89, "OP_NORTE": 11},
            4: {"RODOVIARIO": 96},
            5: {"RODOVIARIO": 91, "OP_NORTE": 9},
            6: {"RODOVIARIO": 91},
            7: {"RODOVIARIO": 96},
            8: {"RODOVIARIO": 89, "OP_NORTE": 11},
            9: {"RODOVIARIO": 82, "OP_NORTE": 18},
            10: {"RODOVIARIO": 96},
            11: {"RODOVIARIO": 100},
            12: {"RUMO": 83, "RODOVIARIO": 17},
        },
        # 2025: no frame t=96 o painel "Market Share por Player" ainda estava com o render
        # antigo (idêntico byte-a-byte ao de Nacional 2025 — artefato de lag do PowerBI ao
        # trocar o filtro de Microrregião, visual não tinha atualizado ainda). Frame t=97
        # (1s depois) já mostra os dados corretos, bem mais simples (quase só RODOVIARIO).
        # Lição: sempre conferir 2+ frames próximos quando um painel muda de escopo, não
        # confiar no primeiro frame só — sobretudo comparando contra dados já capturados
        # de outro escopo (se bater 100% igual, é sinal de render não atualizado).
        2025: {
            1: {"RUMO": 15, "RODOVIARIO": 85},
            2: {"RODOVIARIO": 97},
            3: {"OP_NORTE": 15, "RODOVIARIO": 84},
            4: {"OP_NORTE": 17, "RODOVIARIO": 83},
            5: {"OP_NORTE": 9, "RODOVIARIO": 91},
            6: {"RODOVIARIO": 100},
            7: {"RODOVIARIO": 94},
            8: {"OP_NORTE": 10, "RODOVIARIO": 90},
            9: {"OP_NORTE": 13, "RODOVIARIO": 87},
            10: {"RODOVIARIO": 96},
            11: {"OP_NORTE": 30, "RODOVIARIO": 70},
            12: {"RODOVIARIO": 98},
        },
        2026: {
            1: {"RODOVIARIO": 49, "OP_NORTE": 51},
            2: {"RODOVIARIO": 81, "OP_NORTE": 19},
            3: {"RODOVIARIO": 88, "OP_NORTE": 12},
            4: {"RODOVIARIO": 92, "OP_NORTE": 7},
            5: {"RODOVIARIO": 92, "OP_NORTE": 7},
            6: {"RODOVIARIO": 79, "OP_NORTE": 20},
            7: {"RODOVIARIO": 79, "OP_NORTE": 21},
        },
    },
    "TO Centro": {
        2024: {
            1: {"OP_NORTE": 100},
            2: {"OP_NORTE": 95},
            3: {"OP_NORTE": 88, "RODOVIARIO": 12},
            4: {"OP_NORTE": 94},
            5: {"OP_NORTE": 95},
            6: {"OP_NORTE": 90, "RODOVIARIO": 10},
            7: {"OP_NORTE": 100},
            8: {"OP_NORTE": 100},
            9: {"OP_NORTE": 100},
            10: {"OP_NORTE": 100},
            12: {"OP_NORTE": 100},
        },
        2025: {
            1: {"OP_NORTE": 96},
            2: {"OP_NORTE": 81, "RODOVIARIO": 18},
            3: {"OP_NORTE": 81, "RODOVIARIO": 19},
            4: {"OP_NORTE": 78, "RODOVIARIO": 22},
            5: {"OP_NORTE": 96},
            6: {"OP_NORTE": 100},
            7: {"OP_NORTE": 90, "RODOVIARIO": 10},
            8: {"OP_NORTE": 56, "RODOVIARIO": 44},
            9: {"OP_NORTE": 87, "RODOVIARIO": 13},
            10: {"OP_NORTE": 94},
            11: {"OP_NORTE": 100},
            12: {"OP_NORTE": 77, "RODOVIARIO": 23},
        },
        2026: {
            1: {"OP_NORTE": 80, "RODOVIARIO": 20},
            2: {"OP_NORTE": 81, "RODOVIARIO": 19},
            3: {"OP_NORTE": 89, "RODOVIARIO": 11},
            4: {"OP_NORTE": 88, "RODOVIARIO": 12},
            5: {"OP_NORTE": 94, "RODOVIARIO": 6},
            6: {"OP_NORTE": 95},
            7: {"OP_NORTE": 97},
        },
    },
    "TO Leste": {
        2024: {
            1: {"RODOVIARIO": 83, "OP_NORTE": 17},
            2: {"RODOVIARIO": 13, "OP_NORTE": 87},
            3: {"RODOVIARIO": 52, "OP_NORTE": 48},
            4: {"RODOVIARIO": 46, "OP_NORTE": 54},
            5: {"RODOVIARIO": 16, "OP_NORTE": 84},
            6: {"RODOVIARIO": 9, "OP_NORTE": 91},
            7: {"RODOVIARIO": 20, "OP_NORTE": 80},
            8: {"RODOVIARIO": 49, "OP_NORTE": 51},
            9: {"RODOVIARIO": 61, "OP_NORTE": 39},
            10: {"OP_NORTE": 100},
        },
        2025: {
            1: {"RODOVIARIO": 93},
            2: {"RODOVIARIO": 56, "OP_NORTE": 44},
            3: {"RODOVIARIO": 60, "OP_NORTE": 40},
            4: {"RODOVIARIO": 15, "OP_NORTE": 85},
            5: {"RODOVIARIO": 21, "OP_NORTE": 79},
            6: {"RODOVIARIO": 21, "OP_NORTE": 79},
            7: {"OP_NORTE": 96},
            8: {"OP_NORTE": 95},
            9: {"RODOVIARIO": 18, "OP_NORTE": 82},
            10: {"OP_NORTE": 100},
            12: {"OP_NORTE": 100},
        },
        2026: {
            1: {"OP_NORTE": 100},
            2: {"RODOVIARIO": 42, "OP_NORTE": 58},
            3: {"RODOVIARIO": 30, "OP_NORTE": 70},
            4: {"RODOVIARIO": 10, "OP_NORTE": 90},
            5: {"OP_NORTE": 95},
            6: {"OP_NORTE": 100},
            7: {"OP_NORTE": 99},
        },
    },
    # --- Regiões de player único (100%) capturadas na rodada de fechamento de gap ---
    "AC": {
        2024: {2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100}, 4: {"HIDRO PORTO VELHO": 100}},
        2025: {2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100}, 4: {"HIDRO PORTO VELHO": 100}, 5: {"HIDRO PORTO VELHO": 100}},
        2026: {2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100}, 4: {"HIDRO PORTO VELHO": 100}, 5: {"HIDRO PORTO VELHO": 100}},
    },
    "AL": {
        2025: {1: {"HIDRO PORTO VELHO": 100}},
    },
    "AM": {
        2024: {1: {"HIDRO PORTO VELHO": 100}, 2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100}, 6: {"HIDRO PORTO VELHO": 100}},
        2025: {2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100}, 4: {"HIDRO PORTO VELHO": 100}, 5: {"HIDRO PORTO VELHO": 100}},
        2026: {1: {"HIDRO PORTO VELHO": 100}, 2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100}},
    },
    "BA Outros": {
        2024: {3: {"HBSA": 38, "RODOVIARIO": 62}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}},
        2025: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
               7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}},
        2026: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
               7: {"HBSA": 10, "RODOVIARIO": 90}},
    },
    "PI Outros": {
        2024: {2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
               6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100},
               10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100}},
        2025: {4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}},
        2026: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
    },
    "RJ": {
        2024: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
        2025: {3: {"OP_SUL": 100}, 6: {"OP_NORTE": 100}, 7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}},
        2026: {2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}},
    },
    "ES": {
        2025: {6: {"RODOVIARIO": 100}},
    },
    "CE": {
        2025: {6: {"RODOVIARIO": 100}},
    },
    "RO": {
        2024: {1: {"HIDRO PORTO VELHO": 100}, 2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100},
               4: {"HIDRO PORTO VELHO": 100}, 5: {"HIDRO PORTO VELHO": 100}, 6: {"HIDRO PORTO VELHO": 100},
               7: {"HIDRO PORTO VELHO": 100}, 8: {"HIDRO PORTO VELHO": 100}, 9: {"HIDRO PORTO VELHO": 100},
               10: {"RUMO": 28, "HIDRO PORTO VELHO": 72}, 11: {"HIDRO PORTO VELHO": 100}},
        2025: {1: {"HIDRO PORTO VELHO": 100}, 2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100},
               4: {"HIDRO PORTO VELHO": 100}, 5: {"HIDRO PORTO VELHO": 99}, 6: {"HIDRO PORTO VELHO": 100},
               7: {"HIDRO PORTO VELHO": 100}, 8: {"HIDRO PORTO VELHO": 100}, 9: {"HIDRO PORTO VELHO": 100},
               11: {"HIDRO PORTO VELHO": 100}},
        2026: {1: {"HIDRO PORTO VELHO": 100}, 2: {"HIDRO PORTO VELHO": 100}, 3: {"HIDRO PORTO VELHO": 100},
               4: {"HIDRO PORTO VELHO": 100}, 5: {"HIDRO PORTO VELHO": 100}, 6: {"HIDRO PORTO VELHO": 100},
               7: {"HIDRO PORTO VELHO": 100}},
    },
    "MA Outros": {
        2024: {1: {"RODOVIARIO": 65, "OP_NORTE": 35}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 36, "OP_NORTE": 64},
               4: {"RODOVIARIO": 71, "OP_NORTE": 29}, 5: {"RODOVIARIO": 89, "OP_NORTE": 11}, 6: {"RODOVIARIO": 90, "OP_NORTE": 10},
               7: {"RODOVIARIO": 95}, 8: {"RODOVIARIO": 97}, 9: {"RODOVIARIO": 90, "OP_NORTE": 10}, 12: {"RODOVIARIO": 100}},
        2025: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 97}, 3: {"RODOVIARIO": 50, "OP_NORTE": 50},
               4: {"RODOVIARIO": 85, "OP_NORTE": 15}, 5: {"RODOVIARIO": 94, "OP_NORTE": 17}, 6: {"RODOVIARIO": 83, "OP_NORTE": 17},
               7: {"RODOVIARIO": 93}, 8: {"RODOVIARIO": 99}, 9: {"RODOVIARIO": 97}, 10: {"RODOVIARIO": 77, "OP_NORTE": 23},
               11: {"RODOVIARIO": 35, "OP_NORTE": 65}, 12: {"RODOVIARIO": 58, "OP_NORTE": 42}},
        2026: {1: {"RODOVIARIO": 78, "OP_NORTE": 22}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 88, "OP_NORTE": 12},
               4: {"RODOVIARIO": 85, "OP_NORTE": 15}, 5: {"RODOVIARIO": 82, "OP_NORTE": 18}, 6: {"RODOVIARIO": 89, "OP_NORTE": 11},
               7: {"RODOVIARIO": 96}},
    },
    "TO Sul": {
        # Legendário: HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI NORTE/VLI SUL — dominado por VLI NORTE.
        2024: {
            1: {"OP_NORTE": 97}, 2: {"OP_NORTE": 100}, 3: {"OP_NORTE": 91}, 4: {"OP_NORTE": 96},
            5: {"OP_NORTE": 96}, 6: {"OP_NORTE": 94}, 7: {"OP_NORTE": 99}, 8: {"OP_NORTE": 99},
            9: {"OP_NORTE": 96}, 10: {"OP_NORTE": 98}, 11: {"OP_NORTE": 97}, 12: {"OP_NORTE": 99},
        },
        2025: {
            1: {"OP_NORTE": 88, "RODOVIARIO": 12}, 2: {"OP_NORTE": 85, "RODOVIARIO": 15},
            3: {"OP_NORTE": 91, "RODOVIARIO": 9}, 4: {"OP_NORTE": 94}, 5: {"OP_NORTE": 92},
            6: {"OP_NORTE": 95}, 7: {"OP_NORTE": 96}, 8: {"OP_NORTE": 84, "RODOVIARIO": 14},
            9: {"OP_NORTE": 71, "OP_SUL": 15, "RODOVIARIO": 12}, 10: {"OP_NORTE": 89},
            11: {"OP_NORTE": 98}, 12: {"OP_NORTE": 98},
        },
        2026: {
            1: {"OP_NORTE": 100}, 2: {"OP_NORTE": 88, "RODOVIARIO": 12}, 3: {"OP_NORTE": 87, "RODOVIARIO": 9},
            4: {"OP_NORTE": 94}, 5: {"OP_NORTE": 94}, 6: {"OP_NORTE": 96}, 7: {"OP_NORTE": 92, "RODOVIARIO": 7},
        },
    },
    "MG Triangulo": {
        # Legendário: ADM/RODOVIARIO/RUMO/VLI SUL (4 players).
        2024: {
            1: {"RODOVIARIO": 74, "OP_SUL": 26}, 2: {"RODOVIARIO": 93, "OP_SUL": 15},
            3: {"RODOVIARIO": 85, "OP_SUL": 20}, 4: {"RODOVIARIO": 80, "OP_SUL": 17},
            5: {"RODOVIARIO": 83, "OP_SUL": 17}, 6: {"RODOVIARIO": 85, "OP_SUL": 15},
            7: {"RODOVIARIO": 69, "OP_SUL": 30}, 8: {"RODOVIARIO": 64, "OP_SUL": 35},
            9: {"RODOVIARIO": 31, "OP_SUL": 69}, 10: {"OP_SUL": 94, "RUMO": 20},
            11: {"OP_SUL": 76, "RUMO": 20}, 12: {"RODOVIARIO": 16, "OP_SUL": 79},
        },
        2025: {
            1: {"RODOVIARIO": 94, "OP_SUL": 10}, 2: {"RODOVIARIO": 90, "OP_SUL": 11},
            3: {"RODOVIARIO": 89, "OP_SUL": 11}, 4: {"RODOVIARIO": 88, "OP_SUL": 11},
            5: {"RODOVIARIO": 88, "OP_SUL": 12}, 6: {"RODOVIARIO": 81, "OP_SUL": 18},
            7: {"RODOVIARIO": 74, "OP_SUL": 25}, 8: {"RODOVIARIO": 56, "OP_SUL": 36},
            9: {"RODOVIARIO": 35, "OP_SUL": 65, "HBSA": 8}, 10: {"OP_SUL": 88},
            11: {"OP_SUL": 88, "RODOVIARIO": 11}, 12: {"OP_SUL": 76, "RODOVIARIO": 23},
        },
        2026: {
            1: {"RODOVIARIO": 70, "RUMO": 25}, 2: {"RODOVIARIO": 72, "OP_SUL": 28},
            3: {"RODOVIARIO": 68, "OP_SUL": 32}, 4: {"RODOVIARIO": 60, "OP_SUL": 39},
            5: {"RODOVIARIO": 65, "OP_SUL": 35}, 6: {"RODOVIARIO": 61, "OP_SUL": 39},
            7: {"RODOVIARIO": 43, "OP_SUL": 56},
        },
    },
    "MT Medio Norte": {
        # Legendário: HBSA/HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI NORTE/VLI SUL.
        2024: {
            1: {"HBSA": 46, "RUMO": 44}, 2: {"HBSA": 40, "RUMO": 52}, 3: {"HBSA": 49, "RUMO": 48},
            4: {"HBSA": 44, "RODOVIARIO": 8, "RUMO": 55}, 5: {"HBSA": 34, "RODOVIARIO": 8, "RUMO": 63},
            6: {"HBSA": 29, "RODOVIARIO": 9, "RUMO": 61}, 7: {"HBSA": 13, "RODOVIARIO": 19, "RUMO": 70},
            8: {"RUMO": 76}, 9: {"RODOVIARIO": 12, "RUMO": 97}, 10: {"RUMO": 99}, 11: {"RUMO": 100},
            12: {"RUMO": 100},
        },
        2025: {
            1: {"HBSA": 30, "RODOVIARIO": 8, "RUMO": 61}, 2: {"HBSA": 39, "RUMO": 55},
            3: {"HBSA": 33, "RUMO": 60}, 4: {"HBSA": 27, "RUMO": 71}, 5: {"HBSA": 29, "RUMO": 66},
            6: {"HBSA": 25, "RUMO": 69}, 7: {"HBSA": 23, "RUMO": 67}, 8: {"RUMO": 88},
            9: {"RUMO": 96}, 10: {"RUMO": 99}, 11: {"RUMO": 97}, 12: {"RUMO": 82},
        },
        2026: {
            1: {"HBSA": 20, "RODOVIARIO": 14, "RUMO": 63}, 2: {"HBSA": 22, "RODOVIARIO": 8, "RUMO": 68},
            3: {"HBSA": 31, "RUMO": 63}, 4: {"HBSA": 29, "RUMO": 69}, 5: {"HBSA": 34, "RUMO": 59},
            6: {"HBSA": 31, "RUMO": 59}, 7: {"HBSA": 24, "RUMO": 67},
        },
    },
    "MT Nordeste Sul": {
        # Legendário: HBSA/RODOVIARIO/RUMO/VLI NORTE/VLI SUL.
        2024: {
            1: {"HBSA": 8, "RODOVIARIO": 27, "RUMO": 47}, 2: {"RODOVIARIO": 14, "RUMO": 61},
            3: {"RODOVIARIO": 13, "RUMO": 74}, 4: {"RODOVIARIO": 90}, 5: {"RODOVIARIO": 85},
            6: {"RODOVIARIO": 93}, 7: {"RODOVIARIO": 93}, 8: {"RODOVIARIO": 89},
            9: {"RODOVIARIO": 95}, 10: {"RODOVIARIO": 96}, 11: {"RODOVIARIO": 85, "OP_SUL": 15},
            12: {"RODOVIARIO": 99},
        },
        2025: {
            1: {"RODOVIARIO": 12, "RUMO": 48, "OP_SUL": 38}, 2: {"RODOVIARIO": 15, "RUMO": 51, "OP_SUL": 30},
            3: {"RODOVIARIO": 15, "RUMO": 47, "OP_SUL": 37}, 4: {"RODOVIARIO": 12, "RUMO": 55, "OP_SUL": 32},
            5: {"RODOVIARIO": 15, "RUMO": 59, "OP_SUL": 26}, 6: {"RODOVIARIO": 13, "RUMO": 52, "OP_SUL": 35},
            7: {"RODOVIARIO": 10, "RUMO": 49, "OP_SUL": 41}, 8: {"RODOVIARIO": 11, "RUMO": 65, "OP_SUL": 29},
            9: {"RUMO": 60, "OP_SUL": 28}, 10: {"RUMO": 41, "OP_SUL": 57},
            11: {"RUMO": 49, "OP_SUL": 51}, 12: {"RUMO": 31, "OP_SUL": 63},
        },
        2026: {
            1: {"OP_SUL": 35, "RUMO": 42}, 2: {"OP_SUL": 26, "RUMO": 56}, 3: {"OP_SUL": 29, "RUMO": 56},
            4: {"OP_SUL": 33, "RUMO": 57}, 5: {"OP_SUL": 7, "OP_NORTE": 9, "RUMO": 49},
            6: {"OP_NORTE": 9, "RUMO": 51}, 7: {"OP_SUL": 22, "RUMO": 67},
        },
    },
    "MT Sudeste": {
        # Legendário: HBSA/HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI NORTE/VLI SUL.
        2024: {
            1: {"RODOVIARIO": 16, "RUMO": 71, "OP_SUL": 13}, 2: {"RODOVIARIO": 22, "RUMO": 71},
            3: {"RUMO": 93}, 4: {"RUMO": 95}, 5: {"RUMO": 95}, 6: {"RUMO": 97}, 7: {"RUMO": 99},
            8: {"RUMO": 99}, 9: {"RUMO": 95}, 10: {"RUMO": 98}, 11: {"RUMO": 99}, 12: {"RUMO": 96},
        },
        2025: {
            1: {"RODOVIARIO": 35, "RUMO": 52, "OP_SUL": 12}, 2: {"RODOVIARIO": 32, "RUMO": 65},
            3: {"RODOVIARIO": 31, "RUMO": 68}, 4: {"RODOVIARIO": 17, "RUMO": 81},
            5: {"RODOVIARIO": 20, "RUMO": 77}, 6: {"RODOVIARIO": 17, "RUMO": 79},
            7: {"RODOVIARIO": 16, "RUMO": 83}, 8: {"RODOVIARIO": 13, "RUMO": 86},
            9: {"RODOVIARIO": 15, "RUMO": 96}, 10: {"RUMO": 94}, 11: {"RUMO": 83, "OP_SUL": 15},
            12: {"RUMO": 96},
        },
        2026: {
            1: {"RODOVIARIO": 43, "RUMO": 49, "OP_SUL": 7}, 2: {"RODOVIARIO": 37, "RUMO": 59},
            3: {"RODOVIARIO": 21, "RUMO": 77}, 4: {"RODOVIARIO": 12, "RUMO": 86},
            5: {"RODOVIARIO": 8, "RUMO": 89}, 6: {"RODOVIARIO": 10, "RUMO": 87},
            7: {"RODOVIARIO": 10, "RUMO": 89},
        },
    },
    "BA Oeste Sul": {
        # Legendário: RODOVIARIO/VLI NORTE/VLI SUL.
        2024: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100},
            5: {"RODOVIARIO": 90}, 6: {"RODOVIARIO": 82, "OP_SUL": 16}, 7: {"RODOVIARIO": 79, "OP_SUL": 8, "OP_NORTE": 14},
            8: {"RODOVIARIO": 89, "OP_NORTE": 9}, 9: {"RODOVIARIO": 77, "OP_SUL": 14, "OP_NORTE": 9},
            10: {"RODOVIARIO": 92}, 11: {"RODOVIARIO": 73, "OP_NORTE": 27}, 12: {"RODOVIARIO": 89, "OP_NORTE": 11},
        },
        2025: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 98},
            5: {"RODOVIARIO": 92, "OP_SUL": 8}, 6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100},
            8: {"RODOVIARIO": 99}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 79, "OP_NORTE": 21},
            11: {"RODOVIARIO": 25, "OP_NORTE": 75}, 12: {"OP_SUL": 73, "OP_NORTE": 27},
        },
    },
    "MS Norte": {
        # Legendário: RODOVIARIO/RUMO/VLI SUL.
        2024: {
            1: {"RODOVIARIO": 91, "RUMO": 9}, 2: {"RODOVIARIO": 68, "RUMO": 32},
            3: {"RODOVIARIO": 54, "RUMO": 46}, 4: {"RODOVIARIO": 37, "RUMO": 63},
            5: {"RODOVIARIO": 48, "RUMO": 52}, 6: {"RODOVIARIO": 58, "RUMO": 42},
            7: {"RODOVIARIO": 49, "RUMO": 51}, 8: {"RODOVIARIO": 51, "RUMO": 49},
            9: {"RODOVIARIO": 63, "RUMO": 28, "OP_SUL": 9}, 10: {"RODOVIARIO": 54, "OP_SUL": 42},
            11: {"RODOVIARIO": 12, "RUMO": 88}, 12: {"RODOVIARIO": 59, "RUMO": 41},
        },
        2025: {
            1: {"RODOVIARIO": 90, "RUMO": 10}, 2: {"RODOVIARIO": 67, "RUMO": 33},
            3: {"RODOVIARIO": 51, "RUMO": 49}, 4: {"RODOVIARIO": 52, "RUMO": 47},
            5: {"RODOVIARIO": 56, "RUMO": 44}, 6: {"RODOVIARIO": 67, "RUMO": 28},
            7: {"RODOVIARIO": 61, "RUMO": 28, "OP_SUL": 11}, 8: {"RODOVIARIO": 86, "RUMO": 14},
            9: {"RODOVIARIO": 68, "RUMO": 32}, 10: {"RODOVIARIO": 49, "RUMO": 49},
            11: {"RODOVIARIO": 94}, 12: {"RODOVIARIO": 88, "OP_SUL": 12},
        },
        2026: {
            1: {"RODOVIARIO": 84, "RUMO": 16}, 2: {"RODOVIARIO": 69, "RUMO": 31},
            3: {"RODOVIARIO": 46, "RUMO": 54}, 4: {"RODOVIARIO": 32, "RUMO": 68},
            5: {"RODOVIARIO": 44, "RUMO": 56}, 6: {"RODOVIARIO": 42, "RUMO": 58},
            7: {"RODOVIARIO": 39, "RUMO": 61},
        },
    },
    "MS Sul": {
        # Legendário: RODOVIARIO/RUMO (2 players).
        2024: {
            1: {"RODOVIARIO": 51, "RUMO": 49}, 2: {"RODOVIARIO": 59, "RUMO": 41},
            3: {"RODOVIARIO": 39, "RUMO": 61}, 4: {"RODOVIARIO": 22, "RUMO": 78},
            5: {"RODOVIARIO": 30, "RUMO": 70}, 6: {"RODOVIARIO": 37, "RUMO": 63},
            7: {"RODOVIARIO": 17, "RUMO": 83}, 8: {"RODOVIARIO": 9, "RUMO": 91},
            9: {"RODOVIARIO": 12, "RUMO": 88}, 10: {"RUMO": 99}, 11: {"RODOVIARIO": 26, "RUMO": 74},
            12: {"RODOVIARIO": 22, "RUMO": 78},
        },
        2025: {
            1: {"RODOVIARIO": 76, "RUMO": 24}, 2: {"RODOVIARIO": 72, "RUMO": 28},
            3: {"RODOVIARIO": 42, "RUMO": 58}, 4: {"RODOVIARIO": 44, "RUMO": 56},
            5: {"RODOVIARIO": 48, "RUMO": 52}, 6: {"RODOVIARIO": 41, "RUMO": 59},
            7: {"RODOVIARIO": 45, "RUMO": 55}, 8: {"RODOVIARIO": 24, "RUMO": 76},
            9: {"RODOVIARIO": 20, "RUMO": 80}, 10: {"RODOVIARIO": 33, "RUMO": 67},
            11: {"RODOVIARIO": 22, "RUMO": 78}, 12: {"RODOVIARIO": 73, "RUMO": 27},
        },
        2026: {
            1: {"RODOVIARIO": 81, "RUMO": 19}, 2: {"RODOVIARIO": 56, "RUMO": 44},
            3: {"RODOVIARIO": 44, "RUMO": 56}, 4: {"RODOVIARIO": 26, "RUMO": 74},
            5: {"RODOVIARIO": 30, "RUMO": 70}, 6: {"RODOVIARIO": 31, "RUMO": 69},
            7: {"RODOVIARIO": 37, "RUMO": 63},
        },
    },
    "MT Norte": {
        # Legendário: HBSA/HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI NORTE/VLI SUL.
        2024: {
            1: {"HBSA": 78, "RUMO": 18}, 2: {"HBSA": 74, "RUMO": 20}, 3: {"HBSA": 78, "RUMO": 19},
            4: {"HBSA": 78, "RUMO": 21}, 5: {"HBSA": 69, "RUMO": 27}, 6: {"HBSA": 54, "RUMO": 43},
            7: {"HBSA": 48, "RUMO": 48}, 8: {"HBSA": 25, "RUMO": 74}, 9: {"HBSA": 11, "RODOVIARIO": 12, "RUMO": 77},
            10: {"RUMO": 99}, 11: {"RUMO": 96}, 12: {"RUMO": 98},
        },
        2025: {
            1: {"HBSA": 84, "RUMO": 14}, 2: {"HBSA": 86, "RUMO": 13}, 3: {"HBSA": 76, "RUMO": 21},
            4: {"HBSA": 69, "RUMO": 30}, 5: {"HBSA": 67, "RUMO": 30}, 6: {"HBSA": 67, "RUMO": 30},
            7: {"HBSA": 47, "RUMO": 46}, 8: {"HBSA": 42, "RUMO": 57}, 9: {"HBSA": 43, "RUMO": 57},
            10: {"HBSA": 26, "RUMO": 74}, 11: {"HBSA": 34, "RUMO": 66}, 12: {"HBSA": 58, "RUMO": 42},
        },
        2026: {
            1: {"HBSA": 67, "RUMO": 28}, 2: {"HBSA": 77, "RUMO": 21}, 3: {"HBSA": 86, "RUMO": 14},
            4: {"HBSA": 83, "RUMO": 16}, 5: {"HBSA": 80, "RUMO": 19}, 6: {"HBSA": 66, "RUMO": 29},
            7: {"HBSA": 64, "RUMO": 36},
        },
    },
    "MT Oeste": {
        # Legendário: HBSA/HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI NORTE/VLI SUL.
        2024: {
            1: {"RUMO": 40, "HIDRO PORTO VELHO": 52}, 2: {"RUMO": 55, "HIDRO PORTO VELHO": 36},
            3: {"RUMO": 63, "HIDRO PORTO VELHO": 30}, 4: {"RUMO": 69, "HIDRO PORTO VELHO": 27},
            5: {"RUMO": 71, "HIDRO PORTO VELHO": 25}, 6: {"RUMO": 67, "HIDRO PORTO VELHO": 31},
            7: {"RUMO": 80, "HIDRO PORTO VELHO": 19}, 8: {"RUMO": 72, "HIDRO PORTO VELHO": 27},
            9: {"RUMO": 91, "RODOVIARIO": 8}, 10: {"RUMO": 98}, 11: {"RUMO": 97},
            12: {"RUMO": 55, "HIDRO PORTO VELHO": 44},
        },
        2025: {
            1: {"RUMO": 55, "HIDRO PORTO VELHO": 36}, 2: {"RUMO": 36, "HIDRO PORTO VELHO": 56},
            3: {"RUMO": 43, "HIDRO PORTO VELHO": 49}, 4: {"RUMO": 47, "HIDRO PORTO VELHO": 45},
            5: {"RUMO": 34, "HIDRO PORTO VELHO": 61}, 6: {"RUMO": 48, "HIDRO PORTO VELHO": 46},
            7: {"RUMO": 77, "HIDRO PORTO VELHO": 21}, 8: {"RUMO": 60, "HIDRO PORTO VELHO": 40},
            9: {"RUMO": 81, "HIDRO PORTO VELHO": 18}, 10: {"RUMO": 74, "HIDRO PORTO VELHO": 26},
            11: {"RUMO": 79, "HIDRO PORTO VELHO": 21}, 12: {"RUMO": 70, "HIDRO PORTO VELHO": 30},
        },
        2026: {
            1: {"RUMO": 45, "RODOVIARIO": 9, "HIDRO PORTO VELHO": 43}, 2: {"RUMO": 50, "HIDRO PORTO VELHO": 44},
            3: {"RUMO": 49, "HIDRO PORTO VELHO": 43, "HBSA": 7}, 4: {"RUMO": 46, "HIDRO PORTO VELHO": 49},
            5: {"RUMO": 54, "HIDRO PORTO VELHO": 41}, 6: {"RUMO": 61, "HIDRO PORTO VELHO": 33},
            7: {"RUMO": 49, "HIDRO PORTO VELHO": 44},
        },
    },
    "PA Nordeste": {
        # Legendário: HBSA/RODOVIARIO/VLI NORTE/VLI SUL. Segmento azul de baixa confiança
        # (HBSA vs VLI NORTE) atribuído por heurística de magnitude — ver nota no memory file.
        2024: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 85, "HBSA": 11}, 3: {"RODOVIARIO": 98},
            4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 99}, 7: {"RODOVIARIO": 97},
            8: {"RODOVIARIO": 97}, 9: {"RODOVIARIO": 91, "HBSA": 9}, 10: {"RODOVIARIO": 100},
            11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2025: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 99}, 3: {"RODOVIARIO": 94}, 4: {"RODOVIARIO": 94},
            5: {"RODOVIARIO": 95}, 6: {"RODOVIARIO": 91, "OP_NORTE": 9}, 7: {"RODOVIARIO": 86, "OP_NORTE": 14},
            8: {"RODOVIARIO": 75, "OP_NORTE": 25}, 9: {"RODOVIARIO": 99}, 10: {"RODOVIARIO": 100},
            11: {"RODOVIARIO": 27, "OP_NORTE": 73}, 12: {"RODOVIARIO": 100},
        },
        2026: {
            1: {"RODOVIARIO": 81, "OP_NORTE": 19}, 2: {"RODOVIARIO": 81, "OP_NORTE": 18},
            3: {"RODOVIARIO": 90}, 4: {"RODOVIARIO": 98}, 5: {"RODOVIARIO": 99}, 6: {"RODOVIARIO": 99},
            7: {"RODOVIARIO": 99},
        },
    },
    "PA Outros": {
        2024: {5: {"RODOVIARIO": 100}},
    },
    "PR": {
        # Legendário: HIDRO PORTO VELHO/RODOVIARIO/RUMO/VLI SUL.
        2024: {
            1: {"RODOVIARIO": 93}, 2: {"RODOVIARIO": 72, "RUMO": 28}, 3: {"RODOVIARIO": 84, "RUMO": 16},
            4: {"RODOVIARIO": 84, "RUMO": 16}, 5: {"RODOVIARIO": 86, "RUMO": 14}, 6: {"RODOVIARIO": 93},
            7: {"RODOVIARIO": 91, "RUMO": 9}, 8: {"RODOVIARIO": 94}, 9: {"RODOVIARIO": 93},
            10: {"RODOVIARIO": 76, "RUMO": 24}, 11: {"RODOVIARIO": 75, "RUMO": 25}, 12: {"RODOVIARIO": 89, "RUMO": 11},
        },
        2025: {
            1: {"RODOVIARIO": 99}, 2: {"RODOVIARIO": 89, "RUMO": 11}, 3: {"RODOVIARIO": 83, "RUMO": 17},
            4: {"RODOVIARIO": 87, "RUMO": 13}, 5: {"RODOVIARIO": 81, "RUMO": 19}, 6: {"RODOVIARIO": 80, "RUMO": 20},
            7: {"RODOVIARIO": 88, "RUMO": 12}, 8: {"RODOVIARIO": 92}, 9: {"RODOVIARIO": 93},
            10: {"RODOVIARIO": 92, "RUMO": 8}, 11: {"RODOVIARIO": 94}, 12: {"RODOVIARIO": 93},
        },
        2026: {
            1: {"RODOVIARIO": 97}, 2: {"RODOVIARIO": 87, "RUMO": 13}, 3: {"RODOVIARIO": 80, "RUMO": 20},
            4: {"RODOVIARIO": 82, "RUMO": 18}, 5: {"RODOVIARIO": 82, "RUMO": 18}, 6: {"RODOVIARIO": 83, "RUMO": 17},
            7: {"RODOVIARIO": 83, "RUMO": 17},
        },
    },
    "GO Norte": {
        # Legendário: RODOVIARIO/RUMO/VLI NORTE/VLI SUL.
        2024: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 79, "OP_SUL": 16},
            3: {"RODOVIARIO": 53, "RUMO": 17, "OP_SUL": 30}, 4: {"RODOVIARIO": 39, "RUMO": 31, "OP_SUL": 28},
            5: {"RODOVIARIO": 49, "RUMO": 27, "OP_SUL": 24}, 6: {"RODOVIARIO": 68, "OP_SUL": 22},
            7: {"RODOVIARIO": 34, "RUMO": 15, "OP_NORTE": 8, "OP_SUL": 43},
            8: {"RODOVIARIO": 14, "RUMO": 40, "OP_NORTE": 20, "OP_SUL": 26},
            9: {"RODOVIARIO": 13, "RUMO": 85}, 10: {"RUMO": 99}, 11: {"RUMO": 100}, 12: {"RUMO": 100},
        },
        2025: {
            1: {"RUMO": 100}, 2: {"RODOVIARIO": 49, "RUMO": 13, "OP_SUL": 37},
            3: {"RODOVIARIO": 54, "RUMO": 19, "OP_SUL": 23},
            4: {"RODOVIARIO": 49, "RUMO": 11, "OP_NORTE": 11, "OP_SUL": 29},
            5: {"RODOVIARIO": 37, "OP_NORTE": 19, "OP_SUL": 38}, 6: {"RODOVIARIO": 40, "OP_SUL": 39},
            7: {"RODOVIARIO": 56, "OP_NORTE": 11, "OP_SUL": 30}, 8: {"RODOVIARIO": 37, "RUMO": 11, "OP_SUL": 52},
            9: {"RODOVIARIO": 17, "RUMO": 35, "OP_SUL": 48}, 10: {"RODOVIARIO": 50, "RUMO": 33, "OP_SUL": 17},
            11: {"OP_SUL": 95}, 12: {"RUMO": 80, "OP_SUL": 19},
        },
        2026: {
            1: {"RUMO": 100}, 2: {"RODOVIARIO": 22, "RUMO": 35, "OP_NORTE": 10, "OP_SUL": 34},
            3: {"RODOVIARIO": 28, "RUMO": 33, "OP_SUL": 37},
            4: {"RODOVIARIO": 34, "RUMO": 33, "OP_NORTE": 9, "OP_SUL": 24},
            5: {"RODOVIARIO": 29, "RUMO": 42, "OP_NORTE": 21},
            6: {"RODOVIARIO": 31, "RUMO": 45, "OP_NORTE": 18, "OP_SUL": 7},
            7: {"RODOVIARIO": 21, "RUMO": 43, "OP_NORTE": 14, "OP_SUL": 21},
        },
    },
    "MG Outros": {
        # Legendário: ADM/RODOVIARIO/RUMO/VLI SUL.
        2024: {
            1: {"RODOVIARIO": 97}, 2: {"RODOVIARIO": 96}, 3: {"RODOVIARIO": 97}, 4: {"RODOVIARIO": 95},
            5: {"RODOVIARIO": 93}, 6: {"RODOVIARIO": 94}, 7: {"RODOVIARIO": 94}, 8: {"RODOVIARIO": 99},
            9: {"RODOVIARIO": 97}, 10: {"RODOVIARIO": 13, "RUMO": 21, "OP_SUL": 66},
            11: {"OP_SUL": 96}, 12: {"OP_SUL": 98},
        },
        2025: {
            1: {"RODOVIARIO": 97}, 2: {"RODOVIARIO": 96}, 3: {"RODOVIARIO": 97}, 4: {"RODOVIARIO": 97},
            5: {"RODOVIARIO": 96}, 6: {"RODOVIARIO": 94}, 7: {"RODOVIARIO": 92}, 8: {"RODOVIARIO": 96},
            9: {"RODOVIARIO": 63, "OP_SUL": 37}, 10: {"RODOVIARIO": 83, "OP_SUL": 16},
            11: {"RODOVIARIO": 76, "OP_SUL": 22}, 12: {"RODOVIARIO": 73, "OP_SUL": 27},
        },
        2026: {
            1: {"RODOVIARIO": 52, "OP_SUL": 46}, 2: {"RODOVIARIO": 90, "OP_SUL": 9}, 3: {"RODOVIARIO": 94},
            4: {"RODOVIARIO": 93}, 5: {"RODOVIARIO": 89, "OP_SUL": 9}, 6: {"RODOVIARIO": 89},
            7: {"RODOVIARIO": 83, "OP_SUL": 14},
        },
    },
    "MG Noroeste": {
        # Legendário: ADM/RODOVIARIO/RUMO/VLI SUL (4 players). Alguns meses de 2026 (mai-jul)
        # mostram um segmento azul fino sem correspondente na legenda visível — omitido.
        2024: {
            1: {"RODOVIARIO": 41, "OP_SUL": 59}, 2: {"RODOVIARIO": 36, "OP_SUL": 62},
            3: {"RODOVIARIO": 36, "OP_SUL": 64}, 4: {"RODOVIARIO": 48, "OP_SUL": 52},
            5: {"RODOVIARIO": 41, "OP_SUL": 58}, 6: {"RODOVIARIO": 50, "OP_SUL": 49},
            7: {"RODOVIARIO": 46, "OP_SUL": 53}, 8: {"RODOVIARIO": 33, "OP_SUL": 66},
            9: {"RODOVIARIO": 40, "OP_SUL": 60}, 10: {"OP_SUL": 97}, 11: {"OP_SUL": 99}, 12: {"OP_SUL": 99},
        },
        2025: {
            1: {"RODOVIARIO": 73, "OP_SUL": 27}, 2: {"RODOVIARIO": 55, "OP_SUL": 45},
            3: {"RODOVIARIO": 46, "OP_SUL": 54}, 4: {"RODOVIARIO": 51, "OP_SUL": 49},
            5: {"RODOVIARIO": 45, "OP_SUL": 55}, 6: {"RODOVIARIO": 37, "OP_SUL": 63},
            7: {"RODOVIARIO": 32, "OP_SUL": 68}, 8: {"RODOVIARIO": 23, "OP_SUL": 77},
            9: {"OP_SUL": 95}, 10: {"RODOVIARIO": 19, "OP_SUL": 81}, 11: {"OP_SUL": 99},
            12: {"RODOVIARIO": 9, "OP_SUL": 91},
        },
        2026: {
            1: {"RODOVIARIO": 62, "OP_SUL": 38}, 2: {"RODOVIARIO": 45, "OP_SUL": 51},
            3: {"RODOVIARIO": 23, "OP_SUL": 73}, 4: {"RODOVIARIO": 16, "OP_SUL": 83},
            5: {"RODOVIARIO": 26, "OP_SUL": 64}, 6: {"RODOVIARIO": 29, "OP_SUL": 60},
            7: {"RODOVIARIO": 39, "OP_SUL": 53},
        },
    },
}

PRODUTO = "Soja"


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
    cur.execute("DROP TABLE IF EXISTS market_share_volume")
    cur.execute("""CREATE TABLE market_share_volume(
        escopo TEXT, produto TEXT, ano INTEGER, mes TEXT, volume_t REAL, fonte TEXT)""")
    cur.executemany("INSERT INTO market_share_volume VALUES (?,?,?,?,?,?)", vol_rows)

    cur.execute("DROP TABLE IF EXISTS market_share_player")
    cur.execute("""CREATE TABLE market_share_player(
        escopo TEXT, produto TEXT, ano INTEGER, mes TEXT, player TEXT, pct REAL, fonte TEXT)""")
    cur.executemany("INSERT INTO market_share_player VALUES (?,?,?,?,?,?,?)", ms_rows)
    con.commit()

    print(f"market_share_volume: {len(vol_rows)} linhas")
    print(f"market_share_player: {len(ms_rows)} linhas")
    for escopo in VOLUME:
        n = sum(1 for r in vol_rows if r[0] == escopo)
        print(f"  {escopo}: {n} meses com volume lido")
    con.close()


if __name__ == "__main__":
    main()
