import datetime

from django.conf import settings
from django.core.management import call_command

from comum.models import Configuracao, Ano, Municipio, PrestadorServico, OcupacaoPrestador, Ocupacao
from rh.models import Setor, UnidadeOrganizacional, Situacao, JornadaTrabalho, GrupoCargoEmprego, CargoEmprego, Servidor, PessoaJuridica, Funcao, ServidorFuncaoHistorico, Atividade


def start_database():
    call_command('create_postgres_extensions', skip_checks=True)
    call_command('loaddata', 'initial_data', skip_checks=True)

    if 'documento_eletronico' in settings.INSTALLED_APPS_SUAP:
        call_command('documento_eletronico_initial', skip_checks=True)

    if 'processo_eletronico' in settings.INSTALLED_APPS_SUAP:
        call_command('processo_eletronico_initial', skip_checks=True)

    call_command('sync_permissions', skip_checks=True)


# ------------------------------------------------------------------------------------------------------------------
# Funções auxiliares
# ------------------------------------------------------------------------------------------------------------------
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
            campus = UnidadeOrganizacional.objects.suap().create(setor=setor, codigo_ug=codigo, nome=sigla, sigla=sigla)
        qs = UnidadeOrganizacional.objects.filter(setor=setor_siap, equivalente=campus)
        if not qs.exists():
            UnidadeOrganizacional.objects.create(setor=setor_siap, equivalente=campus, nome=sigla, sigla=sigla)
    # associando campus aos respectivos setores
    setor.uo = setor._get_uo()
    setor.save(update_fields=['uo'])
    setor_siap.uo = setor_siap._get_uo()
    setor_siap.save(update_fields=['uo'])
    return setor, setor_siap


def definir_endereco(uo, *endereco):
    for dictionary in endereco:
        for key in dictionary:
            setattr(uo, key, dictionary[key])
    uo.save()


def initial_data():
    """
    Setores criados (SUAP e SIAPE com mesma estrutura)
    * Setores que são campi (A, B e C)
    ------------------------------------------------------------------------------------
                                             RAIZ
                        A0*                  B0*                  C0*          CEN*               CZN*
                    A1      A2           B1      B2            C1    C2        DIAC/CEN       DIAC/CNZ
    ------------------------------------------------------------------------------------

    Servidores criados:
     - Abraão do setor A1 (usuário a1)
     - Artur do setor A2 (usuário a2)
     - Bernardo do setor B1 (usuário b1)
     - Bruno do setor B2 (usuário b2)
    """
    # ------------------------------------------------------------------------------------------------------------------
    # Cria e adiciona as configurações para que a aplicação consiga ser executada
    # ------------------------------------------------------------------------------------------------------------------
    Configuracao.objects.get_or_create(app='comum', chave='setores', valor='SUAP')
    Configuracao.objects.get_or_create(app='comum', chave='instituicao', valor='Instituto Federal de Educação, Ciência e Tecnologia do Rio Grande do Norte')
    Configuracao.objects.get_or_create(app='comum', chave='instituicao_sigla', valor='IFRN')
    Configuracao.objects.get_or_create(app='comum', chave='reitoria_sigla', valor='RAIZ')
    Configuracao.objects.get_or_create(app='edu', chave='ano_letivo_atual', valor='2019')
    Configuracao.objects.get_or_create(app='edu', chave='periodo_letivo_atual', valor='1')
    Configuracao.objects.get_or_create(app='rh', chave='permite_email_institucional_email_secundario', valor=True)

    from django.core.cache import cache
    cache.clear()

    # Configuração do RECAPTCHA ----------------------------------------------------------------------------------------
    settings.RECAPTCHA_PUBLIC_KEY = ''
    settings.RECAPTCHA_PRIVATE_KEY = ''

    # ------------------------------------------------------------------------------------------------------------------
    # Adiciona os dados básicos
    # ------------------------------------------------------------------------------------------------------------------
    Ano.objects.get_or_create(ano=2018)
    Ano.objects.get_or_create(ano=2019)
    Ano.objects.get_or_create(ano=2020)

    municipio, _ = Municipio.objects.get_or_create(nome='Natal', uf='RN', codigo='NAT')
    endereco = {'endereco': 'Rua Dr. Nilo Bezerra Ramalho, 1692, Tirol', 'cep      ': '59015-300', 'municipio': municipio}

    setor_raiz_suap, setor_raiz_siape = cadastrar_setor('RAIZ', None, 'RAIZ')
    definir_endereco(setor_raiz_suap.uo, endereco)
    definir_endereco(setor_raiz_suap.uo, endereco)

    # Hierarquia CEN

    setor_cen_suap, _ = Setor.todos.get_or_create(sigla='CEN', nome='Campus Central', superior=setor_raiz_suap, codigo_siorg='1337')
    setor_cen_siape, _ = Setor.todos.get_or_create(sigla='CEN', nome='Campus Central', superior=setor_raiz_siape, codigo='CEN', codigo_siorg='1337')

    campus_cen_suap, _ = UnidadeOrganizacional.objects.suap().get_or_create(tipo_id=1, setor=setor_cen_suap, codigo_protocolo='23002', nome='Campus Central', sigla='CEN')
    definir_endereco(campus_cen_suap, endereco)

    campus_cen_suap_siape, _ = UnidadeOrganizacional.objects.get_or_create(setor=setor_cen_siape, equivalente=campus_cen_suap)
    definir_endereco(campus_cen_suap_siape, endereco)

    # Recuperando os setores para pegar o campo ``uo`` atualizado
    setor_cen_suap = Setor.todos.get(pk=setor_cen_suap.pk)
    setor_cen_siape = Setor.todos.get(pk=setor_cen_siape.pk)

    # Criando setores folhas EDU - SUAP
    setor_diac_cen_suap, _ = cadastrar_setor('DIAC/CEN', setor_cen_suap, None)
    cadastrar_setor('DIATI/CEN', setor_diac_cen_suap, None)

    # Criando setores folhas DOCUMENTO ELETRONICO - SUAP
    setor_dide_cen_suap, _ = cadastrar_setor('DIDE/CEN', setor_cen_suap, None)
    cadastrar_setor('CODE/CEN', setor_dide_cen_suap, None)

    # Begin Hierarquia CZN
    setor_czn_suap, _ = Setor.todos.get_or_create(sigla='CZN', nome='Campus Zona Norte', codigo_siorg="00100", superior=setor_raiz_suap)
    setor_czn_siape, _ = Setor.todos.get_or_create(sigla='CZN', nome='Campus Zona Norte', superior=setor_raiz_siape, codigo='CZN')
    campus_czn_suap, _ = UnidadeOrganizacional.objects.suap().get_or_create(tipo_id=1, setor=setor_czn_suap, codigo_protocolo='23003', nome='Campus Zona Norte', sigla='CZN')
    definir_endereco(campus_czn_suap, endereco)

    campus_czn_suap_siape, _ = UnidadeOrganizacional.objects.get_or_create(setor=setor_czn_siape, equivalente=campus_czn_suap)
    definir_endereco(campus_czn_suap_siape, endereco)

    # Recuperando os setores para pegar o campo ``uo`` atualizado
    setor_czn_suap = Setor.todos.get(pk=setor_czn_suap.pk)
    setor_czn_siape = Setor.todos.get(pk=setor_czn_siape.pk)

    # Criando setores folhas
    Setor.todos.get_or_create(sigla='DIAC/CZN', nome='Diretoria Acadêmica', superior=setor_czn_suap)
    Setor.todos.get_or_create(sigla='DIAC/CZN', nome='Diretoria Acadêmica', superior=setor_czn_siape, codigo='DIAC/CZN')

    # END Hierarquia CZN
    # Hierarquia A ------------------------------------
    setor_a0_suap, _ = Setor.todos.get_or_create(sigla='A0', nome='A0', superior=setor_raiz_suap, codigo_siorg="666")
    setor_a0_siape, _ = Setor.todos.get_or_create(sigla='A0', nome='A0', superior=setor_raiz_siape, codigo='A0')

    campus_a_suap, _ = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor_a0_suap, codigo_protocolo='23001', nome='A0', sigla='A0')
    definir_endereco(campus_a_suap, endereco)

    campus_a_suap_siape, _ = UnidadeOrganizacional.objects.get_or_create(setor=setor_a0_siape, defaults=dict(equivalente=campus_a_suap))
    definir_endereco(campus_a_suap_siape, endereco)

    # Recuperando os setores para pegar o campo ``uo`` atualizado
    setor_a0_suap = Setor.todos.get(pk=setor_a0_suap.pk)
    setor_a0_siape = Setor.todos.get(pk=setor_a0_siape.pk)

    # Criando setores folhas
    setor_a1_suap, _ = Setor.todos.get_or_create(sigla='A1', nome='A1', superior=setor_a0_suap, codigo=None, codigo_siorg=439)
    setor_a1_siape, _ = Setor.todos.get_or_create(sigla='A1', nome='A1', superior=setor_a0_siape, codigo='A1')

    setor_a2_suap, _ = Setor.todos.get_or_create(sigla='A2', nome='A2', superior=setor_a0_suap, codigo=None)
    setor_a2_siape, _ = Setor.todos.get_or_create(sigla='A2', nome='A2', superior=setor_a0_siape, codigo='A2')

    # Hierarquia B ------------------------------------
    setor_b0_suap, _ = Setor.todos.get_or_create(sigla='B0', nome='B0', superior=setor_raiz_suap, codigo=None)
    setor_b0_siape, _ = Setor.todos.get_or_create(sigla='B0', nome='B0', superior=setor_raiz_siape, codigo='B0')

    campus_b_suap, _ = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor_b0_suap, codigo_protocolo='23002', nome='B0', sigla='B0')
    definir_endereco(campus_b_suap, endereco)
    setor_b0_suap.uo = campus_b_suap
    setor_b0_suap.save(update_fields=['uo'])

    campus_b_suap_siape, _ = UnidadeOrganizacional.objects.get_or_create(setor=setor_b0_siape, equivalente=campus_b_suap)

    # Recuperando os setores para pegar o campo ``uo`` atualizado
    setor_b0_suap = Setor.todos.get(pk=setor_b0_suap.pk)
    setor_b0_siape = Setor.todos.get(pk=setor_b0_siape.pk)

    # Criando setores folhas
    setor_b1_suap, _ = Setor.todos.get_or_create(sigla='B1', nome='B1', superior=setor_b0_suap)
    setor_b1_siape, _ = Setor.todos.get_or_create(sigla='B1', nome='B1', superior=setor_b0_siape, codigo='B1')

    setor_b2_suap, _ = Setor.todos.get_or_create(sigla='B2', nome='B2', superior=setor_b0_suap)
    setor_b2_siape, _ = Setor.todos.get_or_create(sigla='B2', nome='B2', superior=setor_b0_siape, codigo='B2')

    # Hierarquia C ------------------------------------
    setor_c0_suap, _ = Setor.todos.get_or_create(sigla='C0', nome='C0', superior=setor_raiz_suap)
    setor_c0_siape, _ = Setor.todos.get_or_create(sigla='C0', nome='C0', superior=setor_raiz_siape, codigo='C0')

    campus_c_suap, _ = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor_c0_suap, codigo_protocolo='24001', nome='C0', sigla='C0')
    definir_endereco(campus_c_suap, endereco)

    campus_c_suap_siape, _ = UnidadeOrganizacional.objects.get_or_create(setor=setor_c0_siape, equivalente=campus_c_suap)
    definir_endereco(campus_c_suap_siape, endereco)

    # Recuperando os setores para pegar o campo ``uo`` atualizado
    setor_c0_suap = Setor.todos.get(pk=setor_c0_suap.pk)
    setor_c0_siape = Setor.todos.get(pk=setor_c0_siape.pk)

    # Criando setores folhas
    Setor.todos.get_or_create(sigla='C1', nome='C1', superior=setor_c0_suap, codigo=None)
    Setor.todos.get_or_create(sigla='C1', nome='C1', superior=setor_c0_siape, codigo='C1')

    Setor.todos.get_or_create(sigla='C2', nome='C2', superior=setor_c0_suap, codigo=None)
    Setor.todos.get_or_create(sigla='C2', nome='C2', superior=setor_c0_siape, codigo='C2')

    # Criando os servidores --------------------------------------------------------------------------------------------

    # Criando Situações para Servidores
    situacao_ativo_permanente, _ = Situacao.objects.get_or_create(codigo=Situacao.ATIVO_PERMANENTE, nome_siape='ATIVO PERMANENTE', excluido=False)

    # Criando jornada de trabalho
    jornada_trabalho, _ = JornadaTrabalho.objects.get_or_create(codigo='01', nome='40h', excluido=False)

    # Criando cargos para servidores
    grupo_cargo_emprego, _ = GrupoCargoEmprego.objects.get_or_create(codigo='01', nome='Grupo X', sigla='X', categoria='tecnico_administrativo', excluido=False)
    cargo_emprego_a, _ = CargoEmprego.objects.get_or_create(codigo='01', nome='Cargo A', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='01', excluido=False)
    cargo_emprego_b, _ = CargoEmprego.objects.get_or_create(codigo='02', nome='Cargo B', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='01', excluido=False)

    # Criando os servidores
    kwargs_admin = dict(
        nome='admin',
        matricula='admin',
        excluido=False,
        situacao=situacao_ativo_permanente,
        cargo_emprego=cargo_emprego_a,
        setor=setor_a1_suap,
        setor_lotacao=setor_a1_siape,
        setor_exercicio=setor_a1_siape,
        email='admin@mail.gov',
        cpf='865.572.326-65',
        jornada_trabalho=jornada_trabalho,
    )
    admin = Servidor.objects.get_or_create(matricula='admin', defaults=kwargs_admin)[0]
    user = admin.user
    user.set_password('abc')
    user.is_superuser = True
    user.is_staff = True
    user.save()

    kwargs_servidor_1 = dict(
        nome='Servidor 1',
        excluido=False,
        situacao=situacao_ativo_permanente,
        cargo_emprego=cargo_emprego_a,
        setor=setor_a1_suap,
        data_inicio_exercicio_na_instituicao=datetime.date(2010, 1, 1),
        setor_lotacao=setor_a1_siape,
        setor_exercicio=setor_a1_siape,
        email='servidor.a@mail.gov',
        cpf='861.474.078-64',
        jornada_trabalho=jornada_trabalho,
    )
    servidor_1 = Servidor.objects.get_or_create(matricula='1111111', defaults=kwargs_servidor_1)[0]
    servidor_1.user.set_password('abc')
    servidor_1.user.save()

    kwargs_servidor_2 = dict(
        nome='Servidor 2',
        situacao=situacao_ativo_permanente,
        cargo_emprego=cargo_emprego_b,
        setor=setor_b1_suap,
        setor_lotacao=setor_b1_siape,
        setor_exercicio=setor_b1_siape,
        email='servidor.b@mail.gov',
        jornada_trabalho=jornada_trabalho,
        data_inicio_exercicio_na_instituicao=datetime.date(2010, 1, 1),
        cpf='817.483.818-06',
        data_inicio_exercicio_no_cargo=datetime.date(2010, 1, 1),
    )
    servidor_2 = Servidor.objects.get_or_create(matricula='2222222', defaults=kwargs_servidor_2)[0]
    servidor_2.user.set_password('abc')
    servidor_2.user.save()

    kwargs_servidor_3 = dict(
        nome='Servidor 3',
        situacao=situacao_ativo_permanente,
        cargo_emprego=cargo_emprego_b,
        setor=setor_a2_suap,
        setor_lotacao=setor_a2_siape,
        setor_exercicio=setor_a2_siape,
        data_inicio_exercicio_na_instituicao=datetime.date(2010, 1, 1),
        email='servidor.c@mail.gov',
        cpf='575.333.822-42',
        jornada_trabalho=jornada_trabalho,
    )
    servidor_3 = Servidor.objects.get_or_create(matricula='3333333', defaults=kwargs_servidor_3)[0]
    servidor_3.user.set_password('abc')
    servidor_3.user.save()

    kwargs_servidor_4 = dict(
        nome='Servidor 4',
        situacao=situacao_ativo_permanente,
        cargo_emprego=cargo_emprego_b,
        setor=setor_b2_suap,
        setor_lotacao=setor_b2_siape,
        setor_exercicio=setor_b2_siape,
        email='servidor.d@mail.gov',
        cpf='153.148.137-00',
        jornada_trabalho=jornada_trabalho,
    )

    servidor_4 = Servidor.objects.get_or_create(matricula='4444444', defaults=kwargs_servidor_4)[0]
    servidor_4.user.set_password('abc')
    servidor_4.user.save()

    # Criando Chefe de Setor

    funcao, _ = Funcao.objects.get_or_create(codigo=Funcao.CODIGO_FG, defaults=dict(nome="Chefe de Setor"))

    ServidorFuncaoHistorico.objects.get_or_create(servidor=servidor_1, data_inicio_funcao=datetime.date(2010, 1, 1), funcao=funcao, setor=setor_a1_siape, setor_suap=setor_a1_suap)

    # Criando pessoa jurídica

    pessoa_juridica = PessoaJuridica.objects.get_or_create(cnpj='45.006.424/0001-00', defaults=dict(nome='Pessoa Jurídica'))[0]
    # Criando prestador de serviço
    kwargs_prestador_1 = dict(nome='Prestador 1', setor=setor_a0_suap)
    PrestadorServico.objects.get_or_create(cpf='506.213.644-01', defaults=kwargs_prestador_1)
    prestador_1 = PrestadorServico.objects.get(cpf='506.213.644-01')
    ocupacao = Ocupacao.objects.get_or_create(codigo='', descricao='Teste Ocupação')[0]
    OcupacaoPrestador.objects.create(prestador=prestador_1, ocupacao=ocupacao, empresa=pessoa_juridica, data_inicio=datetime.date(2010, 1, 1), data_fim=datetime.date(2100, 1, 1))
    prestador_1.user.set_password('123')
    prestador_1.user.save()

    # Criando prestador de serviço
    kwargs_prestador_2 = dict(nome='Parecerista Obra', setor=setor_a0_suap)
    PrestadorServico.objects.get_or_create(cpf='342.456.058-80', defaults=kwargs_prestador_2)
    prestador_2 = PrestadorServico.objects.get(cpf='342.456.058-80')
    ocupacao = Ocupacao.objects.get_or_create(codigo='', descricao='Teste Ocupação')[0]

    OcupacaoPrestador.objects.create(prestador=prestador_2, ocupacao=ocupacao, empresa=pessoa_juridica, data_inicio=datetime.date(2010, 1, 1), data_fim=datetime.date(2100, 1, 1))
    prestador_2.user.set_password('abcd')
    prestador_2.user.save()

    # Criando Funções
    funcao, _ = Funcao.objects.get_or_create(nome="Chefe de Setor", codigo=Funcao.CODIGO_FG)
    diretoria_reitor, _ = Funcao.objects.get_or_create(nome="Reitor", codigo=Funcao.CODIGO_CD)

    # Criando Atividades
    Atividade.objects.get_or_create(codigo=Atividade.REITOR, nome='Reitor')
