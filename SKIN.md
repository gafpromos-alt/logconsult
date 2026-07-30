# Skin — Elite Health & Performance (APLICADO)

**Status: aplicado ao `Painel_LogconsultOS.html`** (tema claro, fonte Geist, acento verde, nav-rail à esquerda, header com título dinâmico). Tokens Elite (oklch) inline no `painel_template.html` via `:root`, com meus nomes remapeados por alias (`--panel→--surface`, `--txt→--ink`, `--accent→--green`…). Os semânticos de barra (`--good/--warn/--info/--hot`) usam os matizes Elite (160/75) com um pouco mais de chroma para legibilidade dos gráficos.

**Re-tematizar em 1 minuto:** troque o matiz (3º número) de `--green` no `:root` do `painel_template.html` e rode `build_painel.py`. Tudo acompanha (cards, badges, barras) porque os `*-bg` derivam via `color-mix`.

> O dashboard antigo `03_Radar_Oportunidades/Radar_Logconsult.html` (tema escuro) foi **superado** pelo painel unificado — mantido só como histórico. Se quiser, aplico o mesmo skin nele.

---

## (Referência) Reskin — adotar o layout do Elite Performance Project

Os dashboards (`painel_template.html` e `../03_Radar_Oportunidades/radar_template.html`)
usam **variáveis CSS no `:root`**. Trocar a identidade visual = sobrescrever essas
variáveis — nenhuma mudança de estrutura/JS.

## O que preciso de você (configs do Elite Performance)
- **Paleta:** cor de fundo, cor de painel, cor de texto, e a cor de destaque (accent).
- **Tipografia:** família da fonte (e se há fonte para números/mono).
- **Raio de canto** e estilo (mais quadrado / mais arredondado).
- **Logo** (arquivo) e nome a exibir no cabeçalho.
- Tema **claro ou escuro**.

## Onde aplico (variáveis atuais)
```css
:root{
  --bg / --bg-2 / --panel / --panel-2   /* fundos */
  --line / --line-2                     /* bordas */
  --txt / --txt-2 / --txt-3             /* textos (principal→apagado) */
  --accent / --accent-2                 /* destaque (dourado atual) */
  --good --warn --info --hot --bad      /* semânticos (verde/âmbar/azul/laranja/vermelho) */
  --radius / --radius-sm                /* cantos */
  --font / --mono                       /* tipografia */
}
```

Me mande as configs (ou um print/CSS do Elite Performance) e eu gero um bloco `:root`
único, aplico nos dois templates e rebuildo. Fica idêntico à identidade de vocês.
