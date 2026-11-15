"""Atualiza as notas de empenho de 2026 (lista mês a mês, com o pago do dia) e busca a ficha só das notas novas.

Uso: python3 -u ../estudos/dossies/rondonia-rural-show/scripts/rodar_v4.py maquina/atualiza_2026.py
A lista anterior fica em dados-fonte/s3_empenhos_2026.<data>.json. Depois rode coleta_detalhes_por_chave.py 2026.
"""
import json
import shutil
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coleta_s3 import PORTAL, empenhos  # noqa: E402

ARQ = RAIZ / "dados-fonte" / "s3_empenhos_2026.json"
antes = json.loads(ARQ.read_text(encoding="utf-8"))
notas = empenhos(2026)
print(f"2026: {len(notas)} notas agora; {len(antes['dados'])} em {antes['meta']['coletado_em']}")
if len(notas) < len(antes["dados"]) * 0.98:
    sys.exit("lista menor que a anterior: o portal pode estar recarregando; nada gravado")
shutil.copy(ARQ, ARQ.with_suffix(f".{antes['meta']['coletado_em'][:10]}.json"))
ARQ.write_text(json.dumps({"meta": {"coletado_em": time.strftime("%Y-%m-%d %H:%M"),
                                    "fonte": PORTAL + "/despesa/despesa-estadual (Despesas por Empenho, mês a mês)"},
                           "dados": notas}, ensure_ascii=False), encoding="utf-8")
print("gravado", ARQ.name)
