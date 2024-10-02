from django.db.models import Min

from cnpq.models import AreaAvaliacao, ClassificacaoPeriodico, PeriodicoRevista
from djtools.assincrono import task
import xlrd

from djtools.utils import XlsResponse


@task('Lendo conteúdo da planilha periódico webqualis')
def importar_planilha_periodico_qualis(file_content, task=None):
    if not file_content:
        raise Exception('Arquivo vazio.')
    try:
        workbook = xlrd.open_workbook(file_contents=file_content)
        sheet = workbook.sheet_by_index(0)
    except Exception:
        raise Exception('Não foi possível processar a planilha. Verifique se o formato do arquivo é .xls ou .xlsx.')
    issn_anterior = ''
    for row in task.iterate(list(range(1, sheet.nrows))):
        try:
            issn = (sheet.cell_value(row, 0)).strip().replace('-', '')
            titulo = (sheet.cell_value(row, 1)).strip()
            nome_area_avaliacao = (sheet.cell_value(row, 2)).strip()
            estrato = (sheet.cell_value(row, 3)).strip()
            if len(issn) <= 8:
                qsarea = AreaAvaliacao.objects.filter(nome=nome_area_avaliacao)
                if qsarea.exists():
                    area_avaliacao = qsarea[0]
                else:
                    area_avaliacao, _ = AreaAvaliacao.objects.get_or_create(nome=nome_area_avaliacao)
                if issn != issn_anterior:
                    qsperiodico = PeriodicoRevista.objects.filter(issn=issn)
                    if qsperiodico.exists():
                        periodico = qsperiodico[0]
                    else:
                        periodico, _ = PeriodicoRevista.objects.get_or_create(issn=issn, nome=titulo)

                ClassificacaoPeriodico.objects.get_or_create(periodico=periodico, estrato=estrato, area_avaliacao=area_avaliacao)
                issn_anterior = issn

        except ValueError:
            raise Exception('Alguma coluna da planilha possui um valor incorreto.')
        except Exception:
            raise Exception('Erro inesperado, por favor verifique sua planilha e tente novamente.')
    task.finalize('Importação realizada com sucesso.', '/cnpq/importar_lista_completa/')


@task('Exportar Indicadores com Publicação para XLS')
def exportar_indicadores_com_publicacao_xls(modelos, task=None):
    rows = [['#', 'Ano', 'Tipo', 'Servidor', 'Publicação']]
    count = 0
    for modelo in task.iterate(modelos):
        autores = set()
        for autor in modelo.get_autores_unicos():
            autores.add(autor.pessoa.nome)
        count += 1
        row = [count, modelo.get_ano(), modelo.get_tipo(), ', '.join(autores), modelo]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Indicadores sem Publicação para XLS')
def exportar_indicadores_sem_publicacao_xls(dados, task=None):
    exportacao = dict()

    for dado in task.iterate(dados):
        if dado == 'Produções Bibliográficas':
            rows = [['#', 'Ano', 'Tipo', 'Servidor', 'Periódico/Revista', 'ISSN', 'Estrato', 'Publicação']]
            count = 0
            modelos = dados[dado]
            modelos = modelos.annotate(estrato=Min('artigo__periodico__estratos_qualis__estrato'))
            for modelo in modelos:
                titulo_periodico_revista = ''
                issn = ''
                estrato = ''
                autores = set()
                if hasattr(modelo, 'artigo'):
                    titulo_periodico_revista = modelo.artigo.titulo_periodico_revista
                    issn = modelo.artigo.issn
                    estrato = modelo.estrato

                for autor in modelo.get_autores_unicos():
                    autores.add(autor.pessoa.nome)
                count += 1
                row = [count, modelo.get_ano(), modelo.get_tipo(), ', '.join(autores), titulo_periodico_revista, issn, estrato, modelo]
                rows.append(row)
        else:
            rows = [['#', 'Ano', 'Tipo', 'Servidor', 'Publicação']]
            count = 0
            modelos = dados[dado]
            for modelo in modelos:
                autores = set()
                for autor in modelo.get_autores_unicos():
                    autores.add(autor.pessoa.nome)
                count += 1
                row = [count, modelo.get_ano(), modelo.get_tipo(), ', '.join(autores), modelo]
                rows.append(row)

        exportacao[dado] = rows
    return XlsResponse(exportacao, processo=task)
