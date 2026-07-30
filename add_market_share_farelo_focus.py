# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=FARELO DE SOJA
Rodada "MODO DE FOCO / EXPANDIR" — CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

OBJETIVO (pedido do usuário): preencher as lacunas de VOLUME de Farelo de Soja usando o
"modo de foco / expandir" do dashboard Power BI de terceiro ("Competitividade"). A premissa
era que cada painel de ano (2024/2025/2026) teria um ícone "expandir" que abre o gráfico
GRANDE em tela cheia, com os 12 meses TODOS rotulados sem colisão — e que os meses faltantes
estariam ali. Fonte apontada: 09_Fotos/IMG_0224.MOV, IMG_0225.MOV, IMG_0226.MOV.

RESULTADO DA INVESTIGAÇÃO (15/jul/2026) — NENHUM DADO NOVO FOI EXTRAÍDO. Motivos, apurados
frame a frame (ffmpeg fps=1; 255+236+101 = 592 frames; contact sheets 6x5 de todos os três
vídeos + zoom em frames-chave em 1920x1080):

1) O "modo de foco" (tela cheia com 1 gráfico e botão "Voltar ao relatório") NÃO APARECE em
   NENHUM frame de NENHUM dos três vídeos. Todos os 592 frames mostram exclusivamente o
   layout padrão de 3 painéis lado a lado (2024 | 2025 | 2026). O ícone de expandir existe na
   barra de ferramentas do visual (⤢, visível ao lado do título de cada ano), mas o
   apresentador NUNCA o clicou durante as gravações. O botão da barra superior-esquerda
   (x~55-95) é a seta de "voltar" do navegador/PowerBI, não o "Voltar ao relatório" do focus.

2) IMG_0225.MOV é do PRODUTO ERRADO. O dropdown "Produto" no topo lê "FARELO DE MILHO"
   (confirmado por zoom no frame f002), não "Farelo de Soja". IMG_0225 é um walkthrough
   completo, região a região, de Farelo de MILHO — produto distinto, fora do escopo deste
   arquivo. (Obs. para o backlog: é a fonte que faltava para o módulo Farelo de Milho, hoje
   pendente no banco.) Apenas IMG_0224 e IMG_0226 são Farelo de Soja — e ambos já foram
   transcritos por completo em add_market_share_farelo_soja.py.

3) No layout de 3 painéis (única visão que os vídeos oferecem), os meses-alvo faltantes são
   EXATAMENTE as barras cujo rótulo numérico o Power BI esconde por colisão. Ex.: Nacional
   2024 mostra rótulo só em jan/mar/abr/jul/ago/out/nov (os 7 já no banco); fev/mai/jun/set/dez
   ficam sem rótulo — idênticos à lacuna. Sem tela cheia (mais espaço horizontal) esses
   rótulos não existem na imagem. Foi por isso que o usuário pediu o modo de foco; como ele
   não foi acionado nas gravações, os valores permanecem ilegíveis.

4) Tooltip de drill-through (caixa "Date Mês / Volume Total / Aux Ordenador") foi a única via
   alternativa de leitura. O apresentador só passou o mouse sobre "2025 janeiro" (=899.528) na
   seção Nacional do IMG_0224 (frames f001-f002) — mês JÁ existente no banco. Nenhum tooltip
   sobre mês-alvo faltante em nenhum frame.

DISCIPLINA DO PROJETO ("não inventar precisão"): como nenhuma célula-alvo ficou legível, este
script NÃO insere nada. VOLUME está vazio de propósito. Fica como slot idempotente da cadeia:
se no futuro o usuário gravar um vídeo ACIONANDO o modo de foco (clicar o ícone ⤢ em cada
painel de ano, com Produto=FARELO DE SOJA e Microrregião selecionada), basta transcrever os
12 rótulos aqui e rodar — o padrão INSERT ... WHERE NOT EXISTS garante que nada duplica.

Para preencher de fato as lacunas-alvo (Nacional, MT Sudeste, PR, MT Medio Norte, SP, RS,
BA Oeste Norte), a captura precisa: (a) confirmar Produto=FARELO DE SOJA no topo; (b) abrir a
Microrregião desejada; (c) clicar EXPANDIR (⤢) no painel do ano; (d) filmar estável o gráfico
grande com os 12 rótulos; (e) identificar a região por valor-âncora, não pelo banner.

IMPORTANTE: só INSERT (idempotente, WHERE NOT EXISTS), nunca DROP. Roda DEPOIS de
add_market_share_farelo_soja.py. Ver ordem canônica em rebuild_market_share.sh.

NÃO EXECUTADO — script preparado para revisão do usuário antes de rodar.
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "Produto=FARELO DE SOJA) — rodada \"modo de foco/expandir\". Nenhum frame dos vídeos "
         "IMG_0224/IMG_0225/IMG_0226 exibiu o modo de foco em tela cheia; os meses-alvo "
         "permanecem sem rótulo (colisão) no layout de 3 painéis. Sem inserção nesta rodada.")

# escopo -> {ano: [12 meses, None = sem rótulo/colisão/ilegível]}
# VAZIO DE PROPÓSITO — ver docstring. Preencher só com rótulos lidos em modo de foco real,
# identificando a região por valor-âncora (SELECT ... WHERE volume_t=<valor>), nunca pelo banner.
VOLUME = {}

PRODUTO = "Farelo de Soja"


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    vol_inserted = 0
    vol_skipped = 0
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                mes = MESES[i]
                cur.execute(
                    """INSERT INTO market_share_volume (escopo, produto, ano, mes, volume_t, fonte)
                       SELECT ?, ?, ?, ?, ?, ?
                       WHERE NOT EXISTS (
                           SELECT 1 FROM market_share_volume
                           WHERE escopo=? AND produto=? AND ano=? AND mes=?
                       )""",
                    (escopo, PRODUTO, ano, mes, float(v), FONTE, escopo, PRODUTO, ano, mes),
                )
                if cur.rowcount:
                    vol_inserted += 1
                else:
                    vol_skipped += 1

    con.commit()

    print(f"market_share_volume (Farelo de Soja, modo de foco): {vol_inserted} linhas novas "
          f"inseridas ({vol_skipped} já existiam / puladas)")
    if not VOLUME:
        print("  VOLUME vazio: nenhum frame dos vídeos exibiu o modo de foco em tela cheia; "
              "meses-alvo permanecem ilegíveis (colisão de rótulo). Ver docstring.")
    con.close()


if __name__ == "__main__":
    main()
