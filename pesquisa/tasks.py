from cnpq.models import CurriculoVittaeLattes
from djtools.assincrono import task
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse


@task('Exportar Lista de Avaliadores para XLS')
def listar_avaliadores_export_to_xls(avaliadores, task=None):
    rows = [['#', 'Nome', 'Email', 'Lattes', 'Área de Conhecimento']]

    contador = 0
    for avaliador in task.iterate(avaliadores):
        areas = list()
        for area in avaliador.areas_de_conhecimento.all():
            areas.append(area.descricao)

        lattes = '-'
        vinculo = avaliador.get_vinculo()
        if CurriculoVittaeLattes.objects.filter(vinculo=vinculo).exists():
            lattes = 'http://lattes.cnpq.br/{}'.format(CurriculoVittaeLattes.objects.filter(vinculo=vinculo)[0].numero_identificador)
        row = [contador, format_(avaliador.nome), format_(avaliador.email), format_(lattes), format_(', '.join(areas))]
        rows.append(row)
        contador += 1
    return XlsResponse(rows, processo=task)


@task('Exportar Equipe dos Projetos para XLS')
def listar_equipes_dos_projetos_export_to_xls(projetos, task=None):
    rows = [['#', 'Projeto', 'Área de Conhecimento', 'Nome', 'Matrícula', 'Email', 'Lattes', 'Vínculo', 'Ativo', 'Titulação', 'Curso', 'Agência', 'Banco', 'Conta']]

    contador = 0
    for projeto in task.iterate(projetos):
        for participacao in projeto.participacao_por_vinculo.all():
            contador += 1
            agencia = '-'
            banco = '-'
            conta = '-'

            participante = participacao.get_participante()
            matricula = participacao.get_identificador()
            if participacao.ativo:
                ativo = 'Sim'
            else:
                ativo = 'Não'
            titulacao = participacao.get_titulacao()
            curso = ''
            nome = '{}'.format(participacao.get_nome())
            if participacao.is_servidor():
                email = participante.email
                lattes = ''
            elif hasattr(participante, 'lattes'):
                email = participante.email
                lattes = participante.lattes
            else:
                email = participante.pessoa_fisica.email
                lattes = participante.pessoa_fisica.lattes
                curso = participante.curso_campus
                from ae.models import DadosBancarios

                dados_bancarios = participante.get_dados_bancarios().filter(banco=DadosBancarios.BANCO_BB).order_by('-id')
                if dados_bancarios.exists():
                    agencia = dados_bancarios[0].numero_agencia
                    banco = dados_bancarios[0].banco
                    op = ' (Operação: ' + dados_bancarios[0].operacao + ') - ' if dados_bancarios[0].operacao else ' - '
                    conta = dados_bancarios[0].numero_conta + op + dados_bancarios[0].tipo_conta

            if participacao.vinculo == 'Bolsista' and participacao.bolsa_concedida:
                vinculo = 'Bolsista'
            else:
                vinculo = 'Voluntário'

            row = [
                contador,
                format_(projeto.titulo),
                format_(projeto.area_conhecimento),
                format_(nome),
                format_(matricula),
                format_(email),
                format_(lattes),
                format_(vinculo),
                format_(ativo),
                format_(titulacao),
                format_(curso),
                format_(banco),
                format_(agencia),
                format_(conta),
            ]
            rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Atualizar Curriculo Lattes')
def atualizar_curriculo_lattes(url, edital, task=None):
    edital.normalizar_pontuacao_curriculo_lattes(uo=None, task=task)
    task.finalize('Atualização realizada com sucesso.', url)
    edital.classifica_projetos_pesquisa()


@task('Exportar Bolsas de Projetos para XLS')
def exportar_bolsas_para_xls(projetos, task=None):
    rows = [
        [
            '#',
            'Edital',
            'Projeto',
            'Coordenador',
            'Vínculo/Bolsa',
            'Servidor',
            'Categoria/Titulação',
            'Aluno',
            'CRE',
            'Modalidade/Forma de Ensino',
            'Forma de Ingresso',
            'Curso',
            'Situação',
            'Pontuação do Currículo',
            'Pontuação do Currículo normalizado',
            'Pontuação do Grupo de Pesquisa',
            'Pontuação do Grupo de Pesquisa normalizado',
            'Pontuação da Avaliação',
            'Pontuação Final',
        ]
    ]

    contador = 0
    for projeto in task.iterate(projetos):
        for participacao in projeto.participacao_por_vinculo.all():
            contador += 1
            responsavel_nome = ''
            servidor_nome = ''
            aluno_nome = ''
            aluno_ira = ''
            aluno_forma_ingresso = ''
            aluno_curso = ''
            aluno_modalidade = ''

            if participacao.responsavel:
                responsavel_nome = participacao.vinculo_pessoa.pessoa.nome

            if participacao.eh_aluno():
                registro_aluno = participacao.get_participante()
                aluno_nome = participacao.vinculo_pessoa.pessoa.nome
                aluno_ira = registro_aluno.get_ira()
                aluno_forma_ingresso = registro_aluno.forma_ingresso
                aluno_curso = registro_aluno.curso_campus
                aluno_modalidade = registro_aluno.curso_campus.modalidade
            else:
                servidor_nome = participacao.vinculo_pessoa.pessoa.nome

            if participacao.vinculo == 'Bolsista' and participacao.bolsa_concedida:
                bolsa_status = 'Bolsa concedida'
            elif participacao.vinculo == 'Bolsista' and not participacao.bolsa_concedida:
                bolsa_status = 'Bolsa não concedida'
            else:
                bolsa_status = 'Vonlutário'

            if projeto.aprovado:
                situacao = 'Aprovado'
            else:
                situacao = 'Não Aprovado'
            row = [
                contador,
                format_(projeto.edital.titulo),
                format_(projeto.titulo),
                format_(responsavel_nome),
                format_(bolsa_status),
                format_(servidor_nome),
                format_(participacao.get_titulacao()),
                format_(aluno_nome),
                format_(aluno_ira),
                format_(aluno_modalidade),
                format_(aluno_forma_ingresso),
                format_(aluno_curso),
                format_(situacao),
                format_(projeto.pontuacao_curriculo),
                format_(projeto.pontuacao_curriculo_normalizado),
                format_(projeto.pontuacao_grupo_pesquisa),
                format_(projeto.pontuacao_grupo_pesquisa_normalizado),
                format_(projeto.pontuacao),
                format_(projeto.pontuacao_total),
            ]
            rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Lista de Projetos em Atraso para XLS')
def listar_projetos_em_atraso_export_to_xls(projetos, task=None):
    rows = [['#', 'Edital', 'Projeto', 'Coordenador', 'Fim da Execução']]

    contador = 0
    for projeto in task.iterate(projetos):
        contador += 1
        row = [contador, format_(projeto.edital), format_(projeto.titulo), format_(projeto.vinculo_coordenador.pessoa.nome), format_(projeto.fim_execucao)]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório de Dimensão para XLS')
def relatorio_dimensao_export_to_xls(quantidade_projetos, areas, lista_qtd, quantidade_participantes, participantes_por_area_conhecimento, lista_grupos_pesquisa, task=None):
    total_projetos = 0
    total_projetos_aprovados = 0
    total_projetos_concluidos = 0
    rows = [['Projetos por Edital']]

    row = ['Edital', 'Projetos Submetidos', 'Projetos Aprovados', 'Projetos Concluídos']
    rows.append(row)

    task.start_progress()

    for info in quantidade_projetos:
        total_projetos = total_projetos + info['total']
        total_projetos_aprovados = total_projetos_aprovados + info['aprovados']
        total_projetos_concluidos = total_projetos_concluidos + info['concluidos']

        row = [format_(info['edital']), format_(info['total']), format_(info['aprovados']), format_(info['concluidos'])]
        rows.append(row)

        task.update_progress(10)
    row = ['Total', format_(total_projetos), format_(total_projetos_aprovados), format_(total_projetos_concluidos)]
    rows.append(row)
    row = ['']
    rows.append(row)

    row = ['Projetos por Área de Conhecimento (Submetidos/Aprovados)']
    rows.append(row)
    qtd_areas = len(areas)
    areas.insert(0, "Edital")
    rows.append(areas)

    for info, valores in list(lista_qtd.items()):

        lista_valores = list()
        lista_valores.append(info)
        idx = 0

        while idx < qtd_areas * 2:
            lista_valores.append('{}/{}'.format(valores['valores'][idx], valores['valores'][idx + 1]))
            idx += 2
        rows.append(lista_valores)

        task.update_progress(30)

    row = ['']
    rows.append(row)
    row = ['Participações por Edital']
    rows.append(row)

    row = ['Edital', 'Bolsistas (Docentes/Téc. Adm/Discentes)', 'Voluntários (Docentes/Téc. Adm/Discentes)']
    rows.append(row)

    for info in quantidade_participantes:
        row = [
            format_(info['edital']),
            format_('%s/%s/%s') % (info['docentes_bolsistas'], info['tecnicos_adm_bolsistas'], info['alunos_bolsistas']),
            format_('%s/%s/%s') % (info['docentes_voluntarios'], info['tecnicos_adm_voluntarios'], info['alunos_voluntarios']),
        ]

        rows.append(row)

        task.update_progress(50)

    row = ['']
    rows.append(row)
    row = ['Participantes por Área de Conhecumento']
    rows.append(row)
    row = ['Área', 'Bolsistas (Docentes/Téc. Adm/Discentes)', 'Voluntários (Docentes/Téc. Adm/Discentes)']
    rows.append(row)

    for info in participantes_por_area_conhecimento:
        row = [
            format_(info['area']),
            format_('%s/%s/%s') % (info['docentes_bolsistas'], info['tec_adm_bolsistas'], info['alunos_bolsistas']),
            format_('%s/%s/%s') % (info['docentes_voluntarios'], info['tec_adm_voluntarios'], info['alunos_voluntarios']),
        ]

        rows.append(row)

        task.update_progress(70)

    row = ['']
    rows.append(row)
    row = ['Quantidade de Projetos Aprovados por Grupo de Pesquisa']
    rows.append(row)
    row = ['Grupo de Pesquisa', 'Quantidade de Projetos']
    rows.append(row)

    for info in lista_grupos_pesquisa:
        row = [format_('{}'.format(info[0])), format_('{}'.format(info[1]))]

        rows.append(row)

        task.update_progress(90)

    return XlsResponse(rows, processo=task)


@task('Exportar Lista Mensal de Bolsistas para XLS')
def lista_mensal_bolsistas_to_xls(registros, ano, mes, task=None):
    rows = [['', '', 'Relatório Mensal de Bolsistas - {} / {}'.format(mes, ano)], ['']]
    rows.append(['#', 'Aluno', 'Edital', 'Projeto', 'Bolsista', 'Ativo'])

    contador = 0
    for registro in task.iterate(registros):
        contador += 1
        participacao = registro.get_participacao()
        bolsista = 'Não'
        ativo = 'Não'
        matricula = ''
        nome = ''
        if participacao:
            if participacao.eh_aluno() == "Bolsista" and participacao.bolsa_concedida:
                bolsista = 'Sim'
            if participacao.ativo:
                ativo = 'Sim'
            matricula = participacao.get_participante().matricula
        if registro.vinculo_membro_equipe:
            nome = registro.vinculo_membro_equipe.pessoa.nome
        row = [
            contador,
            format_('{} ({})'.format(nome, matricula)),
            format_(registro.projeto.edital.titulo),
            format_(registro.projeto.titulo),
            format_(bolsista),
            format_(ativo),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)
