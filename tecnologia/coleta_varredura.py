"""Varredura de todas as notas de empenho 2023–2026 onde tecnologia costuma estar escondida, de qualquer modalidade
(pregão, dispensa, inexigibilidade, adesão a ata, credenciamento…), de qualquer fornecedor, conhecido ou não.

Por quê: contrato e convênio publicados não pegam tudo. Compra por dispensa ou inexigibilidade muitas vezes não vira
"contrato" no portal, e tecnologia é empenhada em elementos que não são o 40 (TIC).

Como:
  1. dados-fonte/s5_elemento_por_nota.json diz o elemento de cada nota (consulta da lista filtrada por elemento).
  2. Candidatas: notas dos elementos abaixo, com valor mínimo por elemento, cujo credor não é claramente de outra área
     (prefeitura, INSS, energia, combustível, saúde, obra, conselho escolar etc.) e cujo detalhe ainda não foi aberto.
  3. Abre o detalhe (histórico, CNPJ, modalidade). A classificação (é tecnologia?) é feita no build_tecnologia.py.
Uso: python3 tecnologia/coleta_varredura.py   Grava dados-fonte/s5_varredura.json (retoma de onde parou).
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

ARQ = FONTE / "s5_varredura.json"
MINIMO = {"33903900": 5000, "33903000": 5000, "44905200": 3000, "44903900": 0, "33903700": 0, "33903500": 0, "44903000": 0, "33913900": 0}
NAO_TI_CREDOR = re.compile(
    r"PREFEITURA|MUNICIPIO|FUNDO (MUNICIPAL|PREVID|ESTADUAL)|SECRETARIA|INSS|INSTITUTO NACIONAL DO SEGURO|ENERGISA|CAERD|CERON|"
    r"POSTO|COMBUSTIV|PETRO|DERIVADOS|AUTO ?PECAS|PNEU|CONSTRU|ENGENHARIA|EDIFICA|PAVIMENT|TERRAPLEN|HOSPITAL|CLINICA|LABORAT|FARMA|DROGA|MEDIC|"
    r"ODONTO|ALIMENT|RESTAURANTE|REFEIC|HOTEL|POUSADA|TRANSPORTE|VIAGENS|TURISMO|AGROPEC|VETERIN|AGRICOLA|CONSELHO ESCOLAR|ASSOCIA|APAE|"
    r"IGREJA|SINDICATO|BANCO DO BRASIL|CAIXA ECONOMICA|CORREIOS|EMPRESA BRASILEIRA DE CORREIOS|GRAFICA|EDITORA|LIVRARIA|CONFEC|UNIFORME|"
    r"MOVEIS|MADEIR|FERRAGENS|MATERIAIS DE CONSTRU|LIMPEZA|CONSERVACAO|SEGURANCA PRIVADA|VIGILANCIA|PROTECAO MAXIMA|PROALVO|LOCADORA DE VEICULOS|"
    r"LOCACAO DE VEICULOS|VEICULOS|MOTOS|CAMINHOES|TRATORES|MAQUINAS AGRICOLAS|GAS|OXIGENIO|ACOUGUE|SUPERMERCADO|PANIFIC|HORTI|FRIGORIF")


def valor(s):
    try:
        return float(s.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return 0.0


def main():
    elemento = {}
    for chave, links in json.loads((FONTE / "s5_elemento_por_nota.json").read_text()).items():
        el = chave.split("_")[0]
        for l in links:
            elemento[l] = el
    ja = set()
    for arq, campo in (("s5_empenhos_fornecedores.json", "detalhes"),):
        if (FONTE / arq).exists():
            ja |= set(json.loads((FONTE / arq).read_text())[campo])
    if (FONTE / "s5_empenhos_tic.json").exists():
        ja |= {n["linkDetalhes"] for n in json.loads((FONTE / "s5_empenhos_tic.json").read_text())["dados"]}
    cand = {}
    for ano in (2023, 2024, 2025, 2026):
        for n in json.loads((FONTE / f"s3_empenhos_{ano}.json").read_text())["dados"]:
            el = elemento.get(n["linkDetalhes"])
            if el not in MINIMO or n["linkDetalhes"] in ja:
                continue
            if valor(n["valorEmpenhado"]) < MINIMO[el] or NAO_TI_CREDOR.search(sem_acento(n["credor"])):
                continue
            cand[n["linkDetalhes"]] = {**n, "ano": ano, "elemento": el}
    feito = json.loads(ARQ.read_text())["detalhes"] if ARQ.exists() else {}
    falta = [l for l in cand if l not in feito]
    print(f"{len(cand)} notas candidatas; faltam {len(falta)} detalhes", flush=True)

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
        ARQ.write_text(json.dumps({"meta": {"coletado_em": time.strftime("%Y-%m-%d %H:%M"), "minimo": MINIMO, "candidatas": len(cand)},
                                   "notas": list(cand.values()), "detalhes": feito}, ensure_ascii=False), encoding="utf-8")

    with ThreadPoolExecutor(8) as ex:
        for i, (link, d) in enumerate(ex.map(um, falta), 1):
            if d is not None:
                feito[link] = d
            if i % 1000 == 0:
                print(f"  {i}/{len(falta)}", flush=True)
                grava()
    grava()
    print("gravado", len(feito), "detalhes", flush=True)


if __name__ == "__main__":
    main()
