# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Dados de Mercado (CEPEA) no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Insere preços de commodity (CEPEA/ESALQ) em logconsult.db → tabela precos_commodity.
Permite calcular o FRETE COMO % DO VALOR DA CARGA (materialidade real p/ o cliente).

Valores coletados via web (noticiasagricolas, republicando CEPEA/ESALQ) em 2026-07-06.
Atualize a lista PRECOS quando tiver novas cotações (ou automatize a coleta na Fase 2).

Uso:  python3 add_mercado.py
"""
import sqlite3, pathlib
BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

# produto_base (como aparece na base de tarifas) | commodity | praça | kg/saca | R$/saca | data | fonte
PRECOS = [
    ("SOJA",           "Soja",           "Paranaguá (export)", 60, 139.01, "2026-07-06", "CEPEA/ESALQ via NotíciasAgrícolas"),
    ("MILHO",          "Milho",          "ESALQ/B3",           60,  64.00, "2026-07-06", "CEPEA/ESALQ via NotíciasAgrícolas"),
    ("ACUCAR",         "Açúcar cristal", "São Paulo",          50,  91.94, "2026-07-06", "CEPEA/ESALQ via NotíciasAgrícolas"),
    ("FARELO DE SOJA", "Farelo de soja", "Mato Grosso",      1000, 1554.53, "2026-07-06", "IMEA via NotíciasAgrícolas"),
]
# Pendentes (precisam de referência melhor antes de entrar):
#   combustíveis (diesel/gasolina/álcool) — usar preço EX-REFINARIA/distribuição, não revenda ANP (que tem ~45% imposto);
#   fertilizantes — depende do tipo (MAP/KCl/ureia); siderúrgicos (gusa/minério) — cotação específica.

def main():
    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS precos_commodity")
    cur.execute("""CREATE TABLE precos_commodity(
        produto_base TEXT, commodity TEXT, praca TEXT, kg_saca REAL,
        rs_saca REAL, rs_tonelada REAL, data TEXT, fonte TEXT)""")
    for pb, com, praca, kg, rs_sc, data, fonte in PRECOS:
        rs_t = round(rs_sc / (kg/1000.0), 2)   # R$/saca -> R$/tonelada
        cur.execute("INSERT INTO precos_commodity VALUES (?,?,?,?,?,?,?,?)",
                    (pb, com, praca, kg, rs_sc, rs_t, data, fonte))
    con.commit()
    print("precos_commodity:")
    for r in cur.execute("SELECT produto_base, rs_saca, rs_tonelada, praca FROM precos_commodity"):
        print(f"  {r[0]:10} R$ {r[1]:.2f}/sc  ->  R$ {r[2]:,.0f}/t   ({r[3]})")
    con.close()

if __name__ == "__main__":
    main()
