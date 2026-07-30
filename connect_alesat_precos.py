# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da ALESAT
(tabela alesat_precos_contratuais, minerada dos videos F-LINK IMG_0426-0437) ao Painel do
Cliente, criando os registros da ALESAT (cliente novo, sem dados curados previos).

Para cada fluxo (item ferroviario), usa a vigencia MAIS RECENTE como a situacao tarifaria atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, TETO = Valor TR (ANTT) — vem direto
  da fonte!, frete, acessorias = manobra_origem + manobra_destino + outros (direito de passagem),
  ipoa = acess/frete. distancia_km e volume_ano_ktu = NULL (sem dado de km/volume nos videos).
- projeto_acessorias_abertas (PJA): MANOBRA ORIGEM, MANOBRA DESTINO e, quando presente,
  DIREITO DE PASSAGEM (a abertura de manobra) — assim o Teto Tarifario da ALESAT sai do modo
  "portfolio" e ganha deltas simulaveis.

Idempotente: apaga e reinsere so as linhas da ALESAT (nos dois: PJF e PJA). Deve rodar DEPOIS de
add_projetos_clientes.py (que faz DROP+CREATE dessas tabelas) e DEPOIS de
add_alesat_precos_contratuais.py (que cria a tabela-fonte).

Uso:  python3 connect_alesat_precos.py   (ou automatico via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "ALESAT COMBUSTIVEIS S.A."
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_0426-0437) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_0426-0437) — abertura de manobra/direito de passagem"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tabela-fonte existe? (senao, nao faz nada — evita quebrar rebuild sem a mineracao)
    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='alesat_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! alesat_precos_contratuais nao existe — rode add_alesat_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    # vigencia mais recente por item (a situacao atual)
    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM alesat_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t
               FROM alesat_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

    # limpa ALESAT nas duas tabelas (nao toca nos outros clientes)
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf = npja = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, outros) in atuais:
        fluxo = f"{prod} {o} {d}"
        acess = (mo or 0) + (md or 0) + (outros or 0)
        ipoa = (acess / frete) if frete else 0.0
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2), round(acess, 2), round(ipoa, 4),
             None, None, vf, FONTE_PJF,
             f"reajuste a reajuste desde 2023 (item {it}, {contrato}) — sem dado de km/volume"))
        npjf += 1
        for item_nome, val in (
            ("MANOBRA ORIGEM", mo),
            ("MANOBRA DESTINO", md),
            ("DIREITO DE PASSAGEM", outros),
        ):
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  ALESAT conectada: {npjf} fluxos em projeto_fluxo_tarifas, {npja} itens de manobra/direito de "
          f"passagem em projeto_acessorias_abertas (fonte: precos contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
