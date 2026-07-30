# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — conecta os 12 fluxos de AÇÚCAR dos 5 clientes NOVOS
(acucar_novos_clientes_precos_contratuais, minerado de IMG_0564-0576) ao Painel do Cliente.
(12º fluxo = item 10935/COPERSUCAR, adicionado 28/jul/2026 — ver docstring do script-fonte.)

Cria fluxos NOVOS (rotas/clientes inexistentes na base antes destes vídeos) com abertura de
manobra completa (frete + manobra origem + manobra destino + transbordo origem + direito de
passagem ALLMP + direito de passagem MRS) — mesmo padrão de connect_selecta_farelo_precos.py.

Cada item ferroviário vira 1 fluxo "AÇUCAR <ORIGEM> <DESTINO>"; quando o mesmo cliente tem
2 itens na mesma rota (ex.: BP tem 2 itens ZZB→RJF-TUF), o fluxo leva o número do item no nome
pra não colidir (ex.: "AÇUCAR ZZB RJF-TUF (41802)" / "AÇUCAR ZZB RJF-TUF (41596)").

Volume: sem dado em volume_hist pra nenhum destes 5 clientes/rotas (checado — açúcar é
categoria de carga nova na base, sem histórico de embarque registrado ainda). volume_ano_ktu
fica None em todos os 11 fluxos; sinalizado na cobertura.

Idempotente: apaga e reinsere só os fluxos destes 5 clientes. Roda depois de
add_acucar_novos_clientes_precos_contratuais.py (cria a tabela-fonte). Chamado no fim de
add_projetos_clientes.py, logo após connect_selecta_farelo_precos.py.

Uso:  python3 connect_acucar_novos_clientes_precos.py
"""
import collections
import pathlib
import sqlite3
import sys

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
sys.path.insert(0, str(BASE))
from canon import canon  # noqa: E402
from add_demais_clientes_fluxos_completos import _DESTINO_ALIAS  # noqa: E402

FONTE = "F-LINK Preços Contratuais (vídeos IMG_0564-0576) — vigência mais recente"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    t = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND "
        "name='acucar_novos_clientes_precos_contratuais'").fetchone()
    if not t:
        print("  ! acucar_novos_clientes_precos_contratuais não existe — rode "
              "add_acucar_novos_clientes_precos_contratuais.py antes. Pulando.")
        con.close()
        return

    rows = cur.execute(
        """SELECT cliente, item, contrato, origem, destino, vigencia_final, valor_tr_antt,
                  tarifa_contrato, frete, manobra_origem, manobra_destino, transbordo_origem,
                  dp_allmp, dp_mrs
           FROM acucar_novos_clientes_precos_contratuais""").fetchall()

    # detecta rotas duplicadas por cliente (mesmo origem+destino, item diferente)
    contagem = collections.Counter((r[0], r[3], r[4]) for r in rows)

    clientes = set()
    nfluxos = 0
    nitens = 0
    for row in rows:
        (cliente_raw, item, contrato, origem, destino, vf, tr, tarifa, frete, mo, md, tro,
         dpa, dpm) = row
        # achado 28/jul/2026 (regressão): acucar_novos_clientes_precos_contratuais grava o
        # nome jurídico completo (ex. "CZARNIKOW GROUP LIMITED"), mas o Painel do Cliente e o
        # portfólio genérico (add_demais_clientes_fluxos_completos.py) usam o nome canônico
        # curto (canon() -> "CZARNIKOW"). Sem canonizar aqui, cada rerun do pipeline recriava
        # um cliente "novo" com nome jurídico duplicado ao lado do canônico, e o DELETE (que
        # comparava pelo nome jurídico) nunca alcançava as linhas já canonizadas — duplicando
        # o cliente no dropdown "todos os clientes" a cada rerun.
        cliente = canon(cliente_raw)
        rota_dup = contagem[(cliente_raw, origem, destino)] > 1
        fluxo = f"ACUCAR {origem} {destino}" + (f" ({item})" if rota_dup else "")

        cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
                    (cliente, fluxo))
        cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                    (cliente, fluxo))
        # achado 28/jul/2026: add_demais_clientes_fluxos_completos.py roda ANTES deste script
        # (pipeline) e, na 1ª vez que um cliente açúcar aparece na base (projeto_fluxo_tarifas
        # acabou de ser recriada do zero pelo to_sql(if_exists='replace') em add_projetos_
        # clientes.py), não vê nenhum curado ainda — insere a rota com o código curto genérico
        # (ex. "ACUCAR ZGU ISN"). Sem este delete extra, o vídeo (nome composto "ACUCAR ZGU
        # ISN-SANTOS") convive com o genérico pra MESMA rota física — duplicata visível no
        # Painel do Cliente. Remove o genérico da mesma rota antes de inserir o real.
        destino_curto = _DESTINO_ALIAS.get(destino, destino.split("-")[0])
        fluxo_generico = f"ACUCAR {origem} {destino_curto}"
        if fluxo_generico != fluxo:
            cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
                        (cliente, fluxo_generico))
            cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                        (cliente, fluxo_generico))

        if frete is None:
            # breakdown não confirmado (item 10935, vídeo IMG_0566 travado em "Carregando") —
            # só a tarifa total é lançada, sem inventar frete/acessórias/ipoa.
            acess = None
            ipoa = None
            frete_db = None
            cobertura = (f"item {item}, {contrato} — nome jurídico/cooperativo de COPERSUCAR "
                         f"S.A. (confirmado pelo usuário 28/jul/2026: 'Coop de Produtores de "
                         f"Cana...' = Copersucar); 3º fluxo do cliente, rota ZRP→ISN-Santos "
                         f"distinta dos outros 2 itens (ZGU/ZZB). Abertura de manobra "
                         f"PENDENTE — tela F-LINK não renderizou o detalhamento (vídeo "
                         f"IMG_0566, sempre 'Carregando' nos 3 frames capturados); apenas "
                         f"tarifa total confirmada. Sem histórico de volume em volume_hist.")
        else:
            acess = round(mo + md + tro + dpa + dpm, 2)
            ipoa = round(acess / frete, 4) if frete else 0.0
            frete_db = round(frete, 2)
            cobertura = (f"reajuste a reajuste (item {item}, {contrato}) — fluxo novo, minerado "
                         f"dos vídeos F-LINK IMG_0564-0576 (cliente sem nenhum fluxo na base antes "
                         f"deste lote); sem histórico de volume em volume_hist (categoria AÇÚCAR "
                         f"nova na base)")
        cur.execute(
            """INSERT INTO projeto_fluxo_tarifas
               (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cliente, fluxo, tarifa, round(tr, 2) if tr else None, frete_db, acess, ipoa,
             None, None, vf, FONTE, cobertura))
        nfluxos += 1
        clientes.add(cliente)

        if frete is None:
            continue  # sem componentes confirmados — nada pra inserir em acessorias_abertas

        for nome, val in (
            ("Frete", frete),
            ("Manobra Origem", mo),
            ("Manobra Destino", md),
            ("Transbordo Origem", tro),
            ("Direito de Passagem ALLMP", dpa),
            ("Direito de Passagem MRS", dpm),
        ):
            if val is not None and val > 0 and nome != "Frete":
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas
                       (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (cliente, fluxo, nome, round(val, 2), FONTE))
                nitens += 1

    con.commit()
    print(f"  AÇÚCAR (5 clientes novos): {nfluxos} fluxos, {nitens} itens de abertura de "
          f"manobra/direito de passagem — clientes: {', '.join(sorted(clientes))}.")
    con.close()


if __name__ == "__main__":
    main()
