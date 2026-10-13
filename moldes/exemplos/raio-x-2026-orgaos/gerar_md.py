"""PDF A · Raio-X da Tecnologia do Estado — 2026, por órgão. Só tecnologia da informação (TI).

Gera, a partir da mesma base da aba "Tecnologia no Estado" do painel (dados-fonte/s5_tecnologia.json; nenhum número digitado à mão):
  - raio-x-2026-orgaos.md   (texto do documento, com marcadores FIGURA para as imagens do Codex)
  - assets/g-*.svg          (gráficos vetoriais gerados dos dados)
  - dados_infograficos.json (os números exatos de cada imagem do Codex)
Depois: python3 moldes/gerar_documento.py moldes/exemplos/raio-x-2026-orgaos/raio-x-2026-orgaos.molde.yaml --site

Duas medidas, as mesmas da aba Tecnologia:
  - Empenhado em TI em 2026: notas de empenho de 2026 classificadas como tecnologia nota por nota ("fornecedores" da base),
    sem gestoras de frota, só Poder Executivo. É o dinheiro comprometido no ano.
  - Contratos de TI ativos em 2026: contratos, convênios, termos e parcerias de tecnologia com vigência em algum dia de 2026
    (vencimento a partir de 01/01/2026) ou cadastrados em 2026. Valor global, sem aditivos. É o compromisso firmado.
Ficam fora das somas: rescisões, valor a conferir (implausível) e frota.
"""
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[2]
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(RAIZ / "tecnologia"))
from build_tecnologia import OUTROS_PODERES, modalidade  # noqa: E402

ANO = 2026
INICIO = "2026-01-01"
SEM_LICIT = {"Dispensa", "Inexigibilidade", "Não aplicável (parceria, convênio, termo)", "Adesão a ata"}
AZUL, CINZA = "#1a56b8", "#8a94a6"
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
NOMES_EXTRA = {"SOPH": "Sociedade de Portos e Hidrovias", "CAERD": "Companhia de Águas e Esgotos de Rondônia"}
# modalidade em célula estreita: nome curto, sem parênteses
MOD_CURTO = {"Não aplicável (parceria, convênio, termo)": "Convênio, termo ou parceria", "Outros (o portal não detalha)": "Outros (sem detalhe)",
             "Credenciamento ou chamamento": "Credenciamento"}
PREFIXO_ORG = re.compile(r"^(Secretaria de Estado (de |da |do |das |dos )?|Secretaria (de |da |do )|Superintendência (Estadual )?(de |do |da |dos )?|Departamento (Estadual )?de |"
                         r"Agência (Estadual )?de |Fundação (Estadual )?de |Instituto (Estadual )?de |Companhia de |Entidade Autárquica de )")


def fmt(v):
    a = abs(v)
    if a >= 1e9:
        return f"R$ {v / 1e9:,.2f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
    if a >= 1e6:
        return f"R$ {v / 1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if a >= 1e3:
        return f"R$ {v / 1e3:,.0f} mil".replace(",", ".")
    return f"R$ {v:,.0f}".replace(",", ".")


def pct(a, b):
    return f"{100 * a / b:.1f}%".replace(".", ",") if b else "—"


def br(n):
    return f"{n:,}".replace(",", ".")


def cel(s, n=140):
    s = re.sub(r"\s+", " ", str(s or "")).strip().replace("|", "/")
    if len(s) <= n:
        return s
    corte = s[: n - 1].rsplit(" ", 1)[0] if " " in s[: n - 1] else s[: n - 1]  # corta na palavra, não no meio dela
    return corte.rstrip(" ,.;:-–(") + "…"


def cnpj(c):
    c = re.sub(r"\D", "", c or "")
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else (c or "—")


SUFIXO = re.compile(r"[\s,.-]+(LTDA\.?|S\.?/?A\.?|EIRELI|ME|EPP|S/S)\.?$", re.I)


def empresa_curta(nome, n=30):
    """Nome para rótulo de gráfico: sem o tipo societário, cortado na palavra."""
    s = re.sub(r"\s+", " ", nome or "").strip()
    s = re.sub(r"\s*\(cartão corporativo de servidores\)", "", s)
    for _ in range(2):
        s = SUFIXO.sub("", s).strip()
    return cel(s, n)


def esc(s, n=140):
    return html.escape(cel(s, n))


def link(texto, url):
    return f'<a href="{html.escape(url)}">{html.escape(texto)}</a>'


def data_br(iso):
    return "/".join(reversed(iso.split("-"))) if iso else "—"


# ---------------------------------------------------------------- gráficos SVG e tabelas
def svg_barras(itens, largura=640, rot=240):
    """itens: [(rótulo, valor, cor opcional)] -> barras horizontais com valor escrito."""
    if not itens:
        return ""
    linha, h = 22, 22 * len(itens) + 8
    area = largura - rot - 90
    mx = max(v for _, v, *_ in itens) or 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {h}" width="100%" font-family="Inter, sans-serif" font-size="11">',
           f'<line x1="{rot - .5}" x2="{rot - .5}" y1="2" y2="{h - 2}" stroke="#c4cbd6"/>']
    for i, it in enumerate(itens):
        r, v = it[0], it[1]
        c = it[2] if len(it) > 2 and it[2] else AZUL
        y = 4 + i * linha
        w = max(1.5, area * v / mx)
        out.append(f'<text x="{rot - 8}" y="{y + 14}" text-anchor="end" fill="#15171c">{html.escape(cel(r, int((rot - 12) / 6.4)))}</text>')
        out.append(f'<rect x="{rot}" y="{y + 3}" width="{w:.1f}" height="14" rx="2" fill="{c}"/>')
        out.append(f'<text x="{rot + w + 6:.1f}" y="{y + 14}" fill="#15171c" font-weight="600">{html.escape(fmt(v))}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_colunas(itens, largura=640, altura=200):
    if not itens:
        return ""
    base, alt = altura - 22, altura - 50
    passo = largura / len(itens)
    bw = min(40, passo * .62)
    mx = max(v for _, v in itens) or 1
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" width="100%" font-family="Inter, sans-serif" font-size="11">',
           f'<line x1="0" x2="{largura}" y1="{base + .5}" y2="{base + .5}" stroke="#d3d8e0"/>']
    for i, (r, v) in enumerate(itens):
        x = i * passo + (passo - bw) / 2
        hh = alt * v / mx
        out.append(f'<rect x="{x:.1f}" y="{base - hh:.1f}" width="{bw:.1f}" height="{hh:.1f}" rx="2" fill="{AZUL}"/>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{base - hh - 5:.1f}" text-anchor="middle" fill="#15171c" font-size="10" font-weight="600">{html.escape(fmt(v).replace("R$ ", ""))}</text>')
        out.append(f'<text x="{x + bw / 2:.1f}" y="{base + 15}" text-anchor="middle" fill="#3f4550">{html.escape(r)}</text>')
    out.append("</svg>")
    return "".join(out)


def tabela(colunas, larguras, linhas, cls="tab", num=()):
    """Tabela em HTML com largura de cada coluna (o molde usa table-layout: fixed). Células já vêm escapadas/com link.
    num: índices das colunas de número/valor, alinhadas à direita."""
    col = "".join(f'<col style="width:{w}%">' for w in larguras)
    k = lambda i: ' class="num"' if i in num else ""
    th = "".join(f"<th{k(i)}>{html.escape(c)}</th>" for i, c in enumerate(colunas))
    tr = "".join("<tr>" + "".join(f"<td{k(i)}>{c}</td>" for i, c in enumerate(l)) + "</tr>" for l in linhas)
    return f'<table class="{cls}"><colgroup>{col}</colgroup><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>'


def grava_svg(nome, conteudo):
    (AQUI / "assets").mkdir(exist_ok=True)
    (AQUI / "assets" / nome).write_text(conteudo, encoding="utf-8")


def periodo(iso):
    a, m = iso[:4], int(iso[5:7])
    if a < "2027":
        return "Até dez/2026"
    if a == "2027":
        return f"2027 · {(m - 1) // 3 + 1}º tri"
    return "2028" if a == "2028" else "2029 ou depois"


ORDEM_PER = ["Até dez/2026", "2027 · 1º tri", "2027 · 2º tri", "2027 · 3º tri", "2027 · 4º tri", "2028", "2029 ou depois"]


# ---------------------------------------------------------------- documento
def main():
    d = json.loads((FONTE / "s5_tecnologia.json").read_text(encoding="utf-8"))
    corte = d["data_corte"]
    nomes = {**d["nomes"], **NOMES_EXTRA}
    nome = lambda s: nomes.get(s, s)
    CAT = dict(d["categorias"])
    FUN = d["funcoes"]
    L_NOTA = d["links"]["detalhe"]

    # notas de TI de 2026, Executivo, sem frota: [ano, órgão, credor, cnpj, empenhado, pago, origem, histórico, data, link, parceria, mod. bruta, modalidade]
    notas = [x for x in d["fornecedores"] if x[0] == ANO and not x[6].startswith("frota") and x[1] not in OUTROS_PODERES]
    # contratos de TI ativos em 2026
    ativo = lambda r: (r.get("vigencia_iso") or "") >= INICIO or r["ano"] == ANO
    regs = [r for r in d["registros"] if r["cat"] != "frota" and not r["rescisao"] and not r["conferir"] and ativo(r)]
    conferir = [r for r in d["registros"] if r["conferir"] and r["cat"] != "frota" and ativo(r)]

    def mod_reg(r):
        return modalidade(r.get("origem") or "") if (r.get("instrumento") or "Contrato") == "Contrato" else "Não aplicável (parceria, convênio, termo)"

    chave_emp = lambda x: x[3] or x[2]
    org = defaultdict(lambda: {"emp": 0.0, "pago": 0.0, "forn": defaultdict(lambda: {"v": 0.0, "nome": "", "cnpj": ""}), "modal": defaultdict(float),
                               "notas": [], "regs": []})
    estado = {"emp": 0.0, "pago": 0.0, "mes": defaultdict(float), "modal": defaultdict(float),
              "forn": defaultdict(lambda: {"v": 0.0, "nome": "", "cnpj": "", "orgs": set()})}
    for x in notas:
        o, v = org[x[1]], x[4]
        o["emp"] += v
        o["pago"] += x[5]
        f = o["forn"][chave_emp(x)]
        f["v"] += v
        f["nome"], f["cnpj"] = x[2], x[3]
        o["modal"][x[12]] += v
        o["notas"].append(x)
        estado["emp"] += v
        estado["pago"] += x[5]
        estado["mes"][int(x[8][3:5])] += v
        estado["modal"][x[12]] += v
        e = estado["forn"][chave_emp(x)]
        e["v"] += v
        e["nome"], e["cnpj"] = x[2], x[3]
        e["orgs"].add(x[1])
    for r in regs:
        org[r["sigla"]]["regs"].append(r)

    vale = lambda r: r["valor"] or 0
    soma = lambda rs: sum(vale(r) for r in rs)
    ativos_v = soma(regs)
    novos = [r for r in regs if r["ano"] == ANO]
    vig = [r for r in regs if (r.get("vigencia_iso") or "") >= corte]
    vence27 = [r for r in vig if r["vigencia_iso"][:4] == "2027"]
    abertas = sum(v for m, v in estado["modal"].items() if m != "Não informada")
    sem_lic = sum(v for m, v in estado["modal"].items() if m in SEM_LICIT)
    ordem = sorted(org, key=lambda s: (-org[s]["emp"], -soma(org[s]["regs"])))
    pos_emp = {s: i for i, s in enumerate(sorted((s for s in org if org[s]["emp"] > 0), key=lambda s: -org[s]["emp"]), 1)}
    n_emp_org = len(pos_emp)
    top_forn = sorted(estado["forn"].values(), key=lambda e: -e["v"])

    # o que compra: pelo valor global dos contratos ativos
    cat_v, cat_n = defaultdict(float), Counter()
    for r in regs:
        cat_v[r["cat"]] += vale(r)
        cat_n[r["cat"]] += 1
    # onde se repete: a mesma função contratada por mais de um órgão em 2026
    fun = defaultdict(lambda: {"orgs": set(), "emp": set(), "n": 0, "v": 0.0, "cat": ""})
    for r in regs:
        if not r.get("funcao") or r["funcao"] == "outra":
            continue
        g = fun[r["funcao"]]
        g["orgs"].add(r["sigla"])
        g["emp"].add(r["cnpj"] or r["contratado"])
        g["n"] += 1
        g["v"] += vale(r)
        g["cat"] = r["cat"]
    repete = sorted(((k, g) for k, g in fun.items() if len(g["orgs"]) >= 2), key=lambda t: (-len(t[1]["orgs"]), -t[1]["v"]))
    venc = defaultdict(lambda: [0, 0.0])
    for r in vig:
        p = periodo(r["vigencia_iso"])
        venc[p][0] += 1
        venc[p][1] += vale(r)

    # gráficos
    top_org = [s for s in sorted(org, key=lambda s: -org[s]["emp"]) if org[s]["emp"] > 0][:20]
    grava_svg("g-orgaos.svg", svg_barras([(f"{s} · {cel(PREFIXO_ORG.sub('', nome(s)), 34 - len(s))}" if PREFIXO_ORG.sub('', nome(s)) != s else s, org[s]["emp"]) for s in top_org], rot=280))
    grava_svg("g-meses.svg", svg_colunas([(MESES[m - 1], estado["mes"][m]) for m in sorted(estado["mes"])]))
    mods = sorted(estado["modal"].items(), key=lambda x: -x[1])
    grava_svg("g-modal.svg", svg_barras([(MOD_CURTO.get(m, m), v, AZUL if m in SEM_LICIT else CINZA) for m, v in mods]))
    cats = sorted(cat_v.items(), key=lambda x: -x[1])
    grava_svg("g-categorias.svg", svg_barras([(CAT.get(c, c), v) for c, v in cats], rot=300))

    L = []
    w = L.append
    w("---")
    w("titulo: Tecnologia no Estado — 2026")
    w("---")
    w("")
    w("**A-F01 — Capa.** Capa do documento.")
    w("<!-- FIGURA A-F01 | Capa | tipo=capa | arquivo=assets/capa.png -->")
    w("")
    w("# Apresentação")
    w("")
    w(f"Este documento mostra, órgão por órgão do Poder Executivo de Rondônia, **tudo o que o Estado contratou e empenhou em tecnologia da informação em 2026**: sistemas e software, licenças, datacenter e nuvem, links e telecomunicações, segurança da informação, suporte, impressão, equipamentos, rede e tecnologia operacional. Para cada órgão: quanto, com quais empresas, por qual modalidade e com quais contratos, convênios e parcerias. Tudo sai de dados públicos do Portal da Transparência, coletados em {data_br(corte)}, e cada nota e contrato citados têm link para a fonte.")
    w("")
    w(tabela(["Tecnologia da informação em 2026", "Valor"], [64, 36], [
        ["<b>Empenhado em TI</b> (notas de 2026, até a coleta)", f"<b>{fmt(estado['emp'])}</b>"],
        ["Pago dessas notas até a coleta", fmt(estado["pago"])],
        ["Empresas e entidades que receberam", br(len(estado["forn"]))],
        ["Órgãos com gasto em TI em 2026", br(n_emp_org)],
        ["<b>Contratos, convênios e parcerias de TI ativos em 2026</b> (valor global)", f"<b>{br(len(regs))} · {fmt(ativos_v)}</b>"],
        ["Desses, assinados em 2026", f"{br(len(novos))} · {fmt(soma(novos))}"],
        ["Ainda vigentes na data da coleta", f"{br(len(vig))} · {fmt(soma(vig))}"],
        ["Vencem em 2027", f"{br(len(vence27))} · {fmt(soma(vence27))}"],
        ["Empenhado sem pregão ou concorrência", f"{fmt(sem_lic)} · {pct(sem_lic, abertas)}"],
    ], num=(1,)))
    w("")
    w(f"**A-F06 — Quando vencem os contratos de TI.** Calendário de vencimentos dos {br(len(vig))} contratos de TI vigentes.")
    w("<!-- FIGURA A-F06 | Quando vencem os contratos de TI | tipo=infografico | arquivo=assets/info-vencimentos.png -->")
    w("")
    w("### Como ler")
    w("")
    w("- **Empenhado** é o dinheiro que o órgão reservou em 2026 para pagar a empresa; **pago** é o que já saiu. A nota entra como tecnologia pela classificação nota a nota (elemento de despesa, histórico, credor e CNPJ), a mesma da aba \"Tecnologia no Estado\" do painel. Gestoras de frota (cartão de combustível e manutenção) ficam fora.")
    w("- **Contrato ativo em 2026** é o que esteve em vigor em algum dia do ano (vence a partir de 01/01/2026) ou foi assinado em 2026. O valor é o **valor global** publicado, sem aditivos: é o compromisso inteiro, que pode cobrir vários anos. Por isso ele não se soma ao empenhado.")
    if conferir:
        w(f"- Ficam fora das somas as rescisões e {len(conferir)} registro com valor implausível no portal, que pede conferência: " + "; ".join(f"{r['sigla']}, {esc(r['contratado'], 40)}, {fmt(vale(r))}" for r in conferir) + ".")
    w("- É leitura de dados públicos, não auditoria. Pessoas físicas não aparecem com nome.")
    w("")

    w("# O Estado em 2026")
    w("")
    w("**A-F02 — O Estado em 2026.** Abertura da parte de síntese.")
    w("<!-- FIGURA A-F02 | O Estado em 2026 | tipo=abertura | arquivo=assets/abertura-estado.png -->")
    w("")
    w(f"Em 2026, até {data_br(corte)}, o Executivo empenhou **{fmt(estado['emp'])}** em tecnologia, com {br(len(estado['forn']))} empresas e entidades, em {br(n_emp_org)} órgãos. No mesmo ano estiveram ativos **{br(len(regs))} contratos, convênios e parcerias de TI**, que somam **{fmt(ativos_v)}** em valor global.")
    w("")
    w("**A-G01 — Os 20 órgãos que mais empenharam em tecnologia em 2026.** Notas de TI, Poder Executivo.")
    w("<!-- FIGURA A-G01 | Os 20 órgãos que mais empenharam em tecnologia em 2026 | tipo=grafico | arquivo=assets/g-orgaos.svg -->")
    w("")
    w("## Todos os órgãos")
    w("")
    linhas = []
    for s in ordem:
        o = org[s]
        linhas.append([f"{html.escape(s)}<br><small>{esc(nome(s), 60)}</small>", fmt(o["emp"]) if o["emp"] else "—", fmt(o["pago"]) if o["emp"] else "—",
                       br(len(o["regs"])) if o["regs"] else "—", fmt(soma(o["regs"])) if o["regs"] else "—"])
    linhas.append(["Total", f"<b>{fmt(estado['emp'])}</b>", f"<b>{fmt(estado['pago'])}</b>", f"<b>{br(len(regs))}</b>", f"<b>{fmt(ativos_v)}</b>"])
    w(tabela(["Órgão", "Empenhado 2026", "Pago 2026", "Contratos ativos", "Valor global"], [40, 16, 15, 13, 16], linhas, num=(1, 2, 3, 4)))
    w("")
    w("## O que o Estado compra em tecnologia")
    w("")
    w("Pelo tipo de cada contrato, convênio ou parceria ativo em 2026, em valor global.")
    w("")
    w("**A-G02 — Contratos de TI ativos em 2026, por tipo.** Valor global.")
    w("<!-- FIGURA A-G02 | Contratos de TI ativos em 2026, por tipo | tipo=grafico | arquivo=assets/g-categorias.svg -->")
    w("")
    w("## Mês a mês")
    w("")
    w("**A-G03 — Empenhado em tecnologia, mês a mês.** Executivo, 2026, até a data da coleta.")
    w("<!-- FIGURA A-G03 | Empenhado em tecnologia, mês a mês | tipo=grafico | arquivo=assets/g-meses.svg -->")
    w("")
    w("## Quando vencem os contratos de TI")
    w("")
    w(f"Dos contratos de TI ativos em 2026, {br(len(vig))} seguem vigentes na data da coleta. **{br(len(vence27))} vencem em 2027 ({fmt(soma(vence27))})**: é a janela para renovar de forma conjunta, com um só processo para vários órgãos.")
    w("")
    w(tabela(["Vencimento", "Contratos", "Valor global"], [50, 20, 30], [[p, br(venc[p][0]), fmt(venc[p][1])] for p in ORDEM_PER if p in venc], cls="tab curta", num=(1, 2)))
    w("")

    w("# Como o Estado compra tecnologia")
    w("")
    w("**A-F03 — Como o Estado compra tecnologia.** Abertura da parte de modalidades e fornecedores.")
    w("<!-- FIGURA A-F03 | Como o Estado compra tecnologia | tipo=abertura | arquivo=assets/abertura-compras.png -->")
    w("")
    w(f"A modalidade vem do detalhe de cada nota de empenho. Em 2026, **{fmt(sem_lic)}** ({pct(sem_lic, abertas)}) do empenhado em TI saiu **sem pregão ou concorrência**: dispensa, inexigibilidade (software exclusivo, por exemplo), convênio ou parceria com entidades e adesão a ata de outro órgão. Não é irregular por si; é a parte que mais ganha com compras planejadas em conjunto. \"Outros\" é como o próprio portal registra parte das notas, sem detalhar a modalidade.")
    w("")
    w("**A-G04 — Empenhado em tecnologia por modalidade, 2026.** Azul: sem pregão ou concorrência.")
    w("<!-- FIGURA A-G04 | Empenhado em tecnologia por modalidade | tipo=grafico | arquivo=assets/g-modal.svg -->")
    w("")
    w("## As 25 empresas que mais receberam em TI em 2026")
    w("")
    w(tabela(["#", "Empresa", "CNPJ", "Órgãos", "Empenhado"], [5, 49, 23, 9, 14],
             [[str(i), esc(e["nome"], 70), cnpj(e["cnpj"]), str(len(e["orgs"])), fmt(e["v"])] for i, e in enumerate(top_forn[:25], 1)], num=(3, 4)))
    w("")
    w("## Onde o Estado contrata a mesma coisa várias vezes")
    w("")
    w("Funções de tecnologia contratadas por **dois ou mais órgãos** em contratos ativos em 2026. São as primeiras candidatas a contrato único do Estado, ata de registro de preços compartilhada ou serviço central da SETIC.")
    w("")
    w(tabela(["Função", "Órgãos", "Contratos", "Empresas", "Valor global"], [34, 32, 10, 10, 14],
             [[f"{esc(FUN.get(k, k), 60)}<br><small>{esc(CAT.get(g['cat'], g['cat']), 50)}</small>", esc(", ".join(sorted(g["orgs"])), 220), br(g["n"]), br(len(g["emp"])), fmt(g["v"])]
              for k, g in repete], num=(2, 3, 4)))
    w("")

    w("# Os órgãos, um a um")
    w("")
    w("**A-F05 — Os órgãos.** Abertura da parte de fichas.")
    w("<!-- FIGURA A-F05 | Os órgãos, um a um | tipo=abertura | arquivo=assets/abertura-orgaos.png -->")
    w("")
    w(f"Uma ficha para cada um dos {br(len(ordem))} órgãos com gasto ou contrato de tecnologia em 2026, sempre no mesmo roteiro: o resumo, o que compra, para quem foi o dinheiro, por qual modalidade, **todos os contratos de TI ativos em 2026** e as 5 maiores notas do ano. Órgãos em ordem do valor empenhado em TI.")
    w("")

    for s in ordem:
        o = org[s]
        rs = sorted(o["regs"], key=lambda r: -vale(r))
        rv = [r for r in rs if (r.get("vigencia_iso") or "") >= corte]
        r27 = [r for r in rv if r["vigencia_iso"][:4] == "2027"]
        n26 = [r for r in rs if r["ano"] == ANO]
        sl = sum(v for m, v in o["modal"].items() if m in SEM_LICIT)
        ab = sum(v for m, v in o["modal"].items() if m != "Não informada")
        w(f"# {s} · {nome(s)}")
        w("")
        res = []
        if o["emp"]:
            res += [["Posição no Estado (empenhado em TI)", f"{pos_emp[s]}º de {n_emp_org}"],
                    ["<b>Empenhado em TI em 2026</b>", f"<b>{fmt(o['emp'])}</b> · {br(len(o['forn']))} {'empresas' if len(o['forn']) > 1 else 'empresa'}"],
                    ["Pago dessas notas até a coleta", fmt(o["pago"])],
                    ["Empenhado sem pregão ou concorrência", f"{fmt(sl)} · {pct(sl, ab)}"]]
        else:
            res += [["Empenhado em TI em 2026", "nenhuma nota de TI até a coleta"]]
        res += [["<b>Contratos de TI ativos em 2026</b>", f"<b>{br(len(rs))} · {fmt(soma(rs))}</b>" if rs else "nenhum"]]
        if rs:
            res += [["Assinados em 2026", f"{br(len(n26))} · {fmt(soma(n26))}" if n26 else "nenhum"],
                    ["Vigentes na coleta", f"{br(len(rv))} · {fmt(soma(rv))}" if rv else "nenhum"],
                    ["Vencem em 2027", f"{br(len(r27))} · {fmt(soma(r27))}" if r27 else "nenhum"]]
        w(tabela(["Resumo de 2026", ""], [52, 48], res))
        w("")
        if rs:
            cs = defaultdict(lambda: [0, 0.0])
            for r in rs:
                cs[r["cat"]][0] += 1
                cs[r["cat"]][1] += vale(r)
            w("### O que compra <small>contratos ativos em 2026, por tipo</small>")
            w("")
            w(tabela(["Tipo", "Contratos", "Valor global"], [60, 16, 24], [[esc(CAT.get(c, c)), br(n), fmt(v)] for c, (n, v) in sorted(cs.items(), key=lambda t: -t[1][1])],
                     cls="tab curta" if len(cs) <= 6 else "tab", num=(1, 2)))
            w("")
        if len(o["forn"]) >= 3:
            top = sorted(o["forn"].values(), key=lambda e: -e["v"])[:10]
            w(f"### Para quem foi o dinheiro <small>as {len(top)} maiores empresas, empenhado em TI em 2026</small>")
            w("")
            w(f'<div class="grafico-orgao">{svg_barras([(empresa_curta(e["nome"], 40), e["v"]) for e in top], rot=270)}</div>')
            w("")
        if o["emp"]:
            w("### Por modalidade <small>empenhado em TI em 2026</small>")
            w("")
            w(tabela(["Modalidade", "Empenhado", "Parte"], [62, 22, 16],
                     [[esc(MOD_CURTO.get(m, m)), fmt(v), pct(v, o["emp"])] for m, v in sorted(o["modal"].items(), key=lambda x: -x[1])], num=(1, 2)))
            w("")
        if rs:
            w(f"### Contratos, convênios e parcerias de TI ativos em 2026 <small>{br(len(rs))} · o valor abre a ficha no portal</small>")
            w("")
            linhas = []
            for r in rs:
                ident = f'{esc(r.get("instrumento") or "Contrato", 24)} · {esc(r["numero"], 34)}' + (f'<br>SEI {esc(r["processo"], 30)}' if r.get("processo") else "")
                oque = f'<b>{esc(FUN.get(r.get("funcao"), CAT.get(r["cat"], "")), 60)}</b>' + (f' · {esc(r["produto"], 40)}' if r.get("produto") else "")
                quando = ("até " + r["vigencia"] if r.get("vigencia") else "sem vigência") + (" · encerrado" if (r.get("vigencia_iso") or "9") < corte else "")
                linhas.append([esc(r["contratado"], 60) + f"<br><small>{ident}</small>", f"{oque}<br>{esc(r['objeto'], 120)}",
                               f"{esc(MOD_CURTO.get(mod_reg(r), mod_reg(r)), 30)}<br>{quando}", link(fmt(vale(r)), r["link"]) if r.get("link") else fmt(vale(r))])
            w(tabela(["Contratado", "Objeto", "Modalidade · vigência", "Valor global"], [24, 44, 17, 15], linhas, num=(3,)))
            w("")
        if o["notas"]:
            maiores = sorted(o["notas"], key=lambda x: -x[4])[:5]
            w(f"### {'As 5 maiores notas' if len(o['notas']) > 5 else 'Notas'} de TI de 2026 <small>o valor abre a nota no Portal da Transparência</small>")
            w("")
            w(tabela(["Empresa", "Objeto (histórico da nota)", "Modalidade · data", "Empenhado"], [23, 47, 17, 13],
                     [[esc(x[2], 50), esc(x[7], 120), f"{esc(MOD_CURTO.get(x[12], x[12]), 30)}<br>{x[8]}", link(fmt(x[4]), L_NOTA + x[9])] for x in maiores], num=(3,)))
            w("")

    w("# Fontes e método")
    w("")
    w(tabela(["Dado", "Fonte", "Coleta"], [34, 46, 20], [
        ["Notas de empenho de 2026 (todas)", "Portal da Transparência RO · Despesas por empenho", data_br(corte)],
        ["Detalhe das notas (CNPJ, modalidade, histórico)", "Portal da Transparência RO · detalhe da nota", data_br(corte)],
        ["Contratos, convênios, termos e parcerias", "Portal da Transparência RO · Contratos e Convênios", data_br(corte)],
        ["Classificação de tecnologia", "Painel Rondônia em números · aba Tecnologia no Estado (mesma base)", data_br(corte)],
    ]))
    w("")
    w("**Regras.** Poder Executivo. Tecnologia: nota a nota, pelo elemento de despesa 40 (serviços de TIC) e, nos demais elementos, pelo histórico da nota, pelo credor e pelo CNPJ (atividade de TI); gestoras de frota ficam fora. Contrato de TI: pelo objeto, com revisão manual dos casos duvidosos; ativo em 2026 quando vence a partir de 01/01/2026 ou foi cadastrado em 2026; valor global sem aditivos; rescisões e valores implausíveis fora das somas. Modalidade: a do detalhe da nota; nos contratos, a origem informada no portal (convênios, termos e parcerias como \"convênio, termo ou parceria\"). Leitura de dados públicos, não auditoria.")
    (AQUI / "raio-x-2026-orgaos.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # números exatos para os infográficos do Codex (os mesmos do PDF)
    info = {"coleta": corte, "empenhado_ti": estado["emp"], "pago_ti": estado["pago"], "n_empresas": len(estado["forn"]), "n_orgaos_com_gasto": n_emp_org,
            "n_orgaos_fichas": len(ordem), "contratos_ativos": [len(regs), ativos_v], "assinados_2026": [len(novos), soma(novos)],
            "vigentes_na_coleta": [len(vig), soma(vig)], "vencem_2027": [len(vence27), soma(vence27)],
            "sem_pregao": [sem_lic, 100 * sem_lic / abertas if abertas else 0], "modalidades": dict(mods),
            "top_orgaos_empenhado": [(s, nome(s), org[s]["emp"], len(org[s]["regs"]), soma(org[s]["regs"])) for s in top_org[:10]],
            "top_empresas": [(e["nome"], cnpj(e["cnpj"]), len(e["orgs"]), e["v"]) for e in top_forn[:10]],
            "categorias_contratos": [(CAT.get(c, c), cat_n[c], v) for c, v in cats], "mes_a_mes": {MESES[m - 1]: estado["mes"][m] for m in sorted(estado["mes"])},
            "vencimentos": {p: venc[p] for p in ORDEM_PER if p in venc},
            "repete_top": [(FUN.get(k, k), sorted(g["orgs"]), g["n"], g["v"]) for k, g in repete[:10]]}
    (AQUI / "dados_infograficos.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    sd = org["SEDUC"]
    print(f"md: {len(L)} linhas · {len(ordem)} órgãos · empenhado TI {fmt(estado['emp'])} · contratos ativos {len(regs)} · {fmt(ativos_v)} · "
          f"SEDUC: empenhado {fmt(sd['emp'])}, contratos ativos {len(sd['regs'])} · {fmt(soma(sd['regs']))}")


if __name__ == "__main__":
    main()
