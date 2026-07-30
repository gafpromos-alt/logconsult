# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), dimensão PORTO, Produto=MILHO — RODADA 2
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro "Competitividade",
09_Fotos/IMG_0237.MOV, 92s, gravado 13/07/2026) — Produto=MILHO, filtro Porto ciclando os 12
portos. Complementa add_market_share_porto_milho.py (rodada 1).

Alvos desta rodada e resultado:
- **Tmib (VOLUME): NÃO é render-lag — é AUSÊNCIA REAL de dado.** Nos frames f054 e f055 do
  IMG_0237, com o checkbox TMIB marcado (confirmado) e o gráfico JÁ ASSENTADO, o dashboard
  ficou COMPLETAMENTE EM BRANCO (sem barras em 2024/2025/2026, sem Market Share). Dois frames
  assentados consecutivos em branco = Tmib não movimenta Milho. O banco confirma: Tmib só tem
  Soja (7 linhas) em market_share_volume_porto, zero Milho. A "render-lag" das rodadas
  anteriores era a transição Nacional-lag (f052) -> branco-assentado (f054/55). Logo Tmib NÃO
  é preenchível para Milho — nenhuma linha criada aqui (reportado, não estimado).

- **Vitoria (PLAYER SHARE): estendido.** O banco só tinha jan-abr/2024 (6 linhas). Frame f057
  (Porto=VITORIA, dropdown fechado, assentado; volume 2024 bate 100% com o banco -> identidade
  e estabilidade confirmadas). Legenda: RODOVIARIO(amarelo) / VLI NORTE(azul=OP_NORTE) /
  VLI SUL(laranja=OP_SUL). O mapa de cores é confirmado pelo próprio banco (jan-abr/2024 já
  gravados batem: jan OP_SUL73/OP_NORTE27, mar OP_NORTE100 etc.). Lidos os meses de barra
  LEGÍVEL (2 cores com rótulo, ou 3 cores todas rotuladas). Meses com sliver de 3ª cor SEM
  rótulo tiveram só os players rotulados gravados (não se fabricou o sliver).

- **Santos e Portos Sul (PLAYER SHARE): OMITIDOS de novo (reportado).** Santos (f045, assentado)
  é RUMO(verde)-dominante + RODOVIARIO(amarelo) COM um sliver de VLI SUL(laranja) no topo quase
  sempre SEM rótulo -> mix de 3 players com rótulo parcial, mesma razão da rodada 1. Portos Sul
  não teve frame assentado limpo neste vídeo (transições mostraram Nacional). Por "não inventar
  precisão", nenhum dos dois foi gravado — ver relatório.

IMPORTANTE: só INSERT ... WHERE NOT EXISTS (idempotente). Deve entrar no rebuild_market_share.sh
DEPOIS de add_market_share_porto_milho.py. NÃO EXECUTADO — preparado para revisão do usuário.
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0237.MOV, Produto=MILHO, filtro Porto) — mineração exaustiva (1fps), "
         "transcrição manual dos rótulos, 14/jul/2026 (rodada 2 porto).")

PRODUTO = "Milho"

# Tmib: SEM linhas de volume (ausência real de dado — ver docstring).
VOLUME = {}

# ----------------------------------------------------- MARKET SHARE POR PLAYER (%)
# Nomes de player idênticos aos já usados: OP_NORTE (="VLI NORTE"=azul), OP_SUL (="VLI SUL"=laranja),
# RODOVIARIO (=amarelo). porto -> {ano: {mes(1-12): {player: pct}}}. Só meses legíveis.
MS = {
    "Vitoria": {
        # 2024: jan-abr já no banco (WHERE NOT EXISTS os pula). maio-dez novos, lidos no zoom limpo.
        2024: {
            5:  {"OP_NORTE": 100},                                   # barra azul sólida
            6:  {"OP_SUL": 94, "OP_NORTE": 6},                       # 2 cores (6% = complemento)
            7:  {"OP_SUL": 69, "RODOVIARIO": 9, "OP_NORTE": 22},     # 3 cores TODAS rotuladas (=100)
            8:  {"OP_SUL": 99},                                      # laranja 99% + sliver azul s/ rótulo
            9:  {"OP_SUL": 99},
            10: {"OP_SUL": 86, "OP_NORTE": 13},                      # 2 cores rotuladas
            11: {"OP_SUL": 99},
            12: {"OP_SUL": 77, "OP_NORTE": 19},                      # 2 rotuladas (sliver ~4% s/ rótulo omitido)
        },
        # 2025: metade esquerda (jan-jul) com rótulos nítidos de 2 cores. ago-dez ~99-100% laranja
        # (OP_SUL) mas rótulos exatos na metade direita ficaram incertos -> NÃO gravados (prudência).
        2025: {
            1: {"OP_NORTE": 36, "OP_SUL": 64},
            2: {"OP_NORTE": 9,  "OP_SUL": 91},
            3: {"OP_NORTE": 55, "OP_SUL": 42},                       # (~3% 3ª cor s/ rótulo omitido)
            4: {"OP_NORTE": 57, "OP_SUL": 43},
            5: {"OP_NORTE": 48, "OP_SUL": 52},
            6: {"OP_SUL": 94, "OP_NORTE": 6},
            7: {"OP_SUL": 100},
        },
    },
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    vol_inserted = vol_skipped = 0
    for porto, anos in VOLUME.items():
        for ano, meses in anos.items():
            for mes_num, v in meses.items():
                if v is None:
                    continue
                mes = MESES[mes_num - 1]
                cur.execute(
                    """INSERT INTO market_share_volume_porto (porto, produto, ano, mes, volume_t, fonte)
                       SELECT ?, ?, ?, ?, ?, ?
                       WHERE NOT EXISTS (SELECT 1 FROM market_share_volume_porto
                                         WHERE porto=? AND produto=? AND ano=? AND mes=?)""",
                    (porto, PRODUTO, ano, mes, float(v), FONTE, porto, PRODUTO, ano, mes),
                )
                if cur.rowcount:
                    vol_inserted += 1
                else:
                    vol_skipped += 1

    ms_inserted = ms_skipped = 0
    for porto, anos in MS.items():
        for ano, meses in anos.items():
            for mes_num, players in meses.items():
                mes = MESES[mes_num - 1]
                for player, pct in players.items():
                    cur.execute(
                        """INSERT INTO market_share_player_porto (porto, produto, ano, mes, player, pct, fonte)
                           SELECT ?, ?, ?, ?, ?, ?, ?
                           WHERE NOT EXISTS (SELECT 1 FROM market_share_player_porto
                                             WHERE porto=? AND produto=? AND ano=? AND mes=? AND player=?)""",
                        (porto, PRODUTO, ano, mes, player, float(pct), FONTE,
                         porto, PRODUTO, ano, mes, player),
                    )
                    if cur.rowcount:
                        ms_inserted += 1
                    else:
                        ms_skipped += 1

    con.commit()
    print(f"market_share_volume_porto (Milho, r2): {vol_inserted} novas ({vol_skipped} já existiam)")
    print(f"market_share_player_porto (Milho, r2): {ms_inserted} novas ({ms_skipped} já existiam)")
    print("Tmib: 0 linhas (ausência real de dado de Milho — ver docstring).")
    con.close()


if __name__ == "__main__":
    main()
