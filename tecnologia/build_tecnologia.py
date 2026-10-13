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
from classificar import CATEGORIAS, DATA_CORTE, NAO_TI, NOME_CURTO, classificar, sem_acento, sigla_de_nome  # noqa: E402

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
    "transito-veiculos": "Trânsito e veículos", "transporte-escolar": "Transporte escolar (sistema)", "parceria-ufmg-brtec": "Parceria UFMG/BR TEC (Projeto PAI)", "seguranca-publica": "Segurança pública", "prisional-monitoramento": "Monitoramento eletrônico de presos",
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
              "Idaron": "IDARON", "FUMRESPOM": "PM", "FITHA": "DER", "FUPEN": "SEJUS", "FUNDEC": "SEJUS", "FRBL": "SEDAM", "FEDEC": "SEJUCEL",
              "FEAS": "SEAS", "FECOEP": "SEAS", "FUNEDCA": "SEAS", "FEDIPI": "SEAS", "FUNEDM": "SEAS", "FUNPRECAP": "IPERON",
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
    """Contratos (revisão em revisao/R_*.json) e convênios/termos (revisão em convenios_ti.json), no mesmo formato."""
    bruto = json.loads((FONTE / "s5_contratos.json").read_text(encoding="utf-8"))
    conv = json.loads((FONTE / "s5_convenios.json").read_text(encoding="utf-8")) if (FONTE / "s5_convenios.json").exists() else {"dados": []}
    dec_conv = {x["id"]: x for x in json.loads((AQUI / "convenios_ti.json").read_text(encoding="utf-8"))} if (AQUI / "convenios_ti.json").exists() else {}
    pref = defaultdict(Counter)
    for r in bruto["dados"] + conv["dados"]:
        s = sigla_de_nome(r["orgao"])
        m = re.search(r"(\d{4})\.\s*\d", r["processo_sei"] or "")
        if s and m and not s.startswith("OUTRO"):
            pref[m[1]][s] += 1
    prefixo = {p: c.most_common(1)[0][0] for p, c in pref.items()}
    prefixo.update(PREFIXO_FIXO)
    regs, vistos = [], set()
    fontes = [(bruto["dados"], revisoes(), lambda r: "Contrato", PORTAL + "/contratos"),
              (conv["dados"], dec_conv, lambda r: r.get("tipo", "Convênio"), PORTAL + "/convenios")]
    for dados, dec, instrumento, link_padrao in fontes:
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
            regs.append({"id": k, "instrumento": instrumento(r), "sigla": s, "ano": r["ano_consulta"], "numero": r["numero"], "processo": r["processo_sei"],
                         "assinatura": r["assinatura"], "vigencia": r["vigencia"], "vigencia_iso": vig, "situacao": situacao,
                         "contratado": r["contratado"], "cnpj": r["cnpj"], "valor": r["valor"] or 0, "origem": r["origem"],
                         "aditivo": r["tem_aditivo"], "objeto": re.sub(r"\s+", " ", r["objeto"]).strip(), "cat": cat, "funcao": fun,
                         "produto": d.get("produto") or "", "nota": d.get("nota") or "", "link": r["detalhe"] or link_padrao,
                         "rescisao": bool(re.search(r"RESCIS|DISTRAT", r["numero"] + " " + r["objeto"], re.I)),
                         "conferir": VALOR_A_CONFERIR.get(k, "")})
    regs += parcerias()
    return regs, bruto["meta"]


def parcerias():
    """Instrumentos que não estão nas listas de contratos nem de convênios do portal (só no empenho): acordos com a UFMG/FCO e a BR TEC.
    Valor = soma empenhada (o valor global do acordo não é publicado no portal)."""
    arq = FONTE / "s5_parceria_ufmg_brtec.json"
    if not arq.exists():
        return []
    grupos = defaultdict(list)
    for n in json.loads(arq.read_text(encoding="utf-8"))["notas"]:
        if n["unidadeGestora"] != "SEDUC":
            continue        # o estudo EVEF da SEFIN é consultoria, não tecnologia
        mod, h = n["detalhe"].get("Modalidade licitatória", ""), n["detalhe"].get("Histórico", "")
        transcolar = "INEXIG" in mod.upper() or "Transcolar" in h or "COOPERAÇÃO TÉCNICA" in h.upper()
        grupos[(n["parceiro"], transcolar)].append(n)
    out = []
    for (parceiro, transcolar), ns in grupos.items():
        cnpj = re.sub(r"\D", "", ns[0]["detalhe"].get("CPF/CNPJ do credor", ""))
        datas = sorted(n["dataDocumento"][:10] for n in ns)
        proc = "0029.495160/2021-40" if transcolar else "0029.043399/2024-81"
        out.append({"id": f"parceria|{parceiro}|{proc}", "instrumento": "Cooperação técnica" if transcolar else "Acordo de Parceria",
                    "sigla": "SEDUC", "ano": int(datas[-1][:4]), "numero": "Cooperação técnica (inexigibilidade)" if transcolar else "Acordo de Parceria (Marco Legal de CT&I)",
                    "processo": proc, "assinatura": "/".join(reversed(datas[0].split("-"))), "vigencia": "", "vigencia_iso": "",
                    "situacao": "vencido" if transcolar else "vigente", "contratado": ns[0]["credor"], "cnpj": cnpj,
                    "valor": sum(valor(n["valorEmpenhado"]) for n in ns), "origem": ns[0]["detalhe"].get("Modalidade licitatória", ""), "aditivo": "",
                    "objeto": ("Cooperação técnica para desenvolvimento de tecnologia, produto e serviço para o transporte escolar rural (Sistema Transcolar Rural). "
                               if transcolar else "Acordo de Parceria SEDUC × UFMG (Fundação Christiano Ottoni) e BR TEC. O portal corta o histórico; objeto e plano de trabalho no processo SEI. "
                               "Segundo o Dhiogo, inclui o sistema \"Projeto PAI\" (cerca de R$ 19 mi). ")
                              + f"Valor = soma de {len(ns)} notas de empenho ({datas[0][:4]}–{datas[-1][:4]}); não aparece nas listas de contratos e convênios do portal.",
                    "cat": "sistemas", "funcao": "transporte-escolar" if transcolar else "parceria-ufmg-brtec", "produto": "Transcolar Rural" if transcolar else "Projeto PAI (a confirmar)",
                    "nota": "achado pelo empenho", "link": PORTAL + "/despesa/despesa-estadual", "rescisao": False, "conferir": ""})
    return out


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


PARCEIROS_CNPJ = {"18218909000186": "Fundação Christiano Ottoni (UFMG): cooperação Transcolar Rural (0029.495160/2021-40) e Acordo de Parceria com a SEDUC (0029.043399/2024-81)",
                  "15555941000169": "BR TEC: Acordo de Parceria com a SEDUC (0029.043399/2024-81); estudo EVEF na SEFIN"}
# Atividade principal (CNAE) que conta como empresa de tecnologia
CNAE_TI = re.compile(r"^(62|63|61|5820|5829|9511|4651|4751|2621|2622|2631|2632|8020|7733)")
NAO_TI_NOTA = re.compile(r"FOLHA DE PAGAMENTO|ENERGIA ELETRICA|FORNECIMENTO DE ENERGIA|AR[- ]?CONDICIONADO|LIMPEZA|CONSERVACAO|ALIMENTACAO|HOSPEDAGEM DE|COMBUSTIVE|ENERGIA SOLAR|FOTOVOLTAIC|BALISTIC|MATERIAL PENSO|MEDICAMENT|DIARIAS|PASSAGENS|VIGILANCIA ARMADA|OBRA"
                         r"|TOMOGRAF|RADIODIAGN|DIAGNOSE|RESSONANC|IMAGEM|AUTOMACAO LABORATORIAL|REAGENTE|CROMATOGRAF|ESPECTROMETR|LABORATORI"
                         r"|VIATURA|VEICULO|CONDICIONADORES|CLIMATIZ|CIRURGIA|PISO NACIONAL|ENFERMAGEM|EVENTO|MATERIAL ELETRIC|SISTEMA DE DEFESA AGROPEC"
                         r"|HOSPITAL|PACIENTE|EXAME|CONSULTA MEDICA|UTI\b|LEITO|ODONTO", re.I)
# eletrodomésticos, móveis, cursos e viagens vendidos por empresas com CNAE de informática (revisão de 13/10/2026).
# Só valem quando a nota não cita equipamento claramente de TI (ex.: "tablets para distribuição gratuita" continua TI).
NAO_TI_NOTA2 = re.compile(r"ARES[- ]?CONDICIONADOS?|CONDICIONADOR|CENTRA(L|IS) DE AR|SPLIT|FRIGOBAR|BEBEDOURO|GELADEIRA|REFRIGERADOR|MICRO-?ONDAS|FOGAO|ARMARIO|MOBILIARIO|MOBILIA\b|CADEIRA|MESAS?\b|MAQUINA DE LAVAR|LAVADORA"
                         r"|CAFETEIRA|ELETRODOMEST|UMIDIFICADOR|ESTERILIZADOR|PURIFICADOR|VENTILADOR|DISTRIBUICAO GRATUITA|TELEVISOR|SMART ?TV|\bTV\b"
                         r"|\bCURSOS?\b|INSCRIC|MASTERCLASS|CAPACITACAO|ESTAGI|RECURSOS HUMANOS|PASSAGE(M|NS) AERE|PASSAGEM|AGENCIAMENTO", re.I)
TI_FORTE = re.compile(r"TABLETS?|TABLETES|NOTEBOOK|COMPUTADOR|MONITOR(ES)?\b|SOFTWARE|ROBOTICA|VIDEO ?WALL|SERVIDOR(ES)? (DE REDE|RACK)|SWITCH|IMPRESSORA|TONER|CHROMEBOOK|LICENC")


def nao_ti_nota(h):
    return bool(NAO_TI_NOTA.search(h) or (NAO_TI_NOTA2.search(h) and not TI_FORTE.search(h)))
CREDOR_NAO_EMPRESA = re.compile(r"CREDORES NACIONAIS|DEPARTAMENTO ESTADUAL|SECRETARIA|FUNDO |PREFEITURA|MUNICIPIO|SEM CPF|PESSOA FISICA/JURIDICA", re.I)


def nota_ti(hist, cnae, parceria):
    """Nota de outro elemento conta como tecnologia se o histórico é de TI, ou a empresa é de TI e o histórico não é de outra coisa."""
    h = sem_acento(hist)
    if parceria:
        return True
    if nao_ti_nota(h):
        return False
    cat, regra = classificar(hist)
    if cat and cat != "frota":
        return True
    # só pelo CNAE da empresa: o histórico não pode ser compra genérica de material (empresas de informática também vendem eletrodomésticos e móveis)
    if re.search(r"MATERIA(L|IS) (PERMANENTES?|DE CONSUMO|DE EXPEDIENTE)|BENS PERMANENTES|ITENS PERMANENTES", h) and not re.search(
            r"TECNOLOGI|INFORMATI|TABLET|\bABLET|LENOVO|DELL\b|COMPUTA|NOTEBOOK|SOFTWARE|DIGITAL|ELETRONIC|ASSISTIVA|TOKEN|PERIFERIC|IMPRESSOR|TONER|MONITOR|VIDEO ?WALL|ROBOTICA", h):
        return False
    return bool(CNAE_TI.match(str(cnae or ""))) and not NAO_TI.search(h)


def modalidade(txt):
    t = sem_acento(txt)
    for rx, nome in ((r"DISPENS", "Dispensa"), (r"INEXIG", "Inexigibilidade"), (r"ADES|CARONA|ATA DE REGISTRO|\bARP\b", "Adesão a ata"),
                     (r"PREGAO|PREGÃO", "Pregão"), (r"CONCORR", "Concorrência"), (r"CREDENC|CHAMAMENTO", "Credenciamento ou chamamento"),
                     (r"NAO APLIC|N.O APLIC", "Não aplicável (parceria, convênio, termo)"), (r"CONVITE|TOMADA", "Convite ou tomada de preços"), (r"SUPRIMENTO", "Suprimento de fundos"),
                     (r"^\s*OUTROS", "Outros (o portal não detalha)")):
        if re.search(rx, t):
            return nome
    return "Não informada" if not t.strip() else "Outra"


ELEMENTO_NOME = {"33903900": "outros serviços (39)", "33903000": "material de consumo (30)", "44905200": "equipamentos (52)", "44903900": "outros serviços, investimento",
                 "33903700": "locação de mão de obra (37)", "33903500": "consultoria (35)", "44903000": "material, investimento", "33913900": "serviços intraorçamentários"}


# Gestoras de frota (sistema + cartão de abastecimento e manutenção). Entram com TODOS os empenhos, de todos os órgãos,
# marcadas como frota: o valor inclui o combustível e as peças.
FROTA_CREDOR = re.compile(r"UZZIPAY|PRIME CONSULTORIA E ASSESSORIA|TICKET SOLUC|TICKET GESTAO|TRIVALE|NEO CONSULTORIA E ADMIN|LINK CARD ADMIN|MAXXCARD|VALECARD|GOOD ?CARD|POLICARD", re.I)


def detalhes_todos():
    d = {}
    for arq, campo in (("s5_varredura.json", "detalhes"), ("s5_detalhes_tudo.json", "detalhes"), ("s5_empenhos_fornecedores.json", "detalhes")):
        p = FONTE / arq
        if p.exists():
            d.update(json.loads(p.read_text(encoding="utf-8"))[campo])
    return d


# régua mais rígida para notas avulsas da varredura geral (credor ainda desconhecido)
GERAL_NAO = re.compile(r"APOSTILA|DEVOLUC|ESGOTAMENTO|SANEAMENTO|REPASSE|VIGILANCIA|ORTOPED|BOLSAS|CAMINHAO|CARROCERIA|ONIBUS|OBRA|REAJUSTE DO CONTRATO|"
                       r"MATERIAL DIDATICO|LIVRO|COPA |CAMPEONATO|EMENDA PARLAMENTAR|MEDICO|HOSPITALAR|CIRURG|CONSIGNACAO")
GERAL_CREDOR_NAO = re.compile(r"CONSELHO|ESCOLA|MINISTERIO|SECRET|CONSORCIO|CONSTRU|ENGENHARIA|ASSOCIA|MUNICIPIO|PREFEITURA|FUNDACAO")


def nota_ti_geral(credor, hist):
    h, c = sem_acento(hist), sem_acento(credor)
    if GERAL_NAO.search(h) or GERAL_CREDOR_NAO.search(c) or nao_ti_nota(h):
        return False
    cat, _ = classificar(hist)
    return cat in ("sistemas", "licencas", "datacenter", "conectividade", "seguranca", "impressao", "equipamentos", "rede", "suporte")


def tira_reempenhos(out):
    """Reempenho: o portal mantém a nota original com o valor cheio e cria outra para o mesmo gasto (ex.: ALE × ESYWORLD 2026,
    R$ 10,66 mi empenhados em 11/08 e reempenhados em 08/09). Quando há reempenho, a nota original passa a contar só o que foi pago dela.
    Original = a nota citada no histórico (AAAANE000000) ou, sem número, a nota não paga do mesmo órgão e credor com o mesmo texto."""
    numero = {}
    for ano in (2021, 2022, 2023, 2024, 2025, 2026):
        p = FONTE / f"s3_empenhos_{ano}.json"
        if p.exists():
            for n in json.loads(p.read_text(encoding="utf-8"))["dados"]:
                numero[n["linkDetalhes"]] = (UG_EMPENHO.get(n["unidadeGestora"], n["unidadeGestora"]), n["numeroEmpenho"])
    por_num = {numero[x[9]]: x for x in out if x[9] in numero}
    ajustadas = []
    for x in out:
        if not re.match(r"\s*RE-?EMPENHO", x[7], re.I):
            continue
        citadas = [por_num.get((x[1], ne)) for ne in re.findall(r"\d{4}NE\d{6}", x[7].upper())]
        originais = [y for y in citadas if y and y is not x]
        if not originais:
            corpo = sem_acento(re.sub(r"^\s*RE-?EMPENHO\s*(PARA|DE|DA|DO)?\s*", "", x[7], flags=re.I))[:40]
            originais = [y for y in out if y is not x and y[1] == x[1] and (y[3] or y[2]) == (x[3] or x[2]) and y[5] == 0 and y[4] > 0
                         and not re.match(r"\s*RE-?EMPENHO", y[7], re.I) and corpo and corpo in sem_acento(y[7])]
        for y in originais:
            if y[4] > y[5]:
                ajustadas.append((y[1], y[2], y[4] - y[5]))
                y[4] = y[5]
                y[7] = "[reempenhada: conta só o pago] " + y[7]
    return ajustadas


def fornecedores(regs):
    """Notas pagas a fornecedores de tecnologia: elemento 40 + qualquer outro elemento (s5_empenhos_fornecedores.json).
    Todos os Poderes, com a mesma regra (a tela soma só o Executivo, a menos que se marque "incluir outros Poderes");
    empresas de frota (sistema + cartão, valor com combustível) ficam de fora."""
    so = lambda x: re.sub(r"\D", "", x or "")
    frota = {so(r["cnpj"]) for r in regs if r["cat"] == "frota"} - {so(r["cnpj"]) for r in regs if r["cat"] != "frota"}
    linhas = []
    arq40 = FONTE / "s5_empenhos_tic.json"
    if arq40.exists():
        for n in json.loads(arq40.read_text(encoding="utf-8"))["dados"]:
            d = n.get("detalhe") or {}
            linhas.append((n, d, "elemento 40 (TIC)", ""))
    vistos = {n["linkDetalhes"] for n, *_ in linhas}
    arq = FONTE / "s5_empenhos_fornecedores.json"
    if arq.exists():
        for n in json.loads(arq.read_text(encoding="utf-8"))["notas"]:
            if n["linkDetalhes"] not in vistos:
                vistos.add(n["linkDetalhes"])
                linhas.append((n, n["detalhe"], "outro elemento", n.get("parceria", "")))
    arq = FONTE / "s5_varredura.json"
    if arq.exists():
        v = json.loads(arq.read_text(encoding="utf-8"))
        for n in v["notas"]:
            d = v["detalhes"].get(n["linkDetalhes"])
            if d and n["linkDetalhes"] not in vistos:
                vistos.add(n["linkDetalhes"])
                linhas.append((n, d, "outro elemento: " + ELEMENTO_NOME.get(n.get("elemento"), n.get("elemento", "")), ""))
    det = detalhes_todos()
    # notas de empresas a partir de R$ 20 mil, de qualquer elemento (s5_detalhes_tudo.json): passam pela mesma regra de tecnologia
    p = FONTE / "s5_detalhes_tudo.json"
    if p.exists():
        tudo = json.loads(p.read_text(encoding="utf-8"))["detalhes"]
        for ano in (2023, 2024, 2025, 2026):
            q = FONTE / f"s3_empenhos_{ano}.json"
            if not q.exists():
                continue
            for n in json.loads(q.read_text(encoding="utf-8"))["dados"]:
                d = tudo.get(n["linkDetalhes"])
                if d and n["linkDetalhes"] not in vistos:
                    vistos.add(n["linkDetalhes"])
                    linhas.append(({**n, "ano": ano}, d, "outro elemento: varredura geral", ""))
    # frota: todos os empenhos das gestoras de frota, de todos os órgãos (fora o que já entrou)
    for ano in (2023, 2024, 2025, 2026):
        p = FONTE / f"s3_empenhos_{ano}.json"
        if not p.exists():
            continue
        for n in json.loads(p.read_text(encoding="utf-8"))["dados"]:
            if FROTA_CREDOR.search(n["credor"]) and n["linkDetalhes"] not in vistos:
                vistos.add(n["linkDetalhes"])
                linhas.append(({**n, "ano": ano}, det.get(n["linkDetalhes"]) or {}, "frota (sistema e cartão)", ""))
    empresas = json.loads((FONTE / "s5_empresas.json").read_text(encoding="utf-8")) if (FONTE / "s5_empresas.json").exists() else {}
    out = []
    for n, d, origem, parceria in linhas:
        ug = UG_EMPENHO.get(n["unidadeGestora"], n["unidadeGestora"])
        c = so(d.get("CPF/CNPJ do credor", ""))
        if FROTA_CREDOR.search(n["credor"]):
            origem = "frota (sistema e cartão)"
        doc = d.get("CPF/CNPJ do credor", "")
        suprimento = "SUPRIMENTO" in sem_acento(d.get("Modalidade licitatória", ""))
        if re.search(r"DIARIAS", sem_acento(n["credor"])) or ("*" in doc and not suprimento):
            continue    # diárias e pessoa física (CPF mascarado) que não seja suprimento de fundos: não entram
        if suprimento:  # cartão corporativo de servidor: entra agrupado, com o nome do servidor no histórico
            h = sem_acento(d.get("Histórico", ""))
            if valor(n["valorEmpenhado"]) <= 0 or not (nota_ti(d.get("Histórico", ""), None, "") or re.search(r"COTIC|\bCTI\b|\bGTI\b|SETIC|TECNOLOGIA|INFORMATICA|INFORMACAO E COMUNICACAO", h)):
                continue
            out.append([n["ano"], UG_EMPENHO.get(n["unidadeGestora"], n["unidadeGestora"]), "SUPRIMENTOS DE FUNDOS (cartão corporativo de servidores)", "",
                        valor(n["valorEmpenhado"]), valor(n["valorPago"]), "suprimento de fundos", f'{n["credor"].strip()} (servidor): ' + d.get("Histórico", ""),
                        n["dataDocumentoFormatada"], n["linkDetalhes"], "", d.get("Modalidade licitatória", ""), "Suprimento de fundos"])
            continue
        if c in frota and origem != "frota (sistema e cartão)":
            continue
        if origem not in ("elemento 40 (TIC)", "frota (sistema e cartão)") and CREDOR_NAO_EMPRESA.search(sem_acento(n["credor"])):
            continue
        if origem == "outro elemento: varredura geral":
            if not nota_ti_geral(n["credor"], d.get("Histórico", "")):
                continue
        elif origem not in ("elemento 40 (TIC)", "frota (sistema e cartão)") and not nota_ti(d.get("Histórico", ""), (empresas.get(c) or {}).get("cnae_fiscal"), parceria or PARCEIROS_CNPJ.get(c, "")):
            continue
        if not parceria and c in PARCEIROS_CNPJ:
            parceria = PARCEIROS_CNPJ[c]
        out.append([n["ano"], ug, n["credor"], c, valor(n["valorEmpenhado"]), valor(n["valorPago"]), origem, d.get("Histórico", ""),
                    n["dataDocumentoFormatada"], n["linkDetalhes"], parceria, d.get("Modalidade licitatória", ""), modalidade(d.get("Modalidade licitatória", ""))])
    aj = tira_reempenhos(out)
    if aj:
        print(f"reempenhos: {len(aj)} notas originais passam a contar só o pago (−R$ {sum(v for *_, v in aj) / 1e6:.2f} mi)", aj[:6])
    return out


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
    forn = fornecedores(regs)
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
              "pago_fornecedores": {a: sum(x[4] for x in forn if x[0] == a and not x[6].startswith("frota") and x[1] not in OUTROS_PODERES) for a in (2023, 2024, 2025, 2026)},
              "pago_fornecedores_outros_poderes": {a: {p: sum(x[4] for x in forn if x[0] == a and x[1] == p and not x[6].startswith("frota")) for p in OUTROS_PODERES} for a in (2023, 2024, 2025, 2026)},
              "pago_frota": {a: sum(x[4] for x in forn if x[0] == a and x[6].startswith("frota")) for a in (2023, 2024, 2025, 2026)},
              "pago_fornecedores_fora40": {a: sum(x[4] for x in forn if x[0] == a and x[6].startswith("outro") and x[1] not in OUTROS_PODERES) for a in (2023, 2024, 2025, 2026)},
              "fornecedores_pagos": len({x[3] or x[2] for x in forn if x[1] not in OUTROS_PODERES}),
              "por_modalidade": {m: sum(x[4] for x in forn if x[12] == m and x[1] not in OUTROS_PODERES) for m in sorted({x[12] for x in forn})},
              "pca_itens": len(itens_pca), "pca_valor": sum(i.get("valor_estimado") or 0 for i in itens_pca)}
    dados = {"coletado_em": meta_c["coletado_em"], "data_corte": DATA_CORTE, "ano_foco": ANO_FOCO,
             "links": {"portal": PORTAL + "/contratos", "detalhe": PORTAL + "/Despesa/notas-de-empenho/detalhes"},
             "categorias": [[c, NOME_CAT[c]] for c in ORDEM_CAT], "nomes": nomes, "funcoes": FUNCAO_NOME, "resumo": resumo,
             "registros": regs, "sobreposicoes": sob,
             "empenhos": [[e["ano"], e["ug"], e["credor"], e["cnpj"], e["emp"], e["pago"], e["elemento"], e["item"], e["data"], e["historico"], e["link"]] for e in emps if e["executivo"]],
             "outros_poderes": OUTROS_PODERES,
             "pca": itens_pca, "meta_empenhos": meta_e, "fornecedores": forn}
    (FONTE / "s5_tecnologia.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    # processos de compra de TI publicados no PNCP, cruzados com os contratos (precisa do s5_tecnologia.json recém-gravado)
    pncp = []
    if (FONTE / "s5_pncp_estado.json").exists():
        import cruza_pncp
        cruza_pncp.main()
        pncp = json.loads((FONTE / "s5_pncp_ti.json").read_text(encoding="utf-8"))["dados"]

    # tabelas dos "dados de origem"
    contr = sorted(regs, key=lambda r: (r["sigla"], -r["valor"]))
    tabelas = {
        "tec-contratos": {"id": "tec-contratos", "curto": "Contratos", "titulo": "Contratos e convênios de tecnologia do Governo de Rondônia (2023–2026 e vigentes)",
                          "fonte": "Portal da Transparência de Rondônia (CGE-RO) · Contratos", "url": PORTAL + "/contratos", "coletado_em": meta_c["coletado_em"],
                          "consulta": meta_c["consulta"] + "; classificação de tecnologia revisada contrato a contrato",
                          "nota": "Valor = valor global informado no portal (total previsto na vigência, sem aditivos). Categoria e função são a classificação deste painel.",
                          "colunas": [["Órgão", "t"], ["Instrumento", "t"], ["Categoria", "t"], ["Função", "t"], ["Empresa", "t"], ["CNPJ", "t"], ["Valor global", "r"], ["Ano", "n"],
                                      ["Assinatura", "d"], ["Vigência", "d"], ["Situação", "t"], ["Número", "t"], ["Processo SEI", "t"], ["Modalidade", "t"], ["Aditivo", "t"], ["Objeto", "t"], ["Ficha", "u"]],
                          "linhas": [[r["sigla"], r["instrumento"], NOME_CAT[r["cat"]], r["funcao"], r["contratado"], r["cnpj"], r["valor"], r["ano"], r["assinatura"], r["vigencia"],
                                      r["situacao"], r["numero"], r["processo"], r["origem"], r["aditivo"], r["objeto"], r["link"]] for r in contr]},
    }
    if emps:
        tabelas["tec-empenhos"] = {"id": "tec-empenhos", "curto": "Empenhos TIC", "titulo": "Notas de empenho de TIC (elemento 40), 2023–2026",
                                   "fonte": "Portal da Transparência de Rondônia (CGE-RO) · Despesas por empenho", "url": PORTAL + "/despesa/despesa-estadual",
                                   "coletado_em": meta_e.get("coletado_em", ""), "consulta": "Filtro Elemento de Despesa 33904000 e 44904000, exercícios 2023 a 2026, todos os órgãos",
                                   "nota": "Empenhado = valor final da nota. Pago = valor pago informado pelo portal. Os fundos do Executivo aparecem pelo órgão gestor (ex.: FES = SESAU, FUNESP = SESDEC). Inclui os outros Poderes (coluna Poder), que ficam fora das somas da tela.",
                                   "colunas": [["Ano", "n"], ["Poder", "t"], ["Órgão", "t"], ["Credor", "t"], ["CNPJ", "t"], ["Empenhado", "r"], ["Pago", "r"], ["Elemento", "t"], ["Item de despesa", "t"], ["Data", "d"], ["Histórico", "t"], ["Nota", "l"]],
                                   "linhas": [[e["ano"], "Executivo" if e["executivo"] else OUTROS_PODERES[e["ug"]], e["ug"], e["credor"], e["cnpj"], e["emp"], e["pago"], e["elemento"], e["item"], e["data"], e["historico"], e["link"]] for e in emps]}
    if forn:
        tabelas["tec-pagamentos"] = {"id": "tec-pagamentos", "curto": "Pago às empresas", "titulo": "Empenhos a fornecedores de tecnologia, em qualquer elemento (todos os Poderes, 2023–2026)",
                                     "fonte": "Portal da Transparência de Rondônia (CGE-RO) · Despesas por empenho e detalhe da nota", "url": PORTAL + "/despesa/despesa-estadual",
                                     "coletado_em": meta_e.get("coletado_em", ""), "consulta": "Notas do elemento 40 + notas de outros elementos (a partir de R$ 10 mil) cujo CNPJ é de fornecedor de tecnologia (contrato revisado, elemento 40 ou acordo de parceria)",
                                     "nota": "Inclui pagamentos que não aparecem como contrato ou convênio, como o Acordo de Parceria SEDUC × UFMG (Fundação Christiano Ottoni e BR TEC). Empresas só de frota ficam fora. Notas de outros elementos abaixo de R$ 10 mil não foram abertas.",
                                     "colunas": [["Ano", "n"], ["Órgão", "t"], ["Credor", "t"], ["CNPJ", "t"], ["Empenhado", "r"], ["Pago", "r"], ["Origem", "t"], ["Histórico", "t"], ["Data", "d"], ["Nota", "l"], ["Parceria", "t"], ["Modalidade (texto)", "t"], ["Modalidade", "t"]],
                                     "linhas": forn}
    acordos = json.loads((AQUI / "acordos_ti.json").read_text(encoding="utf-8")) if (AQUI / "acordos_ti.json").exists() else []
    if acordos:
        tabelas["tec-acordos"] = {"id": "tec-acordos", "curto": "Acordos sem custo", "titulo": "Acordos de cooperação de tecnologia sem repasse financeiro (2023–2026): integrações, Infovia, cessão de software",
                                  "fonte": "Portal da Transparência de Rondônia · Acordos que não envolvam transferência de recursos", "url": PORTAL + "/acordos/acordos-sem-repasses-financeiros",
                                  "coletado_em": meta_c["coletado_em"], "consulta": "POST /convenios/filtrartransferenciassemrepasses (AnoProc); acordos de TI escolhidos à mão",
                                  "nota": "Valor zero: são as conexões entre sistemas e órgãos (troca de dados, webservice, Infovia, código-fonte). Insumo para o mapa de integrações do plano diretor.",
                                  "colunas": [["Ano", "n"], ["Órgão", "t"], ["Partícipe", "t"], ["Tipo", "t"], ["Instrumento", "t"], ["Início", "d"], ["Fim", "d"], ["Objeto", "t"]],
                                  "linhas": [[a["ano"], a["orgao"], a["participe"], a["tipo"], a["instrumento"], a["inicio"], a["fim"], a["objeto"]] for a in acordos]}
    if itens_pca:
        tabelas["tec-pca"] = {"id": "tec-pca", "curto": "PCA 2026", "titulo": "Itens de tecnologia nos Planos de Contratações Anuais 2026",
                              "fonte": "Portal da Transparência de Rondônia · Plano de Contratações Anual (portarias no DOE)", "url": PORTAL + "/licitacoes/planoanualdecontratacoes",
                              "coletado_em": meta_c["coletado_em"], "consulta": "PDF do PCA 2026 de cada órgão; itens de TI extraídos página a página",
                              "nota": "Valor estimado conforme o PCA de cada órgão. SEDUC e SESAU não têm PCA 2026 publicado nessa página.",
                              "colunas": [["Órgão", "t"], ["Categoria", "t"], ["Descrição", "t"], ["Quantidade", "n"], ["Unidade", "t"], ["Natureza", "t"], ["Valor estimado", "r"], ["Previsão", "t"], ["Página", "n"]],
                              "linhas": [[i["sigla"], NOME_CAT.get(i.get("categoria"), i.get("categoria", "")), i.get("descricao", ""), i.get("quantidade") or "", i.get("unidade", ""),
                                          i.get("natureza", ""), i.get("valor_estimado") or 0, i.get("previsao", ""), i.get("pagina") or ""] for i in itens_pca]}
    if pncp:
        tabelas["tec-pncp"] = {"id": "tec-pncp", "curto": "Processos no PNCP", "titulo": "Processos de compra de tecnologia publicados no PNCP pelo Poder Executivo (2023–2026)",
                               "fonte": "Portal Nacional de Contratações Públicas (PNCP) · API de consulta de contratações", "url": "https://pncp.gov.br/app/editais?q=&uf=RO",
                               "coletado_em": json.loads((FONTE / "s5_pncp_ti.json").read_text(encoding="utf-8"))["coletado_em"],
                               "consulta": "Contratações da esfera estadual de RO, modalidades dispensa, inexigibilidade, pregão, concorrência e credenciamento; Executivo sem Defensoria; objeto de TI pela mesma regra dos contratos, revisado (cursos, saúde e frota fora)",
                               "nota": "Valor homologado; quando ainda não há, o estimado (teto do registro de preços). É o processo de compra, não o contrato: não se soma aos contratos nem às notas. \"No mapa\" = o mesmo processo SEI já tem contrato ou convênio publicado no Portal da Transparência.",
                               "colunas": [["Órgão", "t"], ["Ano", "n"], ["Modalidade", "t"], ["Registro de preços", "t"], ["Categoria", "t"], ["Objeto", "t"], ["Valor", "r"], ["Tipo de valor", "t"],
                                           ["Situação", "t"], ["Processo SEI", "t"], ["Número", "t"], ["Amparo legal", "t"], ["Publicação", "d"], ["No mapa", "t"], ["PNCP", "u"]],
                               "linhas": [[r["sigla"], r["ano"], r["modalidade"], "sim" if r["srp"] else "não", NOME_CAT.get(r["cat"], r["cat"]), r["objeto"], r["valor"], r["valor_tipo"],
                                           r["situacao"], r["processo"], r["numero"], r["amparo"], r["data"], r["contrato_mapa"] or "não", r["link"]] for r in pncp]}
    dados_pag = {k: dados[k] for k in ("coletado_em", "data_corte", "ano_foco", "links", "categorias", "nomes", "funcoes", "resumo", "registros", "sobreposicoes", "pca")}
    dados_pag["empenhos"] = dados["empenhos"]
    dados_pag["fornecedores"] = forn
    dados_pag["outros_poderes"] = OUTROS_PODERES
    dados_pag["tabelas"] = tabelas
    # [órgão, ano, modalidade, registro de preços, valor, tipo de valor, situação, categoria, objeto, processo, número, link, contrato no mapa, amparo, data]
    dados_pag["pncp"] = [[r["sigla"], r["ano"], r["modalidade"], 1 if r["srp"] else 0, r["valor"], r["valor_tipo"], r["situacao"], r["cat"], r["objeto"], r["processo"],
                          r["numero"], r["link"], r["contrato_mapa"], r["amparo"], r["data"]] for r in pncp]
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
