# Fontes de dados

Todas as fontes usadas pelo painel "Rondônia em números" (as 9 etapas) e pela aba "O que não aparece". São públicas, sem login.

Última coleta da aba "O que não aparece": **08/10/2026, entre 16:46 e 17:02**. As 9 etapas usam a coleta de **07/10/2026**.

## Como refazer

```bash
python3 coleta_s3.py tudo          # baixa tudo de novo (uns 15 minutos; o detalhe das notas é a parte lenta)
python3 nao-aparece/build_s3.py    # gera dados-fonte/s3_resumo.json, esbocos/ e site/
python3 build.py                   # só se mudar as 9 etapas
python3 -m http.server 8765        # e abrir http://127.0.0.1:8765/esbocos/painel.html
```

Só precisa de Python 3, sem bibliotecas extras. Para coletar uma parte só: `python3 coleta_s3.py empenhos|detalhes|diarias|orgaos|rreo|msc|msc_mensal`.

## 1. Tesouro Nacional · Siconfi (contabilidade oficial enviada pelo Estado)

API pública: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt` · documentação: https://apidatalake.tesouro.gov.br/docs/siconfi/ · Rondônia é `id_ente=11`.

| Arquivo | O que é | Consulta | Registros |
|---|---|---|---|
| `dados-fonte/s3_rreo_anexo7.json` | Restos a pagar por Poder, 2019 a 2025 | `rreo?an_exercicio={ano}&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2007&id_ente=11` | 7 anos |
| `dados-fonte/s3_msc_classe6.json` | Execução da despesa por fonte e natureza (saldo final de dez/2025, jun/2026 e ago/2026) | `msc_orcamentaria?id_ente=11&an_referencia={ano}&me_referencia={mes}&co_tipo_matriz=MSCC&classe_conta=6&id_tv=ending_balance` (paginado por `offset`) | 3 meses, cerca de 12 mil linhas cada |
| `dados-fonte/s3_msc_diarias_2026.json` | Só as diárias (naturezas 3.3.90.14 civis e 3.3.90.15 militares), jan a ago/2026 | mesma consulta, mês a mês | 8 meses |
| `dados-fonte/rgf_executivo_2026_q2_siconfi.json` | RGF do Executivo, 2º quadrimestre de 2026 (usado nas 9 etapas) | `rgf` | 1 |

Exemplo para conferir: [RREO Anexo 7 de 2025](https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?an_exercicio=2025&nr_periodo=6&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2007&id_ente=11).

Como se lê:
- Restos a pagar **não processados** = empenhado e não entregue. O total cancelado (R$ 1,21 bi) é a soma de `RestosAPagarNaoProcessadosCancelados` do Poder Executivo, sem intraorçamentários.
- Na MSC, o empenhado é a soma das contas `622130100` a `622130400`, e o pago é a conta `622130400`. Poder Executivo = `poder_orgao` começando por `101`.
- A antiga "Fonte 100" hoje é a fonte `1500` (recursos não vinculados de impostos). Neste painel, `1500` e `1501` contam como dinheiro livre.

## 2. Portal da Transparência de Rondônia (CGE-RO)

Site: https://transparencia.ro.gov.br. Não tem API documentada. A coleta usa os mesmos endereços que o site chama, com o token do formulário (`__RequestVerificationToken`).

| Arquivo | O que é | Endereço | Registros |
|---|---|---|---|
| `dados-fonte/s3_empenhos_2025.json` | Todas as notas de empenho de 2025 (órgão, credor, empenhado, pago) | POST `/Despesa/FiltrarEmpenhos` (`AnoAvancado`, `MesInicialAvancado`, `MesFinalAvancado`, `start`, `length`) | 76.926 |
| `dados-fonte/s3_empenhos_2026.json` | Todas as notas de empenho de 2026 | idem | 58.692 |
| `dados-fonte/s3_detalhes_2025.json` | Detalhe de cada nota de R$ 200 mil ou mais: tipo, liquidado, pago, fonte, programa, ação, CNPJ, histórico | GET `/Despesa/notas-de-empenho/detalhes?id={id}` | 9.032 (90,9% do valor) |
| `dados-fonte/s3_detalhes_2026.json` | idem, 2026 | idem | 6.594 (87,4% do valor) |
| `dados-fonte/s3_diarias_2025.json` | Diárias de 2025, pessoa por pessoa | POST `/diarias/filtrar` (`Exercicio`, `MesInicial`, `MesFinal`) | 64.785 linhas, 48.929 sem repetição |
| `dados-fonte/s3_diarias_2026.json` | Diárias de 2026 | idem | 31.036 linhas, 23.658 sem repetição |
| `dados-fonte/s3_diarias_orgaos.json` | Códigos do filtro "Órgão" das diárias | página `/diarias` | 81 |

Links diretos que o portal aceita:
- Uma nota: `https://transparencia.ro.gov.br/Despesa/notas-de-empenho/detalhes?id={id}` (exemplo: [SEDUC, Instituto Veritas, R$ 35,4 mi](https://transparencia.ro.gov.br/Despesa/notas-de-empenho/detalhes?id=21673254)).
- Diárias filtradas: `https://transparencia.ro.gov.br/diarias?Exercicio=2026&MesInicial=7&MesFinal=7&Orgao=SEDUC`.

Cuidados com o portal:
- **Diárias:** a lista devolve linhas repetidas. Elas são removidas pela chave solicitação + nome + período + valor + autorização.
- **Pago de 2025:** quase não aparece (88% das notas com pago zero). Por isso, em 2025 usamos o **liquidado** (entrega) do detalhe da nota, não o pago da lista.
- **Notas sem detalhe:** algumas notas não abrem (`id=0`), como as 3 em que o governador é credor.
- **Órgãos fora do filtro:** Governadoria, Casa Civil, Cerimonial, Gabinete do Vice, CONEPOD e IESPRO aparecem nas diárias, mas não no filtro de órgão.
- **Busca combinada:** o filtro por nome de credor ignora o filtro por elemento de despesa quando os dois são usados juntos.

Consulta manual feita em 08/10/2026 e registrada no `nao-aparece/build_s3.py` (constante `GOVERNADOR`): nome do governador no filtro de diárias de 2023 a 2026 (zero registros) e como credor de empenho (3 notas, R$ 36.159,36).

## 2b. Convênios da SEAS (terceira aba)

| Arquivo | O que é | Endereço | Registros |
|---|---|---|---|
| `dados-fonte/s4_convenios_seas.json` e `.csv` | Convênios, termos de fomento e termos de cooperação/colaboração da SEAS, de 2015 a 2026 (só há registros de 2019 em diante) | POST `/convenios/ConsultaConvenios` (`CodigoUnidadeGestora`, `TipoDocumento` = 2 convênio, 11 fomento, 13 cooperação; `Ano` obrigatório) | 496 (484 instrumentos e 12 rescisões) |

Coleta: `python3 coleta_convenios.py SEAS` (serve para qualquer órgão: troque a sigla). Build: `python3 convenios/build_convenios.py`. O portal não dá link por convênio, só a página geral (https://transparencia.ro.gov.br/convenios); o número do processo SEI vem em cada linha.

## 2c. Tecnologia no Estado (quarta aba), coleta de 12/10/2026

| Arquivo | O que é | Endereço | Registros |
|---|---|---|---|
| `dados-fonte/s5_contratos.json` e `.csv` | **Todos os contratos** de todos os órgãos, 2015–2026 (ano = ano de cadastro no portal) | POST `/contratos/consultacontratos` (`TipoDocumento=1`, `Ano`; sem filtro de órgão) | 9.611 |
| `tecnologia/revisao/R_*.json` | Revisão contrato a contrato do que é tecnologia (categoria, função, produto, nota), feita por 10 revisores sobre 2.062 contratos de 2023–2026 ou vigentes; regra em `tecnologia/revisao/_BRIEFING.md` | — | 751 de tecnologia |
| `dados-fonte/s5_empenhos_tic.json` | Notas de empenho do elemento de despesa 40 (TIC), 2023–2026, todos os Poderes, com a ficha de detalhe de cada nota | POST `/Despesa/FiltrarEmpenhos` (`CodElementoDespesa` = 33904000 e 44904000) + `/Despesa/notas-de-empenho/detalhes` | 3.445 |
| `dados-fonte/pca/2026/*.pdf` e `pca_2026_ti.json` | Planos de Contratações Anuais 2026 (portarias no DOE) e os itens de TI extraídos | GET `/Licitacoes/FiltrarAnexosPac?filtroId=` (página `/licitacoes/planoanualdecontratacoes`) | 38 PDFs |
| `dados-fonte/s5_empresas.json` | Cadastro público de cada CNPJ (atividade, abertura, porte, município, situação). Sem nomes de sócios | BrasilAPI `/api/cnpj/v1/{cnpj}` (dados da Receita Federal) | — |
| `dados-fonte/s5_tecnologia.json` | Base consolidada da aba (gerada pelo build) | — | — |

Ordem: `python3 coleta_contratos.py` → `python3 tecnologia/classificar.py` (triagem por regra) → revisão (`tecnologia/revisao/`) → `python3 tecnologia/coleta_empenhos.py` → `python3 tecnologia/build_tecnologia.py` → `python3 tecnologia/coleta_empresas.py` → build de novo.

**Regras de leitura da aba**
- **Foco:** contratos cadastrados de 2023 a 2026, mais os anteriores ainda vigentes em 12/10/2026. Os de 2015 a 2022 ficam guardados em `s5_contratos.json`, fora das contas.
- **Valor:** é o "valor global" do portal, o total previsto para toda a vigência, sem aditivos, somado pelo ano de cadastro. Não é gasto anual.
- **Frota e abastecimento** (sistema e cartão) ficam em bloco separado, porque o valor inclui o combustível e as peças.
- **Fora das somas:**
  - 10 rescisões;
  - 1 contrato com valor implausível: o ERP da SOPH, de R$ 135,2 mi, marcado em `VALOR_A_CONFERIR`.
- **Órgão vazio no portal:** é deduzido pelo prefixo do processo SEI (ex.: 0040 = SOPH).
- **Empenho:**
  - o fundo aparece pelo órgão gestor (FES = SESAU, FUNESP = SESDEC, FUNDAT = SEFIN);
  - TJ, ALE, TCE, MP e DPE (e seus fundos) ficam fora das somas do Executivo.
- **Equipamento de informática** (4.4.90.52) não tem elemento próprio. Por isso só aparece pelos contratos.
- **"Repetidos":** a mesma função contratada separadamente por 2 ou mais órgãos. A compra de bens (computadores, periféricos etc.) não entra.

## 3. Dados das 9 etapas (coleta de 07/10/2026)

| Arquivo | Fonte |
|---|---|
| `dados-fonte/s1_dados.json` | Portal da Transparência RO e COGES: LOA 2026 por órgão, mês, função e grupo; emendas por fonte e tipo |
| `dados-fonte/s1_lazy_doe-atos.json` | Diário Oficial do Estado: 454 atos de crédito adicional de 2026 |
| `dados-fonte/s1_lazy_emendas-liberacoes.json` | Liberações de emendas por deputado e município (OFIP + planilha; **não oficial**, sem 2022) |
| `dados-fonte/s1_lazy_renuncia.json` | SEFIN / SIDIEC: renúncia de receita 2017–2026 |
| `dados-fonte/s2_cargos.json` | LC 965/2017 e decretos de estrutura: 1.950 cargos comissionados, órgãos e unidades gestoras |
| `dados-fonte/s2_estatais.json` | 15 estatais e conselhos |
| `dados-fonte/ibge/` | IBGE: malha e nomes dos 52 municípios |

A aba "O que não aparece" também usa o `s1_dados.json` (empenhado por órgão e emendas) e o `s2_cargos.json` (nome por extenso das siglas).

## 4. O que é gerado

`dados-fonte/s3_resumo.json` reúne os números e as tabelas que a aba mostra:

| Tabela | Linhas |
|---|---|
| Notas sem entrega de 2025 | 2.506 |
| Notas sem entrega de 2026 | 1.719 |
| Restos a pagar do Tesouro | 84 |
| Empenhos parados de 2026 | 230 |
| Diárias na contabilidade | 1.824 |
| Diárias no portal por órgão e mês | 828 |
| Empenhado por órgão × notas | 81 |
| Viagens (agências, aéreas, táxi aéreo, hotéis) | 1.446 |

Esse arquivo vai junto com a página. Os brutos `s3_empenhos_*`, `s3_detalhes_*`, `s3_diarias_*` e `s3_msc_classe6.json` ficam fora do git (`.gitignore`), porque são grandes e trazem nome de servidor nas diárias. Para refazê-los, use o `coleta_s3.py`.

## 5. Regras de leitura

- **"Sem entrega"** = valor empenhado menos o liquidado (no ano e depois), nota por nota. Não prova irregularidade: pode ser contrato ainda em execução.
- **R$ 718 mi** dos R$ 2,42 bi sem entrega de 2025 têm como credor um ente público (fundos, secretarias, municípios). Só de fornecedores privados são **R$ 1,70 bi**.
- **"Sem nota visível"** = empenhado por órgão (despesa do portal) menos a soma das notas listadas no mesmo portal. Parte pode ser folha publicada de outra forma.
- **Diárias:** a contabilidade conta pelo mês do pagamento; o portal, pelo mês de início da viagem.
- **"Orçamento secreto"** é o termo das emendas de relator do Congresso (2020–2022). Aqui o certo é **"orçamento opaco"**.
- Empenho global e estimativo são legais (Lei 4.320/64, art. 60).
