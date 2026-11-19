# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine: leva a Ficha de Fluxo Geral 2026 ao Painel do Cliente.
CONFIDENCIAL, USO RESTRITO AOS SÓCIOS

Roda dentro de add_projetos_clientes.py, depois de todos os conectores F-LINK e antes de
fix_consistencia_final.py. Lê ficha_fluxo_ref (gravada por add_ficha_fluxo.py).

1. Fluxo que já existe no painel:
   a) se a cobertura cita o item ferroviário ("item 18421", "itens 12950, 39394") e a ficha tem
      esse item com preço atual, o fluxo passa a usar os valores da ficha (mês de referência);
   b) senão, se o nome do fluxo traz a rota ("PRODUTO ORIG DEST") e a ficha tem item atual do
      mesmo cliente nessa rota e produto, usa o de MAIOR tarifa total (regra do sócio de 27/jul:
      mesma rota, uma linha, a maior tarifa);
   c) fluxo sem rota no nome (SELECTA, SELECTA (retroativo), LD CELULOSE) não é tocado.
   Atualiza tarifa, frete, acessórias (com DP, convenção do banco), teto e a abertura
   (projeto_acessorias_abertas daquele fluxo é refeita a partir dos serviços da ficha).
2. Rota da ficha sem fluxo no painel (inclusive os clientes que ainda não tinham painel):
   cria um fluxo por cliente x rota x produto, com o item de maior tarifa total entre os que
   têm preço atual; os demais itens da rota ficam citados na cobertura.

Só entram itens com preço até um mês antes da referência (status "atual").
Uso:  python3 connect_ficha_fluxo.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import re
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
FONTE = "Ficha de Fluxo Geral 2026 (VLI), mês de referência"
_TAG = re.compile(r"\((?:ITEM\s+)?\d{3,6}\)", re.I)
_ITENS_COB = re.compile(r"\bite(?:m|ns)\s+((?:\d{4,6}\s*(?:,|e)?\s*)+)", re.I)


def norm_prod(p):
    s = _TAG.sub(" ", str(p or "")).upper()
    return " ".join(t for t in s.split() if t not in ("DE", "DO", "DA"))


def mesmo_produto(a, b):
    a, b = norm_prod(a), norm_prod(b)
    if a == b:
        return True
    ta, tb = a.split(), b.split()
    if len(ta) != len(tb) or ta[:-1] != tb[:-1]:
        return False
    x, y = sorted((ta[-1], tb[-1]), key=len)
    return len(x) >= 5 and y.startswith(x)


def rota_do_nome(fluxo):
    p = _TAG.sub(" ", str(fluxo)).split()
    if len(p) >= 3 and re.fullmatch(r"[A-Z0-9]{3}", p[-1]) and re.fullmatch(r"[A-Z0-9]{3}", p[-2]):
        return p[-2], p[-1], " ".join(p[:-2])
    return None


def itens_da_cobertura(cob):
    out = []
    for m in _ITENS_COB.finditer(str(cob or "")):
        out += [int(x) for x in re.findall(r"\d{4,6}", m[1])]
    return out


def abertura(cur, item, mes):
    """serviços não-frete do item no mês: manobras/transbordo somados entre ferrovias; DP por ferrovia."""
    linhas = cur.execute("""SELECT servico, ferrovia, SUM(valor) FROM ficha_fluxo_servico_mes
                            WHERE item=? AND mes=? AND categoria<>'frete' GROUP BY servico, ferrovia""",
                         (item, mes)).fetchall()
    ab = {}
    for serv, fer, v in linhas:
        if v is None or v <= 0:
            continue
        nome = f"{serv} {fer}" if serv.startswith("DIREITO DE PASSAGEM") else serv
        ab[nome] = ab.get(nome, 0.0) + v
    return ab


def gravar(cur, cliente, fluxo, r, existe, extra_cob=""):
    (item, frete, dp, acess, total, teto, mes) = r
    rot = f"{MESES[mes - 1]}/2026"
    cob = f"ficha 2026 (item {item}, {rot})" + (f" · {extra_cob}" if extra_cob else "")
    if existe:
        velha = cur.execute("SELECT cobertura FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
                            (cliente, fluxo)).fetchone()[0] or ""
        if velha and not velha.startswith("ficha 2026"):
            cob += " · antes: " + velha[:160]
        cur.execute("""UPDATE projeto_fluxo_tarifas SET tarifa_total=?, frete=?, acessorias=?, teto=?,
                       fonte=?, cobertura=? WHERE cliente=? AND fluxo=?""",
                    (round(total, 2), round(frete, 2), round(acess + dp, 2), round(teto, 2),
                     FONTE, cob, cliente, fluxo))
    else:
        cur.execute("""INSERT INTO projeto_fluxo_tarifas (cliente, fluxo, tarifa_total, teto, frete,
                       acessorias, ipoa, distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (cliente, fluxo, round(total, 2), round(teto, 2), round(frete, 2),
                     round(acess + dp, 2), None, None, None, None, FONTE, cob))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?", (cliente, fluxo))
    for nome, v in abertura(cur, item, mes).items():
        cur.execute("""INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""", (cliente, fluxo, nome, round(v, 2), f"{FONTE} (item {item}, {rot})"))


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    if not cur.execute("SELECT 1 FROM sqlite_master WHERE name='ficha_fluxo_ref'").fetchone():
        print("  ! ficha_fluxo_ref não existe (rode add_ficha_fluxo.py). Pulando.")
        con.close()
        return
    ref = {}
    por_rota = {}
    for (item, cli, o, d, prod, frete, dp, acess, total, teto, mes) in cur.execute(
            """SELECT item, cliente, origem, destino, produto, frete, dp, acess, total, teto, mes_ref
               FROM ficha_fluxo_ref WHERE status='atual'"""):
        r = (int(item), frete, dp, acess, total, teto, int(mes))
        ref[int(item)] = (cli, o, d, prod, r)
        por_rota.setdefault((cli, o, d), []).append((prod, r))

    def melhor_da_rota(cli, o, d, prod):
        cands = [r for p, r in por_rota.get((cli, o, d), []) if mesmo_produto(p, prod)]
        if not cands:
            # prefixo de palavra com UM produto candidato na rota (mesma regra do volume):
            # CMOC "ROCHA EYC IFA" é a "ROCHA FOSF SECA" da ficha. Nunca junta dois produtos.
            alvo = norm_prod(prod)
            prods = {norm_prod(p) for p, _ in por_rota.get((cli, o, d), [])}
            pref = [p for p in prods if p.startswith(alvo + " ") or alvo.startswith(p + " ")]
            if len(pref) == 1:
                cands = [r for p, r in por_rota.get((cli, o, d), []) if norm_prod(p) == pref[0]]
        return sorted(cands, key=lambda r: -r[4]) if cands else []

    n_item = n_rota = n_novo = 0
    cobertas = set()
    pjf = cur.execute("SELECT cliente, fluxo, cobertura FROM projeto_fluxo_tarifas").fetchall()
    for cli_pjf, fluxo, cob in pjf:
        if "(retroativo)" in cli_pjf:
            continue
        cli = cli_pjf
        rota = rota_do_nome(fluxo)
        escolhido, outros = None, []
        its = [i for i in itens_da_cobertura(cob) if i in ref and ref[i][0] == cli]
        if its:
            cand = sorted((ref[i][4] for i in its), key=lambda r: -r[4])
            escolhido, outros = cand[0], cand[1:]
            n_item += 1
        elif rota:
            cand = melhor_da_rota(cli, rota[0], rota[1], rota[2])
            if cand:
                escolhido, outros = cand[0], cand[1:]
                n_rota += 1
        if escolhido:
            extra = ("outros itens atuais na rota: " + ", ".join(f"{r[0]} (R$ {r[4]:.2f})" for r in outros)) if outros else ""
            gravar(cur, cli, fluxo, escolhido, True, extra)
            # a rota e o produto dos itens usados ficam "cobertos": sem isso a etapa seguinte criava
            # um 2º fluxo para a mesma rota quando o nome do produto difere (CMOC "ROCHA" x
            # "ROCHA FOSF SECA", achado na checagem de 19/nov/2026)
            for r in [escolhido] + outros:
                c_, o_, d_, p_, _ = ref[r[0]]
                cobertas.add((c_, o_, d_, norm_prod(p_)))
        if rota:
            for p, r in por_rota.get((cli, rota[0], rota[1]), []):
                if mesmo_produto(p, rota[2]):
                    cobertas.add((cli, rota[0], rota[1], norm_prod(p)))

    # rotas da ficha sem fluxo no painel
    grupos = {}
    for item, (cli, o, d, prod, r) in ref.items():
        grupos.setdefault((cli, o, d, norm_prod(prod)), []).append(r)
    existentes = {(c, f) for c, f, _ in pjf}
    for (cli, o, d, prod), rs in sorted(grupos.items()):
        if (cli, o, d, prod) in cobertas:
            continue
        rs = sorted(rs, key=lambda r: -r[4])
        fluxo = f"{prod} {o} {d}"
        if (cli, fluxo) in existentes:
            continue
        extra = ("outros itens atuais na rota: " + ", ".join(f"{r[0]} (R$ {r[4]:.2f})" for r in rs[1:])) if len(rs) > 1 else ""
        gravar(cur, cli, fluxo, rs[0], False, extra)
        n_novo += 1
    con.commit()
    n_cli = cur.execute("SELECT COUNT(DISTINCT cliente) FROM projeto_fluxo_tarifas").fetchone()[0]
    con.close()
    print(f"  ficha 2026 no Painel do Cliente: {n_item} fluxos atualizados pelo item, {n_rota} pela rota, "
          f"{n_novo} fluxos novos; {n_cli} clientes no painel.")


if __name__ == "__main__":
    main()
