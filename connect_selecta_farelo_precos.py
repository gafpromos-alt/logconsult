# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — conecta o preço contratual da SELECTA FARELO DE SOJA
EBJ→IUF (selecta_farelo_precos_contratuais, minerado de IMG_0563) ao Painel do Cliente.

Cria um fluxo NOVO "FARELO DE SOJA EBJ IUF" (rota inexistente em projeto_fluxo_tarifas até
este vídeo) com abertura de manobra completa (manobra conexão cheio + manobra destino +
manobra origem + direito de passagem ALLMP + direito de passagem MRS) — mesmo padrão de
connect_selecta_etbvtu_itens.py. Usa a vigência MAIS RECENTE (jul/2026) como a situação
tarifária atual.

Volume: soma o realizado_ktu do último ano disponível (2025) pra rota EBJ→IUF FARELO DE
SOJA MP na base volume_hist (igual volDefaultKt do front).

Idempotente: apaga e reinsere só o fluxo "FARELO DE SOJA EBJ IUF" da SELECTA. Roda DEPOIS de
add_selecta_farelo_precos_contratuais.py (cria a tabela-fonte). Chamado no fim de
add_projetos_clientes.py, logo após connect_selecta_etbvtu_itens.py.

Uso:  python3 connect_selecta_farelo_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "SELECTA"
ORIGEM, DESTINO, PRODUTO = "EBJ", "IUF", "FARELO DE SOJA"
FLUXO = f"{PRODUTO} {ORIGEM} {DESTINO}"
FONTE = "F-LINK Preços Contratuais (vídeo IMG_0563) — vigência mais recente"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='selecta_farelo_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! selecta_farelo_precos_contratuais não existe — rode "
              "add_selecta_farelo_precos_contratuais.py antes. Pulando.")
        con.close()
        return

    row = cur.execute(
        """SELECT item, contrato, vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                  manobra_conexao_cheio, frete, manobra_destino, manobra_origem, dp_allmp, dp_mrs
           FROM selecta_farelo_precos_contratuais
           ORDER BY vigencia_inicial DESC LIMIT 1""").fetchone()
    if not row:
        con.close()
        return
    (item, contrato, vi, vf, tr, tarifa, mcc, frete_val, md, mo, dpa, dpm) = row

    # volume: último ano com realizado na rota (igual volDefaultKt do front)
    vol = cur.execute(
        """SELECT ano, SUM(realizado_ktu) FROM volume_hist
           WHERE UPPER(cliente) LIKE '%SELECTA%' AND origem=? AND destino=?
                 AND UPPER(produto) LIKE '%FARELO%' AND realizado_ktu>0
           GROUP BY ano ORDER BY ano DESC LIMIT 1""", (ORIGEM, DESTINO)).fetchone()
    vol_ano_ktu = round(vol[1], 2) if vol else None

    # remove qualquer versão anterior deste fluxo (idempotente)
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (CLIENTE, FLUXO))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?", (CLIENTE, FLUXO))

    frete = round(frete_val, 2)
    acess = round(mcc + md + mo + dpa + dpm, 2)
    ipoa = round(acess / frete, 4) if frete else 0.0
    cobertura = (f"reajuste a reajuste (item {item}, {contrato}) — fluxo novo, minerado do "
                 f"vídeo F-LINK IMG_0563 (SELECTA não tinha rota FARELO DE SOJA na base antes)")
    cur.execute(
        """INSERT INTO projeto_fluxo_tarifas
           (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
            distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (CLIENTE, FLUXO, tarifa, round(tr, 2) if tr else None, frete, acess, ipoa,
         None, vol_ano_ktu, vf, FONTE, cobertura))

    npja = 0
    for nome, val in (
        ("Manobra Conexão Cheio", mcc),
        ("Manobra Destino", md),
        ("Manobra Origem", mo),
        ("Direito de Passagem ALLMP", dpa),
        ("Direito de Passagem MRS", dpm),
    ):
        if val is not None and val > 0:
            cur.execute(
                """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                   VALUES (?,?,?,?,?)""",
                (CLIENTE, FLUXO, nome, round(val, 2), FONTE))
            npja += 1

    con.commit()
    print(f"  SELECTA FARELO DE SOJA EBJ→IUF: 1 fluxo novo (item {item}), {npja} itens de "
          f"abertura de manobra/direito de passagem — vigência {vi} a {vf}, tarifa R${tarifa:.2f}.")
    con.close()


if __name__ == "__main__":
    main()
