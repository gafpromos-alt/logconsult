#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_alesat_precos_contratuais.py

Cria/recria a tabela `alesat_precos_contratuais` no banco analitico (logconsult.db)
com o historico de tarifa reajuste-a-reajuste dos fluxos ferroviarios da
ALESAT COMBUSTIVEIS S.A., minerado dos videos de tela do F-LINK
(flink.vli.digital, tela "Item Ferroviario > Preco", secao "PRECOS CONTRATUAIS").

Uma linha por (item ferroviario x vigencia/reajuste).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente.

Fonte: F-LINK Precos Contratuais (IMG_0426-0437.MOV) - historico de reajuste ALESAT.

COBERTURA / DISCIPLINA DE LEITURA (importante):
- Cada video mostra 1 item ferroviario (cabecalho fixo: cliente/contrato/origem/
  destino/produto), depois rola pela tabela PRECOS CONTRATUAIS que lista, para
  cada re-cadastro: Data Cadastro, Ultima Atualizacao, Vigencia Inicial/Final,
  Valor TR (ANTT), Tarifa Contrato, Desconto/Incremento, Tarifa Faturamento, e a
  quebra de servicos (FRETE, MANOBRA ORIGEM, MANOBRA DESTINO e, em varios itens,
  DIREITO DE PASSAGEM - mapeado aqui para o campo "outros").
- Videos 428 e 429 mostram o MESMO item (39615, PPT->QPM, ALCOOL) - tratados como
  duplicata; dados extraidos de 429 (mais nitido).
- Videos 431 e 432 mostram o MESMO item (18862, QPM->PPN, OLEO DIESEL) - duplicata;
  431 e a fonte primaria, 432 usado apenas para complementar uma vigencia adicional.
- Videos 435 e 436 mostram o MESMO item (18912, PPN->QPM, OLEO DIESEL) - duplicata;
  435 e a fonte primaria, 436 usado para estender a serie ate a vigencia mais antiga
  (2023-09, inicio do contrato).
- Os itens tem HISTORICO DENSO de re-cadastro (varios por mes, as vezes varios no
  mesmo dia). NAO foi transcrita a totalidade das linhas visiveis nos videos -
  cada item tem, tipicamente, dezenas de re-cadastros ao longo de 2023-2026. Aqui
  foram registradas as vigencias que puderam ser lidas com nitidez total (todos os
  campos legiveis) E cuja soma dos servicos bate com a Tarifa Contrato (tolerancia
  R$ 0,05) - cobrindo a vigencia MAIS RECENTE de cada item (necessaria para o
  Painel do Cliente) e uma amostra representativa espalhada por 2023-2026.
- Frames com "scroll-blur" (dupla-exposicao por rolagem rapida) foram descartados
  integralmente - nenhum digito foi inferido/adivinhado a partir deles.
- Nenhuma vigencia foi inventada; onde a leitura ficou ambigua, a linha foi omitida.
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0426-0437.MOV) - historico de reajuste ALESAT"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# item, contrato, origem, origem_nome, destino, destino_nome, produto, video
# ---------------------------------------------------------------------------
FLUXOS = {
    18911: dict(contrato="C_2023_55", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="ALCOOL", video="IMG_0426.MOV"),
    18869: dict(contrato="C_2023_55", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="GASOLINA", video="IMG_0427.MOV"),
    39615: dict(contrato="C_2023_55", origem="PPT", origem_nome="PATIO DE PALMEIRANTES",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="ALCOOL", video="IMG_0429.MOV (duplicata: IMG_0428.MOV)"),
    18915: dict(contrato="C_2023_55", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QAL", destino_nome="PATIO DE ACAILANDIA",
                produto="OLEO DIESEL", video="IMG_0430.MOV"),
    18862: dict(contrato="C_2023_55", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPN", destino_nome="PATIO DE PORTO NACIONAL",
                produto="OLEO DIESEL", video="IMG_0431.MOV (duplicata: IMG_0432.MOV)"),
    18913: dict(contrato="C_2023_55", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="QAL", destino_nome="PATIO DE ACAILANDIA",
                produto="GASOLINA", video="IMG_0433.MOV"),
    39617: dict(contrato="C_2023_55", origem="PPT", origem_nome="PATIO DE PALMEIRANTES",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0434.MOV"),
    18912: dict(contrato="C_2023_55", origem="PPN", origem_nome="PATIO DE PORTO NACIONAL",
                destino="QPM", destino_nome="PONTA DA MADEIRA",
                produto="OLEO DIESEL", video="IMG_0435.MOV (duplicata: IMG_0436.MOV)"),
    39613: dict(contrato="C_2023_55", origem="QPM", origem_nome="PONTA DA MADEIRA",
                destino="PPT", destino_nome="PATIO DE PALMEIRANTES",
                produto="GASOLINA", video="IMG_0437.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete, manobra_origem, manobra_destino, outros)
# Datas em YYYY-MM-DD. Valores em R$/t. "outros" = DIREITO DE PASSAGEM (EFC),
# presente na maioria dos itens (fluxo intermodal EFC+FNS). None quando o
# servico nao aparece no video para aquele item.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 18911 | PPN->QPM | ALCOOL | IMG_0426.MOV ---
# Servicos: FRETE(FNS) + MANOBRA ORIGEM(FNS) + MANOBRA DESTINO(FNS) + DIREITO DE
# PASSAGEM(EFC). Amostra cobrindo 2023-09 (inicio do contrato) a 2026-07 (atual).
DADOS[18911] = [
    # vig_ini      vig_fim       TR       tarifa   frete   MO     MD     outros
    ("2026-07-10", "2026-12-31", 635.41, 135.35, 79.45,  0.00, 44.36, 11.54),
    ("2026-01-10", "2026-01-31", 643.14, 133.93, 59.84, 20.42, 42.61, 11.06),
    ("2025-12-10", "2026-12-31", 643.14, 134.23, 79.17,  0.00, 44.00, 11.06),
    ("2025-12-10", "2025-12-31", 643.14, 134.23, 79.17,  0.00, 44.00, 11.06),  # 2o cadastro
    ("2024-10-15", "2024-10-19", 601.85, 123.99, 50.41, 20.42, 42.61, 10.55),
    ("2024-07-10", "2024-08-31", 601.85, 123.99, 87.56, 12.94, 12.94, 10.55),
    ("2024-01-10", "2024-08-31", 622.39, 127.75, 91.48, 12.94, 12.94, 10.39),
    ("2023-12-10", "2024-08-31", 622.39, 131.13, 94.86, 12.94, 12.94, 10.39),
    ("2023-11-10", "2024-08-31", 622.39, 131.13, 94.86, 12.94, 12.94, 10.39),  # 2o cadastro
    ("2023-10-10", "2024-08-31", 622.39, 128.01, 91.74, 12.94, 12.94, 10.39),
    ("2023-09-10", "2024-08-31", 622.39, 128.01, 91.74, 12.94, 12.94, 10.39),  # 2o cadastro
    ("2023-09-01", "2024-08-31", 622.39, 118.25, 81.98, 12.94, 12.94, 10.39),  # inicio do contrato
]

# --- 18869 | QPM->PPN | GASOLINA | IMG_0427.MOV ---
DADOS[18869] = [
    ("2026-07-10", "2026-12-31", 856.32, 239.32, 163.20, 44.36, 21.26, 10.50),
    ("2025-01-10", "2025-12-31", 811.08, 234.27, 224.66,  0.00,  0.00,  9.61),
    ("2025-02-10", "2025-12-31", 866.72, 236.40, 203.51, 11.64, 11.64,  9.61),
    ("2024-12-10", "2025-12-31", 811.08, 231.80, 198.91, 11.64, 11.64,  9.61),
]

# --- 39615 | PPT->QPM | ALCOOL | IMG_0429.MOV (duplicata: IMG_0428.MOV) ---
DADOS[39615] = [
    ("2026-07-10", "2026-12-31", 506.30, 114.27, 58.37,  0.00, 44.36, 11.54),
    ("2025-11-10", "2025-12-31", 512.46, 112.59, 57.82,  0.00, 43.71, 11.06),
    ("2025-10-10", "2025-12-31", 512.46, 112.68, 57.88,  0.00, 43.74, 11.06),
    ("2025-03-10", "2025-12-31", 512.46, 112.53, 58.29,  0.00, 43.69, 10.55),
    ("2025-01-10", "2025-12-31", 479.56, 111.86, 101.31, 0.00,  0.00, 10.55),
    ("2024-12-10", "2025-12-31", 479.56, 110.69, 57.17,  0.00, 42.97, 10.55),
    ("2024-12-02", "2025-12-31", 479.56, 109.76, 56.60,  0.00, 42.61, 10.55),
]

# --- 18915 | QPM->QAL | OLEO DIESEL | IMG_0430.MOV ---
# Sem DIREITO DE PASSAGEM neste item (so FRETE/MANOBRA ORIGEM/MANOBRA DESTINO, EFC).
DADOS[18915] = [
    ("2026-07-10", "2026-12-31", 168.85, 190.40, 121.22, 44.36, 24.82, None),
    ("2026-06-10", "2026-12-31", 168.85, 190.67, 121.38, 44.43, 24.86, None),
    ("2025-11-10", "2025-12-31", 161.30, 187.60, 119.43, 43.71, 24.46, None),
    ("2025-09-10", "2025-12-31", 161.30, 187.75, 119.52, 43.75, 24.48, None),
    ("2025-09-10", "2025-12-31", 161.30, 187.74, 13.58, 13.58, 160.58, None),  # 2o cadastro (split distinto)
    ("2025-08-10", "2025-12-31", 161.30, 182.71, 13.58, 13.58, 155.55, None),
    ("2025-08-10", "2025-12-31", 161.30, 182.71, 42.57, 23.82, 116.32, None),  # 2o cadastro
    ("2025-07-10", "2025-12-31", 161.30, 182.55, 42.54, 23.80, 116.21, None),
]

# --- 18862 | QPM->PPN | OLEO DIESEL | IMG_0431.MOV (duplicata: IMG_0432.MOV) ---
DADOS[18862] = [
    ("2026-07-10", "2026-12-31", 856.32, 239.32, 161.42, 44.36, 21.26, 12.28),
    ("2025-09-29", "2025-12-31", 866.72, 235.99, 159.50, 43.75, 20.96, 11.78),  # de IMG_0432 (validado)
    ("2024-08-10", "2025-12-31", 811.08, 225.45, 187.06, 13.58, 13.58, 11.23),
]

# --- 18913 | QPM->QAL | GASOLINA | IMG_0433.MOV ---
# Sem DIREITO DE PASSAGEM (so FRETE/MANOBRA ORIGEM/MANOBRA DESTINO, EFC).
DADOS[18913] = [
    ("2026-07-10", "2026-12-31", 168.85, 190.40, 121.22, 44.36, 24.82, None),
    ("2026-02-10", "2026-12-31", 168.85, 188.34, 165.06, 11.64, 11.64, None),
    ("2026-01-10", "2026-01-31", 168.85, 188.39, 119.77, 44.00, 24.62, None),
    ("2025-12-10", "2026-12-31", 161.30, 188.82, 120.20, 44.00, 24.62, None),
    ("2025-11-10", "2025-12-31", 161.30, 187.60, 119.43, 43.71, 24.46, None),
]

# --- 39617 | PPT->QPM | OLEO DIESEL | IMG_0434.MOV ---
DADOS[39617] = [
    ("2026-07-10", "2026-12-31", 682.32, 114.27, 59.38,  0.00, 42.61, 12.28),
    ("2026-06-08", "2026-12-31", 682.32, 115.43, 60.54,  0.00, 42.61, 12.28),
    ("2026-03-08", "2026-12-31", 682.32, 112.75, 57.86,  0.00, 42.61, 12.28),
    ("2026-02-08", "2026-12-31", 682.32, 113.03, 58.14,  0.00, 42.61, 12.28),
    ("2026-01-08", "2026-12-31", 690.61, 113.07, 58.18,  0.00, 42.61, 12.28),
]

# --- 18912 | PPN->QPM | OLEO DIESEL | IMG_0435.MOV (duplicata: IMG_0436.MOV) ---
DADOS[18912] = [
    ("2026-07-10", "2026-12-31", 856.32, 135.35, 80.45,  0.01, 42.61, 12.28),
    ("2026-06-29", "2026-12-31", 856.32, 135.35, 90.99,  0.00, 44.36,  0.00),  # 2o cadastro
    ("2026-08-10", "2026-12-31", 856.32, 135.54, 60.23, 20.42, 42.61, 12.28),
    ("2026-01-09", "2026-01-31", 866.72, 133.93, 70.90, 20.42, 42.61,  0.00),
    ("2025-12-10", "2026-12-31", 866.72, 134.23, 90.23,  0.00, 44.00,  0.00),
    ("2025-11-10", "2025-12-31", 866.72, 133.36, 89.65,  0.00, 43.71,  0.00),
    ("2024-06-04", "2024-08-31", 811.08, 123.99, 96.83, 13.58, 13.58,  0.00),
    ("2023-11-30", "2024-08-31", 838.76, 131.13, 103.97, 13.58, 13.58,  0.00),
    ("2023-09-28", "2024-08-31", 838.76, 128.01, 100.85, 13.58, 13.58,  0.00),
    ("2023-09-04", "2024-08-31", 838.76, 118.25, 80.35, 13.58, 13.58, 10.74),  # inicio do contrato
]

# --- 39613 | QPM->PPT | GASOLINA | IMG_0437.MOV ---
DADOS[39613] = [
    ("2026-07-10", "2026-12-31", 682.32, 216.11, 139.98, 44.37, 21.26, 10.50),
    ("2026-03-10", "2026-12-31", 682.32, 213.23, 133.90, 43.77, 20.98, 14.58),
    ("2026-02-10", "2026-12-31", 682.32, 213.76, 192.05, 11.64,  0.00, 10.07),
    ("2026-01-10", "2026-01-31", 690.61, 213.83, 192.12, 11.64,  0.00, 10.07),
    ("2025-12-10", "2026-12-31", 690.61, 214.31, 139.16, 44.00, 21.08, 10.07),
]


# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + (MD ou 0) + (outros ou 0) == tarifa_contrato (tolerancia 0,05)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            vi, vf, tr, tarifa, frete, mo, md, outros = ln
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
    cur.execute("DROP TABLE IF EXISTS alesat_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE alesat_precos_contratuais (
            item_ferroviario     INTEGER,
            contrato             TEXT,
            origem               TEXT,
            origem_nome          TEXT,
            destino              TEXT,
            destino_nome         TEXT,
            produto              TEXT,
            vigencia_inicial     TEXT,
            vigencia_final       TEXT,
            valor_tr_antt        REAL,
            tarifa_contrato      REAL,
            frete_rs_t           REAL,
            manobra_origem_rs_t  REAL,
            manobra_destino_rs_t REAL,
            outros_rs_t          REAL,
            fonte                TEXT
        )
        """
    )
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        for (vi, vf, tr, tarifa, frete, mo, md, outros) in linhas:
            cur.execute(
                """INSERT INTO alesat_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, outros, FONTE),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM alesat_precos_contratuais").fetchone()[0]
    print(f"alesat_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
