"""
Segunda leva do backfill de custo_logistico_evolucao (IMG_0219.MOV, continuacao GO Leste).
Mesma metodologia de add_custo_logistico_evolucao_2021.py (tooltip nativo, consistencia
total=soma das 5 parcelas conferida antes de aceitar).
"""
import sqlite3

DB = "logconsult.db"

UBERABA_SANTOS_VLI = [
    ("2022-08", 381.39, 21.25, 172.97, 128.40, 50.00, 8.77),
    ("2023-07", 406.78, 19.62, 149.06, 170.47, 50.00, 17.64),
    ("2023-11", 371.59, 18.29, 137.02, 150.60, 50.00, 15.68),
    ("2024-08", 400.19, 14.94, 95.20, 240.44, 50.00, -0.39),
    ("2024-11", 316.02, 15.96, 100.43, 150.33, 50.00, -0.70),
    ("2025-05", 410.00, 16.47, 148.75, 195.41, 50.00, -0.62),
    ("2026-04", 403.41, 16.19, 168.86, 162.45, 50.00, 5.92),
]

ROTA = "Ferroviario: Uberaba - Santos (VLI)"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for mes, total, quebra, rod, fer, elev, dem in UBERABA_SANTOS_VLI:
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
            ("GO Leste", "Soja", ROTA, mes, "Ferroviario", total, quebra, rod, fer, elev, dem,
             "IMG_0219.MOV tooltip"),
        )
        n += 1
    con.commit()
    print(f"Inseridos {n} novos meses")
    con.close()


if __name__ == "__main__":
    main()
