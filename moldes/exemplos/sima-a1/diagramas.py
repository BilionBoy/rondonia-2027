"""Diagramas vetoriais do SIMA A1 (F07, F12, F13). Gera assets/*.svg; texto em fonte do documento.

Uso: python3 moldes/exemplos/sima-a1/diagramas.py
"""
from html import escape
from pathlib import Path

AQUI = Path(__file__).parent
NAVAL, AZUL, CLARO, FUNDO, LINHA, TINTA, APOIO, ALERTA = "#0f2c66", "#1a56b8", "#dbe6f6", "#f3f6fb", "#c9d3e3", "#15171c", "#3f4550", "#c4451c"


def txt(x, y, s, size=24, weight=400, cor=TINTA, anchor="start"):
    linhas = s.split("\n")
    out = [f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{cor}" text-anchor="{anchor}">']
    for i, l in enumerate(linhas):
        out.append(f'<tspan x="{x}" dy="{0 if i == 0 else size * 1.25:.0f}">{escape(l)}</tspan>')
    return "".join(out) + "</text>"


def caixa(x, y, w, h, fundo="#fff", borda=LINHA, raio=12, esp=2):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{raio}" fill="{fundo}" stroke="{borda}" stroke-width="{esp}"/>'


def seta(x1, y1, x2, y2, cor=AZUL, tracejada=False, esp=3):
    d = ' stroke-dasharray="9 7"' if tracejada else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{cor}" stroke-width="{esp}"{d} marker-end="url(#p-{cor[1:]})"/>'


def marca(x, y, n):
    return f'<circle cx="{x}" cy="{y}" r="17" fill="{ALERTA}"/>' + txt(x, y + 7, str(n), 20, 800, "#fff", "middle")


def svg(w, h, corpo):
    marc = "".join(
        f'<marker id="p-{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in (AZUL, NAVAL, APOIO, ALERTA))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="Inter, Arial, sans-serif">'
            f'<defs>{marc}</defs><rect width="{w}" height="{h}" fill="#fff"/>{corpo}</svg>')


def f12():
    W, H = 1400, 870
    c = [txt(40, 58, "Fluxo atual da gestão de materiais e patrimônio", 36, 800, NAVAL),
         txt(40, 96, "Modelo típico de funcionamento, a validar por unidade. Sem o SIMA.", 22, 400, APOIO)]
    etapas = [("Escola / unidade", "Pede material por\nofício ou SEI;\nrecebe e confere;\nbens em planilha\nlocal"),
              ("Superintendência\nregional", "Reúne pedidos e\ninformações das\nescolas; repassa\npor e-mail, planilha\nou SEI"),
              ("Almoxarifado e\npatrimônio", "Estoque no SGA;\ntombamento e\nmovimentação no\ne-Estado;\nconferência manual"),
              ("Registro oficial\n(e-Estado)", "Bens móveis\nregistrados; a\natualização depende\ndo lançamento\ncentral"),
              ("Contabilidade\n(SIGEF)", "Lançamentos e\nconciliação com\nrelatórios extraídos\ne planilhas")]
    x, y, w, h, gap = 40, 140, 250, 330, 25
    for i, (t, d) in enumerate(etapas):
        xi = x + i * (w + gap)
        c.append(caixa(xi, y, w, h, FUNDO, LINHA))
        c.append(f'<rect x="{xi}" y="{y}" width="{w}" height="96" rx="12" fill="{NAVAL}"/>')
        c.append(f'<rect x="{xi}" y="{y + 70}" width="{w}" height="26" fill="{NAVAL}"/>')
        c.append(txt(xi + 18, y + 40, t, 24, 700, "#fff"))
        c.append(txt(xi + 18, y + 140, d, 20, 400, TINTA))
        if i < len(etapas) - 1:
            c.append(seta(xi + w + 1, y + 200, xi + w + gap - 2, y + 200, AZUL))
            c.append(seta(xi + w + gap - 2, y + 250, xi + w + 1, y + 250, APOIO, True, 2))
    for n, xm, ym in ((1, x + w - 10, y + 115), (2, x + 2 * (w + gap) - 10, y + 115),
                      (3, x + 3 * (w + gap) - 10, y + 115), (4, x + 5 * (w + gap) - gap - 10, y + 115)):
        c.append(marca(xm, ym, n))
    c.append(txt(40, 510, "Seta cheia: envio de pedidos, bens e informações.   Seta tracejada: retorno de confirmações e pendências.", 19, 400, APOIO))
    c.append(caixa(40, 540, W - 80, 300, "#fff", LINHA))
    c.append(txt(70, 588, "Pontos de ruptura", 28, 800, NAVAL))
    rupturas = [("O bem muda de sala ou de escola antes de o registro oficial", "ser atualizado; o histórico fica em mensagens e planilhas."),
                ("Cada unidade mantém sua própria planilha de bens e materiais,", "sem identificação comum nem versão única."),
                ("O inventário é consolidado manualmente, unidade por unidade,", "a partir de listas e relatórios de formatos diferentes."),
                ("A conciliação contábil depende de relatórios extraídos e", "ajustados à mão; as diferenças chegam sem origem clara.")]
    for i, (a, b) in enumerate(rupturas):
        col, lin = i % 2, i // 2
        xr, yr = 70 + col * 650, 640 + lin * 105
        c.append(marca(xr + 17, yr + 6, i + 1))
        c.append(txt(xr + 50, yr + 13, f"{a}\n{b}", 19, 400, TINTA))
    return svg(W, H, "".join(c))


def f13():
    W, H = 1400, 1120
    c = [txt(40, 58, "Fluxo atual por atores: o circuito cotidiano", 36, 800, NAVAL),
         txt(40, 96, "Pedido, movimentação, inventário e fechamento. Modelo típico a validar por unidade. Sem o SIMA.", 22, 400, APOIO)]
    raias = ["Escola /\nunidade", "Regional", "Almoxarifado", "Patrimônio", "Contabilidade", "Sistemas e\nregistros"]
    colunas = ["1. Pedido e recebimento", "2. Movimentação de bens", "3. Inventário anual", "4. Fechamento do período"]
    x0, y0, lw, rh, cw = 40, 170, 190, 145, 292
    for j, col in enumerate(colunas):
        c.append(f'<rect x="{x0 + lw + j * cw}" y="{y0 - 50}" width="{cw - 6}" height="42" rx="8" fill="{NAVAL}"/>')
        c.append(txt(x0 + lw + j * cw + 14, y0 - 22, col, 19, 700, "#fff"))
    for i, r in enumerate(raias):
        yi = y0 + i * rh
        c.append(f'<rect x="{x0}" y="{yi}" width="{W - 80}" height="{rh - 6}" fill="{FUNDO if i % 2 == 0 else "#fff"}" stroke="{LINHA}"/>')
        c.append(f'<rect x="{x0}" y="{yi}" width="{lw - 10}" height="{rh - 6}" fill="{CLARO}"/>')
        c.append(txt(x0 + 16, yi + 60, r, 22, 700, NAVAL))
    passos = {  # (raia, coluna): texto
        (0, 0): "Identifica a necessidade\ne pede por ofício/SEI", (2, 0): "Separa e entrega;\nbaixa o estoque no SGA",
        (0, 0.55): None,
        (5, 0): "SGA: saída de estoque\nSEI: processo do pedido",
        (0, 1): "Muda o bem de sala ou\nescola; anota na planilha", (1, 1): "Autoriza ou informa\na transferência",
        (3, 1): "Lança a transferência\nno e-Estado", (5, 1): "e-Estado: registro\noficial do bem móvel",
        (0, 2): "Comissão local confere\nos bens com lista impressa", (1, 2): "Reúne as listas\ndas escolas",
        (3, 2): "Consolida, apura\nnão localizados e achados", (5, 2): "Planilhas e relatórios\nem formatos diferentes",
        (2, 3): "Fecha o estoque do\nperíodo (base do TC-13)", (3, 3): "Fecha o inventário de\nmóveis (base do TC-15)",
        (4, 3): "Concilia valores e\nlança no SIGEF", (5, 3): "SIGEF: registro contábil\ne demonstrativos",
    }
    pos = {}
    for (r, k), t in passos.items():
        if t is None:
            continue
        xb, yb = x0 + lw + int(k) * cw + 8, y0 + r * rh + 18
        c.append(caixa(xb, yb, cw - 22, rh - 42, "#fff", AZUL, 10, 2))
        c.append(txt(xb + 12, yb + 38, t, 18, 500, TINTA))
        pos[(r, int(k))] = (xb, yb, cw - 22, rh - 42)
    ligacoes = [((0, 0), (2, 0)), ((2, 0), (5, 0)), ((0, 1), (1, 1)), ((1, 1), (3, 1)), ((3, 1), (5, 1)),
                ((0, 2), (1, 2)), ((1, 2), (3, 2)), ((3, 2), (5, 2)), ((3, 3), (4, 3)), ((4, 3), (5, 3))]
    xa, ya, wa, ha = pos[(2, 3)]
    xb, yb, wb, hb = pos[(4, 3)]
    c.append(f'<polyline points="{xa},{ya + ha / 2} {xa - 7},{ya + ha / 2} {xa - 7},{yb + hb / 2} {xb - 3},{yb + hb / 2}" fill="none" '
             f'stroke="{AZUL}" stroke-width="2.5" marker-end="url(#p-{AZUL[1:]})"/>')
    for a, b in ligacoes:
        xa, ya, wa, ha = pos[a]
        xb, yb, wb, hb = pos[b]
        x = xa + wa / 2
        c.append(seta(x, ya + ha, x, yb - 4, AZUL, False, 2.5))
    for (r, k), n in (((0, 1), 1), ((0, 0), 2), ((3, 2), 3), ((4, 3), 4)):
        xb, yb, wb, hb = pos[(r, k)]
        c.append(marca(xb + wb - 6, yb + 4, n))
    yl = y0 + len(raias) * rh + 16
    c.append(txt(40, yl + 22, "Pontos de ruptura:  1 bem muda de lugar antes do registro;  2 controles em planilha local;", 20, 500, ALERTA))
    c.append(txt(40, yl + 52, "3 consolidação manual do inventário;  4 conciliação a partir de relatórios ajustados à mão.", 20, 500, ALERTA))
    return svg(W, H, "".join(c))


def f07():
    W, H = 1400, 1000
    c = [txt(40, 58, "Ecossistema atual: atores e sistemas por competência", 36, 800, NAVAL),
         txt(40, 96, "Quem registra o quê hoje. Linhas cheias: registro; tracejadas: consulta, planilha ou documento.", 22, 400, APOIO)]
    sistemas = [("e-Estado", "Registro patrimonial oficial\nde bens móveis (Estado)"),
                ("SGA", "Almoxarifado e materiais\nde consumo (SEDUC)"),
                ("SIGEF", "Contabilidade e execução\norçamentária (Estado)"),
                ("SEI", "Processos, ofícios\ne documentos"),
                ("Planilhas locais", "Controles paralelos de\nescolas e setores"),
                ("SGIS (histórico)", "2023–2025; declarado inviável\npara patrimônio em 12/2025")]
    sx, sw, sh, sy0 = 470, 460, 108, 140
    centro = {}
    for i, (t, d) in enumerate(sistemas):
        yi = sy0 + i * (sh + 22)
        fundo, borda = (FUNDO, AZUL) if i < 4 else ("#fff", LINHA)
        c.append(caixa(sx, yi, sw, sh, fundo, borda, 12, 2.5))
        c.append(txt(sx + 20, yi + 38, t, 25, 800, NAVAL if i < 5 else APOIO))
        c.append(txt(sx + 20, yi + 70, d, 19, 400, APOIO))
        centro[t] = (sx, yi + sh / 2, sx + sw)
    esquerda = [("Escolas e unidades", ["SEI", "Planilhas locais"], [False, True]),
                ("Superintendências\nregionais", ["SEI", "Planilhas locais"], [False, True]),
                ("Comissões de\ninventário", ["Planilhas locais", "e-Estado"], [True, True])]
    direita = [("Almoxarifado\ncentral", ["SGA", "SEI"], [False, False]),
               ("Patrimônio", ["e-Estado", "Planilhas locais"], [False, True]),
               ("Contabilidade", ["SIGEF", "e-Estado"], [False, True])]
    aw, ah = 300, 120
    for lado, itens in (("e", esquerda), ("d", direita)):
        for i, (t, alvos, tracos) in enumerate(itens):
            ax = 40 if lado == "e" else W - 40 - aw
            ay = 170 + i * 240
            c.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" rx="12" fill="{NAVAL}"/>')
            c.append(txt(ax + 20, ay + 50, t, 24, 700, "#fff"))
            for alvo, tr in zip(alvos, tracos):
                x1 = ax + aw if lado == "e" else ax
                xe, ym, xd = centro[alvo]
                c.append(seta(x1, ay + ah / 2, xe - 4 if lado == "e" else xd + 4, ym, AZUL if not tr else APOIO, tr, 2.5))
    c.append(caixa(40, 900, W - 80, 66, FUNDO, LINHA))
    c.append(txt(64, 942, "Órgãos centrais e controle: SETIC (tecnologia e e-Estado), patrimônio e contabilidade do Estado, CGE e TCE.", 21, 500, NAVAL))
    return svg(W, H, "".join(c))


if __name__ == "__main__":
    for nome, f in (("a1-f12-as-is-geral.svg", f12), ("a1-f13-as-is-raias.svg", f13), ("a1-f07-ecossistema-atual.svg", f07)):
        (AQUI / "assets" / nome).write_text(f(), encoding="utf-8")
        print(nome)
