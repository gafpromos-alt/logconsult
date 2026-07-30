# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da USIMINAS
(tabela usiminas_precos_contratuais, minerada dos videos F-LINK IMG_02XX/03XX.MOV) ao
Painel do Cliente, preenchendo a abertura de manobra origem/destino que faltava.

Ja existem fluxos curados/portfolio em projeto_fluxo_tarifas com teto/distancia_km
preenchidos mas ZERO linhas em projeto_acessorias_abertas (gap de manobra) — pedido do
usuario, 23/jul/2026: "usiminas faltando abertura de manobras".

Cada FLUXO (produto+origem+destino) pode ter varios `item_ferroviario` (linhas de
contrato/vagao distintas para a mesma rota comercial). Para cada item, usa a vigencia
MAIS RECENTE (maior vigencia_inicial), igual ao padrao GERDAU/CMOC/ALZ/AGREX/NOVA AGRI.
Depois, agrega por FLUXO:
  - tarifa_total/frete/valor_tr_antt: MEDIA simples entre os itens do fluxo (cada item e
    uma linha de vagao/contrato distinta da mesma rota comercial — nao ha campo de volume
    por item pra ponderar).
  - manobra origem/destino: só abre no projeto_acessorias_abertas se TODOS os itens do
    fluxo concordam no mesmo par (origem, destino) na vigencia mais recente. Se os itens
    divergem (ex.: alguns dizem 14.85/8.00 e outros 8.00/14.85 pra mesma rota, mesmo
    contrato, mesma vigencia — caso observado em COQUE GROSSO VTU-VIC, itens 19299/19301
    vs 7924/10305/18814/39630), NAO escolhe um valor arbitrariamente: deixa a abertura de
    manobra desse fluxo pendente e sinaliza o conflito em `cobertura` pra confirmacao do
    usuario, mas ainda assim atualiza tarifa/frete/teto do fluxo.

Idempotente: apaga e reinsere so as linhas da USIMINAS (PJA) e faz UPSERT por fluxo (PJF).
Deve rodar DEPOIS de add_projetos_clientes.py e DEPOIS de add_usiminas_precos_contratuais.py.

Uso:  python3 connect_usiminas_precos.py
"""
import pathlib
import sqlite3
from collections import defaultdict

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "USIMINAS"
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_02XX/03XX.MOV) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_02XX/03XX.MOV) — abertura de manobra reajuste-a-reajuste"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='usiminas_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! usiminas_precos_contratuais nao existe — rode add_usiminas_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    # fluxos curados existentes (nome exato) para casar/preservar teto+distancia_km
    curados = {}
    for fluxo, teto, km, vol in cur.execute(
        "SELECT fluxo, teto, distancia_km, volume_ano_ktu FROM projeto_fluxo_tarifas WHERE cliente=?",
        (CLIENTE,),
    ):
        curados[fluxo] = (teto, km, vol)

    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM usiminas_precos_contratuais")]
    latest_by_item = {}
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t
               FROM usiminas_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        latest_by_item[it] = row

    # agrupa por fluxo (produto origem destino)
    by_fluxo = defaultdict(list)
    for it, row in latest_by_item.items():
        (_, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md) = row
        fluxo = f"{str(prod).upper()} {o} {d}"
        by_fluxo[fluxo].append(row)

    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    npjf_upd = npjf_ins = npja = 0
    conflitos = []
    for fluxo, rows in sorted(by_fluxo.items()):
        n = len(rows)
        itens_str = ", ".join(str(r[0]) for r in rows)
        tr_avg = sum(r[7] for r in rows if r[7] is not None) / n
        tarifa_avg = sum(r[8] for r in rows) / n
        frete_avg = sum(r[9] for r in rows) / n
        vf = max(r[6] for r in rows)  # vigencia_final mais distante entre os itens

        pares = sorted(set((r[10], r[11]) for r in rows))
        if len(pares) == 1:
            mo, md = pares[0]
            acess = round((mo or 0) + (md or 0), 2)
            ipoa = (acess / frete_avg) if frete_avg else 0.0
            cobertura = f"reajuste a reajuste (itens {itens_str}, contrato {rows[0][1]})"
        else:
            # conflito genuino entre itens do mesmo fluxo/vigencia — nao escolhe arbitrariamente
            mo = md = None
            acess = None
            ipoa = None
            pares_str = " vs ".join(f"{a:.2f}/{b:.2f}" for a, b in pares)
            cobertura = (f"reajuste a reajuste (itens {itens_str}) — CONFLITO: manobra origem/destino "
                         f"diverge entre itens na mesma vigencia ({pares_str}) — confirmar com o "
                         f"usuario qual valor vigora antes de abrir a manobra")
            conflitos.append((fluxo, itens_str, pares))

        if fluxo in curados:
            teto, km, vol = curados[fluxo]
            if acess is not None:
                cur.execute(
                    """UPDATE projeto_fluxo_tarifas
                       SET tarifa_total=?, teto=COALESCE(teto, ?), frete=?, acessorias=?, ipoa=?,
                           distancia_km=COALESCE(distancia_km, ?),
                           volume_ano_ktu=COALESCE(volume_ano_ktu, ?),
                           vigencia=?, fonte=?, cobertura=?
                       WHERE cliente=? AND fluxo=?""",
                    (round(tarifa_avg, 2), round(tr_avg, 2) if tr_avg else None, round(frete_avg, 2),
                     acess, round(ipoa, 4),
                     km, vol,
                     vf, FONTE_PJF, cobertura, CLIENTE, fluxo),
                )
            else:
                # conflito: atualiza tarifa/frete mas preserva cobertura como pendente/flag,
                # NAO mexe em acessorias (mantém o que já havia, evita sujar o total com um
                # valor de manobra escolhido arbitrariamente)
                cur.execute(
                    """UPDATE projeto_fluxo_tarifas
                       SET tarifa_total=?, teto=COALESCE(teto, ?), frete=?,
                           distancia_km=COALESCE(distancia_km, ?),
                           volume_ano_ktu=COALESCE(volume_ano_ktu, ?),
                           vigencia=?, fonte=?, cobertura=?
                       WHERE cliente=? AND fluxo=?""",
                    (round(tarifa_avg, 2), round(tr_avg, 2) if tr_avg else None, round(frete_avg, 2),
                     km, vol,
                     vf, FONTE_PJF, cobertura, CLIENTE, fluxo),
                )
            npjf_upd += 1
        else:
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (CLIENTE, fluxo, round(tarifa_avg, 2), round(tr_avg, 2) if tr_avg else None,
                 round(frete_avg, 2), acess, round(ipoa, 4) if ipoa is not None else None,
                 None, None, vf, FONTE_PJF, cobertura),
            )
            npjf_ins += 1

        if mo is not None:
            for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md)):
                if val is not None and val > 0:
                    cur.execute(
                        """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                           VALUES (?,?,?,?,?)""",
                        (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                    npja += 1

    con.commit()
    print(f"  USIMINAS conectada: {npjf_upd} fluxos atualizados + {npjf_ins} fluxos novos em "
          f"projeto_fluxo_tarifas, {npja} itens de manobra em projeto_acessorias_abertas "
          f"(fonte: precos contratuais F-LINK).")
    if conflitos:
        print(f"  ! {len(conflitos)} fluxo(s) com CONFLITO de manobra origem/destino entre itens "
              f"— abertura NAO preenchida, precisa confirmacao do usuario:")
        for fluxo, itens_str, pares in conflitos:
            pares_str = " vs ".join(f"{a:.2f}/{b:.2f}" for a, b in pares)
            print(f"      - {fluxo} (itens {itens_str}): {pares_str}")
    con.close()


if __name__ == "__main__":
    main()
