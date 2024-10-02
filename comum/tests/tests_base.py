import logging
import time
from datetime import date

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.color import color_style
from django.db import transaction
from django.test import TestCase, override_settings
from django.test.client import Client

from comum.models import OcupacaoPrestador, Ocupacao
from djtools.utils import prevent_logging_errors

Municipio = apps.get_model('comum', 'Municipio')
User = apps.get_model('comum', 'User')
Group = apps.get_model('auth', 'group')
Permission = apps.get_model('auth', 'permission')
Configuracao = apps.get_model('comum', 'Configuracao')
PrestadorServico = apps.get_model('comum', 'PrestadorServico')
PessoaFisica = apps.get_model('rh', 'PessoaFisica')
PessoaJuridica = apps.get_model('rh', 'PessoaJuridica')
Setor = apps.get_model('rh', 'Setor')
Servidor = apps.get_model('rh', 'Servidor')
UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
TipoUnidadeOrganizacional = apps.get_model('rh', 'TipoUnidadeOrganizacional')
Situacao = apps.get_model('rh', 'Situacao')
GrupoCargoEmprego = apps.get_model('rh', 'GrupoCargoEmprego')
CargoEmprego = apps.get_model('rh', 'CargoEmprego')
JornadaTrabalho = apps.get_model('rh', 'JornadaTrabalho')
Ano = apps.get_model('comum', 'Ano')


class SuapClient(Client):
    """
    Cliente criado para facilitar DEBUG de erros em formulários submetidos
    via método `post`.
    """

    def login(self, **credentials):
        self.user = credentials.pop('user', None)
        if self.user:
            credentials['username'] = self.user.username
            credentials['password'] = '123'
            from comum.utils import tl

            setattr(tl.tl, 'user', self.user)

        return super().login(**credentials)

    def logout(self):
        self.user = None
        return super().logout()

    def post(self, path, data={}, silent=False, *args, **kwargs):
        # Exibe os erros de validação dos forms
        kwargs['HTTP_REFERER'] = 'http://testserver/'
        response = super().post(path=path, data=data, *args, **kwargs)
        lines = response.content.decode('utf-8').split('\n')
        for idx, line in enumerate(lines):
            if line.find('errorlist') > 0:
                line_before = lines[idx - 1].strip()  # shows the error field
                error_msg = line[line.find('<li') + 4: line.find('</li')]
                msg = '[WARNING FORM at {}] {}: {}'.format(path, line_before, error_msg)
                response.error = color_style().SQL_KEYWORD(msg)
                if not silent:
                    print(response.error)
        return response


@override_settings(DEBUG=True)
class SuapTestCase(TestCase):
    """
    Classe base para os testes do SUAP, que já executa o `sync_permissions` e
    cria objetos básicos.
    """

    __tear_down_class = False
    fixtures = ['initial_data']
    first_time = True
    dict_initial_data = None
    resume_num_tests = 0  # Conta a quantidade de testes realizados para cada classe de teste.
    resume_time_start_by_class = 0  # Registra o tempo inicial para cada classe de teste.
    resume_list = []  # Armazena uma lista de dicionário (classe, tempo, quantidade) para registrar
    # os tempos e as quantidades de testes para cada classe de teste
    resume_num_tests_total = 0
    resume_time_start = 0

    @staticmethod
    def cadastrar_setor(sigla, superior=None, codigo=None):
        qs = Setor.todos.filter(sigla=sigla, codigo=None)
        if qs.exists():
            setor = qs[0]
        else:
            setor = Setor.todos.create(sigla=sigla, nome=sigla, superior=superior)
        superior_siap = None
        if superior:
            qs = Setor.todos.filter(sigla=superior.sigla, codigo__isnull=False)
            if qs.exists():
                superior_siap = qs[0]
        qs = Setor.todos.filter(sigla=sigla, codigo=codigo or sigla)
        if qs.exists():
            setor_siap = qs[0]
        else:
            setor_siap = Setor.todos.create(sigla=sigla, nome=sigla, superior=superior_siap, codigo=codigo or sigla)

        if codigo:
            qs = UnidadeOrganizacional.objects.filter(codigo_ug=codigo)
            if qs.exists():
                campus = qs[0]
            else:
                campus = UnidadeOrganizacional.objects.suap().create(setor=setor, codigo_ug=codigo, nome=sigla, sigla=sigla, codigo_protocolo=f'3{setor.id}'.zfill(5))
            qs = UnidadeOrganizacional.objects.filter(setor=setor_siap, equivalente=campus)
            if not qs.exists():
                UnidadeOrganizacional.objects.create(setor=setor_siap, equivalente=campus, codigo_protocolo=f'3{setor_siap.id}'.zfill(5))
        # associando campus aos respectivos setores
        setor.uo = setor._get_uo()
        setor.codigo_siorg = f'1{setor.id}'.zfill(6)
        setor.save(update_fields=['uo'])
        setor_siap.codigo_siorg = f'2{setor.id}'.zfill(6)
        setor_siap.uo = setor_siap._get_uo()
        setor_siap.save(update_fields=['uo'])
        return setor, setor_siap

    @staticmethod
    def definir_endereco(uo, *endereco):
        for dictionary in endereco:
            for key in dictionary:
                setattr(uo, key, dictionary[key])
        uo.save()

    @classmethod
    def setUpClass(cls):
        """
        Executa uma única vez para cada classe de teste antes do self.setUp()
        """
        logger = logging.getLogger()
        logger.info('setUpClass {}'.format(cls.__name__))
        SuapTestCase.resume_num_tests = 0
        SuapTestCase.resume_time_start_by_class = time.time()

        if SuapTestCase.first_time:
            SuapTestCase.resume_time_start = time.time()
            SuapTestCase.carga_sync_permissions()
            SuapTestCase.__carga_inicial()
        super().setUpClass()
        # connections.databases['default']['ATOMIC_REQUESTS'] = True
        SuapTestCase.first_time = False
        SuapTestCase.limpar_cache_permission()

        SuapTestCase.methods_time = {}

    @classmethod
    def setUpTestData(cls):
        """
        Carrega os dados iniciais para os testes uma única vez.
        Se usar o argumento keepdb, esses dados ficaram salvos no banco.
        """

    @classmethod
    def tearDownClass(cls):
        cls.__tear_down_class = True
        super().tearDownClass()
        tend = time.time()
        tdiff = tend - SuapTestCase.resume_time_start_by_class

        dic_test = {}
        dic_test['classe'] = cls.__name__
        dic_test['tempo'] = time.strftime("%H:%M:%S", time.gmtime(tdiff))
        dic_test['quantidade'] = SuapTestCase.resume_num_tests
        dic_test[cls.__name__] = dict()
        dic_test['tempo_metodos'] = SuapTestCase.methods_time
        SuapTestCase.resume_list.append(dic_test)

        SuapTestCase.resume_num_tests_total += SuapTestCase.resume_num_tests

    @classmethod
    def _rollback_atomics(cls, atomics):
        if not cls.__tear_down_class:
            super()._rollback_atomics(atomics)
        else:
            is_rollback = False if settings.TEST_REUSEDB else True
            for db_name in reversed(cls._databases_names()):
                transaction.set_rollback(is_rollback, using=db_name)
                atomics[db_name].__exit__(None, None, None)
        cls.__tear_down_class = False

    @classmethod
    def print_test_resume(cls):
        tend = time.time()
        tdiff = tend - SuapTestCase.resume_time_start
        print('RESUMO DO TESTE')
        print('| {:<75}|{:>10}|{:^10}|'.format('Classe/Método', 'Quantidade', 'Tempo'))
        print('=' * 100)
        lista_resumo = sorted(SuapTestCase.resume_list, key=lambda di: di['tempo'], reverse=True)
        for resumo in lista_resumo:
            print('| {:<75}|{:^10}|{:^10}|'.format(resumo['classe'], resumo['quantidade'], resumo['tempo']))
            for metodo, tempo in list(resumo['tempo_metodos'].items()):
                print('|  {:<74}|{:^10}|{:^10}|'.format(metodo, '-', tempo))
        print('-' * 65)
        if SuapTestCase.resume_time_start > 0:
            stime = time.strftime("%H:%M:%S", time.gmtime(tdiff))
        else:
            stime = '-'
        print('| {:<75}|{:^10}|{:^10}|\n'.format('TOTAL', SuapTestCase.resume_num_tests_total, stime))

    def setUp(self):
        self.logger = logging.getLogger()
        SuapTestCase.resume_time_start_by_method = time.time()
        SuapTestCase.resume_num_tests += 1
        self.definir_variaveis_de_instancia()
        super().setUp()

    def tearDown(self):
        method_name = str(self).split()[0]
        tend = time.time()
        tdiff = tend - SuapTestCase.resume_time_start_by_method
        SuapTestCase.methods_time[method_name] = time.strftime("%H:%M:%S", time.gmtime(tdiff))

    def definir_variaveis_de_instancia(self):
        initial_data = SuapTestCase.dict_initial_data
        self.client = initial_data['client']
        self.instituicao_nome = initial_data['instituicao_nome']
        self.instituicao_sigla = initial_data['instituicao_sigla']
        self.setor_raiz_suap = initial_data['setor_raiz_suap']
        self.setor_raiz_siape = initial_data['setor_raiz_siape']
        self.setor_re_suap = initial_data['setor_re_suap']
        self.setor_re_siape = initial_data['setor_re_siape']
        self.setor_a0_suap = initial_data['setor_a0_suap']
        self.setor_a0_siape = initial_data['setor_a0_siape']
        self.campus_a_suap = initial_data['campus_a_suap']
        self.campus_a_suap_siape = initial_data['campus_a_suap_siape']
        self.setor_a0_suap = initial_data['setor_a0_suap']
        self.setor_a0_siape = initial_data['setor_a0_siape']
        self.setor_a1_suap = initial_data['setor_a1_suap']
        self.setor_a1_siape = initial_data['setor_a1_siape']
        self.setor_a2_suap = initial_data['setor_a2_suap']
        self.setor_a2_siape = initial_data['setor_a2_siape']
        self.setor_b0_suap = initial_data['setor_b0_suap']
        self.setor_b0_siape = initial_data['setor_b0_siape']
        self.campus_b_suap = initial_data['campus_b_suap']
        self.campus_b_suap_siape = initial_data['campus_b_suap_siape']
        self.setor_b0_suap = initial_data['setor_b0_suap']
        self.setor_b0_siape = initial_data['setor_b0_siape']
        self.setor_b1_suap = initial_data['setor_b1_suap']
        self.setor_b1_siape = initial_data['setor_b1_siape']
        self.setor_b2_suap = initial_data['setor_b2_suap']
        self.setor_b2_siape = initial_data['setor_b2_siape']
        self.situacao_ativo_permanente = initial_data['situacao_ativo_permanente']
        self.jornada_trabalho = initial_data['jornada_trabalho']
        self.grupo_cargo_emprego = initial_data['grupo_cargo_emprego']
        self.cargo_emprego_a = initial_data['cargo_emprego_a']
        self.cargo_emprego_b = initial_data['cargo_emprego_b']
        self.admin = initial_data['admin']
        self.servidor_a = initial_data['servidor_a']
        self.servidor_b = initial_data['servidor_b']
        self.servidor_c = initial_data['servidor_c']
        self.servidor_d = initial_data['servidor_d']
        self.pessoa_juridica = initial_data['pessoa_juridica']
        self.prestador_1 = initial_data['prestador_1']

    def logout(self):
        self.client.get('/accounts/logout/')
        self.client.user = None

    def assert_no_validation_errors(self, response, url=None, data=None, content=None):
        errors = []
        erro_note = ''
        for line in response.content.decode().split('\n'):
            if line.find('"errorlist"') > 0:
                errors.append(line[line.find('<li') + 4: line.find('</li')])
            elif line.find(' errornote ') > 0 or erro_note:
                index_inicial = line.find('<p')
                index_final = line.find('</p>')
                # breakpoint()
                if index_final > 0 and index_inicial < index_final:
                    erro_note += line[index_inicial: index_final]
                    break
                elif index_final > 0 and (index_inicial < 0 or index_inicial > index_final):
                    erro_note += line[: index_final + 4]
                    break
                elif index_inicial > 0 > index_final:
                    erro_note += line[index_inicial:]
                elif index_inicial < 0 and index_final < 0 and erro_note:
                    erro_note += line[:]
                else:
                    breakpoint()
        if erro_note:
            errors.append(erro_note)
        if errors:
            file = open('/tmp/testcase.html', 'w')
            file.write(response.content.decode())
            file.close()
            raise Exception('Erros apresentados no form:\n' + ('\n'.join(errors)) + f'\n{url}\n{data}\n{content}')
        return True

    def debug(self, response):
        f = open('/tmp/testcase.html', 'w')
        f.write(response.content.decode())
        f.close()

    def save_page(self, response):
        file = open('/tmp/testcase.html', 'w')
        file.write(response.content.decode())
        file.close()

    @classmethod
    def carga_sync_permissions(cls):
        """
        Método criado para criar o comum/fixtures/test.json com os registros gerados
        pelo command ``sync_permissions``, que é muito pesado de ser rodado em cada setUp.
        """
        from django.contrib.auth.models import Group

        if Group.objects.all().count() == 0:  # Não execute sync_permissions quando utilizar opção keepdb
            call_command('sync_permissions', verbosity=0)
            with open('comum/fixtures/test.json', 'w') as f:
                call_command('dumpdata', 'auth.Group', 'comum.GerenciamentoGrupo', stdout=f)

    @classmethod
    def __carga_inicial(cls):
        """
        Setores criados (SUAP e SIAPE com mesma estrutura)
        * Setores que são campi (A e B)
        ------------------------------------------------------------------------
                                    RAIZ
                            A0*                  B0*
                        A1      A2          B1      B2
        ------------------------------------------------------------------------

        Servidores criados:
         - Abraão do setor A1 (usuário a1)
         - Artur do setor A2 (usuário a2)
         - Bernardo do setor B1 (usuário b1)
         - Bruno do setor B2 (usuário b2)
        """
        call_command('create_postgres_extensions', skip_checks=True)
        # call_command('edu_importar_sistec', '--estados', '--cidades', verbosity=0)
        initial_data = dict()

        initial_data['client'] = SuapClient()

        Configuracao.objects.get_or_create(app='comum', chave='setores', valor='SUAP')
        initial_data['instituicao_nome'], criado = Configuracao.objects.get_or_create(
            app='comum', chave='instituicao', valor='Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte'
        )
        initial_data['instituicao_sigla'], criado = Configuracao.objects.get_or_create(app='comum', chave='instituicao_sigla', valor='IFRN')

        # Configuracao do Recaptcha
        settings.RECAPTCHA_PUBLIC_KEY = '6LeQeb4SAAAAANxeiQhn7aqymlmpIYkaOye6UU-Q'
        settings.RECAPTCHA_PRIVATE_KEY = '6LeQeb4SAAAAACA97Q-nYQU8zPnncvy8AwgZpmI4'

        # Ano
        Ano.objects.get_or_create(ano=2013)

        ######################
        # Criando os setores #
        ######################
        municipio, criado = Municipio.objects.get_or_create(nome='Natal', uf='RN', codigo='NAT')
        endereco = {'endereco': 'Rua Dr. Nilo Bezerra Ramalho, 1692, Tirol', 'cep': '59015-300', 'municipio': municipio}

        initial_data['setor_raiz_suap'], criado = Setor.todos.get_or_create(sigla='RAIZ', nome='RAIZ', codigo=None)
        initial_data['setor_raiz_siape'], criado = Setor.todos.get_or_create(sigla='RAIZ', nome='RAIZ', codigo='RAIZ')

        initial_data['setor_re_suap'], initial_data['setor_re_siape'] = cls.cadastrar_setor('RE', initial_data['setor_raiz_suap'], '00001')  # setor_raiz_suap similar ao setor ifrn
        cls.definir_endereco(initial_data['setor_re_suap'].uo, endereco)
        cls.definir_endereco(initial_data['setor_re_siape'].uo, endereco)

        # Hierarquia A
        initial_data['setor_a0_suap'], criado = Setor.todos.get_or_create(sigla='A0', nome='A0', superior=initial_data['setor_raiz_suap'])
        initial_data['setor_a0_siape'], criado = Setor.todos.get_or_create(sigla='A0', nome='A0', superior=initial_data['setor_raiz_siape'], codigo='A0')

        tipo = TipoUnidadeOrganizacional.objects.get_or_create(id=4, descricao='Reitoria')[0]
        initial_data['campus_a_suap'], criado = UnidadeOrganizacional.objects.suap().get_or_create(
            setor=initial_data['setor_a0_suap'], codigo_protocolo='23001', nome='A0', sigla='A0', tipo=tipo
        )
        cls.definir_endereco(initial_data['campus_a_suap'], endereco)

        initial_data['campus_a_suap_siape'], criado = UnidadeOrganizacional.objects.get_or_create(setor=initial_data['setor_a0_siape'], equivalente=initial_data['campus_a_suap'])
        cls.definir_endereco(initial_data['campus_a_suap_siape'], endereco)

        # Recuperando os setores para pegar o campo ``uo`` atualizado
        initial_data['setor_a0_suap'] = Setor.todos.get(pk=initial_data['setor_a0_suap'].pk)
        initial_data['setor_a0_siape'] = Setor.todos.get(pk=initial_data['setor_a0_siape'].pk)

        # Criando setores folhas
        initial_data['setor_a1_suap'], criado = Setor.todos.get_or_create(sigla='A1', nome='A1', superior=initial_data['setor_a0_suap'], codigo=None)
        initial_data['setor_a1_siape'], criado = Setor.todos.get_or_create(sigla='A1', nome='A1', superior=initial_data['setor_a0_siape'], codigo='A1')

        initial_data['setor_a2_suap'], criado = Setor.todos.get_or_create(sigla='A2', nome='A2', superior=initial_data['setor_a0_suap'], codigo=None)
        initial_data['setor_a2_siape'], criado = Setor.todos.get_or_create(sigla='A2', nome='A2', superior=initial_data['setor_a0_siape'], codigo='A2')

        # Hierarquia B
        initial_data['setor_b0_suap'], criado = Setor.todos.get_or_create(sigla='B0', nome='B0', superior=initial_data['setor_raiz_suap'], codigo=None)
        initial_data['setor_b0_siape'], criado = Setor.todos.get_or_create(sigla='B0', nome='B0', superior=initial_data['setor_raiz_siape'], codigo='B0')

        tipo = TipoUnidadeOrganizacional.objects.get_or_create(id=1, descricao='Campus Não Produtivo')[0]
        initial_data['campus_b_suap'], criado = UnidadeOrganizacional.objects.suap().get_or_create(
            setor=initial_data['setor_b0_suap'], codigo_protocolo='23002', nome='B0', sigla='B0', tipo=tipo
        )
        cls.definir_endereco(initial_data['campus_b_suap'], endereco)
        initial_data['setor_b0_suap'].uo = initial_data['campus_b_suap']
        initial_data['setor_b0_suap'].save(update_fields=['uo'])

        initial_data['campus_b_suap_siape'], criado = UnidadeOrganizacional.objects.get_or_create(setor=initial_data['setor_b0_siape'], equivalente=initial_data['campus_b_suap'])
        cls.definir_endereco(initial_data['campus_b_suap_siape'], endereco)

        # Recuperando os setores para pegar o campo ``uo`` atualizado
        initial_data['setor_b0_suap'] = Setor.todos.get(pk=initial_data['setor_b0_suap'].pk)
        initial_data['setor_b0_siape'] = Setor.todos.get(pk=initial_data['setor_b0_siape'].pk)

        # Criando setores folhas
        initial_data['setor_b1_suap'], criado = Setor.todos.get_or_create(sigla='B1', nome='B1', superior=initial_data['setor_b0_suap'])
        initial_data['setor_b1_siape'], criado = Setor.todos.get_or_create(sigla='B1', nome='B1', superior=initial_data['setor_b0_siape'], codigo='B1')

        initial_data['setor_b2_suap'], criado = Setor.todos.get_or_create(sigla='B2', nome='B2', superior=initial_data['setor_b0_suap'])
        initial_data['setor_b2_siape'], criado = Setor.todos.get_or_create(sigla='B2', nome='B2', superior=initial_data['setor_b0_siape'], codigo='B2')

        #########################
        # Criando os servidores #
        #########################

        # Criando Situações para Servidores
        initial_data['situacao_ativo_permanente'], criado = Situacao.objects.get_or_create(codigo=Situacao.ATIVO_PERMANENTE, nome_siape='ATIVO PERMANENTE', excluido=False)

        # Criando jornada de trabalho
        initial_data['jornada_trabalho'], criado = JornadaTrabalho.objects.get_or_create(codigo='01', nome='40h', excluido=False)

        # Criando cargos para servidores
        initial_data['grupo_cargo_emprego'], criado = GrupoCargoEmprego.objects.get_or_create(
            codigo='01', nome='Grupo X', sigla='X', categoria='tecnico_administrativo', excluido=False
        )
        initial_data['cargo_emprego_a'], criado = CargoEmprego.objects.get_or_create(
            codigo='01', nome='Cargo A', grupo_cargo_emprego=initial_data['grupo_cargo_emprego'], sigla_escolaridade='01', excluido=False
        )
        initial_data['cargo_emprego_b'], criado = CargoEmprego.objects.get_or_create(
            codigo='02', nome='Cargo B', grupo_cargo_emprego=initial_data['grupo_cargo_emprego'], sigla_escolaridade='01', excluido=False
        )
        # Criando os servidores
        kwargs_admin = dict(
            nome='admin',
            template=b'1',
            excluido=False,
            situacao=initial_data['situacao_ativo_permanente'],
            cargo_emprego=initial_data['cargo_emprego_a'],
            setor=initial_data['setor_a1_suap'],
            setor_lotacao=initial_data['setor_a1_siape'],
            setor_exercicio=initial_data['setor_a1_siape'],
            email='admin@mail.gov',
            cpf='865.572.326-65',
            jornada_trabalho=initial_data['jornada_trabalho'],
        )
        initial_data['admin'] = Servidor.objects.get_or_create(matricula='admin', defaults=kwargs_admin)[0]
        user = initial_data['admin'].user
        user.set_password('123')
        user.is_superuser = True
        user.is_staff = True
        user.save()

        kwargs_servidor_a = dict(
            nome='Servidor 1',
            template=b'1',
            excluido=False,
            situacao=initial_data['situacao_ativo_permanente'],
            cargo_emprego=initial_data['cargo_emprego_a'],
            setor=initial_data['setor_a1_suap'],
            setor_lotacao=initial_data['setor_a1_siape'],
            setor_exercicio=initial_data['setor_a1_siape'],
            email='servidor.a@mail.gov',
            cpf='861.474.078-64',
            jornada_trabalho=initial_data['jornada_trabalho'],
        )
        initial_data['servidor_a'] = Servidor.objects.get_or_create(matricula='1111111', defaults=kwargs_servidor_a)[0]
        initial_data['servidor_a'].user.set_password('123')
        initial_data['servidor_a'].user.save()

        kwargs_servidor_b = dict(
            nome='Servidor 2',
            template=b'2',
            situacao=initial_data['situacao_ativo_permanente'],
            cargo_emprego=initial_data['cargo_emprego_b'],
            setor=initial_data['setor_b1_suap'],
            setor_lotacao=initial_data['setor_b1_siape'],
            setor_exercicio=initial_data['setor_b1_siape'],
            email='servidor.b@mail.gov',
            jornada_trabalho=initial_data['jornada_trabalho'],
            data_inicio_exercicio_na_instituicao=date(2010, 1, 1),
            cpf='817.483.818-06',
            data_inicio_exercicio_no_cargo=date(2010, 1, 1),
        )
        initial_data['servidor_b'] = Servidor.objects.get_or_create(matricula='2222222', defaults=kwargs_servidor_b)[0]
        initial_data['servidor_b'].user.set_password('123')
        initial_data['servidor_b'].user.save()

        kwargs_servidor_c = dict(
            nome='Servidor 3',
            template=b'3',
            situacao=initial_data['situacao_ativo_permanente'],
            cargo_emprego=initial_data['cargo_emprego_b'],
            setor=initial_data['setor_a2_suap'],
            setor_lotacao=initial_data['setor_a2_siape'],
            setor_exercicio=initial_data['setor_a2_siape'],
            email='servidor.3@mail.gov',
            cpf='575.333.822-42',
            jornada_trabalho=initial_data['jornada_trabalho'],
        )
        initial_data['servidor_c'] = Servidor.objects.get_or_create(matricula='3333333', defaults=kwargs_servidor_c)[0]
        initial_data['servidor_c'].user.set_password('123')
        initial_data['servidor_c'].user.save()

        kwargs_servidor_d = dict(
            nome='Servidor 4',
            template=b'4',
            situacao=initial_data['situacao_ativo_permanente'],
            cargo_emprego=initial_data['cargo_emprego_b'],
            setor=initial_data['setor_b2_suap'],
            setor_lotacao=initial_data['setor_b2_siape'],
            setor_exercicio=initial_data['setor_b2_siape'],
            email='servidor.d@mail.gov',
            cpf='153.148.137-00',
            jornada_trabalho=initial_data['jornada_trabalho'],
        )
        initial_data['servidor_d'] = Servidor.objects.get_or_create(matricula='4444444', defaults=kwargs_servidor_d)[0]
        initial_data['servidor_d'].user.set_password('123')
        initial_data['servidor_d'].user.save()

        ###########################
        # Criando pessoa jurídica #
        ###########################

        initial_data['pessoa_juridica'] = PessoaJuridica.objects.get_or_create(cnpj='45.006.424/0001-00', defaults=dict(nome='Pessoa Jurídica'))[0]

        ################################
        # Criando prestador de serviço #
        ################################
        kwargs_prestador_1 = dict(nome='Prestador 1', setor=initial_data['setor_a0_suap'])
        PrestadorServico.objects.get_or_create(cpf='506.213.644-01', defaults=kwargs_prestador_1)
        initial_data['prestador_1'] = PrestadorServico.objects.get(cpf='506.213.644-01')
        initial_data['prestador_1'].user.set_password('123')
        initial_data['prestador_1'].user.save()

        ocupacao = Ocupacao.objects.get_or_create(codigo='', descricao='Teste Ocupação')[0]
        OcupacaoPrestador.objects.create(
            prestador=initial_data['prestador_1'], ocupacao=ocupacao, empresa=initial_data['pessoa_juridica'], data_inicio=date(2010, 1, 1), data_fim=date(2100, 1, 1)
        )

        SuapTestCase.dict_initial_data = initial_data

    @classmethod
    def limpar_cache_permission(cls):
        """
        Apaga o cache de permissões de grupos e de usuários
        """
        if SuapTestCase.dict_initial_data:
            if hasattr(SuapTestCase.dict_initial_data['servidor_a'].user, '_group_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_a'].user, '_group_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_a'].user, '_user_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_a'].user, '_user_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_a'].user, '_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_a'].user, '_perm_cache')

            if hasattr(SuapTestCase.dict_initial_data['servidor_b'].user, '_group_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_b'].user, '_group_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_b'].user, '_user_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_b'].user, '_user_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_b'].user, '_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_b'].user, '_perm_cache')

            if hasattr(SuapTestCase.dict_initial_data['servidor_c'].user, '_group_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_c'].user, '_group_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_c'].user, '_user_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_c'].user, '_user_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_c'].user, '_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_c'].user, '_perm_cache')

            if hasattr(SuapTestCase.dict_initial_data['servidor_d'].user, '_group_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_d'].user, '_group_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_d'].user, '_user_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_d'].user, '_user_perm_cache')
            if hasattr(SuapTestCase.dict_initial_data['servidor_d'].user, '_perm_cache'):
                delattr(SuapTestCase.dict_initial_data['servidor_d'].user, '_perm_cache')

    @classmethod
    def allow_save_scenario(cls):
        try:
            return settings.SUAP_TESTS['SALVAR_CENARIO']
        except Exception:
            return False

    @classmethod
    def keep_json(cls):
        try:
            return settings.SUAP_TESTS['MANTER_JSON']
        except Exception:
            return False

    def get_text_array(self, texto):
        if type(texto) == str:
            return [texto]
        if not hasattr(texto, '__iter__'):
            return [texto]

        return texto

    @prevent_logging_errors()
    def verificar_perfil_status(
        self, url, data={}, verificar_sem_perfil=True, pode_sem_perfil=False, perfis_corretos=[], perfis_errados=[], success_status_code=200, error_status_code=403, user=None
    ):
        """
        Verifica se está de acordo com os perfis
        """
        if not user:
            if self.client.user:
                user = self.client.user
            else:
                user = self.servidor_a.user

        # lista de grupos que o usuário tem
        grupos_do_usuario = list(user.groups.all())

        for perfil in perfis_corretos:
            user.groups.remove(Group.objects.get(name=perfil))
        for perfil in perfis_errados:
            user.groups.remove(Group.objects.get(name=perfil))

        if verificar_sem_perfil:
            response = self.client.get(url, data)
            if pode_sem_perfil:
                self.assertEqual(response.status_code, success_status_code, 'Usuário "{}" sem perfil {}!={}'.format(user, response.status_code, success_status_code))
            else:
                self.assertEqual(response.status_code, error_status_code, 'Usuário "{}" sem perfil {}!={}'.format(user, response.status_code, error_status_code))

        for perfil in perfis_corretos:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.get(url, data)
            self.assertEqual(response.status_code, success_status_code, 'Usuário "{}" perfil correto {} {}!={}'.format(user, perfil, response.status_code, success_status_code))
            user.groups.remove(Group.objects.get(name=perfil))

        # TODO: Verificar se é melhor mudar o comportamento do admin para lança um 403 aos inves de um 404 no caso de um objeto que não está no queryset
        if url.startswith('/admin/'):
            error_status_code = [error_status_code, 404]

        for perfil in perfis_errados:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.get(url, data, silent=True)
            if isinstance(error_status_code, list):
                self.assertIn(response.status_code, error_status_code, 'Usuário "{}" perfil errado {} {}!={}'.format(user, perfil, response.status_code, error_status_code))
            else:
                self.assertEqual(response.status_code, error_status_code, 'Usuário "{}" perfil errado {} {}!={}'.format(user, perfil, response.status_code, error_status_code))
            user.groups.remove(Group.objects.get(name=perfil))

        # Adicionar os grupos de volta ao usuário
        for grupo in grupos_do_usuario:
            user.groups.add(grupo)

    def verificar_perfil_contains(
        self, url, data={}, text='', verificar_sem_perfil=False, pode_sem_perfil=False, perfis_corretos=[], perfis_errados=[], error_status_code=None, user=None
    ):
        """
        Verifica se a página (url) contém o texto (text) para os grupos definidos em perfis_corretos.
        Também verifica se o texto não está disponível para os grupos definidos em perfis_errados.
        Caso o grupo definido em perfis_errados não tenha permissão à página e não foi informado error_status_code, o teste irá falha.
        """
        if not user:
            if self.client.user:
                user = self.client.user
            else:
                user = self.servidor_a.user

        # lista de grupos que o usuário tem
        grupos_do_usuario = list(user.groups.all())

        for perfil in perfis_corretos:
            user.groups.remove(Group.objects.get(name=perfil))
        for perfil in perfis_errados:
            user.groups.remove(Group.objects.get(name=perfil))

        if verificar_sem_perfil:
            response = self.client.get(url, data)
            if pode_sem_perfil:
                for text_for in self.get_text_array(text):
                    self.assertContains(response, text=text_for, msg_prefix='Usuário "{}" sem perfil'.format(user))
            else:
                if not (error_status_code and (response.status_code == error_status_code == 403 or response.status_code == error_status_code)):
                    for text_for in self.get_text_array(text):
                        self.assertNotContains(response, text=text_for, msg_prefix='Usuario "{}" sem perfil'.format(user))

        for perfil in perfis_corretos:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.get(url, data)
            for text in self.get_text_array(text):
                self.assertContains(response, text=text, msg_prefix='Usuário "{}" perfil correto {}'.format(user, perfil))

            user.groups.remove(Group.objects.get(name=perfil))

        for perfil in perfis_errados:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.get(url, data, silent=True)
            if not (error_status_code and (response.status_code == error_status_code == 403 or response.status_code == error_status_code)):
                for text in self.get_text_array(text):
                    self.assertNotContains(response, text=text, msg_prefix='Usuário "{}" perfil errado {}'.format(user, perfil))

            user.groups.remove(Group.objects.get(name=perfil))

        # Adicionar os grupos de volta ao usuário
        for grupo in grupos_do_usuario:
            user.groups.add(grupo)

    def verificar_perfil_not_contains(
        self, url, data={}, text='', verificar_sem_perfil=False, pode_sem_perfil=False, perfis_corretos=(), perfis_errados=(), success_status_code=None, user=None
    ):
        """
        Verifica se a página (url) contém não o texto (text) para os grupos definidos em perfis_corretos.
        Também verifica se o texto está disponível para os grupos definidos em perfis_errados.
        Caso o grupo definido em perfis_corretos não tenha permissão à página e não foi informado success_status_code, o teste irá falha.
        """
        if not user:
            if self.client.user:
                user = self.client.user
            else:
                user = self.servidor_a.user

        # lista de grupos que o usuário tem
        grupos_do_usuario = list(user.groups.all())

        for perfil in perfis_corretos:
            user.groups.remove(Group.objects.get(name=perfil))
        for perfil in perfis_errados:
            user.groups.remove(Group.objects.get(name=perfil))

        if verificar_sem_perfil:
            response = self.client.get(url, data)
            if pode_sem_perfil:
                if not (success_status_code and (response.status_code == success_status_code == 403 or response.status_code == success_status_code)):
                    for text in self.get_text_array(text):
                        self.assertNotContains(response, text=text, msg_prefix='Usuário "{}" sem perfil'.format(user))
            else:
                for text in self.get_text_array(text):
                    self.assertContains(response, text=text, msg_prefix='Usuário "{}" sem perfil'.format(user))

        for perfil in perfis_corretos:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.get(url, data)
            # se o success_status_code for 403 desconsiderar
            if not (success_status_code and success_status_code == 403 and response.status_code == success_status_code):
                for text in self.get_text_array(text):
                    self.assertNotContains(response, text=text, msg_prefix='Usuário "{}" perfil correto {}'.format(user, perfil))
                user.groups.remove(Group.objects.get(name=perfil))

        for perfil in perfis_errados:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.get(url, data, silent=True)
            for text in self.get_text_array(text):
                self.assertContains(response, text=text, msg_prefix='Usuário "{}" perfil errado {}'.format(user, perfil))

            user.groups.remove(Group.objects.get(name=perfil))

        # Adicionar os grupos de volta ao usuário
        for grupo in grupos_do_usuario:
            user.groups.add(grupo)

    def verificar_perfil_submit(
        self,
        url,
        data={},
        queryset=None,
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=(),
        perfis_errados=(),
        incremento=1,
        success_status_code=200,
        error_status_code=403,
        after_submit=None,
        modificou=None,
        contains_text=None,
        not_contains_text=None,
        user=None,
        contains_text_perfis_errados=None,
    ):
        """
        Verifica se está de acordo com os perfis
        Keyword arguments:
        modificou    -- Uma função a ser executada após cada submit que retorna um booelano para dizer se houve a mudança
        after_submit -- Uma função a ser executada após cada submit
        """
        if not user:
            if self.client.user:
                user = self.client.user
            else:
                user = self.servidor_a.user

        # lista de grupos que o usuário tem
        grupos_do_usuario = list(user.groups.all())

        for perfil in perfis_corretos:
            user.groups.remove(Group.objects.get(name=perfil))
        for perfil in perfis_errados:
            user.groups.remove(Group.objects.get(name=perfil))

        if verificar_sem_perfil:
            if pode_sem_perfil:
                qtd = queryset.count() + incremento
                response = self.client.post(url, data)
                if modificou:
                    self.assertTrue(modificou(), 'Usuário "{}" sem perfil não modificou'.format(user))
            else:
                qtd = queryset.count()
                response = self.client.post(url, data)
                if modificou and (response.status_code != 403 or response.status_code != error_status_code):
                    self.assertFalse(modificou(), 'Usuário "{}" sem perfil modificou'.format(user))

            self.assertEqual(queryset.count(), qtd, 'Usuário "{}" sem perfil {}!={}'.format(user, queryset.count(), qtd))
            if after_submit:
                after_submit()

        for perfil in perfis_corretos:
            qtd = queryset.count() + incremento
            user.groups.add(Group.objects.get(name=perfil))
            if contains_text or not_contains_text:
                response = self.client.post(url, data, follow=True)
            else:
                response = self.client.post(url, data)

            if not contains_text:
                self.assert_no_validation_errors(response)

            self.assertEqual(response.status_code, success_status_code, 'Usuário "{}" perfil correto {} {}!={}'.format(user, perfil, response.status_code, success_status_code))
            self.assertEqual(queryset.count(), qtd, 'Usuário "{}" perfil correto {} {}!={}'.format(user, perfil, queryset.count(), qtd))
            if contains_text or not_contains_text:
                if response.get('Location'):
                    # Utilizado para recuperar a mensagem
                    response = self.client.get(response.get('Location'), {})

                if contains_text:
                    for contains_text in self.get_text_array(contains_text):
                        self.assertContains(response, text=contains_text, msg_prefix='Usuário "{}" perfil correto {}'.format(user, perfil))
                if not_contains_text:
                    for not_contains_text in self.get_text_array(not_contains_text):
                        self.assertNotContains(response, text=not_contains_text, msg_prefix='Usuário "{}" perfil correto {}'.format(user, perfil))
            if modificou:
                self.assertTrue(modificou(), 'Usuário "{}" perfil {} não modificou'.format(user, perfil))
            if after_submit:
                after_submit()
            user.groups.remove(Group.objects.get(name=perfil))

        # TODO: Verificar se é melhor mudar o comportamento do admin para lança um 403 aos inves de um 404 no caso de um objeto que não está no queryset
        if url.startswith('/admin/'):
            error_status_code = [error_status_code, 404]

        for perfil in perfis_errados:
            qtd = queryset.count()
            user.groups.add(Group.objects.get(name=perfil))
            if contains_text_perfis_errados:
                response = self.client.post(url, data, silent=True, follow=True)
                if (
                    response.status_code != 403
                    or (isinstance(error_status_code, list) and response.status_code not in error_status_code)
                    or (response.status_code != error_status_code)
                ):
                    for contains_text_perfis_errados in self.get_text_array(contains_text_perfis_errados):
                        self.assertContains(response, text=contains_text_perfis_errados, msg_prefix='Usuário "{}" perfil errado {}'.format(user, perfil))
            else:
                response = self.client.post(url, data, silent=True)
                if isinstance(error_status_code, list):
                    self.assertIn(response.status_code, error_status_code, 'Usuário "{}" perfil errado {} {}!={}'.format(user, perfil, response.status_code, error_status_code))
                else:
                    self.assertEqual(response.status_code, error_status_code, 'Usuário "{}" perfil errado {} {}!={}'.format(user, perfil, response.status_code, error_status_code))

            self.assertEqual(queryset.count(), qtd, 'Usuário "{}" perfil errado {} {}!={}'.format(user, perfil, queryset.count(), qtd))
            if modificou and (response.status_code != 403 or response.status_code != error_status_code):
                self.assertFalse(modificou(), 'Usuário "{}" perfil {} modificou'.format(user, perfil))
            if after_submit:
                after_submit()
            user.groups.remove(Group.objects.get(name=perfil))

        # Adicionar os grupos de volta ao usuário
        for grupo in grupos_do_usuario:
            user.groups.add(grupo)


class EmptyTestCase(SuapTestCase):
    def test(self):
        pass


class CreateDatabaseTestCase(TestCase):
    def test(self):
        pass
