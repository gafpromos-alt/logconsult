# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da MOSAIC (Vale
Fertilizantes, tabela mosaic_precos_contratuais, minerada dos vídeos F-LINK IMG_0532-0533) ao
Painel do Cliente, criando 2 fluxos NOVOS em projeto_fluxo_tarifas e
projeto_acessorias_abertas:
  - "ENXOFRE IUF ZVF"        (item 39890)
  - "ROCHA FOS UMIDA ELC ZVF" (item 39889)

Estes 2 fluxos preenchem uma lacuna conhecida: MOSAIC só tinha abertura de manobra para
FERTILIZANTES/GESSO/MINERIO FERRO — ENXOFRE e o "fosfato" (ROCHA FOS UMIDA) não tinham
nenhuma tarifa aberta na base (só volume).

NOTA sobre canon.py: o cliente aparece no F-LINK como "VALE FERTILIZANTES SA". canon.py tem
uma regra separada ("VALE FERTILIZANTES") distinta de "MOSAIC" (usada para "MOSAIC
FERTILIZANTES DO BRASIL LTDA."/"MOSAIC FERTILIZANTES P&K S.A"). Nas rotas já curadas em
projeto_fluxo_tarifas, a rota IUF-TUF→ZVF-VALEFÉRTIL já existe como "FERTILIZANTES IUF ZVF"
sob cliente="MOSAIC" — mesma origem/destino do item 39890 aqui minerado — confirmando que,
na prática de negócio, é a mesma conta. Este script usa cliente="MOSAIC" (hardcoded, sem
chamar canon()) para ficar consistente com o Painel do Cliente já existente. A distinção do
canon.py entre "VALE FERTILIZANTES" e "MOSAIC" fica como ressalva para revisão futura (pode
haver outras tabelas que dependem dessa separação).

Usa a vigência com vigência_inicial MAIS RECENTE por item como a situação tarifária atual.

Idempotente: apaga e reinsere só os 2 fluxos acima (não toca nos outros fluxos MOSAIC nem
em outros clientes). Deve rodar DEPOIS de add_projetos_clientes.py (DROP+CREATE das tabelas
de projeto) e DEPOIS de add_mosaic_precos_contratuais.py (cria a tabela-fonte).

Uso:  python3 connect_mosaic_precos.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "MOSAIC"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0532-0533) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0532-0533) — abertura de manobra reajuste-a-reajuste"

FLUXOS_NOVOS = {
    39890: "ENXOFRE IUF ZVF",
    39889: "ROCHA FOS UMIDA ELC ZVF",
}


def _brdate_key(d):
    if not d:
        return (0, 0, 0)
    dd, mm, aaaa = d.split("/")
    return (int(aaaa), int(mm), int(dd))


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='mosaic_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! mosaic_precos_contratuais não existe — rode add_mosaic_precos_contratuais.py "
              "antes. Pulando conexão.")
        con.close()
        return

    linhas = cur.execute(
        """SELECT item_ferroviario, origem, destino, produto, vigencia_inicial,
                  valor_tr_antt, tarifa_contrato, descarga_rs_t, frete_rs_t,
                  manobra_origem_rs_t, manobra_destino_rs_t,
                  direito_passagem_mrs_rs_t, direito_passagem_allmp_rs_t
           FROM mosaic_precos_contratuais"""
    ).fetchall()

    por_item = {}
    for row in linhas:
        por_item.setdefault(row[0], []).append(row)

    npjf = npja = 0
    for item, fluxo in FLUXOS_NOVOS.items():
        rows = por_item.get(item)
        if not rows:
            print(f"  ! item {item} ({fluxo}) sem linhas em mosaic_precos_contratuais, pulando.")
            continue
        rows_sorted = sorted(rows, key=lambda r: _brdate_key(r[4]), reverse=True)
        (it, o, d, prod, vi, tr, tarifa, descarga, frete, mo, md, dp_mrs, dp_allmp) = rows_sorted[0]

        # remove só este fluxo específico (não toca nos outros fluxos MOSAIC já curados)
        cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (CLIENTE, fluxo))
        cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?", (CLIENTE, fluxo))

        acess = (mo or 0) + (md or 0) + (dp_mrs or 0) + (dp_allmp or 0)
        ipoa = (acess / frete) if frete else 0.0
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
             round(frete, 2) if frete else None, round(acess, 2), round(ipoa, 4),
             None, None, vi, FONTE_PJF,
             f"reajuste a reajuste 2025-2026 (item {item}) — fluxo novo, preenche lacuna de "
             f"abertura de manobra para {prod}"))
        npjf += 1

        itens_abertura = [("Descarga", descarga), ("Manobra Origem", mo), ("Manobra Destino", md),
                           ("Direito de Passagem MRS", dp_mrs), ("Direito de Passagem ALLMP", dp_allmp)]
        for nome, val in itens_abertura:
            if val is not None:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  MOSAIC (novos fluxos ENXOFRE/ROCHA FOS UMIDA) conectados: {npjf} fluxos em "
          f"projeto_fluxo_tarifas, {npja} itens de manobra/direito de passagem em "
          f"projeto_acessorias_abertas (fonte: preços contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
