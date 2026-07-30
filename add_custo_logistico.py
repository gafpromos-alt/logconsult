# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Custo Logístico por Microrregião no banco
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Base nova (jul/2026): o usuário gravou em vídeo (celular filmando a tela do notebook —
09_Fotos/IMG_0218.MOV + IMG_0219.MOV, ~813s) um dashboard de terceiro ("Custo Logístico
Total por Microrregião") comparando rotas ferroviárias × rodoviárias (TCO — Total Cost of
Ownership) para exportação de soja pela microrregião "GO Leste" (Goiás Leste). Não há
export/planilha-fonte disponível — os dados abaixo foram transcritos manualmente lendo os
frames do vídeo (extraídos com ffmpeg em alta resolução, cada valor lido direto do rótulo
numérico impresso no gráfico, não estimado visualmente).

Cobertura: 6 de 9 meses disponíveis no filtro do vídeo foram efetivamente mostrados e lidos
(nov/2025, dez/2025, fev/2026, abr/2026, mai/2026, jun/2026) — jan/mar/jul/2026 não
apareceram nos frames capturados.

Abertura por categoria (2ª leitura, mais cuidadosa, a pedido do usuário — "quero tudo"):
cada barra do gráfico "TCO Modal - Destino Único" tem até 5 categorias empilhadas
(Demurrage, Elevação Portuária, Frete Ferroviário, Frete Rodoviário, Quebra), mas só as
que são grandes o suficiente ganham rótulo numérico visível. Capturamos com confiança:
Elevação Portuária (EP), Frete Ferroviário (FF, só rotas ferroviárias), Frete Rodoviário
(FR, aparece em TODAS as rotas — inclusive ferroviárias, provavelmente o trecho rodoviário
até o pátio/terminal). O que sobra (outros_rs_t = total − EP − FF − FR) é Demurrage +
Quebra somados — na maioria das barras pequenos demais pra ganhar rótulo próprio (só em
dez/2025 a Quebra apareceu destacada, ~16 R$/t em 3 das 5 rotas; nas outras barras esse
resíduo fica em ~10-30 R$/t, sem dar pra separar Demurrage de Quebra com confiança).

A série "Evolução Custos" (linha, 2022-2026, mês a mês, por rota) aparece no vídeo mas os
pontos ficam densos e sobrepostos demais (é um gráfico de linha detalhado, ~60 pontos por
rota) pra alinhar cada valor a um mês exato com confiança — não está nesta base.

Mais microrregiões serão adicionadas conforme o usuário mandar (ver estrutura MICRORREGIOES).
Go Sudoeste (2ª microrregião) já está incluída — ver comentário acima de _GO_SUDOESTE_SOJA.

Uso:  python3 add_custo_logistico.py
"""
import sqlite3, pathlib
BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

# mes (YYYY-MM) | rota | modal | elevacao_portuaria | frete_ferroviario | frete_rodoviario | total
# (outros_rs_t é calculado = total - EP - FF - FR, ver docstring)
_GO_LESTE_SOJA = [
    ("2025-11", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 101, 88, 249.08),
    ("2025-11", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 85, 113, 241.03),
    ("2025-11", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 111, 113, 294.39),
    ("2025-11", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 168, 204.06),
    ("2025-11", "Rodoviário: Santos", "Rodoviário", 23, 0, 263, 300.90),

    ("2025-12", "Ferroviário: Uberaba - Guarujá", "Ferroviário", 23, 85, 122, 248.56),
    ("2025-12", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 85, 122, 252.27),
    ("2025-12", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 98, 122, 292.42),
    ("2025-12", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 252, 287.38),
    ("2025-12", "Rodoviário: Santos", "Rodoviário", 23, 0, 261, 300.44),

    ("2026-02", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 185, 126, 391.43),
    ("2026-02", "Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 209, 102, 361.73),
    ("2026-02", "Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 204, 102, 358.60),
    ("2026-02", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 152, 147, 351.11),
    ("2026-02", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 167, 147, 392.82),
    ("2026-02", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 289, 333.47),
    ("2026-02", "Rodoviário: Paranaguá", "Rodoviário", 23, 0, 322, 370.95),
    ("2026-02", "Rodoviário: Santos", "Rodoviário", 23, 0, 299, 345.71),

    ("2026-04", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 176, 127, 375.12),
    ("2026-04", "Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 212, 162, 417.99),
    ("2026-04", "Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 192, 162, 399.56),
    ("2026-04", "Ferroviário: Uberaba - Guarujá", "Ferroviário", 23, 171, 169, 383.67),
    ("2026-04", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 171, 169, 385.24),
    ("2026-04", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 162, 169, 403.41),
    ("2026-04", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 315, 353.26),
    ("2026-04", "Rodoviário: Paranaguá", "Rodoviário", 23, 0, 357, 402.41),
    ("2026-04", "Rodoviário: Santos", "Rodoviário", 23, 0, 356, 396.06),

    ("2026-05", "Ferroviário: Araguari - Santos", "Ferroviário", 23, 177, 120, 339.59),
    ("2026-05", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 176, 120, 359.88),
    ("2026-05", "Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 190, 117, 350.53),
    ("2026-05", "Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 192, 117, 351.60),
    ("2026-05", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 161, 147, 350.80),
    ("2026-05", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 140, 147, 357.36),
    ("2026-05", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 307, 344.78),
    ("2026-05", "Rodoviário: Paranaguá", "Rodoviário", 23, 0, 359, 402.60),
    ("2026-05", "Rodoviário: Santos", "Rodoviário", 23, 0, 325, 362.92),

    ("2026-06", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 175, 126, 366.07),
    ("2026-06", "Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 190, 129, 359.90),
    ("2026-06", "Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 190, 129, 363.58),
    ("2026-06", "Ferroviário: Santa Luzia - Vitória", "Ferroviário", 23, 117, 168, 323.52),
    ("2026-06", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 133, 137, 341.31),
    ("2026-06", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 301, 336.15),
    ("2026-06", "Rodoviário: Paranaguá", "Rodoviário", 23, 0, 339, 378.13),
    ("2026-06", "Rodoviário: Santos", "Rodoviário", 23, 0, 327, 366.17),
]

# Go Sudoeste (jul/2026): 2ª microrregião, vídeo IMG_0220.MOV (529s). Mesmo dashboard de
# terceiro, mas desta vez com hover nativo sobre CADA segmento da barra ("Modal Destino /
# Categoria Custo / Valor / Total") — deu pra ler Elevação Portuária (EP) e Frete Ferroviário
# (FF) e Frete Rodoviário (FR) direto do rótulo impresso na barra (sem precisar de hover) em
# 2 meses com o filtro Período estável e legível: nov/2025 (Soja, 12 rotas) e dez/2025 (Milho,
# 11 rotas). Outros meses do dropdown "Período" (jan-jul/2026) apareceram só em trânsito
# (dropdown aberto, sem o gráfico assentado) — não incluídos, mesmo princípio de não inventar
# precisão que a fonte não sustenta.
_GO_SUDOESTE_SOJA = [
    ("2025-11", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 108, 125, 293.34),
    ("2025-11", "Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 155, 52, 248.02),
    ("2025-11", "Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 165, 52, 260.01),
    ("2025-11", "Ferroviário: São Simão - Guarujá", "Ferroviário", 23, 120, 83, 244.31),
    ("2025-11", "Ferroviário: São Simão - Santos", "Ferroviário", 23, 183, 83, 309.34),
    ("2025-11", "Ferroviário: Uberaba - Guarujá", "Ferroviário", 23, 88, 113, 242.51),
    ("2025-11", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 81, 113, 237.20),
    ("2025-11", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 109, 113, 292.74),
    ("2025-11", "Ferroviário: Uberaba - Vitória (VLI)", "Ferroviário", 50, 140, 113, 313.01),
    ("2025-11", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 247, 283.22),
    ("2025-11", "Rodoviário: Paranaguá", "Rodoviário", 23, 0, 185, 224.59),
    ("2025-11", "Rodoviário: Santos", "Rodoviário", 23, 0, 256, 294.20),
]
_GO_SUDOESTE_MILHO = [
    ("2025-12", "Ferroviário: Araguari - Vitória (VLI)", "Ferroviário", 50, 83, 131, 271.86),
    ("2025-12", "Ferroviário: Rio Verde - Guarujá", "Ferroviário", 23, 182, 51, 265.58),
    ("2025-12", "Ferroviário: Rio Verde - Santos", "Ferroviário", 23, 170, 51, 257.29),
    ("2025-12", "Ferroviário: São Simão - Guarujá", "Ferroviário", 23, 139, 75, 246.47),
    ("2025-12", "Ferroviário: São Simão - Santos", "Ferroviário", 23, 139, 75, 250.18),
    ("2025-12", "Ferroviário: Uberaba - Guarujá", "Ferroviário", 23, 90, 126, 248.01),
    ("2025-12", "Ferroviário: Uberaba - Santos", "Ferroviário", 23, 119, 126, 280.92),
    ("2025-12", "Ferroviário: Uberaba - Santos (VLI)", "Ferroviário", 50, 97, 126, 285.59),
    ("2025-12", "Rodoviário: Guarujá", "Rodoviário", 23, 0, 264, 293.83),
    ("2025-12", "Rodoviário: Paranaguá", "Rodoviário", 23, 0, 190, 222.91),
    ("2025-12", "Rodoviário: Santos", "Rodoviário", 23, 0, 251, 284.54),
]

MICRORREGIOES = {
    "GO Leste": {"Soja": _GO_LESTE_SOJA},
    "GO Sudoeste": {"Soja": _GO_SUDOESTE_SOJA, "Milho": _GO_SUDOESTE_MILHO},
}

# "Evolução Custos" (linha, 2021-2026, mês a mês, por rota) — na 1ª e 2ª passada este dado
# tinha sido descartado: o eixo X só marca ANO (sem mês/gridline) e os pontos de todas as
# rotas ficam sobrepostos, então ler direto do traçado da linha seria inventar precisão.
# 3ª passada (usuário indicou o caminho certo): passar o MOUSE sobre cada ponto do gráfico
# abre um TOOLTIP nativo do dashboard com a data exata (mês/ano) e os 6 valores (Total
# Custos, Quebra, Frete Rodoviário, Frete Ferroviário [só rotas ferroviárias], Elevação
# Portuária, Demurrage) escritos por extenso — sem ambiguidade de leitura. Reli os vídeos
# frame a frame (ffmpeg, ~1 frame/seg nos trechos com o tooltip visível) e transcrevi só os
# pontos em que a data E os 6 valores apareciam legíveis; todo ponto abaixo foi conferido
# batendo Total = Quebra+FR+FF+EP+Demurrage antes de entrar na base (tolerância 0,05, só
# arredondamento). Cobertura por rota é IRREGULAR (o vídeo não passou o mouse por todo mês
# de todo ano) — não preenchi os meses que faltam.
# formato: (rota, mes "YYYY-MM", total, quebra, frete_rodoviario, frete_ferroviario[None se
# rota rodoviária], elevacao_portuaria, demurrage)
_EVOLUCAO_GO_LESTE_SOJA = [
    ("Ferroviario: Araguari - Vitoria", "2021-06", 250.31, 20.31, 88.06, 81.11, 50.0, 10.84),
    ("Ferroviario: Araguari - Vitoria", "2021-09", 258.17, 18.62, 82.19, 102.39, 50.0, 4.97),
    ("Ferroviario: Araguari - Vitoria", "2021-12", 253.09, 20.05, 75.73, 101.55, 50.0, 5.76),
    ("Ferroviario: Araguari - Vitoria", "2022-07", 342.15, 22.13, 127.01, 127.69, 50.0, 15.32),
    ("Ferroviario: Araguari - Vitoria", "2022-08", 373.54, 21.25, 140.52, 140.52, 50.0, 21.26),
    ("Ferroviario: Araguari - Vitoria", "2022-09", 330.13, 20.65, 126.23, 117.88, 50.0, 15.37),
    ("Ferroviario: Araguari - Vitoria", "2022-10", 322.06, 19.99, 129.3, 117.55, 50.0, 5.22),
    ("Ferroviario: Araguari - Vitoria", "2023-07", 358.73, 19.62, 114.05, 153.87, 50.0, 21.19),
    ("Ferroviario: Araguari - Vitoria", "2023-10", 390.83, 17.92, 133.75, 174.11, 50.0, 15.05),
    ("Ferroviario: Araguari - Vitoria", "2023-12", 347.86, 17.69, 104.2, 154.29, 50.0, 21.68),
    ("Ferroviario: Araguari - Vitoria", "2024-05", 333.68, 17.31, 101.68, 171.91, 50.0, -7.22),
    ("Ferroviario: Araguari - Vitoria", "2024-06", 357.05, 17.4, 109.1, 182.93, 50.0, -2.38),
    ("Ferroviario: Araguari - Vitoria", "2024-08", 421.96, 14.94, 110.2, 241.28, 50.0, 5.54),
    ("Ferroviario: Araguari - Vitoria", "2024-10", 391.68, 15.54, 150.18, 164.58, 50.0, 11.38),
    ("Ferroviario: Araguari - Vitoria", "2024-11", 347.22, 15.98, 89.65, 159.03, 50.0, 32.56),
    ("Ferroviario: Araguari - Vitoria", "2025-11", 249.08, 16.64, 87.6, 101.13, 50.0, -6.28),
    ("Ferroviario: Araguari - Vitoria", "2026-05", 359.88, 16.5, 119.96, 176.47, 50.0, -3.05),
    ("Ferroviario: Uberaba - Santos", "2023-02", 371.82, 21.78, 146.34, 167.64, 23.0, 13.06),
    ("Ferroviario: Uberaba - Santos", "2023-03", 388.39, 21.33, 156.6, 181.58, 23.0, 5.88),
    ("Ferroviario: Uberaba - Santos", "2023-05", 290.99, 18.82, 124.57, 121.44, 23.0, 3.16),
    ("Ferroviario: Uberaba - Santos", "2023-07", 372.87, 19.62, 149.06, 163.55, 23.0, 17.64),
    ("Ferroviario: Uberaba - Santos", "2023-08", 360.42, 18.41, 145.88, 163.33, 23.0, 9.8),
    ("Ferroviario: Uberaba - Santos", "2023-10", 347.42, 17.92, 161.21, 123.76, 23.0, 21.53),
    ("Ferroviario: Uberaba - Santos", "2023-12", 347.76, 17.69, 125.49, 163.0, 23.0, 18.57),
    ("Ferroviario: Uberaba - Santos", "2024-01", 315.83, 16.71, 87.29, 179.21, 23.0, 9.63),
    ("Ferroviario: Uberaba - Santos", "2024-10", 363.77, 15.54, 134.07, 191.57, 23.0, -0.41),
    ("Ferroviario: Uberaba - Santos", "2024-12", 307.49, 16.58, 110.36, 159.98, 23.0, -2.38),
    ("Ferroviario: Uberaba - Santos", "2025-05", 398.52, 16.47, 148.75, 210.92, 23.0, -0.62),
    ("Ferroviario: Uberaba - Santos", "2025-08", 348.77, 15.11, 161.15, 140.71, 23.0, 8.8),
    ("Ferroviario: Uberaba - Santos", "2025-10", 284.29, 15.36, 142.52, 100.01, 23.0, 3.4),
    ("Ferroviario: Uberaba - Santos", "2026-01", 221.74, 15.58, 82.83, 85.25, 23.0, 15.08),
    ("Ferroviario: Uberaba - Santos", "2026-03", 397.84, 16.98, 167.34, 178.97, 23.0, 11.55),
    ("Ferroviario: Uberaba - Santos (VLI)", "2021-05", 273.31, 22.71, 104.05, 93.0, 50.0, 3.55),
    ("Ferroviario: Uberaba - Santos (VLI)", "2021-06", 271.77, 20.31, 103.98, 96.61, 50.0, 0.88),
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-06", 317.51, 23.49, 144.5, 88.03, 50.0, 11.5),
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-07", 359.39, 22.13, 168.27, 104.32, 50.0, 14.66),
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-10", 317.59, 19.99, 132.29, 116.09, 50.0, -0.79),
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-11", 317.52, 20.96, 130.18, 113.73, 50.0, 2.65),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-03", 403.84, 21.33, 156.6, 170.03, 50.0, 5.88),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-06", 321.67, 19.14, 124.59, 117.88, 50.0, 10.05),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-09", 386.34, 18.12, 165.23, 141.15, 50.0, 11.85),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-12", 362.07, 17.69, 125.49, 150.32, 50.0, 18.57),
    ("Ferroviario: Uberaba - Santos (VLI)", "2024-04", 395.77, 16.45, 125.21, 205.44, 50.0, -1.33),
    ("Ferroviario: Uberaba - Santos (VLI)", "2024-07", 457.03, 16.91, 147.74, 240.83, 50.0, 1.56),
    ("Ferroviario: Uberaba - Santos (VLI)", "2024-10", 354.28, 15.54, 134.07, 155.08, 50.0, -0.41),
    ("Ferroviario: Uberaba - Santos (VLI)", "2024-12", 331.51, 16.52, 110.36, 157.01, 50.0, -2.38),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-02", 395.09, 16.53, 156.02, 160.94, 50.0, 11.61),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-04", 404.43, 16.4, 127.45, 209.14, 50.0, 1.43),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-08", 448.03, 15.11, 161.15, 212.96, 50.0, 8.8),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-09", 353.59, 15.19, 139.47, 142.43, 50.0, 6.5),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-12", 292.42, 16.17, 122.17, 98.4, 50.0, 5.68),
    ("Ferroviario: Uberaba - Santos (VLI)", "2026-02", 392.82, 16.1, 146.9, 166.62, 50.0, 13.19),
    ("Ferroviario: Uberaba - Santos (VLI)", "2026-05", 357.36, 16.5, 147.16, 140.23, 50.0, 3.47),
    ("Ferroviario: Uberaba - Santos (VLI)", "2026-06", 341.31, 15.9, 136.87, 133.16, 50.0, 5.37),
    ("Ferroviario: Uberaba - Santos (VLI)", "2026-07", 343.16, 16.85, 141.99, 138.56, 50.0, -4.24),
    ("Rodoviario: Guaruja", "2021-02", 242.08, 13.75, 187.87, None, 23.0, 17.47),
    ("Rodoviario: Guaruja", "2021-05", 243.34, 15.14, 202.09, None, 23.0, 3.11),
    ("Rodoviario: Guaruja", "2021-07", 204.43, 13.42, 175.0, None, 23.0, -6.99),
    ("Rodoviario: Guaruja", "2021-11", 206.58, 12.7, 177.65, None, 23.0, -6.77),
    ("Rodoviario: Guaruja", "2022-01", 263.75, 14.26, 213.36, None, 23.0, 13.13),
    ("Rodoviario: Guaruja", "2022-03", 367.39, 15.39, 316.65, None, 23.0, 12.35),
    ("Rodoviario: Guaruja", "2022-05", 334.66, 15.12, 295.2, None, 23.0, 1.34),
    ("Rodoviario: Guaruja", "2022-08", 369.77, 14.17, 324.34, None, 23.0, 8.26),
    ("Rodoviario: Guaruja", "2022-09", 335.99, 13.77, 304.49, None, 23.0, -5.27),
    ("Rodoviario: Guaruja", "2022-11", 305.99, 13.97, 267.96, None, 23.0, 1.06),
    ("Rodoviario: Guaruja", "2022-12", 350.11, 14.24, 307.5, None, 23.0, 5.37),
    ("Rodoviario: Guaruja", "2023-02", 365.73, 14.52, 314.19, None, 23.0, 14.02),
    ("Rodoviario: Guaruja", "2023-04", 321.98, 13.73, 285.98, None, 23.0, -0.73),
    ("Rodoviario: Guaruja", "2023-07", 367.29, 13.08, 326.24, None, 23.0, 4.98),
    ("Rodoviario: Guaruja", "2023-08", 396.1, 12.27, 349.07, None, 23.0, 11.76),
    ("Rodoviario: Guaruja", "2023-10", 400.81, 11.95, 352.12, None, 23.0, 13.75),
    ("Rodoviario: Guaruja", "2024-01", 261.0, 11.14, 225.34, None, 23.0, 1.52),
    ("Rodoviario: Guaruja", "2024-03", 314.94, 10.84, 278.83, None, 23.0, 2.27),
    ("Rodoviario: Guaruja", "2024-05", 311.67, 11.54, 279.94, None, 23.0, -2.81),
    ("Rodoviario: Guaruja", "2024-06", 328.66, 11.6, 291.95, None, 23.0, 2.1),
    ("Rodoviario: Guaruja", "2024-08", 282.32, 9.96, 249.96, None, 23.0, -0.6),
    ("Rodoviario: Guaruja", "2024-10", 186.26, 10.36, 155.83, None, 23.0, -2.93),
    ("Rodoviario: Guaruja", "2025-01", 255.59, 11.42, 214.15, None, 23.0, 7.02),
    ("Rodoviario: Guaruja", "2025-03", 364.62, 11.7, 327.15, None, 23.0, 2.77),
    ("Rodoviario: Guaruja", "2025-06", 327.46, 10.7, 294.41, None, 23.0, -0.65),
    ("Rodoviario: Guaruja", "2025-07", 286.58, 10.26, 256.39, None, 23.0, -3.08),
    ("Rodoviario: Guaruja", "2025-09", 260.57, 10.12, 230.02, None, 23.0, -2.57),
    ("Rodoviario: Guaruja", "2025-11", 204.06, 11.1, 168.14, None, 23.0, 1.83),
    ("Rodoviario: Guaruja", "2026-01", 288.59, 10.38, 245.77, None, 23.0, 9.43),
    ("Rodoviario: Guaruja", "2026-02", 333.47, 10.74, 288.56, None, 23.0, 11.17),
    ("Rodoviario: Guaruja", "2026-05", 344.78, 11.0, 306.66, None, 23.0, 4.12),
    ("Rodoviario: Guaruja", "2026-07", 320.88, 11.1, 289.91, None, 23.0, -3.13),
    ("Rodoviario: Santos", "2022-10", 303.99, 13.33, 268.46, None, 23.0, -0.79),
    ("Rodoviario: Santos", "2022-11", 311.91, 13.97, 272.29, None, 23.0, 2.65),
    ("Rodoviario: Santos", "2022-12", 342.97, 14.24, 300.42, None, 23.0, 5.31),
    ("Rodoviario: Santos", "2023-03", 376.29, 14.22, 333.19, None, 23.0, 5.88),
    ("Rodoviario: Santos", "2023-05", 339.41, 12.54, 300.7, None, 23.0, 3.16),
    ("Rodoviario: Santos", "2023-07", 389.14, 13.08, 335.42, None, 23.0, 17.64),
    ("Rodoviario: Santos", "2023-08", 394.2, 12.27, 349.13, None, 23.0, 9.8),
    ("Rodoviario: Santos", "2023-11", 344.1, 12.2, 293.23, None, 23.0, 15.68),
    ("Rodoviario: Santos", "2024-03", 313.28, 10.84, 274.4, None, 23.0, 5.03),
    ("Rodoviario: Santos", "2024-05", 322.16, 11.54, 287.23, None, 23.0, 0.39),
    ("Rodoviario: Santos", "2024-07", 358.51, 11.27, 322.68, None, 23.0, 1.56),
    ("Rodoviario: Santos", "2024-08", 319.72, 9.96, 287.15, None, 23.0, -0.39),
    ("Rodoviario: Santos", "2024-10", 258.31, 10.36, 225.36, None, 23.0, -0.41),
    ("Rodoviario: Santos", "2025-01", 242.63, 11.42, 198.02, None, 23.0, 10.19),
    ("Rodoviario: Santos", "2025-03", 401.79, 10.7, 362.29, None, 23.0, 5.8),
    ("Rodoviario: Santos", "2025-05", 332.88, 10.98, 299.52, None, 23.0, -0.62),
    ("Rodoviario: Santos", "2025-08", 382.93, 10.08, 341.06, None, 23.0, 8.8),
    ("Rodoviario: Santos", "2025-10", 311.81, 10.24, 275.17, None, 23.0, 3.4),
    ("Rodoviario: Santos", "2026-01", 285.31, 10.38, 236.84, None, 23.0, 15.08),
    ("Rodoviario: Santos", "2026-04", 396.06, 10.79, 356.35, None, 23.0, 5.92),
    ("Rodoviario: Santos", "2026-07", 358.08, 11.1, 328.02, None, 23.0, -4.04),
]

# Evolução Custos — Go Sudoeste (vídeo IMG_0220.MOV). Mesma técnica de tooltip; desta vez o
# vídeo passou o mouse por bem mais pontos (4 rotas com o filtro "Rota" trocado ao longo do
# vídeo: Uberaba-Santos(VLI), Uberaba-Santos, Uberaba-Guarujá, São Simão-Santos). Todo ponto
# abaixo bate Total = Quebra+FR+FF+EP+Demurrage (tolerância 0,05). Produto: o filtro "Produto"
# fica fora da tela nos frames do painel Evolução Custos (câmera não mostrou); tratado como
# Soja por ser o produto ativo antes do painel abrir (mesma suposição do Go Leste).
_EVOLUCAO_GO_SUDOESTE_SOJA = [
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-04", 335.84, 22.07, 138.45, 120.84, 50.0, 4.47),
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-07", 395.04, 22.13, 148.80, 159.44, 50.0, 14.66),
    ("Ferroviario: Uberaba - Santos (VLI)", "2022-11", 290.58, 20.96, 134.26, 82.71, 50.0, 2.65),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-05", 312.34, 18.82, 119.01, 121.36, 50.0, 3.16),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-09", 361.46, 18.12, 149.46, 132.04, 50.0, 11.85),
    ("Ferroviario: Uberaba - Santos (VLI)", "2023-12", 349.12, 17.69, 123.12, 139.73, 50.0, 18.57),
    ("Ferroviario: Uberaba - Santos (VLI)", "2024-05", 361.29, 17.31, 98.37, 195.22, 50.0, 0.39),
    ("Ferroviario: Uberaba - Santos (VLI)", "2024-10", 340.52, 15.54, 116.31, 159.08, 50.0, -0.41),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-04", 375.01, 16.40, 110.34, 196.84, 50.0, 1.43),
    ("Ferroviario: Uberaba - Santos (VLI)", "2025-09", 344.78, 15.19, 123.41, 149.69, 50.0, 6.50),
    ("Ferroviario: Uberaba - Santos (VLI)", "2026-02", 394.99, 16.10, 157.31, 158.38, 50.0, 13.19),
    ("Ferroviario: Uberaba - Santos (VLI)", "2026-06", 352.88, 15.90, 135.97, 145.63, 50.0, 5.37),
    ("Ferroviario: Uberaba - Santos", "2023-04", 351.16, 20.59, 130.50, 178.84, 23.0, -1.77),
    ("Ferroviario: Uberaba - Santos", "2023-09", 337.08, 18.12, 149.46, 134.66, 23.0, 11.85),
    ("Ferroviario: Uberaba - Santos", "2024-05", 332.16, 17.31, 98.37, 193.09, 23.0, 0.39),
    ("Ferroviario: Uberaba - Santos", "2024-10", 338.27, 15.54, 116.31, 183.83, 23.0, -0.41),
    ("Ferroviario: Uberaba - Santos", "2025-05", 347.29, 16.47, 111.61, 196.83, 23.0, -0.62),
    ("Ferroviario: Uberaba - Santos", "2025-12", 289.94, 16.17, 125.70, 119.39, 23.0, 5.68),
    ("Ferroviario: Uberaba - Santos", "2026-07", 292.35, 16.65, 126.27, 130.47, 23.0, -4.04),
    ("Ferroviario: Uberaba - Guaruja", "2021-10", 213.06, 18.78, 75.33, 99.36, 23.0, -3.41),
    ("Ferroviario: Uberaba - Guaruja", "2022-05", 304.69, 22.68, 138.42, 119.25, 23.0, 1.34),
    ("Ferroviario: Uberaba - Guaruja", "2022-12", 289.50, 21.35, 148.89, 90.88, 23.0, 5.37),
    ("Ferroviario: Uberaba - Guaruja", "2023-06", 322.63, 19.14, 115.14, 159.54, 23.0, 5.80),
    ("Ferroviario: Uberaba - Guaruja", "2024-03", 398.63, 16.26, 109.58, 247.51, 23.0, 2.27),
    ("Ferroviario: Uberaba - Guaruja", "2024-07", 389.77, 16.91, 108.43, 243.95, 23.0, -2.52),
    ("Ferroviario: Uberaba - Guaruja", "2024-12", 293.84, 16.52, 85.11, 172.58, 23.0, -3.37),
    ("Ferroviario: Uberaba - Guaruja", "2025-06", 341.80, 16.05, 115.84, 187.55, 23.0, -0.65),
    ("Ferroviario: Uberaba - Guaruja", "2026-01", 250.72, 15.58, 117.46, 85.25, 23.0, 9.43),
    ("Ferroviario: Uberaba - Guaruja", "2026-07", 321.29, 16.65, 126.27, 158.50, 23.0, -3.13),
    ("Ferroviario: Sao Simao - Santos", "2022-10", 231.74, 19.99, 82.60, 106.95, 23.0, -0.79),
    ("Ferroviario: Sao Simao - Santos", "2023-04", 335.63, 20.59, 103.79, 190.02, 23.0, -1.77),
    ("Ferroviario: Sao Simao - Santos", "2023-09", 302.67, 18.12, 107.33, 142.38, 23.0, 11.85),
    ("Ferroviario: Sao Simao - Santos", "2024-04", 324.67, 16.45, 77.54, 209.01, 23.0, -1.33),
    ("Ferroviario: Sao Simao - Santos", "2024-09", 379.55, 15.60, 81.44, 258.30, 23.0, 1.22),
    ("Ferroviario: Sao Simao - Santos", "2025-03", 379.69, 16.05, 115.93, 218.91, 23.0, 5.80),
    ("Ferroviario: Sao Simao - Santos", "2025-11", 309.34, 16.64, 82.88, 183.00, 23.0, 3.82),
    ("Ferroviario: Sao Simao - Santos", "2026-04", 312.45, 16.19, 99.24, 168.10, 23.0, 5.92),
]

FONTE = ("Vídeo do usuário (celular filmando dashboard de terceiro, "
         "09_Fotos/IMG_0218.MOV + IMG_0219.MOV, IMG_0220.MOV) — transcrição manual dos rótulos "
         "numéricos do gráfico.")
FONTE_EVOLUCAO = ("Vídeo do usuário (celular filmando dashboard de terceiro, "
                   "09_Fotos/IMG_0218.MOV + IMG_0219.MOV, IMG_0220.MOV) — transcrição do tooltip nativo "
                   "do gráfico 'Evolução Custos' (data + 6 valores por ponto), conferida por soma-bate-total.")


EVOLUCAO_MICRORREGIOES = {
    "GO Leste": {"Soja": _EVOLUCAO_GO_LESTE_SOJA},
    "GO Sudoeste": {"Soja": _EVOLUCAO_GO_SUDOESTE_SOJA},
}


def main():
    rows = []
    for micro, produtos in MICRORREGIOES.items():
        for produto, lista in produtos.items():
            for mes, rota, modal, ep, ff, fr, total in lista:
                outros = round(total - ep - ff - fr, 2)
                rows.append((micro, produto, mes, rota, modal, ep, ff, fr, outros, round(total, 2), FONTE))

    evo_rows = []
    for micro, produtos in EVOLUCAO_MICRORREGIOES.items():
        for produto, lista in produtos.items():
            for rota, mes, total, quebra, fr, ff, ep, demurrage in lista:
                modal = "Ferroviário" if ff is not None else "Rodoviário"
                evo_rows.append((micro, produto, rota, mes, modal, round(total, 2), round(quebra, 2),
                                  round(fr, 2), round(ff, 2) if ff is not None else None,
                                  round(ep, 2), round(demurrage, 2), FONTE_EVOLUCAO))

    con = sqlite3.connect(DB); cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS custo_logistico_microrregiao")
    cur.execute("""CREATE TABLE custo_logistico_microrregiao(
        microrregiao TEXT, produto TEXT, mes TEXT, rota TEXT, modal TEXT,
        elevacao_portuaria_rs_t REAL, frete_ferroviario_rs_t REAL, frete_rodoviario_rs_t REAL,
        outros_rs_t REAL, total_rs_t REAL, fonte TEXT)""")
    cur.executemany("INSERT INTO custo_logistico_microrregiao VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)

    cur.execute("DROP TABLE IF EXISTS custo_logistico_evolucao")
    cur.execute("""CREATE TABLE custo_logistico_evolucao(
        microrregiao TEXT, produto TEXT, rota TEXT, mes TEXT, modal TEXT,
        total_rs_t REAL, quebra_rs_t REAL, frete_rodoviario_rs_t REAL, frete_ferroviario_rs_t REAL,
        elevacao_portuaria_rs_t REAL, demurrage_rs_t REAL, fonte TEXT)""")
    cur.executemany("INSERT INTO custo_logistico_evolucao VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", evo_rows)
    con.commit()

    print(f"custo_logistico_microrregiao: {len(rows)} linhas")
    for micro, produtos in MICRORREGIOES.items():
        for produto, lista in produtos.items():
            meses = sorted(set(r[0] for r in lista))
            print(f"  {micro} / {produto}: {len(lista)} linhas, {len(meses)} meses ({meses[0]} a {meses[-1]})")

    print(f"custo_logistico_evolucao: {len(evo_rows)} linhas")
    for micro, produtos in EVOLUCAO_MICRORREGIOES.items():
        for produto, lista in produtos.items():
            for rota in sorted(set(r[0] for r in lista)):
                meses = sorted(m for r, m, *_ in lista if r == rota)
                print(f"  {micro} / {produto} / {rota}: {len(meses)} meses ({meses[0]} a {meses[-1]})")
    con.close()


if __name__ == "__main__":
    main()
