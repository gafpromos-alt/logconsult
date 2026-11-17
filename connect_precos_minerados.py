# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Conector único dos preços contratuais minerados (F-LINK)
dos clientes que tinham conector próprio mas NUNCA foram ligados ao orquestrador.
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Pente-fino lote 4 (nov/2026). Substitui, no pipeline, connect_{vibra,raizen,alesat,cenibra,
suzano,petrobahia,petronac,sabba}_precos.py. Aqueles scripts continuam no disco só como
referência histórica — NÃO chamá-los: todos começam com `DELETE ... WHERE cliente=?`, o que
apaga as rotas que add_demais_clientes_fluxos_completos.py criou para o mesmo cliente (foi
exatamente esse padrão que derrubou a APERAM de 16 para 9 fluxos em jul/2026), e três deles
gravavam o nome jurídico ("ALESAT COMBUSTIVEIS S.A.", "PETROLEO SABBA S.A.") em vez do
canônico.

O que este script faz, por cliente:
  1. Pega a vigência mais recente de cada item ferroviário (datas ISO ou dd/mm/aaaa).
  2. Agrupa os itens por rota+produto ("PRODUTO ORIG DEST", mesmo rótulo do portfólio).
     Quando mais de um item cai na mesma rota:
       - descarta item cuja última vigência é > 180 dias mais velha que a do item mais novo
         (item substituído por outro);
       - dos que sobram, fica UMA rota com a MAIOR tarifa (regra do usuário, 27/jul/2026:
         "considerar 1 rota apenas ... diferença de tarifa menor que 5%. usar a maior
         tarifa"). Se a diferença passar de 5%, a rota continua única (o volume da base é por
         rota, não por item — duas linhas dobrariam o volume) e a divergência fica escrita em
         `cobertura`.
  3. Fluxo já existe em projeto_fluxo_tarifas → UPDATE de tarifa/frete/acessórias/IPOA/
     vigência/fonte/cobertura, PRESERVANDO teto, distância e volume (teto só é preenchido com
     o TR ANTT do F-LINK se estiver vazio). Fluxo não existe → INSERT.
  4. Abertura (projeto_acessorias_abertas): apaga e reinsere só daquele (cliente, fluxo).
  Nenhuma rota do cliente que o F-LINK não cobre é tocada.

LD CELULOSE fica de fora de propósito: o usuário pediu em 19/jul/2026 para "manter o que já
definimos" no fluxo curado dela. O histórico minerado continua disponível para o Rastreador
de reajustes.

Uso:  python3 connect_precos_minerados.py   (ou automático via add_projetos_clientes.py)
"""
import pathlib
import re
import sqlite3
from datetime import date

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MO = ("manobra_origem_rs_t", "MANOBRA ORIGEM")
MD = ("manobra_destino_rs_t", "MANOBRA DESTINO")
DP = ("direito_passagem_rs_t", "DIREITO DE PASSAGEM")
OUTROS_DP = ("outros_rs_t", "DIREITO DE PASSAGEM")   # nas tabelas Vibra/ALE "outros" é o DP
MCC = ("manobra_conexao_cheio_rs_t", "MANOBRA CONEXAO CHEIO")
OSERV = ("outros_servicos_rs_t", "OUTROS SERVICOS")

# (tabela-fonte, cliente canônico — o mesmo que canon.py devolve, componentes da acessória)
CLIENTES = [
    ("vibra_precos_contratuais", "VIBRA", [MO, MD, OUTROS_DP]),
    ("raizen_precos_contratuais", "RAIZEN", [MO, MD, DP]),
    ("alesat_precos_contratuais", "ALE", [MO, MD, OUTROS_DP]),
    ("cenibra_precos_contratuais", "CENIBRA", [MO, MD, MCC, DP, OSERV]),
    ("suzano_precos_contratuais", "SUZANO", [MO, MD, MCC, DP, OSERV]),
    ("petrobahia_precos_contratuais", "PETROBAHIA", [MO, MD, DP]),
    ("petronac_precos_contratuais", "PETRONAC COMBUSTIVEIS", [MO, MD, DP]),
    ("sabba_precos_contratuais", "PETROLEO SABBA", [MO, MD, DP]),
]

DIAS_ITEM_SUBSTITUIDO = 180
TOL_MESMA_ROTA = 0.05


def iso(s):
    """'2026-07-10', '2026-07-10 00:00:00' ou '10/07/2026' -> '2026-07-10' (None se vazio)."""
    if s is None:
        return None
    s = str(s).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return f"{m[3]}-{m[2]}-{m[1]}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)
    return m[0] if m else None


def _dias(a, b):
    return (date.fromisoformat(a) - date.fromisoformat(b)).days


def _tabela_existe(cur, nome):
    return cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                       (nome,)).fetchone() is not None


def conectar_cliente(cur, tabela, cliente, comps):
    cols = [c for c, _ in comps]
    rows = cur.execute(
        f"""SELECT rowid, item_ferroviario, contrato, origem, destino, produto,
                   vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato, frete_rs_t,
                   {', '.join(cols)}
            FROM {tabela}""").fetchall()

    # 1) vigência mais recente por item (empate na data -> a linha inserida por último)
    atual = {}
    for r in rows:
        vi = iso(r[6]) or "0000-00-00"
        chave = (vi, r[0])
        if r[1] not in atual or chave > atual[r[1]][0]:
            atual[r[1]] = (chave, r)

    # 2) agrupa por rota+produto
    por_rota = {}
    for _, r in atual.values():
        fluxo = re.sub(r"\s+", " ", f"{r[5]} {r[3]} {r[4]}".strip().upper())
        por_rota.setdefault(fluxo, []).append(r)

    existentes = {f: (teto,) for f, teto in cur.execute(
        "SELECT fluxo, teto FROM projeto_fluxo_tarifas WHERE cliente=?", (cliente,))}

    n_upd = n_ins = n_pja = 0
    for fluxo, itens in sorted(por_rota.items()):
        mais_nova = max(iso(r[6]) or "0000-00-00" for r in itens)
        vivos = [r for r in itens
                 if _dias(mais_nova, iso(r[6]) or "1900-01-01") <= DIAS_ITEM_SUBSTITUIDO]
        substituidos = [r for r in itens if r not in vivos]
        r = max(vivos, key=lambda x: (x[9] or 0, iso(x[6]) or ""))
        (_, it, contrato, o, d, prod, vi, vf, tr, tarifa, frete, *vals) = r
        acess = round(sum(v or 0 for v in vals), 2)
        ipoa = round(acess / frete, 4) if frete else None

        notas = [f"reajuste a reajuste (item {it}, {contrato}) — vigência {iso(vi)}"]
        outros_vivos = [x for x in vivos if x is not r]
        if outros_vivos:
            dif = max(abs((x[9] or 0) - (tarifa or 0)) / tarifa for x in outros_vivos) if tarifa else 0
            lista = ", ".join(f"{x[1]} (R$ {x[9]:.2f})" for x in outros_vivos)
            notas.append(f"mesma rota em {len(vivos)} itens vigentes ({lista}); usada a maior tarifa"
                         + (f" — ATENÇÃO: diferença de {dif:.0%}, acima de 5%" if dif > TOL_MESMA_ROTA else ""))
        if substituidos:
            notas.append("itens substituídos ignorados: " + ", ".join(str(x[1]) for x in substituidos))
        cobertura = " · ".join(notas)
        fonte = f"F-LINK Preços Contratuais ({tabela}) — vigência mais recente"

        if fluxo in existentes:
            cur.execute(
                """UPDATE projeto_fluxo_tarifas
                   SET tarifa_total=?, frete=?, acessorias=?, ipoa=?, vigencia=?, fonte=?,
                       cobertura=?, teto=COALESCE(teto, ?)
                   WHERE cliente=? AND fluxo=?""",
                (round(tarifa, 2), round(frete, 2) if frete is not None else None, acess, ipoa,
                 iso(vf), fonte, cobertura, round(tr, 2) if tr else None, cliente, fluxo))
            n_upd += 1
        else:
            cur.execute(
                """INSERT INTO projeto_fluxo_tarifas
                   (cliente, fluxo, tarifa_total, teto, frete, acessorias, ipoa,
                    distancia_km, volume_ano_ktu, vigencia, fonte, cobertura)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cliente, fluxo, round(tarifa, 2), round(tr, 2) if tr else None,
                 round(frete, 2) if frete is not None else None, acess, ipoa,
                 None, None, iso(vf), fonte, cobertura))
            n_ins += 1

        cur.execute("DELETE FROM projeto_acessorias_abertas WHERE cliente=? AND fluxo=?",
                    (cliente, fluxo))
        for (_, rotulo), v in zip(comps, vals):
            if v and v > 0:
                cur.execute(
                    """INSERT INTO projeto_acessorias_abertas (cliente, fluxo, item, valor_rs_t, fonte)
                       VALUES (?,?,?,?,?)""",
                    (cliente, fluxo, rotulo, round(v, 2), f"{fonte} (item {it})"))
                n_pja += 1
    return n_upd, n_ins, n_pja


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    for t in ("projeto_fluxo_tarifas", "projeto_acessorias_abertas"):
        if not _tabela_existe(cur, t):
            print(f"  ! {t} não existe — rode add_projetos_clientes.py antes. Pulando.")
            con.close()
            return
    for tabela, cliente, comps in CLIENTES:
        if not _tabela_existe(cur, tabela):
            # Não é mais silencioso: o orquestrador roda o add_ correspondente antes, então
            # a ausência aqui é erro de pipeline, não estado normal.
            print(f"  !! {tabela} AUSENTE — {cliente} ficou sem os preços minerados.")
            continue
        u, i, a = conectar_cliente(cur, tabela, cliente, comps)
        print(f"  {cliente}: {u} fluxos atualizados, {i} novos, {a} itens de abertura "
              f"(fonte {tabela}).")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
