"""Gera o relatório em PDF da SEAS: orçamento, convênios e termos de fomento, e emendas executadas pela SEAS.

Uso: python3 convenios/build_relatorio.py   (depois de coleta_convenios.py SEAS)
Grava esbocos/relatorio-seas.html e .pdf, e site/relatorio-seas.pdf. O PDF sai do Chrome (impressão do HTML),
em duas passadas: a primeira descobre em que página cai cada seção, a segunda escreve esses números no sumário.
"""
import base64
import html
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TIPO_CURTO = {"Convênio": "Convênio", "Termo de Fomento": "Fomento", "Termo de Cooperação/Colaboração": "Cooperação"}
AZUL, AZUL_CLARO, NAVY, OURO, VERDE = "#1351b4", "#a9c1ea", "#0c2f6b", "#e5c800", "#1d8a3e"
AUTORIA = "NextTech Ecosystem"


def br(v, c=0):
    s = f"{v:,.{c}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def din(v):
    a = abs(v)
    if a >= 1e9:
        return f"R$ {br(v / 1e9, 2)} bi"
    if a >= 1e6:
        return f"R$ {br(v / 1e6, 1)} mi"
    if a >= 1e3:
        return f"R$ {br(v / 1e3, 0)} mil"
    return f"R$ {br(v, 0)}"


def rs(v):
    return "R$ " + br(v, 2)


def e(s):
    return html.escape(str(s or ""))


def anos_curto(ys):
    return str(ys[0]) if len(ys) == 1 else str(ys[0]) + " · " + " · ".join(str(y)[2:] for y in ys[1:])


def link_doc(r):
    docs = r.get("sei_docs") or []
    if docs:
        return f'<a class="doc" href="{e(docs[0]["url"])}">Abrir documento no SEI ↗</a>'
    if r.get("detalhe"):
        return f'<a class="doc" href="{e(r["detalhe"])}">Ver no portal ↗</a>'
    return ""


def ehmun(nome):
    return bool(re.search(r"MUNIC", nome or "", re.I))


def data_br(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{m[3]}/{m[2]}/{m[1]}" if m else (iso or "—")


def ordem_data(d):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d or "")
    return (m[3], m[2], m[1]) if m else ("9999", "", "")


def corta(s, n):
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def barras_ano(itens, destaque, altura=150, largura=640, cores=None):
    """Colunas por ano. itens: [(rótulo, [(valor, cor), ...] empilhados)]."""
    mx = max(sum(v for v, _ in partes) for _, partes in itens) or 1
    w = largura / len(itens)
    out = []
    for i, (rot, partes) in enumerate(itens):
        x, y0, tot = i * w + w * .2, altura + 14, sum(v for v, _ in partes)
        for v, cor in partes:
            h = v / mx * altura
            if h > 0:
                out.append(f'<rect x="{x:.1f}" y="{y0 - h:.1f}" width="{w * .6:.1f}" height="{h:.1f}" fill="{cor}"/>')
                y0 -= h
        out.append(f'<text x="{i * w + w / 2:.1f}" y="{y0 - 5:.1f}" class="sv{" sd" if rot == destaque else ""}">{din(tot).replace("R$" + chr(160), "")}</text>'
                   f'<text x="{i * w + w / 2:.1f}" y="{altura + 30}" class="sa{" sd" if rot == destaque else ""}">{rot}</text>')
    return (f'<svg viewBox="0 0 {largura} {altura + 36}" class="graf">{"".join(out)}'
            f'<line x1="0" y1="{altura + 14}" x2="{largura}" y2="{altura + 14}" stroke="#15171c" stroke-width=".8"/></svg>')


def montar(pg):
    """Monta o HTML. pg: páginas de cada âncora (vazio na primeira passada)."""
    bruto = json.loads((FONTE / "s4_convenios_seas.json").read_text(encoding="utf-8"))
    dia = "/".join(reversed(bruto["meta"]["coletado_em"][:10].split("-")))
    regs = [{**r, "ano": r["ano_consulta"], "valor": r["valor"] or 0, "rescisao": bool(re.search(r"RESCIS", r["numero"], re.I))} for r in bruto["dados"]]
    validos = [r for r in regs if not r["rescisao"]]
    total = sum(r["valor"] for r in validos)
    receb = defaultdict(list)
    for r in validos:
        receb[r["contratado"].strip()].append(r)
    mun = [r for r in validos if ehmun(r["contratado"])]
    ent = [r for r in validos if not ehmun(r["contratado"])]
    anos = sorted({r["ano"] for r in regs})
    soma_ano = {y: sum(r["valor"] for r in validos if r["ano"] == y) for y in anos}
    maior_ano = max(anos, key=soma_ano.get)
    n_resc = sum(r["rescisao"] for r in regs)
    n_adit = sum(r["tem_aditivo"] == "Sim" for r in regs)

    orc = {o["orgao"]: o for o in json.loads((FONTE / "s1_dados.json").read_text(encoding="utf-8"))["orgaos"]}
    area = [("SEAS", "Secretaria de Estado da Mulher, da Família, da Assistência e do Desenvolvimento Social", "SECRETARIA DE ESTADO DA MULHER, DA FAMILIA, DA ASSISTENCIA E DO DESENVOLVIMENTO SOCIAL"),
            ("FEAS", "Fundo Estadual de Assistência Social", "FUNDO ESTADUAL DE ASSISTENCIA SOCIAL"),
            ("FECOEP", "Fundo Estadual de Combate e Erradicação da Pobreza", "FUNDO ESTADUAL DE COMBATE E ERRADICACAO DA POBREZA DE RONDONIA"),
            ("FEDM", "Fundo Estadual dos Direitos da Mulher", "FUNDO ESTADUAL DOS DIREITOS DA MULHER")]
    orc_l = [(s, n, orc[k]) for s, n, k in area if k in orc]
    seas = orc_l[0][2]

    lib = json.loads((FONTE / "s1_lazy_emendas-liberacoes.json").read_text(encoding="utf-8"))
    dic = lib["dic"]
    em = [{"ano": r[0], "dep": dic["dep"][r[2]] if dic["dep"][r[2]] not in ("?", "") else "Não informado", "mun": (dic["mun"][r[3]] or "—").title(),
           "valor": r[5], "data": r[6], "oficio": r[7], "entidade": (r[8] or "—").strip(), "objeto": r[9] or "—"}
          for r in lib["rows"] if dic["sec"][r[4]] == "SEAS"]
    em_total = sum(x["valor"] for x in em)
    em_anos = sorted({x["ano"] for x in em})
    em_ent, em_dep = defaultdict(float), defaultdict(float)
    for x in em:
        em_ent[x["entidade"]] += x["valor"]
        em_dep[x["dep"]] += x["valor"]

    p = lambda k: pg.get(k, "")
    P = []
    a = P.append

    # ---------------- capa
    brasao = base64.b64encode((RAIZ / "vendor" / "simbolos" / "brasao-ro.png").read_bytes()).decode()
    a(f"""<section class="capa">
  <div class="faixa"><i style="background:{NAVY}"></i><i style="background:{OURO}"></i><i style="background:{VERDE}"></i></div>
  <div class="capa-corpo">
    <div class="capa-topo"><img src="data:image/png;base64,{brasao}" alt="Brasão do Estado de Rondônia"><div><b>Estado de Rondônia</b><span>Relatório com dados públicos</span></div></div>
    <div class="capa-meio">
      <div class="capa-k">Assistência social · 2019 a 2026</div>
      <h1>Convênios, termos de fomento e emendas da SEAS</h1>
      <p class="capa-sub">Quanto a Secretaria de Estado da Mulher, da Família, da Assistência e do Desenvolvimento Social repassou, para quem, e o que foi liberado em emendas parlamentares.</p>
      <div class="capa-nums">
        <div><b>{din(total)}</b><span>em {len(validos)} convênios e termos de fomento</span></div>
        <div><b>{len(receb)}</b><span>municípios e entidades receberam</span></div>
        <div><b>{din(em_total)}</b><span>em emendas executadas pela SEAS</span></div>
      </div>
    </div>
    <div class="capa-pe"><span>Posição dos dados: {dia}</span><span>Elaborado por <b>{AUTORIA}</b></span></div>
  </div>
</section>""")

    # ---------------- sumário (clicável, com páginas)
    secoes = [("s1", "Resumo"), ("s2", "Orçamento de 2026"), ("s3", "Convênios e termos de fomento, ano a ano"), ("s4", "Quem mais recebeu"),
              ("s5", "Todos os instrumentos, em ordem de assinatura"), ("s6", "Emendas parlamentares executadas pela SEAS"), ("s7", "Fontes, método e cuidados")]
    itens = []
    for i, (k, t) in enumerate(secoes, 1):
        itens.append(f'<li><a href="#{k}"><span class="sn">{i}</span><span class="st">{t}</span></a></li>')
        if k == "s5":
            itens.append('<li class="anos">' + "".join(f'<a href="#a{y}">{y}</a>' for y in anos) + "</li>")
        if k == "s6":
            itens.append('<li class="anos">' + "".join(f'<a href="#e{y}">{y}</a>' for y in em_anos) + "</li>")
    a(f'<section class="pagina sumario"><h2 class="sec-t">Sumário</h2><ol>{"".join(itens)}</ol>'
      f'<p class="nota">Clique num item para ir até ele. Todos os números vêm de fontes públicas, citadas em cada seção e detalhadas na seção 7. '
      f'Valores em reais correntes, sem correção pela inflação.</p></section>')

    # ---------------- 1 e 2
    top1 = max(receb.items(), key=lambda kv: sum(r["valor"] for r in kv[1]))
    a(f"""<section class="pagina" id="s1"><h2 class="sec-t"><span>1</span>Resumo</h2>
<div class="kpis">
  <div><b>{din(seas['orcado_atualizado'])}</b><span>orçamento da SEAS em 2026</span><small>{br(seas['empenhado'] / seas['orcado_atualizado'] * 100)}% comprometido até 7/10</small></div>
  <div><b>{din(total)}</b><span>em convênios e fomento</span><small>{len(validos)} instrumentos, {anos[0]}–{anos[-1]}</small></div>
  <div><b>{din(sum(r['valor'] for r in mun))}</b><span>para municípios</span><small>{len(mun)} instrumentos</small></div>
  <div><b>{din(sum(r['valor'] for r in ent))}</b><span>para entidades</span><small>{len(ent)} instrumentos</small></div>
</div>
<ul class="destaques">
  <li><b>{maior_ano}</b> foi o ano de maior valor assinado: {din(soma_ano[maior_ano])}, {br(soma_ano[maior_ano] / total * 100)}% de todo o período.</li>
  <li>Quem mais recebeu foi o <b>{e(top1[0].title())}</b>: {din(sum(r['valor'] for r in top1[1]))} em {len(top1[1])} instrumentos.</li>
  <li>{n_resc} instrumentos foram rescindidos e {n_adit} tiveram aditivo. As rescisões estão na seção 5 e não entram nos totais.</li>
  <li>Além dos convênios, {din(em_total)} em <b>emendas parlamentares</b> foram liberados para execução pela SEAS, em {len(em)} liberações.</li>
</ul>""")
    mx_o = max(o["orcado_atualizado"] for _, _, o in orc_l)
    barras_o = "".join(
        f"""<div class="ob"><div class="ob-n"><b>{s}</b><span>{br(o['empenhado'] / o['orcado_atualizado'] * 100)}% comprometido</span></div>
<div class="ob-t"><i class="o" style="width:{o['orcado_atualizado'] / mx_o * 100:.2f}%"></i><i class="c" style="width:{o['empenhado'] / mx_o * 100:.2f}%"></i><i class="p" style="width:{o['pago'] / mx_o * 100:.2f}%"></i></div>
<div class="ob-v">{din(o['orcado_atualizado'])}</div></div>""" for s, _, o in orc_l)
    linhas_o = "".join(
        f"<tr><td><b>{s}</b><small>{n}</small></td><td class='n'>{rs(o['orcado_inicial'])}</td><td class='n'>{rs(o['orcado_atualizado'])}</td>"
        f"<td class='n'>{rs(o['empenhado'])}</td><td class='n'>{rs(o['pago'])}</td></tr>" for s, n, o in orc_l)
    a(f"""<div class="bloco" id="s2"><h2 class="sec-t"><span>2</span>Orçamento de 2026</h2>
<p class="lead">O que a SEAS e os fundos da área de assistência têm para 2026, e quanto já foi comprometido em contratos e pago até 7 de outubro, com 77% do ano corrido.</p>
<div class="leg"><span><i style="background:#e6ebf3"></i>orçamento</span><span><i style="background:{AZUL_CLARO}"></i>comprometido</span><span><i style="background:{AZUL}"></i>pago</span></div>
<div class="obs">{barras_o}</div>
<table class="t orc"><colgroup><col style="width:58mm"><col><col><col><col></colgroup>
<thead><tr><th>Órgão ou fundo</th><th class="n">Lei aprovada</th><th class="n">Orçamento atual</th><th class="n">Comprometido</th><th class="n">Pago</th></tr></thead><tbody>{linhas_o}</tbody></table>
<p class="nota">Comprometido = empenhado (contrato ou pedido assinado). Os fundos estão agrupados por área de atuação; a vinculação de cada um à SEAS deve ser confirmada na lei que o criou. Fonte: Portal da Transparência de Rondônia, despesa por órgão, posição 7/10/2026.</p></div></section>""")

    # ---------------- 3
    tipos = ["Convênio", "Termo de Fomento", "Termo de Cooperação/Colaboração"]
    cor_t = {"Convênio": AZUL, "Termo de Fomento": AZUL_CLARO, "Termo de Cooperação/Colaboração": "#5f6b7f"}
    graf = barras_ano([(y, [(sum(r["valor"] for r in validos if r["ano"] == y and r["tipo"] == t), cor_t[t]) for t in tipos]) for y in anos], maior_ano)
    vm, ve = sum(r["valor"] for r in mun), sum(r["valor"] for r in ent)
    linhas_a = ""
    for y in anos:
        ry = [r for r in validos if r["ano"] == y]
        linhas_a += ("<tr><td><b>" + str(y) + "</b></td>" + "".join(f"<td class='n'>{len([r for r in ry if r['tipo'] == t])}</td>" for t in tipos)
                     + f"<td class='n'>{len([r for r in ry if ehmun(r['contratado'])])}</td><td class='n'>{len([r for r in ry if not ehmun(r['contratado'])])}</td><td class='n'><b>{rs(soma_ano[y])}</b></td></tr>")
    linhas_a += ("<tr class='tot'><td>Total</td>" + "".join(f"<td class='n'>{len([r for r in validos if r['tipo'] == t])}</td>" for t in tipos)
                 + f"<td class='n'>{len(mun)}</td><td class='n'>{len(ent)}</td><td class='n'>{rs(total)}</td></tr>")
    a(f"""<section class="pagina" id="s3"><h2 class="sec-t"><span>3</span>Convênios e termos de fomento, ano a ano</h2>
<p class="lead">Valor assinado por ano, pela data de assinatura. Convênios são firmados com municípios e órgãos públicos; termos de fomento, com organizações da sociedade civil (Lei 13.019/2014).</p>
<div class="leg"><span><i style="background:{AZUL}"></i>convênio</span><span><i style="background:{AZUL_CLARO}"></i>termo de fomento</span><span><i style="background:#5f6b7f"></i>cooperação</span></div>
{graf}
<div class="divide"><div><div class="k">Para municípios</div><b>{din(vm)}</b><span>{len(mun)} instrumentos · {br(vm / total * 100)}%</span></div>
<div class="bar2"><i style="width:{vm / total * 100:.2f}%"></i></div>
<div class="dir"><div class="k">Para entidades</div><b>{din(ve)}</b><span>{len(ent)} instrumentos · {br(ve / total * 100)}%</span></div></div>
<table class="t"><colgroup><col style="width:16mm"><col><col><col><col><col><col style="width:36mm"></colgroup>
<thead><tr><th>Ano</th><th class="n">Convênios</th><th class="n">Fomento</th><th class="n">Cooperação</th><th class="n">Municípios</th><th class="n">Entidades</th><th class="n">Valor assinado</th></tr></thead><tbody>{linhas_a}</tbody></table>
<p class="nota">Quantidade de instrumentos por ano; rescisões não entram. Fonte: Portal da Transparência de Rondônia, Convênios, órgão SEAS, coleta de {dia}.</p></section>""")

    # ---------------- 4
    rk = sorted(receb.items(), key=lambda kv: -sum(r["valor"] for r in kv[1]))
    mx_r = sum(r["valor"] for r in rk[0][1])
    linhas_r = ""
    for i, (nome, xs) in enumerate(rk[:30], 1):
        v = sum(r["valor"] for r in xs)
        linhas_r += (f"<tr><td class='n c'>{i}</td><td><b class='nm'>{e(nome)}</b><span class='mb'><i style='width:{v / mx_r * 100:.1f}%'></i></span></td>"
                     f"<td>{'Município' if ehmun(nome) else 'Entidade'}</td><td class='n'>{len(xs)}</td><td>{anos_curto(sorted({r['ano'] for r in xs}))}</td>"
                     f"<td class='n'><b>{rs(v)}</b></td><td class='n'>{br(v / total * 100, 1)}%</td></tr>")
    soma30 = sum(sum(r["valor"] for r in xs) for _, xs in rk[:30])
    a(f"""<section class="pagina" id="s4"><h2 class="sec-t"><span>4</span>Quem mais recebeu</h2>
<p class="lead">Os 30 municípios e entidades com maior valor assinado de {anos[0]} a {anos[-1]}. Juntos, somam {din(soma30)}, {br(soma30 / total * 100)}% do total. A lista completa está na seção 5.</p>
<table class="t rk"><colgroup><col style="width:8mm"><col><col style="width:18mm"><col style="width:11mm"><col style="width:30mm"><col style="width:27mm"><col style="width:12mm"></colgroup>
<thead><tr><th class="n">#</th><th>Quem recebe</th><th>Tipo</th><th class="n">Instr.</th><th>Anos</th><th class="n">Valor</th><th class="n">%</th></tr></thead><tbody>{linhas_r}</tbody></table></section>""")

    # ---------------- 5
    a(f'<section class="pagina" id="s5"><h2 class="sec-t"><span>5</span>Todos os instrumentos, em ordem de assinatura</h2>'
      f'<p class="lead">Os {len(regs)} registros do portal, ano a ano e pela data de assinatura, com o número do instrumento e o processo SEI para conferência. '
      f'<span class="adit">A</span> tem aditivo · <b>Abrir documento no SEI</b> leva ao termo assinado, em acesso público · linhas em cinza são rescisões e não entram nos totais.</p>')
    for i, y in enumerate(anos):
        ry = sorted([r for r in regs if r["ano"] == y], key=lambda r: ordem_data(r["assinatura"]))
        a(f'<div class="ano-bloco{" quebra" if i else ""}" id="a{y}"><h3 class="ano"><span>{y}</span><em>{len([r for r in ry if not r["rescisao"]])} instrumentos · {rs(soma_ano[y])}</em></h3>'
          '<table class="t lista"><colgroup><col style="width:19mm"><col style="width:40mm"><col style="width:43mm"><col><col style="width:25mm"></colgroup>'
          '<thead><tr><th>Data</th><th>Instrumento</th><th>Quem recebe</th><th>Objeto</th><th class="n">Valor</th></tr></thead><tbody>')
        for r in ry:
            a(f"<tr class='{'resc' if r['rescisao'] else ''}'><td class='d'>{e(r['assinatura'] or '—')}</td>"
              f"<td><b>{TIPO_CURTO.get(r['tipo'], r['tipo'])}</b>{' <span class=adit>A</span>' if r['tem_aditivo'] == 'Sim' else ''}<small>{e(r['numero'])}</small><small>SEI {e(r['processo_sei'])}</small>{link_doc(r)}</td>"
              f"<td>{e(r['contratado'])}{'<small>CNPJ ' + e(r.get('cnpj')) + '</small>' if r.get('cnpj') else ''}</td><td class='obj'>{e(corta(r['objeto'], 240))}</td><td class='n'>{'rescisão' if r['rescisao'] else rs(r['valor'])}</td></tr>")
        a("</tbody></table></div>")
    a("</section>")

    # ---------------- 6
    graf_e = barras_ano([(y, [(sum(x["valor"] for x in em if x["ano"] == y), "#b25d00")]) for y in em_anos], max(em_anos, key=lambda y: sum(x["valor"] for x in em if x["ano"] == y)), altura=110)
    linhas_ea = "".join(f"<tr><td><b>{y}</b></td><td class='n'>{len(xs)}</td><td class='n'>{len({x['entidade'] for x in xs})}</td><td class='n'>{len({x['dep'] for x in xs})}</td><td class='n'><b>{rs(sum(x['valor'] for x in xs))}</b></td></tr>"
                        for y in em_anos for xs in [[x for x in em if x["ano"] == y]])
    linhas_ea += f"<tr class='tot'><td>Total</td><td class='n'>{len(em)}</td><td class='n'>{len(em_ent)}</td><td class='n'>{len(em_dep)}</td><td class='n'>{rs(em_total)}</td></tr>"
    mini = lambda d: "".join(f"<tr><td>{e(corta(n, 58))}<span class='mb'><i style='width:{v / max(d.values()) * 100:.1f}%;background:#b25d00'></i></span></td><td class='n'>{din(v)}</td></tr>" for n, v in sorted(d.items(), key=lambda kv: -kv[1])[:12])
    a(f"""<section class="pagina" id="s6"><h2 class="sec-t"><span>6</span>Emendas parlamentares executadas pela SEAS</h2>
<p class="nota" style="margin:0 0 4mm">Fonte: Observatório de Orçamento e Finanças Públicas (OFIP) e planilha "Emendas 2025–2026", compilados pelo painel Transparência Orçamentária. A série cobre 2019 a 2026, sem registros de 2022. Emendas de bancada e de comissão aparecem no nome do deputado que as indicou.</p>
<p class="lead">Liberações de emendas da Assembleia Legislativa cuja execução ficou com a SEAS.</p>
{graf_e}
<table class="t"><colgroup><col style="width:18mm"><col><col><col><col style="width:38mm"></colgroup>
<thead><tr><th>Ano</th><th class="n">Liberações</th><th class="n">Beneficiários</th><th class="n">Deputados</th><th class="n">Valor liberado</th></tr></thead><tbody>{linhas_ea}</tbody></table>
<div class="duas">
  <div><h4>Beneficiários que mais receberam</h4><table class="t mini"><colgroup><col><col style="width:22mm"></colgroup><tbody>{mini(em_ent)}</tbody></table></div>
  <div><h4>Deputados que mais destinaram</h4><table class="t mini"><colgroup><col><col style="width:22mm"></colgroup><tbody>{mini(em_dep)}</tbody></table></div>
</div>""")
    for y in em_anos:
        xs = sorted([x for x in em if x["ano"] == y], key=lambda x: x["data"] or "")
        a(f'<div class="ano-bloco quebra" id="e{y}"><h3 class="ano"><span>{y}</span><em>{len(xs)} liberações · {rs(sum(x["valor"] for x in xs))}</em></h3>'
          '<table class="t lista"><colgroup><col style="width:19mm"><col style="width:12mm"><col style="width:25mm"><col style="width:41mm"><col style="width:23mm"><col><col style="width:23mm"></colgroup>'
          '<thead><tr><th>Data</th><th>Ofício</th><th>Deputado</th><th>Beneficiário</th><th>Município</th><th>Objeto</th><th class="n">Valor</th></tr></thead><tbody>')
        for x in xs:
            a(f"<tr><td class='d'>{data_br(x['data'])}</td><td>{e(x['oficio'])}</td><td>{e(x['dep'])}</td><td>{e(x['entidade'])}</td><td>{e(x['mun'])}</td><td class='obj'>{e(corta(x['objeto'], 160))}</td><td class='n'>{rs(x['valor'])}</td></tr>")
        a("</tbody></table></div>")
    a("</section>")

    # ---------------- 7
    a(f"""<section class="pagina" id="s7"><h2 class="sec-t"><span>7</span>Fontes, método e cuidados</h2>
<table class="t"><colgroup><col style="width:46mm"><col><col style="width:26mm"></colgroup><thead><tr><th>Dado</th><th>Fonte</th><th>Posição</th></tr></thead><tbody>
<tr><td>Convênios, termos de fomento e de cooperação da SEAS</td><td>Portal da Transparência de Rondônia (CGE-RO), Convênios: transparencia.ro.gov.br/convenios, consulta por órgão e ano</td><td class='d'>{dia}</td></tr>
<tr><td>Orçamento de 2026 por órgão</td><td>Portal da Transparência de Rondônia, despesa estadual</td><td class='d'>07/10/2026</td></tr>
<tr><td>Emendas parlamentares liberadas</td><td>OFIP (observatorioofip.com) e planilha "Emendas 2025–2026", compilados pelo painel Transparência Orçamentária</td><td class='d'>03/10/2026</td></tr>
</tbody></table>
<h4>Como os números foram contados</h4>
<ul class="metodo">
  <li>O valor de cada instrumento é o <b>valor global</b> informado no portal, na data de assinatura. Não é o valor efetivamente pago.</li>
  <li>As rescisões aparecem como registros próprios no portal ({n_resc} no período). Estão na lista da seção 5, mas não entram em nenhum total.</li>
  <li>{n_adit} instrumentos têm aditivo. O portal não informa o valor de cada aditivo; os totais usam o valor global publicado.</li>
  <li>"Município" é todo recebedor cujo nome contém "município"; os demais são entidades.</li>
  <li>Cada instrumento traz um link para o documento assinado no SEI (acesso externo público), tirado da ficha de detalhe do portal. Quando o portal não publica o documento, o link leva à ficha do instrumento.</li>
</ul>
<div class="assinatura"><span>Relatório elaborado a partir de dados públicos, sem acesso a sistemas internos do Estado.</span><b>{AUTORIA}</b></div></section>""")

    fonte = base64.b64encode((RAIZ / "vendor" / "fontes" / "inter-var.woff2").read_bytes()).decode()
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Convênios, termos de fomento e emendas da SEAS — Rondônia</title>
<meta name="robots" content="noindex, nofollow">
<style>
@font-face{{font-family:'Inter';font-weight:400 800;src:url(data:font/woff2;base64,{fonte}) format('woff2')}}
@page{{size:A4;margin:22mm 18mm 20mm 18mm;
  @top-left{{content:"Convênios, termos de fomento e emendas da SEAS";font:600 7.5pt Inter;color:#3f4550;vertical-align:bottom;padding-bottom:3mm;border-bottom:.6pt solid #d3d8e0}}
  @top-right{{content:"Estado de Rondônia · dados públicos";font:500 7.5pt Inter;color:#5f6b7f;vertical-align:bottom;padding-bottom:3mm;border-bottom:.6pt solid #d3d8e0}}
  @bottom-left{{content:"Posição dos dados: {dia} · {AUTORIA}";font:500 7pt Inter;color:#5f6b7f;vertical-align:top;padding-top:3mm}}
  @bottom-right{{content:counter(page) " / " counter(pages);font:700 7.5pt Inter;color:#3f4550;vertical-align:top;padding-top:3mm}}}}
@page :first{{margin:0;@top-left{{content:none;border:0}}@top-right{{content:none;border:0}}@bottom-left{{content:none}}@bottom-right{{content:none}}}}
*{{box-sizing:border-box}}
html{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{margin:0;font-family:Inter,sans-serif;color:#15171c;font-size:9pt;line-height:1.45;font-feature-settings:"tnum"}}
a{{color:inherit;text-decoration:none}}
b{{font-weight:700}}

.capa{{width:210mm;height:297mm;position:relative;overflow:hidden;break-after:page;background:#fff}}
.faixa{{position:absolute;left:0;top:0;bottom:0;width:9mm;display:flex;flex-direction:column}} .faixa i{{flex:1}} .faixa i:first-child{{flex:2.2}}
.capa-corpo{{position:absolute;left:27mm;right:20mm;top:22mm;bottom:18mm;display:flex;flex-direction:column}}
.capa-topo{{display:flex;align-items:center;gap:5mm}}
.capa-topo img{{width:21mm;height:auto}}
.capa-topo b{{display:block;font-size:13pt;color:#15171c;letter-spacing:.01em}}
.capa-topo span{{display:block;font-size:9.5pt;color:#3f4550;margin-top:.8mm}}
.capa-meio{{margin-top:34mm}}
.capa-k{{font-size:10pt;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:{AZUL};margin-bottom:6mm}}
.capa h1{{font-size:31pt;max-width:160mm;line-height:1.06;letter-spacing:-.03em;margin:0 0 7mm;font-weight:850;color:#15171c}}
.capa-sub{{font-size:12pt;line-height:1.45;color:#2a2e35;margin:0 0 15mm;max-width:150mm}}
.capa-nums{{display:grid;grid-template-columns:repeat(3,1fr);border-top:2pt solid #15171c}}
.capa-nums>div{{padding:6mm 5mm 0 0}} .capa-nums>div+div{{border-left:.6pt solid #d3d8e0;padding-left:5mm}}
.capa-nums b{{display:block;font-size:21pt;letter-spacing:-.03em;font-weight:850;color:#15171c;white-space:nowrap}}
.capa-nums span{{display:block;font-size:9.5pt;color:#2a2e35;margin-top:2mm;line-height:1.35}}
.capa-pe{{margin-top:auto;display:flex;justify-content:space-between;align-items:center;border-top:.6pt solid #d3d8e0;padding-top:5mm;font-size:9.5pt;color:#3f4550}}
.capa-pe b{{color:#15171c;font-weight:800}}

.pagina{{break-before:page}}
.bloco{{margin-top:8mm}}
.sec-t{{font-size:18pt;letter-spacing:-.02em;margin:0 0 5mm;display:flex;align-items:baseline;gap:4mm;font-weight:780;color:#15171c;break-after:avoid}}
.sec-t span{{font-size:10pt;font-weight:800;color:#fff;background:{AZUL};border-radius:1.5mm;padding:.6mm 2.2mm;transform:translateY(-1mm)}}
.lead{{font-size:9.6pt;color:#2a2e35;margin:0 0 5mm;max-width:168mm}}
.nota{{font-size:7.6pt;color:#4a505a;margin:3mm 0 0}}
.k{{font-size:7.4pt;font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:#15171c}}

.sumario ol{{list-style:none;padding:0;margin:4mm 0 6mm}}
.sumario li a{{display:grid;grid-template-columns:10mm 1fr;align-items:baseline;padding:3.6mm 0;border-bottom:.6pt solid #d3d8e0;font-size:11.5pt;font-weight:600}}
.sumario .sn{{color:{AZUL};font-weight:800}} .sumario .sp{{text-align:right;color:#3f4550;font-weight:700}}
.sumario li.anos{{display:flex;flex-wrap:wrap;gap:2mm 2mm;padding:2.5mm 0 3mm 10mm;border-bottom:.6pt solid #d3d8e0}}
.sumario li.anos a{{display:inline-flex;gap:1.6mm;align-items:baseline;border:.6pt solid #c5cfdf;border-radius:1.4mm;padding:1mm 2.4mm;font-size:8.6pt;font-weight:650;color:{AZUL}}}
.sumario li.anos em{{font-style:normal;color:#5f6b7f;font-weight:600;font-size:7.6pt}}

.kpis{{display:grid;grid-template-columns:repeat(4,1fr);border-top:2pt solid #15171c;border-bottom:.6pt solid #d3d8e0;margin:0 0 5mm}}
.kpis>div{{padding:4mm 3mm 4mm 0}} .kpis>div+div{{border-left:.6pt solid #d3d8e0;padding-left:3.5mm}}
.kpis b{{display:block;font-size:15pt;letter-spacing:-.025em;font-weight:850;color:#15171c;white-space:nowrap}}
.kpis span{{display:block;font-weight:650;margin-top:1.5mm;font-size:8.6pt}} .kpis small{{display:block;color:#5f6b7f;font-size:7.6pt;margin-top:1mm}}
.destaques{{padding-left:4.5mm;margin:0;font-size:9.6pt}} .destaques li{{margin-bottom:1.8mm}}

.leg{{display:flex;gap:5mm;font-size:7.8pt;color:#3f4550;margin:0 0 2mm}} .leg i{{display:inline-block;width:3mm;height:3mm;border-radius:.6mm;margin-right:1.4mm;vertical-align:-.4mm}}
.obs{{margin:0 0 5mm}}
.ob{{display:grid;grid-template-columns:30mm 1fr 22mm;gap:4mm;align-items:center;padding:1mm 0}}
.ob-n b{{display:block;font-size:9pt}} .ob-n span{{display:block;font-size:7.4pt;color:#5f6b7f}}
.ob-t{{position:relative;height:5mm}} .ob-t i{{position:absolute;left:0;top:0;bottom:0;border-radius:.8mm}}
.ob-t i.o{{background:#e6ebf3}} .ob-t i.c{{background:{AZUL_CLARO}}} .ob-t i.p{{background:{AZUL}}}
.ob-v{{text-align:right;font-weight:700;font-size:8.6pt;white-space:nowrap}}

table.t{{width:100%;border-collapse:collapse;margin:2mm 0 3mm;table-layout:fixed}}
.t th{{white-space:nowrap;text-align:left;font-size:7pt;letter-spacing:.05em;text-transform:uppercase;color:#15171c;font-weight:700;border-bottom:1pt solid #15171c;padding:1.8mm 1.8mm 1.4mm;vertical-align:bottom}}
.t td{{border-bottom:.5pt solid #e1e5ec;padding:1.7mm 1.8mm;vertical-align:top;overflow-wrap:anywhere}}
.t tr{{break-inside:avoid}}
.t thead{{display:table-header-group}}
.t .n{{text-align:right;white-space:nowrap;overflow-wrap:normal}} .t .c{{color:#8a94a6}}
.t td.d{{white-space:nowrap}}
.t td small{{display:block;color:#4a505a;font-size:7pt;margin-top:.5mm}}
.t tr.tot td{{border-top:1pt solid #15171c;border-bottom:0;font-weight:800}}
.t.orc{{font-size:8.2pt}}
.t.rk{{font-size:8pt}} .t.rk .nm{{display:block;font-weight:650}}
.mb{{display:block;height:1.2mm;background:#eef1f6;border-radius:.6mm;margin-top:1.2mm}} .mb i{{display:block;height:100%;background:{AZUL};border-radius:.6mm}}
.t.lista{{font-size:7.4pt;line-height:1.35}} .t.lista td{{padding:1.4mm 1.5mm}}
.t .obj{{color:#2a2e35}}
.t tr.resc td{{color:#8a94a6;background:#f4f5f7}}
.doc{{display:inline-block;margin-top:1mm;font-size:6.8pt;font-weight:700;color:{AZUL};border-bottom:.5pt solid {AZUL}}}
.adit{{display:inline-block;font-size:6.2pt;font-weight:800;color:{AZUL};border:.6pt solid {AZUL};border-radius:.6mm;padding:0 .9mm;margin-left:1mm;line-height:1.35}}
.t.mini{{font-size:7.8pt}} .t.mini td{{padding:1.2mm 1.4mm}}
.ano-bloco.quebra{{break-before:page}}
h3.ano{{display:flex;justify-content:space-between;align-items:baseline;margin:0 0 1mm;padding-bottom:1.6mm;border-bottom:1.6pt solid {AZUL};break-after:avoid}}
h3.ano span{{font-size:15pt;font-weight:800;color:{AZUL}}} h3.ano em{{font-style:normal;font-size:8.8pt;font-weight:650;color:#3f4550}}
h4{{font-size:7.6pt;text-transform:uppercase;letter-spacing:.06em;margin:5mm 0 1mm;break-after:avoid;color:#15171c}}
.graf{{width:100%;height:auto;margin:1mm 0 4mm}}
.graf .sv{{font:600 8px Inter;text-anchor:middle;fill:#3f4550}} .graf .sa{{font:600 9px Inter;text-anchor:middle;fill:#3f4550}}
.graf .sd{{fill:#15171c;font-weight:800}}
.divide{{display:grid;grid-template-columns:auto 1fr auto;gap:6mm;align-items:center;margin:0 0 5mm;padding:4mm 0;border-top:.6pt solid #d3d8e0;border-bottom:.6pt solid #d3d8e0}}
.divide b{{display:block;font-size:14pt;color:#15171c;font-weight:800;margin-top:.6mm}} .divide span{{display:block;font-size:7.6pt;color:#5f6b7f}}
.divide .dir{{text-align:right}}
.bar2{{height:5mm;background:{AZUL_CLARO};border-radius:.8mm;overflow:hidden}} .bar2 i{{display:block;height:100%;background:{AZUL}}}
.alerta{{background:#fdf3e7;border-left:2.4pt solid #b25d00;padding:3mm 4mm;font-size:8.2pt;margin:0 0 5mm;color:#3f2a10}}
.duas{{display:grid;grid-template-columns:1fr 1fr;gap:7mm}}
.metodo{{padding-left:4.5mm;font-size:9pt}} .metodo li{{margin-bottom:2mm}}
.assinatura{{margin-top:12mm;padding-top:4mm;border-top:.6pt solid #d3d8e0;display:flex;justify-content:space-between;align-items:baseline;font-size:8pt;color:#5f6b7f}}
.assinatura b{{font-size:10pt;color:#15171c;font-weight:800}}
</style></head><body>{''.join(P)}</body></html>"""


def imprimir(html_path, pdf_path):
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    "--virtual-time-budget=4000", html_path.resolve().as_uri()], check=True, capture_output=True, timeout=240)


def paginas(pdf_path):
    """Página em que cai cada seção (s1..s7) e cada ano (aNNNN, eNNNN), lida do próprio PDF."""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout.split("\f")
    titulos = {"s1": "Resumo", "s2": "Orçamento de 2026", "s3": "Convênios e termos de fomento, ano a ano", "s4": "Quem mais recebeu",
               "s5": "Todos os instrumentos, em ordem de assinatura", "s6": "Emendas parlamentares executadas pela SEAS", "s7": "Fontes, método e cuidados"}
    pg = {}
    for n, t in enumerate(txt[2:], 3):
        for k, tit in titulos.items():
            if k not in pg and re.search(rf"^\s*{k[1]}\s+{re.escape(tit)}\s*$", t, re.M):
                pg[k] = str(n)
        for m in re.finditer(r"^\s*(20\d\d)\s+\d+\s+(instrumentos|liberações)\s+·", t, re.M):
            k = ("a" if m[2] == "instrumentos" else "e") + m[1]
            pg.setdefault(k, str(n))
    return pg


def links_diretos(pdf_path):
    """Troca os links do sumário (destinos nomeados) por saltos diretos de página, que funcionam em qualquer leitor."""
    try:
        import pymupdf
    except ImportError:
        return
    doc = pymupdf.open(pdf_path)
    for pag in doc:
        for l in pag.get_links():
            if l["kind"] == pymupdf.LINK_NAMED and l.get("page", -1) >= 0:
                pag.delete_link(l)
                pag.insert_link({"kind": pymupdf.LINK_GOTO, "from": l["from"], "page": l["page"], "to": pymupdf.Point(0, 0)})
    tmp = pdf_path.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf_path)


def main():
    out_html = RAIZ / "esbocos" / "relatorio-seas.html"
    out_pdf = RAIZ / "esbocos" / "relatorio-seas.pdf"
    out_html.write_text(montar({}), encoding="utf-8")
    imprimir(out_html, out_pdf)
    pg = paginas(out_pdf)
    out_html.write_text(montar(pg), encoding="utf-8")
    imprimir(out_html, out_pdf)
    links_diretos(out_pdf)
    (RAIZ / "site" / "relatorio-seas.pdf").write_bytes(out_pdf.read_bytes())
    falta = [k for k in ["s1", "s2", "s3", "s4", "s5", "s6", "s7"] if k not in pg]
    print(f"relatorio-seas.pdf {round(out_pdf.stat().st_size / 1024)} KB · seções: {pg}" + (f" · SEM PÁGINA: {falta}" if falta else ""))


if __name__ == "__main__":
    main()
