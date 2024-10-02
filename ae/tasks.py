from collections import OrderedDict

from django.db import transaction
from django.db.models.aggregates import Count
from django.http import HttpRequest

from ae.models import (
    DemandaAluno,
    Participacao,
    ParticipacaoPasseEstudantil,
    PassesChoices,
    RelatorioGrafico, Programa,
)
from ae.relatorio_gestao import (
    preencher_relatorio_atendimentos,
    preencher_relatorio_auxilios,
    preencher_relatorio_bolsas,
    preencher_relatorio_grafico,
    preencher_relatorio_programas,
    preencher_relatorio_resumo,
    preencher_relatorio_saude,
)
from comum.models import User
from djtools.assincrono import task
from djtools.db import models
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse
from edu.models import Aluno, MatriculaPeriodo
from rh.models import UnidadeOrganizacional
from saude.models import TipoAtendimento


@task('Relatório de Atendimento de Gestão')
def relatorio_atendimento(get, querystring, username, task=None):
    from ae.forms import RelatorioAtendimentoForm
    user = User.objects.get(username=username)
    request = HttpRequest()
    request.META = {'QUERY_STRING': querystring}
    request.GET = get
    request.user = user
    with transaction.atomic():
        form = RelatorioAtendimentoForm(get or None, request=request)
        ano, campus, somente_ead, renda = form._get_dados()
        demandas_atendidas, auxilios_atendidos, bolsas_atendidas, participacoes_atendidas, atendimentos_saude = form.processar_queries()

        if demandas_atendidas.exists() or auxilios_atendidos.exists() or bolsas_atendidas.exists() or participacoes_atendidas.exists() or atendimentos_saude.exists():
            relatorio_sistemico = False
            if form.request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos') and not campus:
                relatorio_sistemico = True

            relatorio = form.obter_relatorio()
            if relatorio:
                relatorio.delete()

            relatorio = form.criar_relatorio()

            ################
            # ATENDIMENTOS #
            ################
            # Controla o somatório das refeições
            atendimento_refeicao = 'Refeição (Café da manhã + Almoço + Jantar)'
            demanda_id_refeicao = [DemandaAluno.ALMOCO, DemandaAluno.JANTAR, DemandaAluno.CAFE]
            # Cria um anotate para melhorar performance do cálculo
            total_demandas = demandas_atendidas.filter(demanda__ativa=True).extra(
                select={'mes': "date_part('month', data)"})
            total_demandas = total_demandas.values('demanda__custeio', 'aluno_id', 'demanda__id', 'demanda__nome',
                                                   'mes')
            total_demandas = total_demandas.annotate(qtd=models.Sum('quantidade'))
            total_demandas = total_demandas.annotate(valor_total=models.Sum('valor'))
            total_demandas = total_demandas.annotate(qtd_aluno=models.Count('aluno__id'))
            total_demandas = total_demandas.order_by('demanda__custeio', 'mes', 'demanda__nome')
            # Calcula as demandas do ano escolhido
            atendimentos, total_geral_atendimentos = form.obter_dados_para_exibicao(
                total_demandas,
                nome='demanda__nome',
                custeio='demanda__custeio',
                aluno_id='aluno_id',
                nome_agrupamento=atendimento_refeicao,
                nome_agrupador='demanda__id',
                valores_agrupados=demanda_id_refeicao,
            )

            total_demandas_valor = demandas_atendidas.filter(demanda__ativa=True).exclude(
                demanda__in=demanda_id_refeicao).extra(select={'mes': "date_part('month', data)"})
            total_demandas_valor = total_demandas_valor.values('demanda__custeio', 'aluno_id', 'demanda__id',
                                                               'demanda__nome', 'mes')
            total_demandas_valor = total_demandas_valor.annotate(qtd=models.Sum('quantidade'))
            total_demandas_valor = total_demandas_valor.annotate(valor_total=models.Sum('valor'))
            total_demandas_valor = total_demandas_valor.annotate(qtd_aluno=models.Count('aluno__id'))
            total_demandas_valor = total_demandas_valor.order_by('demanda__custeio', 'mes', 'demanda__nome')
            # Calcula as demandas do ano escolhido
            atendimentos_valor, total_geral_atendimentos_valor = form.obter_dados_para_exibicao(
                total_demandas_valor, nome='demanda__nome', custeio='demanda__custeio', aluno_id='aluno_id',
                nome_agrupador='demanda__id'
            )
            atendimentos = OrderedDict(sorted(list(atendimentos.items()), key=lambda t: t[1]['custeio']))
            preencher_relatorio_atendimentos(relatorio, atendimentos, atendimentos_valor)
            contador = range(0, 25)
            task.iterate(contador)  # 20%

            # Monta o gráfico das demandas no ano e cálcula o número de alunos atendidos
            atendimentos_grafico = list()
            alunos_assistidos = list()
            for nome, dados in list(atendimentos.items()):
                if nome != atendimento_refeicao:
                    atendimentos_grafico.append([nome, dados['total']])
                    alunos_assistidos.append([nome, len(dados['total_alunos'])])

            preencher_relatorio_grafico(relatorio, 'grafico_atendimentos', RelatorioGrafico.PIE,
                                        RelatorioGrafico.ATENDIMENTOS, atendimentos_grafico)
            task.iterate(contador)  # 24%
            preencher_relatorio_grafico(relatorio, 'alunos_unicos', RelatorioGrafico.PIE, RelatorioGrafico.ATENDIMENTOS,
                                        alunos_assistidos)
            task.iterate(contador)  # 28%

            if relatorio_sistemico:
                refeicoes_total = demandas_atendidas.filter(demanda__in=demanda_id_refeicao)
                campi_ids = refeicoes_total.values_list('campus', flat=True).distinct()
                series_refeicoes_por_campus = []
                series_refeicoes_por_campus_unicos = []
                dict_tipos = dict(DemandaAluno.REFEICOES_CHOICES)
                tipos = list(dict_tipos.keys())
                tipos.sort()
                groups = []
                for tipo in tipos:
                    groups.append(dict_tipos.get(tipo))

                campi_ids = list(campi_ids)
                nomes_uos = dict(UnidadeOrganizacional.objects.uo().filter(id__in=campi_ids).values_list('id', 'nome'))
                refeicoes_total = refeicoes_total.filter(campus_id__in=campi_ids).values_list('campus',
                                                                                              'demanda').annotate(
                    qtd=models.Count('demanda'))
                refeicoes_total_dict = dict()
                for campus, demanda, qtd in refeicoes_total:
                    if campus not in refeicoes_total_dict:
                        refeicoes_total_dict[campus] = dict()
                    refeicoes_total_dict[campus][demanda] = qtd

                for campus_id in campi_ids:
                    serie = [nomes_uos[campus_id]]
                    for tipo in tipos:
                        serie.append(refeicoes_total_dict[campus_id].get(tipo))

                    series_refeicoes_por_campus.append(serie)

                    total_demandas = demandas_atendidas.filter(demanda__in=demanda_id_refeicao, campus=campus_id).extra(
                        select={'mes': "date_part('month', data)"})
                    total_demandas = total_demandas.values('demanda__custeio', 'aluno_id', 'demanda__id',
                                                           'demanda__nome', 'mes')
                    total_demandas = total_demandas.annotate(qtd=models.Sum('quantidade'))
                    total_demandas = total_demandas.annotate(valor_total=models.Sum('valor'))
                    total_demandas = total_demandas.annotate(qtd_aluno=models.Count('aluno__id'))
                    total_demandas = total_demandas.order_by('demanda__custeio', 'mes', 'demanda__nome')

                    refeicoes, total_geral_refeicoes = form.obter_dados_para_exibicao(
                        total_demandas,
                        nome='demanda__nome',
                        custeio='demanda__custeio',
                        aluno_id='aluno_id',
                        nome_agrupador='demanda__id',
                        valores_agrupados=demanda_id_refeicao,
                    )

                    serie = [nomes_uos[campus_id]]
                    cafe = almoco = jantar = None
                    for item, dados in list(refeicoes.items()):
                        if item:
                            if item.lower() == list(dict_tipos.values())[0].lower():
                                almoco = len(dados['total_alunos'])
                            elif item.lower() == list(dict_tipos.values())[1].lower():
                                jantar = len(dados['total_alunos'])
                            elif item.lower() == list(dict_tipos.values())[2].lower():
                                cafe = len(dados['total_alunos'])

                    serie.append(jantar)
                    serie.append(cafe)
                    serie.append(almoco)
                    series_refeicoes_por_campus_unicos.append(serie)

                preencher_relatorio_grafico(
                    relatorio, 'total_refeicoes_por_campus', RelatorioGrafico.GROUPEDCOLUMN,
                    RelatorioGrafico.ATENDIMENTOS, series_refeicoes_por_campus, groups
                )
                task.iterate(contador)  # 32%
                preencher_relatorio_grafico(
                    relatorio, 'total_refeicoes_por_campus_unicos', RelatorioGrafico.GROUPEDCOLUMN,
                    RelatorioGrafico.ATENDIMENTOS, series_refeicoes_por_campus_unicos, groups
                )
                task.iterate(contador)  # 36%

            ############
            # AUXÍLIOS #
            ############
            auxilios_atendidos.order_by('tipoatendimentosetor__nome')
            # Cria um anotate para melhorar performance do cálculo
            total_auxilios = auxilios_atendidos.extra(select={'mes': "date_part('month', data)"})
            total_auxilios = total_auxilios.values('id', 'alunos__id', 'tipoatendimentosetor__id',
                                                   'tipoatendimentosetor__nome', 'mes')
            total_auxilios = total_auxilios.annotate(qtd=models.Count('tipoatendimentosetor'))
            total_auxilios = total_auxilios.annotate(valor_total=models.Sum('valor'))
            total_auxilios = total_auxilios.annotate(qtd_aluno=models.Count('alunos__id'))
            total_auxilios = total_auxilios.order_by('mes', 'tipoatendimentosetor__nome')
            # Calcula os auxílios do ano escolhido
            auxilios, total_geral_auxilios = form.obter_dados_para_exibicao(total_auxilios,
                                                                            nome='tipoatendimentosetor__nome',
                                                                            aluno_id='alunos__id',
                                                                            agrupamento_aluno='id')
            preencher_relatorio_auxilios(relatorio, auxilios)
            task.iterate(contador)  # 40%

            # Monta o gráfico das demandas no ano e cálcula o número de alunos atendidos
            auxilios_grafico = list()
            for nome, dados in list(auxilios.items()):
                auxilios_grafico.append([nome, int(dados['total'])])

            preencher_relatorio_grafico(relatorio, 'grafico_auxilios', RelatorioGrafico.PIE, RelatorioGrafico.AUXILIOS,
                                        auxilios_grafico)
            task.iterate(contador)  # 44%

            ##########
            # BOLSAS #
            ##########
            bolsas_atendidas.order_by('categoria__nome')
            total_bolsas = bolsas_atendidas.values('aluno_id', 'categoria__id', 'categoria__nome', 'data_inicio',
                                                   'data_termino', 'id')
            total_bolsas = total_bolsas.annotate(qtd_aluno=models.Count('aluno__id'))
            total_bolsas = total_bolsas.order_by('categoria__nome')
            # Calcula as bolsas do ano escolhido
            bolsas, total_geral_bolsas = form.obter_dados_para_exibicao_ano(total_bolsas, nome='categoria__nome',
                                                                            aluno_id='aluno_id', ano=ano,
                                                                            agrupamento_aluno='id')
            preencher_relatorio_bolsas(relatorio, bolsas)
            task.iterate(contador)  # 48%
            if relatorio_sistemico:
                campi_ids = bolsas_atendidas.values_list('aluno__curso_campus__diretoria__setor__uo',
                                                         flat=True).distinct()
                series_bolsas_por_campus = []
                series_bolsas_por_campus_unicos = []
                tipos = bolsas_atendidas.values_list('categoria__nome', flat=True).distinct()
                groups = []
                for tipo in tipos:
                    groups.append(tipo)

                nomes_uos = dict(UnidadeOrganizacional.objects.uo().filter(id__in=campi_ids).values_list('id', 'nome'))
                for campus_id in campi_ids:
                    serie = [nomes_uos[campus_id]]
                    dados = dict(
                        bolsas_atendidas.filter(aluno__curso_campus__diretoria__setor__uo=campus_id)
                        .values_list('categoria__nome')
                        .annotate(qtd=models.Count('categoria__nome'))
                    )
                    for tipo in tipos:
                        serie.append(dados.get(tipo))
                    series_bolsas_por_campus.append(serie)

                    ids = list()
                    ids_repetidos = list()
                    for item in bolsas_atendidas.filter(aluno__curso_campus__diretoria__setor__uo=campus_id):
                        if item.aluno_id not in ids:
                            ids.append(item.aluno_id)
                        else:
                            ids_repetidos.append(item.id)

                    serie = [nomes_uos[campus_id]]
                    dados_unicos = dict(
                        bolsas_atendidas.filter(aluno__curso_campus__diretoria__setor__uo=campus_id)
                        .exclude(id__in=ids_repetidos)
                        .values_list('categoria__nome')
                        .annotate(qtd=models.Count('categoria__nome'))
                    )
                    for tipo in tipos:
                        serie.append(dados_unicos.get(tipo))

                    series_bolsas_por_campus_unicos.append(serie)

                preencher_relatorio_grafico(relatorio, 'total_bolsas_campus', RelatorioGrafico.GROUPEDCOLUMN,
                                            RelatorioGrafico.BOLSAS, series_bolsas_por_campus, groups)
                task.iterate(contador)  # 52%
                preencher_relatorio_grafico(
                    relatorio, 'total_bolsas_campus_unicos', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.BOLSAS,
                    series_bolsas_por_campus_unicos, groups
                )
                task.iterate(contador)  # 56%

            else:
                bolsas_profissional_total = bolsas_atendidas.filter(aluno__curso_campus__diretoria__setor__uo=campus)
                bolsa_profissional_campus = bolsas_profissional_total.values('categoria__nome').annotate(
                    qtd=Count('categoria__nome')).order_by('categoria__nome')
                bolsas_todas = list()
                bolsas_unicas = list()
                if bolsa_profissional_campus:
                    for item in bolsa_profissional_campus:
                        bolsas_todas.append([item['categoria__nome'], item['qtd']])

                    if bolsas_todas[-1][1] == 0:
                        bolsas_todas.pop()

                    ids = list()
                    ids_repetidos = list()
                    for item in bolsas_profissional_total:
                        if item.aluno_id not in ids:
                            ids.append(item.aluno_id)
                        else:
                            ids_repetidos.append(item.id)

                    for item in (
                            bolsas_profissional_total.exclude(id__in=ids_repetidos).values('categoria__nome').annotate(
                                qtd=Count('categoria__nome')).order_by('categoria__nome')
                    ):
                        bolsas_unicas.append([item['categoria__nome'], item['qtd']])

                preencher_relatorio_grafico(relatorio, 'bolsas_campus', RelatorioGrafico.PIE, RelatorioGrafico.BOLSAS,
                                            bolsas_todas)
                task.iterate(contador)  # 60%
                preencher_relatorio_grafico(relatorio, 'bolsas_campus_unicos', RelatorioGrafico.PIE,
                                            RelatorioGrafico.BOLSAS, bolsas_unicas)
                task.iterate(contador)  # 64%

            #############
            # PROGRAMAS #
            #############
            participacoes_atendidas.order_by('programa__tipo')
            # Cria um anotate para melhorar performance do cálculo
            total_programas = participacoes_atendidas.values(
                'id', 'aluno_id', 'programa__id', 'programa__titulo', 'programa__tipo_programa__titulo', 'data_inicio',
                'data_termino'
            )
            total_programas = total_programas.annotate(qtd_aluno=models.Count('aluno__id'))
            total_programas = total_programas.order_by('programa__tipo_programa__titulo')
            # Cálcula os programas do ano escolhido
            programas, total_geral_programas = form.obter_dados_para_exibicao_ano(
                total_programas, nome='programa__titulo', aluno_id='aluno_id', ano=ano, agrupamento_aluno='id',
                programa=True
            )
            preencher_relatorio_programas(relatorio, programas)
            task.iterate(contador)  # 68%

            transporte_total = ParticipacaoPasseEstudantil.objects.filter(
                participacao__in=participacoes_atendidas.values_list('id', flat=True))
            if relatorio_sistemico:
                campi_ids = transporte_total.values_list('participacao__programa__instituicao', flat=True).distinct()
                series_transportes_por_campus = []
                series_transportes_por_campus_unicos = []
                dict_tipos = dict(PassesChoices.PASSES_CHOICES)
                tipos = list(dict_tipos.keys())
                tipos.sort()
                groups = []
                for tipo in tipos:
                    groups.append(dict_tipos.get(tipo))

                nomes_uos = dict(UnidadeOrganizacional.objects.uo().filter(id__in=campi_ids).values_list('id', 'nome'))
                for campus_id in campi_ids:
                    serie = [nomes_uos[campus_id]]
                    dados = dict(
                        transporte_total.filter(participacao__programa__instituicao=campus_id)
                        .values_list('tipo_passe_concedido')
                        .annotate(qtd=models.Count('tipo_passe_concedido'))
                    )
                    for tipo in tipos:
                        serie.append(dados.get(tipo))

                    series_transportes_por_campus.append(serie)

                    ids = list()
                    ids_repetidos = list()
                    participacoes_passe_estudantil = OrderedDict(
                        (item.id, item.participacao_id) for item in
                        transporte_total.filter(participacao__programa__instituicao=campus_id).order_by(
                            '-participacao_id')
                    )
                    participacoes = dict(
                        (participacao.id, participacao.aluno_id) for participacao in
                        Participacao.objects.filter(id__in=list(participacoes_passe_estudantil.values()))
                    )
                    for participacao_passe_estudantil_id, participacao_id in list(
                            participacoes_passe_estudantil.items()):
                        aluno_id = participacoes[participacao_id]
                        if aluno_id not in ids:
                            ids.append(aluno_id)
                        else:
                            ids_repetidos.append(participacao_passe_estudantil_id)

                    serie = [nomes_uos[campus_id]]
                    dados_unicos = dict(
                        transporte_total.filter(participacao__programa__instituicao=campus_id)
                        .exclude(id__in=ids_repetidos)
                        .values_list('tipo_passe_concedido')
                        .annotate(qtd=models.Count('tipo_passe_concedido'))
                    )
                    for tipo in tipos:
                        serie.append(dados_unicos.get(tipo))

                    series_transportes_por_campus_unicos.append(serie)

                preencher_relatorio_grafico(
                    relatorio, 'total_transportes_por_campus', RelatorioGrafico.GROUPEDCOLUMN,
                    RelatorioGrafico.PROGRAMAS, series_transportes_por_campus, groups
                )
                task.iterate(contador)  # 72%
                preencher_relatorio_grafico(
                    relatorio, 'total_transportes_por_campus_unicos', RelatorioGrafico.GROUPEDCOLUMN,
                    RelatorioGrafico.PROGRAMAS, series_transportes_por_campus_unicos, groups
                )
                task.iterate(contador)  # 76%

            else:
                transporte_por_tipo = (
                    transporte_total.filter(participacao__programa__instituicao=campus)
                    .values('tipo_passe_concedido')
                    .annotate(qtd=Count('tipo_passe_concedido'))
                    .order_by('tipo_passe_concedido')
                )
                dados = list()
                dados_unicos = list()
                if transporte_por_tipo:
                    for item in transporte_por_tipo:
                        if item['tipo_passe_concedido'] == PassesChoices.INTERMUNICIPAL:
                            dados.append(['Intermunicipal', item['qtd']])
                        else:
                            dados.append(['Municipal', item['qtd']])

                    if dados[-1][1] == 0:
                        dados.pop()

                    ids = list()
                    ids_repetidos = list()
                    participacoes_passe_estudantil = OrderedDict(
                        (item.id, item.participacao_id) for item in
                        transporte_total.filter(participacao__programa__instituicao=campus).order_by('-participacao_id')
                    )
                    participacoes = dict(
                        (participacao.id, participacao.aluno_id) for participacao in
                        Participacao.objects.filter(id__in=list(participacoes_passe_estudantil.values()))
                    )
                    for participacao_passe_estudantil_id, participacao_id in list(
                            participacoes_passe_estudantil.items()):
                        aluno_id = participacoes[participacao_id]
                        if aluno_id not in ids:
                            ids.append(aluno_id)
                        else:
                            ids_repetidos.append(participacao_passe_estudantil_id)

                    for item in (
                        transporte_total.filter(participacao__programa__instituicao=campus)
                        .exclude(id__in=ids_repetidos)
                        .values('tipo_passe_concedido')
                        .annotate(qtd=Count('tipo_passe_concedido'))
                        .order_by('tipo_passe_concedido')
                    ):
                        if item['tipo_passe_concedido'] == PassesChoices.INTERMUNICIPAL:
                            dados_unicos.append(['Intermunicipal', item['qtd']])
                        else:
                            dados_unicos.append(['Municipal', item['qtd']])

                    if dados_unicos[-1][1] == 0:
                        dados_unicos.pop()

                preencher_relatorio_grafico(relatorio, 'transporte_campus', RelatorioGrafico.PIE,
                                            RelatorioGrafico.PROGRAMAS, dados)
                task.iterate(contador)  # 80%
                preencher_relatorio_grafico(relatorio, 'transporte_campus_unicos', RelatorioGrafico.PIE,
                                            RelatorioGrafico.PROGRAMAS, dados_unicos)
                task.iterate(contador)  # 84%

            #########
            # SAÚDE #
            #########
            # Cria um anotate para melhorar performance do cálculo
            total_saude = atendimentos_saude.values('id', 'aluno_id', 'tipo', 'data_aberto', 'data_fechado',
                                                    'atendimentopsicologia__data_atendimento')
            total_saude = total_saude.annotate(qtd_aluno=models.Count('aluno__id'))
            # Cálcula os atendimentos de saúde do ano escolhido
            saude, total_geral_saude = form.obter_dados_para_exibicao_ano_saude(total_saude, nome='tipo',
                                                                                aluno_id='aluno_id', ano=ano,
                                                                                agrupamento_aluno='id')
            preencher_relatorio_saude(relatorio, saude)
            task.iterate(contador)  # 88%

            atendimentos_saude = atendimentos_saude.filter(data_aberto__year=ano)
            if campus:
                atendimentos_saude = atendimentos_saude.filter(usuario_aberto__vinculo__setor__uo=campus)

            atendimentos_saude_count = (
                atendimentos_saude.extra(select={'datafechadoisnull': "data_fechado is null"})
                .values('tipo', 'datafechadoisnull')
                .annotate(qtd=Count('tipo'))
                .values('tipo', 'qtd', 'datafechadoisnull')
            )
            dados_atendimentos = dict()
            for atendimento in atendimentos_saude_count:
                tipo = atendimento['tipo']
                datafechadoisnull = atendimento['datafechadoisnull']
                qtd = atendimento['qtd']
                if tipo not in dados_atendimentos:
                    dados_atendimentos[tipo] = dict()

                if datafechadoisnull not in dados_atendimentos[tipo]:
                    dados_atendimentos[tipo][datafechadoisnull] = 0

                dados_atendimentos[tipo][datafechadoisnull] = qtd

            def get_dados_atendimentos(dados_atendimentos, tipo, data_fechado):
                return dados_atendimentos[tipo][data_fechado] if tipo in dados_atendimentos and data_fechado in \
                    dados_atendimentos[tipo] else 0

            avaliacao_biomedica_aberta = get_dados_atendimentos(dados_atendimentos, TipoAtendimento.AVALIACAO_BIOMEDICA,
                                                                True)
            avaliacao_biomedica_fechada = get_dados_atendimentos(dados_atendimentos,
                                                                 TipoAtendimento.AVALIACAO_BIOMEDICA, False)
            atendimentos_medicos = atendimentos_saude.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO,
                                                             condutamedica__isnull=False,
                                                             data_fechado__isnull=False).count()
            atendimentos_enfermagem = atendimentos_saude.filter(tipo=TipoAtendimento.ENFERMAGEM_MEDICO,
                                                                intervencaoenfermagem__isnull=False,
                                                                data_fechado__isnull=False).count()
            atendimentos_odontologicos = get_dados_atendimentos(dados_atendimentos, TipoAtendimento.ODONTOLOGICO, False)
            atendimentos_psicologicos = get_dados_atendimentos(dados_atendimentos, TipoAtendimento.PSICOLOGICO, False)
            atendimentos_multidisciplinares = get_dados_atendimentos(dados_atendimentos,
                                                                     TipoAtendimento.MULTIDISCIPLINAR, False)

            dados = list()
            dados.append(['Avaliação Biomédica Aberta', avaliacao_biomedica_aberta])
            dados.append(['Avaliação Biomédica Fechada', avaliacao_biomedica_fechada])
            dados.append(['Médico', atendimentos_medicos])
            dados.append(['Enfermagem', atendimentos_enfermagem])
            dados.append(['Odontológico', atendimentos_odontologicos])
            dados.append(['Psicológico', atendimentos_psicologicos])
            dados.append(['Multidisciplinar', atendimentos_multidisciplinares])

            preencher_relatorio_grafico(relatorio, 'saude_atendimentos', RelatorioGrafico.PIE, RelatorioGrafico.SAUDE,
                                        dados)
            task.iterate(contador)  # 92%

            ###############
            # TOTALIZADOR #
            ###############
            total_geral = preencher_relatorio_resumo(relatorio, total_geral_atendimentos, total_geral_auxilios,
                                                     total_geral_bolsas, total_geral_programas, total_geral_saude)
            dados_grafico_resumo = list()
            alunos_ativos = Aluno.objects.filter(
                id__in=MatriculaPeriodo.objects.filter(ano_letivo__ano=ano).values_list('aluno', flat=True))
            if campus:
                alunos_ativos = alunos_ativos.filter(curso_campus__diretoria__setor__uo=campus)

            dados_grafico_resumo.append(['Alunos com Vunerabilidade Socioeconômica Assistidos', len(total_geral)])
            dados_grafico_resumo.append(['Alunos com matrícula ativa no ano', alunos_ativos.count()])

            preencher_relatorio_grafico(relatorio, 'alunos_vulnerabilidade_assistidos', RelatorioGrafico.BAR,
                                        RelatorioGrafico.RESUMO, dados_grafico_resumo)
            task.iterate(contador)  # 96%

            task.finalize('Relatório processado com sucesso.',
                          '/ae/relatorio_gestao/?{}&finalize=1'.format(request.META.get('QUERY_STRING', '')))
        else:
            task.finalize('Nenhum registro encontrado.', '/ae/relatorio_gestao/', error=True)


@task('Exportar Folha de Pagamento para XLS')
def exportar_folha_pagamento_xls(
        tipo_programa,
        oferta_do_mes,
        lista,
        ver_nome,
        ver_matricula,
        ver_cpf,
        ver_banco,
        ver_agencia,
        ver_operacao,
        ver_conta,
        ver_tipo_passe,
        ver_valor_padrao,
        ver_valor_pagar,
        total,
        task=None):
    colunas = []
    rows = []
    conta_atributos = 0
    colunas.append('#')
    if ver_nome:
        colunas.append('Nome')
        conta_atributos += 1
    if ver_matricula:
        colunas.append('Matrícula')
        conta_atributos += 1
    if ver_cpf:
        colunas.append('CPF')
        conta_atributos += 1
    if ver_banco:
        colunas.append('Banco')
        conta_atributos += 1
    if ver_agencia:
        colunas.append('Agência')
        conta_atributos += 1
    if ver_operacao:
        colunas.append('Operação')
        conta_atributos += 1
    if ver_conta:
        colunas.append('Conta')
        conta_atributos += 1
    if ver_tipo_passe:
        colunas.append('Tipo de Passe')
        conta_atributos += 1
    if ver_valor_padrao:
        colunas.append('Valor Padrão')
        conta_atributos += 1
    if ver_valor_pagar:
        colunas.append('Valor a Pagar')
        conta_atributos += 1
    rows.append(colunas)
    contador = 1

    for participante, valor in task.iterate(lista):
        row = [contador]
        if ver_nome:
            row.append(format_(participante.aluno.pessoa_fisica.nome))
        if ver_matricula:
            row.append(format_(participante.aluno.matricula))
        if ver_cpf:
            row.append(format_(participante.aluno.pessoa_fisica.cpf.replace('.', '').replace('-', '')))
        dados_bancarios = participante.aluno.get_dados_bancarios_folha_pagamento()
        aluno = participante.aluno
        if ver_banco:
            texto = ''
            if dados_bancarios:
                texto = format_(aluno.get_dados_bancarios_banco())
            row.append(texto)
        if ver_agencia:
            texto = ''
            if dados_bancarios:
                texto = format_(aluno.get_dados_bancarios_numero_agencia())
            row.append(texto)
        if ver_operacao:
            texto = ''
            if dados_bancarios:
                texto = format_(dados_bancarios.operacao)
            row.append(texto)
        if ver_conta:
            texto = ''
            if dados_bancarios:
                texto = format_(aluno.get_dados_bancarios_numero_conta())
            row.append(texto)
        if tipo_programa == Programa.TIPO_TRANSPORTE:
            if ver_tipo_passe:
                row.append(format_(participante.sub_instance().get_tipo_passe_concedido_display()))
            if ver_valor_padrao:
                row.append(format_(participante.sub_instance().valor_concedido))
        else:
            if ver_valor_padrao:
                resultado = oferta_do_mes or 'não informado'
                row.append(format_(resultado))

        if ver_valor_pagar:
            row.append(format_(valor))

        rows.append(row)
        contador += 1
    if ver_valor_pagar:
        row = ['Total']
        item = 1
        while item < conta_atributos:
            row.append('')
            item += 1
        row.append(format_(total))
        rows.append(row)

    XlsResponse(rows, processo=task)


@task('Exportar Relatório de Atendimento PNAES para XLS')
def exportar_relatorio_atendimento_pnaes_xls(alunos,
                                             ids_lista_alunos_alimentacao,
                                             ids_lista_alunos_transporte,
                                             lista_alunos_transporte_valores,
                                             task=None):
    rows = [
        [
            '#',
            'Nome do(a) aluno(a) PNAES',
            'CPF do(a)  aluno(a)',
            'Renda familiar per capita (Salário(s) Mínimo(s)) ',
            'Curso',
            'Código e­Mec do curso',
            'Data de ingresso no curso',
            'Modalidade(s) de benefício(s) recebido(s)',
            'Valor recebido / ano (R$)',
        ]
    ]
    contador = 0
    for aluno in task.iterate(alunos):
        contador += 1
        renda = 0
        valor = 0
        curso = 'Não informado'
        codigo_emec = 'Não informado'
        if aluno.curso_campus:
            curso = aluno.curso_campus
            if curso:
                codigo_emec = curso.codigo_emec
        if hasattr(aluno, 'caracterizacao'):
            renda = aluno.caracterizacao.renda_per_capita
        beneficio = ''
        if aluno.id in ids_lista_alunos_alimentacao:
            beneficio += 'auxílio-alimentação; '
        if aluno.id in ids_lista_alunos_transporte:
            beneficio += 'auxílio-transporte; '
        nome_aluno = aluno.pessoa_fisica.nome
        if nome_aluno in list(lista_alunos_transporte_valores.keys()):
            valor = lista_alunos_transporte_valores[nome_aluno]
        row = [
            contador,
            format_(aluno.pessoa_fisica.nome),
            format_(aluno.pessoa_fisica.cpf),
            format_(renda),
            format_(curso),
            format_(codigo_emec),
            format_(aluno.data_matricula),
            format_(beneficio),
            format_(valor),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)


@task('Exportar Relatório: Alunos Participantes x Índices Acadêmicos para XLS')
def relatorio_aluno_rendimento_frequencia_xls(matriculas, data_inicio, data_fim, task=None):
    rows = [
        [
            '#',
            'Nome do Aluno',
            'Curso',
            'Programas que participa',
            'Rendimento Acadêmico',
            'Frequência Escolar',
            'IRA por Curso',
            'Medidas Disciplinares / Premiações',
            'Atividades Complementares',
        ]
    ]

    contador = 0
    for matricula in task.iterate(matriculas):
        contador += 1
        texto = ''
        for registro in Participacao.abertas.filter(aluno=matricula.aluno):
            texto = texto + '{} (Entrada em: {}), '.format(registro.programa.tipo_programa,
                                                           registro.data_inicio.strftime('%d/%m/%Y'))
        texto = texto[:-2]
        row = [
            contador,
            format_(matricula.aluno.pessoa_fisica.nome),
            format_(matricula.aluno.curso_campus),
            format_(texto),
            format_(matricula.aluno.get_ira()),
            format_('{}%'.format(matricula.get_percentual_carga_horaria_frequentada())),
            format_(matricula.aluno.get_ira_curso_aluno()),
            format_(matricula.aluno.get_total_medidas_disciplinares_premiacoes(data_inicio, data_fim)),
            format_(matricula.aluno.get_total_atividades_complementares(data_inicio, data_fim)),
        ]
        rows.append(row)
    return XlsResponse(rows, processo=task)
