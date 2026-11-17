# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conecta o histórico de preços contratuais da APERAM
(tabela aperam_precos_contratuais, minerada dos vídeos F-LINK IMG_0480-0490) ao Painel do
Cliente. Cliente NOVO — não existia antes no banco.

Para cada item ferroviário, usa a vigência MAIS RECENTE (maior vigencia_inicial) como a
situação tarifária atual:
- projeto_fluxo_tarifas (PJF): tarifa_total=tarifa_contrato, TETO = Valor TR (ANTT) — vem
  direto da fonte, frete, acessorias = manobra_origem + manobra_destino + outros, ipoa =
  acessorias/frete. distancia_km e volume_ano_ktu ficam NULL (sem dado de km/volume minerado
  dos vídeos). Se a vigência mais recente não tiver o detalhe de serviços carregado na tela
  (frete=NULL — caso de parte do item 17395), frete/acessorias/ipoa ficam NULL também, mas a
  linha ainda é gravada (tarifa_total e teto são conhecidos).
- projeto_acessorias_abertas (PJA): MANOBRA ORIGEM, MANOBRA DESTINO e (quando existir)
  TRANSBORDO DESTINO da vigência mais recente que efetivamente tem o detalhe carregado —
  se a vigência mais recente não tem detalhe (NULL), cai para a vigência mais recente
  seguinte que tenha, para não perder a abertura de manobra.

Idempotente: apaga e reinsere só as linhas da APERAM (nos dois: PJF e PJA). Deve rodar DEPOIS
de add_projetos_clientes.py (que faz DROP+CREATE dessas tabelas) e DEPOIS de
add_aperam_precos_contratuais.py (que cria a tabela-fonte).

Uso:  python3 connect_aperam_precos.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
CLIENTE = "APERAM"
FONTE_PJF = "F-LINK Preços Contratuais (vídeos IMG_0480-0490) — vigência mais recente"
FONTE_PJA = "F-LINK Preços Contratuais (vídeos IMG_0480-0490) — abertura de manobra reajuste-a-reajuste"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # tabela-fonte existe? (senão, não faz nada — evita quebrar rebuild sem a mineração)
    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='aperam_precos_contratuais'"
    ).fetchone()
    if not t:
        print("  ! aperam_precos_contratuais não existe — rode add_aperam_precos_contratuais.py antes. Pulando conexão.")
        con.close()
        return

    # km por rota (enriquecimento, se existir cadastro de ipoa_teto para APERAM — senão fica NULL)
    km_por = {}
    for o, d, prod, km in cur.execute(
        """SELECT origem, destino, produto, km_rota FROM ipoa_teto
           WHERE UPPER(cliente) LIKE '%APERAM%' AND km_rota IS NOT NULL"""):
        km_por.setdefault((o, d, str(prod).upper()), km)

    itens = [r[0] for r in cur.execute("SELECT DISTINCT item_ferroviario FROM aperam_precos_contratuais")]

    # vigência mais recente por item (a situação atual — para tarifa_total/teto)
    atuais = []
    # vigência mais recente COM detalhe de serviços carregado, por item (para a abertura PJA)
    atuais_com_detalhe = []
    for it in itens:
        row = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t
               FROM aperam_precos_contratuais WHERE item_ferroviario=?
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        atuais.append(row)

        row_detalhe = cur.execute(
            """SELECT item_ferroviario, contrato, origem, destino, produto,
                      vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                      frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t, outros_rs_t
               FROM aperam_precos_contratuais
               WHERE item_ferroviario=? AND frete_rs_t IS NOT NULL
               ORDER BY vigencia_inicial DESC LIMIT 1""", (it,)).fetchone()
        if row_detalhe:
            atuais_com_detalhe.append(row_detalhe)

    # NAO apaga todo o cliente: a APERAM tem um portfólio mais amplo (16 rotas,
    # incluindo CALCARIO BRITAD/DOLOMITA/PRO SIDERURGICO VIC-VMR e VMR-VAZ) já
    # curado em projeto_fluxo_tarifas via tarifas_praticadas/ipoa_teto/
    # fluxos_servico, que este script NAO minera e NAO deve destruir. Mesmo
    # padrão preservador do connect_arcelormittal_precos.py: fluxo já
    # existente -> UPDATE só dos campos tarifários (preserva teto/km/volume
    # quando já curados); fluxo novo (rota sem portfólio prévio) -> INSERT.
    existentes = {}
    for fluxo, teto, km, vol in cur.execute(
            """SELECT fluxo, teto, distancia_km, volume_ano_ktu
               FROM projeto_fluxo_tarifas WHERE cliente=?""", (CLIENTE,)):
        existentes[fluxo] = dict(teto=teto, distancia_km=km, volume_ano_ktu=vol)

    npjf = npja = n_update = n_insert = 0
    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, outros) in atuais:
        fluxo = f"{prod} {o} {d}"
        if frete is not None:
            acess = (mo or 0) + (md or 0) + (outros or 0)
            ipoa = (acess / frete) if frete else 0.0
        else:
            acess = None
            ipoa = None
        cobertura = f"reajuste a reajuste desde 2025 (item {it}, {contrato})"

        if fluxo in existentes:
            cur.execute(
                """UPDATE projeto_fluxo_tarifas
                   SET tarifa_total=?, frete=?, acessorias=?, ipoa=?,
                       vigencia=?, fonte=?, cobertura=?
                   WHERE cliente=? AND fluxo=?""",
                (round(tarifa, 2), round(frete, 2) if frete is not None else None,
                 round(acess, 2) if acess is not None else None,
                 round(ipoa, 4) if ipoa is not None else None,
                 vf, FONTE_PJF, cobertura, CLIENTE, fluxo))
            n_update += 1
        else:
            km = km_por.get((o, d, str(prod).upper()))
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (CLIENTE, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
                 round(frete, 2) if frete is not None else None,
                 round(acess, 2) if acess is not None else None,
                 round(ipoa, 4) if ipoa is not None else None,
                 round(km, 1) if km else None, None, vf, FONTE_PJF, cobertura))
            n_insert += 1
        npjf += 1

    # limpa PJA só dos fluxos que serão reescritos (não toca acessórias de
    # outras rotas da APERAM que não foram mineradas aqui)
    fluxos_tocados = {f"{prod} {o} {d}" for (_it, _c, o, d, prod, *_r) in atuais}
    for fluxo in fluxos_tocados:
        cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                    (CLIENTE, fluxo))

    for (it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, mo, md, outros) in atuais_com_detalhe:
        fluxo = f"{prod} {o} {d}"
        for item_nome, val in (("MANOBRA ORIGEM", mo), ("MANOBRA DESTINO", md), ("TRANSBORDO/OUTROS", outros)):
            if val is not None and val != 0:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (CLIENTE, fluxo, item_nome, round(val, 2), FONTE_PJA))
                npja += 1

    con.commit()
    print(f"  APERAM conectada: {n_update} fluxos atualizados + {n_insert} fluxos novos em "
          f"projeto_fluxo_tarifas (demais rotas do portfólio preservadas), {npja} itens de "
          f"manobra em projeto_acessorias_abertas (fonte: preços contratuais F-LINK).")
    con.close()


if __name__ == "__main__":
    main()
