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

ATUALIZAÇÃO 30/07/2026: item 41109 (IMG_0584.MOV) RESOLVE o fluxo "FERTILIZANTES IUF
ZVF", que já existia CURADO em projeto_fluxo_tarifas (com teto/distancia_km/
volume_ano_ktu definidos manualmente) mas estava "sem abertura de manobra
(pendente)". Ao contrário dos 2 fluxos novos acima (INSERT), este é um UPDATE que
preserva teto/distancia_km/volume_ano_ktu já cadastrados — mesmo padrão usado em
connect_arcelormittal_precos.py — e só atualiza tarifa_total/frete/acessorias/ipoa/
vigencia/fonte/cobertura, além de popular projeto_acessorias_abertas (que estava
vazia para este fluxo).

Idempotente: apaga e reinsere só os fluxos acima (não toca nos outros fluxos MOSAIC
nem em outros clientes). Deve rodar DEPOIS de add_projetos_clientes.py (DROP+CREATE
das tabelas de projeto) e DEPOIS de add_mosaic_precos_contratuais.py (cria a
tabela-fonte).

Uso:  python3 connect_mosaic_precos.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "MOSAIC"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0532-0533) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0532-0533) — abertura de manobra reajuste-a-reajuste"
FONTE_PJF_41109 = "F-LINK Preços Contratuais (vídeo IMG_0584) — vigência mais recente"
FONTE_PJA_41109 = "F-LINK Preços Contratuais (vídeo IMG_0584) — abertura de manobra"

FLUXOS_NOVOS = {
    39890: "ENXOFRE IUF ZVF",
    39889: "ROCHA FOS UMIDA ELC ZVF",
}

# fluxo JA existente/curado em projeto_fluxo_tarifas (pendente) que este item resolve
FLUXO_EXISTENTE_41109 = "FERTILIZANTES IUF ZVF"


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

        # Descarga entra na soma (pente-fino lote 3, nov/2026): tarifa = frete + descarga +
        # manobras + DP fecha centavo a centavo na vigência vigente; antes a Descarga ia pra
        # abertura mas ficava fora de `acessorias`, e o IPOA saía pela metade.
        acess = (descarga or 0) + (mo or 0) + (md or 0) + (dp_mrs or 0) + (dp_allmp or 0)
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

    # -------------------------------------------------------------------
    # item 41109 -> fluxo JA CURADO "FERTILIZANTES IUF ZVF" (era pendente)
    # UPDATE preservando teto/distancia_km/volume_ano_ktu; PJA so populada
    # (estava vazia). Mesmo padrao do connect_arcelormittal_precos.py.
    # -------------------------------------------------------------------
    rows_41109 = cur.execute(
        """SELECT item_ferroviario, origem, destino, produto, vigencia_inicial,
                  valor_tr_antt, tarifa_contrato, descarga_rs_t, frete_rs_t,
                  manobra_origem_rs_t, manobra_destino_rs_t,
                  direito_passagem_mrs_rs_t, direito_passagem_allmp_rs_t
           FROM mosaic_precos_contratuais WHERE item_ferroviario=41109
           ORDER BY vigencia_inicial DESC LIMIT 1"""
    ).fetchone()

    if rows_41109:
        (it, o, d, prod, vi, tr, tarifa, descarga, frete, mo, md, dp_mrs, dp_allmp) = rows_41109
        fluxo = FLUXO_EXISTENTE_41109
        existe = cur.execute(
            "SELECT 1 FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (CLIENTE, fluxo)
        ).fetchone()
        # Descarga entra na soma (pente-fino lote 3, nov/2026): tarifa = frete + descarga +
        # manobras + DP fecha centavo a centavo na vigência vigente; antes a Descarga ia pra
        # abertura mas ficava fora de `acessorias`, e o IPOA saía pela metade.
        acess = (descarga or 0) + (mo or 0) + (md or 0) + (dp_mrs or 0) + (dp_allmp or 0)
        ipoa = (acess / frete) if frete else 0.0
        cobertura = f"reajuste a reajuste (item {it}, C_2025_190) — vigência {vi}"

        if existe:
            cur.execute(
                """UPDATE projeto_fluxo_tarifas
                   SET tarifa_total=?, frete=?, acessorias=?, ipoa=?,
                       vigencia=?, fonte=?, cobertura=?
                   WHERE cliente=? AND fluxo=?""",
                (round(tarifa, 2), round(frete, 2) if frete is not None else None,
                 round(acess, 2), round(ipoa, 4), vi, FONTE_PJF_41109, cobertura,
                 CLIENTE, fluxo))
        else:
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
                 round(frete, 2) if frete is not None else None, round(acess, 2),
                 round(ipoa, 4), None, None, vi, FONTE_PJF_41109, cobertura))

        cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                    (CLIENTE, fluxo))
        n_pja_41109 = 0
        for nome, val in (("Manobra Origem", mo), ("Manobra Destino", md),
                          ("Direito de Passagem MRS", dp_mrs),
                          ("Direito de Passagem ALLMP", dp_allmp)):
            if val:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, nome, round(val, 2), FONTE_PJA_41109))
                n_pja_41109 += 1
        con.commit()
        print(f"  MOSAIC ({fluxo}, item 41109) RESOLVIDO: fluxo {'atualizado' if existe else 'inserido'} "
              f"em projeto_fluxo_tarifas (teto/km/volume preservados), {n_pja_41109} itens de "
              f"manobra/DP em projeto_acessorias_abertas.")
    else:
        print("  ! item 41109 não encontrado em mosaic_precos_contratuais — pulando resolução do "
              "fluxo FERTILIZANTES IUF ZVF.")

    con.close()


if __name__ == "__main__":
    main()
