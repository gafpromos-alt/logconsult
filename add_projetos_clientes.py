# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Acessórias abertas por cliente + captura de potenciais
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: "01_Dados_Tarifas/LogConsult (tarifas por cliente).xlsx" (18 abas — já é fonte parcial
do Radar via build_radar.py, aba "Portfólio"). Pedido do usuário: trazer a "abertura" de
acessórias (itens individuais como Manobra origem/destino, Direito de Passagem etc.) das
abas cliente-a-cliente, porque vários fluxos no banco só têm o total de acessórias, sem
abertura — e qualquer outra informação rica encontrada nas abas.

Mapeamento das 18 abas (nem todas viraram dado — ver ressalvas):
  - 7 abas com abertura de acessórias utilizável, 3 formatos de layout distintos:
    · multi-fluxo em colunas: CMOC, Gerdau, Cenibra
    · single-fluxo simples: Selecta, Selecta retro, LD
    · single-fluxo mensal (usa a coluna anual): Caramuru
  - Nova Agri: 2 fluxos (TO, MT) com abertura mensal + linha TOTAL (anual) — mesmo padrão,
    tratado como "multi-fluxo" usando a linha TOTAL de cada um.
  - Agrex: 1 fluxo mensal SEM linha TOTAL — anualizado aqui via média ponderada pelo volume
    dos meses que têm volume registrado (4 de 12 meses não têm volume — cobertura parcial,
    sinalizada no campo `cobertura`).
  - Vibra / Ipiranga: abas idênticas ("VIBRA" nas duas) com a seção Abertura em branco —
    sem dado usável, não entram.
  - MosaicTIPA: NÃO é "acessórias aberto" de cliente atual — é um rastreador mês a mês de
    tarifa de CONCORRENTES observada no terminal Mosaic Palmeirante (captura de clientes
    potenciais), com cenário de ganho se a VLI capturar o frete. Vai pra tabela separada
    `captura_clientes_potenciais`.
  - Mosaic Tiplam: aba do mesmo tipo mas praticamente vazia (sem preenchimento) — não entra.
  - Nova Agri / Agrex também têm colunas "Cenário otimista/moderado" (ganho de captura) —
    não usadas aqui (já cobertas pelo par otimista/moderado padrão do resto do painel via
    Comparativo/Acessórias); só a abertura tarifária delas entra nas tabelas de projeto.
  - Aba "Acessorias" (mín/média/máx/desvio por ferrovia×mercadoria) é cópia de referência das
    MESMAS tabelas oficiais já ingeridas via add_acessorias_mercado.py — não reingerida aqui.
  - Aba "Simulado manobras": tabela solta de referência de tarifas de manobra por terminal
    (Tiplam, SL Tegram etc.), sem cliente/fluxo associado — não ingerida (baixo valor sozinha).

Uso:  python3 add_projetos_clientes.py
"""
import pathlib
import sqlite3

import pandas as pd

BASE = pathlib.Path(__file__).resolve().parent
DADOS_DIR = BASE.parent / "01_Dados_Tarifas"
DB = BASE / "logconsult.db"
XLSX = DADOS_DIR / "LogConsult (tarifas por cliente).xlsx"
FONTE = "LogConsult (tarifas por cliente).xlsx — planilha interna de projetos por cliente"


def _raw(sheet):
    return pd.read_excel(XLSX, sheet_name=sheet, header=None)


# ---------------------------------------------------------------- formato A: multi-fluxo em colunas
def parse_multiflow(sheet, cliente, itens_abertura, vigencia_row=11):
    df = _raw(sheet)
    flows = [c for c in range(2, df.shape[1]) if pd.notna(df.iat[2, c])]
    flow_tarifas, flow_abertura = [], []
    for c in flows:
        fluxo = str(df.iat[2, c]).strip()
        vig = df.iat[vigencia_row, 2] if c == flows[0] else None  # vigência costuma ser 1 valor só (col2), não por fluxo
        flow_tarifas.append({
            "cliente": cliente, "fluxo": fluxo,
            "tarifa_total": df.iat[3, c], "teto": df.iat[4, c], "frete": df.iat[5, c],
            "acessorias": df.iat[6, c], "ipoa": df.iat[8, c],
            "distancia_km": df.iat[9, c] if pd.notna(df.iat[9, c]) else None,
            # CORREÇÃO (22/jul/2026): a coluna volume_ano_ktu, em TODA a base, é gravada em
            # TONELADAS/ano (ver painel_template.html:1909 "planilha grava em t/ano" — o front
            # divide por 1000 pra exibir em kt). A linha "Volume ano ktu" das abas CMOC/Gerdau
            # (450.000/75.000/60.000 e 1.400.000/250.000) JÁ está nessa mesma convenção de
            # toneladas — plausível pro volume real dessas rotas. Uma correção anterior desta
            # sessão dividiu por 1000 aqui por engano (achando "450 milhões de t" impossível,
            # quando na verdade eram 450 mil t — o "milhões" foi erro de leitura, não da
            # planilha), fazendo o volume exibido cair pra ~0 ("sem volume" na UI, reportado
            # pelo usuário). Revertido: usa o valor bruto da planilha, sem dividir.
            "volume_ano_ktu": df.iat[10, c] if pd.notna(df.iat[10, c]) else None,
            "vigencia": str(vig) if pd.notna(vig) else None, "fonte": FONTE,
        })
        for row_idx, item_nome in itens_abertura:
            v = df.iat[row_idx, c]
            if pd.notna(v):
                flow_abertura.append({"cliente": cliente, "fluxo": fluxo, "item": item_nome,
                                       "valor_rs_t": round(float(v), 2), "fonte": FONTE})
    return flow_tarifas, flow_abertura


# ---------------------------------------------------------------- formato B: single-fluxo simples
def parse_singleflow(sheet, cliente, abertura_start, itens_abertura, vol_row=None):
    df = _raw(sheet)
    vig = None
    for r in range(3, 8):
        for c in range(2, min(df.shape[1], 6)):
            v = df.iat[r, c]
            if isinstance(v, pd.Timestamp):
                vig = v
    tarifa = {
        "cliente": cliente, "fluxo": cliente,
        "tarifa_total": df.iat[3, 2], "teto": df.iat[4, 2], "frete": df.iat[5, 2],
        "acessorias": df.iat[6, 2], "ipoa": df.iat[7, 2],
        "distancia_km": None,
        "volume_ano_ktu": df.iat[vol_row, 2] if vol_row is not None and pd.notna(df.iat[vol_row, 2]) else None,
        "vigencia": str(vig.date()) if vig is not None else None, "fonte": FONTE,
    }
    abertura = []
    for row_idx, item_nome in itens_abertura:
        v = df.iat[row_idx, 2]
        if pd.notna(v):
            abertura.append({"cliente": cliente, "fluxo": cliente, "item": item_nome,
                              "valor_rs_t": round(float(v), 2), "fonte": FONTE})
    return [tarifa], abertura


# ---------------------------------------------------------------- Caramuru: single-fluxo mensal (usa col. anual)
def parse_caramuru():
    df = _raw("Caramuru")
    cliente = "CARAMURU"
    col = 15  # coluna "2025" (total anual)
    tarifa = {
        "cliente": cliente, "fluxo": cliente,
        "tarifa_total": df.iat[4, col], "teto": df.iat[5, col], "frete": df.iat[6, col],
        "acessorias": df.iat[7, col], "ipoa": df.iat[8, col], "distancia_km": df.iat[9, col],
        "volume_ano_ktu": df.iat[10, col], "vigencia": str(df.iat[11, 2]).split(" ")[0], "fonte": FONTE,
    }
    abertura = [
        {"cliente": cliente, "fluxo": cliente, "item": "Manobra destino", "valor_rs_t": round(float(df.iat[14, col]), 2), "fonte": FONTE},
        {"cliente": cliente, "fluxo": cliente, "item": "Manobra origem", "valor_rs_t": round(float(df.iat[15, col]), 2), "fonte": FONTE},
        {"cliente": cliente, "fluxo": cliente, "item": "DP Rumo/MRS", "valor_rs_t": round(float(df.iat[17, col]), 2), "fonte": FONTE},
    ]
    return [tarifa], abertura


# ---------------------------------------------------------------- Nova Agri: 2 fluxos, linha TOTAL
def parse_nova_agri():
    df = _raw("Nova Agri")
    cliente = "NOVA AGRI"
    blocos = [("TO", 15), ("MT", 30)]  # (nome do fluxo, linha TOTAL)
    tarifas, abertura = [], []
    for fluxo, row in blocos:
        tarifas.append({
            "cliente": cliente, "fluxo": fluxo,
            "tarifa_total": df.iat[row, 2], "teto": df.iat[row, 7], "frete": df.iat[row, 6],
            "acessorias": round(float(df.iat[row, 3]) + float(df.iat[row, 4]) + float(df.iat[row, 5]), 2),
            "ipoa": df.iat[row, 9], "distancia_km": None,
            "volume_ano_ktu": df.iat[row, 10], "vigencia": None, "fonte": FONTE,
        })
        for c, item_nome in [(3, "Manobra Origem"), (4, "Manobra Destino"), (5, "Baldeação")]:
            v = df.iat[row, c]
            if pd.notna(v) and float(v) != 0:
                abertura.append({"cliente": cliente, "fluxo": fluxo, "item": item_nome,
                                  "valor_rs_t": round(float(v), 2), "fonte": FONTE})
    return tarifas, abertura


# ---------------------------------------------------------------- Agrex: 1 fluxo mensal, sem linha TOTAL
def parse_agrex():
    df = _raw("Agrex")
    cliente, fluxo = "AGREX", "AGREX"
    meses = df.iloc[4:16].copy()
    meses.columns = range(meses.shape[1])
    com_vol = meses[meses[9].notna()]
    n_meses_vol = len(com_vol)
    vol_tot = com_vol[9].sum()
    def wavg(col):
        return float((com_vol[col] * com_vol[9]).sum() / vol_tot)
    tarifa = {
        "cliente": cliente, "fluxo": fluxo,
        "tarifa_total": round(wavg(2), 2), "teto": round(wavg(6), 2), "frete": None,
        "acessorias": round(wavg(3) + wavg(4), 2), "ipoa": round(wavg(8), 2),
        "distancia_km": None, "volume_ano_ktu": round(float(vol_tot), 0),
        "vigencia": None, "fonte": FONTE,
        "cobertura": f"média ponderada por volume — só {n_meses_vol} de 12 meses têm volume registrado na planilha",
    }
    abertura = [
        {"cliente": cliente, "fluxo": fluxo, "item": "Manobra Origem", "valor_rs_t": round(wavg(3), 2), "fonte": FONTE},
        {"cliente": cliente, "fluxo": fluxo, "item": "Manobra Destino", "valor_rs_t": round(wavg(4), 2), "fonte": FONTE},
    ]
    return [tarifa], abertura


# ---------------------------------------------------------------- MosaicTIPA: captura de clientes potenciais
def parse_captura_mosaic():
    df = _raw("MosaicTIPA")
    terminal = "Mosaic Palmeirante"
    concorrentes = {2: "AGROJEM", 3: "EUROCHEM", 4: "ALZ", 5: "FERTGROW", 6: "ARAGUAIA", 7: "MOSAIC"}
    rows_tarifa, rows_mes = [], []
    for r in range(4, 16):
        mes = int(df.iat[r, 1])
        vol = df.iat[r, 8]
        for c, nome in concorrentes.items():
            v = df.iat[r, c]
            if pd.notna(v):
                rows_tarifa.append({"terminal": terminal, "mes": mes, "concorrente": nome,
                                     "tarifa_rs_t": round(float(v), 2), "fonte": FONTE})
        rows_mes.append({"terminal": terminal, "mes": mes,
                          "volume_ktu": float(vol) if pd.notna(vol) else None,
                          "tarifa_referencia_otimista_rs_t": round(float(df.iat[r, 10]), 2) if pd.notna(df.iat[r, 10]) else None,
                          "ganho_potencial_otimista_ano": round(float(df.iat[r, 12]), 2) if pd.notna(df.iat[r, 12]) else None,
                          "ganho_potencial_moderado_ano": round(float(df.iat[r, 13]), 2) if pd.notna(df.iat[r, 13]) else None,
                          "fonte": FONTE})
    return rows_tarifa, rows_mes


ITENS_CMOC_GERDAU = [(14, "Manobra destino"), (15, "Manobra origem"), (17, "DP Rumo"), (18, "DP MRS")]
ITENS_CENIBRA = [(14, "Manobra origem"), (15, "Manobra destino")]
ITENS_SELECTA = [(10, "Manobra conexão cheio"), (11, "Manobra destino"), (12, "Manobra origem"),
                  (13, "Direito de passagem"), (15, "Direito de passagem MRS")]
ITENS_LD = [(12, "Manobra destino"), (13, "Manobra origem")]


def main():
    tarifas, abertura = [], []

    t, a = parse_multiflow("CMOC", "CMOC", ITENS_CMOC_GERDAU); tarifas += t; abertura += a
    t, a = parse_multiflow("Gerdau", "GERDAU", ITENS_CMOC_GERDAU); tarifas += t; abertura += a
    t, a = parse_multiflow("Cenibra", "CENIBRA", ITENS_CENIBRA); tarifas += t; abertura += a
    t, a = parse_singleflow("Selecta", "SELECTA", 9, ITENS_SELECTA); tarifas += t; abertura += a
    t, a = parse_singleflow("Selecta retro", "SELECTA (retroativo)", 9, ITENS_SELECTA); tarifas += t; abertura += a
    t, a = parse_singleflow("LD", "LD CELULOSE", 11, ITENS_LD, vol_row=9); tarifas += t; abertura += a
    t, a = parse_caramuru(); tarifas += t; abertura += a
    t, a = parse_nova_agri(); tarifas += t; abertura += a
    t, a = parse_agrex(); tarifas += t; abertura += a

    df_tarifas = pd.DataFrame(tarifas)
    if "cobertura" not in df_tarifas.columns:
        df_tarifas["cobertura"] = None
    df_abertura = pd.DataFrame(abertura)
    cap_tarifa, cap_mes = parse_captura_mosaic()
    df_cap_tarifa = pd.DataFrame(cap_tarifa)
    df_cap_mes = pd.DataFrame(cap_mes)

    con = sqlite3.connect(DB)
    df_tarifas.to_sql("projeto_fluxo_tarifas", con, if_exists="replace", index=False)
    df_abertura.to_sql("projeto_acessorias_abertas", con, if_exists="replace", index=False)
    df_cap_tarifa.to_sql("captura_clientes_potenciais_tarifas", con, if_exists="replace", index=False)
    df_cap_mes.to_sql("captura_clientes_potenciais_mes", con, if_exists="replace", index=False)
    con.commit()

    print(f"projeto_fluxo_tarifas: {len(df_tarifas)} linhas ({df_tarifas['cliente'].nunique()} clientes, "
          f"{df_tarifas['fluxo'].nunique()} fluxos)")
    print(f"projeto_acessorias_abertas: {len(df_abertura)} linhas")
    for cli in df_abertura["cliente"].unique():
        n = len(df_abertura[df_abertura["cliente"] == cli])
        print(f"  {cli}: {n} itens")
    print(f"captura_clientes_potenciais_tarifas: {len(df_cap_tarifa)} linhas "
          f"({df_cap_tarifa['concorrente'].nunique()} concorrentes)")
    print(f"captura_clientes_potenciais_mes: {len(df_cap_mes)} linhas")
    con.close()

    # clientes novos (siderurgia/mineração: Mosaic/Usiminas/ArcelorMittal) derivados da base de
    # teto — SEMPRE depois do to_sql(if_exists='replace') acima, senão o replace apaga esses
    # registros. São INSERT-only nos 3 clientes; não tocam nos curados. Ver o script pro racional.
    import add_projetos_clientes_novos
    add_projetos_clientes_novos.main()

    # GERDAU: substitui os fluxos curados pelos reais (preços contratuais F-LINK, reajuste a
    # reajuste) e traz a abertura de manobra. Só age se gerdau_precos_contratuais existir.
    # Tabela-fonte recriada AQUI (pente-fino lote 4, nov/2026): antes o connect rodava contra
    # uma tabela que só existia por execução manual — se ela sumisse, o connect pulava em
    # silêncio e a GERDAU voltava aos números velhos da planilha.
    import add_gerdau_precos_contratuais
    add_gerdau_precos_contratuais.main()
    import connect_gerdau_precos
    connect_gerdau_precos.main()

    # IPIRANGA (cliente novo): cria os fluxos a partir dos preços contratuais F-LINK (reajuste a
    # reajuste) e traz a abertura de manobra/direito de passagem. Só age se
    # ipiranga_precos_contratuais existir.
    import add_ipiranga_precos_contratuais  # idem (lote 4, nov/2026)
    add_ipiranga_precos_contratuais.main()
    import connect_ipiranga_precos
    connect_ipiranga_precos.main()

    # AGREX: substitui o fluxo genérico (média da planilha) pelo portfólio completo por rota
    # (ipoa_teto + abertura real de fluxos_servico) — pedido do usuário, 19/jul/2026.
    import add_agrex_fluxos_completos
    add_agrex_fluxos_completos.main()

    # SELECTA: adiciona as rotas que faltavam (tarifas_praticadas + fluxos_servico),
    # preservando o par curado EBJ→IUF + retroativo — pedido do usuário, 19/jul/2026.
    import add_selecta_fluxos_completos
    add_selecta_fluxos_completos.main()

    # DEMAIS CLIENTES: replica o modelo SELECTA (portfólio completo por rota) pro resto da
    # base — CARAMURU/NOVA AGRI (substitui fluxo genérico) e MOSAIC/CENIBRA/ARCELORMITTAL/
    # APERAM/RAIZEN/SUZANO (adiciona rotas faltantes, preserva curados). LD CELULOSE
    # explicitamente EXCLUÍDA (pedido do usuário, 19/jul/2026: "manter o que já definimos").
    import add_demais_clientes_fluxos_completos
    add_demais_clientes_fluxos_completos.main()

    # SELECTA ETB→VTU: preenche a abertura de manobra que faltava (vídeos F-LINK IMG_0524/
    # IMG_0525, 2 itens ferroviários distintos pra mesma rota) — pedido do usuário, 20/jul/2026.
    # Roda DEPOIS de add_selecta_fluxos_completos (substitui o fluxo antigo item 41226).
    import add_selecta_etbvtu_novos_itens
    add_selecta_etbvtu_novos_itens.main()
    import connect_selecta_etbvtu_itens
    connect_selecta_etbvtu_itens.main()

    # SELECTA FARELO DE SOJA EBJ→IUF: cria o fluxo novo (rota inexistente na base) a partir
    # do vídeo F-LINK IMG_0563 — pedido do usuário, 24/jul/2026.
    import add_selecta_farelo_precos_contratuais
    add_selecta_farelo_precos_contratuais.main()
    import connect_selecta_farelo_precos
    connect_selecta_farelo_precos.main()

    # AÇÚCAR — 5 CLIENTES NOVOS (BP COMERCIALIZADORA DE ENERGIA, CZARNIKOW GROUP LIMITED,
    # COPERSUCAR S.A., TEREOS AÇUCAR E ENERGIA BRASIL, LOUIS DREYFUS COMPANY SUISSE): 12
    # fluxos novos minerados dos vídeos F-LINK IMG_0564-0576 — pedido do usuário, 28/jul/2026:
    # "baixei os videos dos clientes de acucar, 564 a 576. Carregar dados no sistema". Nenhum
    # destes clientes existia na base antes. "COOP DE PROD CANA DE AÇUCAR" (item 10935) NÃO é
    # um 6º cliente — confirmado pelo usuário em 28/jul/2026 que é o nome jurídico/cooperativo
    # de COPERSUCAR S.A.; checado que a rota (ZRP→ISN-Santos) é diferente dos outros 2 itens
    # de Copersucar (ZGU/ZZB), logo é um 3º fluxo genuíno do mesmo cliente, lançado com só a
    # tarifa total (breakdown nunca resolveu no vídeo IMG_0566 — baixa confiança).
    import add_acucar_novos_clientes_precos_contratuais
    add_acucar_novos_clientes_precos_contratuais.main()
    import connect_acucar_novos_clientes_precos
    connect_acucar_novos_clientes_precos.main()

    # RECONCILIAÇÃO FINAL: garante que TODO fluxo com abertura tenha acessórias = soma dos
    # itens (Direito de Passagem incluso — confirmado com o usuário 20/jul/2026). Os fluxos
    # de portfólio (add_demais_clientes_fluxos_completos.py etc.) já nascem fechados; este
    # passo corrige só os 4 fluxos curados manualmente (CMOC×3, SELECTA retroativo) que a
    # planilha-fonte reseed a cada rodada com o valor antigo (DP fora da soma). Roda por
    # ÚLTIMO, depois de tudo que pode reinserir/reseedar projeto_fluxo_tarifas.
    import fix_dp_acessoria_curados
    fix_dp_acessoria_curados.main()

    # CMOC: reconcilia os 3 fluxos curados manualmente com a situação tarifária real
    # (preços contratuais F-LINK, reajuste a reajuste) — pedido do usuário, 22/jul/2026.
    # Roda DEPOIS de fix_dp_acessoria_curados (senão aquele script recalcularia acessórias
    # a partir dos itens antigos da planilha antes deste substituí-los pelos reais). Só age
    # se cmoc_precos_contratuais existir.
    import add_cmoc_precos_contratuais  # idem (lote 4, nov/2026)
    add_cmoc_precos_contratuais.main()
    import connect_cmoc_precos
    connect_cmoc_precos.main()

    # MOSAIC: acrescenta 2 fluxos novos (ENXOFRE e ROCHA FOS UMIDA, item 39890/39889) a
    # partir dos preços contratuais F-LINK — preenche lacuna de abertura de manobra que não
    # existia pra esses 2 produtos. Pedido do usuário, 22/jul/2026. Só age se
    # mosaic_precos_contratuais existir. add_mosaic_precos_contratuais.main() nunca era
    # chamado pelo orquestrador (tabela-fonte ficava stale de execução manual anterior) —
    # corrigido em 30/jul/2026 ao acrescentar o item 41109 (resolve fluxo FERTILIZANTES
    # IUF ZVF pendente).
    import add_mosaic_precos_contratuais
    add_mosaic_precos_contratuais.main()
    import connect_mosaic_precos
    connect_mosaic_precos.main()

    # ALZ: reconcilia os 2 fluxos curados (SOJA/MILHO PIN QPM) com a situação tarifária
    # real (preços contratuais F-LINK, reajuste a reajuste) — pedido do usuário,
    # 22/jul/2026. Roda por último, mesma posição do CMOC/MOSAIC. Só age se
    # alz_precos_contratuais existir.
    import add_alz_precos_contratuais  # idem (lote 4, nov/2026)
    add_alz_precos_contratuais.main()
    import connect_alz_precos
    connect_alz_precos.main()

    # AGREX: reconcilia os 2 fluxos curados (SOJA/MILHO PPN QPM) com a situação tarifária
    # real (preços contratuais F-LINK, reajuste a reajuste) — pedido do usuário,
    # 22/jul/2026. Roda por último, mesma posição do CMOC/MOSAIC. Só age se
    # agrex_precos_contratuais existir.
    import add_agrex_precos_contratuais  # idem (lote 4, nov/2026)
    add_agrex_precos_contratuais.main()
    import connect_agrex_precos
    connect_agrex_precos.main()

    # NOVA AGRI: reconcilia os 2 fluxos existentes (SOJA/MILHO PPT QPM) com a situacao
    # tarifaria real (precos contratuais F-LINK, reajuste a reajuste) — pedido do usuario,
    # 22/jul/2026. Roda por ultimo, mesma posicao do CMOC/MOSAIC/ALZ/AGREX. So age se
    # novaagri_precos_contratuais existir.
    import add_novaagri_precos_contratuais  # idem (lote 4, nov/2026)
    add_novaagri_precos_contratuais.main()
    import connect_novaagri_precos
    connect_novaagri_precos.main()

    # USIMINAS: preenche a abertura de manobra origem/destino que faltava (25+ fluxos com
    # cobertura "sem abertura de manobra (pendente)") a partir dos precos contratuais F-LINK
    # (usiminas_precos_contratuais, videos IMG_02XX/03XX.MOV) — pedido do usuario, 23/jul/2026:
    # "usiminas faltando abertura de manobras". Roda por ultimo, mesma posicao do
    # CMOC/MOSAIC/ALZ/AGREX/NOVA AGRI. Cria a tabela-fonte primeiro (idempotente, sem
    # dependencia externa — dados vem hardcoded do script, minerados dos videos F-LINK) e so
    # depois conecta. Fluxos com conflito genuino de manobra entre itens (ex.: COQUE GROSSO
    # VTU-VIC) ficam sinalizados em `cobertura`, sem abertura arbitraria.
    import add_usiminas_precos_contratuais
    add_usiminas_precos_contratuais.main()
    import connect_usiminas_precos
    connect_usiminas_precos.main()

    # ARCELORMITTAL: mesmo gap do USIMINAS — connect_arcelormittal_precos.py e
    # add_arcelormittal_precos_contratuais.py ja existiam no repo mas NUNCA foram chamados
    # por este orquestrador, entao os 25 fluxos curados da ARCELORMITTAL ficavam com
    # cobertura "sem abertura de manobra (pendente)" e zero linhas em
    # projeto_acessorias_abertas mesmo tendo volume real em volume_hist (PRO SIDERURGICO /
    # FIO MAQUINA / CARVAO MINERAL / ANTRACITO / COQUE GROSSO / MINERIO FERRO / CNTR CHEIO
    # 20 P) — pedido do usuario, 24/jul/2026: "para arcelor alguns fluxos com volume
    # repetidos e faltando abertura de varias manobras de fluxos com volumes". Roda por
    # ultimo, mesma posicao do USIMINAS.
    import add_arcelormittal_precos_contratuais
    add_arcelormittal_precos_contratuais.main()
    import connect_arcelormittal_precos
    connect_arcelormittal_precos.main()

    # APERAM: add_aperam_precos_contratuais.py/connect_aperam_precos.py ja existiam no repo
    # (cliente novo, videos IMG_0480-0490 + extensao IMG_0577-0580) mas NUNCA foram
    # chamados por este orquestrador — descoberto em 30/jul/2026 ao notar que
    # projeto_fluxo_tarifas.to_sql(if_exists="replace") acima apaga qualquer linha da
    # APERAM que so existisse via execucao manual anterior do connect. Roda por ultimo,
    # mesma posicao do USIMINAS/ARCELORMITTAL.
    import add_aperam_precos_contratuais
    add_aperam_precos_contratuais.main()
    import connect_aperam_precos
    connect_aperam_precos.main()

    # MATERIAL JÁ MINERADO QUE NÃO CHEGAVA AO PAINEL (pente-fino lote 4, nov/2026): 8 clientes
    # com vídeos F-LINK transcritos (VIBRA 20 itens/210 vigências, RAIZEN, ALE, CENIBRA,
    # SUZANO, PETROBAHIA, PETRONAC, SABBA) cujos add_/connect_ nunca foram ligados aqui. Os
    # connect_<cliente>_precos.py antigos NÃO são usados (apagavam o cliente inteiro antes de
    # reinserir); o conector único faz UPDATE/INSERT por fluxo. Ver docstring dele.
    import add_vibra_precos_contratuais
    add_vibra_precos_contratuais.main()
    import add_raizen_precos_contratuais
    add_raizen_precos_contratuais.main()
    import add_alesat_precos_contratuais
    add_alesat_precos_contratuais.main()
    import add_cenibra_precos_contratuais
    add_cenibra_precos_contratuais.main()
    import add_suzano_precos_contratuais
    add_suzano_precos_contratuais.main()
    import add_petrobahia_precos_contratuais
    add_petrobahia_precos_contratuais.main()
    import add_petronac_precos_contratuais
    add_petronac_precos_contratuais.main()
    import add_sabba_precos_contratuais
    add_sabba_precos_contratuais.main()
    import add_ldcelulose_precos_contratuais  # só a tabela-fonte (histórico p/ rastreador)
    add_ldcelulose_precos_contratuais.main()
    import connect_precos_minerados
    connect_precos_minerados.main()

    # CONSISTÊNCIA FINAL (pente-fino lote 3, nov/2026) — sempre o ÚLTIMO passo que escreve em
    # projeto_fluxo_tarifas/projeto_acessorias_abertas: IPOA = acessórias ÷ frete, vigência
    # em formato único, duplicatas de rota, rotas sem tráfego. Ver docstring.
    import fix_consistencia_final
    fix_consistencia_final.main()

    # Salvaguarda permanente (24/jul/2026, pedido do usuario apos 7 rounds da MESMA classe
    # de bug — "volume ultimos 12 meses" borrowed/fabricado por cliente-a-cliente reportado
    # manualmente): roda audit_volumes.py como resumo NAO-BLOQUEANTE ao fim do pipeline, so
    # pra IMPRIMIR um aviso se aparecer instancia nova dessa familia de bug — nunca aborta o
    # build (import/exec protegido; qualquer excecao aqui e so logada, o pipeline principal
    # ja rodou e seus dados ja estao gravados). Ver audit_volumes.py pra rodar standalone com
    # relatorio completo.
    try:
        import audit_volumes
        print("\n--- auditoria de volume (audit_volumes.py, resumo nao-bloqueante) ---")
        audit_volumes.audit()
    except Exception as e:
        print(f"[aviso] audit_volumes.py nao pode rodar ({e}) — build principal nao foi afetado.")

if __name__ == "__main__":
    main()
