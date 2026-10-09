# Rondônia em números

Painel sobre o orçamento de Rondônia e a transição de governo, em três abas. É feito para alguém sem tempo: números grandes, uma ideia por tela, e tudo clicável para quem quiser se aprofundar.

| Aba | Arquivo no ar | O que mostra |
|---|---|---|
| Rondônia em números | `site/numeros.html` | o orçamento de 2026 em 9 etapas |
| O que não aparece | `site/nao-aparece.html` | onde o dinheiro sai do retrato público, em 5 telas |
| Convênios da SEAS | `site/convenios.html` | convênios e termos de fomento da SEAS, 2019–2026 |

**A raiz do site (`/`) abre o painel com as três abas.** `site/index.html` e `site/painel.html` são o mesmo arquivo.

- **No ar:** a pasta `site/`, publicada na Vercel com Root Directory = `site`. As páginas levam `noindex`.
- **Para gerar tudo:** `python3 build.py && python3 nao-aparece/build_s3.py && python3 convenios/build_convenios.py`.
- **Para ver localmente:** `python3 -m http.server 8765 --bind 127.0.0.1` e abrir `http://127.0.0.1:8765/esbocos/painel.html`.

## Primeira aba: as 9 etapas

- **Para editar:** `esbocos/src/rondonia.html`.
- **Para gerar:** `python3 build.py`. Ele injeta dados, fontes e three.js e gera `esbocos/*.html` e `site/`.
- **Para testar localmente:** `python3 -m http.server 8765 --bind 127.0.0.1` e abrir `http://127.0.0.1:8765/esbocos/rondonia.html#N`, onde N é o número da etapa.

## Segunda aba: "O que não aparece"

Tela separada, com visual próprio, sobre onde o dinheiro sai do retrato público: empenho sem entrega, diárias fora do portal, dinheiro livre (fonte 1500) e emendas. Não mexe nas 9 etapas.

- **Para editar:** `nao-aparece/src/nao-aparece.html`. O painel que junta as abas é `nao-aparece/src/painel.html`, gerado por este mesmo build.
- **Para coletar:** `python3 coleta_s3.py` baixa do Portal da Transparência RO (notas de empenho, detalhe de cada nota a partir de R$ 200 mil, diárias) e do Siconfi (RREO Anexo 7, MSC). O bruto fica em `dados-fonte/s3_*` e não vai para o git.
- **Para gerar:** `python3 nao-aparece/build_s3.py`. Grava `dados-fonte/s3_resumo.json`, `esbocos/` e `site/`.

Todas as fontes, consultas, datas de coleta e regras de leitura estão em [FONTES.md](FONTES.md).

Cuidados: as diárias do portal vêm com linhas repetidas (são removidas); o "pago" das notas de 2025 quase não aparece no portal; o Tesouro abre restos a pagar só por Poder, não por secretaria.

## Terceira aba: "Convênios da SEAS"

Uma tela com tudo o que a SEAS assinou: convênios, termos de fomento e de cooperação. Mostra o total por ano, filtra entre municípios e entidades, e lista quem mais recebeu, com número, processo SEI e objeto de cada instrumento. Os 496 registros abrem em tabela paginada, com busca e CSV.

- **Para coletar:** `python3 coleta_convenios.py SEAS`. Serve para qualquer órgão; é só trocar a sigla. Grava `dados-fonte/s4_convenios_seas.json` e `.csv`.
- **Para gerar:** `python3 convenios/build_convenios.py`. Grava `esbocos/convenios.html` e `site/convenios.html`.
- **Para editar:** `convenios/src/convenios.html`. O visual (`convenios/src/_base.css` e `_base.js`) é uma cópia do da segunda aba, para uma aba não quebrar a outra.
- **População (para a conta de R$ por habitante):** `dados-fonte/ibge/ro-populacao-censo2022.json`, do IBGE, Censo 2022.

O portal não tem link por convênio; cada linha leva à página geral de convênios e traz o número do processo SEI.

**Relatório em PDF da SEAS** (botão "Baixar relatório em PDF" na aba): `python3 convenios/build_relatorio.py` gera `esbocos/relatorio-seas.html`, `esbocos/relatorio-seas.pdf` e `site/relatorio-seas.pdf`, usando o Chrome para imprimir. São 7 seções:
1. resumo;
2. orçamento de 2026 da SEAS e dos fundos da área;
3. convênios ano a ano;
4. os 30 que mais receberam;
5. todos os instrumentos em ordem de assinatura;
6. emendas executadas pela SEAS (OFIP, não oficial);
7. fontes e método.

Rode o build de novo sempre que coletar convênios.

## Detalhe da primeira aba: as 9 etapas

| # | Etapa | Fonte |
|---|---|---|
| 1 | O dinheiro de 2026: os 81 órgãos em mosaico | Portal da Transparência RO, 7/10/2026 |
| 2 | O ano passou: o comprometido mês a mês | Portal da Transparência RO |
| 3 | Os 21 órgãos abaixo do ritmo do ano | Portal + régua de leitura do painel (cálculo, não regra legal) |
| 4 | Para onde vai: salário, custeio, obra (pago, a pagar, livre) | Portal, despesa por grupo de natureza |
| 5 | O orçamento mexido: 359 atos, R$ 4,4 bi | Diário Oficial do Estado (créditos adicionais) |
| 6 | A saúde do Estado: folha × limite, caixa × dívida, renúncia | RGF do Executivo, 2º quadrimestre 2026 (Siconfi/Tesouro) e SEFIN/SIDIEC |
| 7 | O Estado no mapa, com as emendas por município e deputado | Malha IBGE, Censo 2022; emendas: OFIP + planilha "Emendas 2025–2026" (**não oficial, sem 2022**) |
| 8 | A virada: o que passa de 2026 para 2027 | Portal (ponto de partida) + cenário com o ritmo médio de 2026; cargos: LC 965/2017 |
| 9 | Resumo: 5 números-chave e o dinheiro por área, tudo clicável | Portal, RGF, Diário Oficial |

## O que foi conferido na fonte oficial (7/10/2026)

- **Orçamento:** os valores pagos por órgão e por função batem centavo por centavo com o Portal da Transparência RO.
- **RGF:** pessoal em 37,92% da RCL, caixa de R$ 6,11 bi, dívida consolidada de R$ 5,66 bi, precatórios vencidos de R$ 2,08 bi e DCL de −R$ 460 mi. Tudo bate com o Siconfi. A cópia está em `dados-fonte/rgf_executivo_2026_q2_siconfi.json`.
- **Emendas por município e deputado:** não conferidas em fonte oficial. A fonte é um observatório independente e não tem 2022. Parte do valor é de emenda de bancada e de comissão, mas aparece no nome de um deputado.

## Termos usados na tela

| Termo | Nome técnico | O que é |
|---|---|---|
| comprometido | empenhado | contrato ou pedido assinado |
| pago | pago | o dinheiro já saiu |
| a pagar | empenhado − pago | — |
| livre | saldo | sem contrato |

"Abaixo do ritmo" é um órgão com orçamento de R$ 20 mi ou mais e comprometimento 10 pontos ou mais abaixo do tempo decorrido (77%).

## Para depurar

O endereço `?foto` desliga as animações. `&tipo=N`, `&mun=N`, `&org=SIGLA`, `&lista=1`, `&restos=1` e `&cargos=1` abrem as fichas direto.
