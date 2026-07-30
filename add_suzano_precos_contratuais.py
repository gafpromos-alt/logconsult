#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_suzano_precos_contratuais.py

Cria/recria a tabela `suzano_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste do fluxo ferroviario PSU (SUZANO) -> QPM (PONTA DA
MADEIRA), minerado do video de tela do F-LINK (flink.vli.digital, tela "Item Ferroviario >
Preco > PRECOS CONTRATUAIS").

ATENCAO: na tela do F-LINK, o campo Cliente deste item aparece como "CELULOSE NIPO BRASILEIRA
S.A. - CENIBRA" (mesmo contrato guarda-chuva CENIBRA_2007_2023) — "SUZANO" e o nome da
estacao de origem (PSU), nao um campo de cliente distinto na fonte. O item foi separado nesta
tabela por decisao do usuario (18/jul/2026), que confirmou que o fluxo se refere a Suzano S.A.
(empresa de celulose distinta da CENIBRA no mundo real), apesar do contrato F-LINK ser
administrado sob o guarda-chuva CENIBRA. Movido para fora de add_cenibra_precos_contratuais.py
(nao duplicado).

Uma linha por vigencia/reajuste/cadastro.

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa, aplica e conecta ao
Painel do Cliente via connect_suzano_precos.py.

Fonte: F-LINK Precos Contratuais (IMG_0451.MOV).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0451.MOV) - fluxo PSU->QPM, contrato guarda-chuva CENIBRA_2007_2023"

# ---------------------------------------------------------------------------
# Metadados do item ferroviario (confirmado no cabecalho do video)
# ---------------------------------------------------------------------------
FLUXOS = {
    14844: dict(contrato="CENIBRA_2007_2023", origem="PSU", origem_nome="SUZANO",
                destino="QPM", destino_nome="PONTA DA MADEIRA", produto="CELULOSE",
                video="IMG_0451.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete, manobra_origem, manobra_destino, manobra_conexao_cheio,
#    direito_passagem, outros_servicos)
# Datas em YYYY-MM-DD. Valores em R$/t. None quando o servico nao existe nesse item.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 14844 | PSU->QPM | CELULOSE | IMG_0451.MOV ---
# Fluxo intermodal EFC (Direito de Passagem) + FNS (Frete/Manobra Origem/Manobra
# Destino/Outros Servicos, este ultimo sempre R$0,00). 40 vigencias/cadastros lidos,
# cobrindo 29/04/2021 (inicio do contrato) ate 30/06/2026. Video de 36s (72 frames);
# leitura frame-a-frame ininterrupta, pulando apenas frames com scroll-blur/dupla-exposicao.
DADOS[14844] = [
    # vig_ini      vig_fim       TR      tarifa   frete   mo    md    mcc    dp     outros
    ("2026-07-10", "2039-07-12", 156.22, 114.91, 83.69, 8.32, 8.32, None, 14.58, 0.00),
    ("2026-06-10", "2039-07-12", 156.22, 115.06, 83.84, 8.32, 8.32, None, 14.58, 0.00),
    ("2026-05-10", "2039-07-12", 156.22, 116.18, 84.96, 8.32, 8.32, None, 14.58, 0.00),
    ("2026-04-10", "2039-07-12", 156.22, 116.00, 84.78, 8.32, 8.32, None, 14.58, 0.00),
    ("2026-03-10", "2039-07-12", 156.22, 113.34, 82.12, 8.32, 8.32, None, 14.58, 0.00),
    ("2026-02-10", "2039-07-12", 156.22, 113.62, 82.99, 8.32, 8.32, None, 13.99, 0.00),
    ("2026-01-10", "2039-07-12", 158.11, 113.65, 83.02, 8.32, 8.32, None, 13.99, 0.00),
    ("2026-01-01", "2039-07-12", 158.11, 113.91, 83.28, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-12-10", "2025-12-31", 158.11,  95.34, 64.71, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-12-02", "2025-12-09", 158.11,  94.73, 64.10, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-11-10", "2039-07-12", 158.11, 113.18, 82.55, 8.32, 8.32, None, 13.99, 0.00),
    ("2023-12-06", "2023-12-31", 153.01,  83.42, 54.03, 8.32, 8.32, None, 12.75, 0.00),  # cadastro 27/10/2025
    ("2022-11-21", "2022-12-31", 145.68,  87.71, 59.01, 8.32, 8.32, None, 12.06, 0.00),  # cadastro 27/10/2025
    ("2023-12-06", "2023-12-31", 153.01,  83.42, 66.78, 8.32, 8.32, None,  0.00, 0.00),  # 1o cadastro (15/10/2025), re-cadastrado acima
    ("2022-11-21", "2022-12-31", 145.68,  87.71, 71.07, 8.32, 8.32, None,  0.00, 0.00),  # 1o cadastro (15/10/2025), re-cadastrado acima
    ("2025-08-10", "2025-09-09", 158.11, 112.57, 81.94, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-07-22", "2025-08-09", 158.11, 112.48, 81.85, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-04-10", "2025-05-09", 158.11, 110.96, 80.33, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-05-10", "2025-06-09", 158.11, 109.52, 78.89, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-07-10", "2025-07-21", 158.11, 108.61, 77.98, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-06-10", "2025-07-09", 158.11, 108.45, 77.82, 8.32, 8.32, None, 13.99, 0.00),
    ("2024-11-25", "2024-12-31", 147.96,  91.38, 60.75, 8.32, 8.32, None, 13.99, 0.00),  # cadastro 08/10/2025
    ("2024-11-25", "2024-12-31", 147.96,  91.38, 74.74, 8.32, 8.32, None,  0.00, 0.00),  # 1o cadastro (07/10/2025)
    ("2025-10-10", "2039-07-12", 158.11, 113.27, 82.64, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-09-10", "2039-07-12", 158.11, 113.26, 82.63, 8.32, 8.32, None, 13.99, 0.00),
    ("2025-03-10", "2039-07-12", 158.11, 111.43, 81.45, 8.32, 8.32, None, 13.34, 0.00),  # cadastro 31/03/2025 14:03
    ("2025-03-11", "2039-07-12", 158.11, 111.43, 81.45, 8.32, 8.32, None, 13.34, 0.00),  # cadastro 31/03/2025 14:02 (dup)
    ("2024-08-10", "2039-07-12", 147.96, 109.17, 79.19, 8.32, 8.32, None, 13.34, 0.00),
    ("2024-07-22", "2039-07-12", 147.96, 107.60, 77.62, 8.32, 8.32, None, 13.34, 0.00),
    ("2024-01-10", "2039-07-12", 153.01, 104.82, 74.84, 8.32, 8.32, None, 13.34, 0.00),  # cadastro 29/02/2024
    ("2024-01-10", "2039-07-12", 153.01, 104.82, 75.43, 8.32, 8.32, None, 12.75, 0.00),  # 1o cadastro (09/02/2024)
    ("2023-10-10", "2039-07-12", 153.01, 108.45, 79.06, 8.32, 8.32, None, 12.75, 0.00),  # cadastro 09/11/2023
    ("2022-07-22", "2039-07-12", 145.68, 111.00, 82.30, 8.32, 8.32, None, 12.06, 0.00),  # cadastro 14/10/2022
    ("2022-07-22", "2039-07-12", 145.68, 111.00, 81.41, 8.32, 8.32, None, 12.95, 0.00),  # 1o cadastro (26/07/2022)
    ("2022-06-10", "2039-07-12", 145.68, 102.65, 73.06, 8.32, 8.32, None, 12.95, 0.00),
    ("2022-04-10", "2039-07-12", 145.68, 100.06, 70.47, 8.32, 8.32, None, 12.95, 0.00),
    ("2021-07-22", "2039-07-12", 123.73,  99.84, 70.25, 8.32, 8.32, None, 12.95, 0.00),
    ("2021-08-10", "2039-07-12", 123.73,  82.01, 52.42, 8.32, 8.32, None, 12.95, 0.00),  # cadastro 22/06/2021
    ("2021-08-10", "2039-07-12", 123.73,  82.01, 39.22, 11.09, 11.09, None, 12.95, 7.66),  # 1o cadastro (28/05/2021), split antigo
    ("2021-04-13", "2039-07-12", 123.73,  80.80, 38.01, 11.09, 11.09, None, 12.95, 7.66),  # inicio do contrato (cadastro 29/04/2021)
]


# ---------------------------------------------------------------------------
def validar(dados):
    """soma dos servicos (None tratado como 0) == tarifa_contrato (tolerancia 0,05)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros = ln
            soma = sum(v for v in (frete, mo, md, mcc, dp, outros) if v is not None)
            if abs(soma - tarifa) > 0.05:
                problemas.append(
                    f"item {item} vig {vi}: soma servicos {soma:.2f} "
                    f"!= tarifa_contrato {tarifa:.2f}"
                )
    return problemas


def main():
    problemas = validar(DADOS)
    if problemas:
        print("INCONSISTENCIAS DE SOMA (revisar antes de gravar):")
        for p in problemas:
            print("  -", p)
        raise SystemExit("Abortado: corrija as inconsistencias acima.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS suzano_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE suzano_precos_contratuais (
            item_ferroviario         INTEGER,
            contrato                 TEXT,
            origem                   TEXT,
            origem_nome              TEXT,
            destino                  TEXT,
            destino_nome             TEXT,
            produto                  TEXT,
            vigencia_inicial         TEXT,
            vigencia_final           TEXT,
            valor_tr_antt            REAL,
            tarifa_contrato          REAL,
            frete_rs_t               REAL,
            manobra_origem_rs_t      REAL,
            manobra_destino_rs_t     REAL,
            manobra_conexao_cheio_rs_t REAL,
            direito_passagem_rs_t    REAL,
            outros_servicos_rs_t     REAL,
            fonte                    TEXT
        )
        """
    )
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        for (vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros) in linhas:
            cur.execute(
                """INSERT INTO suzano_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM suzano_precos_contratuais").fetchone()[0]
    print(f"suzano_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
