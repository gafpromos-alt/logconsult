# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Inclui PETRONAC, PETROBAHIA e ALESAT em `ipoa_teto`, a base
de que a aba "Fluxos por proximidade do teto — teto × acessórias × receita" depende
inteiramente (ver nota em add_fluxos_servico_novos_clientes.py: esses 3 clientes não tinham
NENHUMA linha lá, então não apareciam na aba de jeito nenhum, independente de AO/AD/AOT).

Mecânica: o teto ANTT é um valor REGULATÓRIO por rota+produto — não depende do cliente que
embarca. Os 3 clientes novos usam EXATAMENTE as mesmas rotas (QPM/PPN/PPT/QAL) e produtos
(GASOLINA/OLEO DIESEL/ALCOOL) que clientes-irmãos de combustíveis já presentes em ipoa_teto
(VIBRA, RAIZEN, IPIRANGA, ALE, TDC) — confirmado 100% de cobertura (todo item das 3 tabelas-
fonte tem pelo menos 1 match exato de origem+destino+produto num cliente irmão já existente).

Por isso, em vez de recalcular teto/km_rota do zero (risco de divergir da fonte oficial já
usada para os irmãos), este script COPIA teto/km_rota/corredor_vli/ferrovia_fatura do primeiro
match irmão encontrado para cada (origem,destino,produto), e calcula ipoa/total/teto_1
(pct_teto = frete/teto, confirmado batendo com os valores existentes) usando o frete/acessorias
PRÓPRIO de cada cliente (vigência mais recente das tabelas <cliente>_precos_contratuais).

Idempotente: apaga e reinsere só as linhas destes 3 clientes em ipoa_teto.

Uso:  python3 add_ipoa_teto_novos_clientes.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

CLIENTES = {
    "petronac":   "PETRONAC COMBUSTIVEIS",
    "petrobahia": "PETROBAHIA S A",
    "alesat":     "ALESAT COMBUSTIVEIS S.A.",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute(
        f"DELETE FROM ipoa_teto WHERE cliente IN ({','.join('?' for _ in CLIENTES)})",
        list(CLIENTES.values()),
    )

    total_ins = total_sem_match = 0
    for tabela, cliente in CLIENTES.items():
        tname = f"{tabela}_precos_contratuais"
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({tname})").fetchall()]
        acess_cols = [c for c in ("manobra_origem_rs_t", "manobra_destino_rs_t",
                                   "manobra_conexao_cheio_rs_t", "direito_passagem_rs_t")
                      if c in cols]
        select_cols = ["origem", "destino", "produto", "frete_rs_t"] + acess_cols
        itens = [r[0] for r in cur.execute(f"SELECT DISTINCT item_ferroviario FROM {tname}")]
        n_ins = n_sem = 0
        for it in itens:
            row = cur.execute(
                f"""SELECT {','.join(select_cols)}
                    FROM {tname} WHERE item_ferroviario=?
                    ORDER BY vigencia_inicial DESC LIMIT 1""",
                (it,),
            ).fetchone()
            vals = dict(zip(select_cols, row))
            o, d, p, frete = vals["origem"], vals["destino"], vals["produto"], vals["frete_rs_t"]
            acess = sum(v for c in acess_cols if (v := vals[c]) is not None)

            match = cur.execute(
                """SELECT teto, km_rota, corredor_vli, ferrovia_fatura FROM ipoa_teto
                   WHERE origem=? AND destino=? AND produto=? LIMIT 1""",
                (o, d, p),
            ).fetchone()
            if not match:
                n_sem += 1
                continue
            teto, km, corredor, ferrovia = match

            ipoa = (acess / frete) if frete else 0.0
            tot = frete + acess
            teto_1 = (frete / teto) if teto else None

            cur.execute(
                """INSERT INTO ipoa_teto
                   (item, cliente, origem, destino, produto, ipoa, acessorias, frete,
                    teto, teto_1, total, ferrovia_fatura, corredor_vli, km_rota)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (it, cliente, o, d, p, round(ipoa, 6), round(acess, 2), round(frete, 2),
                 teto, teto_1, round(tot, 2), ferrovia, corredor, km),
            )
            n_ins += 1
        print(f"  {tabela}: {n_ins} fluxos inseridos em ipoa_teto"
              + (f", {n_sem} sem match de rota+produto (nao inserido, sem teto de referencia)" if n_sem else ""))
        total_ins += n_ins
        total_sem_match += n_sem

    con.commit()
    print(f"\nTotal: {total_ins} linhas inseridas em ipoa_teto"
          + (f" ({total_sem_match} itens sem match, nao inseridos)" if total_sem_match else " (100% dos itens tinham rota+produto gemea)."))
    con.close()


if __name__ == "__main__":
    main()
