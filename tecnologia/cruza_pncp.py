"""Contratações de tecnologia publicadas no PNCP pelo Poder Executivo de RO (2023–2026), cruzadas com o mapa da aba Tecnologia.

Uso: python3 tecnologia/cruza_pncp.py   (depois de coleta_pncp.py e build_tecnologia.py)
Lê dados-fonte/s5_pncp_estado.json (todas as contratações da esfera estadual no PNCP) e dados-fonte/s5_tecnologia.json.
Grava dados-fonte/s5_pncp_ti.json: cada contratação de TI do Executivo com órgão (pelo prefixo do processo SEI), tipo de TI,
modalidade, amparo legal, valor (homologado; se não houver, estimado), situação, link do PNCP e se o processo já está no mapa
(contrato ou convênio publicado no Portal da Transparência) ou é novo.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(AQUI))
from classificar import classificar, sigla_de_nome, sem_acento  # noqa: E402
from build_tecnologia import PREFIXO_FIXO, UG_EMPENHO  # noqa: E402

DPE = "01072076000195"  # Defensoria: o PNCP põe no Executivo, mas é órgão autônomo
UNIDADE = {"FUNDO ESTADUAL DE SAUDE": "SESAU", "FUNDO ESP MOD E REAPARELHAM DA POL MILIT": "PM", "FUNDO ESTADUAL DE SEGURANCA PUBLICA": "SESDEC",
           "FUNDO EST.DE PREV.F.E R.DE ENTORPECENTES": "SESDEC", "SUPERINTENDENCIA E TEC DA INF COMUNICACAO": "SETIC",
           "FUNDACAO ROND.A.DES.A.CIENT.TECNOL.PESQ": "FAPERO", "INSTITUTO EST DE DES. DA ED. PROFISSIONAL": "IDEP",
           "EMPRESA EST DE ASSIS TECNICA E EXT RURAL": "EMATER", "SECRETARIA ESTADO DESENVOLVIMENTO ECONOM": "SEDEC",
           "SUPERINTENDENCIA ESTADUAL DE DESENVOLVIMENTO ECONOMICO": "SEDEC"}
# contratações que o filtro de palavras pega mas não são TI (revisadas)
NAO_TI_PNCP = re.compile(r"TOMOGRAF|RESSONANCIA|RAIO.?X|ULTRASSOM|MONITOR MULTIPARAMETRICO|DESFIBRILADOR|ELETROCARDIO|"
                         r"AR.CONDICIONADO|CLIMATIZ|VEICULO|VIATURA|PNEU|COMBUSTIVEL|GENEROS ALIMENT|MEDICAMENT|OBRA|REFORMA|"
                         r"MOBILIARIO|CADEIRA|MESA |FARDAMENTO|UNIFORME|PASSAGE|HOSPEDAGEM|EVENTO|BUFFET|COFFEE")


# termos de procedimento de compra que o classificador leria como "sistema" de TI: saem antes de classificar
PROCEDIMENTO = re.compile(r"SISTEMA DE REGISTRO DE PRECOS?|\(?\bSRP\b\)?|(POR MEIO DE |ATRAVES DE |VIA )?SISTEMA ELETRONICO( DE (COMPRAS|LICITAC\w*|CREDENCIAMENTO))?|"
                          r"SISTEMA (COMPRASNET|COMPRAS\.?GOV|DE COMPRAS|LICITACOES-?E)|SISTEMA UNICO DE SAUDE|SISTEMA (ESTADUAL|PUBLICO) DE SAUDE|SISTEMA PRISIONAL|"
                          r"SISTEMA SOCIOEDUCATIVO|SISTEMA DE (ENSINO|SAUDE)")


# fora sempre (o objeto cita sistema/software de passagem; revisado à mão em 13/10/2026)
EXCLUI_FORTE = re.compile(r"HEMODINAMICA|ORTESE|PROTESE|\bOPME\b|REAGENTE|CONDICIONADO(R|RES) DE AR|UNIDADES MOVEIS|ONIBUS|FURGO|CENSO PREVIDENCIARIO|"
                          r"PROCEDIMENTOS? CIRURGIC|ARMAS? DE FOGO|PISTOLA|\bMUNICA|LIBRAS|INTERPRETE|TRADUCAO|INSTITUICOES FINANCEIRAS|SISTEMA DE DEFESA|GNSS|TOPOGRAF|TEODOLITO|TESTES E PROTOCOLOS|DIAGNOSTICOS? ESPECIALIZ|EXAMES? (LABORATORI|DE IMAGEM|CLINIC)|MATERIA(L|IS) (MEDICO|HOSPITALAR|DE CONSUMO HOSPITALAR)|GASES MEDICINAIS")
# segurança eletrônica, câmeras e inspeção: tecnologia operacional (a mesma regra das câmeras na aba)
OPERACIONAL = re.compile(r"RASTREAMENTO|CONTROLE DE ACESSO|BIOMETRI|SEGURANCA ELETRONICA|ALARME|MONITORAMENTO DE IMAGENS|VIDEOMONITORAMENTO|CFTV|BODY ?SCANNER|INSPECAO CORPORAL|CAMERAS?")


def processo_norm(p):
    """Processo SEI só com dígitos (AAAA.NNNNNN/AAAA-DD = 16 dígitos), para casar formatos diferentes."""
    return re.sub(r"\D", "", p or "")


def main():
    pn = json.loads((FONTE / "s5_pncp_estado.json").read_text(encoding="utf-8"))
    tec = json.loads((FONTE / "s5_tecnologia.json").read_text(encoding="utf-8"))
    contratos = json.loads((FONTE / "s5_contratos.json").read_text(encoding="utf-8"))["dados"]
    pref = defaultdict(Counter)
    for r in contratos:
        s = sigla_de_nome(r["orgao"])
        m = re.match(r"(\d{4})\.", r["processo_sei"] or "")
        if s and m and not s.startswith("OUTRO"):
            pref[m[1]][s] += 1
    prefixo = {p: c.most_common(1)[0][0] for p, c in pref.items()}
    prefixo.update(PREFIXO_FIXO)
    no_mapa = {processo_norm(r["processo"]): r for r in tec["registros"] if r.get("processo")}
    notas_proc = defaultdict(float)  # processo SEI citado na modalidade/histórico das notas de TI -> empenhado
    for x in tec["fornecedores"]:
        for p in re.findall(r"\d{4}\.\d{3}\.?\d{3}/\d{4}-\d{2}", f"{x[11]} {x[7]}"):
            notas_proc[processo_norm(p)] += x[4]

    out, excl = [], Counter()
    for x in pn["dados"]:
        if x["orgaoEntidade"]["poderId"] != "E" or x["orgaoEntidade"]["cnpj"] == DPE:
            continue
        obj = x.get("objetoCompra") or ""
        cat, termo = classificar(PROCEDIMENTO.sub(" ", sem_acento(obj)))
        if not cat or cat == "frota" or re.search(r"GESTAO DE FROTA|AUTOGESTAO|ABASTECIMENTO|MANUTENCAO (PREVENTIVA E CORRETIVA )?DE VEICULO", sem_acento(obj)):
            continue
        if EXCLUI_FORTE.search(sem_acento(obj)):
            excl["forte: " + EXCLUI_FORTE.search(sem_acento(obj))[0]] += 1
            continue
        so = sem_acento(obj)
        # curso, inscrição, capacitação: não é contrato de TI (mesmo se o tema for IA ou BI)
        if re.search(r"\bCURSOS?\b|INSCRIC|MASTERCLASS|SEMINARIO|CONGRESSO|CAPACITACAO|TREINAMENTO DE|PALESTRA|WORKSHOP", so) and not re.search(r"LICENC|AQUISICAO DE (SOFTWARE|EQUIPAMENTO)|SUBSCRICAO|IMPLANTACAO", so):
            excl["curso ou capacitação"] += 1
            continue
        if cat in ("sistemas", "suporte") and OPERACIONAL.search(so) and not re.search(r"SOFTWARE DE GESTAO|SISTEMA (INFORMATIZADO|DE GESTAO)", so):
            cat, termo = "operacional", OPERACIONAL.search(so)[0]
        # "sistema de ..." sozinho não prova TI: precisa de outra palavra de tecnologia no objeto
        if termo.strip() in ("SISTEMA DE", "PORTAL DE", "PORTAL DO") and not re.search(r"AVALIACAO EDUCACIONAL|RESPOSTA AO ITEM|FUNCIONALIDADE|SISTEMA DE GERENCIAMENTO|FERRAMENTA DE PESQUISA|BANCO DE PRECOS|SOFTWARE|INFORMATIZ|\bWEB\b|DIGITA|TECNOLOGI|DADOS|PLATAFORMA|APLICATIVO|NUVEM|LICENC|\bTIC\b|ONLINE|ON-LINE|ELETRONICO|COMPUTA|VIDEOCONFER", so):
            excl["só 'sistema de'"] += 1
            continue
        if cat in ("sistemas", "suporte") and OPERACIONAL.search(sem_acento(obj)) and not re.search(r"SOFTWARE DE GESTAO|SISTEMA (INFORMATIZADO|DE GESTAO)", sem_acento(obj)):
            cat, termo = "operacional", OPERACIONAL.search(sem_acento(obj))[0]
        if NAO_TI_PNCP.search(sem_acento(obj)) and not re.search(r"SOFTWARE|SISTEMA|LICENC|TECNOLOGIA DA INFORMACAO|DATA ?CENTER", sem_acento(obj)):
            excl[NAO_TI_PNCP.search(sem_acento(obj))[0]] += 1
            continue
        dig = re.sub(r"\D", "", x.get("processo") or "")
        s = prefixo.get(dig[:4]) if len(dig) >= 15 else None
        if not s:
            un = sem_acento(re.sub(r"^ERO\s*-\s*", "", x["unidadeOrgao"]["nomeUnidade"]))
            s = next((v for k, v in UNIDADE.items() if k in un), None) or sigla_de_nome(x["unidadeOrgao"]["nomeUnidade"]) or sigla_de_nome(x["orgaoEntidade"]["razaoSocial"]) or "NI"
        if s.startswith("OUTRO"):
            s = "SUPEL" if "COMPRAS" in sem_acento(x["unidadeOrgao"]["nomeUnidade"]) else "NI"
        s = UG_EMPENHO.get(s, s)
        hom, est = x.get("valorTotalHomologado"), x.get("valorTotalEstimado")
        pnorm = processo_norm(x.get("processo"))
        reg = no_mapa.get(pnorm)
        ctrl = x["numeroControlePNCP"]  # CNPJ-1-SEQ/ANO
        mc = re.match(r"(\d{14})-1-(\d+)/(\d{4})", ctrl)
        link = f"https://pncp.gov.br/app/editais/{mc[1]}/{mc[3]}/{int(mc[2])}" if mc else "https://pncp.gov.br"
        out.append({"sigla": s, "ano": x["anoCompra"], "modalidade": x["modalidadeNome"].replace(" - Eletrônico", "").replace(" - Eletrônica", "").replace(" - Presencial", ""),
                    "srp": bool(x.get("srp")) or bool(re.search(r"REGISTRO DE PRECOS?|\bSRP\b|\bATA DE REGISTRO", sem_acento(obj))), "amparo": (x.get("amparoLegal") or {}).get("nome", ""), "processo": x.get("processo") or "",
                    "numero": f'{x["numeroCompra"]}/{x["anoCompra"]}', "objeto": re.sub(r"\s+", " ", obj).strip(), "cat": cat, "termo": termo,
                    "valor": hom if hom else (est or 0), "valor_tipo": "homologado" if hom else "estimado", "situacao": x.get("situacaoCompraNome", ""),
                    "data": (x.get("dataPublicacaoPncp") or "")[:10], "unidade": x["unidadeOrgao"]["nomeUnidade"], "link": link, "controle": ctrl,
                    "no_mapa": bool(reg), "contrato_mapa": f'{reg["instrumento"]} {reg["numero"]}' if reg else "", "empenhado_ref": notas_proc.get(pnorm, 0.0)})
    # a mesma compra publicada duas vezes (pela SUPEL e pelo órgão): fica a do órgão
    vistos, unicos = {}, []
    for r in sorted(out, key=lambda r: r["sigla"].startswith(("OUTRO", "SUPEL"))):
        k = (round(r["valor"]), sem_acento(r["objeto"])[:120])
        if k in vistos:
            vistos[k]["duplicada_em"] = r["controle"]
            continue
        vistos[k] = r
        unicos.append(r)
    out = unicos
    out.sort(key=lambda r: -r["valor"])
    (FONTE / "s5_pncp_ti.json").write_text(json.dumps({"fonte": "PNCP · API de consulta de contratações (esfera estadual, UF RO)", "coletado_em": pn["coletado_em"],
                                                      "regra": "Executivo sem Defensoria; objeto classificado como TI pela mesma regra dos contratos (classificar.py), frota fora",
                                                      "dados": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    fmt = lambda v: f"R$ {v / 1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    print(f"{len(out)} contratações de TI no PNCP · {fmt(sum(r['valor'] for r in out))} · excluídas por termo não TI: {sum(excl.values())} {excl.most_common(8)}")
    for k in ("modalidade", "ano", "cat", "situacao", "valor_tipo"):
        c = defaultdict(lambda: [0, 0.0])
        for r in out:
            c[r[k]][0] += 1
            c[r[k]][1] += r["valor"]
        print(k, {a: (n, fmt(v)) for a, (n, v) in sorted(c.items(), key=lambda t: -t[1][1])})
    novo = [r for r in out if not r["no_mapa"]]
    print(f"já no mapa (mesmo processo SEI): {len(out) - len(novo)} · novas: {len(novo)} · {fmt(sum(r['valor'] for r in novo))}")
    c = defaultdict(lambda: [0, 0.0])
    for r in novo:
        c[r["sigla"]][0] += 1
        c[r["sigla"]][1] += r["valor"]
    print("novas por órgão:", {a: (n, fmt(v)) for a, (n, v) in sorted(c.items(), key=lambda t: -t[1][1])[:20]})


if __name__ == "__main__":
    main()
