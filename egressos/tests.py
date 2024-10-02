# -*- coding: utf-8 -*-


import datetime
from django.contrib.auth.models import Group

# Create your tests here.
from comum.models import Ano
from djtools.templatetags.filters import format_
from edu.models import SituacaoMatricula, Aluno, CursoCampus, MatriculaPeriodo, SituacaoMatriculaPeriodo
from edu.tests import EduTestCase
from egressos.models import Pesquisa, Categoria, Pergunta, Opcao
from rh.models import PessoaFisica


class EgressosTestCase(EduTestCase):
    def setUp(self):
        super(EgressosTestCase, self).setUp()
        # cadastro de gerente de extensão
        self.servidor_a.user.groups.add(Group.objects.get(name='Gerente Sistêmico de Extensão'))

        # cadastro de aluno
        pessoa_fisica = PessoaFisica(username='20131', nome='Carlos Breno Pereira Silva', email_secundario='email@email.com', cpf='359.221.769-00')
        pessoa_fisica.save()
        ano_letivo = Ano.objects.get_or_create(ano='2013')[0]
        situacao = SituacaoMatricula.objects.get(codigo_academico=SituacaoMatricula.CONCLUIDO)
        curso_campus = CursoCampus.objects.all()[0]
        self.aluno = Aluno.objects.create(
            matricula='20131',
            pessoa_fisica=pessoa_fisica,
            ano_letivo=ano_letivo,
            periodo_letivo=1,
            situacao=situacao,
            dt_conclusao_curso=datetime.datetime.now(),
            ano_conclusao=datetime.datetime.now().year,
            curso_campus=curso_campus,
        )
        self.aluno.pessoa_fisica.user.set_password('123')
        self.aluno.pessoa_fisica.user.save()
        matricula_periodo = MatriculaPeriodo(
            aluno=self.aluno, ano_letivo=ano_letivo, periodo_letivo=1, situacao=SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.PERIODO_FECHADO)
        )
        matricula_periodo.save()

    def test_cadastrar_pesquisa(self):
        self.client.login(username=self.servidor_a.user.username, password='123')
        count = Pesquisa.objects.count()
        url = '/admin/egressos/pesquisa/add/'
        self.client.get(url)
        response = self.client.get(url)
        data = dict(
            titulo='Pesquisa Teste',
            descricao='Descrição Pesquisa Teste',
            conclusao=[Ano.objects.get(ano=datetime.datetime.now().year).pk],
            modalidade=self.aluno.curso_campus.modalidade.pk,
        )
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(Pesquisa.objects.count(), count + 1)

        pesquisa = Pesquisa.objects.all()[0]
        url = '/egressos/pesquisa/{}/'.format(pesquisa.pk)
        response = self.client.get(url)
        self.assertContains(response, 'Pesquisa Teste', status_code=200)
        count = Categoria.objects.count()
        url = '/egressos/cadastrar_categoria/{}/'.format(pesquisa.pk)
        data = dict(titulo='Categoria 1', ordem=1)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(Categoria.objects.count(), count + 1)

        categoria = Categoria.objects.all()[0]
        count = Pergunta.objects.count()
        url = '/egressos/cadastrar_pergunta/{}/'.format(categoria.pk)
        data = dict(conteudo='Como você avalia seu curso?', categoria=categoria.pk, tipo=Pergunta.OBJETIVA_RESPOSTA_UNICA, preenchimento_obrigatorio=True)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(Pergunta.objects.count(), count + 1)

        pergunta = Pergunta.objects.all()[0]
        count = Opcao.objects.count()
        url = '/egressos/cadastrar_opcao/{}/'.format(pergunta.pk)
        data = dict(conteudo='Ótimo', direcionamento_categoria=[])
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(Opcao.objects.count(), count + 1)

        url = '/egressos/publicar_pesquisa/{}/'.format(pesquisa.pk)
        data = dict(inicio=format_(datetime.date.today()), fim=format_(datetime.date.today()))
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'A pesquisa foi publicada e foram enviados os convites', status_code=200)
        url = '/egressos/clonar_pesquisa/{}/'.format(pesquisa.pk)
        data = dict(titulo='Pesquisa Clone', descricao='Clone da Pesquisa Teste')
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Pesquisa clonada com sucesso.', status_code=200)
        self.logout()

        self.client.login(username=self.aluno.pessoa_fisica.user.username, password='123')
        url = '/'
        response = self.client.get(url)
        self.assertContains(response, 'Responda Pesquisa de Acompanhamento de Ex-Aluno', status_code=200)

        url = '/egressos/responder_pesquisa_egressos/atualizacao_cadastral/{}/'.format(pesquisa.pk)
        response = self.client.get(url)
        self.assertContains(response, 'Atualização Cadastral do Egresso', status_code=200)
        data = dict(
            estado_civil='Solteiro',
            numero_dependentes='0',
            email_pessoal='meuemail@provedor.com',
            logradouro='Rua dos Passaros',
            numero='1',
            complemento='',
            cep='59001-001',
            bairro='Lagoa Nova',
            tipo_zona_residencial=Aluno.TIPO_ZONA_RESIDENCIAL_CHOICES[0][0],
            telefone_principal='84 99911-1111',
            telefone_secundario='84 99922-2222',
            facebook='',
            instagram='',
            twitter='',
            linkedin='',
            skype='',
            logradouro_profissional='',
            numero_profissional='',
            complemento_profissional='',
            cep_profissional='',
            bairro_profissional='',
            tipo_zona_residencial_profissional='',
        )
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Atualização cadastral realizada com sucesso.', status_code=200)
        pergunta_id = 'pergunta_{}'.format(pergunta.pk)
        data = {pergunta_id: pergunta.opcao_set.all()[0].pk}
        url = '/egressos/responder_pesquisa_egressos/bloco/{}/{}/'.format(pesquisa.pk, categoria.pk)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Obrigado por responder esta pesquisa.', status_code=200)
