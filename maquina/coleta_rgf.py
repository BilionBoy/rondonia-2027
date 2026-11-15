"""RGF do Poder Executivo de RO, Anexo 1 (despesa com pessoal), todos os quadrimestres de 2023 a 2026, pela API do Siconfi.

Uso: python3 maquina/coleta_rgf.py      Grava dados-fonte/s8_rgf_pessoal.json (DTP, % da RCL e limites por período).
"""
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coleta_s3 import siconfi  # noqa: E402

out = []
for ano in (2023, 2024, 2025, 2026):
    for q in (1, 2, 3):
        try:
            itens = siconfi("rgf", {"an_exercicio": ano, "in_periodicidade": "Q", "nr_periodo": q, "co_tipo_demonstrativo": "RGF",
                                    "no_anexo": "RGF-Anexo 01", "co_esfera": "E", "co_poder": "E", "id_ente": 11})
        except Exception as e:  # noqa: BLE001
            print(ano, q, "erro", e)
            continue
        if not itens:
            print(ano, q, "sem dado")
            continue
        v = {}
        for i in itens:
            v.setdefault((i["conta"].strip(), i["coluna"].strip()), i["valor"])
        get = lambda conta, col: next((val for (c, cc), val in v.items() if c.startswith(conta) and cc.startswith(col)), None)  # noqa: E731
        reg = {"ano": ano, "quadrimestre": q, "dtp": get("DESPESA TOTAL COM PESSOAL - DTP", "Valor"),
               "pct_rcl": get("DESPESA TOTAL COM PESSOAL - DTP", "% sobre"), "bruta": get("DESPESA BRUTA COM PESSOAL", "TOTAL (ÚLTIMOS 12 MESES)"),
               "rcl_ajustada": get("= RECEITA CORRENTE LÍQUIDA AJUSTADA PARA CÁLCULO DOS LIMITES DA DESPESA COM PESSOAL", "Valor")
                               or get("RECEITA CORRENTE LÍQUIDA AJUSTADA PARA CÁLCULO DOS LIMITES DA DESPESA", "Valor"),
               "limite_maximo": get("LIMITE MÁXIMO", "% sobre"), "limite_prudencial": get("LIMITE PRUDENCIAL", "% sobre"), "limite_alerta": get("LIMITE DE ALERTA (IX)", "% sobre")}
        out.append(reg)
        print(reg)
        time.sleep(1)
(RAIZ / "dados-fonte" / "s8_rgf_pessoal.json").write_text(json.dumps({"meta": {"fonte": "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rgf",
    "consulta": "RGF, Anexo 1, Poder Executivo de Rondônia (id_ente 11), quadrimestral", "coletado_em": time.strftime("%Y-%m-%d %H:%M")}, "dados": out},
    ensure_ascii=False, indent=1), encoding="utf-8")
