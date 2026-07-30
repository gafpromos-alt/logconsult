# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Painel Multi-Módulo (Fase 1)
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Lê logconsult.db e gera um dashboard HTML autocontido com módulos:
  Acessórias · Teto Tarifário · Comparativo de Tarifas · VLI/Margem · Contatos
Reutiliza o skin do Radar (variáveis CSS prontas p/ Elite Performance).

Uso:  python3 build_painel.py   ->  Painel_LogconsultOS.html
"""
import sqlite3, json, pathlib, datetime, math, re
import pandas as pd, numpy as np
from canon import canon   # padroniza nome de cliente → CONTA (grupo econômico), lógica do CRM

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
TEMPLATE = BASE / "painel_template.html"
OUT = BASE / "Painel_LogconsultOS.html"
RADAR_JSON = BASE.parent / "03_Radar_Oportunidades" / "radar_data.json"  # Horizontes + Pipeline
con = sqlite3.connect(DB)
def q(s): return pd.read_sql_query(s, con)

ALVOS = ["mosaic","selecta","caramuru","nova agri","agrex","cenibra","cmoc",
         "vibra","cargill","bunge","gerdau","raizen","cofco","adm"]
def is_alvo(nome):
    n = str(nome).lower()
    return any(a in n for a in ALVOS)

def clean(v):
    if v is None: return None
    if isinstance(v,float) and (math.isnan(v) or math.isinf(v)): return None
    return v
def rec(df): return [{k:clean(v) for k,v in r.items()} for r in df.to_dict("records")]

def fmt_tel(v):
    """Formata telefone BR a partir do número cru do CRM (ex.: 5531991059845.0)."""
    if v is None or (isinstance(v, float) and math.isnan(v)): return None
    s = "".join(ch for ch in str(v).split(".")[0] if ch.isdigit())
    if not s: return None
    if len(s) == 13 and s[:2] == "55": return f"+55 ({s[2:4]}) {s[4:9]}-{s[9:]}"
    if len(s) == 12 and s[:2] == "55": return f"+55 ({s[2:4]}) {s[4:8]}-{s[8:]}"
    if len(s) == 11: return f"({s[0:2]}) {s[2:7]}-{s[7:]}"
    if len(s) == 10: return f"({s[0:2]}) {s[2:6]}-{s[6:]}"
    return s

P24 = "panorama LIKE '2024%'"

# ============================ REGULATÓRIO FERROVIAS (ANTT) ============================
# Leitura consultiva (IA): pontos das normas que PROTEGEM O CLIENTE = alavancas de negociação.
# Barra direita = referência da norma + link ANTT. Atualizar conforme novas resoluções.
REGULATORIO = {
  "intro": "As normas que regulam a ferrovia protegem o cliente em oito frentes. "
           "Cada proteção é uma alavanca de assessoria — abaixo, o ponto regulatório e como usá-lo na mesa.",
  "temas": [
    {"id":"teto","titulo":"Teto tarifário","cor":"var(--bad)",
     "protege":"A tarifa de frete tem um MÁXIMO homologado pela ANTT por concessionária × trecho × mercadoria.",
     "pontos":[
       "A concessionária não pode cobrar frete acima do teto homologado (Tabela Tarifária / Decisões SUFER).",
       "Cobrança acima do teto é irregular → base para recuperação retroativa (cláusula contratual 3.6.1).",
       "O teto reajusta por índice/decisão — a trajetória é auditável; dá para reconstruir o teto de qualquer data.",
       "Quantificação do retroativo: janela de prescrição tipicamente de 5 anos (validar caso a caso com o jurídico) — define o período recuperável.",
       "Teto desatualizado também é alavanca: cabe pleito de revisão da paramétrica junto à SUFER/ANTT.",
       "Alavanca: fluxo no/acima do teto = renegociação com risco zero para o cliente."],
     "normas":["Tabela Tarifária / Decisões SUFER"]},
    {"id":"acessorias","titulo":"Operações acessórias & IPOA","cor":"var(--hot)",
     "protege":"Acessórias (manobra, carga/descarga, TVU, etc.) são negociadas livremente — MAS sob vigilância anti-abuso.",
     "pontos":[
       "A Res. 6.031/2023 veda expressamente 'práticas abusivas de preço' nas acessórias (Art. 15).",
       "IPOA (Indicador de Participação das Operações Acessórias) = acessórias ÷ frete; referência ANTT ~24,8%.",
       "Acessórias chegaram a 35% do frete em exportação → a ANTT monitora e pode acionar o CADE.",
       "Alavanca: IPOA estourado num fluxo = argumento de abuso para reduzir acessórias (não têm teto, mas têm régua)."],
     "normas":["Resolução ANTT 6.031/2023","Resolução ANTT 6.076/2026"]},
    {"id":"isonomia","titulo":"Isonomia entre clientes e fluxos","cor":"var(--info)",
     "protege":"Usuários em condições equivalentes devem receber tratamento tarifário isonômico e não discriminatório.",
     "pontos":[
       "Acesso e condições não podem discriminar usuários em situações equivalentes.",
       "Diferença de tarifa entre clientes na mesma rota/produto, sem justificativa de custo, é questionável.",
       "Alavanca: benchmark de pares (quem paga mais na mesma rota) sustenta pedido de equalização."],
     "normas":["Resolução ANTT 3.694/2011","Lei 10.233/2001"]},
    {"id":"acesso","titulo":"Livre acesso · Direito de passagem","cor":"var(--warn)",
     "protege":"A malha é compartilhada: direito de passagem e tráfego mútuo garantem acesso não discriminatório.",
     "pontos":[
       "Direito de passagem (trem de um operador na malha de outro) e tráfego mútuo são garantidos e arbitrados pela ANTT.",
       "A ANTT dirime conflitos e coíbe condutas anticompetitivas no compartilhamento da infraestrutura.",
       "Alavanca: rota cativa a uma concessionária pode ter alternativa via direito de passagem → poder de barganha."],
     "normas":["Resolução ANTT 3.695/2011","Lei 14.273/2021"]},
    {"id":"usuario","titulo":"Direitos do usuário & serviço adequado","cor":"var(--good)",
     "protege":"O cliente tem direito a serviço adequado, transparência e canal formal de reclamação.",
     "pontos":[
       "A concessionária deve receber, registrar e responder reclamações em até 30 dias.",
       "Serviço inadequado → o usuário pode reclamar à ANTT (Regulamento dos Usuários).",
       "O Decreto 1.832/1996 (Regulamento dos Transportes Ferroviários) disciplina toda a relação ferrovia × usuário, incluindo responsabilidades no transporte.",
       "O RSF1 (em audiência pública, AP 05/2026) amplia direitos e transparência do usuário.",
       "Alavanca: histórico de serviço inadequado compõe o dossiê de renegociação."],
     "normas":["Resolução ANTT 3.694/2011","Decreto 1.832/1996","RSF1 (em audiência pública)"]},
    {"id":"capacidade","titulo":"Capacidade, metas de produção & Declaração de Rede","cor":"var(--green)",
     "protege":"A concessionária tem METAS mínimas de produção por trecho e deve publicar anualmente a capacidade instalada e ociosa da malha.",
     "pontos":[
       "Res. 3.696/2011: metas de produção por trecho são limite MÍNIMO — sub-serviço sistemático descumpre a pactuação.",
       "Res. 5.943/2021 (Declaração de Rede): a ANTT publica anualmente capacidade instalada e OCIOSA por trecho, limites de carregamento e padrões operacionais.",
       "Capacidade ociosa comprovada derruba o argumento de 'malha saturada' usado para negar volume ou justificar tarifa alta.",
       "Alavanca: cruzar a Declaração de Rede com o pleito do cliente — se há capacidade ociosa no trecho, há espaço para mais volume e melhor tarifa."],
     "normas":["Resolução ANTT 3.696/2011","Resolução ANTT 5.943/2021"]},
    {"id":"renovacao","titulo":"Renovações antecipadas, usuário-investidor & OFI","cor":"var(--accent, var(--green-text))",
     "protege":"As renovações antecipadas criaram obrigações de investimento auditáveis — e o marco legal deu ao cliente instrumentos para investir, contratar capacidade e até operar.",
     "pontos":[
       "Lei 13.448/2017: o aditivo de prorrogação tem CRONOGRAMA de investimentos obrigatórios com 'desconto anual de reequilíbrio' em caso de inexecução — capex atrasado gera compensação.",
       "FCA/VLI, EFVM, MRS e Malha Paulista passaram (ou passam) por renovação — as obrigações do aditivo são públicas e auditáveis contra o realizado.",
       "Usuário-investidor (Lei 14.273/2021): o cliente pode aportar em via, pátios e material rodante com compensação financeira livremente pactuada — investimento vira desconto tarifário estrutural.",
       "OFI — Operador Ferroviário Independente: terceiro habilitado pode contratar capacidade e operar na malha da concessionária, com remuneração regulada pela capacidade contratada.",
       "Alavanca: a simples habilitação de um OFI ou proposta de usuário-investidor cria concorrência crível DENTRO da malha — muda o poder de barganha sem depender de rodovia."],
     "normas":["Lei 13.448/2017","Lei 14.273/2021"]},
    {"id":"concorrencia","titulo":"Defesa da concorrência (CADE)","cor":"var(--hot)",
     "protege":"A ferrovia é monopólio natural na rota — abusos de posição dominante são infração à ordem econômica, além da esfera ANTT.",
     "pontos":[
       "Venda casada (frete condicionado à contratação de acessórias da própria concessionária) pode configurar infração — Lei 12.529/2011, art. 36.",
       "Preço excessivo e discriminação de preços entre clientes equivalentes também são condutas tipificadas.",
       "A própria ANTT encaminha indícios de abuso em acessórias ao CADE (mecanismo do IPOA).",
       "Alavanca: a menção fundamentada à esfera concorrencial (dossiê IPOA + benchmark de pares) eleva o custo de negar a renegociação — uso como último degrau da escada de escalada."],
     "normas":["Lei 12.529/2011","Resolução ANTT 6.031/2023"]},
  ],
  "normas": [
    {"ref":"Resolução ANTT 3.694/2011","titulo":"Regulamento dos Usuários dos Serviços de Transporte Ferroviário de Cargas",
     "tema":"Direitos do usuário","url":"https://anttlegis.antt.gov.br/action/TematicaAction.php?acao=abrirVinculos&cotematica=18461996&cod_menu=8721&cod_modulo=618"},
    {"ref":"Resolução ANTT 3.695/2011","titulo":"Direito de Passagem e Tráfego Mútuo — compartilhamento da malha",
     "tema":"Acesso","url":"https://anttlegis.antt.gov.br/action/TematicaAction.php?acao=abrirVinculos&cotematica=18141546&cod_menu=8721&cod_modulo=618"},
    {"ref":"Resolução ANTT 6.031/2023","titulo":"Operações acessórias ao transporte ferroviário — veda preço abusivo (Art. 15)",
     "tema":"Acessórias / IPOA","url":"https://anttlegis.antt.gov.br/"},
    {"ref":"Resolução ANTT 6.076/2026","titulo":"Atualiza regras das operações acessórias / IPOA",
     "tema":"Acessórias / IPOA","url":"https://www.legisweb.com.br/legislacao/?id=489672"},
    {"ref":"Tabela Tarifária / Decisões SUFER","titulo":"Homologa os tetos por concessionária × trecho × mercadoria e reajustes",
     "tema":"Teto","url":"https://anttlegis.antt.gov.br/"},
    {"ref":"RSF1 — Audiência Pública 05/2026","titulo":"Regulamento dos Serviços e Segurança Ferroviários (1ª Norma) — direitos do usuário",
     "tema":"Novo marco","url":"https://www.gov.br/antt/pt-br"},
    {"ref":"Lei 14.273/2021","titulo":"Marco Legal das Ferrovias (regime de autorizações)",
     "tema":"Marco legal","url":"https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14273.htm"},
    {"ref":"Lei 10.233/2001","titulo":"Cria a ANTT e fixa princípios do transporte terrestre",
     "tema":"Marco legal","url":"https://www.planalto.gov.br/ccivil_03/leis/leis_2001/l10233.htm"},
    {"ref":"Decreto 1.832/1996","titulo":"Regulamento dos Transportes Ferroviários — relações ferrovia × usuários, tráfego mútuo, segurança",
     "tema":"Marco legal","url":"https://www.planalto.gov.br/ccivil_03/decreto/1996/d1832.htm"},
    {"ref":"Resolução ANTT 3.696/2011","titulo":"Metas de produção por trecho (mínimo) e metas de segurança (máximo) das concessionárias",
     "tema":"Capacidade / metas","url":"https://www.legisweb.com.br/legislacao/?id=114292"},
    {"ref":"Resolução ANTT 5.943/2021","titulo":"Declaração de Rede — capacidade instalada e ociosa por trecho, publicada anualmente",
     "tema":"Capacidade / metas","url":"https://portal.antt.gov.br/en/declaracao-de-rede-2022"},
    {"ref":"Lei 13.448/2017","titulo":"Renovações antecipadas — investimentos obrigatórios com desconto de reequilíbrio; capacidade a terceiros e OFI",
     "tema":"Renovação / OFI","url":"https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2017/lei/l13448.htm"},
    {"ref":"Lei 12.529/2011","titulo":"Defesa da concorrência — venda casada, preço excessivo e discriminação (art. 36)",
     "tema":"CADE","url":"https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12529.htm"},
  ],
  "fonte": "Pesquisa em anttlegis.antt.gov.br e gov.br/antt. Síntese consultiva — confirmar vigência antes de citar em proposta.",
}

# ------------------------------------------------------------------ ACESSÓRIAS
serv = q("SELECT itens,servicos,ferrovia,tarifa,cliente,origem,destino,produto FROM fluxos_servico")
serv["cliente"] = serv["cliente"].map(canon)
serv["tarifa"] = pd.to_numeric(serv["tarifa"], errors="coerce")
serv["is_frete"] = serv["servicos"].str.upper().eq("FRETE")
por_servico = (serv.groupby("servicos")
                 .agg(n=("tarifa","size"), tarifa_med=("tarifa","mean"))
                 .reset_index().sort_values("n", ascending=False))
por_servico["tarifa_med"] = por_servico["tarifa_med"].round(2)
# por fluxo: frete vs acessórias, depois média por cliente
flow = serv.groupby("itens").apply(lambda g: pd.Series({
    "cliente": g["cliente"].iloc[0], "produto": g["produto"].iloc[0],
    "origem": g["origem"].iloc[0], "destino": g["destino"].iloc[0],
    "frete": g.loc[g["is_frete"],"tarifa"].sum(),
    "acess": g.loc[~g["is_frete"],"tarifa"].sum(),
})).reset_index()
flow["total"] = flow["frete"]+flow["acess"]
flow["pct_acess"] = np.where(flow["total"]>0, flow["acess"]/flow["total"]*100, np.nan)
acess_cliente = (flow.groupby("cliente")
                   .agg(n_fluxos=("itens","size"), frete=("frete","mean"),
                        acess=("acess","mean"), pct_acess=("pct_acess","mean"))
                   .reset_index().sort_values("acess", ascending=False))
for c in ["frete","acess","pct_acess"]: acess_cliente[c]=acess_cliente[c].round(1)
acess_cliente["alvo"] = acess_cliente["cliente"].map(is_alvo)

# ================= HUB ACESSÓRIAS (coração da Fase 1): comparativo + ranking + simulador =================
# Comparação "dentro do mesmo site da VLI": a MESMA acessória, no MESMO local, entre clientes.
# Serviços de origem comparam no site de origem; de destino, no destino; frete/DP, na rota.
ELIMINAVEIS = {  # acessórias de cobrança questionável → cenário otimista elimina (Res. 6.031/2023)
    "MANOBRA CONEXAO CHEIO": "manobra intermediária — parte da operação de transporte, cobrança questionável",
}
hub = serv[serv["tarifa"].notna()].copy()
hub["servicos"] = hub["servicos"].str.strip().str.upper()
hub = hub[hub["servicos"] != "FRETE"]                      # o hub é de acessórias; frete tem teto próprio
def _site(r):
    s = r["servicos"]
    if "ORIGEM" in s or s == "CARGA":   return "ORI " + str(r["origem"])
    if "DESTINO" in s or s == "DESCARGA": return "DST " + str(r["destino"])
    return "ROTA " + str(r["origem"]) + "→" + str(r["destino"])
hub["site"] = hub.apply(_site, axis=1)
# estatísticas de pares (mesmo serviço × mesmo site, excluindo o próprio cliente)
def _pares(gr):
    out = []
    for i, r in gr.iterrows():
        o = gr[gr["cliente"] != r["cliente"]]["tarifa"]
        out.append((o.median() if len(o) else np.nan, o.min() if len(o) else np.nan, o.nunique() and gr[gr["cliente"]!=r["cliente"]]["cliente"].nunique()))
    gr = gr.copy()
    gr[["med_pares","min_pares","n_pares_cli"]] = pd.DataFrame(out, index=gr.index)
    return gr
hub = hub.groupby(["servicos","site"], group_keys=False).apply(_pares)
hub["elim"] = hub["servicos"].isin(ELIMINAVEIS)
hub["ganho_mod"] = np.maximum(0, hub["tarifa"] - hub["med_pares"].fillna(hub["tarifa"]))
hub["ganho_otm"] = np.where(hub["elim"], hub["tarifa"],
                            np.maximum(0, hub["tarifa"] - hub["min_pares"].fillna(hub["tarifa"])))
hub["alvo"] = hub["cliente"].map(is_alvo)
# volume anual por (cliente-normalizado × O/D) — ano mais recente com realizado
import re as _re
def _cnorm(s):
    t = _re.sub(r"[^A-Z ]", "", str(s).upper()).split()
    return t[0] if t else ""
vh = q("""SELECT cliente, origem, destino, ano, SUM(realizado_ktu) ktu FROM volume_hist
          WHERE realizado_ktu > 0 GROUP BY cliente, origem, destino, ano""")
vh["cli_n"] = vh["cliente"].map(canon)
vh = vh.groupby(["cli_n","origem","destino","ano"], as_index=False)["ktu"].sum()
vh = vh.sort_values("ano").groupby(["cli_n","origem","destino"]).tail(1)
vmap = {(r.cli_n, r.origem, r.destino): (r.ktu * 1000.0, int(r.ano)) for r in vh.itertuples()}
hub["cli_n"] = hub["cliente"]  # já canônico
hub["vol_t"]   = hub.apply(lambda r: vmap.get((r["cli_n"], r["origem"], r["destino"]), (None, None))[0], axis=1)
hub["vol_ano"] = hub.apply(lambda r: vmap.get((r["cli_n"], r["origem"], r["destino"]), (None, None))[1], axis=1)
# rateia o volume do trio cliente×O/D entre os fluxos (itens) — evita dupla contagem no anualizado
_nit = hub.groupby(["cli_n","origem","destino"])["itens"].transform("nunique")
hub["vol_t"] = hub["vol_t"] / _nit
# "ganho sobre a menor" (por linha) = delta vs. o melhor par (min_pares) na mesma família
# serviço×site × volume anualizado da linha — mesma matemática do "otimista" do ranking,
# só que sem agregar por cliente (pra aparecer linha a linha na tabela "Detalhe por cliente no site")
hub["ganho_otm_ano"] = hub["ganho_otm"] * hub["vol_t"]
hub["ganho_mod_ano"] = hub["ganho_mod"] * hub["vol_t"]
# ranking de captura por cliente (anualizado onde há volume; R$/t sempre)
def _rank(gr):
    vol = gr["vol_t"].notna()
    return pd.Series({
        "n_fluxos": gr["itens"].nunique(), "n_serv": len(gr),
        "n_com_gap": int((gr["ganho_mod"] > 0).sum()),
        "gap_mod_rs_t": gr["ganho_mod"].mean(),
        "anual_mod": (gr.loc[vol, "ganho_mod"] * gr.loc[vol, "vol_t"]).sum(),
        "anual_otm": (gr.loc[vol, "ganho_otm"] * gr.loc[vol, "vol_t"]).sum(),
        "pct_vol": vol.mean() * 100,
        "alvo": bool(gr["alvo"].iloc[0]),
    })
acess_rank = hub.groupby("cliente").apply(_rank).reset_index().sort_values("anual_mod", ascending=False)
for c in ["gap_mod_rs_t","pct_vol"]: acess_rank[c] = acess_rank[c].round(1)
for c in ["anual_mod","anual_otm"]: acess_rank[c] = acess_rank[c].round(0)
# comparativo por site (onde 2+ clientes pagam o mesmo serviço no mesmo lugar)
# origem/destino: "site" às vezes é 1 estação só (ORI/DST X) e às vezes uma rota inteira
# (ROTA X→Y) — quando o grupo cobre mais de uma estação real, mostra "vários" em vez de
# escolher uma arbitrariamente.
_un = lambda s: s.iloc[0] if s.nunique() == 1 else "vários"
comp_sites = (hub.groupby(["servicos","site"])
                .agg(n_cli=("cliente","nunique"), tar_min=("tarifa","min"),
                     tar_med=("tarifa","median"), tar_max=("tarifa","max"),
                     origem=("origem", _un), destino=("destino", _un))
                .reset_index())
comp_sites = comp_sites[comp_sites["n_cli"] >= 2].copy()
comp_sites["dispersao"] = (comp_sites["tar_max"] - comp_sites["tar_min"]).round(2)
comp_sites = comp_sites.sort_values("dispersao", ascending=False)

# comparativo por ESTAÇÃO (novo padrão, a pedido do usuário): "site" antigo mistura estação
# única (ORI/DST X) com rota inteira (ROTA X→Y) — aqui cada linha do hub vira DUAS entradas
# (uma pela origem, uma pelo destino), e agrupa por serviço×estação×tipo. Assim "IUF" junta
# TODOS os fluxos que passam por IUF como origem (num grupo) e TODOS como destino (noutro).
_ho = hub.copy(); _ho["estacao"] = _ho["origem"]; _ho["tipo"] = "Origem"
_hd = hub.copy(); _hd["estacao"] = _hd["destino"]; _hd["tipo"] = "Destino"
hub_est = pd.concat([_ho, _hd], ignore_index=True)
hub_est = hub_est[hub_est["estacao"].notna() & (hub_est["estacao"] != "")]
comp_estacoes = (hub_est.groupby(["servicos", "tipo", "estacao"])
                  .agg(n_cli=("cliente", "nunique"), tar_min=("tarifa", "min"),
                       tar_med=("tarifa", "median"), tar_max=("tarifa", "max"))
                  .reset_index())
comp_estacoes = comp_estacoes[comp_estacoes["n_cli"] >= 2].copy()
comp_estacoes["dispersao"] = (comp_estacoes["tar_max"] - comp_estacoes["tar_min"]).round(2)
comp_estacoes = comp_estacoes.sort_values("dispersao", ascending=False)

# volume mensal por trio do hub (cliente canônico × O/D × ano × mês) — alimenta os filtros
# suspensos Ano/Mês do painel "Ganho potencial por cliente" (Acessórias) e o "Vol período (kt)"
# do Painel do Cliente: o front recalcula o volume (e o ganho) pro período escolhido.
# ktu → t (×1000) já aqui, pra casar com vol_t.
_trios_hub = set(zip(hub["cli_n"], hub["origem"], hub["destino"]))
# ALE (cliente real, canon() distinto de ALESAT) e outros do Painel do Cliente sem linha em
# fluxos_servico (hub) ficavam de fora do escopo de volmes inteiro (não só 2026 — SEMPRE,
# mesmo já com o fix abaixo) porque _trios_hub só cobre rotas do hub de acessórias. Amplia o
# escopo com as rotas de `projeto_fluxo_tarifas` (fonte do Painel do Cliente), parseando
# "fluxo" pela mesma convenção do front (fluxoRota(): penúltimo token = origem, último =
# destino; sufixo "(ITEM N)" removido antes, mesma regra de add_demais_clientes_fluxos_completos.py).
def _fluxo_od(fluxo):
    toks = re.sub(r"\(ITEM\s+\S+?\)", " ", str(fluxo), flags=re.I).split()
    return (toks[-2], toks[-1]) if len(toks) >= 2 else (None, None)
_pjf_od = q("SELECT DISTINCT cliente, fluxo FROM projeto_fluxo_tarifas")
_pjf_od["cli_n"] = _pjf_od["cliente"].map(canon)
_pjf_od[["origem", "destino"]] = _pjf_od["fluxo"].apply(lambda f: pd.Series(_fluxo_od(f)))
_trios_pc = set(zip(_pjf_od["cli_n"], _pjf_od["origem"], _pjf_od["destino"]))
_trios_vol = _trios_hub | _trios_pc

# achado do usuário (21/jul/2026): "IPIRANGA... volume ultimos 12 meses todos os fluxos igual,
# impossivel ser igual" — e o mesmo pra VIBRA/RAIZEN. Causa raiz: a query agregava só por
# (cliente,origem,destino,ano,mes), SEM produto — 2 fluxos na MESMA rota com mercadorias
# diferentes (ex. GASOLINA e OLEO DIESEL na mesma origem/destino) caíam na MESMA chave e
# recebiam o volume COMBINADO dos dois, idêntico pros dois. Fix: agrega com produto
# (`mercadoria`, mesma convenção de nome usada no HISTM/SAZ) na chave — `volmes_produto`
# (granular, usado no "Vol período" do Painel do Cliente) e `volmes` (combinado, DERIVADO
# somando produto de volta — mantém o filtro "Ganho potencial por cliente"/Acessórias intacto,
# que espera 1 valor por trio×mês, sem produto).
# achado do usuário (24/jul/2026, "SELECTA farelo continua errado, ta 10,3k e foi realizado
# mais de 200k ano"): `mercadoria` (granularidade escolhida acima, 21/jul/2026, pra não
# misturar produtos DIFERENTES como GASOLINA/DIESEL) às vezes carrega um SUFIXO DE QUALIDADE/
# GRADE da MESMA mercadoria-base — ex. SELECTA EBJ→IUF tem "FARELO DE SOJA", "FARELO DE SOJA -
# SPC" e "FARELO DE SOJA- HIPRO" como 3 rótulos DISTINTOS na base, todos farelo de soja (mesma
# rota, mesmo cliente, mesma tarifa/fluxo contratual — só o grau/especificação do farelo
# difere). `pcVolLookup` (painel_template.html) casa por NOME EXATO contra o produto do fluxo
# contratual ("FARELO DE SOJA", sem sufixo) — só bate no rótulo "pelado", que na SELECTA tem
# dado real só até jun/2019; as safras 2020-2025 (a maior parte do volume real, ~275kt nos
# últimos 12 meses) ficam nos rótulos "- SPC"/"- HIPRO" e nunca aparecem pro fluxo. Resultado:
# "Últimos 12 meses" ancora no último mês do rótulo pelado (2019) e mostra ~10kt em vez de ~275kt.
# Fix: normaliza sufixo de GRADE (" - PALAVRA" ou "-PALAVRA" com espaço ANTES da palavra final,
# ex. " - SPC", "- HIPRO", "- DDG", "- PELLET") ANTES de agregar — mescla os 3 rótulos numa
# única chave "FARELO DE SOJA". Regex exige espaço logo após o hífen (só corta sufixo separado
# por espaço), o que preserva compostos sem espaço como "BIG-BAG" (CYLPEBS EM BIG-BAG) intactos
# — não é um pooling genérico por token (a causa do bug GERDAU/USIMINAS já documentada acima),
# só remove um qualificador de grade quando claramente destacado do nome-base por espaço.
_MERC_GRADE_SUFFIX_RE = re.compile(r"\s*-\s+\S+$")
def _merc_base(m):
    return _MERC_GRADE_SUFFIX_RE.sub("", str(m)).strip() or str(m).strip()

vm = q("""SELECT cliente, origem, destino, mercadoria AS produto, ano, mes,
                 SUM(realizado_ktu) ktu FROM volume_hist
          WHERE realizado_ktu > 0 GROUP BY cliente, origem, destino, mercadoria, ano, mes""")
vm["cli_n"] = vm["cliente"].map(canon)
vm["produto"] = vm["produto"].map(_merc_base)
vm = vm.groupby(["cli_n", "origem", "destino", "produto", "ano", "mes"], as_index=False)["ktu"].sum()
vm = vm[[t in _trios_vol for t in zip(vm["cli_n"], vm["origem"], vm["destino"])]]
vm["t"] = vm["ktu"] * 1000.0

# volume_hist para em set/2025 (achado do usuário 21/jul/2026: "VIBRA não puxou volume do 1º
# semestre 2026" — na verdade a base TODA não tem 2026 em volume_hist). Completa com vli_pnl
# (vol_tu, já em toneladas, cobre até dez/2026 — mesma fonte já usada no histórico mensal/HISTM)
# só nos trios (cliente,origem,destino,produto,ano,mes) que volume_hist NÃO tem, pra não
# duplicar/discrepar volume onde as duas fontes já se sobrepõem (volume_hist continua a fonte
# preferida quando existe). MESMO filtro de "realizado" do HISTM/SAZ (panorama Real, ou 2026 até
# jul) — achado ao validar "Últimos 12 meses" com o usuário (21/jul/2026): sem esse filtro,
# ago-dez/2026 (panorama "Tendência", ORÇADO, não realizado) entrava como se fosse volume real.
_vp = q("""SELECT cliente, origem, destino, mercadoria AS produto, ano, mes, SUM(vol_tu) t FROM vli_pnl
           WHERE modal='Ferrovia' AND (panorama LIKE '%Real%' OR (panorama LIKE '2026%' AND mes<=7))
           GROUP BY cliente, origem, destino, mercadoria, ano, mes HAVING SUM(vol_tu)>0""")
_vp["cli_n"] = _vp["cliente"].map(canon)
_vp["produto"] = _vp["produto"].map(_merc_base)  # mesma normalização de grade do bloco vm acima
_vp = _vp.groupby(["cli_n", "origem", "destino", "produto", "ano", "mes"], as_index=False)["t"].sum()
_vp = _vp[[t in _trios_vol for t in zip(_vp["cli_n"], _vp["origem"], _vp["destino"])]]
_chaves_vh = set(zip(vm["cli_n"], vm["origem"], vm["destino"], vm["produto"], vm["ano"], vm["mes"]))
_vp_fill = _vp[[k not in _chaves_vh for k in zip(_vp["cli_n"], _vp["origem"], _vp["destino"], _vp["produto"], _vp["ano"], _vp["mes"])]]
vm = pd.concat([vm[["cli_n", "origem", "destino", "produto", "ano", "mes", "t"]],
                _vp_fill[["cli_n", "origem", "destino", "produto", "ano", "mes", "t"]]], ignore_index=True)

volmes_produto = [[r.cli_n, r.origem, r.destino, str(r.produto), int(r.ano), int(r.mes), round(r.t, 1)]
                   for r in vm.itertuples()]

_vm_comb = vm.groupby(["cli_n", "origem", "destino", "ano", "mes"], as_index=False)["t"].sum()
volmes = [[r.cli_n, r.origem, r.destino, int(r.ano), int(r.mes), round(r.t, 1)]
          for r in _vm_comb.itertuples()]

acess_hub = {
    "elim": ELIMINAVEIS,
    "vol_cobertura": round(hub["vol_t"].notna().mean() * 100),
    "volmes": volmes,
    "volmes_produto": volmes_produto,
    "ranking": rec(acess_rank),
    "comp_sites": rec(comp_sites.round(2).head(120)),
    "comp_estacoes": rec(comp_estacoes.round(2).head(120)),
    "sim": rec(hub[["cliente","itens","servicos","site","origem","destino","produto",
                    "tarifa","med_pares","min_pares","n_pares_cli","elim","vol_t","vol_ano",
                    "ganho_otm_ano","ganho_mod_ano","alvo"]].round(2)),
}

# ================= ACESSÓRIAS · BENCHMARK DE MERCADO (RUMO/VLI/MRS) =================
# Tabelas de operações acessórias publicadas nos sites das concessionárias (divulgação
# obrigatória, Res. ANTT 6.031/2023), ingeridas via add_acessorias_mercado.py. Cruza com
# a prática interna (hub) em duas frentes: (A) cliente cobrado acima do próprio público
# da VLI; (B) prática da VLI vs. das demais ferrovias (RUMO/MRS) pro mesmo serviço.
mercado = q("SELECT * FROM acessorias_mercado")

SERV_MAP = {  # servicos do hub (fluxos_servico) -> serviço normalizado das tabelas públicas
    "MANOBRA ORIGEM": "Manobra", "MANOBRA DESTINO": "Manobra", "MANOBRA CONEXAO CHEIO": "Manobra",
    "TRANSBORDO ORIGEM": "Transbordo", "TRANSBORDO DESTINO": "Transbordo",
    "CARGA": "Carga e Descarga", "DESCARGA": "Carga e Descarga",
    "LIMPEZA DE VAGAO": "Limpeza",
}
# produto do hub -> mercadoria da tabela pública da VLI (match direto; GESSO cai no bucket
# genérico "Demais Produtos" por falta de linha própria — sinalizado como aproximado no front)
MERC_MAP_VLI = {
    "SOJA": "SOJA", "FARELO DE SOJA": "FARELO DE SOJA", "FERTILIZANTES": "ADUBOS E FERTILIZANTES",
    "ENXOFRE": "ENXOFRE", "GESSO": "DEMAIS PRODUTOS",
}
hub["servico_norm"] = hub["servicos"].map(SERV_MAP)
hub["mercadoria_vli"] = hub["produto"].str.upper().map(MERC_MAP_VLI)

vli_pub = mercado[mercado["ferrovia"] == "VLI"].copy()
vli_pub_idx = vli_pub.set_index(["malha", "mercadoria", "servico"])[["valor_min", "valor_medio", "valor_max"]]

def _lookup_vli(r):
    if r["ferrovia"] not in ("FCA", "FNS") or pd.isna(r["servico_norm"]) or pd.isna(r["mercadoria_vli"]):
        return pd.Series({"ref_min": np.nan, "ref_medio": np.nan, "ref_max": np.nan})
    key = (r["ferrovia"], r["mercadoria_vli"], r["servico_norm"])
    if key not in vli_pub_idx.index:
        return pd.Series({"ref_min": np.nan, "ref_medio": np.nan, "ref_max": np.nan})
    row = vli_pub_idx.loc[key]
    if isinstance(row, pd.DataFrame): row = row.iloc[0]
    return pd.Series({"ref_min": row["valor_min"], "ref_medio": row["valor_medio"], "ref_max": row["valor_max"]})

hub[["ref_min", "ref_medio", "ref_max"]] = hub.apply(_lookup_vli, axis=1)
hub["acima_ref_pct"] = np.where(hub["ref_medio"] > 0, (hub["tarifa"] / hub["ref_medio"] - 1) * 100, np.nan)

_matched_cols = ["cliente", "servicos", "servico_norm", "produto", "mercadoria_vli", "ferrovia", "origem", "destino",
                 "tarifa", "ref_min", "ref_medio", "ref_max", "acima_ref_pct", "alvo", "vol_t"]
matched = hub[hub["ref_medio"].notna()][_matched_cols].sort_values("acima_ref_pct", ascending=False).round(2)
oport_interno = matched[matched["tarifa"] > matched["ref_max"]].copy()

# benchmark cruzado VLI x RUMO x MRS x VALE, por serviço normalizado (média entre malhas/mercadorias)
OUTRAS_FERROVIAS = ["RUMO", "MRS", "VALE"]
def _bench_ferrovia(fer, serv):
    g = mercado[(mercado["ferrovia"] == fer) & (mercado["servico"] == serv)]
    return round(float(g["valor_medio"].mean()), 2) if len(g) else None

bench_rows = []
for serv in sorted(set(SERV_MAP.values())):
    vals = {fer: _bench_ferrovia(fer, serv) for fer in ["VLI"] + OUTRAS_FERROVIAS}
    if vals["VLI"] is None or all(vals[f] is None for f in OUTRAS_FERROVIAS):
        continue
    gaps = {f: (vals["VLI"] / vals[f] - 1) * 100 if vals[f] else None for f in OUTRAS_FERROVIAS}
    # maior |gap| entre as comparações disponíveis (não faz média entre outras ferrovias —
    # metodologias diferentes demais entre si pra virar uma referência única; mostra cada
    # uma separada no front)
    maior_gap = max([g for g in gaps.values() if g is not None], key=abs)
    row = {"servico": serv, "vli_medio": vals["VLI"]}
    for f in OUTRAS_FERROVIAS:
        row[f.lower() + "_medio"] = vals[f]
        row["gap_pct_" + f.lower()] = round(gaps[f], 1) if gaps[f] is not None else None
    row["gap_pct_vs_outras"] = round(maior_gap, 1)
    bench_rows.append(row)
bench_cross = (pd.DataFrame(bench_rows).sort_values("gap_pct_vs_outras", ascending=False, key=lambda s: s.abs())
               if bench_rows else pd.DataFrame(bench_rows))

acess_mercado_cards = [
    {"label": "Ferrovias monitoradas", "valor": int(mercado["ferrovia"].nunique()), "sub": "VLI, RUMO, MRS, Vale — tabelas públicas (Res. ANTT 6.031/2023)"},
    {"label": "Registros públicos", "valor": int(len(mercado)), "sub": f"{mercado['malha'].nunique()} malhas · {mercado['servico'].nunique()} tipos de serviço"},
    {"label": "Clientes acima do próprio público VLI", "valor": int(oport_interno["cliente"].nunique()), "sub": f"{len(oport_interno)} linhas de serviço"},
    {"label": "Maior gap VLI × mercado", "valor": (f"{bench_cross.iloc[0]['gap_pct_vs_outras']:+.0f}%" if len(bench_cross) else "—"),
     "sub": (bench_cross.iloc[0]["servico"] if len(bench_cross) else "sem dado comparável")},
]
acess_mercado_insights = []
if len(oport_interno):
    top = oport_interno.iloc[0]
    acess_mercado_insights.append(
        f"{top['cliente']}: paga R$ {top['tarifa']:.2f}/t de {top['servico_norm']} em {top['produto']} ({top['ferrovia']}) — "
        f"{top['acima_ref_pct']:.0f}% acima do máximo publicado pela própria VLI (R$ {top['ref_max']:.2f}/t).")
if len(bench_cross):
    b = bench_cross.iloc[0]
    direcao = "acima" if (b["gap_pct_vs_outras"] or 0) > 0 else "abaixo"
    acess_mercado_insights.append(
        f"{b['servico']}: prática média da VLI está {abs(b['gap_pct_vs_outras']):.0f}% {direcao} da média de RUMO/MRS para o mesmo serviço.")

acess_mercado = {
    "tabela": rec(mercado.sort_values(["ferrovia", "malha", "servico", "mercadoria"])),
    "cards": acess_mercado_cards,
    "insights": acess_mercado_insights,
    "oport_interno": rec(oport_interno.head(200)),
    "bench_cross": rec(bench_cross),
    "matched": rec(matched.head(400)),
}

# ---------------------------------------------------------------- TETO TARIFÁRIO
teto = q("""SELECT item,cliente,origem,destino,produto,ipoa,acessorias,frete,
                   teto,teto_1 AS pct_teto,total,corredor_vli,km_rota
            FROM ipoa_teto""")
teto["cliente"] = teto["cliente"].map(canon)
for c in ["ipoa","acessorias","frete","teto","pct_teto","total","km_rota"]:
    teto[c] = pd.to_numeric(teto[c], errors="coerce")
teto["folga_teto_pct"] = (1 - teto["pct_teto"])*100     # quanto falta p/ o teto
teto_fluxos = teto.sort_values("pct_teto", ascending=False).copy()
teto_fluxos = teto_fluxos.rename(columns={"corredor_vli": "corredor"})
teto_fluxos["alvo"]=teto_fluxos["cliente"].map(is_alvo)
# acessória sugerida/acess_delta/receita_potencial são calculadas mais abaixo, depois do
# merge com vol12_kt (volume realizado nos últimos 12 meses) — ver perto do merge com
# _op_enrich, pois a média de referência por produto agora exige vol12_kt≥10kt.

# ------------------------------------------------------------- COMPARATIVO TARIFA
# ===== BASE COMPLETA DE TARIFAS + ISONOMIA (Res. 3.694/2011 · Lei 10.233/2001) =====
# Fonte primária: tarifas_praticadas (a base "Base dados tarifas e acessórias" —
# tarifas efetivamente praticadas, já com %teto e %ipoa próprios). ipoa_teto entra
# só como ENRIQUECIMENTO de corredor/ferrovia via chave natural (cliente×O/D×produto)
# — o join por nº de item estava errado: os itens não se correspondem entre as bases.
tf = q("""SELECT item, cliente, origem, destino, produto,
                 frete_trackage AS frete, demais_servicos AS acess,
                 teto AS pct_teto, ipoa, km_rota, vigencia
          FROM tarifas_praticadas WHERE frete_trackage IS NOT NULL""")
tf["cliente"] = tf["cliente"].map(canon)
for _c in ["frete","acess","pct_teto","ipoa","km_rota"]:
    tf[_c] = pd.to_numeric(tf[_c], errors="coerce")
tf["acess"] = tf["acess"].fillna(0.0)
tf["total"] = tf["frete"] + tf["acess"]
tf["vigencia"] = tf["vigencia"].astype(str).str.slice(0, 10)
tf["vig_dt"] = pd.to_datetime(tf["vigencia"], errors="coerce")
# alguns itens vêm sem origem/destino/produto (registro incompleto na base) — antes o
# groupby(dropna=True) descartava essas linhas silenciosamente; o drop_duplicates abaixo
# não teria esse comportamento por padrão, então precisa do dropna explícito aqui.
tf = tf.dropna(subset=["origem", "destino", "produto"])
_enrich = q("SELECT DISTINCT cliente, origem, destino, produto, corredor_vli, ferrovia_fatura FROM ipoa_teto")
_enrich["cliente"] = _enrich["cliente"].map(canon)
_enrich = _enrich.drop_duplicates(["cliente","origem","destino","produto"])
tf = tf.merge(_enrich, on=["cliente","origem","destino","produto"], how="left")
# dedupe por fluxo (cliente×O/D×produto): quando há múltiplos itens/contratos pro mesmo
# fluxo, usar só o de vigência MAIS RECENTE — não misturar preços de contratos/períodos
# diferentes numa mediana. Achado do usuário: alguns fluxos têm variação grande de preço
# entre vigências (ex.: TDC óleo diesel PPN→QPM varia 165% entre 2 vigências) — blendar
# tudo distorcia o comparativo, e comparar o "contrato antigo" de um cliente contra o
# "contrato novo" de outro seria misturar períodos diferentes disfarçado de par isonômico.
tf["n_itens"] = tf.groupby(["cliente","origem","destino","produto"])["item"].transform("nunique")
# checado: 152 dos 155 fluxos com múltiplos itens têm TODOS os itens na MESMA vigência (a
# data não distingue "mais recente" nesses casos — só 3 fluxos têm vigências realmente
# diferentes entre itens). Nesses empates, desempata por item MAIOR (assume-se cadastro
# mais recente) — não é uma garantia de período, mas pelo menos é determinístico e pega
# um contrato real inteiro, nunca mais uma mediana "Frankenstein" que mistura frete de um
# item com acessória de outro (o que dava um total que nenhum contrato de fato tinha).
tf = tf.sort_values(["vig_dt","item"], ascending=[False,False], kind="mergesort")
tf = tf.drop_duplicates(["cliente","origem","destino","produto"], keep="first")
tf = tf.rename(columns={"corredor_vli": "corredor", "ferrovia_fatura": "ferrovia", "km_rota": "km"})
tf = tf.drop(columns=["vig_dt"])
# frete implícito no orçamento 2026 (Tendência 6+6_Aceite v18), por fluxo cliente×O/D×produto —
# SUM(rec_fr)/SUM(vol_tu) do vli_pnl (mesma lição de somar-antes-de-dividir do preço por cliente).
# Cobertura parcial (~18% dos fluxos de tf) mas onde bate é preço REAL do orçamento aceito —
# cruza com o "frete" contratado (tarifas_praticadas) pra achar onde o orçamento já embute alta/baixa.
_t26 = q("""SELECT cliente, origem, destino, mercadoria AS produto, SUM(rec_fr) recfr, SUM(vol_tu) voltu
            FROM vli_pnl WHERE modal='Ferrovia' AND panorama LIKE '2026%'
            GROUP BY cliente, origem, destino, mercadoria""")
_t26["cliente"] = _t26["cliente"].map(canon)
_t26 = _t26.groupby(["cliente","origem","destino","produto"], as_index=False)[["recfr","voltu"]].sum()
# corta fluxos de volume irrisório (< 10.000 t/ano): a razão fica ruidosa e mistura
# linhas com receita negativa (estorno/ajuste) — achado real: LDC PPT->QPM deu -76%
# com só 5,8kt/ano em 5 meses de dado, não é sinal de preço confiável, é ruído contábil
_t26 = _t26[(_t26["recfr"]>0) & (_t26["voltu"]>=10000)]
_t26["frete_26"] = _t26["recfr"] / _t26["voltu"]
tf = tf.merge(_t26[["cliente","origem","destino","produto","frete_26"]], on=["cliente","origem","destino","produto"], how="left")
tf["gap_26_pct"] = np.where(tf["frete_26"].notna(), (tf["frete_26"]/tf["frete"]-1)*100, np.nan)

# ===== Isonomia SELECTA EBJ→IUF: par sintético "espelhado" da CARAMURU por km =====
# Pedido do usuário (20/jul/2026): SELECTA não tem par real na rota EBJ→IUF FARELO DE SOJA
# (n_cli_rota=1, sem comparação de isonomia possível). Usar a rota mais próxima em distância
# da CARAMURU (EPO→ISN, mesmo produto — confirmada com o usuário entre as 2 opções
# disponíveis, a outra era EPO→VTU) como referência de mercado, escalando o preço dela
# LINEARMENTE pela razão de km — pedido explícito do usuário ("proporcional por km rodado",
# NÃO a fórmula fixa+variável do teto ANTT). Insere um cliente sintético "CARAMURU (ref. km)"
# na mesma chave de rota da SELECTA — assim ele entra automaticamente como par real em TODA
# a maquinaria de isonomia já existente (n_cli_rota, med_pares, min_pares, melhor_pagador),
# tanto no Comparativo de Tarifas quanto na aba Isonomia Tarifária do Painel do Cliente.
# Nome do cliente NUNCA deve ser literalmente "CARAMURU" (colidiria com o cliente real em
# qualquer filtro por nome exato no front) — daí o sufixo "(ref. km)".
_ESPELHO_KM_RAZAO = None   # exposto pro bloco de isonomia MENSAL (saz) mais abaixo reusar a mesma razão
_sel_ebj_iuf = tf[(tf["cliente"]=="SELECTA") & (tf["origem"]=="EBJ") & (tf["destino"]=="IUF") & (tf["produto"]=="FARELO DE SOJA")]
_car_epo_isn = tf[(tf["cliente"]=="CARAMURU") & (tf["origem"]=="EPO") & (tf["destino"]=="ISN") & (tf["produto"]=="FARELO DE SOJA")]
if len(_sel_ebj_iuf) and len(_car_epo_isn):
    _km_sel = _sel_ebj_iuf.iloc[0]["km"]
    _car = _car_epo_isn.iloc[0]
    _km_car = _car["km"]
    if pd.notna(_km_sel) and pd.notna(_km_car) and _km_car:
        _razao = _km_sel / _km_car
        _ESPELHO_KM_RAZAO = _razao   # reusado no espelho mensal (saz), mais abaixo
        _frete_esp = round(_car["frete"] * _razao, 2)
        _acess_esp = round(_car["acess"] * _razao, 2)
        _espelho = {
            "item": "ESPELHO-CARAMURU-KM", "cliente": "CARAMURU (ref. km)",
            "origem": "EBJ", "destino": "IUF", "produto": "FARELO DE SOJA",
            "frete": _frete_esp, "acess": _acess_esp, "total": round(_frete_esp + _acess_esp, 2),
            "pct_teto": _car["pct_teto"], "ipoa": _car["ipoa"], "km": _km_sel,
            "vigencia": "espelho por km (base: CARAMURU EPO→ISN)",
            "corredor": _car.get("corredor"), "ferrovia": _car.get("ferrovia"), "n_itens": 1,
        }
        tf = pd.concat([tf, pd.DataFrame([_espelho])], ignore_index=True)
        print(f"  Isonomia SELECTA EBJ→IUF: par espelhado da CARAMURU (EPO→ISN R$ {_car['total']:.2f}/t "
              f"@ {_km_car:.0f}km) escalado por km ({_km_sel:.0f}/{_km_car:.0f}={_razao:.3f}) "
              f"-> R$ {_frete_esp+_acess_esp:.2f}/t")

# ===== Isonomia CMOC ↔ MOSAIC (Vale Fertilizantes): ROCHA e ENXOFRE, espelho bidirecional por km =====
# Pedido do usuário (22/jul/2026): comparar CMOC ROCHA/ENXOFRE com os fluxos equivalentes da
# MOSAIC (ex-Vale Fertilizantes, unificada no canon.py nesta mesma sessão) proporcional à
# distância — E o inverso (MOSAIC ver CMOC como par). Cada par físico gera DOIS espelhos
# sintéticos (mesmo mecanismo do espelho SELECTA↔CARAMURU acima), um em cada direção. Só cria
# o espelho quando AMBOS os lados têm km_rota real — nunca estima distância (MOSAIC ENXOFRE
# ICZ→ZVF não tem km na base — fica de fora, sinalizado no log).
_pares_km_cmoc_mosaic = [
    ("CMOC", "EYC", "IFA", "ROCHA FOSF SECA", "MOSAIC", "ELC", "ZVF", "ROCHA FOS UMIDA"),
    ("CMOC", "IUF", "EYC", "ENXOFRE", "MOSAIC", "IUF", "ZVF", "ENXOFRE"),
]
for _cli_a, _o_a, _d_a, _prod_a, _cli_b, _o_b, _d_b, _prod_b in _pares_km_cmoc_mosaic:
    _ra = tf[(tf["cliente"]==_cli_a)&(tf["origem"]==_o_a)&(tf["destino"]==_d_a)&(tf["produto"]==_prod_a)]
    _rb = tf[(tf["cliente"]==_cli_b)&(tf["origem"]==_o_b)&(tf["destino"]==_d_b)&(tf["produto"]==_prod_b)]
    if not len(_ra) or not len(_rb):
        print(f"  Isonomia {_cli_a}↔{_cli_b} ({_prod_a}/{_prod_b}): fluxo não encontrado em "
              f"tarifas_praticadas, pulando.")
        continue
    _a, _b = _ra.iloc[0], _rb.iloc[0]
    if pd.isna(_a["km"]) or pd.isna(_b["km"]) or not _b["km"]:
        print(f"  Isonomia {_cli_a}↔{_cli_b} ({_prod_a}/{_prod_b}): km faltando de um dos lados, "
              f"pulando (sem estimar).")
        continue
    _razao_ab = _a["km"] / _b["km"]
    _frete_b_esp, _acess_b_esp = round(_b["frete"]*_razao_ab, 2), round(_b["acess"]*_razao_ab, 2)
    _espelho_b = {
        "item": f"ESPELHO-{_cli_b}-KM", "cliente": f"{_cli_b} (ref. km)",
        "origem": _o_a, "destino": _d_a, "produto": _prod_a,
        "frete": _frete_b_esp, "acess": _acess_b_esp, "total": round(_frete_b_esp+_acess_b_esp, 2),
        "pct_teto": _b["pct_teto"], "ipoa": _b["ipoa"], "km": _a["km"],
        "vigencia": f"espelho por km (base: {_cli_b} {_o_b}→{_d_b})",
        "corredor": _b.get("corredor"), "ferrovia": _b.get("ferrovia"), "n_itens": 1,
    }
    _razao_ba = _b["km"] / _a["km"]
    _frete_a_esp, _acess_a_esp = round(_a["frete"]*_razao_ba, 2), round(_a["acess"]*_razao_ba, 2)
    _espelho_a = {
        "item": f"ESPELHO-{_cli_a}-KM", "cliente": f"{_cli_a} (ref. km)",
        "origem": _o_b, "destino": _d_b, "produto": _prod_b,
        "frete": _frete_a_esp, "acess": _acess_a_esp, "total": round(_frete_a_esp+_acess_a_esp, 2),
        "pct_teto": _a["pct_teto"], "ipoa": _a["ipoa"], "km": _b["km"],
        "vigencia": f"espelho por km (base: {_cli_a} {_o_a}→{_d_a})",
        "corredor": _a.get("corredor"), "ferrovia": _a.get("ferrovia"), "n_itens": 1,
    }
    tf = pd.concat([tf, pd.DataFrame([_espelho_b, _espelho_a])], ignore_index=True)
    print(f"  Isonomia {_cli_a} {_o_a}→{_d_a} ↔ {_cli_b} {_o_b}→{_d_b} ({_prod_a}): espelhos "
          f"bidirecionais por km (razão {_razao_ab:.3f}) inseridos.")

# ---- Família tarifária carvão/coque, só p/ COMPARAÇÃO DE TARIFA em fluxos origem VTU
# (jul/2026) — pedido do usuário: "para fluxos origem VTU colocar como mesma familia coque,
# carvao antracito... a tarifa mais barata só pega carvão, deveria pegar todos esses". Do
# ponto de vista de MANOBRA, carvão mineral e as variantes de coque/antracito são cargas
# sólidas minerais a granel manuseadas do mesmo jeito no mesmo terminal — então a tarifa de
# manobra/acessória é comparável entre elas, mesmo sendo produtos distintos.
# ATENÇÃO — isto é EXCLUSIVAMENTE sobre PEER-COMPARISON DE TARIFA/PREÇO (gk abaixo e o bloco
# de R$/km de siderurgia logo a seguir). NUNCA reutilizar esta constante para volume: a família
# `_PROD_FAMILIA_VTU` que poolava volume dentro de `pcNormProd` (frontend) foi REMOVIDA nesta
# mesma sessão porque poolar volume entre produtos distintos estava errado (CARVAO MINERAL,
# ANTRACITO e COQUE GROSSO da GERDAU em VTU→VOB mostravam o MESMO número de kt movimentado,
# o que é falso — são toneladas genuinamente diferentes). Aqui não se soma volume nenhum, só
# se amplia o PEER SET usado no cálculo de mediana/menor tarifa.
# Lista de variantes confirmada na base (volume_hist + tarifas_praticadas, jul/2026):
# CARVAO MINERAL, ANTRACITO, COQUE, COQUE GROSSO, COQUE FINO, COQUE PETROLEO,
# COQUE VERDE DE PETROLEO.
_FAMILIA_CARVAO_COQUE_TARIFA = {
    "CARVAO MINERAL", "ANTRACITO", "COQUE", "COQUE GROSSO", "COQUE FINO",
    "COQUE PETROLEO", "COQUE VERDE DE PETROLEO",
}
# chave de agrupamento "efetiva" p/ produto: vira o rótulo de família quando a ORIGEM é VTU e
# o produto é uma variante carvão/coque/antracito; nas demais origens (ou produtos fora da
# família) fica igual ao produto real — nenhuma outra comparação do sistema é afetada.
tf["_prod_grp_tarifa"] = np.where(
    (tf["origem"] == "VTU") & tf["produto"].isin(_FAMILIA_CARVAO_COQUE_TARIFA),
    "CARVAO/COQUE/ANTRACITO (família VTU)",
    tf["produto"],
)

# pares de isonomia = mesma rota (O/D) + mesmo produto (ou família carvão/coque em VTU), clientes distintos
gk = ["origem","destino","_prod_grp_tarifa"]
grp = tf.groupby(gk)
tf["n_cli_rota"] = grp["cliente"].transform("nunique")
tf["med_pares"]  = grp["total"].transform("median")
tf["min_pares"]  = grp["total"].transform("min")
tf["max_pares"]  = grp["total"].transform("max")
_min_idx = tf.loc[tf.groupby(gk)["total"].idxmin(), gk + ["cliente"]].rename(columns={"cliente":"melhor_pagador"})
tf = tf.merge(_min_idx, on=gk, how="left")
tf["gap_med"] = np.where(tf["n_cli_rota"]>=2, tf["total"]-tf["med_pares"], np.nan)
tf["gap_pct"] = np.where(tf["n_cli_rota"]>=2, (tf["total"]/tf["med_pares"]-1)*100, np.nan)
# anualização: volume do trio cliente×O/D (canônico), rateado entre os produtos do trio
tf["vol_t"] = tf.apply(lambda r: vmap.get((r["cliente"], r["origem"], r["destino"]), (None,None))[0], axis=1)
_nprod = tf.groupby(["cliente","origem","destino"])["produto"].transform("nunique")
tf["vol_t"] = tf["vol_t"] / _nprod
tf["oport_ano"] = np.where((tf["gap_med"]>0) & tf["vol_t"].notna(), tf["gap_med"]*tf["vol_t"], 0.0)

# ---- Siderurgia: isonomia por R$/km (rotas diferentes, mesmo produto) — jul/2026 ----
# Pedido do usuário: Usiminas/Gerdau/ArcelorMittal/Aperam têm cada fluxo numa rota (origem/
# destino) PRÓPRIA — não há par na mesma rota, então a comparação de isonomia por "tarifa
# total" bruta (gk acima) não funciona: rota mais longa custa mais em R$/t por natureza.
# Normalizando por R$/km (tarifa total ÷ distância), dá pra comparar isonomia ENTRE ROTAS
# DIFERENTES, desde que o produto seja o mesmo. Cohort FIXO — só estes 4 clientes por nome,
# não expande sozinho pra outro cliente de minério/siderurgia que porventura carregue os
# mesmos produtos (ex. CMOC também tem MINERIO FERRO, mas não foi pedido pelo usuário).
_SIDER_TOKENS = ("USIMINAS", "GERDAU", "ARCELORMITTAL", "APERAM")
tf["sider"] = tf["cliente"].astype(str).str.upper().apply(lambda c: any(t in c for t in _SIDER_TOKENS))
tf["rs_km"] = np.where(tf["km"] > 0, tf["total"] / tf["km"], np.nan)
_KM_COLS = ["n_cli_prod_km", "med_km", "min_km", "melhor_pagador_km", "gap_km", "gap_km_pct", "oport_km_ano"]
# _sd é construído ANTES de tf ganhar as colunas _KM_COLS (senão o merge abaixo colide com
# colunas já-nomeadas iguais em tf e o pandas sufixa _x/_y em vez de preencher a coluna certa)
_sd = tf[tf["sider"] & tf["rs_km"].notna()].copy()
for _c in _KM_COLS:
    tf[_c] = np.nan
if len(_sd):
    _orig_idx = _sd.index
    # Two-pass: (1) stats "de sempre" por PRODUTO EXATO (cross-rota, ignora origem) — igual ao
    # comportamento original, calculado sobre TODO o _sd (inclui as linhas VTU também, como
    # sempre incluiu). (2) stats da FAMÍLIA carvão/coque/antracito, só entre linhas com origem
    # VTU (peer pool separado). Cada linha usa (2) quando é VTU+família, senão usa (1) — assim
    # uma linha NÃO-VTU do mesmo produto continua vendo EXATAMENTE os mesmos peers/estatística
    # de antes (nunca perde peer só porque uma linha VTU do mesmo produto "saiu" pra família).
    _gkm = _sd.groupby("produto")
    _sd["_n_prod"] = _gkm["cliente"].transform("nunique")
    _sd["_med_prod"] = _gkm["rs_km"].transform("median")
    _sd["_min_prod"] = _gkm["rs_km"].transform("min")
    _min_idx_prod = _sd.loc[_gkm["rs_km"].idxmin(), ["produto", "cliente"]].rename(columns={"cliente": "_melhor_prod"})
    _sd = _sd.merge(_min_idx_prod, on="produto", how="left")
    _sd.index = _orig_idx

    _is_fam_vtu = (_sd["origem"] == "VTU") & _sd["produto"].isin(_FAMILIA_CARVAO_COQUE_TARIFA)
    _fam_pool = _sd[_is_fam_vtu]
    if len(_fam_pool):
        _gfam = _fam_pool.groupby("_prod_grp_tarifa")
        _famstat = pd.DataFrame({
            "n_cli_prod_km": _gfam["cliente"].transform("nunique"),
            "med_km": _gfam["rs_km"].transform("median"),
            "min_km": _gfam["rs_km"].transform("min"),
        }, index=_fam_pool.index)
        _min_idx_fam = _fam_pool.loc[_gfam["rs_km"].idxmin(), ["_prod_grp_tarifa", "cliente"]].rename(columns={"cliente": "melhor_pagador_km"})
        _famstat = _famstat.join(_fam_pool[["_prod_grp_tarifa"]]).merge(
            _min_idx_fam, on="_prod_grp_tarifa", how="left").set_index(_fam_pool.index)
    else:
        _famstat = pd.DataFrame(columns=["n_cli_prod_km", "med_km", "min_km", "melhor_pagador_km"])

    _sd["n_cli_prod_km"] = _sd["_n_prod"]; _sd["med_km"] = _sd["_med_prod"]
    _sd["min_km"] = _sd["_min_prod"]; _sd["melhor_pagador_km"] = _sd["_melhor_prod"]
    for _c in ["n_cli_prod_km", "med_km", "min_km", "melhor_pagador_km"]:
        _sd.loc[_famstat.index, _c] = _famstat[_c]
    _sd = _sd.drop(columns=["_n_prod", "_med_prod", "_min_prod", "_melhor_prod"])
    _sd["gap_km"] = np.where(_sd["n_cli_prod_km"] >= 2, _sd["rs_km"] - _sd["med_km"], np.nan)
    _sd["gap_km_pct"] = np.where(_sd["n_cli_prod_km"] >= 2, (_sd["rs_km"] / _sd["med_km"] - 1) * 100, np.nan)
    _sd["oport_km_ano"] = np.where((_sd["gap_km"] > 0) & _sd["vol_t"].notna(),
                                    _sd["gap_km"] * _sd["km"] * _sd["vol_t"], 0.0)
    for _c in _KM_COLS:
        tf.loc[_sd.index, _c] = _sd[_c]

tf["alvo"] = tf["cliente"].map(is_alvo)
tf = tf.sort_values("oport_ano", ascending=False)
comp_kpis = {"n_fluxos": int(len(tf)), "n_rotas_comp": int(tf[tf["n_cli_rota"]>=2].groupby(gk).ngroups),
             "oport_total": round(float(tf["oport_ano"].sum()),0),
             "gap_max": round(float(tf["gap_pct"].max() if tf["gap_pct"].notna().any() else 0),1)}

# ---- Comparativo SAZONAL (visão mensal, grãos) ----
# tarifas_praticadas não tem granularidade mensal real (vigência é vencimento de contrato,
# só 24 valores únicos, 78% cravados numa única data — não dá pra comparar "mesmo mês" com
# essa base). Achado do usuário: pra grãos/farelo o preço varia bastante mês a mês (sazonalidade
# de mercado), então comparar um cliente de março com outro de janeiro distorce o gap. Aqui
# usamos o vli_pnl (panorama = ano-mês real), que tem receita/volume por fluxo×mês de verdade —
# preço é REALIZADO (rec_fr/vol_tu), não contratado, métrica diferente da "Base completa".
# 2026 não tem panorama "Real" (só "2026 - Tendência 6+6_Aceite v18") — a pedido do usuário,
# tratamos jan-jul/2026 como realizado (meses já fechados) e ago-dez/2026 como projeção pura,
# que fica de fora (senão contaminaria o "preço realizado" com número orçado).
# jul/2026: filtro de mercadoria REMOVIDO (era só grãos) — o Painel do Cliente usa esta base
# pra isonomia mês a mês de qualquer cliente (grãos/fert com lógica mensal como primária;
# demais clientes ganham o filtro de mês/ano como visão secundária). ~5,5 mil linhas.
saz = q("""SELECT cliente, origem, destino, mercadoria AS produto, ano, mes,
                  SUM(rec_fr) recfr, SUM(vol_tu) voltu
           FROM vli_pnl
           WHERE modal='Ferrovia'
             AND (panorama LIKE '%Real%' OR (panorama LIKE '2026%' AND mes<=7))
           GROUP BY cliente, origem, destino, mercadoria, ano, mes""")
saz["cliente"] = saz["cliente"].map(canon)
saz = saz.groupby(["cliente","origem","destino","produto","ano","mes"], as_index=False)[["recfr","voltu"]].sum()
# corta ruído de fluxos residuais (<1 mil t no mês — proporcional ao piso de 10 mil t/ano
# usado no resto do painel, já que aqui a janela é 1 mês em vez de 1 ano)
saz = saz[(saz["recfr"] > 0) & (saz["voltu"] >= 1000)]
saz["preco"] = saz["recfr"] / saz["voltu"]
# jul/2026: isonomia de grãos no Corredor Norte — pedido do usuário. PIN/PPN são pontos de
# escoamento da MESMA rota (PIN é onde outros players carregam, PPN é onde a Agrex carrega);
# PPT/PIP idem (PPT = Nova Agri, PIP = ponto genérico dos demais). Pra fins de comparação de
# isonomia (mediana/menor pagador), tratamos os dois pares como a MESMA rota — sem isso, Agrex
# (só em PPN) e Nova Agri (só em PPT) ficavam sem pares suficientes pra comparação, mesmo
# carregando no mesmo corredor/destino que os outros. "origem_iso" é só a CHAVE DE AGRUPAMENTO
# das estatísticas de pares (med_mes/min_mes/gap/oport) — a coluna "origem" exibida por linha
# continua a estação real onde o cliente carregou, sem alteração. Só grãos (demais produtos e
# demais estações do painel não são afetados).
_ROTA_GRUPO_NORTE = {"PIN": "PIN+PPN", "PPN": "PIN+PPN", "PPT": "PPT+PIP", "PIP": "PPT+PIP"}
_GRAO_RE = r"SOJA|MILHO|FARELO|SORGO"
_is_grao = saz["produto"].astype(str).str.upper().str.contains(_GRAO_RE, regex=True)
saz["origem_iso"] = np.where(_is_grao, saz["origem"].map(_ROTA_GRUPO_NORTE).fillna(saz["origem"]), saz["origem"])

# ===== Isonomia SELECTA EBJ→IUF: espelho MENSAL da CARAMURU por km (continuação do espelho
# de contrato acima, em `tf`) — pedido do usuário (20/jul/2026): a rota é grãos com preço
# mensal realizado, então a visão PADRÃO do Painel do Cliente é "mês a mês" (SAZ), não
# contrato — sem espelhar aqui também, o usuário só veria o par sintético trocando pra
# "Contratos vigentes" manualmente. Réplica mês a mês: pra cada (produto exato, ano, mês) que
# a SELECTA tem em EBJ→IUF (qualquer variante "FARELO DE SOJA*" — a base tem 3 grafias
# diferentes pro mesmo produto), busca o preço da CARAMURU em EPO→ISN no MESMO mês (agregando
# as variantes dela também) e escala pela razão de km — precisa ser o produto EXATO de cada
# linha da SELECTA (não só a família) porque `gk_saz` agrupa por produto exato, e cada
# variante da SELECTA forma seu próprio grupo de pares.
if _ESPELHO_KM_RAZAO is not None:
    _FARELO_RE = r"FARELO\s*DE\s*SOJA"
    _car_saz_mes = saz[(saz["cliente"]=="CARAMURU") & (saz["origem"]=="EPO") & (saz["destino"]=="ISN")
                        & (saz["produto"].astype(str).str.upper().str.contains(_FARELO_RE, regex=True))]
    _car_mensal = _car_saz_mes.groupby(["ano","mes"], as_index=False)[["recfr","voltu"]].sum()
    _car_mes_map = {(int(r.ano), int(r.mes)): (r.recfr/r.voltu, r.voltu) for r in _car_mensal.itertuples() if r.voltu}
    _sel_saz_mes = saz[(saz["cliente"]=="SELECTA") & (saz["origem"]=="EBJ") & (saz["destino"]=="IUF")
                        & (saz["produto"].astype(str).str.upper().str.contains(_FARELO_RE, regex=True))]
    _espelho_mensal = []
    for (produto_exato, ano, mes), _g in _sel_saz_mes.groupby(["produto","ano","mes"]):
        chave = (int(ano), int(mes))
        if chave not in _car_mes_map:
            continue
        _preco_car, _voltu_car = _car_mes_map[chave]
        _preco_esp = round(_preco_car * _ESPELHO_KM_RAZAO, 2)
        _espelho_mensal.append({
            "cliente": "CARAMURU (ref. km)", "origem": "EBJ", "destino": "IUF", "produto": produto_exato,
            "ano": int(ano), "mes": int(mes), "recfr": round(_preco_esp*_voltu_car, 2), "voltu": round(_voltu_car, 2),
            "preco": _preco_esp, "origem_iso": "EBJ",
        })
    if _espelho_mensal:
        saz = pd.concat([saz, pd.DataFrame(_espelho_mensal)], ignore_index=True)
        print(f"  Isonomia SELECTA EBJ→IUF (mensal): {len(_espelho_mensal)} meses espelhados da "
              f"CARAMURU EPO→ISN (razão km {_ESPELHO_KM_RAZAO:.3f})")

gk_saz = ["origem_iso", "destino", "produto", "ano", "mes"]
grp_saz = saz.groupby(gk_saz)
saz["n_cli_mes"] = grp_saz["cliente"].transform("nunique")
saz["med_mes"] = grp_saz["preco"].transform("median")
saz["min_mes"] = grp_saz["preco"].transform("min")
_min_idx_saz = saz.loc[grp_saz["preco"].idxmin(), gk_saz + ["cliente"]].rename(columns={"cliente": "melhor_pagador"})
saz = saz.merge(_min_idx_saz, on=gk_saz, how="left")
saz["gap_pct"] = np.where(saz["n_cli_mes"] >= 2, (saz["preco"]/saz["med_mes"]-1)*100, np.nan)
saz["gap_min_pct"] = np.where(saz["n_cli_mes"] >= 2, (saz["preco"]/saz["min_mes"]-1)*100, np.nan)
saz["oport_mes"] = np.where((saz["preco"] > saz["med_mes"]) & (saz["n_cli_mes"] >= 2),
                             (saz["preco"] - saz["med_mes"]) * saz["voltu"], 0.0)
saz["oport_min_mes"] = np.where((saz["preco"] > saz["min_mes"]) & (saz["n_cli_mes"] >= 2),
                                 (saz["preco"] - saz["min_mes"]) * saz["voltu"], 0.0)
saz["alvo"] = saz["cliente"].map(is_alvo)
saz["mes_lbl"] = saz["ano"].astype(str) + "-" + saz["mes"].astype(str).str.zfill(2)
saz = saz.sort_values(["ano", "mes", "oport_mes"], ascending=[False, False, False])
sazonal_full = rec(saz.round(2))
_meses_disp = sorted(saz["mes_lbl"].unique().tolist(), reverse=True)
_ult_mes = _meses_disp[0] if _meses_disp else None
saz_kpis = {
    "n_linhas": int(len(saz)), "meses_disponiveis": _meses_disp, "ultimo_mes": _ult_mes,
    "oport_total_ult_mes": round(float(saz.loc[saz["mes_lbl"] == _ult_mes, "oport_mes"].sum()), 0) if _ult_mes else 0.0,
    "n_fluxos_ult_mes": int((saz["mes_lbl"] == _ult_mes).sum()) if _ult_mes else 0,
}
# tarifas_full e iso_ins só são montados mais abaixo (depois de _v12map existir, pro gap/
# oportunidade vs. menor tarifa poder usar volume realizado 12m) — ver perto do bloco de negociação.

# ------------------------------------------------------------------- VLI / MARGEM
marg_cli = q(f"""SELECT cliente, SUM(rec_total) rec, SUM(ind_mrg) mrg,
                       (COALESCE(SUM(rec_man),0)+COALESCE(SUM(rec_sa),0)) acess
                FROM vli_pnl WHERE {P24} AND rec_total>0 GROUP BY cliente""")
marg_cli["cliente"]=marg_cli["cliente"].map(canon)   # agrupa entidades no grupo econômico
marg_cli=(marg_cli.groupby("cliente", as_index=False)[["rec","mrg","acess"]].sum())
marg_cli=marg_cli[marg_cli["rec"]>20e6].sort_values("rec", ascending=False)
marg_cli["margem_pct"]=(marg_cli["mrg"]/marg_cli["rec"]*100).round(1)
marg_cli["pct_acess"]=(marg_cli["acess"]/marg_cli["rec"]*100).round(1)
marg_cli["rec_mi"]=(marg_cli["rec"]/1e6).round(1)
marg_cli["alvo"]=marg_cli["cliente"].map(is_alvo)
# tarifa média R$/TU 2025 (Real) vs 2026 (Tendência 6+6_Aceite v18) — sinal de preço:
# pra onde a concessionária está levando o preço no orçamento aceito de 2026 por cliente.
# soma receita e volume primeiro (cada fluxo tem várias linhas por "estágio" —
# ORI/CAR/SUP — e receita e volume raramente vêm preenchidos na mesma linha; um filtro
# rec_fr>0 AND vol_tu>0 por linha jogava fora quase tudo) e só depois divide.
_prc = q("""SELECT panorama, cliente, SUM(rec_fr) recfr, SUM(vol_tu) voltu
            FROM vli_pnl WHERE modal='Ferrovia' AND (panorama LIKE '2025%' OR panorama LIKE '2026%')
            GROUP BY panorama, cliente""")
_prc["cliente"] = _prc["cliente"].map(canon)
_prc = _prc.groupby(["panorama","cliente"], as_index=False)[["recfr","voltu"]].sum()
_prc = _prc[(_prc["recfr"]>0) & (_prc["voltu"]>0)]
_prc["tarifa"] = _prc["recfr"] / _prc["voltu"]
_prc["ano_p"] = _prc["panorama"].str.slice(0,4)
_ptab = _prc.pivot_table(index="cliente", columns="ano_p", values="tarifa", aggfunc="first").reset_index()
_ptab.columns.name = None
_ptab = _ptab.rename(columns={"2025":"tarifa_25","2026":"tarifa_26"})
for _c in ["tarifa_25","tarifa_26"]:
    if _c not in _ptab: _ptab[_c] = np.nan
_ptab["var_tarifa_pct"] = np.where(_ptab["tarifa_25"].notna() & _ptab["tarifa_26"].notna(),
                                    (_ptab["tarifa_26"]/_ptab["tarifa_25"]-1)*100, np.nan)
marg_cli = marg_cli.merge(_ptab[["cliente","tarifa_25","tarifa_26","var_tarifa_pct"]], on="cliente", how="left")
for _c in ["tarifa_25","tarifa_26","var_tarifa_pct"]:
    marg_cli[_c] = marg_cli[_c].round(1)
marg_cor = q(f"""SELECT corredor_vli, SUM(rec_total) rec, SUM(ind_mrg) mrg
                FROM vli_pnl WHERE {P24} AND rec_total>0 AND corredor_vli IS NOT NULL
                GROUP BY corredor_vli HAVING rec>10e6 ORDER BY rec DESC""")
marg_cor["margem_pct"]=(marg_cor["mrg"]/marg_cor["rec"]*100).round(1)
marg_cor["rec_mi"]=(marg_cor["rec"]/1e6).round(0)
panor = q("""SELECT panorama, SUM(rec_total) rec, SUM(ind_mrg)*1.0/NULLIF(SUM(rec_total),0) m,
                    SUM(CASE WHEN modal='Ferrovia' THEN rec_fr END)*1.0
                      /NULLIF(SUM(CASE WHEN modal='Ferrovia' THEN vol_tu END),0) tarifa_media
             FROM vli_pnl GROUP BY panorama ORDER BY panorama""")
panor["margem_pct"]=(panor["m"]*100).round(0); panor["rec_bi"]=(panor["rec"]/1e9).round(1)
panor["tarifa_media"]=panor["tarifa_media"].round(1)

# ------------------------------------------------------------ CONTRATOS EXPIRANDO
contr = q("""SELECT cliente,origem,destino,produto,vigencia,frete_trackage AS frete,
                    demais_servicos AS acess, teto, km_rota
             FROM tarifas_praticadas WHERE vigencia IS NOT NULL""")
contr["cliente"] = contr["cliente"].map(canon)
for c in ["frete","acess","teto","km_rota"]:
    contr[c]=pd.to_numeric(contr[c], errors="coerce")
contr["vigencia"]=contr["vigencia"].astype(str).str.slice(0,10)
contr["ano_exp"]=contr["vigencia"].str.slice(0,4)
contr["tarifa_total"]=contr["frete"]+contr["acess"].fillna(0)
contr["pct_teto"]=contr["teto"]   # a coluna 'teto' da base já é o %teto (frete/teto), 0–1
contr["alvo"]=contr["cliente"].map(is_alvo)
contr_ano=(contr.groupby("ano_exp").size().reset_index(name="n").sort_values("ano_exp"))
# vencidos (já passaram) vs. vencendo no restante de 2026
_hoje = pd.Timestamp.today().normalize()
contr["vig_dt"] = pd.to_datetime(contr["vigencia"], errors="coerce")
contr_vencidos = int((contr["vig_dt"] < _hoje).sum())
contr_venc_2026 = int(((contr["vig_dt"] >= _hoje) & (contr["vig_dt"] <= pd.Timestamp("2026-12-31"))).sum())
contr_lista=contr.sort_values("vigencia")[["cliente","origem","destino","produto",
             "vigencia","tarifa_total","teto","pct_teto","alvo"]].round(2)

# -------------------------------------------------- MERCADO: frete / valor da carga
try:
    merc = q("""SELECT t.cliente AS cliente, t.origem, t.destino, t.produto,
                       (t.frete_trackage + COALESCE(t.demais_servicos,0)) AS tarifa_total,
                       p.rs_tonelada, p.commodity, p.praca, p.data
                FROM tarifas_praticadas t
                JOIN precos_commodity p ON t.produto = p.produto_base
                WHERE t.frete_trackage IS NOT NULL""")
    merc["cliente"] = merc["cliente"].map(canon)
    merc["frete_pct_valor"] = (merc["tarifa_total"]/merc["rs_tonelada"]*100).round(1)
    merc["alvo"] = merc["cliente"].map(is_alvo)
    merc_produto = (merc.groupby(["produto","commodity","rs_tonelada"])
                      .agg(n=("cliente","size"), tarifa_med=("tarifa_total","mean"),
                           frete_pct_med=("frete_pct_valor","mean")).reset_index())
    merc_produto["tarifa_med"]=merc_produto["tarifa_med"].round(1)
    merc_produto["frete_pct_med"]=merc_produto["frete_pct_med"].round(1)
    precos = q("SELECT commodity, praca, rs_saca, kg_saca, rs_tonelada, data, fonte FROM precos_commodity")
    merc_lista = merc.sort_values("frete_pct_valor", ascending=False)[
        ["cliente","produto","origem","destino","tarifa_total","rs_tonelada","frete_pct_valor","alvo"]].round(2)
    mercado = {"precos": rec(precos), "por_produto": rec(merc_produto), "lista": rec(merc_lista)}
except Exception as e:
    mercado = {"precos": [], "por_produto": [], "lista": []}
    print("  ! módulo mercado indisponível:", e)

# preços de portos — elevação portuária VLI (série mensal, Vitória/Santos/São Luís) x
# referência pública RUMO (Elevações Portuárias S.A., Porto de Santos)
try:
    portos_vli = q("SELECT * FROM precos_portos_vli")
    portos_mercado = q("SELECT * FROM precos_portos_mercado")
    mercado["portos"] = {"vli": rec(portos_vli), "mercado": rec(portos_mercado)}
except Exception as e:
    mercado["portos"] = {"vli": [], "mercado": []}
    print("  ! módulo preços de portos indisponível (rode add_precos_portos.py):", e)

# custo logístico por microrregião (ferroviário x rodoviário, TCO) — base transcrita de
# vídeo do usuário, cobertura parcial (ver ressalva em add_custo_logistico.py)
try:
    custo_log = q("SELECT * FROM custo_logistico_microrregiao")
    custo_log["mes_lbl"] = custo_log["mes"]
    custo_evo = q("SELECT * FROM custo_logistico_evolucao")
    custo_logistico = {"linhas": rec(custo_log), "evolucao": rec(custo_evo)}
except Exception as e:
    custo_logistico = {"linhas": [], "evolucao": []}
    print("  ! módulo custo logístico indisponível (rode add_custo_logistico.py):", e)

# market share (Competitividade) — base transcrita de vídeo do usuário, cobertura parcial
# (Nacional + Go Leste + Go Sudoeste, de ~35-40 regiões no vídeo-fonte; ver add_market_share.py)
try:
    ms_vol = q("SELECT * FROM market_share_volume")
    ms_player = q("SELECT * FROM market_share_player")
    market_share = {
        "volume": rec(ms_vol),
        "player": rec(ms_player),
        "escopos": sorted(ms_vol["escopo"].unique().tolist()),
        "produtos": sorted(ms_vol["produto"].unique().tolist()),
    }
except Exception as e:
    market_share = {"volume": [], "player": [], "escopos": [], "produtos": []}
    print("  ! módulo market share indisponível (rode add_market_share.py):", e)

# market share por Porto — dimensão separada (Microrregião="Todos" + Porto=X no vídeo-fonte,
# não cruza com escopo de microrregião); só Soja transcrito por ora (ver add_market_share_porto.py)
try:
    msp_vol = q("SELECT * FROM market_share_volume_porto")
    msp_player = q("SELECT * FROM market_share_player_porto")
    market_share["volume_porto"] = rec(msp_vol)
    market_share["player_porto"] = rec(msp_player)
    market_share["portos"] = sorted(msp_vol["porto"].unique().tolist())
except Exception as e:
    market_share["volume_porto"] = []
    market_share["player_porto"] = []
    market_share["portos"] = []
    print("  ! módulo market share por porto indisponível (rode add_market_share_porto.py):", e)

# projetos por cliente (acessórias abertas + captura de clientes potenciais) — base transcrita
# da planilha interna de projetos, cobertura parcial (ver ressalva em add_projetos_clientes.py)
try:
    projeto_tarifas = q("SELECT * FROM projeto_fluxo_tarifas")
    projeto_abertura = q("SELECT * FROM projeto_acessorias_abertas")
    captura_tarifas = q("SELECT * FROM captura_clientes_potenciais_tarifas")
    captura_mes = q("SELECT * FROM captura_clientes_potenciais_mes")
    projetos_clientes = {
        "fluxos": rec(projeto_tarifas), "abertura": rec(projeto_abertura),
        "captura_tarifas": rec(captura_tarifas), "captura_mes": rec(captura_mes),
    }
    # histórico por cliente de projeto (Painel do Cliente): volume realizado por ano (2021+,
    # volume_hist) + preço ferroviário realizado (vli_pnl, só 2024+ — a base de P&L não cobre
    # anos anteriores; preço fica null onde não há dado, sem inventar).
    _cli_canon = sorted({str(c).replace(" (retroativo)", "").strip()
                         for c in projeto_tarifas["cliente"].unique()})
    _hist_v = q("""SELECT cliente, ano, origem, destino, mercadoria, SUM(realizado_ktu) vol_kt
                   FROM volume_hist WHERE ano>=2021
                   GROUP BY cliente, ano, origem, destino, mercadoria""")
    # rec_fr e vol_tu vêm em LINHAS separadas no P&L — filtrar no agregado (HAVING), nunca por linha
    _hist_p = q("""SELECT cliente, ano, origem, destino, mercadoria,
                          SUM(rec_fr) rec, SUM(vol_tu) vol
                   FROM vli_pnl WHERE modal='Ferrovia'
                   GROUP BY cliente, ano, origem, destino, mercadoria
                   HAVING SUM(rec_fr)>0 AND SUM(vol_tu)>=10000""")
    for _df in (_hist_v, _hist_p):
        _df["cli_up"] = _df["cliente"].astype(str).str.upper()
        # mercadoria base (tira sufixo tipo " - SPC"/" - HIPRO"/"- HIPRO" do P&L)
        _df["merc"] = _df["mercadoria"].astype(str).str.split("-").str[0].str.strip()
    _hist_rows = []
    for _cli in _cli_canon:
        _cu = _cli.upper().split()[0]   # primeiro token (SELECTA, CMOC, GERDAU...)
        _v = _hist_v[_hist_v["cli_up"].str.contains(_cu, regex=False)]
        _p = _hist_p[_hist_p["cli_up"].str.contains(_cu, regex=False)].copy()
        _vg = _v.groupby(["ano","origem","destino","merc"], as_index=False)["vol_kt"].sum()
        if len(_p):
            _pg = (_p.groupby(["ano","origem","destino","merc"], as_index=False)[["rec","vol"]].sum())
            _pg["preco"] = _pg["rec"]/_pg["vol"]
            _pg = _pg[["ano","origem","destino","merc","preco"]]
        else:
            _pg = pd.DataFrame(columns=["ano","origem","destino","merc","preco"])
        _m = _vg.merge(_pg, on=["ano","origem","destino","merc"], how="outer")
        _m["cliente"] = _cli
        _hist_rows.append(_m)
    _hist = pd.concat(_hist_rows, ignore_index=True) if _hist_rows else pd.DataFrame()
    if len(_hist):
        _hist = _hist[(_hist["vol_kt"].fillna(0) >= 1) | _hist["preco"].notna()]
        projetos_clientes["historico"] = rec(_hist.round(2))
    else:
        projetos_clientes["historico"] = []

    # histórico MENSAL por componente (2024+) — frete/manobra/DP/transbordo/acessória-total/total
    # realizados por R$/t, direto do P&L (rec_* / vol_tu). Base pra detectar inconsistência:
    # reajuste de acessória acima da inflação, salto abrupto mês a mês, reclassificação
    # manobra→frete (acessória some, frete pula, total ~igual). "Realizado" = panorama Real +
    # jan-jul/2026 (fechados); ago-dez/2026 é Tendência e fica de fora (não contamina o realizado).
    _hm = q("""SELECT cliente, origem, destino, mercadoria, ano, mes,
                      SUM(rec_fr) fr, SUM(rec_man) man, SUM(rec_dp) dp, SUM(rec_trbd) trbd,
                      SUM(rec_total) tot, SUM(vol_tu) vol
               FROM vli_pnl
               WHERE modal='Ferrovia'
                 AND (panorama LIKE '%Real%' OR (panorama LIKE '2026%' AND mes<=7))
               GROUP BY cliente, origem, destino, mercadoria, ano, mes
               HAVING SUM(vol_tu)>=1000 AND SUM(rec_total)>0""")
    _hm["cli_up"] = _hm["cliente"].astype(str).str.upper()
    _hm["merc"] = _hm["mercadoria"].astype(str).str.split("-").str[0].str.strip()
    _hm_rows = []
    for _cli in _cli_canon:
        _cu = _cli.upper().split()[0]
        _d = _hm[_hm["cli_up"].str.contains(_cu, regex=False)].copy()
        if not len(_d):
            continue
        _g = _d.groupby(["origem", "destino", "merc", "ano", "mes"], as_index=False)[
            ["fr", "man", "dp", "trbd", "tot", "vol"]].sum()
        _g = _g[_g["vol"] > 0]
        _g["frete"] = _g["fr"] / _g["vol"]
        _g["manobra"] = _g["man"] / _g["vol"]
        _g["dp"] = _g["dp"] / _g["vol"]
        _g["transbordo"] = _g["trbd"] / _g["vol"]
        _g["total"] = _g["tot"] / _g["vol"]
        _g["acess"] = _g["total"] - _g["frete"]            # tudo que não é frete = acessória
        _g["acess_out"] = _g["acess"] - _g["manobra"] - _g["dp"] - _g["transbordo"]
        _g["vol_kt"] = _g["vol"] / 1000.0
        _g["cliente"] = _cli
        _hm_rows.append(_g[["cliente", "origem", "destino", "merc", "ano", "mes",
                            "vol_kt", "frete", "manobra", "dp", "transbordo",
                            "acess_out", "acess", "total"]])
    _hmc = pd.concat(_hm_rows, ignore_index=True) if _hm_rows else pd.DataFrame()
    projetos_clientes["historico_mensal"] = rec(_hmc.round(2)) if len(_hmc) else []
    # histórico de reajustes (preços contratuais F-LINK, por fluxo × vigência) — hoje só GERDAU
    try:
        _rea = q("""SELECT item_ferroviario, contrato, origem, destino, produto,
                           vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
                           frete_rs_t, manobra_origem_rs_t, manobra_destino_rs_t
                    FROM gerdau_precos_contratuais ORDER BY item_ferroviario, vigencia_inicial DESC""")
        _rea["fluxo"] = _rea["produto"].astype(str) + " " + _rea["origem"].astype(str) + " " + _rea["destino"].astype(str)
        _rea["cliente"] = "GERDAU"
        projetos_clientes["reajustes"] = rec(_rea.round(2))
    except Exception:
        projetos_clientes["reajustes"] = []
    # ---- Teto regulatório multi-ferrovia (LD Celulose) ----
    # Parâmetros ANTT (tetos_parametros) por ferrovia×produto: parcela fixa + faixas [ate_km, rate]
    # (banda marginal/cumulativa; None = faixa superior sem limite). O JS computa o teto e simula.
    try:
        _tp = q("SELECT ferrovia, produto, fixo, banda_ate_km, rate FROM tetos_parametros")
        _params = {}
        for _, _r in _tp.iterrows():
            _d = _params.setdefault(str(_r["ferrovia"]), {}).setdefault(
                str(_r["produto"]), {"fixo": round(float(_r["fixo"]), 4), "bands": []})
            _d["bands"].append([None if pd.isna(_r["banda_ate_km"]) else float(_r["banda_ate_km"]),
                                round(float(_r["rate"]), 6)])
        for _fer in _params.values():
            for _pr in _fer.values():
                _pr["bands"].sort(key=lambda b: (b[0] is None, b[0] if b[0] is not None else 0))
        projetos_clientes["tetos_params"] = _params
        # segmentação curada da rota (planilha "LogConsult (tarifas por cliente).xlsx", aba LD):
        # a LD roda EDC→VAZ em duas ferrovias, celulose só tem teto próprio na EFVM (na FCA cai em
        # "Demais Produtos"). km e frete por trecho vêm da planilha (não estão abertos por ferrovia na base).
        projetos_clientes["teto_reg"] = {
            "LD CELULOSE": {
                "produto": "CELULOSE", "rota": "EDC→VAZ",
                "segmentos": [
                    {"ferrovia": "EFVM", "km": 635, "frete_seg": 132.37, "tem_teto_produto": True},
                    {"ferrovia": "FCA", "km": 704, "frete_seg": 157.59, "tem_teto_produto": False},
                ],
            }
        }
    except Exception:
        projetos_clientes["tetos_params"] = {}
        projetos_clientes["teto_reg"] = {}
except Exception as e:
    projetos_clientes = {"fluxos": [], "abertura": [], "captura_tarifas": [], "captura_mes": [],
                         "historico": [], "historico_mensal": [], "reajustes": [],
                         "tetos_params": {}, "teto_reg": {}}
    print("  ! módulo projetos por cliente indisponível (rode add_projetos_clientes.py):", e)

# ---------------------------------------------------------------------- CONTATOS
crm = q("""SELECT primeiro_nome, sobrenome, nome_da_conta AS conta, celular, email,
                  subsegmento_comercial AS subsegmento FROM crm_contatos""")
crm = crm[crm["conta"].notna()]
crm["conta"]=crm["conta"].map(canon)   # mesma lógica de grupo aplicada às contas do CRM
crm["nome"]=(crm["primeiro_nome"].fillna("")+" "+crm["sobrenome"].fillna("")).str.strip()
crm["celular"]=crm["celular"].map(fmt_tel)
crm["alvo"]=crm["conta"].map(is_alvo)
# contatos com telefone primeiro (o dado mais útil para o sócio)
crm["_tem_tel"]=crm["celular"].notna()
crm=crm.sort_values(["_tem_tel","nome"], ascending=[False,True])
contas = (crm.groupby("conta")
            .agg(n=("nome","size"), subsegmento=("subsegmento","first"),
                 alvo=("alvo","first"))
            .reset_index().sort_values(["alvo","n"], ascending=[False,False]))

# ------------------ SIMULADOR ANTT (parâmetros de teto por ferrovia × produto) ------------------
try:
    tp = q("SELECT ferrovia,produto,fixo,banda_ate_km,rate,vigencia,decisao FROM tetos_parametros")
    simulador = {}
    for fer, g in tp.groupby("ferrovia"):
        prods = {}
        for prod, gg in g.groupby("produto"):
            gg = gg.sort_values("banda_ate_km", na_position="last")
            bandas = [[None if pd.isna(r.banda_ate_km) else float(r.banda_ate_km), float(r.rate)]
                      for r in gg.itertuples()]
            r0 = gg.iloc[0]
            prods[prod] = {"fixo": round(float(r0.fixo), 4), "vigencia": str(r0.vigencia),
                           "decisao": str(r0.decisao), "bandas": bandas}
        simulador[fer] = prods
except Exception as e:
    simulador = {}; print("  ! simulador ANTT indisponível:", e)

# ===================== OPORTUNIDADES (motor de consultoria — a VITRINE) =====================
# A VLI é insumo: cada fluxo vira uma oportunidade de assessoria por status de teto.
# %teto regula o FRETE; "carga_vs_teto" = tarifa total (frete+acessórias) sobre o teto-frete
# = o custo real do cliente vs. o teto regulatório (ângulo de negociação).
op = q("""SELECT item,cliente,origem,destino,produto,
                 frete_trackage AS frete, demais_servicos AS acess, teto AS pct_teto, vigencia
          FROM tarifas_praticadas WHERE teto IS NOT NULL AND frete_trackage IS NOT NULL""")
op["cliente"] = op["cliente"].map(canon)
op["acess"] = op["acess"].fillna(0.0)
# corredor (enriquecimento via ipoa_teto, mesma chave natural usada no Comparativo)
_enrich_op = q("SELECT DISTINCT cliente, origem, destino, produto, corredor_vli FROM ipoa_teto")
_enrich_op["cliente"] = _enrich_op["cliente"].map(canon)
_enrich_op = _enrich_op.drop_duplicates(["cliente","origem","destino","produto"])
op = op.merge(_enrich_op, on=["cliente","origem","destino","produto"], how="left")
op["tarifa_total"] = op["frete"] + op["acess"]
op["teto_valor"]   = op["frete"] / op["pct_teto"]           # teto regula o frete
op["carga_vs_teto"]= op["tarifa_total"] / op["teto_valor"]  # custo total vs teto-frete
op["vigencia"] = op["vigencia"].astype(str).str.slice(0, 10)
op["alvo"] = op["cliente"].map(is_alvo)
def _status(r):
    v = r["carga_vs_teto"]   # custo total do cliente / teto-frete
    if v > 1.0:
        return ("acima", "Acima do teto", "Negociar redução — acima do teto")
    if v >= 0.90:
        return ("limite", "No limite", "Alavanca máxima — no teto")
    if v >= 0.75:
        return ("proximo", "Próximo do teto", "Monitorar / benchmark")
    return ("folga", "Folga", "Baixa prioridade")
_st = op.apply(_status, axis=1, result_type="expand")
op["status"], op["status_lbl"], op["acao"] = _st[0], _st[1], _st[2]
# sinal de prioridade (insumo VLI, não vitrine): margem que a VLI faz no cliente
_mm = {str(k).lower(): v for k, v in marg_cli.set_index("cliente")["margem_pct"].to_dict().items()}
def _margem(nome):
    n = str(nome).lower()
    for k, v in _mm.items():
        if k and k in n:
            return v
    return None
op["margem_vli"] = op["cliente"].map(_margem)
# op_resumo (status tally) alimenta só "kpis.op_acima" (campo interno, não exibido em
# nenhuma vitrine) — a antiga aba "Oportunidades" (op_lista) foi retirada do painel.
op_resumo = {s: int((op["status"] == s).sum()) for s in ["acima","limite","proximo","folga"]}

# ============ ANÁLISE INTELIGENTE DO TETO + IPOA (prioridade de negociação) ============
IPOA_REF = 0.248   # referência ANTT (Indicador de Participação das Operações Acessórias)
op["ipoa"] = np.where(op["frete"] > 0, op["acess"] / op["frete"], np.nan)
_rc = {str(k).lower(): v for k, v in marg_cli.set_index("cliente")["rec_mi"].to_dict().items()}
def _receita(nome):
    n = str(nome).lower()
    for k, v in _rc.items():
        if k and k in n: return v
    return None
op["receita_cli"] = op["cliente"].map(_receita)                       # receita VLI do cliente (R$ mi) — proxy de tamanho
op["potencial_acess_rs_t"] = np.maximum(0.0, op["acess"] - IPOA_REF * op["frete"]).round(1)  # acess a reduzir p/ ref ANTT
# REGRA: só entra na prioridade quem tem VOLUME REALIZADO nos últimos 12 meses da base
_v12 = q("""SELECT cliente, origem, destino, ano, mes, SUM(realizado_ktu) ktu
            FROM volume_hist WHERE realizado_ktu > 0 GROUP BY cliente, origem, destino, ano, mes""")
_v12["cliente"] = _v12["cliente"].map(canon)
_v12["per"] = _v12["ano"]*12 + _v12["mes"]
# última competência com volume realizado por (cliente×O/D) — pro filtro Ano/Mês do Teto
# olhar pra trás (histórico realizado), não pra frente (vigência do contrato).
_ultima = _v12.loc[_v12.groupby(["cliente","origem","destino"])["per"].idxmax(),
                    ["cliente","origem","destino","ano","mes"]]
_ultimamap = {(r.cliente, r.origem, r.destino): (int(r.ano), int(r.mes)) for r in _ultima.itertuples()}
_permax = int(_v12["per"].max())
VOL12_JANELA = f"{(_permax-11-1)//12}-{(_permax-11-1)%12+1:02d} a {(_permax-1)//12}-{(_permax-1)%12+1:02d}"
_v12 = _v12[_v12["per"] > _permax - 12].groupby(["cliente","origem","destino"], as_index=False)["ktu"].sum()
_v12map = {(r.cliente, r.origem, r.destino): r.ktu for r in _v12.itertuples()}
op["vol12_kt"] = op.apply(lambda r: _v12map.get((r["cliente"], r["origem"], r["destino"])), axis=1)
op["ativo12m"] = op["vol12_kt"].notna()
op["ano_realizado"] = op.apply(lambda r: _ultimamap.get((r["cliente"], r["origem"], r["destino"]), (None, None))[0], axis=1)
op["mes_realizado"] = op.apply(lambda r: _ultimamap.get((r["cliente"], r["origem"], r["destino"]), (None, None))[1], axis=1)
op["receita_ano"] = op["tarifa_total"] * op["vol12_kt"] * 1000.0   # kt -> t, últimos 12m realizados

# ---- Base completa de tarifas: gap/oportunidade vs. MENOR tarifa dos pares (jul/2026) ----
# mesma estrutura do gap/oportunidade vs. mediana (delta × volume), mas com dois diferenciais:
# (1) benchmark é o menor pagador, não a mediana; (2) volume é o REALIZADO 12m (vol12_kt),
# não o vmap/volume_hist anualizado que "oport_ano" (mediana) ainda usa — são bases de volume
# diferentes por desenho (mesma ressalva já registrada na correção da receita_potencial).
tf["vol12_kt"] = tf.apply(lambda r: _v12map.get((r["cliente"], r["origem"], r["destino"])), axis=1)
tf["gap_min"] = np.where(tf["n_cli_rota"]>=2, tf["total"]-tf["min_pares"], np.nan)
tf["gap_min_pct"] = np.where(tf["n_cli_rota"]>=2, (tf["total"]/tf["min_pares"]-1)*100, np.nan)
tf["oport_min_ano"] = np.where((tf["gap_min"]>0) & tf["vol12_kt"].notna(), tf["gap_min"]*tf["vol12_kt"]*1000.0, 0.0)
tarifas_full = rec(tf.round(2))

# insights de IA de isonomia: maiores desvios vs. MEDIANA ou vs. MENOR tarifa dos pares —
# usuário pediu poder alternar entre as duas visões no painel. Manda o universo completo de
# quem estoura >5% em QUALQUER um dos dois critérios (não só um top-N), pra um corte em
# qualquer percentual escolhido no navegador não ficar limitado a um top-N pré-cortado por
# um único critério.
_iso_base = tf[((tf["gap_pct"]>5) | (tf["gap_min_pct"]>5)) & (tf["n_cli_rota"]>=2)]
iso_ins = []
for r in _iso_base.itertuples():
    texto_min = (f"Paga R$ {r.total:,.2f}/t contra a menor tarifa de R$ {r.min_pares:,.2f} dos pares na mesma "
                 f"rota+produto ({r.gap_min_pct:+.0f}%). Melhor pagador: {r.melhor_pagador}. "
                 + (f"Equalizar à menor ≈ R$ {r.oport_min_ano:,.0f}/ano. " if r.oport_min_ano>0 else "")
                 + "Âncora: isonomia — Res. ANTT 3.694/2011 · Lei 10.233/2001.")
    iso_ins.append({
        "cliente": r.cliente, "produto": r.produto, "rota": f"{r.origem}→{r.destino}",
        "paga": round(r.total,2), "med": round(r.med_pares,2), "min": round(r.min_pares,2),
        "gap_pct": round(r.gap_pct,1), "gap_min_pct": round(r.gap_min_pct,1), "n_pares": int(r.n_cli_rota)-1,
        "melhor": r.melhor_pagador, "oport_ano": round(r.oport_ano,0), "oport_min_ano": round(r.oport_min_ano,0),
        "texto": (f"Paga R$ {r.total:,.2f}/t contra mediana de R$ {r.med_pares:,.2f} dos pares na mesma rota+produto "
                  f"({r.gap_pct:+.0f}%). Melhor pagador: {r.melhor_pagador} (R$ {r.min_pares:,.2f}). "
                  + (f"Equalizar à mediana ≈ R$ {r.oport_ano:,.0f}/ano. " if r.oport_ano>0 else "")
                  + "Âncora: isonomia — Res. ANTT 3.694/2011 · Lei 10.233/2001."),
        "texto_min": texto_min,
    })
# score 0-100: proximidade do teto (35%) + acessória acima da média do PRODUTO (55%, mesma
# lógica/agrupamento da "Fluxos por proximidade do teto" — o usuário achou essa mais coerente
# que o corredor+produto usado antes) + receita do PRÓPRIO FLUXO, não do cliente (10%)
_tn = (op["pct_teto"].clip(0, 1.5) / 1.5)
_acess_grp_mean = op.groupby("produto")["acess"].transform("mean")
_acess_excess = np.maximum(0.0, op["acess"] - _acess_grp_mean)
_an = _acess_excess / (_acess_excess.max() or 1)
_rn = (op["receita_ano"].fillna(0) / (op["receita_ano"].max() or 1))
op["score"] = (0.35*_tn + 0.55*_an + 0.10*_rn)
op["score"] = (op["score"] / (op["score"].max() or 1) * 100).round(0)
_opA = op[op["ativo12m"]]                                    # universo da prioridade: fluxos vivos

# ---- funde "Prioridade de negociação" na tabela única de Teto Tarifário (jul/2026) ----
# usuário pediu pra juntar as duas planilhas (Fluxos por proximidade do teto + Prioridade
# de negociação) numa só, com a lógica de ganho da primeira (média por PRODUTO, não
# corredor+produto). Aqui só entram os campos que só existiam na de negociação (teto_fluxos
# já tem seu próprio "ipoa" nativo, vindo de ipoa_teto — não precisa duplicar): vigência,
# volume 12m e o score — via chave natural (item não corresponde entre as bases).
_op_enrich = op[["cliente","origem","destino","produto","vigencia","vol12_kt","score",
                 "ano_realizado","mes_realizado"]].copy()
_op_enrich = _op_enrich.drop_duplicates(["cliente","origem","destino","produto"])
teto_fluxos = teto_fluxos.merge(_op_enrich, on=["cliente","origem","destino","produto"], how="left")
# acessórias abertas por fluxo (origem/destino/outras) — pedido do usuário: nas colunas
# Origem/Destino da tabela ele quer o VALOR da acessória daquele tipo pro fluxo, não a sigla
# da estação (isso já existe na "Rota"). Classifica cada serviço do hub (Acessórias) por nome:
# contém "ORIGEM" → acess_origem; contém "DESTINO" → acess_destino; senão → acess_outras
# (DIREITO DE PASSAGEM, BALDEAÇÃO, CARGA, DESCARGA, UTILIZAÇÃO DE PÁTIO etc.), soma por fluxo.
_dir = np.where(hub["servicos"].str.contains("ORIGEM"), "acess_origem",
        np.where(hub["servicos"].str.contains("DESTINO"), "acess_destino", "acess_outras"))
_acess_abertas = (hub.assign(_dir=_dir)
                     .groupby(["cliente", "origem", "destino", "produto", "_dir"])["tarifa"]
                     .sum().unstack("_dir", fill_value=0.0).reset_index())
for _c in ["acess_origem", "acess_destino", "acess_outras"]:
    if _c not in _acess_abertas.columns: _acess_abertas[_c] = 0.0
_acess_abertas = _acess_abertas.rename(columns={"acess_origem": "_ao", "acess_destino": "_ad", "acess_outras": "_au"})
teto_fluxos = teto_fluxos.merge(_acess_abertas, on=["cliente", "origem", "destino", "produto"], how="left")
# o hub (fonte do detalhamento por serviço) é uma base DIFERENTE de ipoa_teto (fonte da
# "acessorias" oficial) — a soma bruta das 3 partes não batia com o total (achado do
# usuário: R$75 oficial vs. R$783 de soma bruta). Corrigido: em vez de usar os valores
# brutos do hub, usamos só as PROPORÇÕES relativas entre origem/destino/outras encontradas
# lá, e distribuímos o total OFICIAL (acessorias) nessas proporções — garante
# acess_origem+acess_destino+acess_outras == acessorias sempre que há dado de composição.
_soma_bruta = teto_fluxos["_ao"] + teto_fluxos["_ad"] + teto_fluxos["_au"]
teto_fluxos["acess_origem"] = np.where(_soma_bruta > 0, teto_fluxos["_ao"] / _soma_bruta * teto_fluxos["acessorias"], np.nan)
teto_fluxos["acess_destino"] = np.where(_soma_bruta > 0, teto_fluxos["_ad"] / _soma_bruta * teto_fluxos["acessorias"], np.nan)
teto_fluxos["acess_outras"] = np.where(_soma_bruta > 0, teto_fluxos["_au"] / _soma_bruta * teto_fluxos["acessorias"], np.nan)
teto_fluxos = teto_fluxos.drop(columns=["_ao", "_ad", "_au"])
# acessória sugerida (jul/2026, a pedido do usuário) — dois níveis:
# 1) FAMÍLIA (mesmo produto × origem × destino): a menor acessória cobrada entre os OUTROS
#    clientes da mesma família — mesmo critério "vs. menor par" já usado no hub/Comparativo
#    (exclui o próprio cliente, senão ele "se benchmarkaria" contra si mesmo).
# 2) SEM FAMÍLIA (fluxo único, sem peer no mesmo produto×O×D): fallback de inteligência que
#    combina (a) referência regulatória IPOA — quanto seria a acessória se o IPOA do fluxo
#    fosse exatamente a régua ANTT (24,8%) — com (b) a média de acessórias do cluster mais
#    amplo "mesmo produto × mesmo corredor" (outros clientes do corredor, mesma mercadoria).
#    Combina as duas quando ambas existem (média simples); usa a que houver quando só uma
#    existe; fica sem sugestão (NaN) só quando nenhuma das duas é calculável.
# família carvão/coque/antracito em origem VTU (mesma constante/critério do bloco de
# isonomia de tarifa acima) — só amplia o peer-set do "menor par"/"mediana dos pares" de
# ACESSÓRIA (a tela é literalmente "comparativo de manobra"), nunca de volume.
_is_fam_vtu_tf = (teto_fluxos["origem"] == "VTU") & teto_fluxos["produto"].isin(_FAMILIA_CARVAO_COQUE_TARIFA)
teto_fluxos["_prod_grp_tarifa"] = np.where(
    _is_fam_vtu_tf,
    "CARVAO/COQUE/ANTRACITO (família VTU)",
    teto_fluxos["produto"],
)
# GERDAU/USIMINAS/ARCELORMITTAL/CIPLAN/IMI/VALE cada um escoa carvão/coque por um par VTU→X
# DIFERENTE (VIC, VBV, EPM, VOB...) — se o agrupamento de peer exigisse destino IGUAL, a
# família nunca juntaria clientes diferentes (cada um "sozinho" no seu próprio destino), o
# que é exatamente o oposto do pedido do usuário e o motivo de CARVAO MINERAL (destino VIC/
# VBV/VOB, sem nenhum outro cliente no mesmo destino) ficar sem peer mesmo com a família
# aplicada — só GERDAU/CIPLAN/IMI/VALE em EPM "por coincidência" comungavam destino e viam
# peer. Pra linhas família+VTU o agrupamento ignora destino (só _prod_grp_tarifa+origem);
# fora da família, mantém origem+destino exatos como sempre (mesmo critério de sempre p/
# produtos não amplificados).
teto_fluxos["_destino_grp_tarifa"] = np.where(_is_fam_vtu_tf, "(família VTU)", teto_fluxos["destino"])
def _familia_min_peer(gr):
    out = []
    for i, r in gr.iterrows():
        peers = gr.loc[gr["cliente"] != r["cliente"], "acessorias"]
        out.append(peers.min() if len(peers) else np.nan)
    return pd.Series(out, index=gr.index)
_fam_min = teto_fluxos.groupby(["_prod_grp_tarifa", "origem", "_destino_grp_tarifa"], group_keys=False).apply(_familia_min_peer)
# groupby(...).apply() concatena os resultados na ordem dos GRUPOS, não das linhas originais
# — o índice fica certo, mas a ORDEM das linhas não bate mais com teto_fluxos. reindex()
# realinha explicitamente antes de qualquer uso posicional (np.where etc.), senão o rótulo
# "fonte" sai trocado em relação ao valor de acess_sugerida (bug encontrado e corrigido aqui).
_fam_min = _fam_min.reindex(teto_fluxos.index)

# frete==0 (produtos 100% acessória, ex. combustíveis na FNS) tornaria o benchmark de IPOA
# sempre zero (IPOA_REF × 0) — sem sentido pra esse perfil de fluxo; nesses casos o
# fallback usa só o cluster do corredor.
_ipoa_bench = pd.Series(np.where(teto_fluxos["frete"] > 0, IPOA_REF * teto_fluxos["frete"], np.nan), index=teto_fluxos.index)
def _cluster_corredor_avg(gr):
    out = []
    for i, r in gr.iterrows():
        peers = gr.loc[gr["cliente"] != r["cliente"], "acessorias"]
        out.append(peers.mean() if len(peers) else np.nan)
    return pd.Series(out, index=gr.index)
_cluster_avg = teto_fluxos.groupby(["produto", "corredor"], group_keys=False).apply(_cluster_corredor_avg)
_cluster_avg = _cluster_avg.reindex(teto_fluxos.index)
_fallback = pd.concat([_ipoa_bench, _cluster_avg], axis=1).mean(axis=1, skipna=True)

teto_fluxos["acess_sugerida"] = _fam_min.fillna(_fallback).round(2)
teto_fluxos["acess_sugerida_fonte"] = np.where(_fam_min.notna(), "família (menor par)", "estimativa (IPOA + cluster do corredor)")
teto_fluxos["acess_delta"] = np.maximum(0.0, teto_fluxos["acessorias"] - teto_fluxos["acess_sugerida"])

# cenário MODERADO (jul/2026, pra Base Potenciais — otimista/moderado, mesmo par de cenários
# já usado no Comparativo/hub): mesma lógica de família, mas usando a MEDIANA dos pares em vez
# do menor — ponderado, não o "melhor caso". Sem família, cai no mesmo fallback (já é uma
# média/estimativa, não faz sentido ter um 2º fallback ainda mais brando).
def _familia_mediana_peer(gr):
    out = []
    for i, r in gr.iterrows():
        peers = gr.loc[gr["cliente"] != r["cliente"], "acessorias"]
        out.append(peers.median() if len(peers) else np.nan)
    return pd.Series(out, index=gr.index)
_fam_med = teto_fluxos.groupby(["_prod_grp_tarifa", "origem", "_destino_grp_tarifa"], group_keys=False).apply(_familia_mediana_peer)
_fam_med = _fam_med.reindex(teto_fluxos.index)
teto_fluxos["acess_sugerida_moderado"] = _fam_med.fillna(_fallback).round(2)
teto_fluxos["acess_delta_moderado"] = np.maximum(0.0, teto_fluxos["acessorias"] - teto_fluxos["acess_sugerida_moderado"])
# receita_potencial/receita_ano usam o volume REALIZADO nos últimos 12 meses (vol12_kt,
# em mil t → ×1000 pra tonelada), não o vmap/volume_hist anualizado — o usuário validou
# com a SELECTA: (115,57−35,10 acess.) × 275,41 kt × 1000 ≈ R$ 22,16 mi (bateu com o esperado).
# Fluxos sem match em vol12_kt (sem tarifas_praticadas correspondente) ficam sem esses campos.
teto_fluxos["receita_potencial"] = teto_fluxos["acess_delta"] * teto_fluxos["vol12_kt"] * 1000.0
teto_fluxos["receita_potencial_moderado"] = teto_fluxos["acess_delta_moderado"] * teto_fluxos["vol12_kt"] * 1000.0
teto_fluxos["receita_ano"] = teto_fluxos["total"] * teto_fluxos["vol12_kt"] * 1000.0
teto_fluxos["pct_potencial_receita"] = np.where(teto_fluxos["receita_ano"]>0,
    teto_fluxos["receita_potencial"]/teto_fluxos["receita_ano"]*100, np.nan)
# pontos do gráfico (eixos escolhíveis): só fluxos com volume nos últimos 12m, bolha = receita do FLUXO
_scatter_src = teto_fluxos[teto_fluxos["vol12_kt"].notna()].copy()
_scatter_src["ipoa_c"] = _scatter_src["ipoa"].clip(upper=1.5)
scatter = rec(_scatter_src.sort_values("receita_ano", ascending=False).head(260)[
    ["cliente","produto","pct_teto","ipoa_c","receita_ano","acess_delta",
     "receita_potencial","vol12_kt","score","alvo"]].round(3))
teto_cards = {"n_teto_alto": int((_opA["carga_vs_teto"] >= 0.90).sum()),
              "n_ipoa_estouro": int((_opA["ipoa"] > IPOA_REF).sum()),
              "potencial_medio": round(_opA.loc[_opA["potencial_acess_rs_t"] > 0, "potencial_acess_rs_t"].mean(), 1),
              "n_ativos": int(op["ativo12m"].sum()), "n_total": int(len(op)), "janela": VOL12_JANELA}

# ---- INSIGHTS DE IA: onde abordar cada cliente para renegociar (só fluxos ativos 12m) ----
_cli = (_opA.groupby("cliente")
          .agg(n_fluxos=("cliente","size"),
               n_quentes=("carga_vs_teto", lambda x: int((x >= 0.90).sum())),
               carga_max=("carga_vs_teto","max"),
               ipoa_med=("ipoa","mean"),
               pot_med=("potencial_acess_rs_t","mean"),
               receita=("receita_cli","first"),
               vence_min=("vigencia","min"),
               alvo=("alvo","first"),
               score_max=("score","max"))
          .reset_index())
_cli = _cli[_cli["n_quentes"] > 0].sort_values(["score_max","receita"], ascending=False)
def _insight(r):
    nome = str(r.cliente).title().replace(" S/A","").replace(" S.A.","").replace(" Ltda","").strip(" .")
    partes = []
    partes.append(f"{r.n_quentes} de {r.n_fluxos} fluxos com custo total ≥90% do teto-frete"
                  + (f" (pico {r.carga_max:.2f}×)" if r.carga_max and r.carga_max > 1 else ""))
    if pd.notna(r.ipoa_med) and r.ipoa_med > IPOA_REF:
        partes.append(f"IPOA médio {r.ipoa_med*100:.0f}% — {r.ipoa_med/IPOA_REF:.1f}× a referência ANTT")
    if pd.notna(r.pot_med) and r.pot_med > 0:
        partes.append(f"≈R$ {r.pot_med:.0f}/t de acessória acima da régua")
    venc = str(r.vence_min or "")
    if venc and venc <= "2026-12-31":
        partes.append(f"contrato mais antigo vence {venc[8:10]}/{venc[5:7]}/{venc[:4]}" if len(venc) == 10 else "")
    abordagem = ("pleito imediato: recuperação/redução — custo acima do teto com acessórias fora da régua"
                 if (r.carga_max or 0) > 1 and (r.ipoa_med or 0) > IPOA_REF else
                 "renegociação na janela contratual, ancorada no teto ANTT e no benchmark de pares")
    return {"cliente": str(r.cliente), "nome": nome, "alvo": bool(r.alvo),
            "receita": clean(r.receita), "score": float(r.score_max or 0),
            "evidencia": " · ".join(p for p in partes if p), "abordagem": abordagem}
teto_insights = [_insight(r) for r in _cli.head(8).itertuples()]

# IPOA por ferrovia e por fluxo (tabela ipoa_teto — tem a ferrovia de faturamento)
ip = q("SELECT cliente,origem,destino,produto,frete,acessorias,ferrovia_fatura,corredor_vli FROM ipoa_teto")
ip["cliente"] = ip["cliente"].map(canon)
for cc in ["frete","acessorias"]: ip[cc] = pd.to_numeric(ip[cc], errors="coerce")
ip = ip[(ip["frete"] > 0) & ip["acessorias"].notna()].copy()
ip["ipoa"] = ip["acessorias"] / ip["frete"]
ip["estouro"] = ip["ipoa"] > IPOA_REF
ip["alvo"] = ip["cliente"].map(is_alvo)
ipoa_fer = (ip.groupby("ferrovia_fatura")
              .agg(n=("ipoa","size"), ipoa_med=("ipoa","mean"), estouro=("estouro","sum")).reset_index())
ipoa_fer["ipoa_med"] = (ipoa_fer["ipoa_med"]*100).round(1)
ipoa_fer["pct_estouro"] = (ipoa_fer["estouro"]/ipoa_fer["n"]*100).round(0)
ipoa_fer = ipoa_fer.sort_values("ipoa_med", ascending=False)
ipoa_lista = ip.sort_values("ipoa", ascending=False)[
    ["cliente","origem","destino","produto","frete","acessorias","ipoa","ferrovia_fatura","estouro","alvo"]].head(500).round(3)
ipoa_data = {"ref": IPOA_REF, "ipoa_medio": round(ip["ipoa"].mean()*100, 1),
             "n_total": int(len(ip)), "n_estouro": int(ip["estouro"].sum()),
             "por_ferrovia": rec(ipoa_fer), "lista": rec(ipoa_lista)}

# ============================ VOLUME HISTÓRICO (2013–2026) ============================
# Embute o grão completo (ano×mês×corredor×cliente×mercadoria×O/D) com codificação
# compacta: colunas categóricas viram dicionário + array de códigos (BI client-side).
# 2013-2024 vem do volume_hist dedicado (BaseHistoricaFerrovia); 2025/2026 vem do
# vli_pnl novo (24_25_26.xlsx), que agora tem cobertura mensal completa — ao contrário
# da planilha de refresh anterior. VOL-TU/VOL-TKU vêm em linhas separadas por "estágio"
# (mesma lição de somar antes de dividir/usar) e em unidade bruta (tonelada, TKU) — o
# volume_hist já vem em mil-toneladas/milhão-TKU, então divide por 1000/1e6 pra alinhar.
volh_old = q("""SELECT ano, mes, corredor, cliente, mercadoria, origem, destino,
                   realizado_ktu, realizado_mtku
            FROM volume_hist WHERE realizado_ktu > 0 AND ano < 2025""")
volh_new = q("""SELECT ano, mes, corredor_vli AS corredor, cliente, mercadoria, origem, destino,
                       SUM(vol_tu)/1000.0 AS realizado_ktu, SUM(vol_tku)/1e6 AS realizado_mtku
                FROM vli_pnl WHERE modal='Ferrovia' AND ano IN (2025,2026)
                GROUP BY ano, mes, corredor_vli, cliente, mercadoria, origem, destino
                HAVING SUM(vol_tu) > 0""")
volh = pd.concat([volh_old, volh_new], ignore_index=True)
volh["cliente"] = volh["cliente"].map(canon)
# fluxos com vol_tu mas sem vol_tku correspondente (estágio sem essa métrica) dão NaN —
# NaN não é JSON válido e quebra o JSON.parse do payload inteiro no navegador
volh["realizado_ktu"] = volh["realizado_ktu"].fillna(0.0)
volh["realizado_mtku"] = volh["realizado_mtku"].fillna(0.0)
def _enc(s):
    ss = s.fillna("—").astype(str).str.strip()
    cats = sorted(ss.unique().tolist())
    idx = {c: i for i, c in enumerate(cats)}
    return cats, ss.map(idx).astype(int).tolist()
_vc, _vd = {}, {}
for col in ["corredor", "cliente", "mercadoria", "origem", "destino"]:
    _vc[col], _vd[col] = _enc(volh[col])
volume_data = {
    "cats": _vc,
    "rows": {"ano": volh["ano"].astype(int).tolist(),
             "mes": volh["mes"].astype(int).tolist(),
             **_vd,
             "ktu": volh["realizado_ktu"].round(1).tolist(),
             "mtku": volh["realizado_mtku"].round(1).tolist()},
    "n": int(len(volh)),
    "periodo": f"{int(volh['ano'].min())}–{int(volh['ano'].max())}",
}

# ============================ VOLUME HISTÓRICO DE PORTOS (2019–2026) ============================
# Mesma codificação compacta do volume ferroviário. Não tem TKU (sem distância entre
# porto/terminal) — só toneladas (KTU); mas traz orçamento/programa/demanda além do
# realizado, útil pra ver taxa de execução (realizado vs. demanda).
volp = q("""SELECT ano, mes, corredor_terminal, corredor_fluxo, porto, segmento_comercial_n1, produto,
                   orcamento_ktu, programa_ktu, demanda_ktu, realizado_ktu
            FROM volume_hist_portos""")
_vpc, _vpd = {}, {}
for col in ["corredor_terminal", "corredor_fluxo", "porto", "segmento_comercial_n1", "produto"]:
    _vpc[col], _vpd[col] = _enc(volp[col])
volume_portos_data = {
    "cats": _vpc,
    "rows": {"ano": volp["ano"].astype(int).tolist(),
             "mes": volp["mes"].astype(int).tolist(),
             **_vpd,
             "orcamento": volp["orcamento_ktu"].fillna(0).round(1).tolist(),
             "programa": volp["programa_ktu"].fillna(0).round(1).tolist(),
             "demanda": volp["demanda_ktu"].fillna(0).round(1).tolist(),
             "realizado": volp["realizado_ktu"].fillna(0).round(1).tolist()},
    "n": int(len(volp)),
    "periodo": f"{int(volp['ano'].min())}–{int(volp['ano'].max())}",
}

# ============================ MODELOS DE TREM (freq. por frota) ============================
frt = q("""SELECT corredor, mercadoria, frota, orig_flx, dest_flx,
                  jan,fev,mar,abr,mai,jun,jul,ago,\"set\",out,nov,dez
           FROM freq_trens""")
_meses = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
for m in _meses: frt[m] = pd.to_numeric(frt[m], errors="coerce")
frt["freq_media"] = frt[_meses].mean(axis=1).round(2)
frt["freq_pico"] = frt[_meses].max(axis=1).round(2)
frt["frota"] = frt["frota"].astype(str).str.replace(r"\.0$", "", regex=True)
trens_data = {
    "n_frotas": int(frt["frota"].nunique()),
    "n_fluxos": int(len(frt)),
    "lista": rec(frt[["corredor","mercadoria","frota","orig_flx","dest_flx",
                      "freq_media","freq_pico"] + _meses].round(2)),
}

# ============================ PREMISSA DE PLANEJAMENTO (book VLI, cenário 2026-Orçamento) ============================
# Corte de escopo: matrizes de volume por corredor/ativo (Ferrovia/Porto/Terminal). As ~150
# abas restantes do book (material rodante, ciclo de vagão, giro/TT etc., por corredor
# específico) ficam fora deste corte — ver relatório de escopo enviado ao usuário.
_pf_tu = q("SELECT * FROM premissa_ferrovia_vol_tu")
_pf_tku = q("SELECT * FROM premissa_ferrovia_vol_tku")
_pp_tu = q("SELECT * FROM premissa_porto_vol_tu")
_pt_tu = q("SELECT * FROM premissa_terminal_vol_tu")
_pvc = q("SELECT * FROM premissa_vol_consolidado")
premissa_planejamento = {
    "ferrovia": {
        "vol_tu": rec(_pf_tu),
        "vol_tku": rec(_pf_tku),
        "vol_consolidado": rec(_pvc[_pvc["grupo"] == "Ferrovia"].drop(columns=["grupo"])),
        "corredores": sorted(_pf_tu["corredor"].dropna().unique().tolist()),
    },
    "portos": {
        "vol_tu": rec(_pp_tu),
        "terminal_vol_tu": rec(_pt_tu),
        "vol_consolidado": rec(_pvc[_pvc["grupo"] != "Ferrovia"].rename(columns={"grupo": "tipo"})),
        "corredores": sorted(_pp_tu["corredor"].dropna().unique().tolist()),
    },
    "trens": trens_data,
}

# ------------------------------------------------------------------------- KPIs
tot = q(f"SELECT SUM(rec_total) r, SUM(ind_mrg) m FROM vli_pnl WHERE {P24}").iloc[0]
kpis = {
    "op_acima": op_resumo["acima"],
    "teto_95": int((op["pct_teto"] >= 0.95).sum()),
    "contr_vencidos": contr_vencidos,
    "pct_acess_medio": round(acess_cliente["pct_acess"].mean(),0),
    "n_contatos": int(len(crm)),
    "n_contas": int(crm["conta"].nunique()),
    "n_fluxos_teto": int(len(teto)),
    # insumo interno (não exibido como vitrine):
    "vli_receita_bi": round(tot.r/1e9,2),
    "vli_margem_pct": round(tot.m/tot.r*100,0),
}

# --------------------------------------------------- HORIZONTES + PIPELINE (Radar)
horizontes, portfolio, pipe_kpis, radar_base = {}, [], {}, {}
if RADAR_JSON.exists():
    rd = json.loads(RADAR_JSON.read_text(encoding="utf-8"))
    horizontes = rd.get("horizontes", {})
    portfolio = [p for p in rd.get("portfolio", []) if p.get("modelado")]
    pipe_kpis = {"pipeline_otimista": rd["kpis"].get("pipeline_otimista"),
                 "pipeline_moderado": rd["kpis"].get("pipeline_moderado"),
                 "n_projetos": rd["kpis"].get("n_projetos")}
    # Radar analítico (do antigo dashboard, agora dentro do painel): 4 estados da base
    radar_base = {"por_estado": rd["kpis"].get("por_estado", {}),
                  "n_fluxos": rd["kpis"].get("n_fluxos")}
    kpis = {**pipe_kpis, **kpis}
else:
    print("  ! radar_data.json ausente — rode build_radar.py p/ as abas Horizontes/Pipeline")

# ---- universo de clientes (para o gerenciador de Alvos no painel) ----
_universo = set()
for _s in [op["cliente"], tf["cliente"], marg_cli["cliente"], crm["conta"], hub["cliente"]]:
    _universo |= set(_s.dropna().unique().tolist())
todos_clientes = sorted(_universo)

# ---- contagem de dados brutos por cliente (p/ empty-state honesto do Painel do Cliente
# quando o cliente selecionado no dropdown "Todos os clientes" NÃO tem tratamento curado
# em projeto_fluxo_tarifas/PJF — pedido do usuário, 28/jul/2026) ----
_tp_raw = q("SELECT cliente FROM tarifas_praticadas WHERE cliente IS NOT NULL")
_tp_raw["_c"] = _tp_raw["cliente"].map(canon)
_tp_counts = _tp_raw.groupby("_c").size().to_dict()
_vh_raw = q("SELECT cliente, ano, mes FROM volume_hist WHERE cliente IS NOT NULL")
_vh_raw["_c"] = _vh_raw["cliente"].map(canon)
_vh_meses = _vh_raw.groupby("_c").apply(lambda g: g[["ano","mes"]].drop_duplicates().shape[0], include_groups=False).to_dict()
raw_counts = {c: {"tarifas": int(_tp_counts.get(c, 0)), "vol_meses": int(_vh_meses.get(c, 0))}
              for c in set(list(_tp_counts.keys()) + list(_vh_meses.keys()))}

# sem pré-seleção do sistema — o usuário pediu que o "alvo" reflita só quem ELE marcar
# manualmente no painel (gerenciador de Alvos), não a lista ALVOS/is_alvo() abaixo (que
# ainda alimenta o campo "alvo" bruto de cada tabela, mas é sobrescrita no carregamento do
# painel por applyAlvoOverrides() com base nisto aqui — ver painel_template.html).
alvos_default = []

# ================= ROTA -> FERROVIA (pra achar a tarifa oficial de manobra por fluxo) =================
# acessorias_mercado (ingerida 10/jul/2026, tabelas públicas VLI/FCA-FNS + Vale/EFVM-EFC +
# RUMO + MRS, por Res. ANTT 6.031/2023 art. 16) já vem exposta em D.acess_mercado.tabela —
# falta só mapear (origem,destino) -> malha pra o front achar a linha certa por fluxo. Pedido
# do usuário (20/jul/2026): trazer essas tarifas oficiais pros racionais do Painel do Cliente
# (comparar o que cada cliente paga hoje contra o teto que a própria operadora publicou).
_rf = q("SELECT DISTINCT origem, destino, ferrovia_fatura FROM ipoa_teto WHERE ferrovia_fatura IS NOT NULL")
rota_ferrovia = [[r.origem, r.destino, r.ferrovia_fatura] for r in _rf.itertuples()]

# ================= IPOA MÉDIO REAL POR FERROVIA (não é o gatilho ANTT — é a média observada) ==
# Achado do usuário (21/jul/2026), auditoria de especialista: "IPOA só vale por ferrovia,
# concessionária, não por cliente" — o sistema usava um único IPOA_REF=24,8% pra todo mundo
# (esse número É correto como GATILHO REGULATÓRIO da ANTT, Res. 6.031/2023 art.15 — não muda),
# mas pra efeito de BENCHMARK/PAR (quanto a acessória de um cliente destoa do "normal" da malha
# dele), o certo é comparar contra a média REAL de cada ferrovia, que é bem mais alta que 24,8%
# em toda malha (FCA/FNS/EFVM/EFC calculadas abaixo, ~37-48%) — usar 24,8% como "par" nessas
# comparações super-inflava o "excesso" aparente. Fonte: `ipoa_geral` (base bruta item a item,
# frete+acessórias por ferrovia_fatura — mesma string usada em `rota_ferrovia`/`ipoa_teto`).
_ipg = q("""SELECT ferrovia_fatura,
                   SUM(CASE WHEN categoria='FRETE' THEN valor_servico ELSE 0 END) frete_tot,
                   SUM(CASE WHEN categoria='ACESSÓRIAS' THEN valor_servico ELSE 0 END) acess_tot
            FROM ipoa_geral WHERE ferrovia_fatura IS NOT NULL GROUP BY ferrovia_fatura""")
ipoa_ferrovia = {r.ferrovia_fatura: round(r.acess_tot / r.frete_tot, 4)
                 for r in _ipg.itertuples() if r.frete_tot}

# ================= PREMISSAS OPERACIONAIS DE MANOBRA — Grãos e Fertilizantes =================
# Pedido do usuário (21/jul/2026): horário de funcionamento dos terminais + tempo de carga e
# descarga, transcritos de fotos da planilha "Premissas Grãos e Fertilizantes.xlsx" (aba
# "Premissas Gerais") via add_premissas_manobra_graos_ferti.py — usar como REFERÊNCIA na
# simulação de custo da manobra (aba "Peso médio" ainda não recebida, fica pendente).
try:
    _pm = q("SELECT * FROM premissas_manobra_graos_ferti")
    premissas_manobra_graos = _pm.to_dict("records") if len(_pm) else []
except Exception:
    premissas_manobra_graos = []

# ================= BASE POTENCIAIS VLI — visão consolidada por cliente (1ª aba do painel) =================
data = {
  "meta": {"gerado_em": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "aviso":"CONFIDENCIAL — inclui P&L VLI e dados pessoais de CRM. Uso interno.",
           "todos_clientes": todos_clientes, "alvos_default": alvos_default,
           "raw_counts": raw_counts},
  "kpis": kpis,
  "horizontes": horizontes,
  "portfolio": portfolio,
  "radar_base": radar_base,
  "simulador": simulador,
  "regulatorio": REGULATORIO,
  "volume": volume_data,
  "volume_portos": volume_portos_data,
  "trens": trens_data,
  "premissa_planejamento": premissa_planejamento,
  "acess_hub": acess_hub,
  "acess_mercado": acess_mercado,
  "acessorias": {"por_servico": rec(por_servico),
                 "por_cliente": rec(acess_cliente.head(60))},
  "teto": {"fluxos": rec(teto_fluxos[["item","cliente","origem","destino","produto","corredor",
                 "frete","teto","pct_teto","acessorias","acess_sugerida","acess_sugerida_fonte","acess_delta",
                 "acess_sugerida_moderado","acess_delta_moderado",
                 "acess_origem","acess_destino","acess_outras",
                 "receita_potencial","receita_potencial_moderado","receita_ano","pct_potencial_receita",
                 "ipoa","vigencia","ano_realizado","mes_realizado","vol12_kt","score","alvo"]].round(2)),
           "cards": teto_cards, "scatter": scatter,
           "insights": teto_insights, "ipoa_ref": IPOA_REF},
  "ipoa": ipoa_data,
  "comparativo": {"tarifas": tarifas_full, "insights": iso_ins, "kpis": comp_kpis,
                  "sazonal": {"fluxos": sazonal_full, "kpis": saz_kpis}},
  "margem": {"por_cliente": rec(marg_cli[["cliente","rec_mi","margem_pct","pct_acess","alvo",
                                           "tarifa_25","tarifa_26","var_tarifa_pct"]]),
             "por_corredor": rec(marg_cor[["corredor_vli","rec_mi","margem_pct"]]),
             "panoramas": rec(panor[["panorama","rec_bi","margem_pct","tarifa_media"]])},
  "contatos": {"por_conta": rec(contas),
               "lista": rec(crm[["nome","conta","subsegmento","email","celular","alvo"]])},
  "contratos": {"vencidos": contr_vencidos, "venc_2026": contr_venc_2026,
                "hoje": str(_hoje.date()), "lista": rec(contr_lista)},
  "mercado": mercado,
  "custo_logistico": custo_logistico,
  "market_share": market_share,
  "projetos_clientes": projetos_clientes,
  "rota_ferrovia": rota_ferrovia,
  "ipoa_ferrovia": ipoa_ferrovia,
  "premissas_manobra_graos": premissas_manobra_graos,
}

# sem mascara de codinome — nome real da concessionária (VLI) exibido diretamente
payload = json.dumps(data, ensure_ascii=False).replace("</","<\\/")
html = TEMPLATE.read_text(encoding="utf-8").replace("__PAINEL_DATA__", payload)
OUT.write_text(html, encoding="utf-8")
con.close()
print(f"OK -> {OUT.name}")
print(f"  acessorias: {len(acess_cliente)} clientes | teto: {len(teto)} fluxos | "
      f"tarifas full: {len(tf)} | margem: {len(marg_cli)} clientes | "
      f"contatos: {len(crm)} em {crm['conta'].nunique()} contas")
