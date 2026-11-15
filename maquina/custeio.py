"""Quanto o Estado gasta com veículos (combustível, manutenção, locação) e com aluguel de imóveis, 2023-2026.

Uso: python3 maquina/custeio.py      (só a biblioteca padrão)
Lê   dados-fonte/s3_empenhos_<ano>.json (lista de notas do Portal da Transparência RO),
     dados-fonte/s5_detalhes_por_chave_<ano>.json (ficha de cada nota: histórico, liquidado, CNPJ/CPF).
Grava dados-fonte/s8_custeio.json.

Regra: a nota entra pelo HISTÓRICO da ficha (o texto do próprio empenho), nunca pelo nome do credor.
  aluguel de imóvel ...... locação de imóvel, aluguel de prédio, sala, galpão ou casa
  locação de veículos .... locação de veículo, caminhonete, ônibus, ambulância, frota locada
  combustível ............ combustível, gasolina, diesel, etanol, ARLA, gerenciamento de abastecimento
  manutenção de veículos . manutenção de veículo/frota, peças, pneus, lubrificante, guincho, oficina mecânica
Fora: aeronave e embarcação, transporte escolar, água e esgoto, gás de cozinha, aluguel social, convênio e repasse,
diárias e compra de veículo ou máquina. Em 2025 a regra pelo histórico bate com a regra pelo elemento de despesa
(combustível R$ 74,0 mi × 73,9 mi; locação 77,2 × 77,1; imóveis 46,0 × 45,3).
Valor executado: pago da lista (2023, 2024 e 2026) e liquidado da ficha em 2025, ano em que o portal quase não mostra o pago.
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
sys.path.insert(0, str(RAIZ / "economia"))
from base import NOTA, reais  # noqa: E402

ANOS = (2023, 2024, 2025, 2026)
# Fora do Executivo (mesma lista da tela "Fica para 2027"): Legislativo, Judiciário, MP, TCE, Defensoria e seus fundos
OUTROS_PODERES = {"ALE", "TJ", "FUJU", "MP", "FUNDIMPER", "FRBL", "TCE", "FDI/TC", "DPE", "FUNDEP"}


def norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if unicodedata.category(c) != "Mn").upper()
    return re.sub(r"\s+", " ", s)


FORA = re.compile(r"AERONAVE|HELICOPTER|AVIAO|AVIOES|QAV|AVGAS|JET ?A|EMBARCAC|LANCHA|BARCO|BALSA|TRANSPORTE ESCOLAR"
                  r"|ABASTECIMENTO DE AGUA|AGUA POTAVEL|ESGOTAMENTO|SANEAMENTO|MEDICAMENT|ESTACIONAMENTO"
                  r"|GAS LIQUEFEITO|GLP|BOTIJ|GAS DE COZINHA|ALUGUEL SOCIAL|AUXILIO[ -]ALUGUEL|BOLSA[ -]ALUGUEL|BENEFICIO EVENTUAL"
                  r"|CONVENIO|TERMO DE FOMENTO|TERMO DE COLABORA|REPASSE|FUNDO A FUNDO|\bDIARIAS?\b|FOLHA (SUPLEMENTAR|DE PAGAMENTO)"
                  r"|AQUISICAO DE (\d+ |UM |UMA |01 )?(CAMINH|TRATOR|VEICUL|ONIBUS|MICRO|MOTOCICL|AMBULANC|TRITURADOR|ROCADEIRA|MOTOSSERRA"
                  r"|MOTOSERRA|GERADOR|MOTOBOMBA|PULVERIZADOR|SOPRADOR|CORTADOR|EQUIPAMENTO|MAQUINA|IMPLEMENT)")
VEICULO = r"(VEICUL|FROTA|AUTOMOT|VIATURA|MOTOCICL|MOTONETA|CAMINH|ONIBUS|AMBULANCI|PICK[ -]?UP|CAMINHONETE|MAQUINAS? PESADA|PATROL|TRATOR)"
COMBUSTIVEL = re.compile(r"COMBUSTIV|GASOLINA|DIESEL|ETANOL|\bARLA\b|ABASTECIMENTO (DE |DOS |DA )?(COMBUST|VEIC|FROTA|VIATURA)"
                         r"|GERENCIAMENTO (DE |DO )?ABASTEC|GESTAO (DE |DO )?ABASTEC")
MANUTENCAO = re.compile(r"MANUTEN\w*.{0,80}" + VEICULO + r"|PECAS?\b.{0,50}(" + VEICULO[1:-1] + r"|REPOSICAO)|\bPNEU|CAMARAS? DE AR"
                        r"|LUBRIFICANTE|OLEO (DE MOTOR|LUBRIF|HIDRAUL)|FILTROS? (DE )?(OLEO|AR|COMBUST)|GUINCHO|REBOQUE"
                        r"|FUNILARIA|RETIFICA|OFICINA MECANICA|SERVICOS MECANICOS|MECANICA (DE |EM )?VEIC|LAVAGEM.{0,30}" + VEICULO + r"|BATERIAS?.{0,30}" + VEICULO)
LOCACAO_VEIC = re.compile(r"LOCAC\w*.{0,60}" + VEICULO + r"|" + VEICULO + r"\w* LOCAD|FROTA LOCADA|ALUGUEL.{0,30}" + VEICULO)
IMOVEL = re.compile(r"LOCAC\w*.{0,40}IMOVE|ALUGUE[LI]S?\b.{0,40}(IMOVE|PREDIO|SALA|GALPAO|CASA|ESPACO|SEDE|INSTALAC)"
                    r"|IMOVE\w* LOCAD|IMOVE\w* ALUGAD|LOCAC\w* DE (UM |01 )?(PREDIO|SALA|GALPAO|CASA|ESPACO FISICO|AREA|TERRENO)"
                    r"|ALUGUEL MENSAL|ALUGUEIS?\b(?!.{0,30}(EQUIPAMENT|MAQUIN|VEICUL|TOLDO|TENDA|BANHEIRO|PALCO|SOM|IMPRESSOR|CONTAINER|GERADOR))")
NAO_IMOVEL = re.compile(r"(LOCAC|ALUGUE)\w*.{0,30}(EQUIPAMENT|MAQUIN|VEICUL|TOLDO|TENDA|BANHEIRO|PALCO|SONORIZ|IMPRESSOR|CONTAINER"
                        r"|GERADOR|ESTRUTURA|CAMARIM|ARQUIBANCADA|MOBILIARIO|COMPUTADOR|NOTEBOOK)")

TEMAS = {"combustivel": "Combustível", "manutencao": "Manutenção de veículos", "locacao": "Locação de veículos",
         "imovel": "Aluguel de imóveis"}


def tema(h):
    """Só o histórico decide (o elemento de 2026 no nosso arquivo está preso a ids antigos do portal)."""
    if FORA.search(h):
        return None
    if IMOVEL.search(h) and not NAO_IMOVEL.search(h):
        return "imovel"
    if LOCACAO_VEIC.search(h):
        return "locacao"
    if COMBUSTIVEL.search(h) and not re.search(r"MANUTEN|PECAS", h[:120]):
        return "combustivel"
    if MANUTENCAO.search(h):
        return "manutencao"
    if COMBUSTIVEL.search(h):
        return "combustivel"
    return None


def municipios():
    """Os 52 municípios de RO (IBGE), para achar no histórico onde fica o imóvel."""
    p = FONTE / "ibge" / "ro-populacao-censo2022.json"
    series = json.loads(p.read_text(encoding="utf-8"))[0]["resultados"][0]["series"]
    return sorted({s["localidade"]["nome"].replace(" - RO", "") for s in series}, key=len, reverse=True)


def formas(nome):
    """Jeitos de escrever o município no histórico: Alta Floresta D'Oeste, D OESTE, DO OESTE, DOESTE."""
    n = norm(nome)
    fs = {n}
    if "D'OESTE" in n:
        fs |= {n.replace("D'OESTE", x) for x in ("D OESTE", "DO OESTE", "DOESTE", "D` OESTE")}
    if n == "PORTO VELHO":
        fs.add("PVH")
    return fs


def main():
    nomes_mun = municipios()
    canon = {f: n for n in nomes_mun for f in formas(n)}
    rx_mun = re.compile(r"\b(" + "|".join(re.escape(f) for f in sorted(canon, key=len, reverse=True)) + r")\b")

    notas = []
    for ano in ANOS:
        lista = json.loads((FONTE / f"s3_empenhos_{ano}.json").read_text(encoding="utf-8"))["dados"]
        det = json.loads((FONTE / f"s5_detalhes_por_chave_{ano}.json").read_text(encoding="utf-8"))["detalhes"]
        for n in lista:
            d = det.get(f"{ano}|{n['unidadeGestora']}|{n['numeroEmpenho']}") or {}
            h = norm(d.get("Histórico"))
            t = tema(h)
            if not t:
                continue
            liq = reais(d.get("Valor liquidado no exercício da emissão do empenho"))
            pago = reais(n["valorPago"])
            doc = (d.get("CPF/CNPJ do credor") or "").strip()
            mun = rx_mun.search(h) if t == "imovel" else None
            notas.append({"ano": ano, "tema": t, "ug": n["unidadeGestora"], "ne": n["numeroEmpenho"],
                          "credor": n["credor"].strip(), "pf": not re.search(r"\d{2}\.\d{3}\.\d{3}/\d{4}", doc),
                          "emp": reais(n["valorEmpenhado"]), "pago": pago, "liq": liq,
                          "exec": liq if ano == 2025 else pago, "tipo": d.get("Tipo de empenho", ""),
                          "mun": canon.get(mun[1]) if mun else None, "hist": (d.get("Histórico") or "")[:300],
                          "link": NOTA + n["linkDetalhes"], "data": n["dataDocumentoFormatada"]})

    outros = [x for x in notas if x["ug"] in OUTROS_PODERES]
    notas = [x for x in notas if x["ug"] not in OUTROS_PODERES]

    def soma(ns, campo="exec"):
        return round(sum(x[campo] for x in ns), 2)

    out = {"meta": {"fonte": "Portal da Transparência RO: notas de empenho (lista e ficha de cada nota), 2023-2026, só o Poder Executivo",
                    "coleta": "lista e fichas de 2026 em 30/10/2026; anos anteriores fechados",
                    "regra": __doc__.split("Regra:")[1].strip()},
           "temas": {}}
    for t, nome in TEMAS.items():
        ns = [x for x in notas if x["tema"] == t]
        anos = {str(a): {"empenhado": soma([x for x in ns if x["ano"] == a], "emp"), "executado": soma([x for x in ns if x["ano"] == a]),
                         "pago": soma([x for x in ns if x["ano"] == a], "pago"), "notas": sum(x["ano"] == a for x in ns)} for a in ANOS}
        n26 = [x for x in ns if x["ano"] == 2026]
        ug = defaultdict(list)
        for x in n26:
            ug[x["ug"]].append(x)
        ug25 = defaultdict(float)
        for x in ns:
            if x["ano"] == 2025:
                ug25[x["ug"]] += x["exec"]
        por_ug = sorted(({"ug": k, "executado": soma(v), "empenhado": soma(v, "emp"), "notas": len(v),
                          "credores": len({x["credor"] for x in v}), "executado_2025": round(ug25.get(k, 0), 2)}
                         for k, v in ug.items()), key=lambda x: -x["executado"])
        cred = defaultdict(list)
        for x in n26:
            cred["Pessoa física (locador)" if (t == "imovel" and x["pf"]) else x["credor"]].append(x)
        por_credor = sorted(({"credor": k, "executado": soma(v), "empenhado": soma(v, "emp"), "notas": len(v),
                              "orgaos": sorted({x["ug"] for x in v})} for k, v in cred.items()), key=lambda x: -x["executado"])[:25]
        maiores = sorted(n26, key=lambda x: -max(x["emp"], x["pago"]))[:40]
        bloco = {"nome": nome, "anos": anos, "orgaos": por_ug, "credores": por_credor,
                 "notas": [{k: x[k] for k in ("ug", "ne", "data", "emp", "pago", "hist", "link")} |
                           {"credor": "Pessoa física" if (t == "imovel" and x["pf"]) else x["credor"]} for x in maiores]}
        if t == "imovel":
            # quantos imóveis: cada locador por órgão conta um contrato de aluguel pago em 2026 (estimativa por baixo:
            # um locador com dois imóveis no mesmo órgão conta um)
            pares = {(x["ug"], x["credor"]) for x in n26 if x["exec"] > 0 or x["emp"] > 0}
            mun = Counter()
            for (ug_, cr) in pares:
                ms = {x["mun"] for x in n26 if x["ug"] == ug_ and x["credor"] == cr and x["mun"]}
                mun[sorted(ms)[0] if ms else "Não informado no histórico"] += 1
            bloco["locadores_ano"] = {str(a): len({(x["ug"], x["credor"]) for x in ns if x["ano"] == a}) for a in ANOS}
            bloco["locadores_2026"] = {"contratos": len(pares), "pf": sum(1 for (u, c) in pares if any(x["pf"] for x in n26 if x["credor"] == c)),
                                       "orgaos": len({u for u, _ in pares}), "municipios": dict(mun.most_common())}
        out["temas"][t] = bloco
    out["outros_poderes"] = {t: {str(a): round(sum(x["exec"] for x in outros if x["tema"] == t and x["ano"] == a), 2) for a in ANOS}
                             for t in TEMAS}
    veic = [x for x in notas if x["tema"] != "imovel"]
    out["frota_total"] = {str(a): {"executado": soma([x for x in veic if x["ano"] == a]), "empenhado": soma([x for x in veic if x["ano"] == a], "emp")}
                          for a in ANOS}
    (FONTE / "s8_custeio.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for t, b in out["temas"].items():
        print(f"{b['nome']:26}", " ".join(f"{a}: R$ {v['executado'] / 1e6:7.1f} mi ({v['notas']})" for a, v in b["anos"].items()))
    print("imóveis 2026:", {k: v for k, v in out["temas"]["imovel"]["locadores_2026"].items() if k != "municipios"})


if __name__ == "__main__":
    main()
