"""Comparação lote x banco e decisão do que importar (funções puras, sem banco)."""

from datetime import date

from app.domain.comparacao import EstadoDoBanco, comparar
from app.domain.entities import DadosNotaFiscal, DadosPlanilhaComissao, DocumentoArmazenado, FichaCliente, ResultadoExtracao
from app.domain.enums import Situacao, StatusComparacao, StatusExtracao, StatusItem, TipoDocumento
from app.domain.importacao import ClienteAImportar, DocumentoAImportar, ItemForaDaImportacao, PlanoDoLote, decidir

NF = TipoDocumento.NOTA_FISCAL
IGUAL, NOVO, ALTERADO, CONFLITO = (
    StatusComparacao.IGUAL,
    StatusComparacao.NOVO,
    StatusComparacao.ALTERADO,
    StatusComparacao.CONFLITO,
)


def nf(nome_arquivo: str, data: date | None) -> ResultadoExtracao:
    return ResultadoExtracao(nome_arquivo, StatusExtracao.SUCESSO, NF, nome_pelo_conteudo="ANA SOUZA", dados=DadosNotaFiscal(data))


def armazenada(documento_id: int, hash_sha256: str, nome_arquivo: str, data: date | None, editados=()) -> DocumentoArmazenado:
    return DocumentoArmazenado(
        nome_arquivo,
        StatusExtracao.SUCESSO,
        NF,
        nome_pelo_conteudo="ANA SOUZA",
        dados=DadosNotaFiscal(data),
        id=documento_id,
        hash_sha256=hash_sha256,
        cliente_id=1,
        campos_editados=list(editados),
    )


def banco(*documentos: DocumentoArmazenado) -> EstadoDoBanco:
    ana = FichaCliente(nome="Ana Souza", chave="ANA SOUZA", id=1, documentos=list(documentos))
    return EstadoDoBanco([ana], {"ANA SOUZA": 1}, [])


def lote(*clientes: ClienteAImportar) -> PlanoDoLote:
    return PlanoDoLote(1, list(clientes), [], [])


def ana(*documentos: DocumentoAImportar, chave: str = "ANA SOUZA") -> ClienteAImportar:
    return ClienteAImportar(chave, chave.title(), False, list(documentos))


def doc(posicao: int, hash_sha256: str, resultado: ResultadoExtracao) -> DocumentoAImportar:
    return DocumentoAImportar(posicao, hash_sha256, 100, resultado)


V1 = armazenada(10, "h1", "NF Ana Souza.pdf", date(2023, 3, 8))


class TestStatusDoDocumento:
    def test_mesmo_hash_e_igual(self):
        comparacao = comparar(lote(ana(doc(1, "h1", nf("NF qualquer nome.pdf", date(2023, 3, 8))))), banco(V1))
        [documento] = comparacao.clientes[0].documentos
        assert (documento.status, documento.documento_id) == (IGUAL, 10)
        assert comparacao.clientes[0].status is IGUAL

    def test_mesmo_nome_com_conteudo_diferente_e_nova_versao(self):
        comparacao = comparar(lote(ana(doc(1, "h2", nf("NF Ana Souza.pdf", date(2023, 4, 10))))), banco(V1))
        [documento] = comparacao.clientes[0].documentos
        assert documento.status is ALTERADO
        [diferenca] = documento.diferencas
        assert (diferenca.campo, diferenca.valor_atual, diferenca.valor_novo) == ("data_emissao", date(2023, 3, 8), date(2023, 4, 10))
        assert comparacao.clientes[0].status is ALTERADO

    def test_nova_versao_que_mudaria_correcao_manual_e_conflito(self):
        corrigida = armazenada(10, "h1", "NF Ana Souza.pdf", date(2023, 3, 9), editados=["data_emissao"])
        comparacao = comparar(lote(ana(doc(1, "h2", nf("NF Ana Souza.pdf", date(2023, 4, 10))))), banco(corrigida))
        documento = comparacao.clientes[0].documentos[0]
        assert documento.status is CONFLITO
        assert documento.diferencas[0].editado_manualmente
        assert comparacao.clientes[0].status is CONFLITO

    def test_valor_nao_encontrado_na_extracao_nao_apaga_o_atual(self):
        comparacao = comparar(lote(ana(doc(1, "h2", nf("NF Ana Souza.pdf", None)))), banco(V1))
        documento = comparacao.clientes[0].documentos[0]
        assert documento.status is ALTERADO  # o arquivo mudou...
        assert documento.diferencas == []  # ...mas nenhum dado seria apagado

    def test_arquivo_diferente_e_documento_novo(self):
        comparacao = comparar(lote(ana(doc(1, "h3", nf("NF Ana Souza (2).pdf", date(2024, 1, 1))))), banco(V1))
        assert comparacao.clientes[0].documentos[0].status is NOVO
        assert comparacao.clientes[0].status is ALTERADO  # cliente existente ganha documento


class TestStatusDoCliente:
    def test_cliente_desconhecido_e_novo(self):
        comparacao = comparar(lote(ana(doc(1, "h9", nf("NF Bruno.pdf", None)), chave="BRUNO LIMA")), banco(V1))
        assert comparacao.clientes[0].status is NOVO
        assert comparacao.clientes[0].cliente_id is None

    def test_cliente_parecido_com_existente_e_conflito_com_sugestao(self):
        comparacao = comparar(lote(ana(doc(1, "h9", nf("NF Ana.pdf", None)), chave="ANA SOUSA")), banco(V1))
        cliente = comparacao.clientes[0]
        assert cliente.status is CONFLITO
        assert cliente.precisa_decisao
        assert [(s.cliente_id, s.nome) for s in cliente.sugestoes] == [(1, "Ana Souza")]

    def test_cliente_desconhecido_com_todos_os_arquivos_ja_no_banco_e_igual(self):
        # O lote agrupou sob outra chave arquivos que o banco já tem (em outro cliente).
        comparacao = comparar(lote(ana(doc(1, "h1", nf("NF Ana Souza.pdf", None)), chave="ANA SOUSA")), banco(V1))
        cliente = comparacao.clientes[0]
        assert cliente.status is IGUAL
        assert not cliente.precisa_decisao
        assert cliente.documentos[0].cliente_id_no_banco == 1

    def test_vincular_resolve_o_conflito_e_compara_com_o_cliente_escolhido(self):
        plano = lote(ana(doc(1, "h2", nf("NF Ana Souza.pdf", date(2023, 4, 10))), chave="ANA SOUSA"))
        comparacao = comparar(plano, banco(V1), vincular={"ANA SOUSA": 1})
        cliente = comparacao.clientes[0]
        assert (cliente.cliente_id, cliente.precisa_decisao) == (1, False)
        assert cliente.documentos[0].status is ALTERADO  # agora encontra a versão anterior


class TestSelecaoEDecisao:
    def test_selecao_padrao_deixa_de_fora_conflitos_e_clientes_a_decidir(self):
        corrigida = armazenada(10, "h1", "NF Ana Souza.pdf", date(2023, 3, 9), editados=["data_emissao"])
        plano = lote(
            ana(doc(1, "h2", nf("NF Ana Souza.pdf", date(2023, 4, 10))), doc(2, "h3", nf("NF Ana (2).pdf", None))),
            ana(doc(3, "h4", nf("NF Ana Sousa.pdf", None)), chave="ANA SOUSA"),
            ana(doc(4, "h5", nf("NF Bruno.pdf", None)), chave="BRUNO LIMA"),
        )
        comparacao = comparar(plano, banco(corrigida))
        # 1 = CONFLITO (não marcado), 2 = NOVO, 3 = cliente parecido (a decidir), 4 = cliente NOVO
        assert comparacao.selecao_padrao() == {2, 4}

    def test_resumo(self):
        plano = PlanoDoLote(
            1,
            [ana(doc(1, "h1", nf("NF Ana Souza.pdf", date(2023, 3, 8))), doc(2, "h3", nf("NF Ana (2).pdf", None)))],
            [],
            [ItemForaDaImportacao(3, "x.xlsx", StatusItem.TIPO_DESCONHECIDO, "O arquivo não é um PDF.")],
        )
        resumo = comparar(plano, banco(V1)).resumo
        assert resumo["documentos"][IGUAL] == 1
        assert resumo["documentos"][NOVO] == 1
        assert resumo["documentos"][StatusComparacao.ERRO] == 1
        assert resumo["clientes"][ALTERADO] == 1

    def test_decidir_preserva_correcao_manual_a_nao_ser_que_pedido(self):
        corrigida = armazenada(10, "h1", "NF Ana Souza.pdf", date(2023, 3, 9), editados=["data_emissao"])
        planilha = ResultadoExtracao(
            "Planilha Comissão Ana.pdf",
            StatusExtracao.SUCESSO,
            TipoDocumento.PLANILHA_COMISSAO,
            dados=DadosPlanilhaComissao("HELENA", Situacao.VALOR_TOTAL),
        )
        plano = lote(ana(doc(1, "h2", nf("NF Ana Souza.pdf", date(2023, 4, 10))), doc(2, "h3", planilha)))
        comparacao = comparar(plano, banco(corrigida))

        preservando = decidir(plano, comparacao, {1, 2}, {}, set())
        [atualizacao] = preservando.clientes[0].atualizacoes
        assert atualizacao.campos == {}  # correção manual preservada
        assert [d.posicao_item for d in preservando.clientes[0].novos] == [2]

        sobrescrevendo = decidir(plano, comparacao, {1}, {}, {1})
        [atualizacao] = sobrescrevendo.clientes[0].atualizacoes
        assert atualizacao.campos == {"data_emissao": date(2023, 4, 10)}
        assert atualizacao.campos_sobrescritos == ["data_emissao"]
        assert sobrescrevendo.ignorados == 1  # a planilha não foi selecionada

    def test_decidir_documento_igual_so_liga_o_item(self):
        plano = lote(ana(doc(1, "h1", nf("NF Ana Souza.pdf", date(2023, 3, 8)))))
        decidido = decidir(plano, comparar(plano, banco(V1)), set(), {}, set())
        assert decidido.clientes[0].iguais == [(1, 10)]
        assert decidido.ignorados == 0
