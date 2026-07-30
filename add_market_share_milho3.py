# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=MILHO — RODADA 3
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro "Competitividade",
09_Fotos/IMG_0235.MOV, 275s, gravado 13/07/2026 ~22:37) — Produto=MILHO (e Soja, no início,
não usado aqui), dimensão Microrregião.

Região identificada: o vídeo abre com o filtro Microrregião mostrando o rótulo truncado pela
própria UI "OUTROS (vmr_corredor) + B..." (largura fixa da caixa, "..." não é corte do vídeo).
Identidade confirmada por MATCH DE VALOR-ÂNCORA (regra-mãe do projeto): os primeiros ~9s do
vídeo mostram Produto=SOJA nessa mesma microrregião, com Volume Movimentado 2024 = [10233, 19433,
48517, 34776, 69188, 46899, ...] — esses 6 valores batem exatamente (SELECT escopo FROM
market_share_volume WHERE produto='Soja' AND volume_t IN (10233,19433,48517,34776,69188,46899))
com o escopo já existente no banco "BA Oeste Sul". Ou seja, "OUTROS (vmr_corredor) + B..." =
BA Oeste Sul.

Cobertura: BA Oeste Sul NÃO tinha nenhuma linha para Milho em market_share_volume (confirmado via
SELECT antes de escrever este script) — só existia para Soja/Farelo de Soja. Dado novo.

O restante do vídeo (t~10s em diante, ~265s) cicla por dezenas de outras combinações
corredor+microrregião (grupos "NORTE (vmr_corredor)", "SUL (vmr_corredor)", "OUTROS
(vmr_corredor)" + BA/MA/MT/PA/PI/TO/GO/MG/... etc.), aparentemente uma re-passada por
microrregiões que, por amostragem, já estão cobertas no banco (ex.: um frame com
"SUL (vmr_corredor) + GO SU..." bateu com os valores já gravados de GO Sudoeste em
add_market_share_milho2.py). Dado o volume de combinações (~30+) e o tempo disponível nesta
rodada, NÃO foi feita a mineração completa do vídeo além da região BA Oeste Sul — ver relatório
para detalhes e candidatos a checar numa rodada futura (ex.: "SUL (vmr_corredor) + GO LESTE",
avistado com o checkbox de GO LESTE marcado JUNTO com GO NOROESTE no mesmo frame — seleção
parcial/mista, dado descartado por prudência, não gravado aqui).

Market Share por Player: o gráfico "Market Share por Player" desta microrregião mostra 4 cores
nas barras (verde, amarelo, azul, laranja), mas a legenda visível no vídeo só lista 3 players
(ADM cinza, VLI NORTE azul, VLI SUL laranja/amarelo) — NÃO aparece um 4º item de legenda para a
cor verde observada em jan/mai/2025 e parcialmente em fev/mar/2025. Isso é uma INCONSISTÊNCIA:
não dá pra saber com segurança qual player o verde representa (poderia ser RUMO, que usa verde
em outros portos/regiões, mas a legenda não confirma). Por "não inventar precisão", o Market
Share por Player desta região foi OMITIDO por completo neste script — só Volume Movimentado.
Reportado no relatório final para o usuário decidir/investigar.

IMPORTANTE: este script só faz INSERT ... WHERE NOT EXISTS (idempotente, nunca duplica).

NÃO EXECUTADO — script preparado para revisão do usuário antes de rodar.
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0235.MOV, Produto=MILHO, Microrregião=\"OUTROS (vmr_corredor) + B...\" "
         "= BA Oeste Sul, identidade confirmada por match de valor-âncora com a série de Soja "
         "já existente no banco) — transcrição manual dos rótulos numéricos das barras, "
         "13/jul/2026.")

PRODUTO = "Milho"

# escopo -> {ano: [12 meses, None = sem rótulo/colisão]}. Mês ausente do eixo do relatório-fonte
# = sem dado real (região MUITO esparsa para Milho), nunca 0 fabricado.
VOLUME = {
    "BA Oeste Sul": {
        2024: [None, None, None, None, None, None, None, None, None, 3562, 477, None],
        2025: [107, 1981, 483, None, 337, None, None, 113, None, None, None, 92],
        2026: [190, None, None, None, None, None, None, None, None, None, None, None],
    },
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    vol_inserted = 0
    vol_skipped = 0
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                mes = MESES[i]
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

    con.commit()

    print(f"market_share_volume (Milho, rodada 3): {vol_inserted} linhas novas inseridas "
          f"({vol_skipped} já existiam / puladas)")
    for escopo in VOLUME:
        n = sum(1 for ano in VOLUME[escopo].values() for v in ano if v is not None)
        print(f"  {escopo}: {n} meses com volume lido")
    print()
    print("Market Share por Player NÃO incluído (cor verde sem legenda correspondente — ver "
          "docstring / relatório).")

    con.close()


if __name__ == "__main__":
    main()
