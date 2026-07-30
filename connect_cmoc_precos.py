# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da CMOC (tabela
cmoc_precos_contratuais, minerada dos vídeos F-LINK IMG_0534-0536) ao Painel do Cliente,
ATUALIZANDO (não duplicando) os 3 fluxos CURADOS que já existiam em projeto_fluxo_tarifas
(vindos de "LogConsult (tarifas por cliente).xlsx"):
  - "ROCHA EYC IFA"    <- item 12020 (ROCHA FOSF SECA, EYC-POSTO FOSFAGO -> IFA-FABRICA)
  - "ENXOFRE IUF EYC"  <- item 12019 (ENXOFRE, IUF-TUF -> EYC-POSTO FOSFAGO)
  - "ENXOFRE ICZ EYC"  <- item 12018 (ENXOFRE, ICZ-CONCEICAOZINHA -> EYC-POSTO FOSFAGO)

Usa a vigência com vigência_inicial MAIS RECENTE por item como a situação tarifária atual
(sanity check: o "teto" novo bate de perto com o antigo — 157.91≈157.88, 189.49≈189.53,
185.53≈191.14 — confirmando que são os mesmos 3 fluxos/rotas).

Substitui tarifa_total/teto/frete/acessorias/ipoa/vigencia/fonte dos 3 fluxos E substitui
por completo os itens de projeto_acessorias_abertas desses 3 fluxos pela abertura real
reajuste-a-reajuste (Manobra origem/destino, Direito de Passagem MRS/ALLMP, Limpeza de
Vagão quando aplicável).

IMPORTANTE: deve rodar DEPOIS de fix_dp_acessoria_curados.py no pipeline de
add_projetos_clientes.py — senão aquele script re-calcularia acessórias/tarifa_total a
partir dos itens antigos (da planilha) antes deste script substituí-los pelos reais.

Idempotente: apaga e reinsere só os itens dos 3 fluxos CMOC acima. Deve rodar DEPOIS de
add_projetos_clientes.py e DEPOIS de add_cmoc_precos_contratuais.py (cria a tabela-fonte).

Uso:  python3 connect_cmoc_precos.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "CMOC"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0534-0536) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0534-0536) — abertura de manobra reajuste-a-reajuste"


def _brdate_key(d):
    if not d:
        return (0, 0, 0)
    dd, mm, aaaa = d.split("/")
    return (int(aaaa), int(mm), int(dd))


def _volume_12m_real(cur, origem, destino):
    """Últimos 12 meses REALIZADOS de volume_hist pra uma rota CMOC (origem,destino),
    ancorado no último mês com dado (mesma convenção do pcUlt12Sum do front — nunca
    ancora em "hoje", ancora no último dado real disponível). Pedido do usuário
    (22/jul/2026, "volume CMOC ainda muito abaixo do que ele realiza"): a planilha antiga
    tinha um número estático (450/75/60 mil t/ano) que nunca mais foi atualizado — troca
    aqui pelo realizado real mais recente, mesma fonte/lógica que todo o resto da base usa.
    Retorna (kt, ano, mes) ou None se a rota não tem nenhum dado em volume_hist. `kt` já é
    em quilotonelada (unidade de volume_hist.realizado_ktu) — o CALLER deve converter pra
    TONELADAS (×1000) antes de gravar em projeto_fluxo_tarifas.volume_ano_ktu, que usa essa
    convenção em toda a base (ver painel_template.html:1909, "planilha grava em t/ano" —
    achado 22/jul/2026: uma correção anterior gravou esse valor já em kt sem multiplicar,
    o front dividiu por 1000 de novo e a rota sumiu como "sem volume" na UI)."""
    rows = cur.execute(
        """SELECT ano, mes, SUM(realizado_ktu) FROM volume_hist
           WHERE UPPER(cliente)='CMOC' AND origem=? AND destino=?
           GROUP BY ano, mes ORDER BY ano, mes""",
        (origem, destino)).fetchall()
    if not rows:
        return None
    idx = {(a, m): v for a, m, v in rows}
    y, m = rows[-1][0], rows[-1][1]
    total = 0.0
    for _ in range(12):
        total += idx.get((y, m), 0.0)
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return round(total, 1), rows[-1][0], rows[-1][1]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cmoc_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! cmoc_precos_contratuais não existe — rode add_cmoc_precos_contratuais.py "
              "antes. Pulando conexão.")
        con.close()
        return

    linhas = cur.execute(
        """SELECT item_ferroviario, fluxo_curado, produto, vigencia_inicial, valor_tr_antt,
                  tarifa_contrato, manobra_destino_rs_t, manobra_origem_rs_t, frete_rs_t,
                  direito_passagem_allmp_rs_t, direito_passagem_mrs_rs_t, limpeza_vagao_rs_t
           FROM cmoc_precos_contratuais"""
    ).fetchall()

    por_item = {}
    for row in linhas:
        por_item.setdefault(row[0], []).append(row)

    npjf = npja = 0
    for item, rows in por_item.items():
        rows_sorted = sorted(rows, key=lambda r: _brdate_key(r[3]), reverse=True)
        (it, fluxo, prod, vi, tr, tarifa, md, mo, frete, dp_allmp, dp_mrs, limpeza) = rows_sorted[0]

        existe = cur.execute(
            "SELECT 1 FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (CLIENTE, fluxo)
        ).fetchone()
        if not existe:
            print(f"  ! fluxo curado '{fluxo}' (item {item}) não encontrado em "
                  f"projeto_fluxo_tarifas — pulando (não crio fluxo novo aqui).")
            continue

        acess = (mo or 0) + (md or 0) + (dp_mrs or 0) + (dp_allmp or 0) + (limpeza or 0)
        ipoa = (acess / frete) if frete else 0.0

        # volume real (últimos 12 meses realizados de volume_hist) — substitui o número
        # estático da planilha antiga. fluxo = "PRODUTO ORIGEM DESTINO" (últimos 2 tokens).
        _toks = fluxo.split()
        _o, _d = _toks[-2], _toks[-1]
        _vol = _volume_12m_real(cur, _o, _d)
        if _vol:
            vol_kt, ult_ano, ult_mes = _vol
            vol_t = round(vol_kt * 1000, 1)   # coluna grava em TONELADAS, não em kt
            cobertura_txt = (
                f"tarifa/acessórias reajuste a reajuste 2022-2026 (item {item}, contrato "
                f"C_2025_60) — substitui valor antigo da planilha. Volume_ano_ktu = últimos 12 "
                f"meses REALIZADOS de volume_hist ({vol_kt}kt, janela até {ult_mes:02d}/{ult_ano}, "
                f"mesma convenção do resto da base) — substitui o número estático da planilha antiga.")
        else:
            vol_t = None
            cobertura_txt = (
                f"tarifa/acessórias reajuste a reajuste 2022-2026 (item {item}, contrato "
                f"C_2025_60) — substitui valor antigo da planilha. Sem dado em volume_hist pra "
                f"esta rota — volume_ano_ktu não confirmado (não estimado).")

        cur.execute(
            """UPDATE projeto_fluxo_tarifas
               SET tarifa_total=?, teto=?, frete=?, acessorias=?, ipoa=?, vigencia=?, fonte=?,
                   volume_ano_ktu=?, cobertura=?
               WHERE cliente=? AND fluxo=?""",
            (round(tarifa, 2), round(tr, 2) if tr else None, round(frete, 2) if frete else None,
             round(acess, 2), round(ipoa, 4), vi, FONTE_PJF, vol_t, cobertura_txt,
             CLIENTE, fluxo))
        npjf += 1

        cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?", (CLIENTE, fluxo))
        itens_abertura = [("Manobra origem", mo), ("Manobra destino", md),
                           ("DP MRS", dp_mrs), ("DP Rumo", dp_allmp)]
        if limpeza is not None:
            itens_abertura.append(("Limpeza de Vagão", limpeza))
        for nome, val in itens_abertura:
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  CMOC (3 fluxos curados reconciliados com F-LINK) atualizados: {npjf} fluxos em "
          f"projeto_fluxo_tarifas, {npja} itens de manobra/direito de passagem em "
          f"projeto_acessorias_abertas (fonte: preços contratuais F-LINK, substitui planilha antiga).")
    con.close()


if __name__ == "__main__":
    main()
