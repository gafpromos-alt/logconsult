# -*- coding: utf-8 -*-
"""
LogConsult OS: alavancas regulatórias contra a VLI (nov/2026).
CONFIDENCIAL, USO RESTRITO AOS SÓCIOS.

Pedido do sócio (23/nov/2026): "busque mais alavancas de valor para consultoria junto aos
clientes, ou seja, inconsistências da VLI perante regulações atuais" e depois "pode implantar
tudo". Este script calcula as 30 alavancas daquela análise e grava três tabelas, lidas pelo
painel (aba Alavancas Regulatórias e bloco no Painel do Cliente):

  alavanca_catalogo  uma linha por alavanca: grupo, título, norma, fonte, tipo, evidência, uso
  alavanca_linha     linhas de item da Ficha de Fluxo 2026 com R$/t acima da referência. O R$/ano
                     é calculado NO PAINEL com a mesma função de volume do Painel do Cliente;
                     para grãos e farelo vai a série mensal do excesso (coluna `serie`) e o painel
                     soma mês a mês (decisão do sócio de 19/nov/2026)
  alavanca_cliente   valores por cliente que já vêm em R$ (P&L VLI, orçamento) ou contagens

Alavancas cujo número já existe em outra aba (IPOA e mediana dos pares da Ficha, porto,
contratos vencidos) NÃO são recalculadas aqui: o painel lê o número daquela aba (um número,
uma função). Valores não se somam entre alavancas: várias medem o mesmo dinheiro por ângulos
diferentes.

Normas: Res. ANTT 6.031/2023, Res. ANTT 5.943/2021, Decreto 1.832/1996 (RTF), Lei 10.233/2001
art. 25, Código Civil. Nunca citar a Res. 3.695/2011 (revogada) nem o art. 35 da Lei 10.233.
Texto sem travessão nem meia-risca (regra do sócio, 19/nov/2026).

Roda dentro de atualizar_tudo.py, depois de add_projetos_clientes.py e antes de build_painel.py.
"""
import json
import pathlib
import re
import sqlite3
import sys
import unicodedata
import warnings

import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from canon import canon  # noqa: E402

con = sqlite3.connect(BASE / "logconsult.db")
q = lambda s: pd.read_sql_query(s, con)

IPOA_REF = 0.248
GRAO = {"SOJA", "MILHO", "FARELO DE SOJA", "FARELO DE MILHO"}
MANOBRAS = ["MANOBRA ORIGEM", "MANOBRA DESTINO"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
na = lambda s: unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
br = lambda v, n=2: f"{v:,.{n}f}".replace(",", "X").replace(".", ",").replace("X", ".")
ni = lambda v: f"{int(v):,}".replace(",", ".")
mi = lambda v: br(v / 1e6, 1)
pct = lambda v, n=0: br(v * 100, n) + "%"

# ------------------------------------------------------------------ insumos da Ficha 2026
REF = q("SELECT * FROM ficha_fluxo_ref WHERE status='atual'")
MES = int(REF["mes_ref"].max())
LBL_MES = f"{MESES[MES - 1]}/2026"
ITENS = set(REF["item"])
SV = q("""SELECT item, cliente, origem, destino, produto, servico, categoria, ferrovia, mes, valor
          FROM ficha_fluxo_servico_mes WHERE programado=0""")
SV = SV[SV["item"].isin(ITENS)].copy()
IM = q("SELECT item, mes, frete, dp, acess, total FROM ficha_fluxo_item_mes WHERE programado=0 AND frete>0")
IM = IM[IM["item"].isin(ITENS)]
MESES_ITEM = {int(k): sorted(int(x) for x in set(v)) for k, v in IM.groupby("item")["mes"]}
TOT_MES = {(int(i), int(m)): float(t) for i, m, t in zip(IM["item"], IM["mes"], IM["total"])}
INFO = REF.set_index("item")[["cliente", "origem", "destino", "produto"]].to_dict("index")
MREF = {int(k): int(v) for k, v in zip(REF["item"], REF["mes_ref"])}
# mês de referência é POR ITEM (181 itens têm preço atual em outubro, não em novembro)
SVM = SV[SV["mes"] == SV["item"].map(MREF)]
SERV_LBL = {"BALDEACAO": "baldeação", "DEPRECIACACAO DE VAGAO": "depreciação de vagão",
            "TRANSBORDO DESTINO": "transbordo de destino", "TRANSBORDO ORIGEM": "transbordo de origem",
            "MANOBRA ORIGEM": "manobra de origem", "MANOBRA DESTINO": "manobra de destino", "CARGA": "carga",
            "DESCARGA": "descarga", "MANOBRA CONEXAO CHEIO": "manobra de conexão com vagão cheio",
            "UTILIZACAO DE PATIO": "utilização de pátio", "UTILIZACAO DE MURO": "utilização de muro",
            "LIMPEZA DE VAGAO": "limpeza de vagão", "OUTROS SERVICOS": "outros serviços"}
slbl = lambda s: SERV_LBL.get(s, str(s).lower())

COLS = ["item", "servico", "ferrovia", "cobrado", "referencia", "excesso", "detalhe"]
COLS_OUT = COLS + ["serie", "no_mes_ref"]


def aplica(regra, so_ref=False):
    """Aplica `regra(d)` mês a mês na ficha. Devolve as linhas: mês de referência DO ITEM para
    todos os produtos; para grãos e farelo, toda linha com excesso em algum mês do ano, com a
    série mensal do excesso nos meses em que o item tem preço (0 nos meses sem excesso).
    `no_mes_ref` = 1 quando a linha tem excesso no mês de referência do item (base das contagens
    dos textos de evidência)."""
    if so_ref:
        r = regra(SVM)
        if r is None or not len(r):
            return pd.DataFrame(columns=COLS_OUT)
        return r[COLS].assign(serie=None, no_mes_ref=1)
    por_mes = []
    for m in range(1, MES + 1):
        d = SV[SV["mes"] == m]
        if len(d):
            r = regra(d)
            if r is not None and len(r):
                por_mes.append(r[COLS].assign(mes=m))
    if not por_mes:
        return pd.DataFrame(columns=COLS_OUT)
    allm = pd.concat(por_mes, ignore_index=True)
    allm["grao"] = allm["item"].map(lambda i: INFO[i]["produto"] in GRAO)
    allm["eh_ref"] = allm["mes"] == allm["item"].map(MREF)
    ref = allm[allm["eh_ref"]]
    fora = ref[~ref["grao"] & (ref["excesso"] > 0.005)][COLS].assign(serie=None, no_mes_ref=1)
    g = allm[allm["grao"]]
    chaves = g[g["excesso"] > 0.005][["item", "servico", "ferrovia"]].drop_duplicates()
    linhas = []
    for (it, sv, fe), h in g.groupby(["item", "servico", "ferrovia"]):
        if not ((chaves["item"] == it) & (chaves["servico"] == sv) & (chaves["ferrovia"] == fe)).any():
            continue
        h = h.set_index("mes")
        serie = [[m, round(float(h.at[m, "excesso"]), 4) if m in h.index else 0.0] for m in MESES_ITEM.get(int(it), [])]
        mr = MREF[int(it)]
        base = h.loc[mr] if mr in h.index else h.loc[h.index.max()]
        linhas.append({**{c: base[c] for c in COLS}, "item": it, "servico": sv, "ferrovia": fe,
                       "serie": json.dumps(serie), "no_mes_ref": int(mr in h.index and h.at[mr, "excesso"] > 0.005)})
    return pd.concat([fora, pd.DataFrame(linhas, columns=COLS_OUT)], ignore_index=True)


LINHAS, CLIENTES, CATALOGO = [], [], []


def guarda_linhas(aid, df):
    for r in df.itertuples(index=False):
        inf = INFO[int(r.item)]
        LINHAS.append({"alav": aid, "item": int(r.item), "cliente": inf["cliente"], "origem": inf["origem"],
                       "destino": inf["destino"], "produto": inf["produto"], "servico": r.servico,
                       "ferrovia": r.ferrovia, "cobrado": round(float(r.cobrado), 4),
                       "referencia": None if r.referencia is None or pd.isna(r.referencia) else round(float(r.referencia), 4),
                       "excesso": round(float(r.excesso), 4), "detalhe": r.detalhe, "serie": r.serie,
                       "no_mes_ref": int(r.no_mes_ref)})


def guarda_cliente(aid, cli, valor=None, n=None, detalhe=""):
    CLIENTES.append({"alav": aid, "cliente": cli, "valor": None if valor is None else round(float(valor), 2),
                     "n": None if n is None else int(n), "detalhe": detalhe})


def cat(aid, grupo, titulo, norma, fonte, tipo, medida, evidencia, uso, tabela=None):
    CATALOGO.append({"id": aid, "grupo": grupo, "titulo": titulo, "norma": norma, "fonte": fonte, "tipo": tipo,
                     "medida": medida, "evidencia": evidencia, "uso": uso,
                     "tabela": json.dumps(tabela, ensure_ascii=False) if tabela else None})


GRUPOS = {"A": "Descumprimento direto da Res. ANTT 6.031/2023",
          "B": "Como a acessória é formada",
          "C": "Isonomia entre clientes",
          "D": "Direito de passagem e teto",
          "E": "Outras cobranças",
          "F": "Antecipação e negociação"}
F_FICHA = f"Ficha de Fluxo 2026 (VLI), {LBL_MES}"
F_PUB = "Tabela publicada VLI e Vale (coleta 10/jul/2026) e Ficha de Fluxo 2026"
F_PNL = "P&L VLI realizado (uso interno, não vai ao cliente)"

# ------------------------------------------------------------------ tabela publicada (art. 16)
AM = q("SELECT ferrovia op, malha, mercadoria, servico, valor_min mn, valor_medio md, valor_max mx FROM acessorias_mercado")
AM["m"] = AM["mercadoria"].map(na)
AM["s"] = AM["servico"].map(na)
MALHA = {"FCA": ("VLI", "FCA"), "FNS": ("VLI", "FNS"), "EFVM": ("VALE", "EFVM"), "EFC": ("VALE", "EFC")}


def _cands(prod):
    p = na(prod)
    c = []
    if p in ("SOJA", "MILHO"):
        c += [p, "GRAOS E FARELOS"]
    if p.startswith("FARELO"):
        c += ["FARELO DE SOJA" if "SOJA" in p else "", "GRAOS E FARELOS"]
    if p == "FERTILIZANTES":
        c += ["ADUBOS E FERTILIZANTES"]
    if p == "ENXOFRE":
        c += ["ENXOFRE", "ADUBOS E FERTILIZANTES"]
    if p.startswith("ROCHA"):
        c += ["ADUBOS E FERTILIZANTES"]
    if p == "FERRO GUSA":
        c += ["FERRO GUSA"]
    if p in ("PRO SIDERURGICO", "FIO MAQUINA"):
        c += ["PRODUTOS SIDERURGICOS"]
    if p == "MINERIO FERRO":
        c += ["MINERIO DE FERRO"]
    if p.startswith("COQUE"):
        c += ["COQUE"]
    if p == "CARVAO MINERAL":
        c += ["CARVAO MINERAL"]
    if p.startswith("CALCARIO"):
        c += ["CALCARIO BRITADO", "CALCARIO SIDERURGICO"]
    if p == "CELULOSE":
        c += ["CELULOSE"]
    if p == "TORETES":
        c += ["TORAS DE MADEIRA"]
    return [x for x in c if x] + ["DEMAIS PRODUTOS", "OUTROS"]


def _serv(s):
    s = na(s)
    if s.startswith("MANOBRA"):
        return ["MANOBRA"]
    if s.startswith("TRANSBORDO") or s.startswith("BALDEAC"):
        return ["TRANSBORDO", "BALDEACAO"]
    if s in ("CARGA", "DESCARGA"):
        return ["CARGA E DESCARGA", "CARREGAMENTO"]
    return []


_PUB = {}


def publicado(ferr, prod, servico):
    """(máximo da categoria específica, rótulo da categoria, situação)."""
    k = (ferr, prod, servico)
    if k in _PUB:
        return _PUB[k]
    out = (None, None, "ferrovia sem tabela")
    if ferr in MALHA:
        op, malha = MALHA[ferr]
        ss = _serv(servico)
        if not ss:
            out = (None, None, "serviço sem indicador publicado")
        else:
            a = AM[(AM["op"] == op) & (AM["malha"] == malha) & (AM["s"].isin(ss)) & (AM["mx"].notna())]
            cs = _cands(prod)
            esp = a[a["m"].isin(cs[:-2])]
            gen = a[a["m"].isin(cs[-2:])]
            if len(esp):
                r = esp.sort_values("mx").iloc[-1]
                out = (float(r["mx"]), f"{r['mercadoria']} ({r['servico']}, {malha})", "específica")
            elif len(gen):
                out = (None, None, "só genérica")
            else:
                out = (None, None, "sem valor publicado para o produto")
    _PUB[k] = out
    return out


ACESS = lambda d: d[~d["categoria"].isin(["frete", "dp"]) & (d["valor"] > 0)]


def r_acima_max(d):
    a = ACESS(d).copy()
    pb = [publicado(f, p, s) for f, p, s in zip(a["ferrovia"], a["produto"], a["servico"])]
    a["referencia"] = [x[0] for x in pb]
    a["cat"] = [x[1] for x in pb]
    a = a[a["referencia"].notna() & (a["valor"] > a["referencia"] + 0.005)]
    a["cobrado"] = a["valor"]
    a["excesso"] = a["valor"] - a["referencia"]
    a["detalhe"] = "máximo publicado R$ " + a["referencia"].map(br) + "/t, " + a["cat"]
    return a


def r_sem_indicador(d):
    a = ACESS(d).copy()
    pb = [publicado(f, p, s) for f, p, s in zip(a["ferrovia"], a["produto"], a["servico"])]
    a["sit"] = [x[2] for x in pb]
    a = a[a["sit"].isin(["serviço sem indicador publicado", "sem valor publicado para o produto"])]
    a["cobrado"] = a["valor"]
    a["referencia"] = None
    a["excesso"] = a["valor"]
    a["detalhe"] = a["sit"]
    return a


L1 = aplica(r_acima_max)
L2 = aplica(r_sem_indicador)
guarda_linhas(1, L1)
guarda_linhas(2, L2)
_l1m = L1[L1["serie"].isna()]
cat(1, "A", "Acessória acima do máximo publicado",
    "Res. ANTT 6.031/2023, art. 16 §3º (cobrança acima do máximo publicado; multa)", F_PUB, "linhas", "rs_ano",
    f"{L1[L1.no_mes_ref == 1]['item'].nunique()} itens de {L1[L1.no_mes_ref == 1]['item'].map(lambda i: INFO[i]['cliente']).nunique()} clientes cobrados acima do "
    f"máximo que a própria ferrovia publicou para o produto e o serviço. "
    + ("Exemplos: " + "; ".join(f"{INFO[r.item]['cliente']} {slbl(r.servico)} {INFO[r.item]['origem']}→{INFO[r.item]['destino']} "
                               f"R$ {br(r.cobrado)} contra R$ {br(r.referencia)}"
                               for r in L1.sort_values("excesso", ascending=False).drop_duplicates("servico").head(3).itertuples()) + "."
       if len(L1) else ""),
    "Infração objetiva, valor pequeno: serve de porta de entrada e de prova de que a tabela não é respeitada. "
    "Conferir no F-LINK do cliente o valor cobrado no mês e registrar a tabela publicada vigente (ata notarial).")
cat(2, "A", "Serviço cobrado sem indicador publicado",
    "Res. ANTT 6.031/2023, art. 16 §2º (publicar indicadores de preço de cada operação acessória)", F_PUB, "linhas", "rs_ano",
    "Serviços faturados sem valor publicado para o produto ou sem indicador nenhum na tabela: "
    + "; ".join(f"{slbl(s)} na {f} ({n} itens)" for (s, f), n in
                L2[L2.no_mes_ref == 1].groupby(["servico", "ferrovia"])["item"].nunique().sort_values(ascending=False).head(5).items())
    + ". A estadia de vagões também não consta da tabela publicada (alavanca 23).",
    "Pedir à VLI o indicador publicado de cada serviço faturado. Sem indicador, a cobrança fica sem base "
    "para o teste de preço abusivo e pode ser contestada.")

# ------------------------------------------------------------------ 3. publicado x praticado
_m = SVM[SVM["servico"].isin(MANOBRAS) & (SVM["valor"] >= 0.5)]
_tab3 = []
for malha, merc, prods in (("FCA", "SOJA", ["SOJA"]), ("FCA", "MILHO", ["MILHO"]),
                           ("FCA", "FARELO DE SOJA", ["FARELO DE SOJA"]),
                           ("FNS", "GRÃOS E FARELOS", ["SOJA", "MILHO", "FARELO DE SOJA", "FARELO DE MILHO"]),
                           ("FCA", "ADUBOS E FERTILIZANTES", ["FERTILIZANTES"]),
                           ("FCA", "PRODUTOS SIDERÚRGICOS", ["PRO SIDERURGICO", "FIO MAQUINA"]),
                           ("FCA", "FERRO GUSA", ["FERRO GUSA"])):
    a = AM[(AM["op"] == "VLI") & (AM["malha"] == malha) & (AM["mercadoria"] == merc) & (AM["servico"] == "Manobra")]
    x = SV[SV["servico"].isin(MANOBRAS) & (SV["valor"] >= 0.5) & (SV["ferrovia"] == malha) & SV["produto"].isin(prods)]["valor"]
    if len(a) and len(x):
        a = a.iloc[0]
        _tab3.append([f"{malha} · {merc.lower()}", round(a.mn, 2), round(a.md, 2), round(a.mx, 2), int(len(x)),
                      round(x.min(), 2), round(x.mean(), 2), round(x.max(), 2),
                      round(a.mx / x.max(), 1) if x.max() > 0 else None])
_soja = next((r for r in _tab3 if r[0].startswith("FCA · soja")), None)
cat(3, "A", "Tabela publicada não reflete o preço praticado",
    "Res. ANTT 6.031/2023, art. 16 caput (indicadores representativos do preço)", F_PUB, "descritivo", "nenhuma",
    (f"Manobra de soja na FCA: publicado média R$ {br(_soja[2])} e máximo R$ {br(_soja[3])}; praticado em 2026 "
     f"média R$ {br(_soja[6])} e máximo R$ {br(_soja[7])} ({ni(_soja[4])} observações). " if _soja else "")
    + "O máximo publicado fica várias vezes acima do maior preço cobrado, o que esvazia o limite do §3º. "
      "Há também cliente pagando abaixo do mínimo publicado.",
    "Tese de transparência: pedir à ANTT que a VLI publique indicadores aderentes ao praticado. "
    "Usar com a ata notarial da tabela vigente.",
    {"cols": ["Malha e mercadoria", "Publicado mín", "Publicado méd", "Publicado máx", "Observações 2026",
              "Praticado mín", "Praticado méd", "Praticado máx", "Máx publicado ÷ máx praticado"], "rows": _tab3})

# ------------------------------------------------------------------ 4. mudanças de preço (art. 17)
_mm = SV[SV["servico"].isin(MANOBRAS + ["TRANSBORDO ORIGEM"])].sort_values(["item", "servico", "ferrovia", "mes"]).copy()
_mm["ant"] = _mm.groupby(["item", "servico", "ferrovia"])["valor"].shift()
_mm["mant"] = _mm.groupby(["item", "servico", "ferrovia"])["mes"].shift()
_ch = _mm[(_mm["mes"] - _mm["mant"] == 1) & (_mm["ant"] > 0) & ((_mm["valor"] - _mm["ant"]).abs() >= 0.01)].copy()
_ch["sobe"] = _ch["valor"] > _ch["ant"]
_ci = _ch.groupby("item").agg(n=("mes", "size"), up=("sobe", "sum"), meses=("mes", "nunique"))
L4 = pd.DataFrame([{"item": it, "servico": "MANOBRA E TRANSBORDO", "ferrovia": "", "cobrado": 0.0, "referencia": None,
                    "excesso": 0.0, "detalhe": f"{int(r.n)} mudanças em {int(r.meses)} meses, {int(r.up)} aumentos", "serie": None,
                    "no_mes_ref": 1} for it, r in _ci.iterrows()], columns=COLS_OUT)
guarda_linhas(4, L4)
cat(4, "A", "Mudança de preço sem aviso de 20 dias",
    "Res. ANTT 6.031/2023, art. 17 (aviso prévio de 20 dias; parágrafo único: preço contratado segue o contrato)",
    F_FICHA, "evidencia", "contagem",
    f"{ni(len(_ch))} mudanças de preço de manobra e transbordo de um mês para o seguinte em 2026, em {ni(_ch['item'].nunique())} itens "
    f"de {_ch['cliente'].nunique()} clientes; {ni(int(_ch['sobe'].sum()))} são aumentos; "
    f"{ni(int((_ci['meses'] >= 6).sum()))} itens mudaram em seis meses ou mais.",
    "Pedir ao cliente os comprovantes de aviso de cada mudança. Onde o contrato fixa fórmula, conferir se a "
    "mudança segue a fórmula; onde não fixa, mudança sem aviso de 20 dias é descumprimento.")

# ------------------------------------------------------------------ 5. manobra de conexão
def r_conexao(d):
    a = d[(d["servico"] == "MANOBRA CONEXAO CHEIO") & (d["valor"] > 0)].copy()
    a["cobrado"] = a["valor"]
    a["referencia"] = 0.0
    a["excesso"] = a["valor"]
    a["detalhe"] = "movimentação intermediária faturada como manobra"
    return a


L5 = aplica(r_conexao)
guarda_linhas(5, L5)
cat(5, "A", "Manobra de conexão e manobra não solicitada",
    "Res. ANTT 6.031/2023, art. 4º §4º e art. 6º IX (movimentação intermediária por iniciativa da ferrovia não é acessória cobrável)",
    F_FICHA, "linhas", "rs_ano",
    "Manobra de conexão com vagão cheio faturada a "
    + ", ".join(sorted({INFO[i]["cliente"] for i in L5["item"]})) + ". "
    "Para todos os clientes vale verificar se a manobra de origem e de destino foi solicitada expressamente "
    "e se ocorre em terminal operado pelo próprio cliente.",
    "Pedir a solicitação formal de cada manobra faturada. Sem solicitação, a cobrança é indevida e cabe repetição.")

# ------------------------------------------------------------------ 6. IPOA (número da aba Ficha)
_ipo = REF.copy()
_ipo["base"] = _ipo["frete"] + _ipo["dp"]
_fer = SVM.copy()
_fer["tipo"] = np.where(_fer["categoria"].isin(["frete", "dp"]), "base", "acess")
_pf = _fer.groupby(["ferrovia", "tipo"])["valor"].sum().unstack().fillna(0)
cat(6, "A", "IPOA acima da referência de 24,8%",
    "Res. ANTT 6.031/2023, art. 15 (preço abusivo; IPOA de referência)", F_FICHA, "ficha_ipoa", "rs_ano",
    f"IPOA mediano de {pct(float(_ipo['ipoa'].median()))} nos itens da ficha; "
    f"{ni(int((_ipo['ipoa'] > IPOA_REF).sum()))} de {ni(len(_ipo))} itens acima de 24,8%. "
    + "Regra do sócio: IPOA = acessórias sem DP ÷ (frete + DP). Valor = excesso sobre 24,8% vezes o volume "
      "real dos últimos 12 meses (mesmo número da aba Ficha de Fluxo 2026).",
    "Tese central de preço abusivo. Peça do cliente com a tarifa do F-LINK dele; a ficha só orienta.")

# ------------------------------------------------------------------ 7 e 8. manobra de grão em faixas
_g = SVM[SVM["servico"].isin(MANOBRAS) & (SVM["valor"] >= 0.5) & SVM["produto"].isin(GRAO)].copy()
_g["total"] = [TOT_MES.get((int(i), int(mm))) for i, mm in zip(_g["item"], _g["mes"])]
_g = _g[_g["total"].notna() & (_g["total"] > 0)]
_g["pct"] = (_g["valor"] / _g["total"] * 100).round(0)
FAIXAS = [5, 8, 12, 18]
_na_faixa = _g["pct"].isin(FAIXAS)
# menor faixa praticada POR CLASSE e ferrovia (farelo só com farelo, decisão do sócio de 19/nov/2026),
# exigindo que a faixa seja paga por pelo menos 2 clientes daquela classe na ferrovia
classe = lambda p: "FARELO" if str(p).startswith("FARELO") else "GRAOS"
_g["classe"] = _g["produto"].map(classe)
BASE_FAIXA = {}
for (cl, fe), h in _g.groupby(["classe", "ferrovia"]):
    fx = [f for f in FAIXAS if h.loc[h["pct"] == f, "cliente"].nunique() >= 2]
    if fx:
        BASE_FAIXA[(cl, fe)] = min(fx)
_tab7 = [[f"{fe} · {'farelo' if cl == 'FARELO' else 'soja e milho'}"]
         + [int(((_g["ferrovia"] == fe) & (_g["classe"] == cl) & (_g["pct"] == f)).sum()) for f in FAIXAS]
         + [int(((_g["ferrovia"] == fe) & (_g["classe"] == cl) & ~_na_faixa).sum()),
            f"{BASE_FAIXA[(cl, fe)]}%" if (cl, fe) in BASE_FAIXA else "n/d"]
         for cl, fe in sorted(set(zip(_g["classe"], _g["ferrovia"])))]
cat(7, "B", "Manobra de grão é percentual fixo da tarifa",
    "Res. ANTT 6.031/2023, arts. 15 e 16 (preço de serviço acessório, não percentual do frete); "
    "Lei 10.233/2001, art. 25 V", F_FICHA, "contagem", "contagem",
    f"{ni(int(_na_faixa.sum()))} de {ni(len(_g))} linhas de manobra de grão e farelo no mês de referência ({pct(_na_faixa.mean(), 1)}) "
    f"estão em faixas exatas de 5%, 8%, 12% ou 18% da tarifa total do item. "
    + "Preço de serviço formado por custo não seria percentual do frete. O contrato Czarnikow prevê 5% na FCA e 8% na FNS.",
    "Prova de que a manobra é precificada como frete. Pedir ao cliente a cláusula de preço da manobra; "
    "se o contrato não prevê percentual, a faixa aplicada não tem base.",
    {"cols": ["Ferrovia e classe", "5%", "8%", "12%", "18%", "Fora das faixas", "Menor faixa (2+ clientes)"], "rows": _tab7})
for cli, h in _g.groupby("cliente"):
    vc = h["pct"].value_counts().sort_index()
    guarda_cliente(7, cli, None, len(h), "; ".join(f"{int(k)}%: {int(v)} linhas" for k, v in vc.items() if k in FAIXAS)
                   + (f"; fora das faixas: {int((~h['pct'].isin(FAIXAS)).sum())}" if (~h["pct"].isin(FAIXAS)).any() else ""))


def r_faixa(d):
    a = d[d["servico"].isin(MANOBRAS) & (d["valor"] >= 0.5) & d["produto"].isin(GRAO)].copy()
    a["b"] = [BASE_FAIXA.get((classe(p), f)) for p, f in zip(a["produto"], a["ferrovia"])]
    a = a[a["b"].notna()]
    a["total"] = [TOT_MES.get((int(i), int(mm))) for i, mm in zip(a["item"], a["mes"])]
    a = a[a["total"].notna() & (a["total"] > 0)]
    a["cobrado"] = a["valor"]
    a["referencia"] = a["b"] / 100 * a["total"]
    a["excesso"] = (a["valor"] - a["referencia"]).clip(lower=0)
    a["detalhe"] = ((a["valor"] / a["total"] * 100).round(0).astype(int).astype(str) + "% da tarifa total; menor faixa da "
                    + a["ferrovia"] + " para " + a["produto"].map(lambda p: "farelo" if classe(p) == "FARELO" else "soja e milho")
                    + " " + a["b"].astype(int).astype(str) + "%")
    return a


L8 = aplica(r_faixa)
guarda_linhas(8, L8)
cat(8, "B", "Faixa da manobra muda por cliente",
    "Lei 10.233/2001, art. 25 VIII e Res. ANTT 6.031/2023 (isonomia; mesmo serviço, mesma ferrovia)", F_FICHA, "linhas", "rs_ano",
    "No mesmo serviço e na mesma ferrovia, clientes pagam faixas diferentes: "
    + "; ".join(f"{int(f)}%: " + ", ".join(sorted(_g[_g['pct'] == f]['cliente'].value_counts().head(4).index))
                for f in FAIXAS if (_g["pct"] == f).any())
    + ". Valor = manobra acima da menor faixa paga por pelo menos 2 clientes da mesma classe na mesma ferrovia (farelo só com farelo: "
    + ", ".join(f"{fe} {'farelo' if cl == 'FARELO' else 'soja e milho'} {v}%" for (cl, fe), v in sorted(BASE_FAIXA.items()))
    + "), mês a mês, vezes o volume.",
    "Pedir isonomia com a menor faixa da ferrovia. Para clientes em 12% e 18% é a alavanca de maior valor.")

# ------------------------------------------------------------------ 9, 10, 16: P&L ferroviário
_ALIAS = {"COQUE VERDE PETROLEO": "COQUE PETROLEO"}


def normp(p):
    s = re.sub(r"\(ITEM\s+\S+?\)", "", str(p or "")).strip().upper().split(" - ")[0].strip()
    parts = s.split()
    if not parts:
        return s
    parts[0] = {"PRO": "PRODUTO", "ROCHA": "FOSFATO"}.get(parts[0], parts[0])
    j = " ".join(t for t in parts if t not in ("DE", "DO", "DA"))
    return _ALIAS.get(j, j)


P = q("""SELECT ano, mes, cliente, origem, destino, mercadoria, rec_fr, rec_man, rec_trbd, rec_dp, rec_total, vol_tu
         FROM vli_pnl WHERE modal='Ferrovia' AND realizado=1""")
for c in ("rec_fr", "rec_man", "rec_trbd", "rec_dp", "rec_total", "vol_tu"):
    P[c] = pd.to_numeric(P[c], errors="coerce").fillna(0.0)
P["cli"] = P["cliente"].map(canon)
P["prod"] = P["mercadoria"].map(normp)
_ULT = int(P.loc[P["ano"] == P["ano"].max(), "mes"].max())
_ano = P.groupby("ano")[["rec_fr", "rec_man", "rec_trbd", "rec_dp", "rec_total", "vol_tu"]].sum()
_ano["man_t"] = _ano["rec_man"] / _ano["vol_tu"]
_ano["fr_t"] = _ano["rec_fr"] / _ano["vol_tu"]
_ano["ipoa"] = (_ano["rec_total"] - _ano["rec_fr"] - _ano["rec_dp"]) / (_ano["rec_fr"] + _ano["rec_dp"])


def _por_rota(anos, vmin):
    r = P[P["ano"].isin(anos)].groupby(["cli", "origem", "destino", "prod", "ano"])[
        ["rec_fr", "rec_man", "rec_total", "vol_tu"]].sum().unstack("ano")
    ok = np.ones(len(r), bool)
    for a in anos:
        ok &= (r[("vol_tu", a)] >= vmin).values
    return r[ok]


_r = _por_rota([2023, 2024], 50000)
J = pd.DataFrame({"man23": _r[("rec_man", 2023)] / _r[("vol_tu", 2023)], "man24": _r[("rec_man", 2024)] / _r[("vol_tu", 2024)],
                  "fr23": _r[("rec_fr", 2023)] / _r[("vol_tu", 2023)], "fr24": _r[("rec_fr", 2024)] / _r[("vol_tu", 2024)],
                  "vol24": _r[("vol_tu", 2024)]})
J["dman"] = J["man24"] - J["man23"]
J["dfr"] = J["fr24"] - J["fr23"]
J = J[J["dman"] > 5].reset_index()
J["valor"] = J["dman"] * J["vol24"]
for cli, h in J.groupby("cli"):
    guarda_cliente(9, cli, h["valor"].sum(), len(h),
                   f"{len(h)} rota(s); manobra/t mediana de R$ {br(h['man23'].median())} (2023) para R$ {br(h['man24'].median())} (2024); "
                   f"frete/t {'+' if h['dfr'].median() >= 0 else ''}R$ {br(h['dfr'].median())}")
_mm24 = P[P["ano"].isin([2023, 2024])].groupby(["ano", "mes"])[["rec_man", "vol_tu"]].sum()
_mm24["t"] = _mm24["rec_man"] / _mm24["vol_tu"]
cat(9, "B", "O salto da manobra em março de 2024",
    "Res. ANTT 6.031/2023, arts. 15 e 17 (preço abusivo; aviso prévio); Lei 10.233/2001, art. 25 V", F_PNL, "cliente", "rs_ano",
    f"Receita de manobra de R$ {br(_ano.at[2023, 'rec_man'] / 1e9)} bi (2023) para R$ {br(_ano.at[2024, 'rec_man'] / 1e9)} bi (2024), "
    f"com volume de {br(_ano.at[2023, 'vol_tu'] / 1e6, 1)} para {br(_ano.at[2024, 'vol_tu'] / 1e6, 1)} Mt e frete por tonelada "
    f"{br((_ano.at[2024, 'fr_t'] / _ano.at[2023, 'fr_t'] - 1) * 100, 1)}%. IPOA da ferrovia de {pct(_ano.at[2023, 'ipoa'])} para "
    f"{pct(_ano.at[2024, 'ipoa'])}. Em {len(J)} rotas a manobra subiu mais de R$ 5/t; valor = aumento de R$/t vezes o volume de 2024.",
    "Pedir ao cliente o aviso do aumento de março de 2024 e a justificativa de custo. O aumento entrou pela "
    "parcela sem teto: é o argumento mais forte de preço abusivo.",
    {"cols": ["Mês", "Manobra R$/t 2023", "Manobra R$/t 2024"],
     "rows": [[MESES[m - 1], round(float(_mm24.at[(2023, m), "t"]), 2), round(float(_mm24.at[(2024, m), "t"]), 2)]
              for m in range(1, 13) if (2023, m) in _mm24.index and (2024, m) in _mm24.index]})

_r = _por_rota([2021, 2025], 50000)
_r = _r[_r[("rec_man", 2021)] > 0]
K = pd.DataFrame({"man21": _r[("rec_man", 2021)] / _r[("vol_tu", 2021)], "man25": _r[("rec_man", 2025)] / _r[("vol_tu", 2025)],
                  "fr21": _r[("rec_fr", 2021)] / _r[("vol_tu", 2021)], "fr25": _r[("rec_fr", 2025)] / _r[("vol_tu", 2025)],
                  "vol25": _r[("vol_tu", 2025)]})
K["dman"] = K["man25"] / K["man21"] - 1
K["dfr"] = K["fr25"] / K["fr21"] - 1
K["valor"] = (K["man25"] - K["man21"] * (1 + K["dfr"])).clip(lower=0) * K["vol25"]
K = K.reset_index()
for cli, h in K[K["valor"] > 0].groupby("cli"):
    guarda_cliente(10, cli, h["valor"].sum(), len(h),
                   f"{len(h)} rota(s); manobra/t {'+' if h['dman'].median() >= 0 else ''}{pct(h['dman'].median())} contra frete/t "
                   f"{'+' if h['dfr'].median() >= 0 else ''}{pct(h['dfr'].median())} (medianas, 2021 a 2025)")
cat(10, "B", "Manobra subiu mais que o frete de 2021 a 2025",
    "Res. ANTT 6.031/2023, art. 15 (preço abusivo); Lei 10.233/2001, art. 25 V", F_PNL, "cliente", "rs_ano",
    f"Em {len(K)} rotas comparáveis: manobra por tonelada {pct(K['dman'].median())} (mediana), frete {pct(K['dfr'].median())}; "
    f"em {int((K['dman'] > 1).sum())} rotas a manobra mais que dobrou. Valor = manobra de 2025 acima da manobra de 2021 "
    "corrigida pela variação do frete da mesma rota, vezes o volume de 2025.",
    "Argumento de tendência: se o frete (com teto) subiu X, a acessória não tem razão de custo para subir mais.")

_a = P.groupby(["ano", "cli", "origem", "destino", "prod"])[["rec_man", "vol_tu"]].sum().reset_index()
_a = _a[(_a["vol_tu"] >= 20000) & (_a["rec_man"] > 0)]
_a["man_t"] = _a["rec_man"] / _a["vol_tu"]
_iso = []
for (ano, o, d, p), g in _a.groupby(["ano", "origem", "destino", "prod"]):
    if g["cli"].nunique() < 3 or ano > 2025:
        continue
    for row in g.itertuples(index=False):
        med = g[g["cli"] != row.cli]["man_t"].median()
        _iso.append((ano, row.cli, max(0.0, row.man_t - med) * row.vol_tu))
ISO = pd.DataFrame(_iso, columns=["ano", "cli", "exc"])
for cli, h in ISO[ISO["exc"] > 0].groupby("cli"):
    por = h.groupby("ano")["exc"].sum()
    guarda_cliente(16, cli, por.sum(), None, "; ".join(f"{a}: R$ {mi(v)} mi" for a, v in por.items() if v >= 5e4))
_iso_ano = ISO.groupby("ano")["exc"].sum()
cat(16, "C", "Isonomia retroativa, 2021 a 2025",
    "Lei 10.233/2001, art. 25 VIII; Código Civil, art. 876 (repetição do indébito) e arts. 205 e 206 (prescrição)",
    F_PNL, "cliente", "rs_periodo",
    "Manobra por tonelada do cliente acima da mediana dos outros clientes na mesma rota, produto e ano "
    "(3 ou mais clientes, 20 kt ou mais): " + "; ".join(f"{a}: R$ {mi(v)} mi" for a, v in _iso_ano.items()) + ".",
    "Base para pedido retroativo. Prazo de prescrição de 3 a 10 anos conforme a tese; a peça usa as faturas do cliente.")

# ------------------------------------------------------------------ 11, 12: da aba Ficha
cat(11, "B", "Manobra acompanha o frete mês a mês",
    "Res. ANTT 6.031/2023, arts. 15 e 16 (preço de serviço, não do frete)", F_FICHA, "ficha_acomp", "contagem",
    "Itens em que o frete variou mais de 5% no ano e a manobra mudou junto. Serviço com preço de custo não "
    "mudaria com a sazonalidade do frete (mesmo critério da aba Ficha de Fluxo 2026).",
    "Reforça as alavancas 7 e 8: a manobra é parte do preço do frete fora do teto.")
cat(12, "B", "Troca entre frete e acessória com o total parado",
    "Decreto 1.832/1996 e Res. ANTT 6.031/2023 (teto sobre o frete; acessória fora do teto)", F_FICHA, "ficha_troca", "contagem",
    "Meses seguidos em que frete e acessória andaram em sentidos opostos com a tarifa total variando menos de 1%. "
    "O orçamento 2027 da VLI repete a troca em várias rotas (aba Reajustes e Vencimentos).",
    "Mostra que a divisão entre frete e acessória é escolha comercial. Pedir que o preço total seja tratado como frete para o teste do teto.")


# ------------------------------------------------------------------ 13. acessória > frete da ferrovia
def r_ferrovia(d):
    x = d.assign(tipo=np.where(d["categoria"].isin(["frete", "dp"]), "base", "acess"))
    t = x.groupby(["item", "ferrovia", "tipo"])["valor"].sum().unstack().reindex(columns=["base", "acess"]).fillna(0).reset_index()
    t = t[t["ferrovia"].isin(["FCA", "FNS", "EFVM", "EFC"]) & (t["acess"] > 0) & (t["acess"] > t["base"])].copy()
    t["servico"] = "ACESSORIAS DA FERROVIA"
    t["cobrado"] = t["acess"]
    t["referencia"] = t["base"]
    t["excesso"] = (t["acess"] - IPOA_REF * t["base"]).clip(lower=0)
    t["detalhe"] = ("frete + DP da " + t["ferrovia"] + " R$ " + t["base"].map(br) + "/t; acessórias da "
                    + t["ferrovia"] + " R$ " + t["acess"].map(br) + "/t")
    return t


L13 = aplica(r_ferrovia)
guarda_linhas(13, L13)
cat(13, "B", "Frete simbólico de uma ferrovia com acessória cheia",
    "Res. ANTT 6.031/2023, art. 15 (IPOA por concessionária); Decreto 1.832/1996", F_FICHA, "linhas", "rs_ano",
    f"Em {L13[L13.no_mes_ref == 1]['item'].nunique()} itens a acessória de uma ferrovia supera o frete + DP dela própria no mês de referência "
    f"({', '.join(f'{k} {v}' for k, v in L13[L13.no_mes_ref == 1].groupby('ferrovia')['item'].nunique().sort_values(ascending=False).items())}). "
    "Se o IPOA for apurado por concessionária, passa de 100% nesses itens. Valor = acessória da ferrovia acima "
    "de 24,8% do frete + DP da mesma ferrovia, vezes o volume.",
    "Pedir à ANTT que o IPOA seja apurado por concessionária. Forte em fluxos de duas ferrovias (siderurgia, grão FCA e FNS).")

# ------------------------------------------------------------------ 14, 15: isonomia na ficha
cat(14, "C", "Mesmo serviço, mesma estação, preços diferentes",
    "Lei 10.233/2001, art. 25 VIII; Res. ANTT 6.031/2023", F_FICHA, "ficha_gap", "rs_ano",
    "Manobra e transbordo acima da mediana dos outros clientes no mesmo serviço, estação e família de produto "
    "(grão com grão, farelo com farelo), vezes o volume. Mesmo número da aba Ficha de Fluxo 2026; grãos e farelo mês a mês.",
    "Pedido de isonomia com a mediana dos pares. Sem nome de outro cliente na peça (usar referência agregada).")
_FAM = {"SOJA": "GRAOS", "MILHO": "GRAOS", "FARELO DE SOJA": "FARELO", "FARELO DE MILHO": "FARELO",
        "FERTILIZANTES": "FERTILIZANTES", "ENXOFRE": "FERTILIZANTES", "ROCHA FOSF SECA": "FERTILIZANTES",
        "ROCHA FOS UMIDA": "FERTILIZANTES"}
_s = SVM[SVM["servico"].isin(MANOBRAS + ["TRANSBORDO ORIGEM"]) & (SVM["valor"] > 0)].copy()
_s["fam"] = _s["produto"].map(lambda p: _FAM.get(p, p))
_s["est"] = np.where(_s["servico"].str.contains("ORIGEM"), _s["origem"], _s["destino"])
_pc = _s[_s["valor"] >= 0.5].groupby(["servico", "est", "fam", "cliente"])["valor"].median().reset_index()
_med15 = {}
for k, g in _pc.groupby(["servico", "est", "fam"]):
    if g["cliente"].nunique() >= 3:
        for c in g["cliente"]:
            o = g[g["cliente"] != c]["valor"]
            _med15[k + (c,)] = float(o.median())
_s["med"] = [_med15.get((a, b, c, d)) for a, b, c, d in zip(_s["servico"], _s["est"], _s["fam"], _s["cliente"])]
L15 = _s[_s["med"].notna() & ((_s["valor"] < 0.5) | (_s["valor"] < 0.25 * _s["med"]))].copy()
L15 = L15.assign(cobrado=L15["valor"], referencia=L15["med"], excesso=0.0,
                 detalhe="mediana dos outros clientes na estação R$ " + L15["med"].map(br) + "/t", serie=None, no_mes_ref=1)
guarda_linhas(15, L15[COLS_OUT])
cat(15, "C", "Manobra simbólica para alguns clientes",
    "Lei 10.233/2001, art. 25 VIII (tratamento isonômico)", F_FICHA, "evidencia", "contagem",
    f"{len(L15)} linhas em que o cliente paga menos de R$ 0,50/t ou menos de um quarto da mediana dos outros clientes "
    "na mesma estação e serviço: " + ", ".join(sorted(L15["cliente"].unique())[:8]) + ".",
    "Prova de tratamento desigual a favor de alguns. Serve a todos os outros clientes da mesma estação; nunca citar o nome na peça.")

# ------------------------------------------------------------------ 17. transbordo
def r_transbordo(d):
    a = d[(d["categoria"] == "transbordo") & (d["valor"] > 0)].copy()
    a["cobrado"] = a["valor"]
    a["referencia"] = 0.0
    a["excesso"] = a["valor"]
    a["detalhe"] = "transbordo cobrado; verificar se ocorre em terminal do cliente"
    return a


L17 = aplica(r_transbordo)
_t = SVM[(SVM["categoria"] == "transbordo") & (SVM["valor"] > 0)].copy()
_t["est"] = np.where(_t["servico"].str.contains("DESTINO"), _t["destino"], _t["origem"])
_te = _t.groupby(["est", "cliente"])["valor"].median().reset_index().groupby("est")["valor"].agg(["count", "min", "max"])
_te = _te[(_te["count"] >= 3) & (_te["max"] - _te["min"] > 1)].sort_values("count", ascending=False)
_det17 = {e: f"na estação {e}, de R$ {br(r['min'])} a R$ {br(r['max'])} entre {int(r['count'])} clientes" for e, r in _te.iterrows()}
L17["detalhe"] = [_det17.get(INFO[i]["destino"] if "DESTINO" in s else INFO[i]["origem"], "transbordo cobrado")
                  for i, s in zip(L17["item"], L17["servico"])]
guarda_linhas(17, L17)
cat(17, "C", "Transbordo",
    "Res. ANTT 6.031/2023, arts. 4º e 6º (só é acessória a operação prestada pela ferrovia); Lei 10.233/2001, art. 25 VIII",
    F_FICHA, "linhas", "rs_ano",
    f"Transbordo cobrado em {ni(_t['item'].nunique())} itens de {_t['cliente'].nunique()} clientes; "
    f"R$ 15,00/t em {ni(int((_t['valor'].round(2) == 15).sum()))} linhas. Valores diferentes entre clientes em "
    + "; ".join(f"{e} (R$ {br(r['min'])} a R$ {br(r['max'])})" for e, r in _te.head(3).iterrows())
    + ". Valor = transbordo cobrado vezes o volume (é o que está em jogo se o serviço não for prestado pela ferrovia).",
    "Verificar com o cliente quem opera o transbordo. Se é o terminal do cliente, a cobrança cai inteira; se não, pedir isonomia com o menor valor da estação.")

# ------------------------------------------------------------------ 18, 19, 21: direito de passagem
_dp_it = SVM[SVM["categoria"] == "dp"].groupby("item")["valor"].sum()
_rt = REF[["item", "origem", "destino"]].copy()
_rt["dp"] = _rt["item"].map(_dp_it).fillna(0)
_rg = _rt.groupby(["origem", "destino"]).agg(n=("item", "count"), com=("dp", lambda s: int((s > 0).sum())))
_mix = _rg[(_rg["com"] > 0) & (_rg["com"] < _rg["n"])]
_mixset = set(_mix.index)
_det18 = {k: f"{int(r.n - r.com)} de {int(r.n)} itens da rota sem DP" for k, r in _mix.iterrows()}


def r_dp_misto(d):
    a = d[(d["categoria"] == "dp") & (d["valor"] > 0)].copy()
    a = a[[(o, de) in _mixset for o, de in zip(a["origem"], a["destino"])]]
    a["cobrado"] = a["valor"]
    a["referencia"] = 0.0
    a["excesso"] = a["valor"]
    a["detalhe"] = [_det18[(o, de)] for o, de in zip(a["origem"], a["destino"])]
    return a


def r_dp(d):
    a = d[(d["categoria"] == "dp") & (d["valor"] > 0)].copy()
    a["cobrado"] = a["valor"]
    a["referencia"] = 0.0
    a["excesso"] = a["valor"]
    a["detalhe"] = "direito de passagem " + a["ferrovia"] + " repassado ao cliente"
    return a


_dpi = SV[(SV["categoria"] == "dp") & (SV["valor"] > 0)].sort_values("mes").groupby(["item", "ferrovia"]).first()["valor"].to_dict()
_dpm = SV[(SV["categoria"] == "dp") & (SV["valor"] > 0)].sort_values("mes").groupby(["item", "ferrovia"]).first()["mes"].to_dict()


def r_dp_reaj(d):
    a = d[(d["categoria"] == "dp") & (d["valor"] > 0)].copy()
    a["referencia"] = [_dpi.get((i, f)) for i, f in zip(a["item"], a["ferrovia"])]
    a = a[a["referencia"].notna() & (a["valor"] > a["referencia"] + 0.005)]
    a["cobrado"] = a["valor"]
    a["excesso"] = a["valor"] - a["referencia"]
    a["detalhe"] = [f"DP {f} de R$ {br(r)} ({MESES[_dpm[(i, f)] - 1]}) para R$ {br(v)}"
                    for i, f, r, v in zip(a["item"], a["ferrovia"], a["referencia"], a["valor"])]
    return a


L18 = aplica(r_dp_misto)
L19 = aplica(r_dp)
L21 = aplica(r_dp_reaj)
guarda_linhas(18, L18)
guarda_linhas(19, L19)
guarda_linhas(21, L21)
cat(18, "C", "Direito de passagem cobrado de uns e não de outros na mesma rota",
    "Lei 10.233/2001, art. 25 VIII; Res. ANTT 5.943/2021", F_FICHA, "linhas", "rs_ano",
    f"{len(_mix)} rotas em que parte dos itens paga DP e parte não: "
    + "; ".join(f"{o}→{de} ({int(r.n - r.com)} de {int(r.n)} sem DP)" for (o, de), r in _mix.sort_values("n", ascending=False).head(4).iterrows())
    + ". Valor = DP pago pelos itens dessas rotas, vezes o volume.",
    "Pedir o mesmo tratamento dado aos itens sem DP na mesma rota. Sem nome de outro cliente na peça.")
_dpf = SVM[(SVM["categoria"] == "dp") & (SVM["valor"] > 0)].groupby("ferrovia")["valor"].agg(["median", "count"])
cat(19, "D", "Direito de passagem cobrado do cliente",
    "Decreto 1.832/1996, art. 6º e art. 17 §5º (tarifa única ao usuário); Res. ANTT 5.943/2021 (DP é relação entre ferrovias)",
    F_FICHA, "linhas", "rs_ano",
    f"DP faturado ao cliente em {ni(SVM[(SVM['categoria'] == 'dp') & (SVM['valor'] > 0)]['item'].nunique())} itens de "
    f"{SVM[(SVM['categoria'] == 'dp') & (SVM['valor'] > 0)]['cliente'].nunique()} clientes. "
    + "DP mediano por ferrovia: " + "; ".join(f"{f} R$ {br(r['median'])}/t" for f, r in _dpf.sort_values("count", ascending=False).iterrows()) + ".",
    "Tese do caso Czarnikow: contrato sem previsão de DP, VLI fatura o DP à parte. Conferir o contrato do cliente; "
    "a tese principal é transparência e qual teto vale no percurso de duas concessões (alavanca 22).")
_dpmes = SV[(SV["categoria"] == "dp") & (SV["valor"] > 0)].groupby(["ferrovia", "mes"])["valor"].median().unstack()
cat(21, "D", "Direito de passagem reajustado no meio do ano",
    "Res. ANTT 5.943/2021 (contrato operacional entre ferrovias); Res. ANTT 6.031/2023, art. 17", F_FICHA, "linhas", "rs_ano",
    "DP mediano por ferrovia mudou ao longo de 2026: "
    + "; ".join(f"{f} de R$ {br(r.dropna().iloc[0])} para R$ {br(r.dropna().iloc[-1])}"
                for f, r in _dpmes.iterrows() if abs(r.dropna().iloc[-1] - r.dropna().iloc[0]) >= 0.05)
    + ". Valor = aumento do DP no ano, vezes o volume.",
    "Pedir o contrato operacional entre as ferrovias (LAI ou exibição) para medir quanto a VLI paga e quanto repassa.",
    {"cols": ["Ferrovia"] + [MESES[m - 1] for m in _dpmes.columns],
     "rows": [[f] + [None if pd.isna(v) else round(float(v), 2) for v in r] for f, r in _dpmes.iterrows()]})

# ------------------------------------------------------------------ 20. DP no P&L
_pdp = P.groupby("ano")[["rec_fr", "rec_dp"]].sum()
cat(20, "D", "A própria VLI contabiliza o DP como frete",
    "Decreto 1.832/1996, art. 6º; Res. ANTT 5.943/2021", F_PNL, "descritivo", "nenhuma",
    "No P&L da VLI a linha de direito de passagem vem praticamente zerada e o valor está dentro da receita de frete: "
    "frete + DP do P&L bate com frete + DP da Ficha de Fluxo 2026 (razão mediana 1,00).",
    "Reforça a tese da alavanca 19: se o DP é frete na contabilidade da VLI, não é cobrança à parte e entra no teste do teto.",
    {"cols": ["Ano", "Receita de frete (R$ mi)", "Receita de DP (R$ mi)", "DP ÷ frete"],
     "rows": [[int(a), round(r.rec_fr / 1e6, 1), round(r.rec_dp / 1e6, 1), round(r.rec_dp / r.rec_fr, 4) if r.rec_fr else None]
              for a, r in _pdp.iterrows()]})

# ------------------------------------------------------------------ 22. teto em duas concessões
_fr2 = SVM[(SVM["categoria"] == "frete") & (SVM["valor"] > 0)].groupby("item")["ferrovia"].agg(lambda s: "+".join(sorted(set(s))))
L22 = REF[REF["item"].map(_fr2).fillna("").str.contains(r"\+")].copy()
L22 = pd.DataFrame({"item": L22["item"], "servico": "FRETE + DP", "ferrovia": L22["item"].map(_fr2),
                    "cobrado": L22["frete"] + L22["dp"], "referencia": L22["teto"], "excesso": 0.0,
                    "detalhe": L22["pct_teto"].map(lambda v: f"{pct(v, 1)} do teto") + "; frete em " + L22["item"].map(_fr2),
                    "serie": None, "no_mes_ref": 1})
guarda_linhas(22, L22)
cat(22, "D", "Qual teto vale em rota de duas concessões",
    "Decreto 1.832/1996, arts. 17 e 18; Res. ANTT 5.943/2021", F_FICHA, "evidencia", "contagem",
    f"{ni(len(L22))} itens têm frete em duas ferrovias; a VLI aplica um teto só ao percurso inteiro. "
    + f"{int((REF['pct_teto'] >= 0.9).sum())} itens estão a 90% ou mais do teto.",
    "Consulta formal à ANTT sobre o teto aplicável. Prioridade para itens a 90% ou mais do teto.")

# ------------------------------------------------------------------ 23, 24, 25: serviços acessórios do P&L
S = q("""SELECT ano, mercadoria, cliente, SUM(rec_total) rec FROM vli_pnl
         WHERE realizado=1 AND modal='Serviços Acessórios' GROUP BY 1,2,3""")
S["rec"] = pd.to_numeric(S["rec"], errors="coerce").fillna(0.0)
S["cli"] = S["cliente"].map(canon)
_ANO_FIM = int(S["ano"].max())
_lbl_ult = f"{_ANO_FIM} (jan a {MESES[_ULT - 1]})"


def _serv_pnl(aid, merc, valor_anos):
    x = S[S["mercadoria"] == merc].groupby(["cli", "ano"])["rec"].sum().unstack().fillna(0)
    for cli, r in x.iterrows():
        v = sum(r.get(a, 0) for a in valor_anos)
        if v <= 0 and r.sum() <= 0:
            continue
        guarda_cliente(aid, cli, v, None, "; ".join(
            f"{_lbl_ult if a == _ANO_FIM else a}: R$ {mi(r[a])} mi" for a in x.columns if abs(r[a]) >= 5e4))
    return x.sum()


_est = _serv_pnl(23, "Estadia de vagões", [2025])
cat(23, "E", "Estadia de vagões",
    "Res. ANTT 6.031/2023, arts. 4º e 16 (operação acessória com indicador publicado); Código Civil (culpa pela espera)",
    F_PNL, "cliente", "rs_2025",
    "Receita de estadia de vagões por ano: " + "; ".join(f"{_lbl_ult if a == _ANO_FIM else a}: R$ {mi(v)} mi" for a, v in _est.items())
    + ". Valor por cliente = 2025.",
    "Depende de quem causou a espera. Pedir ao cliente o extrato de estadia e os registros de chegada e liberação dos vagões.")
_bal = _serv_pnl(24, "Baldeação", [2025])
cat(24, "E", "Baldeação faturada à parte",
    "Res. ANTT 6.031/2023, arts. 4º, 16 e 17", F_PNL, "cliente", "rs_2025",
    "Linha que não existia até 2024: " + "; ".join(f"{_lbl_ult if a == _ANO_FIM else a}: R$ {mi(v)} mi" for a, v in _bal.items()) + ".",
    "Conferir se a baldeação é operação pedida pelo cliente e se tem indicador publicado (alavanca 2).")
_tp = S[S["mercadoria"] == "Take or Pay"]
_tpa = sorted(_tp["ano"].unique())
_top = _serv_pnl(25, "Take or Pay", _tpa)
cat(25, "E", "Take or pay cobrado",
    "Código Civil, arts. 112, 113 e 423 (interpretação do contrato de adesão); Código Civil, art. 876", F_PNL, "cliente", "rs_periodo",
    "Receita de take or pay: " + "; ".join(f"{a}: R$ {mi(v)} mi" for a, v in _top.items()) + ". Valor por cliente = soma do período.",
    "Revisão retroativa da apuração: volume contratado, falhas de oferta da ferrovia, força maior.")

# ------------------------------------------------------------------ 26. porto (número da aba Porto)
cat(26, "E", "Porto",
    "Lei 10.233/2001, art. 25; base regulatória da ANTAQ a validar", F_PNL, "porto", "rs_ano",
    "R$/t de cada cliente no porto contra o menor par no mesmo porto e produto (mesmo número da aba Porto e Serviços Acessórios). "
    "É teto superior: o escopo do serviço portuário pode diferir entre clientes.",
    "Usar para escolher onde abrir o contrato portuário, não como número de proposta.")

# ------------------------------------------------------------------ 27. orçamento 2027
try:
    _pan = [r[0] for r in con.execute("SELECT DISTINCT panorama FROM vli_pnl_orcamento")]
    _p27 = next(p for p in _pan if p.startswith("2027") and "Aceite" in p)
    _mr = int(q("SELECT MAX(mes) m FROM vli_pnl WHERE ano=2026 AND realizado=1")["m"].iloc[0])
    _sel = """SELECT cliente, origem, destino, mercadoria, SUM(rec_fr) fr, SUM(rec_dp) dp, SUM(rec_total) tot, SUM(vol_tu) vol
              FROM {t} WHERE modal='Ferrovia' AND {w} GROUP BY 1,2,3,4"""

    def _ag(t, w):
        d = q(_sel.format(t=t, w=w))
        for c in ("fr", "dp", "tot", "vol"):
            d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0.0)
        d["cli"] = d["cliente"].map(canon)
        d["prod"] = d["mercadoria"].map(normp)
        return d
    _r26 = _ag("vli_pnl", "ano=2026 AND realizado=1")
    _o27 = _ag("vli_pnl_orcamento", f"panorama='{_p27}' AND mes<={_mr}")
    _kr = ["origem", "destino", "prod"]
    _ra = _r26.groupby(_kr)[["fr", "dp", "tot", "vol"]].sum()
    _oa = _o27.groupby(_kr)[["fr", "dp", "tot", "vol"]].sum()
    _rr = _ra.join(_oa, lsuffix="_r", rsuffix="_o", how="inner")
    _rr = _rr[(_rr["vol_r"] >= 10000) & (_rr["vol_o"] >= 10000)]
    _rr["ac_r"] = (_rr["tot_r"] - _rr["fr_r"] - _rr["dp_r"]) / _rr["vol_r"]
    _rr["ac_o"] = (_rr["tot_o"] - _rr["fr_o"] - _rr["dp_o"]) / _rr["vol_o"]
    _rr["d"] = _rr["ac_o"] - _rr["ac_r"]
    _sobe = _rr[(_rr["d"] > 0.05 * _rr["ac_r"].abs()) & (_rr["d"] > 0.5)]
    _cv = _r26.groupby(["cli"] + _kr)["vol"].sum().reset_index()
    _cv = _cv.merge(_sobe[["ac_r", "ac_o", "d"]].reset_index(), on=_kr)
    _cv = _cv[_cv["vol"] >= 1000]
    _cv["valor"] = _cv["d"] * _cv["vol"]
    for cli, h in _cv.groupby("cli"):
        h = h.sort_values("valor", ascending=False)
        guarda_cliente(27, cli, h["valor"].sum(), len(h), "; ".join(
            f"{r.prod.lower()} {r.origem}→{r.destino}: acessória R$ {br(r.ac_r)} para R$ {br(r.ac_o)}/t" for r in h.head(3).itertuples()))
    _top27 = _sobe.assign(ef=_sobe["d"] * _sobe["vol_o"]).sort_values("ef", ascending=False).head(5)
    cat(27, "F", "Orçamento 2027 com acessória maior",
        "Res. ANTT 6.031/2023, art. 17 (aviso de 20 dias) e art. 15 (preço abusivo)",
        f"Orçamento VLI {_p27} contra realizado 2026 (jan a {MESES[_mr - 1]}), uso interno", "cliente", "rs_periodo",
        f"{len(_sobe)} rotas em que a VLI orçou acessória por tonelada maior em 2027, mesmos meses do ano: "
        + "; ".join(f"{p.lower()} {o}→{de} R$ {br(r.ac_r)} para R$ {br(r.ac_o)}" for (o, de, p), r in _top27.iterrows())
        + ". Valor por cliente = aumento de R$/t da rota vezes o volume do cliente em 2026 no mesmo período.",
        "Avisar o cliente antes da renegociação de 2027: exigir o aviso do art. 17 e contestar pelo art. 15 antes da vigência.")
except Exception as e:  # orçamento ausente: alavanca fica descritiva
    cat(27, "F", "Orçamento 2027 com acessória maior", "Res. ANTT 6.031/2023, arts. 15 e 17", "Orçamento VLI 2027",
        "descritivo", "nenhuma", f"Orçamento 2027 indisponível no banco ({e}).", "")

# ------------------------------------------------------------------ 28. reforma tributária
try:
    _t25 = q("SELECT SUM(imp_pis+imp_cofins) pc, SUM(rec_total) rec FROM vli_pnl WHERE ano=2025 AND realizado=1").iloc[0]
    _t27 = q(f"SELECT SUM(COALESCE(imp_cbs,0)+COALESCE(imp_ibs,0)) ci, SUM(rec_total) rec FROM vli_pnl_orcamento WHERE panorama='{_p27}'").iloc[0]
    _a25 = abs(float(_t25["pc"])) / float(_t25["rec"])
    _a27 = abs(float(_t27["ci"])) / float(_t27["rec"])
    _rc = q("SELECT cliente, SUM(rec_total) rec FROM vli_pnl WHERE ano=2025 AND realizado=1 GROUP BY 1")
    _rc["rec"] = pd.to_numeric(_rc["rec"], errors="coerce").fillna(0.0)
    _rc["cli"] = _rc["cliente"].map(canon)
    _rc = _rc.groupby("cli")["rec"].sum()
    if _a25 > _a27:
        for cli, rec in _rc[_rc >= 1e6].items():
            guarda_cliente(28, cli, rec * (_a25 - _a27), None,
                           f"receita VLI 2025 R$ {mi(rec)} mi × queda de carga orçada ({pct(_a25, 1)} para {pct(_a27, 1)}); estimativa")
    cat(28, "F", "Reforma tributária",
        "LC 214/2025 (CBS e IBS); cláusula tributária de cada contrato; a validar com tributarista",
        f"P&L VLI 2025 e orçamento {_p27}, uso interno", "cliente", "rs_ano",
        f"A VLI orçou CBS e IBS de R$ {mi(abs(float(_t27['ci'])))} mi em 2027, contra PIS e COFINS de R$ {mi(abs(float(_t25['pc'])))} mi "
        f"em 2025: de {pct(_a25, 1)} para {pct(_a27, 1)} da receita. Valor por cliente = receita 2025 do cliente vezes a queda de carga "
        "(estimativa de ordem de grandeza).",
        "Verificar a cláusula tributária do contrato para repasse da redução e o crédito de CBS do cliente. Validar com tributarista antes de usar.")
except Exception as e:
    cat(28, "F", "Reforma tributária", "LC 214/2025", "Orçamento VLI 2027", "descritivo", "nenhuma",
        f"Dados tributários indisponíveis ({e}).", "")

# ------------------------------------------------------------------ 29, 30
cat(29, "F", "Contratos vencidos e sem data final",
    "Res. ANTT 6.031/2023, art. 17 (preço contratado segue o contrato; vencido, vale a tabela e o aviso)",
    "Painel do Cliente (vigência dos fluxos)", "contratos", "contagem",
    "Fluxos do Painel do Cliente com vigência vencida ou sem data final na base (mesma contagem da aba Reajustes e Vencimentos).",
    "Janela de renegociação aberta: entrar antes de a VLI renovar com preço novo.")
cat(30, "F", "Custo da manobra contra o preço cobrado",
    "Res. ANTT 6.031/2023, art. 15 (preço abusivo; referência de custo)", "Modelo de custo da aba Novo Negócio · Manobras",
    "descritivo", "nenhuma",
    "O modelo de custo da aba Novo Negócio estima a manobra em cerca de R$ 1,31/t (premissas editáveis naquela aba), contra R$ 13 a "
    "R$ 17/t cobrados em média. A diferença por cliente e estação está na aba Novo Negócio.",
    "Sustenta a alternativa de o cliente assumir a manobra. Premissa de custo fixo ainda em aberto.")

# ------------------------------------------------------------------ grava
CAT = pd.DataFrame(CATALOGO).sort_values("id")
CAT["grupo_nome"] = CAT["grupo"].map(GRUPOS)
LIN = pd.DataFrame(LINHAS)
CLI = pd.DataFrame(CLIENTES)
assert sorted(CAT["id"]) == list(range(1, 31)), sorted(CAT["id"])
_textos = pd.concat([CAT[c].astype(str) for c in ("titulo", "norma", "fonte", "evidencia", "uso", "tabela")]
                    + [LIN["detalhe"].astype(str), CLI["detalhe"].astype(str)])
_trav = _textos[_textos.str.contains("[–—]")]
assert _trav.empty, f"travessão no texto: {_trav.head(3).tolist()}"
with con:
    for t in ("alavanca_catalogo", "alavanca_linha", "alavanca_cliente"):
        con.execute(f"DROP TABLE IF EXISTS {t}")
    CAT.to_sql("alavanca_catalogo", con, index=False)
    LIN.to_sql("alavanca_linha", con, index=False)
    CLI.to_sql("alavanca_cliente", con, index=False)
con.close()
print(f"OK alavancas: {len(CAT)} no catálogo, {ni(len(LIN))} linhas de item, {ni(len(CLI))} valores por cliente; "
      f"mês de referência {LBL_MES}")
