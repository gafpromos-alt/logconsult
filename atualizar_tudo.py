# -*- coding: utf-8 -*-
"""
LogConsult OS — atualização de ponta a ponta, num comando só.
CONFIDENCIAL — USO RESTRITO AOS SÓCIOS

Pente-fino lote 4 (nov/2026). Antes não existia reconstrução completa: o banco tinha 53
tabelas e cada uma nascia de um script rodado à mão, em ordem que só existia na memória de
quem rodou. Este script é essa ordem, escrita.

    python3 atualizar_tudo.py              # tudo: extratos VLI/tarifas → painel → testes
    python3 atualizar_tudo.py --sem-base   # pula os extratos (só reprocessa o que já está no banco)
    python3 atualizar_tudo.py --so-painel  # só recompila o painel e roda os testes

Quando chegar extrato novo (P&L 24_25_26.xlsx, BaseHistoricaFerrovia, IPOA, Fluxos por serviço,
CRM...), basta substituir o arquivo em 07_Dados VLI/ (mesmo nome — ou ajustar o caminho no topo
de build_db.py) e rodar sem argumentos.

Sempre faz backup do banco antes e para no primeiro erro.
"""
import datetime
import pathlib
import shutil
import subprocess
import sys
import time

BASE = pathlib.Path(__file__).resolve().parent
DB = BASE / "logconsult.db"

# Tabelas-fonte dos preços minerados (F-LINK): autocontidas (dados no próprio script). Rodam
# ANTES dos complementos de ipoa_teto/fluxos_servico, que as leem.
MINERADOS = [
    "add_gerdau_precos_contratuais.py", "add_ipiranga_precos_contratuais.py",
    "add_cmoc_precos_contratuais.py", "add_alz_precos_contratuais.py",
    "add_agrex_precos_contratuais.py", "add_novaagri_precos_contratuais.py",
    "add_mosaic_precos_contratuais.py", "add_usiminas_precos_contratuais.py",
    "add_arcelormittal_precos_contratuais.py", "add_aperam_precos_contratuais.py",
    "add_vibra_precos_contratuais.py", "add_raizen_precos_contratuais.py",
    "add_alesat_precos_contratuais.py", "add_cenibra_precos_contratuais.py",
    "add_suzano_precos_contratuais.py", "add_ldcelulose_precos_contratuais.py",
    "add_petrobahia_precos_contratuais.py", "add_petronac_precos_contratuais.py",
    "add_sabba_precos_contratuais.py", "add_selecta_farelo_precos_contratuais.py",
    "add_selecta_etbvtu_novos_itens.py", "add_acucar_novos_clientes_precos_contratuais.py",
]

ETAPAS_BASE = [
    ("Extratos brutos (P&L VLI, volume, IPOA, serviços, tarifas, CRM)", ["build_db.py"]),
]
ETAPAS_PROCESSO = [
    ("Preços contratuais minerados (F-LINK)", MINERADOS),
    ("Complementos de ipoa_teto e fluxos_servico (clientes F-LINK)",
     ["add_ipoa_teto_novos_clientes.py", "add_fluxos_servico_novos_clientes.py"]),
    ("Ficha de Fluxo Geral 2026 (teto, frete, DP e serviços por item, mês a mês)", ["add_ficha_fluxo.py"]),
    ("Premissas, tetos, mercado e portos",
     ["add_premissas_planejamento.py", "add_tetos.py", "add_acessorias_mercado.py",
      "add_mercado.py", "add_precos_portos.py", "add_porto_referencias.py", "add_premissas_manobra_graos_ferti.py"]),
    ("Market share", ["rebuild_market_share.sh"]),
    ("Custo logístico", ["rebuild_custo_logistico.sh"]),
    ("Projetos por cliente (Painel do Cliente)", ["add_projetos_clientes.py"]),
    ("Alavancas regulatórias (Ficha 2026, P&L, orçamento)", ["add_alavancas.py"]),
]
ETAPAS_PAINEL = [
    ("Painel", ["build_painel.py"]),
    ("Testes de consistência", ["testes_painel.py"]),
]


def rodar(script):
    cmd = ["bash", script] if script.endswith(".sh") else [sys.executable, script]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    dt = time.time() - t0
    ultima = (r.stdout.strip().splitlines() or [""])[-1][:110]
    print(f"    {'ok ' if r.returncode == 0 else 'ERRO'} {script:52s} {dt:5.1f}s  {ultima}")
    if r.returncode != 0:
        print(r.stdout[-3000:])
        print(r.stderr[-3000:])
        sys.exit(f"\nParou em {script}. Banco anterior salvo no backup acima.")


def main():
    args = set(sys.argv[1:])
    if "--so-painel" in args:
        etapas = ETAPAS_PAINEL
    elif "--sem-base" in args:
        etapas = ETAPAS_PROCESSO + ETAPAS_PAINEL
    else:
        etapas = ETAPAS_BASE + ETAPAS_PROCESSO + ETAPAS_PAINEL

    if DB.exists() and "--so-painel" not in args:
        bak = DB.with_name(f"logconsult.db.bak_pre_atualizar_tudo_"
                           f"{datetime.datetime.now():%Y%m%d_%H%M%S}")
        shutil.copy2(DB, bak)
        print(f"Backup: {bak.name}")
        # rotação: ficam os 3 backups mais novos desta rotina na pasta; os mais velhos vão para
        # ~/LogConsult_arquivo/backups_db (fora do OneDrive — 50 MB cada, não precisam sincronizar)
        arq = pathlib.Path.home() / "LogConsult_arquivo" / "backups_db"
        velhos = sorted(BASE.glob("logconsult.db.bak_pre_atualizar_tudo_*"))[:-3]
        if velhos:
            arq.mkdir(parents=True, exist_ok=True)
            for v in velhos:
                shutil.move(str(v), str(arq / v.name))
            print(f"  {len(velhos)} backup(s) antigo(s) movido(s) para {arq}")
    for nome, scripts in etapas:
        print(f"\n▸ {nome}")
        for s in scripts:
            rodar(s)
    print("\nPronto. Painel: Painel_LogconsultOS.html")


if __name__ == "__main__":
    main()
