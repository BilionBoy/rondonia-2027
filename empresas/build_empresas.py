"""Monta a aba "Quem vende ao Estado": todas as empresas e entidades privadas que receberam empenho do Governo de Rondônia
em 2023–2026, por órgão, por ano e por modalidade, com os contratos e convênios de cada uma e a tecnologia destacada.

Uso: python3 empresas/build_empresas.py
Fontes (todas em dados-fonte/):
  s3_empenhos_{2023..2026}.json   todas as notas de empenho (lista: credor, unidade, empenhado, pago)
  s5_*detalhe*                    ficha de cada nota já aberta (CNPJ, modalidade, histórico): s5_empenhos_tic, s5_empenhos_fornecedores,
                                  s5_varredura, s5_detalhes_tudo, s5_parceria_ufmg_brtec
  s5_contratos.json, s5_convenios.json   contratos e convênios/termos do portal
  s5_tecnologia.json              classificação de tecnologia (aba "Tecnologia no Estado")
Grava dados-fonte/s6_empresas_estado.json, empresas/empresas_estado.csv, esbocos/empresas.html e site/empresas.html.

Regras:
  - Credor é classificado pelo nome em: empresa/entidade privada (entra na aba), órgão ou ente público, folha/consignação/encargos
    (sindicatos, INSS, previdência), dívida e precatórios. Só a primeira entra no ranking; as outras somam à parte.
  - Mesmo credor = mesmo CNPJ quando o detalhe foi aberto; senão, o mesmo nome normalizado.
  - Modalidade = a informada no detalhe da nota (abertas: todas as de empresas a partir de R$ 20 mil, mais as de tecnologia).
"""
import base64
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(RAIZ / "tecnologia"))
from build_tecnologia import UG_EMPENHO, OUTROS_PODERES, modalidade  # noqa: E402

PORTAL = "https://transparencia.ro.gov.br"
NOINDEX = '<meta name="robots" content="noindex, nofollow">'
ANOS = (2023, 2024, 2025, 2026)
PUBLICO = re.compile(r"PREFEITURA|MUNICIPIO|FUNDO |FUNDO$|SECRETARIA|SUPERINT|AGENCIA|AG DEF|DEPARTAMENTO|ENT AUT|AUTARQ|TRIBUNAL|ASSEMBLEIA|MINISTERIO|"
                     r"DEFENSORIA|PODER JUDICIARIO|GOVERNO|ESTADO DE RONDONIA|CAMARA MUNICIPAL|RECEITA FEDERAL|POLICIA|CORPO DE BOMBEIROS|"
                     r"UNIVERSIDADE FEDERAL|INSTITUTO FEDERAL|FUNDACAO EST|FUND\. DE HEMAT|FUNDACAO DE HEMAT|JUNTA COMERCIAL|CONTROLADORIA|PROCURADORIA|"
                     r"COMPANHIA DE AGUAS|CAERD|SOCIEDADE DE PORTOS|EMPRESA BRASILEIRA DE CORREIOS|CORREIOS|SERPRO|DATAPREV|IPERON|INSTITUTO DE PREVID|"
                     r"CONSELHO ESCOLAR|UNIDADE EXECUTORA|ESCOLA ESTADUAL|ESCOLA MUNICIPAL|E\.E\.E\.F|EEEFM|CENTRO ESTADUAL DE EDUCA")
FOLHA = re.compile(r"SINDICATO|SIND\.|SINDEPRO|INSS|INSTITUTO NACIONAL DO SEGURO|FUNDO PREVID|PREVIDENCI|PASEP|FGTS|DIARIAS|FOLHA|"
                   r"PESSOA FISICA/JURIDICA SEM|CREDORES NACIONAIS|ASSOCIACAO DOS (SERVIDORES|POLICIAIS|MILITARES|DELEGADOS|PRACAS|OFICIAIS)|"
                   r"CAIXA ECONOMICA|BANCO DO BRASIL|BANCO BRADESCO|BANCO SANTANDER|BANCO ITAU|BANCO DA AMAZONIA|SICOOB|SICREDI|CREDISIS|COOPERATIVA DE CREDITO|"
                   r"PENSAO ALIMENT|RESTITUIC|^PESSOAL |^PROGRAMA |AUXILIO|BOLSA |ESTAGIARIO|ADIANTAMENTO|SUPRIMENTO DE FUNDOS")
DIVIDA = re.compile(r"DIVIDA|PRECATORIO|L\.9496|PROINVESTE|BNDES|TESOURO NACIONAL|SECRETARIA DO TESOURO|RPV|REQUISIC")


# Frota do Estado (tema): gestoras de cartão, combustível, locação, manutenção/peças e compra de veículos.
FROTA_GESTORA = re.compile(r"UZZIPAY|PRIME CONSULTORIA E ASSESSORIA|TICKET SOLUC|TICKET GESTAO|TRIVALE|NEO CONSULTORIA E ADMIN|LINK CARD ADMIN|MAXXCARD|VALECARD|GOOD ?CARD|POLICARD")
FROTA_LOCADORA = re.compile(r"LOCADORA|LOCACAO DE VEIC|LOCALIZA|MOVIDA|CS BRASIL FROTAS|NOSSA FROTA|RENT A CAR|TCAR LOCAC")
FROTA_HIST = re.compile(r"ABASTECIMENTO|COMBUSTIVE|GASOLINA|OLEO DIESEL|DIESEL S10|ETANOL|LOCACAO DE (VEICULO|VIATURA|CAMINHONETE|AUTOMOVE)|MANUTENCAO (PREVENTIVA|CORRETIVA)[^.]{0,60}VEICUL|"
                        r"MANUTENCAO DE (VEICULO|VIATURA|FROTA)|GESTAO DE FROTA|AUTOGESTAO|FROTA|PNEUS?\b|PECAS (AUTOMOTIVAS|E ACESSORIOS PARA VEICULO|PARA VEICULO)|"
                        r"AQUISICAO DE (\d+ )?\(?\w*\)? ?(VEICULO|VIATURA|CAMINHAO|CAMINHOES|ONIBUS|MOTOCICLETA|CAMIONETE|CAMINHONETE|AMBULANCIA|PICK)")
FROTA_NAO = re.compile(r"ABASTECIMENTO DE AGUA|SISTEMA DE ABASTECIMENTO|ABASTECIMENTO PUBLICO|AGUA POTAVEL|TRANSPORTE ESCOLAR|TRANSPORTE DE ALUNOS|PASSAGENS|FRETAMENTO|NACOES UNIDAS")


def tema_frota(credor, hist):
    c, h = sem_acento(credor), sem_acento(hist)
    if FROTA_NAO.search(c) or FROTA_NAO.search(h):
        return False
    return bool(FROTA_GESTORA.search(c) or FROTA_LOCADORA.search(c) or FROTA_HIST.search(h))


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()


def chave_nome(n):
    n = re.sub(r"[^A-Z0-9 ]", " ", sem_acento(n))
    n = re.sub(r"\b(LTDA|S A|SA|EIRELI|ME|EPP|CIA)\b", " ", n)
    return " ".join(n.split())


def valor(s):
    try:
        return float(str(s).replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def tipo_credor(nome):
    n = sem_acento(nome)
    if DIVIDA.search(n):
        return "divida"
    if FOLHA.search(n):
        return "folha"
    if PUBLICO.search(n):
        return "publico"
    return "empresa"


def detalhes():
    d = {}
    for arq, campo in (("s5_empenhos_fornecedores.json", "detalhes"), ("s5_varredura.json", "detalhes"), ("s5_detalhes_tudo.json", "detalhes")):
        p = FONTE / arq
        if p.exists():
            d.update(json.loads(p.read_text(encoding="utf-8"))[campo])
    p = FONTE / "s5_empenhos_tic.json"
    if p.exists():
        for n in json.loads(p.read_text(encoding="utf-8"))["dados"]:
            if n.get("detalhe"):
                d[n["linkDetalhes"]] = n["detalhe"]
    p = FONTE / "s5_parceria_ufmg_brtec.json"
    if p.exists():
        for n in json.loads(p.read_text(encoding="utf-8"))["notas"]:
            if n.get("detalhe"):
                d[n["linkDetalhes"]] = n["detalhe"]
    return d


def main():
    det = detalhes()
    tec = json.loads((FONTE / "s5_tecnologia.json").read_text(encoding="utf-8"))
    cnpj_ti = {re.sub(r"\D", "", r["cnpj"]): r["cat"] for r in tec["registros"] if r.get("cnpj")}
    # mesma classificação da aba de tecnologia, nota por nota (Executivo; inclui frota marcada)
    ti_nota = {x[9]: ("frota" if x[6].startswith("frota") else "ti") for x in tec.get("fornecedores", [])}
    empresas_rf = json.loads((FONTE / "s5_empresas.json").read_text(encoding="utf-8")) if (FONTE / "s5_empresas.json").exists() else {}

    # 1) todas as notas -> credor (CNPJ se houver detalhe; senão nome)
    nome_para_cnpj = {}
    notas = []
    for ano in ANOS:
        for n in json.loads((FONTE / f"s3_empenhos_{ano}.json").read_text(encoding="utf-8"))["dados"]:
            d = det.get(n["linkDetalhes"]) or {}
            c = re.sub(r"\D", "", d.get("CPF/CNPJ do credor", ""))
            if len(c) == 14:
                nome_para_cnpj.setdefault(chave_nome(n["credor"]), c)
            notas.append((ano, n, d, c))
    resumo = {"notas": len(notas), "por_tipo": defaultdict(float), "por_tipo_ano": defaultdict(lambda: defaultdict(float))}
    emp = {}
    for ano, n, d, c in notas:
        ug = UG_EMPENHO.get(n["unidadeGestora"], n["unidadeGestora"])
        t = "pessoa" if "*" in d.get("CPF/CNPJ do credor", "") else tipo_credor(n["credor"])   # CPF mascarado = pessoa física
        v, pg = valor(n["valorEmpenhado"]), valor(n["valorPago"])
        resumo["por_tipo"][t] += v
        resumo["por_tipo_ano"][t][ano] += v
        if t != "empresa":
            continue
        c = c if len(c) == 14 else nome_para_cnpj.get(chave_nome(n["credor"]), "")
        k = c or "N:" + chave_nome(n["credor"])
        e = emp.setdefault(k, {"nome": n["credor"].strip(), "cnpj": c, "total": 0.0, "pago": 0.0, "notas": 0, "anos": defaultdict(float),
                               "orgaos": defaultdict(float), "modal": defaultdict(float), "top": [], "executivo": 0.0,
                               "ti_org": defaultdict(float), "ti_anos": defaultdict(float), "ti_modal": defaultdict(float), "frota": 0.0,
                               "cubo": defaultdict(float)})
        e["total"] += v
        e["pago"] += pg
        e["notas"] += 1
        e["anos"][ano] += v
        e["orgaos"][ug] += v
        if ug not in OUTROS_PODERES:
            e["executivo"] += v
        mod = modalidade(d.get("Modalidade licitatória", "")) if d else "Nota não aberta (abaixo de R$ 20 mil)"
        e["modal"][mod] += v
        tipo_ti = ti_nota.get(n["linkDetalhes"])
        if tipo_ti != "ti" and tema_frota(n["credor"], d.get("Histórico", "")):
            tipo_ti = "frota"
        e["cubo"][(ano, ug, mod, 2 if tipo_ti == "frota" else 1 if tipo_ti else 0)] += v
        if tipo_ti:
            e["ti_org"][ug] += v
            e["ti_anos"][ano] += v
            e["ti_modal"][mod] += v
            if tipo_ti == "frota":
                e["frota"] += v
        e["top"].append([v, pg, ano, ug, n["dataDocumentoFormatada"], (d.get("Histórico") or "")[:200], d.get("Modalidade licitatória", ""), n["linkDetalhes"], mod,
                         2 if tipo_ti == "frota" else 1 if tipo_ti else 0])
        resumo.setdefault("tema", defaultdict(float))[("frota" if tipo_ti == "frota" else "ti" if tipo_ti else "outro", ug in OUTROS_PODERES)] += v

    # 2) contratos e convênios por empresa (CNPJ; senão nome)
    def ligar(arq, rotulo):
        p = FONTE / arq
        if not p.exists():
            return
        for r in json.loads(p.read_text(encoding="utf-8"))["dados"]:
            vig = r.get("vigencia_iso") or ""
            if not (r["ano_consulta"] >= 2023 or vig >= "2026-10-12"):
                continue
            c = re.sub(r"\D", "", r.get("cnpj", ""))
            k = c if c in emp else ("N:" + chave_nome(r["contratado"]))
            if k not in emp:
                k = nome_para_cnpj.get(chave_nome(r["contratado"]), "")
                if k not in emp:
                    continue
            e = emp[k]
            e.setdefault("instrumentos", []).append([rotulo if rotulo != "conv" else r.get("tipo", "Convênio"), r["orgao"] or "—", r["valor"] or 0,
                                                     r["numero"], r["processo_sei"], r["vigencia"], r["origem"], re.sub(r"\s+", " ", r["objeto"])[:220]])
    ligar("s5_contratos.json", "Contrato")
    ligar("s5_convenios.json", "conv")

    # 3) lista final (empresas com R$ 20 mil ou mais no período)
    lista = []
    for k, e in emp.items():
        if e["total"] < 20000:
            continue
        rf = empresas_rf.get(e["cnpj"]) or {}
        e["top"].sort(key=lambda x: -x[0])
        inst = e.get("instrumentos", [])
        lista.append({"nome": e["nome"], "cnpj": e["cnpj"], "total": round(e["total"], 2), "pago": round(e["pago"], 2), "executivo": round(e["executivo"], 2),
                      "notas": e["notas"], "anos": {a: round(v, 2) for a, v in e["anos"].items()},
                      "orgaos": dict(sorted(((o, round(v, 2)) for o, v in e["orgaos"].items()), key=lambda x: -x[1])),
                      "modal": dict(sorted(((m, round(v, 2)) for m, v in e["modal"].items()), key=lambda x: -x[1])),
                      "ti": cnpj_ti.get(e["cnpj"], "") or ("frota" if e["frota"] else ("ti" if e["ti_org"] else "")),
                      "ti_org": {o: round(v, 2) for o, v in sorted(e["ti_org"].items(), key=lambda x: -x[1])}, "ti_anos": {a: round(v, 2) for a, v in e["ti_anos"].items()},
                      "ti_modal": {m: round(v, 2) for m, v in sorted(e["ti_modal"].items(), key=lambda x: -x[1])}, "frota": round(e["frota"], 2), "cnae": rf.get("cnae_fiscal_descricao", ""), "municipio": f'{rf.get("municipio", "")}/{rf.get("uf", "")}' if rf else "",
                      "abertura": rf.get("data_inicio_atividade", ""), "contratos": sum(1 for i in inst if i[0] == "Contrato"),
                      "convenios": sum(1 for i in inst if i[0] != "Contrato"), "valor_instrumentos": round(sum(i[2] for i in inst), 2),
                      "instrumentos": inst[:40], "top": e["top"][:25], "cubo": [[a, o, m, t, round(v, 2)] for (a, o, m, t), v in e["cubo"].items()]})
    lista.sort(key=lambda x: -x["total"])
    meta = {"coletado_em": json.loads((FONTE / "s5_contratos.json").read_text(encoding="utf-8"))["meta"]["coletado_em"], "anos": ANOS,
            "notas": resumo["notas"], "notas_abertas": sum(1 for _, _, d, _ in notas if d),
            "por_tipo": {k: round(v, 2) for k, v in resumo["por_tipo"].items()},
            "por_tipo_ano": {k: {a: round(x, 2) for a, x in v.items()} for k, v in resumo["por_tipo_ano"].items()},
            "empresas": len(lista), "empresas_total": len(emp),
            "tema": {f"{k[0]}|{'outros' if k[1] else 'executivo'}": round(v, 2) for k, v in resumo.get("tema", {}).items()}}
    (FONTE / "s6_empresas_estado.json").write_text(json.dumps({"meta": meta, "empresas": lista}, ensure_ascii=False), encoding="utf-8")
    with open(AQUI / "empresas_estado.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["empresa", "cnpj", "empenhado 2023-2026", "pago", "notas", "órgãos", "modalidades", "contratos", "convênios/termos", "tecnologia", "atividade (CNAE)", "município", "abertura"])
        for e in lista:
            w.writerow([e["nome"], e["cnpj"], e["total"], e["pago"], e["notas"], " | ".join(f"{o} {v:.0f}" for o, v in e["orgaos"].items()),
                        " | ".join(f"{m} {v:.0f}" for m, v in e["modal"].items()), e["contratos"], e["convenios"], e["ti"], e["cnae"], e["municipio"], e["abertura"]])

    nomes = tec["nomes"] if "nomes" in tec else {}
    # página: cubo compacto (índices de órgão e modalidade) em vez dos dicionários por órgão/modalidade/ano
    ORG = sorted({c[1] for e in lista for c in e["cubo"]})
    MOD = sorted({c[2] for e in lista for c in e["cubo"]})
    io, im = {o: i for i, o in enumerate(ORG)}, {m: i for i, m in enumerate(MOD)}
    leve = [{"nome": e["nome"], "cnpj": e["cnpj"], "pago": e["pago"], "notas": e["notas"], "contratos": e["contratos"], "convenios": e["convenios"],
             "valor_instrumentos": e["valor_instrumentos"], "cnae": e["cnae"], "municipio": e["municipio"], "abertura": e["abertura"],
             "c": [[a - 2023, io[o], im[m], t, round(v)] for a, o, m, t, v in e["cubo"]],
             "top": [x[:8] + [im[x[8]], x[9]] for x in e["top"][:12]], "instrumentos": e["instrumentos"][:12]}
            for e in lista if e["total"] >= 50000]
    meta["ORG"], meta["MOD"] = ORG, MOD
    meta["empresas_na_pagina"] = len(leve)
    pagina = {"meta": meta, "empresas": leve, "nomes": nomes, "links": {"portal": PORTAL + "/despesa/despesa-estadual", "detalhe": PORTAL + "/Despesa/notas-de-empenho/detalhes"},
              "coletado_em": meta["coletado_em"], "tabelas": {}}
    payload = json.dumps(pagina, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fonte = base64.b64encode((RAIZ / "vendor" / "fontes" / "inter-var.woff2").read_bytes()).decode()
    css_fonte = f"@font-face{{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:block;src:url(data:font/woff2;base64,{fonte}) format('woff2')}}"
    base = RAIZ / "convenios" / "src"
    h = (AQUI / "src" / "empresas.html").read_text(encoding="utf-8")
    h = (h.replace("/*__BASE_CSS__*/", (base / "_base.css").read_text(encoding="utf-8"))
          .replace("/*__BASE_JS__*/", (base / "_base.js").read_text(encoding="utf-8"))
          .replace("/*__FONTES__*/", css_fonte, 1)
          .replace("/*__DADOS_EMP__*/null", payload))
    (RAIZ / "esbocos" / "empresas.html").write_text(h, encoding="utf-8")
    (RAIZ / "site" / "empresas.html").write_text(h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1), encoding="utf-8")
    print(f"site/empresas.html {round(len(h) / 1024)} KB · {len(lista)} empresas (de {len(emp)}) · {meta['notas_abertas']} de {meta['notas']} notas com detalhe")
    print("por tipo de credor (R$ bi):", {k: round(v / 1e9, 2) for k, v in meta["por_tipo"].items()})


if __name__ == "__main__":
    main()
