# -*- coding: utf-8 -*-
import datetime

from django.apps import apps
from django.contrib.auth.models import Group

from ae.models import Programa, InscricaoAlimentacao, InscricaoPasseEstudantil, OfertaAlimentacao, TipoPrograma

from comum.models import Ano
from comum.tests import SuapTestCase
from edu.models import Aluno, SituacaoMatricula, NivelEnsino
from rh.models import PessoaFisica

Permission = apps.get_model('auth', 'permission')
User = apps.get_model('comum', 'user')


class AtividadeEstudantilTestCase(SuapTestCase):
    def setUp(self):
        super(AtividadeEstudantilTestCase, self).setUp()

        self.servidor_a.user.groups.add(Group.objects.get(name='Assistente Social'))
        self.servidor_a.user.groups.add(Group.objects.get(name='Administrador Acadêmico'))
        self.servidor_a.user.save()
        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        self.tipo_ali = TipoPrograma.objects.get_or_create(titulo='Programa de Alimentação', descricao='Programa de Alimentação', sigla=Programa.TIPO_ALIMENTACAO)[0]
        self.tipo_trans = TipoPrograma.objects.get_or_create(titulo='Programa de  Auxílio Transporte', descricao='Programa de  Auxílio Transporte', sigla=Programa.TIPO_TRANSPORTE)[
            0
        ]
        self.tipo_trab = TipoPrograma.objects.get_or_create(
            titulo='Programa de Iniciação ao Trabalho', descricao='Programa de Iniciação ao Trabalho', sigla=Programa.TIPO_TRABALHO
        )[0]
        self.tipo_idioma = TipoPrograma.objects.get_or_create(titulo='Programa de Cursos de Idiomas', descricao='Programa de Cursos de Idiomas', sigla=Programa.TIPO_IDIOMA)[0]

        self.programa_alm = Programa.objects.get_or_create(tipo_programa=self.tipo_ali, descricao=' Programa de Alimentação (Campus X)', instituicao=self.setor_a0_suap.uo)[0]
        self.programa_pas = Programa.objects.get_or_create(
            tipo_programa=self.tipo_trans, descricao=' Programa de  Auxílio Transporte (Campus X)', instituicao=self.setor_a0_suap.uo
        )[0]
        self.programa_trb = Programa.objects.get_or_create(
            tipo_programa=self.tipo_trab, descricao=' Programa de Iniciação ao Trabalho (Campus X)', instituicao=self.setor_a0_suap.uo
        )[0]
        self.programa_idm = Programa.objects.get_or_create(
            tipo_programa=self.tipo_idioma, descricao=' Programa de Cursos de Idiomas (Campus X)', instituicao=self.setor_a0_suap.uo
        )[0]

        self.nivel_ensino = NivelEnsino.objects.get_or_create(descricao='Superior')[0]

    def test_cadastro_ofertaalimentacao(self):
        oferta = OfertaAlimentacao.objects.create(campus=self.setor_a0_suap.uo)
        url = '/admin/ae/ofertaalimentacao/{:d}/'.format(oferta.pk)
        self.client.get(url)
        # self.assertContains(response, 'Oferta', status_code=200)
        count = OfertaAlimentacao.objects.all().count()
        input = dict(
            campus=self.setor_a0_suap.uo.pk,
            valor_refeicao='5',
            cafe_seg='0',
            cafe_ter='0',
            cafe_qua='0',
            cafe_qui='0',
            cafe_sex='0',
            almoco_seg='10',
            almoco_ter='10',
            almoco_qua='10',
            almoco_qui='10',
            almoco_sex='10',
            janta_seg='0',
            janta_ter='0',
            janta_qua='0',
            janta_qui='0',
            janta_sex='0',
        )
        self.client.post(url, input)
        self.assertEqual(count, 1)

    def test_cadastrar_aluno(self):
        pessoa_fisica = PessoaFisica.objects.get_or_create(nome='Carlos Breno Pereira Silva', defaults={'cpf': '359.221.769-00'})[0]
        ano_letivo = Ano.objects.get_or_create(ano='2013')[0]
        situacao = SituacaoMatricula.objects.get_or_create(descricao='Matriculado', ativo=True)[0]
        count = Aluno.objects.all().count()
        Aluno.objects.create(pessoa_fisica=pessoa_fisica, ano_letivo=ano_letivo, periodo_letivo=1, situacao=situacao, ano_let_prev_conclusao=datetime.datetime.now().year)
        self.assertEqual(Aluno.objects.all().count(), count + 1)

    def get_url_from_response(self, response):
        url = str(response)[(str(response).find('Location: ') + 10):]
        url = url.replace('http://testserver', '').replace(' ', '').replace('\n', '')
        print((url.strip()))
        return url.strip()

    def inscricao_alm(self):
        self.test_cadastrar_aluno()
        aluno = Aluno.objects.all()[0]
        count = InscricaoAlimentacao.objects.count()

        url = '/ae/inscricao_identificacao/'
        response = self.client.get(url)
        self.assertContains(response, 'Efetuar Inscrição em Programa', status_code=200)
        input = dict(aluno=aluno.pk, programa=self.programa_alm.pk, justificativa='Possuo baixa renda familiar')
        response = self.client.post(url, input)
        url = self.get_url_from_response(response)
        response = self.client.get(url)
        self.assertContains(response, 'Informe as refeições que você deseja obter', status_code=200)
        input = dict(seg_almoco='on', ter_almoco='on')
        response = self.client.post(url, input)
        url = '/ae/inscricao_confirmacao/ALM/{:d}/'.format(InscricaoAlimentacao.objects.all()[0].pk)
        response = self.client.get(url)
        self.assertContains(response, 'Inscrição realizada com sucesso.', status_code=200)
        self.assertEqual(InscricaoAlimentacao.objects.all().count(), count + 1)

    def inscricao_pas(self):
        self.test_cadastrar_aluno()
        aluno = Aluno.objects.all()[0]
        count = InscricaoPasseEstudantil.objects.count()

        url = '/ae/inscricao_identificacao/'
        response = self.client.get(url)
        self.assertContains(response, 'Inscrição em Programa Social', status_code=200)
        input = dict(aluno=aluno.pk, programa=self.programa_pas.pk, justificativa='Possuo baixa renda familiar')
        response = self.client.post(url, input)

        url = '/ae/inscricao_detalhamento/PAS/eyJqdXN0aWZpY2F0aXZhIjogIlBvc3N1byBiYWl4YSByZW5kYSBmYW1pbGlhciIsICJwcm9ncmFtYV9pZCI6IDE0LCAiYWx1bm9faWQiOiAzfQequalsequals/'
        response = self.client.get(url)

        self.assertContains(response, 'Infome o tipo do passe estudantil desejado.', status_code=200)
        input = dict(tipo_passe='MUN')
        response = self.client.post(url, input)
        url = '/ae/inscricao_confirmacao/PAS/{:d}/'.format(InscricaoPasseEstudantil.objects.all()[0].pk)
        response = self.client.get(url)
        self.assertContains(response, 'Inscrição realizada com sucesso.', status_code=200)
        self.assertEqual(InscricaoPasseEstudantil.objects.all().count(), count + 1)

    def _test_gerenciar_inscricao(self):
        self.inscricao_alm()
        inscricao = InscricaoAlimentacao.objects.all()[0]

        url = '/ae/inscricoes_programa/{:d}/'.format(self.programa_alm.pk)
        count = InscricaoAlimentacao.objects.filter(aluno__documentada=True).count()
        response = self.client.get(url)
        self.assertContains(response, 'Ação', status_code=200)
        input = dict(acao='2', inscricao_id=str(inscricao.pk))
        response = self.client.post(url, input)
        self.assertEqual(InscricaoAlimentacao.objects.filter(aluno__documentada=True).count(), count + 1)

        url = '/ae/inscricoes_programa/{:d}/'.format(self.programa_alm.pk)
        count = InscricaoAlimentacao.objects.filter(prioritaria=True).count()
        response = self.client.get(url)
        self.assertContains(response, 'Ação', status_code=200)
        input = dict(acao='1', inscricao_id=str(inscricao.pk))
        response = self.client.post(url, input)
        self.assertEqual(InscricaoAlimentacao.objects.filter(prioritaria=True).count(), count + 1)

    def _test_gerenciar_participacao(self):
        self.inscricao_alm()
        self.test_cadastro_ofertaalimentacao()
        inscricao = InscricaoAlimentacao.objects.all()[0]
        url = '/ae/gerenciar_participacao/{:d}/'.format(inscricao.programa.pk)
        input = dict(form_id='1')
        response = self.client.get(url, input)
        self.assertContains(response, 'Carlos Breno Pereira Silva', status_code=200)
        input = dict(inscricao_incluir=str(inscricao.pk), almoco_seg='on')
        response = self.client.post(url, input)
        self.assertContains(response, 'A inclusão no programa só poderá ser realizada caso a documentação tenha sido entregue', status_code=200)
        inscricao.aluno.documentada = True
        inscricao.save()
        response = self.client.post(url, input)
        self.assertContains(response, 'Inclusão no programa realizada com sucesso', status_code=200)
