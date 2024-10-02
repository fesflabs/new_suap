from djtools.assincrono import task
from djtools.utils import XlsResponse


@task('Exportar Indicadores PDI para XLS')
def indicadores_pdi_export_to_xls(lista_indicadores, task=None):
    rows = [['Indicadores']]
    row = ['Indicador', 'Unid. Administrativa', 'Valor Meta', 'Valor Meta Trimestral', 'Valor Real']
    rows.append(row)

    for resultado in task.iterate(lista_indicadores):
        row = [resultado['indicador'], resultado['uo'], resultado['valor_meta'], resultado['valor_trimestral'], resultado['valor_real']]
        rows.append(row)

    return XlsResponse(rows, processo=task)


@task('Exportar Resultados de Indicadores para XLS')
def linhadotempo_export_to_xls(lista_inds, task=None):
    rows = [['Resultado do Indicador Linha do Tempo']]
    row = ['Indicador', 'Unidade Administrativa', 'Ano', 'Meta Anual', 'Valor Alcançado']
    rows.append(row)

    for resultado in task.iterate(lista_inds):
        row = [resultado['indicador'], resultado['uo'], resultado['ano'], resultado['meta_anual'], resultado['valor_alcancado']]
        rows.append(row)

    return XlsResponse(rows, processo=task)
