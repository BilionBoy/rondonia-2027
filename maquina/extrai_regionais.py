"""Secretarias Executivas Regionais (SER I a X e COOREG): custo de 2026 e projeção 2027-2030, agregado.

Uso: <python com openpyxl> maquina/extrai_regionais.py
Lê   estado-ro 2/quadro-servidores/Execucao_Secretarias_Regionais_2026_v04_2026-11-13.xlsx (SIGEF, UG 110009 SUGESP,
     posição 12/11/2026, montada pela equipe de transição) e grava dados-fonte/s8_regionais_2026.json.
Nomes, CPF e telefones (arquivo RESTRITO e PDFs das listas) não são lidos.
"""
import json
from pathlib import Path

import openpyxl

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
ARQ = RAIZ.parent / "quadro-servidores" / "Execucao_Secretarias_Regionais_2026_v04_2026-11-13.xlsx"
SAIDA = RAIZ / "dados-fonte" / "s8_regionais_2026.json"


def linhas(ws, desde=3):
    return [r for r in list(ws.iter_rows(values_only=True))[desde:] if any(c is not None for c in r)]


def r2(v):
    return round(v, 2) if isinstance(v, float) else v


def main():
    wb = openpyxl.load_workbook(ARQ, read_only=True, data_only=True)
    unidades = {}
    for r in linhas(wb["Resumo"]):
        if r[0] and r[0] != "TOTAL" and r[2]:
            unidades[r[0]] = {"codigo": r[0], "nome": r[1], "sede": r[2], "servidores": r[3], "com_cds": r[4],
                              "cds_mes": r2(r[5]), "veic_proprios": r[6], "veic_locados": r[7], "pago_ate_12_11": r2(r[11]),
                              "cds_jan_out": r2(r[12]), "projecao_nov_dez": r2(r[13]), "total_2026": r2(r[14]),
                              "saldo_empenho": r2(r[16]), "tipos": {}, "projecao": {}}
        if r[0] == "TOTAL":
            total = {"servidores": r[3], "com_cds": r[4], "cds_mes": r2(r[5]), "veic_proprios": r[6], "veic_locados": r[7],
                     "pago_ate_12_11": r2(r[11]), "cds_jan_out": r2(r[12]), "projecao_nov_dez": r2(r[13]),
                     "total_2026": r2(r[14]), "saldo_empenho": r2(r[16])}
    for r in linhas(wb["Estrutura"]):
        if r[0] in unidades:
            unidades[r[0]].update(polo=r[3], titular=r[4], municipios=[m.strip() for m in str(r[5]).split(",")])
    for r in linhas(wb["Pessoal"]):
        if r[0] in unidades and isinstance(r[2], (int, float)) and r[9]:
            unidades[r[0]]["vinculos"] = {"cedido_federal": r[2], "cedido_municipal": r[3] + r[4], "comissionado": r[5],
                                          "efetivo_estadual": r[6] + r[7], "outro": r[8]}
    cab_cds = None
    for r in linhas(wb["Pessoal"], 0):
        if r[0] == "Código" and r[2] == "CDS-15":
            cab_cds = r
        elif cab_cds and r[0] in unidades:
            unidades[r[0]]["cds"] = {cab_cds[i]: r[i] for i in range(2, 17) if r[i]}
        elif cab_cds and r[0] == "Valor":
            valor_simbolo = {cab_cds[i]: r[i] for i in range(2, 17)}

    tipos_total, atual = {}, None
    for r in linhas(wb["Custo_por_Tipo"]):
        if r[0] in unidades:
            atual = r[0]
        if r[2] and r[2] not in ("Tipo de custo", "Total", "Total da regional") and isinstance(r[3], (int, float)):
            item = {"mensal": r2(r[3]), "ate_12_11": r2(r[4]), "projecao": r2(r[5]), "total_2026": r2(r[6]), "natureza": r[7]}
            if r[0] in unidades:
                unidades[r[0]]["tipos"][r[2]] = item
            elif r[0] is None and atual is None:
                pass
            elif r[0] is None:
                tipos_total[r[2]] = item
    # a última tabela (sem código) é o total das onze unidades; as linhas sem código antes dela pertencem à unidade anterior
    tipos_total = {}
    bloco = [r for r in linhas(wb["Custo_por_Tipo"])]
    i = max(k for k, r in enumerate(bloco) if r[2] == "Tipo de custo")
    for r in bloco[i + 1:]:
        if r[2] and r[2] != "Total" and isinstance(r[3], (int, float)):
            tipos_total[r[2]] = {"mensal": r2(r[3]), "ate_12_11": r2(r[4]), "projecao": r2(r[5]), "total_2026": r2(r[6])}

    proj_total, anos = {}, ["2027", "2028", "2029", "2030"]
    bloco = linhas(wb["Projecao_2027_2030"])
    i = max(k for k, r in enumerate(bloco) if r[2] == "Tipo de custo")
    for r in bloco[i + 1:]:
        if r[2] and isinstance(r[3], (int, float)):
            proj_total[r[2]] = {"2026": r2(r[3]), "base": r2(r[4]), **{a: r2(r[5 + k]) for k, a in enumerate(anos)}, "total": r2(r[9])}
    for r in bloco:
        if r[0] in unidades and r[2] and isinstance(r[5], (int, float)):
            unidades[r[0]]["projecao"][r[2]] = {a: r2(r[5 + k]) for k, a in enumerate(anos)}

    mensal = {}
    for r in linhas(wb["Mensal"]):
        if r[2] and isinstance(r[3], (int, float)):
            m = mensal.setdefault(r[2], [0.0] * 12)
            for k in range(12):
                m[k] += r[3 + k] or 0
    mensal = {k: [round(x, 2) for x in v] for k, v in mensal.items()}

    premissas = [[c for c in r if c] for r in wb["Premissas"].iter_rows(values_only=True) if any(r)]
    out = {"meta": {"fonte": "Execução das Secretarias Executivas Regionais 2026, v04 de 13/11/2026 (SIGEF, UG 110009 SUGESP, "
                             "posição 12/11/2026; listas de pessoal e de veículos das regionais)",
                    "base_legal": "LC nº 965/2017, arts. 87, II, e 90, parágrafo único (LC nº 1.215/2023); Decreto nº 31.814/2026; Lei nº 1.808/2007",
                    "ipca": {"2027": 0.0522, "2028": 0.049, "2029": 0.04, "2030": 0.04}, "premissas": premissas},
           "total": total, "tipos": tipos_total, "projecao": proj_total, "mensal": mensal, "valor_simbolo": valor_simbolo,
           "unidades": list(unidades.values())}
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(unidades)} unidades; total 2026 R$ {total['total_2026']:,.2f}; 2027-2030 R$ {proj_total['Total']['total']:,.2f}")


if __name__ == "__main__":
    main()
