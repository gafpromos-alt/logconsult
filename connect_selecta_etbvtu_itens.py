# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — conecta os 2 itens novos da SELECTA ETB→VTU SOJA
(selecta_etbvtu_novos_itens, minerados de IMG_0524/IMG_0525) ao Painel do Cliente.

Substitui o fluxo antigo "SOJA ETB VTU" (item 41226, sem abertura de manobra — o buraco que
o usuário pediu pra preencher) por DOIS fluxos, um por item ferroviário (confirmado com o
usuário: são sub-fluxos distintos, mantém os dois): "SOJA (ITEM 41942) ETB VTU" e
"SOJA (ITEM 41928) ETB VTU". Usa a vigência MAIS RECENTE (jul/2026) de cada item como a
situação tarifária atual — mesmo padrão de connect_gerdau_precos.py.

Volume: a base só tem volume_hist agregado por rota (não por item), então o volume anual
(último ano com realizado, igual volDefaultKt do front) é DIVIDIDO IGUALMENTE entre os 2
itens — aproximação registrada explicitamente no campo `cobertura` de cada fluxo (evita
contar o mesmo volume físico 2x no somatório do resumo).

Idempotente: apaga e reinsere só os 2 fluxos "SOJA (ITEM ...) ETB VTU" da SELECTA (preserva
'SELECTA', 'SELECTA (retroativo)' e as demais rotas do portfólio). Roda DEPOIS de
add_selecta_fluxos_completos.py (que cria o "SOJA ETB VTU" antigo, aqui removido) e DEPOIS
de add_selecta_etbvtu_novos_itens.py (cria a tabela-fonte). Chamado no fim de
add_projetos_clientes.py.

Uso:  python3 connect_selecta_etbvtu_itens.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "SELECTA"
ORIGEM, DESTINO, PRODUTO = "ETB", "VTU", "SOJA"
FLUXO_ANTIGO = f"{PRODUTO} {ORIGEM} {DESTINO}"
FONTE = "F-LINK Preços Contratuais (vídeos IMG_0524/IMG_0525) — vigência mais recente"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='selecta_etbvtu_novos_itens'").fetchone()
    if not t:
        print("  ! selecta_etbvtu_novos_itens não existe — rode add_selecta_etbvtu_novos_itens.py antes. Pulando.")
        con.close()
        return

    itens = [r[0] for r in cur.execute("SELECT DISTINCT item FROM selecta_etbvtu_novos_itens")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item, contrato, vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_efvm, frete_fca, manobra_destino_efvm, manobra_origem_fca, transbordo_origem_fca
               FROM selecta_etbvtu_novos_itens WHERE item=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        if row:
            atuais.append(row)
    if not atuais:
        con.close()
        return

    # volume: último ano com realizado na rota (igual volDefaultKt do front), dividido entre os itens
    vol = cur.execute(
        """SELECT ano, SUM(realizado_ktu) FROM volume_hist
           WHERE UPPER(cliente) LIKE '%SELECTA%' AND origem=? AND destino=? AND realizado_ktu>0
           GROUP BY ano ORDER BY ano DESC LIMIT 1""", (ORIGEM, DESTINO)).fetchone()
    vol_total_kt = vol[1] if vol else None
    vol_por_item_t = round(vol_total_kt / len(atuais) * 1000.0, 0) if vol_total_kt else None

    # remove o fluxo antigo (item 41226, sem manobra) e qualquer versão anterior dos 2 novos
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo LIKE ?",
                (CLIENTE, f"{PRODUTO} (ITEM %) {ORIGEM} {DESTINO}"))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo LIKE ?",
                (CLIENTE, f"{PRODUTO} (ITEM %) {ORIGEM} {DESTINO}"))
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (CLIENTE, FLUXO_ANTIGO))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?", (CLIENTE, FLUXO_ANTIGO))

    npjf = npja = 0
    for (it, contrato, vi, vf, tr, tarifa, f_efvm, f_fca, md, mo, to) in atuais:
        fluxo = f"{PRODUTO} (ITEM {it}) {ORIGEM} {DESTINO}"
        frete = round(f_efvm + f_fca, 2)
        acess = round(md + mo + to, 2)
        ipoa = round(acess / frete, 4) if frete else 0.0
        cobertura = (f"reajuste a reajuste (item {it}, {contrato}) — item distinto de "
                     f"41226 (antigo, sem manobra); volume da rota dividido igualmente entre "
                     f"os {len(atuais)} itens (base não distingue volume por item)")
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, tarifa, round(tr, 2) if tr else None, frete, acess, ipoa,
             None, vol_por_item_t, vf, FONTE, cobertura))
        npjf += 1
        for nome, val in (("Manobra Destino", md), ("Manobra Origem", mo), ("Transbordo Origem", to)):
            if val is not None and val > 0:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, nome, round(val, 2), FONTE))
                npja += 1

    con.commit()
    print(f"  SELECTA ETB→VTU: {npjf} fluxos (itens {', '.join(sorted(itens))}), {npja} itens de "
          f"abertura de manobra — item 41226 antigo (sem manobra) substituído.")
    con.close()


if __name__ == "__main__":
    main()
