#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_cenibra_precos_contratuais.py

Cria/recria a tabela `cenibra_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste dos fluxos ferroviarios da CELULOSE NIPO BRASILEIRA
S.A. - CENIBRA, minerado dos videos de tela do F-LINK (flink.vli.digital, tela "Item
Ferroviario > Preco > PRECOS CONTRATUAIS").

Uma linha por (item ferroviario x vigencia/reajuste/cadastro).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa, aplica e conecta ao
Painel do Cliente via connect_cenibra_precos.py.

Fonte: F-LINK Precos Contratuais (IMG_0450/0453/0454/0455/0456.MOV).

ATENCAO - achado de mineracao (14/jul): o video IMG_0453.MOV foi rotulado no pedido original
como "LD CELULOSE, contrato C_104_2019, item 19330", mas o cabecalho visivel em TODOS os
frames legiveis desse video mostra CLIENTE = "CELULOSE NIPO BRASILEIRA S.A. - CENIBRA",
CONTRATO = "CENIBRA_2007_2023", ITEM FERROVIARIO = 19330, ESTACAO ORIGEM = VFS - FREDERICO
SELLOW, ESTACAO DESTINO = VAZ - ARACRUZ (ou seja, o fluxo de RETORNO do item 19328). Os
valores tambem batem em ordem de grandeza com o 19328 (mesma rota, sentido invertido) e NAO
com a LD CELULOSE (tarifa atual ~R$325/t, muito acima da faixa ~R$95-103/t vista aqui, exceto
por 1 cadastro anomalo isolado - ver nota abaixo). Por isso o item 19330 foi tratado aqui como
o 6o item da CENIBRA, e NENHUM dado de LD CELULOSE foi encontrado nos videos fornecidos (ver
add_ldcelulose_precos_contratuais.py, que fica vazio por falta de fonte).

ATENCAO 2 (18/jul, decisao do usuario): o item 14844 (PSU-SUZANO -> QPM), embora administrado
sob o contrato guarda-chuva CENIBRA_2007_2023 na tela do F-LINK, foi MOVIDO para uma tabela
propria (suzano_precos_contratuais / connect_suzano_precos.py) por representar Suzano S.A.,
empresa de celulose distinta da CENIBRA no mundo real. Nao esta mais nesta tabela.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0450/0453/0454/0455/0456.MOV) - historico CENIBRA"

# ---------------------------------------------------------------------------
# Metadados de cada item ferroviario (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    19328: dict(contrato="CENIBRA_2007_2023", origem="VAZ", origem_nome="ARACRUZ",
                destino="VFS", destino_nome="FREDERICO SELLOW", produto="CELULOSE",
                video="IMG_0450.MOV"),
    19332: dict(contrato="CENIBRA_2007_2023", origem="VDD", origem_nome="DESEMBARGADOR DRUMOND",
                destino="VFS", destino_nome="FREDERICO SELLOW", produto="TORETES",
                video="IMG_0454.MOV"),
    19334: dict(contrato="CENIBRA_2007_2023", origem="VCS", origem_nome="COSTA LACERDA",
                destino="VFS", destino_nome="FREDERICO SELLOW", produto="TORETES",
                video="IMG_0455.MOV"),
    14399: dict(contrato="CENIBRA_2007_2023", origem="VTU", origem_nome="TUBARAO",
                destino="EPI", destino_nome="PARQUE INDUSTRIAL", produto="FIO MAQUINA",
                video="IMG_0456.MOV"),
    19330: dict(contrato="CENIBRA_2007_2023", origem="VFS", origem_nome="FREDERICO SELLOW",
                destino="VAZ", destino_nome="ARACRUZ", produto="CELULOSE",
                video="IMG_0453.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete, manobra_origem, manobra_destino, manobra_conexao_cheio,
#    direito_passagem, outros_servicos)
# Datas em YYYY-MM-DD. Valores em R$/t. None quando o servico nao existe nesse item.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 19328 | VAZ->VFS | CELULOSE | IMG_0450.MOV ---
# Fluxo simples EFVM: FRETE + MANOBRA DESTINO + MANOBRA ORIGEM + MANOBRA CONEXAO CHEIO.
# Video termina em scroll-blur apos 19/03/2024 (nao ha dado limpo mais antigo).
DADOS[19328] = [
    # vig_ini      vig_fim       TR      tarifa   frete    mo     md     mcc    dp    outros
    ("2026-04-01", "2031-04-01", 79.29, 101.06, 73.20, 14.72, 13.14, 0.00, None, None),
    ("2025-05-01", "2031-04-01", 75.74, 101.46, 71.51, 15.82, 14.13, 0.00, None, None),
    ("2025-04-01", "2031-04-01", 75.74, 103.19, 72.73, 16.09, 14.37, 0.00, None, None),
    ("2025-03-01", "2031-04-01", 75.74,  97.74, 68.89, 15.24, 13.61, 0.00, None, None),
    ("2024-11-01", "2031-04-01", 72.30,  95.40, 67.24, 14.88, 13.28, 0.00, None, None),
    ("2024-10-01", "2031-04-01", 72.30,  94.39, 66.53,  0.00, 13.14, 14.72, None, None),  # split atipico (MO/MCC trocados na tela)
    ("2024-04-01", "2031-04-01", 72.30, 102.02, 66.52, 14.72, 13.14, 7.64, None, None),
    ("2024-04-01", "2031-04-01", 72.30, 102.02, 65.89, 14.98, 13.38, 7.77, None, None),  # 2o cadastro (22/04)
    ("2024-03-01", "2031-04-01", 72.30, 103.86, 67.73, 14.98, 13.38, 7.77, None, None),
]

# --- 14844 | PSU->QPM | CELULOSE | IMG_0451.MOV ---
# MOVIDO para suzano_precos_contratuais (decisao do usuario, 18/jul) — ver nota no topo
# do arquivo. Nao mineramos de novo, apenas realocamos.

# --- 19332 | VDD->VFS | TORETES | IMG_0454.MOV ---
DADOS[19332] = [
    # vig_ini      vig_fim       TR      tarifa   frete   mo    md    mcc  dp    outros
    ("2026-04-01", "2031-04-01", 42.27, 45.10, 28.74, 8.18, 8.18, None, None, None),
    ("2026-02-01", "2031-04-01", 42.27, 45.27, 28.85, 8.21, 8.21, None, None, None),
    ("2026-01-01", "2031-04-01", 42.27, 45.27, 28.85, 8.21, 8.21, None, None, None),
    ("2025-12-01", "2031-04-01", 40.38, 45.27, 28.85, 8.21, 8.21, None, None, None),
    ("2025-05-01", "2031-04-01", 40.38, 45.27, 28.85, 8.21, 8.21, None, None, None),
    ("2025-04-01", "2031-04-01", 40.38, 46.05, 29.35, 8.35, 8.35, None, None, None),
    ("2025-03-01", "2031-04-01", 40.38, 43.62, 27.80, 7.91, 7.91, None, None, None),
    ("2024-11-01", "2031-04-01", 38.55, 42.57, 27.13, 7.72, 7.72, None, None, None),
    ("2024-10-01", "2031-04-01", 38.55, 42.12, 26.84, 7.64, 7.64, None, None, None),
    ("2024-04-01", "2031-04-01", 38.55, 42.12, 26.84, 7.64, 7.64, None, None, None),
    ("2024-04-01", "2031-04-01", 38.55, 42.12, 26.58, 7.77, 7.77, None, None, None),  # 2o cadastro (12/04)
    ("2024-03-01", "2031-04-01", 38.55, 42.87, 27.33, 7.77, 7.77, None, None, None),
]

# --- 19334 | VCS->VFS | TORETES | IMG_0455.MOV ---
# Nota: 1 vigencia (30/04/2025, cadastro 15:51:25/15:51:48) apareceu com grafismo
# duplicado/dupla-exposicao no frame e frete/manobra nao puderam ser lidos com
# confianca - omitida (ver relatorio da mineracao).
DADOS[19334] = [
    # vig_ini      vig_fim       TR      tarifa   frete   mo     md    mcc  dp    outros
    ("2026-04-01", "2031-04-01", 47.59, 63.82, 34.98, 20.66, 8.18, None, None, None),
    ("2026-02-01", "2031-04-01", 47.59, 64.07, 35.12, 20.74, 8.21, None, None, None),
    ("2026-01-01", "2031-04-01", 47.59, 64.07, 35.12, 20.74, 8.21, None, None, None),
    ("2025-12-01", "2031-04-01", 45.47, 64.07, 35.12, 20.74, 8.21, None, None, None),
    ("2025-04-01", "2031-04-01", 45.47, 65.17, 35.72, 21.10, 8.35, None, None, None),
    ("2025-03-01", "2031-04-01", 45.47, 61.73, 33.83, 19.99, 7.91, None, None, None),
    ("2024-11-01", "2031-04-01", 43.40, 60.25, 33.02, 19.51, 7.72, None, None, None),
    ("2024-10-01", "2031-04-01", 43.40, 59.61, 32.67, 19.30, 7.64, None, None, None),
    ("2024-04-01", "2031-04-01", 43.40, 59.61, 32.67, 19.30, 7.64, None, None, None),
    ("2024-04-01", "2031-04-01", 43.40, 59.61, 32.19, 19.65, 7.77, None, None, None),  # 2o cadastro (12/04)
    ("2024-03-01", "2031-04-01", 43.40, 60.68, 33.26, 19.65, 7.77, None, None, None),
]

# --- 14399 | VTU->EPI | FIO MAQUINA | IMG_0456.MOV ---
# Fluxo intermodal FCA + EFVM: MANOBRA DESTINO(FCA) + MANOBRA ORIGEM(EFVM) + FRETE(FCA) +
# FRETE(EFVM). frete_rs_t aqui = soma dos dois fretes (FCA 3,81 + EFVM 78,94), seguindo o
# mesmo padrao do item 17829 da GERDAU. Video de 5,5s so revela UMA vigencia limpa antes
# do scroll-blur final - nao ha historico adicional disponivel nesta fonte.
DADOS[14399] = [
    # vig_ini      vig_fim       TR      tarifa   frete          mo(EFVM) md(FCA) mcc  dp   outros
    ("2026-07-20", "2027-12-31", 87.35, 110.45, round(3.81 + 78.94, 2), 14.37, 13.33, None, None, None),
]

# --- 19330 | VFS->VAZ | CELULOSE | IMG_0453.MOV ---
# Fluxo de RETORNO do 19328 (mesma rota, sentido invertido). Ver nota no topo do arquivo
# sobre a divergencia com o rotulo original do pedido ("LD CELULOSE").
# 1 cadastro (30/06/2026, vigencia 01/07/2026-31/12/2050, TR R$335,59, tarifa R$316,59) foi
# OMITIDO: a quebra de servicos (Frete/Manobra Origem/Manobra Destino, ferrovias FCA+EFVM)
# nunca terminou de carregar em nenhum frame do video ("Carregando" travado) - impossivel
# validar a soma, e os valores destoam fortemente do padrao do fluxo (~R$95-103/t) e da
# vigencia do contrato (01/04/2021 a 01/04/2031) - pode ser um cadastro-teste/erro na fonte.
DADOS[19330] = [
    # vig_ini      vig_fim       TR      tarifa   frete   mo     md    mcc   dp    outros
    ("2026-04-01", "2031-04-01", 79.29, 101.06, 71.23, 15.76, 14.07, 0.00, None, None),
    ("2025-05-01", "2031-04-01", 75.74, 101.46, 71.51, 15.82, 14.13, 0.00, None, None),
    ("2025-04-01", "2031-04-01", 75.74, 103.19, 72.73, 16.09, 14.37, 0.00, None, None),
    ("2025-03-01", "2031-04-01", 75.74,  97.74, 68.89, 15.24, 13.61, 0.00, None, None),
    ("2024-11-01", "2031-04-01", 72.30,  95.40, 67.24, 14.88, 13.28, 0.00, None, None),
    ("2024-10-01", "2031-04-01", 72.30,  94.39, 66.53, 14.72, 13.14, 0.00, None, None),
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
    cur.execute("DROP TABLE IF EXISTS cenibra_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE cenibra_precos_contratuais (
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
                """INSERT INTO cenibra_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM cenibra_precos_contratuais").fetchone()[0]
    print(f"cenibra_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
