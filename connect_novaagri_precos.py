# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o historico de precos contratuais da NOVA AGRI
(tabela novaagri_precos_contratuais, minerada dos videos F-LINK IMG_0545-0546) ao Painel do
Cliente, ATUALIZANDO (nao duplicando) os 2 fluxos que ja existiam em projeto_fluxo_tarifas
(portfolio completo, modo "replace" em add_demais_clientes_fluxos_completos.py):
  - "SOJA PPT QPM"  <- item 39691 (SOJA,  PPT-PATIO DE PALMEIRANTES -> QPM-PONTA DA MADEIRA)
  - "MILHO PPT QPM" <- item 41658 (MILHO, mesma rota)

Usa a vigencia com vigencia_inicial MAIS RECENTE por fluxo_curado como a situacao tarifaria
atual.

Substitui tarifa_total/teto/frete/acessorias/ipoa/vigencia/fonte dos 2 fluxos E substitui
por completo os itens de projeto_acessorias_abertas desses 2 fluxos pela abertura real
reajuste-a-reajuste (Manobra Origem/Destino, Direito de Passagem EFC).

Tambem recalcula volume_ano_ktu a partir dos ultimos 12 meses REALIZADOS de volume_hist
(mesma logica de connect_cmoc_precos.py / connect_alz_precos.py) — substitui os numeros
estaticos antigos da planilha. ATENCAO: volume_ano_ktu e gravado em TONELADAS em toda a
base (multiplica por 1000 antes de gravar).

IMPORTANTE: deve rodar DEPOIS de fix_dp_acessoria_curados.py e DEPOIS de
add_demais_clientes_fluxos_completos.py (mesma ordem de connect_cmoc_precos.py /
connect_alz_precos.py / connect_agrex_precos.py) — o DELETE+INSERT abaixo garante que o
dado REAL agora prevalece sobre o portfolio "replace" que rodou antes.

Idempotente: apaga e reinsere so os itens dos 2 fluxos NOVA AGRI acima. So age se
novaagri_precos_contratuais existir.

Uso:  python3 connect_novaagri_precos.py   (ou automatico via add_projetos_clientes.py)
"""
import pathlib
import re
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "NOVA AGRI"
FONTE_PJF = "F-LINK Precos Contratuais (videos IMG_0545-0546) — vigencia mais recente"
FONTE_PJA = "F-LINK Precos Contratuais (videos IMG_0545-0546) — abertura de manobra reajuste-a-reajuste"


def _brdate_key(d):
    if not d:
        return (0, 0, 0)
    dd, mm, aaaa = d.split("/")
    return (int(aaaa), int(mm), int(dd))


def _ftok(produto):
    """Primeiro token do produto (mesma convencao de _ftok/famTok/pcNormProd usada em todo o
    resto da base) — acha o produto GASOLINA de FARELO DE SOJA sem misturar SOJA com MILHO."""
    return re.split(r"[ \-]", str(produto or "").upper())[0]


def _volume_12m_real(cur, origem, destino, produto):
    """Ultimos 12 meses REALIZADOS de volume_hist pra uma rota+PRODUTO da NOVA AGRI,
    ancorado no ultimo mes com dado. Filtra por produto (achado 22/jul/2026: SOJA e MILHO
    PPT->QPM tinham ficado com o MESMO volume_ano_ktu — mesma classe de bug ja corrigida
    pra VIBRA/RAIZEN/IPIRANGA nesta sessao, aqui reaparecendo porque esta funcao nao filtrava
    por mercadoria). Retorna (kt, ano, mes) ou None."""
    tok = _ftok(produto)
    rows = cur.execute(
        """SELECT ano, mes, SUM(realizado_ktu) FROM volume_hist
           WHERE UPPER(cliente)='NOVA AGRI' AND origem=? AND destino=?
             AND UPPER(SUBSTR(REPLACE(mercadoria,'-',' '),1,LENGTH(?))) = ?
           GROUP BY ano, mes ORDER BY ano, mes""",
        (origem, destino, tok, tok)).fetchall()
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
        "SELECT name FROM sqlite_master WHERE type='table' AND name='novaagri_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! novaagri_precos_contratuais nao existe — rode "
              "add_novaagri_precos_contratuais.py antes. Pulando conexao.")
        con.close()
        return

    linhas = cur.execute(
        """SELECT item_ferroviario, fluxo_curado, produto, vigencia_inicial, valor_tr_antt,
                  tarifa_contrato, manobra_destino_rs_t, manobra_origem_rs_t, frete_rs_t,
                  direito_passagem_efc_rs_t
           FROM novaagri_precos_contratuais"""
    ).fetchall()

    por_fluxo = {}
    for row in linhas:
        por_fluxo.setdefault(row[1], []).append(row)

    npjf = npja = 0
    for fluxo, rows in por_fluxo.items():
        rows_sorted = sorted(rows, key=lambda r: _brdate_key(r[3]), reverse=True)
        (it, flx, prod, vi, tr, tarifa, md, mo, frete, dp) = rows_sorted[0]

        existe = cur.execute(
            "SELECT 1 FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (CLIENTE, fluxo)
        ).fetchone()
        if not existe:
            print(f"  ! fluxo '{fluxo}' (item {it}) nao encontrado em "
                  f"projeto_fluxo_tarifas — pulando (nao crio fluxo novo aqui).")
            continue

        acess = (mo or 0) + (md or 0) + (dp or 0)
        ipoa = (acess / frete) if frete else 0.0

        _toks = fluxo.split()
        _o, _d = _toks[-2], _toks[-1]
        _vol = _volume_12m_real(cur, _o, _d, prod)
        if _vol:
            vol_kt, ult_ano, ult_mes = _vol
            vol_t = round(vol_kt * 1000, 1)
            cobertura_txt = (
                f"tarifa/acessorias reajuste a reajuste 2025-2026 (item {it}, contrato "
                f"C_2022_33) — substitui valor antigo da planilha. Volume_ano_ktu = ultimos "
                f"12 meses REALIZADOS de volume_hist ({vol_kt}kt, janela ate "
                f"{ult_mes:02d}/{ult_ano}, mesma convencao do resto da base) — substitui o "
                f"numero estatico da planilha antiga.")
        else:
            vol_t = None
            cobertura_txt = (
                f"tarifa/acessorias reajuste a reajuste 2025-2026 (item {it}, contrato "
                f"C_2022_33) — substitui valor antigo da planilha. Sem dado em volume_hist "
                f"pra esta rota — volume_ano_ktu nao confirmado (nao estimado).")

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
        itens_abertura = [("Manobra origem", mo), ("Manobra destino", md), ("DP EFC", dp)]
        for nome, val in itens_abertura:
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  NOVA AGRI (2 fluxos reconciliados com F-LINK) atualizados: {npjf} fluxos em "
          f"projeto_fluxo_tarifas, {npja} itens de manobra/direito de passagem em "
          f"projeto_acessorias_abertas (fonte: precos contratuais F-LINK, substitui planilha antiga).")
    con.close()


if __name__ == "__main__":
    main()
