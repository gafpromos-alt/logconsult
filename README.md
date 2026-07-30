# Banco Analítico — Fase 1

**ESTRITAMENTE CONFIDENCIAL — USO RESTRITO AOS SÓCIOS**
Contém o P&L interno da VLI e dados pessoais de CRM. Não sincronizar fora do OneDrive dos sócios, não versionar em repositório público.

O "banco de dados" da Fase 1: um SQLite único e consultável que consolida as bases
ricas da pasta `07_Dados VLI` + a base tarifária anterior. Migra para PostgreSQL
na Fase 2 sem retrabalho (mesmos nomes em snake_case).

## Arquivos
| Arquivo | Papel |
|---|---|
| `build_db.py` | Ingere os `.xlsx` → `logconsult.db`. Rode para reconstruir. |
| `analises.py` | Roda as análises de maior alavanca e gera `Achados_VLI.md`. |
| `build_painel.py` + `painel_template.html` | Gera o **painel multi-módulo** (HTML). |
| `Painel_LogconsultOS.html` | **Dashboard final** — 6 módulos, abre no navegador. |
| `logconsult.db` | O banco (SQLite). |
| `Achados_VLI.md` | Relatório de achados (conclusões). |

## Painel (Painel_LogconsultOS.html) — TOOL ÚNICO, 9 abas
`python3 build_painel.py` consulta o banco (+ `../03_Radar_Oportunidades/radar_data.json`) e regenera o dashboard. Abas:
**Horizontes** e **Pipeline** (do Radar) · **VLI/Margem** · **Acessórias** · **Teto Tarifário** ·
**Comparativo** (segmento × cliente, dispersão na mesma rota) · **Mercado** (preço CEPEA + frete/valor da carga) ·
**Contratos** (expiração por ano) · **Contatos** (CRM). Alvos LogConsult destacados. Reskin: ver `SKIN.md`.

> Ordem de build: `build_radar.py` (gera radar_data.json) → `add_mercado.py` (preços) → `build_painel.py`.

## Dados de mercado (add_mercado.py)
Insere `precos_commodity` (soja, milho, açúcar via CEPEA/ESALQ; farelo via IMEA — coletados 2026-07-06).
Atualize a lista `PRECOS` no script com novas cotações. Achado: **frete = 20% do valor da carga no farelo**
e **17% no milho** (vs. 8% soja, 7% açúcar) → materialidade forte para Selecta/Caramuru (farelo) e milho.
Pendentes (precisam de referência melhor): combustíveis (usar ex-refinaria, não revenda ANP), fertilizantes, siderúrgicos.

> **Nota técnica:** SQLite não convive bem com escrita direta em pasta sincronizada (OneDrive). O `build_db.py` constrói em disco local e copia o arquivo pronto — não edite o `.db` com o OneDrive sincronizando ativamente.

## Como usar
```
python3 build_db.py     # (re)constrói o banco a partir dos xlsx
python3 analises.py     # regenera Achados_VLI.md
```
Consultas ad-hoc: `sqlite3 logconsult.db` ou pandas `read_sql_query`.

## Tabelas
| Tabela | Linhas | Conteúdo |
|---|---:|---|
| `vli_pnl` | 44.775 | **P&L VLI** por fluxo×mês×panorama: receita (REC-*), custo (CST-*, majoritariamente vazio), imposto (IMP-*), margem (`ind_mrg`), volume (VOL-*). 3 panoramas: 2024 Real, 2025 Tendência, 2026 Orçamento. |
| `fluxos_servico` | 5.401 | Tarifa por fluxo × serviço (abertura de acessórias: frete, manobras, transbordo, DP…). |
| `ipoa_teto` | 1.916 | Fluxo × %IPOA × acessórias × frete × teto × %teto × corredor VLI × km. |
| `ipoa_geral` | 9.536 | Serviço × categoria (frete/acessórias) com tarifa e valor. |
| `tarifas_praticadas` | 1.609 | Base tarifária anterior (Módulo A). |
| `crm_contatos` | 3.420 | Contatos/contas CRM — **dado pessoal**, uso interno. |

**Views:** `v_margem_cliente`, `v_margem_corredor` (margem consolidada 2024).

## Tese analítica
A margem que a VLI faz em cada lane (`ind_mrg`) é o mapa de onde o cliente tem
espaço para negociar. **Margem alta = VLI lucra muito ali = alavanca comercial.**
Cruzada com a participação de acessórias (menos regulada) e com o %teto, dá a
prioridade de ataque. Ver `Achados_VLI.md`.

## Aberto / a validar
- Confirmar a definição de `ind_mrg` entre panoramas (2026 marca 89% de margem — pode ser sub-alocação de custo no orçamento).
- Conectar este banco ao dashboard Radar (`../03_Radar_Oportunidades/`) como nova visão "VLI / Margem".
