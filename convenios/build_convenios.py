"""Monta a aba "Convênios da SEAS".

Uso: python3 convenios/build_convenios.py   (depois de python3 coleta_convenios.py SEAS)
Lê dados-fonte/s4_convenios_seas.json e grava esbocos/convenios.html e site/convenios.html.
O visual (convenios/src/_base.css e _base.js) é uma cópia do da aba "O que não aparece", para as duas abas não dependerem uma da outra.
"""
import base64
import json
import re
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parent
FONTE = RAIZ / "dados-fonte"
PORTAL = "https://transparencia.ro.gov.br/convenios"
NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def main():
    bruto = json.loads((FONTE / "s4_convenios_seas.json").read_text(encoding="utf-8"))
    regs = []
    for r in bruto["dados"]:
        regs.append({"tipo": r["tipo"], "ano": r["ano_consulta"], "numero": r["numero"], "processo_sei": r["processo_sei"],
                     "assinatura": r["assinatura"], "contratado": r["contratado"], "valor": r["valor"], "tem_aditivo": r["tem_aditivo"],
                     "objeto": r["objeto"], "rescisao": bool(re.search(r"RESCIS", r["numero"], re.I))})
    linhas = [[r["ano"], r["tipo"], r["numero"], r["processo_sei"], r["assinatura"], r["contratado"], r["valor"] or 0,
               r["tem_aditivo"], r["objeto"], PORTAL] for r in sorted(regs, key=lambda x: (-x["ano"], -(x["valor"] or 0)))]
    tabela = {"id": "convenios-seas", "titulo": "Convênios, termos de fomento e de cooperação da SEAS", "curto": "SEAS",
              "fonte": "Portal da Transparência de Rondônia (CGE-RO)",
              "consulta": "Convênios: órgão SEAS, tipos Convênio, Termo de Fomento e Termo de Cooperação/Colaboração, ano a ano de 2015 a 2026",
              "url": PORTAL, "nota": "Rescisões aparecem como linhas próprias e não entram nos totais da tela.",
              "coletado_em": bruto["meta"]["coletado_em"],
              "colunas": [["Ano", "n"], ["Tipo", "t"], ["Número", "t"], ["Processo SEI", "t"], ["Assinatura", "d"], ["Quem recebe", "t"],
                          ["Valor global", "r"], ["Aditivo", "t"], ["Objeto", "t"], ["Fonte", "u"]],
              "linhas": linhas}
    dados = {"coletado_em": bruto["meta"]["coletado_em"], "registros": regs, "links": {"portal": PORTAL, "detalhe": ""},
             "tabelas": {"convenios-seas": tabela}, "nomes": {}}
    payload = json.dumps(dados, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    fonte = base64.b64encode((RAIZ / "vendor" / "fontes" / "inter-var.woff2").read_bytes()).decode()
    css_fonte = f"@font-face{{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:block;src:url(data:font/woff2;base64,{fonte}) format('woff2')}}"
    h = (AQUI / "src" / "convenios.html").read_text(encoding="utf-8")
    h = (h.replace("/*__BASE_CSS__*/", (AQUI / "src" / "_base.css").read_text(encoding="utf-8"))
          .replace("/*__BASE_JS__*/", (AQUI / "src" / "_base.js").read_text(encoding="utf-8"))
          .replace("/*__FONTES__*/", css_fonte, 1)
          .replace("/*__DADOS_CONV__*/null", payload))
    (RAIZ / "esbocos" / "convenios.html").write_text(h, encoding="utf-8")
    (RAIZ / "site" / "convenios.html").write_text(h.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n' + NOINDEX, 1), encoding="utf-8")
    print("esbocos/ e site/convenios.html", round(len(h) / 1024), "KB,", len(regs), "registros")


if __name__ == "__main__":
    main()
