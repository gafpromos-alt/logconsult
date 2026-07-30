# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — replica pro RESTANTE da base o modelo aplicado na SELECTA/
AGREX (jul/2026): trazer TODOS os fluxos reais da base pro Painel do Cliente, não só o(s)
fluxo(s) curado(s). Pedido explícito do usuário: "replicar modelo da Selecta para todos os
clientes, com exceção a LD Celulose" (LD CELULOSE fica intocada — mantido o que já foi
definido na mineração F-LINK).

Dois modos por cliente, decididos pela natureza do(s) fluxo(s) curado(s) hoje:
- REPLACE: o(s) fluxo(s) atuais são uma MÉDIA genérica sem rota própria (nome = cliente, ou
  código de região/estado) — não representam nenhuma rota real específica, então são
  SUBSTITUÍDOS pelo portfólio completo por rota (mesmo tratamento que a AGREX recebeu).
  Candidatos: CARAMURU (flow="CARAMURU"), NOVA AGRI (flows="TO"/"MT", códigos de estado).
- ADD: os fluxos atuais já representam rotas específicas reais (nome "PRODUTO ORIGEM
  DESTINO", inclusive os minerados do F-LINK reajuste-a-reajuste) — PRESERVADOS intactos,
  só entram as rotas que a base tem e ainda não estão cobertas (mesmo tratamento da SELECTA).
  Candidatos: MOSAIC, CENIBRA, ARCELORMITTAL, APERAM, RAIZEN, CMOC, SUZANO.
  (GERDAU, USIMINAS, IPIRANGA, VIBRA, ALESAT, PETROBAHIA, PETROLEO SABBA, PETRONAC já
  cobrem 100% das rotas reais encontradas em tarifas_praticadas/ipoa_teto — sem gap, não
  precisam de ação.)

Cobertura "já coberta" é determinada fazendo o parse do nome de cada fluxo curado existente
(mesma convenção do fluxoRota() do front: últimos 2 tokens = origem/destino, resto = produto)
e comparando contra o universo real de tarifas_praticadas ∪ ipoa_teto (canonizado via
canon.py). Rotas com origem==destino (auto-loop, artefato de dado) são descartadas.

Fonte por rota nova, na ordem de preferência: tarifas_praticadas (frete_trackage/demais_
servicos/teto-ratio) > ipoa_teto (frete/acessorias/teto absoluto) — dedupe por (origem,
destino,produto) pegando o de MAIOR total entre as duas fontes. Abertura por serviço vem de
fluxos_servico (item de maior soma) quando existir. Volume do último ano realizado em
volume_hist.

Achado do usuário (20/jul/2026, "algumas somas das manobras RAIZEN não fecham com
acessórias"): tarifas_praticadas/ipoa_teto e fluxos_servico são extrações INDEPENDENTES da
mesma fonte, e o item "vencedor" de cada uma pode ser um contrato/vigência diferente (mesmo
quando o Nº do item bate — achado: item 41356 RAIZEN tem frete R$59,53 em tarifas_praticadas
mas R$46,43 em fluxos_servico, o mesmo item, valores diferentes — extrações divergentes, não
o mesmo registro fielmente replicado). Resultado: a soma dos itens de manobra abertos não
fechava com a acessória total do cabeçalho (chegou a bater só 1/3 do valor em alguns casos).
Fix: quando existe abertura (fluxos_servico) pra uma rota, o frete/acessórias/total do
cabeçalho passam a ser DERIVADOS da própria abertura (FRETE do serviço + soma dos demais
serviços) — nunca mais de tarifas_praticadas/ipoa_teto nesse caso — garantindo fechamento
exato por construção. Sem abertura, mantém o total de tarifas_praticadas/ipoa_teto como
antes (única fonte disponível).

Idempotente: nos clientes REPLACE, apaga e reinsere tudo. Nos ADD, apaga e reinsere só as
linhas cujo fluxo NÃO está entre os curados originais (preserva os curados). Roda DEPOIS de
add_projetos_clientes.py.

Uso:  python3 add_demais_clientes_fluxos_completos.py
"""
import pathlib
import re
import sqlite3
import sys

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
sys.path.insert(0, str(BASE))
from canon import canon  # noqa: E402

FONTE_PJF = "tarifas_praticadas + ipoa_teto (maior total por rota) + fluxos_servico — portfólio completo"
FONTE_PJA = "fluxos_servico (abertura real por serviço do item mais caro da rota)"

NOME_SERV = {
    "MANOBRA ORIGEM": "Manobra Origem",
    "MANOBRA DESTINO": "Manobra Destino",
    "TRANSBORDO ORIGEM": "Transbordo Origem",
    "TRANSBORDO DESTINO": "Transbordo Destino",
    "DIREITO DE PASSAGEM": "Direito de Passagem",
    "MANOBRA CONEXAO CHEIO": "Manobra Conexão Cheio",
}

# cliente (nome canônico já usado em projeto_fluxo_tarifas) -> modo
CLIENTES = {
    "CARAMURU": "replace",
    "NOVA AGRI": "replace",
    "MOSAIC": "add",
    "CENIBRA": "add",
    "ARCELORMITTAL": "add",
    "APERAM": "add",
    "RAIZEN": "add",
    "SUZANO": "add",
    "GERDAU": "add",     # tem dado F-LINK item-a-item rico (connect_gerdau_precos.py) — preservado
    "IPIRANGA": "add",   # idem (connect_ipiranga_precos.py)
    "USIMINAS": "add",   # portfólio top-25 por %teto (add_projetos_clientes_novos.py) — preservado
    "ALZ": "add",        # cliente NOVO no Painel do Cliente (20/jul/2026) — sem curados prévios,
                          # "add" com lista vazia = portfólio completo direto (5 rotas reais)
    "VIBRA": "add",      # idem — cliente novo, sem curados prévios (17 rotas reais)
    "ALE": "add",        # idem — cliente novo, sem curados prévios (10 rotas reais)
    # CMOC: gap era falso positivo (item 12620 EYC->IFA "ROCHA FOSF SECA" já é o mesmo
    # registro-fonte do fluxo curado "ROCHA EYC IFA" — nome truncado, não rota nova).
    # Açúcar F-LINK (28/jul/2026, IMG_0564-0576): os fluxos curados já são rota-específica
    # ("PRODUTO ORIGEM DESTINO-TERMINAL", não nome genérico do cliente) — mesmo critério
    # documentado acima pra modo ADD (MOSAIC/CENIBRA/etc.), NÃO o critério de modo REPLACE
    # (que é só pra fluxo="CLIENTE"/código de região, sem rota própria). "add" preserva os
    # 3/3/3/2/1 fluxos video-confirmados intactos e só completa com rotas reais adicionais
    # que a base tiver (tarifas_praticadas/ipoa_teto/fluxos_servico) e os vídeos não cobriram.
    "BP COMERCIALIZADORA ENERGIA": "add",
    "CZARNIKOW": "add",
    "COPERSUCAR": "add",
    "TEREOS": "add",
    "LDC": "add",
}


_FTOK_SINONIMOS = {"PRO": "PRODUTO", "TORETES": "TORETE"}
# PRO→PRODUTO — achado 22/jul/2026: tarifas_praticadas/ipoa_teto gravam
# "PRO SIDERURGICO" (abreviado) pra GERDAU/ARCELORMITTAL/USIMINAS/APERAM, mas volume_hist grava
# "PRODUTO SIDERURGICO" por extenso — sem o sinônimo, o match falhava pra TODAS as rotas "PRO
# SIDERURGICO" desses 4 clientes, caindo no fallback genérico (mesmo volume repetido em toda
# rota — sintoma reportado pelo usuário: "volumes da APERAM estão replicados").
# TORETES→TORETE — achado 30/jul/2026 (CENIBRA, "volume dos fluxos de torete não aparecem na
# simulação de manobras"): singular/plural varia entre as fontes da mesma mercadoria física
# (a curadoria/planilha grava "TORETE", a mineração F-LINK grava "TORETES" — divergência
# confirmada dentro deste próprio repo, add_cenibra_precos_contratuais.py vs FLUXO_NOME do
# connect) — sem o sinônimo, o volume_hist de qualquer variante nunca casa com a rota de
# torete e o volume_ano_ktu fica None. Sinônimo de GRAFIA da mesma mercadoria (nunca pooling
# de produtos diferentes): nenhuma outra família de produto da base começa com "TORETE".


def _ftok(produto):
    """Primeiro token de um produto (mesma convenção de famTok/pcNormProd no front) — casa
    o produto genérico do fluxo (ex. "ACUCAR") com a mercadoria mais específica gravada em
    volume_hist (ex. "ACUCAR CRISTAL/REF.A GRANEL"), sem misturar produtos DIFERENTES que só
    compartilham prefixo de uma palavra (ex. GASOLINA nunca casa com OLEO DIESEL)."""
    tok = re.split(r"[ \-]", str(produto or "").upper())[0]
    return _FTOK_SINONIMOS.get(tok, tok)


# achado 28/jul/2026 (curadoria açúcar BP/CZARNIKOW/COPERSUCAR/TEREOS/LDC): os conectores
# F-LINK desses clientes gravam o fluxo como "PRODUTO ORIGEM DESTINO-TERMINAL" (destino =
# código curto + nome do terminal/porto, ex. "IUF-TUF", "ISN-SANTOS", "IC2-CONCEICAOZINHA" —
# este último com typo, ICZ vira IC2) em vez do código curto puro que tarifas_praticadas/
# ipoa_teto gravam (ex. "IUF", "ISN", "ICZ"). Sem este alias, parse_fluxo() nunca reconhece
# a rota já curada como "coberta" e o portfólio genérico duplica a mesma rota com um 2º fluxo.
_DESTINO_ALIAS = {
    "IUF-TUF": "IUF",
    "ISN-SANTOS": "ISN",
    "IC2-CONCEICAOZINHA": "ICZ",
}


def parse_fluxo(fluxo):
    """'PRODUTO ORIGEM DESTINO' -> (origem, destino, produto) | None se não parsear (nome
    genérico tipo 'CARAMURU' ou código de região tipo 'TO'). Normaliza a tag "(ITEM N)" que
    alguns conectores (GERDAU, SELECTA) usam pra distinguir itens ferroviários na mesma
    rota — sem isso, cada item vira uma rota "diferente" pro comparador e gera falso-positivo
    de gap (a rota já está coberta, só com mais de um item/contrato registrado nela). Também
    normaliza a tag "(NNNNN)" (item bruto entre parênteses, sem prefixo "ITEM") usada pelos
    conectores açúcar F-LINK (BP/CZARNIKOW), e o alias de destino _DESTINO_ALIAS acima."""
    s = re.sub(r"\s*\(ITEM \d+\)\s*", " ", str(fluxo).strip())
    s = re.sub(r"\s*\(\d+\)\s*$", "", s).strip()
    toks = s.split()
    if len(toks) < 3:
        return None
    destino, origem = toks[-1], toks[-2]
    destino = _DESTINO_ALIAS.get(destino, destino)
    produto = " ".join(toks[:-2]).upper().strip()
    return (origem, destino, produto)


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    total_ins = total_pja = total_rm = 0
    for cliente, modo in CLIENTES.items():
        # ---- rotas já cobertas hoje (parse dos fluxos curados) ----
        curados = [r[0] for r in cur.execute(
            "SELECT fluxo FROM projeto_fluxo_tarifas WHERE cliente=?", (cliente,))]
        cobertas = set(filter(None, (parse_fluxo(f) for f in curados)))

        # ---- universo real: tarifas_praticadas (preferida) + ipoa_teto ----
        rotas = {}
        for item, cli_raw, o, d, prod, frete, acess, teto_ratio, ipoa, vig, km in cur.execute(
            """SELECT item, cliente, origem, destino, UPPER(produto), frete_trackage,
                      demais_servicos, teto, ipoa, vigencia, km_rota FROM tarifas_praticadas"""):
            if canon(cli_raw) != cliente or o == d:
                continue
            k = (o, d, prod)
            total = (frete or 0) + (acess or 0)
            teto_abs = (frete / teto_ratio) if (frete and teto_ratio and teto_ratio > 0) else None
            if k not in rotas or total > rotas[k]["total"]:
                rotas[k] = dict(item=item, origem=o, destino=d, produto=prod, frete=frete,
                                acess=acess, total=total, teto=teto_abs, ipoa=ipoa,
                                vig=str(vig)[:10] if vig else None, km=km, fonte="tarifas_praticadas")
        for item, cli_raw, o, d, prod, ipoa, acess, frete, teto, total, km in cur.execute(
            """SELECT item, cliente, origem, destino, UPPER(produto), ipoa, acessorias,
                      frete, teto, total, km_rota FROM ipoa_teto"""):
            if canon(cli_raw) != cliente or o == d or total is None:
                continue
            k = (o, d, prod)
            if k not in rotas or total > rotas[k]["total"]:
                rotas[k] = dict(item=item, origem=o, destino=d, produto=prod, frete=frete,
                                acess=acess, total=total, teto=teto, ipoa=ipoa, vig=None,
                                km=km, fonte="ipoa_teto")

        # ---- abertura por rota (fluxos_servico, item de maior soma de serviços) ----
        # também serve de 3ª fonte de DESCOBERTA de rota (não só abertura): achado do
        # usuário (22/jul/2026, unificação MOSAIC=VALE FERTILIZANTES no canon.py) — rotas
        # como ICZ→ZVF ENXOFRE e VTU→ZVF FERTILIZANTES só existem em fluxos_servico, nunca
        # apareceram em tarifas_praticadas/ipoa_teto pra esse cliente. Sem essa 3ª fonte,
        # "trazer TODOS os fluxos" (pedido do usuário) ficava incompleto silenciosamente.
        servs = {}
        for it, cli_raw, o, d, prod, sv, tar in cur.execute(
            """SELECT itens, cliente, origem, destino, UPPER(produto), UPPER(servicos), tarifa
               FROM fluxos_servico WHERE tarifa IS NOT NULL"""):
            if canon(cli_raw) != cliente or o == d:
                continue
            servs.setdefault((o, d, prod), {}).setdefault(it, {})
            servs[(o, d, prod)][it][sv] = servs[(o, d, prod)][it].get(sv, 0.0) + tar
        abertura = {}
        for k, itens in servs.items():
            it_best = max(itens, key=lambda i: sum(itens[i].values()))
            abertura[k] = itens[it_best]
            if k not in rotas:
                frete_sv = abertura[k].get("FRETE", 0.0)
                acess_sv = sum(v2 for sv2, v2 in abertura[k].items() if sv2 != "FRETE")
                rotas[k] = dict(item=it_best, origem=k[0], destino=k[1], produto=k[2],
                                 frete=frete_sv, acess=acess_sv, total=frete_sv + acess_sv,
                                 teto=None, ipoa=None, vig=None, km=None, fonte="fluxos_servico")

        # ---- fallback grãos: mesma rota/cliente, produto-irmão de grão já tem abertura ----
        # Achado do usuário (22/jul/2026: "para tarifas iguais de soja e milho abrir as
        # acessórias iguais, está abrindo só p soja, todos os clientes"). Causa raiz: a base
        # `fluxos_servico` NUNCA tem nenhum registro com produto MILHO (confirmado pra TODOS
        # os clientes) — não é um bug de casamento, é que essa mercadoria simplesmente não foi
        # capturada nessa tabela. Mas MILHO/SOJA/outros grãos na MESMA rota costumam usar a
        # MESMA infraestrutura de manobra do terminal — quando a tarifa do fluxo é muito
        # próxima (<=5%, indicando mesma faixa/contrato), empresta a abertura do grão-irmão
        # daquela rota, ESCALADA (nunca copiada bruta) pro total de frete+acessórias do próprio
        # fluxo — preserva o fechamento exato item-a-item = total, mesma garantia do resto do
        # script (ver nota "Fix: quando existe abertura..." acima).
        _GRAO_RE = re.compile(r"SOJA|MILHO|FARELO|TRIGO|SORGO|ALGODAO|ARROZ")
        abertura_rota = {}
        for (ao, ad, aprod), aitens in abertura.items():
            if _GRAO_RE.search(aprod):
                abertura_rota.setdefault((ao, ad), []).append((aprod, aitens))
        for k, r in rotas.items():
            o, d, prod = k
            if k in abertura or not _GRAO_RE.search(prod):
                continue
            melhor = None
            for prod2, itens2 in abertura_rota.get((o, d), []):
                r2 = rotas.get((o, d, prod2))
                if not r2 or not r2.get("total"):
                    continue
                dif_pct = abs((r["total"] or 0) - r2["total"]) / r2["total"]
                if dif_pct <= 0.05 and (melhor is None or dif_pct < melhor[0]):
                    melhor = (dif_pct, prod2, itens2)
            if melhor:
                dif_pct, prod2, itens2 = melhor
                soma2 = sum(itens2.values())
                if soma2 > 0:
                    escala = ((r["frete"] or 0) + (r["acess"] or 0)) / soma2
                    abertura[k] = {sv: v2 * escala for sv, v2 in itens2.items()}
                    print(f"  {cliente}: abertura de {prod2} {o}->{d} espelhada (escala "
                          f"{escala:.3f}) pra {prod} {o}->{d} (grão irmão, mesma rota, "
                          f"tarifa {dif_pct*100:.1f}% próxima)")

        faltam = {k: r for k, r in rotas.items() if (modo == "replace" or k not in cobertas)}
        if not faltam:
            print(f"  {cliente}: nada a fazer (0 rotas novas).")
            continue

        # ---- volume por (origem,destino,PRODUTO): último ano com realizado ----
        # Achado do usuário (21/jul/2026, "volumes duplicados entre produtos... para VIBRA"):
        # a chave era só (origem,destino) — 2 produtos na MESMA rota (ex. GASOLINA e OLEO
        # DIESEL em EYU→VGV) caíam no MESMO bucket e recebiam o volume COMBINADO dos dois,
        # idêntico pros dois (confirmado: VIBRA GASOLINA/OLEO DIESEL EYU→VGV ambos com
        # volume_ano_ktu=18731). Fix: produto na chave, casado por PRIMEIRO TOKEN (mesma
        # convenção de famTok/pcNormProd no front) — volume_hist grava mercadoria mais
        # específica que o produto genérico do fluxo (ex. "ACUCAR CRISTAL/REF.A GRANEL" vs
        # "ACUCAR"), então match exato zeraria volume de grãos/açúcar.
        #
        # Achado do usuário (27/jul/2026, "CARAMURU aparecendo volume de farelo pra destino VTU
        # nos últimos 12 meses, esse fluxo nao existiu"): a rota EPO->VTU FARELO DE SOJA da
        # CARAMURU teve atividade real só até 2018 (SUM(realizado_ktu) por ano="último ano COM
        # QUALQUER realizado>0", sem checar se esse ano é recente) — o script pegava o total de
        # 2018 (153.776 t) e gravava em volume_ano_ktu como se fosse o volume ATUAL da rota; o
        # front-end (volDefaultKt) usa volume_ano_ktu direto, sem re-checar recência, rotulando
        # esse número como "últimos 12 meses"/"Volume 12m" — uma rota morta há ~8 anos aparecia
        # como se estivesse ativa hoje. Fix: só aceita o ano mais recente com realizado>0 se ele
        # estiver dentro de STALE_ANO_MIN (últimos 2 anos-calendário da base, ancorado no ano mais
        # recente presente em TODO volume_hist) — rota sem atividade real recente fica SEM
        # volume_ano_ktu (None), nunca um total anual antigo maquiado de "últimos 12 meses" (mesma
        # convenção: zero/None é honesto, número emprestado de outra época não é). Guarda a lista
        # de rotas descartadas por staleness só pra anotar na cobertura (transparência/auditoria).
        #
        # Escopo do filtro de staleness: só modo="replace" (CARAMURU, NOVA AGRI — fluxos 100%
        # "portfólio completo" gerados do zero por este script, sem nenhuma outra fonte rica).
        # Testado e DELIBERADAMENTE NÃO aplicado a modo="add" (GERDAU/USIMINAS/ARCELORMITTAL/etc.):
        # nesses clientes, anular volume_ano_ktu de uma rota empurra o front-end pro fallback
        # `volRealUlt12KtDoFluxo`/`pcVolLookup`, que casa por FAMÍLIA de produto (mais permissivo) e
        # pode acabar emprestando o número de uma rota-irmã distinta (ex. MINERIO FERRO DLL->EPW
        # passou a mostrar o mesmo valor de MINERIO FERRO VWI->VIC; CALCARIO BRITAD EBI->VIC o
        # mesmo de CALCARIO BRITADO EBI->VIC) — regressão nova, pior que o problema original.
        # Auditado com audit_volumes.py: aplicar só em "replace" resolve CARAMURU sem introduzir
        # nenhum falso-negativo/empréstimo novo nos clientes "add" (rodado antes/depois, 0 diffs).
        stale_ano_min = cur.execute("SELECT MAX(ano) FROM volume_hist").fetchone()[0] - 1
        vol = {}
        vol_stale = {}
        for cli_raw, o, d, prod_vh, ano, ktu in cur.execute(
            """SELECT cliente, origem, destino, mercadoria, ano, SUM(realizado_ktu) FROM volume_hist
               WHERE realizado_ktu > 0 GROUP BY cliente, origem, destino, mercadoria, ano"""):
            if canon(cli_raw) != cliente:
                continue
            key = (o, d, _ftok(prod_vh))
            if key not in vol_stale or ano > vol_stale[key][0]:
                vol_stale[key] = (ano, ktu)
            if modo == "replace" and ano < stale_ano_min:
                continue
            if key not in vol or ano > vol[key][0]:
                vol[key] = (ano, ktu)

        if modo == "replace":
            cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=?", (cliente,))
            cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=?", (cliente,))
            total_rm += len(curados)
        else:
            # apaga só as linhas que NÃO são os fluxos curados originais (idempotência das novas)
            placeholders = ",".join("?" for _ in curados) or "''"
            cur.execute(
                f"DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo NOT IN ({placeholders})",
                (cliente, *curados))
            cur.execute(
                f"DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo NOT IN ({placeholders})",
                (cliente, *curados))

        n_pjf = n_pja = n_reconc = 0
        for k, r in sorted(faltam.items()):
            fluxo = f"{r['produto']} {r['origem']} {r['destino']}"
            ab = abertura.get(k)
            vkey = (r["origem"], r["destino"], _ftok(r["produto"]))
            v = vol.get(vkey)
            v_stale = vol_stale.get(vkey)
            frete_final, acess_final = r["frete"], r["acess"]
            reconciliado = False
            if ab:
                # abertura existe: deriva frete/acessórias DELA (não de tarifas_praticadas/
                # ipoa_teto) pra garantir que a soma dos itens sempre feche com o total.
                frete_ab = ab.get("FRETE", 0.0)
                acess_ab = sum(v2 for sv2, v2 in ab.items() if sv2 != "FRETE")
                if abs((frete_ab + acess_ab) - (r["frete"] or 0) - (r["acess"] or 0)) > 0.5:
                    reconciliado = True
                    n_reconc += 1
                frete_final, acess_final = frete_ab, acess_ab
            total_final = round((frete_final or 0) + (acess_final or 0), 2)
            cobertura = f"portfólio por rota (item {r['item']}, {r['fonte']})" + \
                        ("" if ab else " — sem abertura de manobra na base pra esta rota") + \
                        (" · frete/acessórias reconciliados com fluxos_servico (fonte divergia)" if reconciliado else "") + \
                        (f" · sem volume recente (última atividade real em {v_stale[0]}, rota "
                         f"encerrada — não usado como volume atual)" if (v is None and v_stale) else "")
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cliente, fluxo, total_final, round(r["teto"], 2) if r["teto"] else None,
                 round(frete_final, 2) if frete_final else None,
                 round(acess_final, 2) if acess_final else None,
                 round(r["ipoa"], 4) if r["ipoa"] is not None else None,
                 round(r["km"], 1) if r["km"] else None,
                 round(v[1] * 1000.0, 0) if v else None, r["vig"], FONTE_PJF, cobertura),
            )
            n_pjf += 1
            if ab:
                for sv, val in sorted(ab.items()):
                    if sv == "FRETE" or val <= 0:
                        continue
                    cur.execute(
                        """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                           VALUES (?,?,?,?,?)""",
                        (cliente, fluxo, NOME_SERV.get(sv, sv.title()), round(val, 2), FONTE_PJA))
                    n_pja += 1

        total_ins += n_pjf
        total_pja += n_pja
        acao = f"substituídos {len(curados)} fluxo(s) genérico(s) por" if modo == "replace" else "+"
        reconc_msg = f" ({n_reconc} reconciliados com fluxos_servico)" if n_reconc else ""
        print(f"  {cliente}: {acao}{n_pjf} rotas ({modo}), {n_pja} itens de abertura{reconc_msg}.")

    con.commit()
    print(f"\nTotal: {total_ins} fluxos, {total_pja} itens de abertura, "
          f"{total_rm} fluxos genéricos substituídos.")
    con.close()


if __name__ == "__main__":
    main()
