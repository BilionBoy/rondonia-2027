---
arquivo: documento-modelo
titulo: Modelo de documento institucional
subtitulo: Como escrever um projeto ou plano no molde "Documento" do brief-ro
kicker: Molde Documento · NextTech
slogan: Escreva o conteúdo; o molde cuida da forma
produto: brief-ro
cabecalho: Modelo de documento institucional
titulo_pdf: Modelo de documento institucional
versao: v0.1
ficha:
  Documento: Modelo de referência
  Versão: v0.1
  Data: 11/10/2026
  Natureza: Exemplo do molde
pe: Exemplo do molde Documento
autoria: NextTech Ecosystem
---

# 01 — Capa e cabeçalho

A capa é montada a partir do bloco entre `---` no início do arquivo. Esse bloco tem os campos `titulo`, `subtitulo`, `kicker`, `slogan`, `versao` e `ficha` (uma lista de rótulo e valor que aparece na capa), mais `pe` e `autoria`. O cabeçalho de cada página junta o `produto` e o `cabecalho`. O rodapé traz a `autoria` e a `versao`.

O primeiro parágrafo depois do título de um módulo sai maior. Ele funciona como a abertura do módulo.

## Títulos

Cada `#` começa um módulo numa página nova, com o número grande em azul. Escreva assim: `# 01 — Título do módulo`. O sumário é montado sozinho a partir desses títulos, com a página de cada um.

Use `##` para seções e `###` para subseções. O `####` serve para um rótulo pequeno em caixa alta.

### Texto, listas e destaques

O texto corrido segue o Markdown comum: **negrito**, *itálico*, [links](https://transparencia.ro.gov.br) e listas.

- Primeiro item de uma lista.
- Segundo item, com **negrito** dentro.
  1. Item numerado.
  2. Outro item numerado.

> Um parágrafo que começa com `>` vira um quadro de destaque, em azul-claro. Use para a conclusão de uma seção ou para um ponto que o leitor não pode perder.

# 02 — Visuais, tabelas e selos

Os visuais entram por número. Enquanto a imagem não existe, o PDF mostra um quadro reservado com a descrição. Quando o arquivo é salvo em `img/visual-NN.png`, a imagem entra no mesmo lugar, sem mexer no texto.

## Visual reservado

Escreva o visual numa linha própria:

VISUAL 01 — Linha do tempo dos sistemas patrimoniais, de 2017 a 2026

A linha também pode vir entre colchetes, como `[VISUAL 02 — descrição]`. As palavras FIGURA, QUADRO, DIAGRAMA e IMAGEM funcionam do mesmo jeito.

[DIAGRAMA 02 — Atores institucionais e responsabilidades em alto nível]

## Tabela

| Marcação | Uso | Cor |
|---|---|---|
| [DECIDIDO] [CONFIRMADO] [NORMA] [SEI] | fato com fonte ou decisão tomada | verde |
| [INFERIDO] [PROPOSTA] [ESTIMATIVA] | leitura ou proposta da NextTech | âmbar |
| [A CONFIRMAR] [A VALIDAR] [PENDENTE] [EM ABERTO] | depende de resposta de um órgão | vermelho |

As marcações entre colchetes viram selos coloridos em qualquer lugar do texto, por exemplo: "a carga inicial vem do e-Estado [PROPOSTA], com chave da Central do Desenvolvedor [A CONFIRMAR]".

## Tabelas longas

Uma tabela pode passar de uma página para a outra. O cabeçalho se repete e nenhuma linha é cortada ao meio.
