# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da RAIZEN
(tabela raizen_precos_contratuais, minerada dos videos F-LINK IMG_0405-0420, exceto 415)
ao Painel do Cliente RAIZEN COMBUSTIVEIS SA.

Para cada item ferroviario, usa a vigencia MAIS RECENTE (maior vigencia_inicial; em caso de
empate, maior data_cadastro) como a situacao tarifaria atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, TETO = Valor TR (ANTT) — vem
  direto da fonte!, frete=frete_rs_t, acessorias = manobra_origem + manobra_destino +
  direito_passagem, ipoa = acessorias/frete. distancia_km e volume_ano_ktu = NULL (sem dado
  de km/volume minerado nos videos).
- projeto_acessorias_abertas (PJA): MANOBRA ORIGEM, MANOBRA DESTINO e (quando existir)
  DIREITO DE PASSAGEM — abertura de manobra reajuste-a-reajuste, mesma logica da GERDAU.

Idempotente: apaga e reinsere so as linhas da RAIZEN (nos dois: PJF e PJA). Deve rodar DEPOIS
de add_projetos_clientes.py (que faz DROP+CREATE dessas tabelas) e DEPOIS de
add_raizen_precos_contratuais.py (que cria a tabela-fonte).

Uso:  python3 connect_raizen_precos.py   (ou automatico via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "RAIZEN"
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_0405-0420) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_0405-0420) — abertura de manobra reajuste-a-reajuste"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tabela-fonte existe? (senao, nao faz nada — evita quebrar rebuild sem a mineracao)
    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='raizen_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! raizen_precos_contratuais nao existe — rode add_raizen_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    # km por rota (enriquecimento, se existir cobertura de ipoa_teto para a RAIZEN)
    km_por = {}
    try:
        for o, d, prod, km in cur.execute(
            """SELECT origem, destino, produto, km_rota FROM ipoa_teto
               WHERE UPPER(cliente) LIKE '%RAIZEN%' AND km_rota IS NOT NULL"""
        ):
            km_por.setdefault((o, d, str(prod).upper()), km)
    except sqlite3.OperationalError:
        pass  # ipoa_teto pode nao existir/nao ter colunas esperadas em todo ambiente

    # vigencia mais recente por item (a situacao atual): maior vigencia_inicial,
    # desempate por maior data_cadastro
    itens = [r[0] for r in cur.execute(
        "SELECT DISTINCT item_ferroviario FROM raizen_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, direito_passagem_rs_t
               FROM raizen_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC, data_cadastro DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

    # limpa RAIZEN nas duas tabelas (nao toca nos outros clientes)
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf = npja = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, dp) in atuais:
        fluxo = f"{prod} {o} {d}"
        acess = (mo or 0) + (md or 0) + (dp or 0)
        ipoa = (acess / frete) if frete else 0.0
        km = km_por.get((o, d, str(prod).upper()))
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2) if frete else None, round(acess, 2), round(ipoa, 4),
             None, None, vf, FONTE_PJF,
             f"reajuste a reajuste desde 2025/2026 (item {it}, {contrato})"))
        npjf += 1
        for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md),
                                ("DIREITO DE PASSAGEM", dp)):
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  RAIZEN conectada: {npjf} fluxos em projeto_fluxo_tarifas, {npja} itens de manobra/passagem em "
          f"projeto_acessorias_abertas (fonte: precos contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
