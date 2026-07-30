#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_ldcelulose_precos_contratuais.py

Cria/recria a tabela `ldcelulose_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste do fluxo ferroviario da LD CELULOSE SA, minerado do
video de tela do F-LINK (flink.vli.digital, tela "Item Ferroviario > Preco > PRECOS
CONTRATUAIS").

ATUALIZACAO (18/jul): o usuario confirmou o numero do video real da LD CELULOSE — IMG_0523.MOV
(fora da faixa 345-522 mapeada originalmente). Cliente confirmado no cabecalho: LD CELULOSE SA,
item ferroviario 17429, contrato C_104_2019, vigencia do contrato 21/12/2020 a 31/12/2050,
estacao origem EDC - ESTACAO CELULOSE, estacao destino VAZ - ARACRUZ, produto CELULOSE.
(Nota historica: o video IMG_0453.MOV, apontado no pedido original, na verdade pertence a
CENIBRA — ver nota em add_cenibra_precos_contratuais.py.)

Fluxo intermodal FCA + EFVM: MANOBRA ORIGEM (FCA) + MANOBRA DESTINO (EFVM) + FRETE (EFVM) +
FRETE (FCA). frete_rs_t aqui = soma dos dois fretes (EFVM + FCA), mesmo padrao usado no item
17829 da GERDAU e no item 14399 da CENIBRA.

Uma linha por vigencia/reajuste/cadastro. 17 vigencias lidas com confianca alta, cobrindo
29/11/2022 a 01/07/2026 (video de 55,8s, tabela densa com re-cadastros semanais/quinzenais —
priorizada cobertura ampla ao longo do tempo em vez de exaustao de cada mes; vigencias com
algum valor de servico cortado/ilegivel no frame foram omitidas, nao inventadas: 01/06/2025,
01/09/2024, 01/02/2024 e 01/07/2023 tiveram a leitura da soma completa impossibilitada e nao
entraram na tabela).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa, aplica e conecta ao
Painel do Cliente via connect_ldcelulose_precos.py.

Fonte: F-LINK Precos Contratuais (IMG_0523.MOV).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0523.MOV) - fluxo EDC->VAZ, item 17429"

# ---------------------------------------------------------------------------
# Metadados do item ferroviario (confirmado no cabecalho do video)
# ---------------------------------------------------------------------------
FLUXOS = {
    17429: dict(contrato="C_104_2019", origem="EDC", origem_nome="ESTACAO CELULOSE",
                destino="VAZ", destino_nome="ARACRUZ", produto="CELULOSE",
                video="IMG_0523.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete, manobra_origem, manobra_destino, manobra_conexao_cheio,
#    direito_passagem, outros_servicos)
# Datas em YYYY-MM-DD. Valores em R$/t. None quando o servico nao existe nesse item.
# frete = FRETE(EFVM) + FRETE(FCA) somados; manobra_origem = MANOBRA ORIGEM (FCA);
# manobra_destino = MANOBRA DESTINO (EFVM).
# ---------------------------------------------------------------------------

DADOS = {}

# --- 17429 | EDC->VAZ | CELULOSE | IMG_0523.MOV ---
DADOS[17429] = [
    # vig_ini      vig_fim       TR      tarifa   frete(EFVM+FCA)  mo(FCA)  md(EFVM)  mcc   dp    outros
    ("2026-07-01", "2050-12-31", 335.59, 316.59, round(131.28 + 155.86, 2), 16.28, 13.17, None, None, None),
    ("2026-06-01", "2050-12-31", 335.59, 316.40, round(131.19 + 155.76, 2), 16.28, 13.17, None, None, None),
    ("2026-05-01", "2050-12-31", 335.59, 317.06, round(131.50 + 156.11, 2), 16.28, 13.17, None, None, None),
    ("2026-04-01", "2050-12-31", 335.59, 317.32, round(131.61 + 156.26, 2), 16.28, 13.17, None, None, None),
    ("2026-03-01", "2050-12-31", 335.59, 318.69, round(132.24 + 157.00, 2), 16.28, 13.17, None, None, None),  # cadastro 27/02/2026, frame com dupla-exposicao mas valores estaveis nas 2 camadas
    ("2026-02-01", "2050-12-31", 335.59, 319.61, round(132.66 + 157.50, 2), 16.28, 13.17, None, None, None),
    ("2026-01-01", "2050-12-31", 335.59, 318.91, round(132.34 + 157.12, 2), 16.28, 13.17, None, None, None),  # cadastro 31/12/2025 14:11:55
    ("2025-12-01", "2050-12-31", 335.59, 318.91, round(132.34 + 157.12, 2), 16.28, 13.17, None, None, None),  # cadastro 31/12/2025 09:06:43, vigencia_inicial distinta (mesma tarifa, dado real nao duplicata)
    ("2025-11-01", "2050-12-31", 335.59, 320.87, round(133.24 + 158.18, 2), 16.28, 13.17, None, None, None),
    ("2025-07-01", "2050-12-31", 325.81, 318.68, round(132.24 + 156.99, 2), 16.28, 13.17, None, None, None),
    ("2025-04-01", "2050-12-31", 325.81, 326.49, round(135.81 + 161.23, 2), 16.28, 13.17, None, None, None),
    ("2025-01-01", "2050-12-31", 325.81, 320.22, round(132.94 + 157.83, 2), 16.28, 13.17, None, None, None),
    ("2024-12-01", "2050-12-31", 325.81, 307.09, round(126.94 + 150.70, 2), 16.28, 13.17, None, None, None),  # cadastro 05/12/2024 14:21:19
    ("2024-10-01", "2050-12-31", 325.81, 303.33, round(125.22 + 148.66, 2), 16.28, 13.17, None, None, None),
    ("2024-03-01", "2050-12-31", 312.42, 277.07, round(79.78 + 167.84, 2), 16.28, 13.17, None, None, None),
    ("2023-08-01", "2050-12-31", 335.61, 268.17, round(71.85 + 166.87, 2), 16.28, 13.17, None, None, None),
    ("2022-12-01", "2050-12-20", 335.81, 287.58, round(75.79 + 182.34, 2), 16.28, 13.17, None, None, None),
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
    cur.execute("DROP TABLE IF EXISTS ldcelulose_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE ldcelulose_precos_contratuais (
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
                """INSERT INTO ldcelulose_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM ldcelulose_precos_contratuais").fetchone()[0]
    print(f"ldcelulose_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
