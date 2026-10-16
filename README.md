# Rondônia em números

Painel sobre o orçamento de Rondônia e a transição de governo, em cinco abas. É feito para alguém sem tempo: números grandes, uma ideia por tela, e tudo clicável para quem quiser se aprofundar.

| Aba | Arquivo no ar | O que mostra |
|---|---|---|
| Rondônia em números | `site/numeros.html` | o orçamento de 2026 em 9 etapas |
| O que não aparece | `site/nao-aparece.html` | onde o dinheiro sai do retrato público, em 5 telas |
| Convênios da SEAS | `site/convenios.html` | convênios e termos de fomento da SEAS, 2019–2026 |
| Quem vende ao Estado | `site/empresas.html` | todas as empresas que receberam empenho em 2023–2026, por ano, órgão, modalidade e tema (tecnologia, frota) |
| Tecnologia no Estado | `site/tecnologia.html` | todos os contratos de tecnologia do Estado, 2023–2026: por órgão, tipo, função repetida, vencimento e empresa |

**A raiz do site (`/`) abre o painel com as cinco abas.** `site/index.html` e `site/painel.html` são o mesmo arquivo.

- **No ar:** a pasta `site/`, publicada na Vercel com Root Directory = `site`. As páginas levam `noindex`.
- **Para gerar tudo:** `python3 build.py && python3 nao-aparece/build_s3.py && python3 convenios/build_convenios.py && python3 tecnologia/build_tecnologia.py`.
- **Para ver localmente:** `python3 -m http.server 8765 --bind 127.0.0.1` e abrir `http://127.0.0.1:8765/esbocos/painel.html`.

**Links das notas de 2026 mudam.** O Portal recarrega o ano corrente e, ao recarregar, troca o endereço (`?id=`) de todas as notas de 2026; os de anos fechados não mudam. Em 15/10/2026 todos os links de 2026 abriam outra nota e foram trocados pelos novos (165 mil ocorrências em `dados-fonte/`, `esbocos/` e `site/`), casando número da nota e órgão, sem mudar valor nenhum. Antes de apresentar, confira uma nota de 2026 no Portal; se abrir outra, refaça a coleta de 2026 (`coleta_s3.py`, que consulta mês a mês) e troque os endereços da mesma forma.

**Nenhum link abre JSON ou API.** Quem lê é o governador. Todo dado abre o painel de dados de origem, com busca, fonte, data da coleta e CSV. Links para a API do Tesouro (`apidatalake.tesouro.gov.br`) viram botão que abre a tabela correspondente no painel, já filtrada pelo ano quando o link é de um ano. O "Conferir na fonte" dessas tabelas leva ao Siconfi, não à API; o endereço da API aparece só como texto em "Consulta usada" (regra de 15/10/2026).

## Moldes de documento (propostas e planos em PDF)

Para fazer um documento novo no padrão do plano SISPAC-RO, escreve-se só um `conteudo.yaml`, sem HTML nem CSS.
- **Para gerar:** `python3 moldes/gerar.py moldes/exemplos/<nome>/conteudo.yaml`.
- **Manual e catálogo de blocos:** [moldes/README.md](moldes/README.md).
- **Exemplo de referência:** `moldes/exemplos/sispac-ro/`.

## Primeira aba: as 9 etapas

- **Para editar:** `esbocos/src/rondonia.html`.
- **Para gerar:** `python3 build.py`. Ele injeta dados, fontes e three.js e gera `esbocos/*.html` e `site/`.
- **Para testar localmente:** `python3 -m http.server 8765 --bind 127.0.0.1` e abrir `http://127.0.0.1:8765/esbocos/rondonia.html#N`, onde N é o número da etapa.

## Segunda aba: "O que não aparece"

Tela separada, com visual próprio, sobre onde o dinheiro sai do retrato público: empenho sem entrega, diárias fora do portal, dinheiro livre (fonte 1500) e emendas. Não mexe nas 9 etapas.

- **Para editar:** `nao-aparece/src/nao-aparece.html`. O painel que junta as abas é `nao-aparece/src/painel.html`, gerado por este mesmo build.
- **Para coletar:** `python3 coleta_s3.py` baixa do Portal da Transparência RO (notas de empenho, detalhe de cada nota a partir de R$ 200 mil, diárias) e do Siconfi (RREO Anexo 7, MSC). O bruto fica em `dados-fonte/s3_*` e não vai para o git.
- **Para gerar:** `python3 nao-aparece/build_s3.py`. Grava `dados-fonte/s3_resumo.json`, `esbocos/` e `site/`.
- **Tela 6, "Fica para 2027":** o que o Executivo empenhou em 2026 e ainda não pagou (MSC de setembro de 2026: R$ 1,08 bi, sendo R$ 151 mi já entregues) e os restos de anos anteriores ainda em aberto (RREO 2026, 4º bimestre: entrou com R$ 1,87 bi, R$ 480 mi em aberto em agosto). As fontes ficam em `dados-fonte/s3_msc_a_pagar_2026_09.json`, `s3_rreo_2026_b4.json` e `s3_empenhos_2026.json`. **Para gerar só esta tela:** `cd nao-aparece && python3 build_a_pagar.py` (acrescenta ao `s3_resumo.json` e regera as páginas; o `build_s3.py` completo também a inclui). A lista de órgãos tira os que não são do Executivo (ALE, TJ, FUJU, MP, FUNDIMPER, FRBL, TCE, FDI/TC, DPE, FUNDEP). Ao sair o RREO do 6º bimestre (janeiro de 2027), trocar a MSC de setembro pelo valor inscrito em restos a pagar.

Todas as fontes, consultas, datas de coleta e regras de leitura estão em [FONTES.md](FONTES.md).

Cuidados: as diárias do portal vêm com linhas repetidas (são removidas); o "pago" das notas de 2025 quase não aparece no portal; o Tesouro abre restos a pagar só por Poder, não por secretaria.

## Terceira aba: "Convênios da SEAS"

Uma tela com tudo o que a SEAS assinou: convênios, termos de fomento e de cooperação. Mostra o total por ano, filtra entre municípios e entidades, e lista quem mais recebeu, com número, processo SEI e objeto de cada instrumento. Os 496 registros abrem em tabela paginada, com busca e CSV.

- **Para coletar:** `python3 coleta_convenios.py SEAS`. Serve para qualquer órgão; é só trocar a sigla. Grava `dados-fonte/s4_convenios_seas.json` e `.csv`.
- **Para gerar:** `python3 convenios/build_convenios.py`. Grava `esbocos/convenios.html` e `site/convenios.html`.
- **Para editar:** `convenios/src/convenios.html`. O visual (`convenios/src/_base.css` e `_base.js`) é uma cópia do da segunda aba, para uma aba não quebrar a outra.
- **População (para a conta de R$ por habitante):** `dados-fonte/ibge/ro-populacao-censo2022.json`, do IBGE, Censo 2022.

O portal não tem link por convênio; cada linha leva à página geral de convênios e traz o número do processo SEI.

**Botão "Documentos em PDF"** (na aba): abre um menu com os PDFs da lista `DOCUMENTOS` de `convenios/build_convenios.py`. Hoje são o Relatório da SEAS e o Raio-X da Tecnologia 2026. O Plano SISPAC-RO e o programa SIMA saíram do menu e de `site/` em 15/10/2026, a pedido do Dhiogo; os moldes continuam em `moldes/exemplos/`. Para incluir um documento:
1. ponha o PDF em `site/` (o molde copia com `--site`);
2. acrescente uma linha na lista `DOCUMENTOS`;
3. rode `python3 convenios/build_convenios.py`.

O build para se faltar algum PDF da lista.

**Relatório em PDF da SEAS**: `python3 convenios/build_relatorio.py` gera `esbocos/relatorio-seas.html`, `esbocos/relatorio-seas.pdf` e `site/relatorio-seas.pdf`, usando o Chrome para imprimir. São 7 seções:
1. resumo;
2. orçamento de 2026 da SEAS e dos fundos da área;
3. convênios ano a ano;
4. os 30 que mais receberam;
5. todos os instrumentos em ordem de assinatura;
6. emendas executadas pela SEAS (OFIP, não oficial);
7. fontes e método.

Rode o build de novo sempre que coletar convênios.

## Quarta aba: "Tecnologia no Estado"

Tudo o que o Governo de Rondônia contrata em tecnologia, de todos os órgãos: quanto, com quem, para quê e quando vence. Abre no Estado todo ou num órgão só (seletor no alto). As visões são:
- **por tipo:** sistemas, licenças, datacenter, links, segurança etc.;
- **por órgão;**
- **repetidos:** a mesma função contratada separadamente por vários órgãos, candidata a uma contratação única;
- **vencimentos:** calendário dos vigentes, que mostra a janela para consolidar;
- **empresas;**
- **ano a ano.**

No mesmo quadro aparecem o empenhado em TIC (elemento 40) do Executivo, o bloco de frota e abastecimento (à parte) e os itens de TI dos PCAs 2026.

- **Para coletar:**
  - `python3 coleta_contratos.py` (todos os contratos);
  - `python3 tecnologia/coleta_empenhos.py` (elemento 40 com detalhe);
  - `python3 tecnologia/coleta_empresas.py` (cadastro dos CNPJs).
- **Para classificar:**
  - `python3 tecnologia/classificar.py` faz a triagem por regra;
  - a decisão final é a revisão contrato a contrato em `tecnologia/revisao/R_*.json`;
  - correções pontuais vão em `VALOR_A_CONFERIR` e `PREFIXO_FIXO`, no `build_tecnologia.py`.
- **Para gerar:** `python3 tecnologia/build_tecnologia.py`. Grava `dados-fonte/s5_tecnologia.json`, `tecnologia/contratos_tecnologia.csv`, `esbocos/tecnologia.html` e `site/tecnologia.html`.
- **Para editar:** `tecnologia/src/tecnologia.html`. O visual reaproveita `convenios/src/_base.css` e `_base.js`.
- **Endereços diretos:** `?org=SEDUC`, `?ver=repetidos|vencimentos|empresas|anos|orgao` e `?dados=tec-contratos`.

Fontes e regras de leitura: [FONTES.md](FONTES.md), seção 2c.

## Quinta aba: "Quem vende ao Estado"

Todas as empresas e entidades privadas que receberam empenho do Estado em 2023–2026 (278.633 notas, R$ 56,6 bi; R$ 13,7 bi a empresas), com:
- **filtros:** Ano · Órgão · Modalidade · Poder · **Tema (Tudo / Tecnologia / Frota)** · busca por empresa ou CNPJ;
- **visões:** Quem recebe · Como compra · Quem compra · Ano a ano;
- **ficha de cada empresa:** por órgão, por modalidade, por ano, contratos e convênios no portal, atividade na Receita e maiores notas com histórico.

**Comandos:**
- **Para coletar:**
  - `python3 tecnologia/coleta_tudo.py`: detalhe de todas as notas a empresas a partir de R$ 20 mil;
  - `tecnologia/coleta_varredura.py`;
  - `coleta_contratos.py` e `coleta_contratos.py convenios`.
- **Para gerar:** `python3 tecnologia/build_tecnologia.py && python3 empresas/build_empresas.py`. Grava:
  - `dados-fonte/s6_empresas_estado.json`;
  - `empresas/empresas_estado.csv` (lista completa);
  - `esbocos/` e `site/empresas.html`.
- **Endereços diretos:** `?ano=2025`, `?org=SEDUC`, `?mod=Dispensa`, `?tema=frota|ti`, `?q=UZZIPAY`, `?poderes=1`.

As abas pesadas (Tecnologia e Empresas) só carregam quando abertas. Regras em [FONTES.md](FONTES.md), seção 2d.

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
