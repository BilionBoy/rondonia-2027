"""Histórico completo (2019–2026) dos empenhos do Acordo de Parceria SEDUC × UFMG: Fundação Christiano Ottoni (FCO) e BR TEC.

Uso: python3 tecnologia/coleta_parceria.py   Grava dados-fonte/s5_parceria_ufmg_brtec.json (notas + detalhe).
O portal corta o histórico das notas ("Acordo de Parceria entre a…"); o objeto completo está no processo SEI 0029.043399/2024-81.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from coleta_s3 import PORTAL, detalhe, post_paginado, sessao, token  # noqa: E402

CREDORES = {"CHRISTIANO OTTONI": "Fundação Christiano Ottoni (UFMG)", "INSTITUTO BRASILEIRO DE TECNOLOGIA": "BR TEC"}


def tenta(f, *a, n=5, obrigatorio=True):
    for i in range(n):
        try:
            return f(*a)
        except Exception as e:
            print("  retry", e)
            if "404" in str(e):
                break
            time.sleep(8 * (i + 1))
    if obrigatorio:
        raise SystemExit("portal fora do ar")
    return None


def main():
    notas = {}
    for nome in CREDORES:
        for ano in range(2019, 2027):
            def busca():
                op = sessao()
                op.open(PORTAL + "/despesa/despesa-estadual", timeout=90).read()
                tok = token(op, "/Despesa/FormConsultaEmpenho")
                return post_paginado(op, "/Despesa/FiltrarEmpenhos", tok, {"AnoAvancado": ano, "MesInicialAvancado": 1, "MesFinalAvancado": 12, "NomeCredor": nome})
            for n in tenta(busca):
                notas[n["linkDetalhes"]] = {**n, "ano": ano, "parceiro": CREDORES[nome]}
    for n in notas.values():
        n["detalhe"] = tenta(detalhe, n["linkDetalhes"], obrigatorio=False) or {}
    out = Path(__file__).parent.parent / "dados-fonte" / "s5_parceria_ufmg_brtec.json"
    out.write_text(json.dumps({"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "notas": list(notas.values())}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado", len(notas), "notas")


if __name__ == "__main__":
    main()
