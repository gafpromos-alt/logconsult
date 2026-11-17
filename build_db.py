# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Construção do Banco Analítico (Fase 1)
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Ingere as bases (VLI interna + tarifas + IPOA + CRM) em um banco SQLite único e
consultável — o "banco de dados" da Fase 1. Migra para PostgreSQL na Fase 2 sem
retrabalho (mesmos nomes de tabela/coluna em snake_case).

Uso:  python3 build_db.py                    (atualiza só as 9 tabelas-base dentro do banco existente)
      python3 build_db.py --substituir-banco  (recria o arquivo do zero — depois rode atualizar_tudo.py)
Saída: logconsult.db  (na mesma pasta)
Normalmente não se roda direto: use `python3 atualizar_tudo.py`.
"""
import sqlite3, unicodedata, re, pathlib, warnings, tempfile, shutil, os, sys
import pandas as pd
warnings.simplefilter("ignore")

BASE = pathlib.Path(__file__).resolve().parent
PROD = BASE.parent
VLI = PROD / "07_Dados VLI"
TAR = PROD / "01_Dados_Tarifas"
DB = BASE / "logconsult.db"
# SQLite não convive bem com pastas sincronizadas (OneDrive) durante a escrita:
# construímos em disco local e copiamos o arquivo pronto para a pasta do projeto.
DB_TMP = pathlib.Path(tempfile.gettempdir()) / "logconsult_build.db"

F_PNL = VLI / "24_25_26.xlsx"   # base unificada: abas 2024/2025/2026, substitui Pasta5.xlsx + o refresh parcial anterior
F_SERV = VLI / "Fluxos Graos - Abertura por  serviço 23-04-2026 (1).xlsx"
F_IPOA = VLI / "IPOA.xlsx"
F_CRM = VLI / "Todos os contatos e contas-2025-10-31-09-52-04.xlsx"
F_VOL = VLI / "BaseHistoricaFerrovia-2013-1-2025-9.xlsx"
F_VOL_PORTOS = VLI / "Historico volume 19_26 portos.xlsx"
F_BOOK = VLI / "2026-VLI_BOOK_Orçamento_20206_V1.35.xlsx"
F_BASE = TAR / "Base dados tarifas e acessorias.xlsx"


def snake(s):
    """Normaliza nome de coluna: sem acento, minúsculo, snake_case."""
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^0-9a-zA-Z]+", "_", s).strip("_").lower()
    return s or "col"


def clean_cols(df):
    df = df.copy()
    df.columns = [snake(c) for c in df.columns]
    # deduplica nomes repetidos
    seen, out = {}, []
    for c in df.columns:
        if c in seen:
            seen[c] += 1; out.append(f"{c}_{seen[c]}")
        else:
            seen[c] = 0; out.append(c)
    df.columns = out
    return df


def load(con, name, df, note=""):
    df = clean_cols(df)
    df.to_sql(name, con, if_exists="replace", index=False)
    print(f"  [{name}] {len(df):>6} linhas × {len(df.columns)} col  {note}")
    return df


def main():
    if DB_TMP.exists():
        DB_TMP.unlink()
    con = sqlite3.connect(DB_TMP)
    print(f"Construindo {DB.name} (em disco local, depois copio) …")

    # 1) P&L interno VLI — fato central (receita/custo/imposto/margem/volume)
    # Base unificada (24_25_26.xlsx, 1 aba por ano) — substitui Pasta5.xlsx (só tinha
    # 2024 com cobertura boa) + a planilha de refresh anterior (2025/2026 com VOL-TU/
    # REC-FR muito incompletos,~15-40% das linhas). Aqui as 3 abas têm cobertura mensal
    # completa e volume por ano bate com a tendência histórica (60-65M t/ano).
    pnl = pd.concat([pd.read_excel(F_PNL, sheet_name=sh) for sh in ["2024","2025","2026"]], ignore_index=True)
    load(con, "vli_pnl", pnl, "P&L VLI por fluxo×mês×panorama (base unificada 24_25_26.xlsx)")

    # 2) Tarifa por serviço (abertura de acessórias) — formato tidy
    serv = pd.read_excel(F_SERV, sheet_name="Servicos")
    load(con, "fluxos_servico", serv, "tarifa por fluxo×serviço")

    # 3) IPOA × teto (fluxo com %ipoa, acessorias, frete, teto, %teto, corredor)
    ipoa = pd.read_excel(F_IPOA, sheet_name="IPOA x teto ")
    load(con, "ipoa_teto", ipoa, "fluxo × teto × corredor VLI")

    # 4) IPOA GERAL — abertura serviço × categoria (frete/acessórias)
    geral = pd.read_excel(F_IPOA, sheet_name="GERAL")
    load(con, "ipoa_geral", geral, "serviço × categoria")

    # 5) Base de tarifas praticadas (base anterior — Módulo A)
    base = pd.read_excel(F_BASE)
    load(con, "tarifas_praticadas", base, "base tarifária anterior")

    # 6) CRM — contatos e contas (cabeçalho na linha 10)
    raw = pd.read_excel(F_CRM, header=10)
    raw = raw.dropna(axis=1, how="all").dropna(how="all")
    # remove eventuais colunas 'unnamed' totalmente vazias já tratado por dropna
    crm = raw[raw.iloc[:, 0].notna() | raw.iloc[:, 1].notna()]
    load(con, "crm_contatos", crm, "contatos CRM (dado pessoal — uso interno)")

    # 7) Volume histórico ferroviário (2013–2025) — cabeçalho na linha 5
    vol = pd.read_excel(F_VOL, sheet_name="BASE HISTÓRICA DE FERROVIAS", header=5)
    vol = vol.dropna(subset=["Ano"])
    load(con, "volume_hist", vol, "volume histórico ferroviário 2013–2025")

    # 7b) Volume histórico de portos (2019–2026) — cabeçalho na linha 5
    volp = pd.read_excel(F_VOL_PORTOS, sheet_name="BASE HISTÓRICA DE PORTOS", header=5)
    volp = volp.dropna(axis=1, how="all").dropna(subset=["Ano"])
    load(con, "volume_hist_portos", volp, "volume histórico portos 2019–2026")

    # 8) Frequência/modelos de trem (BOOK Orçamento 2026) — cabeçalho na linha 3
    frt = pd.read_excel(F_BOOK, sheet_name="VLI Fer. Freq. Trens (2)", header=3)
    frt = frt.dropna(subset=["Corredor"])
    load(con, "freq_trens", frt, "frequência de trens por frota/fluxo")

    # ---- índices para acelerar as análises ----
    cur = con.cursor()
    for tbl, cols in {
        "vli_pnl": ["cliente", "fluxo", "corredor_vli", "ano", "panorama", "mercadoria"],
        "fluxos_servico": ["cliente", "produto"],
        "ipoa_teto": ["cliente", "produto", "corredor_vli"],
    }.items():
        existing = {r[1] for r in cur.execute(f"PRAGMA table_info({tbl})")}
        for c in cols:
            if c in existing:
                cur.execute(f'CREATE INDEX IF NOT EXISTS ix_{tbl}_{c} ON {tbl}("{c}")')
    con.commit()

    # ---- views analíticas (conclusões prontas) ----
    cur.executescript("""
    DROP VIEW IF EXISTS v_margem_cliente;
    CREATE VIEW v_margem_cliente AS
      SELECT cliente,
             SUM(rec_total)          AS receita_total,
             SUM(ind_mrg)            AS margem_total,
             CASE WHEN SUM(rec_total)>0 THEN SUM(ind_mrg)*1.0/SUM(rec_total) END AS margem_pct,
             SUM(vol_tku)            AS tku,
             CASE WHEN SUM(vol_tku)>0 THEN SUM(rec_total)*1.0/SUM(vol_tku) END   AS rs_por_tku,
             SUM(rec_man)+SUM(rec_sa) AS receita_acessorios,
             SUM(rec_fr)             AS receita_frete
      FROM vli_pnl
      WHERE panorama LIKE '2024%'
      GROUP BY cliente;

    DROP VIEW IF EXISTS v_margem_corredor;
    CREATE VIEW v_margem_corredor AS
      SELECT corredor_vli,
             SUM(rec_total) AS receita_total,
             SUM(ind_mrg)   AS margem_total,
             CASE WHEN SUM(rec_total)>0 THEN SUM(ind_mrg)*1.0/SUM(rec_total) END AS margem_pct
      FROM vli_pnl WHERE panorama LIKE '2024%'
      GROUP BY corredor_vli;
    """)
    con.commit()

    # resumo
    print("\nTabelas no banco:")
    nomes = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
    for n in nomes:
        c = cur.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0]
        print(f"  {n:20} {c:>7} linhas")
    print("Views:", [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='view'")])
    con.commit()
    con.close()

    # Pente-fino lote 4 (nov/2026): este script só sabe criar 9 das 53 tabelas do banco. Antes
    # ele APAGAVA o logconsult.db e copiava o novo por cima — rodar para atualizar o extrato da
    # VLI destruía a ferramenta inteira (tetos, preços contratuais, market share, custo
    # logístico, projetos por cliente...). Agora, se o banco já existe, só as tabelas e views
    # que ESTE script cria são substituídas; o resto fica intacto. Recriar do zero só com
    # `--substituir-banco` (e aí rode atualizar_tudo.py para refazer o resto).
    if DB.exists() and "--substituir-banco" not in sys.argv:
        _substituir_so_base(DB_TMP, DB)
    else:
        if DB.exists():
            DB.unlink()
        shutil.copy2(DB_TMP, DB)
    print(f"\nOK -> {DB}  ({os.path.getsize(DB)/1e6:.1f} MB)")


def _substituir_so_base(novo, destino):
    """Troca, dentro de `destino`, só as tabelas/views/índices que existem em `novo`.
    Trabalha numa cópia em disco local (SQLite x OneDrive) e devolve o arquivo pronto."""
    tmp = pathlib.Path(tempfile.gettempdir()) / "logconsult_merge.db"
    shutil.copy2(destino, tmp)
    con = sqlite3.connect(tmp)
    con.execute("ATTACH DATABASE ? AS novo", (str(novo),))
    objs = con.execute("""SELECT type, name, sql FROM novo.sqlite_master
                          WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'""").fetchall()
    for tipo, nome, _ in objs:
        if tipo == "view":
            con.execute(f'DROP VIEW IF EXISTS main."{nome}"')
    for tipo, nome, ddl in objs:
        if tipo == "table":
            con.execute(f'DROP TABLE IF EXISTS main."{nome}"')
            con.execute(ddl)
            con.execute(f'INSERT INTO main."{nome}" SELECT * FROM novo."{nome}"')
            print(f"  substituída: {nome}")
    for tipo, nome, ddl in objs:
        if tipo in ("index", "view"):
            con.execute(ddl.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1)
                        if tipo == "index" else ddl)
    con.commit()
    con.execute("DETACH DATABASE novo")
    con.close()
    shutil.copy2(tmp, destino)
    tmp.unlink()
    print("  (demais tabelas do banco preservadas — rode atualizar_tudo.py para reprocessar)")


if __name__ == "__main__":
    main()
