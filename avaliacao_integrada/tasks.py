import tempfile

import xlsxwriter

from avaliacao_integrada.models import Segmento, Indicador
from djtools.assincrono import task
from edu.models import Modalidade


@task('Relatório em XLSX')
def relatorio_xlsx(respostas, task=None):
    response = tempfile.NamedTemporaryFile(suffix='.xlsx', mode='w+b', delete=False)
    workbook = xlsxwriter.Workbook(response)
    worksheet = workbook.add_worksheet('relatorio')

    header = ['#', 'Indicador', 'Subsídio p/ Avaliações', 'Modalidade', 'ID Respondente', 'Eixo', 'Dimensão', 'Macroprocesso', 'Segmento', 'Campus', 'Curso', 'Resposta']
    rows = [header]
    idx = 0
    for obj in task.iterate(respostas.order_by('indicador', 'respondente')):
        row = [idx + 1]
        row.append(str(obj.indicador.aspecto))
        row.append(','.join(obj.indicador.subsidio_para.all().values_list('descricao', flat=True)))
        row.append(str(obj.objeto) if isinstance(obj.objeto, Modalidade) else '-')
        row.append(str(obj.respondente_id))
        row.append(str(obj.indicador.macroprocesso.dimensao.eixo))
        row.append(str(obj.indicador.macroprocesso.dimensao))
        row.append(str(obj.indicador.macroprocesso))
        row.append(str(obj.respondente.segmento))

        if obj.respondente.segmento_id in Segmento.ALUNOS:
            row.append(str(obj.respondente.get_unidade_vinculacao()))
            row.append(str(obj.respondente.get_curso_vinculacao()))
        elif obj.respondente.segmento_id in Segmento.SERVIDORES:
            row.append(str(obj.respondente.get_unidade_atuacao_servidor()))
            row.append(str('-'))
        else:
            row.append(str('-'))
            row.append(str('-'))

        if obj.indicador.tipo_resposta == Indicador.MULTIPLA_ESCOLHA:
            for valor in obj.valor.split('::'):
                if valor != '':
                    rows.append(row + [str(valor)])
        else:
            row.append(str(obj.valor))
            rows.append(row)
        idx += 1

    for row_idx, row_data in enumerate(rows):
        for col_idx, col in enumerate(row_data):
            worksheet.write(row_idx, col_idx, col)

    workbook.close()
    response.close()
    return task.finalize('Arquivo gerado com sucesso.', '..', file_path=response.name)


@task('Reprocessar público alvo')
def reprocessar_publico_alvo(avaliacao, excluir, task=None):
    avaliacao.identificar_respondentes(excluir=excluir, task=task)
    return task.finalize('Público-Alvo reprocessado com sucesso.', '/avaliacao_integrada/avaliacao/{}/'.format(avaliacao.pk))
