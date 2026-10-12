# Moldes de documento

Este molde serve para escrever um documento novo (proposta, plano, apresentação para órgão público) **sem tocar em HTML nem em CSS**. Quem escreve preenche só um arquivo `conteudo.yaml` com texto e números. O `gerar.py` monta o PDF no padrão visual já aprovado.

Existem dois moldes: a **Proposta** (uma ideia por página, a partir de um YAML) e o **Documento** (texto longo a partir de um Markdown, descrito abaixo). Ele reproduz o plano do SISPAC-RO para a SEAS. O padrão de cores, letra e escrita está em `frotas/mvc/docs/PADRAO-VISUAL-TRANSPARENCIA.md`, e este molde é a versão "proposta" dele:
- capa azul;
- uma ideia por página.

## Molde "Documento" (texto longo em Markdown)

Serve para projeto institucional, plano de trabalho e qualquer volume de texto corrido. O conteúdo é o próprio `.md`, sem conversão. O visual é o mesmo do molde Proposta: capa azul, faixa da bandeira e Inter.

```
python3 moldes/gerar_documento.py caminho/documento.md
```

O PDF sai ao lado do `.md`. Exemplo de uso real: o A1 do SIMA, em `sima/api/docs/produto/0-raiz/entendimento/`.

**Estrutura e paginação**
- Cada `# Título` abre uma página nova.
- `# MÓDULO 01 — …` ganha o número grande; `# ANEXO I — …` ganha o rótulo do anexo.
- Títulos em caixa alta são convertidos para caixa de frase, mantendo as siglas como aparecem no texto.
- O sumário (com página) e o índice de figuras são automáticos.

**Figuras**
- Marcador `<!-- FIGURA A1-F07 | TÍTULO | tipo=… | arquivo=assets/x.svg | fonte=… | status=… -->`. O parágrafo `**A1-F07 — Título.** descrição` logo acima vira a legenda.
- A figura **só entra quando o arquivo existe** (o `arquivo=` relativo ao `.md`, ou em `assets/`). Sem arquivo, fica fora do PDF. Para ver quadros reservados no lugar, use `vagas: true` no `.molde.yaml`.

**Selos e tabelas**
- Sinais entre colchetes viram selos coloridos:
  - verde: [DOC] e [DECIDIDO];
  - azul: [FONTE INTERNA];
  - âmbar: [PROPOSTA] e [INFERIDO];
  - vermelho: [APURAÇÃO] e [A CONFIRMAR];
  - roxo: [CONTROVERSO].
- Combinações como `[DOC/APURAÇÃO]` funcionam.
- Tabelas com 6 colunas ou mais saem com letra menor.
- Texto comprido quebra dentro da célula. Nada passa da margem; se passasse, o Chrome encolheria o documento inteiro.

**Cada documento é um projeto dentro do `brief-ro`:** `moldes/exemplos/<projeto>/` guarda tudo, mesmo quando o texto vem de outro repositório.
- `<nome>.molde.yaml`: a configuração; `fonte:` aponta para o `.md`.
- `assets/`: **todas as imagens geradas para o documento, sempre salvas aqui**, com o nome do marcador.
- O PDF gerado.

Exemplo: `moldes/exemplos/sima-a1/`, cujo texto é o `.md` do Codex no repositório do SIMA. Para gerar: `python3 moldes/gerar_documento.py moldes/exemplos/sima-a1/a1.molde.yaml --site`.

No `.molde.yaml`:
- `capa.fundo: assets/x.png` põe a imagem como fundo da capa. Com fundo, não use `texto` na capa.
- `ignorar_figuras: [A1-F01]` evita repetir no corpo a figura que já está na capa.
- `rotulos: {"^TÍTULO": Rótulo}` define o rótulo azul das seções sem número.

**Paginação automática (molde Documento):**
- Figura grande nunca vira miniatura; todas ficam na página em pé, na largura do texto (nada de página deitada); SVG entra como vetor.
- Figuras "flutuam": se uma figura deixaria buraco na página anterior, o gerador a desce alguns blocos de texto (junto com a "Leitura gerencial") e gera de novo, até não sobrar página com menos de 60% ocupada.
- Quando descer não resolve, a figura reduz até 20% ou, se for deitada, volta para página em pé.
- `posicoes:`, `substituir:`, `remover_linhas:`, `omitir_secoes:` ajustam conteúdo e lugar das figuras sem mexer no `.md`.

**Ajustes sem tocar no `.md`:** o `.molde.yaml` (ou `<nome-do-md>.molde.yaml` ao lado do `.md`) também define:
- a capa: título, ficha e `brasao: false`;
- cabeçalho, rodapé e nome do PDF;
- `omitir`: as seções de nível 1, por expressão regular, que não vão para o leitor.

## Para quem vai escrever (pessoa, Codex ou Claude)

1. Copie a pasta do exemplo: `cp -r moldes/exemplos/sispac-ro moldes/exemplos/<nome>`.
2. Apague as imagens que não vai usar (`img/`) e reescreva o `conteudo.yaml`.
3. Gere o PDF: `python3 moldes/gerar.py moldes/exemplos/<nome>/conteudo.yaml`.
   - Com `--site`, o PDF também é copiado para `site/`.
4. Leia o que o gerador imprimiu.
   - **"conteúdo não cabe na página N"**: corte o texto ou divida a página em duas. Não mexa no CSS para fazer caber.
   - **"item com N partes"**: um texto com vírgula dentro de `[ ]` ficou sem aspas.
5. Abra o PDF e confira cada página.

**Não escreva HTML nem CSS, e não mude `proposta.css` para um documento só.** Se faltar um tipo de bloco, ele é criado em `gerar.py` e `proposta.css` e documentado aqui, para servir a todos os documentos.

O gerador precisa de:
- Python 3 com `pyyaml`;
- Google Chrome. Se ele não estiver no caminho padrão, defina `CHROME=/caminho`.

## O arquivo de conteúdo

```yaml
documento:
  produto: SISPAC-RO                    # aparece no cabeçalho de toda página
  slogan: Rondônia conectada pelo cuidado
  arquivo: SEAS-SISPAC-PLANO-DE-GOVERNO # nome do PDF (sem .pdf)
  titulo_pdf: SISPAC-RO · plano         # título nas propriedades do PDF
  autoria: NextTech Ecosystem           # rodapé (padrão: NextTech Ecosystem)

capa:
  topo: [Estado de Rondônia, Proposta com dados públicos]
  kicker: PROPOSTA PARA A SEAS · OUTUBRO DE 2026
  titulo: SISPAC-RO
  subtitulo: Nome completo do produto
  slogan: frase curta (sai em amarelo)
  texto: Um parágrafo dizendo o que é.
  pe: Nome do órgão destinatário

paginas:
  - kicker: A proposta            # página sem número de seção
    titulo: A ideia em uma frase
    blocos: [...]

  - secao: O problema das entidades   # página de seção: o número sai sozinho ("1 · O PROBLEMA…")
    titulo: As parcerias cresceram mais rápido que o apoio a elas
    fonte: "Fonte: Portal da Transparência…"   # rodapé da página (opcional)
    blocos: [...]
```

**Regras de seção e numeração:**
- Páginas seguidas com a mesma `secao` fazem parte da mesma seção.
- O bloco `sumario` lista as seções na ordem em que aparecem.
- O número da página ("4 / 27") é calculado pelo gerador.

**Cuidados de YAML:**
- Texto com `: ` (dois-pontos e espaço) precisa de aspas. Exemplo: `fonte: "Fonte: IBGE"`.
- Dentro de `[ ]`, texto com vírgula precisa de aspas. Exemplo: `["Não substitui, soma", null, "…"]`.
- `null` deixa uma parte vazia.
- `**negrito**` funciona em qualquer texto. Na `frase`, o negrito sai em azul.

## Blocos

Cada bloco é uma chave só. Os itens de lista podem ser escritos como lista curta (`[a, b, c]`) ou com nomes (`{titulo: a, texto: b}`).

| Bloco | Para quê | Forma | Página do SISPAC |
|---|---|---|---|
| `frase` | A ideia central, grande e em azul-escuro | `frase: "texto com **destaque**"` | 2, 26 |
| `destaques` | 2 a 4 ganhos curtos, com régua em cima | `destaques: [[Menos burocracia, para quem ajuda], …]` | 2 |
| `sumario` | Índice automático das seções | `sumario: {nota: "texto opcional"}` | 3 |
| `colunas` | Série por ano ou categoria, com uma coluna em destaque | `colunas: {titulo, itens: [[2019, 3], …], destaque: 2025, nota, altura?}`. O 3º valor do item é o rótulo, quando difere do número | 4 |
| `kpis` | 2 a 4 números lado a lado, com régua preta | `kpis: [["18 → 99", "rótulo"], …]` | 4, 24 |
| `conclusao` | Fecho da página, em azul-escuro e negrito | `conclusao: texto` | 4, 5, 6… |
| `grupos` | Fases numeradas com lista de itens em duas colunas | `grupos: [{titulo, itens: [...]}, …]` | 5 |
| `cartoes` | Grade 2×N de cartões | `cartoes: [[titulo, sub, texto], …]` ou `cartoes: {itens, numerado: false, linha: azul, estilo: numero}` | 6, 11, 12, 16, 17, 18, 25, 26 |
| `numero` | Um número enorme e o que ele significa | `numero: {valor: R$ 193 mi, rotulo: "…"}` | 7, 23 |
| `barras` | Comparação horizontal; o 1º item fica em destaque | `barras: {titulo, itens: [[rótulo, valor_numérico, "texto do valor"]], nota}` | 7 |
| `caixa` | Nome do produto em caixa azul-clara | `caixa: {titulo, subtitulo, texto}` | 8 |
| `secoes` | Blocos com rótulo azul, título e texto | `secoes: [[Para a entidade, Faz a papelada com ela, "texto"], …]` | 8 |
| `imagem` | Infográfico ou foto (caminho relativo ao YAML) | `imagem: img/x.jpg` ou `{arquivo, legenda, altura (mm)}` | 9, 10, 13, 14, 15, 20, 22, 24 |
| `itens` | Lista de título + texto em duas colunas | `itens: [[titulo, texto], …]` ou `{rotulo: "Termos usados", itens}` | 9, 13, 17, 27 |
| `citacao` | Parágrafo com barra à esquerda | `citacao: "**Lead.** resto"` | 15 |
| `tabela` | Indicadores, fontes | `tabela: {colunas: [...], larguras: [%...], linhas: [[...]]}` | 19, 27 |
| `passos` | Cadeia de causa e efeito numerada | `passos: [[Plano bem feito, a parceria é aprovada mais rápido], …]` | 21 |
| `numeros` | Números empilhados com rótulo | `numeros: [[115 mil, rótulo, apoio?], …]` | 23 |
| `mapa` | Os 52 municípios de RO pintados por faixa (malha IBGE de `dados-fonte/ibge/`) | `mapa: {valores: {Ariquemes: 96833, …}, faixas: [[5000, até 5 mil], …, [null, 50 mil ou mais]], legenda, altura?}`. O município pode vir pelo nome (com ou sem acento) ou pelo código IBGE | — |
| `texto` | Parágrafo comum | `texto: …` | 10, 21 |
| `nota` | Linha pequena cinza | `nota: …` | 17 |
| `regua` | Linha preta | `regua: true` | 23 |
| `espaco` | Respiro vertical, em mm | `espaco: 8` | 2, 7 |

## Como escrever (para o documento ficar no padrão)

- **Uma ideia por página.**
  - O título da página já é a conclusão. Exemplo: "As parcerias cresceram mais rápido que o apoio a elas", e não "Parcerias".
  - O resto prova o título.
- **Todo número tem fonte.**
  - Ela vai no `fonte:` da página, com o nome do sistema e a data.
  - A última página é sempre "Fontes e método" (tabela de dados + termos usados).
- **Número vem do dado, não da memória.**
  - Antes de escrever um número, confira-o na fonte ou nos arquivos de `dados-fonte/`.
  - Se ele depende de uma regra (o que conta como "entidade", por exemplo), escreva a regra no rodapé.
- **Linguagem de gente.**
  - Frases curtas e afirmativas.
  - "Comprometido", e não "empenhado"; o termo técnico é explicado uma vez, no glossário.
  - Nada de adjetivo político.
- **Proposta não promete o que não existe.**
  - O que ainda não foi medido aparece como "a medir no piloto".
  - O que depende do órgão aparece como "a definir com a [órgão]".
  - O rodapé da implantação diz: "Proposta sujeita aos procedimentos institucionais e de contratação aplicáveis".
- **Imagens.**
  - Infográficos gerados por IA servem como ilustração, nunca como prova de número.
  - Formato **16:9 (1672×941)**, fundo claro, mesmas cores do molde (azul-escuro `#0f2c66`, azul `#1a56b8`, amarelo `#e5c800`, verde `#1d8a3e`).
  - Texto da imagem em português e conferido letra a letra: IA erra acento e palavra.
  - Use `altura: 86` quando a página tiver imagem e lista.

**Tamanho de referência:** o SISPAC tem 27 páginas, e cada seção tem de 2 a 6. Um plano curto pode ter 12.

## Exemplo de referência

`exemplos/sispac-ro/` traz o plano do SISPAC-RO para a SEAS, refeito neste molde.
- Ele tem as 27 páginas do PDF original de 09/10/2026 e as mesmas imagens.
- Há uma correção de dado: 2021 tem 21 termos de fomento com entidades, e não 20. A APAE "do Município de Santa Luzia D'Oeste" tinha sido contada como prefeitura pela regra `MUNIC` de `convenios/build_relatorio.py`.
- O "85 de 139 entidades" foi mantido como no original. Não foi possível reproduzi-lo com exatidão: pelos dados, o resultado vai de 134 a 141 entidades e de 81 a 87 com uma única parceria, conforme entram ou não bancos e órgãos públicos. Antes de reenviar o documento, fixe a regra e recalcule.

## Arquivos

| Arquivo | O que é |
|---|---|
| `gerar.py` | Lê o YAML, monta o HTML e imprime o PDF pelo Chrome. Antes de imprimir, confere se cada página cabe |
| `proposta.css` | O visual do molde: A4, faixa da bandeira, cabeçalho, rodapé e todos os blocos |
| `exemplos/<nome>/conteudo.yaml` | O conteúdo de cada documento |
| `exemplos/<nome>/img/` | As imagens do documento |
| `exemplos/<nome>/<arquivo>.pdf` | O resultado. O `.html` ao lado é refeito a cada geração e não vai para o git |

O brasão vem de `vendor/simbolos/brasao-ro.png`, a fonte Inter de `vendor/fontes/inter-var.woff2` e a malha dos municípios de `dados-fonte/ibge/`. Tudo vai embutido no PDF.
