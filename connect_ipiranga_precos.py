# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da IPIRANGA
(tabela ipiranga_precos_contratuais, minerada dos vídeos F-LINK IMG_0373-0404) ao Painel do
Cliente, criando os registros de IPIRANGA em projeto_fluxo_tarifas e
projeto_acessorias_abertas a partir de dados reais reajuste-a-reajuste.

Para cada item ferroviário, usa a vigência de cadastro MAIS RECENTE como a situação
tarifária atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, TETO = Valor TR (ANTT) — vem
  direto da fonte!, frete=frete_rs_t, acessorias = manobra_origem + manobra_destino +
  direito_passagem, ipoa = acessorias/frete. distancia_km e volume_ano_ktu ficam NULL
  (sem essa informação minerada dos vídeos).
- projeto_acessorias_abertas (PJA): MANOBRA ORIGEM, MANOBRA DESTINO e DIREITO DE PASSAGEM
  (quando existirem) — abertura de manobra para simulação no Teto Tarifário.

IPIRANGA é cliente novo (não existia antes no banco): este script apenas INSERE, não
precisa fazer DELETE de nada pré-existente, mas o faz mesmo assim (idempotente) para
poder ser rodado de novo com segurança caso o script de mineração seja re-executado.

Idempotente: apaga e reinsere só as linhas da IPIRANGA (nos dois: PJF e PJA). Deve rodar
DEPOIS de add_projetos_clientes.py (que faz DROP+CREATE dessas tabelas) e DEPOIS de
add_ipiranga_precos_contratuais.py (que cria a tabela-fonte).

Uso:  python3 connect_ipiranga_precos.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "IPIRANGA"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0373-0404) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0373-0404) — abertura de manobra reajuste-a-reajuste"


def _brdate_key(d):
    """Converte 'DD/MM/AAAA' em chave ordenável (AAAA, MM, DD) para achar o cadastro mais recente."""
    if not d:
        return (0, 0, 0)
    dd, mm, aaaa = d.split("/")
    return (int(aaaa), int(mm), int(dd))


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tabela-fonte existe? (senão, não faz nada — evita quebrar rebuild sem a mineração)
    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ipiranga_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! ipiranga_precos_contratuais não existe — rode add_ipiranga_precos_contratuais.py "
              "antes. Pulando conexão.")
        con.close()
        return

    # todas as linhas da tabela-fonte, agrupadas por item
    linhas = cur.execute(
        """SELECT item_ferroviario, contrato, origem, destino, produto,
                  data_cadastro, vigencia_inicial, vigencia_final,
                  valor_tr_antt, tarifa_contrato,
                  frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, direito_passagem_rs_t
           FROM ipiranga_precos_contratuais"""
    ).fetchall()

    por_item = {}
    for row in linhas:
        item = row[0]
        por_item.setdefault(item, []).append(row)

    # vigência com data de CADASTRO mais recente por item (a situação atual)
    # Pente-fino lote 3 (nov/2026): o cadastro mais recente nem sempre é o preço vigente. Item
    # 19402 (OLEO DIESEL PPN→QPM, 1.236 km) tinha como último cadastro um preço de UM MÊS
    # (01/04–30/04/2026, frete R$ 6,33/t) já vencido, enquanto o contrato de 01/03/2026 a
    # 31/12/2027 (frete R$ 95,63/t) continuava valendo. Regra: entre as linhas ainda válidas na
    # data mais recente observada do item, descarta preço de curta duração (<= 45 dias) quando
    # existe contrato longo válido; sem nenhuma válida, cai no cadastro mais recente (antes).
    def _dt(s):
        k = _brdate_key(s)
        return k if k and k[0] > 1900 else None

    def _dias(a, b):
        import datetime as _d
        return (_d.date(*a) - _d.date(*b)).days

    atuais = []
    for item, rows in por_item.items():
        rows_sorted = sorted(rows, key=lambda r: _brdate_key(r[5]), reverse=True)
        ref = max((_dt(r[6]) for r in rows if _dt(r[6])), default=None)
        longos = [r for r in rows
                  if ref and _dt(r[6]) and _dt(r[7]) and _dt(r[7]) >= ref
                  and _dias(_dt(r[7]), _dt(r[6])) > 45]
        if longos:
            atuais.append(sorted(longos, key=lambda r: (_dt(r[6]), _brdate_key(r[5])), reverse=True)[0])
        else:
            atuais.append(rows_sorted[0])

    # 27/jul/2026: usuário definiu regra explícita — "gerdau e ipiranga considerar 1 rota
    # apenas se volume for igual e a diferença de tarifa seja menor que 5%, usar a maior
    # tarifa". Isso substitui o fix de 20/jul/2026 abaixo (que mantinha as 9 rotas duplicadas
    # visíveis com item distinto): agora, quando a tarifa dos itens da mesma rota+produto
    # difere menos de 5% (relativo ao menor valor), colapsa pra 1 fluxo só, mantendo o item
    # de tarifa MAIOR. Volume não é rastreado nesta fonte (fica sempre NULL), então "volume
    # igual" é trivialmente satisfeito aqui (mesmo critério da investigação anterior). Pares
    # com diferença >=5% (ex. item 19402 x 39837 na rota PPN→QPM OLEO DIESEL, ~64% de diff)
    # continuam separados com "(ITEM n)" no rótulo, como antes.
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

    # itens que dividem a mesma rota+produto (vários itens ferroviários pro mesmo trajeto)
    # precisam de rótulo distinto — senão entram como 2 linhas com o MESMO nome em
    # projeto_fluxo_tarifas (achado 20/jul/2026: 9 rotas duplicadas silenciosamente).
    # Item vai DENTRO do produto (nunca depois do destino — quebraria o parser de rota do
    # front, mesmo fix aplicado em connect_gerdau_precos.py e connect_selecta_etbvtu_itens.py).
    contagem_rota = Counter((r[2], r[3], str(r[4]).upper()) for r in atuais)

    # limpa IPIRANGA nas duas tabelas (não toca nos outros clientes)
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf = npja = 0
    for (item, contrato, o, d, prod, data_cad, vi, vf, tr, tarifa,
         frete, mo, md, dp) in atuais:
        fluxo = f"{prod} {o} {d}"
        if contagem_rota[(o, d, str(prod).upper())] > 1:
            fluxo = f"{prod} (ITEM {item}) {o} {d}"
        acess = (mo or 0) + (md or 0) + (dp or 0)
        ipoa = (acess / frete) if frete else 0.0
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2) if frete else None, round(acess, 2), round(ipoa, 4),
             None, None, vf, FONTE_PJF,
             f"reajuste a reajuste desde 2024 (item {item}, {contrato})"))
        npjf += 1
        for item_nome, val in (
            ("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md), ("DIREITO DE PASSAGEM", dp)
        ):
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  IPIRANGA conectada: {npjf} fluxos em projeto_fluxo_tarifas, {npja} itens de manobra/direito "
          f"de passagem em projeto_acessorias_abertas (fonte: preços contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
