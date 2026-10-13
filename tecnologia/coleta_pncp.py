"""Todas as contratações publicadas no PNCP por órgãos do Estado de Rondônia (esfera estadual), 2023 a hoje, em todas as
modalidades: pregão, concorrência, dispensa, inexigibilidade, credenciamento, leilão, diálogo competitivo etc.

Por quê: desde a Lei 14.133/2021, toda contratação (inclusive dispensa e inexigibilidade) tem de ser publicada no PNCP,
com objeto, órgão, unidade, modalidade, valor estimado e homologado. É a lista mais completa de "o que o Estado comprou e como".
Uso: python3 tecnologia/coleta_pncp.py   Grava dados-fonte/pncp/AAAAMM_MOD.json e dados-fonte/s5_pncp_estado.json (só esfera E).
API pública: https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao (dataInicial, dataFinal, codigoModalidadeContratacao, uf, pagina)
"""
import calendar
import json
import time
import urllib.request
from datetime import date
from pathlib import Path

FONTE = Path(__file__).parent.parent / "dados-fonte"
PASTA = FONTE / "pncp"
API = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
MODALIDADES = {1: "Leilão eletrônico", 2: "Diálogo competitivo", 3: "Concurso", 4: "Concorrência eletrônica", 5: "Concorrência presencial",
               6: "Pregão eletrônico", 7: "Pregão presencial", 8: "Dispensa", 9: "Inexigibilidade", 10: "Manifestação de interesse",
               11: "Pré-qualificação", 12: "Credenciamento", 13: "Leilão presencial"}


def baixa(url):
    for tentativa in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (briefing-ro-2027)"}), timeout=90) as r:
                corpo = r.read()
                return json.loads(corpo) if corpo.strip() else {"data": [], "totalPaginas": 0}
        except Exception as e:
            print("  retry", e, flush=True)
            time.sleep(5 * (tentativa + 1))
    return None


def main():
    PASTA.mkdir(exist_ok=True)
    hoje = date.today()
    meses = [(a, m) for a in range(2023, hoje.year + 1) for m in range(1, 13) if (a, m) <= (hoje.year, hoje.month)]
    for a, m in meses:
        for mod in MODALIDADES:
            arq = PASTA / f"{a}{m:02d}_{mod:02d}.json"
            if arq.exists() and not (a, m) == (hoje.year, hoje.month):
                continue
            ini, fim = f"{a}{m:02d}01", f"{a}{m:02d}{calendar.monthrange(a, m)[1]:02d}"
            itens, pag, total = [], 1, 1
            while pag <= total:
                d = baixa(f"{API}?dataInicial={ini}&dataFinal={fim}&codigoModalidadeContratacao={mod}&uf=RO&pagina={pag}&tamanhoPagina=50")
                if d is None:
                    break
                total = d.get("totalPaginas") or 0
                itens += [x for x in d.get("data", []) if x.get("orgaoEntidade", {}).get("esferaId") == "E"]
                pag += 1
            arq.write_text(json.dumps(itens, ensure_ascii=False), encoding="utf-8")
        print(f"{a}-{m:02d} ok", flush=True)
    todos = []
    for arq in sorted(PASTA.glob("*.json")):
        todos += json.loads(arq.read_text(encoding="utf-8"))
    (FONTE / "s5_pncp_estado.json").write_text(json.dumps({"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "fonte": API, "modalidades": MODALIDADES,
                                                           "dados": todos}, ensure_ascii=False), encoding="utf-8")
    print("gravado", len(todos), "contratações do Estado no PNCP", flush=True)


if __name__ == "__main__":
    main()
