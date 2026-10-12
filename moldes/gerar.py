"""Gera um documento no molde "Proposta" (o do SISPAC-RO) a partir de um arquivo de conteúdo YAML.

Uso: python3 moldes/gerar.py caminho/do/conteudo.yaml [--site]
Grava <arquivo>.html e <arquivo>.pdf na mesma pasta do YAML (--site copia o PDF para site/).
Quem escreve o documento só mexe no YAML; a lista de blocos e as regras estão em moldes/README.md.
"""
import base64
import html
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
VENDOR = RAIZ / "vendor"
CHROMES = [os.environ.get("CHROME", ""), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
           "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]
TONS_MAPA = ["#dfe7f5", "#b3c6e8", "#7b9bd8", "#3a6bc4", "#0f2c66"]


def e(s):
    return html.escape(str(s if s is not None else ""))


def md(s):
    """Texto com **negrito** (vira <b>) e quebras de linha; o resto é escapado."""
    t = e(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"R\$ ", "R$&nbsp;", t)
    return t.replace("\n", "<br>")


def dado_uri(caminho):
    tipo = mimetypes.guess_type(str(caminho))[0] or "application/octet-stream"
    return f"data:{tipo};base64,{base64.b64encode(Path(caminho).read_bytes()).decode()}"


def par(item, *chaves):
    """Aceita item como lista [a, b, c] ou dict {chave: ...}."""
    if isinstance(item, dict):
        return [item.get(k) for k in chaves]
    if len(item) > len(chaves):
        raise SystemExit(f"item com {len(item)} partes, o máximo é {len(chaves)} ({', '.join(chaves)}): {item!r}\n"
                         "Texto com vírgula dentro de [ ] precisa de aspas.")
    return list(item) + [None] * (len(chaves) - len(item))


def sem_acento(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower().replace("'", "").strip()


# ---------- blocos ----------

def b_texto(v, ctx):
    return f'<p class="texto">{md(v)}</p>'


def b_nota(v, ctx):
    return f'<p class="nota-bloco">{md(v)}</p>'


def b_frase(v, ctx):
    return f'<p class="frase">{md(v)}</p>'


def b_conclusao(v, ctx):
    return f'<p class="conclusao">{md(v)}</p>'


def b_citacao(v, ctx):
    return f'<p class="citacao">{md(v)}</p>'


def b_regua(v, ctx):
    return '<hr class="regua">'


def b_espaco(v, ctx):
    return f'<div style="height:{float(v)}mm"></div>'


def b_destaques(v, ctx):
    linhas = "".join(f'<div class="dest"><div class="dest-t">{md(t)}</div><div class="dest-x">{md(x)}</div></div>'
                     for t, x in (par(i, "titulo", "texto") for i in v))
    return f'<hr class="regua">{linhas}'


def b_sumario(v, ctx):
    linhas = "".join(f'<div class="sum-l"><span class="sum-n">{n}</span><span>{e(nome)}</span></div>'
                     for n, nome in ctx["secoes"])
    nota = f'<p class="nota-bloco" style="margin-top:7mm">{md(v["nota"])}</p>' if isinstance(v, dict) and v.get("nota") else ""
    return f'<div class="sumario">{linhas}</div>{nota}'


def b_colunas(v, ctx):
    itens = [par(i, "rotulo", "valor", "etiqueta") for i in v["itens"]]
    maior = max(float(x[1]) for x in itens) or 1
    alt = float(v.get("altura", 62))
    cols = []
    for rot, val, etq in itens:
        h = max(float(val) / maior * alt, 0.6)
        cls = "col-b dest" if str(rot) == str(v.get("destaque")) else "col-b"
        cols.append(f'<div class="col"><div class="col-v{" dest" if "dest" in cls else ""}">{e(etq if etq is not None else val)}</div>'
                    f'<div class="{cls}" style="height:{h:.1f}mm"></div><div class="col-r">{e(rot)}</div></div>')
    titulo = f'<p class="graf-t">{md(v["titulo"])}</p>' if v.get("titulo") else ""
    nota = f'<p class="nota-bloco">{md(v["nota"])}</p>' if v.get("nota") else ""
    return f'{titulo}<div class="colunas" style="height:{alt + 14}mm">{"".join(cols)}</div>{nota}'


def b_kpis(v, ctx):
    itens = [par(i, "valor", "rotulo") for i in v]
    cel = "".join(f'<div class="kpi"><div class="kpi-v">{md(a)}</div><div class="kpi-r">{md(b)}</div></div>' for a, b in itens)
    return f'<div class="kpis" style="grid-template-columns:repeat({len(itens)},1fr)">{cel}</div>'


def b_numeros(v, ctx):
    itens = [par(i, "valor", "rotulo", "apoio") for i in v]
    return "".join(f'<div class="num-p"><div class="num-pv">{md(a)}</div><div class="num-pr">{md(b)}</div>'
                   + (f'<div class="num-pa">{md(c)}</div>' if c else "") + "</div>" for a, b, c in itens)


def b_numero(v, ctx):
    return f'<div class="numero"><div class="numero-v">{md(v["valor"])}</div><div class="numero-r">{md(v.get("rotulo", ""))}</div></div>'


def b_grupos(v, ctx):
    out = []
    for n, g in enumerate(v, 1):
        itens = "".join(f"<div>{md(i)}</div>" for i in g.get("itens", []))
        out.append(f'<div class="grupo"><div class="grupo-n">{n}</div><div class="grupo-t">{md(g["titulo"])}</div>'
                   f'<div class="grupo-i">{itens}</div></div>')
    return "".join(out)


def b_cartoes(v, ctx):
    if isinstance(v, list):
        v = {"itens": v}
    numerado = v.get("numerado", True)
    linha = "azul" if v.get("linha") == "azul" else "preta"
    out = []
    for n, i in enumerate(v["itens"], 1):
        t, sub, x = par(i, "titulo", "sub", "texto")
        out.append(f'<div class="cartao {linha}">' + (f'<div class="cartao-n">{n}</div>' if numerado else "")
                   + f'<div class="cartao-t">{md(t)}</div>' + (f'<div class="cartao-s">{md(sub)}</div>' if sub else "")
                   + (f'<div class="cartao-x">{md(x)}</div>' if x else "") + "</div>")
    estilo = f' {v["estilo"]}' if v.get("estilo") else ""
    return f'<div class="cartoes{estilo}">{"".join(out)}</div>'


def b_secoes(v, ctx):
    return "".join(f'<div class="secao-b"><div class="secao-r">{md(r)}</div><div class="secao-t">{md(t)}</div>'
                   f'<div class="secao-x">{md(x)}</div></div>' for r, t, x in (par(i, "rotulo", "titulo", "texto") for i in v))


def b_caixa(v, ctx):
    return (f'<div class="caixa"><div class="caixa-t">{md(v["titulo"])}</div>'
            + (f'<div class="caixa-s">{md(v["subtitulo"])}</div>' if v.get("subtitulo") else "")
            + (f'<div class="caixa-x">{md(v["texto"])}</div>' if v.get("texto") else "") + "</div>")


def b_itens(v, ctx):
    if isinstance(v, dict):
        rotulo, v = v.get("rotulo"), v["itens"]
    else:
        rotulo = None
    cel = "".join(f'<div class="item"><div class="item-t">{md(t)}</div><div class="item-x">{md(x)}</div></div>'
                  for t, x in (par(i, "titulo", "texto") for i in v))
    return (f'<p class="rotulo-cx">{e(rotulo)}</p>' if rotulo else "") + f'<div class="itens">{cel}</div>'


def b_passos(v, ctx):
    return '<div class="passos">' + "".join(
        f'<div class="passo"><span class="passo-n">{n}</span><span class="passo-t">{md(t)}</span><span class="passo-x">{md(x)}</span></div>'
        for n, (t, x) in enumerate((par(i, "titulo", "texto") for i in v), 1)) + "</div>"


def b_barras(v, ctx):
    itens = [par(i, "rotulo", "valor", "texto") for i in v["itens"]]
    maior = max(float(x[1]) for x in itens) or 1
    linhas = []
    for k, (rot, val, txt) in enumerate(itens):
        w = max(float(val) / maior * 100, 0.4)
        linhas.append(f'<div class="barra-l"><div class="barra-r">{md(rot)}</div><div class="barra-tr">'
                      f'<div class="barra-b{" dest" if k == 0 else ""}" style="width:{w:.1f}%"></div></div>'
                      f'<div class="barra-v">{md(txt if txt is not None else val)}</div></div>')
    titulo = f'<p class="graf-t">{md(v["titulo"])}</p>' if v.get("titulo") else ""
    nota = f'<p class="nota-bloco">{md(v["nota"])}</p>' if v.get("nota") else ""
    return f'{titulo}<div class="barras">{"".join(linhas)}</div>{nota}'


def b_tabela(v, ctx):
    cols = v["colunas"]
    larg = v.get("larguras") or [100 / len(cols)] * len(cols)
    cg = "".join(f'<col style="width:{w}%">' for w in larg)
    cab = "".join(f"<th>{e(c)}</th>" for c in cols)
    corpo = "".join("<tr>" + "".join(f'<td{" class=pri" if j == 0 else ""}>{md(c)}</td>' for j, c in enumerate(l)) + "</tr>"
                    for l in v["linhas"])
    return f'<table class="tab"><colgroup>{cg}</colgroup><thead><tr>{cab}</tr></thead><tbody>{corpo}</tbody></table>'


def b_imagem(v, ctx):
    if isinstance(v, str):
        v = {"arquivo": v}
    src = dado_uri(ctx["base"] / v["arquivo"])
    alt = f' style="max-height:{float(v["altura"])}mm"' if v.get("altura") else ""
    leg = f'<p class="texto" style="margin-top:5mm">{md(v["legenda"])}</p>' if v.get("legenda") else ""
    return f'<img class="imagem" src="{src}" alt="{e(v.get("alt", ""))}"{alt}>{leg}'


def b_mapa(v, ctx):
    """Mapa dos 52 municípios de RO pintado por faixa. valores: {município ou código IBGE: número}."""
    geo = json.loads((RAIZ / "dados-fonte/ibge/ro-municipios.geojson").read_text())
    nomes = {str(m["id"]): m["nome"] for m in json.loads((RAIZ / "dados-fonte/ibge/ro-municipios-nomes.json").read_text())}
    por_nome = {sem_acento(n): c for c, n in nomes.items()}
    valores = {}
    for k, val in (v.get("valores") or {}).items():
        cod = str(k) if str(k) in nomes else por_nome.get(sem_acento(k))
        if cod is None:
            raise SystemExit(f"mapa: município não encontrado: {k}")
        valores[cod] = float(val)
    faixas = [par(f, "ate", "rotulo") for f in v["faixas"]]
    tons = v.get("cores") or (TONS_MAPA[-len(faixas):] if len(faixas) <= 5 else TONS_MAPA)

    def cor(val):
        if val is None:
            return "#eef1f6"
        for i, (ate, _) in enumerate(faixas):
            if ate is None or val < float(ate):
                return tons[i]
        return tons[-1]

    aneis = []
    for f in geo["features"]:
        g = f["geometry"]
        polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        aneis.append((f["properties"]["codarea"], [p[0] for p in polis]))
    pts = [pt for _, ps in aneis for anel in ps for pt in anel]
    lat0 = math.radians(sum(p[1] for p in pts) / len(pts))
    xs = [p[0] * math.cos(lat0) for p in pts]
    ys = [-p[1] for p in pts]
    x0, y0, w, h = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    W = 1000
    H = W * h / w
    paths = []
    for cod, ps in aneis:
        d = "".join("M" + "L".join(f"{(p[0] * math.cos(lat0) - x0) / w * W:.1f},{(-p[1] - y0) / h * H:.1f}" for p in anel) + "Z" for anel in ps)
        paths.append(f'<path d="{d}" fill="{cor(valores.get(cod))}"><title>{e(nomes.get(cod, cod))}</title></path>')
    leg = "".join(f'<span class="leg"><i style="background:{tons[i]}"></i>{e(r)}</span>' for i, (_, r) in enumerate(faixas))
    alt = float(v.get("altura", 105))
    rot = f'<div class="nota-bloco" style="margin-top:1mm">{md(v["legenda"])}</div>' if v.get("legenda") else ""
    return (f'<svg class="mapa" viewBox="0 0 {W} {H:.0f}" style="height:{alt}mm" stroke="#fff" stroke-width="1.6" stroke-linejoin="round">'
            f'{"".join(paths)}</svg><div class="legenda">{leg}</div>{rot}')


BLOCOS = {k[2:]: f for k, f in globals().items() if k.startswith("b_")}


def bloco(b, ctx):
    if not isinstance(b, dict) or len(b) != 1:
        raise SystemExit(f"bloco inválido (use uma chave só, ex.: {{texto: ...}}): {b!r}")
    tipo, v = next(iter(b.items()))
    if tipo not in BLOCOS:
        raise SystemExit(f"bloco desconhecido: {tipo}. Existem: {', '.join(sorted(BLOCOS))}")
    return f'<div class="b b-{tipo}">{BLOCOS[tipo](v, ctx)}</div>'


# ---------- páginas ----------

def faixa():
    return '<div class="faixa"></div>'


def capa(c, doc, ctx):
    brasao = dado_uri(VENDOR / "simbolos/brasao-ro.png")
    topo = c.get("topo", ["Estado de Rondônia", "Proposta com dados públicos"])
    return f'''<section class="pg capa">{faixa()}
<div class="capa-topo"><img src="{brasao}" alt=""><div><b>{e(topo[0])}</b><span>{e(topo[1] if len(topo) > 1 else "")}</span></div></div>
<div class="capa-meio">
  <div class="capa-k">{e(c.get("kicker", ""))}</div>
  <h1>{e(c.get("titulo", doc["produto"]))}</h1>
  <div class="capa-sub">{md(c.get("subtitulo", ""))}</div>
  {f'<div class="capa-slogan">{md(c["slogan"])}</div>' if c.get("slogan") else ""}
  {f'<div class="capa-x">{md(c["texto"])}</div>' if c.get("texto") else ""}
</div>
<div class="capa-pe"><span>{md(c.get("pe", ""))}</span><b>{md(doc.get("autoria_capa", doc["autoria"]))}</b></div>
</section>'''


def pagina(p, n, total, doc, ctx):
    corpo = "".join(bloco(b, ctx) for b in p.get("blocos", []))
    fonte = f'<span>{md(p["fonte"])}</span>' if p.get("fonte") else "<span></span>"
    return f'''<section class="pg" data-n="{n}">{faixa()}
<div class="cab"><span>{e(doc["produto"])}{(" · " + e(doc["slogan"])) if doc.get("slogan") else ""}</span><b>{n} / {total}</b></div>
<div class="corpo{" centro" if p.get("centralizar") else ""}">
  <div class="kicker">{e(p["_kicker"])}</div>
  <h2>{md(p.get("titulo", ""))}</h2>
  <div class="conteudo">{corpo}</div>
</div>
<div class="rod">{fonte}<b>{e(doc["autoria"])}</b></div>
</section>'''


def montar(cfg, base):
    doc = cfg["documento"]
    doc.setdefault("autoria", "NextTech Ecosystem")
    secoes, paginas = [], []
    for p in cfg["paginas"]:
        if p.get("secao"):
            if not secoes or secoes[-1][1] != p["secao"]:
                secoes.append((len(secoes) + 1, p["secao"]))
            p["_kicker"] = f'{secoes[-1][0]} · {p["secao"]}'.upper()
        else:
            p["_kicker"] = (p.get("kicker") or "").upper()
        paginas.append(p)
    ctx = {"secoes": secoes, "base": base}
    total = len(paginas) + 1
    corpo = capa(cfg.get("capa", {}), doc, ctx) + "".join(pagina(p, i, total, doc, ctx) for i, p in enumerate(paginas, 2))
    fonte = base64.b64encode((VENDOR / "fontes/inter-var.woff2").read_bytes()).decode()
    css = (AQUI / "proposta.css").read_text(encoding="utf-8")
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{e(doc.get("titulo_pdf", doc["produto"]))}</title>
<style>@font-face{{font-family:"Inter";src:url(data:font/woff2;base64,{fonte}) format("woff2");font-weight:100 900}}
{css}</style></head><body>{corpo}
<script>document.fonts.ready.then(()=>{{const o=[...document.querySelectorAll(".pg[data-n]")].filter(p=>{{const c=p.querySelector(".corpo");return c.scrollHeight>c.clientHeight+2}}).map(p=>p.dataset.n);const m=document.createElement("meta");m.name="estouro";m.content=o.join(",");document.head.appendChild(m)}})</script>
</body></html>'''


def chrome():
    for c in CHROMES:
        if c and (Path(c).exists() or shutil.which(c)):
            return c
    raise SystemExit("Chrome não encontrado. Defina CHROME=/caminho/do/chrome.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    yml = Path(args[0]).resolve()
    cfg = yaml.safe_load(yml.read_text(encoding="utf-8"))
    nome = cfg["documento"].get("arquivo") or yml.stem
    out_html, out_pdf = yml.parent / f"{nome}.html", yml.parent / f"{nome}.pdf"
    out_html.write_text(montar(cfg, yml.parent), encoding="utf-8")
    ch = chrome()
    dom = subprocess.run([ch, "--headless=new", "--disable-gpu", "--virtual-time-budget=4000", "--dump-dom", out_html.as_uri()],
                         capture_output=True, text=True, timeout=180).stdout
    estouro = (re.search(r'name="estouro" content="([^"]*)"', dom) or [None, "?"])[1]
    subprocess.run([ch, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={out_pdf}",
                    "--virtual-time-budget=4000", out_html.as_uri()], check=True, capture_output=True, timeout=240)
    if "--site" in sys.argv:
        shutil.copy(out_pdf, RAIZ / "site" / out_pdf.name)
    print(f"{out_pdf.relative_to(RAIZ) if out_pdf.is_relative_to(RAIZ) else out_pdf} · {len(cfg['paginas']) + 1} páginas · {round(out_pdf.stat().st_size / 1024)} KB")
    if estouro and estouro != "?":
        print(f"ATENÇÃO: conteúdo não cabe na página {estouro}. Corte texto ou divida a página.")
    elif estouro == "?":
        print("aviso: não consegui conferir se o conteúdo cabe nas páginas.")


if __name__ == "__main__":
    main()
