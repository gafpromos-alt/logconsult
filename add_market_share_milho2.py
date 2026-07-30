# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=MILHO — RODADA 2
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: mesmo vídeo de add_market_share_milho.py (09_Fotos/IMG_0222.MOV, 428s, Produto=MILHO).
Este arquivo adiciona REGIÕES NOVAS que não estavam no primeiro script — garimpo região a
região do vídeo (título "Competitividade - {REGIÃO}" no topo), lendo os rótulos numéricos das
barras de Volume Movimentado por ano (2024/2025/2026).

Disciplina de precisão (regra-mãe do projeto "não inventar precisão"):
- Barra sem rótulo por COLISÃO (PowerBI esconde rótulo de barras altas adjacentes) = None,
  nunca chutado. Ex.: MT Sudeste SET/2024, SET+NOV/2025 saíram sem rótulo legível — ficam None.
- Só entra número lido com zoom no frame com dropdown FECHADO e página não-scrollada.

IMPORTANTE: só INSERT (não DROP). Roda DEPOIS de add_market_share.py + add_market_share_milho.py.
Ordem canônica: usar rebuild_market_share.sh (roda os 4 scripts na sequência correta).
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0222.MOV, Produto=MILHO) — transcrição manual dos rótulos de Volume. "
         "Rodada 2: regiões novas não cobertas pelo primeiro script.")

# escopo -> {ano: [12 meses, None = sem rótulo/colisão]}
VOLUME = {
    # MT Sudeste (t~150s do vídeo, título "Competitividade - MT SUDESTE", dropdown fechado).
    # SET/2024, SET+NOV/2025 = rótulo escondido por colisão de barra alta -> None.
    "MT Sudeste": {
        2024: [80400, 18706, 11244, 28836, 94243, 82324, 200673, 276675, None, 299618, 238002, 145890],
        2025: [42779, 15718, 21802, 15557, 15627, 30079, 218194, 297371, None, 459235, None, 430173],
        2026: [120065, 42743, 33209, 29423, 68136, 44319, 39901, None, None, None, None, None],
    },
    # MG Outros (t~206s, título "Competitividade - MG OUTROS"). 2024 e 2026 lidos em frame limpo;
    # 2025 tinha o dropdown de Microrregião aberto por cima da cauda -> SET (rótulo coberto),
    # NOV/DEZ (posição de rótulo ambígua entre as duas barras) ficam None.
    "MG Outros": {
        2024: [191, 302, 812, 66, 108, 78, 11090, 24264, 4126, 935, 1158, 4295],
        2025: [4311, 289, 156, 291, 556, 162, 1695, 954, None, 143, None, None],
        2026: [81, 0, 15, 0, 205, 166, 33, None, None, None, None, None],
    },
    # GO Noroeste (t~98s, frame limpo, dropdown fechado). 2024 com os 12 meses rotulados;
    # 2025 sem jan/mar/abr no eixo (volume zero); 2026 sem janeiro no eixo.
    "GO Noroeste": {
        # Eixo verificado (IMG_0222 t99, 13/jul/26): 2025 sem jan/mar/abr; 2026 sem jan -> zero.
        2024: [256, 118, 107, 133, 6703, 5123, 4201, 241, 5435, 7556, 1456, 2693],
        2025: [0, 93, 0, 0, 1227, 470, 10865, 10928, 11788, 4007, 4834, 591],
        2026: [0, 96, 881, 282, 40, 154, 49, None, None, None, None, None],
    },
    # GO Norte (IMG_0222 t104, região nova ultra-esparsa; eixos verificados: 2024 só
    # jan/jun/ago/set/out; 2025 só mar/abr/jul/ago/set/out/nov; 2026 painel vazio).
    "GO Norte": {
        2024: [72, 0, 0, 0, 0, 246, 0, 86, 314, 665, 0, 0],
        2025: [0, 0, 815, 1431, 0, 0, 31, 339, 549, 1220, 237, 0],
        2026: [0, 0, 0, 0, 0, 0, 0, None, None, None, None, None],
    },
    # GO Sudoeste (t~109s, frame limpo). Atribuição rótulo→barra por centragem horizontal +
    # regra "rótulo fica acima do topo da própria barra". Sem rótulo por colisão -> None:
    # JUN+SET+DEZ/2024, OUT+DEZ/2025.
    "GO Sudoeste": {
        # correção 14/jul: shift verificado no frame f095 do IMG_0235 — 564276 é SETEMBRO (não out;
        # o banco tinha set vazio e o pico 1 mês adiante). out (barra sem rótulo no fonte) = None.
        2024: [37147, 33160, 17271, 36978, 74509, None, 510676, 601294, 564276, None, 364419, None],
        2025: [177619, 34434, 29601, 21866, 23412, 54043, 690777, 864435, 543745, None, 529912, None],
        2026: [153273, 10845, 20651, 12008, 23461, 14877, 19536, None, None, None, None, None],
    },
    # MG Noroeste (t~114s, frame limpo, todos os meses visíveis rotulados — sem colisão).
    # Meses fora do eixo (abr/set/out 2024, maio 2025, jul 2026) = sem volume no fonte.
    "MG Noroeste": {
        # Eixos verificados (IMG_0222 t116, 13/jul/26): 2024 sem abr/set/out; 2025 sem
        # maio; 2026 sem julho -> zeros.
        2024: [58, 544, 190, 0, 361, 5838, 1898, 1281, 0, 0, 5736, 20439],
        2025: [40454, 2519, 190, 119, 0, 49, 198, 6183, 2592, 370, 2530, 909],
        2026: [261, 587, 226, 59, 39, 47, 0, None, None, None, None, None],
    },
    # TO Centro (t~74s, frame limpo, título confirmado em t60-63). Região ultra-esparsa:
    # 2024 só tem 5 meses no eixo, 2025 só 2, 2026 sem nenhuma barra (ano vazio no fonte).
    # CORRECAO 13/jul/26: a serie abaixo (97/36/144/5/5...) NAO era TO Centro — o banner
    # "Competitividade - TO CENTRO" nao muda quando se troca a regiao no dropdown; em t74
    # a selecao real era TO NORTE (sequencia t62=TO CENTRO, t71=TO LESTE, t74=TO NORTE,
    # t79=TO SUL). Eixos verificados: 2024 jan/fev/ago/set/nov; 2025 ago/set; 2026 vazio.
    "TO Norte": {
        2024: [97, 36, 0, 0, 0, 0, 0, 144, 5, 0, 5, 0],
        2025: [0, 0, 0, 0, 0, 0, 0, 1708, 108, 0, 0, 0],
        2026: [0, 0, 0, 0, 0, 0, 0, None, None, None, None, None],
    },
    # TO Centro REAL (IMG_0222 t62, banner + campo "NORTE+TO" conferidos; eixo 2024 sem
    # maio; 2025 12/12; 2026 sem maio).
    "TO Centro": {
        2024: [127, 188, 40, 145, 0, 202, 8945, 21820, 40689, 29089, 15267, 15188],
        2025: [98, 48, 446, 471, 561, 2454, 31536, 36983, 34257, 34203, 11390, 23951],
        2026: [672, 85, 47, 21, 0, 1325, 5437, None, None, None, None, None],
    },
    # TO Leste (IMG_0222 t71, dropdown marcando TO LESTE com painel ja renderizado; eixo
    # 2024 sem abr/mai; 2025 sem fev/abr/mai, out-dez tampados pelo dropdown -> None;
    # 2026 painel vazio).
    "TO Leste": {
        2024: [260, 1598, 51, 0, 0, 47, 20276, 29532, 8605, 24201, 20489, 49],
        2025: [355, 0, 20, 0, 0, 488, 11267, 14664, 13167, None, None, None],
        2026: [0, 0, 0, 0, 0, 0, 0, None, None, None, None, None],
    },
    # PI Outros (IMG_0222 t258 — painel puro com PI OUTROS marcado: 2024 so ago/set;
    # 2025 e 2026 vazios. O t254 somava PB por transicao de selecao).
    "PI Outros": {
        2024: [0, 0, 0, 0, 0, 0, 0, 2631, 1167, 0, 0, 0],
        2025: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        2026: [0, 0, 0, 0, 0, 0, 0, None, None, None, None, None],
    },
    # BA Oeste Norte (IMG_0222 t19, campo "NORTE+BA" fechado; eixos: 2024 so
    # jan/mar/set/out/nov/dez; 2025 sem ago/out/nov; 2026 so jan/mar/mai).
    "BA Oeste Norte": {
        2024: [143, 0, 50, 0, 0, 0, 0, 0, 6753, 58307, 54481, 31094],
        2025: [1180, 2160, 1352, 2495, 9013, 528, 81, 0, 39, 0, 0, 46],
        2026: [98, 0, 50, 0, 48, 0, 0, None, None, None, None, None],
    },
    # MT Nordeste (IMG_0222 t44, checkbox MT NORDESTE confirmado; zoom em jul-dez/24:
    # 416.219=jul, 515.805=ago, SET sem rotulo (colisao), 539.108=OUT, 334.872=nov,
    # 52.068=dez. 2025 ago tampado ("486.0..") e set-dez sob dropdown -> None).
    "MT Nordeste": {
        # correção 14/jul: shift verificado no frame f037 do IMG_0235 (crop do pico) — 539108 é SETEMBRO
        # e 334872 é OUTUBRO (o banco tinha set vazio e os dois 1 mês adiante). nov (barra sem rótulo) = None.
        2024: [9709, 1312, 1842, 702, 321, 14875, 416219, 515805, 539108, 334872, None, 52068],
        2025: [737, 513, 515, 334, 142, 36806, 235602, None, None, None, None, None],
        2026: [18605, 3274, 10723, 19448, 6034, 38842, 61983, None, None, None, None, None],
    },
    # TO Sul (t~80s, frame limpo; seleção "TO SUL" confirmada no dropdown em t=78). Todos os
    # meses visíveis rotulados — zero colisão. Fora do eixo: MAR/2024, MAIO/2025, JUN/2026.
    # 2º semestre 2025 completo (ago 143.768 é o pico da região).
    "TO Sul": {
        2024: [69, 620, 0, 82, 19, 18373, 13423, 78819, 106254, 98404, 86482, 53243],
        2025: [18872, 920, 332, 51, 0, 3353, 32958, 143768, 127723, 33639, 10034, 44770],
        2026: [1270, 227, 143, 449, 14, 0, 487, None, None, None, None, None],
    },
    # MS Norte (t~217s, checkbox "MS NORTE" confirmado no dropdown). 2024 completo (12/12
    # rotulados). 2025: dropdown cobria ago (rótulo truncado "89.23…") e set-dez -> None.
    "MS Norte": {
        2024: [6357, 4164, 19425, 9792, 8396, 19072, 26970, 5897, 34006, 48014, 8290, 15181],
        2025: [23751, 7385, 10247, 14434, 12794, 9643, 61013, 89230, 96864, 113947, 51295, 61443],
        2026: [5445, 6360, 8131, 39, 824, 1559, 1122, None, None, None, None, None],
    },
    # MT Oeste (t~233s, frame limpo; checkbox "MT OESTE" em t=231). Centragem rótulo→barra:
    # 2024 AGO/OUT/DEZ sem rótulo (colisão) — 344.709=SET, 287.415=NOV; 2025 set sem rótulo.
    "MT Oeste": {
        2024: [113189, 3209, 2131, 26634, 77518, 146493, 319531, None, 344709, None, 287415, None],
        2025: [19334, 1813, 538, 1530, 1876, 73472, 374080, 309879, None, 295558, 372432, 261254],
        2026: [43411, 3611, 2696, 4215, 3734, 96358, 61263, None, None, None, None, None],
    },
}

PRODUTO = "Milho"


def main():
    vol_rows = []
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                vol_rows.append((escopo, PRODUTO, ano, MESES[i], float(v), FONTE))

    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.executemany("INSERT INTO market_share_volume VALUES (?,?,?,?,?,?)", vol_rows)
    con.commit()

    print(f"market_share_volume (milho rodada 2): {len(vol_rows)} linhas")
    for escopo in VOLUME:
        n = sum(1 for r in vol_rows if r[0] == escopo)
        print(f"  {escopo}: {n} meses com volume lido")
    con.close()


if __name__ == "__main__":
    main()
