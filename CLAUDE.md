# LogConsult OS — regras para trabalhar neste repositório

**Confidencial.** Este repo contém só o CÓDIGO (scripts Python + template HTML). O
banco (`logconsult.db`) e o painel compilado (`Painel_LogconsultOS.html`, que carrega
todo o payload de dados de clientes embutido no JSON) NÃO estão versionados — ficam
fora via `.gitignore`. Nunca remova essas entradas do `.gitignore` nem tente commitar
esses arquivos.

## Arquitetura
- `painel_template.html` → processado por `build_painel.py` (lê `logconsult.db`) → gera `Painel_LogconsultOS.html`.
- Sempre editar `painel_template.html`, nunca o `Painel_LogconsultOS.html` compilado diretamente.
- `add_projetos_clientes.py` é o orquestrador: roda todos os `add_*_precos_contratuais.py` /
  `connect_*_precos.py` na ordem certa, depois `build_painel.py`.
- `connect_<cliente>_precos.py` reconciliam dado de vídeo F-LINK (mineração em
  `add_<cliente>_precos_contratuais.py`) para dentro de `projeto_fluxo_tarifas` /
  `projeto_acessorias_abertas` — sempre idempotentes (DELETE+INSERT).
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
