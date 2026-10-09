"""Convênios, termos de fomento e termos de colaboração de um órgão, no Portal da Transparência RO.

Uso: python3 coleta_convenios.py [SIGLA]   (padrão: SEAS)
Grava dados-fonte/s4_convenios_{sigla}.json e .csv, de 2015 até o ano atual.
Para cada instrumento, abre também a ficha de detalhe do portal: CNPJ, fiscal, vigência e os documentos no SEI (acesso externo público).
"""
import csv
import html
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from coleta_s3 import PORTAL, sessao, token  # noqa: E402

OUT = Path(__file__).parent / "dados-fonte"
TIPOS = {"2": "Convênio", "11": "Termo de Fomento", "13": "Termo de Cooperação/Colaboração"}
COLUNAS = ["numero", "processo_sei", "assinatura", "elaboracao", "contratado", "valor_global", "vigencia", "origem", "tem_aditivo", "objeto"]


def texto(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def valor(s):
    try:
        return float(s.replace("R$", "").replace(".", "").replace(",", ".").strip())
    except ValueError:
        return None


def main(sigla):
    op = sessao()
    pagina = op.open(PORTAL + "/convenios", timeout=60).read().decode()
    trecho = pagina[pagina.find('name="CodigoUnidadeGestora"'):]
    trecho = trecho[:trecho.find("</select>")]
    ug = next(v for v, t in re.findall(r'<option value="([^"]+)"[^>]*>([^<]*)', trecho) if html.unescape(t).startswith(sigla + " "))
    anos = re.findall(r'<option value="(\d{4})"', pagina[pagina.find('name="Ano"'):][:2000])
    tok = token(op, "/convenios")
    linhas = []
    for tipo, nome_tipo in TIPOS.items():
        for ano in anos:
            corpo = urllib.parse.urlencode({"__RequestVerificationToken": tok, "CodigoUnidadeGestora": ug, "TipoDocumento": tipo, "Ano": ano, "Mes": ""}).encode()
            for tentativa in range(3):
                try:
                    h = op.open(urllib.request.Request(PORTAL + "/convenios/ConsultaConvenios", data=corpo), timeout=120).read().decode()
                    break
                except Exception as e:
                    print("  retry", e)
                    time.sleep(4)
            n = 0
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S)[1:]:
                tds = [texto(t) for t in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
                if len(tds) < len(COLUNAS):
                    continue
                r = dict(zip(COLUNAS, tds))
                m = re.search(r"data-parameter='(/Convenios/Detalhes\?[^']+)'", tr)
                r["detalhe"] = PORTAL + html.unescape(m[1]) if m else ""
                metade = r["numero"].split(" ")
                r["numero"] = " ".join(metade[: len(metade) // 2]) if metade[: len(metade) // 2] == metade[len(metade) // 2:] else r["numero"]
                r.update(tipo=nome_tipo, ano_consulta=int(ano), valor=valor(r["valor_global"]))
                linhas.append(r)
                n += 1
            print(f"  {nome_tipo} {ano}: {n}")
    print("detalhes:", len(linhas))
    for i, r in enumerate(linhas):
        r.update(cnpj="", fiscal="", sei_docs=[])
        if not r["detalhe"]:
            continue
        for tentativa in range(3):
            try:
                d = op.open(r["detalhe"], timeout=60).read().decode()
                break
            except Exception as e:
                print("  retry detalhe", e)
                time.sleep(3)
        else:
            continue
        cn = re.search(r"CNPJ/CPF\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", d)
        fi = re.search(r"Fiscal\s*</[^>]+>\s*<[^>]+>\s*([^<]+)", d)
        r["cnpj"] = texto(cn[1]) if cn else ""
        r["fiscal"] = "" if not fi or "Sem Informa" in texto(fi[1]) else texto(fi[1])
        r["sei_docs"] = [{"rotulo": texto(t), "url": html.unescape(u)} for u, t in re.findall(r"<a href='(https://sei\.[^']+)'[^>]*>(.*?)</a>", d, re.S)]
        if i % 50 == 0:
            print(f"  {i}/{len(linhas)}")
        time.sleep(.12)
    meta = {"fonte": PORTAL + "/convenios", "orgao": sigla, "codigo_ug": ug, "coletado_em": time.strftime("%Y-%m-%d %H:%M"),
            "consulta": "POST /convenios/ConsultaConvenios (CodigoUnidadeGestora, TipoDocumento, Ano)"}
    (OUT / f"s4_convenios_{sigla.lower()}.json").write_text(json.dumps({"meta": meta, "dados": linhas}, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(OUT / f"s4_convenios_{sigla.lower()}.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["tipo", "ano_consulta"] + COLUNAS + ["valor", "cnpj", "fiscal", "detalhe", "documento_sei"], delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows([{**r, "documento_sei": " | ".join(x["url"] for x in r["sei_docs"])} for r in linhas])
    print("gravado", len(linhas), "linhas")


if __name__ == "__main__":
    import urllib.request  # noqa: F401  (usado via op.open)
    main(sys.argv[1] if len(sys.argv) > 1 else "SEAS")
