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
- **Navegação nov/2026:** tela inicial `#inicio` (ganhos por cliente em baixo, médio e alto risco, via
  `PC_API.resumoCliente`, sem conta nova; baixo = alavancas com documento 1, 5, 33, 34 por ano e 31, 35, 36 +
  acessória vedada do retroativo como recuperação única), página do cliente `#cliente/NOME`, trilha no topo,
  busca global, histórico do navegador (`pushState`). Menu em 6 grupos; toda tela antiga segue no menu.
  Visual do GestALB (Inter, cinza #F5F5F7, cartões sem sombra, controle segmentado). Cartão explicativo:
  qualquer elemento com `data-hc` (bloco 10 do template). O Início calcula depois de desenhar (`renderDepois`).
- **Ajustes de 25/nov/2026:** faixas laterais recolhidas (menu à esquerda, Insights à direita) que abrem ao
  passar o mouse, por cima do conteúdo (CSS `@media (min-width:1101px)`). A aba Clientes-alvo saiu do menu:
  a marcação de alvo (caixa de seleção) e a prioridade (`lc_prioridade_v1`: P1, P2, P3 ou vazio; `setAlvo`,
  `setPrio`, `prioSelHtml`) ficam na tabela do Início, com filtro por prioridade; a lista completa e o backup
  ficam no bloco recolhível `#iniAlvos` (o endereço `#alvos` abre esse bloco). Retroativo é a coluna ao lado
  do Médio. No Portfólio por Cliente, oportunidade marcada na aba Teto Tarifário é ACESSÓRIA (o ganho é
  acessória cobrada menos sugerida; `ktipo:'teto'` guarda a chave antiga das classificações) e clicar na
  oportunidade abre a caixa do cálculo (`BP_CALC`, `bpCalcHtml`): conta, tabela dos pares com o mesmo
  agrupamento do build e a leitura da mesma rota no Painel do Cliente.
- **Ficha de Fluxo, versão de 24/nov/2026** (com açúcar e combustíveis, 3.018 itens, 94 clientes): a anterior
  está em `07_Dados VLI/_Arquivo`. **Teto = ROTA INTEIRA** (decisão do sócio, 25/nov): a coluna "Teto Tarifario"
  da ficha nova traz teto de trecho em parte dos itens e NÃO é usada. `add_ficha_fluxo.teto_rota_inteira` usa,
  nesta ordem, a ficha de 19/nov arquivada, `ipoa_teto.teto_base` (congelado antes de a ficha escrever), rota
  gêmea e, por último, a ficha nova marcada "ficha (a confirmar)". `teto_ficha` e `teto_fonte` ficam nas
  tabelas da ficha. Teste: nenhum item atual com frete + DP acima do teto.
- **Volume unificado** (25/nov): `VOLU` em build_painel.py = volume_hist + P&L realizado nos meses que ele não
  tem; janela de 12 meses até o último mês realizado. Vale para Hub, aba Teto, Comparativo e data-base.
- **Modelo das abas de origem (25/nov, lista em `../Melhorias_Modelo_2026-11-25.md`):** aba Teto compara
  manobra de origem e de destino serviço a serviço contra os outros clientes na mesma estação e família
  (`_ref_estacao`, `fam_par`), líquido de PIS/COFINS, sem DP; volume repartido entre os itens da rota
  (`vol_item_kt`); sem par = ganho zero e a estimativa pelo IPOA vai em `receita_estimativa`, fora de qualquer
  soma. Hub: pares por serviço + estação + família, DP sem ganho. Portfólio por Cliente: acessória marcada
  vale o valor do Painel do Cliente (`BP_PC.valor`, `bpAplicaPC`, chamado no fim do script), uma vez por
  rota e produto ("já contada"); um só par = selo e risco alto por padrão (`bpRiscoO`); projeção mensal
  segue a série de grãos e farelo (`PC_API.mensalFluxo`).
- **Início × Painel do Cliente (25/nov):** o Início refaz a linha do cliente sempre que o Painel do Cliente
  redesenha os cartões (`INICIO_API.marcar`, chamado em `pcRenderGanhos`), então simulação salva aparece nos
  dois iguais (teste `segueSim`). Cartões P1, P2 e P3 (`#iniPrio`) somam os clientes de cada prioridade e
  filtram a tabela no clique. LD Celulose tem uma rota só, CELULOSE EDC VAZ (o curado nasce com a rota).
- **Aba Porto do Painel do Cliente (25/nov):** aparece para cliente com receita de porto no P&L (`portoDo`).
  Preço = receita ÷ volume (realizado, 2024 em diante, `porto_servicos.mensal`), bruto e líquido; pares no
  mesmo terminal e produto (anonimizados no modo apresentação); referências públicas em
  `precos_portos_referencia` (`add_porto_referencias.py`, curadas com fonte, data e tipo; em Santos só a
  lista do próprio TIPLAM é publicada). O ganho da aba é indicação: fora dos cartões e do Início.
- **Isonomia de grão e farelo por MICRORREGIÃO (25/nov, regra do sócio):** par = outro cliente na mesma
  origem, destino, produto E microrregião do item (Ficha 2026), no mesmo mês de preço, líquido de PIS/COFINS.
  Painel do Cliente: `isoMicroRota` (frete + DP mês a mês, média dos itens do cliente × volume do mês; sem par =
  zero; bloco "Isonomia por microrregião" na aba). Comparativo de Tarifas: `iso_micro` no build (tarifa total do
  item no mês de referência, par do mesmo mês). Alavanca 38: grão e farelo pela ficha por microrregião. O
  retroativo histórico (P&L 2021 a 2025) não tem microrregião e segue pela rota inteira.
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
- **Git (25/nov/2026):** ao fim de cada entrega, com `atualizar_tudo.py` em 0 falhas, o Claude faz commit e
  `git push` (autorizado pelo usuário) e avisa o que subiu. Nunca force-push; banco e painel compilado
  continuam fora do Git.
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
