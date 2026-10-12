"""Todos os contratos do Estado no Portal da Transparência RO, de todos os órgãos, de 2015 até o ano atual.

Uso: python3 coleta_contratos.py            (lista de contratos, ano a ano)
     python3 coleta_contratos.py detalhes   (abre a ficha dos contratos de tecnologia: documentos no SEI)
Grava dados-fonte/s5_contratos.json e .csv. A ficha de detalhe só é aberta para os contratos que
tecnologia/classificar.py marcou como tecnologia (dados-fonte/s5_contratos_ti.json), para não abrir 10 mil páginas.

A consulta é a da página /contratos (Contratos e Convênios > Contratos), sem filtro de órgão:
POST /contratos/consultacontratos com TipoDocumento=1 (Contratos) e Ano. O portal devolve a tabela inteira do ano.
"""
import csv
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from coleta_s3 import PORTAL, sessao, token  # noqa: E402

OUT = Path(__file__).parent / "dados-fonte"
CAMPOS = {"num-documento": "numero", "num-processo": "processo_sei", "unidade": "orgao", "contratado": "contratado", "cnpj": "cnpj",
          "elaboracao": "elaboracao", "vigencia": "vigencia", "objeto": "objeto", "origem": "origem", "valor": "valor_global",
          "aditivo": "tem_aditivo", "fiscal": "fiscal", "retorno": "retorno", "link": "detalhe"}


def texto(s):
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def valor(s):
    try:
        return float(re.sub(r"[^\d,]", "", s).replace(",", "."))
    except ValueError:
        return None


def data_iso(s):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", s or "")
    return f"{m[3]}-{m[2]}-{m[1]}" if m else ""


def consulta(op, tok, ano):
    corpo = urllib.parse.urlencode({"__RequestVerificationToken": tok, "TipoDocumento": "1", "Ano": ano, "Mes": "", "NumeroDocumento": "",
                                    "IdProcedimentoLicitatorio": " ", "CodigoUnidadeGestora": "", "Cnpj": "", "RazaoSocial": "",
                                    "Objeto": "", "Aditivo": ""}).encode()
    for tentativa in range(4):
        try:
            req = urllib.request.Request(PORTAL + "/contratos/consultacontratos", data=corpo, headers={"X-Requested-With": "XMLHttpRequest"})
            return op.open(req, timeout=300).read().decode("utf-8", "replace")
        except Exception as e:
            print("  retry", ano, e)
            time.sleep(6)
    raise SystemExit(f"falhou o ano {ano}")


def linhas_da_tabela(h, ano):
    out = []
    for tr in re.finditer(r"<tr data-num-documento=(.*?)>\s*<td(.*?)</tr>", h, re.S):
        attrs = dict(re.findall(r'data-([a-z-]+)="([^"]*)"', "data-num-documento=" + tr[1]))
        r = {novo: texto(attrs.get(velho, "")) for velho, novo in CAMPOS.items()}
        tds = [texto(re.sub(r"<[^>]+>", " ", t)) for t in re.findall(r"<td[^>]*>(.*?)</td>", "<td" + tr[2], re.S)]
        r["assinatura"] = tds[2] if len(tds) > 2 else ""
        r["detalhe"] = PORTAL + r["detalhe"] if r["detalhe"].startswith("/") else r["detalhe"]
        r.update(ano_consulta=int(ano), valor=valor(r["valor_global"]), vigencia_iso=data_iso(r["vigencia"]),
                 assinatura_iso=data_iso(r["assinatura"]), elaboracao_iso=data_iso(r["elaboracao"]))
        out.append(r)
    return out


def unidades(pagina):
    trecho = pagina[pagina.find('name="CodigoUnidadeGestora"'):]
    trecho = trecho[:trecho.find("</select>")]
    return [{"codigo": v, "nome": texto(t)} for v, t in re.findall(r'<option value="([^"]+)"[^>]*>([^<]*)', trecho) if v.strip()]


def coletar():
    op = sessao()
    pagina = op.open(PORTAL + "/contratos", timeout=60).read().decode()
    anos = re.findall(r'<option value="(\d{4})"', pagina[pagina.find('name="Ano"'):][:2000])
    tok = token(op, "/contratos")
    linhas = []
    for ano in sorted(anos):
        h = consulta(op, tok, ano)
        n = linhas_da_tabela(h, ano)
        print(f"  {ano}: {len(n)} contratos")
        linhas += n
    meta = {"fonte": PORTAL + "/contratos", "coletado_em": time.strftime("%Y-%m-%d %H:%M"), "anos": sorted(anos),
            "consulta": "POST /contratos/consultacontratos (TipoDocumento=1, Ano; sem filtro de órgão)",
            "unidades_gestoras": unidades(pagina),
            "nota": "O ano da consulta é o ano de cadastro do contrato no portal (data de elaboração), não o de vigência."}
    (OUT / "s5_contratos.json").write_text(json.dumps({"meta": meta, "dados": linhas}, ensure_ascii=False, indent=1), encoding="utf-8")
    colunas = ["ano_consulta", "orgao", "numero", "processo_sei", "assinatura", "elaboracao", "vigencia", "contratado", "cnpj",
               "valor", "origem", "tem_aditivo", "fiscal", "objeto", "detalhe"]
    with open(OUT / "s5_contratos.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=colunas, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
    print("gravado", len(linhas), "contratos em dados-fonte/s5_contratos.json")


def detalhes():
    """Abre a ficha de cada contrato de tecnologia e guarda os links dos documentos no SEI."""
    alvo = OUT / "s5_contratos_ti.json"
    bruto = json.loads(alvo.read_text(encoding="utf-8"))
    op = sessao()
    feitos = 0
    for r in bruto["dados"]:
        if r.get("sei_docs") is not None or not r.get("detalhe"):
            continue
        for tentativa in range(3):
            try:
                d = op.open(urllib.request.Request(r["detalhe"], headers={"X-Requested-With": "XMLHttpRequest"}), timeout=60).read().decode()
                break
            except Exception as e:
                print("  retry detalhe", e)
                time.sleep(3)
        else:
            continue
        r["sei_docs"] = [{"rotulo": texto(re.sub(r"<[^>]+>", " ", t)), "url": html.unescape(u)}
                         for u, t in re.findall(r"<a[^>]+href=['\"](https://sei\.[^'\"]+)['\"][^>]*>(.*?)</a>", d, re.S)]
        feitos += 1
        if feitos % 50 == 0:
            print(f"  {feitos} fichas")
            alvo.write_text(json.dumps(bruto, ensure_ascii=False, indent=1), encoding="utf-8")
        time.sleep(.12)
    alvo.write_text(json.dumps(bruto, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fichas abertas:", feitos)


if __name__ == "__main__":
    detalhes() if sys.argv[1:] == ["detalhes"] else coletar()
