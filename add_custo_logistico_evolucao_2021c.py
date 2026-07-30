"""
Terceira leva do backfill de custo_logistico_evolucao (IMG_0220.MOV, GO Sudoeste).
Mesma metodologia (tooltip nativo + checagem de consistencia total=soma das parcelas).
"""
import sqlite3

DB = "logconsult.db"
ROTA = "Ferroviario: Uberaba - Santos"
MICRO = "GO Sudoeste"

PONTOS = [
    ("2024-02", 353.72, 16.00, 120.65, 185.00, 23.00, 9.06),
    ("2024-03", 401.36, 16.26, 109.58, 247.48, 23.00, 5.03),
    ("2024-07", 403.78, 16.91, 108.43, 253.88, 23.00, 1.56),
    ("2024-08", 394.15, 14.94, 103.23, 253.37, 23.00, -0.39),
    ("2025-01", 301.60, 17.14, 88.31, 162.96, 23.00, 10.19),
    ("2025-03", 443.27, 16.05, 170.86, 227.56, 23.00, 5.80),
    ("2025-07", 320.16, 15.39, 137.52, 131.21, 23.00, 13.04),
    ("2026-03", 399.30, 16.98, 165.74, 182.04, 23.00, 11.54),
    ("2026-06", 324.55, 15.90, 135.97, 144.30, 23.00, 5.37),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for mes, total, quebra, rod, fer, elev, dem in PONTOS:
        cur.execute(
            "SELECT COUNT(*) FROM custo_logistico_evolucao WHERE rota=? AND mes=?",
            (ROTA, mes),
        )
        if cur.fetchone()[0] > 0:
            print(f"  ! pulei {ROTA} {mes} (ja existe)")
            continue
        cur.execute(
            """INSERT INTO custo_logistico_evolucao
               (microrregiao, produto, rota, mes, modal, total_rs_t, quebra_rs_t,
                frete_rodoviario_rs_t, frete_ferroviario_rs_t, elevacao_portuaria_rs_t,
                demurrage_rs_t, fonte)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MICRO, "Soja", ROTA, mes, "Ferroviario", total, quebra, rod, fer, elev, dem,
             "IMG_0220.MOV tooltip"),
        )
        n += 1
    con.commit()
    print(f"Inseridos {n} novos meses")
    con.close()


if __name__ == "__main__":
    main()
