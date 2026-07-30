# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade) no banco, Produto=FARELO DE SOJA
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeos do usuário (celular filmando dashboard Power BI de terceiro, "Competitividade"),
mesmo relatório-fonte de add_market_share.py (Soja) e add_market_share_milho.py (Milho), só troca
o filtro Produto para FARELO DE SOJA. Dois vídeos-fonte para este produto:
  - 09_Fotos/IMG_0226.MOV (100.758s) — sequência de ~20 microrregiões (BA Oeste Sul, BA Outros,
    CE, GO Leste, MA Outros, MG Outros, MS Norte, MS Sul, MT Norte, MT Oeste, PA Nordeste,
    PA Outros, PE, PR, RJ, RO, RS, SC, SE, SP).
  - 09_Fotos/IMG_0224.MOV (255.085s) — segundo vídeo do mesmo produto, sequência própria de
    microrregiões (NÃO é a mesma ordem/lista do IMG_0226, embora reutilize nomes de corredor
    "NORTE (vmr_corredor)" com escopos DIFERENTES — ver aviso de colisão abaixo).

Achado importante (CORRIGIDO — não generalizar): as regiões da Bahia (BA Oeste Sul, BA Outros)
e MA Outros só têm RODOVIARIO no legendário, mas isso NÃO é universal do produto — MG Outros
já mostra concorrência real entre RUMO e OP_SUL (VLI Sul). Cada região precisa ter seu
legendário conferido individualmente, igual às outras abas de Market Share.

Cobertura: IMG_0226.MOV transcrito por completo — BA Oeste Sul, BA Outros, MA Outros, MG
Outros, MS Norte, MS Sul, MT Norte, MT Oeste, PA Nordeste, PA Outros, PE, PR, RJ, RO, RS,
SC, SE, SP (18 regiões com dado real). CE e GO Leste checados: sem dado algum (volume zero,
charts vazios). RJ tem só 1 mês (abril/2026=27) e o player do Share não foi identificável
com confiança (sem legenda visível no frame) — omitido do MS por "não inventar precisão".

IMG_0224.MOV — cobertura da parte de Microrregião (t=0 a ~155s; o restante do vídeo, t~155-255s,
sai do escopo de microrregião e passa a fatiar o Nacional por Porto/Player, dimensão que este
schema não representa — não transcrito por não caber na estrutura VOLUME/MS por escopo):
  - "Nacional" (agregado nacional real, visto em t~0-8s com Microrregião="Todos").
  - Corredor "NORTE (vmr_corredor)" (mesmo corredor do IMG_0226, escopos DIFERENTES —
    "BA Oeste Norte"/"MA Sul" aqui ≠ "BA Oeste Sul"/"MA Outros" do IMG_0226): BA Oeste Norte,
    MA Sul, MT Nordeste, PI Sul, TO Centro (Share omitido — player não identificável), TO Leste,
    TO Norte, TO Sul.
  - Corredor "SUL (vmr_corredor)" (Goiás/Minas/Mato Grosso, não presente no IMG_0226): GO Leste,
    GO Norte (abril/2025 cortado pela borda do dropdown em todos os frames — omitido), GO
    Noroeste (checado, sem dado — volume zero, chart vazio), GO Sudoeste, MG Noroeste, MG
    Triangulo, MT Medio Norte (alguns meses sem rótulo numérico por espaço denso — omitidos),
    MT Nordeste Sul, MT Sudeste (ago-dez/2025 cobertos pelo dropdown em todos os frames —
    omitidos).

IMPORTANTE: este script só faz INSERT (não DROP) nas tabelas market_share_volume/
market_share_player — deve rodar DEPOIS de add_market_share.py (que cria as tabelas com os
dados de Soja). Rodar sozinho sem add_market_share.py antes vai falhar (tabela não existe).

Uso:  python3 add_market_share.py && python3 add_market_share_farelo_soja.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "Produto=FARELO DE SOJA) — transcrição manual dos rótulos numéricos das barras. "
         "Dois vídeos-fonte, ambos transcritos por completo (na parte de Microrregião): "
         "IMG_0226.MOV (18 regiões: BA Oeste Sul, BA Outros, MA Outros, MG Outros, MS Norte, "
         "MS Sul, MT Norte, MT Oeste, PA Nordeste, PA Outros, PE, PR, RJ, RO, RS, SC, SE, SP; "
         "CE e GO Leste sem dado) e IMG_0224.MOV (Nacional + corredores NORTE e SUL: BA Oeste "
         "Norte, MA Sul, MT Nordeste, PI Sul, TO Centro, TO Leste, TO Norte, TO Sul, GO Leste, "
         "GO Norte, GO Sudoeste, MG Noroeste, MG Triangulo, MT Medio Norte, MT Nordeste Sul, "
         "MT Sudeste; GO Noroeste sem dado; parte final do IMG_0224 (t~155-255s) fatia o "
         "Nacional por Porto/Player, fora do escopo deste schema).")

# ---------------------------------------------------------------- VOLUME MOVIMENTADO (t)
# escopo -> {ano: {mes(1-12): valor|None}}
# Meses ausentes da lista (não None, simplesmente fora do range) = categoria não exibida
# pelo PowerBI-fonte (volume zero/nulo naquele mês).
VOLUME = {
    # Nacional = agregado "Todos" (Microrregião=Todos), visto no início de IMG_0224.MOV
    # (t~0-8s), confirmado por tooltip de drill-through nativo do PowerBI (Date Mês/Volume
    # Total/Aux Ordenador) — não é estimativa, é o total oficial da fonte.
    "Nacional": {
        2024: [950251, None, 1121832, 1140813, None, None, 1197316, 939468, None, 1137801, 925530, None],
        2025: [899528, None, 1378307, 1303341, None, None, 1160751, None, 1117378, None, 1157673, None],
        2026: [984422, 959153, 1354492, 1549397, 1638252, 1510733, 474441, None, None, None, None, None],
    },
    # ---- IMG_0224.MOV (segundo vídeo do produto) — corredor NORTE, mesma lista de
    # microrregiões do vídeo original de Soja (IMG_0221/add_market_share.py), produto agora
    # Farelo de Soja. Nomes diferem de "BA Oeste Sul" etc (que são do vídeo IMG_0226) — são
    # escopos genuinamente distintos ("BA Oeste Norte" vs "BA Oeste Sul").
    "BA Oeste Norte": {
        2024: [None, None, 95173, 96873, 81082, 89609, 109969, None, 55925, 87719, 82626, 89917],
        2025: [101281, 71793, 121581, None, 124216, None, 104857, 66290, None, None, None, None],
        2026: [123389, 85916, 98171, 110909, 111705, 108140, 40970, None, None, None, None, None],
    },
    "MA Sul": {
        2024: [None, None, None, None, None, None, 5, 5, None, 42, 29, None],
        2025: [None, None, None, 47, None, 18, 28, None, None, 15, 10, None],
        2026: [None, 390, 661, 380, 407, 369, 195, None, None, None, None, None],
    },
    # MT Nordeste: fevereiro/2024 tem barra genuína mas o valor numérico ("50...") fica
    # sempre cortado pela moldura da câmera (bem na borda esquerda) em todos os frames
    # checados — gap permanente. Demais meses reconferidos num frame mais estável (t~57s).
    "MT Nordeste": {
        2024: [None, None, None, None, 422, 884, None, 39, None, 10, None, 88],
        2025: [37, None, None, 74, 39, None, None, None, None, None, None, None],
        2026: [99, 98, 150, None, None, None, None, None, None, None, None, None],
    },
    # PI Sul: leitura inicial (t~35-37s) capturou só um subconjunto instável de meses
    # (render-lag ainda assentando); reconferido num frame posterior (t~53s, checkbox único
    # "PI SUL" confirmado) que mostrou o dataset completo — usar esta versão.
    "PI Sul": {
        2024: [49, 3046, 9808, 17020, 23981, 25851, 21799, 14694, 559, 21629, 6089, None],
        # maio/2025 tem rótulo genuíno ("13.7...") mas sempre coberto pela borda do dropdown
        # em todos os frames checados — só os 2 primeiros dígitos após o ponto são legíveis.
        2025: [None, None, None, 18251, None, None, None, None, None, None, None, None],
        2026: [None, None, 4473, 18000, 6272, 7516, 4607, None, None, None, None, None],
    },
    # TO Centro: player do Share não identificável (sem "Legenda:" renderizada, só 1 barra
    # sem nome) — mesmo tratamento de RJ no IMG_0226, omitido do MS.
    "TO Centro": {
        2026: [None, 51, 84, None, None, None, None, None, None, None, None, None],
    },
    "TO Leste": {
        2025: [None, None, None, 37, None, None, None, None, None, None, None, None],
    },
    "TO Norte": {
        2024: [None, None, None, None, None, 84, None, None, None, None, None, None],
    },
    "TO Sul": {
        2024: [12910, 2196, 28072, 28842, 37227, 54292, 43675, 51001, 35568, 58883, 44110, 9351],
        2025: [32189, 38185, 77533, 62978, 43983, 45602, 49038, 34168, 44267, 35976, 23998, 1418],
        2026: [41, 16867, 41557, 40528, 31726, 38471, 11933, None, None, None, None, None],
    },
    # A partir daqui, IMG_0224 revela um segundo corredor "SUL (vmr_corredor)"
    # (Goiás/Minas/Mato Grosso), distinto do corredor "NORTE" acima.
    "GO Leste": {
        2024: [30587, 37808, 48458, 39700, 15430, 12314, 28128, 18940, 15027, 12540, 13969, 6506],
        2025: [14962, 8233, 19599, 13819, 10337, 1617, 11436, 10665, 8584, 13571, 11965, 17267],
        2026: [15832, 15403, 27813, 19696, 24990, 7160, 814, None, None, None, None, None],
    },
    # GO Norte: abril/2025 permanece cortado pela borda do dropdown em todos os frames
    # conferidos ("14..." parcial) — omitido por precaução.
    "GO Norte": {
        2025: [None, None, 141, None, None, None, None, None, None, None, None, None],
        2026: [None, None, None, 8376, 349, 25, None, None, None, None, None, None],
    },
    "GO Sudoeste": {
        2024: [77426, 64263, 81857, 93396, 82904, 99664, 78910, 22938, 46022, 68651, 56011, 77773],
        2025: [75088, 62521, 80226, 64418, 78107, 70582, 51988, 19057, 58104, 72826, 102420, 71085],
        2026: [76249, 43602, 55883, 65304, 90041, 74375, 18848, None, None, None, None, None],
    },
    "MG Noroeste": {
        2024: [None, 38, None, None, None, None, None, None, None, None, None, 50],
        2025: [None, 47, None, None, None, None, 180, None, None, None, None, None],
        2026: [None, None, 201, None, None, 69, None, None, None, None, None, None],
    },
    "MG Triangulo": {
        2024: [13575, 21873, 17237, 2018, 262, 13281, 1111, 1043, 888, 1602, 5197, 5458],
        2025: [9161, 1820, 1388, 1493, 3851, 3983, 636, 6553, 12561, 3956, 31339, 20308],
        2026: [1560, 3778, 3473, 4332, 2617, 1064, 369, None, None, None, None, None],
    },
    # MT Medio Norte: o PowerBI omite o rotulo numerico de alguns meses por falta de
    # espaco (12 barras densas) — meses sem numero legivel ficaram None.
    "MT Medio Norte": {
        2024: [137782, None, 141391, None, 133285, 112593, None, 95972, 122860, None, 102601, 124714],
        2025: [123654, None, 140943, 137686, None, 174201, 161600, 125942, None, 68920, 114472, 177844],
        2026: [174064, 164589, 184622, 186315, 194600, 188445, 61464, None, None, None, None, None],
    },
    "MT Nordeste Sul": {
        2024: [None, 79, None, 198, 36, None, None, None, None, None, None, 192],
        2025: [255, 40, 48, None, 37, None, 99, None, 100, None, 40, None],
        2026: [None, 180, None, 48, None, 128, None, None, None, None, None, None],
    },
    # MT Sudeste: alguns meses de 2024 sem rotulo numerico (espaco denso) e
    # ago-dez/2025 permanecem cobertos pelo dropdown em todos os frames checados.
    "MT Sudeste": {
        2024: [150105, None, 248405, None, 243891, 195245, None, 173806, None, 187107, None, 152141],
        2025: [166505, 226120, 325278, 281529, 256266, 211440, None, None, None, None, None, None],
        2026: [296080, 290986, 296141, 321874, 431137, 384663, 115775, None, None, None, None, None],
    },
    "BA Oeste Sul": {
        2026: [None, None, None, 78, None, None, None, None, None, None, None, None],
    },
    "BA Outros": {
        2024: [None, 997, 996, 570, 1103, 3124, 2451, 2102, 4636, 5812, 6439, 7255],
        2025: [4842, 3214, 10095, 4589, 4616, 5327, 9661, 3639, 9715, 7372, 8433, 4464],
        2026: [None, 475, 3094, 4767, 4087, None, 1511, None, None, None, None, None],
    },
    "MA Outros": {
        2024: [None, None, None, None, None, None, None, None, None, 37, None, 306],
    },
    "MG Outros": {
        2024: [None, None, None, None, 32, 72, 2, 13, 51, None, None, None],
        2025: [None, None, 117, None, None, None, None, 39, 73, None, None, None],
        2026: [13, None, 116, None, None, None, None, None, None, None, None, None],
    },
    "MS Norte": {
        2024: [14994, 18792, 16840, 25644, 23972, 21716, 26775, 15348, 14590, 12818, 3054, 6649],
        # set/out/nov/dez 2025: dropdown de Microrregião ficou aberto sobre os rótulos em
        # todos os frames tentados (t=30..38) — gap genuíno, valores nunca ficaram visíveis.
        2025: [14046, 41071, 50607, 43123, 51041, 50615, 29499, 29510, None, None, None, None],
        2026: [39498, 39794, 55040, 57336, 47523, 29871, 38, None, None, None, None, None],
    },
    "MS Sul": {
        2024: [94976, 67821, 90182, 85644, 93412, 65015, 83425, 73155, 71308, 96463, 82863, 68591],
        2025: [102059, 76327, 90330, 63042, 22293, 33538, 59733, 78218, 57229, 47183, 92964, 60243],
        2026: [41368, 55103, 74783, 123006, 126004, 102988, 28589, None, None, None, None, None],
    },
    "MT Norte": {
        2024: [250, 50, 250, 88, 127, 403, 979, 1540, 564, 206, 448, 147],
        2025: [468, 77, 206, 49, 183, 77, 265, None, None, 118, 115, 47],
        2026: [263, 90, 316, 491, 285, 322, None, None, None, None, None, None],
    },
    "MT Oeste": {
        2024: [7871, 8883, 9998, 9381, 10938, 10446, 11722, 6377, 10324, 7572, 6773, 339],
        2025: [223, 49, 14072, 20310, 16996, 9053, 9065, 10871, 12101, 11763, 13027, 11872],
        2026: [9351, 10478, 8097, 9756, 5532, 9850, 3157, None, None, None, None, None],
    },
    "PA Nordeste": {
        2024: [190, 84, 256, 353, 481, 791, 611, 657, 595, 668, 341, 432],
        # set/out/nov/dez 2025: só rótulos colidiram (bar pequena) — sem frame com valor legível.
        2025: [732, 291, 577, 478, 319, 85, None, 294, None, None, None, None],
        2026: [390, 147, None, 132, 211, None, None, None, None, None, None, None],
    },
    "PA Outros": {
        2024: [None, None, None, 50, None, None, None, None, None, 1401, None, None],
        2025: [None, 49, None, 49, 291, 93, 31, None, None, None, None, None],
        2026: [None, None, 97, 50, None, None, None, None, None, None, None, None],
    },
    "PE": {
        2025: [None, None, None, None, None, 17, None, None, 2, 2, None, None],
        2026: [2, None, None, None, None, None, None, None, None, None, None, None],
    },
    "PR": {
        2024: [204246, 114547, 182601, None, 138098, 173168, 215964, 160850, 203461, 236933, 185490, 152606],
        2025: [119062, None, 193073, None, 255208, 197666, None, 201867, 172555, None, 206405, None],
        2026: [128531, 133560, 296423, 289366, 256613, 266641, 96076, None, None, None, None, None],
    },
    # RJ: só um dado no vídeo inteiro (abril/2026). Player do Share não identificável com
    # confiança (cor azul não bate com nenhum legendário claramente visível no frame — sem
    # "Legenda:" renderizada nesse recorte) — por "não inventar precisão", omitido do MS.
    "RJ": {
        2026: [None, None, None, 27, None, None, None, None, None, None, None, None],
    },
    "RO": {
        2024: [39, 40, None, 37, None, None, 39, None, 1, None, None, 40],
        2025: [None, 77, None, None, None, None, None, None, None, None, 63, None],
        2026: [None, None, None, None, None, 47, None, None, None, None, None, None],
    },
    "RS": {
        2024: [55717, 42296, 43449, 76246, 106211, None, 123271, 82164, 71940, 99780, 88399, 54342],
        2025: [58803, 46754, 107995, None, 118705, None, 100064, None, None, None, None, None],
        2026: [41309, 53459, 83008, 136683, 151704, 139506, 48388, None, None, None, None, None],
    },
    "SC": {
        2024: [260, 1310, 2681, 12398, 14002, 4720, 171, None, 5451, 20243, 1397, 1778],
        2025: [8265, 5618, 10521, 11161, 2609, None, 324, 4818, None, 105, None, None],
        2026: [1046, 556, 81, 234, 2382, 3153, 258, None, None, None, None, None],
    },
    "SE": {
        2026: [23, None, 23, None, None, None, None, None, None, None, None, None],
    },
    "SP": {
        2024: [52581, 71061, 104139, None, 133878, 105535, None, 112061, None, 94296, 67328, 60443],
        2025: [67896, 82379, 133979, 163160, 138841, 106155, 127196, None, 133033, None, 75305, 71831],
        2026: [35315, 43631, 120185, 151708, 150067, 147931, 41449, None, None, None, None, None],
    },
}

# ---------------------------------------------------------- MARKET SHARE POR PLAYER (%)
# Único player no legendário deste produto: RODOVIARIO (sem concorrência ferroviária).
MS = {
    "Nacional": {
        2024: {
            1: {"RODOVIARIO": 78, "RUMO": 21}, 2: {"RODOVIARIO": 75, "RUMO": 25},
            3: {"RODOVIARIO": 78, "RUMO": 21}, 4: {"RODOVIARIO": 79, "RUMO": 21},
            5: {"RODOVIARIO": 77, "RUMO": 21}, 6: {"RODOVIARIO": 78, "RUMO": 21},
            7: {"RODOVIARIO": 79, "RUMO": 17}, 8: {"RODOVIARIO": 78, "RUMO": 21},
            9: {"RODOVIARIO": 77, "RUMO": 22}, 10: {"RODOVIARIO": 77, "RUMO": 22},
            11: {"RODOVIARIO": 74, "RUMO": 25}, 12: {"RODOVIARIO": 70, "RUMO": 29},
        },
        2025: {
            1: {"RODOVIARIO": 74, "RUMO": 25}, 2: {"RODOVIARIO": 71, "RUMO": 27},
            3: {"RODOVIARIO": 79, "RUMO": 20}, 4: {"RODOVIARIO": 80, "RUMO": 20},
            5: {"RODOVIARIO": 81, "RUMO": 18}, 6: {"RODOVIARIO": 80, "RUMO": 17},
            7: {"RODOVIARIO": 76, "RUMO": 18}, 8: {"RODOVIARIO": 65, "RUMO": 29},
            9: {"RODOVIARIO": 77, "RUMO": 21}, 10: {"RODOVIARIO": 76, "RUMO": 20},
            11: {"RODOVIARIO": 70, "RUMO": 22}, 12: {"RODOVIARIO": 62, "RUMO": 31},
        },
        2026: {
            1: {"RODOVIARIO": 57, "RUMO": 35}, 2: {"RODOVIARIO": 58, "RUMO": 37},
            3: {"RODOVIARIO": 69, "RUMO": 28}, 4: {"RODOVIARIO": 75, "RUMO": 23},
            5: {"RODOVIARIO": 73, "RUMO": 24}, 6: {"RODOVIARIO": 69, "RUMO": 27},
            7: {"RODOVIARIO": 70, "RUMO": 24},
        },
    },
    "BA Oeste Norte": {
        2024: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
               6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100},
               10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
        2025: {m: {"RODOVIARIO": 100} for m in (1, 2, 3, 5, 7, 8)},
        2026: {m: {"RODOVIARIO": 100} for m in range(1, 8)},
    },
    "MA Sul": {
        2024: {7: {"VLI NORTE": 100}, 8: {"VLI NORTE": 100},
               10: {"RODOVIARIO": 88, "VLI NORTE": 12}, 11: {"VLI NORTE": 100}},
        2025: {4: {"RODOVIARIO": 100}, 6: {"VLI NORTE": 100}, 7: {"VLI NORTE": 100},
               10: {"VLI NORTE": 100}, 11: {"VLI NORTE": 100}},
        2026: {m: {"RODOVIARIO": 100} for m in range(2, 8)},
    },
    "MT Nordeste": {
        2024: {2: {"HBSA": 100}, 5: {"RODOVIARIO": 88, "RUMO": 12}, 6: {"RUMO": 100},
               8: {"RUMO": 100}, 10: {"RUMO": 100}, 12: {"RUMO": 100}},
        2025: {1: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}},
        2026: {1: {"HBSA": 50, "RODOVIARIO": 50}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}},
    },
    "PI Sul": {
        2024: {m: {"RODOVIARIO": 100} for m in range(1, 12)},
        2025: {4: {"RODOVIARIO": 100}},
        2026: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
               6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
    },
    "TO Leste": {
        2025: {4: {"RODOVIARIO": 100}},
    },
    "TO Norte": {
        2024: {6: {"VLI NORTE": 100}},
    },
    "TO Sul": {
        2024: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 85, "RUMO": 15}, 3: {"RODOVIARIO": 99},
               4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 99}, 6: {"RODOVIARIO": 100},
               7: {"RODOVIARIO": 99}, 8: {"RODOVIARIO": 96}, 9: {"RODOVIARIO": 91, "RUMO": 8},
               10: {"RODOVIARIO": 78, "VLI NORTE": 16}, 11: {"RODOVIARIO": 64, "RUMO": 16, "VLI NORTE": 20},
               12: {"RODOVIARIO": 99}},
        2025: {m: {"RODOVIARIO": 100} for m in range(1, 13)},
        2026: {1: {"RUMO": 100}, 2: {"RODOVIARIO": 96}, 3: {"RODOVIARIO": 99},
               4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
    },
    "GO Leste": {
        2024: {1: {"RODOVIARIO": 95}, 2: {"RODOVIARIO": 98}, 3: {"RODOVIARIO": 96}, 4: {"RODOVIARIO": 96},
               5: {"RODOVIARIO": 94}, 6: {"RODOVIARIO": 62, "RUMO": 38}, 7: {"RODOVIARIO": 60, "RUMO": 40},
               8: {"RODOVIARIO": 62, "RUMO": 38}, 9: {"RODOVIARIO": 56, "RUMO": 44}, 10: {"RODOVIARIO": 93},
               11: {"RODOVIARIO": 88, "RUMO": 12}, 12: {"RODOVIARIO": 100}},
        2025: {1: {"RODOVIARIO": 76, "RUMO": 22}, 2: {"RODOVIARIO": 98}, 3: {"RODOVIARIO": 86, "RUMO": 9},
               4: {"RODOVIARIO": 86, "VLI SUL": 14}, 5: {"RODOVIARIO": 80, "VLI SUL": 20}, 6: {"VLI SUL": 97},
               7: {"RODOVIARIO": 93}, 8: {"RODOVIARIO": 83, "VLI SUL": 17}, 9: {"RODOVIARIO": 75, "VLI SUL": 25},
               10: {"RODOVIARIO": 85, "VLI SUL": 15}, 11: {"RODOVIARIO": 82, "VLI SUL": 18},
               12: {"RODOVIARIO": 89, "VLI SUL": 11}},
        2026: {1: {"RODOVIARIO": 90, "VLI SUL": 9}, 2: {"RODOVIARIO": 87, "VLI SUL": 13},
               3: {"RODOVIARIO": 92, "VLI SUL": 8}, 4: {"RODOVIARIO": 88, "VLI SUL": 12},
               5: {"RODOVIARIO": 89, "VLI SUL": 11}, 6: {"RODOVIARIO": 58, "VLI SUL": 41},
               7: {"VLI SUL": 94}},
    },
    "GO Norte": {
        2025: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}},
        2026: {4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RUMO": 100}},
    },
    "GO Sudoeste": {
        2024: {1: {"RODOVIARIO": 98}, 2: {"RODOVIARIO": 95}, 3: {"RODOVIARIO": 98}, 4: {"RODOVIARIO": 98},
               5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 97}, 7: {"RODOVIARIO": 97}, 8: {"RODOVIARIO": 97},
               9: {"RODOVIARIO": 98}, 10: {"RODOVIARIO": 98}, 11: {"RODOVIARIO": 92}, 12: {"RODOVIARIO": 98}},
        2025: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 99}, 3: {"RODOVIARIO": 97}, 4: {"RODOVIARIO": 95},
               5: {"RODOVIARIO": 96}, 6: {"RODOVIARIO": 93}, 7: {"RODOVIARIO": 92}, 8: {"RODOVIARIO": 67, "RUMO": 31},
               9: {"RODOVIARIO": 91}, 10: {"RODOVIARIO": 57, "VLI SUL": 38}, 11: {"RODOVIARIO": 33, "VLI SUL": 65},
               12: {"RODOVIARIO": 19, "VLI SUL": 79}},
        2026: {1: {"RODOVIARIO": 18, "RUMO": 10, "VLI SUL": 72}, 2: {"RODOVIARIO": 56, "VLI SUL": 39},
               3: {"RODOVIARIO": 97}, 4: {"RODOVIARIO": 96}, 5: {"RODOVIARIO": 98}, 6: {"RODOVIARIO": 94},
               7: {"RODOVIARIO": 95}},
    },
    "MG Noroeste": {
        2024: {2: {"VLI SUL": 100}, 12: {"RODOVIARIO": 100}},
        2025: {2: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
        2026: {3: {"VLI SUL": 100}, 6: {"RODOVIARIO": 56, "VLI SUL": 44}},
    },
    "MG Triangulo": {
        2024: {1: {"RODOVIARIO": 98}, 2: {"RODOVIARIO": 99}, 3: {"RODOVIARIO": 98},
               4: {"RODOVIARIO": 80, "VLI SUL": 17}, 5: {"VLI SUL": 100}, 6: {"RODOVIARIO": 93},
               7: {"RODOVIARIO": 58, "VLI SUL": 38}, 8: {"RODOVIARIO": 70, "VLI SUL": 25},
               9: {"RUMO": 56, "VLI SUL": 44}, 10: {"RODOVIARIO": 77, "VLI SUL": 23},
               11: {"RODOVIARIO": 96}, 12: {"RODOVIARIO": 94}},
        2025: {1: {"RODOVIARIO": 90, "VLI SUL": 9}, 2: {"VLI SUL": 95}, 3: {"VLI SUL": 94},
               4: {"RODOVIARIO": 84, "VLI SUL": 16}, 5: {"RODOVIARIO": 93}, 6: {"RODOVIARIO": 93},
               7: {"RODOVIARIO": 18, "VLI NORTE": 10, "VLI SUL": 72}, 8: {"RODOVIARIO": 83, "VLI SUL": 16},
               9: {"RODOVIARIO": 95}, 10: {"RODOVIARIO": 87, "VLI SUL": 12}, 11: {"RODOVIARIO": 98},
               12: {"RODOVIARIO": 98}},
        2026: {1: {"VLI NORTE": 6, "RODOVIARIO": 51, "VLI SUL": 43}, 2: {"RODOVIARIO": 91, "VLI SUL": 9},
               3: {"RODOVIARIO": 81, "VLI SUL": 18}, 4: {"RODOVIARIO": 84, "VLI SUL": 9},
               5: {"RODOVIARIO": 74, "VLI SUL": 23}, 6: {"RODOVIARIO": 13, "VLI SUL": 82},
               7: {"VLI SUL": 96}},
    },
    "MT Medio Norte": {
        2024: {1: {"RUMO": 58, "RODOVIARIO": 39}, 2: {"RUMO": 74, "RODOVIARIO": 24},
               3: {"RUMO": 79, "RODOVIARIO": 12, "HBSA": 8}, 4: {"RUMO": 85, "RODOVIARIO": 10},
               5: {"RUMO": 91, "HBSA": 8}, 6: {"RUMO": 93}, 7: {"RUMO": 63, "HBSA": 36}, 8: {"RUMO": 89},
               9: {"RUMO": 95}, 10: {"RUMO": 89, "RODOVIARIO": 11}, 11: {"RUMO": 97}, 12: {"RUMO": 96}},
        2025: {1: {"RUMO": 92}, 2: {"RUMO": 90, "HBSA": 9}, 3: {"RUMO": 93}, 4: {"RUMO": 94},
               5: {"RUMO": 78, "RODOVIARIO": 11, "HBSA": 10}, 6: {"RUMO": 64, "RODOVIARIO": 11, "HBSA": 24},
               7: {"RUMO": 57, "RODOVIARIO": 10, "HBSA": 33}, 8: {"RUMO": 56, "HBSA": 40}, 9: {"RUMO": 88},
               10: {"RUMO": 82, "HBSA": 18}, 11: {"RUMO": 62, "RODOVIARIO": 12, "HBSA": 22},
               12: {"RUMO": 70, "RODOVIARIO": 16, "HBSA": 12}},
        2026: {1: {"RUMO": 78, "RODOVIARIO": 12, "HBSA": 9}, 2: {"RUMO": 71, "RODOVIARIO": 11, "HBSA": 17},
               3: {"RUMO": 77, "HBSA": 20}, 4: {"RUMO": 74, "RODOVIARIO": 13, "HBSA": 13},
               5: {"RUMO": 70, "RODOVIARIO": 8, "HBSA": 22}, 6: {"RUMO": 67, "RODOVIARIO": 7, "HBSA": 26},
               7: {"RUMO": 60, "HBSA": 39}},
    },
    "MT Nordeste Sul": {
        2024: {2: {"RUMO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RUMO": 100}, 12: {"RUMO": 100}},
        2025: {1: {"RUMO": 81, "RODOVIARIO": 19}, 2: {"VLI SUL": 100}, 3: {"VLI SUL": 100},
               5: {"VLI SUL": 100}, 7: {"RODOVIARIO": 100}, 9: {"RUMO": 100}, 11: {"RUMO": 100}},
        2026: {2: {"RUMO": 56, "RODOVIARIO": 44}, 4: {"VLI SUL": 100}, 6: {"RUMO": 69, "RODOVIARIO": 31}},
    },
    "MT Sudeste": {
        2024: {1: {"RUMO": 65, "RODOVIARIO": 35}, 2: {"RUMO": 49, "RODOVIARIO": 51},
               3: {"RUMO": 35, "RODOVIARIO": 65}, 4: {"RUMO": 34, "RODOVIARIO": 66},
               5: {"RUMO": 35, "RODOVIARIO": 65}, 6: {"RUMO": 47, "RODOVIARIO": 53},
               7: {"RUMO": 42, "RODOVIARIO": 58}, 8: {"RUMO": 38, "RODOVIARIO": 62},
               9: {"RUMO": 32, "RODOVIARIO": 68}, 10: {"RUMO": 53, "RODOVIARIO": 46},
               11: {"RUMO": 49, "RODOVIARIO": 50}, 12: {"RUMO": 57, "RODOVIARIO": 42}},
        2025: {1: {"RUMO": 54, "RODOVIARIO": 46}, 2: {"RUMO": 44, "RODOVIARIO": 56},
               3: {"RUMO": 32, "RODOVIARIO": 68}, 4: {"RUMO": 32, "RODOVIARIO": 68},
               5: {"RUMO": 28, "RODOVIARIO": 72}, 6: {"RUMO": 18, "RODOVIARIO": 82},
               7: {"RUMO": 28, "RODOVIARIO": 71}, 8: {"RUMO": 62, "RODOVIARIO": 38},
               9: {"RUMO": 31, "RODOVIARIO": 69}, 10: {"RUMO": 49, "RODOVIARIO": 50},
               11: {"RUMO": 67, "RODOVIARIO": 33}, 12: {"RUMO": 68, "RODOVIARIO": 32}},
        2026: {1: {"RUMO": 60, "RODOVIARIO": 40}, 2: {"RUMO": 69, "RODOVIARIO": 29},
               3: {"RUMO": 66, "RODOVIARIO": 34}, 4: {"RUMO": 54, "RODOVIARIO": 45},
               5: {"RUMO": 52, "RODOVIARIO": 48}, 6: {"RUMO": 63, "RODOVIARIO": 37},
               7: {"RUMO": 59, "RODOVIARIO": 41}},
    },
    "BA Oeste Sul": {
        2026: {4: {"RODOVIARIO": 100}},
    },
    "BA Outros": {
        2024: {m: {"RODOVIARIO": 100} for m in range(2, 13)},
        2025: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 99}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
            7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100},
            10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2026: {2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100},
               5: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
    },
    "MA Outros": {
        2024: {10: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
    },
    # MG Outros: única região vista até agora com concorrência ferroviária de fato
    # (legendário próprio: RUMO + OP_SUL, sem RODOVIARIO) — não presumir single-player aqui.
    "MG Outros": {
        2024: {5: {"OP_SUL": 100}, 6: {"OP_SUL": 100}, 7: {"OP_SUL": 100},
               8: {"OP_SUL": 100}, 9: {"RUMO": 100}},
        2025: {3: {"OP_SUL": 100}, 8: {"OP_SUL": 100}, 10: {"RUMO": 55, "OP_SUL": 45}},
        2026: {1: {"OP_SUL": 100}, 3: {"OP_SUL": 100}},
    },
    "MS Norte": {
        2024: {
            1: {"RODOVIARIO": 98, "RUMO": 2}, 2: {"RODOVIARIO": 93, "RUMO": 7},
            3: {"RODOVIARIO": 87, "RUMO": 13}, 4: {"RODOVIARIO": 88, "RUMO": 12},
            5: {"RODOVIARIO": 89, "RUMO": 11}, 6: {"RODOVIARIO": 91, "RUMO": 9},
            7: {"RODOVIARIO": 96, "RUMO": 4}, 8: {"RODOVIARIO": 91, "RUMO": 9},
            9: {"RODOVIARIO": 94, "RUMO": 6}, 10: {"RODOVIARIO": 96, "RUMO": 4},
            11: {"RODOVIARIO": 75, "RUMO": 25}, 12: {"RODOVIARIO": 100},
        },
        2025: {
            1: {"RODOVIARIO": 97, "RUMO": 3}, 2: {"RODOVIARIO": 98, "RUMO": 2},
            3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
            6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100},
            9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 99, "RUMO": 1},
            11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2026: {m: {"RODOVIARIO": 100} for m in range(1, 8)},
    },
    "MS Sul": {
        2024: {
            1: {"RODOVIARIO": 97, "RUMO": 3}, 2: {"RODOVIARIO": 94, "RUMO": 6},
            3: {"RODOVIARIO": 96, "RUMO": 4}, 4: {"RODOVIARIO": 92, "RUMO": 8},
            5: {"RODOVIARIO": 93, "RUMO": 7}, 6: {"RODOVIARIO": 94, "RUMO": 6},
            7: {"RODOVIARIO": 93, "RUMO": 7}, 8: {"RODOVIARIO": 91, "RUMO": 9},
            9: {"RODOVIARIO": 95, "RUMO": 5}, 10: {"RODOVIARIO": 94, "RUMO": 6},
            11: {"RODOVIARIO": 88, "RUMO": 12}, 12: {"RODOVIARIO": 87, "RUMO": 13},
        },
        2025: {
            1: {"RODOVIARIO": 96, "RUMO": 4}, 2: {"RODOVIARIO": 94, "RUMO": 6},
            3: {"RODOVIARIO": 95, "RUMO": 5}, 4: {"RODOVIARIO": 97, "RUMO": 3},
            5: {"RODOVIARIO": 91, "RUMO": 9}, 6: {"RODOVIARIO": 91, "RUMO": 9},
            7: {"RODOVIARIO": 96, "RUMO": 4}, 8: {"RODOVIARIO": 97, "RUMO": 3},
            9: {"RODOVIARIO": 97, "RUMO": 3}, 10: {"RODOVIARIO": 96, "RUMO": 4},
            11: {"RODOVIARIO": 98, "RUMO": 2}, 12: {"RODOVIARIO": 92, "RUMO": 8},
        },
        2026: {
            1: {"RODOVIARIO": 98, "RUMO": 2}, 2: {"RODOVIARIO": 99, "RUMO": 1},
            3: {"RODOVIARIO": 97, "RUMO": 3}, 4: {"RODOVIARIO": 98, "RUMO": 2},
            5: {"RODOVIARIO": 98, "RUMO": 2}, 6: {"RODOVIARIO": 99, "RUMO": 1},
            7: {"RODOVIARIO": 98, "RUMO": 2},
        },
    },
    # MT Norte: região mais disputada vista até agora — 4 players (HBSA, RODOVIARIO, RUMO, VLI SUL/OP_SUL).
    "MT Norte": {
        2024: {
            1: {"RODOVIARIO": 100}, 2: {"HBSA": 100}, 3: {"RODOVIARIO": 61, "HBSA": 39},
            4: {"RODOVIARIO": 44, "HBSA": 56}, 5: {"RODOVIARIO": 62, "HBSA": 38},
            6: {"RODOVIARIO": 91, "RUMO": 9}, 7: {"RODOVIARIO": 79, "HBSA": 21},
            8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 76, "RUMO": 7, "OP_SUL": 17},
            10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2025: {
            1: {"HBSA": 10, "RODOVIARIO": 39, "OP_SUL": 50}, 2: {"RODOVIARIO": 100},
            3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 74, "RUMO": 26},
            6: {"HBSA": 100}, 7: {"HBSA": 19, "RODOVIARIO": 81},
            10: {"RODOVIARIO": 66, "RUMO": 34}, 11: {"RODOVIARIO": 100}, 12: {"HBSA": 100},
        },
        2026: {
            1: {"RODOVIARIO": 61, "RUMO": 39}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 54, "HBSA": 46}, 5: {"HBSA": 82, "RUMO": 18},
            6: {"HBSA": 89, "RODOVIARIO": 11},
        },
    },
    # MT Oeste: 4 players também, mas dominância invertida — RUMO/HIDRO PORTO VELHO dominam
    # boa parte do ano (ao contrário de MT Norte onde RODOVIARIO domina).
    "MT Oeste": {
        2024: {
            1: {"RODOVIARIO": 99, "RUMO": 1}, 2: {"RODOVIARIO": 99, "RUMO": 1},
            3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
            6: {"RODOVIARIO": 99, "RUMO": 1}, 7: {"RODOVIARIO": 100},
            8: {"RODOVIARIO": 91, "HBSA": 9}, 9: {"RODOVIARIO": 98, "RUMO": 2},
            10: {"RODOVIARIO": 99, "RUMO": 1}, 11: {"RODOVIARIO": 98, "RUMO": 2},
            12: {"RODOVIARIO": 60, "RUMO": 40},
        },
        2025: {
            1: {"RUMO": 100}, 2: {"HIDRO PORTO VELHO": 100},
            3: {"RUMO": 62, "RODOVIARIO": 38}, 4: {"RUMO": 52, "RODOVIARIO": 48},
            5: {"RUMO": 60, "RODOVIARIO": 40}, 6: {"RUMO": 84, "RODOVIARIO": 15},
            7: {"RUMO": 87, "RODOVIARIO": 13}, 8: {"RUMO": 100}, 9: {"RUMO": 100},
            10: {"RUMO": 100}, 11: {"RUMO": 100}, 12: {"RUMO": 21, "RODOVIARIO": 78},
        },
        2026: {
            1: {"RUMO": 84, "RODOVIARIO": 16}, 2: {"RUMO": 99, "RODOVIARIO": 1},
            3: {"RUMO": 99, "RODOVIARIO": 1}, 4: {"RUMO": 100}, 5: {"RUMO": 100},
            6: {"RUMO": 100}, 7: {"RUMO": 100},
        },
    },
    "PA Nordeste": {
        2024: {m: {"RODOVIARIO": 100} for m in range(1, 13)},
        2025: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100},
               4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
               8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 90}, 10: {"RODOVIARIO": 100},
               11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
    },
    "PA Outros": {
        2024: {4: {"HBSA": 100}, 10: {"RODOVIARIO": 100}},
        2025: {2: {"HBSA": 100}, 4: {"HBSA": 100}, 5: {"RODOVIARIO": 82, "HBSA": 18},
               6: {"HBSA": 100}, 7: {"HBSA": 100}},
        2026: {3: {"HBSA": 100}, 4: {"HBSA": 100}},
    },
    "PE": {
        2025: {6: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100}},
        2026: {1: {"RODOVIARIO": 100}},
    },
    "PR": {
        2024: {
            1: {"RODOVIARIO": 91, "RUMO": 9}, 2: {"RODOVIARIO": 75, "RUMO": 25},
            3: {"RODOVIARIO": 88, "RUMO": 12}, 4: {"RODOVIARIO": 83, "RUMO": 17},
            5: {"RODOVIARIO": 80, "RUMO": 20}, 6: {"RODOVIARIO": 84, "RUMO": 16},
            7: {"RODOVIARIO": 88, "RUMO": 12}, 8: {"RODOVIARIO": 84, "RUMO": 16},
            9: {"RODOVIARIO": 89, "RUMO": 11}, 10: {"RODOVIARIO": 89, "RUMO": 11},
            11: {"RODOVIARIO": 88, "RUMO": 12}, 12: {"RODOVIARIO": 85, "RUMO": 15},
        },
        2025: {
            1: {"RODOVIARIO": 89, "RUMO": 11}, 2: {"RODOVIARIO": 84, "RUMO": 16},
            3: {"RODOVIARIO": 90, "RUMO": 10}, 4: {"RODOVIARIO": 91, "RUMO": 9},
            5: {"RODOVIARIO": 87, "RUMO": 13}, 6: {"RODOVIARIO": 87, "RUMO": 13},
            7: {"RODOVIARIO": 84, "RUMO": 16}, 8: {"RODOVIARIO": 88, "RUMO": 12},
            9: {"RODOVIARIO": 82, "RUMO": 18}, 10: {"RODOVIARIO": 89, "RUMO": 11},
            11: {"RODOVIARIO": 88, "RUMO": 12}, 12: {"RODOVIARIO": 89, "RUMO": 11},
        },
        2026: {
            1: {"RODOVIARIO": 88, "RUMO": 12}, 2: {"RODOVIARIO": 87, "RUMO": 13},
            3: {"RODOVIARIO": 92, "RUMO": 8}, 4: {"RODOVIARIO": 90, "RUMO": 10},
            5: {"RODOVIARIO": 92, "RUMO": 8}, 6: {"RODOVIARIO": 91, "RUMO": 9},
            7: {"RODOVIARIO": 94, "RUMO": 6},
        },
    },
    # RO: player único e exclusivo neste corte — HIDRO PORTO VELHO (nenhuma outra região viu
    # esse player como 100% isolado; em MT Oeste ele aparece só num mês, disputando com RUMO).
    "RO": {
        2024: {1: {"HIDRO PORTO VELHO": 100}, 2: {"HIDRO PORTO VELHO": 100},
               4: {"HIDRO PORTO VELHO": 100}, 7: {"HIDRO PORTO VELHO": 100},
               9: {"HIDRO PORTO VELHO": 100}, 12: {"HIDRO PORTO VELHO": 100}},
        2025: {2: {"HIDRO PORTO VELHO": 100}, 11: {"HIDRO PORTO VELHO": 100},
               12: {"HIDRO PORTO VELHO": 100}},
        2026: {6: {"HIDRO PORTO VELHO": 100}},
    },
    "SC": {
        2024: {
            1: {"RUMO": 100}, 2: {"RODOVIARIO": 79, "RUMO": 21}, 3: {"RODOVIARIO": 80, "RUMO": 20},
            4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 99, "RUMO": 1}, 6: {"RODOVIARIO": 100},
            7: {"RODOVIARIO": 62, "RUMO": 38}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100},
            11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 72, "RUMO": 28},
        },
        2025: {
            1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 90, "RUMO": 10},
            8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100},
            11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2026: {m: {"RODOVIARIO": 100} for m in range(1, 8)},
    },
    "SE": {
        2026: {1: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}},
    },
    "SP": {
        2024: {
            1: {"RODOVIARIO": 99}, 2: {"RODOVIARIO": 99}, 3: {"RODOVIARIO": 100},
            4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
            7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100},
            10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100},
        },
        2025: {m: {"RODOVIARIO": 100} for m in range(1, 13)},
        2026: {m: {"RODOVIARIO": 100} for m in range(1, 8)},
    },
}

PRODUTO = "Farelo de Soja"


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

    print(f"market_share_volume (farelo de soja): {len(vol_rows)} linhas")
    print(f"market_share_player (farelo de soja): {len(ms_rows)} linhas")
    for escopo in VOLUME:
        n = sum(1 for r in vol_rows if r[0] == escopo)
        print(f"  {escopo}: {n} meses com volume lido")
    con.close()


if __name__ == "__main__":
    main()
