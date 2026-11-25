# -*- coding: utf-8 -*-
"""
LogConsult Intelligence Engine: referências públicas de preço portuário (aba Porto do Painel do Cliente).
CONFIDENCIAL, USO RESTRITO AOS SÓCIOS

Pesquisa de 25/nov/2026 (pedido do sócio: comparar o que a Mosaic paga no TIPLAM em fertilizantes,
enxofre e amônia com os demais terminais de Santos). Cada linha foi conferida no documento original
(cópias em scratchpad da sessão, não versionadas). Tipos:
  publicado = tabela de preços do terminal (exigência ANTAQ)
  estudo    = premissa de estudo de leilão (EVTEA)
  noticia   = número divulgado em notícia, com conta nossa
comparavel = 1 só quando o serviço é o mesmo pacote de importação no mesmo porto.

Achados que orientam a leitura:
  - Nenhum outro terminal de fertilizantes, enxofre ou amônia em Santos publica tabela (TERMAG,
    Hidrovias STS20, Fertimport, Rumo, DPW): a referência pública em Santos é a lista do próprio TIPLAM.
  - A versão 2025 da tabela do TIPLAM não está linkada na página de regulação da VLI (que mostra a de
    2023); está no servidor da VLI no endereço abaixo.
  - Não conferidos e por isso fora: tarifa da APS vigente (só a de 2022 foi lida) e o acórdão do TCU
    sobre o 1º bloco de arrendamentos de Santos (faixa de R$ 35 a 88/t citada em busca).

Uso:  python3 add_porto_referencias.py
"""
import pathlib
import sqlite3

DB = pathlib.Path(__file__).resolve().parent / "logconsult.db"
T25 = "https://www.vli-logistica.com.br/wp-content/uploads/2025/08/Tarifas-TIPLAM-2025.pdf"
T23 = "https://www.vli-logistica.com.br/wp-content/uploads/2023/03/Tarifas-TIPLAM-2023.pdf"
TMIB = "https://www.vli-logistica.com.br/wp-content/uploads/2025/01/Tarifas-TMIB-2025.pdf"
FOSPAR = "https://mosaicco.com.br/ckfinder/userfiles/files/Fospar/Tarifas-Fospar.pdf"
TESC = "https://www.terminalsc.com.br/uploads/download_arquivo/00031-.pdf"
STS08 = "https://www.portodesantos.com.br/wp-content/uploads/STS08-Secao-B-Estudos-de-Mercado.pdf"
STS20 = "https://www.sopesp.com.br/operacoes/em-leilao-hidrovias-do-brasil-leva-terminal-de-fertilizantes-em-santos/"

# porto, terminal, produto, servico, valor_rs_t, data_ref, tipo, inclui_tributos (1/0/None), comparavel, fonte, url, obs
REFS = [
    ("Santos", "TIPLAM, tabela de lista 2025", "FERTILIZANTES", "Desembarque, demais fertilizantes, com 15 dias livres de armazenagem",
     145.78, "2025-08", "publicado", None, 1, "VLI, Contrato de Adesão ANTAQ 39/2014", T25,
     "Ureia R$ 186,94/t. Excedente por período de 5 dias: R$ 26,69 a 42,70/t. O título da tabela diz 7 dias livres e a linha diz 15."),
    ("Santos", "TIPLAM, tabela de lista 2025", "ROCHA FOSFATICA", "Desembarque, rocha fosfática, com 15 dias livres",
     167.43, "2025-08", "publicado", None, 1, "VLI, Contrato de Adesão ANTAQ 39/2014", T25, "Excedente: R$ 21,35 a 37,36/t por período de 5 dias."),
    ("Santos", "TIPLAM, tabela de lista 2025", "ENXOFRE", "Desembarque, enxofre, com 7 dias livres",
     147.92, "2025-08", "publicado", None, 1, "VLI, Contrato de Adesão ANTAQ 39/2014", T25, "Excedente: R$ 16,01 a 32,02/t por período de 5 dias."),
    ("Santos", "TIPLAM, tabela de lista 2025", "AMONIA", "Desembarque, amônia (sem armazenagem tarifada)",
     97.53, "2025-08", "publicado", None, 1, "VLI, Contrato de Adesão ANTAQ 39/2014", T25, ""),
    ("Santos", "TIPLAM, tabela de lista 2023", "FERTILIZANTES", "Desembarque, demais fertilizantes, 7 dias livres",
     138.57, "2023-01", "publicado", None, 0, "VLI (versão ainda linkada na página de regulação)", T23, "De 2023 para 2025: +5,2%."),
    ("Santos", "TIPLAM, tabela de lista 2023", "ENXOFRE", "Desembarque, enxofre, 7 dias livres",
     138.57, "2023-01", "publicado", None, 0, "VLI (versão ainda linkada na página de regulação)", T23, "De 2023 para 2025: +6,7%."),
    ("Santos", "TIPLAM, tabela de lista 2023", "AMONIA", "Desembarque, amônia",
     91.37, "2023-01", "publicado", None, 0, "VLI (versão ainda linkada na página de regulação)", T23, "De 2023 para 2025: +6,7%."),
    ("Santos", "STS20 (Hidrovias), leilão 2019", "FERTILIZANTES", "Receita média do arrendamento de fertilizantes e sal (todo o pacote)",
     50.26, "2019", "noticia", None, 0, "Leilão ANTAQ 2019: R$ 2,744 bi de receita sobre 54,6 Mt em 25 anos (conta nossa)", STS20,
     "Corrigida pelo IPCA até 2025 fica em torno de R$ 70/t. EVTEA original fora do ar no servidor da ANTAQ."),
    ("Santos", "STS08, estudo de leilão dez/2023 (terminais químicos da Alamoa)", "AMONIA",
     "Granel líquido: recepção, expedição e 15 dias de armazenagem, por giro mensal (tanque ambiente, não amônia refrigerada)",
     102.99, "2023-10", "estudo", None, 0, "APS, Seção B Estudos de Mercado do STS08", STS08,
     "Base: receita por tonelada e mês de Stolthaven, Adonai e Ageo (R$ 82 a 141). Serviço diferente da amônia refrigerada."),
    ("Sergipe", "TMIB (VLI), tabela 2025", "FERTILIZANTES", "Descarga de fertilizantes, com mão de obra portuária",
     115.84, "2025-02", "publicado", 0, 0, "VLI", TMIB, "ISS somado na fatura. Armazém R$ 0,79/t/dia; pesagem na expedição R$ 3,04/t."),
    ("Paranaguá", "Fospar (Mosaic), preços praticados", "FERTILIZANTES",
     "Descarga R$ 23 + carregamento rodoviário R$ 22 (ferroviário R$ 7), 4 dias livres",
     45.00, "2021-03", "publicado", None, 0, "Fospar", FOSPAR, "Preço máximo publicado: descarga R$ 45 + carregamento R$ 30. Tabela de 2021."),
    ("São Francisco do Sul", "TESC (WRC), tabela 2026", "FERTILIZANTES",
     "Granel sólido: operação portuária R$ 132,48 + recebimento e expedição R$ 103,04 (sem acordo comercial)",
     235.52, "2026-02", "publicado", 1, 0, "WRC Operadores Portuários", TESC, "Carga tributária aproximada de 12,25% incluída. Carga IMO: +47,46%."),
]


def main():
    con = sqlite3.connect(DB)
    con.execute("DROP TABLE IF EXISTS precos_portos_referencia")
    con.execute("""CREATE TABLE precos_portos_referencia (porto TEXT, terminal TEXT, produto TEXT, servico TEXT,
                   valor_rs_t REAL, data_ref TEXT, tipo TEXT, inclui_tributos INTEGER, comparavel INTEGER,
                   fonte TEXT, url TEXT, obs TEXT)""")
    con.executemany("INSERT INTO precos_portos_referencia VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", REFS)
    con.commit()
    con.close()
    print(f"  precos_portos_referencia: {len(REFS)} referências ({sum(1 for r in REFS if r[0] == 'Santos')} em Santos).")


if __name__ == "__main__":
    main()
