# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Análises Profundas sobre o Banco (Fase 1)
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Roda o conjunto de análises de maior alavanca comercial sobre logconsult.db e
gera o relatório de achados (Achados_VLI.md). É a camada Hypothesis Generator
rodando em SQL: transforma o P&L da VLI em leitura de consultor.

Tese central: a MARGEM que a VLI faz em cada lane (IND-MRG) é o mapa de onde o
cliente tem espaço para negociar. Margem alta = VLI lucra muito ali = alavanca.

Uso:  python3 analises.py
"""
import sqlite3, pathlib, datetime
import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
OUT = BASE / "Achados_VLI.md"
con = sqlite3.connect(DB)
def q(s): return pd.read_sql_query(s, con)

P24 = "panorama LIKE '2024%'"  # 2024 Real
md = []
def w(x=""): md.append(x)

w("# Achados — Base Interna VLI (P&L por fluxo)")
w()
w(f"**CONFIDENCIAL — USO RESTRITO AOS SÓCIOS** · Gerado em {datetime.datetime.now():%Y-%m-%d %H:%M}")
w()
w("> Lógica proprietária (Hypothesis Generator em SQL). Nunca vai ao cliente — só a conclusão.")
w()

# --- 1. Panorama geral ---
tot = q(f"SELECT SUM(rec_total) rec, SUM(ind_mrg) mrg, SUM(vol_tku) tku FROM vli_pnl WHERE {P24}").iloc[0]
w("## 1. Retrato VLI 2024 (Real)")
w(f"- Receita total: **R$ {tot.rec/1e9:,.2f} bi** · Margem (IND-MRG): **R$ {tot.mrg/1e9:,.2f} bi "
  f"({tot.mrg/tot.rec*100:.0f}%)** · Volume: {tot.tku/1e9:,.1f} bi TKU.")
comp = q(f"""SELECT SUM(rec_fr) fr, SUM(rec_man) man, SUM(rec_sa) sa, SUM(rec_dp) dp,
                   SUM(rec_total) tot FROM vli_pnl WHERE {P24}""").iloc[0]
acc = (comp.man+comp.sa)/comp.tot*100
w(f"- Composição: frete R$ {comp.fr/1e9:,.1f} bi · manobra R$ {comp.man/1e9:,.1f} bi · "
  f"serviços acessórios R$ {comp.sa/1e6:,.0f} mi. **Acessórias/manobra = {acc:.0f}% da receita** "
  f"(pool menos regulado que o frete → alvo de negociação).")
w()

# --- 2. Trajetória de margem nos panoramas (2024→2026) ---
w("## 2. A própria VLI planeja expandir margem (2024 → 2026)")
pan = q("""SELECT panorama, SUM(rec_total) rec, SUM(ind_mrg)*1.0/NULLIF(SUM(rec_total),0) m
           FROM vli_pnl GROUP BY panorama ORDER BY panorama""")
w("| Panorama | Receita | Margem % |")
w("|---|---:|---:|")
for _, r in pan.iterrows():
    w(f"| {r.panorama} | R$ {r.rec/1e9:,.1f} bi | {r.m*100:.0f}% |")
w()
w("> Com receita ~estável, a margem sobe de 66% para ~89% no orçamento 2026 — a VLI embute ganho de "
  "margem. **Cautela metodológica:** a definição de custo pode variar entre panoramas (o orçamento pode "
  "sub-alocar custo); confirmar antes de usar o número de 89% em negociação.")
w()

# --- 3. Margem por corredor ---
w("## 3. Margem por corredor VLI (2024) — onde a VLI mais lucra")
cor = q(f"""SELECT corredor_vli, SUM(rec_total) rec, SUM(ind_mrg)*1.0/NULLIF(SUM(rec_total),0) m
            FROM vli_pnl WHERE {P24} AND corredor_vli IS NOT NULL AND rec_total>0
            GROUP BY corredor_vli ORDER BY rec DESC""")
w("| Corredor | Receita | Margem % | Leitura |")
w("|---|---:|---:|---|")
leitura = {"Centro-Norte":"corredor exportador cativo → alavanca alta",
           "Centro-Leste":"margem intermediária",
           "Centro-Sudeste":"competição rodoviária → pouca folga"}
for _, r in cor.iterrows():
    if r.rec < 10e6: continue
    w(f"| {r.corredor_vli} | R$ {r.rec/1e6:,.0f} mi | {r.m*100:.0f}% | {leitura.get(r.corredor_vli,'—')} |")
w()

# --- 4. Alvos LogConsult: margem que a VLI faz neles ---
w("## 4. Clientes-alvo LogConsult — margem que a VLI faz (2024)")
w("Ordenado por margem %. Margem alta + acessórias altas = maior espaço de renegociação.")
w()
alvos = q(f"""SELECT cliente, SUM(rec_total) rec, SUM(ind_mrg)*1.0/NULLIF(SUM(rec_total),0) m,
                     (SUM(rec_man)+SUM(rec_sa))*1.0/NULLIF(SUM(rec_total),0) acc
              FROM (SELECT cliente, rec_total, ind_mrg,
                           COALESCE(rec_man,0) rec_man, COALESCE(rec_sa,0) rec_sa
                    FROM vli_pnl WHERE {P24}) vli_pnl
              WHERE rec_total>0 AND (
                cliente LIKE '%Mosaic%' OR cliente LIKE '%Selecta%' OR cliente LIKE '%Caramuru%'
                OR cliente LIKE '%Nova Agri%' OR cliente LIKE '%Agrex%' OR cliente LIKE '%Cenibra%'
                OR cliente LIKE '%Cmoc%' OR cliente LIKE '%Vibra%' OR cliente LIKE '%Cargill%'
                OR cliente LIKE '%Bunge%' OR cliente LIKE '%Gerdau%')
              GROUP BY cliente ORDER BY m DESC""")
w("| Cliente | Receita VLI | Margem VLI % | Acessórias % |")
w("|---|---:|---:|---:|")
for _, r in alvos.iterrows():
    w(f"| {r.cliente} | R$ {r.rec/1e6:,.0f} mi | {r.m*100:.0f}% | {r.acc*100:.0f}% |")
w()

# --- 5. Top oportunidades: alta margem + alta receita (fora dos alvos atuais) ---
w("## 5. Radar de originação — alta receita e alta margem (2024)")
w("Clientes onde a VLI fatura muito **e** lucra muito: originação prioritária.")
w()
orig = q(f"""SELECT cliente, SUM(rec_total) rec, SUM(ind_mrg)*1.0/NULLIF(SUM(rec_total),0) m
             FROM vli_pnl WHERE {P24} AND rec_total>0
             GROUP BY cliente HAVING rec>100e6 AND m>0.6
             ORDER BY rec DESC LIMIT 15""")
w("| Cliente | Receita VLI | Margem VLI % |")
w("|---|---:|---:|")
for _, r in orig.iterrows():
    w(f"| {r.cliente} | R$ {r.rec/1e6:,.0f} mi | {r.m*100:.0f}% |")
w()
w("---")
w("*Reproduzir:* `python3 analises.py` · Fonte: `logconsult.db` (tabela `vli_pnl`, panorama 2024 Real).")

OUT.write_text("\n".join(md), encoding="utf-8")
con.close()
print(f"OK -> {OUT.name} ({len(md)} linhas)")
