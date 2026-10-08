# Rondônia em números

Apresentação de uma tela só, em 9 etapas, sobre o orçamento de 2026 e a transição de governo. Ela é feita para alguém sem tempo: números grandes, uma ideia por etapa, e tudo clicável para quem quiser se aprofundar.

- **No ar:** a pasta `site/`, publicada na Vercel com Root Directory = `site`. As páginas levam `noindex`.
- **Para editar:** `esbocos/src/rondonia.html`.
- **Para gerar:** `python3 build.py`. Ele injeta dados, fontes e three.js e gera `esbocos/*.html` e `site/`.
- **Para testar localmente:** `python3 -m http.server 8765 --bind 127.0.0.1` e abrir `http://127.0.0.1:8765/esbocos/rondonia.html#N`, onde N é o número da etapa.

## As 9 etapas

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
