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
const COR_TEMA = {"Combustível": "var(--c1)", "Locação de veículos": "var(--c2)", "Manutenção de veículos": "var(--c3)", "Aluguel de imóveis": "var(--c4)"};
const CHAVE_TEMA = {"Combustível": "combustivel", "Locação de veículos": "locacao", "Manutenção de veículos": "manutencao", "Aluguel de imóveis": "imovel"};
const NOME_CHAVE = Object.fromEntries(Object.entries(CHAVE_TEMA).map(([n, k]) => [k, n]));
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
  (o.estat || []).forEach(([k, , p], i) => { if (p) $(`#esq [data-pe="${i}"]`).onclick = e => prova(e.currentTarget, p, k); });
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
  esq({kicker: "Para a equipe de transição", titulo: "O que dá para decidir em 2027", n: "", s: "Seis pontos tirados dos números deste painel. Clique em cada um para ver a prova e abrir a fonte oficial.",
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
    n: mi(G.bruta), s: `em 12 meses (${G.periodo}), pelo Relatório de Gestão Fiscal<br><b>${mi(t.bruto)}</b> brutos em outubro de 2026 para <b>${br(t.matriculas)}</b> matrículas`,
    provaN: provaRgf("Despesa bruta com pessoal", G.bruta, "Anexo 1, linha DESPESA BRUTA COM PESSOAL (I), coluna Total dos últimos 12 meses",
      [["Inclui", "ativos, aposentados, pensionistas, contribuição patronal e terceirização que conta como pessoal"], ["Outubro de 2026 (SEGEP)", mi(t.bruto) + " brutos, sem encargos"]]),
    estat: [["Salários dos ativos", mi(G.vencimentos), provaRgf("Salários dos ativos", G.vencimentos, "Anexo 1, Vencimentos, Vantagens e Outras Despesas Variáveis")],
      ["Contribuição patronal", mi(G.patronais), provaRgf("Contribuição patronal", G.patronais, "Anexo 1, Obrigações Patronais")],
      ["Aposentadorias e pensões", mi(G.inativos), provaRgf("Aposentadorias e pensões", G.inativos, "Anexo 1, Pessoal Inativo e Pensionistas")],
      ["% da receita (limite 49%)", br(hN.pct_rcl, 2) + "%", provaRgf("Despesa total com pessoal / RCL", hN.dtp, "Anexo 1, DTP (VI) % sobre a RCL Ajustada", [["Percentual", br(hN.pct_rcl, 2) + "%"], ["Alerta / prudencial / máximo", "44,1% / 46,55% / 49%"], ["Lei", "LRF, arts. 19, 20, 22 e 59"]])]],
    alterna: ["Ver:", ["Quem está na folha", "Limite da lei", "2023 a 2026", "Pessoas"], folhaVer, i => { folhaVer = i; telaFolha(); }],
    dicaUso: ["Bruto de outubro de 2026 por vínculo. Clique numa barra para ver em que órgãos esse vínculo está.",
      `Despesa total com pessoal sobre a receita corrente líquida, a conta da LRF. Faltam ${br(G.limites.alerta - hN.pct_rcl, 2)} pontos (${mi(margemAlerta)} por ano) para o limite de alerta.`,
      `Despesa total com pessoal em 12 meses, quadrimestre a quadrimestre: de ${mi(h0.dtp)} para ${mi(hN.dtp)} (${var_(h0.dtp, hN.dtp)}). Em cima, o percentual da receita.`,
      "Pessoas na folha de outubro de 2026, por vínculo."][folhaVer],
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
    n: br(t.ativos), s: `servidores ativos em <b>${M.unidades.length - 1} órgãos</b>, ${mi(t.bruto_ativos)} brutos no mês<br><b>${br(maisCom.length)} órgãos</b> têm mais comissionados sem vínculo que servidores de carreira`,
    provaN: pr("Servidores ativos", br(t.ativos), "uma pessoa por matrícula; aposentados e pensionistas fora", [["Matrículas na folha", br(t.matriculas)], ["Aposentados e pensionistas", br(t.inativos)], ["Afastados (entre os ativos)", br(t.afastados)], ["Sem unidade na planilha", br(t.sem_unidade)],
      ["Conferência", "O estudo de 10/11 (lista pública do Portal, regra pelo cargo) contou 49.023 ativos; a diferença são estagiários, voluntários, cedidos e pagamentos judiciais"]], LK.pessoal),
    estat: [["Efetivos civis", br(gp("efetivo").pessoas), provaGrupo("efetivo")], ["Militares", br(gp("militar").pessoas), provaGrupo("militar")], ["Temporários e CLT", br(gp("temporario").pessoas), provaGrupo("temporario")], ["Comissionados sem vínculo", br(gp("comissionado").pessoas), provaGrupo("comissionado")]],
    alterna: ["Ordenar por:", ["Pessoas", "Valor do mês", "% de comissionados"], orgOrdem, i => { orgOrdem = i; telaOrgaos(); }],
    legenda: legenda(GRUPOS.slice(0, 6).map(g => [g.nome.replace(" e comissionados de outros entes", ""), COR_GRUPO[g.grupo]])),
    dicaUso: orgOrdem === 2 ? "Peso dos comissionados sem vínculo no quadro de cada órgão (órgãos com 20 servidores ou mais). Clique num órgão para abrir." : "Os 18 maiores órgãos, por vínculo. Clique num órgão para ver os números dele; a lista completa está em As provas.",
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
const TEMAS_V = ["Combustível", "Locação de veículos", "Manutenção de veículos"];
function telaVeiculos() {
  const temas = veicTema ? [TEMAS_V[veicTema - 1]] : TEMAS_V, ks = temas.map(t => CHAVE_TEMA[t]);
  const ano = ks.reduce((a, k) => a + C[k].ano_2026, 0), pago = ks.reduce((a, k) => a + C[k].pago_2026, 0), a25 = ks.reduce((a, k) => a + C[k].anos["2025"], 0);
  const cartao = pagoA(/PRIME CONSULT|UZZIPAY|LINK CARD|NEO CONSULT/i);
  const ls = PV.filter(r => temas.includes(r[4]));
  esq({kicker: "Veículos do Estado · Poder Executivo", titulo: "Quanto custam os carros do Estado em 2026",
    n: mi(ano), s: `em 2026 com ${veicTema ? temas[0].toLowerCase() : "combustível, locação e manutenção"}: <b>${mi(pago)}</b> pagos até ${DATA_PAG} e projeção até dezembro<br>Em 2025, o ano inteiro: <b>${mi(a25)}</b>`,
    provaN: pr("Veículos em 2026", mi(ano), `soma de ${temas.join(", ").toLowerCase()}`, [["Pago até " + DATA_PAG, "R$ " + br(pago, 2)], ["Projeção nov e dez", mi(ano - pago)], ["Pagamentos", br(ls.length)],
      ["Fora da conta", "transporte escolar (3.3.90.39.93), combustível de aviação e aeronaves, e os outros Poderes"]], LK.pag),
    estat: [...TEMAS_V.map(t => [t, mi(C[CHAVE_TEMA[t]].ano_2026), provaTema(CHAVE_TEMA[t])]),
      ["Cartões (Prime, Uzzipay e outras)", `${mi(cartao)} pagos`, pr("Gerenciadoras de cartão", mi(cartao), `pago em 2026 até ${DATA_PAG}, só Executivo`, [["Prime", mi(pagoA(/PRIME CONSULT/i))], ["Uzzipay", mi(pagoA(/UZZIPAY/i))], ["Link Card e Neo", mi(pagoA(/LINK CARD|NEO CONSULT/i))],
        ["Por que é mais que o empenhado", "Nas notas estimativas de cartão o portal não soma o reforço no empenhado; o pago soma."]], LK.pag, M.cartao.map(notaContrato))]],
    alterna: ["Mostrar:", ["Tudo", ...TEMAS_V], veicTema, i => { veicTema = i; telaVeiculos(); }],
    legenda: legenda(temas.map(t => [t, COR_TEMA[t]]).concat([["projeção (nov e dez)", "var(--hair)"]])),
    dicaUso: `Pago a cada mês de 2026; nov e dez em tom claro completam o ano pela média de agosto a outubro. Clique num mês para ver quem gastou.`,
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores, 01/01 a ${DATA_PAG}, pelo subelemento da despesa`, dados: ["veiculos-2026", "contratos-vencem"], padrao: () => provasPag(ls)});
  colunas($("#graf"), MESES.map((m, i) => ({rot: m, partes: temas.flatMap(t => {
      const k = CHAVE_TEMA[t], pg = C[k].pago_mensal_2026[i], tot = C[k].mensal_2026[i];
      return [{v: pg, cor: COR_TEMA[t]}, {v: Math.max(tot - pg, 0), cor: claro(COR_TEMA[t])}]; }),
    topo: mi(temas.reduce((a, t) => a + C[CHAVE_TEMA[t]].mensal_2026[i], 0)), destaque: i + 1 === MES_PAG,
    dica: [`${MESES_L[i]} de 2026`, temas.map(t => [t, mi(C[CHAVE_TEMA[t]].pago_mensal_2026[i])]).concat(i + 1 >= MES_PAG ? [["Projeção", mi(temas.reduce((a, t) => a + C[CHAVE_TEMA[t]].mensal_2026[i] - C[CHAVE_TEMA[t]].pago_mensal_2026[i], 0))]] : []), "Clique para ver quem gastou no mês"],
    clique: (g, s) => { foco(s, g); provasPag(ls.filter(r => mesDe(r[0]) === i + 1), `Pagos em ${MESES_L[i]}`, () => { foco(s, null); provasPag(ls); }); }})));
}
function provasPag(ls, filtro, limpar, imovel) {
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
  const txt = porOrgao ? "Órgãos que mais pagaram. Clique para ver os valores, quem recebeu e conferir no portal." : "Quem mais recebeu. Pessoa física aparece somada, sem nome.";
  $("#aviso").hidden = false;
  $("#aviso").innerHTML = `<div class="alterna" style="margin:0"><span class="rot">Provas por:</span>${["Órgão", imovel ? "Locador" : "Empresa"].map((t, i) => `<button type="button" class="${i === (imovel ? imovPor : veicPor) ? "on" : ""}">${t}</button>`).join("")}</div>`;
  $("#aviso").querySelectorAll("button").forEach((b, i) => b.onclick = () => { if (imovel) imovPor = i; else veicPor = i; provasPag(ls, filtro, limpar, imovel); });
  mostraProvas(filtro ? `${filtro}. ${txt}` : txt, lista, {filtro, limpar, todas: lista, tituloTodas: imovel ? "Aluguel de imóveis em 2026" : "Veículos em 2026", limite: 6});
}

let imovPor = 0;
function telaImoveis() {
  const c = C.imovel, i = M.imoveis;
  const gs = agrupa(PI, r => r[1]);
  esq({kicker: "Imóveis alugados · Poder Executivo", titulo: "Quanto o Estado gasta com aluguel e quantos imóveis aluga",
    n: mi(c.ano_2026), s: `em 2026 com aluguel de <b>${br(i.locadores)} imóveis</b> em <b>${br(i.orgaos_total)} órgãos</b><br><b>${mi(c.pago_2026)}</b> pagos até ${DATA_PAG} · em 2025: <b>${mi(c.anos["2025"])}</b> (${br(i.locadores_2025)} imóveis)`,
    provaN: provaTema("imovel"),
    estat: [["Imóveis alugados", br(i.locadores), pr("Imóveis alugados em 2026", br(i.locadores), "locadores diferentes pagos, órgão a órgão", [["Regra", "cada locador (CPF ou CNPJ) pago por um órgão conta um imóvel; quem aluga dois ao mesmo órgão conta um, então o número é piso"], ["Em 2025", br(i.locadores_2025)]], LK.pag)],
      ["De pessoas físicas", `${br(i.pf)} · ${mi(i.pf_valor)}`, pr("Aluguel pago a pessoas físicas", mi(i.pf_valor), `${br(i.pf)} imóveis`, [["Subelemento", "3.3.90.36.15 · locação de imóveis (pessoa física)"], ["Nomes", "não aparecem no painel; estão no portal"]], LK.pag)],
      ["De empresas", `${br(i.pj)} · ${mi(i.pj_valor)}`, pr("Aluguel pago a empresas", mi(i.pj_valor), `${br(i.pj)} imóveis`, [["Subelemento", "3.3.90.39.10 · locação de imóveis (pessoa jurídica)"]], LK.pag)],
      ["Contratos que vencem até 2027", br(VENCE27.filter(x => x.tipo === "imovel").length), pr("Contratos de aluguel que vencem até 31/12/2027", mi(VENCE27.filter(x => x.tipo === "imovel").reduce((a, x) => a + x.valor, 0)), "valor contratado, vigência publicada no portal", [], LK.contratos, VENCE27.filter(x => x.tipo === "imovel").map(notaContrato))]],
    dicaUso: "Pago em 2026 por órgão. Clique num órgão para ver quem são os locadores.",
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores, 01/01 a ${DATA_PAG}, subelementos de locação de imóveis`, dados: ["imoveis-2026", "contratos-vencem"], padrao: () => { imovPor = 0; provasPag(PI, null, null, true); }});
  barras($("#graf"), gs.slice(0, 16).map(g => {
    const n = new Set(g.ls.map(r => r[2] === "Pessoa física" ? "pf" + r[6] : r[2])).size;
    return {rot: g.k, partes: [{v: g.total, cor: "var(--c4)"}], dir: `${mi(g.total)} · ${br(n)} imóve${n > 1 ? "is" : "l"}`,
      dica: [D.nomes[g.k] || g.k, [["Pago em 2026", mi(g.total)], ["Imóveis (locadores)", br(n)]], "Clique para ver os locadores"],
      clique: (el_, s) => { foco(s, el_); imovPor = 1; provasPag(g.ls, `Aluguel pago pelo ${g.k}`, () => { foco(s, null); imovPor = 0; provasPag(PI, null, null, true); }, true); }};
  }));
}

// ---------- 5. 2025 × 2026 no mesmo período
let compVer = 0;
const TEMAS_C = ["combustivel", "locacao", "manutencao", "imovel"];
const seta = (a, b) => { if (!a) return "—"; const p = 100 * (b - a) / a, cor = Math.abs(p) < 1 ? "var(--mute)" : p > 0 ? "var(--c3)" : "var(--c2)";
  return `<span style="color:${cor}">${Math.abs(p) < 1 ? `≈ praticamente igual (${p >= 0 ? "+" : "−"}${br(Math.abs(p), 1)}%)` : `${p > 0 ? "▲" : "▼"} ${br(Math.abs(p), 0)}% a ${p > 0 ? "mais" : "menos"}`}</span>`; };
const fraseVar = (a, b) => { const p = 100 * (b - a) / a; return Math.abs(p) < 3 ? "quase o mesmo que" : `${br(Math.abs(p), 0)}% a ${p > 0 ? "mais" : "menos"} que`; };
function telaComparativo() {
  const v = k => [CP.temas[k]?.["2025"] || 0, CP.temas[k]?.["2026"] || 0];
  const s25 = TEMAS_C.reduce((a, k) => a + v(k)[0], 0), s26 = TEMAS_C.reduce((a, k) => a + v(k)[1], 0);
  const os = CP.orgaos.map(o => ({...o, a: TEMAS_C.reduce((x, k) => x + (o[k + "_2025"] || 0), 0), b: TEMAS_C.reduce((x, k) => x + (o[k + "_2026"] || 0), 0)})).filter(o => o.a + o.b > 0)
    .map(o => ({...o, d: o.b - o.a})).sort((x, y) => Math.abs(y.d) - Math.abs(x.d));
  const periodo = `1º de janeiro a ${CP.ate.slice(0, 2)} de novembro`;
  const provaTipo = k => pr(`${NOME_CHAVE[k]}: 2025 × 2026`, var_(...v(k)), `pago de ${periodo}, em cada ano, só Executivo`,
    [["2025", mi(v(k)[0])], ["2026", mi(v(k)[1])], ["Diferença", (v(k)[1] >= v(k)[0] ? "+" : "−") + mi(Math.abs(v(k)[1] - v(k)[0]))],
      ["Estimativa do ano inteiro", `2025: ${mi(C[k].anos["2025"])} · 2026: ${mi(C[k].ano_2026)} (com projeção de nov e dez)`]], LK.pag);
  esq({kicker: `Comparação justa: ${periodo}, nos dois anos`, titulo: `Em 2026 o Estado gastou ${fraseVar(s25, s26)} 2025 com carros e aluguel`,
    n: mi(s26), s: `pagos em 2026 com combustível, locação, manutenção e aluguel<br>No mesmo período de 2025 foram <b>${mi(s25)}</b> · ${seta(s25, s26)}`,
    provaN: pr("Como a comparação é feita", mi(s26), "mesmo período, mesma régua", [["Período", `${periodo} de 2025 e de 2026`], ["2025", mi(s25)], ["2026", mi(s26)],
      ["Régua", "pagamentos (ordens bancárias) pelo subelemento da despesa, só Executivo"],
      ["Por que não o ano inteiro", "2026 ainda não terminou. O ano inteiro de 2026 só existe como estimativa (com projeção de novembro e dezembro) e aparece dentro de cada tipo de gasto."]], LK.pag),
    estat: TEMAS_C.map(k => [NOME_CHAVE[k], `${seta(...v(k))}<div style="font-size:13px;font-weight:500;color:var(--mute);margin-top:2px">${mi(v(k)[0])} → ${mi(v(k)[1])}</div>`, provaTipo(k)]),
    alterna: ["Ver:", ["Por tipo de gasto", "Mês a mês"], compVer, i => { compVer = i; telaComparativo(); }],
    legenda: legenda([["2025", "var(--cinza)"], ["2026", "var(--c1)"]]),
    dicaUso: compVer ? `Quanto já tinha sido pago até o fim de cada mês, somados os quatro tipos de gasto. Em novembro, os dois anos param no dia ${CP.ate.slice(0, 2)}.`
      : `Cinza é 2025 e azul é 2026, sempre de ${periodo}. Clique numa barra para ver a conta. À direita, os órgãos que mais mudaram.`,
    fonte: `Fonte: Portal da Transparência RO, Pagamentos de fornecedores de 2025 e 2026, pelo subelemento da despesa`, dados: ["veiculos-2026", "imoveis-2026"], padrao: () => provasComp(os)});
  if (compVer === 0) colunas($("#graf"), TEMAS_C.flatMap(k => [
    {rot: NOME_CHAVE[k].replace(" de veículos", "").replace(" de imóveis", ""), partes: [{v: v(k)[0], cor: "var(--cinza)"}], topo: mi(v(k)[0]), dica: [`${NOME_CHAVE[k]} · 2025`, [["Pago de " + periodo, mi(v(k)[0])]]],
      clique: () => mostraProvas("A conta", [provaTipo(k)], {abrir: 0, filtro: NOME_CHAVE[k], limpar: () => provasComp(os)})},
    {rot: "", partes: [{v: v(k)[1], cor: "var(--c1)"}], topo: mi(v(k)[1]), destaque: true, dica: [`${NOME_CHAVE[k]} · 2026`, [["Pago de " + periodo, mi(v(k)[1])], ["Em relação a 2025", var_(...v(k))]]],
      clique: () => mostraProvas("A conta", [provaTipo(k)], {abrir: 0, filtro: NOME_CHAVE[k], limpar: () => provasComp(os)})}]));
  else colunas($("#graf"), MESES.slice(0, MES_PAG).flatMap((m, i) => {
    const a = TEMAS_C.reduce((x, k) => x + CP.acumulado[k]["2025"][i], 0), b = TEMAS_C.reduce((x, k) => x + CP.acumulado[k]["2026"][i], 0);
    return [{rot: m, partes: [{v: a, cor: "var(--cinza)"}], topo: "", dica: [`Até ${MESES_L[i]} de 2025`, [["Acumulado", mi(a)]]]},
      {rot: "", partes: [{v: b, cor: "var(--c1)"}], topo: i === MES_PAG - 1 ? mi(b) : "", destaque: i === MES_PAG - 1, dica: [`Até ${MESES_L[i]} de 2026`, [["Acumulado", mi(b)], ["Em relação a 2025", var_(a, b)]]]}];
  }));
}
function provasComp(os) {
  const max = Math.max(...os.map(o => Math.abs(o.d)), 1);
  const lista = os.map(o => ({nome: o.sigla, sub: `${D.nomes[o.sigla] || ""} · ${mi(o.a)} em 2025 → ${mi(o.b)} em 2026`,
    valor: `${o.d >= 0 ? "▲" : "▼"} ${mi(Math.abs(o.d))}`, barra: Math.abs(o.d) / max,
    linhas: [["2025", mi(o.a)], ["2026", mi(o.b)], ["Mudança", `${o.d >= 0 ? "gastou " + mi(o.d) + " a mais" : "gastou " + mi(-o.d) + " a menos"} (${var_(o.a, o.b)})`],
      ...TEMAS_C.filter(k => o[k + "_2025"] || o[k + "_2026"]).map(k => [NOME_CHAVE[k], `${mi(o[k + "_2025"] || 0)} → ${mi(o[k + "_2026"] || 0)}`])], link: LK.pag}));
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
    legenda: regVer === 0 ? legenda([["mais caro", "var(--c1)"], ["mais barato", "color-mix(in srgb, var(--c1) 22%, transparent)"]]) : "",
    dicaUso: regVer === 0 ? "Cada região com seus municípios; a cor mais forte é a de maior custo em 2026. Clique numa região. A coordenação (COOREG) fica em Porto Velho." :
      regVer === 1 ? "Custo estimado de 2026 por tipo de despesa, somadas as 11 unidades." : "Base de 2026 corrigida pelo IPCA do Focus de 09/11/2026, mantidos quadro, estrutura e contratos.",
    fonte: "Fonte: planilha de execução das regionais (v04, 13/11/2026), sobre o SIGEF da SUGESP (UG 110009), posição 12/11/2026", dados: ["regionais"], padrao: () => provasRegionais(U, regSel)});
  if (regVer === 0) mapa(U);
  else if (regVer === 1) barras($("#graf"), TIPOS_R.map((k, i) => ({rot: k.replace(" do imóvel", ""), partes: [{v: R.tipos[k]?.total_2026 || 0, cor: COR_R[i]}], dir: mi(R.tipos[k]?.total_2026), dica: [k, [["2026", mi(R.tipos[k]?.total_2026)], ["Por mês", mi(R.tipos[k]?.mensal)]]]})));
  else colunas($("#graf"), ["2026", "2027", "2028", "2029", "2030"].map(a => ({rot: a, partes: [{v: R.projecao.Total[a], cor: a === "2026" ? "var(--c1)" : claro("var(--c1)")}], topo: mi(R.projecao.Total[a]), destaque: a === "2026"})));
}
function provasRegionais(U, sel) {
  const max = U[0].total_2026;
  const lista = U.map(u => ({nome: u.codigo === "COOREG" ? "COOREG · Coordenação-Geral" : `${u.nome.replace(/\s*\(.*/, "")} · ${u.sede}`, sub: `${br(u.servidores)} servidores · ${br(u.veic_proprios + u.veic_locados)} veículos · ${u.municipios?.length > 1 ? br(u.municipios.length) + " municípios" : "atuação estadual"}`,
    valor: mi(u.total_2026), barra: u.total_2026 / max,
    linhas: [...TIPOS_R.filter(k => u.tipos[k]?.total_2026).map(k => [k, `${mi(u.tipos[k].total_2026)} · ${mi(u.tipos[k].mensal)}/mês`]), ["2027 a 2030", mi(Object.values(u.projecao).reduce((a, p) => a + p["2027"] + p["2028"] + p["2029"] + p["2030"], 0))],
      ...(u.municipios?.length > 1 ? [["Municípios", u.municipios.join(", ")]] : [])], link: LK_REG}));
  const i = sel ? U.indexOf(sel) : -1;
  if (i >= 0) mostraProvas(lista[i].nome, [lista[i]], {filtro: sel.codigo, limpar: () => { regSel = null; telaRegionais(); }, abrir: 0});
  else mostraProvas("As 11 unidades, da mais cara para a mais barata em 2026. Clique para ver por tipo de despesa.", lista, {limite: 11});
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
    fonte: "Leitura de dado público, não é auditoria.", dados: ["veiculos-2026", "imoveis-2026", "servidores-orgao", "rgf", "contratos-vencem", "regionais"],
    padrao: () => { $("#aviso").hidden = true; mostraProvas("As fontes, com o endereço oficial para conferir.", [...M.fontes.map(f => pr(f[0], "", f[2], [], [f[0], f[1]])), pr("Lei de Responsabilidade Fiscal", "", "limites da despesa com pessoal (arts. 19, 20, 22 e 59)", [], LK.lrf)], {limite: 10}); }});
}

const TELAS = [{curto: "O que decidir", f: telaDecidir}, {curto: "Folha", f: telaFolha}, {curto: "Servidores", f: telaOrgaos}, {curto: "Veículos", f: telaVeiculos},
  {curto: "Imóveis", f: telaImoveis}, {curto: "2025 × 2026", f: telaComparativo}, {curto: "Regionais", f: telaRegionais}, {curto: "Fontes", f: telaMetodo}];
$("#trilha").innerHTML = TELAS.map((t, i) => `<button class="passo" type="button"><b>${i}</b><span>${t.curto}</span></button>`).join("")
  + `<span class="meta"><span title="pagamentos até ${DATA_PAG}">até ${DATA_PAG.slice(0, 5)}</span><button class="tema" id="tema" type="button" aria-label="Claro ou escuro">◐</button></span>`;
$("#trilha").querySelectorAll(".passo").forEach((p, i) => p.onclick = () => ir(i));
function ir(i) {
  atual = Math.max(0, Math.min(TELAS.length - 1, i));
  $("#trilha").querySelectorAll(".passo").forEach((p, j) => { p.classList.toggle("on", j === atual); p.classList.toggle("visto", j < atual); });
  $("#aviso").hidden = true; $("#aviso").innerHTML = "";
  history.replaceState(null, "", "#" + atual);
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
