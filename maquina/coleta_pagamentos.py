"""Todas as ordens bancárias do Estado (Pagamentos de fornecedores do Portal da Transparência RO), mês a mês.

Uso: python3 -u ../estudos/dossies/rondonia-rural-show/scripts/rodar_v4.py maquina/coleta_pagamentos.py 2026 [2025 ...]
Grava dados-fonte/s8_pagamentos_<ano>.json. Cada pagamento traz a natureza no nível do SUBELEMENTO (especificacaoDespesa,
ex.: 33903001 combustível), a unidade gestora (código e nome), o credor, a nota de empenho, a OB, a data e o valor.
É o mesmo dado do extrato do SIGEF por subelemento, em fonte pública.

Armadilha conhecida: o portal repete a mesma OB quando a UG tem dois nomes; a chave OB + nota + UG + subelemento + valor
conta uma vez. Cada mês é conferido contra o recordsTotal do portal.
"""
import calendar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from coleta_s3 import PORTAL, sessao  # noqa: E402

CAMPOS = ("exercicio", "processo", "especificacaoDespesa", "programa", "acao", "funcao", "fonteDeRecursos", "codUnidadeGestora",
          "unidadeGestora", "docCredor", "credor", "modalidadeLicitacao", "numeroDocumento", "dataDocumento",
          "documentoNE_DocumentoOB", "empenho", "valorPaga", "codDescGrupoDespesa", "codDescElementoDespesa")
LOTE = 2000


def reais(s):
    s = str(s or "").replace("R$", "").replace(" ", "").strip()
    return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s or 0)


def mes(op, tok, ano, m):
    fim = min(calendar.monthrange(ano, m)[1], 31)
    di, df = f"01/{m:02d}/{ano}", f"{fim:02d}/{m:02d}/{ano}"
    linhas, inicio, total = [], 0, None
    while total is None or inicio < total:
        corpo = {"draw": 1, "start": inicio, "length": LOTE, "DataInicial": di, "DataFinal": df, "__RequestVerificationToken": tok}
        req = urllib.request.Request(PORTAL + "/fornecedor/getempenhofornecedores", data=urllib.parse.urlencode(corpo).encode(),
                                     headers={"X-Requested-With": "XMLHttpRequest"})
        for tentativa in range(6):
            try:
                j = json.loads(op.open(req, timeout=300).read())
                break
            except Exception as e:  # noqa: BLE001
                print("   repete", tentativa, e, flush=True)
                time.sleep(10 * (tentativa + 1))
        else:
            raise RuntimeError(f"desisti de {di}-{df} início {inicio}")
        total = j["recordsTotal"]
        linhas += j["data"]
        inicio += LOTE
    return linhas, total


def main(anos):
    op = sessao()
    html = op.open(PORTAL + "/fornecedor", timeout=60).read().decode("utf-8", "replace")
    tok = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', html)[1]
    for ano in anos:
        hoje = time.localtime()
        ultimo = hoje.tm_mon if ano == hoje.tm_year else 12
        unicos, conferencia = {}, []
        for m in range(1, ultimo + 1):
            linhas, total = mes(op, tok, ano, m)
            antes = len(unicos)
            for r in linhas:
                x = {k: r.get(k) for k in CAMPOS}
                x["valor"] = reais(x.pop("valorPaga"))
                ob = (x["documentoNE_DocumentoOB"] or "").split(" - ")
                x["ne"], x["ob"] = (ob + ["", ""])[:2]
                chave = (x["ob"], x["ne"], x["codUnidadeGestora"], x["especificacaoDespesa"], round(x["valor"], 2), x["dataDocumento"])
                unicos[chave] = x
            conferencia.append({"mes": m, "portal": total, "baixadas": len(linhas), "unicas": len(unicos) - antes})
            print(f"{ano}-{m:02d}: portal {total}, baixadas {len(linhas)}, únicas {len(unicos) - antes}", flush=True)
        dados = list(unicos.values())
        saida = RAIZ / "dados-fonte" / f"s8_pagamentos_{ano}.json"
        saida.write_text(json.dumps({"meta": {"fonte": PORTAL + "/fornecedor (Pagamentos de fornecedores, POST /fornecedor/getempenhofornecedores)",
                                              "coletado_em": time.strftime("%Y-%m-%d %H:%M"), "conferencia": conferencia},
                                     "dados": dados}, ensure_ascii=False), encoding="utf-8")
        print(f"gravado {saida.name}: {len(dados)} pagamentos, R$ {sum(x['valor'] for x in dados):,.2f}", flush=True)


if __name__ == "__main__":
    main([int(a) for a in sys.argv[1:]] or [2026])
