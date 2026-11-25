// LogConsult OS — executa o <script> REAL do painel compilado contra o payload REAL, num DOM
// mínimo (sem navegador), e devolve em JSON os números que precisam bater entre si.
// Uso: node tests/harness_painel.js Painel_LogconsultOS.html
// Chamado por testes_painel.py. Não depende de pacote npm.
'use strict';
const fs = require('fs');
const vm = require('vm');

const html = fs.readFileSync(process.argv[2], 'utf8');
const payload = (html.match(/<script id="painel-data" type="application\/json">([\s\S]*?)<\/script>/) || [])[1];
const scripts = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const erros = [];

// ---- DOM mínimo e permissivo: todo id existe; seletores devolvem vazio ----
const els = new Map();
function makeEl(id, tag) {
  const cls = new Set();
  const el = {
    id, tagName: (tag || 'div').toUpperCase(), style: {}, dataset: {}, children: [], value: '', checked: false,
    textContent: '', title: '', files: null, options: [], disabled: false, _html: '',
    classList: { add: (...c) => c.forEach(x => cls.add(x)), remove: (...c) => c.forEach(x => cls.delete(x)),
      toggle: (c, f) => { const on = f === undefined ? !cls.has(c) : !!f; on ? cls.add(c) : cls.delete(c); return on; },
      contains: c => cls.has(c) },
    get innerHTML() { return this._html; }, set innerHTML(v) { this._html = String(v); },
    get outerHTML() { return this._html; },
    appendChild(c) { this.children.push(c); return c; }, append() {}, prepend() {}, insertBefore(c) { return c; },
    insertAdjacentHTML() {}, insertAdjacentElement() {}, addEventListener() {}, removeEventListener() {},
    querySelector() { return makeEl(); }, querySelectorAll() { return []; }, closest() { return null; },
    getAttribute() { return null; }, setAttribute() {}, removeAttribute() {}, hasAttribute() { return false; },
    remove() {}, replaceWith() {}, scrollIntoView() {}, scrollTo() {}, focus() {}, blur() {}, click() {}, select() {},
    getBoundingClientRect() { return { width: 900, height: 400, left: 0, top: 0, right: 900, bottom: 400 }; },
    offsetWidth: 900, offsetHeight: 400, clientWidth: 900, clientHeight: 400, scrollWidth: 900, scrollHeight: 400,
    parentNode: null, parentElement: null, firstChild: null, lastChild: null, nextSibling: null,
    getContext() { return null; }, cloneNode() { return makeEl(); }, contains() { return false; },
  };
  return el;
}
const document = {
  getElementById(id) {
    if (id === 'painel-data') return { textContent: payload };
    if (!els.has(id)) els.set(id, makeEl(id));
    return els.get(id);
  },
  querySelector() { return makeEl(); }, querySelectorAll() { return []; },
  createElement(t) { return makeEl(null, t); }, createElementNS(_, t) { return makeEl(null, t); },
  createTextNode() { return makeEl(); }, createDocumentFragment() { return makeEl(); },
  addEventListener() {}, removeEventListener() {},
  body: makeEl('body'), documentElement: makeEl('html'), head: makeEl('head'),
};
const store = new Map();
const localStorage = {
  getItem: k => (store.has(k) ? store.get(k) : null), setItem: (k, v) => store.set(k, String(v)),
  removeItem: k => store.delete(k), key: i => [...store.keys()][i] ?? null, get length() { return store.size; },
  clear: () => store.clear(),
};
const ctx = {
  document, localStorage, sessionStorage: localStorage, console: { log() {}, info() {}, debug() {},
    warn: (...a) => erros.push('warn: ' + a.join(' ')), error: (...a) => erros.push('error: ' + a.map(String).join(' ')) },
  location: { hash: '', href: 'file:///painel.html', reload() {} }, history: { replaceState() {}, pushState() {} },
  navigator: { userAgent: 'node', clipboard: { writeText: async () => {} } },
  setTimeout: () => 0, clearTimeout() {}, setInterval: () => 0, clearInterval() {},
  requestAnimationFrame: () => 0, cancelAnimationFrame() {},
  matchMedia: () => ({ matches: false, addEventListener() {}, addListener() {} }),
  getComputedStyle: () => ({ getPropertyValue: () => '' }),
  scrollTo() {}, scrollBy() {}, innerWidth: 1440, innerHeight: 900,
  alert() {}, confirm: () => false, prompt: () => null, addEventListener() {}, removeEventListener() {},
  dispatchEvent() {}, Event: class { constructor(t) { this.type = t; } }, CustomEvent: class { constructor(t) { this.type = t; } },
  ResizeObserver: class { observe() {} disconnect() {} }, IntersectionObserver: class { observe() {} disconnect() {} },
  MutationObserver: class { observe() {} disconnect() {} },
  Blob: class {}, FileReader: class { readAsText() {} }, URL: { createObjectURL: () => '', revokeObjectURL() {} },
  Intl, Date, Math, JSON, Number, String, Array, Object, Set, Map, RegExp, Error, isFinite, isNaN, parseFloat, parseInt,
};
ctx.window = ctx; ctx.self = ctx; ctx.globalThis = ctx;
vm.createContext(ctx);

let topo = null;
try { vm.runInContext(scripts.join('\n;\n'), ctx, { filename: 'painel.js', timeout: 1800000 }); }
catch (e) { topo = String(e && e.stack || e).split('\n').slice(0, 4).join(' | '); }

// ---- coleta, dentro do mesmo contexto (enxerga let/const globais do script) ----
const coleta = `
(() => {
  const out = {};
  const API = window.PC_API;
  out.pc_api = !!API;
  out.novas = typeof NOVAS === 'object' ? {
    reaj: NOVAS.reaj ? {n: NOVAS.reaj.n, nSerie: NOVAS.reaj.nSerie} : null,
    venc: NOVAS.venc ? {n: NOVAS.venc.n, vencidos: NOVAS.venc.vencidos} : null,
    porto: NOVAS.porto ? {rec: NOVAS.porto.rec} : null,
    captura: NOVAS.captura ? {n: NOVAS.captura.n} : null,
    ficha: NOVAS.ficha ? {n: NOVAS.ficha.n, acimaTeto: NOVAS.ficha.acimaTeto, excIpoa: NOVAS.ficha.excIpoa} : null,
    orc: NOVAS.orc ? {n: NOVAS.orc.n, dTotal: NOVAS.orc.dTotal} : null,
    alav: NOVAS.alav ? {n: NOVAS.alav.n, nCli: NOVAS.alav.nCli, nLinhas: NOVAS.alav.nLinhas, totais: NOVAS.alav.totais} : null } : null;
  // Início (nov/2026): mesmos números dos cards do Painel do Cliente, sem NaN, e página do cliente abre
  out.inicio = {ok: false};
  if (window.INICIO_API && API) {
    try {
      const L = window.INICIO_API.calc();
      const naoNum = L.filter(x => ['baixo','baixoRet','medio','alto','retroM'].some(k => !isFinite(x[k]))).length;
      const difAc = L.filter(x => Math.abs(x.acM - ganhoAcessCliente(x.c).mod) > 1).map(x => x.c);
      let abriu = 0; L.slice(0, 5).forEach(x => { if (window.INICIO_API.abrirCliente(x.c, false)) abriu++; });
      // tabela (25/nov/2026): alvo + prioridade, retroativo logo depois do médio
      window.INICIO_API.render();
      const th = document.getElementById('iniTbl').innerHTML;
      const iM = th.indexOf('> Médio</th>'), iR = th.indexOf('> Retroativo</th>'), iA = th.indexOf('> Alto</th>');
      const tabela = {selPrio: (th.match(/class="prio-sel/g) || []).length, ckAlvo: (th.match(/data-alvo=/g) || []).length,
        ordemOk: iM > 0 && iR > iM && iA > iR};
      out.inicio = {ok: true, n: L.length, naoNum, difAc, abriu, tabela,
        medio: L.reduce((s, x) => s + x.medio, 0), alto: L.reduce((s, x) => s + x.alto, 0), baixo: L.reduce((s, x) => s + x.baixo, 0)};
    } catch (e) { out.inicio = {ok: false, erro: String(e.message || e)}; }
  }
  // caixa do cálculo do Portfólio por Cliente (25/nov/2026): monta para as três origens sem NaN/undefined
  out.calc = {ok: false};
  if (window.BP_CALC) {
    try {
      const mk = (r, ktipo, tipo) => ({cliente: r.cliente, origem: r.origem || '', destino: r.destino || '', produto: r.produto, tipo, ktipo,
        tipo_label: 'x', valor_ano_moderado: 1, valor_ano_otimista: 2, _src: r});
      const T = (D.teto.fluxos || []), ruins = []; let n = 0;
      const amostras = [...T.filter(x => x.acess_sugerida_fonte && x.acess_sugerida_fonte.startsWith('sem par')).slice(0, 40).map(r => mk(r, 'teto', 'acessoria')),
        ...T.filter(x => x.acess_sugerida_fonte && x.acess_sugerida_fonte.startsWith('pares')).slice(0, 40).map(r => mk(r, 'teto', 'acessoria')),
        ...((D.acess_hub && D.acess_hub.sim) || []).slice(0, 60).map(r => mk(r, undefined, 'acessoria')),
        ...(D.comparativo.tarifas || []).slice(0, 60).map(r => mk(r, undefined, 'preco'))];
      amostras.forEach(o => { const h = window.BP_CALC.html(o); n++;
        if (!/Conta/.test(h) || /NaN|undefined/.test(h)) ruins.push(o.cliente + ' ' + o.origem + ' ' + o.destino + ' ' + (o.ktipo || o.tipo)); });
      // regras de 25/nov: volume uma vez por rota, sem par = ganho zero, DP sem ganho, valor do Painel do Cliente
      const porRota = {}; T.forEach(x => { const k = x.cliente + '|' + x.origem + '|' + x.destino + '|' + x.produto;
        (porRota[k] = porRota[k] || {v: x.vol12_kt || 0, s: 0}).s += x.vol_item_kt || 0; });
      const volRuim = Object.entries(porRota).filter(([k, o]) => Math.abs(o.s - o.v) > 0.05 * Math.max(1, o.v)).length;
      const semParComGanho = T.filter(x => x.acess_sugerida_fonte === 'sem par na estação' && ((x.receita_potencial || 0) > 0 || (x.receita_potencial_moderado || 0) > 0)).length;
      const dpComGanho = ((D.acess_hub && D.acess_hub.sim) || []).filter(x => /PASSAGEM/.test(x.servicos) && ((x.ganho_mod_ano || 0) > 0 || (x.ganho_otm_ano || 0) > 0)).length;
      let pcOk = 0, pcRuim = 0;
      if (window.BP_PC) T.filter(x => (x.receita_potencial || 0) > 0).slice(0, 150).forEach(r => { const v = window.BP_PC.valor(mk(r, 'teto', 'acessoria'));
        if (v) { (isFinite(v.mod) && isFinite(v.otm) && v.otm + 1 >= v.mod && (!v.serie || Math.abs(v.serie.reduce((a, b) => a + b, 0) - v.mod) < 1)) ? pcOk++ : pcRuim++; } });
      out.calc = {ok: true, n, ruins: ruins.slice(0, 5), volRuim, semParComGanho, dpComGanho, pcOk, pcRuim,
        tetoMod: T.reduce((a, x) => a + (x.receita_potencial_moderado || 0), 0), volumeAte: (D.meta.data_base || {}).volume_ate};
    } catch (e) { out.calc = {ok: false, erro: String(e.message || e)}; }
  }
  // bloco de alavancas no Painel do Cliente: monta para todo cliente sem erro
  out.alav_cli = {ok: 0, erros: []};
  if (window.ALAV_API && window.pcRenderAlav && API) {
    [...new Set(API.PJF.map(f => API.canonPC(f.cliente)))].forEach(c => {
      try { window.pcRenderAlav(c); window.ALAV_API.doCliente(c); out.alav_cli.ok++; }
      catch (e) { out.alav_cli.erros.push(c + ': ' + String(e.message || e)); }
    });
  }
  out.clientes = {};
  if (API) {
    const clis = [...new Set(API.PJF.map(f => API.canonPC(f.cliente)))];
    clis.forEach(c => {
      const g = ganhoAcessCliente(c);
      const somaFluxos = Object.values(g.porFluxo).reduce((s, x) => s + (x.mod || 0), 0);
      // ganho de um cliente não pode depender de quem está aberto no Painel (bug real de jul/2026)
      const g2 = ganhoAcessCliente(c);
      const naoFinitos = Object.values(g.porFluxo).filter(x => !isFinite(x.mod) || !isFinite(x.otm)).length;
      const inativosComGanho = API.pjDo(c).filter(f => f.rota_inativa && !API.isRetro(f.fluxo)
        && (g.porFluxo[API.fkey(f)] || {}).mod > 0).length;
      const conteinerComGanho = API.pjDo(c).filter(f => f.unidade === 'R$/contêiner'
        && (g.porFluxo[API.fkey(f)] || {}).mod > 0).length;
      const dbgInat = API.pjDo(c).filter(f => f.rota_inativa && (g.porFluxo[API.fkey(f)] || {}).mod > 0)
        .map(f => [f.fluxo, f.rota_ult, API.fluxoVolKtGanho(f)]);
      const detalhe = window.process_env_detalhe === c ? API.pjDo(c).filter(f => !API.isRetro(f.fluxo)).map(f => {
        const x = g.porFluxo[API.fkey(f)] || {}; return [f.fluxo, +(x.mod || 0).toFixed(0), +(x.modRsT || 0).toFixed(2), +(API.fluxoVolKtGanho||API.fluxoVolKt)(f).toFixed(1)]; }) : null;
      out.clientes[c] = {detalhe, dbgInat, mod: g.mod, otm: g.otm, n: g.n, somaFluxos, repetido: g2.mod, naoFinitos,
                         inativosComGanho, conteinerComGanho};
    });
  }
  // relatório do cliente: gera para cada cliente e procura nome de OUTRO cliente no HTML
  out.relatorio = {};
  if (API && typeof relatorioClienteHtml === 'function') {
    const nomes = [...new Set(API.PJF.map(f => API.canonPC(f.cliente)))];
    nomes.forEach(c => {
      try {
        const html = relatorioClienteHtml(c).toUpperCase();
        const norm = s => ' ' + String(s).toUpperCase().replace(/[^A-Z0-9ÀÁÂÃÉÊÍÓÔÕÚÇ]+/g, ' ') + ' ';
        const txt = norm(html);
        const vaz = nomes.filter(o => o !== c && o.length >= 4 && !c.includes(o) && !o.includes(c)
          && txt.includes(norm(o)));
        out.relatorio[c] = {ok: true, vazamentos: vaz, tamanho: html.length};
      } catch (e) { out.relatorio[c] = {ok: false, erro: String(e.message || e)}; }
    });
  }
  // grãos/farelo mês a mês: volume somado dos 12 meses = volume 12m do resto do painel
  out.mensal = {n: 0, volDiverge: 0};
  if (API && API.ganhoMensal) {
    API.PJF.filter(f => !API.isRetro(f.fluxo)).forEach(f => {
      const cob = String(f.cobertura || ''); const m = cob.startsWith('ficha 2026 (item ') ? [null, parseInt(cob.slice(17), 10)] : null; const r = API.fluxoRota(f);
      if (!m || !r || !r.origem) return;
      const g = API.ganhoMensal(API.canonPC(f.cliente), +m[1], r.origem, r.destino, r.produto, 'med');
      if (!g) return;
      out.mensal.n++;
      if (Math.abs(g.volKt - API.volKtRota(API.canonPC(f.cliente), r.origem, r.destino, r.produto)) > 0.001) out.mensal.volDiverge++;
    });
  }
  out.ranking = (typeof rankRows !== 'undefined' && Array.isArray(rankRows))
    ? rankRows.map(r => ({cliente: r.cliente, mod: r.anual_mod, otm: r.anual_otm})) : null;
  return JSON.stringify(out);
})()`;
let dados = null;
ctx.process_env_detalhe = process.env.HARNESS_DETALHE || '';
try { dados = JSON.parse(vm.runInContext(coleta, ctx, { timeout: 1800000 })); }
catch (e) { erros.push('coleta: ' + String(e && e.message || e)); }
process.stdout.write(JSON.stringify({ erro_topo: topo, erros, dados }));
