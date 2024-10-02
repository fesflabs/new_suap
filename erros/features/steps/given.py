# -*- coding: utf-8 -*-

from behave import given
from django.contrib.auth.models import Group

from comum.models import Ano, User
from edu.features.steps.given import cadastrar_aluno, step_cadastros_feature_002
from edu.models import Aluno, Cidade, FormaIngresso, CursoCampus, Matriz, Turno
from edu.models.diretorias import Diretoria
from rh.models import JornadaTrabalho, CargoEmprego, Situacao, Servidor, Setor, PessoaFisica


def mudar_data(context, data):
    context.execute_steps('Quando a data do sistema for "{}"'.format(data))


@given('os cadastros de usuários do módulo de erros')
def step_cadastros_feature_001(context):

    mudar_data(context, '10/03/2021')

    # Cenário: Cadastrar Diretoria Acadêmica
    diretoria = Diretoria.objects.get_or_create(setor=Setor.objects.get(sigla='DIAC/CEN'))[0]

    situacao = Situacao.objects.get(codigo=Situacao.ATIVO_PERMANENTE)
    cargo_emprego = CargoEmprego.objects.get(codigo='01')
    setor_suap = Setor.todos.get(sigla='DIAC/CEN', codigo__isnull=True)
    setor_siape = Setor.todos.get(sigla='DIAC/CEN', codigo__isnull=False)
    jornada_trabalho = JornadaTrabalho.objects.get(codigo='01')

    if not Servidor.objects.filter(matricula='103011').exists():
        servidor = Servidor.objects.get_or_create(
            nome='Atendente Principal do Erro',
            matricula='103011',
            excluido=False,
            situacao=situacao,
            cargo_emprego=cargo_emprego,
            setor=setor_suap,
            setor_lotacao=setor_siape,
            setor_exercicio=setor_siape,
            email='atendente_principal_erro@ifrn.edu.br',
            cpf='404.991.530-81',
            jornada_trabalho=jornada_trabalho,
        )[0]
        user = servidor.user or User()
        user.matricula = '103011'
        user.set_password('abcd')
        user.is_staff = True
        user.save()
        user.groups.add(Group.objects.get(name='Servidor'))
        user.groups.add(Group.objects.get(name='Desenvolvedor'))
        servidor.eh_servidor = True
        servidor.save()

    if not Servidor.objects.filter(matricula='103012').exists():
        servidor = Servidor.objects.get_or_create(
            nome='Atendente Secundário do Erro',
            matricula='103012',
            excluido=False,
            situacao=situacao,
            cargo_emprego=cargo_emprego,
            setor=setor_suap,
            setor_lotacao=setor_siape,
            setor_exercicio=setor_siape,
            email='atendente_secundario_erro@ifrn.edu.br',
            cpf='893.341.100-31',
            jornada_trabalho=jornada_trabalho,
        )[0]
        user = servidor.user or User()
        user.matricula = '103012'
        user.set_password('abcd')
        user.is_staff = True
        user.save()
        user.groups.add(Group.objects.get(name='Servidor'))
        user.groups.add(Group.objects.get(name='Desenvolvedor'))
        servidor.eh_servidor = True
        servidor.save()

    if not Servidor.objects.filter(matricula='103013').exists():
        servidor = Servidor.objects.get_or_create(
            nome='Servidor Interessado no Erro',
            matricula='103013',
            excluido=False,
            situacao=situacao,
            cargo_emprego=cargo_emprego,
            setor=setor_suap,
            setor_lotacao=setor_siape,
            setor_exercicio=setor_siape,
            email='servidor_interessado_erro@ifrn.edu.br',
            cpf='699.590.990-91',
            jornada_trabalho=jornada_trabalho,
        )[0]
        user = servidor.user or User()
        user.matricula = '103013'
        user.set_password('abcd')
        user.is_staff = True
        user.save()
        user.groups.add(Group.objects.get(name='Servidor'))
        servidor.eh_servidor = True
        servidor.save()
        diretoria.save()

    if not Aluno.objects.filter(matricula='103014').exists():
        pessoafisica = PessoaFisica.objects.create(
            nome='Aluno Interessado no Erro',
            cpf='394.184.910-79'
        )
        Turno.objects.get_or_create(descricao='Matutino')
        step_cadastros_feature_002(None)
        cadastrar_aluno(pessoafisica, Cidade.objects.first(), Ano.objects.first(), FormaIngresso.objects.first(), CursoCampus.objects.first(), Matriz.objects.first())
