# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine — premissas operacionais de manobra para clientes de
Grãos e Fertilizantes, extraídas manualmente da planilha "Premissas Grãos e Fertilizantes.xlsx"
(aba "Premissas Gerais"), fotografada pelo usuário em 3 imagens (IMG_0526/0527/0528, 21/jul/2026).

Pedido do usuário: "baixei 3 imagens 526 527 e 528 com premissas de tempo e peso medio e
quando terminal de clientes de graos e ferti operam. incorporar na base e usar como
referencia para simulacao de custo da manobra." — confirmado que só a aba "Premissas Gerais"
foi fotografada (horário de funcionamento + tempo de carga/descarga); a aba "Peso médio"
ainda não foi enviada (usuário: "Incorporar só o que tenho agora (horário+tempo), depois
envio peso médio").

IMPORTANTE — limitação de origem dos dados: os valores abaixo foram transcritos visualmente
de fotos de celular de uma planilha Excel (não é extração digital/OCR). As colunas
"Corredor/Mercadoria/Origem/Destino/Atividade/Horário de funcionamento" têm alta confiança
(texto grande, nítido, sem ambiguidade). As colunas numéricas subsequentes (Horário de
Manutenção, Dias na semana de funcionamento, Capacidade de Carga, Quantidade de vagões por
posição no pátio, Tempo de carga e descarga) são mais estreitas e, em alguns pontos de junção
entre fotos, existe risco de desalinhamento de linha — por isso ficam concatenadas em um único
campo texto "detalhes_operacionais" (não foram forçadas em colunas numéricas separadas, pra não
fabricar precisão que a foto não garante). Uso como REFERÊNCIA, não como fonte automática de
override na simulação de custo — validar com o usuário antes de qualquer cálculo crítico.

Idempotente: DELETE + INSERT completo a cada execução.

Uso:  python3 add_premissas_manobra_graos_ferti.py
"""
import pathlib
import sqlite3

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"
FONTE = "Foto planilha 'Premissas Grãos e Fertilizantes.xlsx' aba Premissas Gerais (IMG_0526-0528, 21/jul/2026)"

# (corredor, mercadoria, origem, destino, atividade,
#  horario_seg_sex, horario_sab, horario_dom, detalhes_operacionais, consideracoes)
LINHAS = [
    # ---------------- Corredor Norte ----------------
    ("Norte", "FARELO DE SOJA", "PAV", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00", ""),
    ("Norte", "FARELO DE SOJA", "PIN", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00", "Terminal VLI"),
    ("Norte", "FARELO DE SOJA", "PPF", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00", ""),
    ("Norte", "FARELO DE SOJA", "PPT", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00", ""),
    ("Norte", "FARELO DE SOJA", "Todos", "QIT", "Descarga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00", ""),
    ("Norte", "FARELO DE SOJA", "Todos", "QIT", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "FERTILIZANTES", "QPM", "PIP", "Limpeza",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00",
     "Quantidade de vagões no pátio, 2 manobras de 20"),
    ("Norte", "FERTILIZANTES", "QPM", "PIP", "Mix de tipos de Ferti",
     "24h/dia", "24h/dia", "24h/dia", "manutenção NA; dias NA; capacidade NA; qtd NA",
     "Será validado após fechamento do volume (mais de 10 produtos)"),
    ("Norte", "FERTILIZANTES - TIPO 1", "QPM", "PIP", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7; capacidade 30; qtd vagões 40", "Quantidade de vagões no pátio"),
    ("Norte", "FERTILIZANTES - TIPO 1", "QPM", "PIP", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7; capacidade 40; qtd vagões 40", "Quantidade de vagões no pátio"),
    ("Norte", "FERTILIZANTES - TIPO 2", "QPM", "PIP", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7; capacidade 30; qtd vagões 40", "Quantidade de vagões no pátio"),
    ("Norte", "FERTILIZANTES - TIPO 2", "QPM", "PIP", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7; capacidade 40; qtd vagões 40", "Quantidade de vagões no pátio"),
    ("Norte", "MILHO", "PAV", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", "Taxa de carregamento"),
    ("Norte", "MILHO", "PPF", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00", "Taxa de carregamento"),
    ("Norte", "MILHO", "PPN", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", "Taxa de carregamento"),
    ("Norte", "MILHO", "PPT", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", "Taxa de carregamento"),
    ("Norte", "MILHO", "Todos", "QIT", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 7,00",
     "Tempo de descarga e % premissa lote 40/40"),
    ("Norte", "SOJA", "PAV", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00", ""),
    ("Norte", "SOJA", "PPF", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SOJA", "PPN", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SOJA", "PPT", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SOJA", "Todos", "QIT", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SORGO", "PAV", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SORGO", "PIN", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SORGO", "PPF", "Todos - VLI/Cliente", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 5,80", "Terminal VLI"),
    ("Norte", "SORGO", "PPT", "Todos - VLI/Cliente", "Carga",
     "07h-23h", "07h-23h", "NÃO OPERA", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "SORGO", "Todos", "QIT", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 6,00; qtd vagões 80,00; tempo carga/descarga 12,00", ""),
    ("Norte", "TEGRAM", "Todos", "QIT", "Mix de Vagões 40/40",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7,00; qtd vagões 80,00; tempo carga/descarga 5,80", ""),

    # ---------------- Corredor Sudeste ----------------
    ("Sudeste", "ENXOFRE", "ICZ", "EYC", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 25,00", "1 dia de 12h/mês"),
    ("Sudeste", "ENXOFRE", "ICZ", "EYC", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 14,00", "1 dia de 12h/mês"),
    ("Sudeste", "ENXOFRE", "IUF", "EYC", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 51,00", "2 dias de 18h, a cada 15 dias"),
    ("Sudeste", "ENXOFRE", "IUF", "EYC", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 51,00", "17 por turno (3 turnos)"),
    ("Sudeste", "ENXOFRE", "IUF", "ZVF", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 36,00", "2 dias de 18h, a cada 15 dias"),
    ("Sudeste", "FARELO DE SOJA", "EBJ", "IUF", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "qtd vagões 5/dia; capacidade 25,00; tempo carga/descarga 81,00",
     "Considerando só tempo de carregamento, e lote de 84vgs (17 por turno, 3 turnos)"),
    ("Sudeste", "FARELO DE SOJA", "EBJ", "IUF", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "capacidade 51,00", "Descarga TIPLAM terminal VLI"),
    ("Sudeste", "FARELO DE SOJA", "EGA", "ISN", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "qtd vagões 0/dia; capacidade 30,00; tempo carga/descarga 68h",
     "Considerando apenas tempo de carregamento. Não considera manobra/posicionamento do lote/inversão/formação de faixa. Premissa de 30 vagões/dia"),
    ("Sudeste", "FARELO DE SOJA", "EGA", "ISN", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "capacidade 30,00; tempo carga/descarga 12,5 vgs/hora", "Descarga TES"),
    ("Sudeste", "FARELO DE SOJA", "ETB", "ISN", "Carga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "FARELO DE SOJA", "ETB", "ISN", "Descarga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "FARELO DE SOJA", "ZZB", "ISN", "Carga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "FARELO DE SOJA", "ZZB", "ISN", "Descarga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "FARELO DE SOJA - SPC", "EBJ", "IUF", "Carga",
     "-", "-", "-", "tempo carga/descarga 81,00", "Considerando só tempo de carregamento, e lote de 84vgs"),
    ("Sudeste", "FARELO DE SOJA - HIPRO", "EPO", "ISN", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "capacidade 30,00",
     "Considerando apenas tempo de carregamento + limpeza. Não considera manobra/posicionamento do lote/inversão/formação de faixa"),
    ("Sudeste", "FARELO DE SOJA - HIPRO", "EPO", "ISN", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "tempo carga/descarga 13,2 vgs/hora", "Descarga T39"),
    ("Sudeste", "FERTILIZANTES", "IUF", "ZVF", "Carga",
     "-", "-", "-", "", "Carregamento feito no Tiplam, premissa planejamento VLI"),
    ("Sudeste", "FERTILIZANTES", "IUF", "ZVF", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 36,00", ""),
    ("Sudeste", "FOSFATO", "ELC", "ZVF", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 23,00", "2 dias de 10h, a cada 15 dias — premissa conforme contrato"),
    ("Sudeste", "FOSFATO", "ELC", "ZVF", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 46,00", "2 dias de 20h, a cada 15 dias — 15 por turno (total de 3 turnos)"),
    ("Sudeste", "FOSFATO", "EYC", "IFA", "Carga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 30,00", ""),
    ("Sudeste", "FOSFATO", "EYC", "IFA", "Descarga",
     "24h/dia", "24h/dia", "24h/dia", "dias/sem 7 dias; capacidade 25,00", ""),
    ("Sudeste", "Grãos Santos", "EBJ", "ICZ", "Carga",
     "07h30-16h", "07h30-16h", "NÃO OPERA", "qtd vagões 0/dia; capacidade 20,00; tempo carga/descarga 102,00",
     "Considerando apenas tempo de carregamento. Não considera manobra/posicionamento do lote/inversão/formação de faixa"),
    ("Sudeste", "Grãos Santos", "EBJ", "ICZ", "Descarga",
     "-", "-", "-", "tempo carga/descarga 10 vgs/hora", "Descarga TEG/TEAG"),
    ("Sudeste", "Grãos Santos", "EBJ", "ISN", "Carga",
     "07h30-16h", "07h30-16h", "NÃO OPERA", "qtd vagões 0/dia; capacidade 20,00; tempo carga/descarga 102,00",
     "Considerando apenas tempo de carregamento. Não considera manobra/posicionamento do lote/inversão/formação de faixa"),
    ("Sudeste", "Grãos Santos", "EBJ", "ISN", "Descarga",
     "-", "-", "-", "tempo carga/descarga 11,8 vgs/hora", "Descarga ISN ADM"),
    ("Sudeste", "Grãos Santos", "EBJ", "IUF", "Carga",
     "07h30-16h", "07h30-16h", "NÃO OPERA", "qtd vagões 0/dia; capacidade 20,00; tempo carga/descarga 102,00",
     "Considerando apenas tempo de carregamento. Não considera manobra/posicionamento do lote/inversão/formação de faixa"),
    ("Sudeste", "Grãos Santos", "EBJ", "IUF", "Descarga", "-", "-", "-", "", "Descarga TIPLAM terminal VLI"),
    ("Sudeste", "Grãos Santos", "ZZB", "ICZ", "Carga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "Grãos Santos", "ZZB", "ICZ", "Descarga",
     "24h/dia", "-", "-", "tempo carga/descarga 10 vgs/hora", "Descarga TEG/TEAG"),
    ("Sudeste", "Grãos Santos", "ZZB", "ISN", "Carga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "Grãos Santos", "ZZB", "ISN", "Descarga",
     "24h/dia", "-", "-", "tempo carga/descarga 11,8 vgs/hora", "Descarga ADM ISN"),
    ("Sudeste", "Grãos Santos", "ZZB", "IUF", "Carga", "24h/dia", "-", "-", "", ""),
    ("Sudeste", "Grãos Santos", "ZZB", "IUF", "Descarga",
     "24h/dia", "-", "-", "", "Descarga TIPLAM terminal VLI"),
    ("Sudeste", "MINÉRIO DE FOSFATO", "ETP", "ETF", "Carga",
     "NA", "NA", "NA", "", "Cliente Mosaic desmobilizou essa operação"),
    ("Sudeste", "MINÉRIO DE FOSFATO", "ETP", "ETF", "Descarga",
     "NA", "NA", "NA", "", "Cliente Mosaic desmobilizou essa operação"),
    ("Sudeste", "UREIA", "IUF", "ZVF", "Descarga",
     "24h/dia", "24h/dia", "-", "dias/sem 7 dias; capacidade 36,00", ""),

    # ---------------- Corredor Leste ----------------
    ("Leste", "FARELO DE MILHO - DDG", "ETB", "VTU", "Carga", "-", "-", "-", "", ""),
    ("Leste", "FARELO DE SOJA", "EGA", "VTU", "Carga",
     "-", "-", "-", "tempo carga/descarga 48h",
     "Considerando apenas tempo de carregamento. Não considera manobra/posicionamento do lote/inversão/formação de faixa. Premissa de 30 vagões/dia"),
    ("Leste", "FARELO DE SOJA", "EPP", "VTU", "Carga", "24h/dia", "24h/dia", "-", "", ""),
    ("Leste", "FARELO DE SOJA", "EPP", "VTU", "Descarga", "24h/dia", "24h/dia", "-", "", ""),
    ("Leste", "FARELO DE SOJA", "ETB", "VTU", "Carga", "24h/dia", "24h/dia", "-", "", ""),
    ("Leste", "FARELO DE SOJA", "ETB", "VTU", "Descarga", "24h/dia", "24h/dia", "-", "", ""),
    ("Leste", "FERTILIZANTES", "VTU", "EDH", "Descarga",
     "Não negociado", "Não negociado", "Não negociado", "qtd vagões 44", ""),
    ("Leste", "Grãos VTU", "ECA", "VTU", "Carga",
     "07h30-16h", "07h30-16h", "-", "qtd vagões 5/dia; capacidade 45,00; tempo carga/descarga 48h",
     "Considerando o tempo de carregamento (h). Considerando carregamento de 45 vagões"),
    ("Leste", "FERTILIZANTES", "VTU", "ETB", "Descarga",
     "24h/dia", "24h/dia", "-", "dias/sem 7 dias; qtd vagões NA",
     "8h, uma vez por semana — Cliente FTO, com sistema integrado à descarga do TIA"),
]


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("DROP TABLE IF EXISTS premissas_manobra_graos_ferti")
    cur.execute(
        """CREATE TABLE premissas_manobra_graos_ferti (
            corredor TEXT, mercadoria TEXT, origem TEXT, destino TEXT, atividade TEXT,
            horario_seg_sex TEXT, horario_sab TEXT, horario_dom TEXT,
            detalhes_operacionais TEXT, consideracoes TEXT, fonte TEXT
        )"""
    )
    cur.executemany(
        """INSERT INTO premissas_manobra_graos_ferti
           (corredor, mercadoria, origem, destino, atividade,
            horario_seg_sex, horario_sab, horario_dom, detalhes_operacionais, consideracoes, fonte)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [linha + (FONTE,) for linha in LINHAS],
    )
    con.commit()
    print(f"  premissas_manobra_graos_ferti: {len(LINHAS)} linhas inseridas "
          f"(aba 'Premissas Gerais' — horário de funcionamento; falta aba 'Peso médio').")
    con.close()


if __name__ == "__main__":
    main()
