# Briefing comum — reescrita do A1 V3 (SIMA, Plano de Governo 2027–2030)

Fontes (ler antes de escrever):
- DIRETRIZ: sima/api/docs/produto/0-raiz/entendimento/SIMA_A1_DIRETRIZ_RECONSTRUCAO_EDITORIAL_V3_CLAUDE.md — seções 0, 2 ("Proporção entre explicação e visual"), 4 (o SEU módulo), 5 e 7. É lei.
- TEXTO V2 (base a reescrever): sima/api/docs/produto/0-raiz/entendimento/SIMA_A1_PROJETO_INSTITUCIONAL_2027_V2_COMPLETO_FINAL.md, nas linhas do seu módulo.
- Fatos de apoio (opcional, só para dados datados e verdadeiros): o "ACERVO DE PRESERVAÇÃO V1.1" no fim do mesmo arquivo (a partir da linha ~1342) e api/docs/produto/0-raiz/entendimento/referencias/seduc-sdc-patrimonio-2026-10-11.md.
(caminhos relativos a /home/dhiogo/projetos/next-tech/)

Regras de escrita:
1. Português do Brasil, registro de plano de governo: afirmativo ("O SIMA organiza", "O modelo estabelece"). O documento JÁ É o projeto formulado.
2. Proibido: falar do próprio documento ("este documento", "esta página", "a figura deve", "o diagramador", "PDF", "A1", "A2", "A3" — use "Plano de Trabalho" e "Caderno da Solução" se precisar), "apreciação", "avaliar a pertinência", "poderia ser implantado", NextTech como sujeito.
3. Proibido afirmar como fato: decreto, aprovação, convênio, API autorizada/homologada, orçamento, contratação, implantação em produção. A execução é "progressiva e condicionada às autorizações e instrumentos exigidos" — dizer isso no máximo UMA vez por módulo, sem ladainha de ressalvas.
4. Nunca inventar número, data, valor, percentual, cargo ou organograma. Dado histórico só com data e origem genérica ("levantamento institucional de 2025").
5. Substância: princípios, fluxos, papéis, critérios, exemplos concretos de rotina (escola, almoxarife, comissão, patrimônio, contabilidade). Sem enchimento, sem repetir.
6. Extensão: mais desenvolvido que a V2 (cerca de 1,5×), sem repetição.

Formato (o gerador depende disso — siga à risca):
- Primeira linha: `# MÓDULO NN — TÍTULO EM CAIXA ALTA` (título novo, de plano de governo).
- Logo abaixo, 1 parágrafo de tese do módulo (2–4 frases).
- Seções: `## N.1. Título`, `## N.2. Título`… sem saltos de numeração. Subseções `### N.1.1. Título` se precisar.
- Tabelas Markdown simples (máx. 5 colunas, texto curto nas células).
- Destaque: linha começando com `> `.
- Figuras: para CADA figura do seu módulo, use EXATAMENTE este bloco de 3 linhas, no ponto onde ela é discutida:
  ```
  **A1-Fxx — Título curto da figura.** Legenda de uma frase dizendo o que a figura mostra (não instrução de produção).

  <!-- FIGURA A1-Fxx | TITULO | arquivo=assets/NOME-DO-ARQUIVO -->
  ```
  Antes de cada figura: pelo menos um parágrafo de contexto. Depois: um parágrafo curto começando com `**Leitura gerencial.**` explicando implicação, responsáveis e efeito. Nunca duas figuras seguidas.
- Não escreva nada além do módulo (sem preâmbulo, sem comentário final).
- Grave o arquivo com a ferramenta Write no caminho indicado e responda só "ok: <caminho> (N linhas)".

Figuras disponíveis (código → arquivo → o que a imagem REALMENTE mostra):
- F02 → a1-f02-sintese-executiva.png → painel 3 colunas: situação atual (controles fragmentados, planilhas, inventário, inconsistências, prestação de contas) → modernização (SIMA integrador, integração e-Estado, inventário por servidores, rastreabilidade, governança de dados, padronização) → resultados.
- F03 → a1-f03-estrutura-seduc.png → SEDUC/RO → almoxarifado central, arquivo, centro de mediação tecnológica, apoio pedagógico, áreas administrativas → 18 superintendências regionais → 409 escolas (78 em Porto Velho). Números históricos.
- F04 → a1-f04-mapa-rede.png → mapa de RO com sedes regionais, 18 regionais, 409 escolas, 78 em Porto Velho.
- F05 → a1-f05-historico.png → linha do tempo: controles descentralizados → SGA → SGIS → e-Estado → 2025 dificuldades → 2026 necessidade → 2027 SIMA (datas da arte são aproximadas; no texto use só as datas verdadeiras do acervo: e-Estado oficial pelo Decreto 22.067/2017; SGIS criado em 2023; em nov–dez/2025 o SGIS-patrimônio foi declarado inviável e os móveis ficaram no e-Estado).
- F06 → a1-f06-comparativo-sistemas.png → matriz SGA × SGIS × e-Estado × controles paralelos (papel, abrangência, pontos fortes, limites, situação atual).
- F07 → a1-f07-ecossistema-atual.svg → ecossistema atual: escolas, regionais, almoxarifado, patrimônio, contabilidade nas bordas; e-Estado, SGA, SIGEF, SEI, planilhas ao centro, por competência.
- F08 → a1-f08-controles-paralelos.jpg → múltiplas fontes (planilhas, formulários, registros locais, documentos avulsos, sistemas isolados) → informação fragmentada → efeitos (retrabalho, divergências, demora, perda de contexto, consolidação).
- F09 → a1-f09-problemas-operacionais.jpg → dificuldades (inventário demorado, localização, visibilidade, atualização lenta, fragilidade nas escolas) e fluxos entre escolas, regionais, almoxarifado, patrimônio, gestores.
- F10 → a1-f10-problemas-patrimoniais.jpg → inconsistências cadastrais, divergências de tombamento, não localizados, sem regularização, bens relacionados.
- F11 → a1-f11-problemas-contabeis.jpg → fluxo contábil-patrimonial em 5 fases (aquisição/incorporação, gestão/movimentação, avaliação/ajustes, baixa, evidenciação) × unidades gestoras, órgão patrimonial, órgão contábil.
- F12 → a1-f12-as-is-geral.svg → AS-IS simplificado SEM SIMA: escola → regional → almoxarifado/patrimônio → registros oficiais (e-Estado) → contabilidade (SIGEF), com planilhas/controles locais e pontos de ruptura.
- F13 → a1-f13-as-is-raias.svg → AS-IS por raias (escola, regional, almoxarifado, patrimônio, contabilidade, sistemas) no circuito cotidiano: pedido/recebimento, movimentação, inventário, consolidação.
- F14 → a1-f14-tcs.png → TC-13 (materiais/almoxarifado), TC-15 (bens móveis), TC-16 (imóveis): aspectos de cada um e como se complementam.
- F15 → a1-f15-cadeia-demonstracao.png → bem físico → levantamento/conferência → registro patrimonial → contabilidade → demonstrativo final, com requisitos transversais.
- F16 → a1-f16-divergencias.png → categorias de divergência (SGIS, imóveis, conciliação, inventário, prestação de contas) e efeitos institucionais.
- F17 → a1-f17-ciclo.png → ciclo anual: planejamento → preparação das equipes → levantamento → tratamento de ocorrências → consolidação → conciliação → fechamento → prestação de contas.
- F18 → a1-f18-situacoes.png → situações: localizado, não localizado, achado, inservível, divergente, sem identificação, com tratamento recomendado.
- F19 → a1-f19-arvore-problema.png → causas estruturais → efeitos na operação → impactos institucionais.
- F20 → a1-f20-necessidades.png → necessidades: inventário estruturado, rastreabilidade, integração, evidência, conciliação, governança, operação em campo, visão gerencial, histórico/auditoria, redução de controles paralelos.
- F21 → a1-f21-matriz-objetivos.png → desafios → objetivos do SIMA → resultados esperados.
- F22 → a1-f22-to-be.png → visão futura: gestão central, escolas, regionais, operação em campo, almoxarifado, patrimônio/CAP, contabilidade em torno do SIMA; integração autorizada com e-Estado.
- F23 → a1-f23-fluxo-to-be.png → fluxo futuro em 8 etapas: entrada → cadastro → distribuição → uso → inventário → divergências → integração → prestação de contas; atores.
- F24 → a1-f24-macroarquitetura.png → camadas: pessoas e papéis, processos, núcleo SIMA, operação em campo (app, fotos, QR/RFID, offline), dados e integrações, governança.
- F25 → a1-f25-integracao-e-estado.png → usuários SEDUC → SIMA → camada de integração autorizada → e-Estado, com solicitações e confirmações.
- F26 → a1-f26-inventario.png → inventário pelos servidores: gestão central, comissão central, regionais, escolas, almoxarifado, patrimônio, contabilidade; fluxo em 6 etapas.
- F27 → a1-f27-atores.png → estrutura de governança: direção estratégica, comitê, SETIC, SEPAT, CAP, almoxarifado, contabilidade, regionais, equipe de apoio técnico, comissões, escolas.
- F28 → a1-f28-responsabilidades.png → matriz atividades × atores (coordena, executa, valida, apoia, integra).
- F29 → a1-f29-resultados.png → resultados por domínio: eficiência, controle patrimonial, confiabilidade contábil, governança, transparência.
- F30 → a1-f30-encaminhamentos.png → 6 passos: consolidação → planejamento executivo → validação institucional → estruturação → implantação gradual → monitoramento; condições de sucesso.
