# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da PETRONAC
(tabela petronac_precos_contratuais, minerada dos videos F-LINK IMG_0444-0448) ao Painel
do Cliente.

Para cada fluxo (item ferroviario), usa a vigencia mais recente (por vigencia_inicial) como
a situacao tarifaria atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, TETO=Valor TR (ANTT), frete,
  acessorias = manobra_origem + manobra_destino + direito_passagem, ipoa = acess/frete.
  distancia_km e volume_ano_ktu ficam NULL.
- projeto_acessorias_abertas (PJA): MANOBRA ORIGEM, MANOBRA DESTINO, DIREITO DE PASSAGEM
  como itens abertos, individualmente simulaveis.

Idempotente: apaga e reinsere so as linhas da PETRONAC. Deve rodar DEPOIS de
add_projetos_clientes.py e DEPOIS de add_petronac_precos_contratuais.py.

Uso:  python3 connect_petronac_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "PETRONAC COMBUSTIVEIS"
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_0444-0448) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_0444-0448) — abertura de manobra"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='petronac_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! petronac_precos_contratuais nao existe — rode add_petronac_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM petronac_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, direito_passagem_rs_t
               FROM petronac_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf = npja = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, dp) in atuais:
        fluxo = f"{prod} {o} {d}"
        acess = (mo or 0) + (md or 0) + (dp or 0)
        ipoa = (acess / frete) if frete else 0.0
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2), round(acess, 2), round(ipoa, 4),
             None, None, vf, FONTE_PJF,
             f"vigencia mais recente (item {it}, {contrato}); historico parcial 2023-2027 na tabela-fonte"))
        npjf += 1
        for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md), ("DIREITO DE PASSAGEM", dp)):
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  PETRONAC conectada: {npjf} fluxos em projeto_fluxo_tarifas, {npja} itens de manobra em "
          f"projeto_acessorias_abertas (fonte: precos contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
