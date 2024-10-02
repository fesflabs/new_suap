from rh.models import PessoaFisica, Servidor
from datetime import date
from datetime import timedelta, datetime

from django.apps.registry import apps
from django.contrib.auth.models import Group

from comum.models import Ano
from comum.tests import SuapTestCase
from djtools.utils import prevent_logging_errors
from comum.utils import get_uo
from djtools.templatetags.filters import in_group
from edu.models import Aluno, SituacaoMatricula
from financeiro.models import CategoriaEconomicaDespesa, ElementoDespesa, GrupoNaturezaDespesa, ModalidadeAplicacao, NaturezaDespesa
from projetos.models import (
    AreaConhecimento,
    Desembolso,
    Edital,
    EditalAnexo,
    EditalAnexoAuxiliar,
    Etapa,
    FocoTecnologico,
    ItemMemoriaCalculo,
    Meta,
    OfertaProjeto,
    Participacao,
    Projeto,
    Recurso,
    CriterioAvaliacao,
    AreaTematica,
    Tema,
    RegistroConclusaoProjeto,
    RegistroExecucaoEtapa,
    RegistroGasto,
    CaracterizacaoBeneficiario,
    TipoBeneficiario,
    TipoVinculo,
    FotoProjeto,
    ProjetoAnexo,
    OrigemRecursoEdital,
    AvaliadorIndicado,
)

ParticipacaoBolsa = apps.get_model('ae', 'participacaobolsa')
CategoriaBolsa = apps.get_model('ae', 'categoriabolsa')
Permission = apps.get_model('auth', 'permission')
User = apps.get_model('comum', 'user')

GRUPO_EXTENSAO_AVALIADOR = 'Avaliador de Projetos de Extensão'
GRUPO_EXTENSAO_PRE_AVALIADOR = 'Coordenador de Extensão'
GRUPO_EXTENSAO_GERENTE_SISTEMICO = 'Gerente Sistêmico de Extensão'
GRUPO_COORDENADOR_PROJETO = 'Servidor'


class ProjetosTestCase(SuapTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.carga_inicial()

    @classmethod
    def carga_inicial(cls):
        categoriaeconomicadespesa = CategoriaEconomicaDespesa.objects.get_or_create(codigo='3', nome='Despesas Correntes')[0]
        gruponaturezadespesa = GrupoNaturezaDespesa.objects.get_or_create(codigo='3', nome='Outras Despesas Correntes')[0]
        modalidadeaplicacao = ModalidadeAplicacao.objects.get_or_create(codigo='90', nome='Aplicações Diretas')[0]
        elementodespesa1 = ElementoDespesa.objects.get_or_create(codigo='30', nome='Material de Consumo')[0]
        elementodespesa2 = ElementoDespesa.objects.get_or_create(codigo='18', nome='Auxílio Financeiro a Estudantes')[0]
        elementodespesa3 = ElementoDespesa.objects.get_or_create(codigo='20', nome='Auxílio Financeiro a Pesquisadores')[0]

        NaturezaDespesa.objects.get_or_create(
            categoria_economica_despesa=categoriaeconomicadespesa,
            grupo_natureza_despesa=gruponaturezadespesa,
            modalidade_aplicacao=modalidadeaplicacao,
            elemento_despesa=elementodespesa1,
            codigo='339030',
        )

        NaturezaDespesa.objects.get_or_create(
            categoria_economica_despesa=categoriaeconomicadespesa,
            grupo_natureza_despesa=gruponaturezadespesa,
            modalidade_aplicacao=modalidadeaplicacao,
            elemento_despesa=elementodespesa2,
            codigo='339018',
        )

        NaturezaDespesa.objects.get_or_create(
            categoria_economica_despesa=categoriaeconomicadespesa,
            grupo_natureza_despesa=gruponaturezadespesa,
            modalidade_aplicacao=modalidadeaplicacao,
            elemento_despesa=elementodespesa3,
            codigo='339020',
        )
        OrigemRecursoEdital.objects.get_or_create(descricao='PROEX')

        if CategoriaBolsa:
            CategoriaBolsa.objects.get_or_create(nome='Bolsa de Extensão', descricao='Bolsa de Extensão', tipo_bolsa='extensão')
            CategoriaBolsa.objects.get_or_create(nome='Bolsa de iniciação científica', descricao='Bolsa de iniciação científica', tipo_bolsa='iniciação científica')

        TipoBeneficiario.objects.get_or_create(descricao='Movimentos Sociais')

        Tema.objects.get_or_create(descricao='Tecnologia da Informação  e Comunicação')

        ano, created = Ano.objects.get_or_create(ano=str(datetime.now().year))
        situacao = SituacaoMatricula.objects.get_or_create(descricao='Matriculado', ativo=True)[0]

        pessoafisica = PessoaFisica.objects.get_or_create(nome='Carlos Breno Pereira Silva', defaults={'cpf': '359.221.769-00'})[0]
        aluno = Aluno.objects.get_or_create(
            matricula='1', pessoa_fisica=pessoafisica, ano_letivo=ano, periodo_letivo=1, situacao=situacao, ano_let_prev_conclusao=datetime.now().year
        )[0]
        aluno.pessoa_fisica.eh_aluno = True
        aluno.pessoa_fisica.save()

        pessoafisica = PessoaFisica.objects.get_or_create(nome='Jailton Carlos de Paiva', defaults={'cpf': '826.526.814-94'})[0]

        aluno = Aluno.objects.get_or_create(
            matricula='2', pessoa_fisica=pessoafisica, ano_letivo=ano, periodo_letivo=1, situacao=situacao, ano_let_prev_conclusao=datetime.now().year
        )[0]

        aluno.pessoa_fisica.eh_aluno = True
        aluno.pessoa_fisica.save()

    def setUp(self):
        super().setUp()
        self.define_usuarios_e_permissoes()
        # self.servidor_a2 = Servidor.objects.get(nome = u'Servidor A2')
        # self.servidor_a3 = Servidor.objects.get(nome = u'Servidor A3')
        # self.servidor_e = Servidor.objects.get(nome = u'Servidor E')

    def define_usuarios_e_permissoes(self):
        # self.servidor_a pertence ao grupo servidor, é o coordenador do projeto

        self.servidor_b.user.groups.add(Group.objects.get(name=GRUPO_EXTENSAO_GERENTE_SISTEMICO))
        self.servidor_b.user.save()
        self.client.login(username=self.servidor_a.user.username, password='123')

        # usuário pré-avaliador pertecente ao mesmo campus do projeto
        self.servidor_a2 = Servidor.objects.create(
            nome='Servidor A2',
            matricula='12',
            cargo_emprego=SuapTestCase.dict_initial_data['cargo_emprego_b'],
            setor=SuapTestCase.dict_initial_data['setor_a1_suap'],
            template=b'12',
            situacao=SuapTestCase.dict_initial_data['situacao_ativo_permanente'],
            email='servidor.a2@mail.gov',
            jornada_trabalho=SuapTestCase.dict_initial_data['jornada_trabalho'],
            cpf='449.717.558-88',
        )
        self.servidor_a2.user.set_password('123')
        self.servidor_a2.user.groups.add(Group.objects.get(name='Coordenador de Extensão'))
        self.servidor_a2.user.save()

        # usuário avaliador pertecente ao mesmo campus do projeto
        self.servidor_a3 = Servidor.objects.create(
            nome='Servidor A3',
            matricula='13',
            cargo_emprego=SuapTestCase.dict_initial_data['cargo_emprego_b'],
            setor=SuapTestCase.dict_initial_data['setor_a1_suap'],
            template=b'13',
            situacao=SuapTestCase.dict_initial_data['situacao_ativo_permanente'],
            email='servidor.a3@mail.gov',
            jornada_trabalho=SuapTestCase.dict_initial_data['jornada_trabalho'],
            cpf='313.444.320-18',
        )
        self.servidor_a3.user.set_password('123')
        self.servidor_a3.user.groups.add(Group.objects.get(name=GRUPO_EXTENSAO_AVALIADOR))
        self.servidor_a3.user.save()

        # usuário pré-avaliador de campus diferente aquele da submissão do projeto
        self.servidor_c.user.groups.add(Group.objects.get(name=GRUPO_EXTENSAO_AVALIADOR))
        self.servidor_c.user.save()

        # usuário avaliador de campus diferente aquele da submissão do projeto
        self.servidor_d.user.groups.add(Group.objects.get(name=GRUPO_EXTENSAO_AVALIADOR))
        self.servidor_d.user.save()

        # usuário Servidor de outro campus
        self.servidor_e = Servidor.objects.create(
            nome='Servidor E',
            matricula='5',
            setor=SuapTestCase.dict_initial_data['setor_b1_suap'],
            template=b'5',
            cargo_emprego=SuapTestCase.dict_initial_data['cargo_emprego_b'],
            situacao=SuapTestCase.dict_initial_data['situacao_ativo_permanente'],
            email='servidor.5@mail.gov',
            jornada_trabalho=SuapTestCase.dict_initial_data['jornada_trabalho'],
            cpf='854.545.233-05',
        )
        self.servidor_e.user.set_password('123')
        self.servidor_e.user.groups.add(Group.objects.get(name='Servidor'))
        self.servidor_e.user.save()

    def retornar(self, cls, qtd=1, chaves={}):
        if chaves:
            return cls.objects.get(**chaves)
        if qtd == 1:
            return cls.objects.latest('id')
        else:
            return cls.objects.all().order_by('-id')[0:qtd]

    def cadastrar(self, cls, data):
        qs = cls.objects.filter(descricao=data['descricao'])
        if qs:
            return qs[0]
        name = cls.__name__.lower()
        url = '/admin/projetos/%s/' % (name)
        self.client.get(url)
        url = '/admin/projetos/%s/add/' % (name)
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar %s' % cls._meta.verbose_name, status_code=200)
        count = cls.objects.all().count()
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(cls.objects.all().count(), count + 1)
        return self.retornar(cls)

    def cadastro_foco_tecnologico(self):
        self.acessar_como_gerente_sistemico()
        data = dict(descricao='Informática e Equipamentos biomédicos', ativo='on', campi=self.servidor_a.pessoafisica.funcionario.setor.uo.pk)
        self.cadastrar(FocoTecnologico, data)
        data = dict(descricao='Informática e Serviços', ativo='on', campi=self.servidor_b.pessoafisica.funcionario.setor.uo.pk)
        self.cadastrar(FocoTecnologico, data)
        uos = [self.servidor_a.pessoafisica.funcionario.setor.uo.pk, self.servidor_b.pessoafisica.funcionario.setor.uo.pk]
        data = dict(descricao='Multidisciplinar', ativo='on', campi=uos)
        foco = self.cadastrar(FocoTecnologico, data)
        self.assertListEqual(uos, list(foco.campi.all().values_list('id', flat=True)))

    def cadastro_edital(self, **params):
        url = '/admin/projetos/edital/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Edital', status_code=200)
        count = Edital.objects.all().count()
        input = dict(
            titulo='Edital 001',
            descricao='Descrição do edital',
            inicio_inscricoes='01/01/2012',
            inicio_inscricoes_time='00:00:00',
            fim_inscricoes='01/02/2012',
            fim_inscricoes_time='23:59:00',
            participa_aluno='1',
            participa_servidor='1',
            inicio_pre_selecao='01/04/2012',
            inicio_pre_selecao_time='00:00:00',
            inicio_selecao='01/05/2012',
            inicio_selecao_time='00:00:00',
            fim_selecao='01/06/2012',
            fim_selecao_time='00:00:00',
            divulgacao_selecao='01/07/2012',
            divulgacao_selecao_time='00:00:00',
            tipo_edital=Edital.EXTENSAO,
            qtd_maxima_alunos=5,
            qtd_maxima_servidores=5,
            qtd_maxima_alunos_bolsistas=3,
            qtd_maxima_servidores_bolsistas=3,
            peso_avaliacao_lattes_coordenador=1,
            peso_avaliacao_projeto=1,
            exige_licoes_aprendidas=False,
            forma_selecao=Edital.CAMPUS,
            qtd_projetos_selecionados=1,
            valor_financiado_por_projeto=0.00,
            tipo_fomento=Edital.FOMENTO_INTERNO,
            exige_anuencia=Edital.SEM_ANUENCIA,
        )
        input.update(params)

        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/projetos/edital/%d/' % Edital.objects.latest("id").pk, status_code=302)
        self.assertEqual(Edital.objects.all().count(), count + 1)
        return self.retornar(Edital)

    def _test_cadastro_edital_continuo(self):
        url = '/admin/projetos/edital/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Edital', status_code=200)
        count = Edital.objects.all().count()
        input = dict(
            titulo='Edital 002',
            descricao='Descrição do edital especial',
            inicio_inscricoes='01/01/' + str(datetime.now().year),
            inicio_inscricoes_time='08:00:00',
            fim_inscricoes='31/12/' + str(datetime.now().year),
            fim_inscricoes_time='00:00:00',
            participa_aluno='1',
            participa_servidor='1',
            inicio_pre_selecao='01/01/' + str(datetime.now().year),
            inicio_pre_selecao_time='08:00:00',
            inicio_selecao='01/01/' + str(datetime.now().year),
            inicio_selecao_time='08:00:00',
            divulgacao_selecao='01/01/' + str(datetime.now().year),
            divulgacao_selecao_time='08:00:00',
            tipo_edital=Edital.EXTENSAO_FLUXO_CONTINUO,
        )
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/projetos/edital/%d/' % Edital.objects.latest("id").pk, status_code=302)
        self.assertEqual(Edital.objects.all().count(), count + 1)

    def _test_cadastro_edital_especial(self):
        url = '/admin/projetos/edital/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Edital', status_code=200)
        count = Edital.objects.all().count()
        input = dict(
            titulo='Edital 001',
            descricao='Descrição do edital',
            inicio_inscricoes='01/01/2012',
            inicio_inscricoes_time='08:00:00',
            fim_inscricoes='01/02/2012',
            fim_inscricoes_time='08:00:00',
            participa_aluno='1',
            participa_servidor='1',
            inicio_pre_selecao='01/04/2012',
            inicio_pre_selecao_time='08:00:00',
            inicio_selecao='01/05/2012',
            inicio_selecao_time='08:00:00',
            divulgacao_selecao='01/06/2012',
            divulgacao_selecao_time='08:00:00',
            tipo_edital=Edital.PESQUISA,
        )
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/projetos/edital/%d/' % Edital.objects.all()[0].pk, status_code=302)
        self.assertEqual(Edital.objects.all().count(), count + 1)

    def cadastro_editalanexoauxiliar(self, edital=None):
        if not edital:
            self.cadastro_edital()
            edital = Edital.objects.all()[0]

        url = '/projetos/adicionar_anexo_auxiliar/%d/' % edital.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Anexo', status_code=200)
        count = EditalAnexoAuxiliar.objects.all().count()
        input = dict(nome='Anexo I', descricao='Termo de compromisso do bolsista docente', ordem=1)
        response = self.client.post(url, input)
        self.assertEqual(EditalAnexoAuxiliar.objects.all().count(), count + 1)
        return self.retornar(EditalAnexoAuxiliar)

    def cadastro_editalanexo(self, edital=None):
        if not edital:
            self.cadastro_edital()
            edital = Edital.objects.all()[0]

        url = '/projetos/adicionar_anexo/%s/' % edital.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Anexo', status_code=200)
        count = EditalAnexo.objects.all().count()
        input = dict(nome='Anexo I', descricao='Termo de compromisso do bolsista docente', edital=edital, tipo_membro=EditalAnexo.ALUNO, vinculo=TipoVinculo.VOLUNTARIO, ordem=1)
        response = self.client.post(url, input)
        self.assertEqual(EditalAnexo.objects.all().count(), count + 1)
        return self.retornar(EditalAnexo)

    def cadastro_ofertaprojeto(self, edital=None, **params):
        if not edital:
            self.cadastro_edital()
            edital = Edital.objects.filter(tipo_edital='Extensão')[0]
        unidadeorganizacional = self.campus_a_suap
        url = '/projetos/adicionar_oferta_projeto/%d/' % edital.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Oferta', status_code=200)
        count = OfertaProjeto.objects.all().count()
        input = dict(uo=unidadeorganizacional.pk, qtd_aprovados='10', qtd_selecionados='5')
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(OfertaProjeto.objects.all().count(), count + 1)
        return self.retornar(OfertaProjeto)

    def cadastro_fonte_recurso(self, edital=None, codigo_despesa='339030'):
        if not edital:
            self.cadastro_edital()
            edital = Edital.objects.all()[0]

        naturezadespesa = self.retornar(NaturezaDespesa, chaves={'codigo': codigo_despesa})

        url = '/projetos/adicionar_recurso/%d/' % edital.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Recurso', status_code=200)
        count = Recurso.objects.all().count()
        origem = OrigemRecursoEdital.objects.all()[0]
        input = dict(origem_recurso=origem.pk, valor='1000,00', despesa=naturezadespesa.pk)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(Recurso.objects.all().count(), count + 1)
        return self.retornar(Recurso)

    def cadastrar_projeto(self, edital=None, **params):
        if not edital:
            self.cadastro_ofertaprojeto()
            edital = Edital.objects.filter(tipo_edital='Extensão')[0]
        unidadeorganizacional = edital.ofertaprojeto_set.all()[0].uo
        areaconhecimento = AreaConhecimento.objects.filter(superior__isnull=False)[0]
        areatematica = AreaTematica.objects.filter(descricao='Multidisciplinar')[0]
        tema = Tema.objects.filter(descricao__contains='Tecnologia')[0]
        focotecnologico = edital.ofertaprojeto_set.all()[0].focos_tecnologicos.all()[0]

        url = '/projetos/adicionar_projeto/%d/' % edital.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Projeto', status_code=200)
        count = Projeto.objects.all().count()
        fim_execucao = datetime.now() + timedelta(days=10)
        input = dict(
            edital=edital.pk,
            uo=unidadeorganizacional.pk,
            titulo='Título do Projeto',
            area_conhecimento=areaconhecimento.pk,
            area_tematica=areatematica.pk,
            tema=tema.pk,
            focotecnologico=focotecnologico.pk,
            justificativa='Justificativa do Projeto',
            resumo='Resumo do Projeto',
            objetivo_geral='Objetivo do Projeto',
            metodologia='Metodologia do Projeto',
            acompanhamento_e_avaliacao='Acompanhamento e Avaliação do Projeto',
            resultados_esperados='Resultados Esperados do Projeto',
            referenciasbibliograficas='Referencias bibliograficas do projeto',
            fundamentacaoteorica='Fundamentação teorica do projeto',
            inicio_execucao='01/01/2012',
            fim_execucao=fim_execucao.strftime('%d/%m/%Y'),
            publico_alvo='Ambos',
            carga_horaria=4,
        )
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(Projeto.objects.all().count(), count + 1)
        return self.retornar(Projeto)

    def _test_cadastrar_projeto_continuo(self):
        self.test_cadastro_edital_continuo()
        edital = Edital.objects.filter(tipo_edital=Edital.EXTENSAO_FLUXO_CONTINUO)[0]

        unidadeorganizacional = edital.ofertaprojeto_set.all()[0].uo
        areaconhecimento = AreaConhecimento.objects.filter(superior__isnull=False)[0]
        focotecnologico = edital.ofertaprojeto_set.all()[0].focos_tecnologicos.all()[0]

        url = '/projetos/adicionar_projeto/%d/' % edital.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Projeto', status_code=200)
        count = Projeto.objects.all().count()
        input = dict(
            edital=edital.pk,
            uo=unidadeorganizacional.pk,
            titulo='Título do Projeto',
            area_conhecimento=areaconhecimento.pk,
            focotecnologico=focotecnologico.pk,
            justificativa='Justificativa do Projeto',
            resumo='Resumo do Projeto',
            objetivo_geral='Objetivo do Projeto',
            metodologia='Metodologia do Projeto',
            acompanhamento_e_avaliacao='Acompanhamento e Avaliação do Projeto',
            resultados_esperados='Resultados Esperados do Projeto',
            referenciasbibliograficas='Referencias bibliograficas do projeto',
            fundamentacaoteorica='Fundamentação teorica do projeto',
            inicio_execucao='01/01/2012',
            fim_execucao='31/12/2012',
        )
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(Projeto.objects.all().count(), count + 1)

    def cadastrar_participacao_aluno(self, projeto=None, **params):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]
        aluno = Aluno.objects.get(matricula='1')

        url = '/projetos/adicionar_participante_aluno/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Aluno', status_code=200)
        count = Participacao.objects.all().count()
        input = dict(vinculo='Bolsista', carga_horaria='10', aluno=aluno.pk, data=self.get_str_date())
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        # self.assertRedirects(response, url, status_code=302)
        self.assertEqual(Participacao.objects.all().count(), count + 1)
        return self.retornar(Participacao)

    def cadastrar_participacao_servidor(self, projeto=None, **params):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]
        servidor = self.servidor_b

        url = '/projetos/adicionar_participante_servidor/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Participante', status_code=200)
        count = Participacao.objects.all().count()
        ae_count = ParticipacaoBolsa.objects.all().count()
        input = dict(vinculo='Bolsista', carga_horaria='10', servidor=servidor.pk, data=self.get_str_date())
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        # self.assertRedirects(response, url, status_code=302)
        self.assertEqual(Participacao.objects.all().count(), count + 1)
        self.assertEqual(ParticipacaoBolsa.objects.all().count(), ae_count)
        return self.retornar(Participacao)

    def cadastrar_meta(self, projeto=None, **params):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/adicionar_meta/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Meta', status_code=200)
        count = Meta.objects.all().count()
        input = dict(ordem='1', descricao='Meta 1')
        input.update(params)
        response = self.client.post(url, input)
        self.assertEqual(Meta.objects.all().count(), count + 1)
        return self.retornar(Meta)

    def cadastrar_foto_projeto(self, projeto=None):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]
        count = FotoProjeto.objects.all().count()

        from PIL import Image
        import io
        from django.core.files.uploadedfile import SimpleUploadedFile
        image = Image.new('RGBA', size=(512, 256), color=(128, 128, 128))
        image_file = io.BytesIO()
        image_file.name = 'arquivo.png'
        image.save(image_file, format='png')
        image_file.seek(0)
        uploaded_image = SimpleUploadedFile('arquivo.png', image_file.read(), 'image/png',)

        url = '/projetos/adicionar_foto/%d/' % projeto.pk
        dados = dict(projeto=projeto.id, legenda='Legenda da Foto', imagem=uploaded_image)
        self.client.post(url, dados)
        self.assertEqual(FotoProjeto.objects.all().count(), count + 1)

    def enviar_projeto(self, projeto=None):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/projeto/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, '/projetos/concluir_planejamento/%d/' % projeto.id, msg_prefix='Botão Enviar Projeto não existe.')

        url = '/projetos/concluir_planejamento/%d/' % projeto.pk
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Projeto enviado com sucesso', status_code=200)
        projeto = Projeto.objects.get(id=projeto.id)
        self.assertEqual(projeto.data_conclusao_planejamento.date(), date.today())

    def registrar_conclusao_projeto(self, projeto=None):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/projeto/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, '/projetos/registro_conclusao/%d/' % projeto.id, msg_prefix='Botão Registrar/Editar Conclusão não existe.')

        url = '/projetos/registro_conclusao/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Conclusão do Projeto', status_code=200)
        count = RegistroConclusaoProjeto.objects.all().count()
        input = dict(
            projeto=projeto.id, resultados_alcancados='Resultados Alcançados', disseminacao_resultados='Disseminação dos Resultados', obs='Observação da conclusão do projeto'
        )
        response = self.client.post(url, input)
        self.assertEqual(RegistroConclusaoProjeto.objects.all().count(), count + 1)
        return self.retornar(Meta)

    def finalizar_projeto(self, projeto=None):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/projeto/%d/?tab=conclusao' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, '/projetos/finalizar_conclusao/%d/' % projeto.id, msg_prefix='Botão Finalizar Projeto não existe.')

        url = '/projetos/finalizar_conclusao/%d/' % projeto.pk
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Conclusão finalizada com sucesso', status_code=200)
        projeto = Projeto.objects.get(id=projeto.id)
        hoje = datetime.now().date()
        self.assertEqual(projeto.data_finalizacao_conclusao.date(), hoje)

    def cadastrar_adicionar_caracterizacao_beneficiario(self, projeto=None, **params):
        if not projeto:
            projeto = self.cadastrar_projeto()
        tipo_beneficiario = TipoBeneficiario.objects.all()[0]

        url = '/projetos/adicionar_caracterizacao_beneficiario/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Caracterização do Beneficiário', status_code=200)

        count = CaracterizacaoBeneficiario.objects.all().count()
        input = dict(tipo_beneficiario=tipo_beneficiario.id, quantidade='10')
        input.update(params)
        response = self.client.post(url, input, follow=True)
        self.assertContains(response, 'Caracterização do beneficiário adicionada com sucesso', status_code=200)
        self.assertEqual(CaracterizacaoBeneficiario.objects.all().count(), count + 1)
        return self.retornar(CaracterizacaoBeneficiario)

    def cadastrar_etapa_atividade(self, meta=None, **params):
        hoje = datetime.now()
        if not meta:
            meta = self.cadastrar_meta()

        url = '/projetos/adicionar_etapa/%d/' % meta.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Atividade', status_code=200)
        count = Etapa.objects.all().count()
        participante = Participacao.objects.filter(projeto=meta.projeto)[0]
        input = dict(
            ordem='1',
            descricao='Atividade 1',
            unidade_medida='Aluno',
            qtd='50',
            indicadores_qualitativos='Nota das avaliacões',
            responsavel=participante.pk,
            inicio_execucao=hoje.strftime('%d/%m/%Y'),
            fim_execucao=(hoje + +timedelta(days=10)).strftime('%d/%m/%Y'),
        )
        input.update(params)
        response = self.client.post(url, input)
        self.assertEqual(Etapa.objects.all().count(), count + 1)
        return self.retornar(Etapa)

    def cadastrar_registro_execucao_atividade(self, etapa_atividade=None, **params):
        hoje = datetime.now()
        if not etapa_atividade:
            etapa_atividade = self.cadastrar_etapa_atividade()

        # Verifica se o botão "Registrar Execução" existe
        url = '/projetos/projeto/%d/?tab=metas' % etapa_atividade.meta.projeto.id
        response = self.client.get(url)
        self.assertContains(response, '/projetos/registro_execucao_etapa/%d/' % etapa_atividade.id, status_code=200, msg_prefix='Botão Registrar Execução não existe')

        url = '/projetos/registro_execucao_etapa/%d/' % etapa_atividade.id
        count = RegistroExecucaoEtapa.objects.all().count()
        input = dict(
            tipo_indicador_qualitativo=RegistroExecucaoEtapa.ATENDIDO,
            qtd='1',
            indicadores_qualitativos='Nota das avaliacões',
            inicio_execucao=hoje.strftime('%d/%m/%Y'),
            fim_execucao=(hoje + +timedelta(days=10)).strftime('%d/%m/%Y'),
            info_ind_qualitativo='',
            obs='Observação sobre a Descrição da Atividade Realizada',
        )
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(RegistroExecucaoEtapa.objects.all().count(), count + 1)
        return self.retornar(RegistroExecucaoEtapa)

    def cadastrar_itemmemoriacalculo(self, projeto=None, **params):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        naturezadespesa = self.retornar(NaturezaDespesa, chaves={'codigo': '339030'})
        recurso = Recurso.objects.filter(despesa=naturezadespesa, edital=projeto.edital)[0]
        url = '/projetos/memoria_calculo/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Memória de Cálculo', status_code=200)
        count = ItemMemoriaCalculo.objects.all().count()
        input = dict(recurso=recurso.pk, descricao='Descrição da despensa', unidade_medida='Unid', qtd='10', valor_unitario='50,00')
        input.update(params)
        response = self.client.post(url, input)
        self.assertEqual(ItemMemoriaCalculo.objects.all().count(), count + 1)
        return self.retornar(ItemMemoriaCalculo)

    def cadastrar_registro_execucao_gastos(self, item_memoria_calculo=None, **params):
        if not item_memoria_calculo:
            item_memoria_calculo = self.cadastrar_itemmemoriacalculo()

        ano, created = Ano.objects.get_or_create(ano=str(datetime.now().year))

        # Verifica se o botão "Gerenciar Gasto" existe
        url = '/projetos/projeto/%d/?tab=plano_desembolso' % item_memoria_calculo.projeto.id
        response = self.client.get(url)
        self.assertContains(response, '/projetos/registro_gasto/%d/' % item_memoria_calculo.id, status_code=200, msg_prefix='Botão Gerenciar Gastos não existe')

        url = '/projetos/registro_gasto/%d/' % item_memoria_calculo.id
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Gasto', status_code=200)
        count = RegistroGasto.objects.all().count()
        input = dict(ano=ano.id, mes=datetime.now().month, descricao='descrição do gasto', qtd='1', valor_unitario='1.000,00')
        input.update(params)
        response = self.client.post(url, input)
        self.assertEqual(RegistroGasto.objects.all().count(), count + 1)
        return self.retornar(RegistroGasto)

    def cadastrar_desembolso(self, itemmemoriacalculo=None, **params):
        if not itemmemoriacalculo:
            self.cadastrar_itemmemoriacalculo()
            itemmemoriacalculo = ItemMemoriaCalculo.objects.all()[0]
        ano, created = Ano.objects.get_or_create(ano=str(datetime.now().year))

        url = '/projetos/adicionar_desembolso/%d/' % itemmemoriacalculo.projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Desembolso', status_code=200)
        count = Desembolso.objects.all().count()
        input = dict(ano=ano.pk, mes='10', item=itemmemoriacalculo.pk, valor='500,00')
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(Desembolso.objects.all().count(), count + 1)
        return self.retornar(Desembolso)

    def cadastrar_caracterizacao_beneficiario(self, projeto=None, **params):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]
        url = '/projetos/adicionar_caracterizacao_beneficiario/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Caracterização do Beneficiário', status_code=200)
        tipo_beneficiario = TipoBeneficiario.objects.latest('id')
        count = CaracterizacaoBeneficiario.objects.all().count()
        input = dict(tipo_beneficiario=tipo_beneficiario.pk, quantidade='10')
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(CaracterizacaoBeneficiario.objects.all().count(), count + 1)
        return self.retornar(CaracterizacaoBeneficiario)

    @prevent_logging_errors()
    def cadastrar_pre_avaliar_projeto(self, projeto=None):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/projetos_nao_avaliados/%d/' % projeto.edital.id
        response = self.client.get(url)
        #         self.assertContains(response, u'/projetos/pre_selecionar/%d/' %projeto.id, status_code=200,
        #                             msg_prefix=u'Botão pré-selecionar não existe.' )

        url = '/projetos/pre_selecionar/%d/' % projeto.pk
        Projeto.objects.filter(pre_aprovado=True, data_pre_avaliacao__isnull=False).count()
        count2 = 0
        if projeto.edital.tipo_edital == Edital.EXTENSAO_FLUXO_CONTINUO:
            count2 = Projeto.objects.filter(aprovado=True).count()
        response = self.client.get(url, HTTP_REFERER='/projetos/projetos_nao_avaliados/%d/' % projeto.edital.id)
        self.assertRedirects(response, '/projetos/projetos_nao_avaliados/%d/' % projeto.edital.id, status_code=302)
        # self.assertEquals(Projeto.objects.filter(pre_aprovado=True, data_pre_avaliacao__isnull=False).count(), count1+1)
        if projeto.edital.tipo_edital == Edital.EXTENSAO_FLUXO_CONTINUO:
            self.assertEqual(Projeto.objects.filter(aprovado=True).count(), count2 + 1)

    def cadastrar_pre_reprovar_projeto(self, projeto=None):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/pre_rejeitar/%d/' % projeto.pk
        count = Projeto.objects.filter(pre_aprovado=False, data_pre_avaliacao__isnull=False).count()
        self.client.get(url)
        self.assertEqual(Projeto.objects.filter(pre_aprovado=False, data_pre_avaliacao__isnull=False).count(), count + 1)

    def cadastrar_avaliar_projeto(self, projeto=None, pontuacao='8.0'):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]
        url = '/projetos/avaliar/%d/' % projeto.pk
        #         response = self.client.get(url)
        #         self.assertContains(response, u'Avaliação de Projeto', status_code=200)
        input = {'parecer': 'Favorável'}
        for criterio in projeto.edital.criterioavaliacao_set.all():
            input[criterio.id] = pontuacao
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, url, status_code=302)

    def cadastrar_emitir_parecer_conclusao_projeto(self, projeto=None, **params):
        if not projeto:
            self.cadastrar_projeto()
            projeto = Projeto.objects.all()[0]

        url = '/projetos/validar_execucao_etapa/%d/?tab=2' % projeto.id
        response = self.client.get(url, follow=True)
        self.assertContains(
            response, '/projetos/avaliar_conclusao_projeto/%d/' % projeto.get_registro_conclusao().pk, status_code=200, msg_prefix='Botão Emitir Parecer não existe.'
        )

        url = '/projetos/avaliar_conclusao_projeto/%d/' % projeto.get_registro_conclusao().pk
        response = self.client.get(url)
        self.assertContains(response, 'Validação da Conclusão do Projeto', status_code=200)
        input = {'aprovado': 'on', 'obs': 'Favorável'}
        input.update(params)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)

        registro_conclusao = RegistroConclusaoProjeto.objects.filter(projeto__id=projeto.id)[0]
        self.assertEqual(registro_conclusao.aprovado, True)

        url = '/projetos/validar_execucao_etapa/%d/?tab=2' % projeto.pk
        response = self.client.get(url)
        hoje = datetime.combine(date.today(), datetime.min.time())
        self.assertContains(response, 'Avaliado em %s' % hoje.strftime('%d/%m/%Y'), status_code=200)

    def cadastrar_aprovar_registro_execucao_etapa(self, registro=None, **params):
        if not registro:
            registro = self.cadastrar_registro_execucao_atividade()

        # Verifica se o botão "Aprovar" existe
        projeto = registro.etapa.meta.projeto
        url = '/projetos/validar_execucao_etapa/%d/' % projeto.id
        response = self.client.get(url)
        self.assertContains(response, '?registro_id=%d' % registro.id, status_code=200, msg_prefix='Botão Aprovar não existe.')
        url = '/projetos/validar_execucao_etapa/%d/?registro_id=%d' % (projeto.id, registro.id)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Execução de atividade validada com sucesso', status_code=200)

        hoje = datetime.combine(date.today(), datetime.min.time())
        self.assertContains(response, 'Aprovado em %s' % hoje.strftime('%d/%m/%y'), status_code=200)
        registro_etapa = RegistroExecucaoEtapa.objects.filter(id=registro.id)[0]
        self.assertEqual(registro_etapa.aprovado, True)

    def cadastrar_aprovar_registro_execucao_gastos(self, registro=None, **params):
        if not registro:
            registro = self.cadastrar_registro_execucao_gastos()

        # Verifica se o botão "Aprovar" existe
        projeto = registro.item.projeto
        url = '/projetos/validar_execucao_etapa/%d/?tab=1' % projeto.id
        response = self.client.get(url)
        self.assertContains(response, '?item_id=%d' % registro.id, status_code=200, msg_prefix='Botão Aprovar não existe.')

        url = '/projetos/validar_execucao_etapa/%d/?item_id=%d' % (projeto.id, registro.id)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Gasto validado com sucesso', status_code=200)

        hoje = datetime.combine(date.today(), datetime.min.time())
        self.assertContains(response, 'Aprovado em %s' % hoje.strftime('%d/%m/%y'), status_code=200)
        registro_gasto = RegistroGasto.objects.filter(id=registro.id)[0]
        self.assertEqual(registro_gasto.aprovado, True)

    def cadastrar_criterio_avaliacao(self, edital=None):
        if not edital:
            self.cadastro_edital()
            edital = Edital.objects.filter(tipo_edital=Edital.EXTENSAO)[0]
        url = '/projetos/adicionar_criterio_avaliacao/%d/' % edital.pk

        count_criterio = CriterioAvaliacao.objects.all().count()
        input = dict(edital=edital.pk, descricao='Adequação da proposta ao tema', pontuacao_maxima='10,00', ordem_desempate=1)
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(CriterioAvaliacao.objects.all().count(), count_criterio + 1)

    def cadastrar_beneficiarios_atendidos(self, projeto):

        url = '/projetos/projeto/%d/?tab=caracterizacao_beneficiario' % projeto.id
        response = self.client.get(url)
        caracterizacao = CaracterizacaoBeneficiario.objects.filter(projeto=projeto)[0]
        self.assertContains(response, '/projetos/registro_beneficiario_atendido/%d/' % caracterizacao.id, status_code=200, msg_prefix='Botão Registrar não existe')

        url = '/projetos/registro_beneficiario_atendido/%d/' % caracterizacao.id
        count = CaracterizacaoBeneficiario.objects.filter(quantidade_atendida__isnull=False).count()
        input = dict(quantidade_atendida='5')
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(CaracterizacaoBeneficiario.objects.filter(quantidade_atendida__isnull=False).count(), count + 1)
        return self.retornar(CaracterizacaoBeneficiario)

    def eh_coordenador_projeto(self, user):
        return user == self.servidor_a.user

    def eh_pre_avaliador(self, user):
        return in_group(user, ['Coordenador de Extensão'])

    def eh_pre_avaliador_mesmo_campus(self, user, projeto):
        return self.eh_pre_avaliador(user) and projeto.uo == get_uo(user)

    def eh_avaliador(self, user):
        return in_group(user, ['Avaliador de Projetos de Extensão'])

    def eh_avaliador_mesmo_campus(self, user, projeto):
        return self.eh_avaliador(user) and projeto.uo == get_uo(user)

    def login_outro_campus(self):
        self.logout()
        successful = self.client.login(user=self.servidor_e.user)
        self.assertEqual(successful, True)
        return self.client.user

    def login(self, user=None):
        self.logout()
        if not user:
            user = self.servidor_a.user
        successful = self.client.login(user=user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_coordenador_projeto(self):
        self.logout()
        successful = self.client.login(user=self.servidor_a.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_pre_avaliador_outro_campus(self):
        self.logout()
        successful = self.client.login(user=self.servidor_c.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_pre_avaliador_mesmo_campus(self):
        self.logout()
        successful = self.client.login(user=self.servidor_a2.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_avaliador_outro_campus(self):
        self.logout()
        successful = self.client.login(user=self.servidor_d.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_avaliador_mesmo_campus(self):
        self.logout()
        successful = self.client.login(user=self.servidor_a3.user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_gerente_sistemico(self):
        self.logout()
        successful = self.client.login(user=self.servidor_b.user)
        self.assertEqual(successful, True)
        return self.client.user

    #
    def get_str_date(self, qtd_dias=0):
        return self.somar_data_atual(qtd_dias).strftime('%d/%m/%Y')

    def somar_data_atual(self, qtd_dias=0):
        hoje = datetime.now()
        return hoje + timedelta(qtd_dias)

    def set_data_antes_inicio_inscricao(self, edital):
        self.set_data_inicio_inscricao(edital)
        edital.inicio_inscricoes = self.somar_data_atual(1)
        edital.save()

    def set_data_inicio_inscricao(self, edital):
        if edital.tipo_edital == Edital.EXTENSAO:
            edital.inicio_inscricoes = self.somar_data_atual(0)
            edital.fim_inscricoes = self.somar_data_atual(5)
            edital.inicio_pre_selecao = self.somar_data_atual(10)
            edital.inicio_selecao = self.somar_data_atual(15)
            edital.fim_selecao = self.somar_data_atual(20)
            edital.divulgacao_selecao = self.somar_data_atual(21)
        edital.save()

    def set_data_pos_fim_inscricoes(self, edital):
        self.set_data_inicio_inscricao(edital)
        edital.fim_inscricoes = self.somar_data_atual(-1)
        if edital.tipo_edital == Edital.EXTENSAO:
            edital.inicio_inscricoes = self.somar_data_atual(-5)
            edital.inicio_pre_selecao = self.somar_data_atual(10)
            edital.inicio_selecao = self.somar_data_atual(15)
            edital.fim_selecao = self.somar_data_atual(20)
            edital.divulgacao_selecao = self.somar_data_atual(21)
        edital.save()

    def set_data_inicio_pre_selecao(self, edital):
        self.set_data_inicio_inscricao(edital)
        if edital.tipo_edital == Edital.EXTENSAO:
            edital.inicio_inscricoes = self.somar_data_atual(-10)
            edital.fim_inscricoes = self.somar_data_atual(-5)
            edital.inicio_pre_selecao = self.somar_data_atual(0)
            edital.inicio_selecao = self.somar_data_atual(15)
            edital.fim_selecao = self.somar_data_atual(20)
            edital.divulgacao_selecao = self.somar_data_atual(21)
        edital.save()

    def set_data_inicio_selecao(self, edital):
        self.set_data_inicio_inscricao(edital)
        if edital.tipo_edital == Edital.EXTENSAO:
            edital.inicio_inscricoes = self.somar_data_atual(-15)
            edital.fim_inscricoes = self.somar_data_atual(-10)
            edital.inicio_pre_selecao = self.somar_data_atual(-5)
            edital.inicio_selecao = self.somar_data_atual(0)
            edital.fim_selecao = self.somar_data_atual(20)
            edital.divulgacao_selecao = self.somar_data_atual(21)
        edital.save()

    def set_data_divulgacao_selecao(self, edital):
        self.set_data_inicio_inscricao(edital)
        if edital.tipo_edital == Edital.EXTENSAO:
            edital.inicio_inscricoes = self.somar_data_atual(-20)
            edital.fim_inscricoes = self.somar_data_atual(-15)
            edital.inicio_pre_selecao = self.somar_data_atual(-10)
            edital.inicio_selecao = self.somar_data_atual(-5)
            edital.fim_selecao = self.somar_data_atual(-1)
            edital.divulgacao_selecao = self.somar_data_atual(0)
        edital.save()

    def cadastros_edital(self, tipo_edital, edital_titulo):
        self.cadastro_foco_tecnologico()

        # EDITAL TIPO EXTENSÃO
        if tipo_edital == Edital.EXTENSAO:
            edital = self.cadastro_edital(
                titulo=edital_titulo,
                inicio_inscricoes=self.get_str_date(),
                fim_inscricoes=self.get_str_date(5),
                inicio_pre_selecao=self.get_str_date(10),
                inicio_selecao=self.get_str_date(15),
                divulgacao_selecao=self.get_str_date(20),
                participa_aluno='1',
                participa_servidor='1',
                tipo_edital=tipo_edital,
                qtd_maxima_alunos=5,
                qtd_maxima_servidores=5,
                qtd_maxima_alunos_bolsistas=3,
                qtd_maxima_servidores_bolsistas=3,
                peso_avaliacao_lattes_coordenador=1,
                peso_avaliacao_projeto=1,
                exige_anuencia=Edital.SEM_ANUENCIA,
            )
        else:
            hoje = datetime.today()
            edital = self.cadastro_edital(
                titulo=edital_titulo,
                inicio_inscricoes='01/01/%s' % hoje.year,
                fim_inscricoes='31/12/%s' % hoje.year,
                inicio_pre_selecao='01/01/%s' % hoje.year,
                inicio_selecao='01/01/%s' % hoje.year,
                divulgacao_selecao='01/01/%s' % hoje.year,
                participa_aluno='1',
                participa_servidor='1',
                tipo_edital=tipo_edital,
                qtd_maxima_alunos=5,
                qtd_maxima_servidores=5,
                qtd_maxima_alunos_bolsistas=3,
                qtd_maxima_servidores_bolsistas=3,
                peso_avaliacao_lattes_coordenador=1,
                peso_avaliacao_projeto=1,
                exige_anuencia=Edital.SEM_ANUENCIA,
            )
        self.cadastro_editalanexoauxiliar(edital)
        self.cadastro_editalanexo(edital)
        self.cadastro_fonte_recurso(edital, codigo_despesa='339030')  # Material de Consumo
        self.cadastro_fonte_recurso(edital, codigo_despesa='339018')  # Auxílio Financeiro a Estudantes
        self.cadastro_fonte_recurso(edital, codigo_despesa='339020')  # Auxílio Financeiro a Pesquisadores
        self.cadastro_ofertaprojeto(edital, uo=self.servidor_a.pessoafisica.funcionario.setor.uo.pk, qtd_aprovados='10', qtd_selecionados='5')
        self.cadastro_ofertaprojeto(edital, uo=self.servidor_b.pessoafisica.funcionario.setor.uo.pk, qtd_aprovados='2', qtd_selecionados='1')

        self.cadastrar_criterio_avaliacao()
        return edital

    def cadastros_projeto(self, edital, projeto_titulo):

        projeto = self.cadastrar_projeto(edital, titulo=projeto_titulo, inicio_execucao=self.get_str_date(), fim_execucao=self.get_str_date(365))
        # aba Caracterização dos Beneficiários
        self.cadastrar_adicionar_caracterizacao_beneficiario(projeto)
        # aba Equipe
        aluno = Aluno.objects.get(matricula='1')
        self.cadastrar_participacao_aluno(projeto, aluno=aluno.id)
        aluno = Aluno.objects.get(matricula='2')
        self.cadastrar_participacao_aluno(projeto, aluno=aluno.id)
        self.cadastrar_participacao_servidor(projeto)
        # aba Metas/Atividades
        meta = self.cadastrar_meta(projeto)
        self.cadastrar_etapa_atividade(meta)
        # Aba Plano de Aplicação
        itemmemoriacalculo = self.cadastrar_itemmemoriacalculo(projeto)
        # Aba Plano de Desembolso
        self.cadastrar_desembolso(itemmemoriacalculo)
        # aba anexos
        editalanexo = EditalAnexo.objects.all()[0]
        participante = Participacao.objects.filter(projeto=projeto)[0]
        from comum.models import Arquivo

        arquivo = Arquivo()
        arquivo.save(nome='teste', vinculo=participante.vinculo_pessoa)
        ProjetoAnexo.objects.create(projeto=projeto, anexo_edital=editalanexo, arquivo=arquivo, vinculo_membro_equipe=participante.get_participante().get_vinculo())

        # aba fotos
        self.cadastrar_foto_projeto(projeto)


class ProjetosExtensaoTestCase(ProjetosTestCase):
    # http://localhost:8000/projetos/avaliacao/
    # http://localhost:8000/projetos/projetos_pre_aprovados/20/1/
    # http://localhost:8000/projetos/avaliar/883/

    def setUp(self):
        super().setUp()
        # Status definidos para serem utilizados na fase de inscrição do edital
        self.status_pre_selecao_gerente_sistemico = Projeto.STATUS_EM_ESPERA
        self.status_selecao_gerente_sistemico = Projeto.STATUS_EM_ESPERA
        self.status_pre_selecao = Projeto.STATUS_AGUARDANDO_PRE_SELECAO
        self.status_avaliacao = Projeto.STATUS_AGUARDANDO_AVALIACAO
        self.status_edital = Projeto.PERIODO_INSCRICAO
        self.status_projeto = Projeto.STATUS_EM_INSCRICAO

        self.acessar_como_gerente_sistemico()
        edital = self.cadastros_edital(Edital.EXTENSAO, 'Edital 001 Extensão')

        self.acessar_como_coordenador_projeto()
        self.cadastros_projeto(edital, 'Projeto 001 Extensão')

    def get_edital(self):
        return self.retornar(Edital, chaves={'titulo': 'Edital 001 Extensão'})

    def get_projeto(self):
        return self.retornar(Projeto, chaves={'titulo': 'Projeto 001 Extensão'})

    def test_enviar_projeto(self):
        """
        Botão enviar projeto ficará visível somente no período de inscrição e se o mesmo não foi enviado.
        Projetos só poderão ser enviados se possuir registros de atividades, plano de aplicações e plano de desembolso
        """

        Meta.objects.all().delete()
        Etapa.objects.all().delete()
        ItemMemoriaCalculo.objects.all().delete()
        Desembolso.objects.all().delete()
        CaracterizacaoBeneficiario.objects.all().delete()
        self.acessar_como_coordenador_projeto()
        edital = self.get_edital()
        projeto = self.get_projeto()

        url = '/projetos/projeto/%d/' % projeto.pk

        # Verifica se o botão "Enviar Projeto" existe
        self.set_data_inicio_inscricao(edital)
        response = self.client.get(url)
        self.assertContains(response, '/projetos/concluir_planejamento/%d/' % projeto.id, status_code=200)

        # Verifica se o botão "Enviar Projeto" não existe
        self.set_data_antes_inicio_inscricao(edital)
        response = self.client.get(url)
        self.assertNotContains(response, '/projetos/concluir_planejamento/%d/' % projeto.id, status_code=200)
        self.set_data_pos_fim_inscricoes(edital)
        response = self.client.get(url)
        self.assertNotContains(response, '/projetos/concluir_planejamento/%d/' % projeto.id, status_code=200)

        # Projeto não pode ser enviado pois está incompleto
        url = '/projetos/concluir_planejamento/%d/' % projeto.pk
        self.set_data_inicio_inscricao(edital)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Cadastre o Plano de Aplicação antes de enviar o Projeto.', status_code=200)
        self.assertContains(response, 'Cadastre as Metas/Atividades antes de enviar o Projeto.', status_code=200)
        self.assertContains(response, 'Cadastre a Caracterização dos Beneficiários antes de enviar o Projeto.', status_code=200)
        # Projeto pode ser enviado
        self.submeter_projeto_para_edital(projeto)

        # Verifica se o botão "Enviar Projeto" não existe
        url = '/projetos/projeto/%d/' % projeto.pk
        response = self.client.get(url)
        self.assertNotContains(response, '/projetos/concluir_planejamento/%d/' % projeto.id, status_code=200)

    def submeter_projeto_para_edital(self, projeto):
        self.set_data_inicio_inscricao(projeto.edital)
        meta = self.cadastrar_meta(projeto)
        self.cadastrar_etapa_atividade(meta)
        itemmemoriacalculo = self.cadastrar_itemmemoriacalculo(projeto)
        self.cadastrar_desembolso(itemmemoriacalculo)
        self.cadastrar_caracterizacao_beneficiario(projeto)
        self.enviar_projeto(projeto)

    def test_fluxo(self):
        """
        Botão finalizar projetos só estará visível se o período do edital for o período de execução,
        existir registros de conclusão do projeto, ser coordenador do projeto e não ter solicitado a finalização do mesmo (
        data_finalizacao_conclusao = None)
        """
        # ./manage.py test_suap projetos.tests.ProjetosExtensaoTestCase.test_fluxo --nopylint

        self.acessar_como_coordenador_projeto()
        edital = self.get_edital()
        projeto = self.get_projeto()

        # TODO: implementar indicar_avaliador
        indicar_avaliador = AvaliadorIndicado()
        indicar_avaliador.projeto = projeto
        indicar_avaliador.pessoa_fisica = self.servidor_a3.pessoa_fisica
        indicar_avaliador.vinculo = self.servidor_a3.get_vinculo()
        indicar_avaliador.save()

        url = '/projetos/projeto/%d/' % projeto.pk

        # Botão "Registrar/Editar Conclusão" e "Finalizar Conclusão" não disponível se não for período de execução
        self.set_data_inicio_inscricao(edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_INSCRICAO, Projeto.STATUS_EM_INSCRICAO)
        botoes = {
            '/projetos/registro_execucao_etapa/': False,
            '/projetos/adicionar_foto/': False,
            '/projetos/remover_foto/': False,
            '/projetos/registro_gasto/': False,
            '/projetos/registro_conclusao/': False,
            '/projetos/finalizar_conclusao/': False,
        }
        self.verificar_botoes_tela_projeto(botoes=botoes)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_validar_execucao(disponivel=False)

        self.acessar_como_coordenador_projeto()
        self.test_enviar_projeto()
        self.status_visualizar_projetos(url, Projeto.PERIODO_INSCRICAO, Projeto.STATUS_INSCRITO)

        self.verificar_botoes_tela_projeto(disponivel=False)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_validar_execucao(disponivel=False)

        # TODO: implementar cadastro_devolver_projeto

        self.pre_aprovar_projeto(projeto)
        self.status_visualizar_projetos(url, Projeto.PERIODO_PRE_SELECAO, Projeto.STATUS_PRE_SELECIONADO)
        self.verificar_botoes_tela_projeto(disponivel=False)
        botoes_pre_selecao = {'/projetos/pre_selecionar/%d/' % projeto.id: False, '/projetos/gerenciar_historico_projeto/%d/' % projeto.id: False}
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=True, botoes=botoes_pre_selecao)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_validar_execucao(disponivel=False)

        self.aprovar_projeto(projeto)
        self.status_visualizar_projetos(url, Projeto.PERIODO_SELECAO, Projeto.STATUS_EM_SELECAO)
        self.verificar_botoes_tela_projeto(disponivel=False)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=True)
        self.verificar_botoes_tela_validar_execucao(disponivel=False)

        # Inicio da fase de execução, o que foi planejado não pode ser editado.
        self.acessar_como_coordenador_projeto()
        self.set_data_divulgacao_selecao(edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_EXECUCAO, Projeto.STATUS_EM_EXECUCAO)
        response = self.client.get(url)
        botoes = {
            '/projetos/editar_meta/': False,
            '/projetos/remover_meta/': False,
            '/projetos/editar_etapa/': False,
            '/projetos/remover_etapa/': False,
            '/?del_id=': False,
            '/?edit_id': False,
            '/projetos/editar_desembolso/': False,
            '/projetos/remover_desembolso/': False,
            '/projetos/finalizar_conclusao/': False,
            'projetos/projeto/%d/delete/' % projeto.id: False,
        }
        self.verificar_botoes_tela_projeto(disponivel=True, botoes=botoes)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_validar_execucao(disponivel=False)

        meta = self.cadastrar_meta(projeto, ordem='1', descricao='Meta 2')
        atividade1 = self.retornar(Etapa)
        atividade2 = self.cadastrar_etapa_atividade(meta, ordem='2', descricao='Atividade 2')

        self.acessar_como_coordenador_projeto()
        self.registrar_conclusao_projeto(projeto)

        # Botão "Registrar/Editar Conclusão" continua disponível, pois o coordenador do projeto pode editar o registro de conclusão
        # se o mesmo ainda não tiver sido avaliado
        # Botão "Finalizar Conclusão"  não disponível pois não há registro de execução de atividades e gastos
        botoes = {'projetos/projeto/%d/delete/' % projeto.id: False, '/projetos/finalizar_conclusao/': False}
        self.verificar_botoes_tela_projeto(disponivel=True, botoes=botoes)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_validar_execucao(disponivel=False)

        self.acessar_como_coordenador_projeto()
        response = self.client.get(url + '?tab=8')
        self.assertContains(response, 'existe(m) atividade(s) sem registro(s) de execução', status_code=200)
        self.assertContains(response, 'existe(m) desembolso(s) sem o(s) registro(s) da(s) despesa(s) realizada(s)', status_code=200)
        self.assertContains(response, 'não foi informada a quantidade de beneficiários atendidos', status_code=200)

        # Registrar execução da atividade e gasto
        registro_execucao_atividade1 = self.cadastrar_registro_execucao_atividade(atividade1)
        registro_execucao_atividade2 = self.cadastrar_registro_execucao_atividade(atividade2)
        item_memoria_calculo = self.retornar(ItemMemoriaCalculo)
        registro_execucao_gasto = self.cadastrar_registro_execucao_gastos(item_memoria_calculo)

        # As mensagem de erros abaixo aparecem pois as execucções das atividades e gastos registrados não foram avaliados
        # Botão "Finalizar Conclusão" não disponível se existir gasto e/ou execução de atividades não avaliados
        response = self.client.get(url + '?tab=8')
        self.assertContains(response, 'existe(m) atividade(s) sem registro(s) de execução', status_code=200)
        self.assertContains(response, 'existe(m) desembolso(s) sem o(s) registro(s) da(s) despesa(s) realizada(s)', status_code=200)
        self.assertContains(response, 'não foi informada a quantidade de beneficiários atendidos', status_code=200)

        botoes = {'projetos/projeto/%d/delete/' % projeto.id: False, '/projetos/finalizar_conclusao/': False}
        self.verificar_botoes_tela_projeto(botoes=botoes)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        botoes = {'/projetos/avaliar_conclusao_projeto/': False}
        self.verificar_botoes_tela_validar_execucao(disponivel=True, botoes=botoes)

        # Uma vez aprovado o registro de atividade e gasto, não há mais mensagem de aviso
        # Botão "Finalizar Conclusão" disponível
        self.acessar_como_pre_avaliador_mesmo_campus()

        self.cadastrar_aprovar_registro_execucao_etapa(registro_execucao_atividade1)
        self.cadastrar_aprovar_registro_execucao_etapa(registro_execucao_atividade2)
        self.cadastrar_aprovar_registro_execucao_gastos(registro_execucao_gasto)

        self.acessar_como_coordenador_projeto()
        self.cadastrar_beneficiarios_atendidos(projeto)
        response = self.client.get(url + '?tab=8')
        self.assertNotContains(response, 'existe(m) atividade(s) sem registro(s) de execução', status_code=200)
        self.assertNotContains(response, 'existe(m) desembolso(s) sem o(s) registro(s) da(s) despesa(s) realizada(s)', status_code=200)
        self.assertNotContains(response, 'não foi informada a quantidade de beneficiários atendidos', status_code=200)

        botoes = {'projetos/projeto/%d/delete/' % projeto.id: False, '/projetos/registro_execucao_etapa/': False}
        self.verificar_botoes_tela_projeto(botoes=botoes)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        botoes = {'/projetos/avaliar_conclusao_projeto/': False}
        self.verificar_botoes_tela_validar_execucao(disponivel=False, botoes=botoes)

        # Só pode emitir parecer se o projeto tiver sido finalizado. Botões "Registrar/Editar Conclusão" e
        # "Finalizar Conclusão" não disponíveis.
        self.acessar_como_coordenador_projeto()
        self.finalizar_projeto(projeto)

        self.verificar_botoes_tela_projeto(disponivel=False)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        botoes = {'/projetos/avaliar_conclusao_projeto/': True}
        self.verificar_botoes_tela_validar_execucao(disponivel=False, botoes=botoes)

        self.acessar_como_pre_avaliador_mesmo_campus()
        self.cadastrar_emitir_parecer_conclusao_projeto(projeto)

        botoes = {}
        self.verificar_botoes_tela_projeto(disponivel=False, botoes=botoes)
        self.verificar_botoes_tela_pre_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_selecao(edital, disponivel=False)
        self.verificar_botoes_tela_validar_execucao(disponivel=False, botoes=botoes)

    def test_devolver_projeto(self):
        """
        Funcionalidade Devolver disponível para pré-avaliadores somente no período de inscrição do edital e se o projeto
        foi enviado.
        Funcionalidade Histórico de Envio disponível para todos independente do período do edital, mas somente se solicitado
        o envio do projeto
        """
        pass

    def verificar_botoes_tela_projeto(self, disponivel=True, botoes={}):
        projeto = self.get_projeto()
        user = self.client.user
        self.acessar_como_coordenador_projeto()
        url = '/projetos/projeto/%d/' % projeto.pk
        response = self.client.get(url)
        botoes_default = {
            'projetos/editar_projeto': disponivel,
            'projetos/projeto/%d/delete/' % projeto.id: disponivel,
            # Aba Caracterização dos Beneficiários
            '/projetos/adicionar_caracterizacao_beneficiario/': disponivel,
            '/projetos/editar_caracterizacao_beneficiario/': disponivel,
            '/projetos/remover_caracterizacao_beneficiario/': disponivel,
            # Aba Equipe
            '/projetos/adicionar_participante_aluno/': disponivel,
            '/projetos/editar_participante_aluno/': disponivel,
            '/projetos/adicionar_participante_servidor/': disponivel,
            '/projetos/editar_participante_servidor/': disponivel,
            '/projetos/remover_participante/': disponivel,
            '/projetos/alterar_coordenador/': disponivel,
            '/projetos/ver_plano_trabalho/': True,
            # Aba Metas/Atividades
            '/projetos/adicionar_meta/': disponivel,
            '/projetos/registro_execucao_etapa/': disponivel,
            # Aba Plano de Aplicação
            '/projetos/memoria_calculo/': disponivel,
            '/projetos/registro_gasto/': disponivel,
            # Aba Plano de Desembolso
            '/projetos/adicionar_desembolso/': disponivel,
            # Aba Anexo
            # Aba Fotos
            '/projetos/adicionar_foto/': disponivel,
            '/projetos/remover_foto/': disponivel,
            # Aba Conclusão
            '/projetos/registro_conclusao/': disponivel,
            '/projetos/finalizar_conclusao/': disponivel,
        }
        botoes_default.update(botoes)
        for botao_url, visivel in list(botoes_default.items()):
            if visivel:
                self.assertContains(response, botao_url, status_code=200)
            else:
                self.assertNotContains(response, botao_url, status_code=200)
        self.login(user)

    @prevent_logging_errors()
    def verificar_botoes_tela_pre_selecao(self, edital, disponivel=True, botoes={}):
        projeto = self.get_projeto()
        periodo = projeto.get_periodo()
        user = self.client.user
        self.acessar_como_pre_avaliador_mesmo_campus()
        url = '/projetos/projetos_nao_avaliados/%d/' % edital.pk
        response = self.client.get(url)
        if periodo == Projeto.PERIODO_PRE_SELECAO:
            botoes_default = {
                '/projetos/pre_selecionar/%d/' % projeto.id: disponivel,
                '/projetos/pre_rejeitar/%d/' % projeto.id: disponivel,
                '/projetos/gerenciar_historico_projeto/%d/' % projeto.id: disponivel,  # gerenciar devolução
                '/projetos/imprimir_projeto/%d/' % projeto.id: disponivel,
            }
            botoes_default.update(botoes)
            for botao_url, visivel in list(botoes_default.items()):
                if visivel:
                    self.assertContains(response, botao_url, status_code=200)
                else:
                    self.assertNotContains(response, botao_url, status_code=200)
        else:
            self.assertEqual(response.status_code, 403)
        self.login(user)

    def verificar_botoes_tela_validar_execucao(self, disponivel=False, botoes={}):
        projeto = self.get_projeto()
        projeto.get_periodo()
        user = self.client.user
        self.acessar_como_pre_avaliador_mesmo_campus()
        url = '/projetos/validar_execucao_etapa/%d/' % projeto.pk
        response = self.client.get(url)
        botoes_default = {
            '?item_id': disponivel,
            '/projetos/reprovar_execucao_gasto/': disponivel,
            '?registro_id': disponivel,
            '/projetos/reprovar_execucao_etapa/': disponivel,
            '/projetos/avaliar_conclusao_projeto/': disponivel,
        }
        botoes_default.update(botoes)
        for botao_url, visivel in list(botoes_default.items()):
            if visivel:
                self.assertContains(response, botao_url, status_code=200)
            else:
                self.assertNotContains(response, botao_url, status_code=200)
        self.login(user)

    @prevent_logging_errors()
    def verificar_botoes_tela_selecao(self, edital, disponivel=True, botoes={}):
        projeto = self.get_projeto()
        periodo = projeto.get_periodo()
        user = self.client.user
        self.acessar_como_avaliador_mesmo_campus()
        url = '/projetos/projetos_pre_aprovados/%d/%d/' % (edital.pk, self.servidor_a3.setor.uo.id)
        response = self.client.get(url)

        if periodo == Projeto.PERIODO_SELECAO:
            botoes_default = {
                '/projetos/projeto/%d/' % projeto.id: disponivel,
                '/projetos/avaliar/%d/' % projeto.id: disponivel,
                '/projetos/imprimir_projeto/%d/' % projeto.id: disponivel,
            }
            botoes_default.update(botoes)
            for botao_url, visivel in list(botoes_default.items()):
                if visivel:
                    self.assertContains(response, botao_url, status_code=200)
                else:
                    self.assertNotContains(response, botao_url, status_code=200)
        else:
            self.assertEqual(response.status_code, 403)
        self.login(user)

    def test_edital_tem_foco_tecnologico(self):
        self.acessar_como_gerente_sistemico()
        edital = self.get_edital()
        url = '/projetos/edital/%d/' % edital.pk
        response = self.client.get(url)
        focos = FocoTecnologico.objects.all()
        self.assertContains(response, focos[0].descricao)
        self.assertContains(response, focos[1].descricao)
        self.assertContains(response, focos[2].descricao)

    def test_pode_cadastrar_edital(self):
        self.login()
        self.verificar_perfil_status(
            '/admin/projetos/edital/add/',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
        )

    def test_pode_visualizar_edital(self):
        edital = self.get_edital()
        self.login()
        self.verificar_perfil_status('/projetos/edital/%d/' % edital.id, perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO])

    def test_pode_cadastrar_projeto(self):
        """
        Pré-avaliadores e Avaliadores não podem cadastrar projetos de nenhuma forma.
        """
        edital = self.get_edital()
        self.login()
        self.verificar_perfil_status(
            '/projetos/adicionar_projeto/%d/' % edital.id,
            perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR],
            perfis_errados=[GRUPO_EXTENSAO_GERENTE_SISTEMICO],
        )

    def test_pode_visualizar_projeto(self):
        """
        Pré-avaliadores e Avaliadores só podem visualizar projetos de seus próprios campi
        """
        projeto = self.get_projeto()
        url = '/projetos/projeto/%d/' % projeto.id

        self.acessar_como_coordenador_projeto()
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO])
        self.login_outro_campus()
        self.verificar_perfil_status(
            url, perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_AVALIADOR], perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR]
        )

    @prevent_logging_errors()
    def test_projeto_disponivel_para_pre_avaliacao(self):
        """
        Acesso "Pré-avaliar Projetos" disponível apenas para pré-avaliadores
        Se a data atual não estiver dentro do período de pré-seleção, exibir a mensagem "Nenhum edital disponível para seleção no momento"
        """

        url = '/projetos/pre_avaliacao/'
        edital = self.get_edital()

        # Projeto está disponível para pré-seleção apenas para pré-avaliadores do mesmo campus
        self.login()

        # Projetos não está disponível para avaliação se a data atual não estiver no período de avaliação
        self.set_data_inicio_inscricao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível no momento',
            perfis_corretos=[GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_pos_fim_inscricoes(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível no momento',
            perfis_corretos=[GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_inicio_pre_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text=edital.titulo,
            perfis_corretos=[GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_inicio_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível no momento',
            perfis_corretos=[GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )
        self.set_data_divulgacao_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível no momento',
            perfis_corretos=[GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        # Se não for período de pré-seleção, a página para pré-aprovar projeto não estará disponível, negar acesso para todos.
        response = self.client.get('/projetos/projetos_nao_avaliados/%d/' % edital.id)
        self.assertEqual(response.status_code, 403)

    @prevent_logging_errors()
    def test_projeto_disponivel_para_avaliacao(self):
        """
        Acesso "Avaliar Projetos" disponível para avaliadores e gerentes sistêmicos.
        Se a data atual não estiver dentro do período de seleção, exibir a mensagem "Nenhum edital disponível para seleção no momento"
        """

        url = '/projetos/avaliacao/'
        edital = self.get_edital()

        self.login()

        # Projetos não está disponível para avaliação se a data atual não estiver no período de avaliação
        self.set_data_inicio_inscricao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível para seleção no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_pos_fim_inscricoes(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível para seleção no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_inicio_pre_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível para seleção no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_inicio_selecao(edital)
        # self.verificar_perfil_contains(url,
        #                                text              = edital.titulo,
        #                                perfis_corretos   = [GRUPO_EXTENSAO_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO],
        #                                perfis_errados    = [GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR],
        #                                error_status_code = 403)
        #
        self.set_data_divulgacao_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum edital disponível para seleção no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            error_status_code=403,
        )

    def pre_aprovar_projeto(self, projeto):
        user = self.client.user
        self.acessar_como_pre_avaliador_mesmo_campus()
        self.set_data_inicio_pre_selecao(projeto.edital)
        self.cadastrar_pre_avaliar_projeto(projeto)
        self.login(user)

    def pre_reprovar_projeto(self, projeto):
        user = self.client.user
        self.acessar_como_pre_avaliador_mesmo_campus()
        self.set_data_inicio_pre_selecao(projeto.edital)
        self.cadastrar_pre_reprovar_projeto(projeto)
        self.login(user)

    def aprovar_projeto(self, projeto):
        """
        Projeto só é aprovado se existir pelo menos duas avaliaçoes
        """
        user = self.client.user
        self.acessar_como_avaliador_mesmo_campus()
        self.set_data_inicio_selecao(projeto.edital)
        self.cadastrar_avaliar_projeto(projeto)

        self.acessar_como_gerente_sistemico()
        self.set_data_inicio_selecao(projeto.edital)
        self.cadastrar_avaliar_projeto(projeto)
        self.login(user)

    def reprovar_projeto(self, projeto):
        user = self.client.user
        self.acessar_como_avaliador_mesmo_campus()
        self.set_data_inicio_selecao(projeto.edital)
        self.cadastrar_avaliar_projeto(projeto, '1.0')
        self.login(user)

    @prevent_logging_errors()
    def test_projeto_disponivel_para_monitoramento(self):
        """
        Acesso Monitoramento disponível para pré-avaliadores e gerentes sistêmicos
        """
        self.acessar_como_pre_avaliador_mesmo_campus()
        url = '/projetos/projetos_em_execucao/'
        edital = self.get_edital()
        projeto = self.get_projeto()

        self.pre_aprovar_projeto(projeto)
        self.aprovar_projeto(projeto)

        self.set_data_inicio_inscricao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum projeto em execução no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_pos_fim_inscricoes(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum projeto em execução no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_inicio_pre_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum projeto em execução no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_inicio_selecao(edital)
        self.verificar_perfil_contains(
            url,
            text='Nenhum projeto em execução no momento',
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

        self.set_data_divulgacao_selecao(edital)
        projeto = self.get_projeto()
        self.verificar_perfil_contains(
            url,
            text='/projetos/projeto/%d/' % projeto.id,
            perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO, GRUPO_EXTENSAO_PRE_AVALIADOR],
            perfis_errados=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_AVALIADOR],
            error_status_code=403,
        )

    def test_status_projetos_listagem_admin(self):
        """
        Testa os status Pré-selecionado e Selecionado em todas as fases do edital
        exibido na listagem de projetos disponível para gerentes sistêmicos
        """
        # Não houve seleção de pré-selecionados e selecionado
        self.login()
        edital = self.get_edital()
        self.set_data_inicio_inscricao(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_EM_ESPERA, Projeto.STATUS_EM_ESPERA)

        self.set_data_pos_fim_inscricoes(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_EM_ESPERA, Projeto.STATUS_EM_ESPERA)

        self.set_data_inicio_pre_selecao(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_EM_ESPERA, Projeto.STATUS_EM_ESPERA)

        self.set_data_inicio_selecao(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_NAO, Projeto.STATUS_EM_ESPERA)

        self.set_data_divulgacao_selecao(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_NAO, Projeto.STATUS_NAO)

        projeto = self.get_projeto()
        self.submeter_projeto_para_edital(projeto)
        # Houve seleção de pré-selecionados e selecionado, ambos foram aceitos
        self.pre_aprovar_projeto(projeto)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_SIM, Projeto.STATUS_EM_ESPERA)

        self.aprovar_projeto(projeto)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_SIM, Projeto.STATUS_SIM)

        self.set_data_divulgacao_selecao(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_SIM, Projeto.STATUS_SIM)

        # Houve seleção de pré-selecionados e selecionado, ambos não foram aceitos
        self.pre_reprovar_projeto(projeto)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_NAO, Projeto.STATUS_EM_ESPERA)

        self.reprovar_projeto(projeto)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_NAO, Projeto.STATUS_NAO)

        self.set_data_divulgacao_selecao(edital)
        self.status_projetos_listagem_admin_gerente_sistemico(Projeto.STATUS_NAO, Projeto.STATUS_NAO)

    def status_projetos_listagem_admin_gerente_sistemico(self, status_pre_selecao, status_selecao):
        """
        Verifica status exibido na listagem de projetos se gerente sistêmico
        """
        url = '/admin/projetos/projeto/'
        self.verificar_perfil_contains(url, text=status_pre_selecao, perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO])

        self.verificar_perfil_contains(url, text=status_selecao, perfis_corretos=[GRUPO_EXTENSAO_GERENTE_SISTEMICO])

    def status_projetos_listagem_admin_pre_avaliador(self, status_pre_selecao, status_selecao):
        url = '/admin/projetos/projeto/'
        self.verificar_perfil_contains(url, text=status_pre_selecao, perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR])

        self.verificar_perfil_contains(url, text=status_selecao, perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR])

    def test_status_listagem_meus_projetos(self):
        """
        Testa os status Pré-selecionado e Selecionado em todas as fases do edital
        exibido na listagem de projetos disponível para coodenador do projeto
        """
        # Não houve seleção de pré-selecionados e selecionado
        self.login()
        projeto = self.get_projeto()
        self.set_data_inicio_inscricao(projeto.edital)
        self.status_listagem_meus_projetos(Projeto.STATUS_AGUARDADO_ENVIO_PROJETO, Projeto.STATUS_AGUARDADO_ENVIO_PROJETO)

        self.set_data_pos_fim_inscricoes(projeto.edital)
        self.status_listagem_meus_projetos(Projeto.STATUS_NAO_ENVIADO, Projeto.STATUS_NAO_ENVIADO)

        self.set_data_inicio_pre_selecao(projeto.edital)
        self.status_listagem_meus_projetos(Projeto.STATUS_NAO_ENVIADO, Projeto.STATUS_NAO_ENVIADO)

        self.set_data_inicio_selecao(projeto.edital)
        self.status_listagem_meus_projetos(Projeto.STATUS_NAO_ENVIADO, Projeto.STATUS_NAO_ENVIADO)

        self.set_data_divulgacao_selecao(projeto.edital)
        self.status_listagem_meus_projetos(Projeto.STATUS_NAO_ENVIADO, Projeto.STATUS_NAO_ENVIADO)

        hoje_str = self.get_str_date()

        self.submeter_projeto_para_edital(projeto)

        # Houve seleção de pré-selecionados e selecionado, ambos foram aceitos
        self.pre_aprovar_projeto(projeto)
        self.status_listagem_meus_projetos('{} {}'.format(Projeto.STATUS_PRE_SELECIONADO_EM, hoje_str), Projeto.STATUS_AGUARDANDO_AVALIACAO)

        self.aprovar_projeto(projeto)
        self.status_listagem_meus_projetos('{} {}'.format(Projeto.STATUS_PRE_SELECIONADO_EM, hoje_str), Projeto.STATUS_AGUARDANDO_AVALIACAO)

        self.set_data_divulgacao_selecao(projeto.edital)
        self.status_listagem_meus_projetos('{} {}'.format(Projeto.STATUS_PRE_SELECIONADO_EM, hoje_str), '{} {}'.format(Projeto.STATUS_SELECIONADO_EM, hoje_str))

        # Houve seleção de pré-selecionados e selecionado, ambos não foram aceitos
        self.pre_reprovar_projeto(projeto)
        self.reprovar_projeto(projeto)
        self.login()
        self.set_data_divulgacao_selecao(projeto.edital)
        self.status_listagem_meus_projetos('{} {}'.format(Projeto.STATUS_NAO_SELECIONADO_EM, hoje_str), '{} {}'.format(Projeto.STATUS_NAO_SELECIONADO_EM, hoje_str))

    def status_listagem_meus_projetos(self, status_pre_selecao, status_selecao):
        """
        Verifica status exibido na listagem de projetos se gerente sistêmico
        """
        url = '/projetos/meus_projetos/'
        self.verificar_perfil_contains(
            url, text=status_pre_selecao, perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR], error_status_code=403
        )

        self.verificar_perfil_contains(
            url, text=status_selecao, perfis_corretos=[GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR, GRUPO_COORDENADOR_PROJETO], error_status_code=403
        )

    def test_status_visualizar_projetos(self):
        """
        Testa os status Pré-selecionado e Selecionado em todas as fases do edital
        exibido na listagem de projetos disponível para coodenador do projeto
        """
        # Não houve seleção de pré-selecionados e selecionado
        self.login()
        projeto = self.get_projeto()
        url = '/projetos/projeto/%d/' % projeto.id

        self.set_data_inicio_inscricao(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_INSCRICAO, Projeto.STATUS_EM_INSCRICAO)

        self.submeter_projeto_para_edital(projeto)

        self.set_data_pos_fim_inscricoes(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_FIM_INSCRICAO, Projeto.STATUS_INSCRITO)

        self.set_data_inicio_pre_selecao(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_PRE_SELECAO, Projeto.STATUS_INSCRITO)

        self.set_data_inicio_selecao(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_SELECAO, Projeto.STATUS_AGUARDANDO_AVALIACAO)

        self.set_data_divulgacao_selecao(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_ENCERRADO, Projeto.STATUS_INSCRITO)

        # Houve seleção de pré-selecionados e selecionado, ambos foram aceitos
        self.pre_aprovar_projeto(projeto)
        self.status_visualizar_projetos(url, Projeto.PERIODO_PRE_SELECAO, Projeto.STATUS_PRE_SELECIONADO)

        self.aprovar_projeto(projeto)
        self.status_visualizar_projetos(url, Projeto.PERIODO_SELECAO, Projeto.STATUS_EM_SELECAO)

        self.set_data_divulgacao_selecao(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_EXECUCAO, Projeto.STATUS_EM_EXECUCAO)

        # Houve seleção de pré-selecionados e selecionado, ambos não foram aceitos
        self.pre_reprovar_projeto(projeto)
        self.set_data_divulgacao_selecao(projeto.edital)
        self.status_visualizar_projetos(url, Projeto.PERIODO_ENCERRADO, Projeto.STATUS_NAO_ACEITO)

    def status_visualizar_projetos(self, url, status_periodo_edital, status_situacao_projeto):
        """
        Verifica status exibido na listagem de projetos se gerente sistêmico
        """
        self.verificar_perfil_contains(
            url, text=status_periodo_edital, perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR, GRUPO_EXTENSAO_GERENTE_SISTEMICO]
        )

        self.verificar_perfil_contains(url, text=status_situacao_projeto, perfis_corretos=[GRUPO_COORDENADOR_PROJETO, GRUPO_EXTENSAO_PRE_AVALIADOR, GRUPO_EXTENSAO_AVALIADOR])
