"""Custo da máquina do Estado: folha, servidores por órgão, veículos, imóveis alugados e secretarias regionais.

Uso: python3 maquina/build_maquina.py      (só a biblioteca padrão; rode antes extrai_folha.py, extrai_regionais.py
                                             e coleta_pagamentos.py, que gravam em dados-fonte/)
Grava:
  maquina/dados.json                      tudo o que a tela mostra (só totais; nenhuma pessoa identificada)
  esbocos/maquina.html                    a aba no padrão do Observatório, para abrir local ou publicar
  maquina/sipre/maquina.js                window.M para o SIPRE (lib/observatorio/maquina.js)
  maquina/sipre/custo_da_maquina.html.erb a tela do Observatório no SIPRE (app/views/observatorio/)
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
SIPRE_COMUM = RAIZ.parent.parent / "sipre" / "app" / "assets" / "javascripts" / "observatorio" / "comum.js"
sys.path.insert(0, str(RAIZ / "tecnologia"))
from classificar import NOME_CURTO  # noqa: E402

# Subelemento da despesa (natureza com 8 dígitos) de cada tema, como no SIGEF de RO
SUBELEMENTOS = {
    "combustivel": {"33903001": "Combustíveis e lubrificantes automotivos", "33903955": "Gerenciamento de abastecimento"},
    "manutencao": {"33903919": "Manutenção e conservação de veículos", "33903039": "Material para manutenção de veículos"},
    "locacao": {"33903913": "Locação de veículos", "33903303": "Locação de meios de transporte (elemento 33)"},
    "transporte": {"33903993": "Transporte escolar (serviço contratado pela SEDUC)"},
    "imovel": {"33903910": "Locação de imóveis (pessoa jurídica)", "33903615": "Locação de imóveis (pessoa física)",
               "33909244": "Aluguel de exercício anterior e indenização"},
}
# "Outros serviços": o subelemento não diz o que é; entra só o pagamento cuja nota tem histórico de frota ou de aluguel
GENERICOS = {"33903999": "Outros serviços de terceiros (pelo histórico da nota)", "33903699": "Outros serviços de pessoa física (pelo histórico da nota)"}
# Fora: combustível de aviação (33903002) e aeronaves pagas como veículo (táxi aéreo, helicóptero)
TEMA_DE = {cod: t for t, cods in SUBELEMENTOS.items() for cod in cods}
NOME_TEMA = {"combustivel": "Combustível", "manutencao": "Manutenção de veículos", "locacao": "Locação de veículos", "transporte": "Transporte escolar",
             "imovel": "Aluguel de imóveis"}
VEICULOS = ("combustivel", "manutencao", "locacao", "transporte")
OUTROS_PODERES = {"ALE", "TJ", "FUJU", "MP", "FUNDIMPER", "FRBL", "TCE", "FDI/TC", "DPE", "FUNDEP", "FUNDEP/DPE"}
RX_AVIACAO = re.compile(r"TAXI AEREO|AEROTAXI|AERO TAXI|HELICOPTER|HELISUL|AVIACAO|AERONAVE|AEROCLUBE|\bAIR\b")
RX_OUTROS = re.compile(r"TRIBUNAL|ASSEMBLEIA|MINISTERIO PUBLICO|DEFENSORIA|PODER JUDICIARIO|JUSTICA DO ESTADO|FUNDO DE INFORMATIZACAO.*JUDIC")


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").upper()


def nome15(s):
    return re.sub(r"[^A-Z0-9]", "", sem_acento(s))[:15]


def ler(nome):
    return json.loads((FONTE / nome).read_text(encoding="utf-8"))


def mes_de(d):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d or "")
    return (int(m[3]), int(m[2]), int(m[1])) if m else (0, 0, 0)


def siglas_por_codigo(pagamentos):
    """Código da UG (pagamento) -> sigla do portal (notas), casando número da nota e credor. A sigla é a mesma das notas
    de empenho, para o órgão aparecer igual em todas as telas."""
    nota = {}
    for ano in (2025, 2026):
        for n in ler(f"s3_empenhos_{ano}.json")["dados"]:
            nota[(n["numeroEmpenho"], nome15(n["credor"]))] = n["unidadeGestora"]
    votos, nomes = defaultdict(Counter), {}
    for p in pagamentos:
        s = nota.get((p["ne"], nome15(p["credor"])))
        if s:
            votos[p["codUnidadeGestora"]][s] += 1
        nomes.setdefault(p["codUnidadeGestora"], p["unidadeGestora"])
    return {c: v.most_common(1)[0][0].upper() for c, v in votos.items()}, nomes


def pagamentos(ano):
    d = ler(f"s8_pagamentos_{ano}.json")
    return d["dados"], d["meta"]


TEMA_HIST = {}


def carregar_historicos():
    """Tema de cada nota de 2025 e 2026 pelo histórico (regra de custeio.py), para os subelementos genéricos."""
    sys.path.insert(0, str(AQUI))
    from custeio import norm, tema as tema_hist  # noqa: E402
    for ano in (2025, 2026):
        lista = ler(f"s3_empenhos_{ano}.json")["dados"]
        det = ler(f"s5_detalhes_por_chave_{ano}.json")["detalhes"]
        for n in lista:
            d = det.get(f"{ano}|{n['unidadeGestora']}|{n['numeroEmpenho']}")
            t = tema_hist(norm(d.get("Histórico"))) if d else None
            if t:
                TEMA_HIST[(n["numeroEmpenho"], nome15(n["credor"]))] = t


def custeio(p26, p25, sigla, nomes, ate):
    """Pago por tema, 2026 mês a mês com projeção, por órgão e por credor."""
    def tema(p):
        cod = str(p["especificacaoDespesa"])
        return TEMA_DE.get(cod) or (TEMA_HIST.get((p["ne"], nome15(p["credor"]))) if cod in GENERICOS else None)

    def sg(p):
        return sigla.get(p["codUnidadeGestora"]) or "UG " + str(p["codUnidadeGestora"])

    def executivo(p):
        return sg(p) not in OUTROS_PODERES and not RX_OUTROS.search(sem_acento(p["unidadeGestora"]))

    def pf(p):
        return not re.search(r"\d{2}\.?\d{3}\.?\d{3}/\d{4}", p["docCredor"] or "")

    def aviao(p):  # aluguel e manutenção de aeronave entram no mesmo subelemento de veículo; ficam fora
        return tema(p) != "imovel" and RX_AVIACAO.search(sem_acento(p["credor"]))

    a26 = [p for p in p26 if tema(p) and executivo(p) and not aviao(p)]
    a25 = [p for p in p25 if tema(p) and executivo(p) and not aviao(p)]
    ult_mes = ate.month
    out, nome_org = {}, {}
    for p in a26:
        nome_org.setdefault(sg(p), NOME_CURTO.get(sg(p)) or p["unidadeGestora"].title())
    for t in SUBELEMENTOS:
        mensal = [0.0] * 12
        for p in a26:
            if tema(p) == t:
                mensal[mes_de(p["dataDocumento"])[1] - 1] += p["valor"]
        pago = sum(mensal)
        media = sum(mensal[ult_mes - 4:ult_mes - 1]) / 3          # agosto a outubro (os três meses fechados antes do atual)
        proj = [0.0] * 12
        proj[ult_mes - 1] = max(media - mensal[ult_mes - 1], 0)  # o que falta do mês corrente
        for m in range(ult_mes, 12):
            proj[m] = media
        anos = {"2025": round(sum(p["valor"] for p in a25 if tema(p) == t), 2)}
        por_sub = Counter()
        for p in a26:
            if tema(p) == t:
                por_sub[str(p["especificacaoDespesa"])] += p["valor"]
        nomes_sub = {**SUBELEMENTOS[t], **GENERICOS}
        out[t] = {"nome": NOME_TEMA[t], "pago_2026": round(pago, 2), "projecao_2026": round(sum(proj), 2),
                  "ano_2026": round(pago + sum(proj), 2), "media_ago_out": round(media, 2),
                  "mensal_2026": [round(mensal[i] + proj[i], 2) for i in range(12)], "pago_mensal_2026": [round(x, 2) for x in mensal],
                  "anos": anos, "subelementos": [{"cod": c, "nome": nomes_sub[c], "valor": round(v, 2)} for c, v in por_sub.most_common()]}

    def por_orgao(temas):
        o = defaultdict(lambda: defaultdict(float))
        loc = defaultdict(set)
        for p in a26:
            if tema(p) in temas:
                o[sg(p)][tema(p)] += p["valor"]
                o[sg(p)]["total"] += p["valor"]
                loc[sg(p)].add(p["docCredor"] or p["credor"])
        return sorted(({"sigla": s, "nome": nome_org.get(s, s), **{k: round(v, 2) for k, v in d.items()}, "locadores": len(loc[s])}
                       for s, d in o.items()), key=lambda x: -x["total"])

    def por_credor(lista, juntar_pf):
        c = defaultdict(lambda: {"valor": 0.0, "orgaos": set(), "temas": set(), "docs": set()})
        for p in lista:
            k = "__pf__" if (juntar_pf and pf(p)) else nome15(p["credor"])
            x = c[k]
            x["credor"] = p["credor"]
            x["valor"] += p["valor"]
            x["orgaos"].add(sg(p))
            x["temas"].add(NOME_TEMA[tema(p)])
            x["docs"].add(p["docCredor"])
            x["pf"] = k == "__pf__"
        return sorted(({"credor": "" if x["pf"] else x["credor"], "pf": x["pf"], "valor": round(x["valor"], 2),
                        "orgaos": sorted(x["orgaos"]), "temas": sorted(x["temas"]), "n": len(x["docs"])} for x in c.values()),
                      key=lambda x: -x["valor"])

    veic = [p for p in a26 if tema(p) != "imovel"]
    imov = [p for p in a26 if tema(p) == "imovel"]
    veiculos = {"orgaos": por_orgao(set(VEICULOS)), "credores": por_credor(veic, True)[:60]}
    for c in veiculos["credores"]:
        if len(c["temas"]) == 1:
            c.pop("temas")
    pares = {(sg(p), p["docCredor"] or p["credor"]) for p in imov}
    pf_doc = {p["docCredor"] for p in imov if pf(p)}
    imoveis = {"orgaos": por_orgao({"imovel"}), "credores": [{k: v for k, v in c.items() if k != "temas"} for c in por_credor(imov, True)[:40]],
               "credores_por_orgao": {s: [{k: v for k, v in c.items() if k != "temas"} for c in por_credor([p for p in imov if sg(p) == s], True)[:15]]
                                      for s in {sg(p) for p in imov}},
               "locadores": len(pares), "pf": len({x for x in pares if x[1] in pf_doc}), "pj": len({x for x in pares if x[1] not in pf_doc}),
               "pf_valor": round(sum(p["valor"] for p in imov if pf(p)), 2), "pj_valor": round(sum(p["valor"] for p in imov if not pf(p)), 2),
               "orgaos_n": len({x[0] for x in pares}),
               "locadores_2025": len({(sg(p), p["docCredor"] or p["credor"]) for p in a25 if tema(p) == "imovel"})}
    imoveis["orgaos_total"] = imoveis.pop("orgaos_n")
    fora = {t: round(sum(p["valor"] for p in p26 if tema(p) == t and not executivo(p)), 2) for t in SUBELEMENTOS}
    # linha a linha (para o painel filtrar e para a tabela de origem); pessoa física sem nome nem CPF
    nomes_sub = {c: n for t_ in SUBELEMENTOS for c, n in {**SUBELEMENTOS[t_], **GENERICOS}.items()}
    linhas = sorted(([p["dataDocumento"], sg(p), "Pessoa física" if pf(p) else p["credor"], "" if pf(p) else (p["docCredor"] or ""),
                      NOME_TEMA[tema(p)], f"{p['especificacaoDespesa']} · {nomes_sub.get(str(p['especificacaoDespesa']), '')}",
                      p["ne"], p["ob"], round(p["valor"], 2)] for p in a26), key=lambda r: (r[0][6:] + r[0][3:5] + r[0][:2]), reverse=True)
    return out, veiculos, imoveis, fora, linhas


def comparativo(p25, p26, sigla, ate):
    """2025 × 2026 no MESMO período (1º/01 a ate) por tema e por órgão, e 2025 inteiro × 2026 com projeção."""
    from datetime import date as _d

    def tema(p):
        cod = str(p["especificacaoDespesa"])
        return TEMA_DE.get(cod) or (TEMA_HIST.get((p["ne"], nome15(p["credor"]))) if cod in GENERICOS else None)

    def ok(p):
        sg_ = sigla.get(p["codUnidadeGestora"]) or ""
        return (tema(p) and sg_ not in OUTROS_PODERES and not RX_OUTROS.search(sem_acento(p["unidadeGestora"]))
                and not (tema(p) != "imovel" and RX_AVIACAO.search(sem_acento(p["credor"]))))

    def ate_dia(p, ano):
        a, m, dd = mes_de(p["dataDocumento"])
        return _d(a, m, dd) <= _d(ano, ate.month, ate.day)

    org = defaultdict(lambda: defaultdict(float))
    tot = defaultdict(lambda: defaultdict(float))
    acum = {t: {"2025": [0.0] * 12, "2026": [0.0] * 12} for t in SUBELEMENTOS}
    for ano, ps in (("2025", p25), ("2026", p26)):
        for p in ps:
            if not ok(p):
                continue
            t, sg_ = tema(p), sigla.get(p["codUnidadeGestora"])
            if ate_dia(p, int(ano)):  # mesmo corte nos dois anos, inclusive no acumulado do mês corrente
                acum[t][ano][mes_de(p["dataDocumento"])[1] - 1] += p["valor"]
                org[sg_][f"{t}_{ano}"] += p["valor"]
                tot[t][ano] += p["valor"]
    for t in acum:
        for ano in acum[t]:
            a = 0
            for i in range(12):
                a += acum[t][ano][i]
                acum[t][ano][i] = round(a, 2)
    orgaos = []
    for sg_, v in org.items():
        x = {"sigla": sg_, **{k: round(val, 2) for k, val in v.items()}}
        x["total_2025"] = round(sum(val for k, val in v.items() if k.endswith("2025")), 2)
        x["total_2026"] = round(sum(val for k, val in v.items() if k.endswith("2026")), 2)
        orgaos.append(x)
    orgaos.sort(key=lambda x: -max(x["total_2025"], x["total_2026"]))
    return {"ate": ate.strftime("%d/%m"), "temas": {t: {k: round(val, 2) for k, val in v.items()} for t, v in tot.items()},
            "acumulado": acum, "orgaos": orgaos}


def contratos_vencendo(hoje):
    """Contratos vigentes de aluguel de imóvel e de locação de veículo do Executivo, com a vigência publicada no portal."""
    sys.path.insert(0, str(RAIZ / "economia"))
    sys.path.insert(0, str(AQUI))
    from base import contratos  # noqa: E402
    from custeio import IMOVEL, LOCACAO_VEIC, NAO_IMOVEL, norm  # noqa: E402
    out, cartao = [], []
    for c in contratos():
        if c["sigla"] in OUTROS_PODERES or c["rescisao"]:
            continue
        o = norm(c["objeto"])
        if re.search(r"PRIME CONSULT|UZZIPAY|LINK CARD|NEO CONSULT", sem_acento(c["contratado"])) and c["valor"] > 1e6 and c["assinatura"] >= "2025":
            cartao.append(c)
            continue
        t = ("imovel" if IMOVEL.search(o) and not NAO_IMOVEL.search(o) else
             "locacao" if LOCACAO_VEIC.search(o) and not re.search(r"AERONAVE|HELICOPTER|EMBARCA", o) else None)
        if t and c["vigencia"] and c["vigencia"] >= hoje:
            pf = not re.fullmatch(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", (c.get("cnpj") or "").strip())  # CPF (mascarado no portal) ou sem documento
            out.append({"tipo": t, "sigla": c["sigla"], "contratado": "Pessoa física (locador)" if pf else c["contratado"], "valor": c["valor"], "vigencia": c["vigencia"],
                        "numero": c["numero"], "processo": c["processo"],
                        "objeto": (re.sub(re.escape(c["contratado"].strip()), "o locador", c["objeto"], flags=re.I) if pf else c["objeto"])[:240], "link": c["link"]})
    out.sort(key=lambda c: c["vigencia"])
    cartao = [{"sigla": c["sigla"], "contratado": c["contratado"], "valor": c["valor"], "assinatura": c["assinatura"], "vigencia": c["vigencia"],
               "numero": c["numero"], "processo": c["processo"], "objeto": c["objeto"][:240], "link": c["link"]} for c in sorted(cartao, key=lambda c: -c["valor"])]
    return out, cartao


def rgf():
    itens = ler("rgf_executivo_2026_q2_siconfi.json")["items"]
    v = {}
    for i in itens:
        if str(i.get("coluna", "")).startswith("TOTAL (ÚLTIMOS 12 MESES)"):
            v.setdefault(i["conta"].strip(), i["valor"])
    return {"bruta": v["DESPESA BRUTA COM PESSOAL (I)"], "ativo": v["Pessoal Ativo"],
            "vencimentos": v["Vencimentos, Vantagens e Outras Despesas Variáveis"], "patronais": v["Obrigações Patronais"],
            "inativos": v["Pessoal Inativo e Pensionistas"], "aposentadorias": v["Aposentadorias, Reserva e Reformas"], "pensoes": v["Pensões"],
            "terceirizacao": next(val for k, val in v.items() if k.startswith("Outras Despesas de Pessoal decorrentes")),
            "liquida": v["DESPESA LÍQUIDA COM PESSOAL (III) = (I - II)"], "periodo": "setembro de 2025 a agosto de 2026", "ate": "agosto de 2026"}


def main():
    folha = ler("s8_folha_2026_10.json")
    regionais = ler("s8_regionais_2026.json")
    # população de cada região (IBGE, Censo 2022) para o custo por habitante do organograma
    series = ler("ibge/ro-populacao-censo2022.json")[0]["resultados"][0]["series"]
    norm_m = lambda n: re.sub(r"[^A-Z]", "", re.sub(r"D'? ?OESTE|DO OESTE", "DOESTE", sem_acento(n)))  # noqa: E731
    pop = {norm_m(x["localidade"]["nome"].replace(" - RO", "")): int(x["serie"]["2022"]) for x in series}
    for u in regionais["unidades"]:
        ms = [m for m in u.get("municipios") or [] if norm_m(m) in pop]
        if len(ms) > 1 or u["codigo"] != "COOREG":
            u["populacao"] = sum(pop[norm_m(m)] for m in ms)
            u["municipios_sem_pop"] = [m for m in u.get("municipios") or [] if norm_m(m) not in pop]
            u["custo_hab"] = round(u["total_2026"] / u["populacao"], 2) if u["populacao"] else None
    p26, m26 = pagamentos(2026)
    p25, _ = pagamentos(2025)
    sigla, nomes = siglas_por_codigo(p26 + p25)
    carregar_historicos()
    ate = max(date(*mes_de(p["dataDocumento"])) for p in p26)
    C, veiculos, imoveis, fora, linhas_pag = custeio(p26, p25, sigla, nomes, ate)
    for u in folha["unidades"]:
        u["nome"] = NOME_CURTO.get(u["unidade"], "")
    G = rgf()
    G["historico"] = ler("s8_rgf_pessoal.json")["dados"]
    G["limites"] = {"alerta": 44.1, "prudencial": 46.55, "maximo": 49}
    comp = comparativo(p25, p26, sigla, ate)
    vencem, cartao = contratos_vencendo(ate.isoformat())
    veic_ano = sum(C[t]["ano_2026"] for t in VEICULOS)
    data_pag = ate.strftime("%d/%m/%Y")
    M = {
        "hoje": date.today().isoformat(),
        "coleta": {"folha": "outubro de 2026", "pagamentos": data_pag, "mes_pagamentos": ate.month, "rgf": "agosto de 2026 (2º quadrimestre)"},
        "resumo": {"veiculos_ano": round(veic_ano, 2), "veiculos_pago": round(sum(C[t]["pago_2026"] for t in VEICULOS), 2),
                   "imoveis_ano": C["imovel"]["ano_2026"], "imoveis_contratos": imoveis["locadores"], "imoveis_orgaos": imoveis["orgaos_total"]},
        "folha": {**{k: folha[k] for k in ("total", "grupos", "faixas", "cds", "aposentadoria")}, "rgf": G},
        "unidades": folha["unidades"],
        "custeio": C, "veiculos": veiculos, "imoveis": {**imoveis, "orgaos_n": imoveis["orgaos_total"]},
        "outros_poderes": fora, "comparativo": comp, "vencem": vencem, "cartao": cartao,
        "regionais": {k: regionais[k] for k in ("total", "tipos", "projecao", "unidades")},
        "leitura": [
            f"<b>Folha:</b> {fmt(G['bruta'])} em 12 meses, pelo Relatório de Gestão Fiscal do Executivo; outubro de 2026 teve {fmt(folha['total']['bruto'])} brutos para {milhar(folha['total']['matriculas'])} matrículas.",
            f"<b>Veículos:</b> {fmt(veic_ano)} em 2026 com combustível, locação, manutenção e transporte escolar (pago até {data_pag} e projeção até dezembro). Em 2025 foram {fmt(sum(C[t]['anos']['2025'] for t in VEICULOS))}.",
            f"<b>Imóveis:</b> {imoveis['locadores']} imóveis alugados por {imoveis['orgaos_total']} órgãos, {fmt(C['imovel']['ano_2026'])} em 2026.",
            f"<b>Regionais:</b> as 10 secretarias executivas regionais e a coordenação custam {fmt(regionais['total']['total_2026'])} em 2026; {fmt(regionais['projecao']['Total']['total'])} de 2027 a 2030 se nada mudar.",
            "Só o Poder Executivo. Legislativo, Judiciário, Ministério Público, TCE e Defensoria ficam de fora.",
        ],
        "fontes": [
            ["SEGEP · Relação de Servidores Ativos e Afastados, outubro de 2026", "https://transparencia.ro.gov.br/servidores", "Folha bruta, vínculo, unidade, departamento e CDS de cada matrícula (matrícula criptografada)"],
            ["SEGEP · Servidores aguardando aposentadoria, outubro de 2026", "https://transparencia.ro.gov.br/servidores", "Afastados para aguardar aposentadoria e salário bruto"],
            ["Tesouro Nacional · RGF do Executivo, 2º quadrimestre de 2026", "https://siconfi.tesouro.gov.br/siconfi/pages/public/consulta_finbra_rgf/finbra_rgf_list.jsf", "Despesa com pessoal dos últimos 12 meses (Anexo 1)"],
            ["Portal da Transparência RO · Pagamentos de fornecedores", "https://transparencia.ro.gov.br/fornecedor", f"Cada ordem bancária de 2025 e de 2026 até {data_pag}, com o subelemento da despesa (coleta de {m26['coletado_em'][:10]})"],
            ["Execução das Secretarias Executivas Regionais 2026 (v04, 13/11/2026)", "https://transparencia.ro.gov.br/fornecedor", "SIGEF, UG 110009 SUGESP, posição 12/11/2026, com as listas de pessoal e de veículos das regionais"],
        ],
        "regras": [
            "Folha: uma pessoa por matrícula. O valor anual oficial é o do RGF (12 meses, com contribuição patronal); a planilha da SEGEP mostra o mês de outubro, sem encargos.",
            "Vínculo: a classificação funcional da SEGEP agrupada em efetivos civis, militares, comissionados sem cargo efetivo, temporários e CLT, cedidos de outros entes, estagiários e voluntários, aposentados e pensionistas.",
            "Custo do CDS: verbas de representação, vencimento, diferença e indenização de CDS da folha de outubro.",
            "Conferência com o estudo de 10/11/2026 (lista pública de Pessoal do Portal, regra pelo nome do cargo): ele contou 49.023 ativos e 5.852 "
            "comissionados; aqui, pela classificação funcional da SEGEP, são 49.838 ativos e 5.809 comissionados sem vínculo. A diferença de ativos "
            "são estagiários, voluntários, cedidos com pagamento parcial e pagamentos judiciais, que a SEGEP lista e o estudo deixou de fora.",
            "Veículos e imóveis: pagamentos (ordens bancárias) do Executivo pelo subelemento da despesa: " +
            "; ".join(f"{NOME_TEMA[t].lower()} = " + ", ".join(f"{c[:1]}.{c[1:2]}.{c[2:4]}.{c[4:6]}.{c[6:]} ({n.lower()})" for c, n in cods.items()) for t, cods in SUBELEMENTOS.items()) +
            ". Em outros serviços (3.3.90.39.99 e 3.3.90.36.99) entra só o pagamento cuja nota tem histórico de combustível, manutenção, locação de veículo ou aluguel.",
            "Fora da conta: combustível de aviação (3.3.90.30.02) e locação ou manutenção de aeronaves (táxi aéreo e helicóptero), mesmo quando pagas no subelemento de veículo. O transporte escolar (3.3.90.39.93) entra em veículos: é serviço de transporte contratado e pago pelo Estado (SEDUC).",
            f"2026 inteiro: pago de 1º/01 a {data_pag} mais a projeção do que falta, pela média mensal paga de agosto a outubro.",
            "Imóveis alugados: cada locador (CPF ou CNPJ) pago por um órgão conta um imóvel. Quem aluga dois imóveis ao mesmo órgão conta um, então o número é piso.",
            "Pessoa física aparece somada, sem nome.",
            "O pagamento repetido pelo portal quando a unidade gestora tem dois nomes conta uma vez.",
            "Regionais: planilha da equipe de transição sobre o extrato do SIGEF; CDS é cálculo sobre o quadro atual e a projeção 2027-2030 corrige pelo IPCA do Focus de 09/11/2026.",
        ],
    }
    (AQUI / "dados.json").write_text(json.dumps(M, ensure_ascii=False, indent=1), encoding="utf-8")
    js = "window.M=" + json.dumps(M, ensure_ascii=False, separators=(",", ":")) + ";"
    corpo = (AQUI / "src" / "corpo.html").read_text(encoding="utf-8")
    (AQUI / "sipre").mkdir(exist_ok=True)
    (AQUI / "sipre" / "maquina.js").write_text(js, encoding="utf-8")
    erb = ('<%= render "observatorio/cabeca", titulo: "Custo da máquina", mapa: false, graficos: true, tecnologia: false, maquina: true %>\n'
           '<div id="observatorio" class="bg-fundo text-texto antialiased min-h-full">\n'
           + corpo.replace("<script>", '<script nonce="<%= content_security_policy_nonce %>">\nShell.montar("v12-custo-da-maquina");', 1)
           + "\n</div>\n")
    (AQUI / "sipre" / "custo_da_maquina.html.erb").write_text("<%# Gerado por estado-ro 2/rondonia-2027/maquina/build_maquina.py: não edite aqui. %>\n" + erb, encoding="utf-8")
    comum = SIPRE_COMUM.read_text(encoding="utf-8")
    html = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow"><title>Custo da máquina · Rondônia</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap">
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.1.11"></script>
<script>{comum}</script>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<script>{js}</script>
<style>body{{background:#f8f8f8}}</style>
</head><body class="bg-fundo text-texto antialiased"><div id="observatorio">
<div class="bg-azul-noite text-white text-xs"><div class="max-w-[1440px] mx-auto px-6 h-8 flex items-center justify-between"><span class="font-semibold tracking-wide">ESTADO DE RONDÔNIA</span><span class="opacity-80">Dados públicos · {data_pag}</span></div></div>
{corpo}
<footer class="max-w-[1440px] mx-auto px-6 pb-8 text-xs text-texto-2">Leitura de dado público, não é auditoria. Pessoa física aparece somada, sem nome.</footer>
</div></body></html>"""
    (RAIZ / "esbocos" / "maquina.html").write_text(html, encoding="utf-8")
    painel(M, linhas_pag, m26)
    print(f"pagamentos até {data_pag}; UGs com sigla {len(sigla)} de {len(nomes)}")
    for t, c in C.items():
        print(f"  {c['nome']:24} pago R$ {c['pago_2026'] / 1e6:6.1f} mi + proj {c['projecao_2026'] / 1e6:5.1f} = {c['ano_2026'] / 1e6:6.1f} | 2025 {c['anos']['2025'] / 1e6:6.1f} | {c['subelementos']}")
    print("  imóveis:", {k: imoveis[k] for k in ("locadores", "pf", "pj", "orgaos_total", "locadores_2025")}, "| outros poderes:", fora)


def painel(M, linhas_pag, meta_pag):
    """Arquivo único no modelo das abas do Rondônia 2027 (visual de convenios/src/_base.*): esbocos/custo-da-maquina.html."""
    import base64
    geo_js = (RAIZ.parent.parent / "sipre" / "lib" / "observatorio" / "mapa.js").read_text(encoding="utf-8")
    geo = json.loads(geo_js[geo_js.index("{"):geo_js.rindex("}") + 1])
    series = ler("ibge/ro-populacao-censo2022.json")[0]["resultados"][0]["series"]
    nome_ibge = {x["localidade"]["id"]: x["localidade"]["nome"].replace(" - RO", "") for x in series}
    for f in geo["features"]:
        f["properties"]["nome"] = nome_ibge.get(f["properties"]["name"], "")
        # coordenadas com 3 casas bastam para o desenho (arquivo menor)
        def arred(c):
            return [arred(x) for x in c] if isinstance(c[0], list) else [round(c[0], 3), round(c[1], 3)]
        f["geometry"]["coordinates"] = arred(f["geometry"]["coordinates"])
    col_pag = [["Data", "d"], ["Órgão", "t"], ["Quem recebe", "t"], ["CNPJ", "t"], ["Tipo", "t"], ["Subelemento", "t"], ["Nota de empenho", "t"],
               ["Ordem bancária", "t"], ["Valor pago", "r"]]
    base_tab = {"fonte": "Portal da Transparência de Rondônia (CGE-RO)", "url": "https://transparencia.ro.gov.br/fornecedor",
                "coletado_em": meta_pag["coletado_em"], "colunas": col_pag}
    U = M["unidades"]
    tabelas = {
        "veiculos-2026": {**base_tab, "titulo": "Pagamentos de 2026 com veículos (combustível, locação, manutenção e transporte escolar), Poder Executivo", "curto": "Veículos",
                          "consulta": "Pagamentos de fornecedores, 01/01/2026 a hoje, mês a mês; subelementos de combustível, gerenciamento de abastecimento, locação, manutenção de veículos e transporte escolar",
                          "nota": "Pessoa física aparece sem nome. Aeronaves e combustível de aviação ficam de fora.",
                          "linhas": [r for r in linhas_pag if r[4] != "Aluguel de imóveis"]},
        "imoveis-2026": {**base_tab, "titulo": "Pagamentos de aluguel de imóveis em 2026, Poder Executivo", "curto": "Imóveis",
                         "consulta": "Pagamentos de fornecedores, 01/01/2026 a hoje, mês a mês; subelementos de locação de imóveis (pessoa jurídica e física) e aluguel de exercício anterior",
                         "nota": "Pessoa física aparece sem nome.", "linhas": [r for r in linhas_pag if r[4] == "Aluguel de imóveis"]},
        "servidores-orgao": {"titulo": "Servidores ativos por órgão, folha de outubro de 2026", "curto": "Servidores", "fonte": "SEGEP (planilha da folha de outubro de 2026)",
                             "url": "https://transparencia.ro.gov.br/servidores", "coletado_em": "2026-11-13 00:00",
                             "consulta": "Relação de Servidores Ativos e Afastados, referência 10/2026, versão com unidade e departamento; uma pessoa por matrícula",
                             "nota": "Só totais: a planilha da SEGEP traz a matrícula criptografada.",
                             "colunas": [["Órgão", "t"], ["Nome", "t"], ["Servidores ativos", "n"], ["Bruto de outubro", "r"], ["Ocupam CDS", "n"], ["Verba de CDS no mês", "r"], ["Afastados", "n"]]
                             + [[g["nome"], "n"] for g in M["folha"]["grupos"] if g["grupo"] != "inativo"],
                             "linhas": [[u["unidade"], u.get("nome", ""), u["pessoas"], u["bruto"], u["com_cds"], u["custo_cds"], u["afastados"]]
                                        + [u["grupos"].get(g["grupo"], {}).get("pessoas", 0) for g in M["folha"]["grupos"] if g["grupo"] != "inativo"] for u in U]},
        "rgf": {"titulo": "Despesa com pessoal do Poder Executivo, RGF Anexo 1, 2023 a 2026", "curto": "RGF", "fonte": "Tesouro Nacional, Siconfi",
                "url": "https://siconfi.tesouro.gov.br/siconfi/pages/public/declaracao/declaracao_list.jsf", "coletado_em": ler("s8_rgf_pessoal.json")["meta"]["coletado_em"],
                "consulta": "RGF, Anexo 1, Poder Executivo de Rondônia, quadrimestral (API do Siconfi: rgf, id_ente 11, co_poder E)",
                "nota": "Valores de 12 meses até o fim de cada quadrimestre. Os limites da LRF: alerta 44,1%, prudencial 46,55%, máximo 49% da receita corrente líquida ajustada.",
                "colunas": [["Ano", "n"], ["Quadrimestre", "n"], ["Despesa bruta com pessoal", "r"], ["Despesa total com pessoal (DTP)", "r"], ["Receita corrente líquida ajustada", "r"], ["% da receita", "t"]],
                "linhas": [[x["ano"], x["quadrimestre"], x["bruta"], x["dtp"], x["rcl_ajustada"], f"{x['pct_rcl']:.2f}%".replace(".", ",")] for x in M["folha"]["rgf"]["historico"]]},
        "contratos-vencem": {"titulo": "Contratos vigentes de aluguel de imóvel, locação de veículo e gerenciadoras de cartão, Poder Executivo", "curto": "Contratos",
                             "fonte": "Portal da Transparência de Rondônia (CGE-RO)", "url": "https://transparencia.ro.gov.br/Contratos", "coletado_em": "2026-10-12 00:00",
                             "consulta": "Contratos do portal (2015-2026), vigência publicada, objeto de locação de imóvel ou de veículo; contratos das gerenciadoras Prime e Uzzipay",
                             "nota": "A vigência é a publicada no portal; aditivos de prazo podem não aparecer. Cada linha abre a ficha do contrato.",
                             "colunas": [["Vence em", "d"], ["Tipo", "t"], ["Órgão", "t"], ["Contratada", "t"], ["Número", "t"], ["Processo SEI", "t"], ["Valor", "r"], ["Objeto", "t"], ["Contrato", "u"]],
                             "linhas": [["/".join(reversed(c["vigencia"].split("-"))) if c["vigencia"] else "", {"imovel": "Aluguel de imóvel", "locacao": "Locação de veículo"}.get(c.get("tipo"), "Gerenciadora de cartão"),
                                         c["sigla"], c["contratado"], c["numero"], c["processo"], c["valor"], c["objeto"], c["link"]] for c in M["cartao"] + M["vencem"]]},
        "regionais": {"titulo": "Secretarias Executivas Regionais: custo de 2026 por tipo", "curto": "Regionais", "fonte": "Equipe de transição, sobre o extrato do SIGEF (UG 110009 SUGESP)",
                      "url": "https://transparencia.ro.gov.br/fornecedor", "coletado_em": "2026-11-13 00:00",
                      "consulta": "Execução das Secretarias Executivas Regionais 2026, v04 de 13/11/2026, posição 12/11/2026",
                      "colunas": [["Unidade", "t"], ["Sede", "t"], ["Tipo de despesa", "t"], ["Por mês", "r"], ["Até 12/11", "r"], ["Total estimado 2026", "r"], ["Natureza do valor", "t"]],
                      "linhas": [[u["codigo"], u["sede"], k, v["mensal"], v["ate_12_11"], v["total_2026"], v.get("natureza") or ""]
                                 for u in M["regionais"]["unidades"] for k, v in u["tipos"].items() if v["total_2026"]]},
    }
    D = {"coletado_em": meta_pag["coletado_em"], "links": {"portal": "https://transparencia.ro.gov.br/fornecedor", "detalhe": ""}, "tabelas": tabelas,
         "nomes": {**{o["sigla"]: o["nome"] for o in M["veiculos"]["orgaos"] + M["imoveis"]["orgaos"]},
                   **{u["unidade"]: u["nome"] for u in U if u.get("nome")}}, "M": M, "geo": geo}
    payload = json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fonte = base64.b64encode((RAIZ / "vendor" / "fontes" / "inter-var.woff2").read_bytes()).decode()
    css_fonte = f"@font-face{{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:block;src:url(data:font/woff2;base64,{fonte}) format('woff2')}}"
    base = RAIZ / "convenios" / "src"
    h = (AQUI / "src" / "painel.html").read_text(encoding="utf-8")
    h = (h.replace("/*__BASE_CSS__*/", (base / "_base.css").read_text(encoding="utf-8"))
          .replace("/*__BASE_JS__*/", (base / "_base.js").read_text(encoding="utf-8"))
          .replace("/*__FONTES__*/", css_fonte, 1)
          .replace("/*__DADOS__*/null", payload)
          .replace("/*__TELAS__*/", (AQUI / "src" / "telas.js").read_text(encoding="utf-8")))
    (RAIZ / "esbocos" / "custo-da-maquina.html").write_text(h, encoding="utf-8")
    print("esbocos/custo-da-maquina.html", round(len(h) / 1024), "KB;", len(linhas_pag), "pagamentos")


def milhar(n):
    return f"{n:,}".replace(",", ".")


def fmt(v):
    a = abs(v)
    if a >= 1e9:
        return f"R$ {v / 1e9:.2f} bilhões".replace(".", ",")
    return f"R$ {v / 1e6:.1f} milhões".replace(".", ",") if a < 1e8 else f"R$ {v / 1e6:.0f} milhões"


if __name__ == "__main__":
    main()
