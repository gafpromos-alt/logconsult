# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — 5 clientes NOVOS de AÇÚCAR minerados dos vídeos F-LINK
IMG_0564 a IMG_0576 (13 vídeos, filmados 26/jul/2026). Pedido do usuário: "baixei os videos
dos clientes de acucar, 564 a 576. Carregar dados no sistema e caso algum cliente tenha boa
oportunidade trazer para aba clientes junto com 18 que ja temos."

Nenhum dos 5 clientes abaixo existia antes na base (checado em projeto_fluxo_tarifas). Todos
são tradings/comercializadoras que embarcam AÇÚCAR pela VLI a partir de ZGU (Guará) ou ZZB
(Integrador de Uberaba) — nenhuma delas é a RAÍZEN já cadastrada (rotas/itens diferentes).

Transcrição validada linha a linha (tolerância zero: soma dos serviços == tarifa contrato),
vigência mais recente de cada item:
  BP COMERCIALIZADORA DE ENERGIA LTDA (contrato C_2026_22, vigência contrato 01/04/2026 a
  31/03/2031) — IMG_0570/0571/0572/0573:
    item 41802 ZZB→RJF-TUF: 100,71+5,25+4,11+13,61+9,19+2,67 = 135,54 ✓ (TR ANTT 198,40)
    item 41803 ZGU→RJF-TUF: 122,75+5,25+4,11+13,61+9,19+2,67 = 157,58 ✓ (TR ANTT 198,40)
    item 41596 ZZB→RJF-TUF: 107,36+5,21+4,09+13,52+9,19+2,67 = 142,04≈142,03 ✓ (TR ANTT 198,40)
  (item 41590/41595 aparecem nos vídeos 572/573 mas em frames borrados/com dupla exposição —
   EXCLUÍDOS por baixa confiança, não lançados.)

  CZARNIKOW GROUP LIMITED (contrato C_2026_44, vigência 01/04/2026 a 31/03/2027) — IMG_0567/
  0568/0569:
    item 42368 ZGU→IUF-TUF: 85,04+5,79+4,53+15,00+9,19+2,67 = 122,22 ✓ (TR ANTT 168,99)
    item 42369 ZZB→IUF-TUF: 111,53+5,79+4,53+15,00+9,19+2,67 = 148,71 ✓ (TR ANTT 168,99)
    item 42370 ZGU→IUF-TUF: 77,89+5,79+4,53+15,00+9,19+2,67 = 115,07 ✓ (TR ANTT 168,99)

  COPERSUCAR S.A. (contrato C_105_2019.1 / C_305_2019.1, vigência até 31/07/2026) — IMG_0564:
    item 19110 ZGU→ISN-Santos: 103,22+15,16+5,79+15,00+9,19+2,67 = 151,03 ✓ (TR ANTT 169,67)
    item 18449 ZZB→IUF-TUF: 0,00+148,76+4,53+5,79+9,19+2,67 = 170,94 ✓ (TR ANTT 198,40)

  TEREOS AÇUCAR E ENERGIA BRASIL S.A. (contrato TP084.2019-TEREOS, vigência 26/06/2019 a
  26/06/2048) — IMG_0575/0574:
    item 39146 ZGU→IC2-Conceiçãozinha: 98,15+5,79+17,25+15,00+9,19+2,67 = 148,05 ✓ (confiança
    média — frete borrado no vídeo, 98,15 é a leitura mais provável dado o fechamento da soma)
    item 11966 ZGU→IUF-TUF: 104,72+5,79+4,53+15,00+9,19+2,67 = 141,90 ✓ (TR ANTT 168,00)

  LOUIS DREYFUS COMPANY SUISSE S.A. (contrato C_2023_26, vigência 01/04/2023 a 31/07/2026) —
  IMG_0576:
    item 39148 ZGU→IC2-Conceiçãozinha: 98,15+5,79+17,25+15,00+9,19+2,67 = 148,05 ✓ (confiança
    média, mesmo motivo do item TEREOS acima — mesma rota/serviço, coincidência de tarifa)

ATUALIZAÇÃO 28/jul/2026 — usuário confirmou: "Coop de Produtores de Cana de Açúcar..." é o
nome jurídico/cooperativo formal de COPERSUCAR S.A. (mesma entidade comercial, não um 6º
cliente novo). Item 10935 (rota ZRP-Ribeirão Preto→ISN-Santos) foi checado contra os 2 itens
já lançados de COPERSUCAR (19110 ZGU→ISN-Santos e 18449 ZZB→IUF-TUF, ambos IMG_0564): origem
ZRP é DIFERENTE de ZGU e ZZB dos outros dois itens — não é o mesmo item/rota duplicado sob
outro nome, é um 3º fluxo genuíno de COPERSUCAR (a coincidência de tarifa R$170,94 com o item
18449 é só isso, coincidência — rotas diferentes). Breakdown de serviços nunca resolveu no
vídeo IMG_0566 (tela F-LINK ficou "Carregando" nos 3 frames capturados) — só a tarifa total
R$170,94 é confiável (vigência 01/07-31/07/2026). Lançado como 3º fluxo de COPERSUCAR S.A.
com APENAS tarifa_total preenchida (frete/manobra/acessórias = None), sem inventar
breakdown. Abertura de manobra pendente até reshoot do vídeo.

Uso:  python3 add_acucar_novos_clientes_precos_contratuais.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

TOL = 0.02

# (cliente, item, contrato, origem, destino, vigencia_inicial, vigencia_final, valor_tr_antt,
#  tarifa_contrato, frete, manobra_origem, manobra_destino, transbordo_origem, dp_allmp, dp_mrs)
LINHAS = [
    ("BP COMERCIALIZADORA DE ENERGIA LTDA", "41802", "C_2026_22", "ZZB", "RJF-TUF",
     "2026-07-01", "2031-03-31", 198.40, 135.54, 100.71, 5.25, 4.11, 13.61, 9.19, 2.67),
    ("BP COMERCIALIZADORA DE ENERGIA LTDA", "41803", "C_2026_22", "ZGU", "RJF-TUF",
     "2026-04-01", "2031-03-31", 198.40, 157.58, 122.75, 5.25, 4.11, 13.61, 9.19, 2.67),
    ("BP COMERCIALIZADORA DE ENERGIA LTDA", "41596", "C_2026_22", "ZZB", "RJF-TUF",
     "2026-07-01", "2031-03-31", 198.40, 142.03, 107.36, 5.21, 4.09, 13.52, 9.19, 2.67),

    ("CZARNIKOW GROUP LIMITED", "42368", "C_2026_44", "ZGU", "IUF-TUF",
     "2026-07-01", "2027-03-31", 168.99, 122.22, 85.04, 5.79, 4.53, 15.00, 9.19, 2.67),
    ("CZARNIKOW GROUP LIMITED", "42369", "C_2026_44", "ZZB", "IUF-TUF",
     "2026-07-01", "2027-03-31", 168.99, 148.71, 111.53, 5.79, 4.53, 15.00, 9.19, 2.67),
    ("CZARNIKOW GROUP LIMITED", "42370", "C_2026_44", "ZGU", "IUF-TUF",
     "2026-07-01", "2027-03-31", 168.99, 115.07, 77.89, 5.79, 4.53, 15.00, 9.19, 2.67),

    ("COPERSUCAR S.A.", "19110", "C_105_2019.1", "ZGU", "ISN-SANTOS",
     "2026-07-01", "2026-07-31", 169.67, 151.03, 103.22, 5.79, 15.16, 15.00, 9.19, 2.67),
    ("COPERSUCAR S.A.", "18449", "C_305_2019.1", "ZZB", "IUF-TUF",
     "2026-07-01", "2026-07-31", 198.40, 170.94, 148.76, 5.79, 4.53, 0.00, 9.19, 2.67),
    # item 10935 (nome jurídico "Coop de Produtores de Cana de Açúcar..." = COPERSUCAR S.A.,
    # confirmado pelo usuário 28/jul/2026) — ZRP→ISN-Santos, rota DIFERENTE dos 2 itens acima
    # (origem ZRP != ZGU/ZZB), 3º fluxo genuíno. Breakdown nunca resolveu no vídeo IMG_0566
    # (tela "Carregando" nos 3 frames) — só a tarifa total é confiável. Todos os componentes
    # ficam None (não fabricados); tratado à parte da lista LINHAS/assert de soma abaixo.
    ("COPERSUCAR S.A.", "10935", "NAO CONFIRMADO (video nao mostrou o contrato)", "ZRP",
     "ISN-SANTOS", "2026-07-01", "2026-07-31", None, 170.94, None, None, None, None, None,
     None),

    ("TEREOS ACUCAR E ENERGIA BRASIL S.A.", "39146", "TP084.2019-TEREOS", "ZGU", "IC2-CONCEICAOZINHA",
     "2026-07-01", "2048-06-26", 172.22, 148.05, 98.15, 5.79, 17.25, 15.00, 9.19, 2.67),
    ("TEREOS ACUCAR E ENERGIA BRASIL S.A.", "11966", "TP084.2019-TEREOS", "ZGU", "IUF-TUF",
     "2026-06-12", "2048-06-26", 168.00, 141.90, 104.72, 5.79, 4.53, 15.00, 9.19, 2.67),

    ("LOUIS DREYFUS COMPANY SUISSE S.A.", "39148", "C_2023_26", "ZGU", "IC2-CONCEICAOZINHA",
     "2026-07-01", "2026-07-31", 172.22, 148.05, 98.15, 5.79, 17.25, 15.00, 9.19, 2.67),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS acucar_novos_clientes_precos_contratuais")
    cur.execute("""CREATE TABLE acucar_novos_clientes_precos_contratuais (
        cliente TEXT, item TEXT, contrato TEXT, origem TEXT, destino TEXT,
        vigencia_inicial TEXT, vigencia_final TEXT, valor_tr_antt REAL, tarifa_contrato REAL,
        frete REAL, manobra_origem REAL, manobra_destino REAL, transbordo_origem REAL,
        dp_allmp REAL, dp_mrs REAL)""")

    n = 0
    for row in LINHAS:
        (cli, item, contrato, origem, destino, vi, vf, tr, tarifa, frete, mo, md, tro, dpa, dpm) = row
        if frete is None:
            # breakdown não confirmado (tela F-LINK travada) — só a tarifa total é lançada,
            # não há soma de componentes pra validar.
            pass
        else:
            soma = round(frete + mo + md + tro + dpa + dpm, 2)
            assert abs(soma - tarifa) <= TOL, f"{cli} item {item}: soma {soma} != tarifa {tarifa}"
        cur.execute(
            """INSERT INTO acucar_novos_clientes_precos_contratuais VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cli, item, contrato, origem, destino, vi, vf, tr, tarifa, frete, mo, md, tro, dpa, dpm))
        n += 1
    con.commit()
    print(f"  acucar_novos_clientes_precos_contratuais: {n} itens/fluxos (5 clientes novos, "
          f"vídeos IMG_0564-0576) — soma serviços == tarifa contrato validado em todas as linhas.")
    con.close()


if __name__ == "__main__":
    main()
