# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da CENIBRA
(tabela cenibra_precos_contratuais, minerada dos videos F-LINK IMG_0450/0453/0454/
0455/0456) ao Painel do Cliente.

NOTA: o item 14844 (PSU-SUZANO->QPM) foi movido para suzano_precos_contratuais /
connect_suzano_precos.py (decisao do usuario, 18/jul) — nao esta mais aqui.

Para cada item ferroviario, usa a vigencia MAIS RECENTE (maior vigencia_inicial) como a
situacao tarifaria atual:
- projeto_fluxo_tarifas (PJF): para itens ja existentes (casados por cliente+fluxo com os
  3 fluxos curados hoje: "CELULOSE VFS vaz", "TORETE VDD", "TORETE VCS"), faz UPDATE
  preservando teto/distancia_km/volume_ano_ktu ja existentes (sao dados do Radar/planilha
  interna que nao vem do F-LINK) e atualizando tarifa_total/frete/acessorias/ipoa/vigencia/
  fonte/cobertura com o dado real reajuste-a-reajuste. Para fluxos novos (14399 VTU->EPI,
  19330 VFS->VAZ retorno), faz INSERT.
- projeto_acessorias_abertas (PJA): abre manobra origem/destino (+ direito de passagem e
  manobra conexao cheio quando existirem) da vigencia mais recente de cada item - a
  "abertura de manobra" que estava pendente (0 linhas antes desta mineracao).

Idempotente: apaga e reinsere so as linhas da CENIBRA (PJA) e faz UPSERT por fluxo (PJF).
Deve rodar DEPOIS de add_projetos_clientes.py (que faz DROP+CREATE dessas tabelas) e DEPOIS
de add_cenibra_precos_contratuais.py (que cria a tabela-fonte).

Uso:  python3 connect_cenibra_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "CENIBRA"
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_0450/0451/0453/0454/0455/0456) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_0450/0451/0453/0454/0455/0456) — abertura de manobra reajuste-a-reajuste"

# fluxo (nome usado em projeto_fluxo_tarifas) por item ferroviario, e km_rota conhecido
# (de ipoa_teto, quando existir) para enriquecer fluxos novos.
FLUXO_NOME = {
    19328: "CELULOSE VFS vaz",   # ja existe (curado) — casa por nome exato
    19332: "TORETE VDD",         # ja existe (curado)
    19334: "TORETE VCS",         # ja existe (curado)
    14399: "FIO MAQUINA VTU EPI",  # novo
    19330: "CELULOSE VFS VAZ (retorno)",  # novo — fluxo de retorno do 19328
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cenibra_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! cenibra_precos_contratuais nao existe — rode add_cenibra_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    # km por rota (enriquecimento), casando CENIBRA x origem x destino x produto
    km_por = {}
    for o, d, prod, km in cur.execute(
        """SELECT origem, destino, produto, km_rota FROM ipoa_teto
           WHERE UPPER(cliente) LIKE '%CENIBRA%' AND km_rota IS NOT NULL"""):
        km_por.setdefault((o, d, str(prod).upper()), km)

    # vigencia mais recente por item
    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM cenibra_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t,
                      manobra_conexao_cheio_rs_t, direito_passagem_rs_t, outros_servicos_rs_t
               FROM cenibra_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

    # limpa acessorias abertas da CENIBRA (nao toca em outros clientes)
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf_upd = npjf_ins = npja = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, mcc, dp, outros) in atuais:
        fluxo = FLUXO_NOME.get(it, f"{prod} {o} {d}")
        acess = sum(v for v in (mo, md, mcc, dp, outros) if v is not None)
        ipoa = (acess / frete) if frete else 0.0
        km = km_por.get((o, d, str(prod).upper()))
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
                 round(km, 1) if km else None, None,
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
                 round(km, 1) if km else None, None, vf, FONTE_PJF, cobertura),
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
    print(f"  CENIBRA conectada: {npjf_upd} fluxos atualizados + {npjf_ins} fluxos novos em "
          f"projeto_fluxo_tarifas, {npja} itens de manobra em projeto_acessorias_abertas "
          f"(fonte: precos contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
