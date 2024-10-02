import hashlib
import io
import os
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize, slugify

from comum.forms import CalendarioForm
from comum.models import Ano, Configuracao
from comum.utils import gerar_documento_impressao, somar_data
from djtools import layout
from djtools.db import models
from djtools.html.calendarios import Calendario
from djtools.html.graficos import PieChart, ColumnChart
from djtools.templatetags.filters import format_, format_daterange, format_datetime, in_group
from djtools.utils import get_cache, get_session_cache, httprr, permission_required, rtr, send_notification, send_mail, \
    XlsResponse, documento
from eventos.forms import (
    AdicionarParticipanteEventoForm,
    EditarParticipanteEventoForm,
    IndeferirEventoForm,
    RelatorioEventosForm,
    ImportarParticipantesForm,
    JustificativaForm,
    RealizarInscricaoForm,
    FotoEventoForm,
    AnexoEventoForm,
    ImportarListaPresencaForm,
    InformarAtividadesForm,
    InformarParticipantesForm,
    EnviarMensagemForm,
)
from eventos.models import Banner, Evento, Participante, Dimensao, TipoParticipante, AtividadeEvento


@layout.quadro('Calendário de Eventos', icone='calendar-alt', pode_esconder=True)
def index_quadros_calendario(quadro, request):
    def do():
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1)
        ultimo_dia = date(hoje.year, hoje.month, 1) - relativedelta(days=1)

        eventos = Evento.objects.filter(deferido=True, ativo=True, data_inicio__lte=primeiro_dia, data_fim__gte=ultimo_dia)
        if eventos.exists():
            cal = Calendario()
            for evento in eventos:
                css = 'info'
                cal.adicionar_evento_calendario(evento.data_inicio, evento.data_fim, evento.nome, css)

            quadro.add_itens(
                [
                    layout.ItemCalendario(calendario=cal.formato_mes(hoje.year, hoje.month)),
                    layout.ItemAcessoRapido(titulo='Calendário Anual', url='/eventos/calendario_eventos/'),
                ]
            )

        return quadro

    return get_session_cache(request, 'index_quadros_eventos', do, 8 * 3600)


@layout.quadro('Eventos', icone='calendar-o')
def index_quadros(quadro, request):
    grupos = request.user.groups.values_list('pk', flat=True)
    dimensoes_sistemicas = Dimensao.objects.filter(grupos_avaliadores_sistemicos__in=grupos).values_list('pk', flat=True)
    dimensoes_locais = Dimensao.objects.filter(grupos_avaliadores_locais__in=grupos).values_list('pk', flat=True)
    if dimensoes_sistemicas or dimensoes_locais:
        eventos_sistemicos = Evento.objects.filter(submetido=True, deferido__isnull=True, dimensoes__in=dimensoes_sistemicas).count()
        eventos_locais = 0
        if request.user.get_vinculo().setor:
            eventos_locais = Evento.objects.filter(campus=request.user.get_vinculo().setor.uo, submetido=True, deferido__isnull=True, dimensoes__in=dimensoes_locais).count()
        eventos_nao_avaliados = eventos_sistemicos + eventos_locais
        if eventos_nao_avaliados > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Evento{}'.format(pluralize(eventos_nao_avaliados, 's')),
                    subtitulo='Não avaliado{}'.format(pluralize(eventos_nao_avaliados, 's')),
                    qtd=eventos_nao_avaliados,
                    url=eventos_sistemicos and '/admin/eventos/evento/?tab=tab_aguardando_aprovacao' or '/admin/eventos/evento/?tab=tab_aguardando_minha_aprovacao',
                )
            )

    return quadro


@layout.quadro('Comunicado', icone='users', pode_esconder=True)
def index_quadros_banners(quadro, request):
    def do():
        hoje = datetime.now()
        banner = Banner.objects.filter(data_inicio__lte=hoje, data_termino__gte=hoje).first()
        if banner and bool(Configuracao.get_valor_por_chave('comum', 'quadro_banner')) is True:
            quadro.add_item(layout.ItemTitulo(titulo=banner.titulo))
            quadro.add_item(layout.ItemImagem(titulo=banner.titulo, url=banner.link, path=banner.imagem.url))

            return quadro

    return get_cache('index_quadros_banners', do, 24 * 3600)


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()
    servicos_anonimos.append(dict(categoria='Eventos', url="/eventos/inscricao_publica/", icone="certificate", titulo='Realizar Inscrição em Evento'))
    return servicos_anonimos


@rtr()
def inscricao_publica(request, evento_id=None):
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    if evento_id:
        evento = get_object_or_404(Evento, pk=evento_id)
        if not (evento.ativo and evento.deferido):
            return httprr('/eventos/inscricao_publica/', 'Você não pode se inscrever nesse evento.', 'error')
        if not evento.is_periodo_inscricao():
            return httprr('/eventos/inscricao_publica/', 'Evento fora do período de inscrição.', 'error')
        if not evento.tem_vagas_disponiveis():
            return httprr('/eventos/inscricao_publica/', 'Todas as vagas já foram preenchidas.', 'error')
        title = evento.nome
        form = RealizarInscricaoForm(data=request.POST or None, evento=evento)
        form.fields['publico_alvo'].queryset = evento.publico_alvo.all()
        if form.is_valid():
            form.processar()
            return httprr(
                '/eventos/inscricao_publica/',
                'Inscrição realizada com sucesso. O comprovante de inscrição será enviado para o e-mail informado assim que a inscrição for confirmada.',
            )
    else:
        title = 'Realizar Inscrição em Evento'
        agora = datetime.today()
        eventos = Evento.objects.filter(inscricao_publica=True, ativo=True, deferido=True)
        eventos_entre_datas = eventos.filter(data_inicio_inscricoes__lt=agora, data_fim_inscricoes__gt=agora)
        eventos_data_hora_inicio = eventos.filter(Q(data_inicio_inscricoes=agora), Q(hora_inicio_inscricoes__isnull=True) | Q(hora_inicio_inscricoes__lte=agora))
        eventos_data_hora_fim = eventos.filter(Q(data_fim_inscricoes=agora), Q(hora_fim_inscricoes__isnull=True) | Q(hora_fim_inscricoes__gte=agora))
        eventos = eventos_entre_datas | eventos_data_hora_inicio | eventos_data_hora_fim
        eventos = eventos.order_by('nome')

        calendario = []
        dia = agora
        while len(calendario) < 7:
            calendario.append((dia.strftime('%d/%m/%Y'), eventos.filter(data_inicio_inscricoes__lt=dia, data_fim_inscricoes__gte=dia)))
            dia = somar_data(dia, qtd_dias=1)

    return locals()


@rtr()
@login_required
def calendario_eventos(request):
    title = 'Calendário de Eventos por Campus'
    uo = request.user.get_relacionamento().setor.uo
    ano = Ano.objects.filter(ano=date.today().year).first()

    form = CalendarioForm(request.POST or None)
    ano = Ano.objects.get(ano=date.today().year)

    if form.is_valid():
        if form.cleaned_data.get('ano'):
            ano = form.cleaned_data['ano']
        if form.cleaned_data.get('uo'):
            uo = form.cleaned_data['uo']

    eventos = Evento.objects.filter(campus=uo, ativo=True, deferido=True, data_inicio__year__lte=ano.ano, data_fim__year__gte=ano.ano)
    calendario = Calendario(tipos_eventos_default=False)
    calendario.adicionar_tipo_evento('info', 'Evento/Data Comemorativa')
    for evento in eventos:
        css = 'info'
        calendario.adicionar_evento_calendario(evento.data_inicio, evento.data_fim, evento.nome, css)

    calendario_ano = calendario.formato_ano(ano.ano)
    return locals()


@rtr()
@permission_required('eventos.change_evento')
def evento(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    title = evento.nome
    tipos_participantes = []
    queries = dict()
    for tipo_participante in evento.tipos_participante.all():
        participantes = evento.participantes.filter(tipo=tipo_participante).order_by('nome')
        query = request.GET.get(f'q{tipo_participante.id}')
        if query:
            participantes_nome = participantes.filter(nome__unaccent__icontains=query)
            participantes_cpf = participantes.filter(cpf__startswith=query)
            participantes = participantes_nome | participantes_cpf
        queries[tipo_participante.id] = query
        tipos_participantes.append((tipo_participante, participantes))

    pode_gerenciar = evento.pode_gerenciar(request.user)
    pode_avaliar = evento.pode_avaliar(request.user)
    pode_finalizar = evento.pode_finalizar(request.user)
    participacoes_inconsistentes = evento.get_participacoes_inconsistentes()

    if pode_gerenciar and evento.ativo and evento.deferido:
        if 'excluir_foto' in request.GET:
            evento.fotoevento_set.filter(pk=request.GET['excluir_foto']).delete()
            return httprr('/eventos/evento/{}/?tab=fotos'.format(evento_id), 'Foto excluída com sucesso')
        if 'excluir_anexo' in request.GET:
            evento.anexoevento_set.filter(pk=request.GET['excluir_anexo']).delete()
            return httprr('/eventos/evento/{}/?tab=anexos'.format(evento_id), 'Anexo excluído com sucesso')

    return locals()


@rtr()
@login_required()
def deferir(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_avaliar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode avaliar este evento.')
    evento.deferir(request.user)
    titulo = '[SUAP] Avaliação de Evento'
    texto = '<h1>Avaliação de Evento</h1>'
    texto += '<h2>{}</h2>'.format(evento.nome)
    texto += '<p>O evento <strong>{}</strong> foi deferido.</p>'.format(evento.nome)
    texto += '<p>--</p>'
    texto += '<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(evento.get_absolute_url())
    if evento.coordenador:
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [evento.coordenador.get_vinculo()])
    return httprr('/eventos/evento/{}/'.format(evento.pk), 'O evento foi deferido.')


@rtr()
@login_required()
def indeferir(request, evento_id):
    title = 'Indeferir Evento'
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_avaliar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode avaliar este evento.')
    form = IndeferirEventoForm(request.POST or None, instance=evento, request=request)
    if form.is_valid():
        evento = form.save()
        titulo = '[SUAP] Avaliação de Evento'
        texto = '<h1>Avaliação de Evento</h1>'
        texto += '<h2>{}</h2>'.format(evento.nome)
        texto += '<p>O evento <strong>{}</strong> foi indeferido.</p>'.format(evento.nome)
        texto += '<p>--</p>'
        texto += '<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(evento.get_absolute_url())
        if evento.coordenador:
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [evento.coordenador.get_vinculo()])
        return httprr('..', 'O evento foi indeferido.')
    return locals()


@rtr()
@login_required()
def ativar_evento(request, evento_id):
    title = 'Ativar Evento'
    evento = get_object_or_404(Evento, pk=evento_id)
    if not request.user.is_superuser and not evento.pode_avaliar(request.user):
        raise PermissionDenied('Você não pode ativar este evento.')
    form = JustificativaForm(data=request.POST or None)
    if form.is_valid():
        justificativa = form.cleaned_data['justificativa']
        evento.ativar(justificativa, request.user)
        if evento.coordenador:
            titulo = '[SUAP] Ativação de Evento'
            texto = '<h1>Ativação de Evento</h1>'
            texto += '<h2>{}</h2>'.format(evento.nome)
            texto += '<p>O evento <strong>{}</strong> foi <strong>ativado</strong> por {}.</p>'.format(evento.nome, request.user)
            texto += '<p>Justificativa: <br>{}</p>'.format(justificativa)
            texto += '<p>--</p>'
            texto += '<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(evento.get_absolute_url())
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [evento.coordenador.get_vinculo()])
        return httprr('..', 'O evento foi ativado.')
    return locals()


@rtr()
@login_required()
def desativar_evento(request, evento_id):
    title = 'Inativar Evento'
    evento = get_object_or_404(Evento, pk=evento_id)
    if not request.user.is_superuser and not evento.pode_avaliar(request.user):
        raise PermissionDenied('Você não pode inativar este evento.')
    form = JustificativaForm(data=request.POST or None)
    if form.is_valid():
        justificativa = form.cleaned_data['justificativa']
        evento.suspender(justificativa, request.user)
        if evento.coordenador:
            titulo = '[SUAP] Inativação de Evento'
            texto = '<h1>Inativação de Evento</h1>'
            texto += '<h2>{}</h2>'.format(evento.nome)
            texto += '<p>O evento <strong>{}</strong> foi <strong>inativado</strong> por {}.</p>'.format(evento.nome, request.user)
            texto += '<p>Justificativa: <br>{}</p>'.format(justificativa)
            texto += '<p>--</p>'
            texto += '<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(evento.get_absolute_url())
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [evento.coordenador.get_vinculo()])
        return httprr('..', 'O evento foi inativado.')
    return locals()


@rtr()
@login_required()
def submeter(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.coordenador or request.user.get_vinculo() != evento.coordenador.get_vinculo():
        raise PermissionDenied('Apenas o coordenador do evento pode submetê-lo.')
    evento.submeter(request.user)
    return httprr(request.META.get('HTTP_REFERER', '..'), 'O evento foi submetido.')


@rtr()
@login_required()
def cancelar_avaliacao(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_avaliar(request.user) and evento.submetido and evento.deferido is not None:
        raise PermissionDenied('Você não pode cancelar a avaliação desse evento.')
    evento.cancelar_avaliacao(request.user)
    return httprr(request.META.get('HTTP_REFERER', '..'), 'A avaliação do evento foi cancelada.')


@rtr()
@login_required()
def cancelar(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not in_group(request.user, 'Coordenador de Comunicação Sistêmico'):
        raise PermissionDenied('Você não tem permissão para cancelar este evento.')
    evento.cancelar(request.user)
    return httprr(request.META.get('HTTP_REFERER', '..'), 'O evento foi cancelado com sucesso.')


@rtr()
@login_required()
def desfazer_cancelamento(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not in_group(request.user, 'Coordenador de Comunicação Sistêmico'):
        raise PermissionDenied('Você não tem permissão para desfazer o cancelamento deste evento.')
    evento.desfazer_cancelamento(request.user)
    return httprr(request.META.get('HTTP_REFERER', '..'), 'O evento teve o cancelamento desfeito com sucesso.')


@rtr()
@login_required()
def desfazer_finalizacao(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_gerenciar(request.user):
        raise PermissionDenied('Você não tem permissão para desfazer a finalização deste evento.')
    evento.desfazer_finalizacao(request.user)
    return httprr(request.META.get('HTTP_REFERER', '..'), 'O evento teve a finalização desfeita com sucesso.')


@rtr()
@login_required()
def devolver(request, evento_id):
    title = 'Devolver Evento'
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_avaliar(request.user):
        raise PermissionDenied('Você não pode devolver este evento.')
    form = JustificativaForm(data=request.POST or None)
    if form.is_valid():
        justificativa = form.cleaned_data['justificativa']
        evento.devolver(justificativa, request.user)
        titulo = '[SUAP] Devolução de Evento'
        texto = '<h1>devolução de Evento</h1>'
        texto += '<h2>{}</h2>'.format(evento.nome)
        texto += '<p>O evento <strong>{}</strong> foi <strong>devolvido</strong> por {}.</p>'.format(evento.nome, request.user)
        texto += '<p>Justificativa: <br>{}</p>'.format(justificativa)
        texto += '<p>--</p>'
        texto += '<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(evento.get_absolute_url())
        if evento.coordenador:
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [evento.coordenador.get_vinculo()])
        return httprr('..', 'O evento foi desativado.')
    return locals()


@rtr()
@login_required()
def finalizar(request, evento_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_gerenciar(request.user) or not evento.pode_finalizar(request.user):
        raise PermissionDenied('Você não pode finalizar este evento.')
    evento.finalizar(request.user)
    return httprr(request.META.get('HTTP_REFERER', '..'), 'O evento foi finalizado com sucesso.')


@permission_required('eventos.change_evento')
@rtr()
def relatorio(request):
    title = 'Relatório de Eventos'
    form = RelatorioEventosForm(request.POST or None)
    if form.is_valid():
        eventos = Evento.objects.filter(deferido=True)
        dimensao = form.cleaned_data['dimensao']
        ano = form.cleaned_data['ano']
        campus = form.cleaned_data['campus']
        setor = form.cleaned_data['setor']
        if dimensao:
            eventos = eventos.filter(dimensoes=dimensao)
        if ano != 'Todos':
            eventos = eventos.filter(Q(data_inicio__year__lte=int(ano), data_fim__year__gte=int(ano)) | Q(data_fim__isnull=True, data_inicio__year=int(ano)))
        if setor != 'Todos':
            eventos = eventos.filter(setor=int(setor))
        if campus:
            eventos = eventos.filter(campus=campus)
        else:
            dados = eventos.values('campus__nome').annotate(qtd=models.Count('campus__nome')).order_by('campus__nome')
            dados_grafico = list()
            for dado in dados:
                dado_grafico = list()
                dado_grafico.append(dado['campus__nome'])
                dado_grafico.append(dado['qtd'])
                dados_grafico.append(dado_grafico)

            grafico_campus = PieChart('grafico_campus', title='Por Campus', subtitle='Quantidade de Eventos por Campus', minPointLength=0, data=dados_grafico)

        dados = eventos.filter(natureza__isnull=False).values('natureza__descricao').annotate(qtd=models.Count('natureza__descricao')).order_by('natureza__descricao')
        dados_grafico = list()
        for dado in dados:
            dado_grafico = list()
            dado_grafico.append(dado['natureza__descricao'])
            dado_grafico.append(dado['qtd'])
            dados_grafico.append(dado_grafico)

        grafico_natureza = PieChart('grafico_natureza', title='Por Natureza', subtitle='Quantidade de Eventos por Natureza', minPointLength=0, data=dados_grafico)

        dados = eventos.filter(tipo__isnull=False).values('tipo__descricao').annotate(qtd=models.Count('tipo__descricao')).order_by('tipo__descricao')
        dados_grafico = list()
        for dado in dados:
            dado_grafico = list()
            dado_grafico.append(dado['tipo__descricao'])
            dado_grafico.append(dado['qtd'])
            dados_grafico.append(dado_grafico)

        grafico_tipo = PieChart('grafico_tipo', title='Por Tipo', subtitle='Quantidade de Eventos por Tipo', minPointLength=0, data=dados_grafico)

        dados = (
            eventos.filter(classificacao__isnull=False)
            .values('classificacao__descricao')
            .annotate(qtd=models.Count('classificacao__descricao'))
            .order_by('classificacao__descricao')
        )
        dados_grafico = list()
        for dado in dados:
            dado_grafico = list()
            dado_grafico.append(dado['classificacao__descricao'])
            dado_grafico.append(dado['qtd'])
            dados_grafico.append(dado_grafico)

        grafico_classificacao = PieChart(
            'grafico_classificacao', title='Por Classificação', subtitle='Quantidade de Eventos por Classificação', minPointLength=0, data=dados_grafico
        )

        dados = (
            eventos.filter(publico_alvo__isnull=False).values('publico_alvo__descricao').annotate(qtd=models.Count('publico_alvo__descricao')).order_by('publico_alvo__descricao')
        )
        dados_grafico = list()
        for dado in dados:
            dado_grafico = list()
            dado_grafico.append(dado['publico_alvo__descricao'])
            dado_grafico.append(dado['qtd'])
            dados_grafico.append(dado_grafico)

        grafico_publico_alvo = PieChart('grafico_publico_alvo', title='Por Público Alvo', subtitle='Quantidade de Eventos por Público Alvo', minPointLength=0, data=dados_grafico)

        dados = eventos.filter(dimensoes__isnull=False).values('dimensoes__descricao').annotate(qtd=models.Count('dimensoes__descricao')).order_by('dimensoes__descricao')
        dados_grafico = list()
        for dado in dados:
            dado_grafico = list()
            dado_grafico.append(dado['dimensoes__descricao'])
            dado_grafico.append(dado['qtd'])
            dados_grafico.append(dado_grafico)

        grafico_dimensao = ColumnChart(
            'grafico_dimensao', title='Por Dimensão',
            subtitle='Quantidade de Eventos por Dimensão',
            minPointLength=0, data=dados_grafico
        )

    return locals()


@rtr()
@login_required()
def adicionar_participante(request, evento_id, tipo_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    tipo_participante = TipoParticipante.objects.get(pk=tipo_id)
    if not evento.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')
    title = 'Adicionar {}'.format(tipo_participante)
    participante = Participante(evento=evento)
    form = AdicionarParticipanteEventoForm(request.POST or None, instance=participante, tipo_participante=tipo_participante, evento=evento)
    if tipo_participante.tipo_participacao.descricao.lower() == 'participante':
        form.fields['publico_alvo'].queryset = evento.publico_alvo.all()
    if form.is_valid():
        form.instance.tipo_id = tipo_id
        form.save()
        return httprr('..', '{} adicionado com sucesso.'.format(tipo_participante))
    return locals()


@rtr()
@login_required()
def editar_participante(request, participante_id):
    participante = get_object_or_404(Participante, pk=participante_id)
    if not participante.evento.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')
    title = 'Atualizar {}'.format(participante.tipo)
    form = EditarParticipanteEventoForm(data=request.POST or None, instance=participante)
    if participante.tipo.tipo_participacao.descricao.lower() == 'participante':
        form.fields['publico_alvo'].queryset = participante.evento.publico_alvo.all()
    if form.is_valid():
        form.save()
        return httprr('..', '{} atualizado com sucesso.'.format(participante.tipo))
    return locals()


@rtr()
@login_required()
def importar_participantes_evento(request, evento_id, tipo_id):
    obj = get_object_or_404(Evento, pk=evento_id)
    if not obj.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')
    title = 'Importar Participantes'
    form = ImportarParticipantesForm(obj, data=request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        form.processar(tipo_id)
        return httprr('..', 'Participantes adicionados com sucesso.')
    return locals()


@login_required()
def exportar_participantes_evento(request, evento_id, tipo_id):
    obj = get_object_or_404(Evento, pk=evento_id)
    qs = obj.participantes.filter(tipo_id=tipo_id)
    rows = [['#', 'Nome', 'CPF', 'Tipo', 'Público Alvo', 'E-mail', 'Telefone', 'Data de Cadastro', 'Inscrição Validada', 'Inscrição Confirmada', 'Presença Confirmada', 'Certificado Enviado', 'Carga Horária']]
    for i, p in enumerate(qs):
        row = [
            format_(i + 1), format_(p.nome), format_(p.cpf), format_(p.tipo),
            format_(p.publico_alvo), format_(p.email), format_(p.telefone), format_(p.data_cadastro),
            format_(p.inscricao_validada, False), format_(p.presenca_confirmada, False),
            format_(p.certificado_enviado, False), format_(p.carga_horaria, False)
        ]
        rows.append(row)
    return XlsResponse(rows)


@login_required
def confirmar_inscricao(request, evento_id, tipo_participante_id, pks):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')

    pks = pks.split('_')
    participantes = '0' in pks and evento.participantes.all() or evento.participantes.filter(pk__in=pks)
    participantes = participantes.filter(tipo=tipo_participante_id)
    emails = []
    qtd_inscroes_confirmadas = 0
    for participante in participantes:
        if not participante.inscricao_validada:
            qtd_inscroes_confirmadas += 1

        participante.inscricao_validada = True
        participante.save()
        emails.append(participante.email)

    texto = 'Sua inscrição no evento "{}" foi confirmada.'.format(evento.nome)
    titulo = '[SUAP] Confirmação de Inscrição em Evento'
    html = '<h1>Confirmação de Inscrição</h1>'
    html += '<h2>{}</h2>'.format(evento.nome)
    html += '<p>Sua inscrição no evento <strong>{}</strong> foi <strong>confirmada</strong>.</p>'.format(evento.nome)
    html += '<p>--</p>'
    html += '<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(evento.get_absolute_url())

    for email in emails:
        send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True, html=html)

    url = request.META.get('HTTP_REFERER', f'/eventos/evento/{evento_id}/?tab=participante{tipo_participante_id}#participantes')
    if qtd_inscroes_confirmadas == 0:
        return httprr(url, 'Nenhuma inscrição confirmada.', tag='error')

    return httprr(url, f'{qtd_inscroes_confirmadas} inscrição(ões) confirmada(s) com sucesso.')


@login_required
def confirmar_presenca(request, evento_id, tipo_participante_id, pks):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')
    pks = pks.split('_')
    participantes = '0' in pks and evento.participantes.all() or evento.participantes.filter(pk__in=pks)
    participantes = participantes.filter(tipo=tipo_participante_id)
    qtd_presencas_confirmadas = 0
    for participante in participantes.filter(inscricao_validada=True):
        if not participante.presenca_confirmada:
            qtd_presencas_confirmadas += 1

        participante.presenca_confirmada = True
        participante.save()

    url = request.META.get('HTTP_REFERER', f'/eventos/evento/{evento_id}/?tab=participante{tipo_participante_id}#participantes')
    if qtd_presencas_confirmadas == 0:
        return httprr(url, 'Nenhuma presença confirmada.', tag='error')

    return httprr(url, f'{qtd_presencas_confirmadas} presença(s) confirmada(s) com sucesso.')


@login_required
def enviar_certificados(request, evento_id, tipo_participante_id, pks):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_gerenciar(request.user):
        raise PermissionDenied('Você não pode gerenciar este evento.')

    if not evento.gera_certificado:
        raise PermissionDenied('Este evento não está configurado para gerar certificados.')

    if not evento.data_emissao_certificado:
        evento.data_emissao_certificado = datetime.now()
        if evento.data_fim is None:
            evento.data_fim = evento.data_inicio
        if evento.data_emissao_certificado.date() < evento.data_fim:
            evento.data_emissao_certificado = evento.data_fim
        evento.save()

    pks = pks.split('_')
    participantes = '0' in pks and evento.participantes.all() or evento.participantes.filter(pk__in=pks)
    participantes = participantes.filter(tipo=tipo_participante_id)
    qtd_emails_enviado = 0
    for participante in participantes.filter(presenca_confirmada=True):
        if not participante.get_ch_total():
            continue
        atividades = AtividadeEvento.objects.filter(evento=evento, participantes=participante)
        if participante.codigo_geracao_certificado is None:
            participante.certificado_enviado = True
            participante.codigo_geracao_certificado = hashlib.sha1(
                '{}{}{}{}{}'.format(participante.nome, participante.email, participante.evento_id, participante.data_cadastro, settings.SECRET_KEY).encode()
            ).hexdigest()[0:16]
            participante.save()
        url = f'{settings.SITE_URL}/eventos/baixar_certificado/{evento.id}/?hash={participante.codigo_geracao_certificado}'
        conteudo = """
            <h1>Certificação de Participação</h1>
            <h2>{0}</h2>
            <p>Caro(a) {1},</p>
            <p>Para gerar o seu certificado de participação no evento "{0}", acesse:</p>
        """.format(
            evento.nome, participante.nome
        )
        conteudo = '{}<p><a href="{}">Certificado de Partificação no Evento</a></p>'.format(conteudo, url)
        if atividades.count() > 1:
            for atividade in atividades:
                url_atividade = f'{settings.SITE_URL}/eventos/baixar_certificado/{evento.id}/{atividade.id}/?hash={participante.codigo_geracao_certificado}'
                conteudo = '{}<p><a href="{}">Certificado de Partificação - {}</a></p>'.format(conteudo, url_atividade, atividade)
        send_mail(f'[SUAP] Certificado de Participação - {evento.nome}', conteudo, settings.DEFAULT_FROM_EMAIL, [participante.email])
        qtd_emails_enviado += 1

    url = request.META.get('HTTP_REFERER', f'/eventos/evento/{evento_id}/?tab=participante{tipo_participante_id}#participantes')
    if qtd_emails_enviado == 0:
        return httprr(url, 'Nenhum e-mail enviado.', tag='error')

    return httprr(url, f'{qtd_emails_enviado} E-mail(s) enviado(s) com sucesso.')


@rtr()
def baixar_certificado(request, evento_id=None, atividade_id=None):
    codigo_geracao_certificado = request.GET.get("hash")
    if codigo_geracao_certificado:
        participante = get_object_or_404(Participante, codigo_geracao_certificado=codigo_geracao_certificado)
        atividades = participante.get_atividades()
        evento = get_object_or_404(Evento, pk=participante.evento.id)
    else:
        evento = get_object_or_404(Evento, pk=evento_id)
        tipo_participante = request.GET.get('tipo-participante')
        if not tipo_participante:
            return httprr(f'/eventos/evento/{evento.id}/?tab=detalhamento', 'Tipo de Participante não informado.', 'error')
        atividades = []
        participante = Participante(nome='Participante Teste', cpf='000.000.000-00', evento=evento)
        participante.tipo = TipoParticipante.objects.get(pk=tipo_participante)
        participante.codigo_geracao_certificado = 'xxxxxxxxx'

    url_suap = settings.SITE_URL
    modelo_certificado = participante.get_modelo_certificado()
    if not modelo_certificado:
        return httprr('..', 'Participante sem modelo de certificado definido.', 'error')
    atividades_list = []
    if atividade_id:
        atividades = atividades.filter(id=atividade_id)

    count = len(atividades)
    for i, a in enumerate(atividades):
        if i == 0:
            if len(atividades) == 1:
                atividades_list.append('da atividade ')
            else:
                atividades_list.append('das atividades ')
        if i > 0 and i <= count - 1:
            atividades_list.append(' e ' if i == count - 1 else ', ')
        atividades_list.append(str(a))

    if participante.tipo.tipo_participacao.descricao.lower() != 'participante':
        tipo_participacao = 'como {}'.format(participante.tipo.tipo_participacao.descricao.lower())
    else:
        tipo_participacao = ''

    if evento.data_inicio != evento.data_fim and evento.data_fim:
        periodo_realizacao = 'no período de {}'.format(format_daterange(evento.data_inicio, evento.data_fim))
    else:
        periodo_realizacao = 'em {}'.format(format_datetime(evento.data_inicio))

    dicionario = {
        '#INSTITUICAO#': Configuracao.get_valor_por_chave('comum', 'instituicao'),
        '#NOMEDOPARTICIPANTE#': participante.nome,
        '#TIPODOPARTICIPANTE#': participante.tipo.tipo_participacao.descricao,
        '#TIPOPARTICIPACAO#': tipo_participacao,
        '#PARTICIPANTE#': participante.nome,
        '#CPF#': participante.cpf,
        '#NOMEDOEVENTO#': evento.nome,
        '#EVENTO#': evento.nome,
        '#ATIVIDADES#': ''.join(atividades_list),
        '#LOCAL#': evento.local,
        '#CAMPUS#': participante.evento.campus,
        '#CARGAHORARIA#': participante.get_ch_total(atividades),
        '#DATAINICIALADATAFINAL#': format_daterange(evento.data_inicio, evento.data_fim),
        '#PERIODOREALIZACAO#': periodo_realizacao,
        '#SETORRESPONSAVEL#': evento.setor and 'pelo setor {}'.format(evento.setor) or '',
        '#CIDADE#': evento.campus.municipio.nome,
        '#UF#': evento.campus.municipio.uf,
        '#DATAEMISSAO#': format_datetime(date.today()),  # evento.data_emissao_certificado
        '#DATA#': format_datetime(date.today()),
        '#CODIGOVERIFICADOR#': 'Este documento foi emitido pelo SUAP. Para comprovar sua autenticidade acesse a página '
        '{}/eventos/baixar_certificado/?hash={}'.format(url_suap, participante.codigo_geracao_certificado),
    }
    caminho_arquivo = gerar_documento_impressao(dicionario, io.BytesIO(modelo_certificado.read()))
    if not caminho_arquivo:
        aba = slugify(participante.tipo.tipo_participacao.descricao)
        return httprr(f'/eventos/evento/{evento.id}/?tab={aba}', 'Documento não encontrado.', 'error')

    nome_arquivo = caminho_arquivo.split('/')[-1]
    try:
        arquivo = open(caminho_arquivo, "rb")
    except Exception:
        aba = slugify(participante.tipo.tipo_participacao.descricao)
        return httprr(f'/eventos/evento/{evento.id}/?tab={aba}', 'Modelo de certificado não encontrado.', 'error')

    content_type = caminho_arquivo.endswith('.pdf') and 'application/pdf' or 'application/vnd.ms-word'
    response = HttpResponse(arquivo.read(), content_type=content_type)
    response['Content-Disposition'] = 'attachment; filename={}'.format(nome_arquivo)
    arquivo.close()
    os.unlink(caminho_arquivo)
    return response


@rtr()
@login_required()
@permission_required('eventos.change_evento')
def adicionar_anexo_evento(request, evento_id):
    obj = get_object_or_404(Evento, pk=evento_id)
    form = AnexoEventoForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.save(obj)
        return httprr('..', 'Anexo adicionado com sucesso')
    return locals()


@rtr()
@login_required()
@permission_required('eventos.change_evento')
def adicionar_foto_evento(request, evento_id):
    obj = get_object_or_404(Evento, pk=evento_id)
    form = FotoEventoForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.save(obj)
        return httprr('..', 'Foto adicionada com sucesso')
    return locals()


@login_required
def enviar_link_registro_presenca(request, evento_id, tipo_participante_id, pks):
    evento = get_object_or_404(Evento, pk=evento_id, registrar_presenca_online=True)
    if not evento.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')
    if not evento.estah_em_periodo_realizacao():
        raise PermissionDenied('Evento encerrado.')
    pks = pks.split('_')
    participantes = '0' in pks and evento.participantes.all() or evento.participantes.filter(pk__in=pks)
    participantes = participantes.filter(tipo=tipo_participante_id)
    for participante in participantes.filter(inscricao_validada=True, presenca_confirmada=False):
        hash = signing.dumps({"participante_id": participante.id})
        url = f'{settings.SITE_URL}/eventos/confirmar_presenca_por_link/{evento.id}/{participante.id}?hash={hash}'
        conteudo = """
            <h1>Confirmar Presença no Evento</h1>
            <h2>{0}</h2>
            <p>Caro(a) {1},</p>
            <p>Para confirmar sua presença no evento "{0}", acesse: <a href="{2}">{2}</a></p>
        """.format(
            evento.nome, participante.nome, url
        )
        send_mail(f'[SUAP] Confirmar Presença no Evento - {evento.nome}', conteudo, settings.DEFAULT_FROM_EMAIL, [participante.email])

    url = request.META.get('HTTP_REFERER', f'/eventos/evento/{evento_id}/?tab=participante{tipo_participante_id}#participantes')
    return httprr(url, 'Emails enviados com sucesso.')


def confirmar_presenca_por_link(request, evento_id, participante_id):
    try:
        if not participante_id == str(signing.loads(request.GET['hash']).get('participante_id')):
            raise PermissionDenied()
    except Exception:
        raise PermissionDenied()
    evento = get_object_or_404(Evento, pk=evento_id, registrar_presenca_online=True)
    if not evento.estah_em_periodo_realizacao():
        raise PermissionDenied('Evento encerrado.')

    participante = get_object_or_404(Participante, pk=participante_id)
    participante.presenca_confirmada = True
    participante.save()
    return httprr('/', f'Presença confirmada com sucesso no evento {evento.nome}.')


@rtr()
@login_required()
def importar_lista_presenca(request, evento_id, tipo_id):
    evento = get_object_or_404(Evento, pk=evento_id)
    if not evento.pode_gerenciar(request.user) and not request.user.is_superuser:
        raise PermissionDenied('Você não pode gerenciar este evento.')

    title = 'Importar Lista de Presença'
    form = ImportarListaPresencaForm(evento, tipo_id, data=request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Presenças atualizadas com sucesso.')
    return locals()


@rtr()
@permission_required('eventos.change_evento')
def informar_atividades(request, participante_id):
    participante = get_object_or_404(Participante, pk=participante_id)
    title = 'Inscrever Participante'
    form = InformarAtividadesForm(data=request.POST or None, instance=participante)
    if form.is_valid():
        form.save()
        return httprr('..', 'Participante inscrito com sucesso.')
    return locals()


@rtr()
@permission_required('eventos.change_evento')
def informar_participantes(request, pk, atividade_id):
    obj = get_object_or_404(Evento, pk=pk)
    title = 'Informar Participantes'
    form = InformarParticipantesForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.processar(atividade_id)
        return httprr('..', 'Participantes informados com sucesso.')
    return locals()


@rtr()
@permission_required('eventos.change_evento')
def lista_participantes(request, pk, atividade_id):
    atividade = get_object_or_404(AtividadeEvento, pk=atividade_id)
    evento = get_object_or_404(Evento, pk=pk)
    title = 'Lista de Presença - {}'.format(atividade)
    inscritos = Participante.objects.filter(evento=pk, atividades=atividade_id)
    popup = ''
    q = request.GET.get('q', '')
    if request.GET.get('_popup'):
        popup = '&_popup=1'
    if q:
        inscritos = inscritos.filter(nome__unaccent__icontains=q) | inscritos.filter(cpf__contains=q)
    inscritos = inscritos.order_by('nome')
    pode_gerenciar = request.user.is_superuser or evento.pode_gerenciar(request.user)
    presentes = atividade.participantes.values_list('id', flat=True)
    if request.POST:
        for id in request.POST.getlist('adicionar'):
            atividade.participantes.add(id)
        for id in request.POST.getlist('remover'):
            atividade.participantes.remove(id)
        atividade.participantes.update(inscricao_validada=True, presenca_confirmada=True)
        url = '/eventos/lista_participantes/{}/{}/?q={}{}'.format(pk, atividade_id, q, popup)
        return httprr(url, 'Lista atualizada com sucesso.')
    return locals()


@documento()
@rtr()
@permission_required('eventos.change_evento')
def lista_participantes_pdf(request, pk, atividade_id):
    atividade = get_object_or_404(AtividadeEvento, pk=atividade_id)
    evento = get_object_or_404(Evento, pk=pk)
    q = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    participantes = Participante.objects.filter(evento=pk, atividades=atividade_id)
    if q:
        participantes = participantes.filter(nome__unaccent__icontains=q) | participantes.filter(cpf__contains=q)

    if tipo == 'todos':
        title = 'Lista de Inscritos - {}'.format(atividade)
    elif tipo == 'confirmados':
        title = 'Lista Presentes - {}'.format(atividade)
        presentes = atividade.participantes.values_list('id', flat=True)
        participantes = participantes.filter(id__in=presentes)
    elif tipo == 'nao_confirmados':
        title = 'Lista Não Presentes - {}'.format(atividade)
        presentes = atividade.participantes.values_list('id', flat=True)
        participantes = participantes.exclude(id__in=presentes)

    participantes = participantes.order_by('nome')
    return locals()


@rtr()
@permission_required('eventos.change_evento')
def enviar_mensagem(request, pk):
    obj = get_object_or_404(Evento, pk=pk)
    title = 'Enviar Mensagem'
    pode_gerenciar = request.user.is_superuser or obj.pode_gerenciar(request.user)
    if pode_gerenciar:
        form = EnviarMensagemForm(obj, data=request.POST or None)
        if form.is_valid():
            assunto = form.cleaned_data['assunto']
            mensagem = ''.join(['<p>{}</p>'.format(line) for line in form.cleaned_data['mensagem'].split('\n')])
            titulo = '[SUAP] Mensagem do Evento - {}'.format(assunto)
            html = '<h1>{}</h1>{}'.format(obj, mensagem)
            for participante in obj.participantes.all():
                send_mail(titulo, html, settings.DEFAULT_FROM_EMAIL, [participante.email], fail_silently=True)
            return httprr('..', 'Mensagem enviada com sucesso.')
    return locals()
