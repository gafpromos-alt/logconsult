#!/bin/bash
# Roda toda a cadeia de ingestão de Market Share na ordem certa. add_market_share.py faz
# DROP+CREATE de market_share_volume/player (só Soja) — rodar sozinho apaga Milho/Farelo/Porto
# que os outros scripts inseriram por cima. Sempre usar este wrapper, nunca rodar
# add_market_share.py isolado quando já existe dado de Milho/Farelo/Porto no banco.
set -e
cd "$(dirname "$0")"
python3 add_market_share.py
python3 add_market_share_soja_focus.py
python3 add_market_share_milho.py
python3 add_market_share_milho2.py
python3 add_market_share_milho3.py
python3 add_market_share_milho4.py
python3 add_market_share_milho_focus.py
python3 add_market_share_farelo_soja.py
python3 add_market_share_farelo_focus.py
python3 add_market_share_farelo_milho.py
python3 add_market_share_porto.py
python3 add_market_share_porto_milho.py
python3 add_market_share_porto_milho2.py
python3 fix_market_share_shifts.py
echo "OK — Soja+Milho+Farelo+Porto reconstruidos (+ correcao de shift)"
