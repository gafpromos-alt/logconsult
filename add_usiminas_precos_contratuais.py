#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
add_usiminas_precos_contratuais.py

Cria/recria a tabela `usiminas_precos_contratuais` no banco analitico
(logconsult.db) com o historico de tarifa reajuste-a-reajuste dos fluxos
ferroviarios da USINAS SIDERURGICAS DE MINAS GERAIS S/A (USIMINAS), minerado
dos videos de tela do F-LINK (flink.vli.digital, tela "Preco"), um video por
item ferroviario.

Uma linha por (item ferroviario x vigencia/reajuste).

NAO EXECUTAR automaticamente sem revisao. A conversa principal revisa,
aplica e conecta ao Painel do Cliente (a USIMINAS ainda nao tinha abertura
de manobra origem/destino -> "Ganho Potencial" ficava zerado no painel).

Fonte: F-LINK Preco (IMG_02XX/03XX.MOV) - historico de reajuste USIMINAS.

ATUALIZACAO 24/07/2026: item 8382 (VIC->ECA, PRO SIDERURGICO, ate entao
pendente) adicionado a partir de IMG_0562.MOV (lote IMG_0550-0562.MOV,
"F-LINK Precos Contratuais (videos IMG_0550-0562)"). Alem disso, os itens
19301 e 19299 (COQUE GROSSO VTU->VIC) tiveram manobra_origem/manobra_destino
CORRIGIDOS (estavam trocados por bug de ordem de coluna na transcricao
original) com base em nova confirmacao do item gemeo 39630 em IMG_0561.MOV -
ver notas inline em cada DADOS[...].
"""

import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logconsult.db")
FONTE = "F-LINK Preco (IMG_02XX/03XX.MOV) - historico de reajuste USIMINAS"
FONTE_LOTE_550_562 = "F-LINK Precos Contratuais (videos IMG_0550-0562)"

# ---------------------------------------------------------------------------
# Metadados de cada fluxo (confirmados no cabecalho de cada video)
# item, contrato, origem, origem_nome, destino, destino_nome, produto, video
# ---------------------------------------------------------------------------
FLUXOS = {
    40761: dict(contrato="C_2025_53", origem="VFU", origem_nome="FUNIL",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0248.MOV"),
    18814: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE GROSSO", video="IMG_0249.MOV"),
    8397: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="ECE", destino_nome="CAPITAO EDUARDO",
               produto="PRO SIDERURGICO", video="IMG_0250.MOV"),
    12950: dict(contrato="C_2025_53", origem="EBI", origem_nome="BATISTA ALMEIDA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="CALCARIO BRITADO", video="IMG_0251.MOV"),
    # NOTA: IMG_0252.MOV e IMG_0279.MOV mostram o MESMO item 12950 (mesmo
    # cabecalho, mesmos dados) - videos duplicados, nao geraram FLUXOS/DADOS
    # separados.
    39843: dict(contrato="C_2025_54", origem="ECE", origem_nome="CAPITAO EDUARDO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0253.MOV"),
    41130: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE FINO", video="IMG_0254.MOV"),
    40276: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VTU", destino_nome="TUBARAO",
                produto="PRO SIDERURGICO", video="IMG_0255.MOV"),
    10414: dict(contrato="C_2025_53", origem="VPN", origem_nome="PEDRO NOLASCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="ANTRACITO", video="IMG_0256.MOV"),
    39558: dict(contrato="C_2025_53", origem="VPN", origem_nome="PEDRO NOLASCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0257.MOV"),
    40115: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="EHF", destino_nome="HORTO FLORESTAL",
                produto="PRO SIDERURGICO", video="IMG_0258.MOV"),
    # NOTA: IMG_0259.MOV mostra o MESMO item 40115 (video duplicado).
    39379: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VPN", destino_nome="PEDRO NOLASCO",
                produto="PRO SIDERURGICO", video="IMG_0260.MOV"),
    7924: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
               destino="VIC", destino_nome="INTENDENTE CAMARA",
               produto="COQUE GROSSO", video="IMG_0261.MOV"),
    9912: dict(contrato="C_2025_53", origem="ENG", origem_nome="NOVA GRANJA",
               destino="VIC", destino_nome="INTENDENTE CAMARA",
               produto="CALCARIO BRITADO", video="IMG_0262.MOV"),
    19842: dict(contrato="C_2025_53", origem="ECE", origem_nome="CAPITAO EDUARDO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0263.MOV"),
    39950: dict(contrato="C_2025_53", origem="ESQ", origem_nome="SILVA OLIVEIRA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0265.MOV"),
    40052: dict(contrato="C_2025_53", origem="ELD", origem_nome="DR. LUND",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0266.MOV"),
    39402: dict(contrato="C_2025_53", origem="VOB", origem_nome="OURO BRANCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0267.MOV"),
    14780: dict(contrato="C_2025_53", origem="VWI", origem_nome="PEDREIRA DO RIO DAS VELHAS",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0268.MOV"),
    14785: dict(contrato="C_2025_53", origem="EBI", origem_nome="BATISTA ALMEIDA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0269.MOV"),
    # NOTA: IMG_0270.MOV mostra o MESMO item 14785 (video duplicado, mais
    # longo - usado para complementar o historico, ver DADOS[14785]).
    # NOTA: IMG_0271.MOV mostra o MESMO item 40276 do IMG_0255.MOV (dup).
    # NOTA: IMG_0272.MOV mostra o MESMO item 39843 do IMG_0253.MOV (dup).
    18243: dict(contrato="C_2025_53", origem="EWD", origem_nome="PAULO MENICUCCI",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE PETROLEO", video="IMG_0273.MOV"),
    40283: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VPN", destino_nome="PEDRO NOLASCO",
                produto="PRO SIDERURGICO", video="IMG_0274.MOV"),
    # NOTA: IMG_0275.MOV mostra o MESMO item 40283 do IMG_0274.MOV (dup).
    # NOTA: IMG_0276.MOV e IMG_0277.MOV mostram o MESMO item 40761 do
    # IMG_0248.MOV (tela rotula "40763", mas os dados batem 100% - ver nota
    # em DADOS[40761]).
    8391: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="EYU", destino_nome="EMBIRUCU",
               produto="PRO SIDERURGICO", video="IMG_0278.MOV"),
    # NOTA: IMG_0279.MOV, IMG_0280.MOV e IMG_0281.MOV mostram o MESMO item
    # 12950/39379 (duplicados, ver notas em DADOS[12950]/DADOS[39379]).
    39552: dict(contrato="C_2025_53", origem="VFU", origem_nome="FUNIL",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="CALCARIO BRITADO", video="IMG_0282.MOV"),
    19260: dict(contrato="C_2025_53", origem="VOB", origem_nome="OURO BRANCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE GROSSO", video="IMG_0283.MOV"),
    39929: dict(contrato="C_2025_54", origem="EHF", origem_nome="HORTO FLORESTAL",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0284.MOV"),
    # NOTA: IMG_0285.MOV mostra o MESMO item 19260 do IMG_0283.MOV (dup,
    # complementou historico - ver DADOS[19260]).
    # NOTA: IMG_0286.MOV mostra o MESMO item 39558 do IMG_0257.MOV (dup).
    15802: dict(contrato="C_2025_54", origem="VMR", origem_nome="MARIO CARVALHO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0287.MOV"),
    # NOTA: IMG_0288.MOV mostra o MESMO item 15802 do IMG_0287.MOV (dup).
    8388: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="EYB", destino_nome="COUTO E SILVA",
               produto="PRO SIDERURGICO", video="IMG_0289.MOV"),
    8342: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="VEB", destino_nome="ENG. LAF. BANDEIRA",
               produto="PRO SIDERURGICO", video="IMG_0290.MOV"),
    15533: dict(contrato="C_2025_54", origem="EEL", origem_nome="ELDORADO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0291.MOV"),
    8478: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="ECE", destino_nome="CAPITAO EDUARDO",
               produto="PRO SIDERURGICO", video="IMG_0292.MOV"),
    7917: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
               destino="VIC", destino_nome="INTENDENTE CAMARA",
               produto="ANTRACITO", video="IMG_0293.MOV"),
    14791: dict(contrato="C_2025_53", origem="EWD", origem_nome="PAULO MENICUCCI",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0294.MOV"),
    # NOTA: IMG_0295.MOV mostra o MESMO item 14791 do IMG_0294.MOV (dup).
    40765: dict(contrato="C_2025_53", origem="ENG", origem_nome="NOVA GRANJA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0296.MOV"),
    40287: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VEB", destino_nome="ENG. LAF. BANDEIRA",
                produto="PRO SIDERURGICO", video="IMG_0297.MOV"),
    7901: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="VTU", destino_nome="TUBARAO",
               produto="PRO SIDERURGICO", video="IMG_0298.MOV"),
    40288: dict(contrato="C_2025_54", origem="VEB", origem_nome="ENG. LAF. BANDEIRA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0299.MOV"),
    40050: dict(contrato="C_2025_53", origem="ELD", origem_nome="DR. LUND",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0300.MOV"),
    11896: dict(contrato="C_2025_54", origem="VOB", origem_nome="OURO BRANCO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0301.MOV"),
    40190: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VEB", destino_nome="ENG. LAF. BANDEIRA",
                produto="PRO SIDERURGICO", video="IMG_0302.MOV"),
    18241: dict(contrato="C_2025_53", origem="VAB", origem_nome="AROABA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="CARVAO MINERAL", video="IMG_0303.MOV"),
    15804: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VMR", destino_nome="MARIO CARVALHO",
                produto="PRO SIDERURGICO", video="IMG_0304.MOV"),
    39394: dict(contrato="C_2025_53", origem="ECE", origem_nome="CAPITAO EDUARDO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="CALCARIO BRITADO", video="IMG_0305.MOV"),
    14783: dict(contrato="C_2025_53", origem="EPM", origem_nome="PRUDENTE DE MORAIS",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0306.MOV"),
    40270: dict(contrato="C_2025_53", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="EYU", destino_nome="EMBIRUCU",
                produto="PRO SIDERURGICO", video="IMG_0307.MOV"),
    40264: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="ECE", destino_nome="CAPITAO EDUARDO",
                produto="PRO SIDERURGICO", video="IMG_0308.MOV"),
    # NOTA: IMG_0309.MOV mostra o MESMO item 41130 do IMG_0254.MOV (dup).
    40188: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VEB", destino_nome="ENG. LAF. BANDEIRA",
                produto="PRO SIDERURGICO", video="IMG_0310.MOV"),
    40291: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="EEL", destino_nome="ELDORADO",
                produto="PRO SIDERURGICO", video="IMG_0311.MOV"),
    39808: dict(contrato="C_2025_53", origem="VTB", origem_nome="BARAO DE COCAIS",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0312.MOV"),
    15535: dict(contrato="C_2025_54", origem="EPI", origem_nome="PARQUE INDUSTRIAL",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0313.MOV"),
    10305: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE GROSSO", video="IMG_0314.MOV"),
    39630: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE GROSSO", video="IMG_0316.MOV"),
    40767: dict(contrato="C_2025_53", origem="ENG", origem_nome="NOVA GRANJA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0317.MOV"),
    # NOTA: IMG_0319.MOV mostra o MESMO item 19842 do IMG_0263.MOV (dup).
    40281: dict(contrato="C_2025_54", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0320.MOV"),
    40302: dict(contrato="C_2025_54", origem="ECE", origem_nome="CAPITAO EDUARDO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0321.MOV"),
    40272: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="EYB", destino_nome="COUTO E SILVA",
                produto="PRO SIDERURGICO", video="IMG_0322.MOV"),
    40285: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VEB", destino_nome="ENG. LAF. BANDEIRA",
                produto="PRO SIDERURGICO", video="IMG_0323.MOV"),
    40278: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
                destino="VTU", destino_nome="TUBARAO",
                produto="PRO SIDERURGICO", video="IMG_0324.MOV"),
    39952: dict(contrato="C_2025_53", origem="ESQ", origem_nome="SILVA OLIVEIRA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0325.MOV"),
    # NOTA: IMG_0327.MOV mostra o MESMO item 18814 do IMG_0249.MOV (dup,
    # confirmou o historico ja capturado, sem linhas novas - video nao
    # chegou mais para tras que 20/04/2024, mesmo gap ja documentado).
    # NOTA: IMG_0328.MOV e IMG_0329.MOV mostram o MESMO item 40761 do
    # IMG_0248.MOV/IMG_0276.MOV/IMG_0277.MOV (dup, 3o e 4o video repetido) -
    # confirmaram as 13 linhas ja existentes, sem novidade.
    # NOTA: IMG_0336.MOV mostra o MESMO item 40052 do IMG_0266.MOV (dup) -
    # confirmou as linhas ja capturadas, sem linhas novas.
    14789: dict(contrato="C_2025_53", origem="VWI", origem_nome="PEDREIRA DO RIO DAS VELHAS",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0330.MOV"),
    39900: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="CARVAO MINERAL", video="IMG_0331.MOV"),
    19301: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE GROSSO", video="IMG_0332.MOV"),
    # NOTA: IMG_0333.MOV mostra o MESMO item 19301 do IMG_0332.MOV (dup),
    # confirma o cabecalho, nao revisado item a item (dados ja completos
    # vieram do IMG_0332.MOV).
    39554: dict(contrato="C_2025_53", origem="VMR", origem_nome="MARIO CARVALHO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="MINERIO FERRO", video="IMG_0334.MOV"),
    10019: dict(contrato="C_2025_53", origem="EPI", origem_nome="PARQUE INDUSTRIAL",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="SUCATA", video="IMG_0335.MOV"),
    19299: dict(contrato="C_2025_53", origem="VTU", origem_nome="TUBARAO",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="COQUE GROSSO", video="IMG_0337.MOV"),
    40304: dict(contrato="C_2025_54", origem="ECE", origem_nome="CAPITAO EDUARDO FCA",
                destino="VIC", destino_nome="INTENDENTE CAMARA",
                produto="PRO SIDERURGICO", video="IMG_0338.MOV"),
    # --- lote IMG_0550-0562.MOV (24/07/2026): fluxos pendentes USIMINAS/
    # ARCELORMITTAL/GERDAU (manobras "sem abertura") ---
    8382: dict(contrato="C_2025_54", origem="VIC", origem_nome="INTENDENTE CAMARA",
               destino="ECA", destino_nome="CARREIRA COMPRIDA",
               produto="PRO SIDERURGICO", video="IMG_0562.MOV"),
}

# ---------------------------------------------------------------------------
# Dados por fluxo. Cada tupla:
#   (vigencia_inicial, vigencia_final, valor_tr_antt, tarifa_contrato,
#    frete, manobra_origem, manobra_destino)
# Datas em YYYY-MM-DD. Valores em R$/t. Use None se um servico nao existir.
# Preenchido incrementalmente a partir da leitura dos frames dos videos.
# Mais recente primeiro.
# ---------------------------------------------------------------------------

DADOS = {}

# --- 40761 | C_2025_53 | VFU->VIC | MINERIO FERRO | IMG_0248.MOV ---
# 24s, item unico ferrovia EFVM. Manobra praticamente constante MO=29,09/
# 29,49(raro) MD=7,88-7,98(varia pouco por reajuste). 12 vigencias cobrindo
# todo o contrato (01/01/2025 a 31/12/2027), da vigencia inicial 01/01/2025
# ate a mais recente 20/06/2026. Tabela lida integralmente (video terminou
# no fim do scroll, confirmado por 2 frames identicos no final).
# IMG_0276.MOV e um video DUPLICADO do mesmo item (a tela mostrou o numero
# "40763", mas todos os 13 valores de vigencia/tarifa/frete/MO/MD conferem
# EXATAMENTE com 40761 -> tratado como o mesmo item, provavel erro de
# digito na leitura de um dos dois videos; ver relatorio). Confirmou todas
# as linhas e acrescentou um 3o cadastro para a vigencia 20/12/2025 (mesma
# tarifa 73,66, split diferente: frete 36,37/MO 29,09/MD 8,20).
# IMG_0277.MOV e um TERCEIRO video do mesmo item (tambem rotulado "40763"
# na tela) - confirma tudo, nenhuma linha nova.
DADOS[40761] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 38.08, 73.12, 36.13, 29.09, 7.90),
    ("2026-05-20", "2027-12-31", 38.08, 73.27, 36.28, 29.09, 7.90),
    ("2026-05-20", "2027-12-31", 38.08, 73.27, 36.28, 29.09, 7.90),  # 2o cadastro (11:10:33)
    ("2026-04-20", "2027-12-31", 38.08, 73.33, 36.34, 29.09, 7.90),
    ("2026-03-20", "2027-12-31", 38.08, 73.65, 36.66, 29.09, 7.90),
    ("2026-02-20", "2027-12-31", 38.08, 73.86, 36.87, 29.09, 7.90),
    ("2026-02-20", "2027-12-31", 38.08, 74.15, 36.68, 29.49, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 38.08, 73.70, 36.38, 29.42, 7.90),
    ("2025-12-20", "2027-12-31", 38.38, 73.37, 36.38, 29.09, 7.90),
    ("2025-12-20", "2027-12-31", 38.38, 73.66, 36.38, 29.38, 7.90),  # 2o cadastro (12/12/2025)
    ("2025-12-20", "2027-12-31", 38.38, 73.66, 36.37, 29.09, 8.20),  # 3o cadastro (confirmado por IMG_0276.MOV)
    ("2025-11-20", "2027-12-31", 36.38, 73.18, 36.17, 29.09, 7.90),  # soma 73,16 vs tarifa 73,18 (dif 0,02)
    ("2025-10-20", "2027-12-31", 36.38, 73.21, 36.22, 29.11, 7.88),
    ("2025-01-01", "2027-12-31", 36.38, 73.53, 36.38, 29.24, 7.91),
]

# --- 18814 | C_2025_53 | VTU->VIC | COQUE GROSSO | IMG_0249.MOV ---
# 36,6s, ferrovia EFVM. PADRAO DE MANOBRA MUDA no tempo: MO=14,85/MD=8,00
# (constante) em 2025-2026 ate vig 20/09/2025 (1o cadastro); a partir de um
# re-cadastro em 19/09/2025 o split vira MO=11,95/MD=11,95 (igual) e assim
# permanece ate abril/2024 (inicio dos frames capturados). Varios re-cadastros
# com MESMA tarifa mas split diferente (mantidos como 1o/2o cadastro). Duas
# linhas com vigencia curta (20/04-30/04/2025 e 20/02-19/03/2025) coexistem
# com uma vigencia longa (01/05/2025-31/12/2027) de mesmo valor - mantidas
# como estao na tela. Video (36,6s) cobre da vigencia mais recente
# (20/06/2026) ate aprox. 20/04/2024; 2 linhas (30/12/2024 e 19/12/2024,
# vig_fim 28/02/2025 e 31/12/2024 respectivamente) tiveram Vigencia Inicial
# ilegivel no frame disponivel -> OMITIDAS (nao adivinhado). Vigencias
# anteriores a 20/04/2024 (ate o inicio do contrato 20/07/2023) nao apareceram
# nos frames extraidos (video pode ter terminado antes de chegar la) -> gap.
DADOS[18814] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 113.99, 91.14, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 97.59, 114.23, 91.38, 14.85, 8.00),
    ("2026-04-20", "2027-12-31", 97.59, 114.33, 91.48, 14.85, 8.00),
    ("2026-03-20", "2027-12-31", 97.59, 114.83, 91.98, 14.85, 8.00),
    ("2026-02-20", "2027-12-31", 97.59, 115.16, 92.31, 14.85, 8.00),
    ("2026-02-20", "2027-12-31", 97.59, 117.00, 93.94, 14.99, 8.07),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 97.59, 114.91, 92.06, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 114.39, 91.54, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 116.21, 92.41, 14.85, 8.95),  # 2o cadastro (12/12/2025) - confirmado c/ zoom
    ("2025-11-20", "2027-12-31", 93.23, 114.07, 91.22, 14.85, 8.00),
    ("2025-10-20", "2027-12-31", 93.23, 114.14, 91.29, 14.85, 8.00),
    ("2025-09-20", "2027-12-31", 93.23, 114.13, 91.28, 14.85, 8.00),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 93.23, 114.13, 90.23, 11.95, 11.95),  # 2o cadastro (rebalanceio manobra, 19/09/2025)
    ("2025-08-20", "2027-12-31", 93.23, 113.71, 89.81, 11.95, 11.95),
    ("2025-07-20", "2027-12-31", 93.23, 113.60, 89.70, 11.95, 11.95),
    ("2025-06-20", "2027-12-31", 93.23, 113.67, 89.77, 11.95, 11.95),
    ("2025-05-20", "2027-12-31", 93.23, 114.62, 90.72, 11.95, 11.95),
    ("2025-05-01", "2027-12-31", 93.23, 116.41, 92.51, 11.95, 11.95),
    ("2025-04-20", "2025-04-30", 93.23, 116.41, 92.51, 11.95, 11.95),
    ("2025-03-20", "2025-04-30", 93.23, 116.59, 92.69, 11.95, 11.95),
    ("2025-02-20", "2025-03-19", 93.23, 116.15, 92.25, 11.95, 11.95),
    ("2025-04-01", "2025-04-30", 93.23, 116.01, 92.11, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.23, 116.01, 92.11, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.23, 115.95, 92.05, 11.95, 11.95),  # 2o cadastro
    ("2024-11-20", "2024-12-31", 88.99, 115.28, 88.98, 13.14, 13.14),  # soma 115,26 vs tarifa 115,28 (dif 0,02)
    ("2024-10-20", "2024-12-31", 88.99, 114.76, 88.98, 12.89, 12.89),
    ("2024-09-20", "2024-12-31", 88.99, 114.51, 88.97, 12.77, 12.77),
    ("2024-08-20", "2024-12-31", 88.99, 114.53, 88.97, 12.78, 12.78),
    ("2024-07-20", "2024-12-31", 88.99, 114.78, 88.78, 13.00, 13.00),  # soma 114,78 vs tarifa 114,76 (dif 0,02)
    ("2024-06-20", "2024-12-31", 88.99, 114.20, 88.70, 12.75, 12.75),
    ("2024-05-20", "2024-12-31", 88.99, 114.31, 88.81, 12.75, 12.75),
    ("2024-04-20", "2024-12-31", 88.99, 114.19, 88.69, 12.75, 12.75),
]

# --- 8397 | C_2025_54 | VIC->ECE | PRO SIDERURGICO | IMG_0250.MOV ---
# INTERMODAL EFVM+FCA, video de 65,8s (o mais longo do lote), ESTRUTURA COM
# 5 LINHAS DE SERVICO (nao 3-4 como o resto): TRANSBORDO DESTINO (FCA) +
# FRETE (EFVM) + FRETE (FCA) + MANOBRA ORIGEM (EFVM) + MANOBRA DESTINO (FCA).
# frete_rs_t aqui = TRANSBORDO DESTINO + FRETE EFVM + FRETE FCA (dobra o
# transbordo dentro do "frete" para poder usar a mesma formula de validacao
# frete+MO+MD=tarifa). manobra_origem = MANOBRA ORIGEM EFVM (CONSTANTE em
# quase todo o historico: 8,99 em 2025-2026, 13,25 em 2023-2025). manobra_
# destino = MANOBRA DESTINO FCA (19,73/19,74 em 2025-2026; 8,26 em 2023-2025).
# A transicao MO 13,25/MD 8,26 -> MO 8,99/MD 19,73 acontece por volta de
# 20/05/2025-20/09/2025 (varios re-cadastros na mesma janela, ver abaixo).
# Alguns re-cadastros tem o FRETE quase todo alocado para FCA em vez de EFVM
# (ex. 07/08/2024, 18/06/2024) - mantido como lido, a soma valida.
# Vigencia do contrato no cabecalho: 19/05/2011 a 31/12/2027 (contrato antigo,
# mas os precos capturados vao de 20/12/2023 ate 20/06/2026 - o video nao
# chegou nem precisou chegar mais para tras: ultimo frame (t=64,5s de 65,8s)
# ja mostra o fim do scroll).
# vig_ini=2025-09-20 teve MUITOS re-cadastros com a MESMA tarifa (63,21) mas
# splits diferentes; um deles (07/10/2025 15:06:22, MO=0,00) parece anomalia
# de digitacao e foi OMITIDO. Mantidas as duas variantes mais consistentes
# (1o cadastro 19/09/2025: MO=13,25/MD=8,26; 2o cadastro 07/10/2025:
# MO=8,99/MD=19,73 - a mesma transicao de padrao vista no resto do historico).
# Linha 2025-05-20 (1o cadastro, 19/05/2025 23:47:35): FRETE FCA lido como
# 8,99 (destoante do padrao ~1,0-1,5 do resto) e FRETE EFVM DERIVADO por
# diferenca (tarifa - demais componentes) por estar borrado no frame -> baixa
# confianca nesta linha especifica, mantida pois a soma fecha exatamente.
DADOS[8397] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 50.49, 63.15, 34.43, 8.99, 19.73),
    ("2026-05-20", "2027-12-31", 50.49, 63.28, 34.56, 8.99, 19.73),
    ("2026-04-20", "2027-12-31", 50.49, 63.33, 34.61, 8.99, 19.73),
    ("2026-03-20", "2027-12-31", 50.49, 63.60, 34.88, 8.99, 19.73),
    ("2026-02-20", "2027-12-31", 50.49, 63.78, 35.06, 8.99, 19.73),
    ("2026-01-20", "2027-12-31", 50.49, 63.64, 34.92, 8.99, 19.73),
    ("2026-01-01", "2026-01-19", 50.49, 63.56, 34.84, 8.99, 19.73),  # vig curta (re-cadastro 28/04/2026)
    ("2025-09-20", "2027-12-31", 48.24, 63.21, 34.48, 8.99, 19.74),  # 2o cadastro (07/10/2025) frete=TRANSBORDO0+EFVM33,42+FCA1,06
    ("2025-09-20", "2027-12-31", 48.24, 63.21, 41.70, 13.25, 8.26),  # 1o cadastro (19/09/2025) frete=TRANSBORDO0+EFVM40,42+FCA1,28
    ("2025-08-20", "2027-12-31", 48.24, 62.98, 41.47, 13.25, 8.26),  # frete=TRANSBORDO0+EFVM40,20+FCA1,27
    ("2025-07-20", "2027-12-31", 48.24, 62.92, 41.41, 13.25, 8.26),  # frete=TRANSBORDO0+EFVM40,14+FCA1,27
    ("2025-06-20", "2027-12-31", 48.24, 62.96, 41.45, 13.25, 8.26),  # frete=TRANSBORDO0+EFVM40,18+FCA1,27
    ("2025-05-20", "2027-12-31", 48.24, 63.48, 41.97, 13.25, 8.26),  # 1o cadastro (baixa confianca, ver nota acima) frete=TRANSBORDO0+EFVM32,98(derivado)+FCA8,99(lido)
    ("2025-05-20", "2027-12-31", 48.24, 63.48, 41.97, 13.25, 8.26),  # 2o cadastro (19/05/2025 23:30:08) frete=TRANSBORDO22,01+EFVM19,35+FCA0,61
    ("2025-05-01", "2027-12-31", 48.24, 64.47, 42.96, 13.25, 8.26),  # frete=TRANSBORDO22,01(derivado)+EFVM20,31+FCA0,64
    ("2025-05-01", "2027-12-31", 48.24, 82.00, 60.49, 13.25, 8.26),  # 2o cadastro (30/04/2025 15:30:31) frete=TRANSBORDO22,01+EFVM37,30+FCA1,18
    ("2025-04-20", "2025-04-30", 48.24, 82.00, 60.49, 13.25, 8.26),  # 1o cadastro frete=TRANSBORDO17,53+EFVM41,78+FCA1,18
    ("2025-04-20", "2025-04-30", 48.24, 82.00, 60.49, 13.25, 8.26),  # 2o cadastro (19/04/2025 23:15:11) frete=TRANSBORDO22,01+EFVM37,30+FCA1,18
    ("2025-03-20", "2025-04-30", 48.24, 82.10, 60.59, 13.25, 8.26),  # frete=TRANSBORDO12,95+EFVM46,18+FCA1,46
    ("2025-03-01", "2025-03-31", 48.24, 70.69, 49.18, 13.25, 8.26),  # frete=TRANSBORDO12,95+EFVM35,12+FCA1,11
    ("2025-01-01", "2025-02-19", 48.24, 80.77, 59.26, 13.25, 8.26),  # frete=TRANSBORDO22,01+EFVM36,11+FCA1,14 (re-cadastrado tardiamente em 27/05/2025)
    ("2024-12-20", "2025-02-28", 48.04, 70.69, 49.18, 13.25, 8.26),  # frete=TRANSBORDO12,95+EFVM35,12+FCA1,11
    ("2024-12-20", "2024-12-31", 48.04, 70.69, 49.18, 13.25, 8.26),  # 2o cadastro (19/12/2024) frete=TRANSBORDO12,95+EFVM35,12(derivado)+FCA1,11
    ("2024-11-20", "2024-12-31", 48.04, 70.36, 48.85, 13.25, 8.26),  # frete=TRANSBORDO12,95+EFVM34,80+FCA1,10
    ("2024-08-20", "2024-12-31", 48.04, 70.01, 48.50, 13.25, 8.26),  # frete=TRANSBORDO12,95+EFVM34,46+FCA1,09
    ("2024-07-20", "2024-12-31", 48.04, 70.12, 48.61, 13.25, 8.26),  # 1o cadastro (07/08/2024) frete=TRANSBORDO14,92+EFVM0,00+FCA33,69
    ("2024-07-20", "2024-12-31", 48.04, 70.12, 48.61, 13.25, 8.26),  # 2o cadastro (18/07/2024) frete=TRANSBORDO12,95+EFVM34,57(derivado)+FCA1,09
    ("2024-06-20", "2024-12-31", 48.04, 69.85, 48.34, 13.25, 8.26),  # frete=TRANSBORDO12,95+EFVM15,31+FCA20,08 (alocacao atipica p/ FCA)
    ("2024-03-20", "2024-12-31", 48.04, 69.78, 48.27, 13.25, 8.26),  # frete=TRANSBORDO14,92+EFVM14,11+FCA19,24
    ("2024-02-20", "2024-12-31", 48.04, 69.37, 47.86, 13.25, 8.26),  # frete=TRANSBORDO14,92+EFVM13,87+FCA19,07
    ("2024-01-20", "2024-12-31", 48.04, 69.23, 47.72, 13.25, 8.26),  # frete=TRANSBORDO14,92+EFVM13,79(derivado)+FCA19,01
    ("2023-12-20", "2024-12-31", 43.63, 70.17, 48.66, 13.25, 8.26),  # frete=TRANSBORDO14,92+EFVM14,24+FCA19,50
]

# --- 12950 | C_2025_53 | EBI->VIC | CALCARIO BRITADO | IMG_0251.MOV ---
# INTERMODAL FCA+EFVM (par invertido em relacao ao 8397): aqui MANOBRA
# ORIGEM e da FCA (origem EBI fica na malha FCA) e MANOBRA DESTINO e da EFVM
# (destino VIC fica na malha EFVM). frete_rs_t = FRETE(FCA) + FRETE(EFVM).
# manobra_origem(FCA) fica CONSTANTE em R$12,47 do inicio ao fim do historico
# capturado (2023-2027). manobra_destino(EFVM) muda de padrao: R$7,91/7,92/
# 7,98 (raro) em 2025-2026 -> R$11,95 (constante) a partir de 20/09/2025 pra
# tras ate 20/12/2023 - mesmo padrao de "rebalanceio" visto no item 8397 na
# mesma janela temporal (~set/2025), reforcando que e uma mudanca sistemica
# de classificacao de manobra na VLI, nao um erro de leitura. Video de 36,3s,
# tabela lida quase por completo: ultima linha (28/11/2023, vig 20/12/2023)
# esta perto do fim do scroll/video. Uma linha (03/04/2025 15:55:xx, tarifa
# 112,93) ficou com o FRETE cortado no frame disponivel -> OMITIDA.
DADOS[12950] = [
    # vig_ini      vig_fim       TR       tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 129.22, 112.54, 92.16, 12.47, 7.91),
    ("2026-03-20", "2027-12-31", 129.22, 113.35, 92.97, 12.47, 7.91),
    ("2026-02-20", "2027-12-31", 129.22, 113.67, 93.29, 12.47, 7.91),
    ("2026-02-20", "2027-12-31", 129.22, 113.68, 91.00, 14.70, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 129.22, 113.42, 93.04, 12.47, 7.91),
    ("2025-12-20", "2027-12-31", 129.22, 112.91, 92.53, 12.47, 7.91),
    ("2025-12-20", "2027-12-31", 129.22, 112.92, 90.39, 14.61, 7.92),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 129.22, 112.59, 92.21, 12.47, 7.91),
    ("2025-10-20", "2027-12-31", 125.46, 112.68, 92.28, 12.47, 7.91),
    ("2025-09-20", "2027-12-31", 125.46, 112.65, 92.27, 12.47, 7.91),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 125.46, 112.65, 88.23, 12.47, 11.95),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 125.46, 112.24, 87.82, 12.47, 11.95),
    ("2025-07-20", "2027-12-31", 125.46, 112.14, 87.72, 12.47, 11.95),
    ("2025-06-20", "2027-12-31", 125.46, 112.21, 87.79, 12.47, 11.95),
    ("2025-05-20", "2027-12-31", 125.46, 113.15, 88.73, 12.47, 11.95),
    ("2025-05-01", "2027-12-31", 125.46, 114.92, 90.50, 12.47, 11.95),
    ("2025-04-20", "2025-04-30", 125.46, 114.92, 90.50, 12.47, 11.95),
    ("2025-03-20", "2025-04-30", 125.46, 115.10, 90.68, 12.47, 11.95),
    ("2024-12-20", "2025-02-28", 125.46, 113.81, 89.39, 12.47, 11.95),
    ("2024-12-20", "2024-12-31", 125.46, 113.81, 89.39, 12.47, 11.95),
    ("2024-11-20", "2024-12-31", 125.46, 113.13, 88.71, 12.47, 11.95),
    ("2024-10-20", "2024-12-31", 125.46, 112.64, 88.22, 12.47, 11.95),
    ("2024-09-20", "2024-12-31", 120.37, 112.39, 87.97, 12.47, 11.95),
    ("2024-08-20", "2024-12-31", 120.37, 112.41, 87.99, 12.47, 11.95),
    ("2024-07-20", "2024-12-31", 120.37, 112.64, 88.22, 12.47, 11.95),
    ("2024-06-20", "2024-12-31", 120.37, 112.10, 87.68, 12.47, 11.95),
    ("2024-05-20", "2024-12-31", 120.37, 112.22, 87.80, 12.47, 11.95),
    ("2024-04-20", "2024-12-31", 120.37, 112.10, 87.68, 12.47, 11.95),
    ("2024-03-20", "2024-12-31", 120.37, 111.95, 87.53, 12.47, 11.95),
    ("2024-02-20", "2024-12-31", 120.37, 111.12, 86.70, 12.47, 11.95),
    ("2024-01-20", "2024-12-31", 120.37, 110.83, 86.41, 12.47, 11.95),
    ("2023-12-20", "2024-12-31", 120.37, 112.74, 88.32, 12.47, 11.95),
]

# --- 39843 | C_2025_54 | ECE->VIC | PRO SIDERURGICO | IMG_0253.MOV ---
# Rota INVERSA (par) do item 8397 (VIC->ECE): aqui MANOBRA ORIGEM e FCA e
# MANOBRA DESTINO e EFVM (mesma logica: ECE fica na malha FCA, VIC na EFVM).
# Estrutura com TRANSBORDO ORIGEM (FCA) em vez de "destino". frete_rs_t =
# TRANSBORDO ORIGEM + FRETE(FCA) + FRETE(EFVM). Mesmo padrao de rebalanceio
# de manobra visto nos itens 8397/12950 na mesma janela (~jul-set/2025):
# MO(FCA)=8,26 / MD(EFVM)=13,25 ate 20/08/2025, depois MO=19,74 / MD=8,99 (ou
# 0,00 num re-cadastro pontual de 07/10/2025 15:25 - possivel erro de
# digitacao, mantido por transparencia mas de baixa confianca). Video curto
# (12,6s, so 3 frames) - so 8 vigencias capturadas, da mais recente
# (20/06/2026) ate 20/03/2025; nao da pra saber se ha vigencias mais antigas
# sem novo video/replay. Uma linha (vig_ini 2025-05-01, 1o cadastro, tarifa
# 63,63) teve FRETE FCA/EFVM cortados no frame -> frete_rs_t derivado por
# diferenca (tarifa - MO - MD, assumindo TRANSBORDO=0 como no cadastro
# vizinho) - baixa confianca no split interno, mas o total valida.
# IMG_0272.MOV e um video DUPLICADO do mesmo item 39843 - confirmou todas as
# linhas de 2025-07 a 2025-09 e 2025-04/05 exatamente como lidas acima
# (inclusive a anomalia MD=0,00 do re-cadastro de 07/10/2025 15:25).
DADOS[39843] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 78.26, 62.31, 33.59, 19.73, 8.99),
    ("2025-09-20", "2027-12-31", 75.98, 62.38, 42.64, 19.74, 0.00),  # 1o cadastro (07/10/2025 15:25) - MD=0 possivel anomalia
    ("2025-09-20", "2027-12-31", 75.98, 62.38, 33.65, 19.74, 8.99),  # 2o cadastro (07/10/2025 11:17)
    ("2025-09-20", "2027-12-31", 75.98, 62.38, 40.87, 8.26, 13.25),  # cadastro anterior (19/09/2025), padrao antigo de manobra
    ("2025-08-20", "2027-12-31", 75.98, 62.15, 40.64, 8.26, 13.25),
    ("2025-07-20", "2027-12-31", 75.98, 62.09, 40.58, 8.26, 13.25),
    ("2025-05-01", "2027-12-31", 75.98, 63.63, 42.12, 8.26, 13.25),  # 1o cadastro - frete derivado (split FCA/EFVM nao lido)
    ("2025-05-01", "2027-12-31", 75.98, 85.64, 64.13, 8.26, 13.25),  # 2o cadastro (30/04/2025 15:32)
    ("2025-04-20", "2025-04-30", 75.98, 85.64, 64.13, 8.26, 13.25),  # frete=TRANSBORDO22,01+FCA1,96+EFVM40,16
    ("2025-03-20", "2025-04-30", 75.98, 85.74, 64.23, 8.26, 13.25),  # frete=TRANSBORDO22,01+FCA1,12+EFVM41,10
]

# --- 41130 | C_2025_53 | VTU->VIC | COQUE FINO | IMG_0254.MOV ---
# 7,8s, so 2 frames -> cobertura parcial da tabela (so as vigencias mais
# recentes, 20/12/2025 em diante). Ferrovia unica EFVM, manobra CONSTANTE
# MO=14,85 / MD=8,00 em todas as linhas capturadas. Vigencia "20/01/2026,
# vig_fim 19/02/2026" (TR85,74) e uma linha retroativa curta (re-cadastro).
# Uma linha adicional (cad 04/02/2026, TR81,91) tinha os mesmos valores da
# linha de vig 20/01/2026 mas com o ano da vigencia inicial ilegivel (dava
# pra ler "20/01/20XX", nao deu pra confirmar 2025 ou 2026 com confianca) ->
# OMITIDA para nao duplicar/confundir com a linha ja capturada.
DADOS[41130] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 85.74, 91.61, 68.76, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 85.74, 91.80, 68.95, 14.85, 8.00),
    ("2026-04-20", "2027-12-31", 85.74, 91.88, 69.03, 14.85, 8.00),
    ("2026-03-20", "2027-12-31", 85.74, 92.28, 69.43, 14.85, 8.00),
    ("2026-02-20", "2027-12-31", 85.74, 92.54, 69.69, 14.85, 8.00),
    ("2026-01-20", "2026-02-19", 85.74, 92.34, 69.49, 14.85, 8.00),
    ("2026-01-01", "2026-01-19", 85.74, 92.22, 69.37, 14.85, 8.00),
    ("2025-12-20", "2025-12-31", 81.91, 91.92, 69.07, 14.85, 8.00),
]
# IMG_0309.MOV e um video DUPLICADO do mesmo item 41130 - confirmou todas
# as linhas acima com clareza (inclusive a vigencia curta 20/01/2026-
# 19/02/2026). A linha ambigua (cad 04/02/2026, "vig_ini 20/01/2025")
# permanece omitida - mesmo no frame mais nitido o ano ficou inconsistente
# com a sequencia (tarifa/TR identicos a uma vigencia de 2026 ja
# capturada).

# --- 40276 | C_2025_54 | VIC->VTU | PRO SIDERURGICO | IMG_0255.MOV ---
# Ferrovia unica EFVM (nao intermodal apesar do par de rota com 18814/39843).
# Mesmo padrao de rebalanceio de manobra visto nos outros itens na mesma
# janela: MO=8,99/MD=18,73(74) ate 20/10/2025, depois MO=13,25/MD=13,25
# (constante) a partir do re-cadastro de 19/09/2025 (varios re-cadastros
# identicos nesse dia, mantida 1 linha representativa). Video de 14,2s, 3
# frames, cobre de 20/06/2026 ate 20/08/2025. GAP: vigencia 20/04/2026 nao
# apareceu em nenhum frame (pulo entre os frames 0 e 1) -> omitida.
# IMG_0271.MOV e um video DUPLICADO do mesmo item 40276 - confirmou todas as
# linhas acima e completou a lacuna do 1o cadastro de 20/09/2025.
DADOS[40276] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 68.06, 87.69, 59.97, 8.99, 18.73),
    ("2026-05-20", "2027-12-31", 68.06, 87.87, 60.15, 8.99, 18.73),
    ("2026-03-20", "2027-12-31", 68.06, 88.32, 60.60, 8.99, 18.73),  # frete derivado (cortado no topo do frame)
    ("2026-02-20", "2027-12-31", 68.06, 88.57, 60.85, 8.99, 18.73),
    ("2026-01-20", "2027-12-31", 68.06, 88.38, 60.66, 8.99, 18.73),
    ("2025-12-20", "2027-12-31", 65.02, 87.98, 60.26, 8.99, 18.73),
    ("2025-11-20", "2027-12-31", 65.02, 87.73, 60.01, 8.99, 18.73),
    ("2025-10-20", "2027-12-31", 65.02, 87.79, 60.06, 8.99, 18.74),
    ("2025-09-20", "2027-12-31", 65.02, 87.78, 60.05, 8.99, 18.74),  # 1o cadastro (07/10/2025) - confirmado por IMG_0271.MOV (duplicado)
    ("2025-09-20", "2027-12-31", 65.02, 87.78, 61.28, 13.25, 13.25),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 65.02, 87.46, 60.96, 13.25, 13.25),
]

# --- 10414 | C_2025_53 | VPN->VIC | ANTRACITO | IMG_0256.MOV ---
# Ferrovia unica EFVM. Linha "LIMPEZA DE VAGAO" (EFVM) sempre R$0,00 em
# todas as vigencias vistas -> ignorada (nao entra na soma). Mesmo padrao
# de rebalanceio de manobra: MO=14,85/MD=7,99 ate 20/10/2025, depois
# MO=11,95/MD=11,95 (constante) a partir do re-cadastro de 19/09/2025.
# Video de 28,3s, 4 frames + 3 extras (frame 3 original veio com double-
# exposure/scroll-ghosting, substituido por frames extras em t=13,2/14,8/
# 16,4s). Cobertura de 20/06/2026 ate 01/03/2025.
DADOS[10414] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 98.15, 91.61, 68.77, 14.85, 7.99),
    ("2026-02-20", "2027-12-31", 98.15, 92.54, 69.70, 14.85, 7.99),
    ("2026-01-20", "2027-12-31", 98.15, 92.34, 69.50, 14.85, 7.99),
    ("2025-12-20", "2027-12-31", 93.76, 91.92, 69.08, 14.85, 7.99),
    ("2025-11-20", "2027-12-31", 93.76, 91.66, 68.82, 14.85, 7.99),
    ("2025-10-20", "2027-12-31", 93.76, 91.72, 68.88, 14.85, 7.99),
    ("2025-09-20", "2027-12-31", 93.76, 91.71, 68.87, 14.85, 7.99),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 93.76, 91.71, 67.81, 11.95, 11.95),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 93.76, 91.38, 67.48, 11.95, 11.95),
    ("2025-07-20", "2027-12-31", 93.76, 91.30, 67.40, 11.95, 11.95),
    ("2025-06-20", "2027-12-31", 93.76, 91.36, 67.46, 11.95, 11.95),
    ("2025-05-20", "2027-12-31", 93.76, 92.13, 68.23, 11.95, 11.95),
    ("2025-05-01", "2027-12-31", 93.76, 93.57, 69.67, 11.95, 11.95),
    ("2025-04-20", "2025-04-30", 93.76, 93.57, 69.67, 11.95, 11.95),
    ("2025-03-20", "2025-04-30", 93.76, 93.71, 69.81, 11.95, 11.95),
    ("2025-02-20", "2025-03-19", 93.76, 91.94, 68.04, 11.95, 11.95),
    ("2025-04-01", "2025-04-30", 93.76, 91.77, 67.87, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.76, 91.77, 67.87, 11.95, 11.95),
]

# --- 39558 | C_2025_53 | VPN->VIC | MINERIO FERRO | IMG_0257.MOV ---
# Ferrovia unica EFVM. Vigencia do contrato comeca em 11/07/2024 (item mais
# novo). Rebalanceio de manobra na mesma janela de sempre: MO=19,94/MD=7,90
# (aprox constante) ate 20/09/2025, depois MO=13,25/MD=14,62 (constante) a
# partir do re-cadastro de por volta de 17-18/06-07/2025 (aqui a transicao
# aparenta ter acontecido um pouco mais cedo que nos outros itens, em torno
# de jun/jul 2025 em vez de set/2025 - ver linhas 2025-06/07). Linha
# 2026-02-20 (1o cadastro, cad 19/02/2026): tarifa lida como 82,00 na tela
# mas a soma dos servicos fecha em 83,09 - tratado como provavel troca de
# digito 9<->0 na leitura, usado 83,09 (bate com o 2o cadastro da mesma
# vigencia). Video de 16,98s, 4 frames, cobertura quase completa ate
# 28/10/2024 (perto do inicio do contrato).
DADOS[39558] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 59.82, 82.25, 54.41, 19.94, 7.90),
    ("2026-05-20", "2027-12-31", 59.82, 82.42, 54.58, 19.94, 7.90),
    ("2026-02-20", "2027-12-31", 59.82, 83.09, 55.25, 19.94, 7.90),  # 1o cadastro (19/02/2026) - tarifa corrigida (tela mostrava 82,00, soma fecha em 83,09, ver nota)
    ("2026-02-20", "2027-12-31", 59.82, 83.09, 54.98, 20.13, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 59.82, 82.91, 55.07, 19.94, 7.90),
    ("2025-12-20", "2027-12-31", 57.14, 82.54, 54.70, 19.94, 7.90),
    ("2025-12-20", "2027-12-31", 57.14, 82.54, 54.63, 19.99, 7.92),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 57.14, 82.31, 54.47, 19.94, 7.90),
    ("2025-09-20", "2027-12-31", 57.14, 82.36, 54.50, 19.95, 7.91),
    ("2025-07-20", "2027-12-31", 57.14, 81.98, 54.11, 13.25, 14.62),  # rebalanceio de manobra
    ("2025-06-20", "2027-12-31", 57.14, 82.03, 54.16, 13.25, 14.62),
    ("2025-05-20", "2027-12-31", 57.14, 82.72, 54.85, 13.25, 14.62),
    ("2025-05-01", "2027-12-31", 57.14, 84.01, 56.14, 13.25, 14.62),
    ("2025-04-20", "2025-04-30", 57.14, 84.01, 56.14, 13.25, 14.62),
    ("2025-03-20", "2025-04-30", 57.14, 84.14, 56.27, 13.25, 14.62),
    ("2025-02-20", "2025-03-19", 57.14, 82.55, 54.68, 13.25, 14.62),
    ("2025-04-01", "2025-04-30", 57.14, 82.40, 54.53, 13.25, 14.62),
    ("2025-03-01", "2025-03-31", 57.14, 82.40, 54.53, 13.25, 14.62),
    ("2024-12-20", "2025-02-28", 54.54, 82.40, 54.53, 13.25, 14.62),
    ("2024-12-20", "2024-12-31", 54.54, 82.40, 54.53, 13.25, 14.62),
    ("2024-10-28", "2024-12-31", 54.54, 81.55, 54.53, 13.25, 13.77),
]
# IMG_0286.MOV e um video DUPLICADO do mesmo item 39558 - confirma tudo.

# --- 40115 | C_2025_54 | VIC->EHF | PRO SIDERURGICO | IMG_0258.MOV ---
# INTERMODAL EFVM+FCA mas com ESTRUTURA DE 3 LINHAS SO (sem Manobra Origem):
# FRETE(EFVM) + FRETE(FCA) + MANOBRA DESTINO(FCA). manobra_origem gravado
# como 0,00 (nao existe na tela). frete_rs_t = FRETE(EFVM) + FRETE(FCA).
# MD(FCA) sobe de forma modesta de R$20,58/20,60 para R$21,01 a partir do
# re-cadastro de 19/09/2025 (mesma janela de sempre, mas aqui a mudanca e
# suave porque nao ha realocacao entre MO/MD - so MD existe). Video de
# 13,2s, 3 frames, cobertura boa: 20/06/2026 ate 20/06/2025 (14 vigencias).
# IMG_0259.MOV e um video DUPLICADO do mesmo item 40115 (mesmo cabecalho,
# mesmos dados) - confirmou a leitura e corrigiu a linha 2025-09-20 (1o
# cadastro): tarifa correta e 68,62 (nao 68,82 como uma leitura inicial
# sugeria); FRETE EFVM 44,47 estava certo.
DADOS[40115] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 50.84, 68.53, 47.95, 0.00, 20.58),
    ("2026-05-20", "2027-12-31", 50.84, 68.67, 48.09, 0.00, 20.58),
    ("2026-01-01", "2026-01-19", 50.84, 68.99, 48.41, 0.00, 20.58),
    ("2026-04-20", "2027-12-31", 50.84, 68.73, 48.15, 0.00, 20.58),
    ("2026-03-20", "2027-12-31", 50.84, 69.03, 48.45, 0.00, 20.58),
    ("2026-02-20", "2027-12-31", 50.84, 69.23, 48.65, 0.00, 20.58),
    ("2026-01-20", "2027-12-31", 50.84, 69.08, 48.50, 0.00, 20.58),
    ("2025-12-20", "2027-12-31", 48.56, 68.77, 48.19, 0.00, 20.58),
    ("2025-11-20", "2027-12-31", 48.56, 68.58, 48.00, 0.00, 20.58),
    ("2025-09-20", "2027-12-31", 48.56, 68.62, 48.02, 0.00, 20.60),  # 1o cadastro (07/10/2025) - confirmado por IMG_0259.MOV (duplicado)
    ("2025-09-20", "2027-12-31", 48.56, 68.62, 47.61, 0.00, 21.01),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 48.56, 68.37, 47.36, 0.00, 21.01),
    ("2025-07-20", "2027-12-31", 48.56, 68.31, 47.30, 0.00, 21.01),
    ("2025-06-20", "2027-12-31", 48.56, 68.35, 47.34, 0.00, 21.01),
]
# IMG_0315.MOV e um TERCEIRO video do mesmo item 40115 (dup de IMG_0258/
# IMG_0259) - confirmou todas as linhas 2025-2026 acima, inclusive a
# correcao da linha 2025-09-20 (1o cadastro).

# --- 39379 | C_2025_54 | VIC->VPN | PRO SIDERURGICO | IMG_0260.MOV ---
# Rota inversa do item 10414 (VPN->VIC). Ferrovia unica EFVM. Mesmo padrao
# de rebalanceio: MO=8,99/MD=18,73(74) ate 20/10/2025, depois MO=13,25/
# MD=13,93 (constante) a partir do re-cadastro de ~18-19/09/2025. Video de
# 20,6s, 5 frames, boa cobertura ate 01/01/2025 (praticamente todo o
# historico do contrato). Uma linha (vig_ini 20/09/2025, 1o cadastro) ficou
# cortada entre dois frames (so FRETE=60,06 visivel, MO/MD nao capturados) ->
# OMITIDA.
DADOS[39379] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 68.31, 87.70, 59.98, 8.99, 18.73),
    ("2026-05-20", "2027-12-31", 68.31, 87.88, 60.16, 8.99, 18.73),
    ("2026-04-20", "2027-12-31", 68.31, 87.95, 60.23, 8.99, 18.73),
    ("2026-03-20", "2027-12-31", 68.31, 88.33, 60.61, 8.99, 18.73),
    ("2026-02-20", "2027-12-31", 68.31, 88.58, 60.86, 8.99, 18.73),
    ("2026-01-20", "2027-12-31", 68.31, 88.39, 60.67, 8.99, 18.73),
    ("2025-12-20", "2027-12-31", 65.26, 87.99, 60.27, 8.99, 18.73),
    ("2025-11-20", "2027-12-31", 65.26, 87.74, 60.02, 8.99, 18.73),
    ("2025-10-20", "2027-12-31", 65.26, 87.80, 60.07, 8.99, 18.74),
    ("2025-09-20", "2027-12-31", 65.26, 87.44, 60.26, 13.25, 13.93),  # 2o cadastro (rebalanceio, ~18-19/09/2025)
    ("2025-01-01", "2025-02-19", 65.26, 87.84, 60.66, 13.25, 13.93),  # re-cadastro tardio (27/05/2025)
    ("2025-05-20", "2027-12-31", 65.26, 88.17, 60.99, 13.25, 13.93),
    ("2025-05-01", "2027-12-31", 65.26, 89.54, 62.36, 13.25, 13.93),
    ("2025-04-20", "2025-04-30", 65.26, 89.54, 62.36, 13.25, 13.93),
    ("2025-03-20", "2025-04-30", 65.26, 89.68, 62.50, 13.25, 13.93),
    ("2025-02-20", "2025-03-19", 65.26, 88.00, 60.82, 13.25, 13.93),
    ("2025-04-01", "2025-04-30", 65.26, 87.84, 60.66, 13.25, 13.93),  # MD derivado (13,93, coerente com o padrao)
    # Linhas abaixo vieram de IMG_0280.MOV, video DUPLICADO do mesmo item
    # 39379 que capturou historico adicional (2024) nao visto em IMG_0260:
    ("2024-12-20", "2025-02-28", 62.29, 89.26, 62.08, 13.25, 13.93),
    ("2024-12-20", "2024-12-31", 62.29, 89.26, 62.08, 13.25, 13.93),
    ("2024-11-20", "2024-12-31", 62.29, 88.73, 61.55, 13.25, 13.93),
    ("2024-10-20", "2024-12-31", 62.29, 88.34, 61.16, 13.25, 13.93),
    ("2024-09-20", "2024-12-31", 62.29, 88.14, 60.96, 13.25, 13.93),
    ("2024-08-20", "2024-12-31", 62.29, 88.15, 60.97, 13.25, 13.93),
    ("2024-07-20", "2024-08-19", 62.29, 88.33, 61.15, 13.25, 13.93),
]
# IMG_0281.MOV (e tambem IMG_0260/IMG_0280) sao videos DUPLICADOS do mesmo
# item 39379 - todos confirmam os mesmos valores.

# --- 7924 | C_2025_53 | VTU->VIC | COQUE GROSSO | IMG_0261.MOV ---
# Ferrovia unica EFVM. Mesmo padrao de rebalanceio: MO=14,85/MD=8,00 ate
# 20/08/2025, depois MO=11,95/MD=11,95 (constante) a partir do re-cadastro
# de 19/09/2025. Video de 27,2s, 6 frames (o frame 0 automatico veio
# scrollado - header recuperado de um frame extra em t=0,2s). Cobertura
# ampla: 20/06/2026 ate 01/03/2025.
DADOS[7924] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 107.58, 84.73, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 97.59, 107.80, 84.95, 14.85, 8.00),
    ("2026-04-20", "2027-12-31", 97.59, 107.89, 85.04, 14.85, 8.00),
    ("2026-03-20", "2027-12-31", 97.59, 108.36, 85.51, 14.85, 8.00),
    ("2026-02-20", "2027-12-31", 97.59, 108.67, 85.82, 14.85, 8.00),
    ("2026-01-20", "2027-12-31", 97.59, 108.43, 85.58, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 107.94, 85.09, 14.85, 8.00),
    ("2025-11-20", "2027-12-31", 93.23, 107.64, 84.79, 14.85, 8.00),
    ("2025-10-20", "2027-12-31", 93.23, 107.71, 84.86, 14.85, 8.00),
    ("2025-09-20", "2027-12-31", 93.23, 107.70, 84.85, 14.85, 8.00),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 93.23, 107.70, 83.80, 11.95, 11.95),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 93.23, 107.31, 83.41, 11.95, 11.95),
    ("2025-07-20", "2027-12-31", 93.23, 107.21, 83.31, 11.95, 11.95),
    ("2025-05-01", "2027-12-31", 93.23, 109.87, 85.97, 11.95, 11.95),
    ("2025-04-20", "2025-04-30", 93.23, 109.87, 85.97, 11.95, 11.95),
    ("2025-03-20", "2025-04-30", 93.23, 110.04, 86.14, 11.95, 11.95),
    ("2025-02-20", "2025-03-19", 93.23, 107.97, 84.07, 11.95, 11.95),
    ("2025-04-01", "2025-04-30", 93.23, 107.77, 83.87, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.23, 107.77, 83.87, 11.95, 11.95),
]

# --- 9912 | C_2025_53 | ENG->VIC | CALCARIO BRITADO | IMG_0262.MOV ---
# INTERMODAL FCA+EFVM (mesmo par que 12950: origem na malha FCA, destino na
# EFVM). frete_rs_t = FRETE(FCA) + FRETE(EFVM). Video de 46,4s (o 2o mais
# longo do lote), mas os 10 frames no fim deram pra ler. Rebalanceio de
# manobra: MO=14,57/MD=7,91 (TR=79,75) ate 20/12/2025, depois MO=12,47/
# MD=11,95 (TR=77,43) em mai-jul/2025 - a transicao exata (ago-out/2025) NAO
# aparece nos frames capturados (GAP). Ha tambem um GAP entre mar/2025 e
# abr/2024 (nao capturado). Varias linhas tem a tarifa da tela destoando
# ~0,20 da soma dos servicos (2026-05-20, 2026-01-20) -> nesses casos foi
# usada a tarifa DERIVADA da soma (mais confiavel que o digito isolado).
DADOS[9912] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 79.75, 84.70, 62.22, 14.57, 7.91),
    ("2026-05-20", "2027-12-31", 79.75, 84.88, 62.40, 14.57, 7.91),  # tarifa corrigida (ver nota)
    ("2026-04-20", "2027-12-31", 79.75, 84.95, 62.47, 14.57, 7.91),
    ("2026-03-20", "2027-12-31", 79.75, 85.32, 62.84, 14.57, 7.91),
    ("2026-02-20", "2027-12-31", 79.75, 85.56, 63.08, 14.57, 7.91),
    ("2026-02-20", "2027-12-31", 79.75, 85.56, 62.87, 14.71, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 79.75, 85.57, 63.09, 14.57, 7.91),  # tarifa corrigida (tela mostrava 85,37, ver nota)
    ("2025-12-20", "2027-12-31", 79.75, 84.98, 62.50, 14.57, 7.91),
    ("2025-12-20", "2027-12-31", 79.75, 84.98, 62.45, 14.61, 7.92),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 79.75, 84.74, 62.26, 14.57, 7.91),
    ("2025-07-20", "2027-12-31", 77.43, 84.44, 60.02, 12.47, 11.95),  # rebalanceio de manobra (janela exata nao capturada)
    ("2025-05-20", "2027-12-31", 77.43, 85.15, 60.73, 12.47, 11.95),
    ("2025-05-01", "2027-12-31", 77.43, 86.48, 62.06, 12.47, 11.95),
    ("2025-04-20", "2025-04-30", 77.43, 86.48, 62.06, 12.47, 11.95),
    ("2025-03-20", "2025-04-30", 77.43, 86.61, 62.19, 12.47, 11.95),
    ("2024-04-20", "2024-12-31", 74.29, 84.54, 60.12, 12.47, 11.95),  # frete FCA derivado (cortado no topo do frame)
    ("2024-03-20", "2024-12-31", 74.29, 84.23, 59.81, 12.47, 11.95),
    ("2024-02-20", "2024-12-31", 74.29, 83.61, 59.19, 12.47, 11.95),
    ("2024-01-20", "2024-12-31", 74.29, 83.39, 58.97, 12.47, 11.95),
    ("2023-12-20", "2024-12-31", 74.29, 84.82, 60.40, 12.47, 11.95),
]

# --- 19842 | C_2025_53 | ECE->VIC | MINERIO FERRO | IMG_0263.MOV ---
# INTERMODAL FCA+EFVM com TRANSBORDO ORIGEM (FCA), sempre R$0,00 em todas as
# vigencias vistas. frete_rs_t = TRANSBORDO(0) + FRETE(FCA) + FRETE(EFVM).
# Rebalanceio de manobra ATIPICO em relacao aos outros itens: em vez de MO
# cair e MD subir, aqui MO(FCA) SOBE de ~12,06/12,08 para 21,17 (e MD(EFVM)
# sobe soh um pouco, 7,90->7,91) a partir de re-cadastros de meados/set-out
# 2025; TR ANTT tambem muda de 79,35 para 77,03 nessa janela. Ha varios
# cadastros na mesma vigencia 20/09/2025 com o padrao ANTIGO (MO~12,08) e
# depois o NOVO (MO=21,17) - mantidas as duas variantes mais claras. Video
# de 37,5s, 8 frames, mas so os 4 primeiros foram revisados em detalhe
# (cobertura ate 20/09/2025); frames 4-7 (mais antigos) NAO foram
# transcritos por tempo - possivel historico adicional nao capturado aqui.
DADOS[19842] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 79.35, 64.26, 44.30, 12.06, 7.90),
    ("2026-01-01", "2026-01-19", 79.35, 64.68, 44.72, 12.06, 7.90),
    ("2026-04-20", "2027-12-31", 79.35, 64.44, 44.48, 12.06, 7.90),
    ("2026-03-20", "2027-12-31", 79.35, 64.72, 44.76, 12.06, 7.90),
    ("2026-02-20", "2027-12-31", 79.35, 64.90, 44.94, 12.06, 7.90),
    ("2026-01-20", "2027-12-31", 79.35, 64.76, 44.80, 12.06, 7.90),
    ("2025-12-20", "2027-12-31", 79.35, 64.47, 44.51, 12.06, 7.90),
    ("2025-11-20", "2027-12-31", 79.35, 64.29, 44.33, 12.06, 7.90),
    ("2025-09-20", "2027-12-31", 77.03, 64.33, 44.34, 12.08, 7.91),  # padrao antigo (1o cadastro, 19/09/2025)
    ("2025-09-20", "2027-12-31", 77.03, 64.33, 35.25, 21.17, 7.91),  # padrao novo (re-cadastro 18-20/10/2025)
    ("2025-08-20", "2027-12-31", 77.03, 64.10, 44.11, 12.08, 7.91),  # confirmado por IMG_0319.MOV (duplicado)
    ("2025-07-20", "2027-12-31", 77.03, 64.04, 44.05, 12.08, 7.91),  # confirmado por IMG_0319.MOV (duplicado)
]
# IMG_0319.MOV e um video DUPLICADO do mesmo item 19842 - confirmou todas as
# linhas 2026 acima e acrescentou as duas linhas de 2025-07/08.

# --- 39950 | C_2025_53 | ESQ->VIC | MINERIO FERRO | IMG_0265.MOV ---
# INTERMODAL FCA+EFVM (mesmo par que 12950/9912: origem FCA, destino EFVM).
# frete_rs_t = FRETE(EFVM) + FRETE(FCA). manobra_destino(EFVM) e manobra_
# origem(FCA) praticamente constantes (7,90/12,07) no periodo capturado.
# Video de 29,3s, 7 frames, so os 3 primeiros foram revisados (cobertura
# 20/06/2026 ate 20/01/2026) - frames 3-6 (vigencias mais antigas) NAO
# transcritos por tempo.
# IMG_0326.MOV e um video DUPLICADO do mesmo item 39950 (cabecalho identico,
# 7,2s, 9 frames) - CONFIRMOU as 8 linhas acima (split FRETE_EFVM+FRETE_FCA
# integralmente legivel, validou o frete ja derivado da vig 20/01/2026) E
# ESTENDEU o historico ate 01/01/2025 (inicio do contrato), preenchendo o
# gap que tinha ficado por falta de tempo. Os valores das vigencias
# 20/09/2025 a 01/01/2025 batem EXATAMENTE com o item gemeo 39952 (ver
# abaixo), reforçando a leitura.
DADOS[39950] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 94.15, 103.75, 83.78, 12.07, 7.90),
    ("2026-05-20", "2027-12-31", 94.15, 103.97, 84.00, 12.07, 7.90),
    ("2026-01-01", "2026-01-19", 94.15, 104.45, 84.48, 12.07, 7.90),
    ("2026-04-20", "2027-12-31", 94.15, 104.06, 84.09, 12.07, 7.90),
    ("2026-03-20", "2027-12-31", 94.15, 104.51, 84.54, 12.07, 7.90),
    ("2026-02-20", "2027-12-31", 94.15, 104.81, 84.84, 12.07, 7.90),
    ("2026-02-20", "2027-12-31", 94.15, 104.81, 84.65, 12.18, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 94.15, 104.58, 84.61, 12.07, 7.90),  # frete confirmado por IMG_0326.MOV (57,10+27,51)
    ("2025-12-20", "2027-12-31", 94.15, 104.11, 84.14, 12.07, 7.90),  # NOVO (IMG_0326.MOV) 1o cadastro (19/12/2025)
    ("2025-12-20", "2027-12-31", 94.15, 104.11, 84.09, 12.10, 7.92),  # NOVO (IMG_0326.MOV) 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 94.15, 103.82, 83.85, 12.07, 7.90),  # NOVO (IMG_0326.MOV)
    ("2025-10-20", "2027-12-31", 91.41, 103.89, 83.91, 12.07, 7.91),  # NOVO (IMG_0326.MOV)
    ("2025-09-20", "2027-12-31", 91.41, 103.88, 83.90, 12.07, 7.91),  # NOVO (IMG_0326.MOV) 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 91.41, 103.88, 83.89, 12.08, 7.91),  # NOVO (IMG_0326.MOV) 2o cadastro (rebalanceio) - confere com 39952
    ("2025-08-20", "2027-12-31", 91.41, 103.50, 83.51, 12.08, 7.91),  # NOVO (IMG_0326.MOV) - confere com 39952
    ("2025-07-20", "2027-12-31", 91.41, 103.40, 83.41, 12.08, 7.91),  # NOVO (IMG_0326.MOV) - confere com 39952
    ("2025-01-01", "2027-12-31", 91.41, 103.94, 83.95, 12.08, 7.91),  # NOVO (IMG_0326.MOV) - confere com 39952
]

# --- 40052 | C_2025_53 | ELD->VIC | MINERIO FERRO | IMG_0266.MOV ---
# INTERMODAL FCA+EFVM (mesmo par: origem FCA, destino EFVM). frete_rs_t =
# FRETE(EFVM) + FRETE(FCA). manobra_destino(EFVM)~7,90/7,92/7,98 e manobra_
# origem(FCA)~16,80/16,91/17,02, praticamente constantes no periodo. Video
# de 21,7s, 5 frames, so os 3 primeiros revisados (cobertura 20/06/2026 ate
# 20/12/2025, com GAP em 20/05/2026 e 20/04/2026 - cortados entre frames);
# frames 3-4 (mais antigos) nao transcritos por tempo.
DADOS[40052] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 85.86, 82.75, 58.05, 16.80, 7.90),
    ("2026-03-20", "2027-12-31", 85.86, 83.35, 58.65, 16.80, 7.90),
    ("2026-02-20", "2027-12-31", 85.86, 83.59, 58.89, 16.80, 7.90),
    ("2026-02-20", "2027-12-31", 85.86, 83.90, 58.90, 17.02, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 85.86, 83.41, 58.71, 16.80, 7.90),
    ("2025-12-20", "2027-12-31", 85.86, 83.03, 58.33, 16.80, 7.90),
    ("2025-12-20", "2027-12-31", 85.86, 83.34, 58.51, 16.91, 7.92),  # 2o cadastro (12/12/2025)
]

# --- 39402 | C_2025_53 | VOB->VIC | MINERIO FERRO | IMG_0267.MOV ---
# Ferrovia unica EFVM, mas com linha extra "TRANSBORDO ORIGEM" (0,00 na
# maioria, mas R$15,00 em varias vigencias de fev-mai/2025). frete_rs_t =
# FRETE + TRANSBORDO ORIGEM. Rebalanceio de manobra na janela usual: MO=
# 16,76/77 e MD=7,90/91 ate 20/08/2025, depois MO=13,25/MD=13,25 (constante)
# a partir do re-cadastro de 19/09/2025. Video de 20,2s, 4 frames, cobertura
# ampla: 20/06/2026 ate 01/03/2025.
DADOS[39402] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 41.03, 63.15, 38.49, 16.76, 7.90),
    ("2026-01-20", "2027-12-31", 41.03, 63.64, 38.98, 16.76, 7.90),  # frete derivado (cortado no topo do frame)
    ("2025-12-20", "2027-12-31", 39.20, 63.35, 38.69, 16.76, 7.90),
    ("2025-11-20", "2027-12-31", 39.20, 63.17, 38.51, 16.76, 7.90),
    ("2025-09-20", "2027-12-31", 39.20, 63.21, 38.53, 16.77, 7.91),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 39.20, 63.21, 36.71, 13.25, 13.25),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 39.20, 62.98, 36.48, 13.25, 13.25),
    ("2025-05-01", "2027-12-31", 39.20, 64.48, 37.98, 13.25, 13.25),
    ("2025-04-20", "2025-04-30", 39.20, 79.48, 52.98, 13.25, 13.25),  # frete inclui TRANSBORDO ORIGEM=15,00
    ("2025-03-20", "2025-04-30", 39.20, 79.58, 53.08, 13.25, 13.25),  # frete inclui TRANSBORDO ORIGEM=15,00
    ("2025-02-20", "2025-03-19", 39.20, 78.97, 52.47, 13.25, 13.25),  # frete inclui TRANSBORDO ORIGEM=15,00
    ("2025-04-01", "2025-04-30", 39.20, 78.85, 52.35, 13.25, 13.25),  # frete inclui TRANSBORDO ORIGEM=15,00
]

# --- 14780 | C_2025_53 | VWI->VIC | MINERIO FERRO | IMG_0268.MOV ---
# Ferrovia unica EFVM. Rebalanceio de manobra ATIPICO (como no 19842): MO
# SOBE de 13,92/13,93 para 18,06 (MD quase nao muda, 7,90->7,91) a partir do
# re-cadastro de 19/09/2025. Video de 32,8s, 7 frames; frame 2 veio com
# double-exposure (varias linhas fantasma sobrepostas) mas ainda deu pra
# ler os valores em negrito/nitidos. Cobertura: 20/06/2026 ate 20/09/2025.
DADOS[14780] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 38.20, 57.54, 35.72, 13.92, 7.90),
    ("2026-05-20", "2027-12-31", 38.20, 57.66, 35.84, 13.92, 7.90),
    ("2026-04-20", "2027-12-31", 38.20, 57.71, 35.89, 13.92, 7.90),
    ("2026-03-20", "2027-12-31", 38.20, 57.96, 36.14, 13.92, 7.90),
    ("2026-02-20", "2027-12-31", 38.20, 58.13, 36.31, 13.92, 7.90),
    ("2026-02-20", "2027-12-31", 38.20, 58.39, 36.29, 14.12, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 38.20, 58.00, 36.18, 13.92, 7.90),
    ("2025-12-20", "2027-12-31", 36.49, 57.74, 35.92, 13.92, 7.90),
    ("2025-12-20", "2027-12-31", 36.49, 58.00, 36.06, 14.02, 7.92),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 36.49, 57.58, 35.76, 13.92, 7.90),
    ("2025-09-20", "2027-12-31", 36.49, 57.62, 35.78, 13.93, 7.91),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 36.49, 57.62, 31.65, 18.06, 7.91),  # 2o cadastro (19/09/2025, rebalanceio atipico)
]

# --- 14785 | C_2025_53 | EBI->VIC | MINERIO FERRO | IMG_0269.MOV ---
# INTERMODAL FCA+EFVM (mesmo par que 12950: origem FCA, destino EFVM).
# IMG_0269.MOV (2,9s) so capturou a vigencia mais recente; IMG_0270.MOV
# (20,1s) e um video DUPLICADO do MESMO item que capturou muito mais
# historico (confirma a linha de 2026 e acrescenta 2024-2025). Manobra quase
# constante ate 20/09/2025 (MO~13,99/MD~7,91), depois leve ajuste (MO=13,25/
# MD=7,91) no re-cadastro de 19/09/2025; em 2024 o padrao era MO=13,25/
# MD=13,25 (igual). Linha 2024-05-20: FRETE FCA derivado (cortado no frame).
DADOS[14785] = [
    # vig_ini      vig_fim       TR       tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 129.02, 111.90, 90.02, 13.98, 7.90),
    ("2025-09-20", "2027-12-31", 125.26, 112.01, 90.11, 13.99, 7.91),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 125.26, 112.01, 90.85, 13.25, 7.91),  # 2o cadastro (19/09/2025)
    ("2024-10-20", "2024-12-31", 120.18, 110.21, 83.71, 13.25, 13.25),
    ("2024-09-20", "2024-12-31", 120.18, 109.97, 83.47, 13.25, 13.25),
    ("2024-08-20", "2024-12-31", 120.18, 109.99, 83.49, 13.25, 13.25),
    ("2024-07-20", "2024-12-31", 120.18, 110.21, 83.71, 13.25, 13.25),
    ("2024-06-20", "2024-12-31", 120.18, 109.68, 83.18, 13.25, 13.25),
    ("2024-05-20", "2024-12-31", 120.18, 109.79, 83.29, 13.25, 13.25),  # frete FCA derivado (cortado no frame)
]

# --- 18243 | C_2025_53 | EWD->VIC | COQUE PETROLEO | IMG_0273.MOV ---
# INTERMODAL FCA+EFVM (mesmo par que 12950/9912/39950: origem FCA, destino
# EFVM). frete_rs_t = FRETE(FCA) + FRETE(EFVM). Rebalanceio de manobra:
# MO(FCA)=14,85/MD(EFVM)=8,00 ate 20/10/2025, depois MO=13,77/MD=13,76
# (constante) a partir do re-cadastro de 19/09/2025. Linha 2025-11-20: soma
# dos servicos fecha em 99,99 mas a tela mostrava 99,69 (dif 0,30) -> usado
# o valor derivado da soma. Video de 21,4s, 5 frames, boa cobertura ate
# 01/04/2025.
DADOS[18243] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 141.96, 99.94, 77.09, 14.85, 8.00),
    ("2025-11-20", "2027-12-31", 141.98, 99.99, 77.14, 14.85, 8.00),  # tarifa corrigida (ver nota)
    ("2025-10-20", "2027-12-31", 137.83, 100.05, 77.20, 14.85, 8.00),
    ("2025-09-20", "2027-12-31", 137.83, 100.04, 77.19, 14.85, 8.00),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 137.83, 100.04, 72.51, 13.77, 13.76),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-05-20", "2027-12-31", 137.83, 100.49, 72.96, 13.77, 13.76),
    ("2025-05-01", "2027-12-31", 137.83, 102.06, 74.53, 13.77, 13.76),
    ("2025-04-20", "2025-04-30", 137.83, 102.06, 74.53, 13.77, 13.76),
    ("2025-03-20", "2025-04-30", 137.83, 102.22, 74.69, 13.77, 13.76),
    ("2025-02-20", "2025-03-19", 137.83, 100.29, 72.76, 13.77, 13.76),
    ("2025-04-01", "2025-04-30", 137.83, 100.11, 72.58, 13.77, 13.76),
]

# --- 40283 | C_2025_54 | VIC->VPN | PRO SIDERURGICO | IMG_0274.MOV ---
# Mesmo par de rota que 39379 (VIC->VPN). Ferrovia unica EFVM. Rebalanceio
# de manobra: MO=8,99/MD=18,73(74) ate 20/10/2025, depois MO=13,25/MD=13,93
# (constante) a partir do re-cadastro de 19/09/2025. Linha 2026-03-20: FRETE
# lido como 60,81 mas so fecha a soma com 60,61 (tarifa 88,33) -> usado
# 60,61 (provavel troca de digito 6/8). Video de 11,9s, 3 frames, cobertura
# ampla: 20/06/2026 ate 20/08/2025. IMG_0275.MOV e um video DUPLICADO do
# mesmo item 40283 - confirmou a correcao do FRETE 60,61 (2026-03-20 e
# 2025-09-20 2o cadastro).
DADOS[40283] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 68.31, 87.70, 59.98, 8.99, 18.73),
    ("2026-05-20", "2027-12-31", 68.31, 87.88, 60.16, 8.99, 18.73),
    ("2026-03-20", "2027-12-31", 68.31, 88.33, 60.61, 8.99, 18.73),  # frete corrigido (ver nota)
    ("2026-02-20", "2027-12-31", 68.31, 88.58, 60.86, 8.99, 18.73),
    ("2026-01-20", "2027-12-31", 68.31, 88.39, 60.67, 8.99, 18.73),
    ("2025-12-20", "2027-12-31", 65.28, 87.99, 60.27, 8.99, 18.73),
    ("2025-11-20", "2027-12-31", 65.28, 87.74, 60.02, 8.99, 18.73),
    ("2025-10-20", "2027-12-31", 65.28, 87.80, 60.07, 8.99, 18.74),
    ("2025-09-20", "2027-12-31", 65.28, 87.79, 60.06, 8.99, 18.74),  # 1o cadastro (07/10/2025)
    ("2025-09-20", "2027-12-31", 65.28, 87.79, 60.61, 13.25, 13.93),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 65.28, 87.47, 60.29, 13.25, 13.93),
]

# --- 8391 | C_2025_54 | VIC->EYU | PRO SIDERURGICO | IMG_0278.MOV ---
# INTERMODAL EFVM+FCA (origem EFVM, destino FCA - par igual ao 8397).
# frete_rs_t = FRETE(FCA)+FRETE(EFVM). Rebalanceio de manobra: MO(EFVM)=8,99
# /MD(FCA)=20,99 ate abril/2026 (dados de cabecalho ainda "Carregando" no
# frame inicial, header recuperado de um frame de transicao em t=0,2s -
# mostrou por instantes dados do item anterior 40761/40763, cuidado). Depois
# do rebalanceio (por volta de mai-jul/2025): MO=13,25/MD=18,06 (constante).
# Linha 2026-06-20: MANOBRA ORIGEM lida como 6,99 mas a soma so fecha com
# 8,99 -> corrigido (digito 6/8). Video de 24,8s, 6 frames, so os frames 0 e
# 2 revisados (GAP entre 20/04/2026 e 20/07/2025, e entre 20/04/2025 e o
# inicio do contrato).
DADOS[8391] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 53.59, 70.73, 40.75, 8.99, 20.99),  # MO corrigido (tela mostrava 6,99)
    ("2026-05-20", "2027-12-31", 53.59, 70.88, 40.90, 8.99, 20.99),
    ("2026-01-01", "2026-01-19", 53.59, 71.20, 41.22, 8.99, 20.99),
    ("2026-04-20", "2027-12-31", 53.59, 70.94, 40.96, 8.99, 20.99),
    ("2025-07-20", "2027-12-31", 51.20, 70.48, 39.17, 13.25, 18.06),
    ("2025-06-20", "2027-12-31", 51.20, 70.52, 39.21, 13.25, 18.06),
    ("2025-01-01", "2025-02-19", 51.20, 70.84, 39.53, 13.25, 18.06),
    ("2025-05-20", "2027-12-31", 51.20, 71.11, 39.80, 13.25, 18.06),
    ("2025-05-01", "2027-12-31", 51.20, 72.22, 40.91, 13.25, 18.06),
    ("2025-04-20", "2025-04-30", 51.20, 72.22, 40.91, 13.25, 18.06),
]

# --- 39552 | C_2025_53 | VFU->VIC | CALCARIO BRITADO | IMG_0282.MOV ---
# Ferrovia unica EFVM. TRES padroes de manobra distintos ao longo do tempo
# (nao um simples rebalanceio): 2026 (frames iniciais) MO=28,98/MD=7,91;
# fev-abr/2025 MO=0,00/MD=11,95 (toda a manobra vira "destino"); out-dez/2024
# MO=25,06/MD=13,77. Ha um GRANDE GAP entre 20/05/2026 (frame0) e 20/02/2025
# (frame2) - varias vigencias intermediarias (jun/2025-abr/2026) NAO foram
# capturadas (video de 12,8s, so 3 frames, pulo grande entre frame1 e frame2
# nao revisado). Reportar como cobertura parcial.
DADOS[39552] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 72.32, 79.34, 42.45, 28.98, 7.91),
    ("2026-05-20", "2027-12-31", 72.32, 79.50, 42.61, 28.98, 7.91),
    ("2025-02-20", "2025-03-19", 69.09, 80.30, 68.35, 0.00, 11.95),
    ("2025-04-01", "2025-04-30", 69.09, 80.15, 68.20, 0.00, 11.95),
    ("2025-03-01", "2025-03-31", 69.09, 80.15, 68.20, 0.00, 11.95),
    ("2025-03-01", "2025-03-31", 69.09, 80.92, 68.97, 0.00, 11.95),  # 2o cadastro
    ("2024-12-20", "2025-02-28", 65.95, 80.92, 42.09, 25.06, 13.77),
    ("2024-12-20", "2024-12-31", 65.95, 80.92, 42.09, 25.06, 13.77),
    ("2024-10-28", "2024-12-31", 65.95, 80.09, 41.26, 25.06, 13.77),
]

# --- 19260 | C_2025_53 | VOB->VIC | COQUE GROSSO | IMG_0283.MOV ---
# Ferrovia unica EFVM. Manobra praticamente simetrica (MO~MD) mas MUDA de
# patamar por vigencia: 26,50/26,50 (jul/2024), 24,45/24,45 (ago-set/2024),
# 24,32/24,32 (mai-jun/2024), 24,17-24,24 (mar-abr/2024). Video de 13,9s, 3
# frames, mas o header (frame0) ainda mostrava "Carregando" nos valores da
# tabela - so o frame2 (final) deu pra ler. IMG_0285.MOV e um video
# DUPLICADO do mesmo item que confirmou tudo acima E capturou as 2 vigencias
# mais recentes (2026, com um 4o patamar de manobra: MO~38,8/MD~7,9). GAP
# entre 20/09/2024 e 20/05/2026 permanece (varias vigencias 2025 nao
# capturadas em nenhum dos 2 videos).
DADOS[19260] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 63.34, 106.41, 59.72, 38.80, 7.89),
    ("2026-05-20", "2027-12-31", 63.34, 106.63, 59.84, 38.88, 7.91),
    ("2024-09-20", "2024-12-31", 57.76, 106.49, 57.59, 24.45, 24.45),
    ("2024-08-20", "2024-12-31", 57.76, 106.51, 57.61, 24.45, 24.45),
    ("2024-07-20", "2024-12-31", 57.76, 106.72, 53.72, 26.50, 26.50),
    ("2024-06-20", "2024-12-31", 57.76, 106.20, 57.56, 24.32, 24.32),
    ("2024-05-20", "2024-12-31", 57.76, 106.31, 57.67, 24.32, 24.32),
    ("2024-04-20", "2024-12-31", 57.76, 106.20, 57.74, 24.24, 24.22),
    ("2024-03-20", "2024-12-31", 57.76, 106.06, 57.72, 24.17, 24.17),
]

# --- 39929 | C_2025_54 | EHF->VIC | PRO SIDERURGICO | IMG_0284.MOV ---
# INTERMODAL FCA+EFVM, estrutura de 3 linhas so (sem Manobra Destino, igual
# ao par 40115 mas invertido - aqui so tem MANOBRA ORIGEM(FCA)). manobra_
# destino gravado como 0,00. frete_rs_t = FRETE(FCA)+FRETE(EFVM). MO(FCA)
# sobe de forma modesta de 20,58 para 21,01 a partir do re-cadastro de
# 19/09/2025 (mesmo padrao suave visto no 40115). Video de 13,8s, 3 frames,
# boa cobertura: 20/06/2026 ate 01/01/2025.
DADOS[39929] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 79.08, 79.31, 58.73, 20.58, 0.00),
    ("2026-05-20", "2027-12-31", 79.08, 79.47, 58.89, 20.58, 0.00),
    ("2025-09-20", "2027-12-31", 78.77, 79.41, 58.40, 21.01, 0.00),
    ("2025-08-20", "2027-12-31", 78.77, 79.12, 58.11, 21.01, 0.00),
    ("2025-07-20", "2027-12-31", 78.77, 79.05, 58.04, 21.01, 0.00),
    ("2025-05-20", "2025-06-19", 78.77, 79.76, 58.75, 21.01, 0.00),
    ("2025-06-20", "2027-12-31", 78.77, 79.10, 58.09, 21.01, 0.00),
    ("2025-01-01", "2027-12-31", 78.77, 81.01, 60.00, 21.01, 0.00),
]

# --- 15802 | C_2025_54 | VMR->VIC | PRO SIDERURGICO | IMG_0287.MOV ---
# Ferrovia unica EFVM, rota curta (tarifas ~R$25/t). Video de 15,8s, 4
# frames, mas so frames 0 e 3 revisados -> GRANDE GAP entre 20/05/2026 e
# 20/05/2024 (2 anos sem cobertura). O padrao de manobra e RADICALMENTE
# diferente entre as duas janelas capturadas: em 2026 MD=8,99/MO=3,00 (frete
# alto, ~13,6); em 2024 MD=11,48/MO=11,91 (praticamente simetrico, frete
# baixo, ~1,5-1,8) - mudanca estrutural grande, nao um simples rebalanceio.
DADOS[15802] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 34.40, 25.55, 13.56, 3.00, 8.99),
    ("2026-05-20", "2027-12-31", 34.40, 25.60, 13.61, 3.00, 8.99),
    ("2024-05-20", "2024-12-31", 31.37, 25.12, 1.73, 11.91, 11.48),
    ("2024-04-20", "2024-12-31", 31.37, 25.10, 1.71, 11.91, 11.48),
    ("2024-03-20", "2024-12-31", 31.37, 25.06, 1.67, 11.91, 11.48),
    ("2024-02-20", "2024-12-31", 31.37, 24.87, 1.48, 11.91, 11.48),
    ("2024-01-20", "2024-12-31", 31.37, 24.81, 1.42, 11.91, 11.48),
    ("2023-12-20", "2024-12-31", 29.93, 25.23, 1.84, 11.91, 11.48),
]
# IMG_0288.MOV e um video DUPLICADO do mesmo item 15802 - confirmou as
# linhas de 2024 e mostrou (sem componentes carregados, so a tarifa, por
# isso NAO adicionadas) mais 4 vigencias 2026 intermediarias: 20/04/2026
# tarifa 25,62; 20/03/2026 tarifa 25,73; 20/02/2026 tarifa 25,80; 20/01/2026
# tarifa 25,74 - ficam como pendencia para um novo video/replay.

# --- 8388 | C_2025_54 | VIC->EYB | PRO SIDERURGICO | IMG_0289.MOV ---
# INTERMODAL EFVM+FCA (origem EFVM, destino FCA - mesmo par que 8397/8391).
# frete_rs_t = FRETE(FCA)+FRETE(EFVM). Video de 18,4s, 4 frames, mas so os
# frames 0 e 3 revisados -> GAP entre 20/06/2026 e 20/04/2024 (quase 2 anos
# sem cobertura). Manobra CONSTANTE no periodo 2024 capturado: MO(EFVM)=
# 13,25/MD(FCA)=18,06 (identico ao padrao "novo" pos-rebalanceio visto em
# outros itens, aqui ja presente desde 2023/2024).
DADOS[8388] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 53.51, 85.23, 41.81, 8.99, 34.43),
    ("2024-04-20", "2024-12-31", 48.80, 85.92, 54.61, 13.25, 18.06),
    ("2024-03-20", "2024-12-31", 48.80, 85.81, 54.50, 13.25, 18.06),
    ("2024-02-20", "2024-12-31", 48.80, 85.17, 53.86, 13.25, 18.06),
    ("2024-01-20", "2024-12-31", 48.80, 84.95, 53.64, 13.25, 18.06),
    ("2023-12-20", "2024-12-31", 46.55, 86.41, 55.10, 13.25, 18.06),
]

# --- 8342 | C_2025_54 | VIC->VEB | PRO SIDERURGICO | IMG_0290.MOV ---
# Ferrovia unica EFVM, com linha "TRANSBORDO DESTINO" (0,00 em 2026; 14,36
# constante em 2023-2024). frete_rs_t = TRANSBORDO + FRETE. GAP entre
# 20/06/2026 (unica vigencia 2026 capturada) e 20/03/2024 (video de 18,8s,
# 4 frames, so 0 e 3 revisados). Manobra constante no periodo 2024: MO=
# 13,25/MD=13,25.
DADOS[8342] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.86, 45.15, 8.99, 18.72),
    ("2024-03-20", "2024-12-31", 48.75, 82.83, 56.33, 13.25, 13.25),
    ("2024-02-20", "2024-12-31", 48.75, 82.33, 55.83, 13.25, 13.25),
    ("2024-01-20", "2024-12-31", 48.75, 82.15, 55.65, 13.25, 13.25),
    ("2023-12-20", "2024-12-31", 44.60, 83.30, 56.80, 13.25, 13.25),
]

# --- 15533 | C_2025_54 | EEL->VIC | PRO SIDERURGICO | IMG_0291.MOV ---
# ATENCAO: video inicialmente parecia ser um duplicado do item 8342 (a
# tabela mostrava os MESMOS numeros de tarifa para 20/06/2026, TR51,27,
# ainda "Carregando" os componentes) mas ao continuar o video o cabecalho
# real (capturado em t=2,5s) revelou tratar-se de OUTRO item, 15533
# (EEL-ELDORADO), com estrutura INTERMODAL FCA+EFVM (origem FCA, destino
# EFVM). O TR51,27/tarifa72,86 do inicio do video pertencem de fato a este
# item tambem (nao e coincidencia com o 8342) - MAS os componentes de
# servico dessas linhas 2026 vieram de um frame borrado/fantasma (scroll em
# transicao, t=6s) e foram DERIVADOS (frete = tarifa - MO - MD, assumindo
# MO=20,83/MD=8,99 conforme padrao visivel nas linhas ghost) -> confianca
# MEDIA nessas 5 primeiras linhas. As linhas 2025 (frame limpo, t=11s) e
# 2024 (frame limpo, t=18,5-21s) tem confianca alta. frete_rs_t =
# FRETE(EFVM)+FRETE(FCA). Manobra praticamente constante: MO(FCA)=16,51,
# MD(EFVM)=13,25 em 2024-2025; MO=20,83/MD=8,99 em 2026 (padrao mais
# recente, oposto do rebalanceio "tardio" visto em outros itens - aqui ja
# esta assim desde o inicio do periodo capturado).
DADOS[15533] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.86, 43.04, 20.83, 8.99),  # frete derivado (frame fantasma)
    ("2026-05-20", "2027-12-31", 51.27, 73.01, 43.19, 20.83, 8.99),  # frete derivado (frame fantasma)
    ("2026-04-20", "2027-12-31", 51.27, 73.07, 43.25, 20.83, 8.99),  # frete derivado (frame fantasma)
    ("2026-03-20", "2027-12-31", 51.27, 73.35, 43.53, 20.83, 8.99),  # frete derivado (frame fantasma) - vig curta 01/01-19/01/2026 na tela, mantido vig_fim padrao
    ("2025-09-20", "2027-12-31", 81.11, 69.89, 40.13, 16.51, 13.25),
    ("2025-08-20", "2027-12-31", 81.11, 69.84, 40.08, 16.51, 13.25),  # FRETE FCA derivado (5,79, tela sugeria 5,59)
    ("2025-07-20", "2027-12-31", 81.11, 69.58, 39.82, 16.51, 13.25),
    ("2025-06-20", "2027-12-31", 81.11, 69.62, 39.86, 16.51, 13.25),
    ("2025-05-20", "2027-12-31", 81.11, 70.20, 40.44, 16.51, 13.25),
    ("2024-08-20", "2024-12-31", 77.82, 69.76, 40.00, 16.51, 13.25),
    ("2024-05-20", "2024-12-31", 77.82, 69.82, 40.06, 16.51, 13.25),
    ("2024-04-20", "2024-12-31", 77.82, 69.75, 39.99, 16.51, 13.25),
    ("2024-03-20", "2024-12-31", 77.82, 69.65, 39.89, 16.51, 13.25),
    ("2024-02-20", "2024-12-31", 77.82, 69.14, 39.38, 16.51, 13.25),  # frete derivado (cortado no frame)
]

# --- 8478 | C_2025_54 | VIC->ECE | PRO SIDERURGICO | IMG_0292.MOV ---
# INTERMODAL EFVM+FCA, MESMO PAR de item/estrutura que 8397 (mesma rota
# VIC->ECE, mesmo produto) mas item DIFERENTE (numero e tarifas distintas -
# confirmado via header claro, nao e duplicado). TRANSBORDO DESTINO(FCA)
# sempre 0,00 em 2026, mas R$18,73 constante em 2023-2024 (mesmo padrao do
# 8397). frete_rs_t = TRANSBORDO+FRETE(FCA)+FRETE(EFVM). Manobra:
# MO(EFVM)=8,99/MD(FCA)=19,73 em 2026; MO=13,25/MD=8,26 em 2023-2024 (NAO
# houve leitura da janela de transicao 2025). Video de 26,8s, 6 frames, so
# 0 e 5 revisados -> GAP grande entre 20/04/2026 e 20/03/2024.
DADOS[8478] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 50.49, 62.71, 33.99, 8.99, 19.73),
    ("2026-05-20", "2027-12-31", 50.49, 62.84, 34.12, 8.99, 19.73),
    ("2026-01-01", "2026-01-19", 50.49, 63.13, 34.41, 8.99, 19.73),
    ("2024-03-20", "2024-12-31", 48.04, 73.59, 52.08, 13.25, 8.26),
    ("2024-02-20", "2024-12-31", 48.04, 73.18, 51.67, 13.25, 8.26),
    ("2024-01-20", "2024-12-31", 48.04, 73.04, 51.53, 13.25, 8.26),
    ("2023-12-20", "2024-12-31", 43.93, 73.98, 52.47, 13.25, 8.26),
]

# --- 7917 | C_2025_53 | VTU->VIC | ANTRACITO | IMG_0293.MOV ---
# Ferrovia unica EFVM, linha "LIMPEZA DE VAGAO" sempre 0,00. Video de 25,6s,
# 6 frames, so 0 e 5 revisados -> GAP grande entre 20/06/2026 e 20/03/2024.
# Manobra constante no periodo 2024 capturado: MO=11,95/MD=11,95.
DADOS[7917] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 91.61, 68.77, 14.85, 7.99),
    ("2024-03-20", "2024-12-31", 88.99, 91.16, 67.26, 11.95, 11.95),
    ("2024-02-20", "2024-12-31", 88.99, 90.49, 66.59, 11.95, 11.95),
    ("2024-01-20", "2024-12-31", 88.99, 90.25, 66.35, 11.95, 11.95),
    ("2023-12-20", "2024-12-31", 84.90, 91.80, 67.90, 11.95, 11.95),
]

# --- 14791 | C_2025_53 | EWD->VIC | MINERIO FERRO | IMG_0294.MOV ---
# INTERMODAL FCA+EFVM (origem FCA, destino EFVM - mesmo par que 12950/9912).
# frete_rs_t = FRETE(FCA)+FRETE(EFVM). Video de 19,6s, 4 frames, so 0 e 3
# revisados -> GAP entre 20/06/2026 e 20/03/2024. Manobra constante no
# periodo 2024: MO(FCA)=18,06/MD(EFVM)=13,25.
DADOS[14791] = [
    # vig_ini      vig_fim       TR       tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 106.74, 106.90, 85.02, 13.98, 7.90),
    ("2024-03-20", "2024-12-31", 99.43, 105.00, 73.69, 18.06, 13.25),
    ("2024-02-20", "2024-12-31", 99.43, 104.22, 72.91, 18.06, 13.25),
    ("2024-01-20", "2024-12-31", 99.43, 103.95, 72.64, 18.06, 13.25),
    ("2023-12-20", "2024-12-31", 99.43, 105.73, 74.42, 18.06, 13.25),
]
# IMG_0295.MOV e um video DUPLICADO do mesmo item 14791 - confirma tudo.

# --- 40765 | C_2025_53 | ENG->VIC | MINERIO FERRO | IMG_0296.MOV ---
# INTERMODAL EFVM+FCA (origem EFVM, destino FCA - mesmo par que 8397/8391/
# 8478). frete_rs_t = FRETE(EFVM)+FRETE(FCA). Manobra praticamente
# constante: MD(EFVM)~7,87-7,98, MO(FCA)~14,51-14,70. Video de 21,7s, so 2
# frames revisados (0 e 1), cobertura boa: 20/06/2026 ate 20/10/2025.
DADOS[40765] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 84.28, 80.28, 57.87, 14.51, 7.90),
    ("2026-01-20", "2027-12-31", 84.28, 80.92, 58.51, 14.51, 7.90),
    ("2025-12-20", "2027-12-31", 84.28, 80.55, 58.14, 14.51, 7.90),
    ("2025-12-20", "2027-12-31", 84.28, 80.87, 58.34, 14.61, 7.92),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 84.28, 80.32, 57.91, 14.51, 7.90),
    ("2025-10-20", "2027-12-31", 81.81, 80.37, 57.99, 14.51, 7.87),
]

# --- 40287 | C_2025_54 | VIC->VEB | PRO SIDERURGICO | IMG_0297.MOV ---
# Mesma rota que 8342 (VIC->VEB) mas item DIFERENTE (numero e estrutura
# distintos - confirmado por header claro). Ferrovia unica EFVM. Rebalanceio
# de manobra: MO=8,99/MD=18,72(73) ate 20/11/2025, depois MO=13,25/MD=13,25
# a partir do re-cadastro de 19/09/2025. Video de 15,8s, 4 frames, so 0 e 1
# revisados, cobertura boa: 20/06/2026 ate 20/08/2025.
DADOS[40287] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.45, 44.74, 8.99, 18.72),
    ("2026-05-20", "2027-12-31", 51.27, 72.60, 44.89, 8.99, 18.72),
    ("2025-12-20", "2027-12-31", 48.98, 72.69, 44.98, 8.99, 18.72),
    ("2025-11-20", "2027-12-31", 48.98, 72.49, 44.78, 8.99, 18.72),
    ("2025-09-20", "2027-12-31", 48.98, 72.54, 44.82, 8.99, 18.73),  # 1o cadastro (07/10/2025)
    ("2025-09-20", "2027-12-31", 48.98, 72.54, 46.04, 13.25, 13.25),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 48.98, 72.28, 45.78, 13.25, 13.25),
]

# --- 7901 | C_2025_54 | VIC->VTU | PRO SIDERURGICO | IMG_0298.MOV ---
# Ferrovia unica EFVM. Header so ficou legivel em t~5s (frames iniciais
# tinham spinner "carregando" e um frame de transicao fantasma-duplicado em
# t=4s) - cuidado ja aplicado (nao confundir com outro item so pelos
# valores de tarifa). Rebalanceio de manobra: MO=8,99/MD=18,73 em 2026,
# MO=13,25/MD=13,25 (constante) em 2023-2024 (janela de transicao 2025 nao
# capturada, GAP). Video de 19,6s, 4 frames revisados (0/h5 para header, e
# o frame3 original para os dados 2024).
DADOS[7901] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 68.06, 87.69, 59.97, 8.99, 18.73),
    ("2026-05-20", "2027-12-31", 68.06, 87.87, 60.15, 8.99, 18.73),
    ("2026-01-01", "2026-01-19", 68.06, 88.27, 60.55, 8.99, 18.73),
    ("2026-04-20", "2027-12-31", 68.06, 87.94, 60.22, 8.99, 18.73),
    ("2026-03-20", "2027-12-31", 68.06, 88.32, 60.60, 8.99, 18.73),
    ("2024-08-20", "2024-12-31", 62.08, 85.88, 59.38, 13.25, 13.25),
    ("2024-05-20", "2024-12-31", 62.08, 85.97, 59.47, 13.25, 13.25),
    ("2024-04-20", "2024-12-31", 62.08, 85.88, 59.38, 13.25, 13.25),
    ("2024-03-20", "2024-12-31", 62.08, 85.77, 59.27, 13.25, 13.25),
    ("2024-02-20", "2024-12-31", 62.08, 85.13, 58.63, 13.25, 13.25),
    ("2024-01-20", "2024-12-31", 62.08, 84.91, 58.41, 13.25, 13.25),
    ("2023-12-20", "2024-12-31", 59.21, 86.37, 59.19, 13.59, 13.59),
]

# --- 40288 | C_2025_54 | VEB->VIC | PRO SIDERURGICO | IMG_0299.MOV ---
# Rota inversa do 40287 (VEB->VIC). Ferrovia unica EFVM. Manobra ja
# rebalanceada (MO=13,25/MD=13,25) em todas as vigencias capturadas
# (20/09/2025 em diante) - NAO vimos o padrao "antigo" MO=18,72/MD=8,99
# aqui apesar de aparecer na linha mais recente de 2026 (isso sugere a
# transicao aconteceu entre 20/08/2025 e 20/09/2025, mas so temos essas 2
# pontas). Video de 6,97s, so 2 frames, cobertura parcial: 20/06/2026,
# 20/05/2026, e depois 20/09/2025 (varios re-cadastros no mesmo dia) e
# 20/08/2025.
DADOS[40288] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.05, 44.34, 18.72, 8.99),
    ("2026-05-20", "2027-12-31", 51.27, 72.20, 44.49, 18.72, 8.99),
    ("2025-09-20", "2027-12-31", 48.98, 72.14, 45.64, 13.25, 13.25),
    ("2025-08-20", "2027-12-31", 48.98, 71.88, 45.38, 13.25, 13.25),
]

# --- 40050 | C_2025_53 | ELD->VIC | MINERIO FERRO | IMG_0300.MOV ---
# ATENCAO: item DIFERENTE do 40052 (mesma rota ELD->VIC, mesmo produto),
# mas a PRIMEIRA linha (20/06/2026) tem EXATAMENTE os mesmos valores do
# 40052 (TR85,86/tarifa82,75/frete58,05/MO16,80/MD7,90) - coincidencia
# notavel entre itens gemeos da mesma rota; header conferido com cuidado
# (numero "40050" claramente legivel, nao e erro de leitura). INTERMODAL
# FCA+EFVM, frete_rs_t=FRETE(FCA)+FRETE(EFVM). Varias linhas 2025 tem
# MANOBRA ORIGEM(FCA)=0,00 (anomalia/re-cadastro, mantida pois a soma
# fecha); uma linha (20/06/2025) mostra o padrao "antigo" MO=16,88. Video
# de 9,2s, 2 frames.
DADOS[40050] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 85.86, 82.75, 58.05, 16.80, 7.90),
    ("2025-09-20", "2027-12-31", 83.38, 82.85, 74.94, 0.00, 7.91),
    ("2025-08-20", "2027-12-31", 83.38, 82.55, 74.64, 0.00, 7.91),
    ("2025-07-20", "2027-12-31", 83.38, 82.47, 74.56, 0.00, 7.91),
    ("2025-06-20", "2027-12-31", 83.38, 82.52, 57.73, 16.88, 7.91),
]

# --- 11896 | C_2025_54 | VOB->VIC | PRO SIDERURGICO | IMG_0301.MOV ---
# Ferrovia unica EFVM. A linha mais recente (20/06/2026) veio com os
# componentes ainda em "Carregando" na tela E a tarifa exibida (82,75)
# coincidia suspeitosamente com a do item 40050/40052 (provavel artefato
# visual de transicao de pagina, nao dado real deste item) -> OMITIDA por
# seguranca. Manobra constante no periodo capturado: MO=13,25/MD=13,25.
# Video de 15,7s, 3 frames, so 0 e 2 revisados -> cobertura so de 2023-2024
# (GAP grande ate 2026).
DADOS[11896] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2024-08-20", "2024-12-31", 47.75, 66.98, 40.48, 13.25, 13.25),
    ("2024-05-20", "2024-12-31", 47.75, 67.05, 40.55, 13.25, 13.25),
    ("2024-04-20", "2024-12-31", 47.75, 66.98, 40.48, 13.25, 13.25),
    ("2024-03-20", "2024-12-31", 47.75, 66.89, 40.39, 13.25, 13.25),
    ("2024-02-20", "2024-12-31", 47.75, 66.39, 39.89, 13.25, 13.25),
    ("2024-01-20", "2024-12-31", 47.75, 66.22, 39.72, 13.25, 13.25),
    ("2023-12-20", "2024-12-31", 45.56, 67.36, 40.86, 13.25, 13.25),
]

# --- 40190 | C_2025_54 | VIC->VEB | PRO SIDERURGICO | IMG_0302.MOV ---
# ATENCAO: item DIFERENTE do 40287 (mesma rota VIC->VEB, mesmo produto, e
# TODOS os valores de tarifa/frete/MO/MD IDENTICOS aos do 40287), mas com
# vigencia do contrato diferente (16/04/2019 vs 01/01/2025 do 40287) - item
# numero conferido com zoom, "40190" claramente legivel, nao e erro de
# leitura. Provavel "item gemeo" da mesma rota com precificacao
# sincronizada. Ferrovia unica EFVM. Rebalanceio de manobra: MO=8,99/MD=
# 18,72 ate 20/05/2026, MO=13,25/MD=13,25 a partir do re-cadastro de
# 19/09/2025. Video de 15,2s, so 2 frames.
DADOS[40190] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.45, 44.74, 8.99, 18.72),
    ("2026-05-20", "2027-12-31", 51.27, 72.60, 44.89, 8.99, 18.72),
    ("2025-09-20", "2027-12-31", 48.98, 72.54, 46.04, 13.25, 13.25),
    ("2025-08-20", "2027-12-31", 48.98, 72.28, 45.78, 13.25, 13.25),
    ("2025-07-20", "2025-08-19", 48.98, 72.21, 45.71, 13.25, 13.25),
]

# --- 18241 | C_2025_53 | VAB->VIC | CARVAO MINERAL | IMG_0303.MOV ---
# Ferrovia unica EFVM. Linha mais recente (20/06/2026, 20/05/2026) veio com
# componentes "Carregando" e tarifa suspeitosamente igual a de outro item
# (72,45/72,60, mesma do 40287/40190 que sao de rota diferente) -> OMITIDAS
# por seguranca (provavel artefato de transicao de pagina). Manobra do
# periodo 2024 capturado varia bastante: 11,54/11,55 (mai-jun/2024),
# 10,52-10,55 (mar-abr/2024), 13,25/13,25 (dez/2023-fev/2024). Video de
# 13,9s, 4 frames, so 0 e 3 revisados -> GAP entre 2026 e 20/06/2024.
DADOS[18241] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2024-06-20", "2024-12-31", 70.20, 91.28, 68.19, 11.54, 11.55),
    ("2024-05-20", "2024-12-31", 70.20, 91.38, 68.29, 11.54, 11.55),
    ("2024-04-20", "2024-12-31", 70.20, 91.28, 70.19, 10.54, 10.55),
    ("2024-03-20", "2024-12-31", 70.20, 91.16, 70.12, 10.52, 10.52),
    ("2024-02-20", "2024-12-31", 70.20, 90.49, 63.99, 13.25, 13.25),
    ("2024-01-20", "2024-12-31", 70.20, 90.25, 63.75, 13.25, 13.25),
    ("2023-12-20", "2024-12-31", 66.97, 91.80, 65.30, 13.25, 13.25),
]

# --- 15804 | C_2025_54 | VIC->VMR | PRO SIDERURGICO | IMG_0304.MOV ---
# Rota inversa do 15802 (VMR->VIC). Ferrovia unica EFVM, rota curta (tarifas
# ~R$25/t). Video de 13,8s, 3 frames, so 0 e 2 revisados -> GAP entre
# 20/05/2026 e 20/06/2024 (2 anos). Manobra constante no periodo 2024:
# MD=11,91/MO=11,48 (mesmo padrao "simetrico" do 15802).
DADOS[15804] = [
    # vig_ini      vig_fim       TR      tarifa  frete  MO     MD
    ("2026-06-20", "2027-12-31", 34.40, 25.94, 13.96, 8.99, 2.99),
    ("2026-05-20", "2027-12-31", 34.40, 25.99, 14.01, 8.99, 2.99),
    ("2024-06-20", "2024-12-31", 31.37, 25.10, 1.71, 11.48, 11.91),
    ("2024-05-20", "2024-12-31", 31.37, 25.12, 1.73, 11.48, 11.91),
    ("2024-04-20", "2024-12-31", 31.37, 25.09, 1.70, 11.48, 11.91),
    ("2024-03-20", "2024-12-31", 31.37, 25.06, 1.67, 11.48, 11.91),
    ("2024-02-20", "2024-12-31", 31.37, 24.87, 1.48, 11.48, 11.91),
    ("2024-01-20", "2024-12-31", 31.37, 24.81, 1.42, 11.48, 11.91),
    ("2023-12-20", "2024-12-31", 29.93, 25.23, 1.84, 11.48, 11.91),
]

# --- 39394 | C_2025_53 | ECE->VIC | CALCARIO BRITADO | IMG_0305.MOV ---
# INTERMODAL EFVM+FCA com TRANSBORDO ORIGEM (FCA). frete_rs_t = FRETE(EFVM)+
# FRETE(FCA)+TRANSBORDO. manobra_destino=EFVM, manobra_origem=FCA. Linha
# mais recente (20/06/2026) veio com componentes "Carregando" e tarifa
# suspeita (25,94/25,99, igual ao item 15804 de rota totalmente diferente)
# -> OMITIDA por seguranca (artefato de transicao). Os splits variam MUITO
# entre re-cadastros da mesma vigencia (ex. 06/09/2024 com MD=13,73/MO=
# 18,71, bem diferente do padrao MD=11,95/MO=5,23 visto nas outras 3 linhas
# de set-out/2024) - mantidas como lidas. Video de 21,7s, 5 frames, so 0 e 4
# revisados.
DADOS[39394] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2024-10-20", "2024-12-31", 72.15, 88.02, 70.84, 5.23, 11.95),
    ("2024-09-20", "2024-12-31", 69.22, 87.85, 70.67, 5.23, 11.95),
    ("2024-09-06", "2024-12-31", 69.22, 87.86, 55.42, 18.71, 13.73),
    ("2024-08-01", "2024-12-31", 69.22, 87.83, 70.65, 5.23, 11.95),
]

# --- 14783 | C_2025_53 | EPM->VIC | MINERIO FERRO | IMG_0306.MOV ---
# INTERMODAL FCA+EFVM (origem FCA, destino EFVM). frete_rs_t = FRETE(EFVM)+
# FRETE(FCA). Manobra constante no periodo 2024: MO(FCA)=10,64/MD(EFVM)=
# 13,25. Video de 21,7s, 4 frames, so 0 e 3 revisados -> GAP entre
# 20/06/2026 e 20/03/2024.
DADOS[14783] = [
    # vig_ini      vig_fim       TR       tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 107.64, 72.53, 50.65, 13.98, 7.90),
    ("2024-03-20", "2024-12-31", 100.28, 68.94, 45.05, 10.64, 13.25),
    ("2024-02-20", "2024-12-31", 100.28, 68.43, 44.54, 10.64, 13.25),
    ("2024-01-20", "2024-12-31", 100.28, 68.25, 44.36, 10.64, 13.25),
    ("2023-12-20", "2024-12-31", 100.28, 69.43, 45.54, 10.64, 13.25),
]

# --- 40270 | C_2025_53 | VIC->EYU | PRO SIDERURGICO | IMG_0307.MOV ---
# ATENCAO: video complexo, navegou por VARIOS itens (revisitou 8391, passou
# pela pagina de LISTAGEM "Item Ferroviario" com 85 itens cadastrados, e
# so depois abriu este item 40270 - header confirmado com clareza em
# t=6,5s). Item GEMEO do 8391 (mesma rota VIC->EYU, MESMOS valores de
# tarifa/frete/MO/MD para as vigencias 2026, so difere no numero do item e
# na vigencia do contrato: 01/04/2021 aqui vs 19/05/2011 do 8391).
# INTERMODAL EFVM+FCA. So as 3 primeiras linhas foram capturadas com
# confianca (headers limpos em t=4-6,5s); o resto do video (frame 2, t=11s)
# mostrava dados de OUTRO item ainda nao identificado (TR51,20, mesma
# estrutura EFVM+FCA) - nao usado aqui por incerteza de qual item pertence.
DADOS[40270] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 53.59, 70.73, 40.75, 8.99, 20.99),
    ("2026-05-20", "2027-12-31", 53.59, 70.88, 40.90, 8.99, 20.99),
    ("2026-04-20", "2027-12-31", 53.59, 70.94, 40.96, 8.99, 20.99),
]

# --- 40264 | C_2025_54 | VIC->ECE | PRO SIDERURGICO | IMG_0308.MOV ---
# Item GEMEO do 8397 (mesma rota VIC->ECE, mesmo produto, MESMOS valores
# 2026 - so difere no numero do item e na vigencia do contrato: 01/01/2025
# aqui vs 19/05/2011 do 8397). INTERMODAL EFVM+FCA (origem EFVM, destino
# FCA). Rebalanceio de manobra: MO=8,99/MD=19,73 -> MO=13,25/MD=8,26 a
# partir de 19/09/2025. Video de 7,7s, 2 frames.
DADOS[40264] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 50.49, 63.15, 34.43, 8.99, 19.73),
    ("2025-09-20", "2027-12-31", 48.24, 63.21, 41.70, 13.25, 8.26),
    ("2025-08-20", "2027-12-31", 48.24, 62.98, 41.47, 13.25, 8.26),
]

# --- 40188 | C_2025_54 | VIC->VEB | PRO SIDERURGICO | IMG_0310.MOV ---
# Item GEMEO do 40287/40190 (mesma rota VIC->VEB, mesmo produto, valores
# muito proximos). Ferrovia unica EFVM. Rebalanceio de manobra: MO=8,99/
# MD=18,72 ate 20/05/2026, MO=13,25/MD=13,25 a partir do re-cadastro de
# 19/09/2025. Video de 6,7s, 2 frames.
DADOS[40188] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.86, 45.15, 8.99, 18.72),
    ("2026-05-20", "2027-12-31", 51.27, 73.01, 45.30, 8.99, 18.72),
    ("2025-09-20", "2027-12-31", 48.98, 72.96, 46.46, 13.25, 13.25),
    ("2025-08-20", "2027-12-31", 48.98, 72.70, 46.20, 13.25, 13.25),
    ("2025-07-20", "2025-08-19", 48.98, 72.63, 46.13, 13.25, 13.25),
]

# --- 40291 | C_2025_54 | VIC->EEL | PRO SIDERURGICO | IMG_0311.MOV ---
# Rota inversa/gemea do 15533 (EEL->VIC). INTERMODAL EFVM+FCA (origem EFVM,
# destino FCA). Rebalanceio de manobra: MO=8,99/MD=20,84 -> MO=13,25/
# MD=16,51 a partir do re-cadastro de 19/09/2025. Video de 7,2s, 2 frames.
DADOS[40291] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 52.30, 70.22, 40.39, 8.99, 20.84),
    ("2025-09-20", "2027-12-31", 49.98, 70.29, 40.53, 13.25, 16.51),
    ("2025-08-20", "2027-12-31", 49.98, 70.04, 40.28, 13.25, 16.51),
]

# --- 39808 | C_2025_53 | VTB->VIC | MINERIO FERRO | IMG_0312.MOV ---
# Ferrovia unica EFVM. Salto GRANDE de manobra entre 2026 (MO=18,76/MD=7,90)
# e 2024-2025 (MO=18,83-19,43/MD=22,07) - MD quase triplicou; nao e um
# rebalanceio suave como nos outros itens, GAP entre 20/05/2026 e 20/02/2025
# nao permite ver a transicao exata. Video de 10s, 2 frames.
DADOS[39808] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 33.18, 57.67, 31.01, 18.76, 7.90),
    ("2026-05-20", "2027-12-31", 33.18, 57.79, 31.13, 18.76, 7.90),
    ("2025-02-20", "2025-03-19", 31.70, 58.02, 16.52, 19.43, 22.07),
    ("2025-04-01", "2025-04-30", 31.70, 57.91, 16.41, 19.43, 22.07),
    ("2025-03-01", "2025-03-31", 31.70, 57.91, 16.41, 19.43, 22.07),
    ("2025-03-01", "2025-03-31", 31.70, 58.30, 16.80, 19.43, 22.07),  # 2o cadastro
    ("2024-12-20", "2025-02-28", 30.26, 58.30, 16.80, 19.43, 22.07),
    ("2024-12-20", "2024-12-31", 30.26, 58.30, 16.80, 19.43, 22.07),  # 2o cadastro
    ("2024-11-01", "2024-12-31", 30.26, 57.70, 16.80, 18.83, 22.07),
]

# --- 15535 | C_2025_54 | EPI->VIC | PRO SIDERURGICO | IMG_0313.MOV ---
# INTERMODAL FCA+EFVM (origem FCA, destino EFVM - mesmo par que 12950).
# frete_rs_t = FRETE(FCA)+FRETE(EFVM). Rebalanceio de manobra: MD(EFVM)=
# 8,99/MO(FCA)=20,90 em 2026, MD=13,25/MO=18,06 em 2023-2024 (janela exata
# de transicao nao capturada, GAP entre 20/02/2026 e 20/03/2024). Video de
# 17,6s, 4 frames, todos revisados (0 e 1 ghosted mas cross-checados com
# frames extras limpos).
DADOS[15535] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 83.15, 70.04, 40.15, 20.90, 8.99),
    ("2026-05-20", "2027-12-31", 83.15, 70.19, 40.30, 20.90, 8.99),
    ("2026-04-20", "2027-12-31", 83.15, 70.25, 40.36, 20.90, 8.99),
    ("2026-03-20", "2027-12-31", 83.15, 70.55, 40.66, 20.90, 8.99),
    ("2026-02-20", "2027-12-31", 83.15, 70.75, 40.86, 20.90, 8.99),
    ("2024-03-20", "2024-12-31", 77.48, 69.65, 38.34, 18.06, 13.25),
    ("2024-02-20", "2024-12-31", 77.48, 69.14, 37.83, 18.06, 13.25),
    ("2024-01-20", "2024-12-31", 77.48, 68.97, 37.66, 18.06, 13.25),
    ("2023-12-20", "2024-12-31", 77.46, 70.15, 38.84, 18.06, 13.25),
]

# --- 10305 | C_2025_53 | VTU->VIC | COQUE GROSSO | IMG_0314.MOV ---
# Ferrovia unica EFVM. Terceiro item COQUE GROSSO VTU->VIC visto (junto com
# 7924/18814) - "item gemeo" da mesma familia. Manobra varia bastante entre
# re-cadastros: 14,85/8,00 (2026), 11,95/11,95 (maioria 2024), 12,78/12,78
# (18/08/2024, cadastro isolado). Ha um re-cadastro datado 02/07/2024 para a
# vigencia 20/08/2024 (fora de ordem cronologica, mantido como lido). Video
# de 10,6s, 2 frames, GAP entre 20/05/2026 e 20/10/2024.
DADOS[10305] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 112.73, 89.88, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 97.59, 112.96, 90.11, 14.85, 8.00),
    ("2024-10-20", "2024-12-31", 88.99, 110.15, 86.25, 11.95, 11.95),
    ("2024-09-20", "2024-12-31", 88.99, 109.91, 86.01, 11.95, 11.95),
    ("2024-08-20", "2024-12-31", 88.99, 109.93, 84.37, 12.78, 12.78),
    ("2024-07-20", "2024-12-31", 88.99, 110.15, 86.25, 11.95, 11.95),
    ("2024-08-20", "2024-12-31", 88.99, 109.62, 85.72, 11.95, 11.95),  # re-cadastro (02/07/2024, fora de ordem)
    ("2024-05-20", "2024-12-31", 88.99, 109.74, 85.84, 11.95, 11.95),
    ("2024-04-20", "2024-12-31", 88.99, 109.76, 85.86, 11.95, 11.95),
]
# IMG_0318.MOV mostra os MESMOS cadastros de 2024 deste item 10305 (mesmos
# timestamps exatos) mas com tarifas 2026 DIFERENTES (108,39 em vez de
# 112,73 para 20/06/2026) e sem header legivel (spinner "carregando" durante
# todo o video, nunca resolveu) -> as linhas 2026 desse video NAO foram
# usadas por conflitarem com os valores ja confirmados aqui; possivel
# re-cadastro entre as duas gravacoes ou erro de leitura, fica como
# pendencia para revisao.

# --- 39630 | C_2025_53 | VTU->VIC | COQUE GROSSO | IMG_0316.MOV ---
# Item GEMEO do 18814 (mesma rota/produto, MESMOS valores 2026 e vigencia
# do contrato 20/07/2023 identica). Ferrovia unica EFVM. Manobra: 14,85/8,00
# em 2026; 11,95/11,95 na maior parte de 2025; 12,40/12,41 em dez/2024.
# Video de 9,3s, 2 frames, GAP entre 20/05/2026 e 20/03/2025.
DADOS[39630] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 113.99, 91.14, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 97.59, 114.23, 91.38, 14.85, 8.00),
    ("2025-03-20", "2025-04-30", 93.23, 116.59, 92.69, 11.95, 11.95),
    ("2025-02-20", "2025-03-19", 93.23, 115.65, 91.75, 11.95, 11.95),
    ("2025-04-01", "2025-04-30", 93.23, 115.44, 91.54, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.23, 115.44, 91.54, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.23, 113.79, 89.89, 11.95, 11.95),  # 2o cadastro
    ("2024-12-20", "2025-02-28", 88.99, 113.79, 88.98, 12.41, 12.40),
    ("2024-12-20", "2024-12-31", 88.99, 113.79, 88.98, 12.41, 12.40),  # 2o cadastro
]

# --- 40767 | C_2025_53 | ENG->VIC | MINERIO FERRO | IMG_0317.MOV ---
# Item GEMEO do 40765 (mesma rota/produto, MESMOS valores em todas as
# vigencias capturadas). INTERMODAL EFVM+FCA. Video de 10,1s, 2 frames.
DADOS[40767] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 84.28, 80.28, 57.87, 14.51, 7.90),
    ("2026-01-20", "2027-12-31", 84.28, 80.92, 58.51, 14.51, 7.90),
    ("2025-12-20", "2027-12-31", 84.28, 80.55, 58.14, 14.51, 7.90),
    ("2025-12-20", "2027-12-31", 84.28, 80.87, 58.34, 14.61, 7.92),  # 2o cadastro
    ("2025-11-20", "2027-12-31", 84.28, 80.32, 57.91, 14.51, 7.90),
    ("2025-10-20", "2027-12-31", 81.81, 80.37, 57.99, 14.51, 7.87),
]

# --- 40281 | C_2025_54 | VTU->VIC | PRO SIDERURGICO | IMG_0320.MOV ---
# Ferrovia unica EFVM. Rota inversa do 7901 (VIC->VTU). Video de 9,2s, so 2
# vigencias capturadas (frame1 igual ao frame0, sem avanco de scroll).
DADOS[40281] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 68.06, 87.30, 59.58, 18.73, 8.99),
    ("2026-05-20", "2027-12-31", 68.06, 87.48, 59.76, 18.73, 8.99),
]

# --- 40302 | C_2025_54 | ECE->VIC | PRO SIDERURGICO | IMG_0321.MOV ---
# Item GEMEO do 39843 (mesma rota ECE->VIC, MESMOS valores 2026). INTERMODAL
# EFVM+FCA (origem FCA, destino EFVM). Rebalanceio de manobra: MD=8,99/
# MO=19,73 -> MD=13,25/MO=8,26 a partir de 19/09/2025. Video de 7,5s, 2
# frames.
DADOS[40302] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 78.26, 62.31, 33.59, 19.73, 8.99),
    ("2025-09-20", "2027-12-31", 75.98, 62.38, 40.87, 8.26, 13.25),
    ("2025-08-20", "2027-12-31", 75.98, 62.15, 40.64, 8.26, 13.25),
]

# --- 40272 | C_2025_54 | VIC->EYB | PRO SIDERURGICO | IMG_0322.MOV ---
# Item GEMEO do 8388 (mesma rota VIC->EYB, MESMOS valores 2026). INTERMODAL
# EFVM+FCA (origem EFVM, destino FCA). Rebalanceio: MO=8,99/MD=34,43(45) ate
# 07/10/2025, depois MO=18,06/MD=18,06 (constante) a partir do re-cadastro
# de 19/09/2025. Ha um re-cadastro isolado (07/10/2025 11:59) com MO=0,00
# anomalo, nao usado (mantida a variante MO=8,99). Video de 4s, 2 frames.
DADOS[40272] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 53.51, 85.23, 41.81, 8.99, 34.43),
    ("2025-10-20", "2027-12-31", 51.12, 85.32, 41.88, 8.99, 34.45),
    ("2025-09-20", "2027-12-31", 51.12, 85.31, 41.87, 8.99, 34.45),  # padrao antigo
    ("2025-09-20", "2027-12-31", 51.12, 85.31, 49.19, 18.06, 18.06),  # padrao novo (rebalanceio 19/09/2025)
    ("2025-08-20", "2027-12-31", 51.12, 85.00, 48.88, 18.06, 18.06),
]

# --- 40285 | C_2025_54 | VIC->VEB | PRO SIDERURGICO | IMG_0323.MOV ---
# QUARTO item gemeo na rota VIC->VEB (junto com 8342/40287/40190/40188).
# Ferrovia unica EFVM. Rebalanceio de manobra: MO=8,99/MD=18,72(73) ate
# 20/11/2025, MO=13,25/MD=13,25 a partir do re-cadastro de 19/09/2025.
# Video de 4,7s, 2 frames.
DADOS[40285] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 51.27, 72.86, 45.15, 8.99, 18.72),
    ("2026-05-20", "2027-12-31", 51.27, 73.01, 45.30, 8.99, 18.72),
    ("2025-12-20", "2027-12-31", 48.98, 73.11, 45.40, 8.99, 18.72),
    ("2025-11-20", "2027-12-31", 48.98, 72.91, 45.20, 8.99, 18.72),
    ("2025-09-20", "2027-12-31", 48.98, 72.96, 45.24, 8.99, 18.73),  # 1o cadastro (07/10/2025)
    ("2025-09-20", "2027-12-31", 48.98, 72.96, 46.46, 13.25, 13.25),  # 2o cadastro (19/09/2025, rebalanceio)
    ("2025-08-20", "2027-12-31", 48.98, 72.70, 46.20, 13.25, 13.25),
]

# --- 40278 | C_2025_54 | VIC->VTU | PRO SIDERURGICO | IMG_0324.MOV ---
# Item GEMEO do 7901 (mesma rota VIC->VTU, MESMOS valores em toda a janela
# capturada). Ferrovia unica EFVM. Rebalanceio: MO=8,99/MD=18,73(74) ate
# 20/10/2025, MO=13,25/MD=13,25 a partir de 19/09/2025. Video de 3,7s, 2
# frames.
DADOS[40278] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 68.06, 87.69, 59.97, 8.99, 18.73),
    ("2026-05-20", "2027-12-31", 68.06, 87.87, 60.15, 8.99, 18.73),
    ("2026-01-20", "2027-12-31", 68.06, 88.38, 60.66, 8.99, 18.73),
    ("2025-12-20", "2027-12-31", 65.02, 87.98, 60.26, 8.99, 18.73),
    ("2025-11-20", "2027-12-31", 65.02, 87.73, 60.01, 8.99, 18.73),
    ("2025-10-20", "2027-12-31", 65.02, 87.79, 60.06, 8.99, 18.74),
    ("2025-09-20", "2027-12-31", 65.02, 87.78, 60.05, 8.99, 18.74),  # 1o cadastro
    ("2025-09-20", "2027-12-31", 65.02, 87.78, 61.28, 13.25, 13.25),  # 2o cadastro (rebalanceio)
    ("2025-08-20", "2027-12-31", 65.02, 87.46, 60.96, 13.25, 13.25),
]

# --- 39952 | C_2025_53 | ESQ->VIC | MINERIO FERRO | IMG_0325.MOV ---
# Item GEMEO do 39950 (mesma rota, MESMO valor 2026). INTERMODAL FCA+EFVM
# (origem FCA, destino EFVM). Manobra quase constante: MD(EFVM)=7,91,
# MO(FCA)=12,08 no periodo capturado. Video de 7,6s, 2 frames.
DADOS[39952] = [
    # vig_ini      vig_fim       TR      tarifa   frete   MO     MD
    ("2026-06-20", "2027-12-31", 94.15, 103.75, 83.78, 12.07, 7.90),
    ("2025-09-20", "2027-12-31", 91.41, 103.88, 83.89, 12.08, 7.91),
    ("2025-08-20", "2027-12-31", 91.41, 103.50, 83.51, 12.08, 7.91),
    ("2025-07-20", "2027-12-31", 91.41, 103.40, 83.41, 12.08, 7.91),
    ("2025-01-01", "2027-12-31", 91.41, 103.94, 83.95, 12.08, 7.91),
]

# =============================================================================
# ITENS NOVOS minerados dos videos IMG_0330-0338.MOV (continuacao apos
# interrupcao por erro de infraestrutura). Mesma disciplina/validacao dos
# itens acima. IMG_0326-0329.MOV e IMG_0336.MOV nao geraram itens novos
# (videos duplicados de itens ja existentes - ver notas em FLUXOS e, no
# caso do 39950, ampliacao do historico acima).
# =============================================================================

# --- 14789 | C_2025_53 | VWI->VIC | MINERIO FERRO | IMG_0330.MOV ---
# Ferrovia unica EFVM. Vigencia do contrato 01/04/2021-31/12/2027. Video de
# 15s, 20 frames, cobertura MUITO ampla: 20/06/2026 ate 20/12/2023 (quase
# todo o historico do item). Padrao de rebalanceio de manobra na janela
# usual: MD=7,90/91 e MO=13,92/93 ate 20/09/2025 (1o cadastro), depois
# MD=7,91 e MO=18,06 a partir do re-cadastro de 19/09/2025 - ATENCAO: aqui
# o campo que muda e MANOBRA ORIGEM (13,92->18,06), diferente da maioria dos
# outros itens onde e a MANOBRA DESTINO que salta; mantido como lido na
# tela (soma valida em todas as linhas). Ha uma 2a transicao de padrao em
# 19/05/2025 (MD salta de 7,91 para 13,25, mantendo MO=18,06) - tambem
# mantida como lida, soma confere. Linha 2025-07-20: soma 57,36 vs tarifa
# 57,38 (dif 0,02, dentro da tolerancia).
DADOS[14789] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 38.20, 57.54, 35.72, 13.92, 7.90),
    ("2026-05-20", "2027-12-31", 38.20, 57.66, 35.84, 13.92, 7.90),
    ("2026-04-20", "2027-12-31", 38.20, 57.71, 35.89, 13.92, 7.90),
    ("2026-03-20", "2027-12-31", 38.20, 57.96, 36.14, 13.92, 7.90),
    ("2026-02-20", "2027-12-31", 38.20, 58.13, 36.31, 13.92, 7.90),
    ("2026-02-20", "2027-12-31", 38.20, 58.39, 36.29, 14.12, 7.98),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 38.20, 58.00, 36.18, 13.92, 7.90),
    ("2025-12-20", "2027-12-31", 38.49, 57.74, 35.92, 13.92, 7.90),
    ("2025-12-20", "2027-12-31", 38.49, 58.00, 36.06, 14.02, 7.92),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 38.49, 57.58, 35.76, 13.92, 7.90),
    ("2025-09-20", "2027-12-31", 38.49, 57.62, 35.78, 13.93, 7.91),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 38.49, 57.62, 31.65, 18.06, 7.91),  # 2o cadastro (rebalanceio, 19/09/2025)
    ("2025-08-20", "2027-12-31", 38.49, 57.41, 31.44, 18.06, 7.91),
    ("2025-07-20", "2027-12-31", 38.49, 57.38, 31.39, 18.06, 7.91),  # soma 57,36 vs tarifa 57,38 (dif 0,02)
    ("2025-06-20", "2027-12-31", 36.49, 57.40, 31.43, 18.06, 7.91),
    ("2025-05-20", "2027-12-31", 36.49, 57.88, 26.57, 18.06, 13.25),  # 2a transicao: MD salta para 13,25
    ("2025-05-01", "2027-12-31", 36.49, 58.78, 27.47, 18.06, 13.25),
    ("2025-04-20", "2025-04-30", 38.49, 58.78, 27.47, 18.06, 13.25),
    ("2025-03-20", "2025-04-30", 38.49, 58.87, 27.56, 18.06, 13.25),
    ("2025-03-01", "2025-03-31", 36.49, 57.91, 26.60, 18.06, 13.25),
    ("2025-03-01", "2025-03-31", 36.49, 60.32, 29.01, 18.06, 13.25),  # 2o cadastro
    ("2024-12-20", "2025-02-28", 34.84, 60.32, 29.01, 18.06, 13.25),
    ("2024-11-20", "2024-12-31", 34.84, 59.96, 28.65, 18.06, 13.25),
    ("2024-10-20", "2024-12-31", 34.84, 59.70, 28.39, 18.06, 13.25),
    ("2024-09-20", "2024-12-31", 34.84, 59.57, 28.26, 18.06, 13.25),
    ("2024-08-20", "2024-12-31", 34.84, 59.58, 28.27, 18.06, 13.25),
    ("2024-07-20", "2024-12-31", 34.84, 59.70, 28.39, 18.06, 13.25),
    ("2024-06-20", "2024-12-31", 34.84, 59.41, 28.10, 18.06, 13.25),
    ("2024-05-20", "2024-12-31", 34.84, 59.47, 28.16, 18.06, 13.25),
    ("2024-04-20", "2024-12-31", 34.84, 59.41, 28.10, 18.06, 13.25),
    ("2024-03-20", "2024-12-31", 34.84, 59.33, 28.02, 18.06, 13.25),
    ("2024-02-20", "2024-12-31", 34.84, 58.89, 27.58, 18.06, 13.25),
    ("2024-01-20", "2024-12-31", 34.84, 58.74, 27.43, 18.06, 13.25),
    ("2023-12-20", "2024-12-31", 33.23, 59.75, 28.44, 18.06, 13.25),
]

# --- 39900 | C_2025_53 | VTU->VIC | CARVAO MINERAL | IMG_0331.MOV ---
# Ferrovia unica EFVM. Video de 6,8s, 11 frames, cobertura ampla: 20/06/2026
# ate 01/01/2025 (inicio do contrato). Rebalanceio de manobra na janela
# usual: MO=14,85/MD=7,99 ate 20/09/2025 (1o cadastro), depois MO=11,95/
# MD=11,95 (constante) a partir do re-cadastro de 19/09/2025.
DADOS[39900] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 80.03, 91.61, 68.77, 14.85, 7.99),
    ("2026-05-20", "2027-12-31", 80.03, 91.80, 68.96, 14.85, 7.99),
    ("2026-01-01", "2026-01-19", 80.03, 92.22, 69.38, 14.85, 7.99),  # cadastro retroativo (29/04/2026)
    ("2026-04-20", "2027-12-31", 80.03, 91.88, 69.04, 14.85, 7.99),
    ("2026-03-20", "2027-12-31", 80.03, 92.28, 69.44, 14.85, 7.99),
    ("2026-02-20", "2027-12-31", 80.03, 92.54, 69.70, 14.85, 7.99),
    ("2026-02-20", "2027-12-31", 80.03, 92.54, 69.49, 14.98, 8.07),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 78.45, 92.34, 69.50, 14.85, 7.99),  # 1o cadastro (04/02/2026)
    ("2026-01-20", "2027-12-31", 80.03, 92.34, 69.50, 14.85, 7.99),  # 2o cadastro (18/01/2026)
    ("2025-12-20", "2027-12-31", 78.45, 91.92, 69.08, 14.85, 7.99),
    ("2025-12-20", "2027-12-31", 78.45, 91.92, 69.03, 14.88, 8.01),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 78.45, 91.66, 68.82, 14.85, 7.99),
    ("2025-10-20", "2027-12-31", 78.45, 91.72, 68.88, 14.85, 7.99),
    ("2025-09-20", "2027-12-31", 78.45, 91.71, 68.87, 14.85, 7.99),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 78.45, 91.71, 67.81, 11.95, 11.95),  # 2o cadastro (rebalanceio, 19/09/2025)
    ("2025-08-20", "2027-12-31", 78.45, 91.38, 67.48, 11.95, 11.95),
    ("2025-07-20", "2027-12-31", 78.45, 91.30, 67.40, 11.95, 11.95),
    ("2025-06-20", "2027-12-31", 78.45, 91.36, 67.46, 11.95, 11.95),
    ("2025-05-20", "2027-12-31", 78.45, 92.13, 68.23, 11.95, 11.95),
    ("2025-01-01", "2027-12-31", 78.45, 93.57, 69.67, 11.95, 11.95),
]

# --- 19301 | C_2025_53 | VTU->VIC | COQUE GROSSO | IMG_0332.MOV ---
# Ferrovia unica EFVM. Vigencia do contrato 20/07/2023-31/12/2027. Video de
# 10,4s, 14 frames, cobertura MUITO ampla: 20/06/2026 ate 20/04/2024 (quase
# todo o historico). Rebalanceio de manobra na janela usual: MD=8,00/
# MO=14,85 ate 20/09/2025, depois MD=11,95/MO=11,95 (constante) a partir do
# re-cadastro de 19/09/2025. Ha uma vigencia retroativa curta (01/01/2025-
# 19/02/2025, cadastro 27/05/2025). Duas linhas (12/02/2026 e 18/01/2026)
# ficaram com leitura ambigua da soma (dif >0,05) e foram OMITIDAS por
# seguranca. Uma linha com vigencia_inicial ambigua ("20/02/2024" vs
# possivel "20/02/2025", cadastro 30/12/2024) tambem foi OMITIDA.
# IMG_0333.MOV e um video DUPLICADO do mesmo item (cabecalho identico).
# CORRIGIDO (24/07/2026, evidencia IMG_0561.MOV): a tabela abaixo estava
# gravada em ordem (MD, MO) mas o INSERT sempre le posicionalmente como
# (mo, md) -> os valores ficavam TROCADOS no banco (destino=14.85/
# origem=8.00 quando o correto e origem=14.85/destino=8.00, confirmado
# tambem pelos itens gemeos 18814/7924/10305/39630 e por nova captura de
# tela do item 39630 em IMG_0561.MOV mostrando MANOBRA ORIGEM=14,85 /
# MANOBRA DESTINO=8,00 de forma consistente). Colunas re-normalizadas
# para (MO, MD) como nos demais itens da familia.
DADOS[19301] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 113.99, 91.14, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 97.59, 114.23, 91.38, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 114.39, 91.54, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 115.65, 92.75, 14.88, 8.01),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 93.23, 114.07, 91.22, 14.85, 8.00),
    ("2025-10-20", "2027-12-31", 93.23, 114.14, 91.29, 14.85, 8.00),
    ("2025-09-20", "2027-12-31", 93.23, 114.13, 91.28, 14.85, 8.00),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 93.23, 114.13, 90.23, 11.95, 11.95),  # 2o cadastro (rebalanceio, 19/09/2025)
    ("2025-08-20", "2027-12-31", 93.23, 113.71, 89.81, 11.95, 11.95),
    ("2025-07-20", "2027-12-31", 93.23, 113.60, 89.70, 11.95, 11.95),
    ("2025-06-20", "2027-12-31", 93.23, 113.67, 89.77, 11.95, 11.95),
    ("2025-01-01", "2025-02-19", 93.23, 115.44, 91.54, 11.95, 11.95),  # vig retroativa curta (cad 27/05/2025)
    ("2025-05-20", "2027-12-31", 93.23, 114.62, 90.72, 11.95, 11.95),
    ("2025-05-01", "2027-12-31", 93.23, 116.41, 92.51, 11.95, 11.95),
    ("2025-04-20", "2025-04-30", 93.23, 116.41, 92.51, 11.95, 11.95),
    ("2025-03-20", "2025-04-30", 93.23, 116.59, 92.69, 11.95, 11.95),
    ("2025-02-20", "2025-03-19", 93.23, 115.65, 91.75, 11.95, 11.95),
    ("2025-04-01", "2025-04-30", 93.23, 115.44, 91.54, 11.95, 11.95),
    ("2025-03-01", "2025-03-31", 93.23, 115.44, 91.54, 11.95, 11.95),  # 1o cadastro
    ("2025-03-01", "2025-03-31", 93.23, 113.79, 89.89, 11.95, 11.95),  # 2o cadastro
    ("2024-12-20", "2024-12-31", 88.99, 113.79, 88.98, 12.41, 12.40),
    ("2024-10-20", "2024-12-31", 88.99, 112.62, 88.72, 11.95, 11.95),
    ("2024-09-20", "2024-12-31", 88.99, 112.37, 88.47, 11.95, 11.95),
    ("2024-08-20", "2024-12-31", 88.99, 112.39, 86.83, 12.78, 12.78),
    ("2024-07-20", "2024-12-31", 88.99, 112.62, 88.72, 11.95, 11.95),
    ("2024-06-20", "2024-12-31", 88.99, 112.08, 88.18, 11.95, 11.95),
    ("2024-05-20", "2024-12-31", 88.99, 112.20, 88.30, 11.95, 11.95),
    ("2024-04-20", "2024-12-31", 88.99, 112.23, 88.33, 11.95, 11.95),
]

# --- 39554 | C_2025_53 | VMR->VIC | MINERIO FERRO | IMG_0334.MOV ---
# Ferrovia unica EFVM, MAS SEM MANOBRA ORIGEM (so 2 servicos: FRETE e
# MANOBRA DESTINO - estacao provavelmente sem manobra de origem tarifada).
# frete_rs_t = FRETE, manobra_origem = None. Video de 7,7s, 10 frames,
# cobertura ampla: 20/06/2026 ate 28/10/2024. Rebalanceio: MD=7,90/91
# constante ate 19/05/2025, depois MD=13,25/13,77(so na 1a linha) a partir
# do re-cadastro de 19/05/2025 - transicao mais cedo que a janela usual
# (set/2025) vista nos outros itens.
DADOS[39554] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-06-20", "2027-12-31", 19.87, 23.94, 16.04, None, 7.90),
    ("2026-05-20", "2027-12-31", 19.87, 23.99, 16.09, None, 7.90),
    ("2026-04-20", "2027-12-31", 19.87, 24.01, 16.11, None, 7.90),
    ("2026-03-20", "2027-12-31", 19.87, 24.11, 16.21, None, 7.90),
    ("2026-02-20", "2027-12-31", 19.87, 24.18, 16.28, None, 7.90),
    ("2026-01-20", "2027-12-31", 19.87, 24.13, 16.23, None, 7.90),
    ("2025-12-20", "2027-12-31", 18.98, 24.02, 16.12, None, 7.90),
    ("2025-11-20", "2027-12-31", 18.98, 23.95, 16.05, None, 7.90),
    ("2025-09-20", "2027-12-31", 18.98, 23.97, 16.06, None, 7.91),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 18.98, 23.97, 16.06, None, 7.91),  # 2o cadastro (rebalanceio, 19/09/2025) - mesmos valores
    ("2025-08-20", "2027-12-31", 18.98, 23.88, 15.97, None, 7.91),
    ("2025-07-20", "2027-12-31", 18.98, 23.86, 15.95, None, 7.91),
    ("2025-06-20", "2027-12-31", 18.98, 23.88, 15.97, None, 7.91),
    ("2025-05-20", "2027-12-31", 18.98, 24.08, 10.83, None, 13.25),  # rebalanceio (MD salta para 13,25)
    ("2025-05-01", "2027-12-31", 18.98, 24.46, 11.21, None, 13.25),
    ("2025-04-20", "2025-04-30", 18.98, 24.46, 11.21, None, 13.25),
    ("2025-03-20", "2025-04-30", 18.98, 24.50, 11.25, None, 13.25),
    ("2025-02-20", "2025-03-19", 18.98, 24.03, 10.78, None, 13.25),
    ("2025-04-01", "2025-04-30", 18.98, 23.99, 10.74, None, 13.25),
    ("2025-03-01", "2025-03-31", 18.98, 23.99, 10.74, None, 13.25),  # 1o cadastro
    ("2025-03-01", "2025-03-31", 18.98, 24.14, 10.89, None, 13.25),  # 2o cadastro
    ("2024-12-20", "2025-02-28", 18.12, 24.14, 10.89, None, 13.25),
    ("2024-12-20", "2024-12-31", 18.12, 24.14, 10.89, None, 13.25),
    ("2024-10-28", "2024-12-31", 18.12, 23.90, 10.13, None, 13.77),
]

# --- 10019 | C_2025_53 | EPI->VIC | SUCATA | IMG_0335.MOV ---
# INTERMODAL EFVM+FCA (origem FCA/EPI, destino EFVM/VIC). frete_rs_t =
# FRETE(EFVM) + FRETE(FCA). Vigencia do contrato 01/08/2016-31/12/2027
# (item antigo). Video de 19,6s, 26 frames, cobertura ampla: 20/06/2026 ate
# 20/12/2023. Rebalanceio de manobra na janela usual: MO(FCA)=12,47/
# MD(EFVM)=11,95 ate 20/08/2024, depois MO=12,47/MD=11,95 continua
# praticamente igual em boa parte do periodo recente, com pequenas
# variacoes (10,02-10,08) em alguns re-cadastros pontuais de dez/2025-
# fev/2026. Duas linhas com leitura muito prejudicada por ghosting/blur de
# scroll (28/02/2025 e 15/09/2024) foram OMITIDAS por seguranca, criando
# pequenos gaps no historico entre mar/2025-abr/2025 e abr/2024-ago/2024.
DADOS[10019] = [
    # vig_ini      vig_fim       TR       tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 106.58, 76.84, 56.86, 9.99, 9.99),
    ("2026-02-20", "2027-12-31", 106.58, 77.61, 57.45, 10.08, 10.08),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 106.58, 77.44, 57.46, 9.99, 9.99),
    ("2025-12-20", "2027-12-31", 106.58, 77.09, 57.11, 9.99, 9.99),
    ("2025-12-20", "2027-12-31", 106.58, 77.09, 57.05, 10.02, 10.02),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 106.58, 76.87, 56.89, 9.99, 9.99),
    ("2025-09-20", "2027-12-31", 103.48, 76.92, 56.94, 9.99, 9.99),  # 1o cadastro (08/10/2025)
    ("2025-09-20", "2027-12-31", 103.48, 76.92, 52.50, 12.47, 11.95),  # 2o cadastro (rebalanceio, 19/09/2025)
    ("2025-08-20", "2027-12-31", 103.48, 76.62, 52.20, 12.47, 11.95),
    ("2025-07-20", "2027-12-31", 103.48, 76.57, 52.15, 12.47, 11.95),
    ("2025-05-20", "2027-12-31", 103.48, 77.26, 52.84, 12.47, 11.95),
    ("2025-05-01", "2027-12-31", 103.48, 78.47, 54.05, 12.47, 11.95),
    ("2025-04-20", "2025-04-30", 103.48, 78.47, 54.05, 12.47, 11.95),
    ("2025-03-20", "2025-04-30", 103.48, 78.59, 54.17, 12.47, 11.95),
    ("2024-12-20", "2025-02-28", 103.48, 76.97, 52.53, 12.47, 11.95),
    ("2024-11-20", "2024-12-31", 103.48, 76.51, 52.09, 12.47, 11.95),
    ("2024-10-20", "2024-12-31", 103.48, 76.18, 51.76, 12.47, 11.95),
    ("2024-03-20", "2024-12-31", 99.24, 75.70, 51.28, 12.47, 11.95),
    ("2024-02-20", "2024-12-31", 99.24, 75.14, 50.72, 12.47, 11.95),
    ("2024-01-20", "2024-12-31", 99.24, 74.94, 50.52, 12.47, 11.95),
    ("2023-12-20", "2024-12-31", 99.24, 76.22, 51.80, 12.47, 11.95),
]

# --- 19299 | C_2025_53 | VTU->VIC | COQUE GROSSO | IMG_0337.MOV ---
# Ferrovia unica EFVM (nao intermodal, apesar do produto/rota parecidos com
# 19301). Vigencia do contrato 20/07/2023-31/12/2027. Video de 14,5s, 19
# frames, cobertura MUITO ampla: 20/06/2026 ate 20/04/2024 (quase todo o
# historico). Rebalanceio de manobra na janela usual: MD=8,00/MO=14,85 ate
# 20/09/2025, depois MD=11,95/MO=11,95 (constante) a partir do re-cadastro
# de 19/09/2025. Linha 2025-09-20 (1o cadastro): frete lido como 82,13 mas
# a soma so fecha com 82,03 (tarifa 104,88) - usado o valor derivado
# (provavel troca de digito 1<->0 na leitura).
# CORRIGIDO (24/07/2026, evidencia IMG_0561.MOV): mesma correcao de ordem
# de colunas aplicada ao item 19301 (ver nota acima) - tabela estava em
# ordem (MD, MO), re-normalizada para (MO, MD).
DADOS[19299] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 97.59, 104.86, 82.01, 14.85, 8.00),
    ("2026-05-20", "2027-12-31", 97.59, 105.08, 82.23, 14.85, 8.00),
    ("2026-04-20", "2027-12-31", 97.59, 105.17, 82.32, 14.85, 8.00),
    ("2026-03-20", "2027-12-31", 97.59, 105.63, 82.78, 14.85, 8.00),
    ("2026-02-20", "2027-12-31", 97.59, 105.93, 83.08, 14.85, 8.00),
    ("2026-02-20", "2027-12-31", 97.59, 105.91, 82.86, 14.98, 8.07),  # 2o cadastro (12/02/2026)
    ("2026-01-20", "2027-12-31", 97.59, 105.70, 82.85, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 105.22, 82.37, 14.85, 8.00),
    ("2025-12-20", "2027-12-31", 93.23, 105.21, 82.32, 14.88, 8.01),  # 2o cadastro (12/12/2025)
    ("2025-11-20", "2027-12-31", 93.23, 104.92, 82.07, 14.85, 8.00),
    ("2025-10-20", "2027-12-31", 93.23, 104.99, 82.14, 14.85, 8.00),
    ("2025-09-20", "2027-12-31", 93.23, 104.88, 82.03, 14.85, 8.00),  # 1o cadastro - frete derivado (ver nota)
    ("2025-09-20", "2027-12-31", 93.23, 104.98, 81.08, 11.95, 11.95),  # 2o cadastro (rebalanceio, 19/09/2025)
    ("2025-08-20", "2027-12-31", 93.23, 104.60, 80.70, 11.95, 11.95),
    ("2025-07-20", "2027-12-31", 93.23, 104.50, 80.60, 11.95, 11.95),
    ("2025-06-20", "2027-12-31", 93.23, 104.57, 80.67, 11.95, 11.95),
    ("2025-05-20", "2027-12-31", 93.23, 105.45, 81.55, 11.95, 11.95),
    ("2025-05-01", "2027-12-31", 93.23, 107.10, 83.20, 11.95, 11.95),
    ("2025-04-20", "2025-04-30", 93.23, 107.10, 83.20, 11.95, 11.95),
    ("2025-03-20", "2025-04-30", 93.23, 107.26, 83.36, 11.95, 11.95),
    ("2024-10-20", "2024-12-31", 88.99, 102.46, 78.56, 11.95, 11.95),
    ("2024-09-20", "2024-12-31", 88.99, 102.23, 78.33, 11.95, 11.95),
    ("2024-08-20", "2024-12-31", 88.99, 102.25, 76.69, 12.78, 12.78),
    ("2024-07-20", "2024-12-31", 88.99, 102.46, 78.56, 11.95, 11.95),
    ("2024-06-20", "2024-12-31", 88.99, 101.96, 78.06, 11.95, 11.95),
    ("2024-05-20", "2024-12-31", 88.99, 102.07, 78.17, 11.95, 11.95),
    ("2024-04-20", "2024-12-31", 88.99, 102.09, 78.19, 11.95, 11.95),
]

# --- 40304 | C_2025_54 | ECE->VIC | PRO SIDERURGICO | IMG_0338.MOV ---
# INTERMODAL EFVM+FCA (mesmo par que 40264/40302/8397: origem FCA, destino
# EFVM - "CAPITAO EDUARDO FCA" na tela, ja indicando lado FCA). frete_rs_t =
# FRETE(EFVM) + FRETE(FCA). Video de 14,1s, 18 frames, mas item NOVO
# (criado ~ago/2025, como os itens gemeos 40264/40302/40272): cobertura
# apenas 20/06/2026 ate 20/08/2025 (o video ficou repetindo muitos
# re-cadastros identicos em torno de 19/09/2025 sem progredir mais para
# tras). Rebalanceio de manobra: MO(FCA)=19,73(74)/MD(EFVM)=8,99 ate
# 07/10/2025, depois MO=8,26/MD=13,25 a partir do re-cadastro de
# 19/09/2025 (mesmo padrao dos itens gemeos da mesma rota).
DADOS[40304] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO     MD
    ("2026-06-20", "2027-12-31", 78.28, 62.75, 34.03, 19.73, 8.99),
    ("2026-05-20", "2027-12-31", 78.28, 62.88, 34.16, 19.73, 8.99),
    ("2026-04-20", "2027-12-31", 78.28, 62.93, 34.21, 19.73, 8.99),
    ("2026-03-20", "2027-12-31", 78.28, 63.20, 34.48, 19.73, 8.99),
    ("2025-10-20", "2027-12-31", 75.98, 62.81, 34.08, 19.74, 8.99),  # 1o cadastro (07/10/2025)
    ("2025-09-20", "2027-12-31", 75.98, 62.81, 41.30, 8.26, 13.25),  # 2o cadastro (rebalanceio, 19/09/2025)
    ("2025-08-20", "2027-12-31", 75.98, 62.58, 41.07, 8.26, 13.25),
]

# --- 8382 | C_2025_54 | VIC->ECA | PRO SIDERURGICO | IMG_0562.MOV ---
# Item pendente (sem abertura de manobra ate 24/07/2026). INTERMODAL
# EFVM+FCA (FRETE EFVM 45,61 + FRETE FCA 2,31 = 47,92; MANOBRA ORIGEM(EFVM)
# = 0,00; MANOBRA DESTINO(FCA) = 25,98). Video de 36,9s com scroll extenso,
# mas so a linha mais recente (17/07/2026) foi transcrita com confianca
# (header nitido); linhas mais antigas do mesmo item (a partir de 19/09/2025,
# outro item ferroviario na mesma rota, manobra 13,25/13,25 simetrica)
# aparecem no mesmo video mas SEM certeza de que sao do MESMO item 8382 -
# omitidas por seguranca, pendencia para revisao.
DADOS[8382] = [
    # vig_ini      vig_fim       TR      tarifa  frete   MO    MD
    ("2026-07-20", "2027-12-31", 51.02, 73.90, 47.92, 0.00, 25.98),
]

# ---------------------------------------------------------------------------
def validar(dados):
    """frete + MO + (MD ou 0) == tarifa_contrato (tolerancia 0,05)."""
    problemas = []
    for item, linhas in dados.items():
        for ln in linhas:
            vi, vf, tr, tarifa, frete, mo, md = ln
            soma = (frete or 0) + (mo or 0) + (md or 0)
            if abs(soma - tarifa) > 0.05:
                problemas.append(
                    f"item {item} vig {vi}: soma servicos {soma:.2f} "
                    f"!= tarifa_contrato {tarifa:.2f}"
                )
    return problemas


def main():
    problemas = validar(DADOS)
    if problemas:
        print("INCONSISTENCIAS DE SOMA (revisar antes de gravar):")
        for p in problemas:
            print("  -", p)
        raise SystemExit("Abortado: corrija as inconsistencias acima.")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS usiminas_precos_contratuais")
    cur.execute(
        """
        CREATE TABLE usiminas_precos_contratuais (
            item_ferroviario     INTEGER,
            contrato             TEXT,
            origem               TEXT,
            origem_nome          TEXT,
            destino              TEXT,
            destino_nome         TEXT,
            produto              TEXT,
            vigencia_inicial     TEXT,
            vigencia_final       TEXT,
            valor_tr_antt        REAL,
            tarifa_contrato      REAL,
            frete_rs_t           REAL,
            manobra_origem_rs_t  REAL,
            manobra_destino_rs_t REAL,
            fonte                TEXT
        )
        """
    )
    LOTE_550_562_ITENS = {8382}
    for item, linhas in DADOS.items():
        meta = FLUXOS[item]
        fonte_item = FONTE_LOTE_550_562 if item in LOTE_550_562_ITENS else FONTE
        for (vi, vf, tr, tarifa, frete, mo, md) in linhas:
            cur.execute(
                """INSERT INTO usiminas_precos_contratuais VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item, meta["contrato"], meta["origem"], meta["origem_nome"],
                 meta["destino"], meta["destino_nome"], meta["produto"],
                 vi, vf, tr, tarifa, frete, mo, md, fonte_item),
            )
    conn.commit()
    n = cur.execute("SELECT COUNT(*) FROM usiminas_precos_contratuais").fetchone()[0]
    print(f"usiminas_precos_contratuais criada com {n} linhas.")
    conn.close()


if __name__ == "__main__":
    main()
