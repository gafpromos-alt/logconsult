# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da GERDAU
(tabela gerdau_precos_contratuais, minerada dos vídeos F-LINK IMG_0239-0246 e IMG_0492-0522)
ao Painel do Cliente, substituindo os registros curados da GERDAU por dados reais
reajuste-a-reajuste.

A tabela-fonte cobre DUAS razões sociais do grupo ("GERDAU ACOMINAS S/A" e "GERDAU ACOS
LONGOS S.A."), mantidas na mesma tabela (coluna razao_social) e no mesmo cliente="GERDAU"
do Painel — a distinção de razão social fica registrada no campo `cobertura` de cada fluxo
e no rótulo do fluxo quando há mais de um item ferroviário para a mesma rota/produto
(vários pares de itens no lote novo têm tarifas idênticas para o mesmo trajeto, registrados
sob razões sociais/itens diferentes; ver comentários em add_gerdau_precos_contratuais.py).

Para cada fluxo (item ferroviário), usa a vigência MAIS RECENTE como a situação tarifária atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, TETO = Valor TR (ANTT) — vem direto
  da fonte!, frete, acessorias = manobra_origem + manobra_destino, ipoa = acess/frete.
- projeto_acessorias_abertas (PJA): MANOBRA ORIGEM e MANOBRA DESTINO (a abertura que estava
  pendente) — assim o Teto Tarifário da GERDAU sai do modo "portfólio" e ganha deltas simuláveis.

Idempotente: apaga e reinsere só as linhas da GERDAU (nos dois: PJF e PJA). Deve rodar DEPOIS de
add_projetos_clientes.py (que faz DROP+CREATE dessas tabelas) e DEPOIS de add_gerdau_precos_contratuais.py
(que cria a tabela-fonte). É chamado no fim de add_projetos_clientes.py.

Uso:  python3 connect_gerdau_precos.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "GERDAU"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0239-0246, IMG_0492-0522) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0239-0246, IMG_0492-0522) — abertura de manobra reajuste-a-reajuste"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tabela-fonte existe? (senão, não faz nada — evita quebrar rebuild sem a mineração)
    t = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gerdau_precos_contratuais'").fetchone()
    if not t:
        print("  ! gerdau_precos_contratuais não existe — rode add_gerdau_precos_contratuais.py antes. Pulando conexão.")
        con.close()
        return

    # km por rota (enriquecimento) do ipoa_teto, casando GERDAU × origem × destino × produto
    km_por = {}
    for o, d, prod, km in cur.execute(
        """SELECT origem, destino, produto, km_rota FROM ipoa_teto
           WHERE UPPER(cliente) LIKE '%GERDAU%' AND km_rota IS NOT NULL"""):
        km_por.setdefault((o, d, str(prod).upper()), km)

    # vigência mais recente por item (a situação atual)
    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM gerdau_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto, razao_social,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t
               FROM gerdau_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        if row:
            atuais.append(row)

    # 27/jul/2026: usuário definiu regra explícita — "gerdau e ipiranga considerar 1 rota
    # apenas se volume for igual e a diferença de tarifa seja menor que 5%, usar a maior
    # tarifa". Isso REVERTE a decisão anterior (manter linhas separadas por razão social:
    # GERDAU ACOMINAS S/A x GERDAU ACOS LONGOS S.A.) — o usuário quer 1 fluxo só quando a
    # tarifa praticamente coincide, mesmo entre razões sociais diferentes. Volume não é
    # rastreado nesta fonte (fica sempre NULL), então "volume igual" é trivialmente
    # satisfeito aqui (mesmo critério da investigação anterior, achado 24/jul/2026). Diferença
    # relativa: (max-min)/min < 0.05. Mantém o item de tarifa MAIOR; descarta os outros do
    # grupo antes de gerar os fluxos (então nem entram no rótulo "(ITEM n)" abaixo).
    from collections import Counter, defaultdict as _dd
    _por_rota = _dd(list)
    for r in atuais:
        _por_rota[(r[2], r[3], str(r[4]).upper())].append(r)
    atuais_dedup = []
    for _key, _rows in _por_rota.items():
        if len(_rows) < 2:
            atuais_dedup.extend(_rows)
            continue
        _tarifas = [r[9] for r in _rows]  # tarifa_contrato
        _tmin, _tmax = min(_tarifas), max(_tarifas)
        _pct = (_tmax - _tmin) / _tmin if _tmin else None
        if _pct is not None and _pct < 0.05:
            _melhor = max(_rows, key=lambda r: r[9])
            atuais_dedup.append(_melhor)
        else:
            atuais_dedup.extend(_rows)
    atuais = atuais_dedup

    # itens que dividem a mesma rota+produto (tarifas idênticas registradas sob item/razão
    # social diferentes, ex. 40409 x 9687) precisam de rótulo de fluxo distinto — senão
    # entram como duas linhas com o MESMO nome em projeto_fluxo_tarifas.
    contagem_rota = Counter((r[2], r[3], str(r[4]).upper()) for r in atuais)

    # limpa GERDAU nas duas tabelas (não toca nos outros clientes)
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf = npja = 0
    for (it, contrato, o, d, prod, razao_social, vi, vf, tr, tarifa, frete, mo, md) in atuais:
        # item vai DENTRO do produto (antes de origem/destino), nunca depois do destino —
        # o parser de rota do front (fluxoRota()) usa os 2 ÚLTIMOS tokens como destino/origem;
        # "PRODUTO O D (item N)" quebrava isso (rota virava "(item"→"N)"). Mesmo fix aplicado
        # na SELECTA (item 20/jul/2026, ver connect_selecta_etbvtu_itens.py).
        fluxo = f"{prod} {o} {d}"
        if contagem_rota[(o, d, str(prod).upper())] > 1:
            fluxo = f"{prod} (ITEM {it}) {o} {d}"
        acess = (mo or 0) + (md or 0)
        ipoa = (acess / frete) if frete else 0.0
        km = km_por.get((o, d, str(prod).upper()))
        cobertura = f"reajuste a reajuste desde 2023 (item {it}, {contrato}, {razao_social})"
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2), round(acess, 2), round(ipoa, 4),
             round(km, 1) if km else None, None, vf, FONTE_PJF, cobertura))
        npjf += 1
        for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md)):
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  GERDAU conectada: {npjf} fluxos em projeto_fluxo_tarifas, {npja} itens de manobra em "
          f"projeto_acessorias_abertas (fonte: preços contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
