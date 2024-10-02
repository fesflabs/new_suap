from djtools.assincrono import task
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse


@task('Exportar Relatório de Dimensão para XLS')
def relatorio_dimensao_export_to_xls(quantidade_projetos, quantidade_participantes, participantes_por_area_tematica, task=None):
    task.start_progress()
    total_projetos = 0
    total_projetos_aprovados = 0
    rows = [['Projetos por Edital']]

    row = ['Edital', 'Projetos Submetidos', 'Projetos Aprovados']
    rows.append(row)
    for info in quantidade_projetos:
        total_projetos = total_projetos + info['total']
        total_projetos_aprovados = total_projetos_aprovados + info['aprovados']

        row = [format_(info['edital']), format_(info['total']), format_(info['aprovados'])]
        rows.append(row)
    task.update_progress(20)
    row = ['Total', format_(total_projetos), format_(total_projetos_aprovados)]
    rows.append(row)
    row = ['']
    rows.append(row)
    row = ['Projetos por Área Temática (Submetidos/Aprovados)']
    rows.append(row)
    row = [
        'Edital',
        'Comunicação',
        'Cultura',
        'Direitos Humanos e Justiça',
        'Educação',
        'Meio Ambiente',
        'Saúde',
        'Tecnologia e Produção',
        'Trabalho',
        'Multidisciplinar',
        'Outros/Não Informado',
        'Total Submetido',
        'Total Aprovado',
    ]
    rows.append(row)

    for info in quantidade_projetos:
        row = [
            format_(info['edital']),
            format_('%s/%s') % (info['comunicacao_total'], info['comunicacao_aprovados']),
            format_('%s/%s') % (info['cultura_total'], info['cultura_aprovados']),
            format_('%s/%s') % (info['direito_total'], info['direito_aprovados']),
            format_('%s/%s') % (info['educacao_total'], info['educacao_aprovados']),
            format_('%s/%s') % (info['meio_ambiente_total'], info['meio_ambiente_aprovados']),
            format_('%s/%s') % (info['saude_total'], info['saude_aprovados']),
            format_('%s/%s') % (info['tecnologia_total'], info['tecnologia_aprovados']),
            format_('%s/%s') % (info['trabalho_total'], info['trabalho_aprovados']),
            format_('%s/%s') % (info['multidisciplinar_total'], info['multidisciplinar_aprovados']),
            format_('%s/%s') % (info['outros_total'], info['outros_aprovados']),
            format_(info['total']),
            format_(info['aprovados']),
        ]
        rows.append(row)
    task.update_progress(40)
    row = ['']
    rows.append(row)
    row = ['Participantes por Edital']
    rows.append(row)
    row = ['Edital', 'Bolsistas (Docentes/Téc. Adm/Discentes)', 'Voluntários (Docentes/Téc. Adm/Discentes)']
    rows.append(row)
    for info in quantidade_participantes:
        row = [
            format_(info['edital']),
            format_('%s/%s/%s') % (
                info['docentes_bolsistas'], info['tecnicos_adm_bolsistas'], info['alunos_bolsistas']),
            format_('%s/%s/%s') % (
                info['docentes_voluntarios'], info['tecnicos_adm_voluntarios'], info['alunos_voluntarios']),
        ]

        rows.append(row)
    task.update_progress(60)

    row = ['']
    rows.append(row)
    row = ['Participantes por Área Temática']
    rows.append(row)
    row = ['Área', 'Bolsistas (Docentes/Téc. Adm/Discentes)', 'Voluntários (Docentes/Téc. Adm/Discentes)']
    rows.append(row)

    for info in participantes_por_area_tematica:
        row = [
            format_(info['area']),
            format_('%s/%s/%s') % (info['docentes_bolsistas'], info['tec_adm_bolsistas'], info['alunos_bolsistas']),
            format_('%s/%s/%s') % (
                info['docentes_voluntarios'], info['tec_adm_voluntarios'], info['alunos_voluntarios']),
        ]

        rows.append(row)

    task.update_progress(80)

    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Lições Aprendidas para XLS')
def relatorio_licoes_aprendidas_to_xls(licoes, task=None):
    rows = [['#', 'Campus', 'Edital', 'Projeto', 'Coordenador', 'Lição Aprendida', 'Área de Conhecimento']]
    contador = 0
    for licao in task.iterate(licoes):
        contador += 1
        if licao.projeto.vinculo_coordenador:
            coordenador = licao.projeto.vinculo_coordenador.pessoa.nome
        else:
            coordenador = licao.projeto.get_responsavel().pessoa.nome
        row = [
            contador,
            format_(licao.projeto.uo.nome),
            format_(licao.projeto.edital),
            format_(licao.projeto.titulo),
            format_(coordenador),
            format_(licao.descricao),
            format_(licao.area_licao_aprendida),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Equipes de Projetos para XLS')
def listar_equipes_dos_projetos_to_xls(dados_do_projeto, task=None):
    rows = [['#', 'Campus', 'Edital', 'Projeto', 'Nome', 'Vínculo', 'Titulação', 'Curso']]

    contador = 1
    for dados in task.iterate(dados_do_projeto):
        if dados['lattes']:
            nome_pessoa = '{} ({}) - {}'.format(dados['nome'], dados['matricula'], dados['lattes'])
        else:
            nome_pessoa = '{} ({})'.format(dados['nome'], dados['matricula'])

        row = [
            contador,
            format_(dados['campus']),
            format_(dados['edital']),
            format_(dados['projeto']),
            format_(nome_pessoa),
            format_(dados['vinculo']),
            format_(dados['titulacao']),
            format_(dados['curso']),
        ]
        contador += 1
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Projetos em Atraso para XLS')
def listar_projetos_em_atraso_export_to_xls(projetos, task=None):
    rows = [['#', 'Campus', 'Edital', 'Projeto', 'Coordenador', 'Email', 'Fim da Execução']]

    contador = 0
    for projeto in task.iterate(projetos):
        contador += 1
        if projeto.vinculo_coordenador:
            coordenador = projeto.vinculo_coordenador
        else:
            coordenador = projeto.get_responsavel()
        row = [
            contador,
            format_(projeto.uo.nome),
            format_(projeto.edital),
            format_(projeto.titulo),
            format_(coordenador.pessoa.nome),
            format_(coordenador.pessoa.email),
            format_(projeto.fim_execucao),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Avaliadores de Projetos para XLS')
def listar_avaliadores_de_projetos_export_to_xls(avaliadores, task=None):
    rows = [['#', 'Nome', 'Matrícula', 'Instituição', 'Email', 'Áreas Temáticas']]
    contador = 0
    for avaliador in task.iterate(avaliadores):
        matricula = '-'
        if avaliador.vinculo.eh_servidor():
            matricula = (avaliador.vinculo.relacionamento.matricula,)

        areas_tematicas = avaliador.get_areas_tematicas().values_list('descricao', flat=True)
        areas = ', '.join(areas_tematicas)
        row = [contador, format_(avaliador.vinculo.pessoa.nome), format_(matricula), format_(avaliador.get_instituicao()), format_(avaliador.get_email()), format_(areas)]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Caracterização de Beneficiários para XLS')
def relatorio_caracterizacao_beneficiarios_to_xls(registros, task=None):
    rows = [['#', 'Campus', 'Edital', 'Projeto', 'Coordenador', 'Tipo de Beneficiário', 'Quantidade Prevista', 'Quantidade Atendida']]

    contador = 0
    for registro in task.iterate(registros):
        contador += 1
        coordenador = registro.projeto.vinculo_coordenador.pessoa.nome
        row = [
            contador,
            format_(registro.projeto.uo.nome),
            format_(registro.projeto.edital),
            format_(registro.projeto.titulo),
            format_(coordenador),
            format_(registro.tipo_beneficiario.descricao),
            format_(registro.quantidade),
            format_(registro.quantidade_atendida),
        ]
        rows.append(row)
    XlsResponse(rows, processo=task)
