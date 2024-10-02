from djtools.assincrono import task
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse


@task('Exportar Contratos para XLS')
def buscar_contrato_export_to_xls(contratos, task=None):
    rows = [['#', 'Número', 'Contratada', 'Período de Vigência', 'Termos Aditivos']]

    contador = 0
    for contrato in task.iterate(contratos):
        contador += 1
        if contrato.data_vencimento != contrato.data_fim:
            data_fim = 'Prorrogado de {} para {}'.format(format_(contrato.data_fim),
                                                         format_(contrato.data_vencimento))
        else:
            data_fim = '{}'.format(format_(contrato.data_fim))
        vigencia = 'Início: {}, Vencimento: {}'.format(format_(contrato.data_inicio), format_(data_fim))
        aditivos = ''
        for aditivo in contrato.aditivos_set.all():
            aditivos = aditivos + '{}, '.format(aditivo)

        row = [contador, format_(contrato.numero), format_(contrato.pessoa_contratada), format_(vigencia),
               format_(aditivos[:-2])]
        rows.append(row)
    return XlsResponse(rows, processo=task)
