import datetime

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.db.models.aggregates import Count, Sum
from django.db.transaction import atomic
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize

from comum.utils import get_uo
from djtools import layout
from djtools.choices import Situacao
from djtools.html.calendarios import CalendarioPlus
from djtools.html.graficos import GraficoAgendamento
from djtools.html.graficos import PieChart, ColumnChart
from djtools.utils import rtr, httprr, permission_required, user_has_one_of_perms
from djtools.utils import send_notification
from edu.models import Aluno
from estacionamento.models import Veiculo
from frota.forms import (
    ViagemRetroativaForm,
    ViagemSaidaForm,
    ViagemAgendamentoRespostaForm,
    ViagemChegadaForm,
    ViaturaOrdemAbastecimentoForm,
    PeriodoRelatorioViagemForm,
    PeriodoForm,
    EstatisticasViagemForm,
    ControleRevisaoForm,
    EditarDataProximaRevisaoForm,
)
from frota.models import Viagem, ViagemAgendamento, ViagemAgendamentoResposta, Viatura, ManutencaoViatura
from rh.models import UnidadeOrganizacional, Setor, Funcao
from djtools.utils.calendario import somarDias


@layout.quadro('Frota', icone='car', pode_esconder=True)
def index_quadros(quadro, request):
    registros = None
    vinculo = request.user.get_vinculo()
    eh_coordenador_frota_campus = request.user.has_perm('frota.tem_acesso_viatura_campus')
    eh_coordenador_frota_sistemico = request.user.has_perm('frota.tem_acesso_viatura_sistemico')
    eh_operador_frota = request.user.has_perm('frota.tem_acesso_agendamento_operador')

    quantidade_registros = 0
    if eh_coordenador_frota_campus:
        registros = ViagemAgendamento.objects.filter(setor__uo=get_uo(request.user), status=Situacao.PENDENTE, data_saida__gte=datetime.datetime.now())
        quantidade_registros = registros.count()
    if eh_coordenador_frota_sistemico:
        registros = ViagemAgendamento.objects.filter(status=Situacao.PENDENTE, data_saida__gte=datetime.datetime.now())
        quantidade_registros = registros.count()

    if quantidade_registros:
        quadro.add_item(
            layout.ItemContador(
                titulo='Viage{}'.format(pluralize(quantidade_registros, 'm,ns')),
                subtitulo='Sem avaliação',
                qtd=quantidade_registros,
                url='/admin/frota/viagemagendamento/?status__exact=Pendente',
            )
        )

    if vinculo.eh_servidor():
        servidor = request.user.get_relacionamento()
        hoje = datetime.datetime.now().date()
        setores = servidor.historico_funcao(hoje, hoje).filter(funcao__codigo__in=Funcao.get_codigos_funcao_chefia()).values_list('setor_suap', flat=True)

        viagens_pendentes_avaliacao = ViagemAgendamento.objects.filter(
            data_saida__gte=datetime.datetime.now(), setor__in=setores, avaliado_em__isnull=True, status=Situacao.PENDENTE
        )
        if viagens_pendentes_avaliacao.exists():
            qtd_viagens_pendentes_avaliacao = viagens_pendentes_avaliacao.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Solicitaç{} de Viagem'.format(pluralize(qtd_viagens_pendentes_avaliacao, 'ão,ões')),
                    subtitulo='Pendente{} de sua autorização'.format(pluralize(qtd_viagens_pendentes_avaliacao)),
                    qtd=qtd_viagens_pendentes_avaliacao,
                    url='/admin/frota/viagemagendamento/?tab=tab_agendamentos_pendentes_autorizacao',
                )
            )

    if eh_coordenador_frota_campus or eh_coordenador_frota_sistemico or eh_operador_frota:
        viaturas_inconsistentes = Viatura.objects.filter(patrimonio__isnull=False).exclude(patrimonio__carga_contabil__campus=F('campus')).only('id')
        if viaturas_inconsistentes.exists():
            qtd_viaturas_inconsistentes = viaturas_inconsistentes.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Viatura{}'.format(pluralize(qtd_viaturas_inconsistentes)),
                    subtitulo='Vinculada{} a um campus diferente da carga contábil do patrimônio'.format(pluralize(qtd_viaturas_inconsistentes)),
                    qtd=qtd_viaturas_inconsistentes,
                    url='/admin/frota/viatura/{}/'.format(viaturas_inconsistentes[0].id),
                )
            )

        quadro.add_item(layout.ItemAcessoRapido(titulo='Agendar Viagem', url='/admin/frota/viagemagendamento/add/', icone='plus', classe='success'))

    if eh_operador_frota:
        ids_viaturas_atraso = list()
        ids_viaturas_prevista = list()
        ids_viaturas_por_km = list()
        for viatura in Viatura.ativas.all():
            if viatura.tem_revisao_atraso():
                ids_viaturas_atraso.append(viatura.id)
            elif viatura.tem_revisao_prevista():
                ids_viaturas_prevista.append(viatura.id)
            elif viatura.tem_odometro_perto_10k():
                ids_viaturas_por_km.append(viatura.id)

        if ids_viaturas_atraso:
            qtd = len(ids_viaturas_atraso)
            quadro.add_item(
                layout.ItemContador(
                    titulo='Viatura{}'.format(pluralize(qtd)), subtitulo='Com revisão em atraso', qtd=qtd, url='/frota/controle_revisoes_viaturas/?situacao=Revisão+em+Atraso'
                )
            )

        if ids_viaturas_prevista:
            qtd = len(ids_viaturas_prevista)
            quadro.add_item(
                layout.ItemContador(
                    titulo='Viatura{}'.format(pluralize(qtd)),
                    subtitulo='Com revisão prevista em até 30 dias',
                    qtd=qtd,
                    url='/frota/controle_revisoes_viaturas/?situacao=Revisão+nos+próximos+30+dias',
                )
            )

        if ids_viaturas_por_km:
            qtd = len(ids_viaturas_por_km)
            quadro.add_item(
                layout.ItemContador(
                    titulo='Viatura{}'.format(pluralize(qtd)),
                    subtitulo='Com revisão por KM prevista',
                    qtd=qtd,
                    url='/frota/controle_revisoes_viaturas/?situacao=Revisão+por+KM+(10+Mil)',
                )
            )

    return quadro


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus'])
def avaliar_agendamento_viagem(request, agendamento_id):
    title = 'Avaliação de Agendamento'
    status = Situacao.get_choices()
    viaturas_indisponiveis = list()
    motoristas_indisponiveis = list()
    agendamento = get_object_or_404(ViagemAgendamento, pk=agendamento_id)
    if not request.user.has_perm('frota.tem_acesso_viagem_sistemico'):
        if not agendamento.setor.uo == get_uo(request.user):
            raise PermissionDenied()

    if not agendamento.aprovado and agendamento.avaliado_em:
        return httprr('/admin/frota/viagemagendamento/', 'Agendamento não autorizado pela chefia.', tag='error')

    limite_inferior = somarDias(agendamento.data_saida, -1)
    limite_superior = somarDias(agendamento.data_chegada, +1)
    viaturas = Viatura.objects.filter(ativo=True, campus=get_uo(request.user))

    grafico = GraficoAgendamento(limite_inferior, limite_superior)
    grafico.set_items(viaturas)

    viagens = Viagem.objects.filter(
        saida_data__lte=agendamento.data_chegada,
        saida_data__gte=agendamento.data_saida,
        chegada_data__gte=agendamento.data_saida,
        agendamento_resposta__agendamento__setor__uo=get_uo(request.user),
        agendamento_resposta__agendamento__status=Situacao.DEFERIDA,
    ) | Viagem.objects.filter(
        saida_data__lte=agendamento.data_chegada,
        saida_data__gte=agendamento.data_saida,
        chegada_data__isnull=True,
        agendamento_resposta__agendamento__setor__uo=get_uo(request.user),
        agendamento_resposta__agendamento__status=Situacao.DEFERIDA,
    )

    agendamentos = ViagemAgendamento.objects.filter(
        data_saida__lte=agendamento.data_chegada, data_chegada__gte=agendamento.data_saida, status=Situacao.DEFERIDA, viagemagendamentoresposta__viagem__isnull=True
    ).exclude(id=agendamento.id)
    respostas_agendamentos = ViagemAgendamentoResposta.objects.filter(agendamento__in=agendamentos.values_list('id', flat=True))
    respostas_viagens = ViagemAgendamentoResposta.objects.filter(id__in=viagens.values_list('agendamento_resposta__id', flat=True))
    respostas = respostas_agendamentos | respostas_viagens

    for resposta in respostas:
        if resposta.viatura and resposta.viatura.ativo:
            texto = resposta.agendamento.objetivo + ' Motoristas: ' + resposta.get_motoristas()
            grafico.preencher_intervalo(resposta.viatura.id, '#FCF8E3', resposta.agendamento.data_saida, resposta.agendamento.data_chegada, texto)
            viaturas_indisponiveis.append(resposta.viatura.id)
            for motorista in resposta.motoristas.all():
                motoristas_indisponiveis.append(motorista.id)
    for viatura in viaturas:
        grafico.preencher_intervalo(viatura.id, '#3C763D', agendamento.data_saida, agendamento.data_chegada, agendamento.objetivo)

    if agendamento.status == Situacao.PENDENTE:
        form = ViagemAgendamentoRespostaForm(
            request.POST or None,
            agendamento_id=agendamento_id,
            request=request,
            viaturas_indisponiveis=set(viaturas_indisponiveis),
            motoristas_indisponiveis=set(motoristas_indisponiveis),
        )
    else:
        agendamentoResposta = ViagemAgendamentoResposta.objects.get(agendamento=agendamento)
        form = ViagemAgendamentoRespostaForm(
            request.POST or None,
            instance=agendamentoResposta,
            agendamento_id=agendamento_id,
            request=request,
            viaturas_indisponiveis=set(viaturas_indisponiveis),
            motoristas_indisponiveis=set(motoristas_indisponiveis),
        )

    if form.is_valid():
        registro = form.save(commit=False)
        viatura_escolhida = None
        status = form.cleaned_data.get('status')
        agendamento.status = status
        if status == Situacao.DEFERIDA:
            agendamento.local_saida = form.cleaned_data.get('local_saida')
            if form.cleaned_data.get('viatura'):
                viatura_escolhida = form.cleaned_data.get('viatura')
        agendamento.save()

        kwargs = dict(obs=form.cleaned_data.get('obs'), data=datetime.datetime.now(), vinculo_responsavel=request.user.get_vinculo(), viatura=viatura_escolhida)

        avaliacao_agendamento = ViagemAgendamentoResposta.objects.update_or_create(agendamento=agendamento, defaults=kwargs)[0]
        string_motoristas = ''
        if status == Situacao.DEFERIDA:
            for motorista in form.cleaned_data.get('motoristas'):
                avaliacao_agendamento.motoristas.add(motorista)
                string_motoristas += motorista.pessoa.nome + ', '
            string_motoristas = string_motoristas[:-2]
            for motorista in avaliacao_agendamento.motoristas.all():
                if motorista not in form.cleaned_data.get('motoristas'):
                    avaliacao_agendamento.motoristas.remove(motorista)
        elif status == Situacao.INDEFERIDA:
            for motorista in avaliacao_agendamento.motoristas.all():
                avaliacao_agendamento.motoristas.remove(motorista)

        agendamento_avaliado = get_object_or_404(ViagemAgendamento, pk=agendamento_id)
        titulo = '[SUAP] Avaliação de Agendamento da Viagem'
        texto = (
            '<h1>Frota</h1>'
            '<h2>Avaliação de Agendamento da Viagem #{}</h2>'
            '<p>A viagem, com o objetivo "{}", foi <strong>{}</strong>.</p><br />'.format(agendamento_avaliado.id, agendamento_avaliado.objetivo, agendamento_avaliado.status)
        )
        if form.cleaned_data['status'] == Situacao.DEFERIDA:
            texto += (
                '<dl>'
                '<dt>Motorista(s):</dt><dd>{}<dd>'
                '<dt>Veículo:</dt><dd>{}<dd>'
                '<dt>Local de Saída:</dt><dd>{}</dd>'
                '<dt>Saída:</dt><dd>{}</dd>'
                '<dt>Chegada:</dt><dd>{}</dd>'.format(
                    string_motoristas, form.cleaned_data['viatura'], form.cleaned_data['local_saida'], agendamento_avaliado.data_saida, agendamento_avaliado.data_chegada
                )
            )
        if form.cleaned_data['obs']:
            texto += '<dt>Observação do Avaliador:</dt><dd>{}</dd>'.format(form.cleaned_data['obs'])
        texto += '</dl>'

        destinatarios = []
        destinatarios.append(agendamento_avaliado.vinculo_solicitante)
        if agendamento.vinculos_interessados.exists():
            for interessado in agendamento.vinculos_interessados.all():
                destinatarios.append(interessado)

        if form.cleaned_data['status'] == Situacao.DEFERIDA:
            if form.cleaned_data.get('motoristas'):
                for motorista in form.cleaned_data.get('motoristas'):
                    destinatarios.append(motorista)
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, destinatarios)
        return httprr('/admin/frota/viagemagendamento/', 'Agendamento avaliado com sucesso.')

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def viagens_agendadas(request):
    title = 'Viagens Agendadas'
    is_gerente = request.user.has_perm('frota.tem_acesso_viagem_sistemico') or request.user.is_superuser

    if not is_gerente:
        agendamentos_viagem = list(Viagem.objects.filter(agendamento_resposta__agendamento__setor__uo=get_uo(request.user)).values_list('agendamento_resposta_id', flat=True))
        resp_agendamentos = (
            ViagemAgendamentoResposta.objects.filter(
                agendamento__setor__uo=get_uo(request.user),
                agendamento__status=Situacao.DEFERIDA,
                agendamento__data_saida__lte=datetime.date.today() + datetime.timedelta(15),
                agendamento__data_saida__gte=datetime.date.today() + datetime.timedelta(-30),
            )
            .exclude(id__in=agendamentos_viagem)
            .order_by('-agendamento__data_saida')
        )
    else:
        agendamentos_viagem = list(Viagem.objects.all().values_list('agendamento_resposta_id', flat=True))
        resp_agendamentos = (
            ViagemAgendamentoResposta.objects.filter(
                agendamento__status=Situacao.DEFERIDA,
                agendamento__data_saida__lte=datetime.date.today() + datetime.timedelta(15),
                agendamento__data_saida__gte=datetime.date.today() + datetime.timedelta(-30),
            )
            .exclude(id__in=agendamentos_viagem)
            .order_by('-agendamento__data_saida')
        )

    if 'all' in request.GET:
        pass
    else:
        resp_agendamentos = resp_agendamentos.filter(viatura__campus=get_uo(request.user))

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def saida_viagem(request, resp_agendamento_id):
    title = 'Registrar Saída'
    resp_agendamento = get_object_or_404(ViagemAgendamentoResposta, pk=resp_agendamento_id)
    if not request.user.has_perm('frota.tem_acesso_viagem_sistemico'):
        if not resp_agendamento.agendamento.setor.uo == get_uo(request.user):
            raise PermissionDenied()

    if request.POST:
        form = ViagemSaidaForm(request.POST, request=request, resp_agendamento_id=resp_agendamento_id)
        if form.is_valid():
            form.save()
            for motorista in form.cleaned_data.get('motoristas'):
                form.instance.motoristas.add(motorista)
            turma = form.cleaned_data.get('turma')
            lista_alunos = form.cleaned_data.get('lista_alunos')
            diario = form.cleaned_data.get('diario')

            if turma:
                matriculas = turma.get_alunos_matriculados()
                for matricula in matriculas:
                    form.instance.vinculos_passageiros.add(matricula.aluno.vinculos.all()[0])
                    form.instance.save()

            if lista_alunos:
                matriculas = lista_alunos.split(',')
                for matricula in matriculas:
                    aluno = Aluno.objects.filter(matricula=matricula)
                    if aluno.exists():
                        form.instance.vinculos_passageiros.add(aluno[0].vinculos.all()[0])
                        form.instance.save()

            if diario:
                alunos = Aluno.objects.filter(matriculaperiodo__matriculadiario__diario=diario)
                if alunos.exists():
                    for aluno in alunos:
                        form.instance.vinculos_passageiros.add(aluno.vinculos.all()[0])
                        form.instance.save()

            return httprr('/frota/viagens_agendadas/', 'Viagem iniciada com sucesso.')
    else:
        form = ViagemSaidaForm(resp_agendamento_id=resp_agendamento.id, request=request)
    return locals()


@rtr('frota/templates/viagens_iniciadas.html')
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def viagens_iniciadas(request):
    title = 'Viagens Iniciadas'
    is_gerente = request.user.has_perm('frota.tem_acesso_viagem_sistemico') or request.user.is_superuser

    if not is_gerente:
        viagens = Viagem.objects.filter(chegada_data=None, agendamento_resposta__agendamento__setor__uo=get_uo(request.user)).order_by('-saida_data')
    else:
        viagens = Viagem.objects.filter(chegada_data=None).order_by('-saida_data')

    if 'all' in request.GET:
        pass
    else:
        viagens = viagens.filter(viatura__campus=get_uo(request.user)).order_by('-saida_data')

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def chegada_viagem(request, viagem_id):
    title = 'Registrar Chegada'
    viagem = get_object_or_404(Viagem, pk=viagem_id)
    resp_agendamento_id = viagem.agendamento_resposta.id

    if not request.user.has_perm('frota.tem_acesso_viagem_sistemico'):
        if not viagem.agendamento_resposta.agendamento.setor.uo == get_uo(request.user):
            raise PermissionDenied()
    if request.POST:
        form = ViagemChegadaForm(request.POST, resp_agendamento_id=resp_agendamento_id, instance=viagem)
        if form.is_valid():
            form.save()
            return httprr('/frota/viagens_iniciadas/', 'Viagem finalizada com sucesso.')
    else:
        form = ViagemChegadaForm(resp_agendamento_id=resp_agendamento_id)
    return locals()


@rtr('frota/templates/viagens.html')
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def viagens(request):
    title = 'Listar Viagens'
    hoje = datetime.datetime.today()
    data_inicio = somarDias(hoje, -30)
    data_termino = hoje
    eh_sistemico = request.user.has_perm('frota.tem_acesso_viagem_sistemico')
    if request.method == 'GET' and not 'data_inicio' in request.GET:
        form = PeriodoForm(request=request)
        form.fields['data_inicio'].initial = data_inicio
        form.fields['data_termino'].initial = data_termino
    else:
        form = PeriodoForm(request.GET, request=request)

    if form.is_valid():
        data_inicio = form.cleaned_data['data_inicio']
        data_termino = form.cleaned_data['data_termino']
        grupo_viatura = form.cleaned_data['grupo_viatura']
        uo = form.cleaned_data['uo']
        id_viagem = form.cleaned_data['id_viagem']
        passageiro = form.cleaned_data['passageiro']

        viagens = Viagem.objects.filter(saida_data__gt=data_inicio, saida_data__lt=data_termino).order_by('-saida_data')
        if request.user.has_perm('frota.tem_acesso_viagem_campus'):
            viagens = viagens.filter(agendamento_resposta__agendamento__setor__uo=get_uo(request.user))
        elif request.user.has_perm('frota.tem_acesso_viagem_operador'):
            viagens = viagens.filter(agendamento_resposta__agendamento__vinculo_solicitante__user=request.user)

        if grupo_viatura:
            viagens = viagens.filter(viatura__grupo=grupo_viatura)

        if uo:
            viagens = viagens.filter(viatura__campus=uo)

        if id_viagem:
            viagens = viagens.filter(agendamento_resposta__agendamento=id_viagem)
        if passageiro:
            viagens = viagens.filter(vinculos_passageiros=passageiro)

    return locals()


@rtr('frota/templates/agendamento.html')
def agendamento(request, agendamento_id):
    agendamento = get_object_or_404(ViagemAgendamento, id=agendamento_id)
    eh_o_chefe = False

    if request.user.is_authenticated:
        vinculo = request.user.get_vinculo()
        if vinculo.eh_servidor():
            eh_o_chefe = request.user.get_relacionamento().eh_chefe_do_setor_hoje(agendamento.setor)

        if (
            user_has_one_of_perms(
                request.user, ['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador', 'frota.tem_acesso_agendamento_agendador']
            )
            or request.user.get_relacionamento() == agendamento.avaliado_por
            or eh_o_chefe
        ):
            title = 'Dados do Agendamento da Viagem'

            resposta = ViagemAgendamentoResposta.objects.filter(agendamento=agendamento)
            if resposta:
                viatura = resposta[0].viatura
            return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def viagem(request, viagem_id):
    eh_sistemico = request.user.has_perm('frota.tem_acesso_viagem_sistemico')
    viagem = get_object_or_404(Viagem, id=viagem_id)
    title = 'Viagem #{}'.format(viagem.agendamento_resposta.agendamento.id)
    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def pdf_requisicao(request, viagem_id):
    agendamento_resposta = get_object_or_404(ViagemAgendamentoResposta, pk=viagem_id)
    try:
        setor = agendamento_resposta.agendamento.vinculo_solicitante.setor
    except Exception:
        pass
    solicitante = agendamento_resposta.agendamento.vinculo_solicitante
    dt_solicitacao = agendamento_resposta.agendamento.data_solicitacao
    hr_solicitacao = agendamento_resposta.agendamento.data_solicitacao
    avaliador = agendamento_resposta.vinculo_responsavel
    dt_avaliacao = agendamento_resposta.data_avaliacao
    hr_avaliacao = agendamento_resposta.data_avaliacao
    veiculo = agendamento_resposta.viatura
    objetivo = agendamento_resposta.agendamento.objetivo
    intinerario = agendamento_resposta.agendamento.intinerario
    dt_prev_saida = agendamento_resposta.agendamento.data_saida
    hr_prev_saida = agendamento_resposta.agendamento.data_saida
    dt_prev_chegada = agendamento_resposta.agendamento.data_chegada
    hr_prev_chegada = agendamento_resposta.agendamento.data_chegada
    lista_passageiros = ', '.join([passageiro.pessoa.nome for passageiro in agendamento_resposta.agendamento.vinculos_passageiros.all().order_by('pessoa__nome')])
    return locals()


@rtr('frota/templates/viatura.html')
@permission_required(['frota.tem_acesso_viatura_sistemico', 'frota.tem_acesso_viatura_campus', 'frota.tem_acesso_viatura_operador'])
def viatura(request, viatura_id):
    viatura = get_object_or_404(Viatura, id=viatura_id)
    title = 'Viatura {} ({})'.format(viatura.placa_codigo_atual, viatura.modelo)

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viatura_sistemico', 'frota.tem_acesso_viatura_campus', 'frota.tem_acesso_viatura_operador'])
def ordem_abastecimento(request, viagem_id):
    viagem = get_object_or_404(Viagem, id=viagem_id)
    title = 'Registrar Ordem de Abastecimento - Viagem #{}'.format(viagem.agendamento_resposta.agendamento.id)
    if request.POST:
        form = ViaturaOrdemAbastecimentoForm(request.POST, request.FILES, viagem_id=viagem_id)
        if form.is_valid():
            form.save()
            return httprr('/frota/viagem/{}/'.format(viagem_id), 'Ordem de Abastecimento cadastrada com sucesso.')
    else:
        form = ViaturaOrdemAbastecimentoForm(viagem_id=viagem_id)
    return locals()


@rtr()
@atomic
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus', 'frota.tem_acesso_viagem_operador'])
def viagem_retroativa(request):
    title = 'Viagem Retroativa'
    form = ViagemRetroativaForm(request.POST or None, request=request)
    if form.is_valid():
        v = Viagem()
        if not form.cleaned_data['agendamento_resposta']:
            a = ViagemAgendamento()
            a.status = Situacao.DEFERIDA
            a.vinculo_solicitante = form.cleaned_data['vinculo_solicitante']
            a.objetivo = form.cleaned_data['objetivo']
            a.intinerario = form.cleaned_data['itinerario']
            a.data_saida = form.cleaned_data['data_saida']
            a.data_chegada = form.cleaned_data['data_chegada']
            a.data_solicitacao = form.cleaned_data['data_saida']
            a.save()
            a.vinculos_passageiros.set(form.cleaned_data['vinculos_passageiros'])

            a.save()

            r = ViagemAgendamentoResposta()
            r.agendamento = a
            r.vinculo_responsavel = form.request.user.get_vinculo()
            r.data = datetime.datetime.now()
            r.save()

            v.agendamento_resposta = r
        else:
            v.agendamento_resposta = form.cleaned_data['agendamento_resposta']

        v.viatura = form.cleaned_data['viatura']

        v.saida_odometro = form.cleaned_data['saida_odometro']
        v.saida_data = form.cleaned_data['data_saida']
        v.saida_obs = form.cleaned_data['saida_obs']

        v.chegada_odometro = form.cleaned_data['chegada_odometro']
        v.chegada_data = form.cleaned_data['data_chegada']
        v.chegada_obs = form.cleaned_data['chegada_obs']
        v.save()

        if v.viatura.odometro < form.cleaned_data['chegada_odometro']:
            v.viatura.odometro = form.cleaned_data['chegada_odometro']
            v.viatura.save()

        v.vinculos_passageiros.set(form.cleaned_data['vinculos_passageiros'])
        v.save()

        for motorista in form.cleaned_data['motoristas']:
            v.motoristas.add(motorista)
        return httprr('/frota/viagem_retroativa/', 'Viagem retroativa #{} cadastrada com sucesso.'.format(v.agendamento_resposta.agendamento.id))

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viatura_sistemico', 'frota.tem_acesso_viatura_campus'])
def estatisticas_viaturas(request):
    # grafico 1
    title = 'Estatística de Viaturas por Campus'
    viaturas_total = Viatura.objects.all()
    conta_viatura = 0
    series = viaturas_total.values('campus__nome').annotate(qtd=Count('campus__sigla')).order_by('campus__nome')
    dados = list()
    for item in series:
        dados.append([item['campus__nome'], item['qtd']])
        conta_viatura += item['qtd']
    if dados[-1][1] == 0:
        dados.pop()
    if viaturas_total.count() != conta_viatura:
        dados.append(['SEM CAMPUS', viaturas_total.count() - conta_viatura])

    grafico1 = PieChart('grafico1', title='Viaturas por Campus', subtitle='Total de viaturas por campus', minPointLength=0, data=dados)

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viatura_sistemico', 'frota.tem_acesso_viatura_campus'])
def estatisticas_deslocamento(request):
    title = 'Relatório de Deslocamento por Viatura'
    hoje = datetime.datetime.today()
    data_inicio = somarDias(hoje, -30)
    data_termino = hoje
    form = PeriodoRelatorioViagemForm(request.GET or None, request=request)
    form.fields['data_inicio'].initial = data_inicio
    form.fields['data_termino'].initial = data_termino
    graficos = []
    if form.is_valid():
        data_inicio = form.cleaned_data['data_inicio']
        data_termino = form.cleaned_data['data_termino']
        viatura_form = form.cleaned_data['viatura']
        uo = form.cleaned_data['uo']
        if uo:
            uos = UnidadeOrganizacional.objects.suap().filter(id=uo.id)
        else:
            uos = UnidadeOrganizacional.objects.suap().all()
        for uo in uos:
            dados = list()
            viagens = Viagem.objects.filter(viatura__campus=uo, saida_data__gte=data_inicio, chegada_data__lte=data_termino)
            if viatura_form:
                viagens = viagens.filter(viatura=viatura_form)
            if viagens:
                series2 = viagens.values('viatura__placa_codigo_atual').order_by('viatura__placa_codigo_atual').annotate(count=Sum(F('chegada_odometro') - F('saida_odometro')))
                teste = list(series2.values_list('viatura__placa_codigo_atual', flat=True))
                teste2 = list(series2.values_list('count', flat=True))
                for (i, item) in enumerate(teste):
                    modelo = str(Veiculo.objects.get(placa_codigo_atual=teste[i]).modelo)
                    teste[i] = teste[i] + ' - ' + modelo
                contador = 0
                for item in teste:
                    x = []
                    x.append(item)
                    x.append(teste2[contador])
                    dados.append(x)
                    contador = contador + 1
                grafico2 = ColumnChart('grafico' + str(uo.id), title='Deslocamento por Viatura', subtitle='Número de km rodados por viatura', minPointLength=0, data=dados)
                grafico2.id = uo.id
                grafico2.h1 = UnidadeOrganizacional.objects.suap().get(pk=uo.id).nome
                graficos.append(grafico2)
            else:
                pass

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus'])
def viagens_por_viatura(request):
    title = 'Relatório de Viagem por Viatura'
    hoje = datetime.datetime.today()
    data_inicio = somarDias(hoje, -30)
    data_termino = hoje
    form = PeriodoRelatorioViagemForm(request.GET or None, request=request)
    form.fields['data_inicio'].initial = data_inicio
    form.fields['data_termino'].initial = data_termino
    existe_registro = False
    graficos = []
    if form.is_valid():
        data_inicio = form.cleaned_data['data_inicio']
        data_termino = form.cleaned_data['data_termino']
        viatura_form = form.cleaned_data['viatura']
        uo = form.cleaned_data['uo']

        viaturas = []

        if uo:
            viaturas = Viatura.objects.filter(campus=uo)
        else:
            viaturas = Viatura.objects.all()

        if viatura_form:
            viaturas = viaturas.filter(pk=viatura_form.id)

        for viatura in viaturas:
            viagens_totais = Viagem.objects.filter(saida_data__gt=data_inicio, saida_data__lt=data_termino, viatura=viatura).order_by('saida_data')
            viagens = viagens_totais.values(
                'chegada_odometro',
                'agendamento_resposta__agendamento__objetivo',
                'chegada_data',
                'saida_odometro',
                'saida_data',
                'agendamento_resposta__agendamento__vinculo_solicitante__pessoa__nome',
                'id',
                'motoristas',
                'viatura_id',
            ).annotate(distancia=F('chegada_odometro') - F('saida_odometro'))
            setattr(viatura, 'viagens', viagens)
            total = 0
            for viagem in viatura.viagens:
                if viagem['distancia']:
                    total = total + viagem['distancia']
                viagem['passageiros'] = viagens_totais.filter(id=viagem['id'])[0].get_string_passageiros()
                viagem['motoristas'] = viagens_totais.filter(id=viagem['id'])[0].get_motoristas()

            setattr(viatura, 'total', total)
            count = 0
            if len(viagens) > 0:
                existe_registro = True

            for viagem in viagens:

                if count < len(viagens) - 1 and Viagem.objects.get(id=viagem['id']).tem_descontinuidade():
                    viagens[count]['descontinuidade'] = viagens[count + 1]['saida_odometro'] - viagens[count]['chegada_odometro']
                else:
                    viagens[count]['descontinuidade'] = 0
                count += 1

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viagem_sistemico', 'frota.tem_acesso_viagem_campus'])
def estatistica_viagens_por_campus_setor(request):
    title = 'Estatística de Viagens por Campus/Setor'
    hoje = datetime.datetime.today()
    data_inicio = somarDias(hoje, -30)
    data_termino = hoje
    form = EstatisticasViagemForm(request.POST or None, request=request)
    form.fields['data_inicio'].initial = data_inicio
    form.fields['data_termino'].initial = data_termino
    existe_registro = False
    graficos = []
    if form.is_valid():
        data_inicio = form.cleaned_data['data_inicio']
        data_termino = form.cleaned_data['data_termino']
        uo = form.cleaned_data['uo']
        series = (
            Viagem.objects.filter(agendamento_resposta__agendamento__vinculo_solicitante__setor__uo=uo, saida_data__gt=data_inicio, saida_data__lt=data_termino)
            .values('agendamento_resposta__agendamento__vinculo_solicitante__setor__nome')
            .annotate(qtd=Count('agendamento_resposta__agendamento__vinculo_solicitante__setor__nome'))
            .order_by('agendamento_resposta__agendamento__vinculo_solicitante__setor__nome')
        )
        if series:
            dados = list()
            for item in series:
                dados.append([item['agendamento_resposta__agendamento__vinculo_solicitante__setor__nome'], item['qtd']])
            if dados[-1][1] == 0:
                dados.pop()
            grafico1 = PieChart('grafico1', title='Viagens por Campus/Setor', subtitle='Total de Viagens por Campus/Setor no Período Informado', minPointLength=0, data=dados)

    return locals()


@rtr()
@permission_required(['frota.tem_acesso_viatura_sistemico', 'frota.tem_acesso_viatura_campus', 'frota.tem_acesso_viatura_operador'])
def manutencaoviatura(request, servico_id):
    servico = get_object_or_404(ManutencaoViatura, pk=servico_id)
    title = 'Dados do Serviço'

    return locals()


@rtr()
@permission_required('frota.view_viagemagendamento')
def ver_calendario_agendamento(request):
    title = 'Calendário de Agendamento'

    # ------------
    # até o mês do último agendamento que 'caia' pelo menos dentro do mês corrente
    qs_solicitacoes = ViagemAgendamento.objects.filter(status__in=[Situacao.DEFERIDA, Situacao.PENDENTE]).order_by('data_saida')
    cal_meses = []

    uo = ''
    setor = ''
    status = ''
    mes_filtro = ''
    ano_filtro = ''
    if request.GET.get('status__exact'):
        status = request.GET.get('status__exact')
        qs_solicitacoes = ViagemAgendamento.objects.filter(status=status)

    data_agora = datetime.datetime.now()
    ano_corrente = data_agora.year
    mes_corrente = data_agora.month

    if request.GET.get('setor__uo__id__exact'):
        uo = get_object_or_404(UnidadeOrganizacional, pk=request.GET.get('setor__uo__id__exact'))
        qs_solicitacoes = qs_solicitacoes.filter(setor__uo=uo)

    if not request.user.has_perm('frota.tem_acesso_viatura_sistemico'):
        qs_solicitacoes = qs_solicitacoes.filter(setor__uo=get_uo(request.user))

    if request.GET.get('setor__id__exact'):
        setor = get_object_or_404(Setor, pk=request.GET.get('setor__id__exact'))
        qs_solicitacoes = qs_solicitacoes.filter(setor=setor)

    if request.GET.get('data_saida__year'):
        ano_filtro = int(request.GET.get('data_saida__year'))
        qs_solicitacoes = qs_solicitacoes.filter(data_saida__year=ano_filtro)
        ano_corrente = ano_filtro

        if request.GET.get('data_saida__month'):
            mes_filtro = int(request.GET.get('data_saida__month'))
            qs_solicitacoes = qs_solicitacoes.filter(data_saida__month=mes_filtro)
            mes_corrente = mes_filtro
        else:
            mes_corrente = 1
    else:
        qs_solicitacoes = qs_solicitacoes.filter(data_saida__year=data_agora.date().year)

    if qs_solicitacoes.exists():

        data_fim = qs_solicitacoes.latest('data_saida').data_saida
        if (data_fim.year == ano_corrente and data_fim.month >= mes_corrente) or (data_fim.year > ano_corrente):
            ultimo_ano = data_fim.year
            ultimo_mes = data_fim.month

            cal = CalendarioPlus()
            cal.mostrar_mes_e_ano = True

            mes = mes_corrente  # inicializa mês

            for ano in range(ano_corrente, ultimo_ano + 1):
                mes_final = 12  # por padrão
                if ano == ultimo_ano:
                    mes_final = ultimo_mes
                for mes in range(mes, mes_final + 1):
                    # -----------------------
                    # Adição das Solicitações
                    for solicitacao in qs_solicitacoes:
                        solicitacao_conflito = False
                        for [agenda_data_inicio, agenda_data_fim] in [[solicitacao.data_saida, solicitacao.data_chegada]]:
                            if agenda_data_inicio.year == ano and agenda_data_inicio.month == mes:

                                dia_todo_list = solicitacao.get_dia_todo_list()

                                if solicitacao.is_deferido():
                                    css = 'success'
                                elif solicitacao.is_indeferido():
                                    css = 'error'
                                else:
                                    css = 'alert'

                                # Se for o dia todo os eventos são separados, o primeiro e o ultimo tem o horário diferenciado
                                if dia_todo_list:

                                    data_fim = datetime.datetime(agenda_data_inicio.year, agenda_data_inicio.month, agenda_data_inicio.day, 23, 59, 59)  # hour,minute,second
                                    horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), data_fim.strftime("%H:%M"))

                                    descricao = '<a href="/frota/agendamento/{}/"><strong>{}</strong> {}</a>'.format(solicitacao.id, horario, solicitacao.objetivo)

                                    cal.adicionar_evento_calendario(agenda_data_inicio, data_fim, descricao, css)

                                    for dia_todo in dia_todo_list:
                                        if dia_todo.day != agenda_data_fim.day:
                                            horario = 'Todo o dia'

                                            descricao = '<a href="/frota/agendamento/{}/"><strong>{}</strong> {}</a>'.format(solicitacao.id, horario, solicitacao.objetivo)

                                            cal.adicionar_evento_calendario(dia_todo, dia_todo, descricao, css, dia_todo=True)

                                    data_inicio = datetime.datetime(agenda_data_fim.year, agenda_data_fim.month, agenda_data_fim.day, 0, 0, 0)  # hour,minute,second
                                    horario = '{} às {}'.format(data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                    descricao = '<a href="/frota/agendamento/{}/"><strong>{}</strong> {}</a>'.format(solicitacao.id, horario, solicitacao.objetivo)

                                    cal.adicionar_evento_calendario(data_inicio, agenda_data_fim, descricao, css)
                                else:
                                    horario = '{} às {}'.format(agenda_data_inicio.strftime("%H:%M"), agenda_data_fim.strftime("%H:%M"))
                                    descricao = '<a href="/frota/agendamento/{}/"><strong>{}</strong> {}</a>'.format(solicitacao.id, horario, solicitacao.objetivo)

                                    cal.adicionar_evento_calendario(agenda_data_inicio, agenda_data_fim, descricao, css)
                    cal_meses.append(cal.formato_mes(ano, mes))
                    # -------------------
                mes = 1

    return locals()


@rtr()
def autorizar_agendamento(request, agendamento_id, opcao):
    agendamento = get_object_or_404(ViagemAgendamento, pk=agendamento_id)
    eh_o_chefe = False
    vinculo = request.user.get_vinculo()
    if vinculo.eh_servidor():
        eh_o_chefe = request.user.get_relacionamento().eh_chefe_do_setor_hoje(agendamento.setor)
    if eh_o_chefe and agendamento.status == Situacao.PENDENTE:
        if opcao == '1':
            agendamento.aprovado = True
        elif opcao == '2':
            agendamento.aprovado = False
        agendamento.avaliado_por = request.user.get_relacionamento()
        agendamento.avaliado_em = datetime.datetime.now()
        agendamento.save()
        return httprr('/frota/agendamento/{}'.format(agendamento_id), 'Agendamento avaliado com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required(['frota.tem_acesso_viatura_sistemico', 'frota.tem_acesso_viatura_campus', 'frota.tem_acesso_viatura_operador'])
def controle_revisoes_viaturas(request):
    title = 'Controle das Revisões das Viaturas'
    viaturas = Viatura.objects.all().order_by('campus', 'placa_codigo_atual')
    form = ControleRevisaoForm(request.GET or None)
    if form.is_valid():
        situacao = form.cleaned_data.get('situacao')
        if form.cleaned_data.get('uo'):
            viaturas = viaturas.filter(campus=form.cleaned_data.get('uo'))
        if form.cleaned_data.get('viatura'):
            viaturas = viaturas.filter(id=form.cleaned_data.get('viatura').id)
        if situacao:
            ids_viaturas = list()
            if situacao == ControleRevisaoForm.SITUACAO_ATRASO:
                for viatura in viaturas:
                    if viatura.tem_revisao_atraso():
                        ids_viaturas.append(viatura.id)
            elif situacao == ControleRevisaoForm.SITUACAO_PREVISTA:
                for viatura in viaturas:
                    if viatura.tem_revisao_prevista():
                        ids_viaturas.append(viatura.id)
            elif situacao == ControleRevisaoForm.SITUACAO_REVISAO_KM:
                for viatura in viaturas:
                    if viatura.tem_odometro_perto_10k():
                        ids_viaturas.append(viatura.id)
            viaturas = viaturas.filter(id__in=ids_viaturas)

    return locals()


@rtr()
@permission_required('frota.change_viatura')
def editar_proxima_revisao_viatura(request, viatura_id):
    viatura = get_object_or_404(Viatura, pk=viatura_id)
    title = 'Informar Data da Próxima Revisão - {}'.format(viatura)
    form = EditarDataProximaRevisaoForm(request.POST or None, instance=viatura)
    if form.is_valid():
        form.save()
        return httprr('/frota/controle_revisoes_viaturas/', 'Data da próxima revisão cadastrada com sucesso.')
    return locals()
