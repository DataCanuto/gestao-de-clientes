# Banco de dados: PostgreSQL, SQLAlchemy e Alembic

## 1. Modelo

```
┌──────────────────┐        ┌───────────────────────┐
│ cliente          │ 1    n │ cliente_chave         │   todas as grafias (chaves) que
│──────────────────│───────<│───────────────────────│   identificam o cliente: a principal
│ id (PK, BIGINT)  │        │ chave (PK)            │   e os APELIDOS criados ao unir
│ nome             │        │ cliente_id (FK)       │   clientes ou renomear
│ chave (UNIQUE)   │        └───────────────────────┘
│ espolio          │
└────────┬─────────┘
         │ 1
         │        cliente_id NULL = documento sem cliente ("a verificar")
         │ n
┌────────┴──────────────────┐ 1    n ┌──────────────────────────┐
│ documento                 │───────<│ alteracao_documento      │  histórico (versionamento):
│───────────────────────────│        │──────────────────────────│  importação, edição manual,
│ id (PK)                   │        │ campo, valor_anterior,   │  remanejamento, união
│ hash_sha256 (UNIQUE)      │        │ valor_novo, origem,      │
│ nome_arquivo, tipo        │        │ criado_em                │
│ cliente_id (FK, NULL)     │        └──────────────────────────┘
│ nome_pelo_conteudo        │
│ data_emissao      (NF)    │
│ situacao          (todos) │
│ corretor, anotacao (Plan.)│
│ nome_encontrado,          │
│ numero_processo   (Prest.)│
│ avisos, campos_editados   │  (JSONB)
└────────▲──────────────────┘
         │ documento_id (preenchido na importação)
┌────────┴──────────────────┐ n    1 ┌──────────────────────────┐ 1   n ┌──────────────┐
│ processamento_item        │>───────│ processamento            │──────<│ importacao   │
│ posicao, nome_arquivo,    │        │ status, criado_em,       │       │ contadores   │
│ hash, status, resultado   │        │ iniciado_em, finalizado  │       └──────────────┘
│ (JSONB: o que foi extraído)│       └──────────────────────────┘
└───────────────────────────┘
```

### Por que assim

| Decisão | Motivo | Alternativa descartada |
|---|---|---|
| `id` técnico (BIGINT IDENTITY) como chave primária | Corrigir um nome não obriga a atualizar as tabelas que apontam para o cliente | Nome como PK: uma correção de grafia se propagaria por todas as FKs |
| `cliente.chave` única = nome lido do conteúdo, normalizado | É o que une os arquivos (regra do negócio) | — |
| `cliente_chave` (apelidos) | Unir "ALVEZ" com "ALVES" grava a grafia errada como apelido: a próxima importação já acerta | Unir só os documentos: o erro voltaria no próximo lote |
| Uma tabela `documento` para os 3 tipos | A tabela geral sai numa consulta; um endpoint de edição | Uma tabela por tipo: 3 junções e 3 endpoints |
| `hash_sha256` único | O mesmo arquivo nunca entra duas vezes, qualquer que seja o nome | Nome do arquivo como identidade (muda à vontade) |
| `alteracao_documento` | Cada mudança de valor fica registrada: quem, quando, de quanto para quanto | Guardar só o valor atual (perde o histórico) |
| `campos_editados` | Marca o que foi corrigido à mão: reimportar nunca sobrescreve | — |
| `processamento_item.resultado` em JSONB | Guarda o que foi extraído de cada arquivo do lote (revisão sem refazer OCR) | Tabelas por campo: estrutura rígida para um dado só de consulta |
| Enums como `VARCHAR + CHECK` | Acrescentar um valor (ex.: `VERIFICAR`) não exige `ALTER TYPE` | ENUM nativo do PostgreSQL |

## 2. SQLAlchemy em 5 conceitos

| Conceito | Onde | O que é |
|---|---|---|
| **Engine** | `core/database.py` | Sabe se conectar (URL + pool de conexões). Uma por aplicação |
| **Session** | `core/database.py` (`sessionmaker`) | Uma "conversa" com o banco que termina em commit ou rollback |
| **Model** | `models/*.py` | Uma classe = uma tabela; `Mapped[...]` + `mapped_column(...)` = uma coluna |
| **relationship** | `models/*.py` | Navegar entre tabelas em Python (`cliente.documentos`) |
| **select / update** | `repositories/*.py` | Consultas escritas em Python, traduzidas para SQL |

**Como um PDF vira registro no PostgreSQL:**

```
PDF ──pipeline──► ResultadoExtracao (domínio)
    ──ImportacaoService──► DocumentoAImportar (plano)
    ──ImportacaoRepository──► DocumentoModel(...)  ──session.add + commit──► INSERT INTO documento ...
```

**E de volta:** `select(DocumentoModel)` → `documento_para_dominio(model)` (em
`repositories/conversao.py`) → `DocumentoArmazenado` → schema → JSON. Os services **nunca**
recebem models do SQLAlchemy.

**Transações:** cada método de repositório é uma transação (`with sessoes.begin():`). A
importação de um lote inteiro é UM método, portanto uma transação só: se algo falhar no
meio, nada é gravado.

**Evitar o "N+1":** `selectinload(ClienteModel.documentos)` busca os documentos de todos os
clientes numa segunda consulta, em vez de uma consulta por cliente.

## 3. Alembic (migrations)

Uma migration é um script versionado que leva o banco de uma versão do esquema para a
próxima. A tabela `alembic_version` guarda a última aplicada.

```bash
cd APP/backend

# aplicar todas as migrations pendentes (banco novo ou atualização)
.venv/Scripts/python -m alembic upgrade head

# ver em que versão o banco está
.venv/Scripts/python -m alembic current

# depois de ALTERAR um model: gerar a migration com as diferenças
.venv/Scripts/python -m alembic revision --autogenerate -m "descricao da mudanca"
#   -> SEMPRE revisar o arquivo gerado em alembic/versions/ antes de aplicar

# conferir se models e banco estão iguais
.venv/Scripts/python -m alembic check

# desfazer a última migration
.venv/Scripts/python -m alembic downgrade -1
```

- A URL do banco **não** fica no `alembic.ini`: `alembic/env.py` lê do `.env`, via
  `app/core/config.py`. A senha não vai para o Git.
- **Revisar migrations geradas é obrigatório.** Na `0001`, o autogenerate repetia cada CHECK
  de enum três vezes. O arquivo foi corrigido à mão, e o cabeçalho dele registra o que mudou.
- **Migration sobre banco com dados (`0002`).** Adicionar uma coluna `NOT NULL` sem
  `server_default` falha em qualquer tabela que já tenha linhas. O autogenerate não coloca o
  default, e ele foi acrescentado à mão (`server_default='0'`). O `downgrade` foi testado
  (`alembic downgrade -1` e `upgrade head` de novo).

| Versão | Mudança |
|---|---|
| `0001` | Estrutura inicial (7 tabelas) |
| `0002` | `importacao.documentos_atualizados` e `documentos_ignorados` (Fase 4) |
- A **convenção de nomes** (`core/database.py`) dá nomes previsíveis a chaves e índices
  (`fk_documento_cliente_id_cliente`), o que permite ao Alembic alterá-los depois.

## 4. Testes com o banco

Os testes marcados com `banco` usam um banco separado, `<POSTGRES_DB>-teste`
(`gestao-db-teste`). Ele é criado automaticamente, recebe a estrutura pelas migrations do
Alembic (testando as próprias migrations) e é esvaziado (`TRUNCATE`) antes de cada teste.
Os seus dados em `gestao-db` nunca são tocados.

```bash
.venv/Scripts/python -m pytest -m banco          # só os testes com PostgreSQL
.venv/Scripts/python -m pytest -m "not banco"    # sem PostgreSQL (ex.: numa máquina sem banco)
```

## 5. Consultas úteis (psql ou pgAdmin)

```sql
-- clientes com documentos faltando
SELECT c.nome,
       count(*) FILTER (WHERE d.tipo = 'NOTA_FISCAL')       AS nfs,
       count(*) FILTER (WHERE d.tipo = 'PLANILHA_COMISSAO') AS planilhas,
       count(*) FILTER (WHERE d.tipo = 'PRESTACAO_CONTAS')  AS prestacoes
FROM cliente c LEFT JOIN documento d ON d.cliente_id = c.id
GROUP BY c.id, c.nome
HAVING count(*) FILTER (WHERE d.tipo = 'NOTA_FISCAL') = 0
    OR count(*) FILTER (WHERE d.tipo = 'PLANILHA_COMISSAO') = 0
    OR count(*) FILTER (WHERE d.tipo = 'PRESTACAO_CONTAS') = 0
ORDER BY c.nome;

-- histórico de um documento
SELECT campo, valor_anterior, valor_novo, origem, criado_em
FROM alteracao_documento WHERE documento_id = 1 ORDER BY id;

-- todas as grafias que levam ao mesmo cliente
SELECT c.nome, k.chave FROM cliente c JOIN cliente_chave k ON k.cliente_id = c.id ORDER BY c.nome;
```
