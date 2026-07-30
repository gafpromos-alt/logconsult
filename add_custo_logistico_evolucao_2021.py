"""
Backfill de custo_logistico_evolucao via tooltip do painel "Evolução Custos"
(IMG_0218.MOV, GO Leste) — pedido do usuario: fechar 98% do historico 2021+
para as rotas ja existentes de GO Leste/GO Sudoeste.

Cada tupla = (data 'YYYY-MM', total, quebra, rodoviario, ferroviario, elevacao, demurrage)
lida diretamente da caixa de tooltip nativa do PowerBI (nao inferida/estimada).
Todos os pontos abaixo passaram no teste de consistencia:
total == quebra+rodoviario+ferroviario+elevacao+demurrage (tolerancia 0.05).
"""
import sqlite3

DB = "logconsult.db"

ARAGUARI_VITORIA = [
    ("2021-11", 242.71, 19.05, 70.89, 99.46, 50.00, 3.31),
    ("2022-06", 301.66, 23.49, 107.94, 110.87, 50.00, 9.35),
    ("2024-07", 423.25, 16.91, 114.41, 241.71, 50.00, 0.23),
    ("2024-09", 358.11, 15.60, 118.90, 166.43, 50.00, 7.19),
    ("2025-07", 378.61, 15.39, 117.05, 191.52, 50.00, 4.65),
    ("2025-08", 383.46, 15.11, 134.69, 175.90, 50.00, 7.76),
    ("2025-09", 366.23, 15.19, 120.31, 164.23, 50.00, 16.51),
    ("2026-03", 412.98, 16.98, 139.94, 179.39, 50.00, 26.67),
    ("2026-07", 349.08, 16.65, 112.19, 177.69, 50.00, -7.45),
]

UBERABA_SANTOS = [
    ("2021-09", 243.22, 18.62, 95.41, 109.72, 23.00, -3.54),
    ("2021-11", 196.97, 19.05, 87.36, 68.29, 23.00, -0.74),
    ("2022-01", 219.45, 21.40, 96.09, 54.01, 23.00, 24.95),
    ("2022-04", 313.03, 22.07, 157.55, 105.95, 23.00, 4.47),
    ("2022-05", 278.23, 22.68, 147.19, 80.69, 23.00, 4.68),
    ("2022-08", 365.74, 21.25, 172.97, 139.75, 23.00, 8.77),
    ("2022-11", 289.62, 20.96, 130.18, 112.83, 23.00, 2.65),
    ("2023-01", 315.21, 21.57, 126.51, 130.58, 23.00, 13.55),
    ("2024-08", 332.74, 14.94, 95.20, 199.98, 23.00, -0.39),
    ("2025-11", 241.03, 16.64, 112.56, 85.00, 23.00, 3.82),
    ("2026-02", 351.11, 16.10, 146.90, 151.91, 23.00, 13.19),
]

ROTAS = {
    "Ferroviario: Araguari - Vitoria": ("GO Leste", "Ferroviario", ARAGUARI_VITORIA),
    "Ferroviario: Uberaba - Santos": ("GO Leste", "Ferroviario", UBERABA_SANTOS),
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for rota, (micro, modal, pontos) in ROTAS.items():
        for mes, total, quebra, rod, fer, elev, dem in pontos:
            # nao inserir duplicata se (rota,mes) ja existir
            cur.execute(
                "SELECT COUNT(*) FROM custo_logistico_evolucao WHERE rota=? AND mes=?",
                (rota, mes),
            )
            if cur.fetchone()[0] > 0:
                print(f"  ! pulei {rota} {mes} (ja existe)")
                continue
            cur.execute(
                """INSERT INTO custo_logistico_evolucao
                   (microrregiao, produto, rota, mes, modal, total_rs_t, quebra_rs_t,
                    frete_rodoviario_rs_t, frete_ferroviario_rs_t, elevacao_portuaria_rs_t,
                    demurrage_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (micro, "Soja", rota, mes, modal, total, quebra, rod, fer, elev, dem,
                 "IMG_0218.MOV tooltip"),
            )
            n += 1
    con.commit()
    print(f"Inseridos {n} novos meses em custo_logistico_evolucao")
    con.close()


if __name__ == "__main__":
    main()
