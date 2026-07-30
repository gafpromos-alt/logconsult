# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da LD CELULOSE
(tabela ldcelulose_precos_contratuais, minerada do video F-LINK IMG_0523, item 17429,
fluxo EDC->VAZ) ao Painel do Cliente.

Ja existe hoje 1 fluxo curado ("LD CELULOSE", planilha interna) em projeto_fluxo_tarifas com
teto=325.81 e volume_ano_ktu=330000 e 2 linhas de manobra em projeto_acessorias_abertas
(Manobra Origem=16.28, Manobra Destino=13.17) — os MESMOS valores de manobra encontrados no
video, confirmando a fonte. Usa a vigencia MAIS RECENTE (maior vigencia_inicial) da tabela
minerada para: UPDATE em projeto_fluxo_tarifas (preservando teto/volume_ano_ktu ja existentes,
enriquecendo distancia_km via ipoa_teto quando ainda nulo) e substituicao das linhas de
projeto_acessorias_abertas pelo dado reajuste-a-reajuste real (mesma abertura, agora com fonte
F-LINK em vez de planilha).

Idempotente: apaga e reinsere so as linhas da LD CELULOSE em PJA; faz UPDATE (nao INSERT, pois
o fluxo ja existe) em PJF.

Uso:  python3 connect_ldcelulose_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "LD CELULOSE"
FLUXO = "LD CELULOSE"
FONTE_PJF = "F-LINK Precos Contratuais (video IMG_0523) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (video IMG_0523) — abertura de manobra reajuste-a-reajuste"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ldcelulose_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! ldcelulose_precos_contratuais nao existe — rode add_ldcelulose_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    n = cur.execute("SELECT COUNT(*) FROM ldcelulose_precos_contratuais").fetchone()[0]
    if n == 0:
        print("  ! ldcelulose_precos_contratuais esta vazia. Nada para conectar.")
        con.close()
        return

    row = cur.execute(
        """SELECT item_ferroviario, contrato, origem, destino, produto,
                  vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                  frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t,
                  manobra_conexao_cheio_rs_t, direito_passagem_rs_t, outros_servicos_rs_t
           FROM ldcelulose_precos_contratuais
           ORDER BY vigencia_inicial DESC LIMIT 1"""
    ).fetchone()
    (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros) = row

    km = cur.execute(
        """SELECT km_rota FROM ipoa_teto
           WHERE UPPER(cliente) LIKE '%LD CELULOSE%' AND origem=? AND destino=? AND km_rota IS NOT NULL
           LIMIT 1""",
        (o, d),
    ).fetchone()
    km = km[0] if km else None

    acess = sum(v for v in (mo, md, mcc, dp, outros) if v is not None)
    ipoa = (acess / frete) if frete else 0.0
    cobertura = f"reajuste a reajuste (item {it}, {contrato})"

    existe = cur.execute(
        "SELECT rowid FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
        (CLIENTE, FLUXO),
    ).fetchone()
    if existe:
        cur.execute(
            """UPDATE projeto_fluxo_tarifas
               SET tarifa_total=?, frete=?, acessorias=?, ipoa=?,
                   distancia_km=COALESCE(distancia_km, ?),
                   vigencia=?, fonte=?, cobertura=?
               WHERE cliente=? AND fluxo=?""",
            (round(tarifa, 2), round(frete, 2), round(acess, 2), round(ipoa, 4),
             round(km, 1) if km else None,
             vf, FONTE_PJF, cobertura, CLIENTE, FLUXO),
        )
        npjf = "atualizado"
    else:
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, FLUXO, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2), round(acess, 2), round(ipoa, 4),
             round(km, 1) if km else None, None, vf, FONTE_PJF, cobertura),
        )
        npjf = "inserido"

    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))
    npja = 0
    for item_nome, val in (
        ("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md),
        ("MANOBRA CONEXAO CHEIO", mcc), ("DIREITO DE PASSAGEM", dp),
    ):
        if val is not None and val > 0:
            cur.execute(
                """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                   VALUES (?,?,?,?,?)""",
                (CLIENTE, FLUXO, item_nome, round(val, 2), FONTE_PJA))
            npja += 1

    con.commit()
    print(f"  LD CELULOSE conectada: fluxo {npjf} em projeto_fluxo_tarifas, "
          f"{npja} itens de manobra em projeto_acessorias_abertas (fonte: precos contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
