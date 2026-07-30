# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da SUZANO
(tabela suzano_precos_contratuais, minerada do video F-LINK IMG_0451, fluxo PSU->QPM) ao
Painel do Cliente.

SUZANO e um cliente novo (0 linhas hoje em projeto_fluxo_tarifas/projeto_acessorias_abertas):
INSERT de 1 fluxo em PJF, com a abertura de manobra origem/destino/direito de passagem em PJA
usando a vigencia MAIS RECENTE (maior vigencia_inicial).

Idempotente: apaga e reinsere so as linhas da SUZANO.
Deve rodar DEPOIS de add_projetos_clientes.py e DEPOIS de add_suzano_precos_contratuais.py.

Uso:  python3 connect_suzano_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "SUZANO"
FONTE_PJF = "F-LINK Precos Contratuais (video IMG_0451) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (video IMG_0451) — abertura de manobra reajuste-a-reajuste"

FLUXO_NOME = {
    14844: "CELULOSE PSU QPM",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='suzano_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! suzano_precos_contratuais nao existe — rode add_suzano_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM suzano_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t,
                      manobra_conexao_cheio_rs_t, direito_passagem_rs_t, outros_servicos_rs_t
               FROM suzano_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf_upd = npjf_ins = npja = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros) in atuais:
        fluxo = FLUXO_NOME.get(it, f"{prod} {o} {d}")
        acess = sum(v for v in (mo, md, mcc, dp, outros) if v is not None)
        ipoa = (acess / frete) if frete else 0.0
        cobertura = f"reajuste a reajuste (item {it}, {contrato})"

        existe = cur.execute(
            "SELECT rowid FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
            (CLIENTE, fluxo),
        ).fetchone()
        if existe:
            cur.execute(
                """UPDATE projeto_fluxo_tarifas
                   SET tarifa_total=?, teto=?, frete=?, acessorias=?, ipoa=?,
                       distancia_km=COALESCE(distancia_km, ?),
                       volume_ano_ktu=COALESCE(volume_ano_ktu, ?),
                       vigencia=?, fonte=?, cobertura=?
                   WHERE cliente=? AND fluxo=?""",
                (round(tarifa, 2), round(tr, 2) if tr else None, round(frete, 2),
                 round(acess, 2), round(ipoa, 4),
                 None, None,
                 vf, FONTE_PJF, cobertura, CLIENTE, fluxo),
            )
            npjf_upd += 1
        else:
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
                 round(frete, 2), round(acess, 2), round(ipoa, 4),
                 None, None, vf, FONTE_PJF, cobertura),
            )
            npjf_ins += 1

        for item_nome, val in (
            ("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md),
            ("MANOBRA CONEXAO CHEIO", mcc), ("DIREITO DE PASSAGEM", dp),
        ):
            if val is not None and val > 0:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  SUZANO conectada: {npjf_upd} fluxos atualizados + {npjf_ins} fluxos novos em "
          f"projeto_fluxo_tarifas, {npja} itens de manobra em projeto_acessorias_abertas "
          f"(fonte: precos contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
