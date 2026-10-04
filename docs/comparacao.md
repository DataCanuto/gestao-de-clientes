# Comparação e importação (Fase 4)

> Pergunta que a Fase 4 responde: **"o que este lote traria de diferente para o banco?"**
> Nada entra no banco sem passar por esta comparação e pela escolha do usuário.

## 1. Fluxo

```
upload ─► processamento (extração) ─► GET /comparacoes/{id} ─► usuário escolhe ─► POST /importacoes
                                          │                                            │
                            PLANO DO LOTE + FOTO DO BANCO              comparação de novo (estado atual)
                                          │                            + decidir() + 1 transação
                                  NOVO · IGUAL · ALTERADO · CONFLITO · ERRO
```

| Etapa | Onde | O que faz |
|---|---|---|
| Plano do lote | `domain/importacao.montar_plano` | Organiza o lote por cliente, com hash e posição de cada arquivo |
| Foto do banco | `services/comparacao_service.py` | Clientes com documentos, todas as chaves (apelidos), documentos sem cliente |
| **Comparação** | `domain/comparacao.comparar` | **Função pura**: plano × foto → status + diferenças |
| Decisão | `domain/importacao.decidir` | Comparação + escolhas → o que criar, atualizar, ignorar, preservar |
| Gravação | `repositories/importacao_repository.py` | Aplica o plano decidido numa única transação |

A comparação **não é guardada**: é recalculada a cada consulta e de novo na importação. Se
algo mudar no banco entre abrir a tela e confirmar, vale o estado atual.

## 2. Status de cada DOCUMENTO

```
hash já está no banco? ──sim──► IGUAL        (o mesmo arquivo, com qualquer nome)
        │não
cliente existe e já tem documento do MESMO TIPO e MESMO NOME de arquivo?
        │sim ──► é uma NOVA VERSÃO:
        │          alguma diferença cai num campo corrigido à mão? ──sim──► CONFLITO
        │                                                          └─não──► ALTERADO (com o diff)
        │não
        └────► NOVO
```

- **Diferença de campo** = `{campo, valor_atual, valor_novo, editado_manualmente}`.
- **Valor que a extração não encontrou (`null`) nunca conta como diferença.** Se o OCR falhou
  desta vez, o valor que está no banco fica.
- Arquivos com erro, de tipo desconhecido ou duplicados no lote aparecem em
  `fora_da_importacao` (status **ERRO**).

## 3. Status de cada CLIENTE

| Situação | Status | Precisa de decisão? |
|---|---|---|
| Todos os documentos já estão no banco (talvez em outro cliente) | IGUAL | não |
| Chave desconhecida, e nenhum cliente parecido | NOVO | não |
| Chave desconhecida, mas **nome parecido** (≥ 0,85) com um cliente existente | CONFLITO | **sim**: vincular ou criar |
| Cliente existe; algum documento em CONFLITO | CONFLITO | sim, por documento |
| Cliente existe; há documentos NOVOS ou ALTERADOS | ALTERADO | não |

**Por que um nome parecido não é unido automaticamente?** "ANA SOUSA" pode ser erro de
digitação de "ANA SOUZA", ou outra pessoa. Quem sabe é o usuário. Ao **vincular**, a grafia
do lote vira **apelido** do cliente escolhido (`cliente_chave`), e os próximos lotes já
reconhecem sozinhos.

(Diferente da reconciliação de OCR da Fase 1: um nome lido por OCR parecido com um nome de
texto do **mesmo lote** é tratado como erro de leitura e ajustado automaticamente.)

## 4. Seleção padrão e escolhas do usuário

`selecionado_por_padrao` diz o que a tela deve trazer marcado:

| Status | Marcado? |
|---|---|
| NOVO, ALTERADO | sim |
| CONFLITO (correção manual seria sobrescrita) | **não**: exige escolha consciente |
| Documentos de cliente que precisa de decisão | **não** |
| IGUAL | nada a importar (o item do lote só é ligado ao documento existente) |

Corpo do `POST /importacoes`:

```json
{
  "processamento_id": 2,
  "itens": [3, 5, 8],                              // opcional: sem ele, vale a seleção padrão
  "vincular_clientes": {"ANA SOUSA": 12},          // opcional: chave do lote -> cliente existente
  "sobrescrever_campos_editados": [5]              // opcional: aqui, o valor novo substitui a correção
}
```

O que acontece com cada documento selecionado:

- **NOVO:** é criado, com o histórico "Importado do processamento N".
- **ALTERADO/CONFLITO:** o documento existente recebe o novo arquivo (novo hash) e só os campos
  que mudaram. **Correções manuais são preservadas**, a menos que a posição esteja em
  `sobrescrever_campos_editados`. O histórico registra a troca de arquivo (hash antigo e novo)
  e cada campo alterado.

Validações: 400 para itens que não pertencem ao lote ou não podem ser importados; 400 para
`sobrescrever` fora da seleção; 404 para cliente vinculado inexistente.

## 5. Resultado nos arquivos reais (atualização de uma pasta)

Cenário: importar a pasta de documentos **sem ~30 arquivos** e depois enviar a pasta **completa**.

| | Resultado |
|---|---|
| Lote 1 (478 arquivos) | 162 s de processamento; 188 clientes e 473 documentos importados |
| Lote 2 (508 arquivos) | **25 s** (OCR em cache pelo hash: só os 30 novos foram lidos) |
| Comparação | **29 NOVO = exatamente os arquivos retirados**; 473 IGUAL; 0 ALTERADO; 6 ERRO (1 não-PDF + 5 duplicados da pasta) |
| Clientes | 26 ALTERADO (ganharam documentos), 1 CONFLITO (grafia parecida com cliente existente, sugestão correta) |
| Importação padrão | 28 criados, 1 ignorado (o do cliente em conflito) |
| Importação com vínculo | +1 documento no cliente sugerido; a comparação passa a mostrar tudo IGUAL |

## 6. Onde estão as regras (para estudar)

| Pergunta | Resposta no código |
|---|---|
| Como o sistema sabe que o arquivo é o mesmo? | Hash SHA-256: `EstadoDoBanco.documento_com_hash` |
| Como sabe que é uma nova versão? | Mesmo cliente, tipo e nome de arquivo: `EstadoDoBanco.versao_anterior` |
| Como identifica que um registro mudou? | `diferencas_de_campos` compara campo a campo, ignorando `null` novos |
| Como protege correções manuais? | `DocumentoArmazenado.campos_editados` → CONFLITO; `decidir()` não aplica sem `sobrescrever` |
| Como sugere clientes parecidos? | `EstadoDoBanco.clientes_parecidos` (similaridade das chaves e apelidos) |
