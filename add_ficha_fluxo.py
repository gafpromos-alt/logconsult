# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine: Ficha de Fluxo Geral 2026 (base consolidada VLI).
CONFIDENCIAL, USO RESTRITO AOS SÓCIOS

Fonte: 07_Dados VLI/Base_Consolidada_Ficha_de_Fluxo_Geral.xlsx, aba "Base" (nov/2026).
Uma linha por item ferroviário x serviço x ferrovia, com o teto tarifário do item e o valor
de cada mês de 2026 (jan a nov realizados; dez já lançado em parte, tratado como programado).
Ano conferido contra os vídeos F-LINK: item 18421 (SELECTA farelo) e 7894 (ARCELORMITTAL)
batem centavo a centavo em jul/ago de 2026.

Regra de teto e IPOA (pedido do sócio, 19/nov/2026):
  base do teto = frete + direito de passagem
  % do teto    = (frete + DP) / teto
  IPOA         = acessórias / (frete + DP), acessórias sem DP

O script:
  1. grava a ficha em formato longo (ficha_fluxo_servico_mes) e agregada por item x mês
     (ficha_fluxo_item_mes), com frete, DP, manobra origem/destino, transbordo, outros;
  2. grava a situação de referência de cada item (ficha_fluxo_ref): último mês com frete até o
     mês corrente;
  3. atualiza fluxos_servico (base de pares de manobra) com o mês de referência da ficha para
     os itens que ela traz; itens fora da ficha continuam como estavam;
  4. atualiza ipoa_teto com os valores de 2026 dos itens da ficha (insere os que faltam), cria
     as colunas dp e fonte_2026 e recalcula teto_1 e ipoa de TODAS as linhas pela regra acima.

Roda depois de build_db.py e dos complementos de ipoa_teto/fluxos_servico (atualizar_tudo.py).
Uso:  python3 add_ficha_fluxo.py
"""
import datetime
import pathlib
import sqlite3
import warnings

import pandas as pd

from canon import canon

warnings.simplefilter("ignore")
BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
XLSX = BASE.parent / "07_Dados VLI" / "Base_Consolidada_Ficha_de_Fluxo_Geral.xlsx"
ANO = 2026
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
# Teto da ROTA INTEIRA (decisão do sócio, 25/nov/2026: "aqui vale a rota inteira"). A versão de 24/nov
# da ficha traz na coluna "Teto Tarifario" (chave produto + origem + destino) um teto diferente em
# 1.278 itens; em parte deles é o trecho próprio da concessionária (açúcar ZGU→IUF: R$ 92,60 contra
# R$ 164,07 da rota), o que punha 38 itens acima do teto. O teto usado no sistema é, nesta ordem:
#   1. o da ficha de 19/nov (arquivada), por item;
#   2. o teto-base do item em ipoa_teto (coluna teto_base, congelada antes de a ficha escrever);
#   3. o de uma rota gêmea (mesma origem, destino e produto) nas duas fontes acima;
#   4. sem nenhuma delas, o valor da ficha nova, marcado "ficha (a confirmar)".
# O valor bruto da ficha nova fica em teto_ficha, só para consulta.
XLSX_TETO_ROTA = BASE.parent / "07_Dados VLI" / "_Arquivo" / "Base_Consolidada_Ficha_de_Fluxo_Geral_2026-11-19.xlsx"
TETO_FICHA, TETO_FONTE = {}, {}
FONTE = "Base_Consolidada_Ficha_de_Fluxo_Geral.xlsx (VLI, versão 24/nov/2026, com açúcar e combustíveis)"


def categoria(servico):
    s = str(servico).upper().strip()
    if s.startswith("FRETE"):
        return "frete"
    if s.startswith("DIREITO DE PASSAGEM"):
        return "dp"
    if s == "MANOBRA ORIGEM":
        return "manobra_origem"
    if s == "MANOBRA DESTINO":
        return "manobra_destino"
    if s.startswith("TRANSBORDO") or s.startswith("BALDEAC"):
        return "transbordo"
    return "outros"


def mes_corrente():
    hoje = datetime.date.today()
    return hoje.month if hoje.year == ANO else (12 if hoje.year > ANO else 1)


def teto_rota_inteira(df):
    """devolve (teto por item, fonte por item) para os itens de df (colunas item, origem, destino, produto, teto)."""
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(ipoa_teto)")]
    if "teto_base" not in cols:      # banco recém-reconstruído: congela o teto da base antes da ficha
        cur.execute("ALTER TABLE ipoa_teto ADD COLUMN teto_base REAL")
        cur.execute("UPDATE ipoa_teto SET teto_base = teto")
        con.commit()
    base = pd.read_sql("SELECT item, origem, destino, UPPER(TRIM(produto)) produto, teto_base FROM ipoa_teto WHERE teto_base > 0", con)
    con.close()
    por_item, gemea = {}, {}
    if XLSX_TETO_ROTA.exists():
        v1 = pd.read_excel(XLSX_TETO_ROTA, sheet_name="Base").drop_duplicates("Item")
        v1 = v1[v1["Teto Tarifario"] > 0]
        for c in ("Origem", "Destino", "Produto"):
            v1[c] = v1[c].astype(str).str.strip()
        v1["Produto"] = v1["Produto"].str.upper()
        por_item = {int(i): (float(t), "ficha de 19/nov") for i, t in zip(v1["Item"], v1["Teto Tarifario"])}
        gemea = {k: (float(t), "rota gêmea (ficha de 19/nov)") for k, t in
                 v1.groupby(["Origem", "Destino", "Produto"])["Teto Tarifario"].median().items()}
    b1 = base.drop_duplicates("item")
    for i, t in zip(b1["item"], b1["teto_base"]):
        por_item.setdefault(int(i), (float(t), "base (ipoa_teto)"))
    for k, t in base.groupby(["origem", "destino", "produto"])["teto_base"].median().items():
        gemea.setdefault(k, (float(t), "rota gêmea (base)"))
    teto, fonte = {}, {}
    for r in df.drop_duplicates("item").itertuples():
        v = por_item.get(int(r.item)) or gemea.get((r.origem, r.destino, r.produto)) or (float(r.teto), "ficha (a confirmar)")
        teto[r.item], fonte[r.item] = v
    return teto, fonte


def carregar():
    df = pd.read_excel(XLSX, sheet_name="Base")
    df = df.rename(columns={"Item": "item", "Cliente": "cliente_raw", "Origem": "origem",
                            "Destino": "destino", "Produto": "produto", "Microrregião": "microrregiao",
                            "Teto Tarifario": "teto", "Serviço": "servico", "Ferrovia": "ferrovia"})
    for c in ("cliente_raw", "origem", "destino", "produto", "servico", "ferrovia"):
        df[c] = df[c].astype(str).str.strip()
    df["produto"] = df["produto"].str.upper()
    df["cliente"] = df["cliente_raw"].map(canon)
    TETO_FICHA.update(zip(df["item"], df["teto"]))
    tr, fo = teto_rota_inteira(df)
    TETO_FONTE.update(fo)
    df["teto"] = df["item"].map(tr)
    df["categoria"] = df["servico"].map(categoria)
    longo = df.melt(id_vars=["item", "cliente_raw", "cliente", "origem", "destino", "produto",
                             "microrregiao", "teto", "servico", "categoria", "ferrovia"],
                    value_vars=MESES, var_name="mes_nome", value_name="valor").dropna(subset=["valor"])
    longo["ano"] = ANO
    longo["mes"] = longo["mes_nome"].map({m: i + 1 for i, m in enumerate(MESES)})
    longo["programado"] = longo["mes"] > mes_corrente()
    return df, longo.drop(columns=["mes_nome"])


def agregar(longo):
    chaves = ["item", "cliente", "cliente_raw", "origem", "destino", "produto", "microrregiao", "teto", "ano", "mes"]
    p = (longo.groupby(chaves + ["categoria"], dropna=False)["valor"].sum()
         .unstack("categoria").reset_index())
    for c in ("frete", "dp", "manobra_origem", "manobra_destino", "transbordo", "outros"):
        if c not in p.columns:
            p[c] = 0.0
        p[c] = p[c].fillna(0.0)
    p = p.dropna(subset=["cliente"])
    fer = (longo[longo["categoria"] == "frete"].groupby(["item", "mes"])["ferrovia"]
           .apply(lambda s: "+".join(sorted(set(s)))).rename("ferrovias_frete"))
    p = p.merge(fer, on=["item", "mes"], how="left")
    p["acess"] = p["manobra_origem"] + p["manobra_destino"] + p["transbordo"] + p["outros"]
    p["total"] = p["frete"] + p["dp"] + p["acess"]
    p["base_teto"] = p["frete"] + p["dp"]
    p["pct_teto"] = p["base_teto"] / p["teto"]
    p["ipoa"] = p["acess"].where(p["base_teto"] > 0) / p["base_teto"].where(p["base_teto"] > 0)
    p["programado"] = p["mes"] > mes_corrente()
    return p[p["total"] > 0].copy()


def referencia(im):
    """último mês realizado com frete > 0, por item."""
    real = im[(~im["programado"]) & (im["frete"] > 0)]
    ref = real.sort_values("mes").groupby("item").tail(1).copy()
    mref = int(real["mes"].max())
    ref["mes_ref"] = ref["mes"]
    ref["status"] = ref["mes"].map(lambda m: "atual" if m >= mref - 1 else "sem preço recente")
    # primeira referência do ano para variação jan→ref (mesma regra: frete > 0)
    pri = real.sort_values("mes").groupby("item").head(1).set_index("item")
    for c in ("frete", "dp", "acess", "total", "manobra_origem", "manobra_destino"):
        ref[c + "_ini"] = ref["item"].map(pri[c])
    ref["mes_ini"] = ref["item"].map(pri["mes"])
    return ref, mref


def main():
    if not XLSX.exists():
        print(f"  ! {XLSX.name} não encontrado, pulando.")
        return
    df, longo = carregar()
    im = agregar(longo)
    ref, mref = referencia(im)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for t in (im, ref):
        t["teto_ficha"] = t["item"].map(TETO_FICHA)
        t["teto_fonte"] = t["item"].map(TETO_FONTE)
    longo.to_sql("ficha_fluxo_servico_mes", con, if_exists="replace", index=False)
    im.to_sql("ficha_fluxo_item_mes", con, if_exists="replace", index=False)
    ref.to_sql("ficha_fluxo_ref", con, if_exists="replace", index=False)

    # ---- 3) fluxos_servico: base de pares passa a ser o mês de referência da ficha ----
    itens = sorted(ref["item"].astype(int).unique().tolist())
    ref_mes = dict(zip(ref["item"].astype(int), ref["mes_ref"].astype(int)))
    linhas = longo[longo.apply(lambda r: ref_mes.get(int(r["item"])) == r["mes"], axis=1)]
    antes = cur.execute("SELECT COUNT(*) FROM fluxos_servico").fetchone()[0]
    cur.executemany("DELETE FROM fluxos_servico WHERE itens=?", [(i,) for i in itens])
    cur.executemany(
        """INSERT INTO fluxos_servico (itens, servicos, ferrovia, tarifa, cliente, origem, destino,
                                       produto, microrregiao) VALUES (?,?,?,?,?,?,?,?,?)""",
        [(int(r.item), r.servico, r.ferrovia, float(r.valor), r.cliente_raw, r.origem, r.destino,
          r.produto, None if pd.isna(r.microrregiao) else r.microrregiao) for r in linhas.itertuples()])
    depois = cur.execute("SELECT COUNT(*) FROM fluxos_servico").fetchone()[0]

    # ---- 4) ipoa_teto: valores de 2026 + regra (frete + DP) ----
    cols = [r[1] for r in cur.execute("PRAGMA table_info(ipoa_teto)")]
    for c, t in (("dp", "REAL"), ("fonte_2026", "TEXT"), ("mes_ref_2026", "INTEGER")):
        if c not in cols:
            cur.execute(f"ALTER TABLE ipoa_teto ADD COLUMN {c} {t}")
    rota_info = {}
    for o, d, cor, fer, km in cur.execute(
            "SELECT origem, destino, corredor_vli, ferrovia_fatura, km_rota FROM ipoa_teto"):
        rota_info.setdefault((o, d), (cor, fer, km))
    existentes = {r[0] for r in cur.execute("SELECT DISTINCT item FROM ipoa_teto")}
    n_upd = n_ins = 0
    for r in ref.itertuples():
        it = int(r.item)
        vals = (round(r.frete, 4), round(r.acess + r.dp, 4), round(r.dp, 4), float(r.teto),
                round(r.total, 4), f"ficha 2026 ({MESES[int(r.mes_ref) - 1].lower()}/2026)", int(r.mes_ref))
        if it in existentes:
            cur.execute("""UPDATE ipoa_teto SET frete=?, acessorias=?, dp=?, teto=?, total=?,
                           fonte_2026=?, mes_ref_2026=? WHERE item=?""", vals + (it,))
            n_upd += 1
        else:
            cor, fer, km = rota_info.get((r.origem, r.destino), (None, None, None))
            fer_item = "VLI (" + " + ".join(str(r.ferrovias_frete).split("+")) + ")" if isinstance(r.ferrovias_frete, str) else fer
            cur.execute("""INSERT INTO ipoa_teto (item, cliente, origem, destino, produto, frete, acessorias,
                           dp, teto, total, fonte_2026, mes_ref_2026, ferrovia_fatura, corredor_vli, km_rota)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (it, r.cliente_raw, r.origem, r.destino, r.produto) + vals[:2] + vals[2:7]
                        + (fer_item, cor, km))
            n_ins += 1
    # DP dos itens fora da ficha: o que fluxos_servico tiver (base antiga), senão 0
    dp_fs = dict(cur.execute("""SELECT itens, SUM(tarifa) FROM fluxos_servico
                                WHERE servicos LIKE 'DIREITO DE PASSAGEM%' GROUP BY itens""").fetchall())
    for (it,) in cur.execute("SELECT DISTINCT item FROM ipoa_teto WHERE fonte_2026 IS NULL").fetchall():
        cur.execute("UPDATE ipoa_teto SET dp=? WHERE item=? AND fonte_2026 IS NULL", (dp_fs.get(it, 0.0) or 0.0, it))
    # regra: teto_1 = (frete + DP)/teto ; ipoa = (acessórias - DP)/(frete + DP)
    cur.execute("""UPDATE ipoa_teto SET
                     teto_1 = CASE WHEN teto > 0 THEN (frete + COALESCE(dp,0)) / teto END,
                     ipoa   = CASE WHEN (frete + COALESCE(dp,0)) > 0
                                   THEN (acessorias - COALESCE(dp,0)) / (frete + COALESCE(dp,0)) END""")
    con.commit()
    con.close()
    print(f"  ficha 2026: {len(df)} linhas, {df['item'].nunique()} itens, {df['cliente'].nunique()} clientes; "
          f"referência {MESES[mref - 1].lower()}/{ANO} ({int((ref['status'] == 'atual').sum())} itens atuais).")
    print(f"  fluxos_servico: {antes} -> {depois} linhas ({len(itens)} itens com o mês de referência da ficha).")
    nf = pd.Series(TETO_FONTE).value_counts().to_dict()
    print("  teto da rota inteira, por fonte: " + "; ".join(f"{k}: {v}" for k, v in nf.items()))
    print(f"  ipoa_teto: {n_upd} itens atualizados, {n_ins} inseridos; teto_1 e ipoa recalculados pela regra frete + DP.")


if __name__ == "__main__":
    main()
