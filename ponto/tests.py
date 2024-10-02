from comum.tests import SuapTestCase
from djtools.utils import prevent_logging_errors
from datetime import date, timedelta, datetime
from django.test.client import Client
from ponto.models import Frequencia, Maquina
from rh.models import Servidor
import xmlrpc.client
from django.apps import apps

Funcionario = apps.get_model('rh', 'funcionario')
User = apps.get_model('comum', 'user')
Permission = apps.get_model('auth', 'permission')
Observacao = apps.get_model('ponto', 'observacao')


def get_xmlrpc_response(url, data):
    c = Client()
    data = xmlrpc.client.dumps(data, url)
    response = c.post('/webservice/', {'body': data}, REMOTE_ADDR='127.0.0.1')
    return xmlrpc.client.loads(response.content)[0][0]


class TestTerminalPonto(SuapTestCase):
    def testGetDadosPessoa(self):
        servidor = Servidor.objects.get(matricula='1111111')

        # Máquina sem permissão
        response = get_xmlrpc_response('get_dados_pessoa', (servidor.matricula,))
        self.assertEqual(response.get('ok'), False)

        # Máquina com permissão
        Maquina.objects.create(ip='127.0.0.1', cliente_ponto=True, ativo=True, descricao='Localhost')
        response = get_xmlrpc_response('get_dados_pessoa', (servidor.matricula,))
        self.assertEqual(response.get('ok'), True)
        self.assertEqual(response.get('pessoa_id'), servidor.pk)

    def testRegistroHorario(self):
        """
        Simula registro de frequencia por um servidor - Entrada e Saída
        Tela de funcionários só é usada para servidores. Terceirizados usam outra tela de frequência.
        """
        self.servidor_a.user.user_permissions.add(Permission.objects.get(codename='pode_ver_frequencia_propria'))

        Maquina.objects.create(ip='127.0.0.1', cliente_ponto=True, ativo=True, descricao='Localhost')
        # Registro as frequências de entrada e saída do servidor
        response = get_xmlrpc_response(
            'registrar_frequencias_offline', ('{funcionario_id};2009-01-01 8:01:20|{funcionario_id};2009-01-01 8:05:59'.format(funcionario_id=self.servidor_a.user.username),)
        )
        self.assertEqual(response.get('ok'), True)
        # Criação das datas para submeter ao formulário
        faixa_0 = date(2009, 1, 1)
        faixa_1 = faixa_0 + timedelta(10)
        faixa_1_form = faixa_1.strftime("%d/%m/%Y")
        faixa_0_form = faixa_0.strftime("%d/%m/%Y")
        c = Client()
        c.login(username=self.servidor_a.user.username, password='123')
        # Submissão do formulário
        response = c.get('/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.servidor_a.pk, 'faixa_0': faixa_0_form, 'faixa_1': faixa_1_form})
        # Verificação se as strings referentes aos registros de frequência
        # estão no objeto response

        self.assertEqual('08:01:20' in response.content.decode(), True)
        self.assertEqual('08:05:59' in response.content.decode(), True)

    def testRegistrarFrequenciaOffline(self):
        # Registrando frequência com horário fora do formato e com uma matrícula inexistente
        response = get_xmlrpc_response('registrar_frequencias_offline', ('1111111;2009-01-01-8:01:20|99;2009-01-01 8:01:20',))
        self.assertEqual(response.get('ok'), False)
        self.assertEqual(Frequencia.objects.count(), 0)

        # Registrando frequêcia com horário correto
        # Máquina sem permissão
        response = get_xmlrpc_response('registrar_frequencias_offline', ('1111111;2009-01-01 8:01:20',))
        self.assertEqual(response.get('ok'), False)
        self.assertEqual(Frequencia.objects.count(), 0)

        # Máquina com permissão
        Maquina.objects.create(ip='127.0.0.1', cliente_ponto=True, ativo=True, descricao='Localhost')
        response = get_xmlrpc_response('registrar_frequencias_offline', ('1111111;2009-01-01 8:01:20',))
        self.assertEqual(response.get('ok'), True)
        self.assertEqual(Frequencia.objects.count(), 1)
        self.assertEqual(Frequencia.objects.order_by('id')[0].horario, datetime(2009, 1, 1, 8, 1, 20))
        self.assertEqual(Frequencia.objects.order_by('id')[0].acao, 'E')

        response = get_xmlrpc_response('registrar_frequencias_offline', ('1111111;2009-01-01 8:05:59',))
        self.assertEqual(response.get('ok'), True)
        self.assertEqual(Frequencia.objects.count(), 2)
        self.assertEqual(Frequencia.objects.order_by('id')[1].horario, datetime(2009, 1, 1, 8, 5, 59))
        self.assertEqual(Frequencia.objects.order_by('id')[1].acao, 'S')


class TestPonto(SuapTestCase):
    def setUp(self):
        """
        Popula o banco de testes
        """
        super().setUp()

        # Criação de datas para o campo Faixa do formulário
        self.faixa_1 = date.today()
        self.faixa_0 = self.faixa_1 - timedelta(10)
        self.faixa_1_form = self.faixa_1.strftime("%d/%m/%Y")
        self.faixa_0_form = self.faixa_0.strftime("%d/%m/%Y")

        # Criação das permissões para ver frequências
        self.permission_a = Permission.objects.get(codename='pode_ver_frequencia_propria')
        # Todas as próximas permissões, ao serem atribuídas, devem ser acompanhadas pela
        # permissão `pode_ver_frequencia_propria` para permitir o comportamento correto
        # da view `frequencia_funcionario`
        self.permission_b = Permission.objects.get(codename='pode_ver_frequencias_enquanto_foi_chefe')
        self.permission_c = Permission.objects.get(codename='pode_ver_frequencia_campus')
        self.permission_d = Permission.objects.get(codename='pode_ver_frequencia_todos')

        # Criação de funcionários de teste
        self.funcionario_d_1 = Servidor.objects.get_or_create(
            matricula='9991', nome='Funcionario D_1 do setor B1', setor=self.setor_b1_suap, template=b'5', situacao=self.situacao_ativo_permanente, cpf="315.316.533-59"
        )[0]
        self.funcionario_d_1.user.user_permissions.add(self.permission_a)
        self.funcionario_d_1.user.user_permissions.add(self.permission_b)
        self.funcionario_d_1.user.set_password('123')
        self.funcionario_d_1.user.email = '4@mail.com'
        self.funcionario_d_1.user.save()
        self.funcionario_d_1.save()
        self.user_d_1 = self.funcionario_d_1.user

        self.funcionario_d_2 = Servidor.objects.get_or_create(
            matricula='9992', nome='Funcionario D_2 do setor B1', setor=self.setor_b1_suap, template=b'6', situacao=self.situacao_ativo_permanente, cpf="498.681.821-07"
        )[0]
        self.funcionario_d_2.user.user_permissions.add(self.permission_a)
        self.funcionario_d_2.user.user_permissions.add(self.permission_b)
        self.funcionario_d_2.user.set_password('123')
        self.funcionario_d_2.user.email = '13@email.com'
        self.funcionario_d_2.user.save()
        self.funcionario_d_2.save()
        self.user_d_2 = self.funcionario_d_2.user

        self.funcionario_e_1 = Servidor.objects.get_or_create(
            matricula='9993', nome='Funcionario E_1 do setor B0', setor=self.setor_b0_suap, template=b'7', situacao=self.situacao_ativo_permanente, cpf="464.953.810-69"
        )[0]
        self.funcionario_e_1.user.user_permissions.add(self.permission_a)
        self.funcionario_e_1.user.user_permissions.add(self.permission_b)
        self.funcionario_e_1.user.set_password('123')
        self.funcionario_e_1.user.email = '6@email.com'
        self.funcionario_e_1.user.save()
        self.funcionario_e_1.save()
        self.user_e_1 = self.funcionario_e_1.user

        self.funcionario_e_2 = Servidor.objects.get_or_create(
            nome='Funcionario E_2 do setor B0', setor=self.setor_b0_suap, template=b'8', matricula='1111', situacao=self.situacao_ativo_permanente, cpf="312.643.426-67"
        )[0]
        self.funcionario_e_2.user.user_permissions.add(self.permission_a)
        self.funcionario_e_2.user.user_permissions.add(self.permission_b)
        self.funcionario_e_2.user.set_password('123')
        self.funcionario_e_2.user.save()
        self.funcionario_e_2.save()
        self.user_e_2 = self.funcionario_e_2.user

        self.funcionario_e_3 = Servidor.objects.get_or_create(
            nome='Funcionario E_3 do setor B1', setor=self.setor_b1_suap, template=b'9', matricula='1112', situacao=self.situacao_ativo_permanente, cpf='378.134.839-36'
        )[0]
        self.user_e_3 = self.funcionario_e_3.user

        self.funcionario_f_0 = Servidor.objects.get_or_create(
            nome='Funcionario F_0 do setor A0',
            setor=self.setor_a0_suap,
            excluido=False,
            template=b'10',
            matricula='1113',
            situacao=self.situacao_ativo_permanente,
            cpf="717.482.546-00",
        )[0]
        self.funcionario_f_0.user.user_permissions.add(self.permission_a)
        self.funcionario_f_0.user.user_permissions.add(self.permission_c)
        self.funcionario_f_0.user.set_password('123')
        self.funcionario_f_0.user.save()
        self.funcionario_f_0.save()
        self.user_f_0 = self.funcionario_f_0.user

        self.funcionario_h_0 = Servidor.objects.get_or_create(
            nome='Funcionario H_0 do setor A0',
            setor=self.setor_a0_suap,
            excluido=False,
            template=b'11',
            matricula='1114',
            situacao=self.situacao_ativo_permanente,
            cpf='673.221.568-03',
        )[0]
        self.funcionario_h_0.user.user_permissions.add(self.permission_a)
        self.funcionario_h_0.user.set_password('123')
        self.funcionario_h_0.user.save()
        self.funcionario_h_0.cpf = "738.133.155-17"
        self.funcionario_h_0.save()
        self.user_h_0 = self.funcionario_h_0.user

        self.funcionario_g_1 = Servidor.objects.get_or_create(
            nome='Funcionario G_1 do setor A1',
            setor=self.setor_a1_suap,
            excluido=False,
            template=b'12',
            matricula='1115',
            situacao=self.situacao_ativo_permanente,
            cpf="136.564.170-83",
        )[0]
        self.funcionario_g_1.user.user_permissions.add(self.permission_a)
        self.funcionario_g_1.user.user_permissions.add(self.permission_c)
        self.funcionario_g_1.user.set_password('123')
        self.funcionario_g_1.user.save()
        self.funcionario_g_1.cpf = "282.273.674-02"
        self.funcionario_g_1.save()
        self.user_g_1 = self.funcionario_g_1.user

        self.funcionario_g_2 = Servidor.objects.get_or_create(
            nome='Funcionário G_2 do setor',
            setor=self.setor_b1_suap,
            excluido=False,
            template=b'13',
            situacao=self.situacao_ativo_permanente,
            matricula='1116',
            cpf="420.233.695-09",
        )[0]
        self.funcionario_g_2.user.user_permissions.add(self.permission_a)
        self.funcionario_g_2.user.user_permissions.add(self.permission_d)
        self.funcionario_g_2.user.set_password('123')
        self.funcionario_g_2.user.save()
        self.funcionario_g_2.save()
        self.user_g_2 = self.funcionario_g_2.user

    @prevent_logging_errors()
    def test_ver_frequencia_pessoa(self):
        """
        Trata a permissão `pode_ver_frequencia_propria`
        - Testa se a pessoa pode ver sua própria frequência
        - Testa se a pessoa não pode ver frequência de outra pessoa
        """
        c = Client()
        c.login(username=self.user_d_1.username, password='123')

        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_d_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )

        # Verifica se tem acesso a sua própria frequência
        self.assertEqual(response.status_code, 200)
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_d_2.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )

        # Verifica se tem acesso à frequência de outra pessoa
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            form_errors = formulario.errors
            self.assertFalse(len(form_errors) == 0)

        c.logout()
        c.login(username=self.user_e_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver sua própria frequência:
        # Se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        c.logout()
        c.login(username=self.user_g_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_g_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver sua própria frequência:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        c.logout()
        c.login(username=self.user_g_2.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_g_2.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver sua própria frequência:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

    @prevent_logging_errors()
    def test_adicionar_observacao(self):
        """
        Assegura que a observação de uma pessoa só pode ser cadastrada pela própria
        """
        c = Client()
        c.login(username=self.user_e_1.username, password='123')

        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_d_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se tem acesso às frequências de outra pessoa:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)
        # Verifica se aparece botao para adicionar observacao
        self.assertFalse(str('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y")) in response.content.decode())

        c.logout()
        c.login(username=self.user_g_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_f_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se tem acesso às frequências de outra pessoa:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)
        # Verifica se aparece botao para adicionar observacao
        self.assertFalse(str('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y")) in response.content.decode())

        c.logout()
        c.login(username=self.user_e_2.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_d_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se tem acesso às frequências de outra pessoa:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)
        # Verifica se aparece botao para adicionar observacao
        self.assertFalse(str('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y")) in response.content.decode())

        # Tenta cadastrar uma observação para si próprio
        response = c.post('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y"), {'descricao': 'Não havia energia no prédio.'})
        # Testa se não houve erro no servidor
        self.assertNotEqual(response.status_code, 500)
        # Recupera a última observação cadastrada
        qtd = Observacao.objects.count()
        index_obs = qtd - 1
        obs = Observacao.objects.all()[index_obs]
        # Verifica se a observação cadastrada se refere ao usuário autenticado
        self.assertEqual(obs.vinculo.pessoa.pk, self.funcionario_e_2.pk)

        c.logout()
        c.login(username=self.user_g_1.username, password='123')
        # Tenta cadastrar uma observação para si próprio
        response = c.post('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y"), {'descricao': 'Não havia energia no prédio.'})
        # Testa se não houve erro no servidor
        self.assertNotEqual(response.status_code, 500)
        # Recupera a última observação cadastrada
        qtd = Observacao.objects.count()
        index_obs = qtd - 1
        obs = Observacao.objects.all()[index_obs]
        # Verifica se a observação cadastrada se refere ao usuário autenticado
        self.assertEqual(obs.vinculo.pessoa.pk, self.funcionario_g_1.pk)

        c.logout()
        c.login(username=self.user_e_1.username, password='123')
        # Tenta cadastrar uma observação para si próprio
        response = c.post('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y"), {'descricao': 'Não havia energia no prédio.'})
        # Testa se não houve erro no servidor
        self.assertNotEqual(response.status_code, 500)
        # Recupera a última observação cadastrada
        qtd = Observacao.objects.count()
        index_obs = qtd - 1
        obs = Observacao.objects.all()[index_obs]
        # Verifica se a observação cadastrada se refere ao usuário autenticado
        self.assertEqual(obs.vinculo.pessoa.pk, self.funcionario_e_1.pk)

        c.logout()
        c.login(username=self.user_d_1.username, password='123')
        # Tenta cadastrar uma observação para si próprio
        response = c.post('/ponto/observacao_adicionar/%s/' % self.faixa_0.strftime("%d%m%Y"), {'descricao': 'Não havia energia no prédio.'})
        # Testa se não houve erro no servidor
        self.assertNotEqual(response.status_code, 500)
        # Recupera a última observação cadastrada
        qtd = Observacao.objects.count()
        index_obs = qtd - 1
        obs = Observacao.objects.all()[index_obs]
        # Verifica se a observação cadastrada se refere ao usuário autenticado
        self.assertEqual(obs.vinculo.pessoa.pk, self.funcionario_d_1.pk)

    @prevent_logging_errors()
    def test_ver_frequencia_setor(self):
        """
        Trata a permissão `pode_ver_frequencia_setor`
        - Pessoa com permissão
            - Testa se pode ver frequência de outra do mesmo setor ou descendente
            - Testa se não pode ver frequência de outra pessoa de outro setor e não descendente
        - Pessoa sem permissão
            - Testar que não pode ver nada
        """
        c = Client()
        c.login(username=self.user_e_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_2.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver frequência de outra pessoa do mesmo setor:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_3.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver frequência de outra pessoa de setor descendente:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        c.logout()
        c.login(username=self.user_f_0.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_h_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver frequência de outra pessoa do mesmo setor:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_g_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver frequência de outra pessoa de setor descendente:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        c.logout()
        c.login(username=self.user_e_2.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica pode ver frequência de outra pessoa do mesmo setor:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_d_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver frequência de outra pessoa de setor descendente:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        c.logout()
        c.login(username=self.user_h_0.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_f_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        # Verifica se usuário sem permissão não pode ver frequências de pessoa
        # de mesmo setor
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            form_errors = formulario.errors
            self.assertFalse(len(form_errors) == 0)

        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_g_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        # Verifica se usuário sem permissão não pode ver frequências de pessoa
        # de setor descendente
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            form_errors = formulario.errors
            self.assertFalse(len(form_errors) == 0)

    @prevent_logging_errors()
    def test_ver_frequencia_campus(self):
        """
        Trata a permissão `pode_ver_frequencia_campus`
        - Pessoa com permissão
            - Testa se pode ver frequência de outra pessoa do mesmo campus
            - Testa se não pode ver frequência de outra pessoa de outro campus
        - Pessoa sem permissão
            - Testar que não pode ver nada
        """
        c = Client()
        c.login(username=self.user_g_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_f_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver a frequência de outra pessoa do mesmo campus:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_1.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            chaves_erro = list(formulario.errors.keys())
            self.assertEqual(len(chaves_erro), 1)
            # Verifica se não pode ver frequência de outra pessoa de campus distinto:
            # se `funcionario` está no dicionário de erros do formulário,
            # então suas frequências não podem ser acessadas
            self.assertEqual('funcionario' in chaves_erro, True)

        c.logout()
        c.login(username=self.user_d_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_2.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        # Verifica se pessoa sem a permissão não pode ver frequências de todas
        # as pessoas de seu campus
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            form_errors = formulario.errors
            self.assertFalse(len(form_errors) == 0)

        c.logout()
        c.login(username=self.user_d_2.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_2.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_1_form}
        )
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            chaves_erro = list(formulario.errors.keys())
            self.assertEqual(len(chaves_erro), 1)
            # Verifica se pessoa sem a permissão não pode ver frequência de todas
            # as pessoas de seu campus:
            # se `funcionario` está no dicionário de erros do formulário,
            # então suas frequências não podem ser acessadas
            self.assertEqual('funcionario' in chaves_erro, True)

    @prevent_logging_errors()
    def test_ver_frequencia_todos(self):
        """
        Trata a permissão `pode_ver_frequencia_todos`
        - Pessoa com permissão
            - Testa se pode ver frequência de outra pessoa de campus diferente
        - Pessoa sem permissão
            - Testar que não pode ver nada
        """
        c = Client()
        c.login(username=self.user_g_2.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_f_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_0_form}
        )
        formulario = None
        try:
            a = response.context['form']
            formulario = a['form']
        except KeyError:
            pass
        # Verifica se pode ver frequência de outra pessoa de outro campus:
        # se `form` não está presente no response, então o formulário foi submetido
        # com sucesso.
        self.assertEqual(formulario, None)

        c.logout()
        c.login(username=self.user_d_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_f_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_0_form}
        )
        # Verifica se pessoa sem permissão `pode_ver_frequencia_todos` não pode ver
        # frequências de outros campi
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            form_errors = formulario.errors
            self.assertFalse(len(form_errors) == 0)

        c.logout()
        c.login(username=self.user_e_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_f_0.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_0_form}
        )
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            chaves_erro = list(formulario.errors.keys())
            self.assertEqual(len(chaves_erro), 1)
            # Verifica se pessoa sem a permissão não pode ver frequência de outra pessoa
            # de outro campus:
            # se `funcionario` está no dicionário de erros do formulário,
            # então suas frequências não podem ser acessadas
            self.assertEqual('funcionario' in chaves_erro, True)

        c.logout()
        c.login(username=self.user_g_1.username, password='123')
        response = c.get(
            '/ponto/frequencia_funcionario/', {'sabado': True, 'domingo': True, 'funcionario': self.funcionario_e_2.pk, 'faixa_0': self.faixa_0_form, 'faixa_1': self.faixa_0_form}
        )
        formulario = 'form' in response.context and response.context['form'] or None
        if formulario:
            chaves_erro = list(formulario.errors.keys())
            self.assertEqual(len(chaves_erro), 1)
            # Verifica se pessoa sem a permissão não pode ver frequência de outra pessoa
            # de outro campus:
            # se `funcionario` está no dicionário de erros do formulário,
            # então suas frequências não podem ser acessadas
            self.assertEqual('funcionario' in chaves_erro, True)
