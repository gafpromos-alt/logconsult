# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), dimensão PORTO
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: mesmo vídeo/dashboard-fonte de add_market_share.py (Soja) — 09_Fotos/IMG_0221.MOV,
t~340-397s. Depois de esgotar a dimensão Microrregião, o vídeo pivota o filtro lateral pra
"Porto" (Microrregião="Todos") e cicla pelos ~12 portos: BARCARENA, BELEM, ITACOATIARA, NAO
IDENTIFICADO, PORTO ACU, PORTOS SUL, SALVADOR, SANTAREM, SANTOS, SAO LUIS, TMIB, VITORIA.

IMPORTANTE — esta é uma dimensão DIFERENTE de Microrregião, não um sub-filtro: o dado de Porto
é agregado nacionalmente (Microrregião="Todos" + Porto=X), não existe cruzamento
região×porto na base-fonte. Por isso vive em tabelas próprias (`market_share_volume_porto`/
`market_share_player_porto`, chave `porto` em vez de `escopo`), não junto às tabelas de
Microrregião — um dado de Porto NÃO deve ser somado/comparado diretamente com um dado de
Microrrégião do mesmo produto/mês (bases diferentes, dupla contagem).

Render-lag do PowerBI reconfirmado aqui, mais severo que na troca de Microrregião: o rótulo do
filtro "Porto" muda quase imediato ao marcar o checkbox, mas o gráfico pode levar vários
segundos pra assentar — vários frames-candidato bateram byte-a-byte com o Nacional (Todos) ou
com o porto anterior (ex. PORTOS SUL/SALVADOR mostraram números de "Todos" nos primeiros
frames pós-clique) e foram descartados; só os frames onde o checkbox E os números batiam entre
2+ capturas foram gravados.

"NAO IDENTIFICADO" é um porto real do dashboard-fonte (não erro de leitura) — o volume bate
quase exatamente com o agregado Nacional inteiro, ou seja, a maior parte da carga não tem porto
atribuído nesta visão. Market Share desse "porto" tem legendário de 7 players com muitas
frações finas sem confiança de leitura suficiente — gravado só o Volume, Share omitido
("não inventar precisão"). Mesma decisão para ITACOATIARA (legendário HIDRO PORTO
VELHO/RODOVIARIO com vários meses de leitura ambígua na foto) — Volume completo, Share só
onde a leitura foi inequívoca.

Cobertura: só Produto=SOJA nesta rodada (12 portos). MILHO e FARELO DE SOJA têm as mesmas
seções de Porto nos respectivos vídeos-fonte (IMG_0222.MOV / IMG_0226.MOV+IMG_0224.MOV) —
ainda NÃO transcritas, pendente de rodada futura se o usuário pedir.

IMPORTANTE: este script só faz INSERT (não DROP de tabelas de outros scripts) — deve rodar
DEPOIS de add_market_share.py (mesma DB, tabelas de Microrregião já criadas antes).

Uso:  python3 add_market_share.py && python3 add_market_share_porto.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0221.MOV, Produto=SOJA, filtro Porto ao invés de Microrregião) — "
         "transcrição manual dos rótulos numéricos das barras.")

PRODUTO = "Soja"

# ---------------------------------------------------------------- VOLUME MOVIMENTADO (t)
VOLUME = {
    "Barcarena": {
        2024: [737069, 1673229, 1683018, 1329946, 838489, 297169, None, 4344, 1296, 958, 423, None],
        2025: [506307, 2234629, 1831193, 1625671, 1052857, 401601, None, 158516, None, 51196, None, None],
        2026: [929411, 1971811, 2276692, 2206034, 2178538, 1127724, 206105, None, None, None, None, None],
    },
    "Belem": {
        2024: [None, None, 51, None, None, None, None, None, None, None, None, None],
        2025: [None, None, None, 355, None, None, None, None, None, None, None, None],
        2026: [285, None, 139, 26941, 941, 299, None, None, None, None, None, None],
    },
    "Itacoatiara": {
        2024: [222320, 262074, 227043, 174524, 44260, 26236, 11619, 11544, 5792, 33127, None, None],
        2025: [70056, 432955, 421234, 555071, 284293, 53860, 85330, 52209, 90314, 58545, 58569, None],
        2026: [288384, 555033, 675924, 540468, 522506, 300623, 91321, None, None, None, None, None],
    },
    "Nao Identificado": {
        2024: [4298338, 9784526, 11777246, 9617959, 6786545, 4384262, None, None, None, 1904728, None, None],
        2025: [3323040, 11960994, 14301553, 12467007, 9749852, 7365636, 6680881, None, 3803328, None, None, None],
        2026: [None, None, None, 14015575, 11855302, 3285935, None, None, None, None, None, None],
    },
    "Porto Acu": {
        2024: [None, None, None, None, None, None, 38, None, None, None, None, None],
        2025: [None, None, None, 8, None, None, None, 28, 13, None, None, None],
        2026: [None, None, None, None, 7, None, None, None, None, None, None, None],
    },
    "Portos Sul": {
        2024: [1544284, 2261934, 2659866, 3138467, 3019280, 2566967, 2734397, 1794422, 1108991, None, None, None],
        2025: [1428503, 2454453, 3468055, 2820359, 2223345, 2736081, 2508399, None, None, None, None, None],
        2026: [1295967, 1971811, 3610263, 3524828, 3154878, 2924023, 909826, None, None, None, None, None],
    },
    "Salvador": {
        2024: [133693, 57355, 258450, 196817, 263535, 166771, 188337, 225927, None, 119544, None, 19933],
        2025: [82884, 245844, 309204, 368400, 298373, 373271, 478774, 450507, None, 57711, None, 206],
        2026: [99252, 272611, 412330, 453740, 497638, 481636, 163565, None, None, None, None, None],
    },
    "Santarem": {
        2024: [11585, 108728, 50176, 7160, 30168, 9605, 35679, None, 536, 1240, 1239, 94],
        2025: [810, 25947, 46948, 12742, 10234, 22899, 1954, 748, 731, None, None, 47],
        2026: [None, None, 27000, 33273, 13552, None, None, None, None, None, None, None],
    },
    "Santos": {
        2024: [1420066, 4323986, 4745045, 3671249, 2030099, 1041080, 667806, 436364, None, None, None, None],
        2025: [1147833, 4791722, 6099769, 5140187, 3834094, 2117440, 1872230, 1732888, None, None, None, None],
        2026: [1875699, 4803081, 6588593, 5763794, 5336661, 4785297, 1275960, None, None, None, None, None],
    },
    "Sao Luis": {
        2024: [156314, 899463, 1484975, 1638129, 1217637, 795163, 514167, 229565, None, None, None, None],
        2025: [75477, 1417961, 1714959, 1775200, 1538156, 1213272, 1027403, 968476, None, 461217, None, 174722],
        2026: [380751, 1152904, 1603682, 1440395, 1615008, 1586670, 450237, None, None, None, None, None],
    },
    "Tmib": {
        2024: [None, None, 24503, 8436, 145, None, None, 135, None, None, None, None],
        2025: [None, None, None, 49, 5265, 8592, None, None, None, None, None, None],
        2026: [None] * 12,
    },
    "Vitoria": {
        2024: [73005, 209484, 333862, 291457, 159665, 271671, 99112, 64348, None, 33107, None, None],
        2025: [10889, 356362, 402010, 464101, 466254, 454603, 308349, None, 53136, 16315, None, None],
        2026: [73491, None, None, 642428, 599269, None, 183773, None, None, None, None, None],
    },
}

# ---------------------------------------------------------- MARKET SHARE POR PLAYER (%)
MS = {
    "Barcarena": {
        # Legendário: HBSA/RODOVIARIO (2 players).
        2024: {
            1: {"HBSA": 89, "RODOVIARIO": 11}, 2: {"HBSA": 79, "RODOVIARIO": 21},
            3: {"HBSA": 78, "RODOVIARIO": 22}, 4: {"HBSA": 75, "RODOVIARIO": 25},
            5: {"HBSA": 67, "RODOVIARIO": 33}, 6: {"HBSA": 42, "RODOVIARIO": 58},
            7: {"HBSA": 16, "RODOVIARIO": 84}, 8: {"HBSA": 12, "RODOVIARIO": 88},
            9: {"HBSA": 35, "RODOVIARIO": 65}, 10: {"HBSA": 33, "RODOVIARIO": 67},
            11: {"HBSA": 49, "RODOVIARIO": 51}, 12: {"HBSA": 100},
        },
        2025: {
            1: {"HBSA": 86, "RODOVIARIO": 14}, 2: {"HBSA": 80, "RODOVIARIO": 20},
            3: {"HBSA": 77, "RODOVIARIO": 23}, 4: {"HBSA": 78, "RODOVIARIO": 22},
            5: {"HBSA": 76, "RODOVIARIO": 24}, 6: {"HBSA": 70, "RODOVIARIO": 30},
            7: {"HBSA": 41, "RODOVIARIO": 59}, 8: {"HBSA": 31, "RODOVIARIO": 69},
            9: {"HBSA": 52, "RODOVIARIO": 48}, 10: {"HBSA": 92}, 11: {"HBSA": 97}, 12: {"HBSA": 99},
        },
        2026: {
            1: {"HBSA": 81, "RODOVIARIO": 19}, 2: {"HBSA": 74, "RODOVIARIO": 26},
            3: {"HBSA": 73, "RODOVIARIO": 27}, 4: {"HBSA": 65, "RODOVIARIO": 35},
            5: {"HBSA": 65, "RODOVIARIO": 35}, 6: {"HBSA": 56, "RODOVIARIO": 44},
            7: {"HBSA": 46, "RODOVIARIO": 54},
        },
    },
    "Belem": {
        2024: {3: {"RODOVIARIO": 100}},
        2025: {4: {"RODOVIARIO": 100}},
        2026: {1: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100},
               5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}},
    },
    "Porto Acu": {
        2024: {7: {"RODOVIARIO": 100}},
        2025: {4: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}},
        2026: {5: {"RODOVIARIO": 100}},
    },
    "Portos Sul": {
        # Legendário: RODOVIARIO/RUMO (2 players).
        2024: {
            1: {"RODOVIARIO": 87, "RUMO": 13}, 2: {"RODOVIARIO": 71, "RUMO": 29},
            3: {"RODOVIARIO": 73, "RUMO": 27}, 4: {"RODOVIARIO": 75, "RUMO": 25},
            5: {"RODOVIARIO": 75, "RUMO": 25}, 6: {"RODOVIARIO": 81, "RUMO": 19},
            7: {"RODOVIARIO": 81, "RUMO": 19}, 8: {"RODOVIARIO": 86, "RUMO": 14},
            9: {"RODOVIARIO": 88, "RUMO": 12}, 10: {"RODOVIARIO": 90, "RUMO": 10},
            11: {"RODOVIARIO": 93}, 12: {"RODOVIARIO": 90, "RUMO": 10},
        },
        2025: {
            1: {"RODOVIARIO": 92, "RUMO": 8}, 2: {"RODOVIARIO": 86, "RUMO": 14},
            3: {"RODOVIARIO": 80, "RUMO": 20}, 4: {"RODOVIARIO": 80, "RUMO": 20},
            5: {"RODOVIARIO": 76, "RUMO": 24}, 6: {"RODOVIARIO": 75, "RUMO": 25},
            7: {"RODOVIARIO": 84, "RUMO": 16}, 8: {"RODOVIARIO": 91, "RUMO": 9},
            9: {"RODOVIARIO": 87, "RUMO": 13}, 10: {"RODOVIARIO": 86, "RUMO": 14},
            11: {"RODOVIARIO": 81, "RUMO": 19}, 12: {"RODOVIARIO": 88, "RUMO": 12},
        },
        2026: {
            1: {"RODOVIARIO": 92, "RUMO": 8}, 2: {"RODOVIARIO": 77, "RUMO": 23},
            3: {"RODOVIARIO": 75, "RUMO": 25}, 4: {"RODOVIARIO": 75, "RUMO": 25},
            5: {"RODOVIARIO": 74, "RUMO": 26}, 6: {"RODOVIARIO": 72, "RUMO": 28},
            7: {"RODOVIARIO": 75, "RUMO": 25},
        },
    },
    "Salvador": {
        # Legendário: RODOVIARIO (praticamente único).
        2024: {i: {"RODOVIARIO": 100} for i in range(1, 13)},
        2025: {i: {"RODOVIARIO": 100} for i in range(1, 13)},
        2026: {i: {"RODOVIARIO": 100} for i in range(1, 8)},
    },
    "Santarem": {
        2024: {i: {"RODOVIARIO": 100} for i in range(1, 13)},
        2025: {i: {"RODOVIARIO": 100} for i in range(1, 13)},
        2026: {i: {"RODOVIARIO": 100} for i in range(3, 6)},
    },
    "Santos": {
        # Legendário: RODOVIARIO/RUMO/VLI SUL. Meses sem leitura clara (set-dez/2024,
        # set-dez/2025, mai-jul/2026) — só volume gravado.
        2024: {
            1: {"RODOVIARIO": 28, "RUMO": 61, "OP_SUL": 11}, 2: {"RODOVIARIO": 37, "RUMO": 52, "OP_SUL": 11},
            3: {"RODOVIARIO": 40, "RUMO": 49, "OP_SUL": 11}, 4: {"RODOVIARIO": 36, "RUMO": 54, "OP_SUL": 10},
            5: {"RODOVIARIO": 32, "RUMO": 60}, 6: {"RODOVIARIO": 39, "RUMO": 55},
            7: {"RODOVIARIO": 40, "RUMO": 49, "OP_SUL": 11}, 8: {"RODOVIARIO": 37, "RUMO": 62},
        },
        2025: {
            1: {"RODOVIARIO": 26, "RUMO": 68}, 2: {"RODOVIARIO": 36, "RUMO": 54, "OP_SUL": 10},
            3: {"RODOVIARIO": 43, "RUMO": 45, "OP_SUL": 13}, 4: {"RODOVIARIO": 36, "RUMO": 51, "OP_SUL": 13},
            5: {"RODOVIARIO": 33, "RUMO": 58, "OP_SUL": 9}, 6: {"RODOVIARIO": 29, "RUMO": 61, "OP_SUL": 10},
            7: {"RODOVIARIO": 36, "RUMO": 51, "OP_SUL": 14}, 8: {"RODOVIARIO": 29, "RUMO": 54, "OP_SUL": 17},
        },
        2026: {
            1: {"RODOVIARIO": 11, "RUMO": 84}, 2: {"RODOVIARIO": 26, "RUMO": 62, "OP_SUL": 12},
            3: {"RODOVIARIO": 32, "RUMO": 52, "OP_SUL": 16},
        },
    },
    "Sao Luis": {
        # Legendário: RODOVIARIO/VLI NORTE.
        2024: {
            1: {"RODOVIARIO": 8, "OP_NORTE": 92}, 2: {"RODOVIARIO": 17, "OP_NORTE": 83},
            3: {"RODOVIARIO": 37, "OP_NORTE": 63}, 4: {"RODOVIARIO": 40, "OP_NORTE": 60},
            5: {"RODOVIARIO": 37, "OP_NORTE": 63}, 6: {"RODOVIARIO": 41, "OP_NORTE": 59},
            7: {"RODOVIARIO": 49, "OP_NORTE": 51}, 8: {"RODOVIARIO": 50, "OP_NORTE": 50},
            9: {"RODOVIARIO": 58, "OP_NORTE": 42}, 10: {"RODOVIARIO": 42, "OP_NORTE": 58},
            11: {"RODOVIARIO": 28, "OP_NORTE": 72}, 12: {"RODOVIARIO": 14, "OP_NORTE": 86},
        },
        2025: {
            1: {"RODOVIARIO": 39, "OP_NORTE": 61}, 2: {"RODOVIARIO": 35, "OP_NORTE": 65},
            3: {"RODOVIARIO": 38, "OP_NORTE": 62}, 4: {"RODOVIARIO": 40, "OP_NORTE": 60},
            5: {"RODOVIARIO": 42, "OP_NORTE": 58}, 6: {"RODOVIARIO": 39, "OP_NORTE": 61},
            7: {"RODOVIARIO": 51, "OP_NORTE": 49}, 8: {"RODOVIARIO": 52, "OP_NORTE": 48},
            9: {"RODOVIARIO": 39, "OP_NORTE": 61}, 10: {"RODOVIARIO": 31, "OP_NORTE": 69},
            11: {"RODOVIARIO": 11, "OP_NORTE": 89}, 12: {"RODOVIARIO": 15, "OP_NORTE": 85},
        },
        2026: {
            1: {"OP_NORTE": 97}, 2: {"RODOVIARIO": 22, "OP_NORTE": 78},
            3: {"RODOVIARIO": 42, "OP_NORTE": 58}, 4: {"RODOVIARIO": 35, "OP_NORTE": 65},
            5: {"RODOVIARIO": 30, "OP_NORTE": 70}, 6: {"RODOVIARIO": 35, "OP_NORTE": 65},
            7: {"RODOVIARIO": 45, "OP_NORTE": 55},
        },
    },
    "Tmib": {
        2024: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}},
        2025: {4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}},
    },
    "Vitoria": {
        # Legendário: RODOVIARIO/VLI SUL (VLI Sul muito dominante).
        2024: {
            1: {"OP_SUL": 100}, 2: {"OP_SUL": 98}, 3: {"OP_SUL": 98}, 4: {"OP_SUL": 99},
            5: {"OP_SUL": 99}, 6: {"OP_SUL": 99}, 7: {"OP_SUL": 99}, 8: {"OP_SUL": 99},
            10: {"OP_SUL": 100},
        },
        2025: {
            1: {"OP_SUL": 100}, 2: {"OP_SUL": 100}, 3: {"OP_SUL": 99}, 4: {"OP_SUL": 99},
            5: {"OP_SUL": 99}, 6: {"OP_SUL": 100}, 7: {"OP_SUL": 99}, 8: {"OP_SUL": 96},
            10: {"OP_SUL": 100},
        },
        2026: {
            1: {"OP_SUL": 99}, 3: {"OP_SUL": 96}, 4: {"OP_SUL": 98}, 5: {"OP_SUL": 95},
            6: {"OP_SUL": 92, "OP_NORTE": 8}, 7: {"OP_SUL": 95},
        },
    },
}


def main():
    vol_rows = []
    for porto, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                vol_rows.append((porto, PRODUTO, ano, MESES[i], float(v), FONTE))

    ms_rows = []
    for porto, anos in MS.items():
        for ano, meses in anos.items():
            for mes, players in meses.items():
                for player, pct in players.items():
                    ms_rows.append((porto, PRODUTO, ano, MESES[mes - 1], player, float(pct), FONTE))

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS market_share_volume_porto")
    cur.execute("""CREATE TABLE market_share_volume_porto(
        porto TEXT, produto TEXT, ano INTEGER, mes TEXT, volume_t REAL, fonte TEXT)""")
    cur.executemany("INSERT INTO market_share_volume_porto VALUES (?,?,?,?,?,?)", vol_rows)

    cur.execute("DROP TABLE IF EXISTS market_share_player_porto")
    cur.execute("""CREATE TABLE market_share_player_porto(
        porto TEXT, produto TEXT, ano INTEGER, mes TEXT, player TEXT, pct REAL, fonte TEXT)""")
    cur.executemany("INSERT INTO market_share_player_porto VALUES (?,?,?,?,?,?,?)", ms_rows)
    con.commit()

    print(f"market_share_volume_porto: {len(vol_rows)} linhas")
    print(f"market_share_player_porto: {len(ms_rows)} linhas")
    for porto in VOLUME:
        n = sum(1 for r in vol_rows if r[0] == porto)
        print(f"  {porto}: {n} meses com volume lido")
    con.close()


if __name__ == "__main__":
    main()
