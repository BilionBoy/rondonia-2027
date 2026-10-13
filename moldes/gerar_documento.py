"""Gera um documento longo (projeto institucional, plano de trabalho) a partir de um Markdown, no padrão visual dos moldes.

Uso: python3 moldes/gerar_documento.py caminho/documento.md [--site]
Grava <arquivo>.html e <arquivo>.pdf ao lado do .md. Se existir <nome-do-md>.molde.yaml ao lado, ele ajusta capa,
cabeçalho, seções omitidas e pastas de imagens sem tocar no .md. Convenções em moldes/README.md.
O PDF sai do Chrome em duas passadas: a primeira descobre as páginas, a segunda escreve os números no sumário.
"""
import base64
import html
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import markdown
import yaml

from gerar import chrome, dado_uri

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
VENDOR = RAIZ / "vendor"
EXT_IMG = (".svg", ".png", ".jpg", ".jpeg", ".webp")
QUALIDADE = 90  # JPEG das imagens embutidas; 0 = embutir o arquivo original
SELOS = {"DOC": "ok", "DECIDIDO": "ok", "CONFIRMADO": "ok", "NORMA": "ok", "SEI": "ok", "CÓDIGO": "ok", "ACERVO": "ok",
         "FONTE INTERNA": "int", "INFERIDO": "inf", "INFERÊNCIA": "inf", "PROPOSTA": "inf", "ESTIMATIVA": "inf",
         "APURAÇÃO": "abr", "A CONFIRMAR": "abr", "A VALIDAR": "abr", "NÃO RESOLVIDO": "abr", "PENDENTE": "abr", "EM ABERTO": "abr",
         "CONTROVERSO": "con"}
RE_SELO = re.compile(r"\[((?:" + "|".join(sorted(map(re.escape, SELOS), key=len, reverse=True)) + r")(?:\s*[/—–-]\s*[^\]<]{0,120})?)\]")
RE_FIG = re.compile(r"^\s*<!--\s*FIGURA\s+(.+?)-->\s*$")
RE_VISUAL = re.compile(r"^\s*(?:\*\*)?\[?\s*(VISUAL|FIGURA|IMAGEM|QUADRO|DIAGRAMA)\s+(\d+[A-Za-z]?)\s*[—–:\-]\s*(.+?)\s*\]?(?:\*\*)?\s*$", re.I)
RE_MODULO = re.compile(r"^(M[ÓO]DULO|CAP[ÍI]TULO|PARTE)?\s*(\d{1,2})\s*[—–:.\-]\s*(.+)$", re.I)
RE_ANEXO = re.compile(r"^(ANEXO|AP[ÊE]NDICE)(?:\s+EDITORIAL)?\s+([IVXLC]+|\d+|[A-Z])\s*[—–:.\-]\s*(.+)$", re.I)


def e(s):
    return html.escape(str(s if s is not None else ""))


def imagem_uri(caminho, qualidade=90):
    """Embute a imagem no PDF. Fotos e artes rasterizadas (PNG/JPG/WebP) entram como JPEG de alta qualidade, sem
    subamostragem de cor, para o PDF não pesar; o arquivo original em assets/ não é alterado. SVG entra como está."""
    caminho = Path(caminho)
    if caminho.suffix.lower() == ".svg" or not qualidade:
        return dado_uri(caminho)
    try:
        from io import BytesIO
        from PIL import Image
    except ImportError:
        return dado_uri(caminho)
    im = Image.open(caminho)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        fundo = Image.new("RGB", im.size, "white")
        fundo.paste(im, mask=im.split()[-1])
        im = fundo
    buf = BytesIO()
    im.convert("RGB").save(buf, "JPEG", quality=qualidade, subsampling=0, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def separar_frente(texto):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", texto, re.S)
    return (yaml.safe_load(m[1]) or {}, texto[m.end():]) if m else ({}, texto)


def caixa_frase(titulo, grafias):
    """TÍTULO EM CAIXA ALTA → Título em caixa de frase, mantendo siglas e nomes como aparecem no corpo do texto."""
    if titulo != titulo.upper():
        return titulo
    out = []
    for i, p in enumerate(re.split(r"(\s+)", titulo)):
        if not p.strip():
            out.append(p)
            continue
        miolo = re.sub(r"^\W+|\W+$", "", p)
        g = grafias.get(miolo.lower())
        novo = g if g else miolo.lower()
        if i == 0 and novo == miolo.lower():
            novo = novo[:1].upper() + novo[1:]
        out.append(p.replace(miolo, novo, 1) if miolo else p)
    return "".join(out)


def grafias_do_corpo(corpo):
    """Grafia mais comum de cada palavra fora dos títulos (SEDUC, e-Estado, TC-13...)."""
    cont = {}
    for linha in corpo.split("\n"):
        if linha.startswith("#"):
            continue
        for w in re.findall(r"[\wÀ-ÿ][\wÀ-ÿ\-/]*[\wÀ-ÿ]|[\wÀ-ÿ]", linha):
            cont.setdefault(w.lower(), Counter())[w] += 1
    out = {}
    for k, c in cont.items():
        melhor, n = c.most_common(1)[0]
        minusc = c.get(k, 0)
        letras = re.sub(r"[^A-Za-zÀ-ÿ]", "", melhor)
        if melhor == k:
            continue
        if melhor.upper() == melhor and sum(ch.isupper() for ch in melhor) >= 1:
            if len(letras) <= 8 and n > minusc:
                out[k] = melhor                  # siglas: SEDUC, SETIC, TC-13, AS-IS, RFID, A1
        elif minusc == 0:
            out[k] = melhor                      # nome próprio que nunca aparece em minúscula: Rondônia, e-Estado
    return out


def achar_arquivo(nome, bases, pastas):
    if not nome:
        return None
    stem, cand = Path(nome).stem, []
    for base in bases:
        cand += [base / nome] + [base / p / Path(nome).name for p in pastas]
        cand += [base / p / f"{stem}{ext}" for p in ["assets", *pastas] for ext in EXT_IMG]
    return next((c for c in cand if c.exists()), None)


ALTURAS = {}
LIMITE_PAISAGEM = 99  # página deitada desligada: todas as figuras ficam na página em pé (padrão dos documentos)
RETRATO = set()  # artes largas que voltam para página em pé porque a deitada deixaria buraco
ADIAR = {}  # figura -> quantos blocos de texto ela desce para não deixar buraco na página anterior


def figura(ident, titulo, legenda, attrs, base, pastas, numero=None, fonte_padrao=""):
    arq = achar_arquivo(attrs.get("arquivo"), base, pastas)
    fonte = attrs.get("fonte", "").replace("_", " ") or fonte_padrao
    rotulo = f"Figura {numero}" if numero else f"Figura {ident}"
    cap = (f'<figcaption><b>{e(rotulo)} – {e(titulo)}</b>' + (f". {e(legenda)}" if legenda else "")
           + (f'<span class="fig-fonte">Fonte: {e(fonte)}</span>' if fonte else "") + "</figcaption>")
    if arq:
        if arq.suffix.lower() == ".svg":
            conteudo = re.sub(r"<\?xml[^>]*>", "", arq.read_text(encoding="utf-8"))
            vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', conteudo)
            proporcao = float(vb[1]) / float(vb[2]) if vb else 1.4
            arte = conteudo.replace("<svg ", '<svg class="arte" role="img" ', 1)
        else:
            from PIL import Image
            with Image.open(arq) as im:
                proporcao = im.width / im.height
            arte = f'<img class="arte" src="{imagem_uri(arq, QUALIDADE)}" alt="{e(titulo)}">'
        cls = "vis paisagem" if proporcao >= LIMITE_PAISAGEM and ident not in RETRATO else "vis"
        if ident in ALTURAS:
            arte = arte.replace('class="arte"', f'class="arte" style="max-height:{ALTURAS[ident]:.0f}mm"', 1)
        marca = f'<span class="fig-marca">FIGINI{slug(ident)}FIM</span>'
        return f'<figure class="{cls}" id="fig-{slug(ident)}">{marca}{arte}{cap}</figure>', True
    status = attrs.get("status", "a gerar").replace("_", " ").lower()
    return (f'<figure class="vis falta" id="fig-{slug(ident)}"><div class="vaga"><span>FIGURA {e(ident)} · {e(status)}</span>'
            f'<p>{e(titulo)}</p>' + (f'<div class="vaga-x">{e(legenda)}</div>' if legenda else "")
            + f'<small>{e(attrs.get("tipo", "").replace("_", " "))}' + (f' · arquivo previsto: {e(attrs["arquivo"])}' if attrs.get("arquivo") else "")
            + (f' · fonte: {e(fonte)}' if fonte else "") + "</small></div></figure>"), False


def reorganizar(corpo, cfg):
    """Ajustes de conteúdo pedidos no .molde.yaml, sem tocar no .md: corta o que não se publica, troca termos,
    tira seções de nível 2 e leva cada figura para o fim da seção que ela ilustra (figuras espalhadas pelo texto)."""
    linhas = corpo.split("\n")
    for p in cfg.get("parar_em", []):
        k = next((i for i, l in enumerate(linhas) if l.startswith("# ") and re.search(p, l[2:].strip(), re.I)), None)
        if k is not None:
            linhas = linhas[:k]
    for a, b in cfg.get("substituir", []):
        rx = re.compile(a)
        linhas = [l if l.lstrip().startswith("<!--") else rx.sub(b, l) for l in linhas]
    omit = [re.compile(p, re.I) for p in cfg.get("omitir_secoes", [])]
    out, pulando = [], False
    for l in linhas:
        if l.startswith("## ") or l.startswith("# "):
            pulando = l.startswith("## ") and any(p.search(l[3:].strip()) for p in omit)
        if not pulando:
            out.append(l)
    linhas = out
    for ident, secao in (cfg.get("posicoes") or {}).items():
        k = next((i for i, l in enumerate(linhas) if l.lstrip().startswith("<!--") and f"FIGURA {ident} " in l), None)
        if k is None:
            continue
        ini = k
        j = k - 1
        while j >= 0 and not linhas[j].strip():
            j -= 1
        if j >= 0 and linhas[j].startswith(f"**{ident}"):
            ini = j
        bloco = linhas[ini:k + 1]
        del linhas[ini:k + 1]
        h = next((i for i, l in enumerate(linhas) if re.match(rf"^##\s+{re.escape(secao)}\s", l)), None)
        if h is None:
            raise SystemExit(f"posicoes: seção {secao} não encontrada para {ident}")
        fim = next((i for i in range(h + 1, len(linhas)) if linhas[i].startswith("#")), len(linhas))
        while fim > h + 1 and (not linhas[fim - 1].strip() or linhas[fim - 1].strip() == "---"):
            fim -= 1
        linhas[fim:fim] = [""] + bloco + [""]
    return "\n".join(linhas)


def adiar_figuras(corpo):
    if not ADIAR:
        return corpo
    blocos, atual = [], []
    for l in corpo.split("\n"):
        if l.strip():
            atual.append(l)
        elif atual:
            blocos.append(atual)
            atual = []
    if atual:
        blocos.append(atual)
    i = 0
    while i < len(blocos):
        b = blocos[i]
        m = re.match(r"\s*<!--\s*FIGURA\s+(\S+)", b[-1])
        k = ADIAR.get(m[1], 0) if m else 0
        if not k:
            i += 1
            continue
        ini = i - 1 if i > 0 and blocos[i - 1][0].startswith(f"**{m[1]}") else i
        fim = i + 1
        if fim < len(blocos) and blocos[fim][0].startswith("**Leitura"):
            fim += 1
        grupo = blocos[ini:fim]
        del blocos[ini:fim]
        destino, n = ini, 0
        while destino < len(blocos) and n < k and not blocos[destino][0].startswith("# "):
            destino += 1
            n += 1
        def partiria(d):
            if d <= 0 or d >= len(blocos):
                return False
            ant, prox = blocos[d - 1], blocos[d]
            return (ant[0].startswith("**A1-F") or prox[-1].lstrip().startswith("<!-- FIGURA")
                    or (prox[0].startswith("**Leitura") and ant[-1].lstrip().startswith("<!-- FIGURA")))
        while partiria(destino):
            destino += 1  # não separa a legenda, a figura e a leitura de outra figura
        while 0 < destino < len(blocos) and blocos[destino - 1][0].startswith("#") and not blocos[destino][0].startswith("# "):
            destino += 1  # nunca logo depois de um título: o título pularia junto com a figura
        blocos[destino:destino] = grupo
        i = destino + len(grupo)
    return "\n\n".join("\n".join(b) for b in blocos)


def lacunas(pdf_path):
    """Figuras que pularam de página deixando a anterior com pouco texto: {figura: mm livres na página anterior}."""
    usado = ocupacao(pdf_path)
    txt = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout.split("\f")
    out = {}
    for n, pag in enumerate(txt):
        m = re.search(r"FIGINI(\S+?)FIM", pag)
        if not m or n == 0:
            continue
        antes = pag[:m.start()].split("\n")
        corpo = [l for l in antes[1:] if l.strip()]  # tira o cabeçalho
        if corpo:
            continue  # há texto acima da figura na mesma página: não é ela que causou o buraco
        livre = (1 - usado[n - 1]) * 239
        if livre >= 28:
            out[m[1]] = livre
    return out


def preparar(corpo, base, cfg):
    base = base if isinstance(base, list) else [base]
    """Troca marcadores de figura por quadros, separa as seções de nível 1 e tira as que o .molde.yaml omite."""
    grafias = {**grafias_do_corpo(corpo), **{k.lower(): v for k, v in (cfg.get("grafias") or {}).items()}}
    omitir = [re.compile(p, re.I) for p in cfg.get("omitir", [])]
    pastas = cfg.get("pastas_imagens", ["assets"])
    linhas, secoes, figuras, faltando = [], [], [], []
    pulando = False
    parar = [re.compile(p, re.I) for p in cfg.get("parar_em", [])]
    remover = [re.compile(p) for p in cfg.get("remover_linhas", [])]
    renomear = {re.compile(k, re.I): v for k, v in (cfg.get("renomear") or {}).items()}
    for linha in corpo.split("\n"):
        if linha.startswith("# ") and any(p.search(linha[2:].strip()) for p in parar):
            break
        if any(p.search(linha) for p in remover):
            continue
        if linha.startswith("# "):
            for k, v in renomear.items():
                if k.search(linha[2:].strip()):
                    linha = "# " + v
                    break
        ml = re.match(r"^( +)([-*+]|\d+[.)]) ", linha)
        if ml and len(ml[1]) % 4:
            linha = " " * (-(-len(ml[1]) // 2) * 4) + linha.lstrip(" ")
        if linha.startswith("# "):
            titulo = linha[2:].strip()
            pulando = any(p.search(titulo) for p in omitir)
            if pulando:
                continue
            ma, mm = RE_ANEXO.match(titulo), RE_MODULO.match(titulo)
            if ma:
                tipo, num, nome = "anexo", f"{ma[1].capitalize()} {ma[2]}", ma[3]
            elif mm:
                tipo, num, nome = "modulo", mm[2].zfill(2), mm[3]
            else:
                tipo, num, nome = "secao", "", titulo
            nome = caixa_frase(nome.strip(), grafias)
            ident = f"s-{slug(num or nome)[:60]}"
            secoes.append((ident, tipo, num, nome))
            rotulos = cfg.get("rotulos", {})
            rotulo = {"modulo": f"Módulo {num}", "anexo": num}.get(tipo) or next((v for k, v in rotulos.items() if re.search(k, titulo, re.I)), "")
            nova = cfg.get("nova_pagina")
            nova = " nova" if nova is True or (isinstance(nova, list) and any(re.search(k, titulo, re.I) for k in nova)) else ""
            linhas += ["", f'<section class="abre {tipo}{nova}" id="{ident}">' + (f'<div class="abre-k">{e(rotulo)}</div>' if rotulo else "")
                           + f'<h1>{e(nome)}</h1></section>', ""]
            continue
        if pulando:
            continue
        mf = RE_FIG.match(linha)
        if mf:
            partes = [p.strip() for p in mf[1].split("|")]
            ident, titulo = partes[0], (partes[1].title() if len(partes) > 1 else "")
            if ident in cfg.get("ignorar_figuras", []):
                while linhas and not linhas[-1].strip():
                    linhas.pop()
                if linhas and linhas[-1].startswith(f"**{ident}"):
                    linhas.pop()
                continue
            attrs = dict(p.split("=", 1) for p in partes[2:] if "=" in p)
            legenda = ""
            while linhas and not linhas[-1].strip():
                linhas.pop()
            ml2 = re.match(rf"^\*\*{re.escape(ident)}\s*[—–-]\s*(.+?)\*\*\s*(.*)$", linhas[-1]) if linhas else None
            if ml2:
                linhas.pop()
                titulo, legenda = ml2[1].rstrip("."), ml2[2].strip()
            if not cfg.get("legenda_da_descricao", False):
                legenda = ""
            n_fig = len([f for f in figuras if f[2]]) + 1
            bloco, ok = figura(ident, titulo, legenda, attrs, base, pastas,
                               numero=n_fig if cfg.get("numerar_figuras", True) else None, fonte_padrao=cfg.get("fonte_figuras", ""))
            if ok or cfg.get("vagas"):
                figuras.append((ident, titulo, ok, f"fig-{slug(ident)}"))
                linhas += ["", bloco, ""]
            else:
                faltando.append(ident)
            continue
        mv = RE_VISUAL.match(linha)
        if mv:
            bloco, ok = figura(mv[2], mv[3].rstrip("]"), "", {"arquivo": f"img/visual-{mv[2].zfill(2)}.png"}, base, ["img"])
            if ok or cfg.get("vagas"):
                figuras.append((mv[2], mv[3], ok, f"fig-{slug(mv[2])}"))
                linhas += ["", bloco, ""]
            else:
                faltando.append(mv[2])
            continue
        linhas.append(linha)
    return "\n".join(linhas), secoes, figuras, faltando


def selos(h):
    def troca(m):
        partes = re.split(r"\s*/\s*", m[1])
        out = []
        for p in partes:
            chave = next((k for k in sorted(SELOS, key=len, reverse=True) if p.upper().startswith(k)), None)
            if not chave:
                return m[0]
            resto = p[len(chave):].strip(" —–-")
            out.append(f'<span class="selo {SELOS[chave]}">{e(chave)}</span>' + (f'<span class="selo-x">{e(resto)}</span>' if resto else ""))
        return "".join(out)
    h = RE_SELO.sub(troca, h)
    h = re.sub(r"<(h[234])>((?:[IVX]+\.)?\d+(?:\.\d+)*\.?)\s+", r'<\1><span class="hn">\2</span> ', h)
    def tabela(m):
        cols = len(re.findall(r"<th[ >]", m[0].split("</thead>")[0]))
        linhas = m[0].count("<tr>") - 1
        cls = "tab" + (" larga" if cols >= 6 else "") + (" curta" if linhas <= 2 else "")
        return m[0].replace("<table>", f'<table class="{cls}">', 1)
    h = re.sub(r"<table>.*?</table>", tabela, h, flags=re.S)
    return re.sub(r"R\$ ", "R$&nbsp;", h)


def sumario(secoes, figuras, pg):
    def linha(i, n, t, cls=""):
        return (f'<a class="sum-l {cls}" href="#{i}"><span class="sum-n">{e(n)}</span><span class="sum-t">{e(t)}</span>'
                f'<span class="sum-p">{pg.get(i, "")}</span></a>')
    primeiro = next((k for k, s in enumerate(secoes) if s[1] != "secao"), 0)
    corpo = "".join(linha(i, n if tipo == "modulo" else ("" if tipo == "secao" else n), t, tipo) for i, tipo, n, t in secoes[primeiro:])
    out = f'<section class="sumario"><div class="kick">Sumário</div><h2 class="sum-h">O que este documento apresenta</h2>{corpo}</section>'
    prontas = [f for f in figuras if f[2]]
    if prontas:
        fig = "".join(linha(a, f"Figura {n}", t, "fig") for n, (i, t, ok, a) in enumerate(prontas, 1))
        out += f'<section class="sumario lista-fig"><div class="kick">Lista de figuras</div><h2 class="sum-h">Figuras</h2>{fig}</section>'
    
    return out


def capa(c):
    meta = "".join(f"<div><span>{e(k)}</span><b>{e(v)}</b></div>" for k, v in (c.get("ficha") or {}).items())
    topo = (f'<img src="{dado_uri(VENDOR / "simbolos/brasao-ro.png")}" alt="">' if c.get("brasao", True) else "")
    fundo = f' com-fundo" style="background-image:url({c["fundo_uri"]})' if c.get("fundo_uri") else ""
    return f'''<section class="capa{fundo}"><div class="sombra"></div><div class="faixa"></div>
<div class="capa-topo">{topo}<div><b>{e(c.get("topo", "Estado de Rondônia"))}</b><span>{e(c.get("topo2", "Proposta com dados públicos"))}</span></div></div>
<div class="capa-meio">
  <div class="capa-k">{e(c.get("kicker", ""))}</div>
  <h1>{e(c.get("titulo", ""))}</h1>
  <div class="capa-sub">{e(c.get("subtitulo", ""))}</div>
  {f'<div class="capa-slogan">{e(c["slogan"])}</div>' if c.get("slogan") else ""}
  {f'<div class="capa-x">{e(c["texto"])}</div>' if c.get("texto") else ""}
  {f'<div class="capa-meta">{meta}</div>' if meta else ""}
</div>
<div class="capa-pe"><span>{e(c.get("pe", ""))}</span><b>{e(c.get("autoria", "NextTech Ecosystem"))}</b></div>
</section>'''


def montar(c, corpo_html, secoes, figuras, pg):
    fonte = base64.b64encode((VENDOR / "fontes/inter-var.woff2").read_bytes()).decode()
    css = (AQUI / "documento.css").read_text(encoding="utf-8")
    css = css.replace("__CABECALHO__", c.get("cabecalho", c.get("titulo", "")).replace('"', "'")).replace("__RODAPE__", c.get("autoria", "NextTech Ecosystem").replace('"', "'")).replace("__RODAPE_ESQ__", c.get("rodape", "").replace('"', "'"))
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{e(c.get("titulo_pdf", c.get("titulo", "")))}</title>
<style>@font-face{{font-family:"Inter";src:url(data:font/woff2;base64,{fonte}) format("woff2");font-weight:100 900}}
{css}</style></head><body>
{capa(c)}{sumario(secoes, figuras, pg)}<main>{corpo_html}</main></body></html>'''


def imprimir(ch, html_path, pdf_path):
    subprocess.run([ch, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}",
                    "--virtual-time-budget=8000", html_path.as_uri()], check=True, capture_output=True, timeout=900)


def localizar(pdf_path, secoes, figuras, pular):
    """Página de cada seção e figura, lida do PDF: a primeira página, depois do sumário, que traz o texto."""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout.split("\f")
    norm = lambda s: re.sub(r"[^0-9a-zà-ÿ]+", "", s.lower())
    paginas = [norm(t) for t in txt]
    pg, inicio = {}, pular
    for ident, tipo, num, nome in secoes:
        rotulo = {"modulo": f"Módulo {num}", "anexo": num}.get(tipo, "")
        alvo = norm(rotulo + nome)[:40]
        for n in range(inicio, len(paginas)):
            if alvo in paginas[n]:
                pg[ident] = str(n + 1)
                inicio = n
                break
    for k, (ident, titulo, ok, ancora) in enumerate([f for f in figuras if f[2]], 1):
        alvo = norm(f"Figura {k} – {titulo}")[:28]
        n = next((n for n in range(pular, len(paginas)) if alvo in paginas[n]), None)
        if n is not None:
            pg[ancora] = str(n + 1)
    return pg, len(txt) - 1


def orfaos(pdf_path, html_path):
    """Título ou cabeçalho de tabela que ficou como última linha do corpo de uma página (o conteúdo dele foi para a seguinte).
    Lê as linhas do PDF com posição (pdftotext -bbox-layout) e compara com os títulos e cabeçalhos do HTML."""
    import html as H
    doc = html_path.read_text(encoding="utf-8")
    limpa = lambda t: re.sub(r"[^0-9a-zà-ÿ]+", "", H.unescape(re.sub(r"<[^>]+>", " ", t)).lower())
    titulos = {limpa(t) for t in re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", doc, re.S)}
    titulos |= {limpa(t) for t in re.findall(r'<div class="abre-k">(.*?)</div>', doc)}
    cabecalhos = {limpa(" ".join(re.findall(r"<th[^>]*>(.*?)</th>", t, re.S))) for t in re.findall(r"<thead>(.*?)</thead>", doc, re.S)}
    xml = subprocess.run(["pdftotext", "-bbox-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout
    out = []
    for n, pag in enumerate(re.findall(r"<page [^>]*>(.*?)</page>", xml, re.S), 1):
        linhas = []
        for y, corpo in re.findall(r'<line xMin="[\d.]+" yMin="([\d.]+)"[^>]*>(.*?)</line>', pag, re.S):
            if 100 < float(y) < 765:  # só o corpo: sem cabeçalho e rodapé
                linhas.append((float(y), " ".join(re.findall(r">([^<]*)</word>", corpo))))
        if not linhas:
            continue
        linhas.sort()
        # junta as linhas da mesma altura (colunas de tabela) e olha a última faixa
        ult_y = linhas[-1][0]
        ultima = limpa(" ".join(t for y, t in linhas if abs(y - ult_y) < 3))
        if len(ultima) >= 4 and (ultima in titulos or ultima in cabecalhos):
            out.append((n, ultima[:60]))
    return out


def ocupacao(pdf_path):
    """Fração da área do texto ocupada em cada página (0 a 1), medida numa imagem pequena de cada página."""
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["pdftoppm", "-r", "20", "-gray", "-png", str(pdf_path), f"{d}/p"], capture_output=True, check=True)
        out = []
        for f in sorted(Path(d).glob("p-*.png")):
            im = Image.open(f).convert("L")
            w, h = im.size
            top, bot, l, r = int(h * 34 / 297), int(h * 272 / 297), int(w * 30 / 210), int(w * 186 / 210)
            px, ult = im.load(), top
            for y in range(top, bot):
                if any(px[x, y] < 200 for x in range(l, r, 2)):
                    ult = y
            out.append((ult - top) / (bot - top))
        return out


def figuras_no_topo(pdf_path, figuras):
    """Para cada página, a figura que abre a página (antes de qualquer texto), se houver."""
    txt = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, text=True, check=True).stdout.split("\f")
    prontas = [f for f in figuras if f[2]]
    topo = {}
    for n, pag in enumerate(txt):
        linhas = [l for l in pag.split("\n") if l.strip()][1:]  # tira o cabeçalho
        if not linhas:
            continue
        m = re.match(r"\s*Figura (\d+) –", linhas[0])
        if m and int(m[1]) <= len(prontas):
            topo[n] = prontas[int(m[1]) - 1][0]
    return topo


def encaixar(pdf_path, figuras, area_mm=239):
    """Figura que pulou para a página seguinte e deixou buraco: reduz a altura dela para caber no espaço livre."""
    usado, topo, mudou = ocupacao(pdf_path), figuras_no_topo(pdf_path, figuras), False
    for n, ident in topo.items():
        if n == 0 or ident in ALTURAS:
            continue
        livre = (1 - usado[n - 1]) * area_mm - 18  # 18 mm: legenda, fonte e respiro
        if livre >= 62:
            ALTURAS[ident] = livre
            mudou = True
    return mudou


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    entrada = Path(args[0]).resolve()
    if entrada.suffix in (".yaml", ".yml"):
        cfg, projeto = yaml.safe_load(entrada.read_text(encoding="utf-8")) or {}, entrada.parent
        md_path = (projeto / cfg["fonte"]).resolve()
    else:
        md_path, projeto = entrada, entrada.parent
        cfg_path = md_path.with_name(md_path.stem + ".molde.yaml")
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    frente, corpo = separar_frente(md_path.read_text(encoding="utf-8"))
    global QUALIDADE
    QUALIDADE = cfg.get("jpeg_qualidade", 90)
    c = {**frente, **cfg.get("capa", {}), **{k: v for k, v in cfg.items() if k not in ("capa", "omitir", "pastas_imagens", "fonte")}}
    if c.get("fundo"):
        c["fundo_uri"] = imagem_uri(projeto / c["fundo"], QUALIDADE)
    corpo_md = reorganizar(corpo, cfg)
    corpo, secoes, figuras, faltando = preparar(corpo_md, [projeto, md_path.parent], cfg)
    corpo_html = selos(markdown.markdown(corpo, extensions=["tables", "sane_lists", "attr_list", "md_in_html", "fenced_code"]))
    nome = c.get("arquivo") or md_path.stem
    out_html, out_pdf = projeto / f"{nome}.html", projeto / f"{nome}.pdf"
    ch = chrome()
    out_html.write_text(montar(c, corpo_html, secoes, figuras, {}), encoding="utf-8")
    imprimir(ch, out_html, out_pdf)
    ident_por_slug = {slug(f[0]): f[0] for f in figuras}
    anterior = {}
    for _ in range(int(cfg.get("passadas_flutuantes", 24))):
        buracos = {ident_por_slug.get(k, k): v for k, v in lacunas(out_pdf).items()}
        if not buracos:
            break
        for ident, livre in buracos.items():
            if ident in anterior and abs(anterior[ident] - livre) < 4:
                # descer não resolveu (fim de módulo ou tabela que não quebra): reduz até 20% para caber
                if ident not in RETRATO and any(f[0] == ident for f in figuras):
                    RETRATO.add(ident)
                elif livre >= 95 and ident not in ALTURAS:
                    ALTURAS[ident] = livre - 24
                continue
            ADIAR[ident] = ADIAR.get(ident, 0) + max(1, round(livre / 30))
        anterior = buracos
        corpo, secoes, figuras, faltando = preparar(adiar_figuras(corpo_md), [projeto, md_path.parent], cfg)
        corpo_html = selos(markdown.markdown(corpo, extensions=["tables", "sane_lists", "attr_list", "md_in_html", "fenced_code"]))
        out_html.write_text(montar(c, corpo_html, secoes, figuras, {}), encoding="utf-8")
        imprimir(ch, out_html, out_pdf)
    txt0 = subprocess.run(["pdftotext", str(out_pdf), "-"], capture_output=True, text=True).stdout.split("\f")
    pular = 1 + max((i for i, p in enumerate(txt0[:8]) if "LISTA DE FIGURAS" in p.upper() or "O que este documento apresenta" in p), default=1)
    pg, _ = localizar(out_pdf, secoes, figuras, pular)
    out_html.write_text(montar(c, corpo_html, secoes, figuras, pg), encoding="utf-8")
    imprimir(ch, out_html, out_pdf)
    pg2, total = localizar(out_pdf, secoes, figuras, pular)
    if pg2 != pg:
        out_html.write_text(montar(c, corpo_html, secoes, figuras, pg2), encoding="utf-8")
        imprimir(ch, out_html, out_pdf)
        pg = pg2
    for n, t in orfaos(out_pdf, out_html):
        print(f"aviso: página {n} termina com título ou cabeçalho sem conteúdo: {t}")
    if "--site" in sys.argv:
        shutil.copy(out_pdf, RAIZ / "site" / out_pdf.name)
    print(f"{out_pdf} · {total} páginas · {len(secoes)} seções · {round(out_pdf.stat().st_size / 1024)} KB")
    sem = [t for i, _, _, t in secoes if i not in pg]
    if sem:
        print(f"aviso: sumário sem página para: {'; '.join(sem)}")
    faltam = faltando + [i for i, _, ok, _ in figuras if not ok]
    prontas = sum(1 for f in figuras if f[2])
    if prontas or faltam:
        print(f"figuras: {prontas} inseridas" + (f" · sem arquivo, fora do PDF: {', '.join(faltam)}" if faltam else ""))


if __name__ == "__main__":
    main()
