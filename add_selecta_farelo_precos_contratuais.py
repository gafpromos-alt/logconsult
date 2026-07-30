# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — SELECTA FARELO DE SOJA EBJ→IUF: preço contratual minerado
do vídeo F-LINK IMG_0563 ("Preços Contratuais" da CJ SELECTA S.A.), item ferroviário 18421,
contrato SR0915/13 (vigência do contrato 24/11/2017 a 31/12/2038), estação origem EBJ
(Brejo Alegre) → estação destino IUF (TUF), produto FARELO DE SOJA.

Pedido do usuário (24/jul/2026): "lancei as manobras e preços do farelo Selecta no vídeo
563, atualizar no sistema". Rota nova na base — SELECTA não tinha nenhum fluxo de FARELO DE
SOJA em projeto_fluxo_tarifas antes deste vídeo (só SOJA EPP VTU / SOJA ZZB IUF / SOJA ZZB
VTU / SOJA (ITEM 41942/41928) ETB VTU + os 2 curados SELECTA/SELECTA (retroativo)).

Transcrição validada (tolerância zero manobra conexão cheio + frete + manobra destino +
manobra origem + direito de passagem ALLMP + direito de passagem MRS == tarifa contrato):
vigência mais recente (jul/2026): 32,57 + 192,07 + 41,00 + 41,00 + 9,19 + 2,67 = 318,50 ✓.
O vídeo mostra ~20 vigências históricas (jan/2023 a jul/2026, scroll down); só a mais
recente é usada aqui (mesmo padrão de connect_selecta_etbvtu_itens.py / connect_gerdau).

Tabela-fonte: selecta_farelo_precos_contratuais (vigência × serviços, mesmo padrão de
selecta_etbvtu_novos_itens). connect_selecta_farelo_precos.py usa a vigência mais recente
pra popular projeto_fluxo_tarifas/projeto_acessorias_abertas.

Uso:  python3 add_selecta_farelo_precos_contratuais.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

# (vigencia_inicial, vigencia_final, data_cadastro, valor_tr_antt, tarifa_contrato,
#  manobra_conexao_cheio_fca, frete_fca, manobra_destino_fca, manobra_origem_fca,
#  dp_allmp, dp_mrs)
LINHAS = [
    ("2026-07-01", "2026-07-31", "2026-06-30", 216.40, 318.50, 32.57, 192.07, 41.00, 41.00, 9.19, 2.67),
    ("2026-06-01", "2026-06-30", "2026-05-29", 216.40, 318.50, 32.57, 192.07, 41.00, 41.00, 9.19, 2.67),
    ("2026-05-01", "2026-05-31", "2026-04-30", 216.40, 321.90, 32.57, 195.47, 41.00, 41.00, 9.19, 2.67),
]

TOL = 0.01
CONTRATO = "SR0915/13"
ITEM = "18421"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS selecta_farelo_precos_contratuais")
    cur.execute("""CREATE TABLE selecta_farelo_precos_contratuais (
        item TEXT, contrato TEXT, vigencia_inicial TEXT, vigencia_final TEXT, data_cadastro TEXT,
        valor_tr_antt REAL, tarifa_contrato REAL, manobra_conexao_cheio REAL, frete REAL,
        manobra_destino REAL, manobra_origem REAL, dp_allmp REAL, dp_mrs REAL)""")

    n = 0
    for row in LINHAS:
        (vi, vf, dc, tr, tarifa, mcc, frete, md, mo, dpa, dpm) = row
        soma = round(mcc + frete + md + mo + dpa + dpm, 2)
        assert abs(soma - tarifa) <= TOL, f"{vi}: soma {soma} != tarifa {tarifa}"
        cur.execute(
            """INSERT INTO selecta_farelo_precos_contratuais VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ITEM, CONTRATO, vi, vf, dc, tr, tarifa, mcc, frete, md, mo, dpa, dpm))
        n += 1
    con.commit()
    print(f"  selecta_farelo_precos_contratuais: {n} vigências (item {ITEM}, EBJ→IUF FARELO DE "
          f"SOJA) — validado soma serviços == tarifa contrato em todas as linhas.")
    con.close()


if __name__ == "__main__":
    main()
