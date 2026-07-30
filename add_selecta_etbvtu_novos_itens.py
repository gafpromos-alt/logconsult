# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — SELECTA ETB→VTU SOJA: 2 novos itens ferroviários minerados
dos vídeos F-LINK IMG_0524 (item 41942) e IMG_0525 (item 41928), ambos "Preços Contratuais"
da CJ SELECTA S.A., contrato SR0915/13, mesma rota ETB (Term. Integrador Araguari) → VTU
(Tubarão), mesmo produto SOJA — mas dois itens ferroviários DISTINTOS coexistindo, com
tarifas bem diferentes na mesma vigência (jul/2026: R$149,49 vs R$179,38). O item que já
estava na base (41226, tarifa R$200,04, vigência mar/2026) é mais antigo e SEM abertura de
manobra — o buraco que este vídeo veio preencher.

Confirmado com o usuário (20/jul/2026): tratar como 2 sub-fluxos distintos, manter os dois
(não descartar nenhum, não fundir). Cada um vira sua própria linha no Painel do Cliente —
nome do fluxo "SOJA (ITEM <n>) ETB VTU" (o item entra DENTRO do produto, não como sufixo
depois do destino, senão quebra o parser fluxoRota() do front, que assume os 2 últimos
tokens = destino/origem).

Transcrição validada: em cada vigência, frete_efvm + frete_fca + manobra_destino_efvm +
manobra_origem_fca + transbordo_origem_fca == tarifa_contrato exatamente (conferido pra
todas as 10 linhas, tolerância zero) — alta confiança na leitura dos vídeos.

Tabela-fonte: selecta_etbvtu_novos_itens (item×vigência, mesmo padrão de
gerdau_precos_contratuais/usiminas). connect_selecta_etbvtu_itens.py usa a vigência mais
recente de cada item pra popular projeto_fluxo_tarifas/projeto_acessorias_abertas.

Uso:  python3 add_selecta_etbvtu_novos_itens.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

# (item, contrato, vigencia_inicial, vigencia_final, data_cadastro, valor_tr_antt,
#  tarifa_contrato, frete_efvm, frete_fca, manobra_destino_efvm, manobra_origem_fca,
#  transbordo_origem_fca)
LINHAS = [
    # item 41942 — vídeo IMG_0524
    ("41942", "SR0915/13", "2026-07-01", "2026-07-31", "2026-06-30", 257.87, 149.49, 47.50, 57.09, 17.94, 11.96, 15.00),
    ("41942", "SR0915/13", "2026-06-01", "2026-06-30", "2026-05-29", 257.87, 159.36, 51.09, 61.40, 19.12, 12.75, 15.00),
    ("41942", "SR0915/13", "2026-05-01", "2026-05-31", "2026-04-30", 257.87, 159.78, 51.25, 61.58, 19.17, 12.78, 15.00),
    ("41942", "SR0915/13", "2026-04-01", "2026-04-30", "2026-04-29", 257.87, 159.56, 51.17, 61.48, 19.15, 12.76, 15.00),
    # item 41928 — vídeo IMG_0525
    ("41928", "SR0915/13", "2026-07-01", "2026-07-31", "2026-06-30", 257.87, 179.38, 58.36, 70.14, 21.53, 14.35, 15.00),
    ("41928", "SR0915/13", "2026-06-01", "2026-06-30", "2026-05-29", 257.87, 189.24, 61.95, 74.44, 22.71, 15.14, 15.00),
    ("41928", "SR0915/13", "2026-05-01", "2026-05-31", "2026-04-30", 257.87, 189.74, 62.13, 74.66, 22.77, 15.18, 15.00),
    ("41928", "SR0915/13", "2026-04-01", "2026-04-30", "2026-04-29", 257.87, 189.48, 62.03, 74.55, 22.74, 15.16, 15.00),
]

TOL = 0.01


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS selecta_etbvtu_novos_itens")
    cur.execute("""CREATE TABLE selecta_etbvtu_novos_itens (
        item TEXT, contrato TEXT, vigencia_inicial TEXT, vigencia_final TEXT, data_cadastro TEXT,
        valor_tr_antt REAL, tarifa_contrato REAL, frete_efvm REAL, frete_fca REAL,
        manobra_destino_efvm REAL, manobra_origem_fca REAL, transbordo_origem_fca REAL)""")

    n = 0
    for row in LINHAS:
        (item, contrato, vi, vf, dc, tr, tarifa, f_efvm, f_fca, md, mo, to) = row
        soma = round(f_efvm + f_fca + md + mo + to, 2)
        assert abs(soma - tarifa) <= TOL, f"item {item} {vi}: soma {soma} != tarifa {tarifa}"
        cur.execute(
            """INSERT INTO selecta_etbvtu_novos_itens VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", row)
        n += 1
    con.commit()
    print(f"  selecta_etbvtu_novos_itens: {n} vigências (2 itens: 41942 e 41928) — "
          f"validado soma serviços == tarifa contrato em todas as linhas.")
    con.close()


if __name__ == "__main__":
    main()
