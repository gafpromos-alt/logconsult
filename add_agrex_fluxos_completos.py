# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — AGREX: portfólio COMPLETO de fluxos no Painel do Cliente.

Pedido do usuário (19/jul/2026): o Painel do Cliente da AGREX mostrava só "ZZB→IUF SOJA"
(na verdade 1 fluxo genérico 'AGREX' — média ponderada da planilha interna, que o painel
rotulava pela rota principal). A base tem MUITO mais: ipoa_teto traz 8 rotas×produto
(ETB→VTU soja/milho, PIN→QPM s/m, PIP→QPM s/m, PPF→QPM s/m, PPN→QPM s/m, ZZB→IUF soja)
e fluxos_servico traz ainda ETB→IUF SOJA (13 itens, sem teto calculado na base) + a
ABERTURA REAL por serviço (manobra origem/destino, transbordo, DP) de cada fluxo de soja.

Este script SUBSTITUI o fluxo genérico 'AGREX' por uma linha por rota×produto:
- projeto_fluxo_tarifas: dedupe por (origem,destino,produto) pegando o MAIOR total de
  ipoa_teto (situação mais cara = maior oportunidade — mesma regra do portfólio
  Mosaic/Usiminas/ArcelorMittal); ETB→IUF entra via fluxos_servico (tarifa = soma dos
  serviços do item mais caro; teto NULL — não existe na base, não inventamos).
- projeto_acessorias_abertas: abertura real por fluxo a partir de fluxos_servico (item
  escolhido = o de MAIOR soma de serviços da rota; linhas de DP duplicadas são somadas).
  Rotas sem abertura na base (PIN→QPM e todos os fluxos de MILHO — fluxos_servico só tem
  soja da AGREX) ficam sem linhas de manobra, com a cobertura anotando isso (não copiamos
  a abertura de soja pra milho: seria inventar).
- volume_ano_ktu (t/ano): último ano com realizado em volume_hist por (origem,destino).

Idempotente: apaga e reinsere só as linhas da AGREX. Roda DEPOIS de add_projetos_clientes.py.

Uso:  python3 add_agrex_fluxos_completos.py
"""
import pathlib
import re
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "AGREX"
FONTE_PJF = "ipoa_teto (dedupe maior total por rota) + fluxos_servico — portfólio completo AGREX"
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

    # ---- fluxos de ipoa_teto (dedupe por rota×produto, maior total) ----
    rotas = {}
    for item, o, d, prod, ipoa, acess, frete, teto, total, km in cur.execute(
        """SELECT item, origem, destino, produto, ipoa, acessorias, frete, teto, total, km_rota
           FROM ipoa_teto WHERE UPPER(cliente) LIKE '%AGREX%' AND total IS NOT NULL"""):
        k = (o, d, str(prod).upper())
        if k not in rotas or (total or 0) > (rotas[k]["total"] or 0):
            rotas[k] = dict(item=item, origem=o, destino=d, produto=str(prod).upper(),
                            ipoa=ipoa, acess=acess, frete=frete, teto=teto, total=total, km=km)

    # ---- abertura por rota a partir de fluxos_servico: item de MAIOR soma de serviços ----
    servs = {}
    for it, o, d, prod, sv, tar in cur.execute(
        """SELECT itens, origem, destino, UPPER(produto), UPPER(servicos), tarifa
           FROM fluxos_servico WHERE UPPER(cliente) LIKE '%AGREX%' AND tarifa IS NOT NULL"""):
        servs.setdefault((o, d, prod), {}).setdefault(it, {})
        servs[(o, d, prod)][it][sv] = servs[(o, d, prod)][it].get(sv, 0.0) + tar
    abertura = {}
    for k, itens in servs.items():
        it_best = max(itens, key=lambda i: sum(itens[i].values()))
        abertura[k] = dict(item=it_best, servicos=itens[it_best])

    # ---- ETB→IUF (só em fluxos_servico): entra como fluxo sem teto ----
    for k, ab in abertura.items():
        if k not in rotas:
            sv = ab["servicos"]
            frete = sv.get("FRETE", 0.0)
            acess = sum(v for s, v in sv.items() if s != "FRETE")
            rotas[k] = dict(item=ab["item"], origem=k[0], destino=k[1], produto=k[2],
                            ipoa=(acess / frete) if frete else None, acess=acess, frete=frete,
                            teto=None, total=frete + acess, km=None)

    # ---- volume: último ano com realizado por (origem,destino,PRODUTO) ----
    # Mesmo bug achado na VIBRA/RAIZEN/IPIRANGA (21/jul/2026): chave só por rota misturava
    # SOJA e MILHO na mesma origem/destino, dando o mesmo volume combinado pros dois. Produto
    # casado por primeiro token (mesma convenção de famTok/pcNormProd no front/_ftok em
    # add_demais_clientes_fluxos_completos.py).
    def _ftok(produto):
        return re.split(r"[ \-]", str(produto or "").upper())[0]
    vol = {}
    for o, d, prod_vh, ano, ktu in cur.execute(
        """SELECT origem, destino, mercadoria, ano, SUM(realizado_ktu) FROM volume_hist
           WHERE UPPER(cliente) LIKE '%AGREX%' AND realizado_ktu > 0
           GROUP BY origem, destino, mercadoria, ano"""):
        key = (o, d, _ftok(prod_vh))
        if key not in vol or ano > vol[key][0]:
            vol[key] = (ano, ktu)

    # ---- grava (substitui o fluxo genérico e qualquer versão anterior) ----
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (CLIENTE,))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    n_pjf = n_pja = 0
    for k, r in sorted(rotas.items()):
        fluxo = f"{r['produto']} {r['origem']} {r['destino']}"
        ab = abertura.get(k)
        v = vol.get((r["origem"], r["destino"], _ftok(r["produto"])))
        frete_final, acess_final = r["frete"], r["acess"]
        if ab:
            # abertura existe: deriva frete/acessórias DELA, não de ipoa_teto — as duas são
            # extrações independentes da mesma fonte e podem divergir mesmo pro mesmo item
            # (achado do usuário 20/jul/2026 na RAIZEN — mesmo padrão aqui).
            sv_map = ab["servicos"]
            frete_final = sv_map.get("FRETE", 0.0)
            acess_final = sum(v2 for sv2, v2 in sv_map.items() if sv2 != "FRETE")
        cobertura = f"portfólio por rota (item {r['item']})" + ("" if ab else " — sem abertura de manobra na base (fluxos_servico só cobre soja)")
        if r["teto"] is None:
            cobertura += " — sem teto ANTT calculado na base pra esta rota"
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
             round(v[1] * 1000.0, 0) if v else None, None, FONTE_PJF, cobertura),
        )
        n_pjf += 1
        if ab:
            for sv, val in sorted(ab["servicos"].items()):
                if sv == "FRETE" or val <= 0:
                    continue
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, NOME_SERV.get(sv, sv.title()), round(val, 2), FONTE_PJA))
                n_pja += 1

    con.commit()
    print(f"  AGREX portfólio completo: {n_pjf} fluxos em projeto_fluxo_tarifas, "
          f"{n_pja} itens de abertura em projeto_acessorias_abertas.")
    con.close()


if __name__ == "__main__":
    main()
