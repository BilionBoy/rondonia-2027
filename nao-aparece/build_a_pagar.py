"""Sexta tela de "O que não aparece": o que fica para pagar em 2027.

Lê fontes oficiais guardadas em dados-fonte/:
  - s3_msc_a_pagar_2026_09.json: MSC de setembro de 2026, contas de empenho ainda não pago;
  - s3_rreo_2026_b4.json: RREO Anexo 7 de 2026, 4º bimestre (restos a pagar de anos anteriores);
  - s3_empenhos_2026.json: notas de empenho de 2026 do Portal da Transparência RO.

Uso: python3 nao-aparece/build_a_pagar.py
Acrescenta "a_pagar" e três tabelas ao dados-fonte/s3_resumo.json e regera esbocos/ e site/
a partir de nao-aparece/src/. O build_s3.py completo chama a_pagar() e chega ao mesmo resultado;
este arquivo existe porque o dado bruto das outras telas não fica no repositório.
"""
import json
from collections import defaultdict

from build_s3 import FONTE, PORTAL_EMPENHO, SICONFI_RREO, ler, mi, reais, renderiza

# Unidades do Portal que não são do Poder Executivo: saem da lista, para bater com a MSC do Executivo.
FORA_DO_EXECUTIVO = {"ALE", "TJ", "FUJU", "MP", "FUNDIMPER", "FRBL", "TCE", "FDI/TC", "DPE", "FUNDEP"}
# Poder e órgão da MSC: os dois primeiros dígitos dizem o Poder.
PODER_MSC = {"10": "Executivo", "20": "Legislativo e Tribunal de Contas", "30": "Judiciário", "50": "Ministério Público", "60": "Defensoria Pública"}
SITUACAO = {"622130100": "empenhado a liquidar (sem entrega)", "622130200": "em liquidação", "622130300": "liquidado a pagar (entregue)"}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def msc():
    m = ler("s3_msc_a_pagar_2026_09.json")
    soma = defaultdict(float)
    linhas = []
    for x in m["dados"]:
        v = x["valor"] * (1 if x["natureza_conta"] == "C" else -1)
        po = x["poder_orgao"] or ""
        soma[(po[:2] == "10", x["conta_contabil"])] += v
        linhas.append([PODER_MSC.get(po[:2], po), po, x["conta_contabil"], SITUACAO[x["conta_contabil"]], x["fonte_recursos"], x.get("funcao") or "", round(v, 2)])
    liq = soma[(True, "622130300")]
    a_liq = soma[(True, "622130100")] + soma[(True, "622130200")]
    linhas.sort(key=lambda r: (r[0] != "Executivo", -r[6]))
    mes = int(m["dados"][0]["mes_referencia"])
    return {"mes": f"{mes:02d}/2026", "mes_extenso": f"{MESES[mes - 1]} de 2026", "liquidado": mi(liq), "a_liquidar": mi(a_liq), "total": mi(liq + a_liq),
            "todos_poderes": mi(sum(soma.values()))}, m["meta"], linhas


def rreo_2026():
    r = ler("s3_rreo_2026_b4.json")
    # colunas do Anexo 7: processados (a, b, c, d, e) e não processados (f, g, h, i, j, k)
    col = {(x["cod_conta"], x["coluna"]): x["valor"] for x in r["dados"] if x["conta"] == "PODER EXECUTIVO" and not x["cod_conta"].endswith("Intra")}
    def v(prefixo, letra):
        return sum(val for (cod, c), val in col.items() if cod.startswith(prefixo) and f"({letra})" in c.replace(" ", ""))
    P, N = "RestosAPagarProcessadosENaoProcessadosLiquidados", "RestosAPagarNaoProcessados"
    a, b, c, d = v(P, "a"), v(P, "b"), v(P, "c"), v(P, "d")
    f, g, i, j = v(N, "f"), v(N, "g"), v(N, "i"), v(N, "j")
    aberto = next(val for (cod, c_), val in col.items() if cod == "SaldoTotal")
    assert abs((a + b + f + g) - (c + d + i + j) - aberto) < 1, "RREO 2026: a conta do saldo não fecha"
    def situacao(coluna):
        for chave, nome in (("Saldo Total", "Saldo total"), ("Saldo", "Saldo"), ("Exercícios Anteriores", "Inscritos em anos anteriores"),
                            ("31 de dezembro", "Inscritos em 31/12/2025"), ("Liquidados", "Liquidados"), ("Pagos", "Pagos"), ("Cancelados", "Cancelados")):
            if chave in coluna:
                return nome
        return coluna
    def tipo(cod):
        return "Total" if cod.startswith("SaldoTotal") else "Não processados (sem entrega)" if cod.startswith(N) else "Processados (entregues)"
    linhas = [[tipo(x["cod_conta"]), situacao(x["coluna"]), x["coluna"], round(x["valor"], 2), x["cod_conta"]]
              for x in r["dados"] if x["conta"] == "PODER EXECUTIVO" and not x["cod_conta"].endswith("Intra")]
    return {"bimestre": 4, "ate": "agosto de 2026", "entrou": mi(a + b + f + g), "inscrito_2025": mi(b + g), "pago": mi(c + i),
            "cancelado": mi(d + j), "aberto": mi(aberto)}, r["meta"], linhas


def portal():
    e = ler("s3_empenhos_2026.json")
    ugs = defaultdict(lambda: {"a_pagar": 0.0, "qtd": 0, "notas": []})
    linhas = []
    for n in e["dados"]:
        ug = n["unidadeGestora"]
        if ug in FORA_DO_EXECUTIVO:
            continue
        emp, pg = reais(n["valorEmpenhado"]), reais(n["valorPago"])
        falta = emp - pg
        if falta < 0.01:
            continue
        u = ugs[ug]; u["a_pagar"] += falta; u["qtd"] += 1
        u["notas"].append([n["numeroEmpenho"], n["dataDocumentoFormatada"], n["credor"], mi(falta), mi(pg), n["linkDetalhes"]])
        if falta >= 1e4:
            linhas.append([ug, n["numeroEmpenho"], n["dataDocumentoFormatada"], n["credor"], round(emp, 2), round(pg, 2), round(falta, 2), n["linkDetalhes"]])
    lista = []
    for ug, u in ugs.items():
        u["notas"].sort(key=lambda x: -x[3])
        lista.append({"ug": ug, "a_pagar": mi(u["a_pagar"]), "qtd": u["qtd"], "notas": u["notas"][:15]})
    lista.sort(key=lambda u: -u["a_pagar"])
    linhas.sort(key=lambda r: -r[6])
    return {"coletado_em": e["meta"]["coletado_em"], "total": mi(sum(u["a_pagar"] for u in ugs.values())), "qtd": sum(u["qtd"] for u in ugs.values()),
            "ugs": lista}, linhas


def a_pagar():
    """Dados da sexta tela e as três tabelas de origem."""
    m, meta_m, lin_m = msc()
    r, meta_r, lin_r = rreo_2026()
    p, lin_p = portal()
    tabelas = {
        "a-pagar-2026": {"id": "a-pagar-2026", "titulo": "Notas de empenho de 2026 do Executivo com saldo a pagar", "curto": "Portal",
                         "fonte": "Portal da Transparência de Rondônia (CGE-RO)", "consulta": "Despesas por Empenho, exercício 2026; notas do Executivo com pelo menos R$ 10 mil empenhados e não pagos",
                         "url": PORTAL_EMPENHO, "coletado_em": p["coletado_em"],
                         "nota": "A pagar = empenhado menos pago na data da coleta. O Portal mostra só as notas visíveis (ver a tela 4).",
                         "colunas": [["Órgão", "t"], ["Nota", "t"], ["Emissão", "d"], ["Credor", "t"], ["Empenhado", "r"], ["Pago", "r"], ["A pagar", "r"], ["Link", "l"]], "linhas": lin_p},
        "rreo-2026": {"id": "rreo-2026", "titulo": "Restos a pagar do Executivo em 2026, até agosto (RREO, 4º bimestre)", "curto": "RREO 2026",
                      "fonte": "Tesouro Nacional · Siconfi", "consulta": "RREO Anexo 7, exercício 2026, 4º bimestre, Rondônia, linhas do Poder Executivo",
                      "url": meta_r["url"], "coletado_em": meta_r["coletado_em"],
                      "nota": "Inscritos em 31/12/2025 = o que 2025 deixou para 2026. Para somar, busque uma situação, como “Pagos” ou “Cancelados”. Saldos são a posição em agosto.",
                      "colunas": [["Tipo", "t"], ["Situação", "t"], ["Coluna do anexo", "t"], ["Valor", "r"], ["Código da conta", "h"]], "linhas": lin_r},
        "msc-a-pagar-2026": {"id": "msc-a-pagar-2026", "titulo": "Empenhos de 2026 ainda não pagos, por Poder e fonte (MSC de setembro)", "curto": "Contabilidade",
                             "fonte": "Tesouro Nacional · Siconfi", "consulta": meta_m["fonte"], "url": meta_m["url"], "coletado_em": meta_m["coletado_em"],
                             "nota": "Saldo no fim de setembro. O número grande da tela soma só as linhas do Executivo.",
                             "colunas": [["Poder", "t"], ["Código do Poder", "t"], ["Conta", "t"], ["Situação", "t"], ["Fonte de recurso", "t"], ["Função", "t"], ["Valor", "r"]], "linhas": lin_m},
    }
    return {"msc": m, "rreo": r, "portal": p, "links": {"rreo": SICONFI_RREO, "empenho": PORTAL_EMPENHO}}, tabelas


def main():
    resumo = ler("s3_resumo.json")
    dados, tabelas = a_pagar()
    resumo["a_pagar"] = dados
    resumo["tabelas"].update(tabelas)
    (FONTE / "s3_resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=1), encoding="utf-8")
    renderiza(resumo)
    m, r, p = dados["msc"], dados["rreo"], dados["portal"]
    print(f"MSC {m['mes']}: Executivo a pagar R$ {m['total']} mi (entregue {m['liquidado']}, sem entrega {m['a_liquidar']}); todos os Poderes {m['todos_poderes']}")
    print(f"RREO 2026 4º bim: entrou {r['entrou']}, pago {r['pago']}, cancelado {r['cancelado']}, aberto {r['aberto']}; 2025 deixou {r['inscrito_2025']}")
    print(f"Portal: {p['qtd']} notas do Executivo com saldo, R$ {p['total']} mi")


if __name__ == "__main__":
    main()
