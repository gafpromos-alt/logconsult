# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — Market Share (Competitividade): CORRECAO DE SHIFT DE MES
CONFIDENCIAL — USO RESTRITO AOS SOCIOS

A transcricao ORIGINAL da visao compacta de 3 paineis (add_market_share.py) tem, em algumas
series, um DESLOCAMENTO de 1 mes: por colisao de rotulo na tela pequena, o valor de um mes foi
gravado no mes seguinte. Os videos IMG_0229 (Soja) e IMG_0235 (Milho) em MODO DE FOCO / TELA CHEIA
mostram cada barra com o mes rotulado por extenso (janeiro..dezembro), SEM colisao — fonte
DEFINITIVA. Cada uma das 5 series abaixo foi reverificada FRAME A FRAME contra esse eixo (conversa
principal, 15/jul/2026) e a divergencia confirmada; jan/fev (e demais meses fora da janela do shift)
batem exatamente com o banco, o que ancora a identidade regiao/ano.

Correcao = DELETE das linhas daquela (escopo, produto, ano) + INSERT da serie corrigida (so meses
com valor conhecido; mes com rotulo cortado/ilegivel no video fica de fora, nunca chutado).
Idempotente: reescreve sempre a mesma serie corrigida. Deve rodar DEPOIS de add_market_share.py
(que popula os originais deslocados) e dos scripts *_focus (que nao tocam nestas 5 regioes).
Registrado no fim de rebuild_market_share.sh.

Detalhe das 5 series (BANCO deslocado -> EIXO/video definitivo):
  * Soja "MT Norte" 2024: shift +1 a partir de MARCO (banco tinha marco vazio; abr..dez = mar..nov
    reais). dez real ficou SEM rotulo no video -> omitido.
  * Soja "Nacional" 2025: shift +1 a partir de ABRIL. dez real (~3.003.9xx) borrado -> omitido.
  * Soja "GO Leste" 2024: shift so em JUN..SET (banco jun=327.673=jul real, jul=107.150=ago real;
    faltavam jun=420.255 e set=77.932). out/nov/dez ja estavam certos.
  * Milho "MT Medio Norte" 2025: shift +1 a partir de AGOSTO. Alem disso 2 erros de OCR de 1 digito
    corrigidos pelo video: mar 4.826->4.626, abr 8.922->6.922. dez cortado no video -> omitido.
  * Milho "MT Nordeste" 2025: shift +1 a partir de OUTUBRO (banco out=470.356=nov real,
    nov=302.212=dez real; faltava out=627.929).
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
MESES = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]

FONTE = ("Correcao de shift de mes — reverificada frame a frame no MODO DE FOCO / tela cheia "
         "(IMG_0229 Soja / IMG_0235 Milho), eixo com meses rotulados por extenso; substitui a "
         "transcricao deslocada da visao compacta (add_market_share.py). 15/jul/2026.")

# (produto, escopo, ano) -> [12 valores; None = mes sem valor confiavel no video, nao gravado]
CORRECOES = {
    ("Soja", "MT Norte", 2024): [384104, 1140304, 1074228, 816882, 363891, 54170,
                                 23573, 10142, 29958, 8722, 15111, None],
    ("Soja", "Nacional", 2025): [3323040, 11960994, 14301553, 12945760, 12467007, 9749852,
                                 7365636, 6869912, 6680881, 6118695, 3803328, None],
    ("Soja", "GO Leste", 2024): [41795, 184669, 447073, 621492, 384771, 420255,
                                 327673, 107150, 77932, 18607, 24804, 27073],
    ("Milho", "MT Medio Norte", 2025): [40377, 7044, 4626, 6922, 51138, 362377,
                                        804914, 828793, 1100153, 927416, 1055820, None],
    ("Milho", "MT Nordeste", 2025): [737, 513, 515, 334, 142, 36806,
                                     235602, 486019, 570442, 627929, 470356, 302212],
}


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    total = 0
    for (produto, escopo, ano), serie in CORRECOES.items():
        cur.execute("DELETE FROM market_share_volume WHERE produto=? AND escopo=? AND ano=?",
                    (produto, escopo, ano))
        n = 0
        for i, v in enumerate(serie):
            if v is None:
                continue
            cur.execute(
                "INSERT INTO market_share_volume (escopo, produto, ano, mes, volume_t, fonte) "
                "VALUES (?,?,?,?,?,?)",
                (escopo, produto, ano, MESES[i], float(v), FONTE))
            n += 1
        total += n
        print(f"  corrigido {produto} {escopo} {ano}: {n} meses reescritos (shift/foco)")
    con.commit()
    print(f"fix_market_share_shifts: {total} celulas reescritas em {len(CORRECOES)} series")
    con.close()


if __name__ == "__main__":
    main()
