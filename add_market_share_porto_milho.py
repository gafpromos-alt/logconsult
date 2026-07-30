# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), dimensão PORTO, Produto=MILHO
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro "Competitividade",
09_Fotos/IMG_0237.MOV, 92s, gravado 13/07/2026 ~22:43) — Produto=MILHO, filtro Porto (Microrregião
="Todos"). O vídeo cicla alfabeticamente pelos mesmos 12 portos já cobertos para Soja em
add_market_share_porto.py: BARCARENA, BELEM, ITACOATIARA, NAO IDENTIFICADO, PORTO ACU, PORTOS SUL,
SALVADOR, SANTAREM, SANTOS, SAO LUIS, TMIB, VITORIA. Antes deste script, MILHO não tinha NENHUMA
linha em market_share_volume_porto/market_share_player_porto (confirmado via SELECT antes de
escrever este arquivo).

Metodologia / disciplina de precisão (regras do projeto):
- SAO LUIS aparece DUAS VEZES no vídeo (estado inicial ~t0-9s e de novo ~t47-51s, no meio do ciclo
  alfabético) — os dois frames bateram byte-a-byte (mesmos 31 valores de volume + mesmos % de
  player), o que dá confiança alta nessa leitura.
- Render-lag do PowerBI reconfirmado e mais severo que em rodadas anteriores: ao trocar o
  checkbox de Porto, o gráfico pode continuar mostrando o agregado "Todos"/Nacional (ou o porto
  anterior) por vários frames antes de assentar. Ex.: TMIB nunca estabilizou em nenhum frame do
  vídeo (frames com TMIB marcado mostraram ou o agregado Nacional obsoleto, ou o painel em branco
  durante o recarregamento) — por isso TMIB foi OMITIDO deste script (nenhuma linha), não estimado.
- PORTOS SUL 2026: o próprio dropdown (aberto para trocar de porto) ficou por cima das barras de
  janeiro/fevereiro/março, e novembro/dezembro/2025 também ficaram parcialmente cobertos —
  omitidos (None / fora do dicionário) em vez de chutados.
- Barra sem rótulo por colisão (duas barras de altura parecida disputando o mesmo espaço de
  texto) = None, nunca chutado. Meses ausentes do próprio eixo (categoria não desenhada) = ausência
  real de dado no relatório-fonte, tratados como "fora do dicionário" (nunca 0 fabricado).
- Market Share por Player: só gravado onde a leitura foi inequívoca (single-frame com dropdown
  fechado ou, no mínimo, com o gráfico já estabilizado). Portos com mix de 3 players e rótulos
  parciais (SANTOS: RUMO/RODOVIARIO/VLI SUL; PORTOS SUL: RODOVIARIO/RUMO com 2026 parcialmente
  tampado) tiveram o Market Share OMITIDO neste round por prudência — Volume Movimentado desses
  dois portos foi gravado normalmente.

IMPORTANTE: este script só faz INSERT ... WHERE NOT EXISTS (idempotente, nunca duplica) — pode
rodar mais de uma vez sem efeito colateral. Deve rodar depois dos scripts que criam as tabelas
market_share_volume_porto / market_share_player_porto (já existem hoje, criadas por
add_market_share_porto.py com dados de Soja).

NÃO EXECUTADO — script preparado para revisão do usuário antes de rodar.
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0237.MOV, Produto=MILHO, filtro Porto ao invés de Microrregião) — "
         "transcrição manual dos rótulos numéricos das barras, 13/jul/2026.")

PRODUTO = "Milho"

# ---------------------------------------------------------------- VOLUME MOVIMENTADO (t)
# porto -> {ano: [12 meses, None = sem rótulo por colisão]}. Mês ausente do dict (lista mais curta
# tratada via índice explícito abaixo) = categoria não desenhada no eixo do relatório-fonte.
VOLUME = {
    # Confirmado 2x no vídeo (t~0-9s e novamente t~47-51s, valores idênticos byte-a-byte).
    "Sao Luis": {
        2024: [71067, 4834, 2000, 1236, 1022, 48708, 470716, 640515, 739288, 556324, 222032, None],
        2025: [51192, 2773, 2066, 1373, 1314, 15881, 238162, 532495, 608238, 527474, 268622, None],
        2026: [47368, 3714, 2659, 568, 1234, 1767, 13874, None, None, None, None, None],
    },
    "Barcarena": {
        2024: [405008, 16293, 28080, None, 379857, 1009503, 1971362, 1102493, 451413, None, 225260, None],
        2025: [19410, 4039, 9688, 7953, 4517, 634425, 1621997, 1890321, 1130169, None, 927910, None],
        2026: [168569, 7340, 997, 73296, 192473, 1166281, 610040, None, None, None, None, None],
    },
    # Belem: meses ausentes do eixo no relatório-fonte (não é colisão) = sem dado, não zero.
    "Belem": {
        2024: [1219, 1066, 178, None, 51, 24, None, 4598, 2, 97, 49, 315],
        2025: [None, 208, None, 50, None, None, 33, None, None, None, None, None],
        2026: [None, None, 10673, 19438, 5985, 3167, 7647, None, None, None, None, None],
    },
    "Itacoatiara": {
        2024: [42310, 1515, 636, 23801, 53405, 142972, 166475, 144525, 15254, 1023, 17623, 42041],
        2025: [17215, 2384, 1427, 1095, 668, 89399, 407934, 274898, 189535, 325934, 215224, None],
        2026: [34913, 913, 868, 1377, 3747, 120180, 84496, None, None, None, None, None],
    },
    # Nao Identificado: 2024 e 2026 sem NENHUM dado no relatório-fonte (painel vazio, conferido).
    "Nao Identificado": {
        2024: [None] * 12,
        2025: [None, None, None, None, None, None, None, 9911, 6413, 272, None, 564],
        2026: [None] * 12,
    },
    "Porto Acu": {
        2024: [None, None, 9, None, None, 131, None, 25, None, 110, 28, 130],
        2025: [73, None, None, 42, None, None, None, None, None, None, None, None],
        2026: [None, 43, None, None, None, None, None, None, None, None, None, None],
    },
    # Portos Sul: fev/2025 sem rótulo (colisão com jan); nov/2025 e dez/2025 tampados pelo próprio
    # dropdown do filtro Porto (aberto no frame disponível) — sem leitura confiável, omitidos.
    # 2026 inteiro tampado pelo mesmo dropdown (só abril-julho parcialmente visíveis e mesmo assim
    # com dúvida) — omitido por completo neste round.
    "Portos Sul": {
        2024: [481783, 164887, None, 86624, 307198, 392100, 239471, 369127, 454015, 702439, 617204, 533352],
        2025: [808137, None, 303357, 82248, 218350, 550625, 1310528, 1144643, 1050163, 475093, None, None],
        2026: [None] * 12,
    },
    # Salvador: meses ausentes do eixo (mar/out 2024; jun/jul 2025; fev/mar/abr 2026) = sem dado.
    "Salvador": {
        2024: [64, 35, None, 32, 40, 56, 74, 141, 124, None, 135, 90],
        2025: [43, 82, 56, 173, 583, None, None, 79, 108, 50, 146, 46],
        2026: [109, None, None, None, 48, 22, 2, None, None, None, None, None],
    },
    "Santarem": {
        2024: [39710, 3715, 5114, 1823, 3026, 150839, None, 26575, 152555, 213418, 109754, 2123],
        2025: [19155, 6397, 4, 37, 1047, 54231, 93087, 88842, 56822, 37634, 41570, 31799],
        2026: [41075, 319, 103, 186, 9801, 62080, 66291, None, None, None, None, None],
    },
    # Santos: abril/junho/dezembro-2024 e novembro/dezembro-2025 sem rótulo (colisão com barras
    # vizinhas de altura parecida) -> None.
    "Santos": {
        2024: [518342, 91279, 72770, None, 73722, None, 1782148, 2296326, 2670767, 1893680, 1328972, None],
        2025: [176240, None, 63878, 49987, None, 209146, 1883797, 2509495, 2486017, 2076264, None, None],
        2026: [487299, 70298, 69188, 54796, 85125, 157813, 287043, None, None, None, None, None],
    },
    "Vitoria": {
        2024: [392, 689, 34, 163, 102, 1256, 473, 30683, 103317, 23102, 9645, 2435],
        2025: [773, 1181, 805, 829, 1276, 829, 49733, 59625, 60386, 98183, 297173, 243886],
        2026: [6160, 899, 844, 229, 503, 586, 106, None, None, None, None, None],
    },
    # TMIB: NÃO INCLUÍDO — nenhum frame do vídeo estabilizou com dado próprio de Tmib (render-lag
    # mostrou o agregado Nacional obsoleto ou painel em branco). Ver ressalva no cabeçalho.
}

# ---------------------------------------------------------- MARKET SHARE POR PLAYER (%)
# Convenção de nomes de player idêntica à já usada em market_share_player_porto (Soja):
# HBSA, OP_NORTE (= "VLI NORTE" na legenda), OP_SUL (= "VLI SUL"), RODOVIARIO, RUMO,
# HIDRO_PORTO_VELHO.
# porto -> {ano: {mes(1-12): {player: pct}}}. Só meses com leitura inequívoca.
MS = {
    "Sao Luis": {
        # Legendário: RODOVIARIO / VLI NORTE (2 players, igual Soja).
        2024: {
            1: {"RODOVIARIO": 81, "OP_NORTE": 19}, 2: {"OP_NORTE": 64, "RODOVIARIO": 36},
            3: {"OP_NORTE": 87, "RODOVIARIO": 13}, 4: {"OP_NORTE": 63, "RODOVIARIO": 37},
            5: {"OP_NORTE": 77, "RODOVIARIO": 23}, 6: {"OP_NORTE": 99},
            7: {"OP_NORTE": 89, "RODOVIARIO": 11}, 8: {"OP_NORTE": 68, "RODOVIARIO": 32},
            9: {"OP_NORTE": 71, "RODOVIARIO": 29}, 10: {"OP_NORTE": 74, "RODOVIARIO": 26},
            11: {"OP_NORTE": 79, "RODOVIARIO": 21}, 12: {"OP_NORTE": 80, "RODOVIARIO": 20},
        },
        2025: {
            1: {"RODOVIARIO": 98}, 2: {"OP_NORTE": 49, "RODOVIARIO": 51},
            3: {"OP_NORTE": 13, "RODOVIARIO": 87}, 4: {"OP_NORTE": 10, "RODOVIARIO": 90},
            5: {"OP_NORTE": 11, "RODOVIARIO": 89}, 6: {"OP_NORTE": 94},
            7: {"OP_NORTE": 86, "RODOVIARIO": 14}, 8: {"OP_NORTE": 85, "RODOVIARIO": 15},
            9: {"OP_NORTE": 80, "RODOVIARIO": 20}, 10: {"OP_NORTE": 90, "RODOVIARIO": 10},
            11: {"OP_NORTE": 98}, 12: {"OP_NORTE": 90, "RODOVIARIO": 10},
        },
        2026: {
            1: {"RODOVIARIO": 91, "OP_NORTE": 9}, 2: {"OP_NORTE": 70, "RODOVIARIO": 30},
            3: {"OP_NORTE": 27, "RODOVIARIO": 73}, 4: {"OP_NORTE": 100}, 5: {"RODOVIARIO": 100},
            6: {"OP_NORTE": 80, "RODOVIARIO": 20}, 7: {"OP_NORTE": 100},
        },
    },
    "Barcarena": {
        # Legendário: HBSA / RODOVIARIO (2 players, igual Soja).
        2024: {
            1: {"HBSA": 97}, 2: {"HBSA": 95}, 3: {"HBSA": 98}, 4: {"HBSA": 100}, 5: {"HBSA": 100},
            6: {"HBSA": 100}, 7: {"HBSA": 87, "RODOVIARIO": 13}, 8: {"HBSA": 77, "RODOVIARIO": 23},
            9: {"HBSA": 74, "RODOVIARIO": 26}, 10: {"HBSA": 40, "RODOVIARIO": 60},
            11: {"HBSA": 66, "RODOVIARIO": 34}, 12: {"HBSA": 98},
        },
        2025: {
            1: {"RODOVIARIO": 37, "HBSA": 63}, 2: {"HBSA": 94}, 3: {"HBSA": 94}, 4: {"HBSA": 98},
            5: {"HBSA": 99}, 6: {"HBSA": 98}, 7: {"HBSA": 93}, 8: {"HBSA": 88, "RODOVIARIO": 12},
            9: {"HBSA": 84, "RODOVIARIO": 16}, 10: {"HBSA": 85, "RODOVIARIO": 15},
            11: {"HBSA": 85, "RODOVIARIO": 15}, 12: {"HBSA": 88, "RODOVIARIO": 12},
        },
        2026: {
            1: {"HBSA": 94, "RODOVIARIO": 6}, 2: {"HBSA": 87, "RODOVIARIO": 13}, 3: {"HBSA": 97},
            4: {"HBSA": 100}, 5: {"HBSA": 100}, 6: {"HBSA": 93, "RODOVIARIO": 7}, 7: {"HBSA": 88, "RODOVIARIO": 12},
        },
    },
    # Belem: 100% RODOVIARIO em todos os meses com volume (mesmo padrão da Soja).
    "Belem": {
        2024: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
               6: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100},
               11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
        2025: {2: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
        2026: {3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100},
               7: {"RODOVIARIO": 100}},
    },
    # Itacoatiara: 100% HIDRO PORTO VELHO em todos os meses com volume (leitura limpa, sem
    # ambiguidade — diferente da Soja, onde havia mix com RODOVIARIO em alguns meses).
    "Itacoatiara": {
        2024: {m: {"HIDRO_PORTO_VELHO": 100} for m in range(1, 13)},
        2025: {m: {"HIDRO_PORTO_VELHO": 100} for m in range(1, 12)},  # dez sem volume lido
        2026: {m: {"HIDRO_PORTO_VELHO": 100} for m in range(1, 8)},
    },
    # Nao Identificado: 100% RUMO nos 4 meses com volume.
    "Nao Identificado": {
        2025: {8: {"RUMO": 100}, 9: {"RUMO": 100}, 10: {"RUMO": 100}, 12: {"RUMO": 100}},
    },
    # Porto Acu: 100% RODOVIARIO em todos os meses com volume.
    "Porto Acu": {
        2024: {3: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100},
               10: {"RODOVIARIO": 100}, 11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
        2025: {1: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}},
        2026: {2: {"RODOVIARIO": 100}},
    },
    # Salvador: 100% RODOVIARIO em todos os meses com volume.
    "Salvador": {
        2024: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100},
               6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100},
               11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
        2025: {1: {"RODOVIARIO": 100}, 2: {"RODOVIARIO": 100}, 3: {"RODOVIARIO": 100}, 4: {"RODOVIARIO": 100},
               5: {"RODOVIARIO": 100}, 8: {"RODOVIARIO": 100}, 9: {"RODOVIARIO": 100}, 10: {"RODOVIARIO": 100},
               11: {"RODOVIARIO": 100}, 12: {"RODOVIARIO": 100}},
        2026: {1: {"RODOVIARIO": 100}, 5: {"RODOVIARIO": 100}, 6: {"RODOVIARIO": 100}, 7: {"RODOVIARIO": 100}},
    },
    # Santarem: 100% RODOVIARIO em todos os meses com volume.
    "Santarem": {
        2024: {m: {"RODOVIARIO": 100} for m in [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]},
        2025: {m: {"RODOVIARIO": 100} for m in range(1, 13)},
        2026: {m: {"RODOVIARIO": 100} for m in range(1, 8)},
    },
    # Vitoria: legendário RODOVIARIO/VLI NORTE/VLI SUL — só os 4 primeiros meses de 2024 tiveram
    # leitura inequívoca; maio/2024 em diante (e todo 2025/2026) tinham splits de 3 cores com
    # rótulos parciais demais para confiança "não inventar precisão" -> omitidos.
    "Vitoria": {
        2024: {
            1: {"OP_SUL": 73, "OP_NORTE": 27}, 2: {"OP_SUL": 79, "OP_NORTE": 21},
            3: {"OP_NORTE": 100}, 4: {"OP_NORTE": 100},
        },
    },
    # Santos: mix de 3 players (RUMO/RODOVIARIO/VLI SUL) com rótulos parciais em quase todos os
    # meses -> Market Share OMITIDO neste round (só Volume Movimentado gravado acima).
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    vol_inserted = 0
    vol_skipped = 0
    for porto, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                mes = MESES[i]
                cur.execute(
                    """INSERT INTO market_share_volume_porto (porto, produto, ano, mes, volume_t, fonte)
                       SELECT ?, ?, ?, ?, ?, ?
                       WHERE NOT EXISTS (
                           SELECT 1 FROM market_share_volume_porto
                           WHERE porto=? AND produto=? AND ano=? AND mes=?
                       )""",
                    (porto, PRODUTO, ano, mes, float(v), FONTE, porto, PRODUTO, ano, mes),
                )
                if cur.rowcount:
                    vol_inserted += 1
                else:
                    vol_skipped += 1

    ms_inserted = 0
    ms_skipped = 0
    for porto, anos in MS.items():
        for ano, meses in anos.items():
            for mes_num, players in meses.items():
                mes = MESES[mes_num - 1]
                for player, pct in players.items():
                    cur.execute(
                        """INSERT INTO market_share_player_porto
                               (porto, produto, ano, mes, player, pct, fonte)
                           SELECT ?, ?, ?, ?, ?, ?, ?
                           WHERE NOT EXISTS (
                               SELECT 1 FROM market_share_player_porto
                               WHERE porto=? AND produto=? AND ano=? AND mes=? AND player=?
                           )""",
                        (porto, PRODUTO, ano, mes, player, float(pct), FONTE,
                         porto, PRODUTO, ano, mes, player),
                    )
                    if cur.rowcount:
                        ms_inserted += 1
                    else:
                        ms_skipped += 1

    con.commit()

    print(f"market_share_volume_porto (Milho): {vol_inserted} linhas novas inseridas "
          f"({vol_skipped} já existiam / puladas)")
    print(f"market_share_player_porto (Milho): {ms_inserted} linhas novas inseridas "
          f"({ms_skipped} já existiam / puladas)")
    print()
    print("Portos cobertos (volume):", ", ".join(VOLUME.keys()))
    print("TMIB não incluído (ver ressalva no cabeçalho do arquivo).")

    con.close()


if __name__ == "__main__":
    main()
