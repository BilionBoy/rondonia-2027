"""Contratos e atas de registro de preços publicados no PNCP pelos órgãos do Poder Executivo de RO (2023–2026).

Uso: python3 tecnologia/coleta_pncp_contratos.py   (retoma de onde parou; respeita o limite da API)
Órgãos: os CNPJs do Executivo que aparecem nas contratações do PNCP (s5_pncp_estado.json), sem a Defensoria, mais o CNPJ
genérico "Estado de Rondônia" (00394585000171), usado pelo Contratos.gov.br.
Grava dados-fonte/pncp_contratos/{contratos|atas}_{cnpj}_{ano}.json e, no fim, dados-fonte/s5_pncp_contratos.json (tudo junto).
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent.parent
FONTE = RAIZ / "dados-fonte"
PASTA = FONTE / "pncp_contratos"
API = "https://pncp.gov.br/api/consulta/v1/"
DPE = "01072076000195"
ESTADO = "00394585000171"
ANOS = (2023, 2024, 2025, 2026)


def pega(url):
    for tentativa in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (rondonia-2027)", "Accept": "application/json"}), timeout=90)
            corpo = r.read()
            return json.loads(corpo) if corpo else {"data": [], "totalPaginas": 0}
        except urllib.error.HTTPError as e:
            if e.code == 204:
                return {"data": [], "totalPaginas": 0}
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(10 * (tentativa + 1))
                continue
            if e.code == 400:
                return {"data": [], "totalPaginas": 0, "erro": e.read()[:300].decode("utf-8", "ignore")}
            raise
        except Exception:
            time.sleep(10 * (tentativa + 1))
    raise RuntimeError("falhou: " + url)


def coleta(tipo, cnpj, ano):
    arq = PASTA / f"{tipo}_{cnpj}_{ano}.json"
    if arq.exists():
        return json.loads(arq.read_text(encoding="utf-8"))
    fim = "20261012" if ano == 2026 else f"{ano}1231"
    filtro = {"cnpjOrgao": cnpj} if tipo == "contratos" else {"cnpj": cnpj}
    dados, pagina = [], 1
    while True:
        q = urllib.parse.urlencode({"dataInicial": f"{ano}0101", "dataFinal": fim, **filtro, "pagina": pagina, "tamanhoPagina": 500})
        j = pega(API + tipo + "?" + q)
        dados += j.get("data") or []
        if pagina >= (j.get("totalPaginas") or 0):
            break
        pagina += 1
        time.sleep(.6)
    arq.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    return dados


def main():
    PASTA.mkdir(exist_ok=True)
    pn = json.loads((FONTE / "s5_pncp_estado.json").read_text(encoding="utf-8"))["dados"]
    cnpjs = sorted({x["orgaoEntidade"]["cnpj"] for x in pn if x["orgaoEntidade"]["poderId"] == "E" and x["orgaoEntidade"]["cnpj"] != DPE} | {ESTADO})
    print(len(cnpjs), "CNPJs")
    tudo = {"contratos": [], "atas": []}
    for i, c in enumerate(cnpjs, 1):
        for ano in ANOS:
            for tipo in ("contratos", "atas"):
                xs = coleta(tipo, c, ano)
                tudo[tipo] += xs
        print(f"{i}/{len(cnpjs)} {c} · contratos {len(tudo['contratos'])} · atas {len(tudo['atas'])}", flush=True)
    # o mesmo contrato pode vir em dois anos (janela por data de publicação/atualização): fica uma vez
    for tipo, chave in (("contratos", "numeroControlePNCP"), ("atas", "numeroControlePNCPAta")):
        vistos = {}
        for x in tudo[tipo]:
            vistos[x.get(chave) or json.dumps(x, sort_keys=True)[:200]] = x
        tudo[tipo] = list(vistos.values())
    (FONTE / "s5_pncp_contratos.json").write_text(json.dumps({"fonte": "PNCP · API de consulta: /v1/contratos (cnpjOrgao) e /v1/atas (cnpj)",
                                                               "coletado_em": time.strftime("%Y-%m-%d %H:%M"), "cnpjs": cnpjs, **tudo}, ensure_ascii=False), encoding="utf-8")
    print("gravado", len(tudo["contratos"]), "contratos e", len(tudo["atas"]), "atas")


if __name__ == "__main__":
    main()
