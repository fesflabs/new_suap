# -*- coding: utf-8 -*-
from django.conf import settings

from cnpq.xml_parsers import CurriculoVittaeLattesParser
from comum.tests import SuapTestCase
from rh.models import PessoaFisica, Servidor, Situacao, JornadaTrabalho, CargoEmprego, Setor


class CnpqTestCase(SuapTestCase):
    def setUp(self):
        super(CnpqTestCase, self).setUp()
        self.client.login(username=self.servidor_a.user.username, password='123')
        self.criar_servidor_cnpq()

    def criar_servidor_cnpq(self):
        setor_a1_suap = Setor.todos.get(sigla='A1', nome='A1', codigo=None)
        setor_a1_siape = Setor.todos.get(sigla='A1', nome='A1', codigo='A1')
        situacao = Situacao.objects.get(codigo=Situacao.ATIVO_PERMANENTE)
        jornada = JornadaTrabalho.objects.get_or_create(codigo='01', nome='40h', excluido=False)[0]
        cargo = CargoEmprego.objects.get(codigo='01')
        kwargs_servidor_a = dict(
            nome='Servidor 1',
            template=b'1',
            excluido=False,
            situacao=situacao,
            cargo_emprego=cargo,
            setor=setor_a1_suap,
            setor_lotacao=setor_a1_siape,
            setor_exercicio=setor_a1_siape,
            email='servidor.aleatorio@mail.gov',
            cpf='707.651.200-97',
            jornada_trabalho=jornada,
        )
        self.servidor_cnpq = Servidor.objects.get_or_create(matricula='12121212', defaults=kwargs_servidor_a)[0]

    def cnpq_importar(self):
        file = settings.BASE_DIR + '/cnpq/tests_files/curriculo.xml'
        with open(file, encoding='latin-1') as f:
            curriculo_str = f.read()
        curriculo_lattes = CurriculoVittaeLattesParser(curriculo_str, '', '')
        self.servidor_a.pessoafisica = PessoaFisica.objects.get(id=self.servidor_a.pessoafisica.id)
        self.assertTrue(curriculo_lattes.parse(self.servidor_cnpq))

    def test_visualizar_curriculo(self):
        # Visualização do Currículo
        self.cnpq_importar()
        url = '/cnpq/curriculo/%d/' % self.servidor_cnpq.id
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'Professor de Sistemas de Informação do IFRN, Doutor em Engenharia Elétrica e da Computação pela UFRN, Tecnólogo em Desenvolvimento de Software pelo IFRN'
        )

    def test_visualizar_indicadores(self):
        self.cnpq_importar()
