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
- Volume "últimos 12 meses" = janela ancorada no último mês da BASE (não da rota); rota sem
  tráfego na janela tem volume 0 e selo "rota inativa".
- Funções de ganho/volume do Painel do Cliente são expostas em `window.PC_API`; telas fora
  daquele bloco devem usar o PC_API (um número, uma função), nunca recalcular.
- Antes de qualquer alteração destrutiva no banco, fazer backup:
  `cp logconsult.db logconsult.db.bak_pre_<descricao>_$(date +%Y%m%d_%H%M%S)`.
- Trabalho remoto (sem acesso ao `logconsult.db` real): pode editar/revisar lógica,
  mas não roda o pipeline nem valida números — isso só é possível com o banco real local.
