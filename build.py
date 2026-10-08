"""Monta o briefing "Rondônia em 5 minutos" num arquivo HTML único, que funciona sem internet.

Uso: python3 build.py
Lê dados-fonte/ (os dados públicos que os dois sites carregam, coletados em 07/10/2026) e
template.html, e grava index.html.
"""
import json
import os
import re
import unicodedata
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTE = os.path.join(AQUI, "dados-fonte")


def ler(nome):
    with open(os.path.join(FONTE, nome), encoding="utf-8") as f:
        return json.load(f)


s1 = ler("s1_dados.json")
lib = ler("s1_lazy_emendas-liberacoes.json")
ren = ler("s1_lazy_renuncia.json")
s2 = ler("s2_cargos.json")
estatais = ler("s2_estatais.json")


def chave(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s).split())


# ------------------------------------------------------------------ órgãos (junta os dois sites)
ugs = {chave(u[2]): u for u in s2["ugs"]}
org2 = {o[0]: o for o in s2["orgaos"]}

cargos_org = defaultdict(lambda: {"qtd": 0, "custo": 0.0, "linhas": 0})
for r in s2["cargos"]:
    q = r[3] or 0
    cargos_org[r[0]]["qtd"] += q
    cargos_org[r[0]]["custo"] += q * (r[5] or 0)
    cargos_org[r[0]]["linhas"] += 1

dic = lib["dic"]
lib_sec = defaultdict(lambda: [0.0, 0])
for r in lib["rows"]:
    lib_sec[dic["sec"][r[4]]][0] += r[5]
    lib_sec[dic["sec"][r[4]]][1] += 1

PEQUENAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "A", "O", "EM", "AO", "AS", "OS", "À", "SOB", "PARA"}


ACENTO = {"EDUCACAO": "Educação", "SEGURANCA": "Segurança", "PUBLICA": "Pública", "PUBLICO": "Público", "PUBLICOS": "Públicos",
          "SAUDE": "Saúde", "PREVIDENCIA": "Previdência", "JUDICIARIA": "Judiciária", "ADMINISTRACAO": "Administração",
          "JUSTICA": "Justiça", "CONTINGENCIA": "Contingência", "ASSISTENCIA": "Assistência", "CIENCIA": "Ciência",
          "TECNOLOGIA": "Tecnologia", "COMERCIO": "Comércio", "SERVICOS": "Serviços", "GESTAO": "Gestão", "HABITACAO": "Habitação",
          "INDUSTRIA": "Indústria", "ORGANIZACAO": "Organização", "COMUNICACOES": "Comunicações", "AMORTIZACAO": "Amortização",
          "DIVIDA": "Dívida", "INVERSOES": "Inversões", "ENCARGOS": "Encargos", "ESSENCIAL": "Essencial", "A": "à",
          "ENERGIA": "Energia", "AGRARIA": "Agrária", "RONDONIA": "Rondônia", "SUPERVISAO": "Supervisão", "FINANCAS": "Finanças", "CONSELHO": "Conselho"}
PALAVRA_A_E_PREP = {"ESSENCIAL"}


def bonito(nome):
    if nome == nome.upper() and not any(ch in nome for ch in "ÁÉÍÓÚÂÊÔÃÕÇ"):
        ws = nome.split()
        nome = " ".join(ACENTO.get(w, w) if not (w == "A" and (i == 0 or ws[i - 1] not in PALAVRA_A_E_PREP)) else w
                        for i, w in enumerate(ws))
    palavras = nome.lower().split()
    out = []
    for i, p in enumerate(palavras):
        out.append(p if (p.upper() in PEQUENAS and i) else p.capitalize())
    return " ".join(out)


# área de cada órgão: a função em que ele tem mais orçamento, agrupada em 7 grandes áreas
AREA_DA_FUNCAO = {
    "EDUCACAO": "Educação", "SAUDE": "Saúde",
    "JUDICIARIA": "Poderes e controle", "LEGISLATIVA": "Poderes e controle", "ESSENCIAL A JUSTICA": "Poderes e controle",
    "SEGURANCA PUBLICA": "Segurança e cidadania", "DIREITOS DA CIDADANIA": "Segurança e cidadania",
    "PREVIDENCIA SOCIAL": "Finanças, gestão e previdência", "ENCARGOS ESPECIAIS": "Finanças, gestão e previdência",
    "ADMINISTRACAO": "Finanças, gestão e previdência", "RESERVA DE CONTINGENCIA": "Finanças, gestão e previdência",
    "ASSISTENCIA SOCIAL": "Social, cultura e esporte", "CULTURA": "Social, cultura e esporte", "DESPORTO E LAZER": "Social, cultura e esporte",
}
melhor = {}
for f in s1["despesa_funcao"]:
    for o in f.get("orgaos", []):
        v = o.get("orcado_atualizado") or o.get("empenhado") or 0
        if v > melhor.get(o["orgao"], ("", -1))[1]:
            melhor[o["orgao"]] = (f["funcao"], v)

dm = s1["despesa_mensal"]["orgaos"]
orgaos = []
for o in s1["orgaos"]:
    u = ugs.get(chave(o["orgao"]))
    sigla = u[1] if u else ""
    vinc = u[5] if u else ""
    nome = org2[sigla][1] if sigla in org2 else o["orgao"]
    c = cargos_org.get(sigla)
    lsec = lib_sec.get(sigla)
    mes = dm.get(o["orgao"], {})
    orgaos.append({
        "nome": bonito(nome), "sigla": sigla, "vinc": vinc, "nat": u[4] if u else "",
        "ini": round(o["orcado_inicial"]), "orc": round(o["orcado_atualizado"]), "emp": round(o["empenhado"]),
        "liq": round(o["liquidado"]), "pag": round(o["pago"]),
        "mes_emp": mes.get("empenhado", []), "mes_pag": mes.get("pago", []),
        "funcao": bonito(melhor.get(o["orgao"], ("", 0))[0]),
        "area": AREA_DA_FUNCAO.get(melhor.get(o["orgao"], ("", 0))[0], "Infraestrutura e desenvolvimento"),
        "cargos": {"qtd": int(c["qtd"]), "custo": round(c["custo"]), "linhas": c["linhas"]} if c else None,
        "emendas": {"valor": round(lsec[0]), "n": lsec[1]} if lsec else None,
    })
orgaos.sort(key=lambda x: -x["orc"])

# ------------------------------------------------------------------ despesa
t = s1["totais"]
despesa = {
    "ini": t["orcado_inicial"], "orc": t["orcado_atualizado"], "emp": t["empenhado"], "liq": t["liquidado"], "pag": t["pago"],
    "meses": s1["despesa_mensal"]["meses"], "mensal": s1["despesa_mensal"]["totais"],
    "funcoes": [{"nome": bonito(f["funcao"]), "orc": f["orcado_atualizado"], "emp": f["empenhado"], "pag": f["pago"]}
                for f in sorted(s1["despesa_funcao"], key=lambda f: -f["orcado_atualizado"])],
    "grupos": [{"nome": bonito(g["grupo"]), "orc": g["orcado_atualizado"], "emp": g["empenhado"], "pag": g["pago"]}
               for g in s1["despesa_grupo"]],
}

# ------------------------------------------------------------------ créditos e renúncia
ag = s1["diario"]["agregados"]
creditos = {"total": ag["valor_total"], "qtd": ag["qtd"], "novo": ag["dinheiro_novo"], "remanejado": ag["remanejado"],
            "leis": ag["qtd_leis"], "valor_leis": ag["valor_leis"], "por_tipo": ag["por_tipo"], "por_mes": ag["por_mes"],
            "top": ag["top_orgaos"]}
r1 = s1["renuncia"]
mes25 = [0.0] * 12
for b in ren["anos"].get("2025", []):
    for i, v in enumerate(b.get("meses", [])):
        mes25[i] += v or 0
renuncia = {"ano": r1["total_ano_corrente"], "anterior": r1["mesmo_periodo_anterior"], "mes26": r1["por_mes"], "mes25": mes25,
            "serie": r1["serie_anual"], "beneficio": r1["por_beneficio"], "setor": r1["por_setor"], "ate": r1["atualizado_ate"]}

# ------------------------------------------------------------------ emendas
ex = s1["emendas_exec"]
ind = defaultdict(lambda: [0.0, 0])
mun = defaultdict(lambda: [0.0, 0])
ano_tipo = defaultdict(lambda: defaultdict(float))
for r in lib["rows"]:
    tipo = dic["tipo"][r[1]]
    ano_tipo[r[0]][tipo] += r[5]
    m = dic["mun"][r[3]] or "Não informado"
    mun[m][0] += r[5]
    mun[m][1] += 1
    if tipo == "individual":
        ind[dic["dep"][r[2]] or "Não informado"][0] += r[5]
        ind[dic["dep"][r[2]] or "Não informado"][1] += 1
emendas = {
    "tot": ex["totais"], "por_tipo": ex["por_tipo"],
    "autores": sorted([{"nome": f["nome"], "tipo": f["tipo"], "orc": f["orcado_atualizado"], "emp": f["empenhado"], "pag": f["pago"]}
                       for f in ex["por_fonte"] if f["orcado_atualizado"]], key=lambda f: f["pag"] / f["orc"]),
    "mensal": s1["emendas_mensal"],
    "lib": {"total": sum(r[5] for r in lib["rows"]), "n": len(lib["rows"]),
            "anos": {a: dict(v) for a, v in sorted(ano_tipo.items())},
            "deps": sorted([[k, round(v[0]), v[1]] for k, v in ind.items()], key=lambda x: -x[1]),
            "muns": sorted([[bonito(k), round(v[0]), v[1]] for k, v in mun.items()], key=lambda x: -x[1])},
}

# ------------------------------------------------------------------ a máquina (cargos)
quadros = sorted([[k, int(v["qtd"]), round(v["custo"]), v["linhas"]] for k, v in cargos_org.items()], key=lambda x: -x[2])
cargos_lista = [[r[0], r[2], int(r[3]) if r[3] else 0, r[4], r[5], r[6]] for r in s2["cargos"]]
maquina = {
    "cargos": 10472, "linhas": 1899, "quadros": 51, "orgaos": 113, "ugs": 81, "custo_ref": 38.0e6,
    "busca_cargos": sum(x[1] for x in quadros), "busca_custo": sum(x[2] for x in quadros),
    "quadros": quadros, "lista": cargos_lista,
    "tabela": [[r[0], r[1]] for r in s2["tabela"]],
    "estatais": [{"n": e["n"], "tipo": e.get("tipo", ""), "nom": e.get("nom", ""), "jeton": e.get("jeton", "")} for e in estatais],
}

# ------------------------------------------------------------------ mapa (malha do IBGE) e emendas por município
import math
geo = ler("ibge/ro-municipios.geojson")
nomes_ibge = {str(m["id"]): m["nome"] for m in ler("ibge/ro-municipios-nomes.json")}
LAT0, LON0, ESC = -10.9, -63.3, 14.5


def proj(lon, lat):
    return [round((lon - LON0) * math.cos(math.radians(LAT0)) * ESC, 2), round(-(lat - LAT0) * ESC, 2)]


def chave_mun(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper().replace("D'OESTE", "DO OESTE").replace("'", " ")
    return " ".join(re.sub(r"[^A-Z ]", " ", s).split())


APELIDO = {"GOV JORGE TEIXEIRA": "GOVERNADOR JORGE TEIXEIRA", "NOVA BRASILANDIA": "NOVA BRASILANDIA DO OESTE",
           "NOVO HORIZONTE": "NOVO HORIZONTE DO OESTE", "SAO FRANCISCO": "SAO FRANCISCO DO GUAPORE"}
munis, idx_mun = [], {}
for f in geo["features"]:
    cod = f["properties"]["codarea"]
    g = f["geometry"]
    polis = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    aneis = [[proj(x, y) for x, y in poli[0]] for poli in polis]
    pts = [p for a in aneis for p in a]
    cx_ = sum(p[0] for p in pts) / len(pts)
    cz_ = sum(p[1] for p in pts) / len(pts)
    nome = nomes_ibge.get(cod, cod)
    idx_mun[chave_mun(nome)] = len(munis)
    munis.append({"cod": cod, "nome": nome, "c": [round(cx_, 2), round(cz_, 2)], "aneis": aneis,
                  "total": 0, "n": 0, "anos": defaultdict(float), "deps": defaultdict(float), "secs": defaultdict(float)})
varios = {"total": 0, "n": 0}
por_dep_mun = defaultdict(lambda: defaultdict(float))
for r in lib["rows"]:
    nm = chave_mun(dic["mun"][r[3]])
    nm = APELIDO.get(nm, nm)
    i = idx_mun.get(nm)
    if i is None:
        varios["total"] += r[5]
        varios["n"] += 1
        continue
    m = munis[i]
    dep = dic["dep"][r[2]] or "Não informado"
    m["total"] += r[5]
    m["n"] += 1
    m["anos"][r[0]] += r[5]
    m["deps"][dep] += r[5]
    m["secs"][dic["sec"][r[4]] or "Não informado"] += r[5]
    por_dep_mun[dep][i] += r[5]
for m in munis:
    m["total"] = round(m["total"])
    m["anos"] = {a: round(v) for a, v in sorted(m["anos"].items())}
    m["deps"] = sorted([[k, round(v)] for k, v in m["deps"].items()], key=lambda x: -x[1])
    m["secs"] = sorted([[k, round(v)] for k, v in m["secs"].items()], key=lambda x: -x[1])
mapa = {"munis": munis, "varios": {"total": round(varios["total"]), "n": varios["n"]},
        "assembleia": proj(-63.9039, -8.7619),
        "deps": sorted([[d, round(sum(v.values())), [[i, round(x)] for i, x in v.items()]] for d, v in por_dep_mun.items()], key=lambda x: -x[1])}

dados = {
    "posicao": {"despesa": "07/10/2026", "emendas": "07/10/2026", "doe": "06/10/2026", "renuncia": "31/08/2026",
                "liberacoes": "03/10/2026", "transicao": "04/10/2026", "cargos": "03/10/2026", "fiscal": "RGF 2º quadrimestre 2026"},
    "despesa": despesa, "orgaos": orgaos, "mapa": mapa, "creditos": creditos, "renuncia": renuncia, "emendas": emendas, "maquina": maquina,
}

with open(os.path.join(AQUI, "template.html"), encoding="utf-8") as f:
    html = f.read()
payload = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = html.replace("/*__DADOS__*/null", payload)
with open(os.path.join(AQUI, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("index.html", round(len(html) / 1024), "KB")

# esboços: esbocos/src/*.html -> esbocos/*.html, com os mesmos dados
src = os.path.join(AQUI, "esbocos", "src")
if os.path.isdir(src):
    for nome in sorted(os.listdir(src)):
        with open(os.path.join(src, nome), encoding="utf-8") as f:
            h = f.read().replace("/*__DADOS__*/null", payload)
            if "/*__FONTES__*/" in h:
                import base64
                ff = []
                for fam, est, peso, arq in [("Inter", "normal", "400 800", "inter-var.woff2")]:
                    with open(os.path.join(AQUI, "vendor", "fontes", arq), "rb") as fo:
                        b64 = base64.b64encode(fo.read()).decode()
                    ff.append(f"@font-face{{font-family:'{fam}';font-style:{est};font-weight:{peso};font-display:block;src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
                h = h.replace("/*__FONTES__*/", "\n".join(ff))
            if "/*__THREE__*/" in h:
                with open(os.path.join(AQUI, "vendor", "three.min.js"), encoding="utf-8") as t3:
                    h = h.replace("/*__THREE__*/", t3.read().replace("</script", "<\\/script"))
        with open(os.path.join(AQUI, "esbocos", nome), "w", encoding="utf-8") as f:
            f.write(h)
        print("esbocos/" + nome, round(len(h) / 1024), "KB")

# site/: o que vai para o ar (Vercel com Root Directory = site)
site = os.path.join(AQUI, "site")
os.makedirs(site, exist_ok=True)
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
for origem, destino in [("rondonia.html", "numeros.html"), ("a-o-ano-passando.html", "a-o-ano-passando.html")]:
    with open(os.path.join(AQUI, "esbocos", origem), encoding="utf-8") as f:
        h = f.read()
    h = h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1)
    h = h.replace("href=\"rondonia.html\"", "href=\"numeros.html\"")
    with open(os.path.join(site, destino), "w", encoding="utf-8") as f:
        f.write(h)
    print("site/" + destino, round(len(h) / 1024), "KB")
