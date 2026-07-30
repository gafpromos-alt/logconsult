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
  3 fluxos curados hoje: "CELULOSE VFS VAZ", "TORETE VDD VFS", "TORETE VCS VFS" — nomes
  ROTA-CODIFICADOS desde 30/jul/2026, ver FLUXO_RENAME_CENIBRA em add_projetos_clientes.py
  e a migracao de nomes legados FLUXO_NOME_LEGADO abaixo), faz UPDATE
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
import re
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "CENIBRA"
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_0450/0451/0453/0454/0455/0456) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_0450/0451/0453/0454/0455/0456) — abertura de manobra reajuste-a-reajuste"

# fluxo (nome usado em projeto_fluxo_tarifas) por item ferroviario, e km_rota conhecido
# (de ipoa_teto, quando existir) para enriquecer fluxos novos.
#
# 30/jul/2026 (achado do usuario: "volume dos fluxos de torete nao aparecem na simulacao de
# manobras"): nomes passam a ser ROTA-CODIFICADOS ("PRODUTO ORIGEM DESTINO") — o front
# (fluxoRota) e o build (_fluxo_od/_trios_vol do volume mensal) parseiam a rota pelos 2
# ultimos tokens do NOME; os nomes antigos de 2 tokens ("TORETE VDD"/"TORETE VCS") nao
# parseavam rota nenhuma, entao o volume real da rota nunca casava (0 pra sempre na
# simulacao) e o trio cliente×origem×destino nem entrava no payload de volume do painel.
# Origem/destino por item conforme a fonte F-LINK (add_cenibra_precos_contratuais.py).
# 19330 (retorno): "RETORNO CELULOSE" como produto — parseia a rota VFS→VAZ do item sem
# herdar por prefixo o volume da serie "CELULOSE" da mesma rota (o volume da lane pertence
# ao fluxo de ida; retorno fica honesto-0, mesma convencao "zero e honesto" da base toda).
FLUXO_NOME = {
    19328: "CELULOSE VFS VAZ",     # ja existe (curado) — casa por nome exato
    19332: "TORETE VDD VFS",       # ja existe (curado)
    19334: "TORETE VCS VFS",       # ja existe (curado)
    14399: "FIO MAQUINA VTU EPI",  # novo
    19330: "RETORNO CELULOSE VFS VAZ",  # novo — fluxo de retorno do 19328
}

# migracao de nomes legados (pre-30/jul/2026) → nomes rota-codificados. Roda ANTES do upsert
# pra este connect continuar idempotente rodando standalone contra um banco antigo (sem a
# migracao, o casamento por nome exato falharia e o fluxo seria DUPLICADO via INSERT).
FLUXO_NOME_LEGADO = {
    "CELULOSE VFS vaz": "CELULOSE VFS VAZ",
    "TORETE VDD": "TORETE VDD VFS",
    "TORETE VCS": "TORETE VCS VFS",
    "CELULOSE VFS VAZ (retorno)": "RETORNO CELULOSE VFS VAZ",
}

# 1o token do produto com sinonimos de grafia (mesma convencao do _ftok de
# add_demais_clientes_fluxos_completos.py) — a mineracao F-LINK grava "TORETES" (plural),
# ipoa_teto/planilhas gravam "TORETE"/"TORETE DE MADEIRA" (singular): sem normalizar, o
# enriquecimento de km_rota por rota×produto nunca casava pros toretes.
_PROD_TOK_SINONIMOS = {"TORETES": "TORETE", "PRO": "PRODUTO"}


def _tok1(p):
    tok = re.split(r"[ \-]", str(p or "").upper().strip())[0]
    return _PROD_TOK_SINONIMOS.get(tok, tok)


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

    # migra nomes de fluxo legados (sem rota no nome) pros rota-codificados — ver
    # FLUXO_NOME_LEGADO acima. No-op quando o nome antigo nao existe (banco ja migrado
    # ou recem-recriado por add_projetos_clientes.py, que ja nasce com os nomes novos).
    nmig = 0
    for antigo, novo in FLUXO_NOME_LEGADO.items():
        cur.execute("UPDATE projeto_fluxo_tarifas SET fluxo=? WHERE cliente=? AND fluxo=?",
                    (novo, CLIENTE, antigo))
        nmig += cur.rowcount if cur.rowcount > 0 else 0
        cur.execute("UPDATE projeto_acessorias_abertas SET fluxo=? WHERE cliente=? AND fluxo=?",
                    (novo, CLIENTE, antigo))
    if nmig:
        print(f"  CENIBRA: {nmig} fluxo(s) com nome legado migrado(s) pro nome rota-codificado.")

    # km por rota (enriquecimento), casando CENIBRA x origem x destino x familia de produto
    # (1o token com sinonimo TORETES→TORETE — ver _tok1 acima; produto completo nao casava
    # entre a mineracao F-LINK "TORETES" e o rotulo de ipoa_teto)
    km_por = {}
    for o, d, prod, km in cur.execute(
        """SELECT origem, destino, produto, km_rota FROM ipoa_teto
           WHERE UPPER(cliente) LIKE '%CENIBRA%' AND km_rota IS NOT NULL"""):
        km_por.setdefault((o, d, _tok1(prod)), km)

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
        km = km_por.get((o, d, _tok1(prod)))
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
