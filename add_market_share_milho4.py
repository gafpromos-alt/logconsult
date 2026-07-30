# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=MILHO — RODADA 12
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro "Competitividade",
09_Fotos/IMG_0235.MOV, 275s, gravado 13/07/2026) — Produto=MILHO, dimensão Microrregião.
Mineração EXAUSTIVA do vídeo inteiro (frames a 1fps) para fechar buracos de Milho.

Metodologia / disciplina de precisão (regras do projeto), aplicada aqui:
- IDENTIDADE de cada microrregião confirmada por (a) checkbox marcado no MESMO frame quando o
  dropdown Microrregião estava aberto E (b) MATCH DE VALOR-ÂNCORA contra a série já no banco
  (SELECT escopo FROM market_share_volume WHERE produto='Milho' AND volume_t=<valor lido>).
  O banner/título do topo NÃO acompanha o dropdown — nunca usado como fonte de identidade.
- SELEÇÃO MISTA (2+ checkboxes / rótulo "Seleções múltiplas") = SOMA de regiões → DESCARTADA.
- RENDER-LAG do PowerBI: descartados frames logo após troca de filtro (chart do filtro anterior).
  Só valores de frames estáveis (≥3s após a troca, chart assentado).
- COLISÃO de rótulo (duas barras de altura parecida disputando o texto) = None, nunca chutado.
  Mês ausente do eixo do relatório-fonte = ausência real de dado, tratado como fora do dict
  (nunca 0 fabricado), salvo eixo-verificado onde a barra existe com rótulo 0.

Este script SÓ preenche BURACOS (INSERT ... WHERE NOT EXISTS, idempotente): meses/anos que já
existem no banco NÃO são tocados. Ver relatório final para o que foi lido, o que ficou de fora
e por quê, e ambiguidades reportadas (não decididas).

IMPORTANTE: NÃO EXECUTADO — preparado para revisão do usuário. Deve entrar no rebuild_market_share.sh
DEPOIS de add_market_share_milho3.py (que não faz DROP; a cadeia de DROP é add_market_share.py).
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0235.MOV, Produto=MILHO, dimensão Microrregião) — mineração exaustiva "
         "(1fps), identidade por checkbox+match de valor-âncora, transcrição manual dos rótulos "
         "das barras, 14/jul/2026 (rodada 12).")

PRODUTO = "Milho"

# escopo -> {ano: {mes_1a12: volume_t}}. SÓ meses NOVOS (buracos). Só valores lidos com confiança.
# Preenchido INCREMENTALMENTE conforme cada região foi lida no vídeo (checkpoint anti-travamento).
VOLUME = {
    # ---- preenchido incrementalmente abaixo ----

    # PI Sul: frame f048 (t=48s), dropdown FECHADO, Microrregião="NORTE (vmr_corredor) + PI S...".
    # 2024 do frame bate 100% com o banco (âncora) -> frame estável e identidade confirmada.
    # 2025 cauda set-dez lida limpa no zoom (barras alinhadas exatamente aos rótulos de mês):
    "PI Sul": {
        2025: {9: 23034, 10: 3934, 11: 986, 12: 22827},
    },

    # MT Nordeste: frame f037 (t=37s), dropdown FECHADO, "NORTE (vmr_corredor) + MT...".
    # 2024 do frame confirma identidade (jan-ago batem com banco). 2025: julho=235.602 (=banco 07)
    # ancora o alinhamento -> ago-nov novos, limpos (banco só tinha até jul). dez tem barra mas
    # rótulo colidido -> None.
    # NB(reportado, NÃO inserido aqui): MT Nordeste 2024 tem SHIFT no banco — frame f037 mostra
    # 09=539.108 e 10=334.872 com nov ausente, mas o banco tem 539.108 em 10 e 334.872 em 11.
    # Correção (mover meses) é caso do rebuild, não deste INSERT-only (evita duplicar 539.108).
    "MT Nordeste": {
        2025: {8: 486019, 9: 570442, 10: 470356, 11: 302212},
    },

    # TO Leste: frame f056 (t=56s), dropdown FECHADO, "NORTE (vmr_corredor) + TO...".
    # 2024 bate 100% com banco (âncora). 2025 cauda: sete=13.167 (=banco 09) ancora ->
    # out/nov/dez novos, lidos no zoom.
    "TO Leste": {
        2025: {10: 700, 11: 50, 12: 710},
    },

    # GO Leste (corredor SUL): REGIÃO NOVA para Milho (banco tinha ZERO Milho; só Soja=corredor SUL).
    # Frames f074 e f085 (t74 e t85, independentes, IDÊNTICOS), dropdown FECHADO mostrando
    # "SUL (vmr_corredor) + GO LE..." = seleção ÚNICA (não "Seleções múltiplas", não "Todos").
    # Nenhum dos valores existe sob outro escopo no banco (checado) -> não é render-lag de vizinho.
    # Corredor SUL = a mesma série canônica de GO Leste já usada em Soja. 12+12 meses limpos,
    # todos rotulados; 2026 maio ausente do eixo (sem dado).
    "GO Leste": {
        2024: {1: 355, 2: 1388, 3: 1283, 4: 2129, 5: 6319, 6: 6082, 7: 17637,
               8: 34572, 9: 32552, 10: 39149, 11: 48735, 12: 47130},
        2025: {1: 17539, 2: 4552, 3: 853, 4: 468, 5: 7201, 6: 2851, 7: 57110,
               8: 111045, 9: 54778, 10: 58075, 11: 70400, 12: 67368},
        2026: {1: 4937, 2: 179, 3: 287, 4: 38, 6: 172, 7: 156},
    },

    # GO Sudoeste: frame f095 (t95), dropdown FECHADO "SUL (vmr_corredor) + GO SU...".
    # 2024 dez=433.867 (banco não tinha 12; valor inédito no escopo) -> fill limpo. junho tem
    # barra pequena SEM rótulo -> None. 2025 out=546.242 (f098 zoom; nov=529.912 = banco 11,
    # então SEM shift em 2025) -> fill limpo do mês 10; dez tem barra mas SEM rótulo -> None.
    # NB(reportado, NÃO inserido): GO Sudoeste 2024 tem SHIFT no banco igual ao MT Nordeste —
    # o frame limpo f095 mostra 09=564.276 e 10=364.419 (nov ausente), mas o banco tem 564.276
    # em 10 e 364.419 em 11. Correção é caso de rebuild (mover meses), não deste INSERT-only.
    "GO Sudoeste": {
        2024: {12: 433867},
        2025: {10: 546242},
    },

    # MG Outros: frame f190 (t190), dropdown ABERTO com MG OUTROS marcado, assentado.
    # 2024 bate 100% com banco. 2025: dez=213 (banco não tinha 12) -> fill limpo; set e nov têm
    # barra mas os rótulos ficaram TAMPADOS pela caixa do dropdown aberto -> None (não chutados).
    # (dez=213 lido na borda direita do gráfico, fora do dropdown; leitura de 3 dígitos legível,
    # leve ressalva de posição-de-borda reportada.)
    "MG Outros": {
        2025: {12: 213},
    },
}

# escopo -> {ano: {mes_1a12: {player: pct}}}. Player share novo, onde legível e inequívoco.
# (Nenhum player share transcrito nesta rodada: foco na meta de 98% de VOLUME; os stacks de
#  3-4 cores no vídeo tremido têm risco alto de erro — deixados para passe dedicado. Ver relatório.)
MS = {
    # ---- preenchido incrementalmente abaixo ----
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    vol_inserted = vol_skipped = 0
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for mes_num, v in meses.items():
                if v is None:
                    continue
                mes = MESES[mes_num - 1]
                cur.execute(
                    """INSERT INTO market_share_volume (escopo, produto, ano, mes, volume_t, fonte)
                       SELECT ?, ?, ?, ?, ?, ?
                       WHERE NOT EXISTS (
                           SELECT 1 FROM market_share_volume
                           WHERE escopo=? AND produto=? AND ano=? AND mes=?
                       )""",
                    (escopo, PRODUTO, ano, mes, float(v), FONTE, escopo, PRODUTO, ano, mes),
                )
                if cur.rowcount:
                    vol_inserted += 1
                else:
                    vol_skipped += 1

    ms_inserted = ms_skipped = 0
    for escopo, anos in MS.items():
        for ano, meses in anos.items():
            for mes_num, players in meses.items():
                mes = MESES[mes_num - 1]
                for player, pct in players.items():
                    cur.execute(
                        """INSERT INTO market_share_player (escopo, produto, ano, mes, player, pct, fonte)
                           SELECT ?, ?, ?, ?, ?, ?, ?
                           WHERE NOT EXISTS (
                               SELECT 1 FROM market_share_player
                               WHERE escopo=? AND produto=? AND ano=? AND mes=? AND player=?
                           )""",
                        (escopo, PRODUTO, ano, mes, player, float(pct), FONTE,
                         escopo, PRODUTO, ano, mes, player),
                    )
                    if cur.rowcount:
                        ms_inserted += 1
                    else:
                        ms_skipped += 1

    con.commit()
    print(f"market_share_volume (Milho, rodada 12): {vol_inserted} novas ({vol_skipped} já existiam)")
    print(f"market_share_player (Milho, rodada 12): {ms_inserted} novas ({ms_skipped} já existiam)")
    con.close()


if __name__ == "__main__":
    main()
