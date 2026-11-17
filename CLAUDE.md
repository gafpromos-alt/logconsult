# LogConsult OS — regras para trabalhar neste repositório

**Confidencial.** Este repo contém só o CÓDIGO (scripts Python + template HTML). O
banco (`logconsult.db`) e o painel compilado (`Painel_LogconsultOS.html`, que carrega
todo o payload de dados de clientes embutido no JSON) NÃO estão versionados — ficam
fora via `.gitignore`. Nunca remova essas entradas do `.gitignore` nem tente commitar
esses arquivos.

## Arquitetura
- `painel_template.html` → processado por `build_painel.py` (lê `logconsult.db`) → gera `Painel_LogconsultOS.html`.
- Sempre editar `painel_template.html`, nunca o `Painel_LogconsultOS.html` compilado diretamente.
- `add_projetos_clientes.py` é o orquestrador principal, mas **NÃO roda tudo e NÃO chama
  `build_painel.py`** (auditoria 31/jul/2026). Ele chama ~25 dos ~62 scripts `add_*`/
  `connect_*`; o rebuild do painel é um passo manual separado. Antes de assumir que um
  script roda no pipeline, confira com `grep -n "<nome_do_script>" add_projetos_clientes.py`.
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
- `rebuild_market_share.sh` sequencia a cadeia de market share. A cadeia de custo logístico
  NÃO tem equivalente: `add_custo_logistico.py` faz `DROP TABLE` e 7 backfills inserem
  depois — rodar só o primeiro destrói 74% das linhas.
- `canon.py` normaliza nomes de cliente entre tabelas (regras específicas→genéricas).
- `audit_volumes.py` faz auditoria de matching de volume — rodar depois de qualquer
  mudança que toque volume/produto/rota.

## Convenções
- Sempre preferir 0/"sem dado" honesto a qualquer número inventado ou emprestado de
  outro fluxo/rota/cliente — este é o bug recorrente mais caro já encontrado neste projeto.
- Nunca agrupar (pool) produtos genuinamente diferentes pra "resolver" um match —
  só sinônimos de rótulo confirmados (grafia, abreviação, sufixo de grade).
- Ao editar `painel_template.html`, rodar `python3 build_painel.py` depois e verificar
  que não há erro de sintaxe (`node -e "new Function(...)"` no bloco de script).
- Antes de qualquer alteração destrutiva no banco, fazer backup:
  `cp logconsult.db logconsult.db.bak_pre_<descricao>_$(date +%Y%m%d_%H%M%S)`.
- Trabalho remoto (sem acesso ao `logconsult.db` real): pode editar/revisar lógica,
  mas não roda o pipeline nem valida números — isso só é possível com o banco real local.
