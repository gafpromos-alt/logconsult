# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=FARELO DE MILHO
CONFIDENCIAL — USO RESTRITO AOS SOCIOS

Fonte: video do usuario 09_Fotos/IMG_0225.MOV (236s, Produto=FARELO DE MILHO confirmado no dropdown,
dimensao Microrregiao). Walkthrough regiao-a-regiao na visao COMPACTA de 3 paineis (2024|2025|2026).
Este e' o UNICO material de Farelo de Milho na base (modulo antes vazio).

Disciplina de precisao (regra-mae "nao inventar precisao"):
  - So grava mes com rotulo NUMERICO legivel e alinhado ao seu mes no eixo.
  - Mes com barra ocluida pela LISTA SUSPENSA aberta (a apresentacao clica regiao a regiao pelo
    dropdown, que cobre a metade direita do painel 2025) = nao lido, fica de fora.
  - Frame de TRANSICAO (render-lag: valores de outra regiao aparecem por 1-2 frames enquanto a
    selecao muda) descartado; usado sempre o frame estavel com o banner batendo a regiao.
  - Volumes de Farelo de Milho sao pequenos (ordem de 1k-140k t/mes), bem menores que Soja/Milho.

INSERT ... WHERE NOT EXISTS (idempotente). Entra no rebuild_market_share.sh depois dos scripts de
Farelo de Soja. Mineracao incremental regiao a regiao (IMG_0225).
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
PRODUTO = "Farelo de Milho"
FONTE = ("Video do usuario (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0225.MOV, Produto=FARELO DE MILHO, dimensao Microrregiao) — visao compacta "
         "3 paineis, transcricao manual dos rotulos de Volume Movimentado, jul/2026.")

# escopo -> {ano: {mes_1a12: volume_t}}. So meses lidos com nitidez (dropdown nao occluindo, frame
# estavel). Meses ausentes = ocluidos/ilegiveis, a preencher em rodada futura.
VOLUME = {
    # MT MEDIO NORTE (IMG_0225 t=128, banner confirma; dropdown MT MEDIO NORTE marcado).
    # 2024: jan cortado na borda esquerda (nao lido). fev..dez legiveis.
    # 2025: jan..jul legiveis; ago (~19.58x, ultimo digito incerto) e set..dez ocluidos pela lista.
    # 2026: jan..jul legiveis (ano corrente, so ate julho).
    "MT MEDIO NORTE": {
        2024: {2: 22103, 3: 19485, 4: 22223, 5: 18663, 6: 17243, 7: 11000,
               8: 14973, 9: 15698, 10: 19621, 11: 22750, 12: 27413},
        2025: {1: 16945, 2: 24945, 3: 20404, 4: 22706, 5: 17751, 6: 13404, 7: 28295},
        2026: {1: 29818, 2: 24268, 3: 18214, 4: 15073, 5: 38782, 6: 10590, 7: 1551},
    },
    # MG OUTROS (IMG_0225 t=44, banner confirma; dropdown MG OUTROS marcado).
    # Grafico plota so mar e abr 2024 (valor "1" cada); 2025 e 2026 sem barras (sem dados).
    "MG OUTROS": {
        2024: {3: 1, 4: 1},
    },
    # MS SUL (IMG_0225 t=52, banner confirma; MS SUL marcado; dropdown aberto).
    # 2024: mar e jul ausentes no eixo (sem dados). jan..dez restantes legiveis.
    # 2025: jan..jul legiveis; ago (~1.05x) cortado pela lista, set..dez ocluidos.
    # 2026: so jan..jun no eixo (jul ausente/sem dados).
    "MS SUL": {
        2024: {1: 302, 2: 159, 4: 6305, 5: 1848, 6: 373, 8: 492, 9: 360,
               10: 7443, 11: 7300, 12: 13224},
        2025: {1: 17936, 2: 10479, 3: 13743, 4: 12095, 5: 6734, 6: 2017, 7: 774},
        2026: {1: 16116, 2: 17015, 3: 27341, 4: 7595, 5: 7018, 6: 119},
    },
    # MT NORTE (IMG_0225 t=58, banner confirma; MT NORTE marcado; dropdown aberto).
    # 2024: 12 meses completos, legiveis. 2025: jan..jul legiveis; ago (~66.61x) cortado
    # pela lista, set..dez ocluidos. 2026: jan..jul completos.
    "MT NORTE": {
        2024: {1: 39420, 2: 30828, 3: 32741, 4: 31594, 5: 41222, 6: 49853, 7: 63869,
               8: 57344, 9: 43046, 10: 49681, 11: 90374, 12: 76604},
        2025: {1: 67821, 2: 66890, 3: 53328, 4: 60064, 5: 47481, 6: 17005, 7: 58520},
        2026: {1: 90083, 2: 76609, 3: 82766, 4: 51946, 5: 53861, 6: 76114, 7: 24926},
    },
    # MT OESTE (IMG_0225 t=63, banner confirma; MT OESTE marcado; dropdown aberto).
    # 2024: jan e abr ausentes no eixo (sem dados); demais legiveis.
    # 2025: jan ausente; fev..ago legiveis; sete (~4x) cortado, out..dez ocluidos.
    # 2026: jan..jul completos.
    "MT OESTE": {
        2024: {2: 130, 3: 474, 5: 76, 6: 466, 7: 812, 8: 7939, 9: 43, 10: 439,
               11: 384, 12: 44},
        2025: {2: 129, 3: 318, 4: 938, 5: 501, 6: 192, 7: 95, 8: 283},
        2026: {1: 143, 2: 147, 3: 674, 4: 576, 5: 452, 6: 1294, 7: 516},
    },
    # PA OUTROS (IMG_0225 t=67, banner confirma; PA OUTROS marcado; dropdown aberto).
    # Grafico so plota out e nov de 2025; 2024 e 2026 sem barras.
    "PA OUTROS": {
        2025: {10: 3727, 11: 481},
    },
    # PR (IMG_0225 t=72, banner confirma; PR marcado; dropdown aberto).
    # 2024: 12 meses completos. 2025: jan..ago legiveis (ago=930 nitido); set..dez ocluidos.
    # 2026: jan..jul completos.
    "PR": {
        2024: {1: 1211, 2: 775, 3: 1076, 4: 1226, 5: 1476, 6: 765, 7: 737, 8: 595,
               9: 892, 10: 1263, 11: 404, 12: 1026},
        2025: {1: 1067, 2: 1014, 3: 916, 4: 806, 5: 606, 6: 1637, 7: 1377, 8: 930},
        2026: {1: 569, 2: 943, 3: 1601, 4: 3493, 5: 1165, 6: 365, 7: 15},
    },
    # RJ (IMG_0225 t=77, banner confirma; RJ marcado). Os 3 paineis vazios (sem dados). Nada a gravar.
    # RN (IMG_0225 t=80, banner confirma; RN marcado; dropdown aberto).
    # 2024: so jul=47. 2025: jan=45 nitido; fev (~48x) cortado na borda da lista -> omitido. 2026 vazio.
    "RN": {
        2024: {7: 47},
        2025: {1: 45},
    },
    # RO (IMG_0225 t=82, banner confirma; RO marcado; dropdown aberto). So set/2024=22. 2025 e 2026 vazios.
    "RO": {
        2024: {9: 22},
    },
    # RS (IMG_0225 t=86, banner confirma; RS marcado; dropdown aberto).
    # 2024: 12 meses completos. 2025: jan..jul legiveis; ago (~1.16x) cortado; set..dez ocluidos.
    # 2026: jan..mai (jun/jul ausentes no eixo).
    "RS": {
        2024: {1: 6035, 2: 3343, 3: 5825, 4: 4369, 5: 1874, 6: 2981, 7: 3768, 8: 2380,
               9: 3124, 10: 2928, 11: 1099, 12: 1472},
        2025: {1: 730, 2: 363, 3: 736, 4: 1185, 5: 1319, 6: 4973, 7: 5417},
        2026: {1: 187, 2: 428, 3: 107, 4: 156, 5: 119},
    },
    # SC (IMG_0225 t=92, banner confirma; SC marcado; dropdown aberto).
    # 2024: so mar, jun, ago. 2025: abr=51; dez (~70) cortado na borda da lista -> omitido. 2026 vazio.
    "SC": {
        2024: {3: 36, 6: 30, 8: 39},
        2025: {4: 51},
    },
    # SE (IMG_0225 t=95, banner confirma; SE marcado sozinho; dropdown aberto). 3 paineis vazios. Nada a gravar.
    # SP (IMG_0225 t=102, banner confirma; SP marcado; dropdown aberto/rolado).
    # 2024: 12 meses completos. 2025: jan..out legiveis (sete=37, outu=37); nov ocluido -> omitido; dez=38.
    # 2026: jan..mai e jul (junho ausente no eixo).
    "SP": {
        2024: {1: 388, 2: 2254, 3: 536, 4: 169, 5: 807, 6: 705, 7: 704, 8: 2223,
               9: 1191, 10: 935, 11: 2743, 12: 1145},
        2025: {1: 1529, 2: 1217, 3: 551, 4: 1136, 5: 5567, 6: 112, 7: 302, 8: 229,
               9: 37, 10: 37, 12: 38},
        2026: {1: 75, 2: 74, 3: 856, 4: 86, 5: 45, 7: 51},
    },
    # GO LESTE (IMG_0225 t=107, banner confirma; GO LESTE marcado; dropdown aberto).
    # 2024: mai/jun/ago ausentes no eixo; demais legiveis. 2025: so janeiro=165 visivel a esquerda
    # da lista (fev+ possivelmente ocluidos pela lista, nao lidos). 2026: mar,abr,mai,jul (jan/fev/jun ausentes).
    "GO LESTE": {
        2024: {1: 1622, 2: 1284, 3: 391, 4: 40, 7: 238, 9: 38, 10: 1128, 11: 79, 12: 136},
        2025: {1: 165},
        2026: {3: 47, 4: 777, 5: 563, 7: 43},
    },
    # GO NOROESTE (IMG_0225 t=110, banner confirma; GO NOROESTE marcado; dropdown aberto).
    # 2024: so nov, dez. 2025: jan,mar,abr,mai,ago,set,out (fev/jun/jul ausentes). 2026: mar,mai,jul.
    "GO NOROESTE": {
        2024: {11: 488, 12: 100},
        2025: {1: 144, 3: 830, 4: 815, 5: 219, 8: 47, 9: 94, 10: 44},
        2026: {3: 24, 5: 12, 7: 37},
    },
    # GO NORTE (IMG_0225 t=113, banner confirma; GO NORTE marcado; dropdown aberto). So mar/2024=78. 2025/2026 vazios.
    "GO NORTE": {
        2024: {3: 78},
    },
    # MG TRIANGULO (IMG_0225 t=123, banner confirma; MG TRIANGULO marcado; lista semitransparente).
    # 2024: fev,jun,jul,nov,dez. 2025: fev..ago legiveis; set..dez ocluidos pela lista. 2026: jan..jul completos.
    "MG TRIANGULO": {
        2024: {2: 37, 6: 36, 7: 30, 11: 159, 12: 14},
        2025: {2: 327, 3: 131, 4: 106, 5: 423, 6: 284, 7: 320, 8: 128},
        2026: {1: 281, 2: 320, 3: 258, 4: 571, 5: 339, 6: 506, 7: 100},
    },
    # MT NORDESTE SUL (IMG_0225 t=132, banner confirma; dropdown FECHADO). So 2024 fev=95, mar=39.
    # 2025 e 2026 confirmadamente vazios (lista fechada).
    "MT NORDESTE SUL": {
        2024: {2: 95, 3: 39},
    },
    # MT SUDESTE (IMG_0225 t=136, banner confirma; dropdown FECHADO -> 2025 completo visivel).
    # 2024: 12 meses. 2025: 12 meses. 2026: jan..jul completos.
    "MT SUDESTE": {
        2024: {1: 159, 2: 1267, 3: 4456, 4: 3284, 5: 3349, 6: 5110, 7: 4265, 8: 1510,
               9: 2870, 10: 4029, 11: 3277, 12: 4579},
        2025: {1: 1842, 2: 2253, 3: 699, 4: 1815, 5: 2124, 6: 2037, 7: 1137, 8: 525,
               9: 168, 10: 1786, 11: 224, 12: 88},
        2026: {1: 4049, 2: 177, 3: 413, 4: 272, 5: 319, 6: 251, 7: 44},
    },
    # GO SUDOESTE (IMG_0225 t=117, banner confirma; GO SUDOESTE marcado; dropdown aberto).
    # 2024: 12 meses completos. 2025: jan..jun legiveis; jul (~52) cortado -> omitido; sete=84, outu=28,
    # dez=60 (ago/nov ausentes no eixo). 2026: fev..jun (jan/jul ausentes).
    "GO SUDOESTE": {
        2024: {1: 544, 2: 1868, 3: 520, 4: 943, 5: 1588, 6: 3124, 7: 565, 8: 58,
               9: 118, 10: 126, 11: 108, 12: 200},
        2025: {1: 548, 2: 439, 3: 577, 4: 4115, 5: 2844, 6: 673, 9: 84, 10: 28, 12: 60},
        2026: {2: 400, 3: 2696, 4: 3100, 5: 161, 6: 373},
    },
    # TO SUL (IMG_0225 t=38, banner confirma; TO SUL marcado; dropdown aberto). Primeira regiao do walkthrough.
    # 2024: mai,jun,ago,set,out,nov (jan-abr, jul, dez ausentes). 2025: so julho=47. 2026: so maio=32.
    "TO SUL": {
        2024: {5: 48, 6: 240, 8: 125, 9: 1347, 10: 506, 11: 48},
        2025: {7: 47},
        2026: {5: 32},
    },
    # BA OUTROS (IMG_0225 t=41, banner confirma; BA OUTROS marcado; dropdown aberto).
    # 2024: so mai=30. 2025: so dez=3. 2026 vazio.
    "BA OUTROS": {
        2024: {5: 30},
        2025: {12: 3},
    },
    # MS NORTE (IMG_0225 t=47, banner confirma; MS NORTE marcado; dropdown aberto).
    # 2024: jan,fev,mar,abr,jun,set (demais ausentes). 2025 vazio. 2026: so maio=78.
    "MS NORTE": {
        2024: {1: 38, 2: 109, 3: 38, 4: 82, 6: 38, 9: 38},
        2026: {5: 78},
    },
    # --- Regioes que apareceram no video mas NAO gravadas (documentadas p/ rastreabilidade) ---
    # RJ (t=77) e SE (t=95): banner confirma a regiao, porem os 3 paineis vazios (sem dados). Nada a inserir.
    # MA SUL (t=187-189 e 228-230): banner confirma MA SUL, MAS um slicer de PORTO (=SAO LUIS) estava
    #   ATIVO em todos os frames (as demais regioes foram lidas com Porto=Todos). Alem disso os valores de
    #   2025 divergem entre t=188 (jul=702, outu=95) e t=229 (jul=47, outu=48), confirmando que o filtro de
    #   Porto particiona o volume. Para preservar a consistencia da base (todo o resto e' Porto=Todos) e a
    #   regra "nao inventar precisao", MA SUL fica de fora. Valores vistos sob Porto=SAO LUIS (NAO inseridos,
    #   apenas registro): 2024 {10:49,11:48}; 2025 {1:233,2:1110,3:1218,4:1308,5:689,6:802,7:702,9:422,10:95,
    #   11:47}; 2026 {2:29,5:37,6:39}.
    # PI SUL / BA OESTE NORTE: NAO foram selecionadas individualmente (varredura de banner frame-a-frame de
    #   t=38..236 nao mostra esses rotulos); sem dados de Farelo de Milho a extrair aqui.
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    ins = skip = 0
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for mes_num, v in meses.items():
                if v is None:
                    continue
                mes = MESES[mes_num - 1]
                cur.execute(
                    "INSERT INTO market_share_volume (escopo, produto, ano, mes, volume_t, fonte) "
                    "SELECT ?,?,?,?,?,? WHERE NOT EXISTS ("
                    "  SELECT 1 FROM market_share_volume "
                    "  WHERE escopo=? AND produto=? AND ano=? AND mes=?)",
                    (escopo, PRODUTO, ano, mes, float(v), FONTE, escopo, PRODUTO, ano, mes))
                if cur.rowcount:
                    ins += 1
                else:
                    skip += 1
    con.commit()
    print(f"market_share_volume (Farelo de Milho): {ins} novas ({skip} ja existiam)")
    con.close()


if __name__ == "__main__":
    main()
