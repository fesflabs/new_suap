from djtools.assincrono import task
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse


@task('Exportar Relatório de Acompanhamentos para XLS')
def exportar_relatorio_acompanhamento(qs, task=None):
    rows = [['#', 'Aluno', 'Curso', 'Turma', 'Situação', 'Categorias', 'Encaminhamentos', 'Data de Abertura do Encaminhamento', 'Interessado']]
    count = 0
    for obj in task.iterate(qs):
        count += 1
        row = [
            count,
            obj.aluno,
            obj.aluno.curso_campus,
            obj.aluno.get_ultima_matricula_periodo().turma,
            format_(obj.get_situacao_display()),
            format_(obj.get_categorias()),
            format_(obj.get_encaminhamentos()),
            obj.data,
        ]
        interessados = []
        for vinculo in obj.get_interessados():
            interessados.append('%s (%s)' % (vinculo.pessoa.nome, vinculo.user.username))
        row.append(format_(interessados))
        rows.append(row)

    return XlsResponse({'Registros': rows}, processo=task)
