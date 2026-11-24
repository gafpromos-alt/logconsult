# LogConsult OS — regras para trabalhar neste repositório

**Confidencial.** Este repo contém só o CÓDIGO (scripts Python + template HTML). O
banco (`logconsult.db`) e o painel compilado (`Painel_LogconsultOS.html`, que carrega
todo o payload de dados de clientes embutido no JSON) NÃO estão versionados — ficam
fora via `.gitignore`. Nunca remova essas entradas do `.gitignore` nem tente commitar
esses arquivos.

## Arquitetura
- **Comando único: `python3 atualizar_tudo.py`** (nov/2026). Faz backup do banco, roda os
  extratos (`build_db.py`), as tabelas mineradas, complementos, tetos, market share, custo
  logístico, projetos por cliente, `build_painel.py` e `testes_painel.py`, nessa ordem, e para
  no primeiro erro. `--sem-base` pula os extratos; `--so-painel` só recompila e testa.
  Reconstrução do zero validada em cópia: 51/52 tabelas idênticas ao banco de 30/jul.
- `painel_template.html` → processado por `build_painel.py` (lê `logconsult.db`) → gera `Painel_LogconsultOS.html`.
- Sempre editar `painel_template.html`, nunca o `Painel_LogconsultOS.html` compilado diretamente.
- `build_db.py` cria só 9 tabelas-base; com banco existente ele **substitui só essas 9** (antes
  apagava o arquivo inteiro). `--substituir-banco` recria do zero.
- `add_projetos_clientes.py` monta o Painel do Cliente (`projeto_fluxo_tarifas`/
  `projeto_acessorias_abertas`); termina com `connect_precos_minerados.py` (Vibra, Raízen, ALE,
  Cenibra, Suzano, Petrobahia, Petronac, Sabba) e `fix_consistencia_final.py` (IPOA, vigência
  ISO, duplicatas de rota, unidade). Script novo que escreve nessas tabelas entra ANTES do
  `fix_consistencia_final`. Antes de assumir que um script roda, confira com
  `grep -n "<nome_do_script>" add_projetos_clientes.py atualizar_tudo.py`.
- **Testes:** `testes_painel.py` (banco) + `tests/harness_painel.js` (executa o script real do
  painel em Node contra o payload real: KPI × tabela, soma das linhas × total, rota inativa sem
  ganho, ids repetidos no HTML, relatório do cliente sem nome de terceiros). Rodar depois de
  qualquer mudança; os números das telas só valem com 0 falhas.
- `connect_{vibra,raizen,alesat,cenibra,suzano,petrobahia,petronac,sabba}_precos.py` estão
  obsoletos (apagam o cliente inteiro) — não usar; o conector único os substitui.
- **Ficha de Fluxo Geral 2026** (`07_Dados VLI/Base_Consolidada_Ficha_de_Fluxo_Geral.xlsx`, nov/2026):
  `add_ficha_fluxo.py` grava `ficha_fluxo_servico_mes`/`ficha_fluxo_item_mes`/`ficha_fluxo_ref`,
  troca em `fluxos_servico` (pares) os itens da ficha pelo mês de referência e atualiza
  `ipoa_teto` (colunas `dp`, `fonte_2026`). `connect_ficha_fluxo.py` (dentro de
  add_projetos_clientes) leva a ficha ao Painel do Cliente: pelo item citado na cobertura, senão
  pela rota (maior tarifa), e cria fluxos para rotas/clientes sem painel. Ficha nova: substituir
  o arquivo e rodar `atualizar_tudo.py --sem-base`.
- **P&L VLI** (`vli_pnl`): `build_db.py` junta `24_25_26.xlsx` (2024), `Precos21_24.xlsx` (2021 a 2023)
  e `Precos 25_27.xls.xlsx` (2025 Real e a tendência do ano, que substitui a anterior). Coluna
  `realizado` = 1 no Real e nos N meses realizados da tendência "N+M": **toda leitura de realizado
  usa `realizado=1`**, nunca `panorama LIKE ...` com mês fixo. Orçamentos e BP ficam em
  `vli_pnl_orcamento` (nunca somar com `vli_pnl`). No P&L o DP vem dentro de `rec_fr`
  (`rec_dp` quase sempre zero): "frete" do P&L = frete + DP.
- **Alavancas regulatórias** (`add_alavancas.py`, 23/nov/2026; roda depois de `add_projetos_clientes.py`):
  as 30 inconsistências da VLI frente à regulação em `alavanca_catalogo` (grupo, norma, fonte, tipo,
  evidência), `alavanca_linha` (itens da ficha com R$/t acima da referência, no mês de referência DE
  CADA ITEM; grãos e farelo levam a série mensal do excesso) e `alavanca_cliente` (R$ do P&L e do
  orçamento, contagens). O R$/ano das linhas é calculado no painel (aba Alavancas Regulatórias) com
  `PC_API.volKtRota`/`volMensalRota`; as alavancas 6, 11, 12 e 14 leem `NOVAS.ficha`, a 26 lê o porto e
  a 29 lê `NOVAS.venc` (um número, uma função). Faixa da manobra (8): menor faixa paga por 2+ clientes
  da mesma classe e ferrovia, farelo só com farelo. Bloco `#pcAlavancas` no Painel do Cliente some no
  modo apresentação e não entra no relatório do cliente (usa P&L e ficha, internos da VLI). Texto sem
  travessão (teste). Normas: nunca Res. 3.695/2011 nem art. 35 da Lei 10.233.
- **Varredura de 24/nov/2026** (regras em `../06_Corporate_Memory/Regras_e_Decisoes_LogConsultOS.md` §7):
  comparação entre clientes sempre LÍQUIDA de PIS/COFINS (`ALIQ_PC`/`aliq_pc` no build, `fatorPC`/`famPC` e
  `D.meta.aliq_pc` no painel, `ficha.aliq_item` no mês a mês; P&L também sem ICMS e ISS), par nunca é o
  próprio cliente, janela de volume da base (pcUlt12Sum/volMensal12), grão = média dos itens da rota
  (`ganhoMensalFluxo`, com cache), porto por terminal (`ativo`) e líquido. Alavancas 31 a 46 (grupos G e H)
  cruzam o documento do cliente: tela F-LINK × TR, F-LINK × Ficha (faturado acima do contrato), contratos
  lidos (`CONTRATOS_LIDOS` em add_alavancas.py; acrescentar ali cada contrato novo lido na íntegra), tabela
  publicada anterior em `02_Regulatorio_Tetos/Tabelas_Acessorias/_Arquivo`. Manobra NUNCA entra no teste do teto.
- `gerar_indice_videos.py` gera `09_Fotos/_indice_videos.csv` (diário de captura: vídeo →
  status/cliente/script). Rodar depois de minerar vídeos novos.
- Regras de negócio que definem os números: `../06_Corporate_Memory/Regras_e_Decisoes_LogConsultOS.md`.
- **Armadilha recorrente (já encontrada 6×):** vários `add_<cliente>_precos_contratuais.py`
  existem no disco mas nunca foram ligados ao orquestrador — o `connect_*` correspondente
  roda, não encontra a tabela-fonte, e **pula em silêncio** (`if not t: print("... Pulando"); return`).
  O dado nunca chega ao painel e nada avisa. Ao mexer em qualquer cliente, verifique
  os DOIS scripts (o `add_` e o `connect_`) na ordenação.
- `connect_<cliente>_precos.py` reconciliam dado de vídeo F-LINK (mineração em
  `add_<cliente>_precos_contratuais.py`) para dentro de `projeto_fluxo_tarifas` /
  `projeto_acessorias_abertas` — idempotentes via DELETE+INSERT.
  **O DELETE deve ser por `cliente + fluxo`, nunca só por `cliente`**: um DELETE por cliente
  apaga rotas curadas por OUTROS scripts que o connect não repõe (bug real na APERAM,
  16→9 fluxos). Alguns connects ainda não ligados têm essa bomba armada.
- `rebuild_market_share.sh` e `rebuild_custo_logistico.sh` sequenciam as duas cadeias.
  Nunca rodar `add_custo_logistico.py` sozinho: ele faz `DROP TABLE` e os 7 backfills inserem
  depois — sem eles some 74% da aba.
- `canon.py` normaliza nomes de cliente entre tabelas (regras específicas→genéricas).
- `audit_volumes.py` faz auditoria de matching de volume — rodar depois de qualquer
  mudança que toque volume/produto/rota.

## Convenções
- Sempre preferir 0/"sem dado" honesto a qualquer número inventado ou emprestado de
  outro fluxo/rota/cliente — este é o bug recorrente mais caro já encontrado neste projeto.
- Nunca agrupar (pool) produtos genuinamente diferentes pra "resolver" um match —
  só sinônimos de rótulo confirmados (grafia, abreviação, sufixo de grade).
- Ao editar `painel_template.html`, rodar `python3 atualizar_tudo.py --so-painel` (compila e
  roda os testes). Id novo no HTML: conferir que não existe em outra aba (`tCaptura`/`capKpis`
  já colidiram uma vez e uma tabela escrevia por cima da outra).
- **Teto e IPOA (regra do sócio, 19/nov/2026):** % do teto = (frete + DP) ÷ teto; IPOA =
  acessórias sem DP ÷ (frete + DP). `acessorias` no banco soma o DP; o DP separado está em
  `projeto_fluxo_tarifas.dp_rs_t` e `ipoa_teto.dp`. Nunca voltar a comparar teto só com frete.
- Pares de manobra ignoram valores abaixo de R$ 0,50/t (cobrança simbólica).
- Volume "últimos 12 meses" = janela ancorada no último mês da BASE (não da rota); rota sem
  tráfego na janela tem volume 0 e selo "rota inativa".
- Funções de ganho/volume do Painel do Cliente são expostas em `window.PC_API`; telas fora
  daquele bloco devem usar o PC_API (um número, uma função), nunca recalcular.
- Antes de qualquer alteração destrutiva no banco, fazer backup:
  `cp logconsult.db logconsult.db.bak_pre_<descricao>_$(date +%Y%m%d_%H%M%S)`.
- Trabalho remoto (sem acesso ao `logconsult.db` real): pode editar/revisar lógica,
  mas não roda o pipeline nem valida números — isso só é possível com o banco real local.
