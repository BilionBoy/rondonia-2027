# Revisão de contratos: o que é tecnologia no Governo de Rondônia (2023–2026)

Você revisa um lote de contratos do Portal da Transparência de Rondônia. O objetivo do projeto é mapear **todo o gasto do Estado com tecnologia**, para achar sobreposição (vários órgãos pagando a mesma coisa, vários sistemas para a mesma função) e economia possível.

## Entrada
Um arquivo JSON com uma lista de contratos:
- `id`: chave do contrato; copie exatamente;
- `ano`: ano de cadastro no portal;
- `orgao`: órgão contratante;
- `valor`: valor global em R$;
- `contratado`: empresa;
- `objeto`: texto do objeto;
- `categoria_regra`: só nos lotes **A**. É a categoria que uma regra automática deu e pode estar errada.

## O que decidir para CADA contrato
1. **É tecnologia?** Tecnologia aqui é o que um plano de TI do Estado precisa enxergar:

| código | categoria | exemplos |
|---|---|---|
| `sistemas` | Sistemas e software de gestão (contratados, locados, SaaS, desenvolvidos, mantidos) | gestão escolar, diário eletrônico, prontuário, sistema de RH/folha, ERP, plataforma educacional, BI, banco de preços, portal, app, sustentação/fábrica de software, sistema de ponto, gestão de processos, protocolo, GED |
| `licencas` | Licenças de software de mercado | Microsoft, Office, Windows, Oracle, Adobe, AutoCAD, ArcGIS, VMware, antivírus por licença (se for só antivírus, use `seguranca`) |
| `datacenter` | Datacenter, nuvem, hospedagem, servidores, storage, backup | — |
| `conectividade` | Links, internet, telefonia fixa/móvel, VoIP, satélite, rádio digital, fibra, Infovia | — |
| `seguranca` | Segurança da informação | firewall, antivírus, certificado digital, SOC, VPN |
| `impressao` | Outsourcing de impressão, locação de multifuncionais, reprografia | — |
| `equipamentos` | Equipamentos de informática e eletrônicos de TI | computadores, notebooks, tablets, chromebooks, monitores, nobreaks, switches, roteadores, scanners, projetores, lousas/painéis interativos, totens, kits de robótica, laboratórios de informática, toner/cartucho |
| `rede` | Rede lógica, cabeamento estruturado, wi-fi | — |
| `suporte` | Serviços de TI | suporte técnico, service desk, mão de obra de TI, manutenção de equipamentos de informática, digitalização de documentos |
| `operacional` | Tecnologia operacional | monitoramento eletrônico (tornozeleira), videomonitoramento/CFTV/câmeras, rastreamento, telemetria, drones, reconhecimento facial, leitura de placas, bloqueador de sinal, controle de acesso eletrônico/biometria |
| `frota` | Gestão de frota/abastecimento/manutenção por sistema e cartão | Ticket, Trivale, Prime, UzziPay etc. quando o objeto é gestão de frota, abastecimento ou manutenção de veículos via sistema ou cartão |
| `fora` | NÃO é tecnologia | — |

**Exemplos de `fora`:**
- ar-condicionado, equipamentos médicos ou laboratoriais, centrífugas;
- livros didáticos impressos, gráfica, material de expediente;
- obras, eventos, alimentação, vale-alimentação, cartão benefício;
- consultoria não-TI, cursos e treinamentos (salvo se o objeto principal é uma plataforma ou sistema);
- assinatura de jornal impresso, publicações em jornal.

**Na dúvida:** se o objeto principal é um software, sistema, plataforma ou serviço digital, é tecnologia; se a tecnologia é só um detalhe, é `fora`. **Atenção:** um contrato do lote **A** pode estar mal classificado, por exemplo "sistema" de ar-condicionado ou "câmara fria". Corrija.

2. **Função** (`funcao`): uma etiqueta curta e PADRONIZADA do que aquilo faz, para achar sobreposição. Use, de preferência, uma destas e crie outra só se nenhuma servir:
   - `gestao-escolar`, `diario-eletronico`, `plataforma-educacional`, `avaliacao-educacional`, `prontuario-saude`, `regulacao-saude`, `gestao-hospitalar`, `laboratorio-saude`, `telemedicina`;
   - `rh-folha`, `ponto-eletronico`, `gestao-processos-documentos`, `protocolo-atendimento`, `portal-site`, `app-cidadao`;
   - `financeiro-contabil`, `tributario-arrecadacao`, `compras-licitacao`, `banco-de-precos`, `patrimonio-almoxarifado`, `frota-abastecimento`, `frota-manutencao`, `bi-dados`, `ia`, `juridico`;
   - `transito-veiculos`, `seguranca-publica`, `prisional-monitoramento`, `videomonitoramento`, `geo-mapas`, `meio-ambiente`, `agro-defesa`;
   - `microsoft`, `antivirus`, `certificado-digital`, `firewall`, `nuvem`, `datacenter-servidores`, `backup`;
   - `internet-link`, `telefonia-fixa`, `telefonia-movel`, `satelite`, `radio`;
   - `impressao`, `computadores`, `notebooks-tablets`, `perifericos-suprimentos`, `rede-wifi`, `audiovisual-interativo`, `robotica-maker`;
   - `suporte-servicedesk`, `fabrica-software`, `digitalizacao`, `outra`.
3. **Produto/sistema** (`produto`): o nome do sistema ou da marca, se o objeto citar (ex.: "i-Educar", "Microsoft 365", "Fortinet", "SIGEF"). Vazio se não citar.
4. **Nota** (`nota`): só se houver algo relevante, como "é do Tribunal de Justiça, não do Executivo", "valor parece errado", "aditivo" ou "é a mesma solução que outro órgão contrata". Máximo de 15 palavras.

## Saída
Grave **um único arquivo JSON** no caminho que o pedido indicar, com uma lista: `[{"id": "...", "categoria": "sistemas|...|fora", "funcao": "...", "produto": "...", "nota": "..."}]`.
- **Lote A:** inclua TODOS os contratos.
- **Lote B:** inclua SÓ os que são tecnologia (os `fora` podem ser omitidos).
- Não altere outros arquivos.
- Ao final, responda em até 5 linhas: quantos revisou, quantos são tecnologia e os 3 achados mais interessantes do lote (ex.: o mesmo sistema em vários órgãos, ou valor muito alto).
