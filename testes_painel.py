# -*- coding: utf-8 -*-
"""
LogConsult OS — testes de consistência do banco e do painel compilado.
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Pente-fino nov/2026 (item 6.2 da análise): os guardas numéricos usados para validar os lotes
de julho (KPI × tabela, soma das linhas × total, ganho independente do cliente aberto) tinham
sido escritos e jogados fora duas vezes. Agora rodam a cada `atualizar_tudo.py`.

    python3 testes_painel.py                 # banco + painel compilado
    python3 testes_painel.py --so-banco      # sem o painel (antes do build)

Sai com código 1 se algum teste falhar; avisos não falham.
"""
import json
import pathlib
import re
import sqlite3
import subprocess
import sys
from datetime import date

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
PAINEL = BASE / "Painel_LogconsultOS.html"

# baseline conhecido do audit_volumes.py (nov/2026): ARCELORMITTAL CNTR CHEIO ×2, GERDAU COQUE
# PETROLEO, USIMINAS COQUE PETROLEO/FINO… — casos de rota com mais de um produto parecido que
# o auditor sinaliza mas que já foram revisados. Subir daqui = regressão de volume.
AUDIT_VOLUME_MAX = 5

falhas, avisos = [], []


def ok(cond, msg, aviso=False):
    if not cond:
        (avisos if aviso else falhas).append(msg)
    return cond


def testes_banco():
    con = sqlite3.connect(DB)
    q = lambda s, *a: con.execute(s, a).fetchall()
    cols = [r[1] for r in q("PRAGMA table_info(projeto_fluxo_tarifas)")]

    # 1. tabelas-fonte de preço contratual presentes (conector sem fonte pulava em silêncio)
    fontes = ["gerdau", "ipiranga", "cmoc", "alz", "agrex", "novaagri", "mosaic", "usiminas",
              "arcelormittal", "aperam", "vibra", "raizen", "alesat", "cenibra", "suzano",
              "ldcelulose", "petrobahia", "petronac", "sabba"]
    tabs = {r[0] for r in q("SELECT name FROM sqlite_master WHERE type='table'")}
    for f in fontes:
        ok(f"{f}_precos_contratuais" in tabs, f"tabela-fonte ausente: {f}_precos_contratuais")

    # 2. IPOA = acessórias ÷ frete
    n = q("""SELECT COUNT(*) FROM projeto_fluxo_tarifas WHERE frete>0 AND acessorias IS NOT NULL
             AND ABS(ipoa - acessorias/frete) > 0.0005""")[0][0]
    ok(n == 0, f"{n} fluxo(s) com IPOA gravado ≠ acessórias ÷ frete")

    # 3. vigência: data final ISO ou vazia (um formato, um significado)
    ruins = q("""SELECT cliente, fluxo, vigencia FROM projeto_fluxo_tarifas
                 WHERE vigencia IS NOT NULL AND vigencia NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'""")
    ok(not ruins, f"{len(ruins)} vigência(s) fora do formato AAAA-MM-DD: {ruins[:3]}")

    # 4. nenhuma vigência inicial no futuro nas tabelas mineradas (ex.: '2026' lido como '2028')
    hoje = date.today().isoformat()
    for f in fontes:
        t = f"{f}_precos_contratuais"
        if t not in tabs:
            continue
        for (vi,) in q(f"SELECT vigencia_inicial FROM {t}"):
            m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", str(vi or ""))
            iso = f"{m[3]}-{m[2]}-{m[1]}" if m else str(vi or "")[:10]
            if iso > hoje:
                ok(False, f"{t}: vigência inicial no futuro ({vi})")
                break

    # 5. unidade: contêiner marcado
    ok("unidade" in cols, "coluna `unidade` ausente em projeto_fluxo_tarifas")
    if "unidade" in cols:
        n = q("""SELECT COUNT(*) FROM projeto_fluxo_tarifas
                 WHERE UPPER(fluxo) LIKE 'CNTR %' AND COALESCE(unidade,'') <> 'R$/contêiner'""")[0][0]
        ok(n == 0, f"{n} fluxo(s) de contêiner sem unidade R$/contêiner")

    # 6. abertura fecha com a acessória (±R$0,05)
    dif = q("""SELECT p.cliente, p.fluxo, p.acessorias, ROUND(SUM(a.valor_rs_t),2)
               FROM projeto_fluxo_tarifas p JOIN projeto_acessorias_abertas a
                 ON a.cliente=p.cliente AND a.fluxo=p.fluxo
               GROUP BY p.cliente, p.fluxo
               HAVING ABS(COALESCE(p.acessorias,0) - SUM(a.valor_rs_t)) > 0.05""")
    ok(not dif, f"{len(dif)} fluxo(s) com abertura ≠ acessória: {dif[:3]}")

    # 7. rota duplicada no mesmo cliente (mesma origem/destino/produto, nomes diferentes)
    rot = {}
    for cli, fl in q("SELECT cliente, fluxo FROM projeto_fluxo_tarifas"):
        if "(" in fl:
            continue
        m = re.match(r"^(.+?)\s+([A-Z0-9]{3})\s+([A-Z0-9]{3})$", fl.strip())
        if m:
            rot.setdefault((cli, m[1].upper(), m[2], m[3]), []).append(fl)
    dup = {k: v for k, v in rot.items() if len(v) > 1}
    ok(not dup, f"{len(dup)} rota(s) duplicada(s): {list(dup.items())[:3]}")

    # 8. cliente gravado com nome canônico (não jurídico)
    from canon import canon
    nc = [c for (c,) in q("SELECT DISTINCT cliente FROM projeto_fluxo_tarifas")
          if canon(c.replace(" (retroativo)", "")) != c.replace(" (retroativo)", "")]
    ok(not nc, f"cliente(s) fora do nome canônico: {nc}")

    # 9. auditoria de volume não piorou
    r = subprocess.run([sys.executable, "-c", "import audit_volumes; audit_volumes.audit()"],
                       cwd=BASE, capture_output=True, text=True)
    m = re.search(r"FAIL — (\d+) instancia", r.stdout)
    n = int(m[1]) if m else (0 if "PASS" in r.stdout else -1)
    ok(n >= 0, "audit_volumes.py não rodou: " + (r.stderr[-300:] or r.stdout[-300:]))
    ok(n <= AUDIT_VOLUME_MAX, f"audit_volumes.py: {n} instâncias suspeitas (baseline {AUDIT_VOLUME_MAX})")
    con.close()


def testes_painel():
    if not ok(PAINEL.exists(), "painel compilado não existe — rode build_painel.py"):
        return
    r = subprocess.run(["node", str(BASE / "tests" / "harness_painel.js"), str(PAINEL)],
                       capture_output=True, text=True, timeout=300)
    if not ok(r.returncode == 0 and r.stdout.startswith("{"), "harness não rodou: " + r.stderr[-400:]):
        return
    out = json.loads(r.stdout)
    # ids repetidos no HTML estático: makeTable/getElementById escrevem no PRIMEIRO e a outra
    # tela fica vazia (bug real nov/2026: tCaptura/capKpis em duas abas)
    estatico = re.sub(r"<script[\s\S]*?</script>", "", PAINEL.read_text(encoding="utf-8"))
    ids = re.findall(r'\sid="([^"]+)"', estatico)
    rep = sorted({i for i in ids if ids.count(i) > 1})
    ok(not rep, f"id(s) repetido(s) no HTML: {rep}")
    ok(out["erro_topo"] is None, f"erro de execução no script do painel: {out['erro_topo']}")
    errs = [e for e in out["erros"] if e.startswith("error") or e.startswith("coleta")]
    ok(not errs, f"erros no console do painel: {errs[:3]}")
    ok(not [e for e in out["erros"] if "PC_API ausente" in e], "PC_API ausente — Painel do Cliente não montou")
    d = out["dados"] or {}
    ok(d.get("pc_api"), "window.PC_API não foi criado")
    nv = d.get("novas") or {}
    for k in ("reaj", "venc", "porto", "captura"):
        ok(nv.get(k), f"aba nova sem dado: {k}")
    cli = d.get("clientes") or {}
    ok(len(cli) >= 20, f"só {len(cli)} clientes no Painel do Cliente")
    for c, v in cli.items():
        ok(abs(v["somaFluxos"] - v["mod"]) < 1, f"{c}: soma das linhas ≠ total do card")
        ok(abs(v["repetido"] - v["mod"]) < 1, f"{c}: ganho muda entre duas chamadas (estado vazando)")
        ok(v["naoFinitos"] == 0, f"{c}: {v['naoFinitos']} fluxo(s) com ganho não numérico")
        ok(v["inativosComGanho"] == 0, f"{c}: {v['inativosComGanho']} rota(s) inativa(s) com ganho/ano")
        ok(v["conteinerComGanho"] == 0, f"{c}: fluxo em R$/contêiner multiplicado por tonelada")
    rk = d.get("ranking")
    if ok(rk is not None, "ranking de captura não montou"):
        for r_ in rk:
            g = cli.get(r_["cliente"])
            if g:
                ok(abs((r_["mod"] or 0) - g["mod"]) < 1,
                   f"{r_['cliente']}: ranking ({r_['mod']}) ≠ card do cliente ({g['mod']})")


def main():
    testes_banco()
    if "--so-banco" not in sys.argv:
        testes_painel()
    for a in avisos:
        print("  aviso:", a)
    for f in falhas:
        print("  FALHA:", f)
    print(f"testes: {len(falhas)} falha(s), {len(avisos)} aviso(s)")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
