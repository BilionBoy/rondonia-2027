"""Junta os módulos reescritos (a1-v3/M01..M15.md) num único .md da V3, com glossário e ficha técnica."""
import re
from pathlib import Path

ENT = Path(__file__).parent / "fonte"  # cópia dos textos-fonte; originais em sima/api/docs/produto/0-raiz/entendimento/
V2 = (ENT / "SIMA_A1_PROJETO_INSTITUCIONAL_2027_V2_COMPLETO_FINAL.md").read_text(encoding="utf-8").split("\n")
ini = next(i for i, l in enumerate(V2) if l.startswith("# ANEXO EDITORIAL VI"))
fim = next(i for i, l in enumerate(V2) if i > ini and l.startswith("# "))
glossario = [l for l in V2[ini + 1:fim] if not re.match(r"^- \*\*A[123]:\*\*", l) and l.strip() != "---"
             and not l.startswith("**Convenção de linguagem")]

partes = ["---", 'titulo: "SIMA — Programa de Modernização 2027–2030"', 'versao: "3.0"', "---", ""]
for n in range(1, 16):
    t = (ENT / "a1-v3" / f"M{n:02d}.md").read_text(encoding="utf-8").strip()
    partes += [t, ""]
partes += ["# ANEXO I — GLOSSÁRIO E CONVENÇÕES", ""] + glossario + [""]
partes += ["# FICHA TÉCNICA", "",
           "**SIMA — Modernização Integrada da Gestão de Materiais, Almoxarifado e Patrimônio da Educação Estadual de Rondônia.**",
           "",
           "Programa de Modernização 2027–2030 — concepção institucional em apresentação. "
           "Sua instituição formal e sua execução dependem dos atos, autorizações e instrumentos próprios da Administração.",
           "",
           "Versão 3.0 · outubro de 2026 · concepção técnica e editorial: NextTech Ecosystem.", ""]
saida = ENT / "SIMA_A1_PROGRAMA_MODERNIZACAO_2027_2030_V3.md"
saida.write_text("\n".join(partes), encoding="utf-8")
print(saida, sum(1 for _ in saida.open()), "linhas")
