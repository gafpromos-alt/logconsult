# -*- coding: utf-8 -*-
"""
audit_volumes.py — auditoria permanente do volume "últimos 12 meses" do Painel do Cliente.

Reproduz em Python, o mais fielmente possível, a mesma cadeia de funções JS do
painel_template.html usada pra exibir o volume "Últimos 12 meses" de cada fluxo
(rota×produto) de um cliente:

    fluxoRota()  -> pcNormFull() -> pcVolLookup()/pcVolIdx() -> pcUlt12Sum()
    volDefaultKt() (fallback de item-colidido, honesto-zero)

... e cruza o resultado ("o que a UI mostra hoje") contra uma referência de
verdade-terrestre PERMISSIVA: soma de TODOS os volume_hist/vli_pnl daquele
cliente×origem×destino (qualquer variante de rótulo de mercadoria), últimos 12
meses reais (mesma âncora — mês mais recente COM DADO, não "hoje").

Serve pra flagar 3 classes de sintoma da MESMA família de bug ("a UI inventa/
empresta um número em vez de honestamente mostrar 0 ou refletir o dado real"):

  (a) FALSO NEGATIVO — UI mostra 0 mas existe volume real >0 pra rota (produto
      pode até não casar por nome, mas a ROTA tem volume de sobra: sinal de
      fragmentação de rótulo ainda não coberta pelos normalizadores atuais).
  (b) EMPRÉSTIMO — 2+ fluxos DISTINTOS do mesmo cliente (rota/produto
      diferentes) mostram o MESMO valor de volume — assinatura clássica de
      fallback que empresta o valor de outro fluxo em vez de calcular o
      próprio.
  (c) FRAGMENTAÇÃO PARCIAL — UI mostra volume bem abaixo (<40%) do total real
      da rota (produto casou, mas só um subconjunto dos rótulos de mercadoria
      entrou no match) — indício de sinônimo/grade/abreviação ainda não
      normalizado.

Rodar standalone:  python3 audit_volumes.py
Saída: relatório PASS/FAIL por fluxo, agrupado por cliente, no stdout.

Convenção desta base (ver comentários em painel_template.html/build_painel.py):
"zero é honesto" — flag (a)/(c) só indica potencial bug quando a diferença é
grande e há dado real de sobra; uma rota genuinamente sem volume_hist/vli_pnl
NÃO é uma falha, é lacuna de dado real (reportada, não "corrigida").
"""
import re
import sqlite3
import sys
from collections import defaultdict

DB = "logconsult.db"

sys.path.insert(0, ".")
from canon import canon  # noqa: E402

# ---------------------------------------------------------------- utilidades

_PROD_SINONIMOS = {"PRO": "PRODUTO"}
_ITEM_RE = re.compile(r"\(ITEM\s+\S+?\)", re.I)
_MERC_GRADE_SUFFIX_RE = re.compile(r"\s*-\s+\S+$")


def pc_norm_prod_token(p):
    """Réplica de pcNormProd() (painel_template.html linha ~2544) — só o 1º
    token (com sinônimo). Usado aqui APENAS pra formar a referência de
    verdade-terrestre "familia de produto" da auditoria (não é usado pelo
    front pra decidir volume exibido — ver aviso no código-fonte sobre não
    reusar pcNormProd nesse caminho)."""
    s = _ITEM_RE.sub("", str(p or "")).strip().upper()
    tok = re.split(r"[ \-]", s)[0] if s else ""
    return _PROD_SINONIMOS.get(tok, tok)


_STOPWORDS = {"DE", "DO", "DA"}


def pc_norm_full(p):
    """Réplica de pcNormFull() (painel_template.html linha ~2552), incluindo
    o fix de conectores isolados DE/DO/DA (24/jul/2026)."""
    s = _ITEM_RE.sub("", str(p or "")).strip().upper()
    parts = s.split()
    if not parts or not parts[0]:
        return s
    parts[0] = _PROD_SINONIMOS.get(parts[0], parts[0])
    return " ".join(t for t in parts if t not in _STOPWORDS)


def merc_base(m):
    """Réplica de _merc_base() (build_painel.py linha ~322) — sufixo de grade."""
    s = _MERC_GRADE_SUFFIX_RE.sub("", str(m or "")).strip()
    return s or str(m or "").strip()


def fluxo_od_produto(fluxo):
    """Réplica de fluxoRota() pro caso multi-token (>=3 tokens): últimos 2
    tokens = origem/destino, resto = produto."""
    toks = _ITEM_RE.sub(" ", str(fluxo or "")).split()
    if len(toks) >= 3:
        dest, orig = toks[-1], toks[-2]
        produto = " ".join(toks[:-2])
        return orig, dest, produto
    return None, None, None


def ult12_sum(anos_map):
    """Réplica de pcUlt12Sum() — âncora no mês mais recente COM DADO, soma
    12 meses pra trás (inclusive), ano/mês em índice linear ano*12+mes."""
    if not anos_map:
        return None
    ancora = -1
    for a, meses in anos_map.items():
        for m in meses:
            idx = a * 12 + m
            if idx > ancora:
                ancora = idx
    if ancora < 0:
        return None
    total = 0.0
    achou = False
    for i in range(12):
        idx = ancora - i
        a = (idx - 1) // 12
        m = idx - a * 12
        v = anos_map.get(a, {}).get(m)
        if v is not None:
            total += v
            achou = True
    return total if achou else None


# ------------------------------------------------------------------ carga DB

def carregar(conn):
    cur = conn.cursor()

    fluxos = cur.execute(
        "SELECT cliente, fluxo, volume_ano_ktu FROM projeto_fluxo_tarifas"
    ).fetchall()

    # volume_hist + vli_pnl, agregados exatamente como build_painel.py monta
    # volmes_produto (fonte do PCVM que pcVolIdx usa no front).
    vh = cur.execute(
        """SELECT cliente, origem, destino, mercadoria, ano, mes, SUM(realizado_ktu)
           FROM volume_hist WHERE realizado_ktu > 0
           GROUP BY cliente, origem, destino, mercadoria, ano, mes"""
    ).fetchall()

    vp = cur.execute(
        """SELECT cliente, origem, destino, mercadoria, ano, mes, SUM(vol_tu)
           FROM vli_pnl
           WHERE modal='Ferrovia' AND (panorama LIKE '%Real%' OR (panorama LIKE '2026%' AND mes<=7))
           GROUP BY cliente, origem, destino, mercadoria, ano, mes HAVING SUM(vol_tu) > 0"""
    ).fetchall()

    # PCVM replica: chave (cli_n,o,d,produto_normalizado_de_grade,ano,mes) -> t (toneladas)
    pcvm = defaultdict(float)
    chaves_vh = set()
    for cli, o, d, merc, ano, mes, ktu in vh:
        cli_n = canon(cli)
        prod = merc_base(merc)
        k = (cli_n, o, d, prod, int(ano), int(mes))
        pcvm[k] += (ktu or 0.0) * 1000.0
        chaves_vh.add((cli_n, o, d, prod, int(ano), int(mes)))
    for cli, o, d, merc, ano, mes, t in vp:
        cli_n = canon(cli)
        prod = merc_base(merc)
        k = (cli_n, o, d, prod, int(ano), int(mes))
        if k not in chaves_vh:  # vli_pnl só preenche o que volume_hist não tem
            pcvm[k] += (t or 0.0)

    # verdade-terrestre PERMISSIVA por (cli_n,o,d,1o-token-do-produto) — junta
    # todos os rótulos de mercadoria que comecem pela MESMA palavra-base
    # (pega grade/sinonimo/abreviacao que os normalizadores atuais ainda nao
    # cobrem), mas SEM misturar produtos genuinamente diferentes da mesma
    # rota (ex. CALCARIO x MINERIO x PELOTAS na mesma rota nao se misturam
    # aqui, exatamente pela mesma razao documentada em painel_template.html
    # sobre nao reusar pcNormProd pra decidir volume exibido -- aqui e so
    # referencia/ground-truth da auditoria, permissiva mas nao cega).
    gt_rota = defaultdict(lambda: defaultdict(dict))  # (cli_n,o,d,token) -> ano -> mes -> total
    for k, t in pcvm.items():
        cli_n, o, d, prod, ano, mes = k
        tok = pc_norm_prod_token(prod)
        gt_rota[(cli_n, o, d, tok)][ano][mes] = gt_rota[(cli_n, o, d, tok)][ano].get(mes, 0.0) + t

    # pcVolIdx replica: (cli_n,o,d) -> produto_normalizado_full -> ano -> mes -> total
    pcvolidx = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    for (cli_n, o, d, prod, ano, mes), t in pcvm.items():
        full = pc_norm_full(prod)
        pcvolidx[(cli_n, o, d)][full][ano][mes] = pcvolidx[(cli_n, o, d)][full][ano].get(mes, 0.0) + t

    return fluxos, pcvolidx, gt_rota


def pc_vol_lookup(pcvolidx, cli_n, o, d, produto):
    nomes = pcvolidx.get((cli_n, o, d))
    if not nomes:
        return None
    full = pc_norm_full(produto)
    if full in nomes:
        return nomes[full]
    cands = [n for n in nomes if n != full and (n.startswith(full) or full.startswith(n))]
    if len(cands) == 1:
        return nomes[cands[0]]
    return None


# --------------------------------------------------------------------- main

def audit():
    conn = sqlite3.connect(DB)
    fluxos, pcvolidx, gt_rota = carregar(conn)

    # agrupa fluxos por cliente canônico
    por_cliente = defaultdict(list)
    for cliente, fluxo, vol_ano_ktu in fluxos:
        por_cliente[canon(cliente)].append((fluxo, vol_ano_ktu))

    resultados = []  # (cliente, fluxo, ui_kt, gt_kt, motivo)
    valores_por_cliente = defaultdict(list)  # cliente -> [(fluxo, ui_kt)] pra checar empréstimo

    # réplica da checagem de "irmãos" de volDefaultKt (fix #4): quando 2+ fluxos
    # do MESMO cliente caem na MESMA rota+produto-normalizado (pcNormFull) mas
    # tem nomes BRUTOS diferentes (evidência de itens de tarifa distintos, ex.
    # sufixo "(ITEM nnnn)"), honesto-zero é o comportamento CORRETO — não um bug.
    grupos_full = defaultdict(set)  # (cli_n,o,d,full) -> {nomes brutos distintos}
    fluxo_info = {}  # fluxo_raw (por cliente) -> (o,d,produto,full)
    for cli_n, flist in por_cliente.items():
        for fluxo, vol_ano_ktu in flist:
            if vol_ano_ktu:
                continue
            o, d, produto = fluxo_od_produto(fluxo)
            if o is None:
                continue
            full = pc_norm_full(produto)
            grupos_full[(cli_n, o, d, full)].add(str(fluxo).strip())
            fluxo_info[(cli_n, fluxo)] = (o, d, produto, full)

    for cli_n, flist in sorted(por_cliente.items()):
        for fluxo, vol_ano_ktu in flist:
            # 1) volume_ano_ktu próprio? (planilha) — não passa pelo matching, sem risco desta
            #    classe de bug; pula da auditoria de matching (mas registra pra checagem de
            #    duplicidade sem sentido não é necessária aqui).
            if vol_ano_ktu:
                continue

            o, d, produto = fluxo_od_produto(fluxo)
            if o is None:
                # fluxo de <3 tokens (nomeado só pelo cliente) — honesto 0 hoje (fix #5).
                resultados.append((cli_n, fluxo, 0.0, None, "sem-rota-propria (honesto 0, OK)"))
                valores_por_cliente[cli_n].append((fluxo, 0.0))
                continue

            full = pc_norm_full(produto)
            irmaos = grupos_full.get((cli_n, o, d, full), set())
            item_ambiguo = len(irmaos) > 1  # mesmo caso do fix #4 -> zero é o comportamento CORRETO

            anos_map = None if item_ambiguo else pc_vol_lookup(pcvolidx, cli_n, o, d, produto)
            ui_soma = ult12_sum(anos_map)
            ui_kt = (ui_soma / 1000.0) if ui_soma is not None else 0.0

            tok = pc_norm_prod_token(produto)
            gt_map = gt_rota.get((cli_n, o, d, tok))
            gt_soma = ult12_sum(gt_map) if gt_map else None
            gt_kt = (gt_soma / 1000.0) if gt_soma is not None else 0.0

            valores_por_cliente[cli_n].append((fluxo, ui_kt))

            motivo = None
            if item_ambiguo:
                pass  # honesto-zero esperado (fix #4) — não é bug
            elif ui_kt == 0.0 and gt_kt > 1.0:
                motivo = f"FALSO-NEGATIVO: UI=0 mas rota/familia-produto tem {gt_kt:.1f}kt reais (produto='{produto}')"
            elif gt_kt > 1.0 and ui_kt > 0 and ui_kt < 0.4 * gt_kt:
                motivo = f"FRAGMENTACAO-PARCIAL: UI={ui_kt:.1f}kt << rota-total={gt_kt:.1f}kt (produto='{produto}')"

            if motivo:
                resultados.append((cli_n, fluxo, ui_kt, gt_kt, motivo))

    # (b) EMPRÉSTIMO: fluxos de rota/produto DIFERENTES com valor IDÊNTICO (>0) no mesmo cliente
    emprestimos = []
    for cli_n, vals in valores_por_cliente.items():
        by_val = defaultdict(list)
        for fluxo, v in vals:
            if v and v > 0:
                by_val[round(v, 3)].append(fluxo)
        for v, fs in by_val.items():
            fs_unicos = sorted(set(fs))
            if len(fs_unicos) >= 2:
                # só é suspeito se as rotas/produtos parseados são DIFERENTES entre si
                ods = {fluxo_od_produto(f) for f in fs_unicos}
                if len(ods) >= 2:
                    emprestimos.append((cli_n, v, fs_unicos))

    # ------------------------------------------------------------ relatório
    print("=" * 100)
    print("AUDITORIA DE VOLUME — ultimos 12 meses (Painel do Cliente)")
    print("=" * 100)
    print(f"Clientes com fluxos em projeto_fluxo_tarifas: {len(por_cliente)}")
    total_fluxos = sum(len(v) for v in por_cliente.values())
    print(f"Total de fluxos auditados: {total_fluxos}")
    print()

    falsos_neg = [r for r in resultados if r[4].startswith("FALSO-NEGATIVO")]
    fragmentos = [r for r in resultados if r[4].startswith("FRAGMENTACAO")]

    print(f"[a] Falsos-negativos (UI=0, dado real existe):     {len(falsos_neg)}")
    print(f"[b] Emprestimos (valor identico entre fluxos dif.): {len(emprestimos)}")
    print(f"[c] Fragmentacao parcial (UI << total da rota):     {len(fragmentos)}")
    print()

    if falsos_neg:
        print("-" * 100)
        print("[a] FALSOS-NEGATIVOS")
        print("-" * 100)
        for cli_n, fluxo, ui, gt, motivo in falsos_neg:
            print(f"  {cli_n:22s} | {fluxo:50s} | {motivo}")

    if emprestimos:
        print("-" * 100)
        print("[b] EMPRESTIMOS (mesmo valor, fluxos de rota/produto diferentes)")
        print("-" * 100)
        for cli_n, v, fs in emprestimos:
            print(f"  {cli_n:22s} | valor={v:.2f}kt | fluxos: {fs}")

    if fragmentos:
        print("-" * 100)
        print("[c] FRAGMENTACAO PARCIAL")
        print("-" * 100)
        for cli_n, fluxo, ui, gt, motivo in fragmentos:
            print(f"  {cli_n:22s} | {fluxo:50s} | {motivo}")

    ok = not falsos_neg and not emprestimos and not fragmentos
    print()
    print("=" * 100)
    print("RESULTADO: " + ("PASS — nenhuma instancia suspeita encontrada." if ok
                            else f"FAIL — {len(falsos_neg)+len(emprestimos)+len(fragmentos)} instancia(s) suspeita(s) acima."))
    print("=" * 100)
    conn.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(audit())
