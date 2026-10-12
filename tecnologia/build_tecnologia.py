"""Monta a aba "Tecnologia no Estado": todo o gasto do Governo de Rondônia com tecnologia, por órgão, tipo, empresa e vencimento.

Uso: python3 tecnologia/build_tecnologia.py
Ordem completa:
  python3 coleta_contratos.py                 contratos de todos os órgãos, 2015–2026 (dados-fonte/s5_contratos.json)
  python3 tecnologia/classificar.py           primeira triagem por regra (dados-fonte/s5_contratos_ti.json)
  (revisão contrato a contrato)               tecnologia/revisao/R_*.json, conforme tecnologia/revisao/_BRIEFING.md
  python3 tecnologia/coleta_empenhos.py       notas de empenho do elemento 40 (TIC), 2023–2026 (dados-fonte/s5_empenhos_tic.json)
  PCA 2026                                    dados-fonte/pca/pca_2026_ti.json (itens de TI dos Planos de Contratações Anuais)
  python3 tecnologia/build_tecnologia.py      grava dados-fonte/s5_tecnologia.json, esbocos/tecnologia.html e site/tecnologia.html

Regras de leitura (vão escritas na tela):
  - Foco: contratos cadastrados no portal de 2023 a 2026, mais os anteriores ainda vigentes em DATA_CORTE.
    2015–2022 ficam guardados em dados-fonte/s5_contratos.json, fora das contas.
  - Valor do contrato = "valor global" informado no portal (o valor total previsto para toda a vigência, sem aditivos).
  - Tecnologia = decisão da revisão contrato a contrato (não só a regra automática).
  - Empenhado e pago = notas de empenho do elemento 40 (TIC). Equipamento (4.4.90.52) não tem elemento próprio e só aparece pelos contratos.
"""
import base64
import csv
import glob
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(AQUI))
from classificar import CATEGORIAS, DATA_CORTE, NOME_CURTO, sigla_de_nome  # noqa: E402

ANO_FOCO = 2023
PORTAL = "https://transparencia.ro.gov.br"
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
NOME_CAT = {c: n for c, n, _ in CATEGORIAS}
ORDEM_CAT = ["sistemas", "licencas", "datacenter", "conectividade", "seguranca", "suporte", "impressao", "equipamentos", "rede", "operacional", "frota"]
# funções genéricas (compra de bens) não contam como "sistema repetido"
GENERICAS = {"computadores", "notebooks-tablets", "perifericos-suprimentos", "audiovisual-interativo", "outra", "", "rede-wifi", "robotica-maker",
             "nobreak-energia", "drones", "radio", "satelite"}
SINONIMOS = {"design-midia": "design-grafico", "cad-bim": "cad-engenharia", "engenharia-cad": "cad-engenharia", "projeto-engenharia-cad": "cad-engenharia",
             "rastreamento-frota": "rastreamento-veicular", "consulta-cadastral": "consulta-bases-dados", "gestao-contratos": "compras-licitacao",
             "microsoft": "suite-escritorio-email", "suite-escritorio": "suite-escritorio-email", "email-colaboracao": "suite-escritorio-email",
             "monitoramento-rede": "observabilidade-apm", "": "outra"}
FUNCAO_NOME = {
    "gestao-escolar": "Gestão escolar", "diario-eletronico": "Diário eletrônico", "plataforma-educacional": "Plataforma educacional e de aprendizagem",
    "avaliacao-educacional": "Avaliação educacional", "tecnologia-assistiva": "Tecnologia assistiva", "prontuario-saude": "Prontuário eletrônico",
    "regulacao-saude": "Regulação em saúde", "gestao-hospitalar": "Gestão hospitalar", "laboratorio-saude": "Sistema de laboratório", "telemedicina": "Telemedicina",
    "rh-folha": "RH e folha", "ponto-eletronico": "Ponto eletrônico", "gestao-processos-documentos": "Gestão de processos e documentos",
    "protocolo-atendimento": "Protocolo e atendimento", "portal-site": "Portal e site", "app-cidadao": "Aplicativo ao cidadão",
    "financeiro-contabil": "Financeiro e contábil", "tributario-arrecadacao": "Tributário e arrecadação", "compras-licitacao": "Compras, licitações e contratos",
    "banco-de-precos": "Banco de preços (pesquisa de preços)", "patrimonio-almoxarifado": "Patrimônio e almoxarifado", "frota-abastecimento": "Frota: abastecimento",
    "frota-manutencao": "Frota: manutenção", "rastreamento-veicular": "Rastreamento veicular", "bi-dados": "BI e painéis de dados", "ia": "Inteligência artificial",
    "juridico": "Jurídico", "erp": "ERP (gestão integrada)", "previdencia": "Previdência", "registro-empresarial": "Registro empresarial",
    "transito-veiculos": "Trânsito e veículos", "seguranca-publica": "Segurança pública", "prisional-monitoramento": "Monitoramento eletrônico de presos",
    "videomonitoramento": "Videomonitoramento e câmeras", "cameras-corporais": "Câmeras corporais", "pericia-forense-digital": "Perícia forense digital",
    "geo-mapas": "Geoprocessamento e mapas", "meio-ambiente": "Meio ambiente", "agro-defesa": "Defesa agropecuária", "cad-engenharia": "Projeto e CAD/BIM de engenharia",
    "orcamento-obras": "Orçamento de obras", "gestao-obras": "Gestão de obras", "design-grafico": "Design gráfico e mídia (Adobe e similares)",
    "suite-escritorio-email": "Escritório, e-mail e colaboração (Microsoft, Google)", "editor-pdf": "Editor de PDF", "antivirus": "Antivírus e proteção de estações",
    "certificado-digital": "Certificado digital", "firewall": "Firewall", "gestao-vulnerabilidades": "Gestão de vulnerabilidades", "plataforma-seguranca": "Plataforma de segurança e criptografia",
    "pam-acessos": "Gestão de acessos privilegiados", "antispam-email": "Antispam de e-mail", "lgpd": "LGPD", "nuvem": "Nuvem", "datacenter-servidores": "Datacenter e servidores",
    "backup": "Backup", "banco-de-dados": "Banco de dados", "observabilidade-apm": "Monitoramento de sistemas e rede", "internet-link": "Internet e links de dados",
    "telefonia-fixa": "Telefonia fixa e VoIP", "telefonia-movel": "Telefonia móvel e chips de dados", "satelite": "Satélite", "radio": "Rádio digital",
    "videoconferencia": "Videoconferência", "transmissao-webinar": "Transmissão e webinar", "impressao": "Impressão (outsourcing e locação)",
    "computadores": "Computadores", "notebooks-tablets": "Notebooks e tablets", "perifericos-suprimentos": "Periféricos e suprimentos", "rede-wifi": "Rede lógica e wi-fi",
    "audiovisual-interativo": "Audiovisual e telas interativas", "robotica-maker": "Robótica e maker", "nobreak-energia": "Nobreaks", "drones": "Drones",
    "suporte-servicedesk": "Suporte e service desk", "fabrica-software": "Fábrica de software e sustentação", "digitalizacao": "Digitalização e guarda de documentos",
    "consultoria-ti": "Consultoria de TI", "auditoria-ti": "Auditoria de TI", "gestao-projetos": "Gestão de projetos", "consulta-bases-dados": "Consulta a bases de dados",
    "controle-acesso": "Controle de acesso", "alarme-intrusao": "Alarme", "acessibilidade-digital": "Acessibilidade digital", "outra": "Outros",
}
# processos cujo órgão vem vazio no portal e não aparece em nenhum outro contrato
PREFIXO_FIXO = {"0040": "SOPH"}
# valor global implausível no portal: fica na lista, marcado, e fora das somas até conferência
VALOR_A_CONFERIR = {"010/SOPH/RO/2026|0040.000108/2026 - 73": "R$ 135,2 mi para o ERP da Sociedade de Portos: valor provavelmente digitado errado no portal"}
# sigla da unidade gestora nos empenhos -> sigla usada aqui
UG_EMPENHO = {"PC-RO": "PC", "PCIVIL": "PC", "PM-RO": "PM", "PMILIT": "PM", "CBOMB": "CBM", "CBMRO": "CBM", "CGE-RO": "CGE", "PGE-RO": "PGE",
              "Iperon": "IPERON", "Fapero": "FAPERO", "CETAS": "IESPRO",
              # fundos do Executivo -> órgão gestor
              "FUNESP": "SESDEC", "FESPREN": "SESDEC", "FUNRESPOL": "PC", "FUNDAT": "SEFIN", "FES": "SESAU", "FIDER": "SEDEC", "FEPRAM": "SEDAM",
              "FERHRO": "SEDAM", "FESA": "IDARON", "FUMORPGE": "PGE", "FUREFUR": "SEPAT", "FRFUR": "SEPAT", "FUNESBOM": "CBM",
              # outros Poderes e órgãos autônomos (fora das contas do Executivo)
              "FUJU": "TJ", "FDI/TC": "TCE", "FUNDIMPER": "MP", "FUNDEP": "DPE"}
OUTROS_PODERES = {"TJ": "Tribunal de Justiça", "ALE": "Assembleia Legislativa", "TCE": "Tribunal de Contas", "MP": "Ministério Público", "DPE": "Defensoria Pública"}


def valor(s):
    try:
        return float(re.sub(r"[^\d,-]", "", s or "").replace(",", "."))
    except ValueError:
        return 0.0


def revisoes():
    dec = {}
    for p in sorted(glob.glob(str(AQUI / "revisao" / "R_*.json"))):
        for x in json.loads(Path(p).read_text(encoding="utf-8")):
            dec.setdefault(x["id"], x)
    return dec


def contratos():
    bruto = json.loads((FONTE / "s5_contratos.json").read_text(encoding="utf-8"))
    dados = bruto["dados"]
    pref = defaultdict(Counter)
    for r in dados:
        s = sigla_de_nome(r["orgao"])
        m = re.search(r"(\d{4})\.\s*\d", r["processo_sei"] or "")
        if s and m and not s.startswith("OUTRO"):
            pref[m[1]][s] += 1
    prefixo = {p: c.most_common(1)[0][0] for p, c in pref.items()}
    prefixo.update(PREFIXO_FIXO)
    dec = revisoes()
    regs, vistos = [], set()
    for r in dados:
        k = f"{r['numero']}|{r['processo_sei']}"
        d = dec.get(k)
        if not d or d.get("categoria") in (None, "", "fora"):
            continue
        vig = r["vigencia_iso"]
        situacao = "vigente" if vig and vig >= DATA_CORTE else ("sem vigência" if not vig else "vencido")
        if not (r["ano_consulta"] >= ANO_FOCO or situacao == "vigente"):
            continue
        s = sigla_de_nome(r["orgao"])
        if s.startswith("OUTRO"):
            s = "AGERO" if "REGULA" in s.upper() else s[6:]
        if not s:
            m = re.search(r"(\d{4})\.\s*\d", r["processo_sei"] or "")
            s = prefixo.get(m[1], "NI") if m else "NI"
        dup = (k, r["valor"], r["contratado"])
        if dup in vistos:      # o portal repete alguns registros idênticos
            continue
        vistos.add(dup)
        cat = d["categoria"] if d["categoria"] in NOME_CAT else "sistemas"
        fun = SINONIMOS.get(d.get("funcao") or "", d.get("funcao") or "outra")
        regs.append({"id": k, "sigla": s, "ano": r["ano_consulta"], "numero": r["numero"], "processo": r["processo_sei"],
                     "assinatura": r["assinatura"], "vigencia": r["vigencia"], "vigencia_iso": vig, "situacao": situacao,
                     "contratado": r["contratado"], "cnpj": r["cnpj"], "valor": r["valor"] or 0, "origem": r["origem"],
                     "aditivo": r["tem_aditivo"], "objeto": re.sub(r"\s+", " ", r["objeto"]).strip(), "cat": cat, "funcao": fun,
                     "produto": d.get("produto") or "", "nota": d.get("nota") or "", "link": r["detalhe"] or PORTAL + "/contratos",
                     "rescisao": bool(re.search(r"RESCIS|DISTRAT", r["numero"] + " " + r["objeto"], re.I)),
                     "conferir": VALOR_A_CONFERIR.get(k, "")})
    return regs, bruto["meta"]


def empenhos():
    arq = FONTE / "s5_empenhos_tic.json"
    if not arq.exists():
        return [], {}
    bruto = json.loads(arq.read_text(encoding="utf-8"))
    out = []
    for n in bruto["dados"]:
        d = n.get("detalhe") or {}
        ug = UG_EMPENHO.get(n["unidadeGestora"], n["unidadeGestora"])
        out.append({"ano": n["ano"], "ug": ug, "executivo": ug not in OUTROS_PODERES, "nota": n["numeroEmpenho"], "data": n["dataDocumentoFormatada"], "credor": n["credor"],
                    "cnpj": d.get("CPF/CNPJ do credor", ""), "emp": valor(n["valorEmpenhado"]), "pago": valor(n["valorPago"]),
                    "elemento": n["elemento"], "item": d.get("Item de despesa", ""), "historico": d.get("Histórico", ""),
                    "programa": d.get("Programa de governo", ""), "modalidade": d.get("Modalidade licitatória", ""),
                    "link": n["linkDetalhes"]})
    return out, bruto["meta"]


def pca():
    arq = FONTE / "pca" / "pca_2026_ti.json"
    if not arq.exists():
        return []
    itens = json.loads(arq.read_text(encoding="utf-8"))
    ajuste = {"PC-RO": "PC", "PM-RO": "PM", "CBMRO": "CBM", "CGE-RO": "CGE", "PGE-RO": "PGE", "": "SI"}
    for i in itens:
        i["sigla"] = ajuste.get(i.get("orgao", ""), i.get("orgao", ""))
    return itens


def sobreposicoes(regs):
    """Mesma função em vários órgãos; mesma empresa em vários órgãos; mesma função com várias empresas dentro de um órgão."""
    ativos = [r for r in regs if not r["rescisao"] and not r["conferir"]]
    por_fun = defaultdict(list)
    for r in ativos:
        if r["funcao"] not in GENERICAS:
            por_fun[r["funcao"]].append(r)
    funcoes = []
    for f, xs in por_fun.items():
        orgs = sorted({x["sigla"] for x in xs})
        if len(orgs) >= 2:
            funcoes.append({"funcao": f, "orgaos": orgs, "empresas": len({x["cnpj"] or x["contratado"] for x in xs}),
                            "contratos": len(xs), "valor": sum(x["valor"] for x in xs), "cat": Counter(x["cat"] for x in xs).most_common(1)[0][0]})
    funcoes.sort(key=lambda x: (-len(x["orgaos"]), -x["valor"]))
    por_emp = defaultdict(list)
    for r in ativos:
        por_emp[r["cnpj"] or r["contratado"]].append(r)
    empresas = []
    for k, xs in por_emp.items():
        orgs = sorted({x["sigla"] for x in xs})
        empresas.append({"cnpj": xs[0]["cnpj"], "nome": xs[0]["contratado"], "orgaos": orgs, "contratos": len(xs),
                         "valor": sum(x["valor"] for x in xs), "funcoes": sorted({x["funcao"] for x in xs})})
    empresas.sort(key=lambda x: -x["valor"])
    dentro = []
    por_org_fun = defaultdict(list)
    for r in ativos:
        if r["funcao"] not in GENERICAS:
            por_org_fun[(r["sigla"], r["funcao"])].append(r)
    for (s, f), xs in por_org_fun.items():
        emp = {x["cnpj"] or x["contratado"] for x in xs}
        if len(xs) >= 2 and len(emp) >= 2:
            dentro.append({"sigla": s, "funcao": f, "contratos": len(xs), "empresas": len(emp), "valor": sum(x["valor"] for x in xs)})
    dentro.sort(key=lambda x: -x["valor"])
    return {"funcoes": funcoes, "empresas": empresas, "dentro": dentro}


def main():
    regs, meta_c = contratos()
    emps, meta_e = empenhos()
    itens_pca = pca()
    sob = sobreposicoes(regs)
    nomes = dict(NOME_CURTO)
    nomes.update({"NI": "Órgão não informado no portal", "SOPH": "Sociedade de Portos e Hidrovias", "IEES": "Instituto Estadual de Educação e Saúde",
                  "CAERD": "Companhia de Águas e Esgotos de Rondônia", "ALE": "Assembleia Legislativa"})
    nomes["SOPH"] = "Sociedade de Portos e Hidrovias"
    nomes.update(OUTROS_PODERES)

    conta = [r for r in regs if not r["rescisao"] and not r["conferir"]]
    resumo = {"contratos": len(regs), "valor": sum(r["valor"] for r in conta if r["cat"] != "frota"),
              "valor_frota": sum(r["valor"] for r in conta if r["cat"] == "frota"),
              "contratos_ti": sum(1 for r in conta if r["cat"] != "frota"), "contratos_frota": sum(1 for r in conta if r["cat"] == "frota"),
              "rescisoes": sum(1 for r in regs if r["rescisao"]), "a_conferir": sum(1 for r in regs if r["conferir"]),
              "vigentes": sum(1 for r in regs if r["situacao"] == "vigente"), "orgaos": len({r["sigla"] for r in regs}),
              "empresas": len({r["cnpj"] or r["contratado"] for r in regs}),
              "empenhado": {a: sum(e["emp"] for e in emps if e["ano"] == a and e["executivo"]) for a in (2023, 2024, 2025, 2026)},
              "pago": {a: sum(e["pago"] for e in emps if e["ano"] == a and e["executivo"]) for a in (2023, 2024, 2025, 2026)},
              "empenhado_outros_poderes": {a: sum(e["emp"] for e in emps if e["ano"] == a and not e["executivo"]) for a in (2023, 2024, 2025, 2026)},
              "pca_itens": len(itens_pca), "pca_valor": sum(i.get("valor_estimado") or 0 for i in itens_pca)}
    dados = {"coletado_em": meta_c["coletado_em"], "data_corte": DATA_CORTE, "ano_foco": ANO_FOCO,
             "links": {"portal": PORTAL + "/contratos", "detalhe": PORTAL + "/Despesa/notas-de-empenho/detalhes"},
             "categorias": [[c, NOME_CAT[c]] for c in ORDEM_CAT], "nomes": nomes, "funcoes": FUNCAO_NOME, "resumo": resumo,
             "registros": regs, "sobreposicoes": sob,
             "empenhos": [[e["ano"], e["ug"], e["credor"], e["cnpj"], e["emp"], e["pago"], e["elemento"], e["item"], e["data"], e["historico"], e["link"]] for e in emps if e["executivo"]],
             "outros_poderes": OUTROS_PODERES,
             "pca": itens_pca, "meta_empenhos": meta_e}
    (FONTE / "s5_tecnologia.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")

    # tabelas dos "dados de origem"
    contr = sorted(regs, key=lambda r: (r["sigla"], -r["valor"]))
    tabelas = {
        "tec-contratos": {"id": "tec-contratos", "curto": "Contratos", "titulo": "Contratos de tecnologia do Governo de Rondônia (2023–2026 e vigentes)",
                          "fonte": "Portal da Transparência de Rondônia (CGE-RO) · Contratos", "url": PORTAL + "/contratos", "coletado_em": meta_c["coletado_em"],
                          "consulta": meta_c["consulta"] + "; classificação de tecnologia revisada contrato a contrato",
                          "nota": "Valor = valor global informado no portal (total previsto na vigência, sem aditivos). Categoria e função são a classificação deste painel.",
                          "colunas": [["Órgão", "t"], ["Categoria", "t"], ["Função", "t"], ["Empresa", "t"], ["CNPJ", "t"], ["Valor global", "r"], ["Ano", "n"],
                                      ["Assinatura", "d"], ["Vigência", "d"], ["Situação", "t"], ["Número", "t"], ["Processo SEI", "t"], ["Modalidade", "t"], ["Aditivo", "t"], ["Objeto", "t"], ["Ficha", "u"]],
                          "linhas": [[r["sigla"], NOME_CAT[r["cat"]], r["funcao"], r["contratado"], r["cnpj"], r["valor"], r["ano"], r["assinatura"], r["vigencia"],
                                      r["situacao"], r["numero"], r["processo"], r["origem"], r["aditivo"], r["objeto"], r["link"]] for r in contr]},
    }
    if emps:
        tabelas["tec-empenhos"] = {"id": "tec-empenhos", "curto": "Empenhos TIC", "titulo": "Notas de empenho de TIC (elemento 40), 2023–2026",
                                   "fonte": "Portal da Transparência de Rondônia (CGE-RO) · Despesas por empenho", "url": PORTAL + "/despesa/despesa-estadual",
                                   "coletado_em": meta_e.get("coletado_em", ""), "consulta": "Filtro Elemento de Despesa 33904000 e 44904000, exercícios 2023 a 2026, todos os órgãos",
                                   "nota": "Empenhado = valor final da nota. Pago = valor pago informado pelo portal. Os fundos do Executivo aparecem pelo órgão gestor (ex.: FES = SESAU, FUNESP = SESDEC). Inclui os outros Poderes (coluna Poder), que ficam fora das somas da tela.",
                                   "colunas": [["Ano", "n"], ["Poder", "t"], ["Órgão", "t"], ["Credor", "t"], ["CNPJ", "t"], ["Empenhado", "r"], ["Pago", "r"], ["Elemento", "t"], ["Item de despesa", "t"], ["Data", "d"], ["Histórico", "t"], ["Nota", "l"]],
                                   "linhas": [[e["ano"], "Executivo" if e["executivo"] else OUTROS_PODERES[e["ug"]], e["ug"], e["credor"], e["cnpj"], e["emp"], e["pago"], e["elemento"], e["item"], e["data"], e["historico"], e["link"]] for e in emps]}
    if itens_pca:
        tabelas["tec-pca"] = {"id": "tec-pca", "curto": "PCA 2026", "titulo": "Itens de tecnologia nos Planos de Contratações Anuais 2026",
                              "fonte": "Portal da Transparência de Rondônia · Plano de Contratações Anual (portarias no DOE)", "url": PORTAL + "/licitacoes/planoanualdecontratacoes",
                              "coletado_em": meta_c["coletado_em"], "consulta": "PDF do PCA 2026 de cada órgão; itens de TI extraídos página a página",
                              "nota": "Valor estimado conforme o PCA de cada órgão. SEDUC e SESAU não têm PCA 2026 publicado nessa página.",
                              "colunas": [["Órgão", "t"], ["Categoria", "t"], ["Descrição", "t"], ["Quantidade", "n"], ["Unidade", "t"], ["Natureza", "t"], ["Valor estimado", "r"], ["Previsão", "t"], ["Página", "n"]],
                              "linhas": [[i["sigla"], NOME_CAT.get(i.get("categoria"), i.get("categoria", "")), i.get("descricao", ""), i.get("quantidade") or "", i.get("unidade", ""),
                                          i.get("natureza", ""), i.get("valor_estimado") or 0, i.get("previsao", ""), i.get("pagina") or ""] for i in itens_pca]}
    dados_pag = {k: dados[k] for k in ("coletado_em", "data_corte", "ano_foco", "links", "categorias", "nomes", "funcoes", "resumo", "registros", "sobreposicoes", "pca")}
    dados_pag["empenhos"] = dados["empenhos"]
    dados_pag["tabelas"] = tabelas
    payload = json.dumps(dados_pag, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    with open(AQUI / "contratos_tecnologia.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([c[0] for c in tabelas["tec-contratos"]["colunas"]])
        w.writerows(tabelas["tec-contratos"]["linhas"])

    fonte = base64.b64encode((RAIZ / "vendor" / "fontes" / "inter-var.woff2").read_bytes()).decode()
    css_fonte = f"@font-face{{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:block;src:url(data:font/woff2;base64,{fonte}) format('woff2')}}"
    base = RAIZ / "convenios" / "src"
    h = (AQUI / "src" / "tecnologia.html").read_text(encoding="utf-8")
    h = (h.replace("/*__BASE_CSS__*/", (base / "_base.css").read_text(encoding="utf-8"))
          .replace("/*__BASE_JS__*/", (base / "_base.js").read_text(encoding="utf-8"))
          .replace("/*__FONTES__*/", css_fonte, 1)
          .replace("/*__DADOS_TEC__*/null", payload))
    (RAIZ / "esbocos" / "tecnologia.html").write_text(h, encoding="utf-8")
    (RAIZ / "site" / "tecnologia.html").write_text(h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1), encoding="utf-8")
    print(f"site/tecnologia.html {round(len(h) / 1024)} KB · {len(regs)} contratos · {len(emps)} empenhos · {len(itens_pca)} itens de PCA")
    print("resumo:", json.dumps({k: v for k, v in resumo.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
