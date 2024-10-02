from django.conf import settings
from behave import given
from django.contrib.auth.models import Group

from djtools.new_tests.utils import abrir_debugger, go_url
from rh.models import Setor, Situacao, CargoEmprego, JornadaTrabalho, Servidor, GrupoCargoEmprego
from django.apps.registry import apps
import datetime
from comum.models import Ano

PessoaFisica = apps.get_model('rh', 'PessoaFisica')
UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
if 'edu' in settings.INSTALLED_APPS:
    Aluno = apps.get_model('edu', 'Aluno')
    SituacaoMatricula = apps.get_model('edu', 'SituacaoMatricula')
    Diretoria = apps.get_model('edu', 'Diretoria')
    CursoCampus = apps.get_model('edu', 'CursoCampus')
    Modalidade = apps.get_model('edu', 'Modalidade')
    NivelEnsino = apps.get_model('edu', 'NivelEnsino')
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
@given('acesso a página "{url}"')
def step_acessa_pagina(context, url):
    go_url(context, url)


@given('os seguintes usuários')
def step_seguintes_usuarios(context):
    for row in context.table:
        setor_suap = Setor.todos.get(sigla=row['Setor'], codigo__isnull=True)
        setor_siape = Setor.todos.get(sigla=row['Lotação'], codigo__isnull=False)
        situacao = Situacao.objects.get(codigo=Situacao.ATIVO_PERMANENTE)
        cargo_emprego = CargoEmprego.objects.get(codigo='01')
        jornada_trabalho = JornadaTrabalho.objects.get(codigo='01')
        grupos = row['Grupo'].split(',')
        for grupo_name in grupos:
            grupo = Group.objects.get(name=grupo_name.strip())
            if grupo_name == 'Aluno':

                modalidade = Modalidade.objects.first()
                if not modalidade:
                    modalidade = Modalidade()
                    modalidade.descricao = 'Técnico Integrado'
                    modalidade.nivel_ensino = NivelEnsino.objects.get(pk=NivelEnsino.MEDIO)
                    modalidade.save()

                diretoria = Diretoria.objects.filter(setor=setor_suap).first()
                if not diretoria:
                    diretoria = Diretoria()
                    diretoria.setor = setor_suap
                    diretoria.save()

                curso = CursoCampus.objects.filter(codigo='TECINFO').first()
                if not curso:
                    curso = CursoCampus()
                    curso.descricao = 'Técnico em Informática'
                    curso.codigo = 'TECINFO'
                    curso.diretoria = diretoria
                    curso.ativo = True
                    curso.modalidade = modalidade
                    curso.save()

                qs = Aluno.objects.filter(matricula=row['Matrícula'])
                if not qs.exists():
                    ano, created = Ano.objects.get_or_create(ano='2020')
                    situacao = SituacaoMatricula.objects.get_or_create(descricao='Matriculado', ativo=True)[0]

                    pessoafisica = PessoaFisica.objects.get_or_create(
                        nome=row['Nome'],
                        lattes='http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=K4758430D7',
                        cpf=row['CPF'],
                        email_secundario=row['Email'],
                        nascimento_data='2010-01-01',
                    )[0]
                    aluno = Aluno.objects.get_or_create(
                        matricula=row['Matrícula'],
                        pessoa_fisica=pessoafisica,
                        ano_letivo=ano,
                        periodo_letivo=1,
                        periodo_atual=1,
                        situacao=situacao,
                        ano_let_prev_conclusao=datetime.datetime.now().year,
                        curso_campus=curso,
                    )[0]
                else:
                    qs.update(matricula=row['Matrícula'])
                    aluno = qs[0]
                    pessoafisica = aluno.pessoa_fisica
                    pessoafisica.cpf = row['CPF']
                    pessoafisica.nome = row['Nome']
                    pessoafisica.email_secundario = row['Email']
                    pessoafisica.nascimento_data = '2010-01-01'
                pessoafisica.username = aluno.matricula
                pessoafisica.save()
                aluno.pessoa_fisica.eh_aluno = True
                aluno.pessoa_fisica.save()
                aluno.save()

                user = pessoafisica.user
                user.set_password(row['Senha'])
                user.is_staff = True
                user.groups.add(grupo)
                user.save()

            else:
                grupo_cargo_emprego = GrupoCargoEmprego.objects.get_or_create(codigo='313', nome='Grupo Saude 1', sigla='X', categoria='tecnico_administrativo', excluido=False)[0]

                if grupo_name == 'Auxiliar de Enfermagem':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701411', nome='AUXILIAR DE ENFERMAGEM', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NI', excluido=False
                    )[0]

                elif grupo_name == 'Médico':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701047', nome='MEDICO-AREA', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NS', excluido=False
                    )[0]

                elif grupo_name == 'Odontólogo':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701064', nome='ODONTOLOGO - 40 HORAS', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NS', excluido=False
                    )[0]
                elif grupo_name == 'Técnico em Saúde Bucal':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701241', nome='TECNICO EM HIGIENE DENTAL', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NI', excluido=False
                    )[0]
                elif grupo_name == 'Enfermeiro':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701029', nome='ENFERMEIRO-AREA', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NS', excluido=False
                    )[0]
                elif grupo_name == 'Técnico em Enfermagem':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701233', nome='TECNICO EM ENFERMAGEM', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NI', excluido=False
                    )[0]
                elif grupo_name == 'Fisioterapeuta':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701038', nome='FISIOTERAPEUTA', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NI', excluido=False
                    )[0]
                elif grupo_name == 'Psicólogo':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701060', nome='PSICOLOGO-AREA', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NI', excluido=False
                    )[0]
                elif grupo_name == 'Nutricionista':
                    cargo_emprego = CargoEmprego.objects.get_or_create(
                        codigo='701055', nome='NUTRICIONISTA-HABILITACAO', grupo_cargo_emprego=grupo_cargo_emprego, sigla_escolaridade='NI', excluido=False
                    )[0]

                kwargs_servidor = dict(
                    nome=row['Nome'],
                    excluido=False,
                    situacao=situacao,
                    cargo_emprego=cargo_emprego,
                    setor=setor_suap,
                    setor_lotacao=setor_siape,
                    setor_exercicio=setor_siape,
                    email=row['Email'],
                    cpf=row['CPF'],
                    jornada_trabalho=jornada_trabalho,
                    data_inicio_exercicio_no_cargo='2019-03-01'
                )
                servidor, _ = Servidor.objects.get_or_create(matricula=row['Matrícula'], defaults=kwargs_servidor)

                user = servidor.user
                user.set_password(row['Senha'])
                user.is_staff = True
                user.groups.add(grupo)
                user.save()
                servidor.eh_servidor = True
                servidor.save()


@given('a atual página')
def step_atual_pagina(context):
    pass


@given('abro o debugger')
def step_abro_debugger(context):
    abrir_debugger(context)
