# Migração do notebook para a aplicação

Este documento mapeia o código do notebook `DataManagement_Project/analise_fluxo_dados.ipynb`
para a nova estrutura em `APP/backend`, registra o que foi preservado, o que mudou
(e por quê) e o que ainda depende de decisão.

> **Referência principal:** o notebook. A entidade final do projeto é a `final_table`
> (a "tabela geral"), aqui representada por `FichaCliente`.
>
> **Status:** Fase 1 concluída e revisada (camada de extração + domínio). Próximas fases: FastAPI,
> PostgreSQL, comparação, React (dashboard), integração, Docker, testes e documentação.

---

## 1. Visão geral

```
NOTEBOOK (células executadas em ordem, estado global)
  nf_table / pl_table / pr_table   ← dicionários de listas paralelas
  processar_nome()                 ← chave do cliente = NOME DO ARQUIVO
  extrair_*()                      ← regex por tipo
  final_table                      ← full join por nome
  CSV / Excel                      ← saída

APLICAÇÃO (módulos com responsabilidade única)
  app/extraction/   PDF (bytes) → ResultadoExtracao            (regras dos extrair_*)
  app/domain/       ResultadoExtracao → FichaCliente            (full join pela chave do CONTEÚDO)
                    FichaCliente → ResumoGeral                  (números do dashboard)
  (Fase 2+)         API, banco, edição manual, versionamento     (substitui CSV/Excel)
```

## 2. Mapa: notebook → novo código

| Célula | Código antigo | Novo módulo | Nova classe / função | O que mudou |
|---|---|---|---|---|
| 4 | `nf_table`, `pl_table`, `pr_table` | `app/domain/entities.py` | `DadosNotaFiscal`, `DadosPlanilhaComissao`, `DadosPrestacaoContas`, `ResultadoExtracao` | Listas paralelas viram um objeto por documento, com campos tipados |
| 4 | `final_table` | `app/domain/entities.py` | `FichaCliente` | Placeholders ("Processo não encontrado") viram `None`; `documentos_faltantes` substitui o relatório de faltantes |
| 5 | `startswith('nf ')` etc. | `app/extraction/detector.py` | `DocumentTypeDetector` | Nome em NFC; nova estratégia pelo **conteúdo** como fallback |
| 6 | `processar_nome` | `app/extraction/parsers/nome_cliente.py` | `extrair_nome_do_arquivo` | Deixou de ser a chave: agora é só **reserva** e **verificador** |
| — | (não existia) | `app/extraction/parsers/{planilha,nota_fiscal,prestacao}.py` | `extrair_nome_da_tabela`, `extrair_nome_nota_fiscal`, `limpar_nome_prestacao` | **Nome lido de dentro do documento = chave do cliente** |
| 8 | `extrair_texto_pdf_ocr` | `app/extraction/readers/pdf_ocr_reader.py` | `PdfOcrReader` | Bug do `texto_pagina` corrigido; erro claro se o Tesseract faltar |
| 8 | `normalizar_data_malformada`, `extrair_data_texto` | `app/extraction/parsers/data_emissao.py` | `extrair_data_emissao` | Mesmos 5 padrões e ordem; devolve `date` |
| 14, 23 | `datas_manuais`, `corretor_nao_encontrado` | `app/extraction/correcoes_manuais.py` + JSON | `CorrecoesManuais` | Dados saem do código; na Fase 3 viram **edição manual no frontend** |
| 17 | `extrair_situacao_corretor` | `app/extraction/parsers/anotacao.py` (+ `situacao_corretor.py` como reserva) | `interpretar_anotacao` | Situação vira **enum**; corretor corrigido nos casos "Vl Inct." |
| 26 | `extrair_dados_prestacao` | `app/extraction/parsers/prestacao.py` | `extrair_nome_prestacao`, `extrair_numero_processo` | PDF lido 1× (antes 2×); ausência = `None` |
| 10, 19, 28 | loops que populam as tabelas | `app/extraction/extractors/*`, `pipeline.py` | `*Extractor`, `ExtractionPipeline` | Strategy Pattern; erro num arquivo não interrompe o lote |
| 32–34 | full join por nome | `app/domain/consolidacao.py` | `ConsolidadorFichas` | Chave = **nome do conteúdo**; verificadores apontam possíveis duplicidades |
| 35, 37 | análise de faltantes / múltiplos, relatório de faltantes | `app/domain/relatorio.py` | `gerar_resumo`, `clientes_com_documentos_faltantes` | Vira a base do **dashboard** |
| 37 | exportação CSV/Excel | Fases 2–5 | API + PostgreSQL + React | Substituída pelo banco e pelas telas |
| 40–42 | limpeza/mesclagem de PDFs | não migrado (roadmap) | — | Ver seção 9 |

## 3. Regras preservadas (paridade com o notebook)

- Tipo pelo prefixo do nome do arquivo (`nf `, `planilha`, `prestação`).
- Data da NF: OCR com zoom 2x, idioma `eng`, 5 padrões regex na mesma ordem, anos 2020–2030.
- Prestação: nome após `À`, processo após `Processo`/`N° Processo`.
- Correções manuais: só preenchem campos vazios.
- Colunas da tabela geral: nome, arquivos de cada tipo, data da NF, nº do processo, situação,
  corretor, nome encontrado.

**Regra do notebook que foi ALTERADA (pedido do usuário):** com vários documentos do mesmo tipo,
o notebook guardava só os dados do **primeiro**. Um cliente pode ter várias NFs, planilhas e
prestações, então a `FichaCliente` guarda **todos** os documentos, cada um com os seus dados. As
colunas da tabela geral viram listas: datas das NFs, processos, situações, corretores.

## 4. A chave que une os arquivos: o nome lido do conteúdo

**Problema:** o notebook identificava o cliente pelo nome do arquivo, renomeado à mão.
Renomear um arquivo mudava o cliente ao qual ele pertencia, e o mesmo arquivo com dois
nomes virava dois clientes.

**Regra:** o nome do cliente é lido **de dentro** de cada documento.

| Tipo | Onde está o nome | Como é lido |
|---|---|---|
| Planilha | célula abaixo do cabeçalho **"Cliente"** | `find_tables()` do PyMuPDF (reserva: 1ª linha com valor monetário) |
| NF | **`Cliente: <nome>`** no OCR; no layout antigo, após o nº do processo (`DE: <nome>`, `espólio de: <nome>`) | regex sobre o OCR |
| Prestação | linha após **`À`** | regra do notebook + corte do "Referente:" colado |

O nome é normalizado por `domain/nomes.gerar_chave_cliente`: sem acentos e pontuação, em
maiúsculas, com o representante descartado (`Rep.`, `representado por`,
`ESPÓLIO DE X - <representante>`). **O espólio não faz parte da chave:** "Espólio de X" é o
mesmo cliente X depois do falecimento (o processo continua o mesmo). A ficha guarda o
indicador `espolio`, e o nome exibido mantém a grafia do documento.

**Reconciliação de OCR:** o nome da NF vem do OCR, que troca letras ("MARTA" por "MARIA",
"CONCEIGAO" por "CONCEICAO") e corta nomes na quebra de linha. Se a chave lida por OCR não
existe entre as chaves lidas de camadas de texto (Planilha/Prestação), adota-se a chave de texto
mais parecida:
- similaridade ≥ 0,85; ou
- a leitura do OCR é o **início** da chave de texto, com pelo menos 3 palavras.

Empates não adotam nada. Cada troca é registrada (`Consolidacao.reconciliacoes_ocr`) para
aparecer na revisão. Dois nomes lidos de camadas de texto **nunca** são reconciliados entre
si: essa diferença está no próprio documento e é decisão do usuário.

**Papel do nome do arquivo (nunca une documentos):**
- **Reserva:** um documento sem nome no conteúdo (OCR ilegível) vai para o cliente cujos
  documentos têm o mesmo nome de arquivo;
- **Verificador:** duas fichas diferentes com documentos de mesmo nome de arquivo são apontadas
  como **possível duplicidade**. Também são apontadas fichas com nomes muito parecidos
  (similaridade ≥ 0,85).

**Por que o id do banco não será o nome (Fase 3):** o nome do conteúdo é a **chave de negócio**
(coluna única `chave`). A chave primária técnica é um `id` numérico, para que corrigir um nome
com erro de digitação não obrigue a atualizar todas as tabelas que apontam para o cliente.

### Consequência medida nos arquivos reais

| | Notebook (nome do arquivo) | Nome do conteúdo |
|---|---|---|
| Nome encontrado no conteúdo | — | NF 189/192 · Planilha 151/151 · Prestação 162/164 |
| Clientes (fichas) | 165 | 190 |
| Nomes de OCR reconciliados | — | 31 (todos conferidos manualmente como corretos) |
| Possíveis duplicidades para revisão | — | 29 pares |

As fichas a mais vêm de os **próprios documentos** grafarem o nome de formas diferentes:
- erros de digitação (uma letra trocada ou omitida);
- sobrenomes a mais ou a menos entre um documento e outro;
- em alguns espólios, a Prestação endereçada ao representante.

Cada caso aparece na lista de possíveis duplicidades para revisão (ver a decisão pendente na
seção 7).

## 5. Situação (enum) a partir das siglas

**Enum** (`domain/enums.Situacao`): `VALOR_TOTAL`, `VALOR_FINAL`, `VALOR_INCONTROVERSO`,
`ACORDO`, `CANCELADO`.

**Como a relação foi levantada:** cruzamento, pelo **número do processo**, das siglas extraídas
pelo notebook com a coluna "Situação" do relatório da planilha de controle do escritório (`Tabela Clientes.xlsx`)
(115 clientes em comum):

| Sigla no nome do arquivo | "Situação" no relatório | Conclusão |
|---|---|---|
| `VT`, `VT.` | Valor Total (63/65) | `VALOR_TOTAL` |
| `VF` | Valor Final (4/6) | `VALOR_FINAL` |
| `INCT`, `INCT.`, `INCTR`, `ICTR`, `Incnt.` | Incontroverso | `VALOR_INCONTROVERSO` |
| `V Inct`, `Vl Inct.`, `VI Inct.` | Incontroverso | "V"/"Vl" = "Valor"; quem decide é "Inct" |
| `VI Juliana` | Incontroverso | `VI` = **V**alor **I**ncontroverso |
| `AC`, `ACD`, `ACORDO` | Acordo | `ACORDO` |
| `CANCELADA` (nomes de NF) | — | `CANCELADO` |
| `VS` | "Verificar" | `VERIFICAR` |
| `CORREÇÃO`, `VALOR REMANESCENTE`, planilha sem sigla | Correção / Valor Remanescente | `VERIFICAR` |

**Nova regra** (`parsers/anotacao.py`): dentro dos parênteses, as palavras que são siglas
conhecidas (`data/situacao_siglas.json`) definem a situação, e **o corretor é o que vem depois
da última sigla**. Isso corrige o notebook, que lia `(Vl Inct. Viviane)` como situação `VL`
e corretor `INCT. VIVIANE`. O relatório registra "Incontroverso" e "Viviane".
Quando nenhuma sigla conhecida aparece, a regra original do notebook é usada como reserva.

**`VERIFICAR`** é o valor dos casos desconhecidos: planilha sem sigla, ou com sigla fora da
tabela. O usuário define a situação correta no frontend.

A situação é lida para os três tipos de documento. `CANCELADO` só aparece em NFs. Na tabela
geral, as situações exibidas são as das Planilhas do cliente, como no notebook.

## 6. Mudanças intencionais (bugs e fragilidades corrigidos)

| Problema no notebook | Correção | Onde |
|---|---|---|
| Se o Tesseract falhasse numa página, `texto_pagina` ficava indefinido ou repetia a página anterior | Página com falha contribui com texto vazio e gera log | `PdfOcrReader` |
| Tesseract ausente era engolido silenciosamente | `OcrIndisponivelError` → status ERRO com mensagem clara | `PdfOcrReader` |
| Nomes em Unicode NFD (`Célia` → `CéLia` após `.title()`) | Normalização NFC | `domain/nomes.normalizar_unicode` |
| Corretor errado em `(Vl Inct. X)`, `(V Inct X)` | Corretor = palavras após a última sigla | `parsers/anotacao.py` |
| `nome_encontrado` às vezes com "Referente: Prestação de Contas" colado | Campo mantido bruto; a chave usa a versão limpa | `parsers/prestacao.py` |
| Cada Prestação era lida 2× | Leitura única com cache | `DocumentoPdf` |
| Placeholders de texto misturados aos dados | `None` (NULL no banco) | parsers |
| Caminhos Windows fixos no código | Parâmetros e `.env` | `factory.criar_pipeline`, `.env` |
| Arquivo que não é PDF virava erro de leitura | Verificação da assinatura `%PDF` | `ExtractionPipeline` |

## 7. Decisões do usuário (2026-09-26)

**Objetivo do projeto:** conectar os arquivos de cada cliente e mostrar quais arquivos faltam.

1. **Um cliente pode ter vários documentos de cada tipo:** a ficha guarda todos (seção 3).
2. **Casos desconhecidos viram `VERIFICAR`** e são resolvidos no frontend (seção 5).
3. **Correção manual de tudo:** datas, corretores e situações não identificados ou identificados
   com erro podem ser corrigidos no frontend.
4. **Possíveis duplicidades (29 pares nos arquivos atuais) são remanejadas no frontend:** o
   usuário move arquivos entre clientes ou une duas fichas. A decisão fica gravada no banco
   (a chave "errada" vira um apelido do cliente certo), para que as próximas importações já
   juntem os arquivos automaticamente.

## 8. Requisitos registrados para as próximas fases

- **Dashboard:** cards com total de clientes e total de cada tipo de arquivo, documentos a
  verificar, relatório de clientes com documentos faltantes e a **tabela geral**
  (`FichaCliente`). Os números já existem em `domain/relatorio.py`.
- **Edição manual:** cada documento mostra os campos `campos_a_verificar` em destaque. No banco,
  cada valor registra sua origem (extraído ou manual) e o histórico, e uma edição manual nunca
  é sobrescrita por uma extração posterior sem revisão. Isso substitui o `correcoes_manuais.json`.
- **Remanejamento:** mover um documento para outro cliente, unir clientes, atribuir cliente aos
  documentos sem cliente identificado.

## 9. O que não foi migrado (e por quê)

| Código | Motivo |
|---|---|
| `extracao_docx_relatorio.ipynb` (DOCX via `win32com`) | Exige Windows + MS Word; candidato a `DocxExtractor` com `python-docx` |
| Criação de 100 pastas com planilha modelo | Utilitário de sistema de arquivos, fora do fluxo de dados |
| Limpeza e mesclagem de PDFs por cliente | Candidato a "baixar PDF consolidado do cliente" no roadmap |
| Exportação CSV/Excel | Substituída por PostgreSQL + API; pode voltar como endpoint |

## 10. Como verificar

```bash
cd APP/backend
.venv/Scripts/python -m pytest                    # testes (dados sintéticos)
.venv/Scripts/python -m pytest -m "not ocr"       # sem os testes que usam o Tesseract

.venv/Scripts/python -m scripts.verificar_paridade \
    --pasta "<pasta com os PDFs>" \
    --csv "../../RELATÓRIOS/tabela_final_clientes.csv" \
    --tabela-clientes "<planilha de controle>.xlsx" \
    --tesseract-cmd "C:/Program Files/Tesseract-OCR/tesseract.exe"
```

O relatório de paridade sai só no terminal, porque contém nomes de clientes. Ele tem cinco
seções: resultado por arquivo; paridade com o CSV do notebook (usando a chave legada, para
isolar as regras de extração); situação × relatório Tabela Clientes; agrupamento pela chave do
conteúdo e possíveis duplicidades; números do dashboard.
