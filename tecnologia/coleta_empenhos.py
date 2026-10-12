"""Notas de empenho de tecnologia (elemento de despesa 40, "Serviços de Tecnologia da Informação e Comunicação – PJ"),
de todos os órgãos, de 2023 a 2026, com a ficha de detalhe de cada nota (CNPJ, histórico, item de despesa, programa).

Uso: python3 tecnologia/coleta_empenhos.py            (lista + detalhes, 2023–2026)
     python3 tecnologia/coleta_empenhos.py lista      (só a lista)
Grava dados-fonte/s5_empenhos_tic.json.

O portal filtra a consulta de empenhos por elemento de despesa (campo CodElementoDespesa):
  33904000 = custeio de TIC (serviços, licenças, links, nuvem, outsourcing)
  44904000 = investimento em TIC
Equipamento de informática (4.4.90.52) não tem elemento próprio: fica fora desta coleta e é medido pelos contratos.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from coleta_s3 import PORTAL, detalhe, post_paginado, sessao, token  # noqa: E402

OUT = Path(__file__).parent.parent / "dados-fonte"
ARQ = OUT / "s5_empenhos_tic.json"
ELEMENTOS = {"33904000": "Custeio de TIC (3.3.90.40)", "44904000": "Investimento em TIC (4.4.90.40)"}
ANOS = [2023, 2024, 2025, 2026]


def lista():
    notas = []
    for ano in ANOS:
        for el, nome in ELEMENTOS.items():
            op = sessao()
            op.open(PORTAL + "/despesa/despesa-estadual", timeout=60).read()
            tok = token(op, "/Despesa/FormConsultaEmpenho")
            linhas = post_paginado(op, "/Despesa/FiltrarEmpenhos", tok,
                                   {"AnoAvancado": ano, "MesInicialAvancado": 1, "MesFinalAvancado": 12, "CodElementoDespesa": el})
            for n in linhas:
                n.update(ano=ano, elemento=el, elemento_nome=nome)
            print(f"  {ano} {el}: {len(linhas)} notas")
            notas += linhas
    return notas


def com_detalhes(notas):
    feito = {}
    if ARQ.exists():
        feito = {n["linkDetalhes"]: n.get("detalhe") for n in json.loads(ARQ.read_text())["dados"] if n.get("detalhe")}
    falta = [n["linkDetalhes"] for n in notas if n["linkDetalhes"] not in feito]
    print(f"detalhes: {len(notas)} notas, faltam {len(falta)}")

    def um(link):
        for tentativa in range(3):
            try:
                return link, detalhe(link)
            except Exception:
                time.sleep(3)
        return link, None

    with ThreadPoolExecutor(6) as ex:
        for i, (link, d) in enumerate(ex.map(um, falta), 1):
            if d:
                feito[link] = d
            if i % 500 == 0:
                print(f"  {i}/{len(falta)}")
    for n in notas:
        n["detalhe"] = feito.get(n["linkDetalhes"])
    return notas


def grava(notas):
    meta = {"fonte": PORTAL + "/despesa/despesa-estadual (Despesas por Empenho, filtro Elemento de Despesa)",
            "detalhe": PORTAL + "/Despesa/notas-de-empenho/detalhes", "coletado_em": time.strftime("%Y-%m-%d %H:%M"),
            "elementos": ELEMENTOS, "anos": ANOS}
    ARQ.write_text(json.dumps({"meta": meta, "dados": notas}, ensure_ascii=False), encoding="utf-8")
    print("gravado", ARQ.name, len(notas))


if __name__ == "__main__":
    notas = lista()
    if sys.argv[1:] != ["lista"]:
        notas = com_detalhes(notas)
    grava(notas)
