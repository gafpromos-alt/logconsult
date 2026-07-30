# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — corrige o fechamento manobra × acessória nos ÚLTIMOS 4
fluxos curados manualmente (CMOC ×3, SELECTA (retroativo)) que ainda não fechavam depois do
fix de 20/jul/2026 (RAIZEN e demais clientes de portfólio).

Achado: nesses 4 fluxos (fonte "LogConsult (tarifas por cliente).xlsx", os mais antigos da
base, digitados à mão antes desta sessão), o Direito de Passagem estava contabilizado como
item de abertura mas EXCLUÍDO da soma de "acessórias" do cabeçalho — convenção diferente do
resto da base, onde DP conta como acessória (confirmado com o usuário: manter DP SEMPRE como
acessória, uniformizando com o fix já aplicado em RAIZEN/demais clientes via
add_demais_clientes_fluxos_completos.py).

Recalcula acessórias = soma de TODOS os itens de projeto_acessorias_abertas (inclusive DP) e
tarifa_total = frete + acessórias, pros 4 fluxos. Frete e demais campos não mudam.

Idempotente (recalcula sempre a partir da soma atual dos itens — pode rodar de novo sem
efeito colateral se os itens não mudarem). NÃO faz parte do pipeline regular
(add_projetos_clientes.py) porque esses 4 fluxos são curados manualmente e não são
regenerados por nenhum script — script standalone, rodar uma vez (ou de novo se os itens de
abertura desses 4 fluxos forem editados manualmente no futuro).

Uso:  python3 fix_dp_acessoria_curados.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

ALVOS = [
    ("CMOC", "ROCHA EYC IFA"),
    ("CMOC", "ENXOFRE IUF EYC"),
    ("CMOC", "ENXOFRE ICZ EYC"),
    ("SELECTA (retroativo)", "SELECTA (retroativo)"),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    n = 0
    for cliente, fluxo in ALVOS:
        row = cur.execute(
            "SELECT frete, acessorias, tarifa_total FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
            (cliente, fluxo)).fetchone()
        if not row:
            print(f"  ! {cliente} / {fluxo}: não encontrado, pulando.")
            continue
        frete, acess_old, tarifa_old = row
        itens = cur.execute(
            "SELECT valor_rs_t FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
            (cliente, fluxo)).fetchall()
        soma = round(sum(v for (v,) in itens), 2)
        tarifa_novo = round((frete or 0) + soma, 2)
        cur.execute(
            "UPDATE projeto_fluxo_tarifas SET acessorias=?, tarifa_total=? WHERE cliente=? AND fluxo=?",
            (soma, tarifa_novo, cliente, fluxo))
        print(f"  {cliente} / {fluxo}: acessórias {acess_old:.2f}→{soma:.2f}, "
              f"tarifa {tarifa_old:.2f}→{tarifa_novo:.2f} (DP incluído na soma)")
        n += 1
    con.commit()
    print(f"\n{n} fluxo(s) corrigido(s).")
    con.close()


if __name__ == "__main__":
    main()
