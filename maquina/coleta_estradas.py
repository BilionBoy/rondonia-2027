"""Malha rodoviária estadual e pontes, do Geoportal do DER-RO (página pública https://geo.der.ro.gov.br).

Uso: python3 maquina/coleta_estradas.py [arquivo.html]
     Sem argumento, baixa a página (uns 40 MB: o Geoportal embute todos os dados no HTML, no atributo data-page).
Grava
  dados-fonte/der/geoportal_<data>.json   tudo o que a página traz, menos o token de sessão e o link de rede interna (fora do Git)
  dados-fonte/s8_estradas.json            o que o painel usa: traçado simplificado, pontes, trechos e somas por município e residência
Conferência: a soma dos trechos por tipo tem de bater com o quadro-resumo que o próprio Geoportal publica (tabelaRodovias.tags).
"""
import html
import json
import re
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
URL = "https://geo.der.ro.gov.br/"
BRUTO = RAIZ / "dados-fonte" / "der"
SAIDA = RAIZ / "dados-fonte" / "s8_estradas.json"
TOL = 0.0003  # simplificação do traçado, em graus (cerca de 33 m): de perto, no 3D, a estrada continua no lugar


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").upper().strip()


# grafias do Geoportal que não batem com o IBGE (erro de digitação, nome antigo, distrito)
APELIDO = {"ESPIGAODESTE": "ESPIGAODOESTE", "SAOFRANCISCODOGUAPORA": "SAOFRANCISCODOGUAPORE", "RESIDENTEMEDICI": "PRESIDENTEMEDICI",
           "ALTOALEGREDOPARECIS": "ALTOALEGREDOSPARECIS", "TARILANDIA": "JARU"}
# nomes colados sem separador no Geoportal
COLADOS = {"ALTOALEGREDOPARECISALTAFLORESTADOESTE": ["ALTOALEGREDOSPARECIS", "ALTAFLORESTADOESTE"]}


def norm_mun(n):
    k = re.sub(r"[^A-Z]", "", re.sub(r"D'? ?OESTE|DO OESTE", "DOESTE", sem_acento(n)))
    return APELIDO.get(k, k)


def municipios_de(n):
    """O trecho que passa por mais de um município traz os nomes juntos ("ARIQUEMES / RIO CRESPO")."""
    ms = [m for m in (norm_mun(x) for x in re.split(r"\s*[/,;]\s*|\s+-\s+|\s+E\s+", sem_acento(n))) if m]
    return [y for m in ms for y in COLADOS.get(m, [m])]


def num(s):
    s = str(s or "0").strip()
    if "R$" in s:
        s = s.replace("R$", "").replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def simplifica(pts, tol=TOL):
    """Douglas-Peucker, iterativo."""
    if len(pts) < 3:
        return pts
    manter = [False] * len(pts)
    manter[0] = manter[-1] = True
    pilha = [(0, len(pts) - 1)]
    while pilha:
        a, b = pilha.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        L = (dx * dx + dy * dy) ** .5 or 1e-12
        imax, dmax = -1, 0
        for i in range(a + 1, b):
            x, y = pts[i]
            d = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
            if d > dmax:
                imax, dmax = i, d
        if dmax > tol:
            manter[imax] = True
            pilha += [(a, imax), (imax, b)]
    return [p for p, k in zip(pts, manter) if k]


def linhas(geom):
    if not geom:
        return []
    c = geom["coordinates"]
    ls = [c] if geom["type"] == "LineString" else c if geom["type"] == "MultiLineString" else []
    out = []
    for l in ls:
        s = simplifica([(round(p[0], 5), round(p[1], 5)) for p in l])
        if len(s) >= 2:
            out.append([[round(x, 4), round(y, 4)] for x, y in s])
    return out


def main():
    hoje = date.today().isoformat()
    if len(sys.argv) > 1:
        texto = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 (painel de dados públicos)"})
        texto = urllib.request.urlopen(req, timeout=300).read().decode("utf-8")
    p = json.loads(html.unescape(re.search(r'data-page="([^"]*)"', texto).group(1)))["props"]
    for k in ("token", "linksPaineis", "autenticado", "usuarioAutenticadoPorUrl"):
        p.pop(k, None)
    BRUTO.mkdir(parents=True, exist_ok=True)
    (BRUTO / f"geoportal_{hoje}.json").write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")

    # traçado das rodovias estaduais, por camada
    # a camada "Planejadas(Novo-Decreto)" é a de interesse de incorporar: estradas que ainda não são do Estado
    COB = {"DER-RO-Camada-Pavimentadas": "pav", "DER-RO-Camada-Não-Pavimentadas": "terra", "DER-RO-Camada-Planejadas": "plan"}
    rod, km_cam = [], Counter()
    mun = defaultdict(lambda: {"pav": 0.0, "terra": 0.0, "plan": 0.0, "rodovias": set(), "pontes": [], "rr": Counter()})
    rr = defaultdict(lambda: {"pav": 0.0, "terra": 0.0, "plan": 0.0, "municipios": set()})
    for camada, cob in COB.items():
        for f in p["camadas"][camada]["features"]:
            q = f["properties"]
            ext = num(q.get("EXTENSAO"))
            km_cam[cob] += ext
            g = linhas(f["geometry"])
            if not g:
                continue
            ms = municipios_de(q.get("MUNICIPIO"))
            n_rr = re.match(r"\s*(\d+)", q.get("LOTES_RR") or "")
            r_ = f"DER-{n_rr[1]}RR" if n_rr else ""   # "5ª RR" (às vezes com acento quebrado) vira "DER-5RR", como no cadastro
            rod.append({"c": cob, "r": q.get("RODOVIA") or q.get("Name"), "sre": q.get("SRE"), "m": ms, "rr": r_, "rev": q.get("TIPO_REVES"),
                        "ext": round(ext, 2), "ini": q.get("TRECHO_INI"), "fim": q.get("TRECHO_FIM"), "cl": q.get("CLAS_FUNCI"), "g": g})
            for m in ms:  # trecho em mais de um município: a extensão é dividida em partes iguais
                mun[m][cob] += ext / len(ms)
                mun[m]["rodovias"].add(q.get("RODOVIA") or q.get("Name"))
                mun[m]["rr"][r_] += ext / len(ms)
            if r_:
                rr[r_][cob] += ext
                rr[r_]["municipios"].update(ms)

    federais = [{"br": f["properties"].get("Codigo_BR"), "g": linhas(f["geometry"])} for f in p["malhaFederal"]["features"]]
    federais = [x for x in federais if x["g"]]

    pontes = []
    for tipo, ls in p["pontes"].items():
        for x in ls:
            try:
                lat, lon = float(x["latitude"]), float(x["longitude"])
            except (TypeError, ValueError):
                continue
            madeira = "Madeira" in tipo
            pt = {"t": tipo, "madeira": madeira, "n": x.get("nome_comum") or f"Ponte na {x.get('nome_rodovia')}", "rio": x.get("rio"), "rod": x.get("nome_rodovia"),
                  "sre": x.get("codigo_sre"), "mun": x.get("municipio"), "m": norm_mun(x.get("municipio")),
                  "rr": re.sub(r".*- ", "", x.get("residencia_nome") or ""), "ext": num(x.get("extensao")), "lat": round(lat, 5), "lon": round(lon, 5)}
            pontes.append(pt)
            if madeira:
                mun[pt["m"]]["pontes"].append(pt["n"])

    # trechos cadastrados (patrimônio): valor reavaliado e estado de conservação
    sres = [s for s in p["dadosDosSres"] if not s.get("deleted_at")]
    estado = Counter((s.get("situacao_rodovia") or s.get("status") or "sem registro").lower() for s in sres)
    valor = sum(num(s.get("valor_reavaliado_total")) for s in sres)
    valor_ini = sum(num(s.get("valor_inicial")) for s in sres)
    valor_rr = defaultdict(float)
    nomes_rr = {r["id"]: re.sub(r".*- ", "", r["nome"]) for r in p["residencias"]}
    sede_rr = {re.sub(r".*- ", "", r["nome"]): re.sub(r"^.*Regional de (.*?) - .*$", r"\1", r["nome"]) for r in p["residencias"]}
    for s in sres:
        valor_rr[nomes_rr.get(s.get("id_residencia_resp"), "sem residência")] += num(s.get("valor_reavaliado_total"))

    tags = {t["Categoria"]: round(t["Total"], 2) for t in p["tabelaRodovias"]["tags"]}
    # quilômetros oficiais: soma do cadastro de trechos (é a conta do relatório "Rodovias DER": 6.964,84 km)
    km_tipo = Counter()
    for s in sres:
        km_tipo[s.get("tipo_rodovia") or "sem tipo"] += num(s.get("extensao"))
    out = {
        "meta": {"fonte": "Geoportal do DER-RO (página pública, dados embutidos)", "url": URL, "coletado_em": hoje,
                 "regra": "Traçado simplificado (Douglas-Peucker, ~130 m) só para desenho; quilômetros vêm do campo EXTENSAO de cada trecho."},
        "resumo": {"km": {k: round(v, 2) for k, v in km_tipo.items()}, "km_total": round(sum(km_tipo.values()), 2), "geoportal": tags, "camadas_km": {k: round(v, 2) for k, v in km_cam.items()},
                   "trechos": len(sres), "estado": dict(estado), "valor_reavaliado": round(valor, 2), "valor_inicial": round(valor_ini, 2),
                   "pontes": dict(Counter(x["t"] for x in pontes)),
                   "madeira_n": sum(x["madeira"] for x in pontes), "madeira_m": round(sum(x["ext"] for x in pontes if x["madeira"]), 2),
                   "municipios_com_madeira": len({x["m"] for x in pontes if x["madeira"]}), "rodovias": len({x["r"] for x in rod}),
                   "distritos": len(p["distritos"]), "usinas": len(p["usinas"])},
        "rodovias": rod, "federais": federais, "pontes": pontes,
        "municipios": {m: {"pav": round(v["pav"], 2), "terra": round(v["terra"], 2), "plan": round(v["plan"], 2), "rodovias": sorted(v["rodovias"]),
                           "pontes_madeira": len(v["pontes"]), "rr": v["rr"].most_common(1)[0][0] if v["rr"] else ""} for m, v in mun.items() if m},
        "residencias": {k: {"pav": round(v["pav"], 2), "terra": round(v["terra"], 2), "plan": round(v["plan"], 2), "municipios": len(v["municipios"]),
                            "sede": sede_rr.get(k, "")} for k, v in sorted(rr.items(), key=lambda x: int(re.sub(r"\D", "", x[0])))},
        "valor_por_residencia": {k: round(v, 2) for k, v in sorted(valor_rr.items(), key=lambda x: -x[1])},
        "sede_residencia": sede_rr,
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    r = out["resumo"]
    print(f"rodovias {len(rod)} trechos desenhados ({sum(len(l) for x in rod for l in x['g'])} pontos), federais {len(federais)}, pontes {len(pontes)}")
    print("camadas km:", r["camadas_km"], "| geoportal:", tags)
    print(f"madeira {r['madeira_n']} ({r['madeira_m']} m, {r['municipios_com_madeira']} municípios); valor reavaliado R$ {valor/1e9:.2f} bi; estado {dict(estado)}")
    print(f"saída {SAIDA.stat().st_size/1e6:.2f} MB; municípios {len(out['municipios'])}")


if __name__ == "__main__":
    main()
