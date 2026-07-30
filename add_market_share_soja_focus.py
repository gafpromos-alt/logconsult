# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=SOJA — RODADA FOCO
CONFIDENCIAL — USO RESTRITO AOS SOCIOS

Fonte: videos do usuario 09_Fotos/IMG_0221.MOV e IMG_0229.MOV (Produto=SOJA, dimensao
Microrregiao). O MODO DE FOCO ("Expandir"/tela cheia) do Power BI foi usado para abrir cada
painel de ANO em tela cheia com os 12 meses TODOS rotulados, sem colisao de rotulos. Essa e a
fonte DEFINITIVA para os meses que nao aparecem na visao compacta de 3 paineis.

  - IMG_0221.MOV: 437s, tour compacto de todas as microrregioes (NENHUM modo de foco). Sem dados novos.
  - IMG_0229.MOV: 512s, tour com EXPANSOES (modo de foco) painel a painel. Fonte deste script.

Disciplina de precisao (regra-mae "nao inventar precisao"):
  - Mes com rotulo cortado pela borda da tela (ex.: dezembro fora do frame) = None, nunca chutado.
  - Regiao/ano identificados por MATCH DE VALOR-ANCORA no proprio banco (idsoja), nao pelo banner
    (o banner "Competitividade - XXX" NAO acompanha o dropdown e e' pouco confiavel).

*** ACHADO CRITICO — SHIFT DE 1 MES NO BANCO EXISTENTE (add_market_share.py) ***
  Varios paineis de foco revelam que a transcricao ORIGINAL da visao compacta (add_market_share.py)
  esta DESLOCADA 1 mes a partir de ~abril: o valor gravado em "abril" e', na verdade, MAIO no eixo
  do Power BI; "maio" e' JUNHO; "junho" e' JULHO; etc. Jan/fev/mar batem. Ex. Nacional 2025 abaixo.
  Este script e' INSERT-ONLY (WHERE NOT EXISTS): so preenche meses HOJE AUSENTES, NAO corrige os
  meses ja gravados (mesmo que deslocados). A reconciliacao do shift fica para a conversa principal.
  Efeito colateral esperado: em regioes deslocadas, um mes recem-inserido pode repetir o valor do
  mes anterior ja gravado (sinal do shift) — isso e' esperado e esta sinalizado no relatorio.

IMPORTANTE: so INSERT (nao DROP). Roda DEPOIS de add_market_share.py (que faz DROP+CREATE e
popula Soja). Ordem canonica: rebuild_market_share.sh.
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Video do usuario (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0229.MOV, Produto=SOJA) — MODO DE FOCO/tela cheia, transcricao manual dos "
         "12 rotulos mensais de Volume. Fonte definitiva p/ meses ocultos por colisao na visao compacta.")

PRODUTO = "Soja"

# escopo -> {ano: [12 valores; None = rotulo ilegivel/cortado]}.
# Cada serie e' a leitura DEFINITIVA (focus-true) dos 12 meses no eixo do Power BI.
# O INSERT ... WHERE NOT EXISTS abaixo so grava os meses HOJE AUSENTES no banco.
#
# *** PODA APLICADA NA CONVERSA PRINCIPAL (15/jul/2026) ***
# Foram REMOVIDAS deste dict as regioes que o proprio agente sinalizou como problematicas, para
# NAO corromper o banco com um INSERT-only:
#   - Nacional 2025, GO Leste 2024, MT Norte 2024: SHIFT no banco existente. Inserir o "alvo" ali
#     duplicaria o valor da celula vizinha ja deslocada (ex.: MT Norte gravaria mar=1.074.228 sendo
#     que esse valor ja esta no banco como abr). Shift exige MOVER meses (rebuild), nao insert.
#   - BA Oeste Sul 2024 set (~108.1xx) e MT Oeste 2025 dez (~95.6xx): rotulo BORRADO, digitos
#     incertos -> regra "nao inventar precisao".
# Todas essas ficam reportadas ao usuario para decisao/re-gravacao; ver docstring/relatorio.
# Mantidas abaixo APENAS as 5 regioes ALINHADAS e NITIDAS (9 celulas-alvo).
VOLUME = {
    # MT Nordeste 2024 (IMG_0229 f080; "Voltar ao relatorio" no canto = foco). ALINHADO com o
    # banco (jan-jul, set, dez batem exatamente; nov 72.169~72.165). Preenche alvos ago/out.
    # 2025 do foco (f073) = 12/12 ja no banco, alinhado, nada novo.
    "MT Nordeste": {
        2024: [172572, 570571, 508613, 348706, 407673, 311031,
               138068, 103245, 92195, 133088, 72169, 30990],
    },
    # PA Sudeste 2025 (IMG_0229 f096; "Voltar ao relatorio" no canto). ALINHADO com o banco
    # (fev-jun, ago, set batem). Preenche alvo julho=127.229 (o banco pulava de jun p/ ago).
    # out/nov ja existem; dezembro nao aparece no eixo do foco (chart termina em nov) -> None.
    "PA Sudeste": {
        2025: [479, 105091, 207157, 152229, 116681, 147315,
               127229, 95910, 45080, None, None, None],
    },
    # GO Sudoeste 2024 (IMG_0229 f214, focus). ALINHADO (jul/ago batem). Preenche alvos set=200.054
    # e nov=83.434. Obs.: o foco mostra out=118.170, mas o banco tem out=158.170 (provavel erro de
    # OCR 1<->5 na transcricao original); out ja existe -> WHERE NOT EXISTS nao mexe. dez cortado na
    # borda (banco ja tem 67.209). 2025 (f209) esta 12/12 e alinhado (nada novo).
    "GO Sudoeste": {
        2024: [340756, 1329390, 1031529, 758044, 909563, 882057,
               431458, 234545, 200054, 118170, 83434, None],
    },
    # MT Sudeste 2024 (IMG_0229 f285, foco LIMPO; f284 tinha labels duplicados por selecao->ignorado).
    # ALINHADO (jan,fev,abr,mai,jul,set,dez batem com o banco). Preenche alvos jun=340.388,
    # ago=197.773, out=125.740. Obs.: banco tem nov=81.933 vs foco ~93.933 (nov ja existe, nao mexe).
    # 2025 (f280) esta 12/12 e alinhado.
    "MT Sudeste": {
        2024: [265562, 565579, 395294, 335161, 395993, 340388,
               226023, 197773, 133300, 125740, 81933, 85334],
    },
    # MS Norte 2024 (IMG_0229 f365, foco). ALINHADO (jul-dez batem). Preenche alvo jun=169.596
    # (pico entre mai 155.545 e jul 67.234; o banco pulava de mai p/ jul). Meses existentes usam o
    # valor do banco (mar/mai tiveram leve ruido de OCR no video, mas ja existem -> nao inseridos).
    "MS Norte": {
        2024: [24355, 113941, 150194, 196928, 158343, 169596,
               67234, 32334, 19671, 16382, 1237, 374],
    },
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    inserted = 0
    per_scope = {}
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for i, v in enumerate(meses):
                if v is None:
                    continue
                cur.execute(
                    "INSERT INTO market_share_volume (escopo,produto,ano,mes,volume_t,fonte) "
                    "SELECT ?,?,?,?,?,? WHERE NOT EXISTS ("
                    "  SELECT 1 FROM market_share_volume "
                    "  WHERE escopo=? AND produto=? AND ano=? AND mes=?)",
                    (escopo, PRODUTO, ano, MESES[i], float(v), FONTE,
                     escopo, PRODUTO, ano, MESES[i]),
                )
                if cur.rowcount:
                    inserted += cur.rowcount
                    per_scope[(escopo, ano)] = per_scope.get((escopo, ano), 0) + 1
    con.commit()
    print(f"market_share_volume (soja foco): {inserted} celulas novas inseridas")
    for (escopo, ano), n in sorted(per_scope.items()):
        print(f"  {escopo} {ano}: +{n}")
    con.close()


if __name__ == "__main__":
    main()
