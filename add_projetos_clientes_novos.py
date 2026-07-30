# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Painel do Cliente: NOVOS CLIENTES (siderurgia/mineração)
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Pedido do usuário (jul/2026): trazer Mosaic, Usiminas e ArcelorMittal para o Painel do Cliente
(mesmo modelo das 3 abas da Selecta), com "vários fluxos" (todo o portfólio acima do teto/IPOA).

Diferente dos clientes de grão (que têm 1 fluxo curado + abertura de manobra transcrita da
planilha interna de projetos), estes 3 são de siderurgia/mineração com DEZENAS de fluxos e
NÃO têm abertura de manobra em lugar nenhum da base (só existe manobra por serviço p/ Mosaic
em fluxos_servico; Usiminas/ArcelorMittal não têm). Decisão do usuário: adicioná-los JÁ com o
Teto mostrando a situação tarifária + IPOA por fluxo, com a abertura de manobra marcada como
PENDENTE (ele fornece depois a abertura curada; NÃO derivar da base geral agora).

Este script só cria os registros de projeto (projeto_fluxo_tarifas) desses 3 clientes a partir
da base de teto absoluta (ipoa_teto), SEM nenhum registro em projeto_acessorias_abertas (por isso
o Teto renderiza em modo "portfólio", sem deltas de manobra simuláveis, até a abertura chegar).
Isonomia Tarifária e Retroativo (lado isonomia) funcionam sozinhos, pois vêm de tarifas_praticadas
e vli_pnl (onde os 3 já existem).

Seleção de fluxos por cliente: dedupe por (origem, destino, produto) pegando o maior tarifa_total
(situação atual mais cara = maior oportunidade), filtro pct_teto>=50% OU IPOA>=24,8% (referência
ANTT), ordenado por %teto desc, teto de 25 fluxos por cliente (portfólio, não painel gigante).

Idempotente: apaga e reinsere só as linhas destes 3 clientes (não toca nos 8 clientes curados).

Uso:  python3 add_projetos_clientes_novos.py
"""
import pathlib
import sqlite3

from canon import canon

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

CLIENTES = ("MOSAIC", "USIMINAS", "ARCELORMITTAL")
IPOA_REF = 0.248
MAX_FLUXOS = 25
FONTE = ("ipoa_teto (base de tarifas praticadas) — situação tarifária por fluxo; "
         "abertura de manobra PENDENTE (a fornecer pela consultoria)")
COBERTURA = "sem abertura de manobra (pendente)"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    rows = cur.execute(
        """SELECT cliente, origem, destino, produto, ipoa, acessorias, frete, teto, teto_1, total, km_rota
           FROM ipoa_teto WHERE frete IS NOT NULL AND frete > 0 AND total IS NOT NULL"""
    ).fetchall()

    # agrupa por cliente canônico → dedupe por (o,d,produto) pelo maior total
    por_cli = {c: {} for c in CLIENTES}
    for r in rows:
        c = canon(r[0])
        if c not in por_cli:
            continue
        key = (r[1], r[2], r[3])
        best = por_cli[c].get(key)
        if best is None or (r[9] or 0) > (best[9] or 0):
            por_cli[c][key] = r

    # limpa registros antigos SÓ destes 3 (idempotência sem tocar nos curados)
    for c in CLIENTES:
        cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente = ?", (c,))

    total_ins = 0
    for c in CLIENTES:
        ded = list(por_cli[c].values())
        sel = [r for r in ded if (r[8] or 0) >= 0.50 or (r[4] or 0) >= IPOA_REF]
        sel.sort(key=lambda r: -(r[8] or 0))
        sel = sel[:MAX_FLUXOS]
        for r in sel:
            origem, destino, produto = r[1], r[2], r[3]
            ipoa, acess, frete, teto, total, km = r[4], r[5], r[6], r[7], r[9], r[10]
            fluxo = f"{produto} {origem} {destino}"
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (c, fluxo, round(total, 2), round(teto, 2), round(frete, 2),
                 round(acess, 2), round(ipoa, 4), round(km, 1) if km else None,
                 None, None, FONTE, COBERTURA),
            )
            total_ins += 1
        print(f"  {c}: {len(sel)} fluxos inseridos (portfólio, sem manobra)")

    con.commit()
    print(f"\nTotal: {total_ins} fluxos em projeto_fluxo_tarifas para {len(CLIENTES)} clientes novos.")
    print("Abertura de manobra NÃO inserida (pendente) — Teto renderiza em modo portfólio.")
    con.close()


if __name__ == "__main__":
    main()
