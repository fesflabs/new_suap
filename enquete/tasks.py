from collections import OrderedDict

from djtools.assincrono import task
from djtools.utils import XlsResponse, render_html_file
from enquete.forms import FiltrarRespostasForm
from enquete.models import Resposta
from rh.models import Servidor


@task('Processar Respostas da Enquete')
def processar_respostas_enquete(request, enquete, title, task=None):
    form = FiltrarRespostasForm(request.GET or None, enquete=enquete)
    form.ACTION = f'/enquete/ver_resultados/{enquete.id}/'
    participantes = form.get_participantes()
    respostas_participantes = form.get_respostas_participantes().values(
        'vinculo__pessoa__nome', 'data_cadastro', 'data_ultima_resposta'
    ).distinct('vinculo__pessoa__nome')
    graficos = enquete.get_graficos_resultado(participantes, task)
    contexto = dict(graficos=graficos, enquete=enquete, participantes=participantes, respostas_participantes=respostas_participantes, form=form, title=title)
    return render_html_file('enquete/templates/ver_resultados.html', contexto, request, task)


@task('Exportar Resultados de Enquetes para XLS')
def exportar_resultado_to_xls(enquete, participantes, task=None):
    enquete.get_graficos_resultado(participantes, task)
    exportacao = OrderedDict()

    if enquete.resultado_publico:
        exportacao['Participantes'] = [
            ['#', 'CPF', 'Nome', 'Matrícula', 'E-mail Institucional', 'Campus Lotação', 'Campus', 'Setor', 'Cargo']
        ]
        count = 0
        for vinculo in task.iterate(participantes):
            count += 1
            relacionamento = vinculo.relacionamento
            cpf = vinculo.pessoa.pessoafisica.cpf
            nome = vinculo.pessoa.nome
            matricula = vinculo.relacionamento.matricula or '-'
            uo_setor_lotacao = '-'
            setor = '-'
            uo = '-'
            cargo_emprego = '-'
            email_institucional = '-'
            if type(relacionamento) == Servidor:
                uo_setor_lotacao = relacionamento.setor_lotacao.uo if relacionamento.setor_lotacao else '-'
                setor = relacionamento.setor
                uo = relacionamento.setor.uo if relacionamento.setor else '-'
                cargo_emprego = relacionamento.cargo_emprego
                email_institucional = relacionamento.email_institucional
            exportacao['Participantes'].append([count, cpf, nome, matricula, email_institucional, uo_setor_lotacao, uo, setor, cargo_emprego])
    if hasattr(enquete, 'categorias'):
        for categoria in task.iterate(enquete.categorias):
            cat_nome = 'Categoria Ordem #{}'.format(categoria.ordem)
            if enquete.resultado_publico:
                exportacao[cat_nome] = [['Participantes'] + categoria.cabecalho + ['Data Resposta'] + ['Data da última resposta']]
            else:
                exportacao[cat_nome] = [categoria.cabecalho + ['Data Resposta'] + ['Data da última resposta']]
            if hasattr(categoria, 'tabela'):
                for idx, row in enumerate(categoria.tabela):
                    resp = row[0]
                    cpf = '-'
                    data_cadastro = '-'
                    data_ultima_resposta = '-'
                    if type(resp) == Resposta:
                        cpf = resp.vinculo.pessoa.pessoafisica.cpf
                        data_cadastro = resp.data_cadastro
                        data_ultima_resposta = resp.data_ultima_resposta
                    if enquete.resultado_publico:
                        linha = [cpf] + row + [data_cadastro] + [data_ultima_resposta]
                    else:
                        linha = row + [data_cadastro] + [data_ultima_resposta]
                    exportacao[cat_nome].append(linha)
    return XlsResponse(exportacao, processo=task)
