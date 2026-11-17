#!/bin/bash
# Reconstrói as 2 tabelas de Custo Logístico na ordem certa (pente-fino lote 4, nov/2026).
# add_custo_logistico.py faz DROP TABLE e recria só a 1ª leva; as outras 418 de 563 linhas da
# evolução vêm dos 7 backfills abaixo, que só INSEREM. Rodar só o primeiro apaga 74% da aba.
# Ordem validada em cópia do banco: resultado idêntico linha a linha (79 + 563).
set -e
cd "$(dirname "$0")"
python3 add_custo_logistico.py
python3 add_custo_logistico_evolucao_2021.py
python3 add_custo_logistico_evolucao_2021b.py
python3 add_custo_logistico_evolucao_2021c.py
python3 add_custo_logistico_evolucao_milho.py
python3 add_custo_logistico_evolucao_milho_full.py
python3 add_custo_logistico_evolucao_v3.py
python3 add_custo_logistico_tco_novos.py
echo "OK — Custo Logístico reconstruído (microrregião + evolução com backfills)"
