#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_aperam_precos_contratuais.py

Cria/recria a tabela `aperam_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos fluxos
ferroviarios da APERAM INOX AMERICA DO SUL S.A, minerado dos videos de tela
do F-LINK (flink.vli.digital, tela "Precos Contratuais").

Uma linha por (item ferroviario x vigencia/reajuste/cadastro).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente.

Fonte: F-LINK Precos Contratuais (IMG_0480-0490.MOV, camera de tela) -
historico de reajuste APERAM. Cliente NOVO no banco (nao existia antes).

Itens minerados (6 itens ferroviarios, 10 videos - alguns itens lidos mais
de uma vez para conferencia cruzada):
  17395 (2x: IMG_0480, IMG_0481) - SR059-2018 - VMR->ECE - PRO SIDERURGICO
  39638 (3x: IMG_0482, IMG_0483, IMG_0485) - A_001_2020_C - VTU->VMR - PELOTAS
  9810  (1x: IMG_0484) - SR059-2018 - VMR->VPN - PRO SIDERURGICO
  40322 (1x: IMG_0486) - SR059-2018 - VMR->VTU - PRO SIDERURGICO
  40324 (1x: IMG_0488) - SR059-2018 - VTU->VMR - PRO SIDERURGICO
  39640 (2x: IMG_0489, IMG_0490) - A_001_2020_C - VTU->VMR - MINERIO FERRO

DISCIPLINA DE LEITURA (ver relatorio da mineracao para detalhes completos):
  - item 17395 tem DUAS series de cadastro coexistentes no F-LINK: uma serie
    "nova" (cadastros fev-jul/2026, vigencia_final 31/12/2029, rota EFVM
    direta com 3 servicos: FRETE/MANOBRA ORIGEM/MANOBRA DESTINO) cujo detalhe
    de servicos NUNCA carregou nos frames capturados (ficou "Carregando" o
    tempo todo, sem tempo de assentar) - por isso frete/manobra/outros dessas
    6 linhas estao gravados como NULL (nao inventados); e uma serie "antiga"
    (vigencia_final 31/12/2027, rota FCA+EFVM com TRANSBORDO DESTINO) que
    carregou por completo e foi validada linha a linha. Ambas as series sao
    mantidas (re-cadastro real, nao redundancia - instrucao de manter ambas).
  - itens 9810, 40322, 40324, 39640 tiveram apenas as 1-7 vigencias mais
    recentes lidas de forma limpa (sem scroll-blur); o restante do historico
    (potencialmente mais vigencias 2023-2025) NAO foi capturado com fidelidade
    e foi OMITIDO (nao inventado) - ver relatorio para a lista de videos e
    trechos com blur descartados.
  - varios itens (17395 antigo, 39638, 9810, 40322, 40324) tem estrutura
    multi-servico (rotas com trecho FCA + trecho EFVM, e/ou TRANSBORDO
    DESTINO). Aqui: frete_rs_t = soma de todos os "FRETE" da linha,
    manobra_origem_rs_t = "MANOBRA ORIGEM", manobra_destino_rs_t =
    "MANOBRA DESTINO", outros_rs_t = "TRANSBORDO DESTINO" (quando existir).
  - re-cadastros (mesma vigencia, cadastros com timestamps diferentes e
    split frete/manobra diferente mas tarifa igual ou proxima) foram mantidos
    como linhas separadas, conforme instrucao.

ATUALIZACAO 30/07/2026: lote adicional IMG_0577-0580.MOV traz 3 itens NOVOS
(12612 ECE->VMR MINERIO FERRO, 39908 VOB->VMR MINERIO FERRO, 40330 VMR->VIC
PRO SIDERURGICO) e uma extensao do historico do item 17395 ("serie antiga",
2 vigencias mais recentes que a ja registrada). Nenhum destes fluxos estava
na lista de pendencias (todos os itens ARCELORMITTAL/MOSAIC/USIMINAS
pendentes ficam nos respectivos arquivos add_*) - dado complementar bonus,
frames limpos, soma validada em todas as linhas.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (videos IMG_0480-0490) - historico de reajuste APERAM"

# ---------------------------------------------------------------------------
# Metadados de cada item ferroviario (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    17395: dict(contrato="SR059-2018", origem="VMR", origem_nome="MARIO CARVALHO",
                destino="ECE", destino_nome="CAPITAO EDUARDO FCA",
                produto="PRO SIDERURGICO", video="IMG_0480.MOV / IMG_0481.MOV"),
    39638: dict(contrato="A_001_2020_C", origem="VTU", origem_nome="TUBARAO",
                destino="VMR", destino_nome="MARIO CARVALHO",
                produto="PELOTAS", video="IMG_0482.MOV / IMG_0483.MOV / IMG_0485.MOV"),
    9810: dict(contrato="SR059-2018", origem="VMR", origem_nome="MARIO CARVALHO",
               destino="VPN", destino_nome="PEDRO NOLASCO",
               produto="PRO SIDERURGICO", video="IMG_0484.MOV"),
    40322: dict(contrato="SR059-2018", origem="VMR", origem_nome="MARIO CARVALHO",
                destino="VTU", destino_nome="TUBARAO",
                produto="PRO SIDERURGICO", video="IMG_0486.MOV"),
    40324: dict(contrato="SR059-2018", origem="VTU", origem_nome="TUBARAO",
                destino="VMR", destino_nome="MARIO CARVALHO",
                produto="PRO SIDERURGICO", video="IMG_0488.MOV"),
    39640: dict(contrato="A_001_2020_C", origem="VTU", origem_nome="TUBARAO",
                destino="VMR", destino_nome="MARIO CARVALHO",
                produto="MINERIO FERRO", video="IMG_0489.MOV / IMG_0490.MOV"),
    # --- lote IMG_0577-0580.MOV (30/07/2026): itens novos ---
    12612: dict(contrato="A_001_2020_C", origem="ECE", origem_nome="CAPITAO EDUARDO FCA",
                destino="VMR", destino_nome="MARIO CARVALHO",
                produto="MINERIO FERRO", video="IMG_0577.MOV"),
    39908: dict(contrato="A_001_2020_C", origem="VOB", origem_nome="OURO BRANCO",
                destino="VMR", destino_nome="MARIO CARVALHO",
                produto="MINERIO FERRO", video="IMG_0578.MOV"),
    40330: dict(contrato="SR059-2018", origem="VMR", origem_nome="MARIO CARVALHO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0580.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t)
# Datas em YYYY-MM-DD. Valores em R$/t. None quando o dado nao carregou a
# tempo na tela (nunca inventado) ou quando o servico nao existe na rota.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 17395 | SR059-2018 | VMR->ECE | PRO SIDERURGICO | IMG_0480/0481.MOV ---
# Serie NOVA (vig_final 2029, rota EFVM direta, 3 servicos) - detalhe de
# servicos nunca carregou nos frames capturados ("Carregando" persistente).
# Serie ANTIGA (vig_final 2027, rota FCA+EFVM+TRANSBORDO DESTINO) - lida e
# validada por completo (soma = tarifa em todas as linhas).
DADOS[17395] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD     outros
    # -- linhas acrescentadas 30/07/2026 (IMG_0579.MOV, serie antiga) --
    ("2026-08-20", "2027-12-31", 49.26,  58.82,  43.32,  0.01,  15.49, 0.00),  # cadastro 17/08/2026 - frete=EFVM41,89+FCA1,43
    ("2026-05-20", "2027-12-31", 49.26,  58.94,  43.40,  0.01,  15.53, 0.00),  # cadastro 19/05/2026 - frete=EFVM41,97+FCA1,43
    ("2026-07-20", "2029-12-31", 113.17, 118.05, None,   None,  None,  None),  # serie nova, servicos nao carregaram
    ("2026-06-20", "2029-12-31", 113.17, 117.98, None,   None,  None,  None),
    ("2026-05-20", "2029-12-31", 113.17, 118.91, None,   None,  None,  None),
    ("2026-04-20", "2029-12-31", 113.17, 119.61, None,   None,  None,  None),
    ("2026-03-20", "2029-12-31", 113.17, 120.21, None,   None,  None,  None),
    ("2026-02-20", "2029-12-31", 113.17, 120.29, None,   None,  None,  None),
    ("2026-04-20", "2027-12-31", 49.26,  58.99,  43.37,  0.01,  15.61, 0.00),  # serie antiga (FCA+EFVM+transbordo)
    ("2026-03-20", "2027-12-31", 49.26,  59.25,  43.64,  0.00,  15.61, 0.00),
    ("2026-02-20", "2027-12-31", 49.26,  59.42,  43.77,  0.00,  15.65, 0.00),  # 1o cadastro (00:33:47)
    ("2026-02-20", "2027-12-31", 49.26,  59.42,  30.80,  13.47, 15.15, 0.00),  # 2o cadastro (00:30:20)
    ("2026-01-20", "2027-12-31", 49.26,  59.29,  43.67,  0.00,  15.62, 0.00),  # 1o cadastro (11:52:15)
    ("2026-01-20", "2027-12-31", 49.26,  59.29,  30.67,  13.47, 15.15, 0.00),  # 2o cadastro (11:40:39)
    ("2025-12-20", "2026-01-31", 47.06,  57.50,  42.35,  0.00,  15.15, 0.00),
]

# --- 39638 | A_001_2020_C | VTU->VMR | PELOTAS | IMG_0482/0483/0485.MOV ---
# Rota EFVM simples (FRETE + MANOBRA ORIGEM + MANOBRA DESTINO, tudo EFVM).
# Historico anterior a 20/01/2025 e o intervalo 20/06/2025-20/09/2025 (exceto
# 20/06 e 20/08) nao foram capturados sem blur - omitidos.
DADOS[39638] = [
    # vig_ini      vig_fim       TR     tarifa  frete   MO     MD     outros
    ("2026-06-20", "2026-12-31", 60.97, 87.97, 53.02, 15.96, 18.99, 0.00),
    ("2026-05-20", "2026-12-31", 60.97, 88.15, 53.13, 15.99, 19.03, 0.00),
    ("2025-09-20", "2025-12-31", 58.24, 87.95, 53.01, 15.95, 18.99, 0.00),
    ("2025-08-20", "2025-12-31", 58.24, 87.63, 52.82, 15.89, 18.92, 0.00),  # cadastro 19/08 22:47:38
    ("2025-08-20", "2025-12-31", 58.24, 87.60, 52.80, 15.89, 18.91, 0.00),  # cadastro 17/08 10:20:40
    ("2025-05-20", "2025-12-31", 58.24, 88.34, 53.25, 16.02, 19.07, 0.00),
    ("2025-04-20", "2025-12-31", 58.24, 89.72, 54.08, 16.27, 19.37, 0.00),
    ("2025-03-20", "2025-12-31", 58.24, 89.86, 54.16, 16.30, 19.40, 0.00),  # cadastro 21:14:41
    ("2025-03-20", "2025-12-31", 58.24, 89.96, 54.26, 16.30, 19.40, 0.00),  # cadastro 20:45:16
    ("2025-02-20", "2025-12-31", 58.24, 88.16, 53.14, 15.99, 19.03, 0.00),
    ("2025-01-01", "2025-12-31", 58.24, 88.00, 53.04, 15.96, 19.00, 0.00),
]

# --- 9810 | SR059-2018 | VMR->VPN | PRO SIDERURGICO | IMG_0484.MOV ---
# Rota EFVM. As 2 vigencias mais recentes (20/06 e 20/05/2026) mostravam
# "Carregando" com valores de tarifa identicos aos de outros itens (efeito de
# cache do F-LINK antes do carregamento real) - descartadas por suspeita de
# dado nao confiavel (nunca inventar). Historico anterior a 20/06/2025 nao
# capturado sem blur - omitido.
DADOS[9810] = [
    # vig_ini      vig_fim       TR     tarifa  frete   MO     MD     outros
    ("2025-11-20", "2025-12-31", 60.43, 76.44, 62.97, 13.47, 0.00,  0.00),
    ("2025-09-20", "2025-12-31", 60.43, 76.49, 61.34, 0.00,  15.15, 0.00),
    ("2025-08-20", "2025-12-31", 60.43, 76.21, 61.11, 0.00,  15.10, 0.00),  # cadastro 18/08 23:12:57
    ("2025-08-20", "2025-12-31", 60.43, 76.21, 62.74, 13.47, 0.00,  0.00),  # cadastro 18/08 23:06:15
    ("2025-07-20", "2025-12-31", 60.43, 76.14, 60.82, 0.00,  15.32, 0.00),  # cadastro 22/07 10:53:54
    ("2025-07-20", "2025-12-31", 60.43, 76.14, 62.67, 13.47, 0.00,  0.00),  # cadastro 20/07 08:20:42
    ("2025-06-20", "2025-12-31", 60.43, 76.19, 61.10, 0.00,  15.09, 0.00),
]

# --- 40322 | SR059-2018 | VMR->VTU | PRO SIDERURGICO | IMG_0486.MOV ---
# Rota EFVM. Apenas as 2 vigencias mais recentes foram lidas de forma limpa
# (video curto, 8,6s); restante do historico omitido.
DADOS[40322] = [
    # vig_ini      vig_fim       TR     tarifa  frete   MO    MD     outros
    ("2026-06-20", "2027-12-31", 69.29, 79.45, 62.88, 0.01, 16.56, 0.00),
    ("2026-05-20", "2027-12-31", 69.29, 79.61, 63.01, 0.01, 16.59, 0.00),
]

# --- 40324 | SR059-2018 | VTU->VMR | PRO SIDERURGICO | IMG_0488.MOV ---
# Rota EFVM (servicos exibidos na ordem FRETE / MANOBRA DESTINO / MANOBRA
# ORIGEM na tela). Apenas as 2 vigencias mais recentes foram lidas (video
# curto, 5,4s); restante do historico omitido.
DADOS[40324] = [
    # vig_ini      vig_fim       TR     tarifa  frete   MO     MD    outros
    ("2026-06-20", "2027-12-31", 69.29, 80.61, 62.74, 17.86, 0.01, 0.00),
    ("2026-05-20", "2027-12-31", 69.29, 80.78, 62.91, 17.86, 0.01, 0.00),
]

# --- 39640 | A_001_2020_C | VTU->VMR | MINERIO FERRO | IMG_0489/0490.MOV ---
# Rota EFVM. Video curto (7,4s e 4,0s) mostrando apenas as 2 vigencias mais
# recentes, confirmadas identicas nas duas gravacoes (IMG_0489 e IMG_0490 -
# leitura redundante do mesmo item, mesmas vigencias). Restante do historico
# omitido. Valores coincidem com os do item 39638 (mesma rota VTU->VMR) -
# aparentemente a APERAM pratica tarifa unificada por rota nesses reajustes
# recentes; mantido conforme lido (nao e erro de leitura, confirmado em 2
# videos e 2 zooms independentes).
DADOS[39640] = [
    # vig_ini      vig_fim       TR     tarifa  frete   MO     MD     outros
    ("2026-06-20", "2026-12-31", 60.97, 87.97, 53.02, 15.96, 18.99, 0.00),
    ("2026-05-20", "2026-12-31", 60.97, 88.15, 53.13, 15.99, 19.03, 0.00),
]

# --- 12612 | A_001_2020_C | ECE->VMR | MINERIO FERRO | IMG_0577.MOV ---
# Item NOVO. Rota intermodal FCA+EFVM: FRETE(FCA)+FRETE(EFVM)+MANOBRA
# ORIGEM(FCA)+MANOBRA DESTINO(EFVM)+TRANSBORDO ORIGEM(FCA). Video de 30,1s
# com muito scroll-blur; so a linha mais recente (cadastro 22/12/2025) foi
# lida sem blur (frame 0577_005). Restante do historico (2024-2025, muitos
# frames com dupla-exposicao) omitido, nao inventado.
DADOS[12612] = [
    ("2025-12-20", "2026-01-31", 76.93, 59.43, 23.32, 17.19, 18.92, 0.00),
]

# --- 39908 | A_001_2020_C | VOB->VMR | MINERIO FERRO | IMG_0578.MOV ---
# Item NOVO. Rota EFVM simples: FRETE + MANOBRA DESTINO + MANOBRA ORIGEM.
# Video curto (4,7s), so a linha mais recente lida (cadastro 22/12/2025).
DADOS[39908] = [
    ("2025-12-20", "2026-01-31", 37.81, 72.65, 37.63, 15.99, 19.03, 0.00),
]

# --- 40330 | SR059-2018 | VMR->VIC | PRO SIDERURGICO | IMG_0580.MOV ---
# Item NOVO. Rota EFVM simples: FRETE + MANOBRA DESTINO + MANOBRA ORIGEM.
# Video curto (6,3s), 2 vigencias lidas sem blur.
DADOS[40330] = [
    ("2026-06-20", "2027-12-31", 34.40, 21.28, 21.27, 0.01, 0.00, 0.00),
    ("2026-05-20", "2027-12-31", 34.40, 21.33, 21.32, 0.01, 0.00, 0.00),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + MD + outros == tarifa_contrato (tolerancia 0,05).
    Linhas com frete=None (servico nao carregou na tela) sao puladas."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            vi, vf, tr, tarifa, frete, mo, md, outros = ln
            if frete is None:
                continue
            soma = (frete or 0) + (mo or 0) + (md or 0) + (outros or 0)
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
    cur.execute("DROP TABLE IF EXISTS aperam_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE aperam_precos_contratuais (
            item_ferroviario     INTEGER,
            contrato              TEXT,
            origem                TEXT,
            origem_nome           TEXT,
            destino               TEXT,
            destino_nome          TEXT,
            produto               TEXT,
            vigencia_inicial      TEXT,
            vigencia_final        TEXT,
            valor_tr_antt         REAL,
            tarifa_contrato       REAL,
            frete_rs_t            REAL,
            manobra_origem_rs_t   REAL,
            manobra_destino_rs_t  REAL,
            outros_rs_t           REAL,
            fonte                 TEXT
        )
        """
    )
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        for (vi, vf, tr, tarifa, frete, mo, md, outros) in linhas:
            cur.execute(
                """INSERT INTO aperam_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, outros, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM aperam_precos_contratuais").fetchone()[0]
    print(f"aperam_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
