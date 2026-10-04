# API REST

> Fase 4: API com FastAPI, PDFs guardados em disco (por hash), dados no **PostgreSQL** e
> **comparação lote × banco** antes de importar.
> Banco: [banco.md](banco.md). Comparação e importação: [comparacao.md](comparacao.md).

## Como executar

```bash
cd APP/backend
py -3.14 -m venv .venv                                # uma vez
.venv/Scripts/python -m pip install -r requirements-dev.txt
cp .env.example .env                                  # e preencha (banco, TESSERACT_CMD etc.)
.venv/Scripts/python -m alembic upgrade head          # cria/atualiza as tabelas

.venv/Scripts/python -m uvicorn app.main:app --reload
```

- Documentação interativa (gerada automaticamente pelo FastAPI): <http://localhost:8000/docs>
- `--reload` reinicia o servidor a cada alteração no código (só para desenvolvimento).

## Fluxo

```
React                                   FastAPI                                    Segundo plano
  │ POST /api/v1/uploads (multipart)       │                                            │
  │──────────────────────────────────────► │ UploadService: valida, calcula SHA-256,    │
  │                                        │ salva em storage/<hash>.pdf, cria o lote   │
  │ ◄───────────── 202 Accepted {id: 1}    │                                            │
  │                Location: /processamentos/1  ──── BackgroundTasks ─────────────────► │ ProcessamentoService.processar(1)
  │                                        │                                            │  para cada arquivo: pipeline de extração
  │ GET /processamentos/1  (a cada 2 s)    │                                            │  ao final: consolidação (tabela geral)
  │──────────────────────────────────────► │ {status: PROCESSANDO, progresso: 43%}     │
  │   ...                                  │                                            │
  │ ◄──────── {status: CONCLUIDO}          │                                            │
  │ GET /processamentos/1/clientes         │ tabela geral                               │
  │ GET /processamentos/1/resumo           │ números do dashboard                       │
  │ GET /processamentos/1/verificacoes     │ o que revisar                              │
```

## Endpoints

Prefixo: `/api/v1`.

| Método | Rota | O que faz | Respostas |
|---|---|---|---|
| GET | `/saude` | API no ar? OCR disponível? | 200 |
| POST | `/uploads` | Recebe um ou vários PDFs (ou uma pasta) e inicia o processamento | 202, 422 |
| GET | `/processamentos` | Lista os lotes, do mais recente ao mais antigo | 200 |
| GET | `/processamentos/{id}` | Progresso do lote e cada arquivo com os dados extraídos | 200, 404 |
| GET | `/processamentos/{id}/clientes` | **Tabela geral**: cada cliente, todos os seus arquivos e o que falta. `?apenas_com_faltantes=true` filtra | 200, 404, 409 |
| GET | `/processamentos/{id}/resumo` | **Números do dashboard** (totais, faltantes, a verificar) | 200, 404, 409 |
| GET | `/processamentos/{id}/verificacoes` | Possíveis duplicidades, nomes corrigidos do OCR, documentos sem cliente | 200, 404, 409 |
| GET | `/comparacoes/{id}` | **Compara o lote com o banco**: NOVO, IGUAL, ALTERADO, CONFLITO, ERRO, com o diff e a seleção padrão | 200, 404, 409 |
| POST | `/importacoes` | Leva as escolhas para o banco: `processamento_id` + opcionais `itens`, `vincular_clientes`, `sobrescrever_campos_editados` | 201, 400, 404, 409 |
| GET | `/importacoes` | Lista as importações e seus contadores | 200 |
| GET | `/dashboard` | Números da tela inicial sobre os dados do banco | 200 |
| GET | `/clientes` | **Tabela geral** do banco. `?busca=joão`, `?apenas_com_faltantes=true` | 200 |
| GET | `/clientes/{id}` | Um cliente e todos os seus documentos | 200, 404 |
| POST | `/clientes` | Cria um cliente (ex.: destino de um remanejamento) | 201, 409 |
| PUT | `/clientes/{id}` | Corrige o nome (a grafia antiga vira apelido) / marca espólio | 200, 404, 409 |
| DELETE | `/clientes/{id}` | Exclui um cliente **sem** documentos | 204, 404, 409 |
| POST | `/clientes/{id}/unir` | Absorve outro cliente (`{"cliente_origem_id": 7}`): documentos + apelidos | 200, 400, 404 |
| GET | `/documentos` | `?tipo=`, `?cliente_id=`, `?sem_cliente=true`, `?a_verificar=true` | 200 |
| GET | `/documentos/{id}` | Um documento | 200, 404 |
| GET | `/documentos/{id}/historico` | Todas as alterações do documento | 200, 404 |
| GET | `/documentos/{id}/arquivo` | O PDF original, para conferir na tela | 200, 404 |
| PUT | `/documentos/{id}` | **Correção manual** e/ou **mudança de cliente** | 200, 400, 404 |
| DELETE | `/documentos/{id}` | Exclui o documento e o arquivo | 204, 404 |

### Por que cada método HTTP

| Método | Significado | Onde é usado |
|---|---|---|
| **GET** | Ler, sem alterar nada. Pode ser repetido à vontade | Todas as consultas, inclusive o polling de progresso |
| **POST** | Criar um recurso novo; repetir cria outro | `POST /uploads` cria um processamento |
| **PUT** | Substituir o estado de um recurso existente; repetir dá o mesmo resultado | `PUT /documentos/{id}` (correção manual), `PUT /clientes/{id}` |
| **DELETE** | Remover um recurso | `DELETE /documentos/{id}`, `DELETE /clientes/{id}` |

**Ações** que mexem em vários recursos de uma vez (unir clientes, importar um lote) são
modeladas como **POST** em um sub-recurso (`/clientes/{id}/unir`) ou como a criação de um
registro da ação (`POST /importacoes`).

**PUT e não PATCH:** o corpo do `PUT /documentos/{id}` é o estado **completo** dos campos
editáveis, e não só o que mudou. O frontend envia todos os campos, com os valores atuais nos
que não mudaram, e o resultado não depende de quantas vezes a requisição é repetida
(idempotência). O PATCH ("mude só isto") seria a alternativa, com semântica mais difícil de
acertar para campos que podem ficar vazios.

### Códigos de resposta

| Código | Quando |
|---|---|
| 200 OK | Consulta bem-sucedida |
| 202 Accepted | Upload aceito; o processamento **ainda vai acontecer**. O cabeçalho `Location` diz onde acompanhar |
| 400 Bad Request | Requisição sem sentido para a regra de negócio (ex.: lote vazio) |
| 404 Not Found | O processamento não existe |
| 201 Created | Recurso criado: importação, cliente |
| 204 No Content | Exclusão feita (resposta sem corpo) |
| 409 Conflict | Conflito com o estado atual: lote ainda em processamento, cliente com documentos, nome já usado por outro cliente |
| 422 Unprocessable Entity | Formato inválido, detectado automaticamente pelo FastAPI (ex.: POST sem o campo `arquivos`) |

Todos os erros têm o formato `{"detail": "mensagem"}`.

## Exemplos

**Corrigir a data de uma NF e mover para outro cliente** (um único PUT):

```bash
curl -X PUT http://localhost:8000/api/v1/documentos/12   -H "Content-Type: application/json"   -d '{"cliente_id": 7, "data_emissao": "2023-03-08", "situacao": null}'
```

O documento volta com `"campos_editados": ["data_emissao"]`, e `GET /documentos/12/historico`
mostra a correção (`EDICAO_MANUAL`) e a mudança de cliente (`REMANEJAMENTO`). Enviar um campo
que não se aplica ao tipo (ex.: `corretor` numa NF) retorna **400**.

**Unir duas fichas do mesmo cliente** (grafias diferentes nos documentos):

```bash
curl -X POST http://localhost:8000/api/v1/clientes/3/unir   -H "Content-Type: application/json" -d '{"cliente_origem_id": 8}'
```

**Enviar arquivos** (o campo `arquivos` se repete, um por arquivo):

```bash
curl -X POST http://localhost:8000/api/v1/uploads \
  -F "arquivos=@NF Ana Souza.pdf" \
  -F "arquivos=@Planilha Comissão Ana Souza (VT Helena).pdf"
```

```json
HTTP/1.1 202 Accepted
Location: /api/v1/processamentos/1

{"id": 1, "status": "PENDENTE", "total_arquivos": 2, "arquivos_processados": 0, "progresso_percentual": 0, ...}
```

**Upload de pasta:** no navegador, `<input type="file" webkitdirectory>` entrega os arquivos da
pasta. O frontend envia o caminho relativo como nome (`formData.append("arquivos", arquivo,
arquivo.webkitRelativePath)`). O item guarda o caminho, e a extração usa só o nome do arquivo.

**Uma linha da tabela geral** (`GET /processamentos/1/clientes`):

```json
{
  "nome": "ANA SOUZA",
  "chave": "ANA SOUZA",
  "espolio": false,
  "quantidade_documentos": {"NOTA_FISCAL": 2, "PLANILHA_COMISSAO": 1, "PRESTACAO_CONTAS": 0},
  "documentos_faltantes": ["PRESTACAO_CONTAS"],
  "documentos_a_verificar": 1,
  "datas_nf": ["2023-03-08", "2024-01-10"],
  "situacoes": ["VALOR_TOTAL"],
  "corretores": ["HELENA"],
  "numeros_processo": [],
  "documentos": [
    {"nome_arquivo": "NF Ana Souza.pdf", "tipo": "NOTA_FISCAL", "nome_cliente": "ANA SOUZA",
     "dados": {"data_emissao": "2023-03-08", "situacao": null, ...},
     "campos_a_verificar": [], "avisos": []}
  ]
}
```

**Mesmo arquivo com outro nome:** o hash SHA-256 é igual. O segundo item volta com
`"status": "DUPLICADO"` e `"duplicado_de": "<nome do primeiro>"`, e não é contado duas vezes
na tabela geral.

## Como o React vai chamar a API (Fase 5)

```js
// services/api.js
const api = axios.create({ baseURL: "http://localhost:8000/api/v1" });

const form = new FormData();
arquivos.forEach((a) => form.append("arquivos", a, a.webkitRelativePath || a.name));
const { data: lote } = await api.post("/uploads", form);           // 202 { id }

const { data: progresso } = await api.get(`/processamentos/${lote.id}`);  // polling
const { data: clientes } = await api.get(`/processamentos/${lote.id}/clientes`);
```

O navegador só permite essas chamadas entre origens diferentes (`localhost:5173` →
`localhost:8000`) porque a API libera o frontend via **CORS** (`CORS_ORIGINS` no `.env`).
