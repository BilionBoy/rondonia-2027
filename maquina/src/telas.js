// ---------- custo da máquina
const M = D.M, F = M.folha, C = M.custeio, R = M.regionais, G = F.rgf, CP = M.comparativo;
const mi = v => Math.abs(v || 0) < 1000 ? "R$ " + br(v || 0) : fmt(v / 1e6);
const PORTAL_PAG = "https://transparencia.ro.gov.br/fornecedor";
const DATA_PAG = M.coleta.pagamentos, MES_PAG = M.coleta.mes_pagamentos;
const LK = {
  rgf: ["Conferir o RGF no Siconfi (Executivo de RO, Anexo 1)", "https://siconfi.tesouro.gov.br/siconfi/pages/public/declaracao/declaracao_list.jsf"],
  lrf: ["Lei de Responsabilidade Fiscal (arts. 19, 20, 22 e 59)", "https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp101.htm"],
  pessoal: ["Folha de pagamento no Portal da Transparência", "https://transparencia.ro.gov.br/Pessoal"],
  pag: ["Pagamentos de fornecedores no Portal da Transparência", PORTAL_PAG],
  contratos: ["Contratos no Portal da Transparência", "https://transparencia.ro.gov.br/Contratos"],
};
const COR_TEMA = {"Combustível": "var(--c1)", "Locação de veículos": "var(--c2)", "Manutenção de veículos": "var(--c3)", "Transporte escolar": "var(--c6)", "Ambulâncias": "var(--c7)", "Aluguel de imóveis": "var(--c4)"};
const CHAVE_TEMA = {"Combustível": "combustivel", "Locação de veículos": "locacao", "Manutenção de veículos": "manutencao", "Transporte escolar": "transporte", "Ambulâncias": "ambulancia", "Aluguel de imóveis": "imovel"};
const NOME_CHAVE = Object.fromEntries(Object.entries(CHAVE_TEMA).map(([n, k]) => [k, n]));
const CURTO = {"Combustível": "Combustível", "Locação de veículos": "Locação", "Transporte escolar": "Transporte escolar", "Manutenção de veículos": "Manutenção", "Ambulâncias": "Ambulâncias", "Aluguel de imóveis": "Aluguel"};
const claro = cor => `color-mix(in srgb, ${cor} 35%, transparent)`;
const GRUPOS = F.grupos.filter(g => g.grupo !== "inativo");
const COR_GRUPO = {efetivo: "var(--c1)", militar: "var(--c5)", comissionado: "var(--c3)", temporario: "var(--c2)", cedido: "var(--c4)", apoio: "var(--c6)", judicial: "var(--cinza)", inativo: "var(--cinza)"};
const legenda = itens => `<div class="legenda">${itens.map(([n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("")}</div>`;
const notaPag = (nome, v, l2, cnpj, link = PORTAL_PAG) => ({credor: nome, valor: v / 1e6, l2, cnpj, link});
const notaContrato = c => ({credor: `${c.sigla} · ${c.contratado}`, valor: c.valor / 1e6, l2: `Contrato ${c.numero} · vigência até ${c.vigencia ? c.vigencia.split("-").reverse().join("/") : "—"}`,
  historico: c.objeto, fonte: c.processo ? "Processo SEI " + c.processo : "", link: c.link});
const pr = (nome, valor, sub, linhas, link, notas) => ({nome, valor, sub, linhas, link, notas});
const var_ = (a, b) => a ? `${b >= a ? "+" : "−"}${br(Math.abs(100 * (b - a) / a), 0)}%` : "—";
const dataBR = iso => iso ? iso.split("-").reverse().join("/") : "—";
let atual = 0;

// Telão: a base escala pela referência Full HD (1920 × 1080 = zoom 1), o que deixa a letra pequena numa TV.
// Aqui a referência é 1440 × 900: numa TV Full HD tudo fica 20% maior (além da letra já aumentada); em 4K, 2,4 vezes.
// A altura de 900 garante que cada etapa caiba sem rolar. Abaixo disso nada muda.
const zoomTelao = () => document.documentElement.style.setProperty("--z", Math.max(1, Math.min(2.6, innerWidth / 1440, innerHeight / 900)).toFixed(3));
zoomTelao(); addEventListener("resize", zoomTelao);

// Animação curta: a base espera até 2 s para empilhar dez partes; aqui tudo aparece em menos de meio segundo,
// para o clique responder na hora
const anima = (e, set, atraso) => {
  if (semMov()) return set(1);
  const t0 = performance.now() + Math.min(atraso, 250);
  const p = t => { const k = Math.max(0, Math.min(1, (t - t0) / 380)); set(1 - Math.pow(1 - k, 3)); if (k < 1) requestAnimationFrame(p); };
  requestAnimationFrame(p);
};
cresce = (e, y0, y1, h1, atraso) => anima(e, q => { e.setAttribute("y", y0 + (y1 - y0) * q); e.setAttribute("height", h1 * q); }, atraso / 8);
alarga = (e, w1, atraso) => anima(e, q => e.setAttribute("width", w1 * q), atraso / 8);

// Barras que ocupam a altura do quadro (a base limita a 40 px por linha e sobra espaço embaixo)
barras = function (cont, itens, ref) {
  const h0 = cont.clientHeight || 300;
  itens = itens.slice(0, Math.max(5, Math.floor(h0 / 28)));   // cada linha com pelo menos 28 px; o resto fica em As provas
  const {s, w, h} = novoSvg(cont), n = itens.length, linha = Math.min(72, h / n), rot = Math.min(230, w * .34), area = w - rot - 170;
  const max = Math.max(...itens.map(i => i.partes.reduce((a, p) => a + p.v, 0)), 1e-9);
  itens.forEach((it, i) => {
    const g = el(s, "g", {class: "alvo"}), y = i * linha, bh = Math.min(linha * .62, 34);
    el(g, "rect", {x: 0, y, width: w, height: linha, fill: "transparent"});
    el(g, "text", {x: rot - 12, y: y + linha / 2 + 5, "text-anchor": "end", class: it.destaque ? "forte" : ""}, it.rot);
    let acum = 0;
    it.partes.forEach((p, j) => {
      const ww = area * p.v / max, r = el(g, "rect", {class: "b", x: rot + acum, y: y + (linha - bh) / 2, width: 0, height: bh, fill: p.cor, rx: 3});
      alarga(r, ww, i * 40 + j * 200); acum += ww;
    });
    el(g, "text", {x: rot + acum + 10, y: y + linha / 2 + 5, class: "forte"}, it.dir);
    if (it.dica) dica(g, ...it.dica);
    if (it.clique) g.addEventListener("click", () => it.clique(g, s));
  });
  return s;
};

function esq(o) {
  $("#esq").innerHTML = `<div class="entra"><div class="kicker">${o.kicker}</div><h2 class="titulo">${o.titulo}</h2>
    ${o.n ? `<div class="numero${o.provaN ? " clic" : ""}" data-pn="1"><span class="n">${o.n}</span><span class="s">${o.s}</span></div>` : `<p class="dica-uso" style="margin:4px 0 8px">${o.s}</p>`}
    ${o.estat ? `<div class="estat">${o.estat.map(([k, v, p], i) => `<div class="${p ? "clic" : ""}" data-pe="${i}"><div class="k">${k}</div><div class="v">${v}</div></div>`).join("")}</div>` : ""}</div>
    ${o.alterna ? `<div class="alterna"><span class="rot">${o.alterna[0]}</span>${o.alterna[1].map((t, i) => `<button type="button" class="${i === o.alterna[2] ? "on" : ""}">${t}</button>`).join("")}</div>` : ""}
    ${o.legenda || ""}
    ${o.corpo || `<div class="grafico" id="graf"></div>`}
    <div class="dica-uso">${o.dicaUso || ""}</div>
    <div class="rodape"><div class="fonte">${o.fonte}</div>${o.dados ? `<button class="btn-dados contorno" type="button" data-dados="1">▦ Ver os dados de origem</button>` : ""}
      <span class="navp"><button type="button" id="ant" aria-label="Etapa anterior" ${atual ? "" : "disabled"}>←</button><button type="button" id="prox" aria-label="Próxima etapa" ${atual < TELAS.length - 1 ? "" : "disabled"}>→</button></span></div>`;
  if (o.alterna) $("#esq").querySelectorAll(".alterna button").forEach((b, i) => b.onclick = () => o.alterna[3](i));
  // cada número abre a prova: de onde vem, a regra da conta e o link oficial
  const marca = el => document.querySelectorAll("#esq .clic").forEach(x => x.classList.toggle("sel", x === el));
  const prova = (el, p, rot) => { marca(el); $("#aviso").hidden = true; mostraProvas("De onde vem este número. Clique para abrir; o link leva à fonte oficial.", [p], {filtro: rot, abrir: 0, limpar: () => { marca(null); o.padrao?.(); }}); };
  if (o.provaN && o.n) $("#esq [data-pn]").onclick = e => prova(e.currentTarget, o.provaN, "número principal");
  (o.estat || []).forEach(([k, , p], i) => { if (p) $(`#esq [data-pe="${i}"]`).onclick = e => prova(e.currentTarget, p, k.replace(/<[\s\S]*/, "").trim()); });
  idsAtuais = o.dados || [];
  document.querySelectorAll("[data-dados]").forEach(b => b.onclick = () => abreDados(idsAtuais));
  $("#btn-dados").onclick = () => idsAtuais.length ? abreDados(idsAtuais) : null;
  $("#btn-dados").style.visibility = idsAtuais.length ? "visible" : "hidden";
  $("#ant").onclick = () => ir(atual - 1); $("#prox").onclick = () => ir(atual + 1);
  o.padrao?.();
}
const provaRgf = (nome, valor, conta, extra = []) => pr(nome, mi(valor), `RGF do Executivo, ${G.periodo}`,
  [["Valor", "R$ " + br(valor, 2)], ["Onde está", conta], ["Período", "12 meses até agosto de 2026 (2º quadrimestre)"], ...extra], LK.rgf);

// ---------- 0. o que decidir
const PRIME_MAN = M.cartao.find(c => /PRIME/i.test(c.contratado) && c.sigla === "SUGESP");
const UZZI = M.cartao.find(c => /UZZIPAY/i.test(c.contratado) && c.sigla === "SUGESP");
const PRIME_DER = M.cartao.find(c => /PRIME/i.test(c.contratado) && c.sigla === "DER");
const PV = D.tabelas["veiculos-2026"].linhas, PI = D.tabelas["imoveis-2026"].linhas;
const pagoA = rx => PV.filter(r => rx.test(r[2])).reduce((a, r) => a + r[8], 0);
const VENCE27 = M.vencem.filter(c => c.vigencia <= "2027-12-31");
const margemAlerta = (G.limites.alerta - G.historico.at(-1).pct_rcl) / 100 * G.historico.at(-1).rcl_ajustada;
function decisoes() {
  const ap = F.aposentadoria, t = F.total, h = G.historico.at(-1);
  return [
    {q: "Vence antes da posse", urgente: true, v: dataBR(PRIME_MAN?.vigencia), t: "O contrato de manutenção de toda a frota (Prime, pela SUGESP) termina em 02/01/2027",
      d: `Valor de ${mi(PRIME_MAN?.valor)}. Sem renovação ou novo contrato, a frota fica sem manutenção nos primeiros dias do governo.`,
      prova: pr("Contrato de autogestão de frota · SUGESP", mi(PRIME_MAN?.valor), "manutenção preventiva e corretiva por rede credenciada", [["Contratada", PRIME_MAN?.contratado], ["Assinatura", dataBR(PRIME_MAN?.assinatura)], ["Vigência publicada", dataBR(PRIME_MAN?.vigencia)], ["Pago à Prime em 2026 pelo Executivo", mi(pagoA(/PRIME CONSULT/i))]], LK.contratos, [notaContrato(PRIME_MAN)])},
    {q: "Juntar contratos", v: mi(pagoA(/UZZIPAY|PRIME CONSULT/i)), t: "Duas gerenciadoras de cartão cuidam da frota: Uzzipay e Prime",
      d: `Combustível pela Uzzipay (SUGESP, ${mi(UZZI?.valor)}) e pela Prime (DER, ${mi(PRIME_DER?.valor)}); manutenção pela Prime. Um contrato só na renovação dá escala de preço. Pago às duas em 2026 até ${DATA_PAG}.`,
      prova: pr("Contratos das gerenciadoras de cartão", mi(pagoA(/UZZIPAY|PRIME CONSULT/i)), `pago em 2026 até ${DATA_PAG}, só Executivo`, [["Uzzipay, pago em 2026", mi(pagoA(/UZZIPAY/i))], ["Prime, pago em 2026", mi(pagoA(/PRIME CONSULT/i))],
        ["Atenção", "Nos contratos de abastecimento (Uzzipay e Prime-DER) o portal mostra a vigência original já vencida e os pagamentos seguem em 2026: conferir os aditivos no SEI."]], LK.contratos, M.cartao.map(notaContrato))},
    {q: "Janela de renegociação", v: br(VENCE27.length), t: `contratos de aluguel e de locação de veículos vencem até dezembro de 2027`,
      d: `Somam ${mi(VENCE27.reduce((a, c) => a + c.valor, 0))} em valor contratado. Na renovação dá para trocar imóvel alugado por prédio próprio ou juntar locações.`,
      prova: pr("Contratos que vencem até 31/12/2027", mi(VENCE27.reduce((a, c) => a + c.valor, 0)), "aluguel de imóvel e locação de veículo, Poder Executivo, vigência publicada no portal",
        [["Aluguel de imóvel", br(VENCE27.filter(c => c.tipo === "imovel").length)], ["Locação de veículo", br(VENCE27.filter(c => c.tipo === "locacao").length)]], LK.contratos, VENCE27.map(notaContrato))},
    {q: "Folha parada", v: mi(ap.bruto_mes * 13) + "/ano", t: `${br(ap.pessoas)} servidores afastados aguardando aposentadoria`,
      d: `${br(ap.tempo["mais de 2 anos"] || 0)} esperam há mais de 2 anos. Acelerar os processos tira esse salário da folha ativa e libera a vaga.`,
      prova: pr("Servidores aguardando aposentadoria", mi(ap.bruto_mes) + "/mês", "SEGEP, referência outubro de 2026", [["Servidores", br(ap.pessoas)], ["Afastados da função", br(ap.afastados)], ["Por ano (13 salários)", mi(ap.bruto_mes * 13)],
        ...["até 6 meses", "7 a 12 meses", "1 a 2 anos", "mais de 2 anos"].map(k => ["Esperando há " + k, br(ap.tempo[k] || 0)])], LK.pessoal)},
    {q: "Cobrar a SEGEP", v: br(t.sem_unidade), t: "servidores ativos sem unidade na planilha da folha",
      d: `${mi(t.bruto_sem_unidade)} por mês pagos a quem não aparece lotado em nenhum órgão. Antes de cortar ou contratar, é preciso saber onde estão.`,
      prova: pr("Servidores ativos sem unidade", br(t.sem_unidade), "planilha da SEGEP de outubro de 2026, coluna UNIDADE vazia", [["Bruto de outubro", mi(t.bruto_sem_unidade)], ["Por ano (× 13⅓)", mi(t.bruto_sem_unidade * 13.33)]], LK.pessoal)},
    {q: "Margem da lei", v: br(h.pct_rcl, 2) + "%", t: "da receita corrente líquida vai para pessoal (limite de alerta: 44,1%)",
      d: `Até o limite de alerta cabem mais ${mi(margemAlerta)} por ano de folha. Em 2023 eram ${br(G.historico[0].pct_rcl, 2)}%.`,
      prova: provaRgf("Despesa total com pessoal sobre a receita", h.dtp, "Anexo 1, linha DTP (VI), coluna % sobre a RCL Ajustada", [["Percentual", br(h.pct_rcl, 2) + "%"], ["Receita corrente líquida ajustada", mi(h.rcl_ajustada)], ["Limite de alerta (90%)", "44,1%"], ["Limite prudencial (95%)", "46,55%"], ["Limite máximo", "49%"]])},
  ];
}
function telaDecidir() {
  const DS = decisoes();
  esq({kicker: "Para a equipe de transição", titulo: "O que dá para decidir em 2027", n: "", s: "Seis pontos tirados do painel. Clique num deles para ver a prova.",
    corpo: `<div class="decisoes" id="decs">${DS.map((d, i) => `<button class="dec${d.urgente ? " urgente" : ""}" type="button" data-i="${i}"><span class="q">${d.q}</span><span class="v">${d.v}</span><span class="t">${d.t}</span><span class="d">${d.d}</span></button>`).join("")}</div>`,
    dicaUso: "", fonte: `Fontes: Portal da Transparência RO (contratos e pagamentos até ${DATA_PAG}) · SEGEP (folha de outubro) · Siconfi (RGF do 2º quadrimestre de 2026)`,
    dados: ["contratos-vencem", "veiculos-2026"], padrao: () => mostraProvas("Clique num dos pontos à esquerda para ver a prova de cada um.", DS.map(d => d.prova), {limite: 6})});
  $("#decs").querySelectorAll(".dec").forEach(b => b.onclick = () => {
    $("#decs").querySelectorAll(".dec").forEach(x => x.classList.toggle("sel", x === b));
    const d = DS[+b.dataset.i];
    mostraProvas(d.t, [d.prova], {filtro: d.q, abrir: 0, limpar: () => { $("#decs").querySelectorAll(".dec").forEach(x => x.classList.remove("sel")); mostraProvas("Clique num dos pontos à esquerda para ver a prova de cada um.", DS.map(d => d.prova), {limite: 6}); }});
  });
}

// ---------- 1. folha
let folhaVer = 0;
function telaFolha() {
  const t = F.total, ap = F.aposentadoria, h = G.historico, h0 = h[0], hN = h.at(-1);
  esq({kicker: "Folha de pagamento · Poder Executivo", titulo: "Quanto o Estado paga de pessoal por ano",
    n: mi(G.bruta), s: `em 12 meses, pelo RGF (${G.periodo})<br>Outubro: <b>${mi(t.bruto)}</b> para <b>${br(t.matriculas)}</b> matrículas`,
    provaN: provaRgf("Despesa bruta com pessoal", G.bruta, "Anexo 1, linha DESPESA BRUTA COM PESSOAL (I), coluna Total dos últimos 12 meses",
      [["Inclui", "ativos, aposentados, pensionistas, contribuição patronal e terceirização que conta como pessoal"], ["Outubro de 2026 (SEGEP)", mi(t.bruto) + " brutos, sem encargos"]]),
    estat: [["Salários dos ativos", mi(G.vencimentos), provaRgf("Salários dos ativos", G.vencimentos, "Anexo 1, Vencimentos, Vantagens e Outras Despesas Variáveis")],
      ["Contribuição patronal", mi(G.patronais), provaRgf("Contribuição patronal", G.patronais, "Anexo 1, Obrigações Patronais")],
      ["Aposentadorias e pensões", mi(G.inativos), provaRgf("Aposentadorias e pensões", G.inativos, "Anexo 1, Pessoal Inativo e Pensionistas")],
      ["% da receita (limite 49%)", br(hN.pct_rcl, 2) + "%", provaRgf("Despesa total com pessoal / RCL", hN.dtp, "Anexo 1, DTP (VI) % sobre a RCL Ajustada", [["Percentual", br(hN.pct_rcl, 2) + "%"], ["Alerta / prudencial / máximo", "44,1% / 46,55% / 49%"], ["Lei", "LRF, arts. 19, 20, 22 e 59"]])]],
    alterna: ["Ver:", ["Quem está na folha", "Limite da lei", "2023 a 2026", "Pessoas"], folhaVer, i => { folhaVer = i; telaFolha(); }],
    dicaUso: ["Bruto de outubro por vínculo. Clique numa barra: em que órgãos estão.",
      `Pessoal sobre a receita, a conta da LRF. Faltam ${br(G.limites.alerta - hN.pct_rcl, 2)} pontos (${mi(margemAlerta)} por ano) até o alerta.`,
      `Pessoal em 12 meses, a cada quadrimestre: de ${mi(h0.dtp)} para ${mi(hN.dtp)} (${var_(h0.dtp, hN.dtp)}). Em cima, o % da receita. Clique numa coluna.`,
      "Pessoas na folha de outubro, por vínculo. Clique numa barra: em que órgãos estão."][folhaVer],
    fonte: "Fonte: Siconfi, RGF do Executivo (Anexo 1), 2023 a 2026 · SEGEP, folha de outubro de 2026 (matrícula criptografada)", dados: ["rgf", "servidores-orgao"], padrao: provasFolha});
  if (folhaVer === 1) medidorLrf();
  else if (folhaVer === 2) colunas($("#graf"), h.map(x => ({rot: `${x.quadrimestre}º/${String(x.ano).slice(2)}`, partes: [{v: x.dtp, cor: x === hN ? "var(--c1)" : claro("var(--c1)")}], topo: br(x.pct_rcl, 1) + "%", destaque: x === hN,
    dica: [`${x.quadrimestre}º quadrimestre de ${x.ano}`, [["Despesa total com pessoal (12 meses)", mi(x.dtp)], ["% da receita", br(x.pct_rcl, 2) + "%"], ["Receita corrente líquida ajustada", mi(x.rcl_ajustada)]], "RGF do Executivo, Siconfi"],
    clique: () => mostraProvas("RGF do quadrimestre", [provaRgf(`Despesa total com pessoal · ${x.quadrimestre}º quadrimestre de ${x.ano}`, x.dtp, "Anexo 1, DTP (VI)", [["% da receita", br(x.pct_rcl, 2) + "%"], ["Despesa bruta", mi(x.bruta)]])], {abrir: 0, filtro: `${x.quadrimestre}º/${x.ano}`, limpar: provasFolha})})));
  else {
    const G2 = F.grupos.filter(x => x.pessoas), pes = folhaVer === 3;
    barras($("#graf"), G2.map(x => ({rot: x.nome.replace(" e comissionados de outros entes", ""), partes: [{v: pes ? x.pessoas : x.bruto, cor: COR_GRUPO[x.grupo]}], dir: pes ? br(x.pessoas) : mi(x.bruto), destaque: x.grupo === "comissionado",
      dica: [x.nome, [["Pessoas", br(x.pessoas)], ["Bruto de outubro", mi(x.bruto)], ["Média por pessoa", "R$ " + br(x.bruto / x.pessoas)], ["Ocupam CDS", br(x.com_cds)]], "Clique para ver os órgãos"],
      clique: (gr, s) => { foco(s, gr); provasVinculo(x, () => { foco(s, null); provasFolha(); }); }})));
  }
}
function medidorLrf() {
  const cont = $("#graf"); cont.innerHTML = "";
  const w = cont.clientWidth || 600, h = 220, hN = G.historico.at(-1), L = G.limites, max = 60;
  const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", `0 0 ${w} ${h}`); s.style.width = "100%"; s.style.height = h + "px"; cont.append(s);
  const x = v => 10 + (w - 20) * v / max, y0 = 60, bh = 46;
  el(s, "rect", {x: x(0), y: y0, width: x(max) - x(0), height: bh, rx: 8, fill: "var(--hair)"});
  el(s, "rect", {x: x(L.alerta), y: y0, width: x(L.prudencial) - x(L.alerta), height: bh, fill: "color-mix(in srgb, var(--c3) 35%, transparent)"});
  el(s, "rect", {x: x(L.prudencial), y: y0, width: x(L.maximo) - x(L.prudencial), height: bh, fill: "color-mix(in srgb, #c0392b 35%, transparent)"});
  el(s, "rect", {x: x(L.maximo), y: y0, width: x(max) - x(L.maximo), height: bh, fill: "color-mix(in srgb, #c0392b 60%, transparent)"});
  const r = el(s, "rect", {class: "b", x: x(0), y: y0 + 8, width: 0, height: bh - 16, rx: 5, fill: "var(--c1)"}); alarga(r, x(hN.pct_rcl) - x(0), 0);
  // limites: alerta e máximo acima da barra (um alinhado à direita, outro à esquerda); prudencial abaixo
  [["alerta", L.alerta, y0 - 14, "end"], ["prudencial", L.prudencial, y0 + bh + 26, "middle"], ["máximo", L.maximo, y0 - 14, "start"]].forEach(([n, v, ty, anc]) => {
    el(s, "line", {x1: x(v), x2: x(v), y1: y0 - 8, y2: y0 + bh + 8, stroke: "var(--ink)", "stroke-width": 1.5});
    el(s, "text", {x: x(v) + (anc === "end" ? -4 : anc === "start" ? 4 : 0), y: ty, "text-anchor": anc, class: "mute"}, `${n} ${br(v, 2)}%`);
  });
  el(s, "text", {x: x(hN.pct_rcl), y: y0 + bh + 26, "text-anchor": "middle", class: "forte azul"}, `hoje ${br(hN.pct_rcl, 2)}%`);
  const hs = G.historico.map(q => q.pct_rcl);
  el(s, "text", {x: x(0), y: y0 + bh + 62, class: "mute"}, `Desde 2023 a folha ficou entre ${br(Math.min(...hs), 2)}% e ${br(Math.max(...hs), 2)}% da receita, a cada quadrimestre.`);
}
function provasFolha() {
  const ap = F.aposentadoria, t = F.total;
  const itens = [["Salários dos ativos", G.vencimentos, "Vencimentos, Vantagens e Outras Despesas Variáveis"], ["Contribuição patronal", G.patronais, "Obrigações Patronais"],
    ["Aposentadorias e reformas", G.aposentadorias, "Aposentadorias, Reserva e Reformas"], ["Pensões", G.pensoes, "Pensões"], ["Terceirização que conta como pessoal", G.terceirizacao, "art. 18, § 1º, da LRF"]];
  const lista = itens.map(([n, v, conta]) => ({...provaRgf(n, v, "Anexo 1, " + conta), sub: `${br(100 * v / G.bruta, 1)}% do total do ano`, barra: v / G.bruta}));
  lista.push(pr("Afastados aguardando aposentadoria", mi(ap.bruto_mes) + "/mês", `${br(ap.pessoas)} servidores fora da função enquanto o processo anda`,
    [["Servidores", br(ap.pessoas)], ["Por ano (13 salários)", mi(ap.bruto_mes * 13)], ...["até 6 meses", "7 a 12 meses", "1 a 2 anos", "mais de 2 anos"].map(k => ["Esperando há " + k, br(ap.tempo[k] || 0)])], LK.pessoal));
  lista.push(pr("Cargos em comissão (CDS)", mi(t.custo_cds) + "/mês", `${br(t.com_cds)} pessoas · verbas de representação, vencimento e indenização de CDS`,
    F.cds.map(c => [c.simbolo === "sem símbolo" ? "Sem símbolo" : c.simbolo, `${br(c.pessoas)} pessoas · ${mi(c.custo_cds)}/mês`]), LK.pessoal));
  mostraProvas("A conta do ano pelo RGF, os afastados que aguardam aposentadoria e os cargos em comissão. Clique para abrir; o link leva à fonte.", lista);
}
function provasVinculo(x, limpar) {
  const us = M.unidades.filter(u => u.grupos[x.grupo]).sort((a, b) => b.grupos[x.grupo].pessoas - a.grupos[x.grupo].pessoas);
  const max = us[0]?.grupos[x.grupo].pessoas || 1;
  const lista = us.map(u => ({nome: u.unidade === "SEM UNIDADE" ? "Sem unidade na planilha" : u.unidade, sub: u.nome, valor: br(u.grupos[x.grupo].pessoas), barra: u.grupos[x.grupo].pessoas / max,
    linhas: [["Pessoas", br(u.grupos[x.grupo].pessoas)], ["Bruto de outubro", mi(u.grupos[x.grupo].bruto)]], link: LK.pessoal}));
  mostraProvas(`${x.nome}: em que órgãos estão, do maior para o menor.`, lista, {filtro: x.nome, limpar, todas: lista, tituloTodas: x.nome, limite: 6});
}

// ---------- 2. servidores por órgão
let orgOrdem = 0;
const pctCom = u => u.pessoas ? 100 * (u.grupos.comissionado?.pessoas || 0) / u.pessoas : 0;
function telaOrgaos() {
  const t = F.total, gp = k => F.grupos.find(x => x.grupo === k);
  const provaGrupo = k => { const g = gp(k); return pr(g.nome, br(g.pessoas), "folha de outubro de 2026, classificação funcional da SEGEP", [["Bruto de outubro", mi(g.bruto)], ["Média por pessoa", "R$ " + br(g.bruto / g.pessoas)], ["Ocupam CDS", br(g.com_cds)], ["Afastados", br(g.afastados)]], LK.pessoal); };
  const maisCom = M.unidades.filter(u => u.pessoas >= 20 && (u.grupos.comissionado?.pessoas || 0) > ((u.grupos.efetivo?.pessoas || 0) + (u.grupos.militar?.pessoas || 0)));
  esq({kicker: "Servidores · folha de outubro de 2026", titulo: "Quantos servidores cada secretaria tem",
    n: br(t.ativos), s: `servidores ativos em <b>${M.unidades.length - 1} órgãos</b> · ${mi(t.bruto_ativos)} no mês<br><b>${br(maisCom.length)} órgãos</b> têm mais comissionados que servidores de carreira`,
    provaN: pr("Servidores ativos", br(t.ativos), "uma pessoa por matrícula; aposentados e pensionistas fora", [["Matrículas na folha", br(t.matriculas)], ["Aposentados e pensionistas", br(t.inativos)], ["Afastados (entre os ativos)", br(t.afastados)], ["Sem unidade na planilha", br(t.sem_unidade)],
      ["Conferência", "O estudo de 10/11 (lista pública do Portal, regra pelo cargo) contou 49.023 ativos; a diferença são estagiários, voluntários, cedidos e pagamentos judiciais"]], LK.pessoal),
    estat: [["Efetivos civis", br(gp("efetivo").pessoas), provaGrupo("efetivo")], ["Militares", br(gp("militar").pessoas), provaGrupo("militar")], ["Temporários e CLT", br(gp("temporario").pessoas), provaGrupo("temporario")], ["Comissionados sem vínculo", br(gp("comissionado").pessoas), provaGrupo("comissionado")]],
    alterna: ["Ordenar por:", ["Pessoas", "Valor do mês", "% de comissionados"], orgOrdem, i => { orgOrdem = i; telaOrgaos(); }],
    legenda: legenda(GRUPOS.slice(0, 6).map(g => [g.nome.replace(" e comissionados de outros entes", ""), COR_GRUPO[g.grupo]])),
    dicaUso: orgOrdem === 2 ? "Comissionados sem vínculo no quadro de cada órgão (20 servidores ou mais). Clique num órgão." : "Os maiores órgãos, por vínculo. Clique num órgão; todos estão em As provas.",
    fonte: "Fonte: SEGEP, Relação de Servidores Ativos e Afastados, outubro de 2026 (versão com unidade e departamento)", dados: ["servidores-orgao"], padrao: () => provasOrgaos(ordenaU())});
  const U = ordenaU();
  if (orgOrdem === 2) barras($("#graf"), U.slice(0, 18).map((u, i) => ({rot: u.unidade, partes: [{v: pctCom(u), cor: "var(--c3)"}], dir: `${br(pctCom(u), 0)}% · ${br(u.grupos.comissionado?.pessoas || 0)} de ${br(u.pessoas)}`,
    dica: [u.nome || u.unidade, [["Comissionados sem vínculo", br(u.grupos.comissionado?.pessoas || 0)], ["Servidores", br(u.pessoas)]], "Clique para abrir"], clique: (g, s) => { foco(s, g); provasOrgaos(U, i, () => { foco(s, null); provasOrgaos(U); }); }})));
  else {
    const campo = orgOrdem ? "bruto" : "pessoas";
    barras($("#graf"), U.slice(0, 18).map((u, i) => ({rot: u.unidade === "SEM UNIDADE" ? "Sem unidade" : u.unidade,
      partes: GRUPOS.map(g => ({v: u.grupos[g.grupo]?.[campo] || 0, cor: COR_GRUPO[g.grupo]})), dir: orgOrdem ? mi(u.bruto) : br(u.pessoas),
      dica: [u.nome || u.unidade, [["Servidores", br(u.pessoas)], ["Bruto de outubro", mi(u.bruto)], ["Ocupam CDS", br(u.com_cds)]], "Clique para abrir"],
      clique: (g, s) => { foco(s, g); provasOrgaos(U, i, () => { foco(s, null); provasOrgaos(U); }); }})));
  }
}
const ordenaU = () => orgOrdem === 2 ? M.unidades.filter(u => u.pessoas >= 20 && u.unidade !== "SEM UNIDADE").sort((a, b) => pctCom(b) - pctCom(a))
  : [...M.unidades].sort((a, b) => b[orgOrdem ? "bruto" : "pessoas"] - a[orgOrdem ? "bruto" : "pessoas"]);
function provaOrgao(u, max) {
  const campo = orgOrdem === 1 ? "bruto" : "pessoas";
  return {nome: u.unidade === "SEM UNIDADE" ? "Sem unidade na planilha" : u.unidade, sub: u.nome, valor: orgOrdem === 2 ? br(pctCom(u), 0) + "%" : campo === "bruto" ? mi(u.bruto) : br(u.pessoas),
    barra: orgOrdem === 2 ? pctCom(u) / 100 : u[campo] / max,
    linhas: [["Servidores ativos", br(u.pessoas)], ["Bruto de outubro", mi(u.bruto)], ["Por ano (× 13⅓)", mi(u.bruto * 13.33)], ["Ocupam CDS", `${br(u.com_cds)} · ${mi(u.custo_cds)}/mês`], ["Comissionados sem vínculo", `${br(u.grupos.comissionado?.pessoas || 0)} (${br(pctCom(u), 0)}%)`], ["Afastados", br(u.afastados)],
      ...GRUPOS.filter(g => u.grupos[g.grupo] && g.grupo !== "comissionado").map(g => [g.nome, br(u.grupos[g.grupo].pessoas)]),
      ...u.departamentos.slice(0, 6).map(d => ["Lotação " + d.nome, br(d.pessoas)])], link: LK.pessoal};
}
function provasOrgaos(U, i, limpar) {
  const max = U[0][orgOrdem === 1 ? "bruto" : "pessoas"], lista = U.map(u => provaOrgao(u, max));
  if (i == null) mostraProvas("Todos os órgãos. Clique para ver vínculos, cargos em comissão e onde trabalham.", lista, {todas: lista, tituloTodas: "Servidores por órgão", limite: 6});
  else mostraProvas(`${U[i].nome || U[i].unidade}`, [lista[i]], {filtro: U[i].unidade, limpar, abrir: 0});
}

// ---------- 3 e 4. pagamentos (veículos e imóveis), agregados aqui a partir das linhas
const mesDe = d => +String(d).slice(3, 5);
function agrupa(ls, chave) {
  const m = new Map();
  ls.forEach(r => { const k = chave(r); if (!m.has(k)) m.set(k, {k, total: 0, ls: []}); const x = m.get(k); x.total += r[8]; x.ls.push(r); });
  return [...m.values()].sort((a, b) => b.total - a.total);
}
function credoresDe(ls) {
  return agrupa(ls, r => r[2]).map(c => notaPag(c.k === "Pessoa física" ? `Pessoas físicas (sem nome)` : c.k, c.total,
    `${[...new Set(c.ls.map(r => r[4]))].join(", ")} · ${br(c.ls.length)} pagamentos · ${[...new Set(c.ls.map(r => r[1]))].slice(0, 5).join(", ")}`, c.ls[0][3]));
}
const provaTema = (k, extra = []) => {
  const c = C[k];
  return pr(c.nome + " em 2026", mi(c.ano_2026), `pago até ${DATA_PAG} mais projeção até dezembro, só Poder Executivo`,
    [["Pago de 1º/01 a " + DATA_PAG, "R$ " + br(c.pago_2026, 2)], ["Projeção (nov e dez)", mi(c.projecao_2026)], ["Média mensal ago–out", mi(c.media_ago_out)], ["2025, o ano inteiro", mi(c.anos["2025"])],
      ...c.subelementos.map(x => [`Subelemento ${x.cod}`, `${x.nome}: ${mi(x.valor)}`]), ...extra], LK.pag);
};

let veicTema = 0, veicPor = 0;
const TEMAS_V = ["Combustível", "Transporte escolar", "Locação de veículos", "Ambulâncias", "Manutenção de veículos"];
function telaVeiculos() {
  const temas = veicTema ? [TEMAS_V[veicTema - 1]] : TEMAS_V, ks = temas.map(t => CHAVE_TEMA[t]);
  const ano = ks.reduce((a, k) => a + C[k].ano_2026, 0), pago = ks.reduce((a, k) => a + C[k].pago_2026, 0), a25 = ks.reduce((a, k) => a + C[k].anos["2025"], 0);
  const cartao = pagoA(/PRIME CONSULT|UZZIPAY|LINK CARD|NEO CONSULT/i);
  const ls = PV.filter(r => temas.includes(r[4]));
  esq({kicker: "Veículos do Estado · Poder Executivo", titulo: "Quanto o Estado gasta com veículos",
    n: mi(ano), s: `${veicTema ? temas[0].toLowerCase() + " em 2026" : "em 2026"} · <b>${mi(pago)}</b> pagos até ${DATA_PAG.slice(0, 5)}<br>2025 inteiro: <b>${mi(a25)}</b>`,
    provaN: pr("Veículos em 2026", mi(ano), `soma de ${temas.join(", ").toLowerCase()}`, [["Pago até " + DATA_PAG, "R$ " + br(pago, 2)], ["Projeção nov e dez", mi(ano - pago)], ["Pagamentos", br(ls.length)],
      ["Transporte escolar", "entra: transporte de alunos contratado pela SEDUC (3.3.90.39.93)"], ["Ambulâncias", "entram: remoção de pacientes contratada pela SESAU (3.3.90.39.61)"],
      ["Fora da conta", "aviões, helicópteros e UTI aérea, e os outros Poderes (Assembleia, Judiciário, MP, TCE e Defensoria)"]], LK.pag),
    estat: [...TEMAS_V.map(t => [CURTO[t], mi(C[CHAVE_TEMA[t]].ano_2026), provaTema(CHAVE_TEMA[t])])],
    alterna: ["Mostrar:", ["Tudo", ...TEMAS_V.map(t => CURTO[t])], veicTema, i => { veicTema = i; telaVeiculos(); }],
    legenda: legenda(temas.map(t => [t, COR_TEMA[t]]).concat([["projeção (nov e dez)", "var(--hair)"]])),
    dicaUso: `Pago por mês. Nov e dez em tom claro: projeção pela média de ago a out. Clique num mês ou num tipo acima.`,
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores, 01/01 a ${DATA_PAG}, pelo subelemento da despesa`, dados: ["veiculos-2026", "contratos-vencem"], padrao: () => provasPag(ls)});
  colunas($("#graf"), MESES.map((m, i) => ({rot: m, partes: temas.flatMap(t => {
      const k = CHAVE_TEMA[t], pg = C[k].pago_mensal_2026[i], tot = C[k].mensal_2026[i];
      return [{v: pg, cor: COR_TEMA[t]}, {v: Math.max(tot - pg, 0), cor: claro(COR_TEMA[t])}]; }),
    topo: mi(temas.reduce((a, t) => a + C[CHAVE_TEMA[t]].mensal_2026[i], 0)), destaque: i + 1 === MES_PAG,
    dica: [`${MESES_L[i]} de 2026`, temas.map(t => [t, mi(C[CHAVE_TEMA[t]].pago_mensal_2026[i])]).concat(i + 1 >= MES_PAG ? [["Projeção", mi(temas.reduce((a, t) => a + C[CHAVE_TEMA[t]].mensal_2026[i] - C[CHAVE_TEMA[t]].pago_mensal_2026[i], 0))]] : []), "Clique para ver quem gastou no mês"],
    clique: (g, s) => { foco(s, g); provasPag(ls.filter(r => mesDe(r[0]) === i + 1), `Pagos em ${MESES_L[i]}`, () => { foco(s, null); provasPag(ls); }); }})));
}
function provasPag(ls, filtro, limpar, imovel, tituloTodas) {
  const porOrgao = !(imovel ? imovPor : veicPor);
  const gs = agrupa(ls, r => porOrgao ? r[1] : r[2]), max = gs[0]?.total || 1;
  const lista = gs.map(x => {
    const temas = agrupa(x.ls, r => r[4]);
    return {nome: porOrgao ? x.k : (x.k === "Pessoa física" ? "Pessoas físicas (sem nome)" : x.k), sub: porOrgao ? (D.nomes[x.k] || "") : [...new Set(x.ls.map(r => r[1]))].slice(0, 6).join(", "),
      valor: mi(x.total), barra: x.total / max,
      linhas: [["Pago", "R$ " + br(x.total, 2)], ["Pagamentos", br(x.ls.length)], ...(!porOrgao && x.ls[0][3] ? [["CNPJ", x.ls[0][3]]] : []),
        ...(imovel && porOrgao ? [["Imóveis (locadores)", br(new Set(x.ls.map(r => r[2] === "Pessoa física" ? "pf" + r[6] : r[2])).size)]] : []),
        ...temas.map(t => [t.k, mi(t.total)]), ["Como conferir", "Pagamentos de fornecedores: escolha o período e busque pelo credor ou pela nota de empenho"]],
      notas: porOrgao ? credoresDe(x.ls).slice(0, 10) : agrupa(x.ls, r => r[1]).slice(0, 10).map(o => notaPag(o.k + (D.nomes[o.k] ? " · " + D.nomes[o.k] : ""), o.total, `${br(o.ls.length)} pagamentos · notas ${[...new Set(o.ls.map(r => r[6]))].slice(0, 4).join(", ")}`, "")),
      link: LK.pag};
  });
  const txt = porOrgao ? "Órgãos que mais pagaram. Clique para abrir." : "Quem mais recebeu (pessoa física somada, sem nome).";
  $("#aviso").hidden = false;
  $("#aviso").innerHTML = `<div class="alterna" style="margin:0"><span class="rot">Provas por:</span>${["Órgão", imovel ? "Locador" : "Empresa"].map((t, i) => `<button type="button" class="${i === (imovel ? imovPor : veicPor) ? "on" : ""}">${t}</button>`).join("")}</div>`;
  $("#aviso").querySelectorAll("button").forEach((b, i) => b.onclick = () => { if (imovel) imovPor = i; else veicPor = i; provasPag(ls, filtro, limpar, imovel, tituloTodas); });
  mostraProvas(filtro ? `${filtro}. ${txt}` : txt, lista, {filtro, limpar, todas: lista, tituloTodas: tituloTodas || (imovel ? "Aluguel de imóveis em 2026" : "Veículos em 2026"), limite: 6});
}

let imovPor = 0;
function telaImoveis() {
  const c = C.imovel, i = M.imoveis;
  const gs = agrupa(PI, r => r[1]);
  esq({kicker: "Imóveis alugados · Poder Executivo", titulo: "Quanto o Estado gasta com aluguel",
    n: mi(c.ano_2026), s: `em 2026 · <b>${br(i.locadores)} imóveis</b> em <b>${br(i.orgaos_total)} órgãos</b><br>2025 inteiro: <b>${mi(c.anos["2025"])}</b> (${br(i.locadores_2025)} imóveis)`,
    provaN: provaTema("imovel"),
    estat: [["Imóveis alugados", br(i.locadores), pr("Imóveis alugados em 2026", br(i.locadores), "locadores diferentes pagos, órgão a órgão", [["Regra", "cada locador (CPF ou CNPJ) pago por um órgão conta um imóvel; quem aluga dois ao mesmo órgão conta um, então o número é piso"], ["Em 2025", br(i.locadores_2025)]], LK.pag)],
      ["De pessoas físicas", `${br(i.pf)} · ${mi(i.pf_valor)}`, pr("Aluguel pago a pessoas físicas", mi(i.pf_valor), `${br(i.pf)} imóveis`, [["Subelemento", "3.3.90.36.15 · locação de imóveis (pessoa física)"], ["Nomes", "não aparecem no painel; estão no portal"]], LK.pag)],
      ["De empresas", `${br(i.pj)} · ${mi(i.pj_valor)}`, pr("Aluguel pago a empresas", mi(i.pj_valor), `${br(i.pj)} imóveis`, [["Subelemento", "3.3.90.39.10 · locação de imóveis (pessoa jurídica)"]], LK.pag)],
      ["Contratos que vencem até 2027", br(VENCE27.filter(x => x.tipo === "imovel").length), pr("Contratos de aluguel que vencem até 31/12/2027", mi(VENCE27.filter(x => x.tipo === "imovel").reduce((a, x) => a + x.valor, 0)), "valor contratado, vigência publicada no portal", [], LK.contratos, VENCE27.filter(x => x.tipo === "imovel").map(notaContrato))]],
    dicaUso: "Pago em 2026 por órgão. Clique num órgão: quem são os locadores.",
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores, 01/01 a ${DATA_PAG}, subelementos de locação de imóveis`, dados: ["imoveis-2026", "contratos-vencem"], padrao: () => { imovPor = 0; provasPag(PI, null, null, true); }});
  barras($("#graf"), gs.slice(0, 16).map(g => {
    const n = new Set(g.ls.map(r => r[2] === "Pessoa física" ? "pf" + r[6] : r[2])).size;
    return {rot: g.k, partes: [{v: g.total, cor: "var(--c4)"}], dir: `${mi(g.total)} · ${br(n)} imóve${n > 1 ? "is" : "l"}`,
      dica: [D.nomes[g.k] || g.k, [["Pago em 2026", mi(g.total)], ["Imóveis (locadores)", br(n)]], "Clique para ver os locadores"],
      clique: (el_, s) => { foco(s, el_); imovPor = 1; provasPag(g.ls, `Aluguel pago pelo ${g.k}`, () => { foco(s, null); imovPor = 0; provasPag(PI, null, null, true); }, true); }};
  }));
}

// ---------- contas de consumo, serviços de apoio e viagens
const PCs = D.tabelas["consumo-2026"].linhas;
const FAM = [["Contas", ["energia", "agua", "telecom", "correios"], "var(--c3)"], ["Apoio", ["vigilancia", "limpeza", "predial", "maoobra"], "var(--c1)"], ["Viagens", ["diarias", "passagens"], "var(--c4)"]];
const COR_CONS = {energia: "var(--c3)", agua: "var(--c6)", telecom: "var(--c4)", correios: "var(--c5)", vigilancia: "var(--c1)", limpeza: "var(--c2)", predial: "var(--c3)", maoobra: "var(--c5)", diarias: "var(--c4)", passagens: "var(--c7)"};
const somaK = (ks, campo) => ks.reduce((a, k) => a + (campo === "2025" ? C[k].anos["2025"] : C[k][campo]), 0);
let consFam = 0;
function telaConsumo() {
  const f = consFam ? FAM[consFam - 1] : null, ks = f ? f[1] : FAM.flatMap(x => x[1]);
  const series = f ? f[1].map(k => [C[k].nome, [k], COR_CONS[k]]) : FAM.map(([n, k, c]) => [n, k, c]);
  const ano = somaK(ks, "ano_2026"), pago = somaK(ks, "pago_2026"), a25 = somaK(ks, "2025");
  const nomes = new Set(ks.map(k => C[k].nome)), ls = PCs.filter(r => nomes.has(r[4]));
  const provaFam = ([n, k]) => pr(`${n} em 2026`, mi(somaK(k, "ano_2026")), `pago até ${DATA_PAG} mais projeção até dezembro, só Executivo`,
    [["Pago até " + DATA_PAG, mi(somaK(k, "pago_2026"))], ["2025, o ano inteiro", mi(somaK(k, "2025"))], ...k.map(x => [C[x].nome, `${mi(C[x].ano_2026)} · subelemento ${C[x].subelementos.map(s => s.cod).join(", ")}`])], LK.pag);
  esq({kicker: "Contas, serviços de apoio e viagens · Poder Executivo", titulo: f ? `${f[0]}: quanto custam` : "Quanto custa manter a máquina",
    n: mi(ano), s: `em 2026 · <b>${mi(pago)}</b> pagos até ${DATA_PAG.slice(0, 5)}<br>2025 inteiro: <b>${mi(a25)}</b>`,
    provaN: pr("Contas, apoio e viagens em 2026", mi(ano), "pago até " + DATA_PAG + " mais projeção", [["Pago até " + DATA_PAG, mi(pago)], ["Projeção nov e dez", mi(ano - pago)], ["Pagamentos", br(ls.length)],
      ["Fora da conta", "remédio, serviço hospitalar, alimentação de presos e pacientes, repasses a municípios (são a política pública); estatais (CAERD e SOPH); outros Poderes"]], LK.pag),
    estat: f ? f[1].map(k => [C[k].nome, mi(C[k].ano_2026), provaTema(k)]) : FAM.map(x => [`${x[0]} <small class="sub-estat">${x[1].map(k => C[k].nome.toLowerCase()).join(", ")}</small>`, mi(somaK(x[1], "ano_2026")), provaFam(x)]),
    alterna: ["Mostrar:", ["Tudo", ...FAM.map(x => x[0])], consFam, i => { consFam = i; telaConsumo(); }],
    legenda: legenda(series.map(([n, , c]) => [n, c]).concat([["projeção", "var(--hair)"]])),
    dicaUso: "Pago por mês. Nov e dez em tom claro: projeção. Clique num mês ou num tipo acima.",
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores, 01/01 a ${DATA_PAG}, pelo subelemento da despesa`, dados: ["consumo-2026"], padrao: () => provasPag(ls, null, null, false, "Contas, apoio e viagens em 2026")});
  colunas($("#graf"), MESES.map((m, i) => ({rot: m, partes: series.flatMap(([, k, c]) => {
      const pg = k.reduce((a, x) => a + C[x].pago_mensal_2026[i], 0), tot = k.reduce((a, x) => a + C[x].mensal_2026[i], 0);
      return [{v: pg, cor: c}, {v: Math.max(tot - pg, 0), cor: claro(c)}]; }),
    topo: mi(ks.reduce((a, k) => a + C[k].mensal_2026[i], 0)), destaque: i + 1 === MES_PAG,
    dica: [`${MESES_L[i]} de 2026`, series.map(([n, k]) => [n, mi(k.reduce((a, x) => a + C[x].pago_mensal_2026[i], 0))]), "Clique para ver quem pagou no mês"],
    clique: (g, s_) => { foco(s_, g); provasPag(ls.filter(r => mesDe(r[0]) === i + 1), `Pagos em ${MESES_L[i]}`, () => { foco(s_, null); provasPag(ls, null, null, false, "Contas, apoio e viagens em 2026"); }, false, "Contas, apoio e viagens em 2026"); }})));
}

// ---------- custo de cada secretaria
const SEC = M.secretarias, PARTES_SEC = [["Folha (estimada)", "folha_ano", "var(--c1)"], ["Veículos", "veiculos", "var(--c2)"], ["Aluguel", "imoveis", "var(--c4)"], ["Contas", "contas", "var(--c3)"], ["Apoio", "apoio", "var(--c6)"], ["Viagens", "viagens", "var(--c7)"]];
let secVer = 0;
const valSec = (x, c) => secVer === 2 ? (x.pessoas ? x[c] / x.pessoas : 0) : x[c];
function provaSec(x, max) {
  const totalV = secVer === 1 ? x.custeio : x.total;
  return {nome: x.sigla, sub: x.nome || "", valor: secVer === 2 ? (x.pessoas ? "R$ " + br(x.custeio / x.pessoas) : "—") : mi(totalV), barra: (secVer === 2 ? (x.pessoas ? x.custeio / x.pessoas : 0) : totalV) / max,
    linhas: [["Servidores ativos (outubro)", br(x.pessoas)], ["Folha bruta de outubro", mi(x.folha_mes)], ["Folha do ano (× 13⅓, sem encargos)", mi(x.folha_ano)],
      ...PARTES_SEC.slice(1).filter(([, c]) => x[c]).map(([n, c]) => [n + " em 2026", mi(x[c])]),
      ...Object.entries(x.temas).map(([k, v]) => ["· " + C[k].nome, mi(v)]),
      ["Custeio da máquina em 2026", mi(x.custeio)], ...(x.pessoas ? [["Custeio por servidor", "R$ " + br(x.custeio / x.pessoas)]] : []),
      ...(x.unidades.length ? [["Inclui a folha de", x.unidades.join(", ")]] : []), ...(x.pagadoras.length ? [["Inclui os pagamentos de", x.pagadoras.join(", ")]] : [])], link: LK.pag};
}
function provasSec(lista, i, limpar) {
  const ord = ordenaSec(), max = Math.max(...ord.map(x => secVer === 2 ? (x.pessoas ? x.custeio / x.pessoas : 0) : secVer === 1 ? x.custeio : x.total), 1), L_ = ord.map(x => provaSec(x, max));
  if (i == null) mostraProvas("Todos os órgãos. Clique para abrir a conta completa de cada um.", L_, {todas: L_, tituloTodas: "Custo por secretaria em 2026", limite: 6});
  else mostraProvas(ord[i].nome || ord[i].sigla, [L_[i]], {filtro: ord[i].sigla, limpar, abrir: 0});
}
const ordenaSec = () => secVer === 2 ? SEC.filter(x => x.pessoas >= 100).sort((a, b) => b.custeio / b.pessoas - a.custeio / a.pessoas)
  : [...SEC].sort((a, b) => (secVer ? b.custeio - a.custeio : b.total - a.total));
function telaSecretarias() {
  const tot = SEC.reduce((a, x) => a + x.total, 0), cus = SEC.reduce((a, x) => a + x.custeio, 0), fol = SEC.reduce((a, x) => a + x.folha_ano, 0);
  const soma = c => SEC.reduce((a, x) => a + x[c], 0);
  const provaParte = ([n, c]) => pr(`${n} · todos os órgãos`, mi(soma(c)), c === "folha_ano" ? "folha bruta de outubro × 13⅓, sem encargos" : "pago em 2026 e projeção até dezembro",
    SEC.filter(x => x[c]).sort((a, b) => b[c] - a[c]).slice(0, 12).map(x => [x.sigla, mi(x[c])]), c === "folha_ano" ? LK.pessoal : LK.pag);
  const ord = ordenaSec(), partes = secVer ? PARTES_SEC.slice(1) : PARTES_SEC;
  esq({kicker: "Custo de cada secretaria · 2026", titulo: "Quanto custa cada secretaria",
    n: mi(secVer ? cus : tot), s: secVer ? `de custeio da máquina em 2026, sem a folha<br>${br(SEC.length)} órgãos do Executivo` : `em 2026: folha <b>${mi(fol)}</b> + custeio <b>${mi(cus)}</b><br>${br(SEC.length)} órgãos do Executivo`,
    provaN: pr("Custo dos órgãos em 2026", mi(tot), "folha estimada mais custeio da máquina", [["Folha (outubro × 13⅓, sem encargos)", mi(fol)], ["Custeio (veículos, aluguel, contas, apoio e viagens)", mi(cus)],
      ["Fora", "encargos patronais, aposentados, servidores sem unidade na planilha, remédio, hospital contratado, obras, repasses"], ["Hospitais", "HB, João Paulo II, Cemetron, Policlínica, Lacen e outros somados à SESAU"]], LK.pessoal),
    estat: PARTES_SEC.map(p => [p[0].replace(" (estimada)", ""), mi(soma(p[1])), provaParte(p)]),
    alterna: ["Ver:", ["Custo total", "Só custeio", "Custeio por servidor"], secVer, i => { secVer = i; telaSecretarias(); }],
    legenda: legenda(partes.map(([n, , c]) => [n, c])),
    dicaUso: ["Folha mais custeio de 2026, os 18 maiores. Clique num órgão para a conta completa.", "Sem a folha: veículos, aluguel, contas, apoio e viagens. Clique num órgão.",
      "Custeio da máquina dividido pelos servidores do órgão (100 servidores ou mais). Clique num órgão."][secVer],
    fonte: `Fonte: SEGEP, folha de outubro de 2026 · Portal da Transparência RO, pagamentos até ${DATA_PAG}`, dados: ["servidores-orgao", "veiculos-2026", "imoveis-2026", "consumo-2026"], padrao: () => provasSec()});
  barras($("#graf"), ord.slice(0, 18).map((x, i) => ({rot: x.sigla, partes: partes.map(([, c, cor]) => ({v: valSec(x, c), cor})),
    dir: secVer === 2 ? "R$ " + br(x.custeio / x.pessoas) : mi(secVer ? x.custeio : x.total),
    dica: [x.nome || x.sigla, partes.filter(([, c]) => x[c]).map(([n, c]) => [n, mi(x[c])]), "Clique para a conta completa"],
    clique: (g, s_) => { foco(s_, g); provasSec(null, i, () => { foco(s_, null); provasSec(); }); }})));
}

// ---------- estradas: mapa 3D (satélite e relevo) com rodovias, pontes e repasses do DER
const E = M.estradas, ER = E.resumo, LK_DER = ["Geoportal do DER-RO (rodovias e pontes)", "https://geo.der.ro.gov.br/"];
const nmz = s => semAcento(s).replace(/D'? ?OESTE|DO OESTE/g, "DOESTE").replace(/[^A-Z]/g, "");
const km = v => br(v || 0, 0) + " km";
const COR_VIA = {pav: "#ffc94a", terra: "#ff7a33", plan: "#d9dde3"};
let estVer = 0, mapa3d = null, mapaEl = null, mapaPronto = false, mapa2d = false;
const VISTAS_E = ["Rodovias", "Pontes de madeira", "Repasses do DER"];
const munE = k => E.municipios[k];
function cartaoMun(k) {
  const x = munE(k); if (!x) return null;
  const pts = E.pontes.filter(p => p.m === k && p.madeira).sort((a, b) => b.ext - a.ext);
  return {nome: x.nome, sub: `${km(x.pav)} de asfalto · ${km(x.terra)} de terra${x.pontes_madeira ? ` · ${x.pontes_madeira} ponte${x.pontes_madeira > 1 ? "s" : ""} de madeira` : ""}`,
    valor: estVer === 2 ? mi(x.repasse) : km(x.pav + x.terra), k,
    linhas: [["Rodovia estadual com asfalto", km(x.pav)], ["Rodovia estadual de terra", km(x.terra)], ...(x.plan ? [["Interesse de incorporar (ainda não é do Estado)", km(x.plan)]] : []),
      ["Rodovias", x.rodovias.join(", ") || "nenhuma estadual"], ["Pontes de madeira", x.pontes_madeira ? `${x.pontes_madeira} · ${br(x.madeira_m, 0)} m` : "nenhuma"],
      ...pts.slice(0, 6).map(p => ["· " + p.n, `${p.rod} · ${br(p.ext, 1)} m`]),
      ["Repasses do DER à prefeitura em 2026", x.repasse ? `${mi(x.repasse)} · ${x.repasse_n} pagamentos` : "nenhum"],
      ...(x.pop ? [["População (Censo 2022)", br(x.pop)]] : []), ...(x.rr ? [["Residência do DER", `${x.rr}${E.residencias[x.rr]?.sede ? " · " + E.residencias[x.rr].sede : ""}`]] : [])], link: LK_DER};
}
const cartaoPonte = p => ({nome: p.n, sub: `${p.rod} · ${p.mun} · ${p.t}`, valor: br(p.ext, 1) + " m", ponte: p,
  linhas: [["Tipo", p.t], ["Rodovia", `${p.rod} (trecho ${p.sre})`], ["Rio", p.rio || "sem registro"], ["Município", p.mun], ["Residência do DER", p.rr], ["Extensão", br(p.ext, 1) + " m"],
    ["Coordenadas", `${p.lat}, ${p.lon}`]], link: LK_DER});
function listaE() {
  if (estVer === 1) return E.pontes.filter(p => p.madeira).sort((a, b) => b.ext - a.ext).map(cartaoPonte);
  const v = k => estVer === 2 ? munE(k).repasse : munE(k).pav + munE(k).terra;
  return Object.keys(E.municipios).filter(v).sort((a, b) => v(b) - v(a)).map(cartaoMun);
}
const TIT_LISTA = ["Municípios com mais rodovia estadual", "Pontes de madeira, das maiores para as menores", "O que o DER repassou a cada prefeitura em 2026"];
// cartão flutuante à direita do mapa: a lista da vista ou o detalhe do que foi clicado
function cartaoLista() {
  const L_ = listaE(), c = $("#est-card");
  c.innerHTML = `<div class="ec-cab"><b>${TIT_LISTA[estVer]}</b><span>${br(L_.length)} · clique para voar até lá</span></div>
    <div class="ec-lista">${L_.map((it, i) => `<button type="button" data-i="${i}"><span class="n">${i + 1}</span><span class="t">${esc(it.nome)}<small>${esc(it.sub)}</small></span><b>${esc(it.valor)}</b></button>`).join("")}</div>`;
  c.querySelectorAll("[data-i]").forEach(b => b.onclick = () => { const it = L_[+b.dataset.i]; voa(it); cartaoItem(it); });
}
function cartaoItem(it) {
  const c = $("#est-card");
  c.innerHTML = `<button type="button" class="ec-volta">← ${TIT_LISTA[estVer].split(",")[0]}</button>
    <div class="ec-item"><b>${esc(it.nome)}</b><span class="ec-v">${esc(it.valor || "")}</span><small>${esc(it.sub || "")}</small></div>
    <div class="ec-linhas">${(it.linhas || []).map(([k, v]) => `<div class="linha"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}</div>
    ${it.link ? `<a class="link-fonte" href="${it.link[1]}" target="_blank" rel="noopener">${esc(it.link[0])} ↗</a>` : ""}`;
  c.querySelector(".ec-volta").onclick = () => { voaEstado(); cartaoLista(); };
}
const mostraUm = it => cartaoItem(it);
function padMapa() {
  const r = mapaEl?.getBoundingClientRect(), n = $(".est-nums")?.getBoundingClientRect(), c = $("#est-card")?.getBoundingClientRect(), t = $(".est-topo")?.getBoundingClientRect();
  if (!r || innerWidth < 760) return 30;
  const z = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--z")) || 1;
  return {left: n ? (n.right - r.left) / z + 20 : 30, right: c ? (r.right - c.left) / z + 20 : 30, top: t ? (t.bottom - r.top) / z + 10 : 60, bottom: 50};
}
function voa(item) {
  if (!item) return;
  if (mapa3d && mapaPronto) {
    const pd = padMapa(), off = typeof pd === "object" ? [(pd.left - pd.right) / 2, (pd.top - pd.bottom) / 2] : [0, 0];
    if (item.ponte) mapa3d.flyTo({center: [item.ponte.lon, item.ponte.lat], zoom: 12, pitch: 62, bearing: -20, duration: 2400, offset: off, essential: true});
    else if (item.k && caixaMun[item.k]) {
      const cam = mapa3d.cameraForBounds(caixaMun[item.k], {padding: padMapa()});
      mapa3d.flyTo({center: cam.center, zoom: Math.min(cam.zoom, 10.5), pitch: 60, bearing: -14, duration: 2400, essential: true});
    }
    marcaSel(item);
  } else if (mapa2d) desenha2D(item);
}
function voaEstado() {
  if (mapa3d && mapaPronto) { mapa3d.setPadding({top: 0, bottom: 0, left: 0, right: 0}); mapa3d.fitBounds(CAIXA_RO, {padding: padMapa(), pitch: 48, bearing: -6, duration: 1800}); marcaSel(null); }
  else if (mapa2d) desenha2D(null);
}

// geometrias para o mapa
const caixaMun = {};
const GEO_MUN = {type: "FeatureCollection", features: D.geo.features.map(f => {
  const k = nmz(f.properties.nome), x = munE(k) || {};
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  (f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates).flat().forEach(r => r.forEach(([a, b]) => { x0 = Math.min(x0, a); x1 = Math.max(x1, a); y0 = Math.min(y0, b); y1 = Math.max(y1, b); }));
  caixaMun[k] = [[x0, y0], [x1, y1]];
  return {type: "Feature", geometry: f.geometry, properties: {k, nome: f.properties.nome, repasse: x.repasse || 0, pav: x.pav || 0, terra: x.terra || 0, madeira: x.pontes_madeira || 0}};
})};
const CAIXA_RO = [[-66.81, -13.69], [-59.77, -7.97]];
const ROTULOS = {type: "FeatureCollection", features: GEO_MUN.features.map(f => { const b = caixaMun[f.properties.k]; return {type: "Feature", properties: {nome: f.properties.nome}, geometry: {type: "Point", coordinates: [(b[0][0] + b[1][0]) / 2, (b[0][1] + b[1][1]) / 2]}}; })};
const GEO_VIAS = {type: "FeatureCollection", features: D.vias.rodovias.map((r, i) => ({type: "Feature", id: i, properties: {c: r.c, r: r.r, i}, geometry: {type: "MultiLineString", coordinates: r.g}}))};
const GEO_FED = {type: "FeatureCollection", features: D.vias.federais.map(r => ({type: "Feature", properties: {br: r.br}, geometry: {type: "MultiLineString", coordinates: r.g}}))};
const GEO_PONTES = {type: "FeatureCollection", features: E.pontes.map((p, i) => ({type: "Feature", properties: {i, madeira: p.madeira ? 1 : 0, ext: p.ext}, geometry: {type: "Point", coordinates: [p.lon, p.lat]}}))};
const maxRep = Math.max(...Object.values(E.municipios).map(x => x.repasse));

function telaEstradas() {
  const d = E.der, madeira = E.pontes.filter(p => p.madeira).sort((a, b) => b.ext - a.ext), K = ER.km, T = ER.km_total;
  const est = Object.entries(ER.estado).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${v} ${k}`).join(", ");
  const PROVAS = {
    malha: pr("Malha rodoviária estadual", km(T), `cadastro de trechos do Geoportal do DER, ${dataBR(E.meta.coletado_em)}`,
      [["Com asfalto", km(K["Pavimentada"])], ["De terra", km(K["Não Pavimentada"])], ["Planejada", km(K["Planejada"])], ["Interesse de incorporar (ainda não é do Estado)", km(K["Interesse de Incorporar"])],
        ["Trechos cadastrados", br(ER.trechos)], ["Estado de conservação registrado", est], ["Rodovias", br(ER.rodovias)]], LK_DER),
    madeira: pr("Pontes de madeira", br(ER.madeira_n), `${br(ER.madeira_m, 0)} metros em ${ER.municipios_com_madeira} municípios`,
      [...Object.entries(ER.pontes).map(([k, v]) => [k, br(v)]), ["A maior", `${madeira[0].n}, ${br(madeira[0].ext, 1)} m (${madeira[0].mun})`]], LK_DER),
    valor: pr("Valor das rodovias (patrimônio)", mi(ER.valor_reavaliado), "valor reavaliado dos trechos cadastrados",
      [["Valor inicial (custo)", mi(ER.valor_inicial)], ...Object.entries(E.valor_por_residencia).slice(0, 8).map(([k, v]) => [k + (E.residencias[k]?.sede ? " · " + E.residencias[k].sede : ""), mi(v)])], LK_DER),
    der: pr("O que o DER pagou em 2026", mi(d.pago), `DER e FITHA, pagamentos até ${DATA_PAG}`, Object.entries(d.grupos).map(([k, v]) => [k, mi(v)]), LK.pag),
    rep: pr("Repasses do DER às prefeituras", mi(d.repasses), `convênios pagos em 2026 até ${DATA_PAG}`,
      [["Municípios", br(d.municipios_com_repasse)], ["Sem município identificado", mi(d.repasses_sem_municipio)]], LK.pag)};
  const pct = k => 100 * (K[k] || 0) / T;
  const LEG = [[["asfalto", COR_VIA.pav], ["terra", COR_VIA.terra], ["interesse de incorporar", COR_VIA.plan], ["federal", "#ffffff"]],
    [["ponte de madeira", "#ff3b30"]], [["mais repasse", "#ffc94a"], ["menos", "rgba(255,201,74,.3)"]]];
  $("#esq").innerHTML = `<div class="est">
    <div class="est-mapa" id="slot3d"></div>
    <div class="est-topo"><div class="est-tit"><span class="kicker">Estradas do Estado · DER-RO</span><h2>Só ${br(pct("Pavimentada"), 0)}% das rodovias estaduais têm asfalto</h2></div>
      <div class="est-vistas">${VISTAS_E.map((v, i) => `<button type="button" data-v="${i}" class="${i === estVer ? "on" : ""}">${v}</button>`).join("")}</div></div>
    <div class="est-nums">
      <button type="button" class="est-n grande" data-p="malha"><b>${km(T)}</b><span>de rodovias estaduais</span>
        <i class="est-barra"><em style="width:${pct("Pavimentada")}%;background:${COR_VIA.pav}"></em><em style="width:${pct("Não Pavimentada")}%;background:${COR_VIA.terra}"></em><em style="width:${pct("Interesse de Incorporar") + pct("Planejada")}%;background:${COR_VIA.plan}"></em></i>
        <small><i style="background:${COR_VIA.pav}"></i>${km(K["Pavimentada"])} asfalto <i style="background:${COR_VIA.terra}"></i>${km(K["Não Pavimentada"])} terra</small></button>
      <button type="button" class="est-n" data-p="madeira"><b>${br(ER.madeira_n)}</b><span>pontes de madeira</span></button>
      <button type="button" class="est-n" data-p="valor"><b>${mi(ER.valor_reavaliado)}</b><span>valem as rodovias</span></button>
      <button type="button" class="est-n" data-p="der"><b>${mi(d.pago)}</b><span>pagos pelo DER em 2026</span></button>
      <button type="button" class="est-n" data-p="rep"><b>${mi(d.repasses)}</b><span>foram para prefeituras</span></button>
    </div>
    <div class="est-card" id="est-card"></div>
    <div class="est-pe"><span class="est-leg">${LEG[estVer].map(([n, c]) => `<span><i style="background:${c}"></i>${n}</span>`).join("")}</span>
      <span class="est-fonte">Geoportal do DER-RO · Portal da Transparência · satélite Sentinel-2 (EOX) · relevo AWS</span>
      <button class="btn-dados contorno" type="button" data-dados="1">▦ Dados</button>
      <span class="navp"><button type="button" id="ant" aria-label="Etapa anterior">←</button><button type="button" id="prox" aria-label="Próxima etapa">→</button></span></div>
  </div>`;
  idsAtuais = ["estradas-municipios", "pontes"];
  document.querySelectorAll("[data-dados]").forEach(b => b.onclick = () => abreDados(idsAtuais));
  $("#ant").onclick = () => ir(atual - 1); $("#prox").onclick = () => ir(atual + 1);
  $("#esq").querySelectorAll("[data-p]").forEach(b => b.onclick = () => {
    $("#esq").querySelectorAll("[data-p]").forEach(x => x.classList.toggle("sel", x === b));
    if (b.dataset.p === "madeira" && estVer !== 1) trocaVista(1);
    if (b.dataset.p === "rep" && estVer !== 2) trocaVista(2);
    cartaoItem(PROVAS[b.dataset.p]);
  });
  $("#esq").querySelectorAll("[data-v]").forEach(b => b.onclick = () => trocaVista(+b.dataset.v));
  cartaoLista();
  montaMapa();
}
function trocaVista(i) {
  estVer = i;
  $("#esq").querySelectorAll("[data-v]").forEach(b => b.classList.toggle("on", +b.dataset.v === i));
  const LEG = [[["asfalto", COR_VIA.pav], ["terra", COR_VIA.terra], ["interesse de incorporar", COR_VIA.plan], ["federal", "#ffffff"]], [["ponte de madeira", "#ff3b30"]], [["mais repasse", "#ffc94a"], ["menos", "rgba(255,201,74,.3)"]]];
  $(".est-leg").innerHTML = LEG[i].map(([n, c]) => `<span><i style="background:${c}"></i>${n}</span>`).join("");
  cartaoLista(); aplicaVista(); if (mapa2d) desenha2D(null);
  if (i === 2) voaEstado();
}
function montaMapa() {
  const slot = $("#slot3d");
  if (mapaEl) { slot.append(mapaEl); if (mapa3d) { setTimeout(() => { mapa3d.resize(); aplicaVista(); }, 30); } else if (mapa2d) desenha2D(null); return; }
  mapaEl = el_("div", "mapa3d"); slot.append(mapaEl);
  mapaEl.innerHTML = `<div class="m3-carrega">Carregando o mapa em 3D…</div>`;
  const desiste = setTimeout(() => { if (!mapaPronto) usa2D(); }, 9000);
  carregaLib().then(() => {
    const cv = document.createElement("canvas");
    if (!window.maplibregl || !(cv.getContext("webgl2") || cv.getContext("webgl"))) throw new Error("sem WebGL");
    criaMapa(() => clearTimeout(desiste));
  }).catch(() => { clearTimeout(desiste); usa2D(); });
}
const el_ = (tag, cls) => { const e = document.createElement(tag); e.className = cls; return e; };
function carregaLib() {
  if (window.maplibregl) return Promise.resolve();
  const css = document.createElement("link"); css.rel = "stylesheet"; css.href = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"; document.head.append(css);
  return new Promise((ok, erro) => { const s_ = document.createElement("script"); s_.src = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"; s_.onload = ok; s_.onerror = erro; document.head.append(s_); });
}
function criaMapa(pronto) {
  mapaEl.innerHTML = "";
  const caixa = el_("div", "m3-mapa"); mapaEl.append(caixa);
  mapa3d = new maplibregl.Map({container: caixa, bounds: CAIXA_RO, fitBoundsOptions: {padding: padMapa()}, pitch: 0, bearing: 0, maxPitch: 75, attributionControl: false,
    style: {version: 8, glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
      sources: {
        sat: {type: "raster", tiles: ["https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg"], tileSize: 256, maxzoom: 15,
          attribution: "Sentinel-2 cloudless 2016 por EOX (CC BY 4.0), com dados Copernicus Sentinel"},
        dem: {type: "raster-dem", tiles: ["https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"], tileSize: 256, encoding: "terrarium", maxzoom: 12, attribution: "Relevo: Terrain Tiles (AWS, Mapzen)"},
        mun: {type: "geojson", data: GEO_MUN, promoteId: "k"}, rot: {type: "geojson", data: ROTULOS},
        vias: {type: "geojson", data: GEO_VIAS}, fed: {type: "geojson", data: GEO_FED}, pontes: {type: "geojson", data: GEO_PONTES, promoteId: "i"}},
      layers: [
        {id: "sat", type: "raster", source: "sat", paint: {"raster-saturation": -0.15, "raster-brightness-max": 0.85, "raster-contrast": 0.1}},
        {id: "mun-fill", type: "fill", source: "mun", paint: {"fill-color": "#ffffff", "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.16, ["boolean", ["feature-state", "sel"], false], 0.12, 0.0]}},
        {id: "mun-rep", type: "fill", source: "mun", layout: {visibility: "none"}, paint: {"fill-color": ["interpolate", ["linear"], ["get", "repasse"], 0, "rgba(255,201,74,0.06)", maxRep, "rgba(255,201,74,0.55)"]}},
        {id: "mun-ext", type: "fill-extrusion", source: "mun", layout: {visibility: "none"}, paint: {
          "fill-extrusion-color": ["interpolate", ["linear"], ["get", "repasse"], 0, "rgba(255,201,74,0.15)", maxRep, "#ffc94a"],
          "fill-extrusion-height": ["*", ["/", ["get", "repasse"], maxRep], 60000], "fill-extrusion-opacity": 0.85}},
        {id: "mun-linha", type: "line", source: "mun", paint: {"line-color": "#ffffff", "line-opacity": 0.45, "line-width": ["case", ["boolean", ["feature-state", "sel"], false], 3, 0.8]}},
        {id: "fed", type: "line", source: "fed", paint: {"line-color": "#ffffff", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1, 10, 3], "line-opacity": 0.55}},
        {id: "via-plan", type: "line", source: "vias", filter: ["==", ["get", "c"], "plan"], paint: {"line-color": COR_VIA.plan, "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.8, 10, 2.5], "line-dasharray": [2, 2], "line-opacity": 0.75}},
        {id: "via-terra", type: "line", source: "vias", filter: ["==", ["get", "c"], "terra"], paint: {"line-color": COR_VIA.terra, "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.2, 10, 4]}},
        {id: "via-pav", type: "line", source: "vias", filter: ["==", ["get", "c"], "pav"], paint: {"line-color": COR_VIA.pav, "line-width": ["interpolate", ["linear"], ["zoom"], 5, 1.6, 10, 5]}},
        {id: "via-sel", type: "line", source: "vias", filter: ["==", ["get", "i"], -1], paint: {"line-color": "#ffffff", "line-width": 7, "line-opacity": 0.9}},
        {id: "ponte", type: "circle", source: "pontes", filter: ["==", ["get", "madeira"], 1], paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "ext"], 4, 4, 90, 13], "circle-color": "#ff3b30", "circle-stroke-color": "#ffffff",
          "circle-stroke-width": ["case", ["boolean", ["feature-state", "sel"], false], 4, 1.5], "circle-opacity": 0.95}},
        {id: "rotulo", type: "symbol", source: "rot", minzoom: 6.4, layout: {"text-field": ["get", "nome"], "text-font": ["Noto Sans Regular"], "text-size": ["interpolate", ["linear"], ["zoom"], 6.4, 11, 10, 16], "text-allow-overlap": false},
          paint: {"text-color": "#ffffff", "text-halo-color": "rgba(0,0,0,.85)", "text-halo-width": 1.6}}]}});
  mapa3d.addControl(new maplibregl.NavigationControl({visualizePitch: true}), "top-right");
  mapa3d.addControl(new maplibregl.AttributionControl({compact: true}), "bottom-right");
  const pop = new maplibregl.Popup({closeButton: false, closeOnClick: false, className: "m3-pop", offset: 10});
  let hov = null;
  const tira = () => { if (hov != null) mapa3d.setFeatureState({source: "mun", id: hov}, {hover: false}); hov = null; };
  mapa3d.on("mousemove", e => {
    const f = mapa3d.queryRenderedFeatures(e.point, {layers: ["ponte", "via-pav", "via-terra", "via-plan", estVer === 2 ? "mun-ext" : "mun-fill"].filter(l => mapa3d.getLayer(l))})[0];
    mapa3d.getCanvas().style.cursor = f ? "pointer" : "";
    if (!f) { pop.remove(); tira(); return; }
    let h;
    if (f.layer.id === "ponte") { const p = E.pontes[f.properties.i]; h = `<b>${esc(p.n)}</b><span>${p.t} · ${br(p.ext, 1)} m · ${esc(p.rod)} · ${esc(p.mun)}</span>`; tira(); }
    else if (f.layer.id.startsWith("via")) { const r = D.vias.rodovias[f.properties.i]; h = `<b>${esc(r.r)} · ${r.c === "pav" ? "asfalto" : r.c === "terra" ? "terra" : "interesse de incorporar"}</b><span>${esc(r.ini || "")} → ${esc(r.fim || "")} · ${br(r.ext, 1)} km</span>`; tira(); }
    else { const k = f.properties.k, x = munE(k); if (hov !== k) { tira(); hov = k; mapa3d.setFeatureState({source: "mun", id: k}, {hover: true}); }
      h = `<b>${esc(f.properties.nome)}</b><span>${x ? (estVer === 2 ? `${mi(x.repasse)} do DER em 2026` : `${km(x.pav)} asfalto · ${km(x.terra)} terra · ${x.pontes_madeira} pontes de madeira`) : "sem rodovia estadual"}</span>`; }
    pop.setLngLat(e.lngLat).setHTML(h).addTo(mapa3d);
  });
  mapa3d.getCanvas().addEventListener("mouseleave", () => { pop.remove(); tira(); });
  mapa3d.on("click", e => {
    const f = mapa3d.queryRenderedFeatures(e.point, {layers: ["ponte", "via-pav", "via-terra", "via-plan", estVer === 2 ? "mun-ext" : "mun-fill"].filter(l => mapa3d.getLayer(l))})[0];
    if (!f) return;
    if (f.layer.id === "ponte") { const it = cartaoPonte(E.pontes[f.properties.i]); voa(it); mostraUm(it, "ponte"); }
    else if (f.layer.id.startsWith("via")) { const r = D.vias.rodovias[f.properties.i];
      mapa3d.setFilter("via-sel", ["==", ["get", "i"], f.properties.i]);
      mostraUm(pr(`${r.r} · trecho ${r.sre}`, br(r.ext, 1) + " km", `${r.c === "pav" ? "asfalto" : r.c === "terra" ? "terra" : "interesse de incorporar"} · ${r.cl || ""}`,
        [["Início", r.ini], ["Fim", r.fim], ["Revestimento", r.rev || "—"], ["Município", r.m.map(k => munE(k)?.nome || k).join(", ")], ["Residência do DER", `${r.rr}${E.residencias[r.rr]?.sede ? " · " + E.residencias[r.rr].sede : ""}`]], LK_DER), r.r); }
    else { const it = cartaoMun(f.properties.k); if (it) { voa(it); mostraUm(it, it.nome); } }
  });
  // botões: 2D/3D, voltar ao Estado e tela cheia
  const bt = el_("div", "m3-botoes"); mapaEl.append(bt);
  bt.innerHTML = `<button type="button" data-a="3d">2D</button><button type="button" data-a="ro">↺ Estado</button><button type="button" data-a="tela">⛶ Tela cheia</button>`;
  bt.querySelector('[data-a="ro"]').onclick = voaEstado;
  bt.querySelector('[data-a="3d"]').onclick = e => { const plano = mapa3d.getPitch() > 5; mapa3d.setTerrain(plano ? null : {source: "dem", exaggeration: 2.2}); mapa3d.easeTo({pitch: plano ? 0 : 55, bearing: plano ? 0 : -8, duration: 900}); e.currentTarget.textContent = plano ? "3D" : "2D"; };
  bt.querySelector('[data-a="tela"]').onclick = () => document.fullscreenElement ? document.exitFullscreen() : ($(".est") || mapaEl).requestFullscreen?.();
  // ao abrir: o Estado visto de cima, e a câmera inclina devagar até o relevo aparecer
  mapa3d.on("load", () => { mapaPronto = true; pronto(); mapa3d.setTerrain({source: "dem", exaggeration: 2.2}); aplicaVista();
    mapa3d.fitBounds(CAIXA_RO, {padding: padMapa(), pitch: 48, bearing: -6, duration: 3200});
    caixa.querySelector(".maplibregl-ctrl-attrib")?.classList.remove("maplibregl-compact-show"); });
  mapa3d.on("error", () => {});
}
let selAnt = null;
function marcaSel(item) {
  if (!mapa3d || !mapaPronto) return;
  if (selAnt) mapa3d.setFeatureState(selAnt, {sel: false});
  selAnt = item?.ponte ? {source: "pontes", id: E.pontes.indexOf(item.ponte)} : item?.k ? {source: "mun", id: item.k} : null;
  if (selAnt) mapa3d.setFeatureState(selAnt, {sel: true});
  if (!item) mapa3d.setFilter("via-sel", ["==", ["get", "i"], -1]);
}
function aplicaVista() {
  if (!mapa3d || !mapaPronto) return;
  const vis = (id, on) => mapa3d.setLayoutProperty(id, "visibility", on ? "visible" : "none");
  const op = estVer === 1 ? 0.35 : 1;
  ["via-pav", "via-terra"].forEach(l => mapa3d.setPaintProperty(l, "line-opacity", op));
  vis("via-plan", estVer === 0); vis("fed", estVer !== 2); vis("mun-ext", estVer === 2); vis("mun-rep", estVer === 2); vis("ponte", estVer !== 2);
  mapa3d.setPaintProperty("ponte", "circle-radius", estVer === 1 ? ["interpolate", ["linear"], ["get", "ext"], 4, 5, 90, 16] : ["interpolate", ["linear"], ["get", "ext"], 4, 3, 90, 9]);
}
// reserva sem internet ou sem WebGL: o mesmo mapa, desenhado e plano
function usa2D() { mapa2d = true; mapa3d = null; desenha2D(null); }
function desenha2D(sel) {
  mapaEl.innerHTML = `<div class="m3-aviso">Mapa simplificado (sem conexão para o satélite)</div>`;
  const w = mapaEl.clientWidth || 700, h = mapaEl.clientHeight || 420;
  const s_ = document.createElementNS(NS, "svg"); s_.setAttribute("viewBox", `0 0 ${w} ${h}`); s_.setAttribute("class", "m2d"); mapaEl.classList.add("plano"); mapaEl.append(s_);
  const [[x0, y0], [x1, y1]] = CAIXA_RO, kx = Math.cos((y0 + y1) / 2 * Math.PI / 180), e_ = Math.min((w - 20) / ((x1 - x0) * kx), (h - 20) / (y1 - y0));
  const px = ([x, y]) => [10 + (x - x0) * kx * e_, 10 + (y1 - y) * e_], cam = l => "M" + l.map(p => px(p).map(v => v.toFixed(1)).join(",")).join("L");
  GEO_MUN.features.forEach(f => {
    const k = f.properties.k, x = munE(k);
    const d = (f.geometry.type === "Polygon" ? f.geometry.coordinates : f.geometry.coordinates.flat()).map(r => cam(r) + "Z").join("");
    const fill = estVer === 2 && x ? `color-mix(in srgb, var(--c3) ${(15 + 85 * x.repasse / maxRep).toFixed(0)}%, transparent)` : sel?.k === k ? "var(--azul-fundo)" : "var(--bg)";
    const p = el(s_, "path", {d, fill, stroke: "var(--hair)", "stroke-width": 0.8, class: "alvo"});
    dica(p, f.properties.nome, x ? [["Asfalto", km(x.pav)], ["Terra", km(x.terra)], ["Pontes de madeira", br(x.pontes_madeira)], ["Repasses do DER", mi(x.repasse)]] : [["Rodovia estadual", "nenhuma"]], "Clique para ver");
    p.addEventListener("click", () => { const it = cartaoMun(k); if (it) { desenha2D(it); mostraUm(it, it.nome); } });
  });
  if (estVer !== 2) D.vias.rodovias.forEach(r => el(s_, "path", {d: r.g.map(cam).join(""), fill: "none", stroke: r.c === "pav" ? "#d99a00" : r.c === "terra" ? "#e0662a" : "#b8bec6", "stroke-width": r.c === "pav" ? 1.8 : 1.1, "stroke-dasharray": r.c === "plan" ? "3 3" : "", opacity: estVer === 1 ? 0.35 : 1, "pointer-events": "none"}));
  if (estVer !== 2) E.pontes.filter(p => p.madeira).forEach(p => { const [cx, cy] = px([p.lon, p.lat]);
    const c = el(s_, "circle", {cx, cy, r: estVer === 1 ? 2.5 + p.ext / 12 : 2 + p.ext / 20, fill: "#e5322d", stroke: sel?.ponte === p ? "var(--ink)" : "#fff", "stroke-width": sel?.ponte === p ? 2.5 : 0.8, class: "alvo"});
    dica(c, p.n, [["Tipo", p.t], ["Rodovia", p.rod], ["Extensão", br(p.ext, 1) + " m"], ["Município", p.mun]], "Clique para ver");
    c.addEventListener("click", () => { const it = cartaoPonte(p); desenha2D(it); mostraUm(it, "ponte"); }); });
}

// ---------- 5. 2025 × 2026 no mesmo período
let compVer = 0;
const BLOCOS_C = {veiculos: ["Veículos", ["combustivel", "transporte", "locacao", "ambulancia", "manutencao"]], imovel: ["Aluguel", ["imovel"]],
  contas: ["Contas", ["energia", "agua", "telecom", "correios"]], apoio: ["Apoio", ["vigilancia", "limpeza", "predial", "maoobra"]], viagens: ["Viagens", ["diarias", "passagens"]]};
const TEMAS_C = Object.keys(BLOCOS_C), NOME_BLOCO = k => BLOCOS_C[k][0];
const seta = (a, b) => { if (!a) return "—"; const p = 100 * (b - a) / a, cor = Math.abs(p) < 1 ? "var(--mute)" : p > 0 ? "var(--c3)" : "var(--c2)";
  return `<span style="color:${cor}">${Math.abs(p) < 1 ? `≈ praticamente igual (${p >= 0 ? "+" : "−"}${br(Math.abs(p), 1)}%)` : `${p > 0 ? "▲" : "▼"} ${br(Math.abs(p), 0)}% a ${p > 0 ? "mais" : "menos"}`}</span>`; };
const setaC = (a, b) => { if (!a) return "—"; const p = 100 * (b - a) / a, cor = Math.abs(p) < 1 ? "var(--mute)" : p > 0 ? "var(--c3)" : "var(--c2)";
  return `<span style="color:${cor}">${Math.abs(p) < 1 ? "≈ igual" : `${p > 0 ? "▲" : "▼"} ${br(Math.abs(p), 0)}%`}</span>`; };
const fraseVar = (a, b) => { const p = 100 * (b - a) / a; return Math.abs(p) < 3 ? "quase o mesmo que" : `${br(Math.abs(p), 0)}% a ${p > 0 ? "mais" : "menos"} que`; };
function telaComparativo() {
  const ks = b => BLOCOS_C[b][1];
  const v = b => [ks(b).reduce((a, k) => a + (CP.temas[k]?.["2025"] || 0), 0), ks(b).reduce((a, k) => a + (CP.temas[k]?.["2026"] || 0), 0)];
  const s25 = TEMAS_C.reduce((a, b) => a + v(b)[0], 0), s26 = TEMAS_C.reduce((a, b) => a + v(b)[1], 0);
  const doOrg = (o, b, ano) => ks(b).reduce((x, k) => x + (o[`${k}_${ano}`] || 0), 0);
  const os = CP.orgaos.map(o => ({...o, a: TEMAS_C.reduce((x, b) => x + doOrg(o, b, "2025"), 0), b: TEMAS_C.reduce((x, b) => x + doOrg(o, b, "2026"), 0)})).filter(o => o.a + o.b > 0)
    .map(o => ({...o, d: o.b - o.a, blocos: TEMAS_C.map(b => [b, doOrg(o, b, "2025"), doOrg(o, b, "2026")])})).sort((x, y) => Math.abs(y.d) - Math.abs(x.d));
  const periodo = `1º de janeiro a ${CP.ate.slice(0, 2)} de novembro`;
  const provaTipo = b => pr(`${NOME_BLOCO(b)}: 2025 × 2026`, var_(...v(b)), `pago de ${periodo}, em cada ano, só Executivo`,
    [["2025", mi(v(b)[0])], ["2026", mi(v(b)[1])], ["Diferença", (v(b)[1] >= v(b)[0] ? "+" : "−") + mi(Math.abs(v(b)[1] - v(b)[0]))],
      ...ks(b).map(k => [C[k].nome, `${mi(CP.temas[k]?.["2025"] || 0)} → ${mi(CP.temas[k]?.["2026"] || 0)} (${var_(CP.temas[k]?.["2025"] || 0, CP.temas[k]?.["2026"] || 0)})`])], LK.pag);
  esq({kicker: `Mesmo período nos dois anos: ${periodo}`, titulo: `Em 2026 o Estado gastou ${fraseVar(s25, s26)} 2025 para manter a máquina`,
    n: mi(s26), s: `pagos em 2026<br>Em 2025: <b>${mi(s25)}</b> · ${seta(s25, s26)}`,
    provaN: pr("Como a comparação é feita", mi(s26), "mesmo período, mesma régua", [["Período", `${periodo} de 2025 e de 2026`], ["2025", mi(s25)], ["2026", mi(s26)],
      ["Régua", "pagamentos (ordens bancárias) pelo subelemento da despesa, só Executivo, sem estatais"],
      ["Por que não o ano inteiro", "2026 ainda não terminou: o ano inteiro só existe como estimativa e aparece em cada aba."]], LK.pag),
    estat: TEMAS_C.map(b => [NOME_BLOCO(b), `${setaC(...v(b))}<div class="sub-estat">${mi(v(b)[0])} → ${mi(v(b)[1])}</div>`, provaTipo(b)]),
    alterna: ["Ver:", ["Por tipo de gasto", "Mês a mês"], compVer, i => { compVer = i; telaComparativo(); }],
    legenda: legenda([["2025", "var(--cinza)"], ["2026", "var(--c1)"]]),
    dicaUso: compVer ? `Pago acumulado até o fim de cada mês. Em novembro, os dois anos param no dia ${CP.ate.slice(0, 2)}.`
      : `Cinza: 2025. Azul: 2026. Clique numa barra para ver a conta; à direita, os órgãos que mais mudaram.`,
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores de 2025 e 2026, pelo subelemento da despesa`, dados: ["veiculos-2026", "imoveis-2026", "consumo-2026"], padrao: () => provasComp(os)});
  if (compVer === 0) colunas($("#graf"), TEMAS_C.flatMap(b => [
    {rot: NOME_BLOCO(b), partes: [{v: v(b)[0], cor: "var(--cinza)"}], topo: mi(v(b)[0]), dica: [`${NOME_BLOCO(b)} · 2025`, [["Pago de " + periodo, mi(v(b)[0])]]],
      clique: () => mostraProvas("A conta", [provaTipo(b)], {abrir: 0, filtro: NOME_BLOCO(b), limpar: () => provasComp(os)})},
    {rot: "", partes: [{v: v(b)[1], cor: "var(--c1)"}], topo: mi(v(b)[1]), destaque: true, dica: [`${NOME_BLOCO(b)} · 2026`, [["Pago de " + periodo, mi(v(b)[1])], ["Em relação a 2025", var_(...v(b))]]],
      clique: () => mostraProvas("A conta", [provaTipo(b)], {abrir: 0, filtro: NOME_BLOCO(b), limpar: () => provasComp(os)})}]));
  else colunas($("#graf"), MESES.slice(0, MES_PAG).flatMap((m, i) => {
    const todos = TEMAS_C.flatMap(ks), a = todos.reduce((x, k) => x + CP.acumulado[k]["2025"][i], 0), b = todos.reduce((x, k) => x + CP.acumulado[k]["2026"][i], 0);
    return [{rot: m, partes: [{v: a, cor: "var(--cinza)"}], topo: "", dica: [`Até ${MESES_L[i]} de 2025`, [["Acumulado", mi(a)]]]},
      {rot: "", partes: [{v: b, cor: "var(--c1)"}], topo: i === MES_PAG - 1 ? mi(b) : "", destaque: i === MES_PAG - 1, dica: [`Até ${MESES_L[i]} de 2026`, [["Acumulado", mi(b)], ["Em relação a 2025", var_(a, b)]]]}];
  }));
}
function provasComp(os) {
  const max = Math.max(...os.map(o => Math.abs(o.d)), 1);
  const lista = os.map(o => ({nome: o.sigla, sub: `${D.nomes[o.sigla] || ""} · ${mi(o.a)} em 2025 → ${mi(o.b)} em 2026`,
    valor: `${o.d >= 0 ? "▲" : "▼"} ${mi(Math.abs(o.d))}`, barra: Math.abs(o.d) / max,
    linhas: [["2025", mi(o.a)], ["2026", mi(o.b)], ["Mudança", `${o.d >= 0 ? "gastou " + mi(o.d) + " a mais" : "gastou " + mi(-o.d) + " a menos"} (${var_(o.a, o.b)})`],
      ...o.blocos.filter(([, a, b]) => a || b).map(([b, a, c]) => [NOME_BLOCO(b), `${mi(a)} → ${mi(c)}`])], link: LK.pag}));
  mostraProvas(`Órgãos que mais mudaram. ▲ gastou mais em 2026; ▼ gastou menos. Mesmo período nos dois anos.`, lista, {todas: lista, tituloTodas: "2025 × 2026 por órgão", limite: 6});
}

// ---------- 6. secretarias regionais
let regVer = 0, regSel = null;
const normMun = s => semAcento(s).replace(/D'? ?OESTE|DO OESTE/g, "DOESTE").replace(/[^A-Z]/g, "");
const TIPOS_R = ["Pessoal comissionado (CDS)", "Pessoal cedido (ressarcimento)", "Locação de veículos", "Combustível", "Aluguel de imóvel", "Energia, água e taxas do imóvel", "Internet", "Diárias"];
const COR_R = ["var(--c1)", "color-mix(in srgb, var(--c1) 55%, transparent)", "var(--c2)", "var(--c6)", "var(--c4)", "var(--c3)", "var(--cinza)", "var(--cinza2)"];
const LK_REG = ["Pagamentos da SUGESP (UG 110009) no Portal", PORTAL_PAG];
function telaRegionais() {
  const T = R.total, P = R.projecao.Total, U = [...R.unidades].sort((a, b) => b.total_2026 - a.total_2026);
  const provaR = (nome, v, linhas) => pr(nome, v, "planilha de execução das regionais (v04, 13/11/2026), sobre o SIGEF da SUGESP, posição 12/11/2026", linhas, LK_REG);
  esq({kicker: "Secretarias Executivas Regionais · Gabinete do Governador", titulo: "Quanto custam as 10 secretarias regionais e a coordenação",
    n: mi(T.total_2026), s: `estimados em 2026: <b>${mi(T.pago_ate_12_11)}</b> pagos no SIGEF até 12/11, CDS e projeção até dezembro<br>De 2027 a 2030, se nada mudar: <b>${mi(P.total)}</b>`,
    provaN: provaR("Custo das regionais em 2026", mi(T.total_2026), [["Pago até 12/11 (SIGEF)", mi(T.pago_ate_12_11)], ["CDS de jan a out (cálculo sobre o quadro atual)", mi(T.cds_jan_out)], ["Projeção nov e dez", mi(T.projecao_nov_dez)], ["Unidade que paga", "SUGESP, ação 4546 (polos regionais)"], ["Base legal", "LC 965/2017, arts. 87 e 90 (LC 1.215/2023); Decreto 31.814/2026"]]),
    estat: [["Servidores", `${br(T.servidores)} · ${br(T.com_cds)} com CDS`, provaR("Servidores das regionais", br(T.servidores), [["Com CDS", br(T.com_cds)], ["Origem", "listas de pessoal encaminhadas pelas regionais (nomes não aparecem)"]])],
      ["CDS por mês", mi(T.cds_mes), provaR("Cargos em comissão das regionais", mi(T.cds_mes) + "/mês", Object.entries(M.regionais.unidades.reduce((a, u) => { Object.entries(u.cds || {}).forEach(([k, v]) => a[k] = (a[k] || 0) + v); return a; }, {})).map(([k, v]) => [k, br(v)]))],
      ["Veículos", `${br(T.veic_proprios + T.veic_locados)} · ${br(T.veic_locados)} locados`, provaR("Veículos das regionais", br(T.veic_proprios + T.veic_locados), [["Próprios (SUGESP)", br(T.veic_proprios)], ["Locados (S10)", br(T.veic_locados)], ["Locação em 2026", mi(R.tipos["Locação de veículos"].total_2026)]])],
      ["2027", mi(P["2027"]), provaR("Projeção 2027 a 2030", mi(P.total), [["2027", mi(P["2027"])], ["2028", mi(P["2028"])], ["2029", mi(P["2029"])], ["2030", mi(P["2030"])], ["Correção", "IPCA do Focus de 09/11/2026: 5,22%, 4,90%, 4,00% e 4,00%"]])]],
    alterna: ["Ver:", ["Mapa", "Por tipo de despesa", "2026 a 2030"], regVer, i => { regVer = i; telaRegionais(); }],
    legenda: regVer === 0 ? legenda([["mais caro em 2026", "var(--c1)"], ["mais barato", "color-mix(in srgb, var(--c1) 22%, transparent)"]]) : "",
    dicaUso: ["Cada região com seus municípios; a cor mais forte é a de maior custo em 2026. Clique numa região. A coordenação (COOREG) fica em Porto Velho. O organograma completo está na próxima etapa →",
      "Custo estimado de 2026 por tipo de despesa, somadas as 11 unidades.", "Base de 2026 corrigida pelo IPCA do Focus de 09/11/2026, mantidos quadro, estrutura e contratos."][regVer],
    fonte: "Fonte: planilha de execução das regionais (v04, 13/11/2026), sobre o SIGEF da SUGESP (UG 110009), posição 12/11/2026 · população: IBGE, Censo 2022", dados: ["regionais"], padrao: () => provasRegionais(U, regSel)});
  if (regVer === 0) mapa(U);
  else if (regVer === 1) barras($("#graf"), TIPOS_R.map((k, i) => ({rot: k.replace(" do imóvel", ""), partes: [{v: R.tipos[k]?.total_2026 || 0, cor: COR_R[i]}], dir: mi(R.tipos[k]?.total_2026), dica: [k, [["2026", mi(R.tipos[k]?.total_2026)], ["Por mês", mi(R.tipos[k]?.mensal)]]]})));
  else colunas($("#graf"), ["2026", "2027", "2028", "2029", "2030"].map(a => ({rot: a, partes: [{v: R.projecao.Total[a], cor: a === "2026" ? "var(--c1)" : claro("var(--c1)")}], topo: mi(R.projecao.Total[a]), destaque: a === "2026"})));
}
// organograma: a hierarquia da LC 965/2017, art. 87, II, com os números de cada unidade
const FUNCOES_SER = ["agentes de transformação regional", "indução do engajamento da sociedade civil", "auxílio às Secretarias de Estado na região",
  "apoio técnico aos municípios e às organizações comunitárias", "apoio aos municípios na implantação de políticas públicas",
  "representação do Governo nas Regiões de Planejamento e Gestão", "apoio à SEPOG no Seminário Anual de Avaliação", "colaboração no Plano de Desenvolvimento Estadual Sustentável (PDES)"];
// Etapa própria, tela inteira: o organograma da folha A3 das regionais, caixa por caixa, com o custo de cada uma
const TIPOS_TAB = ["Pessoal comissionado (CDS)", "Pessoal cedido (ressarcimento)", "Locação de veículos", "Combustível", "Manutenção de veículos",
  "Aluguel de imóvel", "Energia, água e taxas do imóvel", "Internet", "Manutenção predial", "Diárias"];
const reais = v => "R$ " + br(Math.round(v || 0));
const nomeSer = u => u.codigo === "COOREG" ? "COOREG" : u.nome.replace(/\s*\(.*/, "");
function telaOrganograma() {
  const ser = R.unidades.filter(u => u.codigo !== "COOREG"), co = R.unidades.find(u => u.codigo === "COOREG"), T = R.total;
  const vs = ser.map(u => u.total_2026), max = Math.max(...vs), min = Math.min(...vs), t01 = u => (u.total_2026 - min) / (max - min || 1);
  const veic = u => `${br(u.veic_proprios)} próp. / ${br(u.veic_locados)} loc.`;
  const caixa = u => `<div class="arv-filho"><button type="button" class="arv-ser" data-cod="${u.codigo}">
      <span class="arv-cab" style="--p:${(30 + 70 * t01(u)).toFixed(0)}%"><b>${esc(nomeSer(u))}</b><small>${esc(u.sede)}</small></span>
      <span class="arv-v">${mi(u.total_2026)}<i>R$ ${br(u.custo_hab || 0, 2)} por habitante</i></span>
      <span class="arv-l"><i>Servidores</i><b>${br(u.servidores)}</b></span>
      <span class="arv-l"><i>CDS/mês</i><b>${mi(u.cds_mes)}</b></span>
      <span class="arv-l"><i>Veículos</i><b>${br(u.veic_proprios + u.veic_locados)}${u.veic_locados ? ` <small>(${u.veic_locados} loc.)</small>` : ""}</b></span>
      <span class="arv-l"><i>Pago</i><b>${mi(u.pago_ate_12_11)}</b></span>
      <span class="arv-mun"><b>${br(u.municipios.length)} município${u.municipios.length > 1 ? "s" : ""}</b>${u.municipios.map(esc).join(", ")}</span>
    </button></div>`;
  $("#esq").innerHTML = `<div class="entra arv-topo"><div><div class="kicker">Secretarias Executivas Regionais do Gabinete do Governador</div>
      <h2 class="titulo">Organograma das regionais</h2></div>
      <button type="button" class="arv-tot" id="arv-tot"><b>${mi(T.total_2026)}</b><span>em 2026, as 11 unidades<br>${br(T.servidores)} servidores · ${br(T.veic_proprios + T.veic_locados)} veículos</span></button></div>
    <div class="arv">
      <div class="arv-no gov">Governador do Estado</div><i class="arv-v1"></i>
      <div class="arv-no gab">Gabinete do Governador</div><i class="arv-v1"></i>
      <button type="button" class="arv-no co" data-cod="COOREG"><b>Coordenadoria-Geral das Secretarias Regionais (COOREG)</b>
        <small>Coordenador-Geral, CDS-14 · ${br(co.servidores)} servidores · ${mi(co.total_2026)} em 2026</small></button><i class="arv-v1"></i>
      <div class="arv-sub">10 Secretarias Executivas Regionais · cada uma chefiada por um Secretário-Executivo Regional, CDS-13</div>
      <div class="arv-filhos">${ser.map(caixa).join("")}</div>
    </div>
    <div class="arv-pe">
      <div class="arv-fun"><b>Funções das regionais (LC 965/2017, art. 90, parágrafo único, em síntese)</b>
        <ol>${FUNCOES_SER.map(f => `<li>${esc(f)}</li>`).join("")}</ol></div>
      <div class="arv-leg"><span><i class="arv-cor min"></i>menor custo em 2026 <i class="arv-cor max"></i>maior</span>
        <span>Valor grande: estimado para 2026. Pago: até 12/11, no SIGEF.</span><span>Sem orçamento próprio: a SUGESP paga.</span></div>
    </div>
    <div class="dica-uso">Clique numa caixa: abre o custo por tipo de despesa e a projeção até 2030.</div>
    <div class="rodape"><div class="fonte">Fonte: LC 965/2017 (arts. 87 e 90); SIGEF, UG 110009, 12/11/2026; listas das regionais; IBGE, Censo 2022</div>
      <button class="btn-dados contorno" type="button" data-dados="1">▦ Ver os dados de origem</button>
      <span class="navp"><button type="button" id="ant" aria-label="Etapa anterior">←</button><button type="button" id="prox" aria-label="Próxima etapa">→</button></span></div>`;
  idsAtuais = ["regionais"];
  document.querySelectorAll("[data-dados]").forEach(b => b.onclick = () => abreDados(idsAtuais));
  $("#ant").onclick = () => ir(atual - 1); $("#prox").onclick = () => ir(atual + 1);
  $("#esq").querySelectorAll("[data-cod]").forEach(b => b.onclick = () => abreUnidade(R.unidades.find(u => u.codigo === b.dataset.cod)));
  $("#arv-tot").onclick = () => abreUnidade(null);
}
// gaveta com a tabela de custo da unidade (ou das 11 somadas), como na folha A3 de custos
function abreUnidade(u) {
  const tipos = u ? u.tipos : R.tipos, proj = u ? u.projecao["Total da regional"] : R.projecao.Total;
  const ni = k => (u ? [u] : R.unidades).every(x => /não identificado/i.test(x.tipos[k]?.natureza || ""));
  const cel = (k, c) => ni(k) ? "n.i." : tipos[k]?.[c] ? reais(tipos[k][c]) : "—";
  const soma = c => TIPOS_TAB.reduce((a, k) => a + (tipos[k]?.[c] || 0), 0);
  $("#painel-tit").textContent = u ? `${nomeSer(u)}${u.codigo === "COOREG" ? " · Coordenadoria-Geral" : ""} · ${u.sede}` : "As 11 unidades somadas";
  $("#painel-busca").hidden = true;
  $("#painel-lista").innerHTML = `<div class="arv-ficha">
    ${u ? `<p><b>${esc(u.titular || "")}</b> · ${br(u.servidores)} servidores (${br(u.com_cds)} com CDS) · veículos ${br(u.veic_proprios)} próprios e ${br(u.veic_locados)} locados${u.populacao ? ` · ${br(u.populacao)} habitantes (Censo 2022), R$ ${br(u.custo_hab, 2)} por habitante` : ""}</p>` : `<p>${br(R.total.servidores)} servidores · ${br(R.total.veic_proprios + R.total.veic_locados)} veículos · COOREG e 10 regionais</p>`}
    <table class="arv-tab"><thead><tr><th>Tipo de despesa</th><th>Por mês</th><th>Até 12/11</th><th>Total 2026</th></tr></thead><tbody>
      ${TIPOS_TAB.map(k => `<tr><td>${esc(k)}</td><td>${cel(k, "mensal")}</td><td>${cel(k, "ate_12_11")}</td><td>${cel(k, "total_2026")}</td></tr>`).join("")}
      <tr class="tot"><td>Total</td><td>${reais(soma("mensal"))}</td><td>${reais(soma("ate_12_11"))}</td><td>${reais(soma("total_2026"))}</td></tr></tbody></table>
    <table class="arv-tab"><thead><tr><th>Se nada mudar</th>${["2027", "2028", "2029", "2030"].map(a => `<th>${a}</th>`).join("")}</tr></thead>
      <tbody><tr><td>Projeção (IPCA)</td>${["2027", "2028", "2029", "2030"].map(a => `<td>${reais(proj[a])}</td>`).join("")}</tr>
      <tr class="tot"><td>4 anos</td><td colspan="4">${reais(["2027", "2028", "2029", "2030"].reduce((a, k) => a + proj[k], 0))}</td></tr></tbody></table>
    ${u && Object.keys(u.cds || {}).length ? `<p><b>Cargos em comissão:</b> ${Object.entries(u.cds).map(([k, v]) => `${v}× ${k}`).join(", ")}</p>` : ""}
    ${u && u.municipios?.length > 1 ? `<p><b>Municípios (${u.municipios.length}):</b> ${u.municipios.map(esc).join(", ")}</p>` : ""}
    <p class="arv-nota">CDS: cálculo sobre o quadro atual, sem encargos. Demais tipos: pago no SIGEF até 12/11 e projeção de novembro e dezembro pela média de agosto a outubro. n.i.: não identificado na base (contratos gerais da SUGESP não rateados). Projeção corrigida pelo IPCA do Focus de 09/11/2026.</p>
    <a class="link-fonte" href="${LK_REG[1]}" target="_blank" rel="noopener">${esc(LK_REG[0])} ↗</a></div>`;
  $("#painel").classList.add("on"); $("#cortina").classList.add("on"); $("#painel").setAttribute("aria-hidden", "false");
}
const abrePainelBase = abrePainel;
abrePainel = (t, l) => { $("#painel-busca").hidden = false; abrePainelBase(t, l); };
function provasRegionais(U, sel) {
  const max = U[0].total_2026;
  const lista = U.map(u => ({nome: u.codigo === "COOREG" ? "COOREG · Coordenação-Geral" : `${u.nome.replace(/\s*\(.*/, "")} · ${u.sede}`, sub: `${br(u.servidores)} servidores · ${br(u.veic_proprios + u.veic_locados)} veículo${u.veic_proprios + u.veic_locados === 1 ? "" : "s"} · ${u.municipios?.length > 1 ? br(u.municipios.length) + " municípios" : "atuação estadual"}`,
    valor: mi(u.total_2026), barra: u.total_2026 / max,
    linhas: [["Titular", u.titular || ""], ...(u.populacao ? [["População da região (Censo 2022)", br(u.populacao)], ["Custo por habitante em 2026", "R$ " + br(u.custo_hab, 2)]] : []),
      ...Object.entries(u.cds || {}).length ? [["Cargos em comissão", Object.entries(u.cds).map(([k, v]) => `${v}× ${k}`).join(", ")]] : [],
      ...TIPOS_R.filter(k => u.tipos[k]?.total_2026).map(k => [k, `${mi(u.tipos[k].total_2026)} · ${mi(u.tipos[k].mensal)}/mês`]), ["2027 a 2030", mi(Object.values(u.projecao).reduce((a, p) => a + p["2027"] + p["2028"] + p["2029"] + p["2030"], 0))],
      ...(u.municipios?.length > 1 ? [["Municípios", u.municipios.join(", ")]] : [])], link: LK_REG}));
  const i = sel ? U.indexOf(sel) : -1;
  if (i >= 0) mostraProvas(lista[i].nome, [lista[i]], {filtro: sel.codigo, limpar: () => { regSel = null; telaRegionais(); }, abrir: 0});
  else mostraProvas("As 11 unidades, da mais cara para a mais barata em 2026, e o que a lei manda as regionais fazerem. Clique para abrir.",
    [...lista, pr("O que as regionais fazem (LC 965/2017, art. 90, parágrafo único)", "", "funções comuns às dez secretarias executivas regionais, em síntese",
      FUNCOES_SER.map((f, i) => [["I", "II", "III", "IV", "V", "VI", "VII", "VIII"][i], f]).concat([["Vínculo", "subordinadas ao Gabinete do Governador (art. 87, II); sem unidade orçamentária própria: a SUGESP paga"]]), LK_REG)], {limite: 12});
}
function mapa(U) {
  const cont = $("#graf"); cont.innerHTML = "";
  const w = cont.clientWidth || 600, h = cont.clientHeight || 420;
  const reg = new Map();
  U.forEach(u => (u.municipios || []).forEach(m => reg.set(normMun(m), u)));
  const feats = D.geo.features;
  let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
  const anel = f => f.geometry.type === "Polygon" ? f.geometry.coordinates : f.geometry.coordinates.flat();
  feats.forEach(f => anel(f).forEach(r => r.forEach(([x, y]) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); })));
  const kx = Math.cos((y0 + y1) / 2 * Math.PI / 180), esc_ = Math.min((w - 20) / ((x1 - x0) * kx), (h - 20) / (y1 - y0));
  const px = ([x, y]) => [10 + (x - x0) * kx * esc_, 10 + (y1 - y) * esc_];
  const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", `0 0 ${w} ${h}`); s.setAttribute("class", "mapa"); s.style.width = "100%"; s.style.height = "100%"; cont.append(s);
  const vs = U.filter(u => u.codigo !== "COOREG").map(u => u.total_2026), max = Math.max(...vs), min = Math.min(...vs);
  const grupos = new Map();
  feats.forEach(f => {
    const u = reg.get(normMun(f.properties.nome)); const k = u ? u.codigo : "sem";
    if (!grupos.has(k)) grupos.set(k, {g: el(s, "g", {class: "reg alvo"}), u});
    const d = anel(f).map(r => "M" + r.map(p => px(p).map(v => v.toFixed(1)).join(",")).join("L") + "Z").join("");
    const pct = u ? 22 + 78 * (u.total_2026 - min) / (max - min || 1) : 0;
    const p = el(grupos.get(k).g, "path", {d, fill: u ? `color-mix(in srgb, var(--c1) ${pct.toFixed(0)}%, transparent)` : "var(--hair)"});
    if (u) dica(p, `${f.properties.nome} · ${u.nome.replace(/\s*\(.*/, "")}`, [["Sede", u.sede], ["Custo da regional em 2026", mi(u.total_2026)], ["Servidores", br(u.servidores)]], "Clique para ver a regional");
  });
  grupos.forEach(({g, u}) => {
    if (!u) return;
    g.addEventListener("click", () => { regSel = u; foco(s, g); provasRegionais([...R.unidades].sort((a, b) => b.total_2026 - a.total_2026), u); });
    const sede = feats.find(f => normMun(f.properties.nome) === normMun(u.sede));
    if (!sede) return;
    const ps = anel(sede).flat().map(px), cx = (Math.min(...ps.map(p => p[0])) + Math.max(...ps.map(p => p[0]))) / 2, cy = (Math.min(...ps.map(p => p[1])) + Math.max(...ps.map(p => p[1]))) / 2;
    el(s, "text", {x: cx, y: cy + 4, "text-anchor": "middle"}, u.nome.replace(/\s*\(.*/, "").replace("SER ", ""));
  });
}

// ---------- 7. método
function telaMetodo() {
  esq({kicker: "Fonte e método", titulo: "De onde vem cada número e como foi contado", n: "", s: `Dado público, conferido fonte a fonte. Folha de ${M.coleta.folha}; pagamentos até ${DATA_PAG}; RGF de ${M.coleta.rgf}. Todo número do painel abre a própria prova ao ser clicado.`,
    corpo: `<ol class="metodo">${M.regras.map(r => `<li>${r}</li>`).join("")}<li>Só o Poder Executivo: Legislativo, Judiciário, Ministério Público, TCE e Defensoria ficam de fora (em 2026 pagaram ${mi(Object.values(M.outros_poderes).reduce((a, v) => a + v, 0))} nos mesmos tipos de despesa).</li>
      <li>2025 × 2026: sempre o mesmo período (1º/01 a ${CP.ate}) nos dois anos; o ano inteiro de 2026 aparece só como estimativa.</li></ol>`,
    fonte: "Leitura de dado público, não é auditoria.", dados: ["veiculos-2026", "imoveis-2026", "consumo-2026", "servidores-orgao", "rgf", "contratos-vencem", "regionais"],
    padrao: () => { $("#aviso").hidden = true; mostraProvas("As fontes, com o endereço oficial para conferir.", [...M.fontes.map(f => pr(f[0], "", f[2], [], [f[0], f[1]])), pr("Lei de Responsabilidade Fiscal", "", "limites da despesa com pessoal (arts. 19, 20, 22 e 59)", [], LK.lrf)], {limite: 10}); }});
}

const TELAS = [{curto: "Decidir", f: telaDecidir}, {curto: "Folha", f: telaFolha}, {curto: "Servidores", f: telaOrgaos}, {curto: "Secretarias", f: telaSecretarias},
  {curto: "Veículos", f: telaVeiculos}, {curto: "Imóveis", f: telaImoveis}, {curto: "Contas", f: telaConsumo}, {curto: "Estradas", f: telaEstradas, cheia: true}, {curto: "2025 × 2026", f: telaComparativo},
  {curto: "Regionais", f: telaRegionais}, {curto: "Organograma", f: telaOrganograma, cheia: true}];
$("#trilha").innerHTML = TELAS.map((t, i) => `<button class="passo" type="button"><b>${i}</b><span>${t.curto}</span></button>`).join("")
  + `<span class="meta"><span title="pagamentos até ${DATA_PAG}">até ${DATA_PAG.slice(0, 5)}</span><button class="tema" id="tema" type="button" aria-label="Claro ou escuro">◐</button></span>`;
$("#trilha").querySelectorAll(".passo").forEach((p, i) => p.onclick = () => ir(i));
function ir(i) {
  atual = Math.max(0, Math.min(TELAS.length - 1, i));
  $("#trilha").querySelectorAll(".passo").forEach((p, j) => { p.classList.toggle("on", j === atual); p.classList.toggle("visto", j < atual); });
  $("#aviso").hidden = true; $("#aviso").innerHTML = "";
  history.replaceState(null, "", "#" + atual);
  $("#tela").classList.toggle("cheia", !!TELAS[atual].cheia);
  TELAS[atual].f();
}
$("#tema").addEventListener("click", () => {
  const r = document.documentElement, escuro = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = escuro ? "light" : "dark";
  try { localStorage.setItem("tema-na", r.dataset.theme); } catch (e) {}
  TELAS[atual].f();
});
try { const t = localStorage.getItem("tema-na"); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
addEventListener("keydown", e => { if (e.key === "Escape") { fechaPainel(); fechaDados(); } if (!e.target.closest("input")) { if (e.key === "ArrowRight") ir(atual + 1); if (e.key === "ArrowLeft") ir(atual - 1); } });
let pend; addEventListener("resize", () => { clearTimeout(pend); pend = setTimeout(() => TELAS[atual].f(), 150); });
ir(parseInt(location.hash.slice(1)) || 0);
