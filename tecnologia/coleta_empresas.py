"""Cadastro público (Receita Federal, via BrasilAPI) de cada empresa com contrato de tecnologia ou empenho de TIC.

Uso: python3 tecnologia/coleta_empresas.py   (depois do build_tecnologia.py, que grava dados-fonte/s5_tecnologia.json)
Grava dados-fonte/s5_empresas.json: {cnpj: {razão social, atividade principal (CNAE), abertura, porte, município/UF,
situação cadastral, capital social, natureza jurídica, número de sócios}}. Os nomes dos sócios não são guardados.
Retoma de onde parou.
"""
import json
import re
import time
import urllib.request
from pathlib import Path

FONTE = Path(__file__).parent.parent / "dados-fonte"
ARQ = FONTE / "s5_empresas.json"
API = "https://brasilapi.com.br/api/cnpj/v1/"
CAMPOS = ["razao_social", "nome_fantasia", "cnae_fiscal", "cnae_fiscal_descricao", "data_inicio_atividade", "porte", "municipio", "uf",
          "descricao_situacao_cadastral", "capital_social", "natureza_juridica"]


def main():
    d = json.loads((FONTE / "s5_tecnologia.json").read_text(encoding="utf-8"))
    cnpjs = {re.sub(r"\D", "", r["cnpj"]) for r in d["registros"]} | {re.sub(r"\D", "", e[3]) for e in d["empenhos"]} | {re.sub(r"\D", "", f[3]) for f in d.get("fornecedores", [])}
    cnpjs = sorted(c for c in cnpjs if len(c) == 14)
    feito = json.loads(ARQ.read_text(encoding="utf-8")) if ARQ.exists() else {}
    falta = [c for c in cnpjs if c not in feito]
    print(f"{len(cnpjs)} CNPJs, faltam {len(falta)}")
    for i, c in enumerate(falta, 1):
        for tentativa in range(4):
            try:
                j = json.loads(urllib.request.urlopen(urllib.request.Request(API + c, headers={"User-Agent": "Mozilla/5.0 (briefing-ro-2027)"}), timeout=30).read())
                feito[c] = {k: j.get(k) for k in CAMPOS} | {"socios": len(j.get("qsa") or [])}
                break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    feito[c] = {"erro": "não encontrado"}
                    break
                time.sleep(5 * (tentativa + 1))
            except Exception:
                time.sleep(5 * (tentativa + 1))
        if i % 25 == 0:
            ARQ.write_text(json.dumps(feito, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  {i}/{len(falta)}")
        time.sleep(.35)
    ARQ.write_text(json.dumps(feito, ensure_ascii=False, indent=1), encoding="utf-8")
    print("gravado", len(feito), "empresas")


if __name__ == "__main__":
    main()
