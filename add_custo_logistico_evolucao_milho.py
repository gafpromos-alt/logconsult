# -*- coding: utf-8 -*-
"""
Backfill de custo_logistico_evolucao — GO Leste, via mineração de 3 vídeos novos
(09_Fotos/IMG_0232.MOV 129s, IMG_0233.MOV 328s, IMG_0234.MOV 334s, celular filmando
dashboard de terceiro (VLI), gravados 13/07/2026 ~22:21-22:35).

Prioridade #1 do pedido do usuário: Milho estava 100% ausente da tabela
custo_logistico_evolucao (só existia para Soja) — IMG_0233.MOV mostrou o filtro
Produto=Milho o vídeo inteiro (GO Leste, Período 01/07/2026 fixo) e permitiu capturar
o tooltip nativo do gráfico "Evolução Custos" (data + 6 valores) para 5 rotas.

Prioridade #2: das ~7 rotas que já existem no snapshot (custo_logistico_microrregiao)
mas não tinham nenhum ponto em custo_logistico_evolucao, IMG_0234.MOV (Soja, GO Leste)
mostrou o filtro "Rota" trocando ao longo do vídeo e revelou pontos novos para duas
delas: "Ferroviario: Rio Verde - Guaruja" e "Ferroviario: Rio Verde - Santos" (nenhuma
tinha QUALQUER mês na evolução antes deste backfill). Também apareceram pontos novos
de Soja para rotas que já tinham alguma cobertura (Araguari-Vitoria, Rodoviario:
Guaruja, Rodoviario: Santos) — meses que ainda faltavam no histórico 2021-2026.

Metodologia (igual aos scripts de referência add_custo_logistico_evolucao_2021*.py):
- Cada ponto é lido do tooltip nativo do PowerBI (Total Custos, Quebra, Frete
  Rodoviário, Frete Ferroviário [None se rota rodoviária], Elevação Portuária,
  Demurrage) parando o vídeo frame a frame (ffmpeg, 1 frame/seg).
- Todo ponto abaixo foi conferido: total == quebra+frete_rodoviario+frete_ferroviario
  (ou 0 se None)+elevacao_portuaria+demurrage, tolerância 0.05.
- Nomes de rota SEM acento, seguindo a convenção já usada na tabela
  custo_logistico_evolucao (diferente do snapshot, que usa acentos).
- Filtro do dashboard em todos os 3 vídeos: Microrregião Originação Carga = "Go Leste".

Pontos DESCARTADOS por inconsistência ou duplicidade não são listados aqui —
ver relatório da tarefa para detalhes de qualquer conflito encontrado.

Uso:  python3 add_custo_logistico_evolucao_milho.py
"""
import sqlite3
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MICRO = "GO Leste"

FONTE_232 = "IMG_0232.MOV tooltip"
FONTE_233 = "IMG_0233.MOV tooltip"
FONTE_234 = "IMG_0234.MOV tooltip"

# formato de cada tupla: (mes 'YYYY-MM', total, quebra, frete_rodoviario,
# frete_ferroviario [None se rota rodoviaria], elevacao_portuaria, demurrage)

# =============================================================================
# MILHO (produto 100% ausente antes deste backfill) — todos de IMG_0233.MOV
# =============================================================================

MILHO_ARAGUARI_VITORIA = [
    ("2021-02", 239.29, 8.79, 80.72, 76.61, 50.00, 23.17),
    ("2021-04", 284.61, 10.10, 109.40, 92.61, 50.00, 22.50),
    ("2021-05", 230.68, 10.57, 85.28, 72.58, 50.00, 12.25),
    ("2021-06", 240.00, 10.00, 88.06, 81.11, 50.00, 10.84),
    ("2021-07", 241.08, 8.49, 76.00, 103.81, 50.00, 2.77),
    ("2021-08", 252.34, 8.57, 75.75, 112.13, 50.00, 5.88),
    ("2021-09", 247.74, 8.19, 82.19, 102.39, 50.00, 4.97),
    ("2021-10", 227.42, 8.78, 71.52, 102.72, 50.00, -5.60),
    ("2022-02", 331.06, 9.98, 115.18, 116.99, 50.00, 38.92),
    ("2022-10", 312.70, 10.62, 129.30, 117.55, 50.00, 5.22),
]

MILHO_RIO_VERDE_SANTOS = [
    ("2021-07", 196.41, 8.49, 70.00, 99.75, 23.00, -4.83),
]

MILHO_UBERABA_SANTOS_VLI = [
    ("2021-01", 243.12, 8.16, 65.65, 93.66, 50.00, 25.65),
    ("2021-05", 261.16, 10.57, 104.05, 93.00, 50.00, 3.55),
    ("2021-06", 261.46, 10.00, 103.98, 96.61, 50.00, 0.88),
]

MILHO_RODOVIARIO_GUARUJA = [
    ("2021-02", 234.20, 5.86, 187.87, None, 23.00, 17.47),
    ("2021-04", 267.62, 6.73, 236.58, None, 23.00, 1.31),
]

MILHO_RODOVIARIO_SANTOS = [
    ("2025-04", 340.29, 5.39, 310.46, None, 23.00, 1.43),
]

MILHO_ROTAS = {
    "Ferroviario: Araguari - Vitoria": ("Ferroviario", MILHO_ARAGUARI_VITORIA, FONTE_233),
    "Ferroviario: Rio Verde - Santos": ("Ferroviario", MILHO_RIO_VERDE_SANTOS, FONTE_233),
    "Ferroviario: Uberaba - Santos (VLI)": ("Ferroviario", MILHO_UBERABA_SANTOS_VLI, FONTE_233),
    "Rodoviario: Guaruja": ("Rodoviario", MILHO_RODOVIARIO_GUARUJA, FONTE_233),
    "Rodoviario: Santos": ("Rodoviario", MILHO_RODOVIARIO_SANTOS, FONTE_233),
}

# =============================================================================
# SOJA — pontos novos (bônus, mesma mineração) para fechar buracos no histórico
# de rotas já cobertas (Araguari-Vitoria, Rodoviario:Guaruja, Rodoviario:Santos,
# todos de IMG_0232.MOV / IMG_0234.MOV) e para as 2 rotas que ainda não tinham
# NENHUM ponto na evolução (Rio Verde-Guaruja, Rio Verde-Santos, ambas de
# IMG_0234.MOV) — uma das ~7 lacunas "snapshot-mas-nao-evolucao" citadas no pedido.
# =============================================================================

SOJA_ARAGUARI_VITORIA = [
    ("2021-02", 251.12, 20.62, 80.72, 76.61, 50.00, 23.17),
    ("2021-03", 319.63, 22.00, 116.20, 97.13, 50.00, 34.29),
    ("2021-04", 296.95, 22.44, 109.40, 92.61, 50.00, 22.50),
    ("2021-05", 242.82, 22.71, 85.28, 72.58, 50.00, 12.25),
    ("2021-07", 252.72, 20.13, 76.00, 103.81, 50.00, 2.77),
    ("2021-08", 263.17, 19.40, 75.75, 112.13, 50.00, 5.88),
    ("2021-09", 258.17, 18.62, 82.19, 102.39, 50.00, 4.97),
    ("2021-10", 237.42, 18.78, 71.52, 102.72, 50.00, -5.60),
    ("2023-04", 357.93, 20.59, 107.20, 169.62, 50.00, 10.51),
    ("2025-02", 396.35, 16.53, 131.17, 173.41, 50.00, 25.23),
    ("2025-06", 382.07, 16.05, 106.04, 205.13, 50.00, 4.85),
    ("2026-02", 391.43, 16.10, 126.06, 185.39, 50.00, 13.88),
    ("2026-06", 366.07, 15.90, 125.98, 174.61, 50.00, -0.42),
]

SOJA_RIO_VERDE_SANTOS = [
    ("2023-09", 324.21, 18.12, 119.18, 152.06, 23.00, 11.85),
    ("2024-04", 409.30, 16.45, 119.95, 251.23, 23.00, -1.33),
    ("2024-10", 383.58, 15.54, 115.00, 230.45, 23.00, -0.41),
    ("2025-05", 393.61, 16.47, 122.79, 231.97, 23.00, -0.62),
]

SOJA_RIO_VERDE_GUARUJA = [
    ("2022-11", 359.54, 20.96, 175.53, 138.99, 23.00, 1.06),
    ("2023-06", 293.54, 19.14, 134.51, 111.08, 23.00, 5.80),
    ("2023-12", 230.11, 17.69, 35.00, 142.95, 23.00, 11.47),
    ("2024-08", 511.72, 14.94, 213.05, 261.33, 23.00, -0.60),
]

SOJA_RODOVIARIO_SANTOS = [
    ("2021-07", 217.37, 13.42, 185.78, None, 23.00, -4.83),
    ("2026-05", 362.92, 11.00, 325.45, None, 23.00, 3.47),
]

SOJA_RODOVIARIO_GUARUJA = [
    ("2022-02", 303.36, 15.15, 251.83, None, 23.00, 13.37),
    ("2025-04", 344.02, 10.93, 311.06, None, 23.00, -0.97),
]

SOJA_ROTAS = {
    "Ferroviario: Araguari - Vitoria": ("Ferroviario", SOJA_ARAGUARI_VITORIA, FONTE_232),
    "Ferroviario: Rio Verde - Santos": ("Ferroviario", SOJA_RIO_VERDE_SANTOS, FONTE_234),
    "Ferroviario: Rio Verde - Guaruja": ("Ferroviario", SOJA_RIO_VERDE_GUARUJA, FONTE_234),
    "Rodoviario: Santos": ("Rodoviario", SOJA_RODOVIARIO_SANTOS, FONTE_234),
    "Rodoviario: Guaruja": ("Rodoviario", SOJA_RODOVIARIO_GUARUJA, FONTE_234),
}


def _check_soma(total, quebra, rod, ferro, elev, dem, tol=0.05):
    partes = quebra + rod + (ferro or 0.0) + elev + dem
    return abs(partes - total) <= tol


def _inserir(cur, produto, rota, modal, pontos, fonte):
    n = 0
    for mes, total, quebra, rod, ferro, elev, dem in pontos:
        if not _check_soma(total, quebra, rod, ferro, elev, dem):
            print(f"  ! SOMA NAO BATE, pulando {produto}/{rota} {mes} (total={total})")
            continue
        cur.execute(
            """SELECT COUNT(*) FROM custo_logistico_evolucao
               WHERE microrregiao=? AND produto=? AND rota=? AND mes=?""",
            (MICRO, produto, rota, mes),
        )
        if cur.fetchone()[0] > 0:
            print(f"  ! pulei {produto}/{rota} {mes} (ja existe)")
            continue
        cur.execute(
            """INSERT INTO custo_logistico_evolucao
               (microrregiao, produto, rota, mes, modal, total_rs_t, quebra_rs_t,
                frete_rodoviario_rs_t, frete_ferroviario_rs_t, elevacao_portuaria_rs_t,
                demurrage_rs_t, fonte)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (MICRO, produto, rota, mes, modal, total, quebra, rod, ferro, elev, dem, fonte),
        )
        n += 1
    return n


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    total_n = 0

    print("== Milho (novo produto) ==")
    for rota, (modal, pontos, fonte) in MILHO_ROTAS.items():
        n = _inserir(cur, "Milho", rota, modal, pontos, fonte)
        print(f"  {rota}: {n} inseridos")
        total_n += n

    print("== Soja (bonus: rotas novas + buracos de historico) ==")
    for rota, (modal, pontos, fonte) in SOJA_ROTAS.items():
        n = _inserir(cur, "Soja", rota, modal, pontos, fonte)
        print(f"  {rota}: {n} inseridos")
        total_n += n

    con.commit()
    print(f"\nTotal inserido em custo_logistico_evolucao: {total_n}")
    con.close()


if __name__ == "__main__":
    main()
