# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — SELECTA: portfólio COMPLETO de fluxos no Painel do Cliente.

Pedido do usuário (19/jul/2026): o Painel da SELECTA mostrava só o fluxo curado EBJ→IUF
FARELO DE SOJA (com referência do contrato retroativo). A base tem 5 rotas reais em
tarifas_praticadas: EBJ→IUF FARELO, ZZB→IUF SOJA, EPP→VTU SOJA, ETB→VTU SOJA, ZZB→VTU SOJA
— 3 delas com abertura real por serviço em fluxos_servico.

Este script ADICIONA as 4 rotas que faltavam, PRESERVANDO intactos os fluxos curados
'SELECTA' (EBJ→IUF, planilha interna) e 'SELECTA (retroativo)' — o par que alimenta os
deltas de manobra vs. contrato retroativo e as simulações salvas do usuário (localStorage
é chaveado pelo nome do fluxo; renomear quebraria tudo).

Fontes por rota nova:
- tarifas_praticadas: frete (frete_trackage), acessórias (demais_servicos), tarifa = soma,
  teto ANTT absoluto = frete ÷ coluna 'teto' (que é a razão frete/teto), km_rota, vigência.
- fluxos_servico: abertura por serviço do item de maior soma (ZZB→IUF e EPP→VTU têm;
  ETB→VTU e ZZB→VTU não têm — ficam sem abertura, com a cobertura anotando).
- volume_hist: último ano com realizado por (origem,destino).

Idempotente: apaga e reinsere só as rotas NOVAS da SELECTA (nome de fluxo "PRODUTO O D");
nunca toca em 'SELECTA' / 'SELECTA (retroativo)'. Roda DEPOIS de add_projetos_clientes.py.

Uso:  python3 add_selecta_fluxos_completos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "SELECTA"
ROTA_CURADA = ("EBJ", "IUF", "FARELO DE SOJA")   # já coberta pelo par curado+retroativo
FONTE_PJF = "tarifas_praticadas (frete+acessórias; teto = frete ÷ %teto) + fluxos_servico — portfólio SELECTA"
FONTE_PJA = "fluxos_servico (abertura real por serviço do item mais caro da rota)"

NOME_SERV = {
    "MANOBRA ORIGEM": "Manobra Origem",
    "MANOBRA DESTINO": "Manobra Destino",
    "TRANSBORDO ORIGEM": "Transbordo Origem",
    "TRANSBORDO DESTINO": "Transbordo Destino",
    "DIREITO DE PASSAGEM": "Direito de Passagem",
    "MANOBRA CONEXAO CHEIO": "Manobra Conexão Cheio",
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # rotas de tarifas_praticadas (dedupe por rota×produto, maior tarifa)
    rotas = {}
    for item, o, d, prod, frete, acess, teto_ratio, ipoa, vig, km in cur.execute(
        """SELECT item, origem, destino, UPPER(produto), frete_trackage, demais_servicos,
                  teto, ipoa, vigencia, km_rota
           FROM tarifas_praticadas WHERE UPPER(cliente) LIKE '%SELECTA%'"""):
        k = (o, d, prod)
        if k == ROTA_CURADA:
            continue                                   # curada — não duplicar
        total = (frete or 0) + (acess or 0)
        if k not in rotas or total > rotas[k]["total"]:
            teto_abs = (frete / teto_ratio) if (frete and teto_ratio and teto_ratio > 0) else None
            rotas[k] = dict(item=item, origem=o, destino=d, produto=prod, frete=frete,
                            acess=acess, total=total, teto=teto_abs, ipoa=ipoa,
                            vig=str(vig)[:10] if vig else None, km=km)

    # abertura por rota (fluxos_servico, item de maior soma de serviços)
    servs = {}
    for it, o, d, prod, sv, tar in cur.execute(
        """SELECT itens, origem, destino, UPPER(produto), UPPER(servicos), tarifa
           FROM fluxos_servico WHERE UPPER(cliente) LIKE '%SELECTA%' AND tarifa IS NOT NULL"""):
        servs.setdefault((o, d, prod), {}).setdefault(it, {})
        servs[(o, d, prod)][it][sv] = servs[(o, d, prod)][it].get(sv, 0.0) + tar
    abertura = {}
    for k, itens in servs.items():
        it_best = max(itens, key=lambda i: sum(itens[i].values()))
        abertura[k] = itens[it_best]

    # volume por (origem,destino): último ano com realizado
    vol = {}
    for o, d, ano, ktu in cur.execute(
        """SELECT origem, destino, ano, SUM(realizado_ktu) FROM volume_hist
           WHERE UPPER(cliente) LIKE '%SELECTA%' AND realizado_ktu > 0
           GROUP BY origem, destino, ano"""):
        if (o, d) not in vol or ano > vol[(o, d)][0]:
            vol[(o, d)] = (ano, ktu)

    # apaga só as rotas novas anteriores (nome "PRODUTO O D") — nunca os curados
    cur.execute("""DELETE FROM projeto_fluxo_tarifas
                   WHERE cliente=? AND fluxo NOT IN ('SELECTA','SELECTA (retroativo)')""", (CLIENTE,))
    cur.execute("""DELETE FROM projeto_acessorias_abertas
                   WHERE cliente=? AND fluxo NOT IN ('SELECTA','SELECTA (retroativo)')""", (CLIENTE,))

    n_pjf = n_pja = 0
    for k, r in sorted(rotas.items()):
        fluxo = f"{r['produto']} {r['origem']} {r['destino']}"
        ab = abertura.get(k)
        v = vol.get((r["origem"], r["destino"]))
        frete_final, acess_final = r["frete"], r["acess"]
        if ab:
            # abertura existe: deriva frete/acessórias DELA, não de tarifas_praticadas — as
            # duas são extrações independentes da mesma fonte e podem divergir mesmo pro
            # mesmo item (achado do usuário 20/jul/2026 na RAIZEN — mesmo padrão aqui).
            frete_final = ab.get("FRETE", 0.0)
            acess_final = sum(v2 for sv2, v2 in ab.items() if sv2 != "FRETE")
        cobertura = f"portfólio por rota (item {r['item']})" + ("" if ab else " — sem abertura de manobra na base pra esta rota")
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round((frete_final or 0) + (acess_final or 0), 2),
             round(r["teto"], 2) if r["teto"] else None,
             round(frete_final, 2), round(acess_final, 2),
             round(r["ipoa"], 4) if r["ipoa"] is not None else None,
             round(r["km"], 1) if r["km"] else None,
             round(v[1] * 1000.0, 0) if v else None, r["vig"], FONTE_PJF, cobertura),
        )
        n_pjf += 1
        if ab:
            for sv, val in sorted(ab.items()):
                if sv == "FRETE" or val <= 0:
                    continue
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, NOME_SERV.get(sv, sv.title()), round(val, 2), FONTE_PJA))
                n_pja += 1

    con.commit()
    print(f"  SELECTA portfólio: +{n_pjf} rotas novas em projeto_fluxo_tarifas, "
          f"{n_pja} itens de abertura (curado EBJ→IUF + retroativo preservados).")
    con.close()


if __name__ == "__main__":
    main()
