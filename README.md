# Gestão de Clientes e Documentos

Sistema que reúne os documentos de cada cliente de um escritório (Notas Fiscais, Planilhas de
Comissão e Prestações de Contas, em PDF), identifica a quem cada arquivo pertence e mostra
**quais documentos faltam** para cada cliente.

O projeto foi desenvolvido para um cliente real e é apresentado aqui de forma anonimizada: o
repositório contém apenas código, testes e documentação. Nenhum documento, planilha ou dado de
cliente é versionado (ver [Privacidade](#privacidade)).

Este README conta também **como o projeto evoluiu**: começou como um notebook de análise de
dados e virou uma aplicação full stack com API, banco de dados e interface web.

---

## Evolução do projeto

| | v1: Notebook | v2: Aplicação full stack |
|---|---|---|
| Período | dez/2025 – jan/2026 | set/2026 |
| Formato | Jupyter Notebook, células executadas em ordem | Backend FastAPI + PostgreSQL + frontend React |
| Identificação do cliente | Nome do **arquivo** | Nome lido do **conteúdo** do documento, com reconciliação de erros de OCR |
| Dados | Dicionários de listas paralelas, estado global | Domínio em Python puro, banco relacional com migrations |
| Correções | Dicionários escritos no código | Edição manual na interface, com histórico e origem de cada valor |
| Saída | CSV / Excel | Dashboard, tabela geral, revisão, exportação `.xlsx` e pastas organizadas |
| Atualização | Reprocessar tudo | Comparação entre lotes: só arquivos novos ou alterados são processados |
| Testes | Nenhum | 267 testes no backend e 16 no frontend |

### v1: notebook de análise (`DataManagement_Project/`)

O problema inicial: centenas de PDFs espalhados em pastas, de três tipos diferentes, sem um
lugar que dissesse quais clientes estavam com a documentação completa.

O notebook resolveu isso como um pipeline de ETL:

- leitura de PDFs com texto (PyPDF2) e digitalizados, via OCR (PyMuPDF + Tesseract);
- extração por expressões regulares de data de emissão, número do processo, corretor e situação;
- padronização dos nomes e *full join* entre os três tipos de documento;
- relatório de documentos faltantes em CSV/Excel e junção dos PDFs de cada cliente em um só.

Funcionou, mas expôs os limites do formato: regras, leitura de arquivos e exibição misturadas
nas mesmas células; caminhos de pasta fixos no código; correções manuais escritas como
dicionários; e a chave do cliente era o nome do arquivo, que varia muito.

### v2: aplicação full stack (`backend/`, `frontend/`, `docs/`)

A v2 foi construída em fases, cada uma documentada em `docs/`:

1. **Extração e domínio:** as regras do notebook viraram módulos testáveis, com o
   comportamento original preservado e bugs documentados corrigidos.
2. **API REST (FastAPI):** upload de lotes, processamento em segundo plano e consulta do
   resultado.
3. **Banco de dados (PostgreSQL + SQLAlchemy + Alembic):** clientes, documentos, versões e
   histórico de alterações.
4. **Comparação entre lotes:** ao enviar a pasta de novo, o sistema mostra o que é novo, igual,
   alterado ou conflitante antes de importar.
5. **Interface (React + Vite):** painel, clientes, documentos, revisão, lotes e exportação.

### O que mudou na forma de desenvolver

- **De script para arquitetura em camadas:** `api → services → repositories → models`, com um
  domínio em Python puro que não depende de framework nem de banco.
- **Decisões registradas:** 26 decisões de arquitetura descritas em
  [`docs/architecture.md`](docs/architecture.md), cada uma com o problema, a alternativa
  descartada e onde aparece no código.
- **Paridade antes de evoluir:** a migração manteve as regras do notebook e documentou cada
  mudança intencional em [`docs/migration.md`](docs/migration.md).
- **Testes automatizados**, incluindo testes de integração com PostgreSQL real.
- **Configuração fora do código:** caminhos, credenciais e OCR vêm de variáveis de ambiente
  (`.env`).

---

## Funcionalidades

- **Upload de lotes de PDFs** (arquivos ou pasta inteira), com processamento em segundo plano e
  acompanhamento do progresso.
- **Detecção do tipo de documento** pelo nome e pelo conteúdo.
- **Extração automática:**
  - Nota Fiscal: data de emissão e nome do cliente, via OCR;
  - Planilha de Comissão: nome do cliente (tabela do PDF), corretor e situação;
  - Prestação de Contas: nome do cliente e número do processo.
- **Consolidação por cliente:** junta todos os documentos de cada cliente, reconcilia nomes lidos
  com erro de OCR e aponta possíveis duplicidades para revisão.
- **Documentos faltantes e pendências:** lista de clientes com documentos faltando e de campos
  a verificar.
- **Revisão e edição manual:** correção de datas, corretores e situações; mover documentos entre
  clientes e unir clientes. A grafia corrigida vira um apelido, e as próximas importações já
  juntam os arquivos automaticamente.
- **Comparação e importação incremental:** os arquivos são identificados pelo hash SHA-256, e o
  OCR já feito é reaproveitado.
- **Exportação:** relatório `.xlsx`, PDFs organizados em pastas e PDF único por cliente.
- **Instalação e uso no Windows:** scripts `instalar`, `iniciar` e `backup` para uso local pelo
  escritório.

### Resultado medido (agregado, sem dados pessoais)

- Lote de 478 arquivos: 188 clientes e 473 documentos importados em 162 s.
- Reenvio da pasta completa (508 arquivos): **25 s**, porque só os 30 arquivos novos passaram pelo OCR. A
  comparação marcou como novos exatamente os 29 documentos retirados do primeiro envio.
- Identificar o cliente pelo conteúdo, e não pelo nome do arquivo, encontrou o nome em 189 de 192
  NFs, 151 de 151 planilhas e 162 de 164 prestações.

---

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Backend | Python, FastAPI, Pydantic Settings, Uvicorn |
| Extração | PyMuPDF, PyPDF2, Tesseract OCR (pytesseract), Pillow, regex |
| Banco de dados | PostgreSQL, SQLAlchemy 2, Alembic, psycopg 3 |
| Frontend | React 19, Vite |
| Exportação | openpyxl |
| Testes e qualidade | pytest, `node --test`, oxlint |
| v1 | Jupyter Notebook, pandas |

## Arquitetura

```
React (Vite) ──HTTP/JSON──► FastAPI ──SQL──► PostgreSQL
                              │
                              ├─ api/routes     só HTTP
                              ├─ services       regras de aplicação
                              ├─ repositories   todo o SQL
                              ├─ extraction     PDF → objetos (Strategy por tipo de documento)
                              ├─ domain         regras puras (consolidação, comparação, relatório)
                              └─ core           configuração, logging, armazenamento
                                     │
                                     └─ storage/<sha256>.pdf
```

Detalhes em [`docs/architecture.md`](docs/architecture.md), [`docs/api.md`](docs/api.md),
[`docs/banco.md`](docs/banco.md) e [`docs/comparacao.md`](docs/comparacao.md).

## Estrutura do repositório

```
backend/                 API, extração, domínio, banco (Alembic) e testes
frontend/                interface React
docs/                    arquitetura, API, banco, comparação e migração do notebook
DataManagement_Project/  v1: notebook original
instalar.ps1 / iniciar.ps1 / backup.ps1   scripts de uso local no Windows
```

## Como executar

Pré-requisitos: Python 3, Node.js, PostgreSQL e Tesseract OCR.

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Linux/macOS: .venv/bin/python
cp .env.example .env        # preencha usuário e senha do PostgreSQL
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

No Windows, `Instalar.bat` e `Iniciar Relatorio.bat` fazem esses passos automaticamente.

Testes:

```bash
cd backend && .venv/Scripts/python -m pytest
cd frontend && npm test
```

## Privacidade

- Os documentos enviados, o banco, os backups, os relatórios gerados e as correções manuais ficam
  apenas na máquina onde o sistema roda e estão no `.gitignore`.
- Nomes de pessoas, números de processo e valores usados em testes e exemplos são fictícios.
- Credenciais ficam no `.env` (não versionado); o repositório traz apenas o `.env.example`.

## Autor

**Pedro Canuto**: desenvolvimento, arquitetura e documentação.
