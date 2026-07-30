# -*- coding: utf-8 -*-
"""
Backfill de custo_logistico_microrregiao (snapshot "TCO Modal - Destino Unico")
com o mes novo 2026-07 para GO Leste, capturado nos vídeos IMG_0232.MOV (Soja) e
IMG_0233.MOV (Milho) — celular filmando dashboard de terceiro (VLI), 13/07/2026.

Cobertura anterior de GO Leste no snapshot: só Soja, meses 2025-11, 2025-12,
2026-02, 2026-04, 2026-05, 2026-06 — nenhum Milho, e 2026-07 ausente para
qualquer produto. Os dois vídeos mostraram o filtro "Período Único" parado em
01/07/2026 com o gráfico "TCO Modal - Destino Unico" plenamente carregado (6
barras, rótulos numéricos legíveis) tanto para Produto=Soja quanto Produto=Milho.

Leitura: cada barra empilhada tem até 5 categorias (Demurrage, Elevação
Portuária, Frete Ferroviário [só rotas ferroviárias], Frete Rodoviário, Quebra),
mas só Elevação Portuária, Frete Ferroviário e Frete Rodoviário têm rótulo
numérico impresso na barra (mesma limitação já documentada em
add_custo_logistico.py). outros_rs_t = total - elevacao - frete_ferroviario -
frete_rodoviario (residual de Quebra + Demurrage, pode ser levemente negativo
por arredondamento — mesma convenção do script de referência).

Uso:  python3 add_custo_logistico_tco_novos.py
"""
import sqlite3
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MICRO = "GO Leste"
MES = "2026-07"

FONTE = ("Vídeo do usuário (celular filmando dashboard de terceiro, "
         "09_Fotos/IMG_0232.MOV + IMG_0233.MOV) — transcrição manual dos rótulos "
         "numéricos do gráfico 'TCO Modal - Destino Unico'.")

# mes | rota | modal | elevacao_portuaria | frete_ferroviario | frete_rodoviario | total
_GO_LESTE_SOJA_202607 = [
    ("Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 178, 108, 344.93),
    ("Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 213, 134, 383.24),
    ("Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 190, 134, 358.70),
    ("Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 139, 144, 344.72),
    ("Rodoviário: Guarujá", "Rodoviário", 23, 0, 288, 318.48),
    ("Rodoviário: Santos", "Rodoviário", 23, 0, 330, 359.05),
]

_GO_LESTE_MILHO_202607 = [
    ("Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 178, 108, 334.86),
    ("Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 213, 134, 373.17),
    ("Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 190, 134, 348.64),
    ("Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 139, 144, 334.65),
    ("Rodoviário: Guarujá", "Rodoviário", 23, 0, 288, 311.77),
    ("Rodoviário: Santos", "Rodoviário", 23, 0, 330, 352.33),
]

PRODUTOS = {
    "Soja": _GO_LESTE_SOJA_202607,
    "Milho": _GO_LESTE_MILHO_202607,
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for produto, linhas in PRODUTOS.items():
        for rota, modal, elev, ferro, rod, total in linhas:
            outros = round(total - elev - ferro - rod, 2)
            cur.execute(
                """SELECT COUNT(*) FROM custo_logistico_microrregiao
                   WHERE microrregiao=? AND produto=? AND mes=? AND rota=?""",
                (MICRO, produto, MES, rota),
            )
            if cur.fetchone()[0] > 0:
                print(f"  ! pulei {produto}/{rota} {MES} (ja existe)")
                continue
            cur.execute(
                """INSERT INTO custo_logistico_microrregiao
                   (microrregiao, produto, mes, rota, modal, elevacao_portuaria_rs_t,
                    frete_ferroviario_rs_t, frete_rodoviario_rs_t, outros_rs_t,
                    total_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (MICRO, produto, MES, rota, modal, elev, ferro, rod, outros, total, FONTE),
            )
            n += 1
    con.commit()
    print(f"Inseridos {n} novos registros em custo_logistico_microrregiao")
    con.close()


if __name__ == "__main__":
    main()
