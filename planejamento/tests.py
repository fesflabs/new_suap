# -*- coding: utf-8 -*-

from djtools.choices import Situacao
from comum.models import Ano
from comum.tests import SuapTestCase
from django.contrib.auth.models import Group
from financeiro.models import (
    Programa,
    Acao as AcaoFinanceiro,
    FonteRecurso,
    GrupoFonteRecurso,
    EspecificacaoFonteRecurso,
    NaturezaDespesa,
    CategoriaEconomicaDespesa,
    GrupoNaturezaDespesa,
    ModalidadeAplicacao,
    ElementoDespesa,
)
from planejamento.enums import TipoUnidade
from planejamento.models import (
    Configuracao,
    Dimensao,
    ObjetivoEstrategico,
    AcaoProposta,
    Atividade,
    UnidadeMedida,
    MetaUnidade,
    Acao,
    UnidadeAdministrativa,
    MetaUnidadeAcaoProposta,
    NaturezaDespesa as Natureza,
    OrigemRecurso,
    OrigemRecursoUA,
    AcaoExecucao,
    AcaoValidacao,
    Meta,
)
from rh.models import Servidor


class PlanejamentoTestCase(SuapTestCase):
    def setUp(self):

        super(PlanejamentoTestCase, self).setUp()

        self.servidor_a.user.groups.add(Group.objects.get(name='Administrador de Planejamento'))
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Planejamento Sistêmico'))
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Planejamento'))
        self.client.login(username=self.servidor_a.user.username, password='123')

        self.servidor_a3 = Servidor.objects.create(
            nome='Servidor A3',
            matricula='3000',
            setor=self.setor_a2_suap,
            template=b'30',
            cargo_emprego=self.cargo_emprego_b,
            situacao=self.situacao_ativo_permanente,
            cpf='017.769.177-82',
        )

    def test_cadastrar_configuracao(self):
        """
        Testa o cadastro da configuracao do planejamento anual
        """
        qtd_conf_antes = Configuracao.objects.count()
        # Verificando que não há ainda configuracoes cadastradas
        self.assertEqual(qtd_conf_antes, 0)
        # Criando um ano
        self.ano = Ano.objects.create(ano='2012')
        # Testando acesso a página
        response = self.client.get('/admin/planejamento/configuracao/add/')
        self.assertEqual(response.status_code, 200)
        # Cadastrando a configuracao com dados válidos
        self.client.post(
            '/admin/planejamento/configuracao/add/',
            dict(
                ano_base=self.ano.pk,
                data_geral_inicial='01/01/2012',
                data_geral_final='01/12/2012',
                data_metas_inicial='01/06/2011',
                data_metas_final='01/07/2011',
                data_acoes_inicial='02/07/2011',
                data_acoes_final='02/08/2011',
                data_validacao_inicial='02/10/2011',
                data_validacao_final='02/12/2011',
                data_planilhas_inicial='01/12/2011',
                data_planilhas_final='20/12/2011',
            ),
        )
        # Verificando se 1 item foi cadastrado para a configuracao
        self.assertEqual(Configuracao.objects.count(), qtd_conf_antes + 1)

    def test_cadastrar_unidade_administrativa(self):
        """
        Testa o cadastro da unidade administrativa
        """

        self.test_cadastrar_configuracao()

        qtd_unidade_antes = UnidadeAdministrativa.objects.count()
        # Verificando que não há ainda unidades administrativas cadastradas para o cadastro
        self.assertEqual(qtd_unidade_antes, 0)

        # Testando acesso a página
        response = self.client.get('/admin/planejamento/unidadeadministrativa/add/')
        self.assertEqual(response.status_code, 200)

        # Cadastrando a unidade administrativa com dados válidos
        response = self.client.post(
            '/admin/planejamento/unidadeadministrativa/add/',
            dict(
                configuracao=Configuracao.objects.all()[0].pk,
                tipo=TipoUnidade.CAMPUS,
                codigo_simec='123456',
                codigo_simec_digito='3',
                setor_equivalente=self.setor_a1_suap.pk,
                orcamento='100',
            ),
        )
        # Verificando se 1 item foi cadastrado para a unidade Administrativa

        self.assertEqual(UnidadeAdministrativa.objects.count(), qtd_unidade_antes + 1)

    def test_cadastrar_dimensao(self):
        """
        Testar o cadastro de dimensões
        """
        qtd_dimensao_antes = Dimensao.objects.count()
        # Verificando que não há ainda dimensoes cadastradas
        self.assertEqual(qtd_dimensao_antes, 0)
        # Testando acesso a  página que efetua o cadastro da dimensao
        response = self.client.get('/admin/planejamento/dimensao/add/')
        self.assertEqual(response.status_code, 200)
        # Cadastrando a dimensao com dados válidos
        response = self.client.post('/admin/planejamento/dimensao/add/', dict(descricao='Dimensao 01', sigla='SIGLA 01', setor_sistemico=self.setor_a1_suap.pk, codigo='01'))

        # Verificando se 1 item foi cadastrado para o empenho
        self.assertEqual(Dimensao.objects.count(), qtd_dimensao_antes + 1)

    def test_cadastrar_objetivo_estrategico(self):
        """
        Testar o cadastro do Objetivo Estratégico
        """

        self.test_cadastrar_configuracao()

        self.test_cadastrar_dimensao()

        # Obtendo a quantidade atual de obj. estrategicos cadastrados
        qtd_obj_antes = ObjetivoEstrategico.objects.count()
        # Verificando que não há ainda obj. estrategicos cadastrados
        self.assertEqual(qtd_obj_antes, 0)
        # Testando acesso a  página que efetua o cadastro
        response = self.client.get('/admin/planejamento/objetivoestrategico/add/')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            '/admin/planejamento/objetivoestrategico/add/',
            dict(
                data_cadastro='11/06/2011',
                macro_projeto_institucional='macro projeto institucional 01',
                descricao='objetivo 01',
                configuracao=Configuracao.objects.all()[0].pk,
                dimensao=Dimensao.objects.all()[0].pk,
                codigo='01',
            ),
        )
        # Verificando se 1 item foi cadastrado para Objetivo estrategico
        self.assertEqual(ObjetivoEstrategico.objects.count(), qtd_obj_antes + 1)

    def test_cadastrar_meta(self):
        """
        Testar o cadastro de metas 
        """
        self.test_cadastrar_objetivo_estrategico()
        # Obtendo a quantidade atual de metas
        qtd_metas_antes = Meta.objects.count()
        # Verificando que não há ainda metas cadastradas
        self.assertEqual(qtd_metas_antes, 0)
        objetivo = ObjetivoEstrategico.objects.all()[0].pk
        # Criando uma unidade medida
        self.unidade = UnidadeMedida.objects.create(nome='Acesso')
        # Testando acesso a página que efetua o cadastro
        response = self.client.get('/admin/planejamento/meta/add/?objetivo=estrategico=%s' % objetivo)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            '/admin/planejamento/meta/add/?objetivo=estrategico=%s' % objetivo,
            dict(
                data_cadastro='11/07/2011',
                data_cadastro_inicio='10:00:00',
                objetivo_estrategico=ObjetivoEstrategico.objects.all()[0].pk,
                titulo='Meta 01',
                justificativa='Meta criada para teste',
                unidade_medida=self.unidade.pk,
                data_inicial='01/01/2012',
                data_final='01/12/2012',
                codigo='01',
            ),
        )
        # Verificando se 1 item foi cadastrado para meta
        self.assertEqual(Meta.objects.count(), qtd_metas_antes + 1)

    def test_cadastrar_acao_proposta(self):
        """
        Testa o cadastro de acao proposta
        """
        self.test_cadastrar_meta()
        # Obtendo a quantidade atual de acao propostas
        qtd_acao_proposta_antes = AcaoProposta.objects.count()
        # Verificando que nao há ainda acao proposta cadastradas
        self.assertEqual(qtd_acao_proposta_antes, 0)
        meta = Meta.objects.all()[0].pk
        # Criando Programa
        self.programa = Programa.objects.create(codigo='1', nome='Programa 01')
        # Criando Acao
        self.acao = AcaoFinanceiro.objects.create(codigo_acao='1', nome='Fonte 1', programa=self.programa, codigo='01')

        # Criando Grupo Fonte Recurso
        self.grupo = GrupoFonteRecurso.objects.create(id='1', codigo='1', nome='grupo recurso')

        # Criando Especificacao Fonte Recurso
        self.especificacao = EspecificacaoFonteRecurso.objects.create(codigo='01', nome='especificacao 1')

        # Criando Fonte Recurso
        self.fonte = FonteRecurso.objects.create(codigo='2', nome='fonte 01', grupo=self.grupo, especificacao=self.especificacao)

        # Criando uma unidade medida
        self.unidade = UnidadeMedida.objects.create(nome='Acao')

        # Testando acesso à página que efetua o cadastro
        response = self.client.get('/admin/planejamento/acaoproposta/add/?meta=%s' % meta)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            '/admin/planejamento/acaoproposta/add/?meta=%s' % meta,
            {
                'metaunidadeacaoproposta_set-__prefix__-id': '',
                'metaunidadeacaoproposta_set-0-meta_unidade': '',
                'metaunidadeacaoproposta_set-__prefix__-acao_proposta': '',
                'metaunidadeacaoproposta_set-0-quantidade': '',
                'metaunidadeacaoproposta_set-__prefix__-meta_unidade': '',
                'metaunidadeacaoproposta_set-MAX_NUM_FORMS': '',
                'metaunidadeacaoproposta_set-0-acao_proposta': '',
                'metaunidadeacaoproposta_set-__prefix__-quantidade': '',
                'metaunidadeacaoproposta_set-0-valor_unitario': '',
                'metaunidadeacaoproposta_set-TOTAL_FORMS': '0',
                'metaunidadeacaoproposta_set-__prefix__-valor_unitario': '',
                'metaunidadeacaoproposta_set-0-id': '',
                'metaunidadeacaoproposta_set-INITIAL_FORMS': '0',
                'data_inicial': '12/06/2011',
                'data_final': '12/08/2011',
                'meta': Meta.objects.all()[0].pk,
                'titulo': 'Acao Proposta 01',
                'codigo': '2',
                'acao_orcamento': self.acao.pk,
                'fonte_financiamento': self.fonte.pk,
                'unidade_medida': self.unidade.pk,
            },
        )

        # Verificando se 1 item foi cadastrado para acao proposta
        self.assertEqual(AcaoProposta.objects.count(), qtd_acao_proposta_antes + 1)

    def test_importar_acao_proposta(self):
        """
        Testar a importacao da Acao Proposta
        """
        self.test_cadastrar_acao_proposta()

        qtd_acao_antes = Acao.objects.count()
        # Verificando que nao há ainda acao proposta cadastrados
        self.assertEqual(qtd_acao_antes, 0)

        # Unidade Administrativa
        self.unidadeadministrativa = UnidadeAdministrativa.objects.create(
            configuracao=Configuracao.objects.all()[0],
            codigo_simec='123456',
            codigo_simec_digito='5',
            setor_equivalente=self.setor_a1_suap,
            tipo=TipoUnidade.CAMPUS,
            orcamento='20',
        )

        # Criando Meta Unidade
        MetaUnidade.objects.create(meta=Meta.objects.all()[0], unidade=self.unidadeadministrativa, quantidade='10', valor_total='1000')
        metaproposta = MetaUnidadeAcaoProposta.objects.create(
            meta_unidade=MetaUnidade.objects.all()[0], acao_proposta=AcaoProposta.objects.all()[0], quantidade='10', valor_unitario='10'
        )
        meta_proposta = metaproposta.pk
        response = self.client.get('/admin/planejamento/acao/add/?metaunidade_acoespropostas/%s/' % (meta_proposta))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            '/admin/planejamento/acao/add/?metaunidade_acoespropostas/%s/' % (meta_proposta),
            dict(
                data_cadastro='12/06/2011',
                data_cadastro_inicio='10:00:00',
                meta_unidade=MetaUnidade.objects.all()[0].pk,
                titulo='Acao 01',
                detalhamento='acao teste',
                unidade_medida=self.unidade.pk,
                quantidade='5',
                setor_responsavel=self.setor_a1_suap.pk,
                acao_orcamento=self.acao.pk,
                fonte_financiamento=self.fonte.pk,
                codigo='2',
                data_inicial='01/01/2012',
                data_final='01/12/2012',
                acao_indutora='',
                status=Situacao.DEFERIDA,
            ),
        )

        self.assertEqual(Acao.objects.count(), qtd_acao_antes + 1)

    def test_cadastrar_acao(self):
        """
        Testa o cadastro de acao
        """

        self.test_cadastrar_meta()

        # Obtendo a quantidade atual de acao
        qtd_acao_antes = Acao.objects.count()
        # Verificando que não há ainda acao cadastradas
        self.assertEqual(qtd_acao_antes, 0)
        # Criando Programa
        self.programa = Programa.objects.create(codigo='2', nome='Programa 02')
        # Criando Acao
        self.acao = AcaoFinanceiro.objects.create(codigo_acao='2', nome='Fonte 2', programa=self.programa, codigo='02')

        # Criando Grupo Fonte Recurso
        self.grupo = GrupoFonteRecurso.objects.create(id='2', codigo='2', nome='grupo recurso 2')

        # Criando Especificacao Fonte Recurso
        self.especificacao = EspecificacaoFonteRecurso.objects.create(codigo='02', nome='especificacao 2')

        # Criando Fonte Recurso
        self.fonte = FonteRecurso.objects.create(codigo='3', nome='fonte 02', grupo=self.grupo, especificacao=self.especificacao)

        # Unidade Administrativa
        self.unidadeadministrativa = UnidadeAdministrativa.objects.create(
            configuracao=Configuracao.objects.all()[0], codigo_simec='12345', codigo_simec_digito='1', setor_equivalente=self.setor_a1_suap, tipo=TipoUnidade.CAMPUS, orcamento='90'
        )

        # Criando uma unidade medida
        self.unidade = UnidadeMedida.objects.create(nome='Bolsa')
        # MetaUnidade
        self.metaunidade = MetaUnidade.objects.create(meta=Meta.objects.all()[0], unidade=self.unidadeadministrativa, quantidade='10', valor_total='1000')

        metaunid = MetaUnidade.objects.all()[0].pk
        # Testando acesso a página que efetua o cadastro
        response = self.client.get('/admin/planejamento/acao/add/?meta_unidade=%s' % metaunid)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            '/admin/planejamento/acao/add/?meta_unidade=%s' % metaunid,
            dict(
                data_cadastro='12/06/2011',
                data_cadastro_inicio='10:00:00',
                meta_unidade=MetaUnidade.objects.all()[0].pk,
                titulo='Acao 01',
                detalhamento='acao teste',
                unidade_medida=self.unidade.pk,
                quantidade='5',
                setor_responsavel=self.setor_a1_suap.pk,
                acao_orcamento=self.acao.pk,
                fonte_financiamento=self.fonte.pk,
                codigo='',
                data_inicial='01/01/2012',
                data_final='01/12/2012',
                acao_indutora='',
                status=Situacao.PENDENTE,
            ),
        )

        self.assertEqual(Acao.objects.count(), qtd_acao_antes + 1)

    def test_cadastrar_atividade(self):
        """
        Testa o cadastro de atividade
        """

        self.test_cadastrar_acao()
        # Obtendo a quantidade atual de atividade
        qtd_atividade_antes = Atividade.objects.count()
        # Verificando que não há ainda acao cadastradas
        self.assertEqual(qtd_atividade_antes, 0)
        acao = Acao.objects.all()[0].pk

        # Criando uma unidade medida
        self.unidade = UnidadeMedida.objects.create(nome='Atendimento')
        # Criando Categoria Economica de Despesa
        self.cateconomica = CategoriaEconomicaDespesa.objects.create(codigo='1', nome='categoria 01', descricao='primeira categoria')

        # Criando Grupo Natureza Despesa
        self.gruponatdespesa = GrupoNaturezaDespesa.objects.create(codigo='1', nome='grupo 01', descricao='')

        # Criando Modalidade Aplicacao
        self.modalidade = ModalidadeAplicacao.objects.create(codigo='1', nome='modalidade 01', descricao='')

        # Criando Elemento Despesa
        self.elementodespesa = ElementoDespesa.objects.create(codigo='1', nome='elemento despesa 10', descricao='')

        # Criando Natureza Despesa
        self.naturezadespesa = NaturezaDespesa.objects.create(
            categoria_economica_despesa=self.cateconomica,
            grupo_natureza_despesa=self.gruponatdespesa,
            modalidade_aplicacao=self.modalidade,
            elemento_despesa=self.elementodespesa,
            nome='Atividade para teste',
            codigo='',
            tipo='Capital',
        )

        # Criando Tipo Recurso
        self.tiporecurso = OrigemRecurso.objects.create(
            configuracao=Configuracao.objects.all()[0], nome='recurso para teste', valor_capital='10000.00', valor_custeio='10000.00', visivel_campus=True
        )

        # criando Unidade Administrativa
        self.unidadeadministrativa = UnidadeAdministrativa.objects.create(
            configuracao=Configuracao.objects.all()[0], codigo_simec='54321', codigo_simec_digito='1', setor_equivalente=self.setor_a1_suap, tipo=TipoUnidade.CAMPUS, orcamento='90'
        )

        # criando Origem Recurso UA
        self.origemrecursoua = OrigemRecursoUA.objects.create(
            origem_recurso=OrigemRecurso.objects.all()[0], unidade=self.unidadeadministrativa, valor_capital='5000.00', valor_custeio='5000.00'
        )

        self.natureza = Natureza.objects.create(naturezadespesa=NaturezaDespesa.objects.all()[0])

        # Testando acesso a pagina que efetua o cadastro
        response = self.client.get('/admin/planejamento/atividade/add/?acao=%s' % acao)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            '/admin/planejamento/atividade/add/?acao=%s' % acao,
            dict(
                acao=Acao.objects.all()[0].pk,
                descricao='Atividade',
                detalhamento='detalhamento sobre a atividade',
                unidade_medida=self.unidade.pk,
                quantidade='3',
                valor_unitario='10.00',
                elemento_despesa=self.natureza.pk,
                tipo_recurso=self.tiporecurso.pk,
            ),
        )

        self.assertEqual(Atividade.objects.count(), qtd_atividade_antes + 1)

    def test_registrar_execucao(self):
        """
        Testar o registro de execucao
        """
        self.test_cadastrar_acao()

        acao = Acao.objects.all()[0].pk

        # Testando acesso a pagina que efetua o cadastro
        response = self.client.get('/planejamento/acompanhamento/acao/%s/#fcad' % acao)
        self.assertEqual(response.status_code, 200)

        response = self.client.post('/planejamento/acompanhamento/acao/%s/#fcad' % acao, dict(acao=Acao.objects.all()[0].pk, texto='Acao concluida', percentual='100'))
        self.assertEqual(AcaoExecucao.objects.count(), 1)

    def test_validacao_acao(self):
        """
        Testa a validacao da acao
        """
        self.test_cadastrar_acao()
        qtd_acaovalidacao_antes = AcaoValidacao.objects.count()
        self.assertEqual(qtd_acaovalidacao_antes, 0)
        metaunidade = MetaUnidade.objects.all()[0].pk
        acao = Acao.objects.filter(meta_unidade=metaunidade)[0].pk
        # Testando acesso a pagina que efetua o cadastro
        response = self.client.get('/')
        response = self.client.get('/planejamento/acao/%s/validar/%s/' % (metaunidade, acao))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            '/planejamento/acao/%s/validar/%s/' % (metaunidade, acao),
            {'acao': acao, 'comentario_acao': 'Acao própria para o planejamento', 'status_acao': Situacao.DEFERIDA},
            follow=True,
        )
        self.assertContains(response, 'Ação validada com sucesso', status_code=200)
