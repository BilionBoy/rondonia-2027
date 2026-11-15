"""Diárias e passagens do DER, 2022 a 2026, agregadas (sem nome, sem CPF).

Uso: <python com openpyxl> maquina/extrai_diarias_der.py
Lê   estado-ro 2/Diarias_Passagens_DER_Mensal_2022_2026_v03_2026-11-14.xlsx (planilha da equipe de transição sobre o relatório
     de pagamentos de diárias do DER, unidade 110025, e o relatório de pagamentos do exercício, natureza 3.3.90.33)
Grava dados-fonte/s8_diarias_der.json só com totais: por mês, por ano, quantos servidores, faixas e concentração.
Conferência: a soma da base de pagamentos tem de bater com o total que a própria planilha mostra no painel (R$ 118.981.956,55).
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import openpyxl

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
PLANILHA = RAIZ.parent / "Diarias_Passagens_DER_Mensal_2022_2026_v03_2026-11-14.xlsx"
SAIDA = RAIZ / "dados-fonte" / "s8_diarias_der.json"
FAIXAS = [(0, 5000), (5000, 15000), (15000, 30000), (30000, 60000), (60000, 100000), (100000, 1e12)]


def linhas(ws, cab):
    it = ws.iter_rows(values_only=True)
    for r in it:
        if r and cab in [str(x).strip() for x in r if x is not None]:
            nomes = [str(x).strip() if x is not None else "" for x in r]
            break
    for r in it:
        if any(x is not None for x in r):
            yield dict(zip(nomes, r))


def main():
    wb = openpyxl.load_workbook(PLANILHA, read_only=True, data_only=True)
    # pagamentos de diárias: uma linha por ordem bancária a um servidor
    mes = defaultdict(lambda: {"valor": 0.0, "pagamentos": 0, "servidores": set(), "maior": 0.0})
    ano_serv = defaultdict(lambda: defaultdict(float))
    serv_anos = defaultdict(set)
    total = 0.0
    for r in linhas(wb["Base Diárias"], "Beneficiário"):
        try:
            a, m, v = int(r["Ano"]), int(r["Mês"]), float(r["Valor pago"] or 0)
        except (TypeError, ValueError):
            continue
        if v <= 0:
            continue
        chave = f"{r['CPF']}|{str(r['Beneficiário']).strip()}"   # só para contar pessoas; não sai do script
        x = mes[(a, m)]
        x["valor"] += v
        x["pagamentos"] += 1
        x["servidores"].add(chave)
        ano_serv[a][chave] += v
        serv_anos[chave].add(a)
        total += v
    for (a, m), x in mes.items():
        pass
    # maior valor recebido por um servidor no mês (soma dos pagamentos do mês), sem nome
    serv_mes = defaultdict(float)
    for r in linhas(wb["Base Diárias"], "Beneficiário"):
        try:
            a, m, v = int(r["Ano"]), int(r["Mês"]), float(r["Valor pago"] or 0)
        except (TypeError, ValueError):
            continue
        if v > 0:
            serv_mes[(a, m, f"{r['CPF']}|{str(r['Beneficiário']).strip()}")] += v
    for (a, m, _), v in serv_mes.items():
        mes[(a, m)]["maior"] = max(mes[(a, m)]["maior"], v)

    passagens = defaultdict(float)
    for r in linhas(wb["Base Passagens"], "Valor pago no mês"):
        try:
            passagens[(int(r["Ano"]), int(r["Mês"]))] += float(r["Valor pago no mês"] or 0)
        except (TypeError, ValueError):
            continue

    anos = sorted({a for a, _ in mes})
    por_ano = {}
    for a in anos:
        vs = sorted(ano_serv[a].values(), reverse=True)
        n = len(vs)
        dez = max(1, round(n * .1))
        por_ano[a] = {
            "diarias": round(sum(vs), 2), "passagens": round(sum(v for (aa, _), v in passagens.items() if aa == a), 2),
            "pagamentos": sum(mes[(a, m)]["pagamentos"] for m in range(1, 13)), "servidores": n,
            "media_servidor": round(sum(vs) / n, 2) if n else 0, "maior_servidor": round(vs[0], 2) if vs else 0,
            "top10_pct": round(100 * sum(vs[:dez]) / sum(vs), 1) if vs else 0, "top10_n": dez,
            "acima_100mil": sum(v >= 100000 for v in vs), "acima_60mil": sum(v >= 60000 for v in vs),
            "faixas": [{"de": lo, "ate": hi if hi < 1e12 else None, "servidores": sum(lo <= v < hi for v in vs),
                        "valor": round(sum(v for v in vs if lo <= v < hi), 2)} for lo, hi in FAIXAS],
            "maiores": [round(v, 2) for v in vs[:10]],
            "mensal": [{"mes": m, "diarias": round(mes[(a, m)]["valor"], 2), "pagamentos": mes[(a, m)]["pagamentos"],
                        "servidores": len(mes[(a, m)]["servidores"]), "maior": round(mes[(a, m)]["maior"], 2),
                        "passagens": round(passagens.get((a, m), 0), 2)} for m in range(1, 13)],
        }
    out = {
        "meta": {"fonte": "Planilha da equipe de transição sobre os relatórios do DER (pagamentos de diárias; pagamentos do exercício, natureza 3.3.90.33), unidade 110025",
                 "arquivo": PLANILHA.name, "posicao": "2026 até 10/11/2026", "gerado": "sem nome nem CPF: só totais"},
        "total": {"diarias": round(total, 2), "passagens": round(sum(passagens.values()), 2), "servidores": len(serv_anos),
                  "todos_os_anos": sum(len(x) == len(anos) for x in serv_anos.values())},
        "anos": por_ano,
    }
    SAIDA.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"diárias R$ {total:,.2f} (planilha: 118.981.956,55); passagens R$ {out['total']['passagens']:,.2f}; servidores {len(serv_anos)}")
    for a, x in por_ano.items():
        print(a, f"R$ {x['diarias']/1e6:.2f} mi · {x['servidores']} servidores · média {x['media_servidor']:,.0f} · maior {x['maior_servidor']:,.0f} · top10% {x['top10_pct']}% · ≥100 mil {x['acima_100mil']}")


if __name__ == "__main__":
    main()
