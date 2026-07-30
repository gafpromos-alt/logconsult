# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da VIBRA
ENERGIA S.A. (tabela vibra_precos_contratuais, minerada dos vídeos F-LINK
IMG_0346-0348, IMG_0352, IMG_0354-0371) ao Painel do Cliente.

VIBRA é cliente NOVO no banco (criado nesta mineração) — não há registros
curados a substituir; este script apenas POPULA projeto_fluxo_tarifas e
projeto_acessorias_abertas para VIBRA a partir da tabela-fonte.

Para cada fluxo (item ferroviário), usa a vigência MAIS RECENTE como a situação
tarifária atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, teto=Valor TR (ANTT)
  — vem direto da fonte —, frete=frete_rs_t, acessorias=manobra_origem+
  manobra_destino+outros(direito de passagem), ipoa=acessorias/frete.
  distancia_km e volume_ano_ktu ficam NULL (sem dado de km/volume minerado
  nos vídeos para VIBRA — ao contrário da GERDAU, não há tabela ipoa_teto
  com km_rota para cruzar).
- projeto_acessorias_abertas (PJA): abre MANOBRA ORIGEM, MANOBRA DESTINO e,
  quando existir, DIREITO DE PASSAGEM — a abertura de manobra que estava
  pendente, dando ao Teto Tarifário da VIBRA deltas simuláveis desde já.

Idempotente: apaga e reinsere só as linhas da VIBRA (nos dois: PJF e PJA), não
toca em outros clientes. Deve rodar DEPOIS de add_projetos_clientes.py (que faz
DROP+CREATE dessas tabelas) e DEPOIS de add_vibra_precos_contratuais.py (que
cria a tabela-fonte).

Uso:  python3 connect_vibra_precos.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "VIBRA"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0346-0348, IMG_0352, IMG_0354-0371) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0346-0348, IMG_0352, IMG_0354-0371) — abertura de manobra/direito de passagem"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tabela-fonte existe? (senão, não faz nada — evita quebrar rebuild sem a mineração)
    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='vibra_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! vibra_precos_contratuais não existe — rode add_vibra_precos_contratuais.py antes. Pulando conexão.")
        con.close()
        return

    # projeto_fluxo_tarifas / projeto_acessorias_abertas existem? (dependem de add_projetos_clientes.py)
    for tabela in ("projeto_fluxo_tarifas", "projeto_acessorias_abertas"):
        if not cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
        ).fetchone():
            print(f"  ! {tabela} não existe — rode add_projetos_clientes.py antes. Pulando conexão.")
            con.close()
            return

    # vigência mais recente por item (a situação atual)
    itens = [r[0] for r in cur.execute(
        "SELECT DISTINCT item_ferroviario FROM vibra_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t
               FROM vibra_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        if row:
            atuais.append(row)

    # itens que dividem a mesma rota+produto (ex. 15686/8036, mesma lane QPM->QMA
    # OLEO DIESEL, itens/videos diferentes) precisam de rótulo de fluxo distinto —
    # senão entram como duas linhas com o MESMO nome em projeto_fluxo_tarifas.
    from collections import Counter
    contagem_rota = Counter((r[2], r[3], str(r[4]).upper()) for r in atuais)

    # limpa VIBRA nas duas tabelas (não toca nos outros clientes) — idempotente
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf = npja = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, outros) in atuais:
        fluxo = f"{prod} {o} {d}"
        if contagem_rota[(o, d, str(prod).upper())] > 1:
            fluxo = f"{fluxo} (item {it})"
        acess = (mo or 0) + (md or 0) + (outros or 0)
        ipoa = (acess / frete) if frete else 0.0
        cobertura = f"reajuste a reajuste (item {it}, {contrato}), vigência atual {vi}"
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2) if frete else None, round(acess, 2), round(ipoa, 4),
             None, None, vf, FONTE_PJF, cobertura))
        npjf += 1
        for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md),
                                ("DIREITO DE PASSAGEM", outros)):
            if val:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  VIBRA conectada: {npjf} fluxos em projeto_fluxo_tarifas, {npja} itens de manobra/direito "
          f"de passagem em projeto_acessorias_abertas (fonte: preços contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
