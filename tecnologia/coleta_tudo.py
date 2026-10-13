"""Detalhe de TODAS as notas de empenho de 2023–2026 pagas a empresas e entidades privadas a partir de R$ 20 mil,
de qualquer elemento e qualquer órgão: CNPJ, modalidade (pregão, dispensa, inexigibilidade, adesão, "não aplicável"…) e histórico.

Por quê: o contrato publicado não mostra a realidade. Ex.: a UzziPay tem 4 contratos no portal, mas recebeu empenho de 50
unidades; o acordo SEDUC × UFMG/BR TEC não está em contrato nem convênio. O empenho é a única lista que pega tudo.
Uso: python3 tecnologia/coleta_tudo.py   Grava dados-fonte/s5_detalhes_tudo.json (retoma; checkpoint a cada 1.000).
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).parent.parent
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(RAIZ))
from coleta_s3 import detalhe  # noqa: E402

ARQ = FONTE / "s5_detalhes_tudo.json"
MINIMO = 20000
PUBLICO = re.compile(r"PREFEITURA|MUNICIPIO|FUNDO|SECRETARIA|INSS|INSTITUTO NACIONAL DO SEGURO|DIARIAS|FOLHA|TRIBUNAL|ASSEMBLEIA|MINISTERIO|"
                     r"DEFENSORIA|PODER JUDICIARIO|GOVERNO|ESTADO DE RONDONIA|CAMARA MUNICIPAL|RECEITA FEDERAL|CAIXA ECONOMICA|BANCO DO BRASIL|"
                     r"PASEP|IPERON|INSTITUTO DE PREVID|CONSELHO ESCOLAR|ASSOCIACAO DE PAIS", re.I)


def valor(s):
    try:
        return float(s.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def ja_abertos():
    ja = set()
    for arq, campo in (("s5_empenhos_fornecedores.json", "detalhes"), ("s5_varredura.json", "detalhes")):
        if (FONTE / arq).exists():
            ja |= set(json.loads((FONTE / arq).read_text())[campo])
    if (FONTE / "s5_empenhos_tic.json").exists():
        ja |= {n["linkDetalhes"] for n in json.loads((FONTE / "s5_empenhos_tic.json").read_text())["dados"]}
    return ja


def main():
    ja = ja_abertos()
    alvo = []
    for ano in (2023, 2024, 2025, 2026):
        for n in json.loads((FONTE / f"s3_empenhos_{ano}.json").read_text())["dados"]:
            if valor(n["valorEmpenhado"]) >= MINIMO and not PUBLICO.search(n["credor"]) and n["linkDetalhes"] not in ja:
                alvo.append(n["linkDetalhes"])
    feito = json.loads(ARQ.read_text())["detalhes"] if ARQ.exists() else {}
    falta = [l for l in dict.fromkeys(alvo) if l not in feito]
    print(f"{len(alvo)} notas; faltam {len(falta)}", flush=True)

    def um(link):
        for tentativa in range(3):
            try:
                return link, detalhe(link)
            except Exception as e:
                if "404" in str(e):
                    return link, {}
                time.sleep(4)
        return link, None

    def grava():
        ARQ.write_text(json.dumps({"meta": {"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "minimo": MINIMO}, "detalhes": feito}, ensure_ascii=False), encoding="utf-8")

    with ThreadPoolExecutor(8) as ex:
        for i, (link, d) in enumerate(ex.map(um, falta), 1):
            if d is not None:
                feito[link] = d
            if i % 1000 == 0:
                print(f"  {i}/{len(falta)}", flush=True)
                grava()
    grava()
    print("gravado", len(feito), flush=True)


if __name__ == "__main__":
    main()
