# -*- coding: utf-8 -*-
import xlwt
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from compras.forms import ProcessoCompraCampusMaterialFormFactory, ProcessoCompraFormFactory, CalendarioForm, FaseForm, \
    CalendarioCompraForm
from compras.models import ProcessoCompraCampus, ProcessoCompra, ProcessoCompraCampusMaterial, Evento, Calendario, \
    Processo, Fase, SolicitacaoParticipacao
from comum.models import Ano
from comum.utils import get_uo
from djtools import layout
from djtools.utils import rtr, httprr, XlsResponse
from materiais.models import Material, MaterialCotacao
from datetime import date, datetime
from djtools.html.calendarios import Calendario as Cal


@layout.info()
def index_infos(request):
    infos = list()

    if request.user.groups.filter(name='Gerenciador de Compras').exists():
        for processos in ProcessoCompra.get_no_periodo_para_mim():
            infos.append(dict(url='/compras/processo_compra/{}'.format(processos.pk), titulo='Processo de compra: {}.'.format(processos.descricao)))

    return infos


@layout.alerta()
def index_alertas(request):
    alertas = list()

    if request.user.has_perm('compras.view_processocompra'):
        if Fase.objects.filter(fase_inicial=True).exists():
            for fase in Fase.objects.filter(fase_inicial=True):
                if not SolicitacaoParticipacao.objects.filter(fase=fase, campus_solicitante=get_uo(request.user)).exists():
                    alertas.append(dict(url='/compras/solicitar_participacao/{}/'.format(fase.id), titulo='A fase <strong>{}</strong> do processo <strong>{}</strong> está aberta e você pode <strong>solicitar a participação do seu campus</strong>.'.format(fase.descricao, fase.processo.tipo_processo.descricao)))

    return alertas


@permission_required('compras.add_processocompracampusmaterial')
@rtr()
def processo_compra(request, pk):
    obj = ProcessoCompra.objects.get(pk=pk)
    materiais_ids = set(ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__processo_compra=pk).values_list('material', flat=True).order_by('material'))
    cotacoes_anexos = MaterialCotacao.objects.filter(material__in=materiais_ids, arquivo__isnull=False).exclude(arquivo='').exists()
    return locals()


@permission_required('compras.pode_gerenciar_processocompra')
def processo_compra_validar(request, pk):
    obj = ProcessoCompra.objects.get(pk=pk)
    if not obj.pode_validar(request.user):
        raise PermissionDenied()
    obj.validar(request.user)
    return httprr('/compras/processo_compra/{}/'.format(pk), 'Processo validado com sucesso.')


@permission_required('compras.pode_gerenciar_processocompra')
def processo_compra_relatorio_ug(request, pk):
    pcompra = ProcessoCompra.objects.get(pk=pk)
    consulta = (
        ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__in=pcompra.processocompracampus_set.all())
        .values(
            'processo_compra_campus__processo_compra__tags__descricao',
            'processo_compra_campus__campus__codigo_ug',
            'material__id',
            'material__codigo_catmat',
            'material__especificacao',
            'material__unidade_medida__descricao',
            'valor_unitario',
        )
        .annotate(soma_qtd=Sum('qtd'), soma_valor_total=Sum('valor_total'))
        .order_by('processo_compra_campus__processo_compra__tags__descricao', 'processo_compra_campus__campus__codigo_ug', 'material__id')
    )
    rows = [['Tag', 'UG', 'Material ID', 'CATMAT', 'Material Especificação', 'Unidade medida', 'Qtd.', 'Valor Unit.', 'Valor Total']]
    for row in consulta:
        rows.append(
            [
                row['processo_compra_campus__processo_compra__tags__descricao'],
                row['processo_compra_campus__campus__codigo_ug'],
                row['material__id'],
                row['material__codigo_catmat'],
                row['material__especificacao'],
                row['material__unidade_medida__descricao'],
                row['soma_qtd'],
                row['valor_unitario'],
                row['soma_valor_total'],
            ]
        )
    #
    return XlsResponse(rows=rows, convert_to_ascii=True)


@permission_required('compras.pode_gerenciar_processocompra')
def processo_compra_relatorio_campus(request, pk):
    pcompra = ProcessoCompra.objects.get(pk=pk)
    consulta = (
        ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__in=pcompra.processocompracampus_set.all())
        .values(
            'processo_compra_campus__processo_compra__tags__descricao',
            'processo_compra_campus__campus__setor__sigla',
            'material__id',
            'material__especificacao',
            'material__unidade_medida__descricao',
            'valor_unitario',
        )
        .annotate(soma_qtd=Sum('qtd'), soma_valor_total=Sum('valor_total'))
        .order_by('processo_compra_campus__processo_compra__tags__descricao', 'processo_compra_campus__campus__setor__sigla', 'material__id')
    )
    if consulta:
        relatorio = {}
        materiais = {}
        campus = []

        for r in consulta:
            if not r['material__id'] in materiais:
                materiais[r['material__id']] = r['material__especificacao']
        for registro in consulta:
            if not registro['material__id'] in relatorio:
                relatorio[registro['material__id']] = {}

            if registro['processo_compra_campus__campus__setor__sigla'] not in campus:
                campus.append(registro['processo_compra_campus__campus__setor__sigla'])

            if not registro['processo_compra_campus__campus__setor__sigla'] in relatorio[registro['material__id']]:
                relatorio[registro['material__id']][registro['processo_compra_campus__campus__setor__sigla']] = registro['soma_qtd']
            else:
                relatorio[registro['material__id']][registro['processo_compra_campus__campus__setor__sigla']] += registro['soma_qtd']
        #
        rows = []
        rows.append(['ID', 'Catmat', 'Material'] + campus)
        for material, mat_campus in list(relatorio.items()):
            row = []
            row.append(material)
            mat = Material.objects.get(id=material)
            row.append(mat.codigo_catmat)
            row.append(materiais[material])
            for c in campus:
                if c in mat_campus:
                    row.append(mat_campus[c])
                else:
                    row.append("0")
            rows.append(row)
    return XlsResponse(rows=rows, convert_to_ascii=True)


@permission_required('compras.pode_gerenciar_processocompra')
def processo_compra_relatorio_geral(request, pk):
    pcompra = ProcessoCompra.objects.get(pk=pk)
    consulta = (
        ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__in=pcompra.processocompracampus_set.all())
        .values('processo_compra_campus__processo_compra__tags__descricao', 'material__id', 'material__especificacao', 'material__unidade_medida__descricao', 'valor_unitario')
        .annotate(soma_qtd=Sum('qtd'), soma_valor_total=Sum('valor_total'))
        .order_by('processo_compra_campus__processo_compra__tags__descricao', 'material__id')
    )
    # verifica se existem dados retornados
    rows = [['Tag', 'Material ID', 'Material Especificação', 'Material Descrição', 'Unidade medida', 'Qtd.', 'Valor Unit.', 'Valor Total']]
    for row in consulta:
        rows.append(
            [
                row['processo_compra_campus__processo_compra__tags__descricao'],
                row['material__id'],
                row['material__especificacao'],
                Material.objects.get(id=row['material__id']).descricao,
                row['material__unidade_medida__descricao'],
                row['soma_qtd'],
                row['valor_unitario'],
                row['soma_valor_total'],
            ]
        )
    return XlsResponse(rows=rows, convert_to_ascii=True)


@rtr()
@permission_required('compras.add_processocompracampusmaterial')
def relatorio_processo_compra_campus(request, pk):
    pcompra = ProcessoCompraCampus.objects.get(pk=pk)
    consulta = (
        ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus=pcompra)
        .values('processo_compra_campus__processo_compra__tags__descricao', 'material__id', 'material__especificacao', 'material__unidade_medida__descricao', 'valor_unitario')
        .annotate(soma_qtd=Sum('qtd'), soma_valor_total=Sum('valor_total'))
        .order_by('processo_compra_campus__processo_compra__tags__descricao', 'material__id')
    )
    # verifica se existem dados retornados
    rows = [['Tag', 'Material ID', 'Material Especificação', 'Material Descrição', 'Unidade medida', 'Qtd.', 'Valor Unit.', 'Valor Total']]
    for row in consulta:
        rows.append(
            [
                row['processo_compra_campus__processo_compra__tags__descricao'],
                row['material__id'],
                row['material__especificacao'],
                Material.objects.get(id=row['material__id']).descricao,
                row['material__unidade_medida__descricao'],
                row['soma_qtd'],
                row['valor_unitario'],
                row['soma_valor_total'],
            ]
        )
    return XlsResponse(rows=rows, convert_to_ascii=True)


@permission_required('compras.pode_gerenciar_processocompra')
def processo_compra_relatorio_cotacao(request, pk):
    processo_compra = get_object_or_404(ProcessoCompra, pk=pk)

    wb = xlwt.Workbook(encoding='iso8859-1')

    sheet = wb.add_sheet('Cotacao')

    header = ['Tag', 'Material ID', 'Valor da Cotação', 'Data', 'Site', 'UASG', 'Número Pregão', 'Número Item', 'Data Validade']

    for idx, col in enumerate(header):
        sheet.write(0, idx, label=col)

    p_materiais = processo_compra.processocompramaterial_set.all().distinct()

    linha = 1

    for p_material in p_materiais:
        material = p_material.material
        cotacoes = processo_compra.processomaterialcotacao_set.filter(material=material).values_list('cotacao__id', flat=True).distinct()
        cotacoes = MaterialCotacao.objects.filter(pk__in=cotacoes)
        n_cotacoes = cotacoes.count()

        sheet.write_merge(linha, linha + n_cotacoes - 1, 0, 0, label=', '.join(processo_compra.tags.all().values_list('descricao', flat=True)))
        sheet.write_merge(linha, linha + n_cotacoes - 1, 1, 1, label=material.id)

        for cotacao in cotacoes:
            sheet.write(linha, 2, label='{}'.format(cotacao.valor))
            sheet.write(linha, 3, label=cotacao.data.strftime('%d/%m/%Y'))
            sheet.write(linha, 4, label='{}'.format(cotacao.site))
            sheet.write(linha, 5, label='{}'.format(cotacao.uasg))
            sheet.write(linha, 6, label='{}'.format(cotacao.numero_pregao))
            sheet.write(linha, 7, label='{}'.format(cotacao.numero_item))
            if cotacao.data_validade:
                sheet.write(linha, 8, label=cotacao.data_validade.strftime('%d/%m/%Y'))
            else:
                sheet.write(linha, 8, label='-')
            linha += 1

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=processo_compra.xls'
    wb.save(response)

    return response


@permission_required('compras.add_processocompracampusmaterial')
@rtr()
def processo_compra_campus(request, pk):
    obj = ProcessoCompraCampus.objects.get(pk=pk)

    itens = obj.get_itens()

    # tem filtro?
    if request.method == 'GET' and 'q' in request.GET and request.GET['q']:
        query = request.GET['q']

        # filtra campos não inteiros
        itens = obj.get_itens().filter(Q(material__descricao__unaccent__icontains=query) | Q(material__especificacao__icontains=query))

        # tem campo inteiro?
        if query.isdigit():
            # filtra o campo inteiro e concatena com o queryset anterior
            itens = itens | obj.get_itens().filter(Q(material__id=query) | Q(material__codigo_catmat=query))

            # remove duplicidades
        itens = itens.distinct()

    if obj.estah_no_periodo():
        FormClass = ProcessoCompraCampusMaterialFormFactory(obj)
        form = FormClass(request.POST or None, initial=dict(processo_compra_campus=pk))
        if form.is_valid():
            form.save()
            return httprr('.', 'Item adicionado com sucesso.')
    return locals()


@rtr()
def processo_compra_campus_validar(request, pk):
    obj = ProcessoCompraCampus.objects.get(pk=pk)
    if not obj.pode_validar(request.user):
        raise PermissionDenied()
    obj.validar(request.user)
    return httprr('/compras/processo_compra_campus/{}/'.format(pk), 'Processo validado com sucesso.')


@rtr()
@permission_required('compras.change_processocompra')
def processo_compra_editar(request, pk):
    title = 'Editar Processo de Compra'
    processo_compra = ProcessoCompra.objects.get(id=pk)
    FormClass = ProcessoCompraFormFactory(instance=processo_compra)
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            processo_compra.descricao = form.cleaned_data['descricao']
            processo_compra.observacao = form.cleaned_data['observacao']
            processo_compra.data_inicio = form.cleaned_data['data_inicio']
            processo_compra.data_fim = form.cleaned_data['data_fim']
            if form.cleaned_data['update_data'] is True:
                processo_compra.processocompracampus_set.update(data_inicio=processo_compra.data_inicio)
                processo_compra.processocompracampus_set.update(data_fim=processo_compra.data_fim)
            processo_compra.save()
            return httprr('.', 'Processo Compra editada com sucesso')
    else:
        form = FormClass()
    return locals()


@permission_required('compras.pode_gerenciar_processocompra')
def preencher_materiais_ausentes_campus(request, pk):
    processo_compra_campus = ProcessoCompraCampus.objects.get(id=pk)

    # "Processo Compra Campus" deve ter sido VALIDADO, ao contrário de "Processo Compra"
    if (processo_compra_campus.status == ProcessoCompraCampus.STATUS_VALIDADO) and (processo_compra_campus.processo_compra.status == ProcessoCompra.STATUS_AGUARDANDO_VALIDACAO):
        processo_compra_campus.preencher_materiais_ausentes(request.user)
        return httprr('/compras/processo_compra_campus/{}'.format(pk), 'Preenchimento de materiais ausentes efetuado com sucesso.')
    else:
        raise PermissionDenied("Operação não permitida.")


@rtr()
def detalhar_anexos(request, pk):
    title = 'Cotações com Anexos'
    materiais_ids = set(ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__processo_compra=pk).values_list('material', flat=True).order_by('material'))
    cotacao = MaterialCotacao.objects.filter(material__in=materiais_ids, arquivo__isnull=False).exclude(arquivo='')
    return locals()


@rtr()
@permission_required('compras.view_fase')
def calendarios_referencia(request):
    title = 'Calendários de Compras e Aquisições'
    ano = Ano.objects.filter(ano=date.today().year).first()
    eventos = Evento.objects.filter(ativo=True)
    calendarios = Calendario.objects.filter(ativo=True)
    form = CalendarioForm(request.POST or None)
    if form.is_valid():
        if form.cleaned_data.get('ano'):
            ano = form.cleaned_data['ano']
            data_ini = date(ano.ano, 1, 1)
            data_fim = date(ano.ano, 12, 31)
            eventos = eventos.filter(data_inicio__lte=data_fim, data_fim__gte=data_ini)
            calendarios = calendarios.filter(id__in=eventos.values_list('tipo_evento__calendario__id', flat=True))
        if form.cleaned_data.get('calendario'):
            calendario = form.cleaned_data['calendario']
            eventos = eventos.filter(tipo_evento__calendario=calendario)
            calendarios = calendarios.filter(id=calendario.id)

    lista_calendarios = list()
    for registro in calendarios:
        calendario = Cal()
        for evento in eventos.filter(tipo_evento__calendario=registro):
            calendario.adicionar_evento_calendario(evento.data_inicio, evento.data_fim, evento.tipo_evento.descricao,
                                                   evento.tipo_evento.cor, evento.tipo_evento.descricao)

        calendario_ano = calendario.formato_ano_calendario_compras(ano.ano)
        lista_calendarios.append([registro.descricao, calendario_ano])

    return locals()


@rtr()
@csrf_exempt
@permission_required('compras.view_fase')
def calendarios_compra(request):
    title = 'Calendários de Compras e Aquisições'
    ano = Ano.objects.filter(ano=date.today().year).first()
    fases = Fase.objects.filter(ativo=True)
    calendarios = Calendario.objects.filter(ativo=True)
    form = CalendarioCompraForm(request.POST or None)
    buscou_processo = False
    if form.is_valid():
        if form.cleaned_data.get('ano'):
            ano = form.cleaned_data['ano']
            data_ini = date(ano.ano, 1, 1)
            data_fim = date(ano.ano, 12, 31)
            fases = fases.filter(data_inicio__lte=data_fim, data_fim__gte=data_ini)
            calendarios = calendarios.filter(id__in=fases.values_list('processo__tipo_processo__tipo_calendario__id', flat=True))
        if form.cleaned_data.get('calendario'):
            calendario = form.cleaned_data['calendario']
            fases = fases.filter(processo__tipo_processo__tipo_calendario=calendario)
            calendarios = calendarios.filter(id=calendario.id)
        if form.cleaned_data.get('processo'):
            buscou_processo = True
            processo = form.cleaned_data['processo']
            fases = fases.filter(processo=processo)
            calendarios = calendarios.filter(id__in=fases.values_list('processo__tipo_processo__tipo_calendario__id', flat=True))

        if form.cleaned_data.get('fase'):
            fase = form.cleaned_data['fase']
            fases = fases.filter(id=fase.id)
            calendarios = calendarios.filter(id__in=fases.values_list('processo__tipo_processo__tipo_calendario__id', flat=True))

    lista_calendarios = list()
    for registro in calendarios:
        calendario = Cal()
        for evento in fases.filter(processo__tipo_processo__tipo_calendario=registro):
            calendario.adicionar_evento_calendario(evento.data_inicio, evento.data_fim, evento.descricao, evento.cor, evento.descricao)
        titulo = '{} - {}'.format(registro.descricao, ano)
        subtitulo = ''
        if buscou_processo and form.cleaned_data.get('processo').get_campi_solicitantes():
            subtitulo = 'Campi Participantes: {}'.format(form.cleaned_data.get('processo').get_campi_solicitantes())
        calendario_ano = calendario.formato_ano_calendario_compras(ano.ano)
        lista_calendarios.append([registro.descricao, calendario_ano, titulo, subtitulo])

    return locals()


@rtr()
@permission_required('compras.add_fase')
def adicionar_fase(request, pk):
    processo = get_object_or_404(Processo, pk=pk)
    if request.user.get_relacionamento() not in processo.tipo_processo.nucleo_responsavel.componentes.all() and not request.user.has_perm('compras.add_calendario'):
        raise PermissionDenied
    title = 'Adicionar Fase - {}'.format(processo)
    form = FaseForm(request.POST or None)
    if form.is_valid():
        o = form.save(False)
        o.processo = processo
        o.save()
        return httprr('/admin/compras/processo/', 'Fase cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('compras.view_processocompra')
def solicitar_participacao(request, pk):
    fase = get_object_or_404(Fase, pk=pk)
    if fase.fase_inicial:
        title = 'Solicitar Participação'
        if request.POST:
            o = SolicitacaoParticipacao()
            o.fase = fase
            o.solicitada_em = datetime.now()
            o.solicitada_por = request.user.get_relacionamento()
            o.campus_solicitante = get_uo(request.user)
            o.save()
            return httprr('/', 'Solicitação de participação cadastrada com sucesso.')

        return locals()
    else:
        raise PermissionDenied
