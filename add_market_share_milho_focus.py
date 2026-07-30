# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade), Produto=MILHO — MODO DE FOCO
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Fonte: vídeo do usuário (celular filmando dashboard Power BI de terceiro "Competitividade",
09_Fotos/IMG_0235.MOV, 275s, gravado 13/07/2026) — Produto=MILHO, dimensão Microrregião.
Mineração dos frames em MODO DE FOCO / TELA CHEIA ("Voltar ao relatório"): o usuário expandiu
alguns painéis de ano para tela cheia, onde cada gráfico aparece GRANDE com os 12 meses
rotulados por extenso (janeiro..dezembro) e sem colisão de rótulo, permitindo ler meses que no
relatório de 3 painéis ficavam escondidos.

Cobertura dos vídeos (frames a 1fps):
- IMG_0222.MOV: NENHUM frame em tela cheia — o vídeo inteiro é o relatório de 3 painéis
  (2024/2025/2026 lado a lado). Nada a extrair aqui pelo modo de foco.
- IMG_0235.MOV: 8 expansões de tela cheia (curtas, ~1-3s cada). Regiões/anos identificados por
  MATCH DE VALOR-ÂNCORA contra a série já no banco (regra-mãe: o banner do topo NÃO é confiável;
  identidade sempre confirmada pelos meses que batem 100% com o banco):
    f034-035  -> MT Nordeste 2025   (jan..set batem com o banco)  [SHIFT — ver relatório, NÃO gravado]
    f096-104  -> GO Sudoeste 2025   (fev..nov batem)              -> dez=612.756  (NOVO)
    f127-128  -> MT Medio Norte 2025(jan..jul batem)              [SHIFT — ver relatório, NÃO gravado]
    f135-136  -> MT Nordeste Sul 2025(jan..jul batem)             -> ago=242.991  (NOVO); nov cortado
    f143-144  -> MT Sudeste 2025    (jan..ago batem)              -> set=308.258  (NOVO); nov cortado
    f205-206  -> MT Norte 2025      (jan..ago batem)              -> set=1.538.252, nov=646.105 (NOVOS)
    f211      -> MT Norte 2024      (fev..jul batem)              -> ago=1.174.029, nov=511.402 (NOVOS)
    f242      -> PR 2025            (fev,abr..ago batem)          -> mar=101.161  (NOVO); out cortado

Disciplina de precisão (regras do projeto), aplicada aqui:
- Só entra número lido com nitidez no gráfico em tela cheia, com o rótulo do próprio mês visível.
- Bar/rótulo cortado no topo da tela (setembro/outubro/novembro altos saíam para fora do quadro)
  ou dezembro cortado na borda direita = NÃO lido -> fica fora do dict (nunca chutado).
- Cada valor gravado abaixo é um mês que HOJE está VAZIO no banco (buraco) E cujos meses vizinhos
  no mesmo frame batem 100% com o banco (frame alinhado, sem shift). Confirmado por SELECT antes
  de escrever.
- Regiões com SHIFT (o frame de foco mostra o pico um mês adiante do que o banco tem gravado) NÃO
  são tocadas por este script INSERT-only — corrigir shift exige MOVER meses, o que é caso de
  rebuild, não de insert. Reportadas ao usuário para decisão (ver relatório final):
    * MT Nordeste 2025: foco mostra out=627.929, nov=470.356; banco tem out=470.356, nov=302.212.
      Ou seja o banco parece deslocado (out real = 627.929, ausente; 470.356 seria nov; 302.212
      seria dez). dez do foco ficou cortado, não confirmado.
    * MT Medio Norte 2025: foco mostra ago=828.793, set=1.100.153, out=927.416, nov=1.055.820;
      banco tem ago=1.100.153, set=927.416, out=1.055.820 (deslocado 1 mês para trás a partir de
      agosto; ago real=828.793 ausente). dez do foco ficou cortado.

IMPORTANTE: este script só faz INSERT ... WHERE NOT EXISTS (idempotente, nunca duplica, nunca
sobrescreve). Entra no rebuild_market_share.sh DEPOIS de add_market_share_milho4.py.
NÃO EXECUTADO — preparado para revisão do usuário antes de rodar.
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Vídeo do usuário (celular filmando dashboard Power BI de terceiro \"Competitividade\", "
         "09_Fotos/IMG_0235.MOV, Produto=MILHO, dimensão Microrregião) — MODO DE FOCO / tela cheia "
         "(painel de ano expandido, 12 meses rotulados por extenso, sem colisão), identidade por "
         "match de valor-âncora com a série já no banco, transcrição manual dos rótulos das barras, "
         "15/jul/2026.")

PRODUTO = "Milho"

# escopo -> {ano: {mes_1a12: volume_t}}. SÓ meses NOVOS (buracos) lidos com nitidez em tela cheia,
# em frame ALINHADO (vizinhos batendo com o banco). Meses cortados/ilegíveis ficam de fora.
VOLUME = {
    # MT Norte 2024 (f211, IMG_0235 t=211s; 2024 confirmado pelo eixo). fev..jul batem com o banco
    # (4.879 / 9.182 / 44.363 / 46.305 / 559.492 / 1.301.498); set=884.077 e out=515.787 também
    # batem -> frame ALINHADO. Buracos preenchidos: ago (entre jul e set) e nov (entre out e dez).
    "MT Norte": {
        2024: {8: 1174029, 11: 511402},
        # MT Norte 2025 (f205, t=205s). jan..ago batem (19.250 / 4.170 / 4.544 / 2.086 / 5.169 /
        # 465.636 / 1.426.487 / 1.622.316); out=759.440 bate -> alinhado. Buracos: set, nov.
        2025: {9: 1538252, 11: 646105},
    },
    # MT Sudeste 2025 (f143, t=143s). jan..ago batem (42.779 / 15.718 / 21.802 / 15.557 / 15.627 /
    # 30.079 / 218.194 / 297.371) -> alinhado. Buraco lido: set. out(alto) e nov ficaram cortados
    # no topo da tela, não lidos.
    "MT Sudeste": {
        2025: {9: 308258},
    },
    # MT Nordeste Sul 2025 (f135-136, t=135s). jan..jul batem (12.320 / 4.041 / 567 / 256 / 2.875 /
    # 39.484 / 260.595); set=352.725 e out=507.041 batem -> alinhado. Buraco lido: ago (entre jul e
    # set). nov ficou com rótulo acima da borda superior, não lido.
    "MT Nordeste Sul": {
        2025: {8: 242991},
    },
    # PR 2025 (f242, t=242s). fev=184.646, abr=33.595, mai=150.014, jun=241.861, jul=601.183,
    # ago=757.885 batem; nov=754.479 bate -> alinhado. Buraco lido: mar=101.161 (rótulo "101.161",
    # barra menor que maio 150.014, coerente). out(alto) ficou cortado no topo, não lido.
    "PR": {
        2025: {3: 101161},
    },
    # GO Sudoeste 2025 (f096-104, t=96-104s). fev..nov batem (34.434 / 29.601 / 21.866 / 23.412 /
    # 54.043 / 690.777 / [ago pico sem rótulo] / 543.745 / 546.242 / 529.912) -> alinhado, sem shift.
    # Buraco lido: dez=612.756.
    "GO Sudoeste": {
        2025: {12: 612756},
    },
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()

    vol_inserted = vol_skipped = 0
    for escopo, anos in VOLUME.items():
        for ano, meses in anos.items():
            for mes_num, v in meses.items():
                if v is None:
                    continue
                mes = MESES[mes_num - 1]
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
    print(f"market_share_volume (Milho, modo de foco): {vol_inserted} novas ({vol_skipped} já existiam)")
    con.close()


if __name__ == "__main__":
    main()
