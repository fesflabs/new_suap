from djtools.assincrono import task
from djtools.utils import XlsResponse
from gestao.models import Variavel
from rh.models import UnidadeOrganizacional


@task(name='Gestao >> Recuperar_valor Variavel de Gestão')
def recuperar_valor(variaveis, uos, task=None):
    task.count(variaveis, uos)
    for variavel in task.iterate(variaveis):
        print(variavel.pk)
        Variavel.recuperar_valor(variavel.pk, 0)
        for uo in task.iterate(uos):
            print(uo)
            Variavel.recuperar_valor(variavel.pk, uo.pk)
    task.finalize("Variáveis de Gestão calculadas com sucesso.", '')


@task('Exportar Detalhamento de Variáveis de Gestão')
def detalhar_variavel_ac_xls(qs_alunos, task=None):
    from gestao.views import get_exportacao

    rows = get_exportacao(
        qs_alunos,
        ['matricula', 'pessoa_fisica.nome', 'pessoa_fisica.cpf', 'curso_campus', 'curso_campus.diretoria.setor.uo.nome', 'ano_letivo', 'periodo_letivo'],
        ['Matrícula', 'Nome', 'CPF', 'Curso', 'Campus', 'Ano Inicial', 'Período Inicial'],
        task,
    )
    return XlsResponse(rows, processo=task)


@task('Exportar Detalhamento de Variáveis de Gestão')
def detalhar_variavel_am_xls(qs_matriculas, task=None):
    from gestao.views import get_exportacao_apenas_dados
    rows = get_exportacao_apenas_dados(
        qs_matriculas,
        [
            'aluno.matricula',
            'aluno.pessoa_fisica.nome',
            'aluno.pessoa_fisica.cpf',
            'aluno.curso_campus',
            'aluno.curso_campus.diretoria',
            'aluno.ano_letivo',
            'aluno.periodo_letivo',
        ],
        0,
        task=task,
    )

    return XlsResponse(rows, processo=task)


@task('Processar Indicadores de Gestão')
def processar_indicadores(indicadores, user, task=None):
    orgao_regulamentador = 'Outros'
    for indicador in task.iterate(indicadores):
        orgao_regulamentador = indicador.orgao_regulamentador
        indicador.get_valor_formatado(user=user)
        for uo in UnidadeOrganizacional.objects.suap().all():
            indicador.get_valor_formatado(uo, user=user)
    return task.finalize('Processamento finalizado', f'/gestao/exibir_indicadores/{orgao_regulamentador}/')
