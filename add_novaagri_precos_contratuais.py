#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_novaagri_precos_contratuais.py

Cria/recria a tabela `novaagri_precos_contratuais` no banco analitico (logconsult.db) com o
historico de tarifa reajuste-a-reajuste de 2 itens ferroviarios da NOVAAGRI INFRA-ESTRUTURA
DE ARM E ESC AGRICOLA S.A. (canon.py -> "NOVA AGRI"), minerados dos videos de tela do F-LINK
(flink.vli.digital, tela "Item Ferroviario > Preco", secao "PRECOS CONTRATUAIS").

Uma linha por (item ferroviario x vigencia inicial), usando SEMPRE a versao mais recente
("Data Cadastro" mais recente) quando a tabela do F-LINK mostrava mais de uma linha para a
mesma vigencia_inicial (o F-LINK acumula correcoes/reclassificacoes — ex.: parte do valor de
Direito de Passagem foi remanejada pra dentro de Frete em correcoes posteriores, sem mudar a
tarifa_contrato total). Quando duas linhas da mesma vigencia tinham tarifa_contrato total
DIFERENTE (nao so reclassificacao de rubrica), ficou a versao de cadastro mais recente.

Fonte: F-LINK Precos Contratuais (IMG_0545.MOV 64s / IMG_0546.MOV 15s) - NOVA AGRI.

Estes 2 itens ja existiam como fluxos "SOJA PPT QPM" / "MILHO PPT QPM" em
projeto_fluxo_tarifas (portfolio completo, modo "replace" em
add_demais_clientes_fluxos_completos.py). Os dados aqui minerados ENRIQUECEM/RECONCILIAM
esses 2 fluxos com a situacao tarifaria real reajuste-a-reajuste (2025-2026), nao criam
fluxos novos:
  - item 39691 (SOJA,  PPT-PATIO DE PALMEIRANTES -> QPM-PONTA DA MADEIRA) == "SOJA PPT QPM"
  - item 41658 (MILHO, PPT-PATIO DE PALMEIRANTES -> QPM-PONTA DA MADEIRA) == "MILHO PPT QPM"

Contrato unico C_2022_33 (vigencia 01/05/2016 a 31/07/2026) para os 2 itens.

Disciplina de mineracao:
  1. Cliente/item/contrato confirmados pelo cabecalho de cada video (Numero do Item
     Ferroviario, Contrato/Acordo, Estacao Origem/Destino, Produto).
  2. So foram gravadas linhas onde TODOS os campos necessarios estavam legiveis e SEM
     ambiguidade — a tabela do F-LINK tem varios trechos com motion-blur/double-exposure
     durante o scroll. Linhas ambiguas ou onde duas versoes conflitavam em valores que nao
     eram simples reclassificacao (ex.: MILHO vigencia 01/12/2025, frete lido ora R$38,13
     ora R$36,12 entre frames) foram OMITIDAS, nunca adivinhadas.
  3. A PRIMEIRA linha do topo da tabela de SOJA (item 39691), com "Data Cadastro"
     30/06/2026 13:51:32, vigencia_inicial 01/07/2026, tarifa_contrato R$235,67 e servicos
     travados em "Carregando" (nunca resolveram, incluindo um TRANSBORDO ORIGEM que nao
     aparece em nenhuma outra linha do historico) foi tratada como registro nao finalizado/
     anomalo e DESCARTADA — a vigencia 01/07/2026 usada e a da linha seguinte (cadastro
     30/06/2026 13:02:21, tarifa_contrato R$190,43, sem Transbordo Origem), consistente com
     a tendencia das vigencias anteriores e adjacentes.
  4. "Vigencia Final" e um campo de UI (date-input) que fica "congelado"/editavel em varios
     frames — NAO foi usado; so vigencia_inicial (texto estatico, confiavel) foi capturada.
  5. Servicos observados: FRETE (FNS), MANOBRA DESTINO (FNS), MANOBRA ORIGEM (FNS), DIREITO
     DE PASSAGEM (EFC). TRANSBORDO ORIGEM so apareceu na linha anomala descartada (regra 3).
  6. Direito de Passagem = R$0,00 em todas as vigencias ate 01/01/2026 (SOJA) / ate a ultima
     vigencia MILHO capturada (01/04/2026 e anteriores tem 14,78 pontualmente — ver dados);
     nao foi "zerado" pelo script, e o valor real observado no F-LINK.
  7. Para o item 41658 (MILHO), o video (IMG_0546.MOV, 15s) e mais curto que o de SOJA e nao
     alcancou a vigencia mais antiga (01/01/2025) nem o intervalo 01/2026-03/2026 — o
     historico de MILHO aqui e PARCIAL (jan/2025 a dez/2025 nao esta completo; ver
     `cobertura` implicita pela ausencia de linhas). O trecho 01/2025-09/2025 mostrou os
     MESMOS valores de SOJA para a mesma vigencia (aparentemente a mesma tabela de tarifa
     contratual se aplicava aos dois produtos nesse periodo no F-LINK) — transcrito como
     visto, sem inferir/copiar deliberadamente.
  8. Vigencia 01/12/2025 do item 41658 (MILHO) foi OMITIDA (ver regra 2 acima).

NAO EXECUTAR sem revisao. A conversa principal revisa, aplica e conecta ao Painel do
Cliente via connect_novaagri_precos.py (que faz UPDATE dos 2 fluxos existentes, nao INSERT).
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Precos Contratuais (IMG_0545-0546.MOV) - historico de reajuste NOVA AGRI"
CONTRATO = "C_2022_33"

# ---------------------------------------------------------------------------
# Metadados de cada item (confirmados no cabecalho de cada video)
# ---------------------------------------------------------------------------
FLUXOS = {
    39691: dict(origem="PPT", origem_nome="PATIO DE PALMEIRANTES", destino="QPM",
                destino_nome="PONTA DA MADEIRA", produto="SOJA", fluxo_curado="SOJA PPT QPM",
                video="IMG_0545.MOV"),
    41658: dict(origem="PPT", origem_nome="PATIO DE PALMEIRANTES", destino="QPM",
                destino_nome="PONTA DA MADEIRA", produto="MILHO", fluxo_curado="MILHO PPT QPM",
                video="IMG_0546.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por item: (vigencia_inicial, tr, tarifa_contrato, manobra_destino, manobra_origem,
#                   frete, direito_passagem_efc)
# Datas em DD/MM/AAAA. Valores em R$/t. Uma linha por vigencia (versao mais recente de
# cadastro quando havia mais de uma no F-LINK).
# ---------------------------------------------------------------------------
DADOS = {}

# --- 39691 | SOJA | PPT -> QPM | IMG_0545.MOV ---
DADOS[39691] = [
    ("01/07/2026", 174.36, 190.43, 22.85, 34.28, 118.52, 14.78),
    ("01/06/2026", 174.36, 185.18, 22.22, 33.33, 114.85, 14.78),
    ("01/05/2026", 174.36, 191.62, 22.99, 34.49, 119.36, 14.78),
    ("01/04/2026", 174.36, 199.22, 23.91, 35.86, 124.67, 14.78),
    ("01/03/2026", 174.36, 171.46, 20.58, 30.86, 105.24, 14.78),
    ("01/02/2026", 174.36, 130.67, 15.68, 23.52, 76.69, 14.78),
    ("01/01/2026", 176.48, 139.08, 16.69, 25.03, 83.18, 14.18),
    ("01/12/2025", 176.48, 139.08, 16.69, 25.03, 97.36, 0.00),
    ("01/11/2025", 176.48, 159.43, 19.13, 28.70, 111.60, 0.00),
    ("01/10/2025", 176.48, 205.80, 24.70, 37.04, 144.06, 0.00),
    ("01/09/2025", 176.48, 221.93, 26.63, 39.95, 155.35, 0.00),
    ("01/08/2025", 176.48, 231.88, 27.83, 41.74, 162.31, 0.00),
    ("01/07/2025", 176.48, 231.68, 27.80, 41.70, 162.18, 0.00),
    ("01/06/2025", 176.48, 222.93, 26.75, 40.13, 156.05, 0.00),
    ("01/05/2025", 176.48, 225.12, 27.01, 40.52, 157.59, 0.00),
    ("01/04/2025", 176.48, 239.63, 28.76, 43.13, 167.74, 0.00),
    ("01/03/2025", 176.48, 240.65, 60.00, 60.00, 120.65, 0.00),
    ("16/02/2025", 176.48, 193.10, 60.00, 60.00, 73.10, 0.00),
    ("01/02/2025", 176.48, 181.11, 60.00, 60.00, 61.11, 0.00),
    ("01/01/2025", 165.15, 165.31, 60.00, 60.00, 45.31, 0.00),
]

# --- 41658 | MILHO | PPT -> QPM | IMG_0546.MOV --- (historico parcial, video mais curto)
DADOS[41658] = [
    ("01/07/2026", 174.36, 190.43, 22.85, 34.28, 118.52, 14.78),
    ("01/06/2026", 174.36, 185.18, 22.22, 33.33, 114.85, 14.78),
    ("01/05/2026", 174.36, 191.62, 22.99, 34.49, 119.36, 14.78),
    ("01/04/2026", 174.36, 199.22, 23.91, 35.86, 124.67, 14.78),
    # 01/12/2025 OMITIDA: frete lido ora R$38,13 ora R$36,12 entre frames (motion-blur),
    # tarifa_contrato (51,60) e demais servicos consistentes, mas o frete e ambiguo.
    ("01/11/2025", 176.48, 65.78, 7.89, 11.84, 46.05, 0.00),
    ("01/10/2025", 176.48, 109.73, 13.17, 19.75, 76.81, 0.00),
    ("01/09/2025", 176.48, 221.93, 26.63, 39.95, 155.35, 0.00),
    ("01/08/2025", 176.48, 231.88, 27.83, 41.74, 162.31, 0.00),
    ("01/07/2025", 176.48, 231.68, 27.80, 41.70, 162.18, 0.00),
    ("01/06/2025", 176.48, 222.93, 26.75, 40.13, 156.05, 0.00),
    ("01/05/2025", 176.48, 225.12, 27.01, 40.52, 157.59, 0.00),
    ("01/04/2025", 176.48, 239.63, 28.76, 43.13, 167.74, 0.00),
    ("01/03/2025", 176.48, 240.65, 60.00, 60.00, 120.65, 0.00),
    ("16/02/2025", 176.48, 193.10, 60.00, 60.00, 73.10, 0.00),
    # video termina aqui (15s) — vigencias 01/01/2025 e 01/02/2025 (sem o dia 16) e
    # 01/2026-03/2026 do item 41658 nao foram capturadas.
]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("DROP TABLE IF EXISTS novaagri_precos_contratuais")
    cur.execute("""
        CREATE TABLE novaagri_precos_contratuais (
            item_ferroviario INTEGER,
            contrato TEXT,
            origem TEXT,
            origem_nome TEXT,
            destino TEXT,
            destino_nome TEXT,
            produto TEXT,
            fluxo_curado TEXT,
            vigencia_inicial TEXT,
            valor_tr_antt REAL,
            tarifa_contrato REAL,
            manobra_destino_rs_t REAL,
            manobra_origem_rs_t REAL,
            frete_rs_t REAL,
            direito_passagem_efc_rs_t REAL,
            fonte TEXT
        )
    """)

    n = 0
    for item, meta in FLUXOS.items():
        for row in DADOS.get(item, []):
            (vi, tr, tarifa, md, mo, frete, dp) = row
            cur.execute(
                """INSERT INTO novaagri_precos_contratuais
                   (item_ferroviario, contrato, origem, origem_nome, destino, destino_nome,
                    produto, fluxo_curado, vigencia_inicial, valor_tr_antt, tarifa_contrato,
                    manobra_destino_rs_t, manobra_origem_rs_t, frete_rs_t,
                    direito_passagem_efc_rs_t, fonte)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, CONTRATO, meta["origem"], meta["origem_nome"], meta["destino"],
                 meta["destino_nome"], meta["produto"], meta["fluxo_curado"], vi, tr, tarifa,
                 md, mo, frete, dp, FONTE))
            n += 1

    con.commit()
    print(f"novaagri_precos_contratuais: {n} linhas inseridas ({len(FLUXOS)} itens ferroviarios).")
    con.close()


if __name__ == "__main__":
    main()
