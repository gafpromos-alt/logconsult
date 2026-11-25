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


GRUPOS = {"G": "Contrato e F-LINK contra o faturado (cliente e item)",
          "H": "Posição do cliente na negociação",
          "A": "Descumprimento direto da Res. ANTT 6.031/2023",
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
    # varredura 24/nov/2026: baldeação e transbordo são serviços diferentes na própria tabela; a de
    # 2026 não traz mais coluna de baldeação, então baldeação cobrada fica sem indicador publicado
    if s.startswith("BALDEAC"):
        return ["BALDEACAO"]
    if s.startswith("TRANSBORDO"):
        return ["TRANSBORDO"]
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
    "Boa parte das mudanças é contratual: o contrato-padrão (cl. 3.5) reajusta 30% da tarifa todo mês pelo diesel "
    "do fornecedor da VLI. A tese passa a ser a comprovação do índice (alavanca 44); mudança fora da fórmula ou sem "
    "aviso de 20 dias, onde o contrato não prevê fórmula, segue sendo descumprimento.")

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
    "Atenção: no contrato-padrão (cl. 3.2) a manobra é uma fatia da tarifa única. Baixar a faixa sem baixar o total só "
    "move dinheiro para o frete; o valor é a parcela realocável, não desembolso. Usar junto com a isonomia da tarifa "
    "total (alavanca 38) e com o faturado contra o contrato (alavanca 36).")

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


P = q("""SELECT ano, mes, cliente, origem, destino, mercadoria, rec_fr, rec_man, rec_trbd, rec_dp, rec_total, vol_tu,
                COALESCE(imp_icms,0)+COALESCE(imp_iss,0)+COALESCE(imp_pis,0)+COALESCE(imp_cofins,0) imp
         FROM vli_pnl WHERE modal='Ferrovia' AND realizado=1""")
for c in ("rec_fr", "rec_man", "rec_trbd", "rec_dp", "rec_total", "vol_tu", "imp"):
    P[c] = pd.to_numeric(P[c], errors="coerce").fillna(0.0)
# varredura 24/nov/2026: o P&L é bruto (ICMS e PIS/COFINS dentro). Para comparar clientes, a receita
# vai líquida de tributos linha a linha (cliente com e sem o regime de exportador ficam comparáveis)
_liq = np.where(P["rec_total"] > 0, 1 + P["imp"] / P["rec_total"], 1.0)
for c in ("rec_fr", "rec_man", "rec_trbd", "rec_dp", "rec_total"):
    P[c] = P[c] * _liq
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
    "Pedir ao cliente o aviso do aumento de março de 2024 e a justificativa de custo. Parte foi devolvida em 2026 "
    "(alavanca 39: o preço do grão caiu nos últimos 12 meses, de forma desigual entre clientes). Valores líquidos de tributos.",
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
    "Decorre de a manobra ser percentual da tarifa (cl. 3.2 do contrato-padrão) e de a tarifa ser reajustada todo mês "
    "(cl. 3.5). Serve de prova de que a manobra é parte do preço, não serviço com custo próprio.")
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


L18 = aplica(r_dp_misto, so_ref=True).assign(excesso=0.0)
L19 = aplica(r_dp)
L21 = aplica(r_dp_reaj)
guarda_linhas(18, L18)
guarda_linhas(19, L19)
guarda_linhas(21, L21)
cat(18, "C", "Direito de passagem cobrado de uns e não de outros na mesma rota",
    "Lei 10.233/2001, art. 25 VIII; Res. ANTT 5.943/2021", F_FICHA, "evidencia", "contagem",
    f"{len(_mix)} rotas em que parte dos itens paga DP e parte não: "
    + "; ".join(f"{o}→{de} ({int(r.n - r.com)} de {int(r.n)} sem DP)" for (o, de), r in _mix.sort_values("n", ascending=False).head(4).iterrows())
    + ". Não é ganho: quem não paga DP paga frete maior que o frete + DP dos demais (mediana de R$ 24/t a mais, "
      "varredura de 24/nov/2026). Serve de prova de que existe contrato com DP embutido no frete.",
    "Usar como argumento de que o DP pode ser negociado dentro do frete (alavanca 19), não como pedido de isonomia.")
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
    "O DP é repassado a custo: no P&L de 2025 a VLI pagou R$ 353,6 mi de DP e as rotas casadas mostram diferença "
    "de 1% a 4% entre cobrado e pago. A tese é de transparência (contrato operacional, LAI ou exibição), não de margem.",
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
    f"{ni(len(L22))} itens têm frete em duas ferrovias; a VLI aplica a tabela da ferrovia de origem sobre o km total. "
    "Conforme a regra que a ANTT adotar, o efeito vai de zero (soma dos tetos por trecho) a cerca de R$ 122 mi/ano "
    "(menor tabela no percurso inteiro); trecho a trecho, R$ 49 mi (Usiminas e LD Celulose). "
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
    "R$/t de cada cliente no terminal, líquido de ICMS, ISS e PIS/COFINS, contra o menor par no mesmo terminal e produto "
    "(mesmo número da aba Porto e Serviços Acessórios). É teto superior: o escopo do serviço portuário pode diferir entre clientes.",
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
    "Fluxos do Painel do Cliente com vigência vencida ou sem data final na base (mesma contagem da aba Reajustes e Vencimentos). "
    "Fluxo com cadastro vencido mas faturando no mês de referência da Ficha 2026 não conta: o contrato foi renovado e só a "
    "data ficou velha (79 de 118 casos na varredura de 24/nov/2026).",
    "Janela de renegociação aberta: entrar antes de a VLI renovar com preço novo.")
cat(30, "F", "Custo da manobra contra o preço cobrado",
    "Res. ANTT 6.031/2023, art. 15 (preço abusivo; referência de custo)", "Modelo de custo da aba Novo Negócio · Manobras",
    "descritivo", "nenhuma",
    "O modelo de custo da aba Novo Negócio estima a manobra em cerca de R$ 1,31/t (premissas editáveis naquela aba), contra R$ 13 a "
    "R$ 17/t cobrados em média. A diferença por cliente e estação está na aba Novo Negócio.",
    "Sustenta a alternativa de o cliente assumir a manobra. Premissa de custo fixo ainda em aberto.")

# ==================================================================================================
# ALAVANCAS 31 A 46: cliente e item, com documento (varredura de 24/nov/2026)
# Pedido do sócio: as teses gerais "são itens conhecidos no mercado"; o que vale é onde a VLI se
# afasta do próprio documento (tela F-LINK do cliente, contrato assinado, tabela publicada vigente
# no mês, faturamento da Ficha) e a posição de cada cliente na negociação. Pela regra do sócio a
# manobra NÃO entra no teste do teto e o PIS/COFINS zerado dos exportadores de grão é regime
# conhecido: nenhuma das duas teses entra aqui.
# ==================================================================================================
import datetime as _dt

# ---- volume mensal por cliente × rota × produto (volume_hist completado pelo P&L realizado)
_vh = q("""SELECT cliente, origem, destino, mercadoria produto, ano, mes, SUM(realizado_ktu)*1000 t
           FROM volume_hist WHERE realizado_ktu > 0 GROUP BY 1,2,3,4,5,6""")
_vp = q("""SELECT cliente, origem, destino, mercadoria produto, ano, mes, SUM(vol_tu) t
           FROM vli_pnl WHERE modal='Ferrovia' AND realizado=1 GROUP BY 1,2,3,4,5,6 HAVING SUM(vol_tu) > 0""")
for _d in (_vh, _vp):
    _d["cliente"] = _d["cliente"].map(canon)
    _d["produto"] = _d["produto"].map(normp)
    _d["t"] = pd.to_numeric(_d["t"], errors="coerce").fillna(0.0)
_k6 = ["cliente", "origem", "destino", "produto", "ano", "mes"]
_vh = _vh.groupby(_k6, as_index=False)["t"].sum()
_vp = _vp.groupby(_k6, as_index=False)["t"].sum()
_tem = set(zip(*[_vh[c] for c in _k6]))
_vp = _vp[[k not in _tem for k in zip(*[_vp[c] for c in _k6])]]
_VV = pd.concat([_vh, _vp])
_VV["per"] = _VV["ano"] * 12 + _VV["mes"]
_VIDX = {}
for (c, o, d, p, per), t in _VV.groupby(["cliente", "origem", "destino", "produto", "per"])["t"].sum().items():
    _VIDX.setdefault((c, o, d), {}).setdefault(p, {})[int(per)] = float(t)
PER_MAX = int(_VV["per"].max())


def vol_mes(c, o, d, prod, per):
    """t no mês `per` (ano*12+mês); produto pelo nome normalizado, com prefixo único (regra do volume)."""
    n = _VIDX.get((c, o, d))
    if not n:
        return 0.0
    f = normp(prod)
    if f not in n:
        cands = [x for x in n if x.startswith(f) or f.startswith(x)]
        if len(cands) != 1:
            return 0.0
        f = cands[0]
    return n[f].get(int(per), 0.0)


def lbl_per(per):
    a, m = (per - 1) // 12, (per - 1) % 12 + 1
    return f"{MESES[m - 1]}/{a}"


# ---- regime de PIS/COFINS por cliente × família (mesma regra do build_painel: ALIQ_PC)
_pcq = q("""SELECT cliente, mercadoria, SUM(rec_total) rec, SUM(COALESCE(imp_pis,0)+COALESCE(imp_cofins,0)) pc
            FROM vli_pnl WHERE modal='Ferrovia' AND realizado=1
              AND (ano*12+mes) > (SELECT MAX(ano*12+mes) FROM vli_pnl WHERE realizado=1 AND modal='Ferrovia') - 12
            GROUP BY cliente, mercadoria""")
for _c in ("rec", "pc"):
    _pcq[_c] = pd.to_numeric(_pcq[_c], errors="coerce").fillna(0.0)


def fam_pc(p):
    s_ = na(p).strip()
    if s_.startswith("FARELO"): return "FARELO"
    if s_.startswith("SOJA") or s_.startswith("MILHO"): return "GRAOS"
    if s_.startswith("ACUCAR"): return "ACUCAR"
    return s_.split(" ")[0] if s_ else ""


_pcq["cliente"] = _pcq["cliente"].map(canon)
_pcq["fam"] = _pcq["mercadoria"].map(fam_pc)
_pcq = _pcq.groupby(["cliente", "fam"])[["rec", "pc"]].sum()
_pcq = _pcq[_pcq["rec"] >= 1e6]
_ALIQ = {k: float(-r.pc / r.rec) for k, r in _pcq.iterrows() if -r.pc / r.rec >= 0.05}
aliq = lambda c, p: _ALIQ.get((c, fam_pc(p)), 0.0)

# ---- telas F-LINK mineradas: todas as vigências, com componentes e TR ANTT
_TAB_CLI = {"novaagri": "NOVA AGRI", "ldcelulose": "LD CELULOSE", "alesat": "ALE", "selecta_farelo": "SELECTA",
            "acucar_novos_clientes": None}
_fl = []
for _t in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%\\_precos\\_contratuais' ESCAPE '\\'")]:
    _d = q(f'SELECT * FROM "{_t}"')
    _cols = list(_d.columns)
    _ic = "item_ferroviario" if "item_ferroviario" in _cols else ("item" if "item" in _cols else None)
    if _ic is None or "vigencia_inicial" not in _cols:
        continue
    _num = lambda cs: _d[cs].apply(pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1) if cs else pd.Series(0.0, index=_d.index)
    _fr = [c for c in _cols if re.fullmatch(r"frete(_rs_t)?|frete_(fca|efvm|fns|vli|mrs)_rs_t", c)]
    _frc = ["frete_rs_t"] if "frete_rs_t" in _fr else _fr
    _vi = _d["vigencia_inicial"].astype(str).str[:10]
    _dt1 = pd.to_datetime(_vi, errors="coerce", format="%Y-%m-%d")
    _dt1 = _dt1.fillna(pd.to_datetime(_vi, errors="coerce", format="%d/%m/%Y"))
    _base = _t.replace("_precos_contratuais", "")
    if "cliente" in _cols:
        _cli = _d["cliente"].map(canon)
    else:
        _cli = pd.Series(_TAB_CLI.get(_base) or canon(_base.upper()), index=_d.index)
    _fl.append(pd.DataFrame({
        "tab": _base, "cli": _cli, "item": pd.to_numeric(_d[_ic], errors="coerce"),
        "contrato": _d.get("contrato"), "o": _d.get("origem"), "d": _d.get("destino"), "prod": _d.get("produto"),
        "vi": _dt1, "frete": _num(_frc), "dp": _num([c for c in _cols if "direito_passagem" in c]),
        "mo": _num([c for c in _cols if c.startswith("manobra_origem")]),
        "md": _num([c for c in _cols if c.startswith("manobra_destino")]),
        "outras": _num([c for c in _cols if c.startswith("descarga") or c.startswith("manobra_conexao")]),
        "tr": pd.to_numeric(_d.get("valor_tr_antt"), errors="coerce"),
        "tarifa": pd.to_numeric(_d.get("tarifa_contrato"), errors="coerce")}))
FL = pd.concat(_fl, ignore_index=True).dropna(subset=["item", "vi"])
FL["item"] = FL["item"].astype(int)
FL["per"] = FL["vi"].dt.year * 12 + FL["vi"].dt.month
# linha suspeita de coluna trocada na transcrição (mesma regra do rastreador de reajustes)
FL["susp"] = (FL["frete"] < FL["mo"] + FL["md"]) & (FL["frete"] < 0.3 * FL["tarifa"].fillna(1e9))
FL = FL[~FL["susp"]].copy()
# a tarifa da tela às vezes vem sem um componente (Mosaic: sem a descarga até abr/2026): vale o maior
FL["tot"] = np.maximum(FL["tarifa"].fillna(0.0), FL["frete"] + FL["dp"] + FL["mo"] + FL["md"] + FL["outras"])
_n_it_fl = FL.groupby(["cli", "o", "d", "prod"])["item"].transform("nunique")
FL["n_it"] = _n_it_fl
FL = FL.sort_values(["tab", "item", "vi"])
_ULT_TAB = FL.groupby("tab")["per"].max().to_dict()


def _meses_vig(g):
    """Cada vigência vale do mês de início até o mês anterior à vigência seguinte (no máximo 3 meses)."""
    pers = list(g["per"])
    out = []
    for i, p0 in enumerate(pers):
        p1 = pers[i + 1] if i + 1 < len(pers) else p0 + 1
        out.append(list(range(p0, min(max(p1, p0 + 1), p0 + 3))))
    return out


# ---------------------------------------------------------------- 31. frete + DP acima do TR na tela F-LINK
_x = FL[(FL["tr"] > 0) & (FL["frete"] > 0)].copy()
_x["base"] = _x["frete"] + _x["dp"]
_x["exc"] = _x["base"] - _x["tr"]
_r31 = []
for (tab, it), g in _x.groupby(["tab", "item"]):
    g = g.drop_duplicates("per", keep="last")
    for (_, r), ms in zip(g.iterrows(), _meses_vig(g)):
        if r["base"] <= r["tr"] * 1.005:
            continue
        v = sum(vol_mes(r["cli"], r["o"], r["d"], r["prod"], m) for m in ms) / max(1, r["n_it"])
        _r31.append({"cli": r["cli"], "item": it, "o": r["o"], "d": r["d"], "prod": r["prod"], "per": r["per"],
                     "base": r["base"], "tr": r["tr"], "exc": r["exc"], "pct": r["base"] / r["tr"] - 1, "valor": r["exc"] * v})
R31 = pd.DataFrame(_r31)
if len(R31):
    for cli, h in R31.groupby("cli"):
        its = h.groupby(["item", "o", "d", "prod"]).agg(de=("per", "min"), ate=("per", "max"), pmax=("pct", "max")).reset_index()
        guarda_cliente(31, cli, h["valor"].sum(), its["item"].nunique(), ("sem volume casado na rota (produto da tela diferente do "
                       "volume ou rota sem tráfego): valor zero honesto; " if h["valor"].sum() <= 0 else "") + "; ".join(
            f"item {int(r.item)} {str(r.prod).lower()} {r.o}→{r.d}: {lbl_per(r.de)} a {lbl_per(r.ate)}, até {pct(r.pmax, 1)} acima do TR"
            for r in its.sort_values("pmax", ascending=False).head(4).itertuples()))
cat(31, "G", "Frete + DP acima do teto na tela F-LINK do próprio cliente",
    "Teto do contrato de concessão (Tabela Tarifária, Decisões SUFER); Decreto 1.832/1996; Código Civil, art. 876 (repetição)",
    "Telas F-LINK do cliente (preço contratual vigência a vigência, com o TR ANTT da própria tela)", "cliente", "rs_periodo",
    (f"{len(R31)} vigências em {R31['item'].nunique()} itens de {R31['cli'].nunique()} clientes com frete + DP acima do TR ANTT "
     "mostrado na mesma tela. Caso típico: ArcelorMittal item 14399 (fio máquina VTU→EPI), 5% a 13,6% acima de ago/2023 a "
     "nov/2024; em dez/2024 o frete cai exatamente para o TR (R$ 79,65) e a manobra de destino sobe R$ 6,55 no mesmo mês. "
     "Valor = excesso de cada vigência vezes o volume real do mês, dividido entre os itens do cliente na rota."
     if len(R31) else "Nenhuma vigência acima do TR."),
    "Prova é do próprio cliente (tela F-LINK). Pedir a devolução do excesso do período e conferir a troca frete por manobra "
    "no mês em que o frete encosta no teto.")

# ---------------------------------------------------------------- 32. orçamento 2027: frete + DP acima do teto
try:
    _pan = [r[0] for r in con.execute("SELECT DISTINCT panorama FROM vli_pnl_orcamento")]
    _p27b = next(p for p in _pan if p.startswith("2027") and "Aceite" in p)
    _o = q(f"""SELECT cliente, origem, destino, mercadoria, SUM(rec_fr) fr, SUM(rec_dp) dp, SUM(rec_total) tot,
                      SUM(vol_tu) vol, SUM(COALESCE(imp_icms,0)) icms
               FROM vli_pnl_orcamento WHERE modal='Ferrovia' AND panorama='{_p27b}' GROUP BY 1,2,3,4""")
    for c in ("fr", "dp", "tot", "vol", "icms"):
        _o[c] = pd.to_numeric(_o[c], errors="coerce").fillna(0.0)
    _o["cli"] = _o["cliente"].map(canon)
    _o["prod"] = _o["mercadoria"].map(normp)
    _o = _o.groupby(["cli", "origem", "destino", "prod"], as_index=False)[["fr", "dp", "tot", "vol", "icms"]].sum()
    _o = _o[_o["vol"] >= 10000]
    _tt = REF.assign(prod=REF["produto"].map(normp)).groupby(["origem", "destino", "prod"])["teto"].max().rename("teto").reset_index()
    _o = _o.merge(_tt, on=["origem", "destino", "prod"])
    # o P&L traz receita com ICMS em fluxo interno; a ficha e o teto estão sem ICMS
    _o["fr27"] = (_o["fr"] + _o["dp"]) / _o["vol"] * (1 - (_o["icms"].abs() / _o["tot"]).clip(0, 0.25))
    _a = _o[_o["fr27"] > _o["teto"] + 0.005].copy()
    _a["valor"] = (_a["fr27"] - _a["teto"]) * _a["vol"]
    for cli, h in _a.groupby("cli"):
        guarda_cliente(32, cli, h["valor"].sum(), len(h), "; ".join(
            f"{r.prod.lower()} {r.origem}→{r.destino}: frete + DP orçado R$ {br(r.fr27)} contra teto R$ {br(r.teto)}"
            for r in h.sort_values("valor", ascending=False).head(3).itertuples()))
    cat(32, "G", "Orçamento 2027 da VLI com frete + DP acima do teto",
        "Teto do contrato de concessão; Res. ANTT 6.031/2023, art. 17 (aviso de 20 dias)",
        f"Orçamento VLI {_p27b}, uso interno", "cliente", "rs_periodo",
        f"{len(_a)} rotas em que o frete + DP orçado para 2027, líquido de ICMS, passa do teto atual da rota. "
        "Gerdau carvão VTU→VOB e Selecta farelo EBJ→IUF são os maiores: a VLI orçou como frete o que hoje fatura como "
        "acessória. Valor = excesso sobre o teto vezes o volume orçado no ano.",
        "Avisar o cliente antes da renegociação de 2027: um preço de 2027 com frete acima do teto não pode ser aceito; "
        "pedir a composição antes de assinar.")
except Exception as e:
    cat(32, "G", "Orçamento 2027 da VLI com frete + DP acima do teto", "Teto do contrato de concessão", "Orçamento VLI 2027",
        "descritivo", "nenhuma", f"Orçamento 2027 indisponível ({e}).", "")

# ---------------------------------------------------------------- 33 e 34. contratos lidos contra a Ficha
# Contratos-padrão VLI lidos na íntegra (07_Dados VLI): C_2025_175 (Czarnikow) e C_2026_2 (Agrícola
# Alvorada). Cl. 3.2: manobra de origem e de destino = 5% da tarifa na FCA e 8% na FNS, cada uma.
# Nenhum dos dois tem cláusula de direito de passagem. Cl. 3.4: nova acessória só com aditivo.
CONTRATOS_LIDOS = {"CZARNIKOW": "C_2025_175", "ALVORADA": "C_2026_2"}
PCT_CONTRATO = {"FCA": 5.0, "FNS": 8.0}
# Escopo de cada contrato lido: só os produtos que ele cobre. A Ficha de 24/nov/2026 trouxe o açúcar da
# Czarnikow, que roda no contrato C_2026_44 (não lido): sem este filtro as regras do contrato de grãos
# caíam sobre o açúcar e a alavanca 34 subia R$ 7 mi/ano no cenário de baixo risco, sem documento.
CONTRATO_PRODUTOS = {"CZARNIKOW": ("SOJA", "MILHO"), "ALVORADA": ("SOJA", "MILHO")}


def _no_escopo(d):
    return pd.Series([str(p).upper() in CONTRATO_PRODUTOS.get(c, ()) for c, p in zip(d["cliente"], d["produto"])], index=d.index)


def r_contrato_manobra(d):
    a = d[_no_escopo(d) & d["servico"].isin(MANOBRAS) & (d["valor"] > 0)
          & d["ferrovia"].isin(PCT_CONTRATO)].copy()
    a["total"] = [TOT_MES.get((int(i), int(mm))) for i, mm in zip(a["item"], a["mes"])]
    a = a[a["total"].notna() & (a["total"] > 0)]
    a["pc"] = a["ferrovia"].map(PCT_CONTRATO)
    a["cobrado"] = a["valor"]
    a["referencia"] = a["pc"] / 100 * a["total"]
    a["excesso"] = (a["valor"] - a["referencia"]).clip(lower=0)
    a["detalhe"] = ((a["valor"] / a["total"] * 100).round(1).astype(str).str.replace(".", ",", regex=False) + "% da tarifa contra "
                    + a["pc"].astype(int).astype(str) + "% da cl. 3.2 do contrato " + a["cliente"].map(CONTRATOS_LIDOS))
    return a


def r_contrato_dp(d):
    a = d[_no_escopo(d) & (d["categoria"] == "dp") & (d["valor"] > 0)].copy()
    a["cobrado"] = a["valor"]
    a["referencia"] = 0.0
    a["excesso"] = a["valor"]
    a["detalhe"] = "DP " + a["ferrovia"] + " faturado; contrato " + a["cliente"].map(CONTRATOS_LIDOS) + " sem cláusula de direito de passagem"
    return a


L33 = aplica(r_contrato_manobra)
L34 = aplica(r_contrato_dp)
guarda_linhas(33, L33)
guarda_linhas(34, L34)
cat(33, "G", "Manobra faturada acima do percentual do contrato",
    "Contrato-padrão VLI, cl. 3.2 e 3.4; Código Civil, arts. 112, 113 e 876", "Contratos C_2025_175 e C_2026_2 contra a Ficha 2026",
    "linhas", "rs_ano",
    f"Contratos lidos: {', '.join(f'{c} ({n})' for c, n in CONTRATOS_LIDOS.items())}. A cl. 3.2 fixa a manobra de origem e a de "
    "destino em 5% da tarifa na FCA e 8% na FNS. "
    + (f"{L33['item'].nunique()} itens faturados acima do percentual: "
       + "; ".join(f"{INFO[r.item]['cliente']} {slbl(r.servico)} {INFO[r.item]['origem']}→{INFO[r.item]['destino']} {r.detalhe.split(' contra')[0]}"
                   for r in L33.drop_duplicates(["servico"]).head(3).itertuples()) + "."
       if len(L33) else "Nenhum item acima do percentual contratado."),
    "Dinheiro com documento: pedir a devolução da manobra acima do percentual contratado. Vale para todo cliente cujo "
    "contrato a LogConsult ler; hoje há dois contratos na base.")
cat(34, "G", "Direito de passagem faturado sem cláusula no contrato",
    "Contrato-padrão VLI, cl. 3.4 (nova cobrança só com aditivo); Decreto 1.832/1996, art. 6º; Res. ANTT 5.943/2021",
    "Contratos C_2025_175 e C_2026_2 contra a Ficha 2026", "linhas", "rs_ano",
    f"Nenhum dos dois contratos lidos tem cláusula de DP; a Ficha fatura DP em {L34['item'].nunique()} itens "
    f"({', '.join(sorted({INFO[i]['cliente'] for i in L34['item']}))}). A Czarnikow (C_2025_175) tem DP EFC de R$ 14,78/t em "
    "25 de 25 itens no último mês faturado (set/2026); esses itens estão sem preço recente na Ficha e ficam fora das linhas.",
    "Pedir a devolução do DP faturado sem previsão contratual ou o aditivo que o autorize.")

# ---------------------------------------------------------------- 35. manobra acima do máximo publicado vigente no mês
# Tabela publicada anterior da VLI (no site em set/2025, referência out/2024): manobra de "Grão e
# Açúcar" com máximo de R$ 35,00 na FCA e na FNS. A de 2026 (referência out/2025) subiu para R$ 120.
_MAX_ANT = None
try:
    _arq = BASE.parent / "02_Regulatorio_Tetos" / "Tabelas_Acessorias" / "_Arquivo" / "Tabelas-Acessorias-VLI-set25.xlsx"
    _mx = []
    for _sh in ("FCA", "FNS"):
        _t = pd.read_excel(_arq, sheet_name=_sh, header=None)
        _row = _t[_t.iloc[:, 1].astype(str).str.contains("Gr[ãa]o", regex=True)]
        if len(_row):
            _mx.append(float(_row.iloc[0, 5]))
    _MAX_ANT = max(_mx) if _mx else None
except Exception as e:
    print("  ! tabela publicada anterior indisponível:", e)
_GRAO_ACUCAR = lambda p: bool(re.match(r"(SOJA|MILHO|FARELO|ACUCAR|AÇÚCAR)", str(p or "").upper()))
_r35 = []
if _MAX_ANT:
    _y = FL[FL["prod"].map(_GRAO_ACUCAR) & (FL["vi"] >= "2024-10-01") & (FL["vi"] < "2026-01-01")]
    for (tab, it), g in _y.groupby(["tab", "item"]):
        g = g.drop_duplicates("per", keep="last")
        for (_, r), ms in zip(g.iterrows(), _meses_vig(g)):
            exc = max(0.0, r["mo"] - _MAX_ANT) + max(0.0, r["md"] - _MAX_ANT)
            if exc <= 0.005:
                continue
            v = sum(vol_mes(r["cli"], r["o"], r["d"], r["prod"], m) for m in ms if m < 2026 * 12 + 1) / max(1, r["n_it"])
            _r35.append({"cli": r["cli"], "item": it, "o": r["o"], "d": r["d"], "prod": r["prod"], "per": r["per"],
                         "mo": r["mo"], "md": r["md"], "exc": exc, "valor": exc * v})
R35 = pd.DataFrame(_r35)
for cli, h in (R35.groupby("cli") if len(R35) else []):
    guarda_cliente(35, cli, h["valor"].sum(), h["item"].nunique(), "; ".join(
        f"item {int(r.item)} {str(r.prod).lower()} {r.o}→{r.d}: manobra até R$ {br(max(r.mo, r.md))} em {lbl_per(r.per)}"
        for r in h.sort_values("exc", ascending=False).drop_duplicates("item").head(3).itertuples()))
cat(35, "G", "Manobra acima do máximo publicado que valia no mês",
    "Res. ANTT 6.031/2023, art. 16 §3º (cobrança acima do máximo publicado)",
    "Tabela publicada VLI anterior (set/2025) e telas F-LINK do cliente", "cliente", "rs_periodo",
    (f"A tabela publicada anterior da VLI trazia manobra de grão e açúcar com máximo de R$ {br(_MAX_ANT)}; a de 2026 subiu para "
     f"R$ 120,00. {len(R35)} vigências de 2025 cobraram acima do máximo da época, em {R35['cli'].nunique() if len(R35) else 0} clientes. "
     "Valor = excesso sobre o máximo vezes o volume real do mês da vigência."
     if _MAX_ANT else "Tabela anterior não encontrada no arquivo."),
    "Depende de provar qual tabela estava no site em cada mês (histórico do site, Wayback, ata notarial). Infração objetiva.")

# ---------------------------------------------------------------- 36. faturado acima do contrato vigente
_IMF = q("SELECT item, cliente, origem, destino, produto, mes, total FROM ficha_fluxo_item_mes WHERE programado=0 AND frete>0")
_IMF = _IMF[_IMF["item"].isin(ITENS)]
_FLI = {it: g.sort_values("vi") for it, g in FL.groupby("item")}
_NIT_REF = REF.groupby(["cliente", "origem", "destino", "produto"])["item"].count().to_dict()
_r36 = []
for r in _IMF.itertuples():
    g = _FLI.get(int(r.item))
    if g is None:
        continue
    g = g[(g["o"] == r.origem) & (g["d"] == r.destino)]
    if not len(g):
        continue
    ini = pd.Timestamp(2026, int(r.mes), 1)
    fim = ini + pd.offsets.MonthEnd(0)
    per = 2026 * 12 + int(r.mes)
    ate = g[g["vi"] <= fim]
    if not len(ate) or per > _ULT_TAB.get(ate.iloc[-1]["tab"], 0) + 1:
        continue
    c1 = ate.iloc[-1]
    c0 = ate.iloc[-2] if len(ate) >= 2 else None
    if c1["vi"] > ini and c0 is None:
        continue          # vigência começa no meio do mês e não se sabe o preço anterior
    ref = max(c1["tot"], c0["tot"]) if (c1["vi"] > ini and c0 is not None) else c1["tot"]
    if not ref or ref <= 0:
        continue
    tol = max(1.0, 0.02 * ref)
    if r.total > ref + tol:
        v = vol_mes(r.cliente, r.origem, r.destino, r.produto, per) / max(1, _NIT_REF.get((r.cliente, r.origem, r.destino, r.produto), 1))
        _r36.append({"item": int(r.item), "cli": r.cliente, "mes": int(r.mes), "per": per, "fat": r.total, "ref": ref,
                     "exc": r.total - ref, "contrato": c1["contrato"], "vi": c1["vi"], "valor": (r.total - ref) * v})
R36 = pd.DataFrame(_r36)
if len(R36):
    for it, h in R36.groupby("item"):
        u = h.sort_values("mes").iloc[-1]
        guarda_linhas(36, pd.DataFrame([{"item": it, "servico": "TARIFA TOTAL", "ferrovia": "", "cobrado": u["fat"],
                                         "referencia": u["ref"], "excesso": u["exc"],
                                         "detalhe": f"faturado acima do contrato em {', '.join(MESES[m - 1] for m in sorted(h['mes']))}/2026; "
                                                    f"contrato {u['contrato']}, vigência de {u['vi']:%d/%m/%Y}",
                                         "serie": None, "no_mes_ref": 1}]))
    for cli, h in R36.groupby("cli"):
        guarda_cliente(36, cli, h["valor"].sum(), h["item"].nunique(), ("sem volume casado nos meses: valor zero honesto; "
                       if h["valor"].sum() <= 0 else "") + "; ".join(
            f"item {int(it)}: R$ {br(g2['fat'].iloc[-1])} faturados contra R$ {br(g2['ref'].iloc[-1])} do contrato "
            f"({', '.join(MESES[m - 1] for m in sorted(g2['mes']))})"
            for it, g2 in h.groupby("item")))
cat(36, "G", "Faturado acima do preço do contrato vigente",
    "Contrato do cliente (preço e cl. 3.4); Código Civil, arts. 876 (repetição do indébito), 112 e 113",
    "Ficha de Fluxo 2026 (faturado) contra as telas F-LINK do cliente (contrato vigente no mês)", "cliente", "rs_periodo",
    (f"Item a item e mês a mês, a tarifa faturada na Ficha passou do preço do contrato vigente no F-LINK em "
     f"{R36['item'].nunique()} itens de {R36['cli'].nunique()} clientes (tolerância de R$ 1,00 ou 2% para o reajuste mensal do diesel). "
     + "; ".join(f"{r.cli} item {int(r.item)}: R$ {br(r.fat)} contra R$ {br(r.ref)}" for r in
                 R36.sort_values("exc", ascending=False).drop_duplicates("item").head(3).itertuples())
     + ". Valor = excesso vezes o volume real de cada mês. Na Mosaic (itens 39889 e 39890, ZVF) a diferença é a descarga de "
       "R$ 14,50: a tela de fev/2026 mostra frete de R$ 47,42 + descarga R$ 14,50 = R$ 70,22, e a Ficha fatura frete de R$ 61,9 "
       "(que já soma os R$ 14,50) mais a descarga em linha própria. Conferir na fatura se a descarga está sendo cobrada duas vezes; "
       "no item 41109 o frete passou de R$ 57,75 (mai) para R$ 89,29 (ago) contra R$ 57,22 do contrato vigente."
     if len(R36) else "Nenhum mês faturado acima do contrato vigente."),
    "É a alavanca de maior força documental: o cliente tem o contrato e a fatura. Pedir a devolução e a correção do "
    "faturamento. Conferir antes se não houve aditivo depois da última vigência filmada.")

# ---------------------------------------------------------------- 37. baldeação desigual na mesma rota e mês
def r_baldeacao(d):
    a = d[(d["servico"] == "BALDEACAO") & (d["valor"] >= 0.5)].copy()
    if not len(a):
        return a
    a["fam"] = a["produto"].map(fam_pc)
    a["aliq"] = [aliq(c, p) for c, p in zip(a["cliente"], a["produto"])]
    a["liq"] = a["valor"] * (1 - a["aliq"])
    pcli = a.groupby(["origem", "destino", "fam", "cliente"])["liq"].median().reset_index()
    med = {}
    for k, g in pcli.groupby(["origem", "destino", "fam"]):
        for c in g["cliente"]:
            o = g[g["cliente"] != c]["liq"]
            if len(o):
                med[k + (c,)] = float(o.median())
    a["med"] = [med.get((o, de, f, c)) for o, de, f, c in zip(a["origem"], a["destino"], a["fam"], a["cliente"])]
    a = a[a["med"].notna()]
    a["cobrado"] = a["valor"]
    a["referencia"] = a["med"] / (1 - a["aliq"])
    a["excesso"] = (a["valor"] - a["referencia"]).clip(lower=0)
    a["detalhe"] = "mediana dos outros clientes na mesma rota e mês R$ " + a["referencia"].map(br) + "/t"
    return a


L37 = aplica(r_baldeacao)
guarda_linhas(37, L37)
cat(37, "C", "Baldeação com preço diferente na mesma rota e mês",
    "Lei 10.233/2001, art. 25 VIII; Res. ANTT 6.031/2023, art. 16 §2º", F_FICHA, "linhas", "rs_ano",
    f"{L37['item'].nunique()} itens pagam baldeação acima da mediana dos outros clientes na mesma rota, produto e mês "
    "(preço líquido de PIS/COFINS). Ex.: Fert Tocantins VTU→ETB fertilizantes a R$ 20,44 contra cerca de R$ 10,05 de "
    "Fertigran, Yara e Terrena; a Fertigran caiu de R$ 20,11 para R$ 10,05 durante o ano.",
    "Pedir o mesmo preço dado aos pares no mesmo mês; sem nome de outro cliente na peça.")

# ---------------------------------------------------------------- 38. isonomia da tarifa total, líquida de tributos
_T = q("""SELECT cliente, origem, destino, mercadoria, ano, mes, SUM(rec_total) rec, SUM(vol_tu) vol,
                 SUM(COALESCE(imp_icms,0)+COALESCE(imp_iss,0)+COALESCE(imp_pis,0)+COALESCE(imp_cofins,0)) imp
          FROM vli_pnl WHERE modal='Ferrovia' AND realizado=1 GROUP BY 1,2,3,4,5,6""")
for c in ("rec", "vol", "imp"):
    _T[c] = pd.to_numeric(_T[c], errors="coerce").fillna(0.0)
_T["cli"] = _T["cliente"].map(canon)
_T["prod"] = _T["mercadoria"].map(normp)
_T["per"] = _T["ano"] * 12 + _T["mes"]
_PMX = int(_T.loc[_T["vol"] > 0, "per"].max())
_T = _T[(_T["per"] > _PMX - 12) & ~_T["cli"].isin(["POOL", "DIVERSOS"])]
_T = _T.groupby(["cli", "origem", "destino", "prod", "per"], as_index=False)[["rec", "vol", "imp"]].sum()
_T = _T[(_T["vol"] >= 1000) & (_T["rec"] > 0)]
_T["liq"] = (_T["rec"] + _T["imp"]) / _T["vol"]
_T["t"] = (-_T["imp"] / _T["rec"]).clip(0, 0.5)
_r38 = []
# GRÃO E FARELO POR MICRORREGIÃO (25/nov/2026, pedido do sócio): o P&L não tem a microrregião, então
# para esses produtos o preço do mês vem da Ficha 2026 por item (tarifa total do mesmo mês do calendário,
# ou o mais próximo), contra os itens dos OUTROS clientes na mesma origem, destino, produto e
# microrregião no mesmo mês de preço. Ganho do mês = média dos itens do cliente (sem par conta zero)
# vezes o volume do P&L daquele mês. Os demais produtos seguem pela rota inteira no P&L.
_GR38 = {"SOJA", "MILHO", "FARELO SOJA", "FARELO MILHO"}
_RF = REF.assign(prod=REF["produto"].map(normp), micro=REF["microrregiao"].fillna("").astype(str).str.strip())
_RF = _RF[_RF["prod"].isin(_GR38)]
_TOTI = {}
for (_it, _m), _t in TOT_MES.items():
    _TOTI.setdefault(_it, {})[_m] = _t
def _tot_mes(it, m):
    d = _TOTI.get(int(it))
    if not d:
        return None, None
    mm = m if m in d else min(d, key=lambda x: abs(x - m))
    return mm, d[mm]
_RF_by = {k: g for k, g in _RF.groupby(["origem", "destino", "prod"])}
_T_gr = _T[_T["prod"].isin(_GR38)]
_T = _T[~_T["prod"].isin(_GR38)]
for r in _T_gr.itertuples():
    g = _RF_by.get((r.origem, r.destino, r.prod))
    if g is None:
        continue
    meus = g[g["cliente"] == r.cli]
    if not len(meus):
        continue
    m = (int(r.per) - 1) % 12 + 1
    gaps = []
    for it in meus.itertuples():
        mp, tot = _tot_mes(it.item, m)
        if tot is None:
            gaps.append(0.0)
            continue
        a_it = aliq(r.cli, it.produto)
        pares = g[(g["cliente"] != r.cli) & (g["micro"] == it.micro)]
        porc = {}
        for pi in pares.itertuples():
            t2 = TOT_MES.get((int(pi.item), mp))
            if t2:
                porc.setdefault(pi.cliente, []).append(t2 * (1 - aliq(pi.cliente, pi.produto)))
        if not porc:
            gaps.append(0.0)
            continue
        ref = float(np.median([float(np.median(v)) for v in porc.values()]))
        gaps.append(max(0.0, tot * (1 - a_it) - ref) / (1 - a_it))
    exc = float(np.mean(gaps)) if gaps else 0.0
    if exc > 0:
        _r38.append({"cli": r.cli, "rota": f"{r.prod.lower()} {r.origem}→{r.destino}", "valor": exc * r.vol})
for k, g in _T.groupby(["origem", "destino", "prod", "per"]):
    if g["cli"].nunique() < 2:
        continue
    for r in g.itertuples():
        o = g[g["cli"] != r.cli]["liq"]
        exc = max(0.0, r.liq - float(o.median()))
        if exc > 0:
            _r38.append({"cli": r.cli, "rota": f"{r.prod.lower()} {r.origem}→{r.destino}", "valor": exc * r.vol / (1 - r.t)})
R38 = pd.DataFrame(_r38)
for cli, h in (R38.groupby("cli") if len(R38) else []):
    pr = h.groupby("rota")["valor"].sum().sort_values(ascending=False)
    guarda_cliente(38, cli, h["valor"].sum(), len(pr), "; ".join(f"{k}: R$ {mi(v)} mi" for k, v in pr.head(3).items()))
cat(38, "C", "Isonomia da tarifa total, líquida de tributos",
    "Lei 10.233/2001, art. 25 VIII", F_PNL, "cliente", "rs_ano",
    f"Tarifa total (frete + DP + acessórias) de cada cliente, líquida de ICMS e PIS/COFINS, contra a mediana dos OUTROS "
    f"clientes na mesma rota, produto e mês, nos 12 meses até {lbl_per(_PMX)}. Comparar o total elimina a troca entre "
    "frete e acessória; tirar o tributo elimina a diferença de regime. Grão e farelo comparam também a microrregião do "
    "item (Ficha 2026, mesmo mês), porque o P&L não a tem. Ganho devolvido aos termos do cliente. Caso mais "
    "claro: Raízen, maior cliente do diesel QPM→PPN e o maior preço da rota.",
    "Pedido de equalização com a mediana dos pares; a peça usa a fatura do cliente e a referência agregada, sem nomes.")

# ---------------------------------------------------------------- 39. queda do preço do grão desigual entre clientes
_G = P[(P["mercadoria"].notna())].copy()
_G["per"] = _G["ano"] * 12 + _G["mes"]
_PG = int(_G.loc[_G["vol_tu"] > 0, "per"].max())
_G = _G[_G["prod"].isin(["SOJA", "MILHO"]) & (_G["per"] > _PG - 24)]
_G["jan"] = np.where(_G["per"] > _PG - 12, "A", "B")
_k = ["cli", "origem", "destino", "prod", "mes"]
_ga = _G[_G["jan"] == "A"].groupby(_k)[["vol_tu", "rec_total"]].sum()
_gb = _G[_G["jan"] == "B"].groupby(_k)[["vol_tu", "rec_total"]].sum()
_gt = _ga.join(_gb, lsuffix="_a", rsuffix="_b", how="inner")
_gt = _gt[(_gt["vol_tu_a"] > 0) & (_gt["vol_tu_b"] > 0) & (_gt["rec_total_a"] > 0) & (_gt["rec_total_b"] > 0)].reset_index()
_gt["pa"] = _gt["rec_total_a"] / _gt["vol_tu_a"]
_gt["pb"] = _gt["rec_total_b"] / _gt["vol_tu_b"]
_ind = lambda g: (g["pa"] * g["vol_tu_a"]).sum() / (g["pb"] * g["vol_tu_a"]).sum() - 1
_ig = _ind(_gt)
_c39 = _gt.groupby("cli").apply(lambda h: pd.Series({"vol": h["vol_tu_a"].sum(), "ind": _ind(h), "base": (h["pb"] * h["vol_tu_a"]).sum()}))
_c39 = _c39[_c39["vol"] >= 100000]
_c39["valor"] = ((_c39["ind"] - _ig) * _c39["base"]).clip(lower=0)
for cli, r in _c39.iterrows():
    guarda_cliente(39, cli, r["valor"] if r["valor"] > 0 else 0.0, None,
                   f"preço em rota e mês constantes {pct(r['ind'], 1)} em 12 meses contra {pct(_ig, 1)} do grão em geral "
                   f"({br(r['vol'] / 1e6, 2)} Mt comparáveis)")
cat(39, "H", "Queda do preço do grão desigual entre clientes",
    "Lei 10.233/2001, art. 25 VIII (isonomia); argumento de negociação", F_PNL, "cliente", "rs_ano",
    f"Nos 12 meses até {lbl_per(_PG)}, contra os 12 anteriores, na mesma rota, produto e mês do calendário, o preço do grão "
    f"(soja e milho, líquido de tributos) variou {pct(_ig, 1)}. Clientes que caíram menos que a média ficaram para trás. "
    "Valor = diferença entre o índice do cliente e o geral, sobre a receita comparável.",
    "Usar na renegociação de 2027: o cliente pede ao menos a queda média que a VLI já concedeu aos pares.")

# ---------------------------------------------------------------- 40. notas complementares e de crédito
_S = q("""SELECT ano, cliente, SUM(CASE WHEN rec_total > 0 THEN rec_total ELSE 0 END) cob,
                 SUM(CASE WHEN rec_total < 0 THEN rec_total ELSE 0 END) cred
          FROM vli_pnl WHERE estagio='SUP' AND realizado=1 GROUP BY 1,2""")
for c in ("cob", "cred"):
    _S[c] = pd.to_numeric(_S[c], errors="coerce").fillna(0.0)
_S["cli"] = _S["cliente"].map(canon)
_S = _S[~_S["cli"].isin(["POOL", "DIVERSOS"])]
_sc = _S.groupby("cli")[["cob", "cred"]].sum()
_sc["liq"] = _sc["cob"] + _sc["cred"]
for cli, r in _sc[_sc["liq"] > 1e5].iterrows():
    guarda_cliente(40, cli, r["liq"], None, f"cobrado R$ {mi(r['cob'])} mi e creditado R$ {mi(-r['cred'])} mi em notas fora do preço")
_cre = _sc[_sc["liq"] < -1e6].sort_values("liq")
cat(40, "E", "Notas complementares e de crédito fora do preço",
    "Código Civil, arts. 112, 113, 423 e 876; Lei 10.233/2001, art. 25 VIII", F_PNL, "cliente", "rs_periodo",
    f"Lançamentos sem volume (estágio SUP) de {', '.join(str(a) for a in sorted(_S['ano'].unique()))}: R$ {mi(_sc['cob'].sum())} mi "
    f"cobrados e R$ {mi(-_sc['cred'].sum())} mi creditados. Receberam crédito líquido: "
    + ", ".join(f"{c} R$ {mi(-v)} mi" for c, v in _cre["liq"].head(5).items())
    + ". Valor por cliente = cobrança líquida no período.",
    "Auditar cada nota complementar do cliente e pedir o mesmo tratamento dado a quem recebeu crédito. A natureza dos "
    "lançamentos é inferida do P&L; confirmar com as faturas.")

# ---------------------------------------------------------------- 41. cobranças novas no P&L desde 2024
_N = q("""SELECT ano, cliente, mercadoria serv, SUM(rec_total) rec FROM vli_pnl
          WHERE realizado=1 AND modal='Serviços Acessórios'
            AND mercadoria IN ('Movimentação Extra','Orquestração Logística','Estocagem')
          GROUP BY 1,2,3
          UNION ALL
          SELECT ano, cliente, 'Serviço acessório no trem' serv, SUM(rec_sa) rec FROM vli_pnl
          WHERE realizado=1 AND modal='Ferrovia' AND rec_sa > 0 GROUP BY 1,2,3""")
_N["rec"] = pd.to_numeric(_N["rec"], errors="coerce").fillna(0.0)
_N["cli"] = _N["cliente"].map(canon)
_N = _N[~_N["cli"].isin(["POOL", "DIVERSOS"]) & (_N["rec"] > 0)]
# só o que é NOVO para o cliente: primeiro ano com receita daquele serviço em 2024 ou depois
_N["ini"] = _N.groupby(["cli", "serv"])["ano"].transform("min")
_N = _N[_N["ini"] >= 2024]
_ANOF = int(_N["ano"].max())
for cli, h in _N.groupby("cli"):
    ult = h[h["ano"] >= _ANOF - 1].groupby("ano")["rec"].sum()
    if h["rec"].sum() < 5e5:
        continue
    v = float(h[h["ano"] == _ANOF]["rec"].sum())
    guarda_cliente(41, cli, v, None, "; ".join(
        f"{s.lower()}: " + ", ".join(f"{int(a)} R$ {mi(x)} mi" for a, x in g.groupby('ano')['rec'].sum().items())
        for s, g in h.groupby("serv")))
cat(41, "E", "Cobranças que não existiam até 2023",
    "Res. ANTT 6.031/2023, art. 16 §2º (indicador publicado) e art. 17 (aviso)", F_PNL, "cliente", "rs_periodo",
    "Linhas de receita novas: Movimentação Extra nos terminais (fertilizantes no TUF), Orquestração Logística, Estocagem e "
    "serviço acessório faturado junto do trem (ex.: Mosaic, R$ 16,50/t em 2026 contra máximo publicado de R$ 14,00). "
    f"Entra só o serviço cujo primeiro ano de receita para aquele cliente é 2024 ou depois. Valor por cliente = {_ANOF} (meses realizados).",
    "Pedir o contrato ou aditivo que criou cada cobrança e o indicador publicado; sem os dois, a cobrança não tem base.")

# ---------------------------------------------------------------- 42. volume abaixo do orçamento 2026
try:
    _p26o = next(p for p in _pan if p.startswith("2026") and "Oficial" in p)
    _mr2 = int(q("SELECT MAX(mes) m FROM vli_pnl WHERE ano=2026 AND realizado=1")["m"].iloc[0])
    _rv = q("SELECT cliente, SUM(vol_tu) v FROM vli_pnl WHERE modal='Ferrovia' AND ano=2026 AND realizado=1 GROUP BY 1")
    _ov = q(f"SELECT cliente, SUM(vol_tu) v FROM vli_pnl_orcamento WHERE modal='Ferrovia' AND panorama='{_p26o}' AND mes<={_mr2} GROUP BY 1")
    for _d in (_rv, _ov):
        _d["v"] = pd.to_numeric(_d["v"], errors="coerce").fillna(0.0)
        _d["cli"] = _d["cliente"].map(canon)
    _vv = _rv.groupby("cli")["v"].sum().rename("real").to_frame().join(_ov.groupby("cli")["v"].sum().rename("orc"), how="outer").fillna(0)
    _vv = _vv[(_vv["orc"] >= 50000) & (_vv["real"] < 0.95 * _vv["orc"]) & ~_vv.index.isin(["POOL", "DIVERSOS", "RUMO", "MRS"])]
    for cli, r in _vv.iterrows():
        guarda_cliente(42, cli, None, int(round((r["orc"] - r["real"]) / 1000)),
                       f"{pct(1 - r['real'] / r['orc'])} abaixo: {ni(r['real'] / 1000)} kt realizados contra {ni(r['orc'] / 1000)} kt "
                       f"orçados pela VLI (jan a {MESES[_mr2 - 1]}/2026)")
    _tr = _rv["v"].sum(); _to = _ov[~_ov["cli"].isin(["RUMO", "MRS"])]["v"].sum()
    cat(42, "H", "Volume abaixo do que a VLI orçou para 2026",
        "Argumento de negociação; contrato-padrão cl. 8.7 (take or pay recíproco)", f"Orçamento VLI {_p26o} contra o realizado, uso interno",
        "contagem", "contagem",
        f"Jan a {MESES[_mr2 - 1]}/2026: {br(_tr / 1e6, 1)} Mt realizados contra {br(_to / 1e6, 1)} Mt orçados (sem as passagens de "
        f"Rumo e MRS). {len(_vv)} clientes ficaram mais de 5% abaixo do orçado: a VLI precisa do volume deles em 2027 e eles "
        "estão expostos a take or pay.",
        "Entrar na renegociação sabendo quanto a VLI conta com o cliente. Conferir no contrato se a falta de volume foi "
        "causada por oferta da ferrovia (cl. 8.7 vale para as duas partes).")
except Exception as e:
    cat(42, "H", "Volume abaixo do que a VLI orçou para 2026", "Argumento de negociação", "Orçamento VLI 2026",
        "descritivo", "nenhuma", f"Orçamento 2026 indisponível ({e}).", "")

# ---------------------------------------------------------------- 43. cláusulas do contrato-padrão; PREPEX da Alvorada
_alv = q("""SELECT SUM(rec_total) rec, SUM(COALESCE(imp_pis,0)+COALESCE(imp_cofins,0)) pc FROM vli_pnl
            WHERE modal='Ferrovia' AND realizado=1 AND cliente LIKE '%ALVORADA%'
              AND (ano*12+mes) > (SELECT MAX(ano*12+mes) FROM vli_pnl WHERE realizado=1 AND modal='Ferrovia') - 12""").iloc[0]
_alv_pc = -float(_alv["pc"] or 0)
if _alv_pc > 0:
    guarda_cliente(43, "ALVORADA", _alv_pc, None,
                   f"contrato C_2026_2 declara a Alvorada PREPEX (cl. 4.6, suspensão de PIS/COFINS) e o faturamento dos últimos 12 meses "
                   f"traz R$ {mi(_alv_pc)} mi de PIS/COFINS ({pct(_alv_pc / float(_alv['rec']), 1)} da receita); conferir se o Ato Declaratório foi entregue")
cat(43, "G", "Cláusulas do contrato-padrão que o cliente pode usar",
    "Contratos C_2025_175 e C_2026_2 (texto integral); Código Civil, arts. 112, 113 e 423", "Contrato-padrão VLI", "cliente", "rs_ano",
    "Lidas no texto dos dois contratos: tarifa única com manobra percentual (3.2) e custo já incluso (3.3); nova acessória só "
    "com aditivo (3.4); 30% da tarifa reajustados todo mês pelo diesel do fornecedor da VLI (3.5); mudança tributária reflete "
    "no preço, para mais ou para menos (4.2); suspensão de PIS/COFINS para exportador (4.6); multa de take or pay para "
    "qualquer das partes (8.7); aceitação tácita da apuração mensal (8.8). Caso concreto: a Alvorada é PREPEX no contrato e "
    "o faturamento traz PIS/COFINS.",
    "Cada cláusula é uma pergunta para o cliente. 4.2 sustenta o repasse da reforma tributária (alavanca 28); 8.7 permite "
    "cobrar a VLI por capacidade não ofertada; 8.8 exige contestar a apuração no prazo.",
    {"cols": ["Cláusula", "O que diz", "Uso"],
     "rows": [["3.2", "Manobra de origem e de destino = 5% da tarifa (FCA) e 8% (FNS); baldeação R$ 15,00", "Faturado acima do percentual (alavanca 33)"],
              ["3.4", "Nova operação acessória só com autorização expressa e aditivo", "DP e serviços sem aditivo (alavancas 34 e 41)"],
              ["3.5", "30% da tarifa reajustados todo mês pela variação do diesel do fornecedor da VLI", "Pedir comprovação do índice (alavanca 44)"],
              ["4.2", "Impacto tributário positivo ou negativo reflete no valor", "Repasse da queda de carga (alavanca 28)"],
              ["4.6", "Exportador PREPEX com suspensão de PIS/COFINS mediante Ato Declaratório", "Alvorada faturada com PIS/COFINS"],
              ["8.7", "Multa de 70% da tarifa média sobre o volume não cumprido, para qualquer das partes", "Cobrar capacidade não ofertada"],
              ["8.8", "Apuração mensal aceita tacitamente se não contestada até o fim do mês", "Contestar no prazo"]]})

# ---------------------------------------------------------------- 44. reajuste mensal pelo diesel (cl. 3.5)
_cz = q("""SELECT item, mes, total FROM ficha_fluxo_item_mes
           WHERE programado=0 AND frete>0 AND cliente = 'CZARNIKOW'""").sort_values(["item", "mes"])
_cz["var"] = _cz.groupby("item")["total"].pct_change()
_czm = _cz.dropna().groupby("mes")["var"].median()
cat(44, "G", "Reajuste mensal pelo diesel com índice que o cliente não confere",
    "Contrato-padrão VLI, cl. 3.5; Código Civil, arts. 113 e 423", "Contratos C_2025_175 e C_2026_2 e Ficha 2026", "descritivo", "nenhuma",
    "A cl. 3.5 reajusta 30% da tarifa todo mês pela variação do diesel praticado pelo fornecedor da VLI, de forma composta. "
    "O cliente não tem acesso ao índice. Variação mediana da tarifa total dos itens da Czarnikow na Ficha, mês a mês (inclui a "
    "curva mensal de preço do contrato e o diesel; os itens mudam todos juntos): "
    + "; ".join(f"{MESES[int(m) - 1]} {'+' if v >= 0 else ''}{pct(v, 1)}" for m, v in _czm.items() if abs(v) >= 0.0005)
    + ". Um reajuste de 2,3% na tarifa equivale a cerca de 7,8% de diesel em um mês.",
    "Exigir a nota do fornecedor e comparar com a série da ANP. Cada 1 ponto percentual sobre a receita de grãos vale cerca "
    "de R$ 32 mi/ano no mercado.",
    {"cols": ["Mês", "Variação mediana da tarifa total"],
     "rows": [[MESES[int(m) - 1], f"{'+' if v >= 0 else ''}{pct(v, 2)}"] for m, v in _czm.items()]})

# ---------------------------------------------------------------- 45. estadia por tonelada acima da mediana
_E = q("""SELECT ano, cliente, SUM(rec_total) rec FROM vli_pnl
          WHERE realizado=1 AND modal='Serviços Acessórios' AND mercadoria='Estadia de vagões' GROUP BY 1,2""")
_Ev = q("SELECT ano, cliente, SUM(vol_tu) vol FROM vli_pnl WHERE realizado=1 AND modal='Ferrovia' GROUP BY 1,2")
for _d in (_E, _Ev):
    _d["cli"] = _d["cliente"].map(canon)
_E["rec"] = pd.to_numeric(_E["rec"], errors="coerce").fillna(0.0)
_Ev["vol"] = pd.to_numeric(_Ev["vol"], errors="coerce").fillna(0.0)
_E = _E.groupby(["ano", "cli"])["rec"].sum().to_frame().join(_Ev.groupby(["ano", "cli"])["vol"].sum(), how="left").reset_index()
_E = _E[(_E["rec"] > 0) & (_E["vol"] > 0)]
_E["rs_t"] = _E["rec"] / _E["vol"]
_E["med"] = _E.groupby("ano")["rs_t"].transform("median")
_E["exc"] = ((_E["rs_t"] - _E["med"]).clip(lower=0) * _E["vol"])
_ANO_E = 2025 if (_E["ano"] == 2025).any() else int(_E["ano"].max())
for cli, h in _E.groupby("cli"):
    if h["exc"].sum() < 2e5:
        continue
    guarda_cliente(45, cli, float(h.loc[h["ano"] == _ANO_E, "exc"].sum()), None, "; ".join(
        f"{int(r.ano)}: R$ {br(r.rs_t)}/t contra mediana de R$ {br(r.med)}" for r in h.sort_values("ano").itertuples()))
cat(45, "E", "Estadia de vagões por tonelada acima da mediana",
    "Res. ANTT 6.031/2023, arts. 4º e 16; contrato-padrão, Anexo III (registros só da VLI, 7 dias para contestar)", F_PNL,
    "cliente", "rs_2025",
    f"Estadia por tonelada transportada, por cliente e ano, contra a mediana dos clientes com estadia. Mediana de "
    f"{_ANO_E}: R$ {br(float(_E.loc[_E['ano'] == _ANO_E, 'med'].iloc[0]))}/t. Valor = excesso sobre a mediana vezes o volume, em {_ANO_E}. "
    "Na Ipiranga a estadia por tonelada é várias vezes maior nos meses de volume baixo, sinal de espera não causada pelo cliente.",
    "Pedir os registros de chegada e liberação dos vagões e contestar dentro do prazo do Anexo III.")

# ---------------------------------------------------------------- 46. repasse à Vale contra o que a VLI cobra nos mesmos trechos
_V = q("""SELECT cliente, SUM(rec_total) rec, SUM(COALESCE(cst_rep_fix,0)+COALESCE(cst_rep_var,0)) rep, SUM(rec_man) man
          FROM vli_pnl WHERE modal='Ferrovia' AND realizado=1 AND ativo IN ('EFVM','EFC')
            AND (ano*12+mes) > (SELECT MAX(ano*12+mes) FROM vli_pnl WHERE realizado=1 AND modal='Ferrovia') - 12
          GROUP BY 1""")
for c in ("rec", "rep", "man"):
    _V[c] = pd.to_numeric(_V[c], errors="coerce").fillna(0.0)
_V["cli"] = _V["cliente"].map(canon)
_V = _V.groupby("cli")[["rec", "rep", "man"]].sum().sort_values("rec", ascending=False)
cat(46, "H", "O que a VLI repassa à Vale nos trechos da EFVM e da EFC",
    "Argumento de negociação; Res. ANTT 6.031/2023, art. 15 e Lei 10.233/2001, art. 25", F_PNL, "descritivo", "nenhuma",
    f"Nos 12 meses, a receita da VLI nos trechos da EFVM e da EFC foi de R$ {mi(_V['rec'].sum())} mi; o repasse à Vale, "
    f"R$ {mi(-_V['rep'].sum())} mi ({pct(-_V['rep'].sum() / _V['rec'].sum())}); a manobra cobrada nesses mesmos trechos, "
    f"R$ {mi(_V['man'].sum())} mi. Usiminas ESQ→VIC paga R$ 127,1/t e a VLI repassa R$ 13,8/t.",
    "Mostra ao cliente quanto da tarifa fica com a VLI quando a malha é da Vale; insumo de negociação, não ganho direto.",
    {"cols": ["Cliente", "Receita nos trechos (R$ mi)", "Repasse à Vale (R$ mi)", "Manobra cobrada (R$ mi)"],
     "rows": [[c, round(r.rec / 1e6, 1), round(-r.rep / 1e6, 1), round(r.man / 1e6, 1)] for c, r in _V.head(10).iterrows()]})


# ------------------------------------------------------------------ grava
CAT = pd.DataFrame(CATALOGO).sort_values("id")
CAT["grupo_nome"] = CAT["grupo"].map(GRUPOS)
LIN = pd.DataFrame(LINHAS)
CLI = pd.DataFrame(CLIENTES)
assert sorted(CAT["id"]) == list(range(1, 47)), sorted(CAT["id"])
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
