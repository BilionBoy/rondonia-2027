"""Folha de outubro/2026 do Executivo, agregada (sem matrícula, sem nome): quem são, quantos, onde e quanto custam.

Uso: <python com openpyxl> maquina/extrai_folha.py
Lê   estado-ro 2/quadro-servidores/Relação de Servidores Ativos e Afastados Referência 10-2026 Atualizado.xlsx
     (SEGEP, uma linha por verba; matrícula criptografada) e
     estado-ro 2/quadro-servidores/Servidores Aguardando Aposentadoria Mes Referencia 10-2026.xlsx
Grava dados-fonte/s8_folha_2026_10.json só com totais: nenhuma linha identifica pessoa.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
QUADRO = RAIZ.parent / "quadro-servidores"
FOLHA = QUADRO / "Relação de Servidores Ativos e Afastados Referência 10-2026 Atualizado.xlsx"
APOSENTADORIA = QUADRO / "Servidores Aguardando Aposentadoria Mes Referencia 10-2026.xlsx"
SAIDA = RAIZ / "dados-fonte" / "s8_folha_2026_10.json"

# Vínculo (classificação funcional da SEGEP) agrupado em poucas categorias que se leem de uma vez
GRUPOS = [
    ("inativo", "Aposentados e pensionistas", r"^INATIVO|PENSIONISTA"),
    ("militar", "Militares (PM e Bombeiros)", r"^EFETIVO - MILITAR"),
    ("efetivo", "Efetivos civis", r"^EFETIVO"),
    ("comissionado", "Comissionados sem vínculo", r"^COMISSIONADO SEM VINCULO"),
    ("temporario", "Temporários e CLT", r"^CONTRATO"),
    # comissionado "com vínculo" (federal, municipal, judiciário) vem de outro ente: conta como cedido
    ("cedido", "Cedidos e comissionados de outros entes", r"A DISPOSICAO|DISP\.? ?(DE )?RO|^MUNICIPAL|^ESTADUAL DO|^CEDIDO|^FEDERAL|^COMISSIONADO"),
    ("apoio", "Estagiários, bolsistas e voluntários", r"ESTAGIARIO|BOLSISTA|VOLUNTARIO|CONTRIBUINTE INDIVIDUAL|FUNCAO PUBLICA"),
    ("judicial", "Pagamento por decisão judicial", r"PAGAMENTO JUDICIAL"),
]
VERBA_CDS = re.compile(r"REPRESENTACAO CDS|VENCIMENTO CDS|DIF (DE )?(VENC|REPRESENTACAO|INDENIZACAO).*CDS|DIF VENCIMENTO CDS"
                       r"|INDENIZACAO CDS|COMEX - CDS|SUBSTITUICAO INDENIZACAO CDS")


def sem_acento(s):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").upper().strip()


def grupo(classificacao):
    c = sem_acento(classificacao)
    for chave, _, rx in GRUPOS:
        if re.search(rx, c):
            return chave
    return "outro"


def simbolo(cds):
    m = re.search(r"CDS\s*-?\s*0?(\d+)", sem_acento(cds))
    return f"CDS-{int(m[1]):02d}" if m else None


def numero(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main():
    ws = openpyxl.load_workbook(FOLHA, read_only=True, data_only=True).worksheets[0]
    linhas = ws.iter_rows(values_only=True)
    cab = [sem_acento(c) for c in next(linhas)]
    col = {n: cab.index(n) for n in ("MATRICULA", "SALARIOBRUNTO", "SITUACAO", "CARGO", "CLASSIFICACAOFUNCIONAL", "VERBA",
                                      "TIPOVERBA", "VALORVERBA", "CDS", "UNIDADE", "DEPARTAMENTO")}
    pessoas, verbas = {}, defaultdict(lambda: [0, 0.0])
    for r in linhas:
        m = str(r[col["MATRICULA"]]).strip()
        p = pessoas.get(m)
        if p is None:
            un = str(r[col["UNIDADE"]] or "").strip()
            p = pessoas[m] = {"bruto": numero(r[col["SALARIOBRUNTO"]]), "sit": str(r[col["SITUACAO"]]).strip(),
                              "grupo": grupo(r[col["CLASSIFICACAOFUNCIONAL"]]),
                              "unidade": "" if un in ("", "NULL") else un,
                              "dep": str(r[col["DEPARTAMENTO"]] or "").strip(), "cargo": str(r[col["CARGO"]] or "").strip(),
                              "cds": simbolo(r[col["CDS"]]) if str(r[col["CDS"]]).strip() not in ("", "NULL") else None,
                              "cds_txt": str(r[col["CDS"]]).strip() not in ("", "NULL"), "custo_cds": 0.0, "pro": 0.0, "des": 0.0}
        tipo, valor, verba = str(r[col["TIPOVERBA"]]).strip(), numero(r[col["VALORVERBA"]]), sem_acento(r[col["VERBA"]])
        if tipo == "PRO":
            p["pro"] += valor
            verbas[verba][0] += 1
            verbas[verba][1] += valor
            if VERBA_CDS.search(verba):
                p["custo_cds"] += valor
        elif tipo == "DES":
            p["des"] += valor

    ativos = [p for p in pessoas.values() if p["grupo"] != "inativo"]
    soma = lambda ps, campo="bruto": round(sum(p[campo] for p in ps), 2)  # noqa: E731

    por_grupo = []
    for chave, nome, _ in GRUPOS + [("outro", "Outros vínculos", "")]:
        ps = [p for p in pessoas.values() if p["grupo"] == chave]
        if ps:
            por_grupo.append({"grupo": chave, "nome": nome, "pessoas": len(ps), "bruto": soma(ps),
                              "afastados": sum(p["sit"] == "AFA" for p in ps), "com_cds": sum(p["cds_txt"] for p in ps)})

    unidades = defaultdict(list)
    for p in ativos:
        unidades[p["unidade"] or "SEM UNIDADE"].append(p)
    por_unidade = []
    for un, ps in unidades.items():
        g = Counter(p["grupo"] for p in ps)
        deps = Counter(p["dep"] for p in ps if p["dep"] and p["dep"] != "NULL")
        cargos = Counter(p["cargo"] for p in ps)
        por_unidade.append({
            "unidade": un, "pessoas": len(ps), "bruto": soma(ps), "afastados": sum(p["sit"] == "AFA" for p in ps),
            "com_cds": sum(p["cds_txt"] for p in ps), "custo_cds": soma(ps, "custo_cds"),
            "grupos": {k: {"pessoas": n, "bruto": soma([p for p in ps if p["grupo"] == k])} for k, n in g.items()},
            "departamentos": [{"nome": d, "pessoas": n} for d, n in deps.most_common(25)],
            "cargos": [{"nome": c, "pessoas": n} for c, n in cargos.most_common(10)],
        })
    por_unidade.sort(key=lambda x: -x["bruto"])

    cds = defaultdict(lambda: {"pessoas": 0, "custo_cds": 0.0, "bruto": 0.0, "sem_vinculo": 0})
    for p in pessoas.values():
        if p["cds_txt"]:
            c = cds[p["cds"] or "sem símbolo"]
            c["pessoas"] += 1
            c["custo_cds"] += p["custo_cds"]
            c["bruto"] += p["bruto"]
            c["sem_vinculo"] += p["grupo"] == "comissionado"
    cds = [{"simbolo": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}}
           for k, v in sorted(cds.items(), key=lambda x: (x[0] == "sem símbolo", x[0]))]

    faixas = [(0, 3000), (3000, 6000), (6000, 10000), (10000, 20000), (20000, 30000), (30000, 46367), (46367, 1e9)]
    por_faixa = [{"de": a, "ate": b if b < 1e9 else None,
                  "pessoas": sum(a <= p["bruto"] < b for p in ativos),
                  "bruto": round(sum(p["bruto"] for p in ativos if a <= p["bruto"] < b), 2)} for a, b in faixas]

    # Aguardando aposentadoria: a lista traz a matrícula real; o MD5 dela é a matrícula criptografada da folha, o que dá órgão,
    # cargo e vínculo. Daqui só saem totais.
    import hashlib
    from datetime import date
    ws = openpyxl.load_workbook(APOSENTADORIA, read_only=True, data_only=True).worksheets[0]
    ap = {}
    for r in list(ws.iter_rows(values_only=True))[1:]:
        if r[0]:
            ap[str(r[0]).strip()] = r
    ref = date(2026, 10, 31)
    tempo, por_ano, por_un, por_cargo, ap_grupo = Counter(), defaultdict(lambda: [0, 0.0]), defaultdict(lambda: [0, 0.0]), Counter(), Counter()
    meses_l, custo_acum, achados, sem_data = [], 0.0, 0, 0
    for m, r in ap.items():
        ini, bruto = r[1], numero(r[5])
        meses = (ref.year - ini.year) * 12 + (ref.month - ini.month) if ini else None
        tempo["até 6 meses" if meses is not None and meses <= 6 else "7 a 12 meses" if meses is not None and meses <= 12
              else "1 a 2 anos" if meses is not None and meses <= 24 else "mais de 2 anos" if meses is not None else "sem data"] += 1
        if ini:
            por_ano[ini.year][0] += 1
            por_ano[ini.year][1] += bruto
            meses_l.append(meses)
            custo_acum += bruto * max(meses, 0) * 13 / 12   # estimativa: salário de hoje × meses afastado, com 13º
        else:
            sem_data += 1
        p = pessoas.get(hashlib.md5(m.encode()).hexdigest().upper())
        if p:
            achados += 1
            por_un[p["unidade"] or "SEM UNIDADE"][0] += 1
            por_un[p["unidade"] or "SEM UNIDADE"][1] += bruto
            por_cargo[p["cargo"]] += 1
            ap_grupo[p["grupo"]] += 1
        else:
            por_un["Não achado na folha de outubro"][0] += 1
            por_un["Não achado na folha de outubro"][1] += bruto
    meses_l.sort()
    inicios = [r[1] for r in ap.values() if r[1]]
    aposentadoria = {"pessoas": len(ap), "bruto_mes": round(sum(numero(r[5]) for r in ap.values()), 2),
                     "afastados": sum(str(r[4]).strip() == "AFA" for r in ap.values()),
                     "tempo": dict(tempo), "achados_na_folha": achados, "sem_data": sem_data,
                     "mais_antigo": min(inicios).date().isoformat() if inicios else None,
                     "mediana_meses": meses_l[len(meses_l) // 2] if meses_l else None,
                     "custo_acumulado_estimado": round(custo_acum, 2),
                     "por_ano_inicio": [{"ano": a, "pessoas": n, "bruto_mes": round(v, 2)} for a, (n, v) in sorted(por_ano.items())],
                     "por_unidade": [{"unidade": u, "pessoas": n, "bruto_mes": round(v, 2)} for u, (n, v) in sorted(por_un.items(), key=lambda x: -x[1][0])],
                     "por_cargo": [{"cargo": c, "pessoas": n} for c, n in por_cargo.most_common(15)],
                     "por_grupo": dict(ap_grupo)}

    out = {
        "meta": {"fonte": "SEGEP, Relação de Servidores Ativos e Afastados, referência 10/2026 (versão Atualizado, com unidade e departamento)",
                 "aposentadoria": "SEGEP, Servidores Aguardando Aposentadoria, referência 10/2026",
                 "regra": "Uma pessoa por matrícula; bruto = salário bruto da matrícula; custo do CDS = verbas de representação, "
                          "vencimento, diferença e indenização de CDS. Sem encargos patronais."},
        "total": {"matriculas": len(pessoas), "bruto": soma(pessoas.values()), "descontos": soma(pessoas.values(), "des"),
                  "ativos": len(ativos), "bruto_ativos": soma(ativos), "inativos": len(pessoas) - len(ativos),
                  "bruto_inativos": round(soma(pessoas.values()) - soma(ativos), 2),
                  "afastados": sum(p["sit"] == "AFA" for p in pessoas.values()),
                  "com_cds": sum(p["cds_txt"] for p in pessoas.values()), "custo_cds": soma(pessoas.values(), "custo_cds"),
                  "sem_unidade": len(unidades.get("SEM UNIDADE", [])), "bruto_sem_unidade": soma(unidades.get("SEM UNIDADE", [])),
                  "bruto_difere_proventos": sum(abs(p["bruto"] - p["pro"]) > 1 for p in pessoas.values())},
        "grupos": por_grupo, "unidades": por_unidade, "cds": cds, "faixas": por_faixa,
        "verbas": [{"verba": k, "pessoas": n, "valor": round(v, 2)} for k, (n, v) in sorted(verbas.items(), key=lambda x: -x[1][1])[:40]],
        "aposentadoria": aposentadoria,
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    t = out["total"]
    print(f"{t['matriculas']} matrículas, bruto R$ {t['bruto']:,.2f}; ativos {t['ativos']} (R$ {t['bruto_ativos']:,.0f}); "
          f"CDS {t['com_cds']} (R$ {t['custo_cds']:,.0f}); sem unidade {t['sem_unidade']}; aposentadoria {aposentadoria}")


if __name__ == "__main__":
    main()
