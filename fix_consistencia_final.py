# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Consistência final de projeto_fluxo_tarifas /
projeto_acessorias_abertas. CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Pente-fino lote 3 (nov/2026). Roda por ÚLTIMO no add_projetos_clientes.py, depois de todo
script que escreve nessas duas tabelas. Idempotente.

1. Duplicatas de rota com nome diferente
   a) CENIBRA: os 3 fluxos da planilha ("TORETE VDD", "TORETE VCS", "CELULOSE VFS vaz") são
      as mesmas rotas que o portfólio grava com rótulo de rota ("TORETES VDD VFS", ...). Além
      de duplicar a rota no painel, a planilha tem o frete de VDD e VCS trocado entre si
      (R$ 6,27 na linha errada: VDD 35,12 em vez de 28,85; tarifa = frete + acessória só
      fecha com os valores trocados de volta). Fica a linha de rota (F-LINK/portfólio), que
      herda o volume da planilha se não tiver nenhum.
   b) Produto truncado na fonte (USIMINAS "CALCARIO BRITAD" × "CALCARIO BRITADO", mesmos
      itens ferroviários): mesma rota, mesmo produto. Fica a linha cuja vigência termina mais
      tarde (no ECE→VIC a do F-LINK venceu em dez/2024 e era 15,7% mais cara); a outra é
      apagada e o que faltar (teto, km, volume, abertura) é herdado.
      Critério estrito para não juntar produtos diferentes: mesmo cliente, mesma origem e
      destino, mesmo número de palavras, todas iguais menos a última, e a última de um é
      prefixo (>= 5 letras) da do outro. "COQUE" × "COQUE PETROLEO" NÃO casa.
2. Vigência num formato e num significado só: `vigencia` = data FINAL em ISO (AAAA-MM-DD) ou
   NULL. As tabelas F-LINK de CMOC/ALZ/AGREX/NOVA AGRI/MOSAIC não têm data final — os
   conectores gravavam a data INICIAL (dd/mm/aaaa) na mesma coluna. Ela vai para a coluna
   nova `vigencia_inicio` e `vigencia` fica NULL (honesto: fim desconhecido). IPIRANGA grava
   a data final em dd/mm/aaaa → convertida.
3. IPOA = acessórias sem DP ÷ (frete + DP) em todas as linhas (regra do sócio, 19/nov/2026;
   antes era acessórias ÷ frete). Coluna dp_rs_t com o DP da abertura.
4. Unidade: os fluxos de contêiner (ARCELORMITTAL "CNTR CHEIO 20 P ...") têm preço em
   R$/contêiner (R$ 1.260 a R$ 4.666) gravado nas mesmas colunas de R$/t. Coluna nova
   `unidade` ('R$/t' ou 'R$/contêiner'); o painel não multiplica R$/contêiner por tonelada
   (ganho = 0 honesto, com aviso) até existir conversão por peso médio do contêiner.
"""
import pathlib
import re
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

CENIBRA_PLANILHA = {
    "TORETE VDD": "TORETES VDD VFS",
    "TORETE VCS": "TORETES VCS VFS",
    "CELULOSE VFS vaz": "CELULOSE VFS VAZ",
}
CLIENTES_VIGENCIA_INICIAL = {"CMOC", "ALZ", "AGREX", "NOVA AGRI", "MOSAIC"}
_ROTA = re.compile(r"^(.+?)\s+([A-Z0-9]{3})\s+([A-Z0-9]{3})$")


def _iso(s):
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", s)
    if m:
        return f"{m[3]}-{m[2]}-{m[1]}"
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    return m[1] if m else None


def _absorver(cur, cliente, fica, sai):
    """Apaga a linha `sai`, herdando para `fica` o que estiver vazio nela."""
    a = cur.execute("SELECT teto, distancia_km, volume_ano_ktu FROM projeto_fluxo_tarifas "
                    "WHERE cliente=? AND fluxo=?", (cliente, sai)).fetchone()
    if a:
        cur.execute("""UPDATE projeto_fluxo_tarifas SET teto=COALESCE(teto,?),
                         distancia_km=COALESCE(distancia_km,?), volume_ano_ktu=COALESCE(volume_ano_ktu,?)
                       WHERE cliente=? AND fluxo=?""", (*a, cliente, fica))
    tem_abertura = cur.execute("SELECT 1 FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                               (cliente, fica)).fetchone()
    # só herda a abertura se ela fecha com a acessória da linha que fica (±R$0,05) — a linha
    # que sai pode ser de uma vigência antiga (USIMINAS CALCARIO ECE→VIC: abertura de 2024
    # somando 17,18 contra acessória vigente de 19,98)
    soma_sai = cur.execute("SELECT SUM(valor_rs_t) FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                           (cliente, sai)).fetchone()[0]
    acess_fica = cur.execute("SELECT acessorias FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?",
                             (cliente, fica)).fetchone()
    fecha = (soma_sai is not None and acess_fica and acess_fica[0] is not None
             and abs(soma_sai - acess_fica[0]) <= 0.05)
    if not tem_abertura and fecha:
        cur.execute("UPDATE projeto_acessorias_abertas SET fluxo=? WHERE cliente=? AND fluxo=?",
                    (fica, cliente, sai))
    cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?", (cliente, sai))
    cur.execute("DELETE FROM projeto_fluxo_tarifas WHERE cliente=? AND fluxo=?", (cliente, sai))


def dedupe(cur):
    n = 0
    existentes = {(c, f) for c, f in cur.execute("SELECT cliente, fluxo FROM projeto_fluxo_tarifas")}
    for velho, novo in CENIBRA_PLANILHA.items():
        if ("CENIBRA", velho) in existentes and ("CENIBRA", novo) in existentes:
            _absorver(cur, "CENIBRA", novo, velho)
            n += 1
            print(f"    CENIBRA: '{velho}' (planilha, frete trocado VDD×VCS) absorvido por '{novo}'")

    linhas = cur.execute("SELECT cliente, fluxo, vigencia, cobertura FROM projeto_fluxo_tarifas").fetchall()
    por_rota = {}
    for cli, fluxo, vig, cob in linhas:
        m = _ROTA.match(fluxo.strip())
        if not m or "(" in fluxo:
            continue
        por_rota.setdefault((cli, m[2], m[3]), []).append((m[1].split(), fluxo, vig, cob))
    for (cli, o, d), fl in por_rota.items():
        apagados = set()
        for i in range(len(fl)):
            for j in range(i + 1, len(fl)):
                (pa, fa, va, ca), (pb, fb, vb, cb) = fl[i], fl[j]
                if fa in apagados or fb in apagados or len(pa) != len(pb) or pa == pb:
                    continue
                if pa[:-1] != pb[:-1]:
                    continue
                ua, ub = pa[-1], pb[-1]
                curto, longo = (ua, ub) if len(ua) < len(ub) else (ub, ua)
                if len(curto) < 5 or not longo.startswith(curto):
                    continue
                # fica a vigência final mais tardia; empate -> a com abertura F-LINK
                ka = (_iso(va) or "", "reajuste a reajuste" in (ca or ""))
                kb = (_iso(vb) or "", "reajuste a reajuste" in (cb or ""))
                fica, sai = (fa, fb) if ka >= kb else (fb, fa)
                _absorver(cur, cli, fica, sai)
                apagados.add(sai)
                n += 1
                print(f"    {cli}: '{sai}' absorvido por '{fica}' (mesma rota, produto truncado na fonte)")
    return n


def vigencias(cur):
    cols = [r[1] for r in cur.execute("PRAGMA table_info(projeto_fluxo_tarifas)")]
    if "vigencia_inicio" not in cols:
        cur.execute("ALTER TABLE projeto_fluxo_tarifas ADD COLUMN vigencia_inicio TEXT")
    n = 0
    for rowid, cli, vig in cur.execute(
            "SELECT rowid, cliente, vigencia FROM projeto_fluxo_tarifas").fetchall():
        if vig is None or str(vig).strip() == "":
            if vig is not None:
                cur.execute("UPDATE projeto_fluxo_tarifas SET vigencia=NULL WHERE rowid=?", (rowid,))
            continue
        iso = _iso(vig)
        ddmm = bool(re.match(r"^\d{2}/\d{2}/\d{4}$", str(vig).strip()))
        if ddmm and cli in CLIENTES_VIGENCIA_INICIAL:
            cur.execute("UPDATE projeto_fluxo_tarifas SET vigencia_inicio=?, vigencia=NULL WHERE rowid=?",
                        (iso, rowid))
            n += 1
        elif iso != vig:
            cur.execute("UPDATE projeto_fluxo_tarifas SET vigencia=? WHERE rowid=?", (iso, rowid))
            n += 1
    return n


def ipoa(cur):
    """Regra do sócio (19/nov/2026): IPOA = acessórias sem DP / (frete + DP).
    `acessorias` no banco soma o DP (fecha com a tarifa); o DP sai da abertura do fluxo.
    Grava também a coluna dp_rs_t, para o painel e os testes usarem o mesmo número."""
    cols = [r[1] for r in cur.execute("PRAGMA table_info(projeto_fluxo_tarifas)")]
    if "dp_rs_t" not in cols:
        cur.execute("ALTER TABLE projeto_fluxo_tarifas ADD COLUMN dp_rs_t REAL")
    cur.execute("""UPDATE projeto_fluxo_tarifas SET dp_rs_t = COALESCE((
                     SELECT SUM(a.valor_rs_t) FROM projeto_acessorias_abertas a
                     WHERE a.cliente = projeto_fluxo_tarifas.cliente AND a.fluxo = projeto_fluxo_tarifas.fluxo
                       AND (UPPER(a.item) LIKE 'DIREITO DE PASSAGEM%' OR UPPER(a.item) LIKE 'DP %')), 0)""")
    cur.execute("""UPDATE projeto_fluxo_tarifas
                   SET ipoa = CASE WHEN (frete + dp_rs_t) > 0 AND acessorias IS NOT NULL
                                   THEN ROUND((acessorias - dp_rs_t) / (frete + dp_rs_t), 4) ELSE NULL END""")
    return cur.rowcount


def unidades(cur):
    cols = [r[1] for r in cur.execute("PRAGMA table_info(projeto_fluxo_tarifas)")]
    if "unidade" not in cols:
        cur.execute("ALTER TABLE projeto_fluxo_tarifas ADD COLUMN unidade TEXT")
    cur.execute("""UPDATE projeto_fluxo_tarifas SET unidade =
                   CASE WHEN UPPER(fluxo) LIKE 'CNTR %' OR UPPER(fluxo) LIKE '%CONTEINER%'
                        THEN 'R$/contêiner' ELSE 'R$/t' END""")
    return cur.execute("SELECT COUNT(*) FROM projeto_fluxo_tarifas WHERE unidade='R$/contêiner'").fetchone()[0]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    print("  consistência final:")
    d = dedupe(cur)
    v = vigencias(cur)
    i = ipoa(cur)
    u = unidades(cur)
    print(f"    {u} fluxo(s) em R$/contêiner marcados.")
    con.commit()
    con.close()
    print(f"    {d} duplicata(s) de rota absorvida(s); {v} vigência(s) normalizada(s); "
          f"IPOA recalculado em {i} linha(s).")


if __name__ == "__main__":
    main()
