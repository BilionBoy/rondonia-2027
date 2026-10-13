"""Classifica os contratos do Estado: de qual órgão é, se é de tecnologia e de que tipo.

Uso: python3 tecnologia/classificar.py   (depois de python3 coleta_contratos.py)
Lê dados-fonte/s5_contratos.json. Grava:
  - dados-fonte/s5_contratos_ti.json: os contratos de tecnologia, com órgão (sigla), categoria e situação;
  - tecnologia/revisao.csv: a lista para conferência humana (categoria, regra que casou, objeto).

Regras:
  - Órgão: pelo nome que o portal dá; se vier vazio, pelo prefixo do processo SEI (cada órgão tem o seu, ex. 0029 = SEDUC).
  - Tecnologia: pelo objeto do contrato, com regras por categoria (CATEGORIAS, na ordem; a primeira que casar vence)
    e uma lista de exclusões (NAO_TI) para o que tem palavra de TI mas não é TI (ex.: "sistema de ar-condicionado").
  - Correções manuais conferidas na revisão: tecnologia/ajustes.json ({"numero|processo": "categoria" ou "fora"}).
  - Vigente: vigência igual ou posterior à data de corte (DATA_CORTE).
"""
import csv
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
DATA_CORTE = "2026-10-12"
ANO_FOCO = 2023  # foco da análise: contratos cadastrados de 2023 em diante, mais os anteriores ainda vigentes


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "") if unicodedata.category(c) != "Mn").upper()


# --- órgão -------------------------------------------------------------------------------------------
# (sigla, nome curto, regex sobre o nome sem acento). A ordem importa: o mais específico primeiro.
ORGAOS = [
    ("SETIC", "Superintendência Estadual de Tecnologia da Informação e Comunicação", r"TECNOLOGIA DA INFORMACAO|\bSETIC\b"),
    ("AGEVISA", "Agência Estadual de Vigilância em Saúde", r"VIGILANCIA EM SAUDE|AGEVISA"),
    ("FHEMERON", "Fundação de Hematologia e Hemoterapia", r"HEMATOLOGIA|FHEMERON"),
    ("IESPRO", "Instituto Estadual de Educação em Saúde Pública", r"EDUCACAO EM SAUDE PUBLICA|IESPRO"),
    ("CETAS", "Centro de Educação Técnico-Profissional na Área de Saúde", r"TECNICO.PROFISSIONAL NA AREA DE SAUDE|CETAS"),
    ("SESAU", "Secretaria de Estado da Saúde", r"\bSAUDE\b|SESAU"),
    ("IDEP", "Instituto Estadual de Educação Profissional", r"EDUCACAO PROFISSIONAL|IDEP"),
    ("SEDUC", "Secretaria de Estado da Educação", r"\bEDUCACAO\b|SEDUC"),
    ("POLITEC", "Superintendência de Polícia Técnico-Científica", r"TECNICO.CIENTIFICA|POLITEC"),
    ("PC", "Polícia Civil", r"POLICIA CIVIL|PC-RO"),
    ("PM", "Polícia Militar", r"POLICIA MILITAR|PM-RO|PMILIT"),
    ("CBM", "Corpo de Bombeiros Militar", r"BOMBEIRO|CBMRO"),
    ("SESDEC", "Secretaria de Segurança, Defesa e Cidadania", r"SEGURANCA, DEFESA|SESDEC"),
    ("SEJUS", "Secretaria de Estado de Justiça", r"\bJUSTICA\b|SEJUS"),
    ("FEASE", "Fundação Estadual de Atendimento Socioeducativo", r"SOCIOEDUCATIVO|FEASE"),
    ("DETRAN", "Departamento Estadual de Trânsito", r"TRANSITO|DETRAN"),
    ("DER", "Departamento de Estradas, Rodagens, Infraestrutura e Serviços Públicos", r"ESTRADAS, RODAGENS|\bDER\b"),
    ("SEOSP", "Secretaria de Estado de Obras e Serviços Públicos", r"OBRAS E SERVICOS PUBLICOS|SEOSP"),
    ("SUGESP", "Superintendência de Gestão dos Gastos Públicos Administrativos", r"GASTOS PUBLICOS|SUGESP"),
    ("SUPEL", "Superintendência Estadual de Compras e Licitação", r"COMPRAS E LICITACAO|SUPERINTENDENCIA ESTADUAL DE LICITACAO|SUPEL"),
    ("SEFIN", "Secretaria de Estado de Finanças", r"\bFINANCAS\b|SEFIN"),
    ("COGES", "Contabilidade Geral do Estado", r"CONTABILIDADE GERAL"),
    ("CGE", "Controladoria-Geral do Estado", r"CONTROLADORIA"),
    ("PGE", "Procuradoria-Geral do Estado", r"PROCURADORIA"),
    ("SEPOG", "Secretaria de Estado de Planejamento, Orçamento e Gestão", r"PLANEJAMENTO, ORCAMENTO|SEPOG"),
    ("SEGEP", "Superintendência Estadual de Gestão de Pessoas", r"GESTAO DE PESSOAS|SEGEP"),
    ("SEPAT", "Secretaria de Estado de Patrimônio e Regularização Fundiária", r"PATRIMONIO E REGULARIZACAO|SEPAT"),
    ("IPERON", "Instituto de Previdência dos Servidores Públicos", r"PREVIDENCIA|IPERON"),
    ("SEAS", "Secretaria de Estado de Assistência e Desenvolvimento Social", r"ASSISTENCIA E DESENVOLVIMENTO SOCIAL|\bSEAS\b"),
    ("EMATER", "Entidade Autárquica de Assistência Técnica e Extensão Rural", r"EXTENSAO RURAL|EMATER"),
    ("IDARON", "Agência de Defesa Sanitária Agrosilvopastoril", r"AGROSILVOPASTORIL|IDARON"),
    ("SEAGRI", "Secretaria de Estado da Agricultura", r"AGRICULTURA|SEAGRI"),
    ("SEDAM", "Secretaria de Estado do Desenvolvimento Ambiental", r"DESENVOLVIMENTO AMBIENTAL|SEDAM"),
    ("SEDEC", "Secretaria de Estado do Desenvolvimento Econômico", r"DESENVOLVIMENTO ECONOMICO|SEDEC"),
    ("FIDER", "Fundo de Investimento e Desenvolvimento Industrial", r"DESENVOLVIMENTO INDUSTRIAL"),
    ("SEJUCEL", "Secretaria de Estado da Juventude, Cultura, Esporte e Lazer", r"JUVENTUDE|SEJUCEL"),
    ("FUNCER", "Fundação Cultural do Estado", r"FUNDACAO CULTURAL|FUNCER"),
    ("SETUR", "Superintendência Estadual de Turismo", r"TURISMO|SETUR"),
    ("JUCER", "Junta Comercial do Estado", r"JUNTA COMERCIAL|JUCER"),
    ("IPEM", "Instituto de Pesos e Medidas", r"PESOS E MEDIDAS|IPEM"),
    ("AGERO", "Agência de Regulação dos Serviços Públicos Delegados", r"REGULACAO DOS SERVICOS|AGERO"),
    ("FAPERO", "Fundação de Amparo à Pesquisa", r"AMPARO AO DESENVOLVIMENTO|FAPERO"),
    ("SI", "Superintendência Estadual do Indígena", r"INDIGENA"),
    ("SER", "Superintendência do Estado para Resultados", r"PARA RESULTADOS"),
    ("CASA CIVIL", "Casa Civil", r"CASA CIVIL"),
    ("SECOM", "Secretaria de Estado de Comunicação", r"\bCOMUNICACAO\b|SECOM"),
    ("GOVERNO", "Governo do Estado (sem órgão)", r"GOVERNO DO ESTADO"),
]
NOME_CURTO = {s: n for s, n, _ in ORGAOS}


def sigla_de_nome(nome):
    n = sem_acento(nome)
    if not n.strip():
        return ""
    for sigla, _, rx in ORGAOS:
        if re.search(rx, n):
            return sigla
    return "OUTRO:" + nome


# --- categorias de tecnologia -------------------------------------------------------------------------
# (código, nome, regex sobre o objeto sem acento). A ordem importa: a primeira que casar vence.
CATEGORIAS = [
    ("impressao", "Impressão e reprografia",
     r"OUTSOURCING DE IMPRESS|SERVICOS? DE IMPRESS(AO|OES) (CORPORATIVA|DEPARTAMENTAL|E (DIGITALIZ|COPIA))|REPROGRAFI|LOCACAO DE (EQUIPAMENTOS? |MAQUINAS? )?(MULTIFUNCIONA|IMPRESSORA|COPIADORA)|IMPRESSAO,? COPIA|IMPRESSORAS? MULTIFUNCIONA|SOLUCAO DE IMPRESS|GESTAO DE IMPRESS|CENTRAL DE IMPRESS"),
    ("datacenter", "Datacenter, nuvem e hospedagem",
     r"DATA ?CENTER|COMPUTACAO EM NUVEM|NUVEM|\bCLOUD\b|HOSPEDAGEM (DE|EM) (SITE|SISTEMA|APLICAC|DADOS|SERVIDOR)|COLOCATION|HIPERCONVERG|STORAGE|ARMAZENAMENTO DE DADOS|SERVIDORES? (DE REDE|RACK|BLADE|FISICO)|BACKUP|NUTANIX|VMWARE"),
    ("conectividade", "Links, internet e telecomunicações",
     r"LINKS? (DE |DEDICADO|IP|MPLS|SATELIT)|ACESSO A INTERNET|INTERNET (DEDICADA|BANDA|VIA SATELITE|MOVEL)|SERVICOS? DE INTERNET|BANDA LARGA|TELEFONIA|TELECOMUNICAC|\bVOIP\b|MPLS|SD-?WAN|FIBRA OPTICA|COMUNICACAO DE DADOS|TRANSMISSAO DE DADOS|REDE CORPORATIVA|SATELITAL|SERVICO MOVEL PESSOAL|\bSMP\b|\bSTFC\b|PLANO DE DADOS|CHIPS?\b.{0,30}DADOS|RADIOCOMUNICA|RADIO DIGITAL|TETRA|INFOVIA"),
    ("seguranca", "Segurança da informação",
     r"FIREWALL|FIRE WALL|SEGURANCA DA INFORMACAO|SEGURANCA CIBERNETICA|ANTI ?VIRUS|ANTIMALWARE|ENDPOINT|CERTIFICADOS? DIGITA|CERTIFICACAO DIGITAL|\bSOC\b|\bSIEM\b|WAF\b|PROTECAO DE DADOS|NEXT GENERATION|UTM\b|\bVPN\b|AUTENTICACAO MULTIFATOR"),
    ("licencas", "Licenças de software de mercado",
     r"MICROSOFT|WINDOWS|OFFICE 365|M365|GOOGLE WORKSPACE|ORACLE|\bSAP\b|ADOBE|AUTOCAD|AUTODESK|CORELDRAW|ARCGIS|\bESRI\b|RED ?HAT|ZIMBRA|SUBSCRICAO|SUBSCRICOES|LICENCAS? (DE (USO|SOFTWARE|DIREITO)|PERPETUA|PERMANENTE)|LICENCIAMENTO DE (USO|SOFTWARE)|SOFTWARE DE (ANALISE|ESCRITORIO|DESENHO|EDICAO|MODELAGEM|ENGENHARIA|ESTATIST)|PACOTE OFFICE"),
    ("sistemas", "Sistemas e software de gestão",
     r"SOFTWARE|SISTEMA (DE |INTEGRADO|INFORMATIZADO|WEB|ELETRONICO|DIGITAL|COMPUTACIONAL|ONLINE|ON-LINE|INFORMACOES|GERENCIA)|SOLUCAO (TECNOLOGICA|INTEGRADA|DE TI|DIGITAL|INFORMATIZADA|EM NUVEM|WEB|DE SOFTWARE)|PLATAFORMA (DIGITAL|WEB|TECNOLOGICA|ONLINE|ON-LINE|EDUCACIONAL|DE ENSINO|DE GESTAO|INTEGRADA|DE APRENDIZAGEM|ADAPTATIVA)|APLICATIVO|DESENVOLVIMENTO DE (SISTEMA|SOFTWARE|APLICA|SOLUC)|FABRICA DE SOFTWARE|SUSTENTACAO DE SISTEMA|MANUTENCAO (EVOLUTIVA|CORRETIVA E EVOLUTIVA|DE SISTEMA)|LOCACAO DE (SISTEMA|SOFTWARE|SOLUCAO)|CESSAO DE (DIREITO DE )?USO|\bSAAS\b|\bERP\b|BUSINESS INTELLIGENCE|\bBI\b|BANCO DE DADOS|GESTAO ESCOLAR|AVALIACAO EDUCACIONAL EM LARGA ESCALA|TEORIA DA RESPOSTA AO ITEM|DIARIO (DE CLASSE )?ELETRONICO|PRONTUARIO ELETRONICO|PORTAL (WEB|DE|DO)|ASSINATURA ELETRONICA|INTELIGENCIA ARTIFICIAL|CHATBOT|RPA\b"),
    ("operacional", "Tecnologia operacional: monitoramento, rastreamento e câmeras",
     r"MONITORAMENTO ELETRONICO|TORNOZELEIRA|VIDEOMONITORAMENTO|VIDEO ?MONITORAMENTO|CFTV|CIRCUITO FECHADO|CAMERAS?|RASTREAMENTO|TELEMETRIA|\bGPS\b|CERCAMENTO ELETRONICO|RECONHECIMENTO FACIAL|LEITURA DE PLACAS|\bOCR\b|BODY ?CAM|BLOQUEADOR DE SINAL|DRONES?"),
    ("frota", "Gestão de frota e abastecimento por sistema e cartão",
     r"GESTAO (INFORMATIZADA )?(DE |DA )?FROTA|AUTOGESTAO DE FROTA|ABASTECIMENTO.{0,60}(CARTAO|SISTEMA|INFORMATIZ|MAGNETIC|MICROPROCESS)|(CARTAO|SISTEMA|INFORMATIZ).{0,60}ABASTECIMENTO|MANUTENCAO.{0,40}FROTA.{0,60}(SISTEMA|CARTAO|INFORMATIZ)|(SISTEMA|CARTAO|INFORMATIZ).{0,60}MANUTENCAO.{0,30}(VEICUL|FROTA)"),
    ("equipamentos", "Equipamentos de informática",
     r"COMPUTADOR|MICROCOMPUTADOR|DESKTOP|NOTEBOOK|LAPTOP|CHROMEBOOK|TABLET|ESTACOES? DE TRABALHO|MONITOR(ES)? (DE VIDEO|LED|LCD|AUXILIAR|AUXILIARES)|AQUISICAO DE (\\d+ )?(NOVOS )?MONITORES|HEADSETS?|FONES? DE OUVIDO TIPO HEADSET|IPHONES?|SMARTPHONES?|NOBREAK|NO-BREAK|SWITCH|ROTEADOR|ACCESS POINT|PONTOS? DE ACESSO|TOTEM|SCANNER|EQUIPAMENTOS? DE (INFORMATICA|TI\b|TIC\b|REDE|PROCESSAMENTO DE DADOS)|MATERIA(L|IS) DE (INFORMATICA|TIC|PROCESSAMENTO)|SUPRIMENTOS? DE INFORMATICA|TONER|CARTUCHO|PROJETOR(ES)? MULTIMIDIA|LOUSA DIGITAL|LOUSAS DIGITAIS|PAINEL INTERATIVO|TELA INTERATIVA|KIT(S)? (DE )?ROBOTICA|LABORATORIO(S)? (DE )?(INFORMATICA|ROBOTICA|MAKER)"),
    ("rede", "Rede lógica e cabeamento",
     r"CABEAMENTO ESTRUTURADO|REDE LOGICA|REDES? LOGICAS|REDE SEM FIO|WI-?FI|INFRAESTRUTURA DE REDE|ATIVOS DE REDE"),
    ("suporte", "Suporte técnico e serviços de TI",
     r"SUPORTE TECNICO (EM|DE|A|AOS?) (INFORMATICA|TI\b|TIC\b|USUARIO|SISTEMA|EQUIPAMENTO|MICRO)|SERVICE ?DESK|HELP ?DESK|CENTRAL DE (SERVICOS|ATENDIMENTO) DE TI|MANUTENCAO (PREVENTIVA E CORRETIVA )?(DE|EM) (EQUIPAMENTOS DE )?(INFORMATICA|MICROCOMPUTADOR|COMPUTADORES|IMPRESSORA)|TECNOLOGIA DA INFORMACAO|\bTIC\b|SERVICOS DE TI\b|ASSISTENCIA TECNICA (EM|DE) (INFORMATICA|EQUIPAMENTOS DE TI)|DIGITALIZACAO DE (DOCUMENTOS|ACERVO|PROCESSOS)|GESTAO ELETRONICA DE DOCUMENTOS|\bGED\b"),
]
NOME_CAT = {c: n for c, n, _ in CATEGORIAS}

# Palavras de TI em contrato que não é de TI. Se casar, o contrato sai (a menos que ajustes.json diga o contrário).
NAO_TI = re.compile(
    r"AR[- ]CONDICIONADO|CLIMATIZ|REFRIGERAC|SISTEMA DE (ESGOTO|ABASTECIMENTO DE AGUA|AGUA|DRENAGEM|COMBATE|PREVENCAO|PROTECAO CONTRA|ILUMINACAO|ENERGIA SOLAR|GERACAO|FREIOS|TRATAMENTO|IRRIGACAO|SPDA|AQUECIMENTO|EXAUSTAO|GASES|OXIGENIO|AR COMPRIMIDO|VACUO|HIDRAUL|ELETRIC|SINALIZACAO|SOM\b)|"
    r"SISTEMA DE COTAS|SISTEMA PRISIONAL|SISTEMA SOCIOEDUCATIVO|SISTEMA UNICO DE SAUDE|\bSUS\b.{0,20}SISTEMA|SISTEMA ESTADUAL DE (ENSINO|SAUDE)|"
    r"(?<!MAO DE )\bOBRAS?\b|REFORMA|CONSTRUCAO|PAVIMENTA|EDIFICAC|ENGENHARIA CIVIL|"
    r"GENEROS ALIMENTICIOS|ALIMENTACAO ESCOLAR|MERENDA|MEDICAMENTO|MATERIAL MEDICO|HOSPITALAR|LEITOS?\b|UTI\b|EXAMES?\b|CONSULTAS? MEDIC|"
    r"LOCACAO DE (IMOVEL|VEICULO|ONIBUS)|TRANSPORTE ESCOLAR|PASSAGENS AEREAS|AGENCIAMENTO DE VIAGENS|COMBUSTIVE(L|IS)(?!.{0,80}(CARTAO|SISTEMA|INFORMATIZ))|"
    r"VALE[- ]?(ALIMENTACAO|REFEICAO|TRANSPORTE)|AUXILIO|CARTAO (ALIMENTACAO|REFEICAO|BENEFICIO|VALE)|"
    r"VIGILANCIA (ARMADA|DESARMADA|PATRIMONIAL)|LIMPEZA|CONSERVACAO|COPEIRAGEM|PORTARIA|RECEPCAO|JARDINAGEM|"
    r"CAMERA (FRIA|FRIGORIFICA)|CAMARAS? FRIAS?|CAMERAS? FRIAS?|CAMERA DE (CONSERVACAO|VACINA)|"
    r"GPS.{0,40}(TOPOGRAF|GEODESIC)|ROBOTICA (CIRURGICA|MEDICA)|EQUIPAMENTOS? (MEDICO|HOSPITALAR|ODONTOLOG|LABORATORIA)")
# Mesmo com exclusão, estas categorias ficam (a palavra de exclusão aparece de passagem): ex. "monitoramento de UTI" não, mas "sistema de gestão hospitalar" sim.
FORCA_TI = re.compile(r"SOFTWARE|SISTEMA (INFORMATIZADO|DE GESTAO|INTEGRADO DE GESTAO|WEB)|SOLUCAO TECNOLOGICA|PRONTUARIO ELETRONICO|TECNOLOGIA DA INFORMACAO|DATA ?CENTER|LICENC|LINK DE|FIREWALL|OUTSOURCING DE IMPRESS")


def classificar(objeto):
    o = sem_acento(objeto)
    for cod, _, rx in CATEGORIAS:
        m = re.search(rx, o)
        if m:
            if NAO_TI.search(o) and not FORCA_TI.search(o):
                return None, "excluído: " + NAO_TI.search(o)[0]
            return cod, m[0]
    return None, ""


def chave(r):
    return f"{r['numero']}|{r['processo_sei']}"


def main():
    bruto = json.loads((FONTE / "s5_contratos.json").read_text(encoding="utf-8"))
    dados = bruto["dados"]
    ajustes = json.loads((AQUI / "ajustes.json").read_text(encoding="utf-8")) if (AQUI / "ajustes.json").exists() else {}

    # prefixo do processo SEI -> sigla mais frequente entre os contratos com órgão
    por_prefixo = {}
    for r in dados:
        s = sigla_de_nome(r["orgao"])
        m = re.match(r"(\d{4})\.", r["processo_sei"] or "")
        if s and m and not s.startswith("OUTRO"):
            por_prefixo.setdefault(m[1], Counter())[s] += 1
    prefixo = {p: c.most_common(1)[0][0] for p, c in por_prefixo.items()}

    ti, revisao, excl = [], [], Counter()
    for r in dados:
        s = sigla_de_nome(r["orgao"])
        origem_orgao = "portal"
        if not s:
            m = re.match(r"(\d{4})\.", r["processo_sei"] or "")
            s = prefixo.get(m[1], "") if m else ""
            origem_orgao = "prefixo SEI" if s else "não informado"
            s = s or "NI"
        cat, regra = classificar(r["objeto"])
        aj = ajustes.get(chave(r))
        if aj == "fora":
            cat, regra = None, "ajuste manual: fora"
        elif aj:
            cat, regra = aj, "ajuste manual"
        if regra.startswith("excluído"):
            excl[regra] += 1
        if not cat:
            continue
        vig = r["vigencia_iso"]
        situacao = "vigente" if vig and vig >= DATA_CORTE else ("sem vigência" if not vig else "vencido")
        ti.append({**r, "sigla": s, "orgao_nome": NOME_CURTO.get(s, r["orgao"] or "Não informado"), "orgao_origem": origem_orgao,
                   "categoria": cat, "categoria_nome": NOME_CAT[cat], "regra": regra, "situacao": situacao,
                   "foco": r["ano_consulta"] >= ANO_FOCO or situacao == "vigente"})
        revisao.append([cat, regra, s, r["ano_consulta"], situacao, r["valor"] or 0, r["contratado"], r["cnpj"], r["numero"], r["processo_sei"], r["objeto"]])

    meta = {**{k: bruto["meta"][k] for k in ("fonte", "coletado_em", "consulta")}, "data_corte": DATA_CORTE,
            "regra": "Contrato de tecnologia = objeto casa com uma das categorias e não com a lista de exclusões (tecnologia/classificar.py), com correções manuais em tecnologia/ajustes.json.",
            "categorias": [[c, n] for c, n, _ in CATEGORIAS], "orgaos": {s: n for s, n, _ in ORGAOS}}
    (FONTE / "s5_contratos_ti.json").write_text(json.dumps({"meta": meta, "dados": ti}, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(AQUI / "revisao.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["categoria", "regra", "orgao", "ano", "situacao", "valor", "contratado", "cnpj", "numero", "processo", "objeto"])
        w.writerows(sorted(revisao, key=lambda x: (x[0], -x[5])))

    print("no foco (2023+ ou vigente):", sum(1 for x in ti if x["foco"]))
    print(f"{len(dados)} contratos; {len(ti)} de tecnologia; {sum(1 for x in ti if x['situacao']=='vigente')} vigentes")
    print("por categoria:", Counter(x["categoria"] for x in ti).most_common())
    print("excluídos (top):", excl.most_common(8))
    print("órgão por prefixo SEI:", sum(1 for x in ti if x["orgao_origem"] == "prefixo SEI"), "| não informado:", sum(1 for x in ti if x["sigla"] == "NI"))
    print("órgão não reconhecido:", Counter(x["sigla"] for x in ti if x["sigla"].startswith("OUTRO")).most_common(5))


if __name__ == "__main__":
    main()
