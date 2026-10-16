"""Coleta da etapa "O que não aparece".

Fontes públicas, sem login:
  - Portal da Transparência RO: notas de empenho (/Despesa/FiltrarEmpenhos) e diárias (/diarias/filtrar)
  - Tesouro Nacional / Siconfi: RREO Anexo 7 (restos a pagar) e MSC (contabilidade por fonte e natureza)

Uso: python3 coleta_s3.py [empenhos|detalhes|diarias|rreo|msc|tudo]
Grava em dados-fonte/s3_*.json (dado bruto) para o build_s3.py agregar.
"""
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PORTAL = "https://transparencia.ro.gov.br"
SICONFI = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
OUT = Path(__file__).parent / "dados-fonte"
ID_ENTE = 11


def sessao():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", "Mozilla/5.0 (briefing-ro-2027)")]
    return op


def token(op, path):
    html = op.open(PORTAL + path, timeout=60).read().decode("utf-8", "replace")
    m = re.search(r'name="__RequestVerificationToken" type="hidden" value="([^"]+)"', html)
    return m.group(1)


def post_paginado(op, path, tok, campos, lote=10000):
    linhas, inicio, total = [], 0, None
    while total is None or inicio < total:
        corpo = dict(campos, __RequestVerificationToken=tok, draw=1, start=inicio, length=lote)
        req = urllib.request.Request(PORTAL + path, data=urllib.parse.urlencode(corpo).encode())
        for tentativa in range(4):
            try:
                j = json.loads(op.open(req, timeout=300).read())
                break
            except Exception as e:
                print("  retry", tentativa, e)
                time.sleep(5)
        total = j["recordsTotal"]
        linhas += j["data"]
        inicio += lote
        print(f"  {path} {len(linhas)}/{total}")
    return linhas


def empenhos(ano):
    """Notas do ano, consultadas mês a mês. Com o ano inteiro, a paginação do Portal repete e
    pula notas (em 15/10/2026: 1.078 repetidas e outras tantas faltando); um mês cabe numa página."""
    op = sessao()
    op.open(PORTAL + "/despesa/despesa-estadual", timeout=60).read()
    tok = token(op, "/Despesa/FormConsultaEmpenho")
    notas = {}
    for mes in range(1, 13):
        campos = {"AnoAvancado": ano, "MesInicialAvancado": mes, "MesFinalAvancado": mes}
        for n in post_paginado(op, "/Despesa/FiltrarEmpenhos", tok, campos, lote=20000):
            notas[n["linkDetalhes"]] = n
    return list(notas.values())


def diarias(ano):
    op = sessao()
    tok = token(op, "/diarias")
    campos = {"Exercicio": ano, "MesInicial": 1, "MesFinal": 12}
    return post_paginado(op, "/diarias/filtrar", tok, campos, lote=20000)


def siconfi(path, params):
    itens, off = [], 0
    while True:
        q = urllib.parse.urlencode(dict(params, offset=off))
        j = json.loads(urllib.request.urlopen(f"{SICONFI}/{path}?{q}", timeout=180).read())
        itens += j["items"]
        if not j.get("hasMore"):
            return itens
        off += len(j["items"])


CAMPOS_DETALHE = [
    "Histórico", "Modalidade licitatória", "CPF/CNPJ do credor", "Razão social do credor", "Secretaria",
    "Data de emissão", "Valor empenhado final", "Valor pago", "Valor pago no exercício do empenho",
    "Valor pago em anos posteriores ao da emissão do empenho", "Valor liquidado no exercício da emissão do empenho",
    "Valor liquidado em anos posteriores ao da emissão do empenho", "Tipo de empenho", "Efeito", "Função",
    "Subfunção", "Programa de governo", "Ação de governo", "Fonte do recurso", "Item de despesa", "Projeto",
]


def detalhe(link):
    import html as h
    t = urllib.request.urlopen(urllib.request.Request(
        f"{PORTAL}/Despesa/notas-de-empenho/detalhes{link}", headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"\s+", " ", h.unescape(re.sub(r"<[^>]+>", " ", t)))
    t = t[t.find("Informações Gerais"):t.find("A CGE-RO utiliza cookies")]
    # cada rótulo é seguido do valor até o próximo rótulo; os mais longos primeiro para "Valor pago" não engolir os outros
    pos = []
    for c in sorted(CAMPOS_DETALHE, key=len, reverse=True):
        for m in re.finditer(re.escape(c) + " ", t):
            if not any(a <= m.start() < b for a, b, _ in pos):
                pos.append((m.start(), m.end(), c))
    pos.sort()
    return {c: t[e:(pos[i + 1][0] if i + 1 < len(pos) else len(t))].strip() for i, (s, e, c) in enumerate(pos)}


def detalhes(ano, minimo=200000):
    from concurrent.futures import ThreadPoolExecutor
    def valor(s):
        try:
            return float(s.replace("R$", "").replace(".", "").replace(",", ".").strip())
        except ValueError:
            return 0.0
    notas = json.loads((OUT / f"s3_empenhos_{ano}.json").read_text())["dados"]
    alvo = [n["linkDetalhes"] for n in notas if valor(n["valorEmpenhado"]) >= minimo]
    arq = OUT / f"s3_detalhes_{ano}.json"
    feito = json.loads(arq.read_text())["dados"] if arq.exists() else {}
    falta = [l for l in alvo if l not in feito]
    print(f"detalhes {ano}: {len(alvo)} notas, faltam {len(falta)}")

    def um(link):
        for tentativa in range(3):
            try:
                return link, detalhe(link)
            except Exception:
                time.sleep(3)
        return link, None

    with ThreadPoolExecutor(6) as ex:
        for i, (link, d) in enumerate(ex.map(um, falta), 1):
            if d:
                feito[link] = d
            if i % 500 == 0:
                grava(arq.name, feito, PORTAL + "/Despesa/notas-de-empenho/detalhes")
    grava(arq.name, feito, PORTAL + "/Despesa/notas-de-empenho/detalhes")


def grava(nome, dado, fonte):
    meta = {"fonte": fonte, "coletado_em": time.strftime("%Y-%m-%d %H:%M")}
    (OUT / nome).write_text(json.dumps({"meta": meta, "dados": dado}, ensure_ascii=False))
    print("gravado", nome, len(dado))


def main(alvo):
    if alvo in ("empenhos", "tudo"):
        for ano in (2025, 2026):
            grava(f"s3_empenhos_{ano}.json", empenhos(ano), PORTAL + "/despesa/despesa-estadual (Despesas por Empenho)")
    if alvo in ("detalhes", "tudo"):
        for ano in (2025, 2026):
            detalhes(ano)
    if alvo in ("diarias", "orgaos", "tudo"):
        # códigos de órgão do filtro do portal, para montar link direto (?Exercicio=&MesInicial=&MesFinal=&Orgao=)
        import html as h
        pag = sessao().open(PORTAL + "/diarias", timeout=60).read().decode()
        trecho = pag[pag.find('name="Orgao"'):]
        trecho = trecho[:trecho.find("</select>")]
        opcoes = [[h.unescape(v), h.unescape(t)] for v, t in re.findall(r'<option value="([^"]+)"[^>]*>([^<]*)', trecho)]
        grava("s3_diarias_orgaos.json", opcoes, PORTAL + "/diarias (filtro Órgão)")
    if alvo in ("diarias", "tudo"):
        for ano in (2025, 2026):
            grava(f"s3_diarias_{ano}.json", diarias(ano), PORTAL + "/diarias")
    if alvo in ("rreo", "tudo"):
        rp = {}
        for ano in range(2019, 2026):
            rp[ano] = siconfi("rreo", {"an_exercicio": ano, "nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
                                       "no_anexo": "RREO-Anexo 07", "id_ente": ID_ENTE})
        grava("s3_rreo_anexo7.json", rp, SICONFI + "/rreo (RREO Anexo 07, 6º bimestre)")
    if alvo in ("msc", "tudo"):
        msc = {}
        for ano, mes in ((2025, 12), (2026, 6), (2026, 8)):
            msc[f"{ano}-{mes:02d}"] = siconfi("msc_orcamentaria", {
                "id_ente": ID_ENTE, "an_referencia": ano, "me_referencia": mes, "co_tipo_matriz": "MSCC",
                "classe_conta": 6, "id_tv": "ending_balance"})
        grava("s3_msc_classe6.json", msc, SICONFI + "/msc_orcamentaria (MSCC, classe 6, saldo final)")
    if alvo in ("msc_mensal", "tudo"):
        # só as diárias (339014 e 339015) de cada mês de 2026, para o gráfico mês a mês
        mensal = {}
        for mes in range(1, 13):
            try:
                itens = siconfi("msc_orcamentaria", {
                    "id_ente": ID_ENTE, "an_referencia": 2026, "me_referencia": mes, "co_tipo_matriz": "MSCC",
                    "classe_conta": 6, "id_tv": "ending_balance"})
            except Exception as e:
                print("  mes", mes, "sem dado:", e)
                break
            if not itens:
                break
            mensal[mes] = [x for x in itens if (x.get("natureza_despesa") or "")[:6] in ("339014", "339015")]
            print("  msc 2026 mes", mes, len(itens))
        grava("s3_msc_diarias_2026.json", mensal, SICONFI + "/msc_orcamentaria (MSCC, classe 6, saldo final, só diárias)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tudo")
