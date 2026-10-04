# Arquitetura

> Documento vivo: cresce a cada fase. Hoje descreve a **extração (Fase 1)**, a **API
> (Fase 2)**, o **banco (Fase 3)** e a **comparação (Fase 4)**; o React vem na Fase 5.

## 1. Visão geral

```
┌──────────────┐   HTTP/JSON    ┌───────────────────────────────────────────────┐   SQL   ┌────────────┐
│  React (Vite)│ ─────────────► │ FastAPI                                        │ ──────► │ PostgreSQL │
│  Dashboard   │                │  api/routes   → só HTTP ✅                     │         │ ✅ Alembic │
│  Upload      │ ◄───────────── │  services     → regras de aplicação ✅         │ ◄────── │            │
│  Clientes    │                │  repositories → TODO o SQL ✅ (models: tabelas)│         └────────────┘
│  (Fase 5)    │                │  extraction   → PDF → objetos (Fase 1) ✅      │
└──────────────┘                │  domain       → regras puras (Fase 1) ✅       │
                                │  core         → config, logging, arquivos ✅   │
                                └───────────────────────────────────────────────┘
                                          │ storage/<sha256>.pdf (disco)
```

**Regra de dependência:** as setas de `import` apontam para dentro.

```
api → services → repositories → models (SQLAlchemy)
          │   └─→ core (config, database, armazenamento)
          └────→ extraction → domain
                              ▲
             (domain não importa ninguém do projeto)
```

Endpoints, métodos e códigos HTTP: [api.md](api.md). Modelo do banco, SQLAlchemy e Alembic:
[banco.md](banco.md). Comparação e importação: [comparacao.md](comparacao.md).

## 2. Camada de extração: como o PDF vira um objeto Python

```
 bytes do arquivo
       │
       ▼
 ExtractionPipeline.processar(nome_arquivo, conteudo)      app/extraction/pipeline.py
       │
       ├─ assinatura %PDF? ── não ──► ResultadoExtracao(TIPO_DESCONHECIDO)
       │
       ▼
 DocumentoPdf                    guarda os bytes; lê sob demanda, com cache:
       │                            ├─ .texto     PdfTextReader  (PyPDF2)            readers/
       │                            ├─ .texto_ocr PdfOcrReader   (PyMuPDF+Tesseract) readers/
       │                            └─ .tabelas   PdfTableReader (PyMuPDF find_tables) readers/
       ▼
 DocumentTypeDetector            1º pelo prefixo do nome; 2º pelo conteúdo   detector.py
       │
       ▼
 ExtractorRegistry.obter(tipo)   tipo → estratégia                           registry.py
       │
       ▼
 DocumentExtractor.extrair()     Strategy Pattern                            extractors/
   ├─ NotaFiscalExtractor        OCR → data_emissao + NOME ("Cliente:" / após o processo)
   ├─ PlanilhaComissaoExtractor  tabela → NOME (célula abaixo de "Cliente")
   └─ PrestacaoContasExtractor   texto → NOME ("À") + numero_processo
       │                         nos três: anotação do nome do arquivo → Situacao (enum) [+ corretor]
       │                         (regex em parsers/: funções puras; siglas em data/situacao_siglas.json)
       ▼
 CorrecoesManuais.aplicar()      preenche campos vazios (data/correcoes_manuais.json)
       │
       ▼
 ResultadoExtracao               app/domain/entities.py
```

Depois, para um lote de arquivos:

```
 [ResultadoExtracao, ...]
       │
       ▼
 ConsolidadorFichas.consolidar()   app/domain/consolidacao.py
   1. CHAVE de cada documento = nome lido do CONTEÚDO, normalizado (domain/nomes.py)
   2. reconciliação de OCR: nome da NF com erro de leitura adota a chave de texto mais parecida
   3. agrupamento pela chave (full join do notebook)
   4. reserva: documento sem nome no conteúdo → cliente com o mesmo nome de arquivo
   5. verificadores: mesmo nome de arquivo / nomes parecidos → possíveis duplicidades
   6. a ficha guarda TODOS os documentos do cliente (várias NFs, planilhas, prestações)
       │
       ▼
 Consolidacao
   ├─ fichas: [FichaCliente, ...]   a "tabela geral" (equivalente a final_table)
   ├─ possiveis_duplicidades        para o usuário decidir (tela de revisão)
   └─ reconciliacoes_ocr            transparência: o que foi ajustado automaticamente
       │
       ▼
 gerar_resumo(fichas)               app/domain/relatorio.py → números do dashboard
```

## 3. Decisões de arquitetura (Fase 1)

Cada decisão responde: qual problema resolve, por que esta abordagem, qual alternativa foi
descartada e onde aparece no código.

### D1. Domínio sem dependências
- **Problema:** no notebook, regras de negócio, leitura de arquivos e exibição estavam misturadas nas mesmas células.
- **Decisão:** `app/domain` contém só Python puro (dataclasses, enums, funções).
- **Alternativa descartada:** usar os modelos Pydantic/SQLAlchemy como entidades. Isso acoplaria as regras ao framework e ao banco.
- **Onde:** `app/domain/*`.

### D2. Strategy Pattern para os tipos de documento
- **Problema:** cada tipo de PDF tem regras diferentes, e novos tipos vão surgir (ex.: DOCX das planilhas de prestação de contas).
- **Decisão:** uma classe por tipo com a mesma interface (`DocumentExtractor.extrair`), escolhida por um registro.
- **Alternativa descartada:** `if tipo == ... elif ...` no pipeline. Cada tipo novo obrigaria a editar o pipeline.
- **Onde:** `extractors/`, `registry.py`, `factory.py`.

### D3. Parsers como funções puras; componentes com dependências como classes
- **Problema:** separar o que é regra (testável isoladamente) do que é infraestrutura.
- **Decisão:** regex em funções (`parsers/`); leitores, extractors e pipeline em classes com dependências injetadas no construtor.
- **Alternativa descartada:** classes para tudo (métodos estáticos sem estado são só funções com mais cerimônia).

### D4. Protocol para os leitores de texto
- **Problema:** o OCR é lento e exige o Tesseract, o que tornaria os testes lentos e frágeis.
- **Decisão:** `TextReader` é um `Protocol`; nos testes entra um `LeitorFalso` de poucas linhas.
- **Onde:** `readers/base.py`, `tests/conftest.py`.

### D5. Leitura sob demanda com cache (`DocumentoPdf`)
- **Problema:** detector e extractor podem precisar do mesmo texto; o notebook lia a Prestação duas vezes.
- **Decisão:** `@cached_property`. O OCR só roda se alguém pedir `.texto_ocr`.

### D6. Fronteira de erro por arquivo
- **Problema:** um PDF corrompido interrompia o processamento do lote inteiro.
- **Decisão:** o pipeline captura exceções por arquivo e devolve `status=ERRO` com a mensagem.
- **Alternativa descartada:** deixar a exceção subir e tratar no chamador. Cada chamador teria que repetir o tratamento.

### D7. Dados de negócio fora do código
- **Problema:** corrigir uma data ou uma sigla exigia editar código.
- **Decisão:** `data/situacao_siglas.json` e `data/correcoes_manuais.json`. O arquivo real de correções fica no `.gitignore` (contém nomes de clientes).

### D8. A chave do cliente é o nome lido do conteúdo
- **Problema:** o notebook usava o nome do arquivo (renomeado à mão) como chave. Renomear
  um arquivo mudava o cliente.
- **Decisão:** a chave é o nome lido **de dentro** do documento, normalizado. O nome do
  arquivo só serve como reserva e verificador, e erros de leitura do OCR são reconciliados
  com a camada de texto.
- **Alternativas descartadas:**
  - Unir documentos por qualquer chave em comum (conteúdo **ou** arquivo, com Union-Find):
    unia mais, mas deixava o nome do arquivo decidir a identidade.
  - Fuzzy matching entre todos os nomes: unir nomes digitados diferentes no próprio documento
    é uma decisão de negócio, que vai para a revisão do usuário.
- **Onde:** `domain/nomes.py`, `domain/consolidacao.py`; detalhes e números em
  `docs/migration.md`, seção 4.

### D9. Situação como enum, com siglas em arquivo de dados
- **Problema:** as siglas nos nomes de arquivo são irregulares (`VT.`, `Vl Inct.`, `Acd`,
  `CANCELADA`), e a regra do notebook lia só a primeira palavra.
- **Decisão:** `Situacao` é um `StrEnum`, e a tabela sigla → situação fica em
  `data/situacao_siglas.json`. A relação foi levantada cruzando as siglas com o relatório do
  escritório pelo número do processo.
- **Onde:** `domain/enums.py`, `extraction/siglas.py`, `extraction/parsers/anotacao.py`.

### D10. Números do dashboard no domínio
- **Problema:** o dashboard precisa dos mesmos números que o notebook imprimia (faltantes,
  múltiplos, totais).
- **Decisão:** funções puras em `domain/relatorio.py`. A API só as expõe e o React só as
  exibe, então a regra fica num lugar só e é testável sem servidor.

## 4. Camada de API (Fase 2)

Caminho de uma requisição, do HTTP ao domínio e de volta:

```
POST /api/v1/uploads (multipart)
  │
  ▼
api/routes/upload_routes.py      lê os arquivos, chama o service, agenda o processamento → 202
  │   Depends(...)               api/dependencies.py monta UploadService / ProcessamentoService
  ▼
services/upload_service.py       valida, salva (core/armazenamento.py → SHA-256), cria o lote
  │
  ▼
repositories/…EmMemoria          guarda o Processamento (Fase 3: PostgreSQL)

  ─── depois da resposta (BackgroundTasks) ───
services/processamento_service.py
  ├─ hash repetido no lote → DUPLICADO
  ├─ extraction/pipeline.py (OCR com cache por hash: readers/cache.py)
  └─ domain/consolidacao.py → tabela geral do lote

GET /api/v1/processamentos/{id}/clientes
  → services (localiza o lote, confere se terminou) → schemas/cliente.py (domínio → JSON)
  erros do service → api/erros.py → 404 / 409 com {"detail": ...}
```

### D11. Repositório com contrato (Protocol) e implementação em memória
- **Problema:** a API precisa guardar lotes antes de o banco existir (Fase 3), e rotas e
  services não devem depender de como os dados são guardados.
- **Decisão:** `ProcessamentoRepository` define o contrato;
  `ProcessamentoRepositoryEmMemoria` o implementa com um dicionário protegido por
  `threading.Lock`, porque o processamento roda em outra thread. Na Fase 3 entra a implementação
  SQL, trocada num único lugar (`api/dependencies.py`).
- **Alternativa descartada:** acessar um dicionário global direto nas rotas. Isso espalharia o
  acesso a dados e obrigaria a reescrever as rotas na Fase 3.

### D12. Processamento em segundo plano com BackgroundTasks (202 + polling)
- **Problema:** o OCR leva ~1 s por NF. Um lote de 500 arquivos leva minutos, e a requisição
  HTTP não pode ficar esperando.
- **Decisão:** o upload responde **202 Accepted** assim que os arquivos são salvos. O
  processamento roda em `BackgroundTasks` do FastAPI, e o frontend consulta o progresso
  (`GET /processamentos/{id}`).
- **Alternativa descartada:** fila distribuída (Celery + Redis). Seria overengineering para um
  único servidor. **Limitação aceita:** se o servidor reiniciar durante um lote, o lote para no
  meio (fica `PROCESSANDO`). Com volume maior, a evolução natural é uma fila.

### D13. Armazenamento endereçado pelo conteúdo (SHA-256)
- **Problema:** o mesmo PDF chega com nomes diferentes; é preciso reconhecê-lo e não repetir o
  OCR.
- **Decisão:** cada arquivo é salvo como `storage/<sha256>.pdf`. Hash repetido no lote =
  `DUPLICADO`. O texto do OCR fica em cache pelo hash (`LeitorComCache`, padrão Decorator). O
  cache guarda só o **texto**: situação e corretor vêm do nome do arquivo e são recalculados.
- **Onde:** `core/armazenamento.py`, `extraction/readers/cache.py`, `services/processamento_service.py`.

### D14. Schemas separados do domínio; exceções de negócio traduzidas num lugar só
- **Problema:** o JSON da API é um contrato com o React e não deve mudar a cada refatoração
  interna. Os services não devem conhecer HTTP.
- **Decisão:** `schemas/*` com métodos `de_dominio(...)` explícitos. Os services lançam
  exceções próprias (`services/exceptions.py`), e `api/erros.py` as mapeia para 400/404/409.
- **Alternativa descartada:** `HTTPException` dentro dos services. Isso acoplaria o service ao
  FastAPI e impediria reusá-lo em scripts.

### D15. `async` só onde há espera de rede
- A rota de upload é `async` para ler os arquivos da requisição. O trabalho síncrono (gravar em
  disco) vai para `run_in_threadpool`. As rotas de consulta são `def` comuns, e o FastAPI as
  executa em threads. Nada bloqueia o servidor enquanto um lote é processado.

## 5. Banco de dados (Fase 3)

O fluxo de dados completo:

```
upload ──► processamento + itens (JSONB com o que foi extraído)      revisão do lote
                     │
          POST /importacoes (uma transação)
                     ▼
cliente (chave = nome do conteúdo) ◄── cliente_chave (apelidos)
   └── documento (hash único) ──► alteracao_documento (histórico)
                     │
   GET /clientes (tabela geral) · PUT /documentos/{id} (correção, remanejamento)
   POST /clientes/{id}/unir · GET /dashboard
```

### D16. Importação explícita, numa única transação
- **Problema:** o upload não deve alterar os dados do escritório sem revisão. Uma importação
  interrompida no meio deixaria clientes sem documentos.
- **Decisão:** o upload só extrai. `POST /importacoes` leva o lote para o banco numa única
  transação (`ImportacaoRepository.importar`). A importação é idempotente: arquivos já
  importados (mesmo hash) são contados e não mexidos, inclusive as correções manuais feitas
  neles.
- **Fase 4:** insere a comparação (novo, alterado, igual) e a seleção antes deste passo.

### D17. Chave técnica, chave de negócio e apelidos
- **Problema:** o nome lido do conteúdo une os arquivos, mas tem erros de digitação que o
  usuário corrige unindo clientes. O sistema precisa lembrar dessas decisões.
- **Decisão:** `cliente.id` (técnico, nunca muda) + `cliente.chave` (negócio, única) +
  `cliente_chave` (apelidos). Unir clientes ou renomear transforma a grafia antiga em apelido,
  e a importação procura o cliente por qualquer chave.
- **Alternativa descartada:** o nome como chave primária. Cada correção exigiria atualizar
  todas as FKs, e a grafia antiga seria esquecida.

### D18. Histórico na mesma transação da alteração
- `DocumentoRepository.atualizar` muda o valor e grava a linha em `alteracao_documento` no
  mesmo commit: não existe alteração sem histórico. `campos_editados` marca o que foi
  corrigido à mão (destaque na tela e proteção na Fase 4).

### D19. Repositórios recebem a fábrica de sessões e devolvem domínio
- **Problema:** o processamento roda depois que a requisição acaba, então uma sessão "por
  requisição" já estaria fechada. E models do ORM circulando pelos services trariam
  consultas escondidas ("lazy loading") e acoplamento ao banco.
- **Decisão:** cada método de repositório abre a sua transação (`with sessoes.begin()`) e
  devolve dataclasses do domínio (`repositories/conversao.py`).

### D20. Enums como VARCHAR + CHECK; migrations revisadas à mão
- Ver [banco.md](banco.md). Acrescentar um valor ao enum não exige `ALTER TYPE`. O
  autogenerate duplicava as restrições, e a migration foi corrigida e documentada.

### D21. A tabela geral do lote é calculada, não guardada
- O banco guarda os fatos (o resultado de cada arquivo em `processamento_item.resultado`), e
  a consolidação do lote é recalculada na consulta (função pura, rápida). Uma cópia derivada
  poderia ficar desatualizada.

### D22. Testes com PostgreSQL real
- Os testes `banco` usam `gestao-db-teste`, criado pelas próprias migrations. Isso testa
  código e migrations juntos, com JSONB, IDENTITY e CHECK de verdade. SQLite esconderia
  justamente esses detalhes.

## 6. Comparação (Fase 4)

```
PLANO DO LOTE (domain/importacao.montar_plano) ─┐
                                                ├─► domain/comparacao.comparar ─► tela de comparação
FOTO DO BANCO (ComparacaoService)              ─┘         │
                                                 escolhas do usuário (itens, vincular, sobrescrever)
                                                           ▼
                                   domain/importacao.decidir ─► ImportacaoRepository (1 transação)
```

### D23. Comparação como função pura sobre uma "foto" do banco
- **Problema:** as regras de comparação são o coração do negócio e precisam ser testadas em
  muitos cenários.
- **Decisão:** o `ComparacaoService` só reúne os dados (`EstadoDoBanco`). A regra está em
  `domain/comparacao.comparar`, sem acesso a banco: 13 testes rodam em milissegundos.
- **Alternativa descartada:** comparar com consultas SQL campo a campo. A regra ficaria
  espalhada em SQL e só seria testável com banco.

### D24. Identidade do documento: hash; identidade da versão: cliente + tipo + nome de arquivo
- O mesmo arquivo (hash) é IGUAL onde quer que esteja. Um arquivo com o mesmo nome, do mesmo
  cliente e tipo, mas com outro conteúdo, é uma **nova versão**: atualiza o documento
  existente, e o histórico guarda a troca de hash. Um cliente pode ter vários documentos do
  mesmo tipo, por isso só o nome de arquivo igual indica versão.

### D25. Correções manuais só são sobrescritas por decisão explícita
- Diferença em campo de `campos_editados` = CONFLITO, fora da seleção padrão. Mesmo quando
  o documento é selecionado, a correção é preservada, a não ser que a posição esteja em
  `sobrescrever_campos_editados`. Valores `null` da extração nunca apagam dados.

### D26. Comparar de novo na hora de importar
- A comparação da tela pode estar desatualizada (outro usuário, outra importação). O
  `ImportacaoService` compara de novo, com as vinculações aplicadas, antes de decidir. A tela
  é uma prévia; a regra é aplicada sobre o estado atual.

## 7. Estrutura de pastas (atual)

```
APP/
├── backend/
│   ├── app/
│   │   ├── main.py            criar_app(): CORS, rotas, tratadores de erro
│   │   ├── api/
│   │   │   ├── routes/        saude, dashboard, upload, processamento, comparacao, importacao, cliente, documento
│   │   │   ├── dependencies.py   montagem das peças (Depends)
│   │   │   └── erros.py       exceção de service → código HTTP
│   │   ├── core/              config (.env), logging, database (engine/sessões), armazenamento (SHA-256)
│   │   ├── models/            tabelas SQLAlchemy (cliente, documento, processamento, importacao)
│   │   ├── repositories/      TODO o SQL; devolvem domínio (conversao.py); + versão em memória p/ testes
│   │   ├── services/          Upload, Processamento, Comparacao, Importacao, Cliente, Documento, exceptions
│   │   ├── schemas/           contrato JSON da API (documento, processamento, cliente, comparacao, importacao, relatorio)
│   │   ├── domain/            entities, enums, nomes, consolidacao, relatorio, processamento, comparacao, importacao
│   │   └── extraction/
│   │       ├── readers/       PdfTextReader, PdfOcrReader, PdfTableReader, LeitorComCache
│   │       ├── parsers/       regex do notebook (funções puras)
│   │       ├── extractors/    uma estratégia por tipo de documento
│   │       ├── data/          situacao_siglas.json, correcoes_manuais(.example).json
│   │       ├── detector.py, registry.py, pipeline.py, factory.py
│   │       ├── documento_pdf.py, siglas.py, correcoes_manuais.py
│   ├── alembic/               migrations (0001 estrutura, 0002 contadores) + env.py; alembic.ini
│   ├── scripts/verificar_paridade.py
│   ├── tests/                 api/, banco/ (PostgreSQL), domain/, extraction/, test_core.py
│   ├── storage/               PDFs enviados (fora do Git)
│   ├── requirements.txt, requirements-dev.txt, pyproject.toml, .env.example (.env local, fora do Git)
├── frontend/                  scaffold Vite + React (Fase 5)
└── docs/                      architecture.md, migration.md, api.md, banco.md, comparacao.md
```
