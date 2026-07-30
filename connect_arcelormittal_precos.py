# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da
ARCELORMITTAL (tabela arcelormittal_precos_contratuais, minerada dos vídeos
F-LINK IMG_0457-0479) ao Painel do Cliente.

Diferente do conector da GERDAU: o banco já tinha 25 fluxos curados da
ARCELORMITTAL em projeto_fluxo_tarifas (com TETO/distancia_km/volume_ano_ktu
definidos manualmente) mas ZERO linhas em projeto_acessorias_abertas. Aqui:

- projeto_fluxo_tarifas (PJF):
    * Fluxo já existente (mesmo "produto origem destino") -> UPDATE apenas
      tarifa_total, frete, acessorias, ipoa, vigencia, fonte e cobertura,
      PRESERVANDO teto, distancia_km e volume_ano_ktu já cadastrados.
    * Fluxo novo (item ferroviário sem fluxo curado equivalente) -> INSERT,
      usando o Valor TR (ANTT) da fonte como teto (fallback, igual ao padrão
      GERDAU), distancia_km/volume_ano_ktu ficam NULL (sem curadoria prévia).
- projeto_acessorias_abertas (PJA): sempre populada (estava zerada) com
  MANOBRA ORIGEM, MANOBRA DESTINO e, quando aplicável, TRANSBORDO ORIGEM, da
  vigência mais recente de CADA item minerado.

Colisão de fluxo: os itens 40462 (VJM->VTU) e 7894 (VJM->VTU) mapeiam para o
mesmo nome de fluxo "FIO MAQUINA VJM VTU" (mesma rota/produto, itens
ferroviários distintos no F-LINK). Para PJF usa-se o item com vigência mais
recente entre os dois; ambos os itens geram linhas em PJA (fonte identifica
o item), então nenhuma informação de manobra se perde.

Idempotente: apaga e reinsere só as linhas de PJA da ARCELORMITTAL; em PJF
faz UPDATE dos fluxos existentes e INSERT dos novos (sem apagar as demais
linhas de outros clientes nem os 25 fluxos curados que não tiverem
correspondência na mineração).

Deve rodar DEPOIS de add_projetos_clientes.py (cria/popula PJF/PJA) e DEPOIS
de add_arcelormittal_precos_contratuais.py (cria a tabela-fonte).

Uso:  python3 connect_arcelormittal_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "ARCELORMITTAL"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0457-0479) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0457-0479) — abertura de manobra reajuste-a-reajuste"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='arcelormittal_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! arcelormittal_precos_contratuais não existe — rode "
              "add_arcelormittal_precos_contratuais.py antes. Pulando conexão.")
        con.close()
        return

    # fluxos curados existentes da ARCELORMITTAL em PJF (preservar teto/km/volume)
    existentes = {}
    for fluxo, teto, km, vol in cur.execute(
        """SELECT fluxo, teto, distancia_km, volume_ano_ktu
           FROM projeto_fluxo_tarifas WHERE cliente=?""", (CLIENTE,)):
        existentes[fluxo] = dict(teto=teto, distancia_km=km, volume_ano_ktu=vol)

    # vigência mais recente por item (a situação atual)
    itens = [r[0] for r in cur.execute(
        "SELECT DISTINCT item_ferroviario FROM arcelormittal_precos_contratuais")]
    atuais = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t,
                      transbordo_origem_rs_t
               FROM arcelormittal_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

    # agrupa por fluxo (produto origem destino) - pode haver colisao (2 itens
    # distintos, mesma rota/produto); fica o de vigencia_inicial mais recente
    por_fluxo = {}
    for row in atuais:
        it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, transb = row
        fluxo = f"{prod} {o} {d}"
        atual = por_fluxo.get(fluxo)
        if atual is None or vi > atual[5]:
            por_fluxo[fluxo] = row

    # limpa só PJA da ARCELORMITTAL (estava zerada; idempotente)
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (CLIENTE,))

    n_update = n_insert = npja = 0
    for fluxo, row in por_fluxo.items():
        it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, transb = row
        acess = (mo or 0) + (md or 0) + (transb or 0)
        ipoa = (acess / frete) if frete else 0.0
        cobertura = f"reajuste a reajuste (item {it}, {contrato})"

        if fluxo in existentes:
            cur.execute(
                """UPDATE projeto_fluxo_tarifas
                   SET tarifa_total=?, frete=?, acessorias=?, ipoa=?,
                       vigencia=?, fonte=?, cobertura=?
                   WHERE cliente=? AND fluxo=?""",
                (round(tarifa, 2), round(frete, 2) if frete is not None else None,
                 round(acess, 2), round(ipoa, 4), vf, FONTE_PJF, cobertura,
                 CLIENTE, fluxo))
            n_update += 1
        else:
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
                 round(frete, 2) if frete is not None else None, round(acess, 2),
                 round(ipoa, 4), None, None, vf, FONTE_PJF, cobertura))
            n_insert += 1

    # PJA: para TODOS os itens minerados (nao so o "vencedor" do fluxo),
    # assim nenhuma abertura de manobra se perde na colisao de fluxo
    for row in atuais:
        it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, transb = row
        fluxo = f"{prod} {o} {d}"
        fonte_item = f"{FONTE_PJA} (item {it})"
        for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md),
                                ("TRANSBORDO ORIGEM", transb)):
            if val:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), fonte_item))
                npja += 1

    con.commit()
    print(f"  ARCELORMITTAL conectada: {n_update} fluxos atualizados + {n_insert} fluxos novos "
          f"em projeto_fluxo_tarifas, {npja} itens de manobra/transbordo em "
          f"projeto_acessorias_abertas (fonte: preços contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
