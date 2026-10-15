"""Monta a etapa "O que não aparece" e o painel com as duas abas.

Uso: python3 nao-aparece/build_s3.py   (depois de python3 coleta_s3.py)
Lê dados-fonte/s3_* (bruto) e grava dados-fonte/s3_resumo.json, esbocos/nao-aparece.html,
esbocos/painel.html, site/nao-aparece.html e site/painel.html. Não toca nas 9 etapas.
"""
import base64
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
NOINDEX = '<meta name="robots" content="noindex, nofollow">'

SICONFI_API = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
SICONFI_RREO = "https://siconfi.tesouro.gov.br/siconfi/index.jsf"


def link_rreo(ano):
    return f"{SICONFI_API}/rreo?an_exercicio={ano}&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2007&id_ente=11"


def link_msc(ano, mes):
    return (f"{SICONFI_API}/msc_orcamentaria?id_ente=11&an_referencia={ano}&me_referencia={mes}"
            "&co_tipo_matriz=MSCC&classe_conta=6&id_tv=ending_balance")


def link_diarias(ano, mi=1, mf=12, orgao=""):
    return f"https://transparencia.ro.gov.br/diarias?Exercicio={ano}&MesInicial={mi}&MesFinal={mf}" + (f"&Orgao={orgao}" if orgao else "")
PORTAL_EMPENHO = "https://transparencia.ro.gov.br/despesa/despesa-estadual"
PORTAL_DIARIAS = "https://transparencia.ro.gov.br/diarias"
PORTAL_DETALHE = "https://transparencia.ro.gov.br/Despesa/notas-de-empenho/detalhes"


def ler(nome):
    return json.loads((FONTE / nome).read_text(encoding="utf-8"))


def reais(s):
    s = (s or "0").split(" Clas")[0].replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


def mi(x):
    return round(x / 1e6, 2)


# ------------------------------------------------------------------ 1. restos a pagar (Siconfi, RREO Anexo 7)
def restos_a_pagar():
    rreo = ler("s3_rreo_anexo7.json")["dados"]
    serie = []
    for ano in sorted(rreo):
        v = defaultdict(float)
        for x in rreo[ano]:
            if x["conta"] == "PODER EXECUTIVO" and not x["cod_conta"].endswith("Intra"):
                v[x["cod_conta"]] += x["valor"]
        inscrito = v["RestosAPagarNaoProcessadosInscritosEmExerciciosAnteriores"] + v["RestosAPagarNaoProcessadosInscritosEmExercicioAnterior"]
        serie.append({
            "ano": int(ano),
            "inscrito": mi(inscrito),
            "pago": mi(v["RestosAPagarNaoProcessadosPagos"]),
            "cancelado": mi(v["RestosAPagarNaoProcessadosCancelados"]),
            "processado_cancelado": mi(v["RestosAPagarProcessadosENaoProcessadosLiquidadosCancelados"]),
            "link": link_rreo(ano),
        })
    return {"serie": serie, "cancelado_total": round(sum(s["cancelado"] for s in serie), 1),
            "inscrito_total": round(sum(s["inscrito"] for s in serie), 1)}


# ------------------------------------------------------------------ 2. diárias: contabilidade × portal
def msc_itens():
    return ler("s3_msc_classe6.json")["dados"]


EMPENHADO = ("622130100", "622130200", "622130300", "622130400")


def msc_diarias(itens):
    r = defaultdict(float)
    for x in itens:
        nd = x.get("natureza_despesa") or ""
        if x["poder_orgao"].startswith("101") and x["conta_contabil"] in EMPENHADO and nd[:6] in ("339014", "339015"):
            sinal = 1 if x["natureza_conta"] == "C" else -1
            if x["conta_contabil"] == "622130400":
                r[(nd[:6], "pago")] += sinal * x["valor"]
            r[(nd[:6], "empenhado")] += sinal * x["valor"]
    return {"civil_pago": mi(r[("339014", "pago")]), "militar_pago": mi(r[("339015", "pago")]),
            "civil_empenhado": mi(r[("339014", "empenhado")]), "militar_empenhado": mi(r[("339015", "empenhado")])}


MILITARES = {"PMRO", "CBMRO", "CASA MILITAR"}
APELIDO_PORTAL = {"CASA MILITAR": "CM", "CBMRO": "CBM", "PCRO": "PC", "PMRO": "PM"}


def codigos_portal():
    arq = FONTE / "s3_diarias_orgaos.json"
    return {v: t for v, t in ler(arq.name)["dados"]} if arq.exists() else {}


def codigo_orgao(org, cods):
    c = APELIDO_PORTAL.get(org, org)
    return c if c in cods else ""


def portal_diarias(ano, ate_mes):
    linhas = ler(f"s3_diarias_{ano}.json")["dados"]
    vistos, por_mes, por_orgao = set(), Counter(), Counter()
    bruto = civil = militar = 0.0
    for r in linhas:
        mes, a = int(r["periodo"][3:5]), r["periodo"][6:10]
        if a != str(ano):
            continue
        v = reais(r["valorTotalDiaria"])
        chave = (r["solicitacao"], r["nome"], r["periodo"], r["valorTotalDiaria"], r["autorizacao"])
        if mes <= ate_mes:
            bruto += v
        if chave in vistos:
            continue
        vistos.add(chave)
        por_mes[mes] += v
        if mes <= ate_mes:
            org = r["orgao"].strip()
            por_orgao[org] += v
            if org in MILITARES:
                militar += v
            else:
                civil += v
    return {"total": mi(civil + militar), "civil": mi(civil), "militar": mi(militar), "bruto": mi(bruto),
            "linhas": len(linhas), "unicas": len(vistos),
            "por_mes": [mi(por_mes[m]) for m in range(1, 13)],
            "por_orgao": [[o, mi(v)] for o, v in por_orgao.most_common()]}


def contab_diarias_mensal():
    arq = FONTE / "s3_msc_diarias_2026.json"
    if not arq.exists():
        return []
    m = ler(arq.name)["dados"]
    saida, antes = [], {"339014": 0.0, "339015": 0.0}
    for mes in sorted(m, key=int):
        acum = {"339014": 0.0, "339015": 0.0}
        for x in m[mes]:
            if x["poder_orgao"].startswith("101") and x["conta_contabil"] == "622130400":
                acum[x["natureza_despesa"][:6]] += (1 if x["natureza_conta"] == "C" else -1) * x["valor"]
        saida.append({"mes": int(mes), "civil": mi(acum["339014"] - antes["339014"]),
                      "militar": mi(acum["339015"] - antes["339015"]), "link": link_msc(2026, int(mes))})
        antes = acum
    return saida


def diarias(itens):
    contab_2025 = dict(msc_diarias(itens["2025-12"]), link=link_msc(2025, 12))
    contab_2026 = dict(msc_diarias(itens["2026-06"]), link=link_msc(2026, 6))
    p25 = dict(portal_diarias(2025, 12), link=link_diarias(2025))
    p26 = dict(portal_diarias(2026, 6), link=link_diarias(2026, 1, 6))
    p26_ano = portal_diarias(2026, 12)
    cods = codigos_portal()

    def comp(c, p, rotulo):
        contab = c["civil_pago"] + c["militar_pago"]
        return {"rotulo": rotulo, "contabilidade": round(contab, 1), "portal": p["total"],
                "fora": round(contab - p["total"], 1), "fora_pct": round(100 * (contab - p["total"]) / contab, 1),
                "civil": [c["civil_pago"], p["civil"]], "militar": [c["militar_pago"], p["militar"]],
                "link_contab": c["link"], "link_portal": p["link"]}

    return {"comparacao": [comp(contab_2025, p25, "2025 (ano inteiro)"), comp(contab_2026, p26, "2026 (jan–jun)")],
            "portal_2026_por_mes": p26_ano["por_mes"],
            "mensal_2026": [dict(m, portal=p26_ano["por_mes"][m["mes"] - 1], link_portal=link_diarias(2026, m["mes"], m["mes"]))
                            for m in contab_diarias_mensal()],
            "portal_2025_por_orgao": [[o, v, codigo_orgao(o, cods), link_diarias(2025, orgao=codigo_orgao(o, cods)) if codigo_orgao(o, cods) else ""]
                                      for o, v in p25["por_orgao"][:25]],
            "sem_filtro_no_portal": [o for o, v in p25["por_orgao"] if not codigo_orgao(o, cods)],
            "governo": {o: v for o, v in p25["por_orgao"] if o in ("GOVERNADORIA", "CASA CIVIL", "CASA MILITAR", "CERIMONIAL", "SECOM")},
            "duplicadas": {"2025": [p25["linhas"], p25["unicas"]], "2026": [p26_ano["linhas"], p26_ano["unicas"]]}}


# ------------------------------------------------------------------ 3. fonte livre (MSC) e emendas (painel 2026)
def fontes(itens):
    f = defaultdict(float)
    for x in itens["2026-08"]:
        if x["poder_orgao"].startswith("101") and x["conta_contabil"] in EMPENHADO:
            f[x["fonte_recursos"]] += (1 if x["natureza_conta"] == "C" else -1) * x["valor"]
    total = sum(f.values())
    livre = f.get("1500", 0) + f.get("1501", 0)
    return {"total": mi(total), "livre": mi(livre), "livre_pct": round(100 * livre / total, 1), "link": link_msc(2026, 8),
            "top": [[k, mi(v)] for k, v in sorted(f.items(), key=lambda a: -a[1])[:10]]}


def emendas():
    s1 = ler("s1_dados.json")["emendas_exec"]
    return {"totais": s1["totais"], "por_tipo": s1["por_tipo"], "dados_de": s1.get("dados_de")}


# ------------------------------------------------------------------ 4. 2026 em curso: empenhos grandes quase intocados
def parados_2026():
    notas = ler("s3_empenhos_2026.json")["dados"]
    por_ug = defaultdict(lambda: {"qtd": 0, "parado": 0.0, "notas": []})
    for n in notas:
        e, p = reais(n["valorEmpenhado"]), reais(n["valorPago"])
        if e >= 1e6 and p <= 0.05 * e:
            u = por_ug[n["unidadeGestora"]]
            u["qtd"] += 1
            u["parado"] += e - p
            u["notas"].append([n["numeroEmpenho"], n["dataDocumentoFormatada"], n["credor"], mi(e), mi(p), n["linkDetalhes"]])
    lista = []
    for ug, u in sorted(por_ug.items(), key=lambda a: -a[1]["parado"]):
        u["notas"].sort(key=lambda x: -x[3])
        lista.append({"ug": ug, "qtd": u["qtd"], "parado": mi(u["parado"]), "notas": u["notas"][:8]})
    return {"qtd": sum(u["qtd"] for u in lista), "parado": round(sum(u["parado"] for u in lista), 1), "ugs": lista}


# ------------------------------------------------------------------ 5. por secretaria: notas detalhadas de 2025 e 2026
def limpa(s):
    return re.sub(r"\s*(Valores e Execução Financeira|Classificação Orçamentária)\s*$", "", s or "").strip()


def por_secretaria(ano):
    arq = FONTE / f"s3_detalhes_{ano}.json"
    if not arq.exists():
        return None
    det = ler(arq.name)["dados"]
    lista = ler(f"s3_empenhos_{ano}.json")["dados"]
    ug_de = {n["linkDetalhes"]: n["unidadeGestora"] for n in lista}
    total_lista = sum(reais(n["valorEmpenhado"]) for n in lista)
    ugs = defaultdict(lambda: defaultdict(float))
    notas = defaultdict(list)
    por_mes = defaultdict(float)
    for link, d in det.items():
        ug = ug_de.get(link, "?")
        e = reais(d.get("Valor empenhado final"))
        li = reais(d.get("Valor liquidado no exercício da emissão do empenho")) + reais(d.get("Valor liquidado em anos posteriores ao da emissão do empenho"))
        pg = reais(d.get("Valor pago no exercício do empenho")) + reais(d.get("Valor pago em anos posteriores ao da emissão do empenho"))
        tipo = d.get("Tipo de empenho", "?")
        sem = max(e - li, 0)
        u = ugs[ug]
        u["empenhado"] += e
        u["liquidado"] += li
        u["pago"] += pg
        u["sem_entrega"] += sem
        mes = (d.get("Data de emissão") or "00/00")[3:5]
        u["dezembro"] += sem if mes == "12" else 0
        por_mes[mes] += sem
        u["livre"] += e if "NAO VINCULADOS DE IMPOSTOS" in d.get("Fonte do recurso", "") else 0
        u[f"tipo_{tipo}"] += e
        u["n"] += 1
        if sem >= 1e5:
            notas[ug].append([link, limpa(d.get("Razão social do credor")), tipo, mi(e), mi(li), mi(sem),
                              d.get("Data de emissão", ""), limpa(d.get("Histórico"))[:220], limpa(d.get("Fonte do recurso"))[:70],
                              limpa(d.get("Ação de governo"))[:90], limpa(d.get("Programa de governo"))[:90],
                              limpa(d.get("CPF/CNPJ do credor")), limpa(d.get("Modalidade licitatória"))[:60]])
    saida = []
    for ug, u in ugs.items():
        notas[ug].sort(key=lambda x: -x[5])
        saida.append({"ug": ug, "n": int(u["n"]), "empenhado": mi(u["empenhado"]), "liquidado": mi(u["liquidado"]),
                      "pago": mi(u["pago"]), "sem_entrega": mi(u["sem_entrega"]), "livre": mi(u["livre"]), "dezembro": mi(u["dezembro"]),
                      "global": mi(u["tipo_GLOBAL"]), "estimativo": mi(u["tipo_ESTIMATIVO"]), "ordinario": mi(u["tipo_ORDINARIO"]),
                      "notas": notas[ug][:10]})
    saida.sort(key=lambda a: -a["sem_entrega"])
    cobertura = sum(reais(d.get("Valor empenhado final")) for d in det.values()) / total_lista
    tot = lambda k: round(sum(s[k] for s in saida), 1)
    return {"ano": ano, "notas_detalhadas": len(det), "cobertura_pct": round(100 * cobertura, 1),
            "empenhado": tot("empenhado"), "liquidado": tot("liquidado"), "pago": tot("pago"),
            "sem_entrega": tot("sem_entrega"), "por_mes": [mi(por_mes[f"{m:02d}"]) for m in range(1, 13)], "ugs": saida}


def portal_pago(ano):
    notas = ler(f"s3_empenhos_{ano}.json")["dados"]
    e = sum(reais(n["valorEmpenhado"]) for n in notas)
    p = sum(reais(n["valorPago"]) for n in notas)
    zero = sum(1 for n in notas if reais(n["valorPago"]) == 0)
    return {"ano": ano, "notas": len(notas), "empenhado": mi(e), "pago": mi(p), "zero_pago": zero}


# ------------------------------------------------------------------ 6. empenho por órgão × soma das notas visíveis (2026)
PODERES = {"ASSEMBLEIA LEGISLATIVA DO ESTADO DE RONDONIA": "ALE", "TRIBUNAL DE JUSTICA DO ESTADO DE RONDONIA": "TJ",
           "MINISTERIO PUBLICO DO ESTADO DE RONDONIA": "MP", "TRIBUNAL DE CONTAS DO ESTADO DE RONDONIA": "TCE",
           "DEFENSORIA PUBLICA DO ESTADO DE RONDONIA": "DPE", "RECURSOS SOB A SUPERVISAO DA SECRETARIA DE FINANCAS": "RS/SEFIN",
           "CORPO DE BOMBEIROS MILITAR": "CBOMB", "POLICIA MILITAR": "PM", "POLICIA CIVIL": "PC"}


def chave(s):
    import unicodedata
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", s).split())


def sem_nota_2026():
    s1 = ler("s1_dados.json")
    sig = {chave(u[2]): u[1].upper() for u in ler("s2_cargos.json")["ugs"]}
    for c, t in codigos_portal().items():
        sig.setdefault(chave(t.split(" - ", 1)[-1]), c.upper())
    notas = defaultdict(float)
    for n in ler("s3_empenhos_2026.json")["dados"]:
        notas[n["unidadeGestora"].upper()] += reais(n["valorEmpenhado"])
    saida = []
    for o in s1["orgaos"]:
        s = PODERES.get(chave(o["orgao"])) or sig.get(chave(o["orgao"]))
        visto = notas.get(s, 0.0) if s else 0.0
        dif = o["empenhado"] - visto
        if dif > 5e6:
            saida.append({"orgao": o["orgao"], "ug": s or "", "empenhado": mi(o["empenhado"]), "notas": mi(visto),
                          "sem_nota": mi(dif), "poder": s in ("ALE", "TJ", "MP", "TCE", "DPE")})
    saida.sort(key=lambda x: -x["sem_nota"])
    tot_org = sum(o["empenhado"] for o in s1["orgaos"])
    tot_not = sum(notas.values())
    return {"empenhado_orgaos": mi(tot_org), "empenhado_notas": mi(tot_not), "diferenca": mi(tot_org - tot_not),
            "dados_de": s1["meta"]["atualizacao_despesa"], "orgaos": saida[:16]}


# ------------------------------------------------------------------ 7. passagens, agências de viagem, táxi aéreo e hotéis
VIAGEM = ("VIAGE", "TURISMO", "PASSAGE", "AEREO", "AÉREO", "HOTEL", "LINHAS AEREAS", "AVIA")


def viagens(ano):
    notas = ler(f"s3_empenhos_{ano}.json")["dados"]
    grupos = defaultdict(lambda: {"valor": 0.0, "pago": 0.0, "qtd": 0, "notas": []})
    for n in notas:
        cr = n["credor"].upper()
        if any(k in cr for k in VIAGEM) and "AGENCIA EST" not in cr and "AGENCIA DE REG" not in cr and "PROPAGANDA" not in cr:
            g = grupos[(n["unidadeGestora"], n["credor"].strip())]
            e, p = reais(n["valorEmpenhado"]), reais(n["valorPago"])
            g["valor"] += e
            g["pago"] += p
            g["qtd"] += 1
            g["notas"].append([n["numeroEmpenho"], n["dataDocumentoFormatada"], mi(e), mi(p), n["linkDetalhes"]])
    lista = []
    for (ug, cr), g in sorted(grupos.items(), key=lambda a: -a[1]["valor"]):
        g["notas"].sort(key=lambda x: -x[2])
        lista.append({"ug": ug, "credor": cr, "valor": mi(g["valor"]), "pago": mi(g["pago"]), "qtd": g["qtd"], "notas": g["notas"][:8]})
    return {"ano": ano, "total": round(sum(x["valor"] for x in lista), 2), "grupos": lista[:40]}


# ------------------------------------------------------------------ 8. tabelas de origem, para ver dentro da página (paginadas)
CURTO = {"sem-entrega-2025": "2025", "sem-entrega-2026": "2026", "diarias-msc": "Contabilidade (Tesouro)", "diarias-portal": "Portal de diárias"}


def tabela(id_, titulo, fonte, consulta, url, colunas, linhas, nota=""):
    return {"id": id_, "titulo": titulo, "curto": CURTO.get(id_, titulo), "fonte": fonte, "consulta": consulta, "url": url, "nota": nota,
            "colunas": colunas, "linhas": linhas}


def tabelas(coletado):
    t = []
    lista = {}
    for ano in (2025, 2026):
        lista[ano] = {n["linkDetalhes"]: n for n in ler(f"s3_empenhos_{ano}.json")["dados"]}
    for ano in (2025, 2026):
        det = ler(f"s3_detalhes_{ano}.json")["dados"]
        linhas = []
        for link, d in det.items():
            e = reais(d.get("Valor empenhado final"))
            li = reais(d.get("Valor liquidado no exercício da emissão do empenho")) + reais(d.get("Valor liquidado em anos posteriores ao da emissão do empenho"))
            sem = max(e - li, 0)
            if sem < 1e4:
                continue
            n = lista[ano].get(link, {})
            linhas.append([n.get("unidadeGestora", ""), n.get("numeroEmpenho", ""), d.get("Data de emissão", ""), limpa(d.get("Razão social do credor")),
                           limpa(d.get("CPF/CNPJ do credor")), d.get("Tipo de empenho", ""), round(e, 2), round(li, 2), round(sem, 2),
                           limpa(d.get("Fonte do recurso")), limpa(d.get("Ação de governo")), link])
        linhas.sort(key=lambda r: -r[8])
        t.append(tabela(f"sem-entrega-{ano}", f"Notas de empenho de {ano} sem entrega", "Portal da Transparência de Rondônia (CGE-RO)",
                        f"Despesas por Empenho, exercício {ano}, detalhe de cada nota a partir de R$ 200 mil; aqui as que têm pelo menos R$ 10 mil sem entrega",
                        PORTAL_EMPENHO,
                        [["Órgão", "t"], ["Nota", "t"], ["Emissão", "d"], ["Credor", "t"], ["CNPJ/CPF", "t"], ["Tipo", "t"], ["Empenhado", "r"],
                         ["Entregue", "r"], ["Sem entrega", "r"], ["Fonte do recurso", "t"], ["Ação de governo", "t"], ["Link", "l"]], linhas))
    # restos a pagar: linhas do RREO do Executivo
    rreo = ler("s3_rreo_anexo7.json")["dados"]
    def legivel(cod):
        if cod == "SaldoTotal":
            return "Total", "Saldo total"
        tipo = "Não processados (sem entrega)" if cod.startswith("RestosAPagarNaoProcessados") else "Processados (entregues)"
        fim = cod.split("Liquidados", 1)[-1] if "ENaoProcessadosLiquidados" in cod else cod.replace("RestosAPagarNaoProcessados", "")
        situ = {"InscritosEmExerciciosAnteriores": "Inscritos em anos anteriores", "InscritosEmExercicioAnterior": "Inscritos no ano anterior",
                "Pagos": "Pagos", "Cancelados": "Cancelados", "APagar": "A pagar", "Liquidados": "Liquidados", "": "Liquidados"}.get(fim, fim)
        return tipo, situ
    linhas = [[int(ano), *legivel(x["cod_conta"]), x["coluna"], round(x["valor"], 2), x["cod_conta"], link_rreo(ano)] for ano in sorted(rreo) for x in rreo[ano]
              if x["conta"] == "PODER EXECUTIVO" and not x["cod_conta"].endswith("Intra")]
    t.append(tabela("rreo", "Restos a pagar do Poder Executivo, 2019 a 2025", "Tesouro Nacional · Siconfi",
                    "RREO Anexo 7, 6º bimestre, Rondônia (id_ente 11), linhas do Poder Executivo", link_rreo(2025),
                    [["Ano", "n"], ["Tipo", "t"], ["Situação", "t"], ["Coluna do anexo", "t"], ["Valor", "r"], ["Código da conta", "h"], ["Fonte", "u"]], linhas,
                    "Não processados = empenhados e não entregues. Os R$ 1,21 bi da tela são a coluna Cancelados (j), dos não processados: busque “Cancelados (j)”. Saldos e inscritos são a posição no fim de cada ano e não se somam entre anos."))
    # parados 2026: todas as notas
    linhas = []
    for n in ler("s3_empenhos_2026.json")["dados"]:
        e, pg = reais(n["valorEmpenhado"]), reais(n["valorPago"])
        if e >= 1e6 and pg <= 0.05 * e:
            linhas.append([n["unidadeGestora"], n["numeroEmpenho"], n["dataDocumentoFormatada"], n["credor"], round(e, 2), round(pg, 2), n["linkDetalhes"]])
    linhas.sort(key=lambda r: -r[4])
    t.append(tabela("parados-2026", "Empenhos de 2026 de R$ 1 mi ou mais com até 5% pago", "Portal da Transparência de Rondônia (CGE-RO)",
                    "Despesas por Empenho, exercício 2026", PORTAL_EMPENHO,
                    [["Órgão", "t"], ["Nota", "t"], ["Emissão", "d"], ["Credor", "t"], ["Empenhado", "r"], ["Pago", "r"], ["Link", "l"]], linhas))
    # diárias: contabilidade (MSC) e portal por órgão e mês
    m = ler("s3_msc_diarias_2026.json")["dados"]
    nome_conta = {"622130100": "empenhado a liquidar", "622130200": "em liquidação", "622130300": "liquidado a pagar", "622130400": "pago"}
    linhas = [[int(mes), x["natureza_despesa"][:6], "civil" if x["natureza_despesa"].startswith("339014") else "militar", x["conta_contabil"],
               nome_conta[x["conta_contabil"]], x["fonte_recursos"], round(x["valor"] * (1 if x["natureza_conta"] == "C" else -1), 2), link_msc(2026, int(mes))]
              for mes in sorted(m, key=int) for x in m[mes] if x["poder_orgao"].startswith("101") and x["conta_contabil"] in nome_conta]
    t.append(tabela("diarias-msc", "Diárias na contabilidade do Executivo, 2026 (saldo acumulado no fim de cada mês)", "Tesouro Nacional · Siconfi",
                    "Matriz de Saldos Contábeis (MSCC), classe 6, naturezas 3.3.90.14 e 3.3.90.15, Poder Executivo", link_msc(2026, 8),
                    [["Mês", "n"], ["Natureza", "t"], ["Tipo", "t"], ["Conta", "t"], ["Situação", "t"], ["Fonte de recurso", "t"], ["Valor acumulado", "r"], ["Fonte", "u"]], linhas,
                    "O valor de cada mês é acumulado no ano; o pago no mês é a diferença para o mês anterior."))
    cods = codigos_portal()
    linhas = []
    for ano in (2025, 2026):
        vistos, soma, qtd = set(), defaultdict(float), Counter()
        for r in ler(f"s3_diarias_{ano}.json")["dados"]:
            chave_ = (r["solicitacao"], r["nome"], r["periodo"], r["valorTotalDiaria"], r["autorizacao"])
            if chave_ in vistos or r["periodo"][6:10] != str(ano):
                continue
            vistos.add(chave_)
            k = (r["orgao"].strip(), int(r["periodo"][3:5]))
            soma[k] += reais(r["valorTotalDiaria"])
            qtd[k] += 1
        for (org, mes), v in soma.items():
            c = codigo_orgao(org, cods)
            linhas.append([ano, mes, org, qtd[(org, mes)], round(v, 2), link_diarias(ano, mes, mes, c) if c else "sem filtro no portal"])
    linhas.sort(key=lambda r: (-r[0], r[1], -r[4]))
    t.append(tabela("diarias-portal", "Diárias no portal, por órgão e mês (sem linhas repetidas)", "Portal da Transparência de Rondônia (CGE-RO)",
                    "Diárias, exercícios 2025 e 2026, mês de início da viagem", PORTAL_DIARIAS,
                    [["Ano", "n"], ["Mês", "n"], ["Órgão", "t"], ["Diárias", "n"], ["Valor", "r"], ["Abrir no portal", "u"]], linhas))
    # sem nota: todos os órgãos
    sn = sem_nota_2026_todos()
    t.append(tabela("sem-nota", "Empenhado por órgão × soma das notas de empenho, 2026", "Portal da Transparência de Rondônia (CGE-RO)",
                    "Despesa por órgão (posição do painel) × lista de notas de empenho do exercício 2026", PORTAL_EMPENHO,
                    [["Órgão", "t"], ["Sigla", "t"], ["Empenhado por órgão", "r"], ["Soma das notas", "r"], ["Sem nota visível", "r"], ["Fonte", "u"]], sn))
    # viagens: todas as notas
    linhas = []
    for ano in (2025, 2026):
        for n in ler(f"s3_empenhos_{ano}.json")["dados"]:
            cr = n["credor"].upper()
            if any(k in cr for k in VIAGEM) and "AGENCIA EST" not in cr and "AGENCIA DE REG" not in cr and "PROPAGANDA" not in cr:
                linhas.append([ano, n["unidadeGestora"], n["credor"].strip(), n["numeroEmpenho"], n["dataDocumentoFormatada"],
                               reais(n["valorEmpenhado"]), reais(n["valorPago"]), n["linkDetalhes"]])
    linhas.sort(key=lambda r: (-r[0], -r[5]))
    t.append(tabela("viagens", "Notas de empenho com agências de viagem, aéreas, táxi aéreo e hotéis", "Portal da Transparência de Rondônia (CGE-RO)",
                    "Despesas por Empenho, 2025 e 2026, credores com VIAGEM, TURISMO, PASSAGEM, AÉREO, HOTEL ou AVIAÇÃO no nome", PORTAL_EMPENHO,
                    [["Ano", "n"], ["Órgão", "t"], ["Credor", "t"], ["Nota", "t"], ["Emissão", "d"], ["Empenhado", "r"], ["Pago", "r"], ["Link", "l"]], linhas))
    return {x["id"]: dict(x, coletado_em=coletado) for x in t}


def sem_nota_2026_todos():
    s1 = ler("s1_dados.json")
    sig = {chave(u[2]): u[1].upper() for u in ler("s2_cargos.json")["ugs"]}
    for c, t_ in codigos_portal().items():
        sig.setdefault(chave(t_.split(" - ", 1)[-1]), c.upper())
    notas = defaultdict(float)
    for n in ler("s3_empenhos_2026.json")["dados"]:
        notas[n["unidadeGestora"].upper()] += reais(n["valorEmpenhado"])
    linhas = []
    for o in s1["orgaos"]:
        s = PODERES.get(chave(o["orgao"])) or sig.get(chave(o["orgao"])) or ""
        visto = notas.get(s, 0.0) if s else 0.0
        linhas.append([o["orgao"], s, round(o["empenhado"], 2), round(visto, 2), round(o["empenhado"] - visto, 2), PORTAL_EMPENHO])
    return sorted(linhas, key=lambda r: -r[4])


# o governador no portal: consulta feita em 08/10/2026 (nome no filtro de diárias e de credor de empenho)
GOVERNADOR = {
    "nome": "Marcos José Rocha dos Santos",
    "diarias": {"2023": 0, "2024": 0, "2025": 0, "2026": 0},
    "empenhos": [
        {"ug": "FIDER", "data": "03/11/2025", "empenhado": 23895.76, "pago": 0.0},
        {"ug": "SEPOG", "data": "26/11/2025", "empenhado": 6844.80, "pago": 0.0},
        {"ug": "FIDER", "data": "11/08/2026", "empenhado": 5418.80, "pago": 5418.80},
    ],
}


# ------------------------------------------------------------------ nome por extenso de cada sigla de unidade gestora
EXTRA = {
    "ALE": "Assembleia Legislativa", "CBOMB": "Corpo de Bombeiros Militar", "DPE": "Defensoria Pública",
    "MP": "Ministério Público", "TCE": "Tribunal de Contas do Estado", "TJ": "Tribunal de Justiça",
    "RS/SEFIN": "Recursos sob supervisão da SEFIN (encargos gerais do Estado)",
    "FERHRO": "Fundo Estadual de Recursos Hídricos",
}
MINUSCULAS = {"de", "da", "do", "das", "dos", "e", "a", "à", "o", "em", "ao", "sob", "para"}


ACENTOS = {
    "saude": "saúde", "educacao": "educação", "seguranca": "segurança", "publica": "pública", "publico": "público",
    "publicos": "públicos", "aguas": "águas", "rondonia": "rondônia", "erradicacao": "erradicação", "habitacao": "habitação",
    "agencia": "agência", "servicos": "serviços", "judiciarios": "judiciários", "aperfeicoamento": "aperfeiçoamento",
    "assistencia": "assistência", "previdencia": "previdência", "gestao": "gestão", "administracao": "administração",
    "justica": "justiça", "financas": "finanças", "ciencia": "ciência", "inovacao": "inovação", "economico": "econômico",
    "tecnico": "técnico", "tecnica": "técnica", "transito": "trânsito", "juridico": "jurídico", "fiscalizacao": "fiscalização",
    "prevencao": "prevenção", "repressao": "repressão", "regulacao": "regulação", "extensao": "extensão", "agropecuaria": "agropecuária",
    "patrimonio": "patrimônio", "comunicacao": "comunicação", "hidricos": "hídricos", "militar": "militar", "cidadania": "cidadania",
    "governanca": "governança", "logistica": "logística", "esportes": "esportes", "proteção": "proteção", "protecao": "proteção",
    "defensoria": "defensoria", "imprensa": "imprensa", "politicas": "políticas", "estatistica": "estatística", "previdenciario": "previdenciário",
    "capitalizacao": "capitalização", "infraestrutura": "infraestrutura", "agricola": "agrícola", "credito": "crédito",
}


def titulo(s):
    return " ".join(p if (p in MINUSCULAS and i) else p[:1].upper() + p[1:]
                    for i, p in enumerate(ACENTOS.get(w.rstrip(","), w.rstrip(",")) + ("," if w.endswith(",") else "")
                                          for w in s.lower().split()))


PORTAL_SINONIMO = {"FUMRESPOM": "FUNRESPOM"}


def nomes(siglas):
    ugs = {u[1].upper(): u for u in ler("s2_cargos.json")["ugs"]}
    portal = {k.upper(): t.split(" - ", 1)[-1] for k, t in codigos_portal().items()}
    saida = {}
    for s in siglas:
        u = ugs.get(s.upper())
        if s in EXTRA:
            saida[s] = EXTRA[s]
        else:
            nome_portal = portal.get(PORTAL_SINONIMO.get(s.upper(), s.upper()))
            if not (nome_portal or u):
                continue
            vinc = u[5] if u and u[5] and u[5] not in ("A conferir", u[1]) else ""
            saida[s] = titulo(nome_portal or u[2]) + (f" · vinculado: {vinc}" if vinc else "")
    return saida


# ------------------------------------------------------------------ monta
def fontes_css():
    b64 = base64.b64encode((RAIZ / "vendor" / "fontes" / "inter-var.woff2").read_bytes()).decode()
    return f"@font-face{{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:block;src:url(data:font/woff2;base64,{b64}) format('woff2')}}"


def main():
    itens = msc_itens()
    resumo = {
        "coletado_em": ler("s3_empenhos_2026.json")["meta"]["coletado_em"],
        "restos": restos_a_pagar(),
        "diarias": diarias(itens),
        "fontes": fontes(itens),
        "emendas": emendas(),
        "parados_2026": parados_2026(),
        "secretarias_2025": por_secretaria(2025),
        "secretarias_2026": por_secretaria(2026),
        "portal_pago": [portal_pago(2025), portal_pago(2026)],
        "governador": GOVERNADOR,
        "sem_nota_2026": sem_nota_2026(),
        "viagens": [viagens(2025), viagens(2026)],
        "tabelas": tabelas(ler("s3_empenhos_2026.json")["meta"]["coletado_em"]),
        "links": {"rreo": SICONFI_RREO, "rreo_api": link_rreo(2025), "msc_api": link_msc(2026, 8), "empenho": PORTAL_EMPENHO, "diarias": PORTAL_DIARIAS, "detalhe": PORTAL_DETALHE,
                  "msc": "https://apidatalake.tesouro.gov.br/docs/siconfi/"},
    }
    from build_a_pagar import a_pagar
    resumo["a_pagar"], tab_a_pagar = a_pagar()
    resumo["tabelas"].update(tab_a_pagar)
    siglas = {u["ug"] for k in ("secretarias_2025", "secretarias_2026") if resumo[k] for u in resumo[k]["ugs"]}
    resumo["nomes"] = nomes(siglas | {u["ug"] for u in resumo["parados_2026"]["ugs"]} | {u["ug"] for u in resumo["a_pagar"]["portal"]["ugs"]})
    (FONTE / "s3_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    renderiza(resumo)


def renderiza(resumo):
    """Grava esbocos/ e site/ a partir de src/ com os dados do resumo."""
    payload = json.dumps(resumo, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    print("s3_resumo.json", round(len(payload) / 1024), "KB")

    css = fontes_css()
    for nome in ("nao-aparece.html", "painel.html"):
        h = (AQUI / "src" / nome).read_text(encoding="utf-8")
        h = h.replace("/*__DADOS_S3__*/null", payload).replace("/*__FONTES__*/", css)
        (RAIZ / "esbocos" / nome).write_text(h, encoding="utf-8")
        site = h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1)
        site = site.replace('src="rondonia.html"', 'src="numeros.html"').replace('href="rondonia.html"', 'href="numeros.html"')
        (RAIZ / "site" / nome).write_text(site, encoding="utf-8")
        if nome == "painel.html":  # a raiz do site abre o painel com as três abas
            (RAIZ / "site" / "index.html").write_text(site, encoding="utf-8")
        print("esbocos/ e site/" + nome, round(len(h) / 1024), "KB")


if __name__ == "__main__":
    main()
