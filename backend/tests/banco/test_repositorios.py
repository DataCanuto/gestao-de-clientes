"""Repositórios SQL contra o PostgreSQL de testes."""

from datetime import date

import pytest

from app.domain.entities import DadosNotaFiscal, DadosPlanilhaComissao, DadosPrestacaoContas, ResultadoExtracao
from app.domain.enums import OrigemAlteracao, Situacao, StatusExtracao, StatusItem, StatusProcessamento, TipoDocumento
from app.domain.importacao import AtualizacaoDeDocumento, ClienteDecidido, DocumentoAImportar, PlanoDecidido
from app.domain.processamento import ItemProcessamento
from app.repositories import (
    ClienteRepository,
    DocumentoRepository,
    ImportacaoRepository,
    ProcessamentoRepositorySql,
)

pytestmark = pytest.mark.banco

NF_ANA = ResultadoExtracao(
    "NF Ana Souza.pdf",
    StatusExtracao.SUCESSO,
    TipoDocumento.NOTA_FISCAL,
    nome_pelo_arquivo="Ana Souza",
    nome_pelo_conteudo="ANA SOUZA",
    dados=DadosNotaFiscal(date(2023, 3, 8)),
)
PLANILHA_ANA = ResultadoExtracao(
    "Planilha Comissão Ana Souza (VT Helena).pdf",
    StatusExtracao.SUCESSO,
    TipoDocumento.PLANILHA_COMISSAO,
    nome_pelo_conteudo="ANA SOUZA",
    dados=DadosPlanilhaComissao("HELENA", Situacao.VALOR_TOTAL, "VT Helena"),
    avisos=["um aviso"],
)
PRESTACAO_ANA = ResultadoExtracao(
    "Prestação de Contas Ana.pdf",
    StatusExtracao.SUCESSO,
    TipoDocumento.PRESTACAO_CONTAS,
    nome_pelo_conteudo="ANA SOUZA",
    dados=DadosPrestacaoContas("ANA SOUZA", "0001001-37"),
)


def _processamento_com(repositorio: ProcessamentoRepositorySql, *resultados: ResultadoExtracao) -> int:
    itens = [ItemProcessamento(i, r.nome_arquivo, f"hash-{r.nome_arquivo}", 100) for i, r in enumerate(resultados, 1)]
    processamento = repositorio.criar(itens)
    for item, resultado in zip(itens, resultados):
        item.status, item.resultado = StatusItem.SUCESSO, resultado
        repositorio.atualizar_item(processamento.id, item)
    repositorio.concluir(processamento.id)
    return processamento.id


def _importar_ana(sessoes, *resultados: ResultadoExtracao, chave: str = "ANA SOUZA"):
    """Importa documentos novos para o cliente da chave (criando-o se preciso)."""
    processamento_id = _processamento_com(ProcessamentoRepositorySql(sessoes), *resultados)
    documentos = [DocumentoAImportar(i, f"hash-{r.nome_arquivo}", 100, r) for i, r in enumerate(resultados, 1)]
    existentes = {d.hash_sha256: d.id for d in DocumentoRepository(sessoes).listar()}
    cliente = ClienteDecidido(chave, "Ana Souza", False, cliente_id=None)
    for documento in documentos:
        if documento.hash_sha256 in existentes:
            cliente.iguais.append((documento.posicao_item, existentes[documento.hash_sha256]))
        else:
            cliente.novos.append(documento)
    return ImportacaoRepository(sessoes).importar(PlanoDecidido(processamento_id, [cliente]))


class TestProcessamentoRepositorySql:
    def test_resultado_da_extracao_ida_e_volta_pelo_jsonb(self, sessoes):
        repositorio = ProcessamentoRepositorySql(sessoes)
        processamento_id = _processamento_com(repositorio, NF_ANA, PLANILHA_ANA)

        processamento = repositorio.obter(processamento_id)
        assert processamento.status is StatusProcessamento.CONCLUIDO
        assert [item.resultado for item in processamento.itens] == [NF_ANA, PLANILHA_ANA]

    def test_listagem_nao_carrega_os_resultados(self, sessoes):
        repositorio = ProcessamentoRepositorySql(sessoes)
        _processamento_com(repositorio, NF_ANA)
        [processamento] = repositorio.listar()
        assert processamento.itens[0].resultado is None
        assert processamento.arquivos_processados == 1

    def test_falha(self, sessoes):
        repositorio = ProcessamentoRepositorySql(sessoes)
        processamento = repositorio.criar([ItemProcessamento(1, "a.pdf", "h", 1)])
        repositorio.falhar(processamento.id, "RuntimeError: x")
        assert repositorio.obter(processamento.id).status is StatusProcessamento.FALHOU


class TestImportacaoRepository:
    def test_cria_cliente_e_documentos(self, sessoes):
        importacao = _importar_ana(sessoes, NF_ANA, PLANILHA_ANA, PRESTACAO_ANA)

        assert (importacao.clientes_criados, importacao.documentos_criados) == (1, 3)
        [ficha] = ClienteRepository(sessoes).listar()
        assert ficha.chave == "ANA SOUZA"
        assert ficha.documentos_faltantes == []
        assert ficha.datas_nf == [date(2023, 3, 8)]
        assert ficha.situacoes == [Situacao.VALOR_TOTAL]

    def test_reimportar_o_mesmo_arquivo_nao_duplica(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        segunda = _importar_ana(sessoes, NF_ANA)
        assert (segunda.clientes_criados, segunda.documentos_criados, segunda.documentos_ja_existentes) == (0, 0, 1)
        assert len(DocumentoRepository(sessoes).listar()) == 1

    def test_item_do_lote_fica_ligado_ao_documento(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        processamento = ProcessamentoRepositorySql(sessoes).obter(1)
        assert processamento.itens[0].documento_id == DocumentoRepository(sessoes).listar()[0].id

    def test_historico_registra_a_importacao(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        [alteracao] = DocumentoRepository(sessoes).historico(1)
        assert alteracao.origem is OrigemAlteracao.IMPORTACAO


    def test_nova_versao_atualiza_o_documento_e_preserva_a_correcao_manual(self, sessoes):
        _importar_ana(sessoes, NF_ANA, PLANILHA_ANA)
        documentos = DocumentoRepository(sessoes)
        documentos.atualizar(2, {"corretor": "JULIANA"}, OrigemAlteracao.EDICAO_MANUAL)  # correção manual

        processamento_id = _processamento_com(ProcessamentoRepositorySql(sessoes), NF_ANA, PLANILHA_ANA)
        nova_nf = DocumentoAImportar(1, "hash-nf-v2", 120, NF_ANA)
        nova_planilha = DocumentoAImportar(2, "hash-planilha-v2", 120, PLANILHA_ANA)
        cliente = ClienteDecidido(
            "ANA SOUZA",
            "Ana Souza",
            False,
            cliente_id=1,
            atualizacoes=[
                AtualizacaoDeDocumento(1, nova_nf, {"data_emissao": date(2023, 4, 10)}, []),
                AtualizacaoDeDocumento(2, nova_planilha, {}, []),  # o corretor manual fica
            ],
        )
        importacao = ImportacaoRepository(sessoes).importar(PlanoDecidido(processamento_id, [cliente], ignorados=3))

        assert (importacao.documentos_atualizados, importacao.documentos_ignorados) == (2, 3)
        nf = documentos.obter(1)
        assert (nf.hash_sha256, nf.dados.data_emissao) == ("hash-nf-v2", date(2023, 4, 10))
        assert [h.campo for h in documentos.historico(1)] == ["documento", "arquivo", "data_emissao"]
        planilha = documentos.obter(2)
        assert (planilha.dados.corretor, planilha.campos_editados) == ("JULIANA", ["corretor"])

    def test_vincular_grava_a_chave_do_lote_como_apelido(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        processamento_id = _processamento_com(ProcessamentoRepositorySql(sessoes), PLANILHA_ANA)
        cliente = ClienteDecidido(
            "ANA SOUSA",
            "Ana Sousa",
            False,
            cliente_id=1,
            vinculado_manualmente=True,
            novos=[DocumentoAImportar(1, "hash-p", 100, PLANILHA_ANA)],
        )
        ImportacaoRepository(sessoes).importar(PlanoDecidido(processamento_id, [cliente]))
        assert ClienteRepository(sessoes).id_pela_chave("ANA SOUSA") == 1
        assert ClienteRepository(sessoes).mapa_de_chaves() == {"ANA SOUZA": 1, "ANA SOUSA": 1}

    def test_cliente_sem_nada_a_gravar_nao_e_criado(self, sessoes):
        processamento_id = _processamento_com(ProcessamentoRepositorySql(sessoes), NF_ANA)
        cliente = ClienteDecidido("BRUNO LIMA", "Bruno Lima", False, cliente_id=None)  # tudo ignorado
        importacao = ImportacaoRepository(sessoes).importar(PlanoDecidido(processamento_id, [cliente], ignorados=1))
        assert importacao.clientes_criados == 0
        assert ClienteRepository(sessoes).listar() == []


class TestDocumentoRepository:
    def test_edicao_manual_grava_historico_e_marca_o_campo(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        repositorio = DocumentoRepository(sessoes)

        documento = repositorio.atualizar(1, {"data_emissao": date(2024, 1, 2)}, OrigemAlteracao.EDICAO_MANUAL)

        assert documento.dados.data_emissao == date(2024, 1, 2)
        assert documento.campos_editados == ["data_emissao"]
        ultima = repositorio.historico(1)[-1]
        assert (ultima.campo, ultima.valor_anterior, ultima.valor_novo) == ("data_emissao", "2023-03-08", "2024-01-02")

    def test_valor_igual_nao_gera_historico(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        repositorio = DocumentoRepository(sessoes)
        repositorio.atualizar(1, {"data_emissao": date(2023, 3, 8)}, OrigemAlteracao.EDICAO_MANUAL)
        assert len(repositorio.historico(1)) == 1  # só a importação

    def test_mover_documento_para_outro_cliente(self, sessoes):
        _importar_ana(sessoes, NF_ANA)
        outro = ClienteRepository(sessoes).criar("Bruno Lima", "BRUNO LIMA", False)
        repositorio = DocumentoRepository(sessoes)

        documento = repositorio.atualizar(1, {"cliente_id": outro.id}, OrigemAlteracao.EDICAO_MANUAL)

        assert documento.cliente_id == outro.id
        ultima = repositorio.historico(1)[-1]
        assert (ultima.campo, ultima.valor_anterior, ultima.valor_novo, ultima.origem) == (
            "cliente",
            "Ana Souza",
            "Bruno Lima",
            OrigemAlteracao.REMANEJAMENTO,
        )

    def test_filtros(self, sessoes):
        _importar_ana(sessoes, NF_ANA, PLANILHA_ANA)
        repositorio = DocumentoRepository(sessoes)
        assert [d.tipo for d in repositorio.listar(tipo=TipoDocumento.NOTA_FISCAL)] == [TipoDocumento.NOTA_FISCAL]
        assert repositorio.listar(sem_cliente=True) == []


class TestClienteRepository:
    def test_unir_move_documentos_e_transforma_a_chave_em_apelido(self, sessoes):
        _importar_ana(sessoes, NF_ANA, chave="ANA SOUZA")
        _importar_ana(sessoes, PLANILHA_ANA, chave="ANA SOUSA")  # grafia diferente no documento
        clientes = ClienteRepository(sessoes)
        destino, origem = clientes.listar()[0], clientes.listar()[1]  # ordenados por nome (iguais): ids 1 e 2
        assert (destino.id, origem.id) == (1, 2)

        unido = clientes.unir(destino.id, origem.id)

        assert len(unido.documentos) == 2
        assert clientes.obter(origem.id) is None
        assert clientes.id_pela_chave("ANA SOUSA") == destino.id  # apelido
        assert DocumentoRepository(sessoes).historico(2)[-1].origem is OrigemAlteracao.UNIAO_DE_CLIENTES

        # Um documento NOVO com a grafia antiga já vai para o cliente certo.
        importacao = _importar_ana(sessoes, PRESTACAO_ANA, chave="ANA SOUSA")
        assert importacao.clientes_criados == 0
        assert len(clientes.obter(destino.id).documentos) == 3

    def test_renomear_mantem_a_chave_antiga_como_apelido(self, sessoes):
        clientes = ClienteRepository(sessoes)
        cliente = clientes.criar("Ana Sousa", "ANA SOUSA", False)
        atualizado = clientes.atualizar(cliente.id, "Ana Souza", "ANA SOUZA", True)
        assert (atualizado.chave, atualizado.espolio) == ("ANA SOUZA", True)
        assert clientes.id_pela_chave("ANA SOUSA") == cliente.id
