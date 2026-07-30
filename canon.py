# -*- coding: utf-8 -*-
"""
Padronização de nome de cliente → CONTA (grupo econômico), lógica do CRM.
canon(nome) devolve o nome curto do grupo em MAIÚSCULO, agrupando entidades
(ex.: "GERDAU ACOMINAS S/A" e "GERDAU ACOS LONGOS S.A." → "GERDAU").

Regras ordenadas (específico → genérico); a 1ª que casar vence. Colisões
tratadas por ordem: Vale Fertilizantes/Fertigran antes de VALE; ALZ antes de
Amaggi; Selecta antes de CJ; Usiminas casa por 'USIMINAS'/'USINAS SIDERURGICAS'
(não 'USINA'); Petrobahia ≠ Petrobras.
"""
import unicodedata, re

def _norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# (saída, [frases que, se contidas no nome normalizado, casam])
RULES = [
    ("VLI MULTIMODAL", ["VLI MULTIMODAL"]),
    # combustíveis / óleo & gás
    ("BP BUNGE",       ["BP BUNGE"]),
    ("BP BIOENERGY",   ["BP BIOENERGY"]),
    ("PETROBAHIA",     ["PETROBAHIA"]),
    ("PETROBRAS",      ["PETROBRAS", "PETROLEO BRASILEIRO"]),
    ("PETROLEO SABBA", ["PETROLEO SABBA", "SABBA"]),
    ("RAIZEN",         ["RAIZEN"]),
    ("VIBRA",          ["VIBRA"]),
    ("IPIRANGA",       ["IPIRANGA"]),
    ("ALE",            ["ALE COMBUSTIVEIS", "ALESAT"]),
    ("TOTAL",          ["TOTAL COMBUSTIVEIS"]),
    ("TDC",            ["TDC DISTRIBUIDORA"]),
    # trading de grãos / açúcar
    ("ALZ",            ["ALZ", "AMAGGI LOUIS DREYFUS"]),
    ("AMAGGI",         ["AMAGGI", "AGROPECUARIA MAGGI"]),
    ("LDC",            ["LOUIS DREYFUS", "LDC"]),
    ("SELECTA",        ["SELECTA"]),
    ("CJ INTL",        ["CJ INTERNATIONAL"]),
    ("COFCO",          ["COFCO"]),
    ("CARGILL",        ["CARGILL"]),
    ("ADM",            ["ADM"]),
    ("BUNGE",          ["BUNGE"]),
    ("CARAMURU",       ["CARAMURU"]),
    ("CZARNIKOW",      ["CZARNIKOW"]),
    # "Cooperativa de Produtores de Cana, Açúcar e Álcool do Estado de São Paulo" é o nome
    # jurídico/cooperativo histórico da Copersucar (confirmado pelo usuário 28/jul/2026, ao
    # investigar item 10935 ZRP->ISN — mesmo grupo, não cliente diferente).
    ("COPERSUCAR",     ["COPERSUCAR", "COOPERATIVA DE PRODUTORES DE CANA"]),
    ("TEREOS",         ["TEREOS"]),
    ("VITERRA",        ["VITERRA"]),
    ("OLAM",           ["OLAM"]),
    ("ORIGEO",         ["ORIGEO"]),
    ("ENGELHART",      ["ENGELHART"]),
    ("CHS",            ["CHS"]),
    ("AGREX",          ["AGREX"]),
    ("NOVA AGRI",      ["NOVA AGRI", "NOVAAGRI"]),
    ("3 TENTOS",       ["TRES TENTOS", "3 TENTOS"]),
    ("MINAS TRADING",  ["MINAS TRADING"]),
    ("GRANOL",         ["GRANOL"]),
    ("MULTIGRAIN",     ["MULTIGRAIN"]),
    ("NUTRISOYA",      ["NUTRISOYA"]),
    ("HUMBERG",        ["HUMBERG"]),
    ("CUTRALE",        ["CUTRALE"]),
    ("SUCDEN",         ["SUCDEN"]),
    ("ED&F MAN",       ["ED F MAN", "EDF MAN"]),
    # fertilizantes
    ("YARA",           ["YARA"]),
    # Vale Fertilizantes S.A. é o nome legal antigo da Mosaic no Brasil (Vale vendeu a
    # divisão de fertilizantes pra Mosaic em 2018, mesma entidade renomeada) — mesmo grupo,
    # não clientes diferentes. Pedido do usuário (22/jul/2026): unificar como "MOSAIC" único.
    ("MOSAIC",         ["MOSAIC", "VALE FERTILIZANTES"]),
    ("HERINGER",       ["HERINGER"]),
    ("FERT TOCANTINS", ["FERTILIZANTES TOCANTINS"]),
    ("FERTIGRAN",      ["FERTIGRAN", "FERT VALE RIO GRANDE"]),
    ("NUTRIEN",        ["NUTRIEN"]),
    ("FERTIPAR",       ["FERTIPAR"]),
    ("FERTGROW",       ["FERTGROW"]),
    ("GALVANI",        ["GALVANI"]),
    ("OCP",            ["OCP FERTILIZANTE"]),
    ("MACROFERTIL",    ["MACROFERTIL"]),
    ("CIBRAFERTIL",    ["CIBRAFERTIL", "CIBRA FERTIL"]),
    # siderurgia / mineração / metais
    ("GERDAU",         ["GERDAU"]),
    ("ARCELORMITTAL",  ["ARCELORMITTAL"]),
    ("USIMINAS",       ["USIMINAS", "USINAS SIDERURGICAS"]),
    ("APERAM",         ["APERAM"]),
    ("CSN",            ["CSN", "COMPANHIA SIDERURGICA NACIONAL"]),
    ("TERNIUM",        ["TERNIUM"]),
    ("THYSSENKRUPP",   ["THYSSENKRUPP"]),
    ("VALLOUREC",      ["VALLOUREC"]),
    ("FERBASA",        ["FERBASA", "FERRO LIGAS DA BAHIA"]),
    ("MAGNESITA",      ["MAGNESITA"]),
    ("CBA",            ["COMPANHIA BRASILEIRA DE ALUMINIO", "CBA"]),
    ("CBMM",           ["COMPANHIA BRASILEIRA DE METALURGIA"]),
    ("VALE",           ["VALE S A", "VALE SA", "VALE S.A"]),  # Vale (mineração) — após Vale Fert/Fertigran
    ("ANGLO AMERICAN", ["ANGLO AMERICAN"]),
    ("CMOC",           ["CMOC"]),
    ("BURITIRAMA",     ["BURITIRAMA"]),
    ("BAMIN",          ["BAMIN"]),
    ("FERRO GUSA CARAJAS", ["FERRO GUSA CARAJAS"]),
    ("VOTORANTIM",     ["VOTORANTIM"]),
    ("CBF GUSA",       ["CBF INDUSTRIA DE GUSA"]),
    ("VIENA",          ["VIENA"]),
    # celulose / papel / madeira
    ("SUZANO",         ["SUZANO"]),
    ("FIBRIA",         ["FIBRIA"]),
    ("KLABIN",         ["KLABIN"]),
    ("CENIBRA",        ["CENIBRA", "CELULOSE NIPO"]),
    ("LD CELULOSE",    ["LD CELULOSE"]),
    ("ELDORADO",       ["ELDORADO"]),
    # cimento / química
    ("HOLCIM",         ["HOLCIM"]),
    ("INTERCEMENT",    ["INTERCEMENT"]),
    ("CIPLAN",         ["CIPLAN"]),
    ("BRASKEM",        ["BRASKEM"]),
    ("DOW",            ["DOW QUIMICA"]),
    ("DETEN",          ["DETEN"]),
    ("ELEVA",          ["ELEVA QUIMICA"]),
    # proteína / alimentos
    ("JBS",            ["JBS", "SEARA"]),
    ("AMBEV",          ["AMBEV"]),
    # ferrovias / logística (clientes intercompany)
    ("RUMO",           ["RUMO"]),
    ("MRS",            ["MRS LOGISTICA"]),
    ("BRADO",          ["BRADO"]),
    ("FCA",            ["FCA"]),
    ("FNS",            ["FNS", "FERROVIA NORTE SUL"]),
    ("TORA",           ["TORA "]),
]
_COMPILED = [(out, [_norm(p) for p in pats]) for out, pats in RULES]

# tokens de sufixo/descritor jurídico a remover no fallback
_LEGAL = {"S", "A", "SA", "LTDA", "LIMITADA", "EIRELI", "ME", "EPP", "DO", "DE",
          "DA", "E", "BRASIL", "INDUSTRIA", "COMERCIO", "COM", "IND", "INFRA",
          "ESTRUTURA", "ARMAZENAGEM", "ESCOAMEN", "PRODUTOS", "TRADING", "GROUP",
          "LIMITED", "AGRICOLA", "ALIMENTOS", "S/A", "PETROLEO", "AGRONEGOCIO"}

def canon(name):
    if name is None: return name
    n = _norm(name)
    if not n: return str(name)
    padded = " " + n + " "
    for out, pats in _COMPILED:
        if any((" " + p + " ") in padded for p in pats):
            return out
    # fallback: remove sufixos jurídicos e mantém até 3 tokens de conteúdo (MAIÚSCULO)
    toks = [t for t in n.split() if t not in _LEGAL]
    return " ".join(toks[:3]) if toks else n
