
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const br = (x, d = 0) => x.toLocaleString("pt-BR", {minimumFractionDigits: d, maximumFractionDigits: d});
const fmt = mi => {
  const a = Math.abs(mi);
  if (a < .0005) return "R$ 0";
  if (a >= 1000) return "R$ " + br(mi / 1000, 2) + " bi";
  if (a >= 1) return "R$ " + br(mi, a >= 100 ? 0 : 1) + " mi";
  return "R$ " + br(Math.round(mi * 1000)) + " mil";
};
const exato = mi => "R$ " + br(mi * 1e6, 2);
const pct = x => br(x, 1) + "%";
const L = D.links, NS = "http://www.w3.org/2000/svg";
const nomeDe = ug => (D.nomes?.[ug] || "").split(" · ")[0];
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const MESES_L = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"];
const semAcento = s => String(s || "").toUpperCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const quantil = (arr, q) => { const s = [...arr].sort((a, b) => a - b), p = (s.length - 1) * q, b = Math.floor(p); return s[b] + (s[Math.min(b + 1, s.length - 1)] - s[b]) * (p - b); };
const [diaC, horaC] = D.coletado_em.split(" ");

// ---------- dica ao passar o mouse
function dica(el, t, linhas, f) {
  el.dataset.t = t; el.dataset.l = (linhas || []).map(([a, b]) => a + "|" + b).join(";;"); el.dataset.f = f || "";
}
const caixa = $("#dica");
document.addEventListener("mousemove", e => {
  const el = e.target.closest("[data-t]");
  if (!el) { caixa.classList.remove("on"); return; }
  const ls = (el.dataset.l || "").split(";;").filter(Boolean).map(s => s.split("|"));
  caixa.innerHTML = `<div class="tt">${esc(el.dataset.t)}</div>${ls.map(([a, b]) => `<div class="ln"><span>${esc(a)}</span><b>${esc(b)}</b></div>`).join("")}${el.dataset.f ? `<div class="ff">${esc(el.dataset.f)}</div>` : ""}`;
  caixa.classList.add("on");
  const r = caixa.getBoundingClientRect();
  let x = e.clientX + 16, y = e.clientY + 16;
  if (x + r.width > innerWidth - 8) x = e.clientX - r.width - 16;
  if (y + r.height > innerHeight - 8) y = e.clientY - r.height - 16;
  caixa.style.left = Math.max(8, x) + "px"; caixa.style.top = Math.max(8, y) + "px";
});

// ---------- gráficos: colunas e barras, sempre com o valor escrito
function novoSvg(cont) {
  cont.innerHTML = "";
  const w = cont.clientWidth, h = cont.clientHeight, s = document.createElementNS(NS, "svg");
  s.setAttribute("viewBox", `0 0 ${w} ${h}`); cont.appendChild(s);
  return {s, w, h};
}
function el(pai, tag, at, txt) {
  const e = document.createElementNS(NS, tag);
  for (const k in at) e.setAttribute(k, at[k]);
  if (txt != null) e.textContent = txt;
  pai.appendChild(e); return e;
}
const semMov = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
function cresce(e, y0, y1, h1, atraso) {
  if (semMov()) { e.setAttribute("y", y1); e.setAttribute("height", h1); return; }
  const t0 = performance.now() + atraso;
  const p = t => { const k = Math.max(0, Math.min(1, (t - t0) / 700)), q = 1 - Math.pow(1 - k, 3); e.setAttribute("y", y0 + (y1 - y0) * q); e.setAttribute("height", h1 * q); if (k < 1) requestAnimationFrame(p); };
  requestAnimationFrame(p);
}
function alarga(e, w1, atraso) {
  if (semMov()) { e.setAttribute("width", w1); return; }
  const t0 = performance.now() + atraso;
  const p = t => { const k = Math.max(0, Math.min(1, (t - t0) / 700)), q = 1 - Math.pow(1 - k, 3); e.setAttribute("width", w1 * q); if (k < 1) requestAnimationFrame(p); };
  requestAnimationFrame(p);
}
function colunas(cont, itens, ref) {
  const {s, w, h} = novoSvg(cont), base = h - 24, alt = base - 26, n = itens.length, passo = w / n, bw = Math.min(58, passo * .62);
  const max = Math.max(...itens.map(i => i.partes.reduce((a, p) => a + p.v, 0)), 1e-9);
  el(s, "line", {x1: 0, x2: w, y1: base + .5, y2: base + .5, stroke: "var(--hair)"});
  if (ref) {
    const y = base - alt * ref.v / max;
    el(s, "line", {x1: 0, x2: w, y1: y, y2: y, stroke: "var(--cinza2)", "stroke-dasharray": "4 4"});
  }
  itens.forEach((it, i) => {
    const g = el(s, "g", {class: "alvo"}), X = i * passo + (passo - bw) / 2;
    el(g, "rect", {x: i * passo, y: 0, width: passo, height: base, fill: "transparent"});
    let acum = 0;
    it.partes.forEach((p, j) => {
      const hh = alt * p.v / max, r = el(g, "rect", {class: "b", x: X, y: base - acum, width: bw, height: 0, fill: p.cor, rx: 2});
      cresce(r, base - acum, base - acum - hh, hh, i * 45 + j * 200);
      acum += hh;
    });
    if (it.topo) el(g, "text", {x: X + bw / 2, y: base - acum - 7, "text-anchor": "middle", class: it.destaque ? "forte azul" : "mute"}, passo < 90 ? it.topo.replace("R$ ", "") : it.topo);
    el(g, "text", {x: X + bw / 2, y: base + 16, "text-anchor": "middle", class: it.destaque ? "forte" : "mute"}, it.rot);
    if (it.dica) dica(g, ...it.dica);
    if (it.clique) g.addEventListener("click", () => it.clique(g, s));
  });
  return s;
}
function barras(cont, itens, ref) {
  const {s, w, h} = novoSvg(cont), n = itens.length, linha = Math.min(40, h / n), rot = Math.min(190, w * .32), area = w - rot - 160;
  const max = Math.max(...itens.map(i => i.partes.reduce((a, p) => a + p.v, 0)), 1e-9);
  if (ref) {
    const x = rot + area * ref.v / max;
    el(s, "line", {x1: x, x2: x, y1: 0, y2: n * linha, stroke: "var(--cinza2)", "stroke-dasharray": "4 4"});
    el(s, "text", {x: x + 6, y: n * linha + 14, class: "mute"}, ref.rot);
  }
  itens.forEach((it, i) => {
    const g = el(s, "g", {class: "alvo"}), y = i * linha, bh = linha * .56;
    el(g, "rect", {x: 0, y, width: w, height: linha, fill: "transparent"});
    el(g, "text", {x: rot - 12, y: y + linha / 2 + 4, "text-anchor": "end", class: it.destaque ? "forte" : ""}, it.rot);
    let acum = 0;
    it.partes.forEach((p, j) => {
      const ww = area * p.v / max, r = el(g, "rect", {class: "b", x: rot + acum, y: y + (linha - bh) / 2, width: 0, height: bh, fill: p.cor, rx: 2});
      alarga(r, ww, i * 40 + j * 200); acum += ww;
    });
    el(g, "text", {x: rot + acum + 10, y: y + linha / 2 + 4, class: "forte"}, it.dir);
    if (it.dica) dica(g, ...it.dica);
    if (it.clique) g.addEventListener("click", () => it.clique(g, s));
  });
  return s;
}
const foco = (s, g) => s.querySelectorAll(".alvo").forEach(x => x.classList.toggle("apagado", !!g && x !== g));

// ---------- provas
function notaHtml(n) {
  const extra = [["CNPJ", n.cnpj], ["Tipo", n.tipo], ["Fonte", n.fonte], ["Programa", n.programa], ["Ação", n.acao], ["Modalidade", n.modalidade], ["Histórico", n.historico]].filter(([, v]) => v);
  return `<div class="nota"><div class="l1"><span class="cred">${esc(n.credor)}</span><span class="val">${fmt(n.valor)}</span></div>
    <div class="l2">${esc(n.l2)}</div>
    <dl class="rastro">${extra.map(([k, v]) => `<dt>${k}</dt><dd>${esc(v)}</dd>`).join("")}<dt>Nota</dt><dd><a href="${n.link}" target="_blank" rel="noopener">abrir no Portal da Transparência ↗</a></dd></dl></div>`;
}
function provaHtml(p, i) {
  return `<div class="prova">
    <button class="pv-cab" type="button"><span class="i">${i + 1}</span><span class="nome">${esc(p.nome)}${p.sub ? `<small>${esc(p.sub)}</small>` : ""}</span><span class="v">${esc(p.valor)}</span><span class="seta">▶</span></button>
    ${p.barra != null ? `<div class="pv-barra"><i style="width:${Math.max(1, 100 * p.barra)}%"></i></div>` : ""}
    <div class="pv-det">${(p.linhas || []).map(([k, v]) => `<div class="linha"><span>${esc(k)}</span><b>${esc(v)}</b></div>`).join("")}
      ${(p.notas || []).map(notaHtml).join("")}
      ${p.link ? `<a class="link-fonte" href="${p.link[1]}" target="_blank" rel="noopener">${esc(p.link[0])} ↗</a>` : ""}</div></div>`;
}
function ligaProvas(cont) {
  cont.querySelectorAll(".pv-cab").forEach(b => b.onclick = () => b.parentElement.classList.toggle("aberta"));
  cont.querySelectorAll(".nota").forEach(n => n.onclick = e => { if (!e.target.closest("a")) n.classList.toggle("aberta"); });
}
function mostraProvas(sub, lista, opc = {}) {
  $("#provas-sub").textContent = sub;
  const f = $("#filtro");
  f.classList.toggle("on", !!opc.filtro);
  f.innerHTML = opc.filtro ? `Filtro: ${esc(opc.filtro)}<button type="button">✕ limpar</button>` : "";
  if (opc.filtro) f.querySelector("button").onclick = opc.limpar;
  const vis = lista.slice(0, opc.limite || 5);
  $("#provas").innerHTML = `<div class="entra">${vis.map(provaHtml).join("")}</div>`
    + (opc.todas && opc.todas.length > vis.length ? `<button class="ver-todas" type="button">Ver todas (${opc.todas.length}) com busca →</button>` : "");
  ligaProvas($("#provas"));
  if (opc.abrir != null) $("#provas").querySelectorAll(".prova")[opc.abrir]?.classList.add("aberta");
  const v = $("#provas .ver-todas"); if (v) v.onclick = () => abrePainel(opc.tituloTodas || sub, opc.todas);
}
function abrePainel(tit, lista) {
  $("#painel-tit").textContent = tit;
  const busca = $("#painel-busca"); busca.value = "";
  const desenha = () => {
    const q = semAcento(busca.value.trim());
    const ls = lista.filter(p => !q || semAcento([p.nome, p.sub, ...(p.notas || []).map(n => n.credor + " " + (n.cnpj || ""))].join(" ")).includes(q));
    $("#painel-lista").innerHTML = ls.map(provaHtml).join("") || `<p style="color:var(--mute)">Nada encontrado.</p>`;
    ligaProvas($("#painel-lista"));
  };
  busca.oninput = desenha; desenha();
  $("#painel").classList.add("on"); $("#cortina").classList.add("on"); $("#painel").setAttribute("aria-hidden", "false");
  setTimeout(() => busca.focus(), 300);
}
function fechaPainel() { $("#painel").classList.remove("on"); $("#cortina").classList.remove("on"); $("#painel").setAttribute("aria-hidden", "true"); }
$("#painel-x").onclick = fechaPainel; $("#cortina").onclick = fechaPainel;

// nota detalhada do build: [link, credor, tipo, emp, liq, sem, data, histórico, fonte, ação, programa, cnpj, modalidade]
const notaDet = x => ({credor: x[1], valor: x[5], l2: `${x[6]} · empenho ${String(x[2] || "").toLowerCase()} · ${fmt(x[3])} empenhado · ${fmt(x[4])} entregue`,
  cnpj: x[11], tipo: String(x[2] || "").toLowerCase(), fonte: x[8], programa: x[10], acao: x[9], modalidade: x[12], historico: x[7], link: L.detalhe + x[0], data: x[6], mes: +String(x[6]).slice(3, 5)});


// ---------- dados de origem: tabela paginada com busca, ordenação e CSV
let idsAtuais = [];
const TB = D.tabelas || {};
const fmtR = v => typeof v === "number" ? "R$ " + br(v, 2) : esc(v);
const chaveData = s => { const m = String(s).match(/(\d{2})\/(\d{2})\/(\d{4})/); return m ? m[3] + m[2] + m[1] : String(s); };
function celula(v, tipo) {
  if (tipo === "r") return fmtR(v);
  if (tipo === "n") return typeof v === "number" ? br(v) : esc(v);
  if (tipo === "l") return v ? `<a href="${L.detalhe}${v}" target="_blank" rel="noopener">nota ↗</a>` : "";
  if (tipo === "u") return String(v).startsWith("http") ? `<a href="${v}" target="_blank" rel="noopener">abrir ↗</a>` : esc(v);
  return esc(v);
}
function abreDados(ids, qual = 0) {
  const T = ids.map(i => TB[i]).filter(Boolean); if (!T.length) return;
  let t = T[qual], pag = 0, ord = -1, asc = false, q = "";
  const POR = 25, tab = $("#dados-tab");
  const soAnos = T.every(x => /^\d{4}$/.test(x.curto || ""));
  $("#dados-abas").innerHTML = T.length > 1 ? `<div class="alterna" style="margin:0"><span class="rot">${soAnos ? "Escolha o ano:" : "Escolha a tabela:"}</span>${T.map((x, i) => `<button type="button" class="${i === qual ? "on" : ""}">${esc(x.curto || x.titulo)}</button>`).join("")}</div>` : "";
  $("#dados-abas").querySelectorAll("button").forEach((b, i) => b.onclick = () => abreDados(ids, i));
  $("#dados-tit").textContent = t.titulo;
  const [dc, hc] = String(t.coletado_em || "").split(" ");
  $("#dados-ficha").innerHTML = [["Quem publica", t.fonte], ["Registros", br(t.linhas.length)], ["Coletado em", (dc || "").split("-").reverse().join("/") + (hc ? " às " + hc : "")], ["Conferir na fonte", `<a href="${t.url}" target="_blank" rel="noopener">abrir o endereço original ↗</a>`]]
    .map(([k, v]) => `<div><div class="k">${k}</div><div class="v">${k === "Conferir na fonte" ? v : esc(v)}</div></div>`).join("")
    + `<div class="larga" style="grid-column:1/-1"><div class="k">Consulta usada</div><div class="v">${esc(t.consulta)}</div><div style="margin-top:4px"><code>${esc(t.url)}</code></div></div>`;
  $("#dados-nota").textContent = t.nota || "";
  $("#dados-nota").style.display = t.nota ? "block" : "none";
  const linhasF = () => {
    let ls = q ? t.linhas.filter(r => semAcento(r.join(" ")).includes(q)) : t.linhas;
    if (ord >= 0) {
      const tipo = t.colunas[ord][1];
      ls = [...ls].sort((a, b) => { let x = a[ord], y = b[ord]; if (tipo === "d") { x = chaveData(x); y = chaveData(y); } return (asc ? 1 : -1) * ((x > y) - (x < y)); });
    }
    return ls;
  };
  const desenha = () => {
    const ls = linhasF(), np = Math.max(1, Math.ceil(ls.length / POR)); pag = Math.min(pag, np - 1);
    const vis = ls.slice(pag * POR, pag * POR + POR);
    const longos = t.colunas.map((c, i) => c[1] === "t" && t.linhas.slice(0, 200).some(r => String(r[i]).length > 28));
    const li = t.colunas.findIndex(c => c[1] === "l" || c[1] === "u");
    const alvo = li < 0 ? -1 : [t.colunas.findIndex(c => c[0] === "Nota" || c[0] === "Número"), t.colunas.findIndex(c => c[0] === "Órgão"), 0].find(x => x >= 0);
    const ia = t.colunas.findIndex(c => c[0] === "Ação de governo"), ifo = t.colunas.findIndex(c => c[0] === "Fonte do recurso");
    const cols = t.colunas.map((c, i) => i).filter(i => i !== li && i !== ia && t.colunas[i][1] !== "h");
    const hrefDe = r => { const v = r[li]; if (!v) return ""; if (t.colunas[li][1] === "l") return L.detalhe + v; return String(v).startsWith("http") ? v : ""; };
    const cel = (r, i) => {
      if (i === alvo) { const hr = hrefDe(r); return hr ? `<a href="${hr}" target="_blank" rel="noopener" title="Abrir na fonte oficial">${esc(r[i])} ↗</a>` : `${esc(r[i])}${li >= 0 && r[li] ? `<small style="display:block;color:var(--mute)">${esc(r[li])}</small>` : ""}`; }
      const nome = t.colunas[i][0];
      if (nome === "Ano") return String(r[i]);
      if (nome === "Mês" && typeof r[i] === "number") return MESES[r[i] - 1] || String(r[i]);
      return celula(r[i], t.colunas[i][1]);
    };
    tab.innerHTML = `<table><thead><tr>${cols.map(i => { const [n, tp] = t.colunas[i]; return `<th class="${tp === "r" || tp === "n" ? "r " : ""}${i === ord ? "ord" + (asc ? " asc" : "") : ""}" data-i="${i}">${esc(n)}${i === alvo ? " ↗" : ""}</th>`; }).join("")}</tr></thead>
      <tbody>${vis.map(r => `<tr>${cols.map(i => `<td class="${t.colunas[i][1] === "r" || t.colunas[i][1] === "n" ? "r" : longos[i] ? "longo" : ""}"${longos[i] ? ` title="${esc(r[i])}${i === ifo && ia >= 0 ? " · Ação: " + esc(r[ia]) : ""}"` : ""}>${cel(r, i)}</td>`).join("")}</tr>`).join("") || `<tr><td colspan="${cols.length}">Nada encontrado.</td></tr>`}</tbody></table>`;
    tab.querySelectorAll("th").forEach(th => th.onclick = () => { const i = +th.dataset.i; asc = i === ord ? !asc : false; ord = i; pag = 0; desenha(); });
    $("#dados-cont").textContent = `${br(ls.length)} registros${q ? " encontrados" : ""}`;
    const nums = [...new Set([0, 1, pag - 1, pag, pag + 1, np - 2, np - 1].filter(x => x >= 0 && x < np))].sort((a, b) => a - b);
    let html = `<button type="button" data-p="${pag - 1}" ${pag === 0 ? "disabled" : ""}>←</button>`, ant = -1;
    nums.forEach(x => { if (x - ant > 1) html += `<span>…</span>`; html += `<button type="button" data-p="${x}" class="${x === pag ? "on" : ""}">${x + 1}</button>`; ant = x; });
    html += `<button type="button" data-p="${pag + 1}" ${pag >= np - 1 ? "disabled" : ""}>→</button><span class="esp"></span><span>Página ${pag + 1} de ${np} · ${POR} por página</span>`;
    $("#dados-pag").innerHTML = html;
    $("#dados-pag").querySelectorAll("button[data-p]").forEach(b => b.onclick = () => { pag = +b.dataset.p; desenha(); tab.scrollTop = 0; });
  };
  const busca = $("#dados-busca"); busca.value = "";
  busca.oninput = () => { q = semAcento(busca.value.trim()); pag = 0; desenha(); };
  $("#dados-csv").onclick = () => {
    const ls = linhasF(), sep = ";", cel = v => `"${String(v ?? "").replace(/"/g, '""')}"`;
    const csv = [t.colunas.map(c => cel(c[0])).join(sep), ...ls.map(r => r.map((v, i) => cel(t.colunas[i][1] === "l" && v ? L.detalhe + v : typeof v === "number" ? String(v).replace(".", ",") : v)).join(sep))].join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["\ufeff" + csv], {type: "text/csv;charset=utf-8"}));
    a.download = t.id + ".csv"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  };
  desenha();
  $("#dados").classList.add("on"); $("#cortina").classList.add("on"); $("#dados").setAttribute("aria-hidden", "false");
}
function fechaDados() { $("#dados").classList.remove("on"); $("#dados").setAttribute("aria-hidden", "true"); if (!$("#painel").classList.contains("on")) $("#cortina").classList.remove("on"); }
$("#dados-x").onclick = fechaDados;
$("#cortina").addEventListener("click", fechaDados);
$("#btn-dados").onclick = () => abreDados(idsAtuais);


document.addEventListener("click", (ev) => document.querySelectorAll("details.docs[open]").forEach((d) => { if (!d.contains(ev.target)) d.removeAttribute("open"); }));
document.addEventListener("keydown", (ev) => { if (ev.key === "Escape") document.querySelectorAll("details.docs[open]").forEach((d) => d.removeAttribute("open")); });
