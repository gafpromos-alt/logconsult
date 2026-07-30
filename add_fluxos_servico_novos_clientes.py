# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Popula `fluxos_servico` (base do Hub Acessórias / colunas
AO-AD-AOT em "Fluxos por proximidade do teto") com os itens minerados dos vídeos F-LINK para
os 14 clientes trazidos em jul/2026 (USIMINAS 248-338 + GERDAU/ArcelorMittal/IPIRANGA/VIBRA/
RAIZEN/PETRONAC/PETROBAHIA/ALESAT/APERAM/SABBA/CENIBRA/SUZANO/LD CELULOSE 345-523).

ACHADO (18/jul): a aba "Fluxos por proximidade do teto — teto × acessórias × receita" lê a
tabela base de `ipoa_teto` (situação tarifária) e as colunas AO/AD/AOT de `fluxos_servico`
(detalhamento por serviço) — DUAS tabelas que nunca receberam os dados desta mineração (que
foi toda gravada em projeto_fluxo_tarifas/projeto_acessorias_abertas, a base do "Painel do
Cliente"/"Oportunidades", não a do Teto). Por isso os clientes novos apareciam no Teto (já
estavam em ipoa_teto de mineração anterior) mas com AO/AD/AOT vazios.

Este script lê a vigência MAIS RECENTE de cada item nas 14 tabelas `<cliente>_precos_
contratuais` e insere em `fluxos_servico` uma linha por (item x serviço): FRETE, MANOBRA
ORIGEM, MANOBRA DESTINO e, quando existirem, MANOBRA CONEXAO CHEIO / DIREITO DE PASSAGEM /
TRANSBORDO ORIGEM. Campos "outros_rs_t"/"outros_servicos_rs_t" (tipicamente 0,00 ou de
categoria ambígua) NÃO são inseridos — por disciplina de não rotular errado um serviço.

O nome do cliente usado é o MESMO já usado em projeto_fluxo_tarifas/projeto_acessorias_
abertas (para GERDAU, usa razao_social por item — 2 entidades legais distintas) — canon()
normaliza e casa com o cliente já existente em ipoa_teto (quando existe), fazendo o merge em
build_painel.py funcionar automaticamente.

NOTA: PETRONAC, PETROBAHIA e ALESAT não têm NENHUM registro em ipoa_teto (clientes 100% novos,
sem teto/ANTT calculado ainda) — para esses 3, este script ainda assim insere em
fluxos_servico (não custa nada e fica pronto), mas eles NÃO vão aparecer em "Fluxos por
proximidade do teto" até que ipoa_teto also tenha uma linha pra eles (fora do escopo desta
mineração — a view é 100% escopada a ipoa_teto).

Idempotente: apaga e reinsere só as linhas destes 14 clientes em fluxos_servico (usa a lista
de nomes de cliente abaixo).

Uso:  python3 add_fluxos_servico_novos_clientes.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

# tabela-fonte -> (cliente_default, usa_razao_social)
TABELAS = {
    "gerdau":         (None, True),   # cliente vem de razao_social por item
    "usiminas":       ("USIMINAS", False),
    "arcelormittal":  ("ARCELORMITTAL", False),
    "ipiranga":       ("IPIRANGA PRODUTOS DE PETROLEO SA", False),
    "vibra":          ("VIBRA ENERGIA S.A.", False),
    "raizen":         ("RAIZEN COMBUSTIVEIS SA", False),
    "petronac":       ("PETRONAC COMBUSTIVEIS", False),
    "petrobahia":     ("PETROBAHIA S A", False),
    "alesat":         ("ALESAT COMBUSTIVEIS S.A.", False),
    "aperam":         ("APERAM INOX AMERICA DO SUL S.A", False),
    "sabba":          ("PETROLEO SABBA S.A.", False),
    "cenibra":        ("CELULOSE NIPO BRASILEIRA S.A. - CENIBRA", False),
    "suzano":         ("SUZANO", False),   # ver nota em add_suzano_precos_contratuais.py
    "ldcelulose":     ("LD CELULOSE SA", False),
}

CLIENTES_TODOS = [
    "GERDAU ACOMINAS S/A", "GERDAU ACOS LONGOS S.A.", "USIMINAS", "ARCELORMITTAL",
    "IPIRANGA PRODUTOS DE PETROLEO SA", "VIBRA ENERGIA S.A.", "RAIZEN COMBUSTIVEIS SA",
    "PETRONAC COMBUSTIVEIS", "PETROBAHIA S A", "ALESAT COMBUSTIVEIS S.A.",
    "APERAM INOX AMERICA DO SUL S.A", "PETROLEO SABBA S.A.",
    "CELULOSE NIPO BRASILEIRA S.A. - CENIBRA", "SUZANO", "LD CELULOSE SA",
]

# coluna -> nome do serviço em fluxos_servico
SERVICO_COL = {
    "frete_rs_t": "FRETE",
    "manobra_origem_rs_t": "MANOBRA ORIGEM",
    "manobra_destino_rs_t": "MANOBRA DESTINO",
    "manobra_conexao_cheio_rs_t": "MANOBRA CONEXAO CHEIO",
    "direito_passagem_rs_t": "DIREITO DE PASSAGEM",
    "transbordo_origem_rs_t": "TRANSBORDO ORIGEM",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    cur.execute(
        f"DELETE FROM fluxos_servico WHERE cliente IN ({','.join('?' for _ in CLIENTES_TODOS)})",
        CLIENTES_TODOS,
    )

    total = 0
    for tabela, (cliente_default, usa_razao) in TABELAS.items():
        tname = f"{tabela}_precos_contratuais"
        existe = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tname,)
        ).fetchone()
        if not existe:
            print(f"  ! {tname} nao existe, pulando.")
            continue

        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({tname})").fetchall()]
        servico_cols = [c for c in SERVICO_COL if c in cols]
        razao_col = "razao_social" if (usa_razao and "razao_social" in cols) else None
        select_cols = ["item_ferroviario", "origem", "destino", "produto",
                        "vigencia_inicial"] + servico_cols
        if razao_col:
            select_cols.append(razao_col)

        itens = [r[0] for r in cur.execute(f"SELECT DISTINCT item_ferroviario FROM {tname}")]
        n_cliente = 0
        for it in itens:
            row = cur.execute(
                f"""SELECT {','.join(select_cols)} FROM {tname}
                    WHERE item_ferroviario=? ORDER BY vigencia_inicial DESC LIMIT 1""",
                (it,),
            ).fetchone()
            vals = dict(zip(select_cols, row))
            origem, destino, produto = vals["origem"], vals["destino"], vals["produto"]
            cliente = vals.get(razao_col) if razao_col else cliente_default

            for col in servico_cols:
                v = vals.get(col)
                if v is None or v <= 0:
                    continue
                cur.execute(
                    """INSERT INTO fluxos_servico
                       (itens, servicos, ferrovia, tarifa, cliente, origem, destino, produto, microrregiao)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (it, SERVICO_COL[col], "", round(v, 2), cliente, origem, destino, produto, None),
                )
                n_cliente += 1
                total += 1
        print(f"  {tabela}: {n_cliente} linhas de servico inseridas ({len(itens)} itens)")

    con.commit()
    print(f"\nTotal: {total} linhas inseridas em fluxos_servico.")
    print("NOTA: PETRONAC/PETROBAHIA/ALESAT nao aparecerao em 'Fluxos por proximidade do teto' "
          "(view escopada a ipoa_teto, onde esses 3 clientes ainda nao tem nenhuma linha).")
    con.close()


if __name__ == "__main__":
    main()
