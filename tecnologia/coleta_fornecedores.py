"""Tudo o que os fornecedores de tecnologia receberam do Estado em 2023–2026, em QUALQUER elemento de despesa.

Por quê: o elemento 40 (TIC) não pega tudo. Internet via satélite das escolas, centro de monitoramento, softwares
comprados como material e acordos de parceria (ex.: SEDUC × UFMG via Fundação Christiano Ottoni e BR TEC) são pagos
em outros elementos e nem sempre viram "contrato" ou "convênio" no portal.

Como:
  1. Fornecedor de tecnologia = CNPJ de contrato de tecnologia revisado (menos frota) + credor de nota do elemento 40
     + PARCEIROS (acordos de parceria achados à mão).
  2. Das notas de empenho de 2023–2026 (dados-fonte/s3_empenhos_{ano}.json), pega as que não são do elemento 40, com
     valor >= MINIMO e cujo credor tem nome parecido com um fornecedor; abre o detalhe e fica só com as de CNPJ igual.
Uso: python3 tecnologia/coleta_fornecedores.py   (depois do build_tecnologia.py). Grava dados-fonte/s5_empenhos_fornecedores.json.
Retoma de onde parou.
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(AQUI))
from coleta_s3 import detalhe  # noqa: E402
from classificar import sem_acento  # noqa: E402

ARQ = FONTE / "s5_empenhos_fornecedores.json"
MINIMO = 10000
PARCEIROS = {"18218909000186": "Fundação Christiano Ottoni (UFMG): Acordo de Parceria com a SEDUC, processo 0029.043399/2024-81",
             "15555941000169": "BR TEC (Instituto Brasileiro de Tecnologia, Empreendedorismo e Gestão): Acordo de Parceria com a SEDUC, processo 0029.043399/2024-81"}
STOP = r"\b(LTDA|S A|SA|EIRELI|ME|EPP|CIA|COMERCIO|E|DE|DA|DO|DOS|DAS|EMPRESA|SERVICOS|SERVICO|SOLUCOES|SOLUCAO|TECNOLOGIA|TECNOLOGIAS|INFORMATICA|LTD)\b"


def chave(n):
    w = re.sub(STOP, " ", re.sub(r"[^A-Z0-9 ]", " ", sem_acento(n))).split()
    return " ".join(w[:2])


def so_num(s):
    return re.sub(r"\D", "", s or "")


def valor(s):
    try:
        return float(s.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def main():
    T = json.loads((FONTE / "s5_tecnologia.json").read_text(encoding="utf-8"))
    E = json.loads((FONTE / "s5_empenhos_tic.json").read_text(encoding="utf-8"))["dados"]
    cnpjs, nomes = dict(PARCEIROS), {}
    for r in T["registros"]:
        if r["cat"] != "frota" and so_num(r["cnpj"]):
            cnpjs.setdefault(so_num(r["cnpj"]), r["contratado"])
            nomes[chave(r["contratado"])] = 1
    for n in E:
        c = so_num((n.get("detalhe") or {}).get("CPF/CNPJ do credor", ""))
        if len(c) == 14:
            cnpjs.setdefault(c, n["credor"])
            nomes[chave(n["credor"])] = 1
    nomes[chave("FUNDACAO CHRISTIANO OTTONI")] = nomes[chave("INSTITUTO BRASILEIRO DE TECNOLOGIA, EMPRED.E GESTÃO")] = 1
    nomes.pop("", None)
    ja40 = {n["linkDetalhes"] for n in E}
    cand = []
    for ano in (2023, 2024, 2025, 2026):
        for n in json.loads((FONTE / f"s3_empenhos_{ano}.json").read_text(encoding="utf-8"))["dados"]:
            if n["linkDetalhes"] not in ja40 and valor(n["valorEmpenhado"]) >= MINIMO and chave(n["credor"]) in nomes:
                cand.append({**n, "ano": ano})
    feito = json.loads(ARQ.read_text(encoding="utf-8"))["detalhes"] if ARQ.exists() else {}
    falta = [n["linkDetalhes"] for n in cand if n["linkDetalhes"] not in feito]
    print(f"{len(cnpjs)} CNPJs de fornecedores; {len(cand)} notas candidatas; faltam {len(falta)} detalhes")

    def um(link):
        for tentativa in range(3):
            try:
                return link, detalhe(link)
            except Exception:
                time.sleep(3)
        return link, None

    def grava():
        notas = []
        for n in cand:
            d = feito.get(n["linkDetalhes"])
            c = so_num((d or {}).get("CPF/CNPJ do credor", ""))
            if d and c in cnpjs:
                notas.append({**n, "cnpj": c, "detalhe": d, "parceria": PARCEIROS.get(c, "")})
        meta = {"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "minimo": MINIMO, "candidatas": len(cand), "fornecedores": len(cnpjs),
                "regra": "notas de 2023–2026 fora do elemento 40, credor com CNPJ de fornecedor de tecnologia (contrato revisado, elemento 40 ou parceria)"}
        ARQ.write_text(json.dumps({"meta": meta, "notas": notas, "detalhes": feito}, ensure_ascii=False), encoding="utf-8")
        return notas

    with ThreadPoolExecutor(6) as ex:
        for i, (link, d) in enumerate(ex.map(um, falta), 1):
            if d:
                feito[link] = d
            if i % 500 == 0:
                print(f"  {i}/{len(falta)}")
                grava()
    notas = grava()
    print("gravado", len(notas), "notas confirmadas por CNPJ, R$", round(sum(valor(n["valorEmpenhado"]) for n in notas) / 1e6, 1), "mi")


if __name__ == "__main__":
    main()
