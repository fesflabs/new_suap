from collections import OrderedDict
from datetime import datetime, timedelta
from functools import reduce
from operator import or_
from decimal import Decimal

import xlwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.db.transaction import atomic
from django.forms.formsets import formset_factory
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.utils.text import get_valid_filename
from django_tables2 import DateColumn, LinkColumn
from django_tables2.utils import Accessor

from comum.models import Arquivo, Configuracao, Notificador
from comum.utils import get_table, get_uo, proximo_mes, somar_data, get_setor
from contratos.forms import (
    AnexoContratoForm,
    ApostilamentoForm,
    ContratoCancelarForm,
    CronogramaForm,
    DespachoFiscalForm,
    DespachoTermoAditivoForm,
    FiltroContratoEletricoForm,
    FiltroContratoForm,
    FiscalForm,
    GarantiaForm,
    MaoDeObraForm,
    MedicaoEletricaForm,
    MedicaoForm,
    OcorrenciaForm,
    ParcelaContratoFormSet,
    ParcelaForm,
    PenalidadeForm,
    PublicacaoAditivoForm,
    PublicacaoContratoForm,
    RelatorioPendenciasForm,
    SituacaoContratosForm,
    SolicitacaoPublicacaoPortariaFiscalForm,
    TermoAditivoForm,
    UploadArquivoForm,
    OcorrenciaMedicaoForm,
    ExportacaoForm,
    UploadArquivoContratoForm,
    AnexoMaoDeObraForm,
    ArrecadacaoReceitaForm,
    ContratoTiposDocumentosComprobatorioForm,
    MedicaoTipoDocumentoComprobatorioForm, EditarPublicacaoContratoForm)
from contratos.models import (
    Aditivo,
    AnexoContrato,
    Apostilamento,
    Contrato,
    Fiscal,
    Garantia,
    MaoDeObra,
    Medicao,
    MedicaoEletrica,
    Ocorrencia,
    Parcela,
    Penalidade,
    PublicacaoAditivo,
    PublicacaoContrato,
    AnexoMaoDeObra,
    DocumentoTextoContrato,
    ArrecadacaoReceita,
    ContratoTipoDocumentoComprobatorio,
    MedicaoTipoDocumentoComprobatorio,
    TipoDocumentoComprobatorio)
from djtools import layout
from djtools.html.graficos import LineChart
from djtools.templatetags.filters import in_group, format_money
from djtools.utils import XlsResponse, httprr, render, rtr, send_mail, \
    group_required
from documento_eletronico.forms import ListarDocumentosTextoForm
from documento_eletronico.models import ModeloDocumento, DocumentoTexto, Documento, TipoVinculoDocumento, \
    VinculoDocumentoTexto, HipoteseLegal
from documento_eletronico.status import DocumentoStatus
from documento_eletronico.utils import get_variaveis, EstagioProcessamentoVariavel, processar_template_ckeditor
from rh.models import UnidadeOrganizacional
from . import tasks
from .utils import por_extenso, Notificar, verificar_fiscal


@layout.servicos_anonimos()
def servicos_anonimos(request):

    servicos_anonimos = list()

    servicos_anonimos.append(dict(categoria='Consultas', titulo='Contratos', icone='file-contract', url='/contratos/listar_contratos/'))

    return servicos_anonimos


@layout.quadro('Contratos', icone='file-alt')
def index_quadros(quadro, request):
    relacionamento = request.user.get_relacionamento()
    if relacionamento.setor:
        uo_id = relacionamento.setor.uo_id
    dias_inicio_licitacao = Configuracao.get_valor_por_chave('contratos', 'dias_nova_licitacao') or 90
    if request.user.groups.filter(name='Gerente de Contrato').exists():
        proximos_a_vencer = Contrato.objects.proximos_a_vencer().filter(campi=uo_id).count()
        if proximos_a_vencer:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} no campus'.format(pluralize(proximos_a_vencer)),
                    subtitulo='Com vencimento nos próximos {} dias'.format(dias_inicio_licitacao),
                    qtd=proximos_a_vencer,
                    url='/admin/contratos/contrato/?campi__id__exact={}&tab=tab_proximos_a_vencer'.format(uo_id),
                )
            )

        proximos_a_vencer_com_garantias = Contrato.objects.proximos_a_vencer_com_garantias().filter(campi=uo_id).count()
        if proximos_a_vencer_com_garantias:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} no campus'.format(pluralize(proximos_a_vencer_com_garantias)),
                    subtitulo='Com garantia e vencimento nos próximos {} dias'.format(dias_inicio_licitacao),
                    qtd=proximos_a_vencer_com_garantias,
                    url='/admin/contratos/contrato/?campi__id__exact={}&tab=tab_proximos_a_vencer_com_garantias'.format(uo_id),
                )
            )

        com_vigencia_expirada = Contrato.objects.com_vigencia_expirada().filter(campi=uo_id).count()
        if com_vigencia_expirada:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} no campus'.format(pluralize(com_vigencia_expirada)),
                    subtitulo='Com vigência expirada',
                    qtd=com_vigencia_expirada,
                    url='/admin/contratos/contrato/?campi__id__exact={}&tab=tab_com_vigencia_expirada'.format(uo_id),
                )
            )

        com_ocorrencias_expiradas = Contrato.objects.com_ocorrencias_expiradas().filter(campi=uo_id).count()
        if com_ocorrencias_expiradas:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} no campus'.format(pluralize(com_ocorrencias_expiradas)),
                    subtitulo='Com ocorrências expiradas',
                    qtd=com_ocorrencias_expiradas,
                    url='/admin/contratos/contrato/?campi__id__exact={}&tab=tab_com_ocorrencias_expiradas'.format(uo_id),
                )
            )

    if request.user.groups.filter(name='Fiscal de Contrato').exists():
        ids_contrato_como_fiscal_ativo = Fiscal.objects.filter(servidor=relacionamento, inativo=False).only('contrato').values_list('contrato', flat=True)
        proximos_a_vencer = Contrato.objects.proximos_a_vencer().filter(id__in=ids_contrato_como_fiscal_ativo).count()
        if proximos_a_vencer:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} que fiscalizo'.format(pluralize(proximos_a_vencer)),
                    subtitulo='Com vencimento nos próximos {} dias'.format(dias_inicio_licitacao),
                    qtd=proximos_a_vencer,
                    url='/admin/contratos/contrato/?fiscal=somente_eu&tab=tab_proximos_a_vencer',
                )
            )

        proximos_a_vencer_com_garantias = Contrato.objects.proximos_a_vencer_com_garantias().filter(id__in=ids_contrato_como_fiscal_ativo).count()
        if proximos_a_vencer_com_garantias:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} que fiscalizo'.format(pluralize(proximos_a_vencer_com_garantias)),
                    subtitulo='Com garantia e vencimento nos próximos {} dias'.format(dias_inicio_licitacao),
                    qtd=proximos_a_vencer_com_garantias,
                    url='/admin/contratos/contrato/?fiscal=somente_eu&tab=tab_proximos_a_vencer_com_garantias',
                )
            )

        com_vigencia_expirada = Contrato.objects.com_vigencia_expirada().filter(id__in=ids_contrato_como_fiscal_ativo).count()
        if com_vigencia_expirada:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} que fiscalizo'.format(pluralize(com_vigencia_expirada)),
                    subtitulo='Com vigência expirada',
                    qtd=com_vigencia_expirada,
                    url='/admin/contratos/contrato/?fiscal=somente_eu&tab=tab_com_vigencia_expirada',
                )
            )

        com_ocorrencias_expiradas = Contrato.objects.com_ocorrencias_expiradas().filter(id__in=ids_contrato_como_fiscal_ativo).count()
        if com_ocorrencias_expiradas:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Contrato{} que fiscalizo'.format(pluralize(com_ocorrencias_expiradas)),
                    subtitulo='Com ocorrências expiradas',
                    qtd=com_ocorrencias_expiradas,
                    url='/admin/contratos/contrato/?fiscal=somente_eu&tab=tab_com_ocorrencias_expiradas',
                )
            )

    return quadro


@login_required
def redirect_contratos(request):
    uo = get_uo(request.user)
    url_base = '/admin/contratos/contrato/'
    return HttpResponseRedirect(url_base + '?campi__id__exact={}'.format(uo.id) if uo else url_base)


@rtr()
@permission_required('contratos.pode_visualizar_contrato')
def aditivo(request, aditivo_id):
    aditivo = get_object_or_404(Aditivo, pk=aditivo_id)
    title = 'Termo Aditivo {}'.format(aditivo.numero)
    pode_atualizar_contrato = request.user.has_perm('contratos.change_contrato')
    pode_submeter_arquivo = request.user.has_perm('contratos.pode_submeter_arquivo')
    pode_visualizar_arquivo = request.user.has_perm('contratos.pode_visualizar_arquivo')
    pode_adicionar_publicacao = request.user.has_perm('contratos.pode_adicionar_publicacao')
    pode_excluir_publicacao = request.user.has_perm('contratos.pode_excluir_publicacao')
    pode_submeter_publicacao = request.user.has_perm('contratos.pode_submeter_publicacao')
    pode_visualizar_publicacao = request.user.has_perm('contratos.pode_visualizar_publicacao')
    pode_adicionar_fiscal = request.user.has_perm('contratos.pode_adicionar_fiscal')
    pode_excluir_fiscal = request.user.has_perm('contratos.pode_excluir_fiscal')

    return locals()


@rtr()
@login_required()
def contrato(request, contrato_id):
    pode_atualizar_contrato = request.user.has_perm('contratos.change_contrato')
    pode_submeter_arquivo = request.user.has_perm('contratos.pode_submeter_arquivo')
    pode_visualizar_arquivo = request.user.has_perm('contratos.pode_visualizar_arquivo')
    pode_efetuar_medicao = request.user.has_perm('contratos.pode_efetuar_medicao')
    pode_gerar_cronograma = request.user.has_perm('contratos.pode_gerar_cronograma')
    pode_visualizar_cronograma = request.user.has_perm('contratos.pode_visualizar_cronograma')
    pode_adicionar_publicacao = request.user.has_perm('contratos.pode_adicionar_publicacao')
    pode_excluir_publicacao = request.user.has_perm('contratos.pode_excluir_publicacao')
    pode_submeter_publicacao = request.user.has_perm('contratos.pode_submeter_publicacao')
    pode_visualizar_publicacao = request.user.has_perm('contratos.pode_visualizar_publicacao')
    pode_adicionar_anexo = request.user.has_perm('contratos.pode_adicionar_anexo')
    pode_visualizar_anexo = request.user.has_perm('contratos.pode_visualizar_anexo')
    pode_adicionar_fiscal = request.user.has_perm('contratos.pode_adicionar_fiscal')
    pode_excluir_fiscal = request.user.has_perm('contratos.pode_excluir_fiscal')
    pode_aditivar_contrato = request.user.has_perm('contratos.pode_aditivar_contrato')
    pode_cancelar_contrato = request.user.has_perm('contratos.pode_cancelar_contrato')
    is_operador = request.user.groups.filter(name__in=['Operador de Contrato', 'Gerente de Contrato']).exists()

    contrato = get_object_or_404(Contrato, pk=contrato_id)
    title = str(contrato.numero)
    data_vencimento = contrato.data_vencimento
    vence_nos_proximos_90_dias = False
    hoje = datetime.now().date()
    if data_vencimento and data_vencimento > hoje and (data_vencimento < (hoje + timedelta(days=90))):
        vence_nos_proximos_90_dias = True
    campus_filtro = None
    aditivos = contrato.get_aditivos()
    apostilamentos = contrato.apostilamentos_set.all()
    garantias = contrato.garantias_set.all()
    penalidades = contrato.penalidades_set.all()
    maosdeobra = contrato.maodeobra_set.all()
    ocorrencias = contrato.ocorrencia_set.all().order_by('data')
    arrecadacaoreceita = contrato.arrecadacaoreceita_set.all()
    anexos = contrato.anexos_set.all()
    pks_uos_contrato = Contrato.objects.filter(pk=contrato.id).values_list('campi', flat=True)
    uos = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)
    uo_selecionada = int(request.GET.get('uo_selecionada') or 0)
    documentostexto_do_contrato = contrato.documentotexto_contrato_set.exclude(documento__status__in=[DocumentoStatus.STATUS_CANCELADO])

    # evita exceção quando usuário logado não é um servidor
    fiscal = None
    eh_gestor_contrato = None
    medicao = None
    if request.user.eh_servidor:
        fiscal = contrato.get_fiscal(request.user.get_relacionamento())
        eh_gestor_contrato = contrato.eh_gestor_contrato(request.user.get_relacionamento())

    pode_efetuar_medicao = pode_efetuar_medicao and fiscal
    pode_gerenciar_todas_medicoes = pode_efetuar_medicao and fiscal.tipo.pode_gerenciar_todas_medicoes_contrato

    if pode_excluir_fiscal and 'excluir_fiscal' in request.GET:
        fiscal = Fiscal.objects.get(pk=request.GET['excluir_fiscal'])
        fiscal.inativo = True
        fiscal.data_exclusao = datetime.today()
        fiscal.save()
        return httprr("/contratos/contrato/{}/".format(contrato.id), 'Fiscal removido com sucesso.')

    if pode_excluir_publicacao and 'excluir_publicacao' in request.GET:
        publicacao = PublicacaoContrato.objects.get(pk=request.GET['excluir_publicacao'])
        publicacao.delete()
        return httprr("/contratos/contrato/{}/".format(contrato.id), 'Publicação removida com sucesso.')

    if 'excluir_ocorrencia' in request.GET:
        if not fiscal:
            return httprr('..', 'Você não cadastrou essa ocorrência. Portanto, não pode excluí-la.')

        ocorrencia = Ocorrencia.objects.get(pk=request.GET['excluir_ocorrencia'])
        ocorrencia.delete()
        return httprr("/contratos/contrato/{}/".format(contrato.id), 'Ocorrência removida com sucesso.')

    if fiscal:
        if 'excluir_anexo' in request.GET:
            anexo = AnexoContrato.objects.get(pk=request.GET['excluir_anexo'])
            anexo.delete()
            return httprr("/contratos/contrato/{}/".format(contrato.id), 'Anexo removido com sucesso.')

    # Todo: verificar se será utilizada apenas remoção lógica e caso seja delete() adicionar a checagem de permission requerid ou grupo Gerente de Contrato
    if 'remover_vinculo_documento' in request.GET:
        if in_group(request.user, 'Gerente de Contrato'):
            documento_contrato = DocumentoTextoContrato.objects.get(pk=request.GET['remover_vinculo_documento'])
            documento_contrato.delete()
            return httprr("/contratos/contrato/{}/".format(contrato.id), 'Vínculo com documento {} removido com sucesso.'.format(documento_contrato.documento.identificador))
        else:
            raise PermissionDenied

    fiscais = Fiscal.objects.filter(contrato=contrato)

    cronograma = contrato.get_cronograma()
    if cronograma:
        if cronograma.parcelas_set.exists():
            parcelas = contrato.get_cronograma().parcelas_set.all().order_by('data_prevista_inicio')
    if uo_selecionada:
        fiscais = fiscais.filter(campus=uo_selecionada)
        ocorrencias = ocorrencias.filter(campus=uo_selecionada)
        maosdeobra = maosdeobra.filter(campus=uo_selecionada)
        anexos = anexos.filter(campus=uo_selecionada)
        if medicao:
            parcelas = parcelas.filter(campus=uo_selecionada)
        campus_filtro = uo_selecionada

    documentos_relacionados = anexos.count() + documentostexto_do_contrato.count()
    termo = Aditivo()
    termo.valor = contrato.valor
    termo.qtd_parcelas = contrato.qtd_parcelas
    termo.data_inicio = contrato.data_inicio
    termo.data_fim = contrato.data_fim

    aditivo_form = TermoAditivoForm(instance=termo, data_inicio_contrato=contrato.data_inicio)
    tipo_contrato_eletrico = contrato.subtipo and contrato.subtipo_id == int(Configuracao.get_valor_por_chave('contratos', 'tipo_contrato_energia_eletrica') or 0)
    if tipo_contrato_eletrico:
        form_contrato_eletrico = FiltroContratoEletricoForm(request.POST or None, contrato=contrato)
        if form_contrato_eletrico.is_valid():
            medicoes_eletricas = MedicaoEletrica.objects.filter(medicao__parcela__cronograma__contrato=contrato)
            ano = form_contrato_eletrico.cleaned_data.get('ano')
            mes = form_contrato_eletrico.cleaned_data.get('mes')
            if ano != 'todos':
                medicoes_eletricas = medicoes_eletricas.filter(ano_referencia=int(ano))
            if mes:
                medicoes_eletricas = medicoes_eletricas.filter(mes_referencia=mes)

            medicoes_ = OrderedDict()
            for medicao in medicoes_eletricas.order_by('ano_referencia', 'mes_referencia'):
                mes_ano = '{}/{}'.format(medicao.mes_referencia, medicao.ano_referencia)
                consumo_ponta = consumo_fora_ponta = 0
                if medicoes_.get(mes_ano):
                    if medicao.consumo_ponta:
                        consumo_ponta = float(medicao.consumo_ponta)
                    medicoes_[mes_ano]['consumo_ponta'] += consumo_ponta
                    if medicao.consumo_fora_ponta:
                        consumo_fora_ponta = float(medicao.consumo_fora_ponta)
                    medicoes_[mes_ano]['consumo_fora_ponta'] += consumo_fora_ponta
                    medicoes_[mes_ano]['total'] += consumo_ponta + consumo_fora_ponta
                else:
                    medicoes_[mes_ano] = dict()
                    if medicao.consumo_ponta:
                        consumo_ponta = float(medicao.consumo_ponta)
                    medicoes_[mes_ano]['consumo_ponta'] = consumo_ponta
                    if medicao.consumo_fora_ponta:
                        consumo_fora_ponta = float(medicao.consumo_fora_ponta)
                    medicoes_[mes_ano]['consumo_fora_ponta'] = consumo_fora_ponta
                    medicoes_[mes_ano]['total'] = consumo_ponta + consumo_fora_ponta

            series = [[key, float(dicionario['consumo_ponta']), float(dicionario['consumo_fora_ponta']), float(dicionario['total'])] for key, dicionario in list(medicoes_.items())]
            grafico = LineChart(
                'grafico',
                title='Gastos Elétricos',
                data=series,
                groups=['Consumo de Ponta', 'Consumo Fora Ponta', 'Consumo Total'],
                yAxis_title_text='kWh',
                plotOptions_line_dataLabels_enable=True,
                plotOptions_line_enableMouseTracking=True,
            )
    return locals()


@rtr()
@permission_required('contratos.pode_cancelar_contrato')
def cancelar_contrato(request, contrato_id):
    title = "Cancelar contrato"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    form = ContratoCancelarForm(request.POST or None)
    if form.is_valid():
        motivo_cancelamento = form.cleaned_data['motivo_cancelamento']
        contrato.motivo_cancelamento = motivo_cancelamento
        contrato.cancelado = True
        contrato.dh_cancelamento = datetime.now()
        contrato.usuario_cancelamento = request.user
        contrato.save()
        return httprr("..", 'Contrato cancelado.')

    return locals()


@rtr()
@permission_required('contratos.can_delete')
@atomic
def excluir(request, contrato_id):
    pass


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def exportar_maodeobra(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    rows = [['Prestador de Serviço', 'Data de Nascimento', 'Categoria', 'Função', 'Escolaridade', 'Jornada de Trabalho', 'Salário Bruto', 'Custo Mensal', 'Data de Desligamento']]
    for maodeobra in contrato.maodeobra_set.all():
        row = [
            maodeobra.prestador_servico,
            maodeobra.data_nascimento,
            maodeobra.categoria,
            maodeobra.funcao,
            maodeobra.escolaridade,
            maodeobra.jornada_trabalho,
            maodeobra.salario_bruto,
            maodeobra.custo_mensal,
            maodeobra.desligamento,
        ]
        rows.append(row)
    return XlsResponse(rows)


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def excluir_maodeobra(request, maodeobra_id):
    maodeobra = get_object_or_404(MaoDeObra, pk=maodeobra_id)
    contrato_id = maodeobra.contrato.id
    maodeobra.delete()
    return httprr("/contratos/contrato/{}/".format(contrato_id), 'Mão de obra excluída com sucesso.')


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def editar_maodeobra(request, maodeobra_id):
    title = "Editar Mão de obra"
    maodeobra = get_object_or_404(MaoDeObra, pk=maodeobra_id)
    if request.method == 'POST':
        form = MaoDeObraForm(request.POST, instance=maodeobra)
        if form.is_valid():
            form.save()
            return httprr('..', 'Mão de obra editada com sucesso.')
    else:
        form = MaoDeObraForm(instance=maodeobra)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def adicionar_maodeobra(request, contrato_id):
    title = "Adicionar Mão de obra"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    maodeobra = MaoDeObra()
    maodeobra.contrato = contrato
    if request.method == 'POST':
        form = MaoDeObraForm(request.POST, instance=maodeobra, contrato=contrato)
        if form.is_valid():
            form.instance.contrato = contrato
            form.save()
            return httprr('..', 'Mão de obra adicionada com sucesso.')
    else:
        form = MaoDeObraForm(instance=maodeobra, contrato=contrato)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def adicionar_anexomaodeobra(request, maodeobra_id):
    title = 'Adicionar Anexo à Mão de Obra'
    maodeobra = get_object_or_404(MaoDeObra, pk=maodeobra_id)
    form = AnexoMaoDeObraForm(request.POST or None, request.FILES or None, maodeobra=maodeobra)
    if form.is_valid():
        form.save()
        return httprr('..', 'Anexo adicionado com sucesso à mão de obra.')

    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def remover_anexomaodeobra(request, anexomaodeobra_id):
    anexo = get_object_or_404(AnexoMaoDeObra, pk=anexomaodeobra_id)
    anexo.delete()
    return httprr('..', 'Anexo removido com sucesso.')


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def excluir_apostilamento(request, apostilamento_id):
    apostilamento = get_object_or_404(Apostilamento, pk=apostilamento_id)
    contrato_id = apostilamento.contrato.id
    apostilamento.delete()
    return httprr("/contratos/contrato/{}/".format(contrato_id), 'Apostilamento excluído com sucesso.')


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def editar_apostilamento(request, apostilamento_id):
    title = "Editar Apostilamento"
    apostilamento = get_object_or_404(Apostilamento, pk=apostilamento_id)
    if request.method == 'POST':
        form = ApostilamentoForm(request.POST, request.FILES, instance=apostilamento, data_inicio_contrato=apostilamento.contrato.data_inicio)
        if form.is_valid():
            form.save()
            return httprr("/contratos/contrato/{}/".format(apostilamento.contrato.id), 'Apostilamento editado com sucesso.')
    else:
        form = ApostilamentoForm(instance=apostilamento, data_inicio_contrato=apostilamento.contrato.data_inicio)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def adicionar_apostilamento(request, contrato_id):
    title = "Adicionar Apostilamento"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'POST':
        form = ApostilamentoForm(request.POST, request.FILES, data_inicio_contrato=contrato.data_inicio)
        if form.is_valid():
            form.instance.contrato = contrato
            form.save()
            return httprr("/contratos/contrato/{}/".format(contrato_id), 'Apostilamento adicionado com sucesso.')
    else:
        apostilamento = Apostilamento()
        apostilamento.valor = contrato.valor
        apostilamento.data_inicio = contrato.data_inicio
        apostilamento.data_fim = contrato.data_fim
        form = ApostilamentoForm(instance=apostilamento, data_inicio_contrato=contrato.data_inicio)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def excluir_garantia(request, garantia_id):
    garantia = get_object_or_404(Garantia, pk=garantia_id)
    contrato_id = garantia.contrato.id
    garantia.delete()
    return httprr("/contratos/contrato/{}/".format(contrato_id), 'Garantia excluída com sucesso.')


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def editar_garantia(request, garantia_id):
    title = "Editar Garantia"
    garantia = get_object_or_404(Garantia, pk=garantia_id)
    if request.method == 'POST':
        form = GarantiaForm(request.POST, request.FILES, instance=garantia)
        if form.is_valid():
            form.save()
            return httprr("/contratos/contrato/{}/".format(garantia.contrato.id), 'Garantia editada com sucesso.')
    else:
        form = GarantiaForm(instance=garantia)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def adicionar_garantia(request, contrato_id):
    title = "Adicionar Garantia"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    garantia = Garantia()
    garantia.contrato = contrato
    if request.method == 'POST':
        form = GarantiaForm(request.POST, request.FILES, instance=garantia)
        if form.is_valid():
            form.instance.contrato = contrato
            form.save()
            return httprr('..', 'Garantia adicionada com sucesso.')
    else:
        form = GarantiaForm(instance=garantia)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def adicionar_penalidade(request, contrato_id):
    title = "Adicionar Penalidade"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    penalidade = Penalidade()
    penalidade.contrato = contrato
    if request.method == 'POST':
        form = PenalidadeForm(request.POST, request.FILES, instance=penalidade)
        if form.is_valid():
            form.instance.contrato = contrato
            form.instance.atualizado_por = request.user.get_vinculo()
            form.save()
            return httprr('..', 'Penalidade adicionada com sucesso.')
    else:
        form = PenalidadeForm(instance=penalidade)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def editar_penalidade(request, penalidade_id):
    title = "Editar Penalidade"
    penalidade = get_object_or_404(Penalidade, pk=penalidade_id)
    if request.method == 'POST':
        form = PenalidadeForm(request.POST, request.FILES, instance=penalidade)
        if form.is_valid():
            form.instance.atualizado_por = request.user.get_vinculo()
            form.save()
            return httprr("/contratos/contrato/{}/?tab=penalidades".format(penalidade.contrato.id), 'Penalidade editada com sucesso.')
    else:
        form = PenalidadeForm(instance=penalidade)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def excluir_penalidade(request, penalidade_id):
    penalidade = get_object_or_404(Penalidade, pk=penalidade_id)
    contrato_id = penalidade.contrato.id
    penalidade.delete()
    return httprr("/contratos/contrato/{}/?tab=penalidades".format(contrato_id), 'Penalidade removida com sucesso.')


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def adicionar_aditivo(request, contrato_id):
    title = "Adicionar Aditivo"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'POST':
        form = TermoAditivoForm(request.POST, request.FILES, data_inicio_contrato=contrato.data_inicio)
        if form.is_valid():
            termo = form.save(commit=False)
            contrato.adicionar_termo_aditivo(termo)
            arquivo_up = request.FILES['arquivo_aditivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if termo.arquivo:
                termo.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            termo.arquivo = arquivo
            termo.save()
            arquivo.store(request.user, content)
            return httprr("..", 'Termo aditivo adicionado com sucesso.')
    else:
        termo = Aditivo()
        termo.valor = contrato.valor
        termo.qtd_parcelas = contrato.qtd_parcelas
        termo.data_inicio = contrato.data_inicio
        termo.data_fim = contrato.data_fim
        form = TermoAditivoForm(instance=termo, data_inicio_contrato=contrato.data_inicio)
    return locals()


@rtr()
@permission_required('contratos.pode_aditivar_contrato')
def excluir_aditivo(request, aditivo_id):
    aditivo = get_object_or_404(Aditivo, pk=aditivo_id)
    contrato_id = aditivo.contrato.id
    aditivo.delete()
    return httprr("/contratos/contrato/{}/".format(contrato_id), 'Termo aditivo excluído com sucesso.')


@rtr()
@permission_required('contratos.pode_adicionar_fiscal')
def adicionar_fiscal(request, contrato_id):
    title = 'Adicionar Fiscal'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'POST':
        form = FiscalForm(data=request.POST, instance=None, contrato=contrato)
        if form.is_valid():
            fiscal = form.save(commit=False)
            contrato.adicionar_fiscal(fiscal)
            return httprr('..', 'Fiscal adicionado com sucesso.')
    else:
        form = FiscalForm(contrato=contrato)
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_fiscal')
def editar_fiscal(request, fiscal_id):
    title = 'Editar Fiscal'
    instance = get_object_or_404(Fiscal, pk=fiscal_id)
    if request.method == 'POST':
        form = FiscalForm(data=request.POST, instance=instance)
        if form.is_valid():
            fiscal = form.save()
            return httprr("/contratos/contrato/{}/".format(fiscal.contrato.id), 'Fiscal editado com sucesso.')
    else:
        form = FiscalForm(instance=instance)
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_fiscal')
def adicionar_fiscal_aditivo(request, aditivo_id):
    title = 'Adicionar Fiscal'
    aditivo = get_object_or_404(Aditivo, pk=aditivo_id)
    if request.method == 'POST':
        form = FiscalForm(data=request.POST)
        if form.is_valid():
            fiscal = form.save(commit=False)
            fiscal.termo_aditivo = aditivo
            aditivo.contrato.adicionar_fiscal(fiscal)
            return httprr('..', 'Fiscal adicionado com sucesso.')
    else:
        form = FiscalForm()
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_publicacao')
def adicionar_publicacao(request, contrato_id):
    title = 'Adicionar Publicação'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'POST':
        form = PublicacaoContratoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            publicacao = PublicacaoContrato()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            publicacao.contrato = contrato
            publicacao.data = form.cleaned_data['data']
            publicacao.numero = form.cleaned_data['numero']
            publicacao.descricao = form.cleaned_data['descricao']
            publicacao.tipo = form.cleaned_data['tipo']
            publicacao.arquivo = arquivo
            publicacao.save()
            arquivo.store(request.user, content)
            contrato.adicionar_publicacao(publicacao)
            return httprr("..", 'Publicação adicionada com sucesso.')
    else:
        form = PublicacaoContratoForm()
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_publicacao')
def editar_publicacao(request, publicacao_id):
    title = 'Editar Publicação'
    instance = PublicacaoContrato.objects.get(pk=publicacao_id)
    initial = {
        'contrato': instance.contrato,
        'data': instance.data,
        'numero': instance.numero,
        'descricao': instance.descricao,
        'tipo': instance.tipo.id,
    }
    if request.method == 'POST':
        form = EditarPublicacaoContratoForm(request.POST, request.FILES, initial=initial)
        if form.is_valid():
            publicacao = instance
            pessoa = request.user.get_profile()
            publicacao.data = form.cleaned_data['data']
            instance.numero = form.cleaned_data['numero']
            instance.descricao = form.cleaned_data['descricao']
            instance.tipo = form.cleaned_data['tipo']
            publicacao.save()
            return httprr("/contratos/contrato/{}/".format(publicacao.contrato.id), 'Publicação editada com sucesso.')
    else:
        form = EditarPublicacaoContratoForm(initial=initial)
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_publicacao')
def adicionar_publicacao_aditivo(request, aditivo_id):
    title = 'Adicionar Publicação'
    aditivo = get_object_or_404(Aditivo, pk=aditivo_id)
    if request.method == 'POST':
        form = PublicacaoAditivoForm(data=request.POST)
        if form.is_valid():
            publicacao = form.save(commit=False)
            aditivo.adicionar_publicacao(publicacao)
            return httprr("/contratos/aditivo/{}/".format(aditivo.id), 'Publicação adicionada com sucesso.')
    else:
        form = PublicacaoAditivoForm()
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_publicacao')
def editar_publicacao_aditivo(request, publicacao_id):
    title = 'Editar Publicação de Aditivo'
    instance = get_object_or_404(PublicacaoAditivo, pk=publicacao_id)
    if request.method == 'POST':
        form = PublicacaoAditivoForm(data=request.POST, instance=instance)
        if form.is_valid():
            publicacao = form.save()
            return httprr("/contratos/aditivo/{}/".format(instance.aditivo.id), 'Publicação editada com sucesso.')
    else:
        form = PublicacaoAditivoForm(instance=instance)
    return locals()


@rtr()
@permission_required('contratos.pode_excluir_publicacao')
def excluir_publicacao_aditivo(request, publicacao_id):
    instance = get_object_or_404(PublicacaoAditivo, pk=publicacao_id)
    contrato_id = instance.aditivo.contrato.id
    instance.delete()
    return httprr("/contratos/contrato/{}/".format(contrato_id), 'Publicação excluída com sucesso.')


@rtr()
@permission_required('contratos.pode_adicionar_anexo')
def adicionar_anexo(request, contrato_id):
    title = 'Adicionar Anexo'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    anexo = AnexoContrato()
    anexo.contrato = contrato
    form = AnexoContratoForm(request.POST or None, request.FILES or None, instance=anexo, contrato=contrato)
    if form.is_valid():
        arquivo_up = request.FILES['anexo']
        arquivo_up.seek(0)
        content = arquivo_up.read()
        nome = arquivo_up.name
        vinculo = request.user.get_vinculo()
        arquivo = Arquivo()
        arquivo.save(nome, vinculo)
        anexo.arquivo = arquivo
        anexo.save()
        arquivo.store(request.user, content)
        contrato.adicionar_anexo(anexo)
        return httprr('..', 'Anexo adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('contratos.pode_adicionar_anexo')
def editar_anexo(request, anexo_id):
    title = 'Editar Anexo'
    anexo = get_object_or_404(AnexoContrato, pk=anexo_id)
    form = AnexoContratoForm(request.POST or None, request.FILES or None, instance=anexo, user=request.user)
    if form.is_valid():
        anexo = form.save(commit=False)
        arquivo_up = request.FILES.get('anexo')
        if arquivo_up:
            nome = arquivo_up.name
            pessoa = request.user.get_vinculo()
            if anexo.arquivo:
                anexo.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, pessoa)
            anexo.arquivo = arquivo
        anexo.save()
        if arquivo_up:
            arquivo_up.seek(0)
            content = arquivo_up.read()
            arquivo.store(request.user, content)
        return httprr("/contratos/contrato/{}/?tab=5".format(anexo.contrato.id), 'Anexo atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('contratos.pode_gerar_cronograma')
def definir_cronograma(request, contrato_id):
    title = 'Cronograma'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'POST':
        form = CronogramaForm(data=request.POST)
        if form.is_valid():
            cronograma = form.save(commit=False)
            contrato.set_cronograma(cronograma)
            return httprr("..", 'Número de cronograma definido com sucesso. As parcelas necessitam ser geradas.')
    else:
        form = CronogramaForm()
    return locals()


@rtr()
@permission_required('contratos.pode_gerar_cronograma')
def atualizar_parcela(request, parcela_id, contrato_id):
    title = 'Atualizar Parcela'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    parcela = get_object_or_404(Parcela, pk=parcela_id)
    if request.method == 'POST':
        form = ParcelaForm(data=request.POST, instance=parcela)
        form.set_contrato(contrato)
        if form.is_valid():
            temp = form.save(commit=False)
            parcela.data_prevista_inicio = temp.data_prevista_inicio
            parcela.data_prevista_fim = temp.data_prevista_fim
            if form.cleaned_data.get('valor_previsto'):
                parcela.valor_previsto = temp.valor_previsto
            parcela.save()
            return httprr("..", 'Parcela atualizada com sucesso.')
    else:
        form = ParcelaForm(instance=parcela)
    return locals()


@rtr()
@permission_required('contratos.pode_gerar_cronograma')
def adicionar_parcela(request, contrato_id):
    title = "Adicionar Parcela"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if contrato.get_cronograma() is None:
        return httprr("..", 'Contrato não possui número de cronograma definido.')
    if request.method == 'POST':
        form = ParcelaForm(data=request.POST, contrato=contrato)
        form.set_contrato(contrato)
        if form.is_valid():
            parcela = form.save(commit=False)
            contrato.get_cronograma().adicionar_parcela(parcela)
            return httprr("..", 'Parcela adicionada com sucesso.')
    else:
        parcela = Parcela()
        parcela.data_prevista_inicio = contrato.data_inicio
        parcela.data_prevista_fim = somar_data(contrato.data_inicio, 30)
        parcela.valor_previsto = contrato.get_saldo_contrato()
        form = ParcelaForm(instance=parcela, contrato=contrato)
        form.set_contrato(contrato)
    return locals()


@rtr()
@permission_required('contratos.pode_gerar_cronograma')
def gerar_parcelas(request, contrato_id):
    title = "Gerenciar Parcelas"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if contrato.get_cronograma() is None:
        return httprr("/contratos/contrato/{}/".format(contrato.id), 'Contrato não possui número de cronograma definido.')
    if request.method == 'POST':
        formset = ParcelaContratoFormSet(data=request.POST)
        for form in formset.forms:
            form.set_contrato(contrato)
        if formset.is_valid():
            for form in formset.forms:
                parcela = form.save(commit=False)
                contrato.get_cronograma().adicionar_parcela(parcela)
            return httprr("/contratos/contrato/{}/".format(contrato.id), 'Parcelas geradas com sucesso.')
    else:
        initial = []
        data = contrato.data_inicio
        data_inicial = data
        qtd_parcelas = request.GET.get('parcelas', contrato.qtd_parcelas) or 0

        if 'data' in request.GET:
            try:
                data = datetime.strptime(request.GET['data'], "%d/%m/%Y")
            except Exception:
                data = contrato.data_inicio
        for i in range(1, int(qtd_parcelas) + 1):
            vencimento = proximo_mes(data)

            initial.append({'data_prevista_inicio': data, 'data_prevista_fim': somar_data(vencimento, -1), 'valor_previsto': contrato.get_saldo_contrato() / int(qtd_parcelas)})
            data = vencimento
        formset = ParcelaContratoFormSet(initial=initial)
        for form in formset.forms:
            form.set_contrato(contrato)
    return locals()


@rtr()
@group_required("Gerente de Contrato")
def configurar_medicao(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    title = "Configurar Medição - {}".format(contrato.numero)
    tipos_documentos_do_contrato = ContratoTipoDocumentoComprobatorio.objects.filter(contrato__id=contrato.pk).order_by('id')
    form = ContratoTiposDocumentosComprobatorioForm(request.POST or None, contrato=contrato)
    if form.is_valid():
        form.save()
        return httprr("/contratos/configurar_medicao/{}/".format(contrato.id), 'Tipo de documento comprobatório adicionado ao contrato.')

    return locals()


@group_required("Gerente de Contrato")
def excluir_tipo_documento_contrato(request, contrato_id, tipo_documento_contrato_id):
    tipo_documento_contrato = get_object_or_404(ContratoTipoDocumentoComprobatorio, pk=tipo_documento_contrato_id)
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if MedicaoTipoDocumentoComprobatorio.objects.filter(medicao__parcela__cronograma__contrato=contrato, tipo_documento_comprobatorio=tipo_documento_contrato.tipo_documento_comprobatorio).exists():
        return httprr("/contratos/configurar_medicao/{}/".format(contrato.id), 'Você não pode excluir este tipo de documento pois já está vinculado a uma medição.', tag="warning")
    tipo_documento_contrato.delete()
    return httprr("/contratos/configurar_medicao/{}/".format(contrato.id), 'Tipo de documento comprobatório excluído para este contrato.')


@permission_required('contratos.pode_gerar_cronograma')
def excluir_parcela(request, parcela_id, contrato_id):
    parcela = get_object_or_404(Parcela, pk=parcela_id)
    if parcela.medicoes_set.all().exists():
        return httprr('/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato_id, parcela_id), 'Você não pode excluir uma parcela com medição.')
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    parcela.delete()
    return httprr("/contratos/contrato/{}/".format(contrato.id), 'Parcela excluída com sucesso.')


@rtr()
@permission_required('contratos.pode_efetuar_medicao')
def sem_medicao(request, parcela_id, contrato_id):
    parcela = get_object_or_404(Parcela, pk=parcela_id)
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if not (contrato.eh_fiscal(request.user.get_relacionamento()) or parcela.cronograma.contrato == contrato):
        raise ValidationError('Você não é fiscal desse contrato.')
    if parcela.sem_medicao:
        parcela.sem_medicao = False
    else:
        parcela.sem_medicao = True
    parcela.save()
    return httprr("/contratos/contrato/{}/?tab=cronograma#parcela_{}".format(contrato.id, parcela_id), 'Parcela sem medição informada com sucesso.')


@rtr()
@permission_required('contratos.pode_efetuar_medicao')
@verificar_fiscal()
def efetuar_medicao(request, parcela_id, contrato_id):
    title = 'Efetuar Medição'
    parcela = get_object_or_404(Parcela, pk=parcela_id)
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    fiscal = contrato.get_fiscal(servidor=request.user.get_relacionamento())
    tipo_contrato = ''
    tipo_contrato_eletrico = Configuracao.get_valor_por_chave('contratos', 'tipo_contrato_energia_eletrica')
    if tipo_contrato_eletrico and contrato.subtipo and contrato.subtipo_id == int(tipo_contrato_eletrico):
        FormClass = MedicaoEletricaForm
        tipo_contrato = 'eletrico'
    else:
        FormClass = MedicaoForm

    form = FormClass(request.POST or None, request.FILES or None, parcela=parcela)
    if form.is_valid():
        medicao = form.save(commit=False)
        medicao.fiscal = fiscal
        parcela.registrar_medicao(medicao)
        arquivo_up = request.FILES['arquivo_medicao']
        arquivo_up.seek(0)
        content = arquivo_up.read()
        nome = arquivo_up.name
        vinculo = request.user.get_vinculo()
        if medicao.arquivo:
            medicao.arquivo.delete()
        arquivo = Arquivo()
        arquivo.save(nome, vinculo)
        medicao.arquivo = arquivo
        medicao.save()
        arquivo.store(request.user, content)
        if ContratoTipoDocumentoComprobatorio.objects.filter(contrato__pk=contrato.id).exists():
            for field_conf in ContratoTipoDocumentoComprobatorio.objects.filter(contrato__pk=contrato.id):
                name_field_esperado = "field_name_{}".format(field_conf.tipo_documento_comprobatorio.id)
                if name_field_esperado in form.cleaned_data.keys():
                    id_tipo_doc = field_conf.tipo_documento_comprobatorio.id
                    MedicaoTipoDocumentoComprobatorio.objects.get_or_create(medicao=medicao,
                                                                            tipo_documento_comprobatorio=TipoDocumentoComprobatorio.objects.get(pk=id_tipo_doc),
                                                                            confirmacao_fiscal=form.cleaned_data.get(name_field_esperado) or MedicaoTipoDocumentoComprobatorio.NAO_SE_APLICA)
        if tipo_contrato == 'eletrico':
            kwargs = dict(
                ano_referencia=form.cleaned_data.get('ano_referencia'),
                mes_referencia=form.cleaned_data.get('mes_referencia'),
                consumo_ponta=form.cleaned_data.get('consumo_ponta'),
                consumo_fora_ponta=form.cleaned_data.get('consumo_fora_ponta'),
            )
            MedicaoEletrica.objects.update_or_create(medicao=medicao, defaults=kwargs)
        return httprr('..', anchor='parcela_{}'.format(parcela_id), message='Medição realizada com sucesso.')
    return locals()


@rtr()
@permission_required('contratos.pode_efetuar_medicao')
@verificar_fiscal()
def atualizar_medicao(request, medicao_id, contrato_id):
    title = 'Atualizar Medição'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    fiscal = contrato.get_fiscal(servidor=request.user.get_relacionamento())
    # é o mesmo fiscal que fez a medição?
    pode_gerenciar_todas_medicoes = fiscal.tipo.pode_gerenciar_todas_medicoes_contrato
    if fiscal.servidor != medicao.fiscal.servidor and not pode_gerenciar_todas_medicoes:
        return httprr(
            '/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id).format(contrato.id),
            'Somente o fiscal que registrou a medição tem permissão para alterá-la.',
        )

    tipo_contrato = ''
    tipo_contrato_eletrico = Configuracao.get_valor_por_chave('contratos', 'tipo_contrato_energia_eletrica')
    if tipo_contrato_eletrico and contrato.subtipo and contrato.subtipo.pk == int(tipo_contrato_eletrico):
        FormClass = MedicaoEletricaForm
        tipo_contrato = 'eletrico'
    else:
        FormClass = MedicaoForm

    form = FormClass(request.POST or None, request.FILES or None, parcela=medicao.parcela, instance=medicao, request=request)
    if form.is_valid():
        medicao = form.save(commit=False)
        medicao.fiscal = fiscal
        parcela = medicao.parcela
        parcela.registrar_medicao(medicao)
        arquivo_up = request.FILES.get('arquivo_medicao')
        arquivo = None
        if arquivo_up:
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if medicao.arquivo:
                medicao.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            medicao.arquivo = arquivo
        medicao.save()
        if arquivo_up and arquivo:
            arquivo_up.seek(0)
            content = arquivo_up.read()
            arquivo.store(request.user, content)
        if ContratoTipoDocumentoComprobatorio.objects.filter(contrato__pk=contrato.id).exists():
            for field_conf in ContratoTipoDocumentoComprobatorio.objects.filter(contrato__pk=contrato.id):
                name_field_esperado = "field_name_{}".format(field_conf.tipo_documento_comprobatorio.id)
                id_tipo_doc = 0
                if name_field_esperado in form.cleaned_data.keys():
                    id_tipo_doc = field_conf.tipo_documento_comprobatorio.id
                else:
                    return httprr('/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id),
                                  'Por favor, selecione um tipo de documento comprobatório.', 'error')
                medicao_tipo_doc = MedicaoTipoDocumentoComprobatorio.objects.filter(medicao__id=medicao.id, tipo_documento_comprobatorio__id=TipoDocumentoComprobatorio.objects.get(pk=id_tipo_doc).id).first()
                if medicao_tipo_doc:
                    medicao_tipo_doc.confirmacao_fiscal = form.cleaned_data.get(name_field_esperado) or MedicaoTipoDocumentoComprobatorio.NAO_SE_APLICA
                    medicao_tipo_doc.save()
                else:
                    return httprr('/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id),
                                  'Documento Comprobatório da Medição inexiste.', 'error')
        if tipo_contrato == 'eletrico':
            kwargs = dict(
                ano_referencia=form.cleaned_data.get('ano_referencia'),
                mes_referencia=form.cleaned_data.get('mes_referencia'),
                consumo_ponta=form.cleaned_data.get('consumo_ponta'),
                consumo_fora_ponta=form.cleaned_data.get('consumo_fora_ponta'),
            )
            MedicaoEletrica.objects.update_or_create(medicao=medicao, defaults=kwargs)
        return httprr('/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id), 'Medição atualizada com sucesso.')
    return locals()


@rtr()
@permission_required('contratos.pode_efetuar_medicao')
@verificar_fiscal()
def conferencia_documentos(request, medicao_id, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)

    title = f'Conferência de Documentos: {medicao}'
    medicoes = medicao.medicaotipodocumentocomprobatorio_set.all()

    return locals()


@rtr()
@permission_required('contratos.pode_efetuar_medicao')
@verificar_fiscal()
def adicionar_ocorrencia_medicao(request, medicao_id, contrato_id):
    title = 'Informar Ocorrência na Medição'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    eh_servidor = request.user.eh_servidor
    fiscal = contrato.get_fiscal(servidor=request.user.get_relacionamento())
    # é o mesmo fiscal que fez a medição?
    pode_gerenciar_todas_medicoes = fiscal.tipo.pode_gerenciar_todas_medicoes_contrato
    if fiscal.servidor != medicao.fiscal.servidor and not pode_gerenciar_todas_medicoes:
        return httprr(
            '/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id).format(contrato.id),
            'Somente o fiscal que registrou a medição tem permissão para alterar ou informar ocorrência.',
        )
    form = OcorrenciaMedicaoForm(request.POST or None, instance=medicao)
    if form.is_valid():
        medicao = form.save()
        return httprr('/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id), 'Ocorrência/Providência da Medição atualizada com sucesso.')
    return locals()


@rtr()
@permission_required('contratos.pode_efetuar_medicao')
@verificar_fiscal()
def excluir_medicao(request, medicao_id, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    fiscal = contrato.get_fiscal(servidor=request.user.get_relacionamento())
    pode_gerenciar_todas_medicoes = fiscal.tipo.pode_gerenciar_todas_medicoes_contrato
    if not fiscal.servidor == medicao.fiscal.servidor and not pode_gerenciar_todas_medicoes:
        return httprr("/contratos/contrato/{}/?tab=cronograma".format(contrato.id), 'Você não tem permissão para excluir essa medição')
    medicao.delete()
    return httprr('/contratos/contrato/{}/?tab=cronograma#parcela_{}'.format(contrato.id, medicao.parcela.id), 'Medição excluída com sucesso')


# TODO: A chamada para esta função foi removida na demanda 850, tendo em vista que o despacho agora é gerado como documento nato-digital
@rtr()
def despacho_medicao(request, medicao_id, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    parcela = medicao.parcela
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    dia = medicao.data_medicao.day
    mes = meses[medicao.data_medicao.month - 1]
    ano = medicao.data_medicao.year

    key = medicao.fiscal.servidor.setor.uo.setor.sigla
    mapa = dict()
    for campus in UnidadeOrganizacional.objects.suap().all():
        mapa[campus.setor.sigla] = {'endereco': campus.endereco, 'cidade': campus.municipio}
    endereco = mapa[key]['endereco']
    cidade = mapa[key]['cidade']
    return locals()


@group_required('Fiscal de Contrato')
@verificar_fiscal()
def gerar_despacho_documentotexto(request, medicao_id, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    # Instanciar modelo de documento texto
    modelo = None
    try:
        modelo = ModeloDocumento.objects.get(nome='Relatório Circustanciado de Recebimento Provisório')
    except Exception:
        messages.error(request, 'Não existe o modelo de documento texto com nome de "Relatório Circustanciado de Recebimento Provisório".')

    user = request.user

    docs_medicao = medicao.medicaotipodocumentocomprobatorio_set.filter()
    tabela_documentos_comprobatorios = '''<table border="1" style="border:1px solid #000000; width:100%">
    <tbody>
        <tr>
            <td rowspan="1" style="background-color:#7f7f7f">
            <p style="text-align:left"><span style="color:#ffffff"><span style="font-family:Calibri,serif"><span style="font-size:small"><strong>ITENS (Cadastrados pelo Gestor)</strong></span></span></span></p>
            </td>
            <td colspan="1" style="background-color:#7f7f7f">
            <p style="text-align:left"><span style="color:#ffffff"><span style="font-family:Calibri,serif"><span style="font-size:small"><strong>REVISADO?</strong></span></span></span></p>
            </td>
    '''
    for doc in docs_medicao:
        tabela_documentos_comprobatorios += "<tr><td>{}</td><td>{}</td></tr>".format(doc.tipo_documento_comprobatorio.descricao, doc.confirmacao_fiscal_display)

    tabela_documentos_comprobatorios += "</tbody> </table >"

    assunto = "Relatório de Recebimento Provisório - contrato {} - medição de {} até {}".format(contrato.numero, medicao.data_inicio.strftime("%d/%m/%Y"), medicao.data_fim.strftime("%d/%m/%Y"))
    setor_dono = get_setor(user)

    # Tags do modelo
    variaveis = dict()
    variaveis['cidade_campus_fiscal'] = contrato.campi.first().municipio
    variaveis['numero_processo_medicao_ou_contrato'] = medicao.processo if medicao.processo else contrato.processo
    variaveis['contrato_numero'] = contrato.numero
    variaveis['contrato_objeto'] = contrato.objeto
    variaveis['medicao_numero_nota_fiscal'] = medicao.numero_documento
    variaveis['medicao_data_inicial'] = medicao.data_inicio.strftime('%d/%m/%Y')
    variaveis['medicao_data_final'] = medicao.data_fim.strftime('%d/%m/%Y')
    variaveis['nome_contratada'] = contrato.pessoa_contratada.nome
    variaveis['cnpj_contratada'] = contrato.pessoa_contratada.get_cpf_ou_cnpj()
    variaveis['campus_pluralize'] = "dos Campi" if contrato.campi.all().count() > 1 else "do Campus"
    variaveis['contrato_sigla_campi'] = contrato.get_uos_as_string()
    variaveis['medicao_parcela_cronograma'] = medicao.parcela.cronograma.numero
    variaveis['instituicao_sigla'] = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    variaveis['medicao_valor'] = format_money(medicao.valor_executado)
    variaveis['medicao_valor_por_extenso'] = por_extenso(medicao.valor_executado)
    variaveis['contrato_nome_fiscal'] = medicao.fiscal.servidor.nome
    variaveis['contrato_matricula_fiscal'] = medicao.fiscal.servidor.matricula
    variaveis['tabela_documentos_comprobatorios'] = tabela_documentos_comprobatorios
    variaveis['ocorrencias'] = medicao.ocorrencia
    variaveis['providencias'] = medicao.providencia
    # Se documento ja existe e é rascunho ou concluido cria novamente
    # Se o documento está assinado ou finalizado já mostra documento e exibe uma mensagem que para gerar um novo deve cancelar o antigo
    # Se o documento está cancelado no momento de criar o novo deve adicionar o vinculo do antigo como retifica e depois adicionar a referencia para o novo

    variaveis_correntes = get_variaveis(
        documento_identificador=None, estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO, usuario=user, setor_dono=setor_dono
    )

    def gerar_documento():
        hipotese_legal = HipoteseLegal.objects.filter(pk=6).first()
        documento_novo = DocumentoTexto.adicionar_documento_texto(
            usuario=user, setor_dono=setor_dono, modelo=modelo, assunto=assunto, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, hipotese_legal=hipotese_legal, variaveis=variaveis)
        # Vincula o documento digital criado a medição do contrato
        medicao.despacho_documentotexto = documento_novo
        medicao.save()
        return documento_novo

    tag = 'success'
    if not medicao.despacho_documentotexto:
        documento_novo = gerar_documento()
        msg = 'Relatório gerado com sucesso!'
    elif medicao.despacho_documentotexto.estah_em_rascunho or medicao.despacho_documentotexto.estah_concluido:
        documento_novo = medicao.despacho_documentotexto
        variaveis_correntes.update(variaveis)
        documento_novo.corpo = processar_template_ckeditor(texto=modelo.corpo_padrao, variaveis=variaveis_correntes)
        if medicao.despacho_documentotexto.estah_concluido:
            documento_novo.editar_documento()
        documento_novo.save()
        msg = 'Relatório atualizado com sucesso!'
    elif medicao.despacho_documentotexto.estah_aguardando_assinatura:
        documento_novo = medicao.despacho_documentotexto
        msg = 'Este documento está na situação {} que não permite edição. Para gerar um novo despacho deve-se excluir solicitação da assinatura do documento: {}'.format(
            documento_novo.get_status(), documento_novo.identificador)
        tag = 'warning'
    elif medicao.despacho_documentotexto.estah_assinado or medicao.despacho_documentotexto.estah_finalizado:
        documento_novo = medicao.despacho_documentotexto
        msg = 'Este documento está na situação {} que não permite edição. Para gerar um novo despacho favor cancelar este documento: {}'.format(
            documento_novo.get_status(), documento_novo.identificador)
        tag = 'warning'
    elif medicao.despacho_documentotexto.estah_cancelado:
        documento_antigo = medicao.despacho_documentotexto
        documento_novo = gerar_documento()
        # tipo vinculo - retificação
        tipo_vinculo = TipoVinculoDocumento.objects.get(descricao='Retificação')
        # Vincula documentos
        vinculo_documentos = VinculoDocumentoTexto()
        vinculo_documentos.tipo_vinculo_documento = tipo_vinculo
        vinculo_documentos.documento_texto_base = documento_novo
        vinculo_documentos.documento_texto_alvo = documento_antigo
        vinculo_documentos.usuario_criacao = user
        vinculo_documentos.save()
        # Atualiza referencia da objeto de Medicao
        medicao.despacho_documentotexto = documento_novo
        medicao.save()
        msg = 'Relatório substituído com sucesso!'

    return httprr(documento_novo.get_absolute_url(), msg, tag=tag)


@rtr()
@permission_required('contratos.pode_submeter_arquivo')
def upload_contrato(request, contrato_id):
    title = 'Upload de Arquivo'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    form = UploadArquivoContratoForm(request.POST or None, request.FILES or None, instance=contrato)
    if form.is_valid():
        arquivo_up = request.FILES.get('arquivo_contrato')
        if arquivo_up:
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if contrato.arquivo:
                contrato.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            form.instance.arquivo = arquivo
            form.save()
            arquivo.store(request.user, content)
        return httprr("/contratos/contrato/{}/".format(contrato.id), 'Arquivo do contrato atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('contratos.pode_submeter_arquivo')
def upload_aditivo(request, aditivo_id):
    aditivo = get_object_or_404(Aditivo, pk=aditivo_id)
    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if aditivo.arquivo:
                aditivo.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            aditivo.arquivo = arquivo
            aditivo.save()
            arquivo.store(request.user, content)
            return httprr("/contratos/aditivo/{}/".format(aditivo.id), 'Termo aditivo enviado com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


@rtr()
@permission_required('contratos.pode_submeter_arquivo')
def upload_publicacao(request, pub_id, contrato_id):
    title = "Upload de publicação"
    publicacao = get_object_or_404(PublicacaoContrato, pk=pub_id)
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if publicacao.arquivo:
                publicacao.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            publicacao.arquivo = arquivo
            publicacao.save()
            arquivo.store(request.user, content)
            return httprr("/contratos/contrato/{}/".format(contrato.id), 'Publicação enviada com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


@rtr()
@permission_required('contratos.pode_submeter_medicao')
def notificar_ocorrencia(request, ocorrencia_id):
    ocorrencia = get_object_or_404(Ocorrencia, pk=ocorrencia_id)
    """ Enviando email, notificando a empresa sobre a ocorrência """
    if not ocorrencia.contrato.pessoa_contratada.email:
        return httprr(ocorrencia.contrato.get_absolute_url(), 'O e-mail da contratada não foi informado. Por favor, verifique.', tag='error')

    titulo = '[SUAP] Contratos: Notificação de Ocorrência'
    texto = []
    texto.append('<h1>Notificação de Ocorrência</h1>')
    texto.append('<dl>')
    texto.append('<dt>Descrição da Ocorrência:</dt><dd>{}</dd>'.format(ocorrencia.descricao))
    texto.append('</dl>')
    texto.append('<p>--</p>')
    url = '{}{}'.format(settings.SITE_URL, ocorrencia.contrato.get_absolute_url())
    texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(url))
    send_mail(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [ocorrencia.contrato.pessoa_contratada.email])

    ocorrencia.notificacao_enviada = True
    ocorrencia.save()

    return httprr(ocorrencia.contrato.get_absolute_url(), 'Notificação enviada com sucesso.')


def __upload_arquivo_ocorrencia(request, tipo, ocorrencia_id):
    """ Método privado, pois está sendo usado apenas internamente
        Responsável por realizar um upload de arquivo na ocorrencia.
        O upload pode ser da ocorrencia ou da resposta
        :param tipo = ['ocorrencia', 'resposta']
    """
    tipo_label = 'Ocorrência' if tipo == 'ocorrencia' else 'Resposta'
    title = 'Upload de Arquivo de {}'.format(tipo_label)
    ocorrencia = get_object_or_404(Ocorrencia, pk=ocorrencia_id)

    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            if tipo == 'ocorrencia':
                arquivo_up = request.FILES['arquivo']
                arquivo_up.seek(0)
                content = arquivo_up.read()
                nome = arquivo_up.name
                vinculo = request.user.get_vinculo()
                arquivo = Arquivo()
                arquivo.save(nome, vinculo)
                if ocorrencia.arquivo:
                    ocorrencia.arquivo.delete()
                ocorrencia.arquivo = arquivo
                ocorrencia.save()
                arquivo.store(request.user, content)
            else:
                ocorrencia.anexo_resposta = request.FILES['arquivo']
                ocorrencia.save()
            return httprr("/contratos/contrato/{}/".format(ocorrencia.contrato.id), 'Arquivo de {} enviado com sucesso.'.format(tipo_label))
    else:
        form = UploadArquivoForm()
    return locals()


@rtr()
@permission_required('contratos.pode_submeter_medicao')
def upload_ocorrencia(request, ocorrencia_id):
    return __upload_arquivo_ocorrencia(request, 'ocorrencia', ocorrencia_id)


@rtr()
@permission_required('contratos.pode_submeter_medicao')
def upload_ocorrencia_resposta(request, ocorrencia_id):
    return __upload_arquivo_ocorrencia(request, 'resposta', ocorrencia_id)


@rtr()
@permission_required('contratos.pode_submeter_arquivo')
def upload_publicacao_aditivo(request, pub_id, aditivo_id):
    publicacao = get_object_or_404(PublicacaoAditivo, pk=pub_id)
    aditivo = get_object_or_404(Aditivo, pk=aditivo_id)
    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if publicacao.arquivo:
                publicacao.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            publicacao.arquivo = arquivo
            publicacao.save()
            arquivo.store(request.user, content)
            return httprr("/contratos/aditivo/{}/".format(aditivo.id), 'Publicação enviada com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


@rtr()
@permission_required('contratos.pode_submeter_medicao')
@verificar_fiscal()
def upload_medicao(request, medicao_id, contrato_id):
    # TODO: verificar se somente quem fez a medição pode submeter
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    title = 'Enviar Arquivo - Número do Documento: {} (Contrato: {})'.format(medicao.numero_documento, contrato)

    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if medicao.arquivo:
                medicao.arquivo.delete()

            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            medicao.arquivo = arquivo
            medicao.save()
            arquivo.store(request.user, content)
            return httprr("/contratos/contrato/{}/".format(contrato.id), 'Anexo enviado com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


def visualizar_arquivo_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    arquivo = contrato.arquivo_contrato
    try:
        response = HttpResponse(arquivo.read(), content_type='application/pdf')
        response['Content-Disposition'] = 'filename=contrato.pdf'
        arquivo.close()
        return response
    except Exception:
        return HttpResponse("O arquivo solicitado foi adulterado ou não existe.")


def visualizar_arquivo(request, arquivo_id):
    arquivo = get_object_or_404(Arquivo, pk=arquivo_id)
    content = arquivo.load(request.user)
    if content is not None:
        response = HttpResponse(content, content_type=arquivo.get_content_type(content))
        response['Content-Disposition'] = f'inline; filename={get_valid_filename(arquivo.nome)}'
        return response
    else:
        return HttpResponse("O arquivo solicitado foi adulterado ou não existe.")


@rtr()
@permission_required('contratos.pode_visualizar_contrato')
def buscar_contrato_export_to_xls(request, contratos):
    return tasks.buscar_contrato_export_to_xls(contratos)


@rtr('contratos.html')
def contratos_a_serem_aditivados(request):
    cabecalho = 'Contratos a serem Aditivados'
    contratos = Contrato.objects.a_serem_aditivados()
    return locals()


@rtr('contratos.html')
def contratos_a_serem_licitados(request):
    cabecalho = 'Contratos a serem Licitados'
    contratos = Contrato.objects.a_serem_licitados()
    return locals()


@rtr()
def solicitacao_fiscal(request, contrato_id):
    title = 'Geração de Ofício para Solicitação de Fiscal'
    campus = get_uo(request.user).nome
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
    hoje = datetime.today()
    dia = hoje.day
    mes = meses[hoje.month - 1]
    ano = hoje.year

    template = get_template('contratos/templates/memorando_solicitacao_fiscal.html')
    html = template.render(
        {'title': title, 'campus': campus, 'contrato': contrato, 'meses': meses, 'hoje': hoje, 'dia': dia, 'mes': mes, 'ano': ano})

    try:
        modelo = ModeloDocumento.objects.get(nome='Ofício de Solicitação de Fiscal')
    except Exception:
        messages.error(request,
                       'Não existe o modelo de documento texto com nome de "Ofício de Solicitação de Fiscal".')

    user = request.user
    assunto = f"Ofício para Solicitação de Fiscal do Contrato {contrato.numero}"
    setor_dono = get_setor(user)

    documento_novo = DocumentoTexto.adicionar_documento_texto(usuario=user, setor_dono=setor_dono, assunto=assunto, modelo=modelo, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, corpo=html)
    # Cria vínculo entre o documento e o contrato
    documento_contrato = DocumentoTextoContrato()
    documento_contrato.documento = documento_novo
    documento_contrato.contrato = contrato
    documento_contrato.save()
    msg = 'Ofício gerado com sucesso!'
    return httprr(documento_novo.get_absolute_url(), msg, 'success')


@rtr()
def gerar_despacho_termo_aditivo(request, termo_id):
    title = 'Geração de Despacho para Termo Aditivo'
    termo = get_object_or_404(Aditivo, pk=termo_id)
    if request.method == 'GET':
        form = DespachoTermoAditivoForm()
    else:
        form = DespachoTermoAditivoForm(request.POST)
        if form.is_valid():
            memorando = form.cleaned_data['numero_memorando']
            despacho = form.cleaned_data['numero_despacho']
            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            hoje = datetime.today()
            dia = hoje.day
            mes = meses[hoje.month - 1]
            ano = hoje.year
            dia_contrato = termo.contrato.data_inicio.day
            mes_contrato = meses[termo.contrato.data_inicio.month - 1]
            ano_contrato = termo.contrato.data_inicio.year
            return render('despacho_termo_aditivo.html', locals())
    return locals()


@rtr()
def gerar_despacho_fiscal(request, contrato_id):
    title = 'Geração de Despacho para Fiscal'
    campus = get_uo(request.user).nome
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    if request.method == 'GET':
        form = DespachoFiscalForm()
    else:
        form = DespachoFiscalForm(request.POST)
        if form.is_valid():
            servidor = form.cleaned_data['servidor']
            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            hoje = datetime.today()
            dia = hoje.day
            mes = meses[hoje.month - 1]
            ano = hoje.year

            template = get_template('contratos/templates/despacho_fiscal.html')
            html = template.render(
                {'title': title, 'campus': campus, 'contrato': contrato,
                 'servidor': servidor, 'meses': meses, 'hoje': hoje, 'dia': dia, 'mes': mes, 'ano': ano})

            try:
                modelo = ModeloDocumento.objects.get(nome='Despacho Simples')
            except Exception:
                messages.error(request,
                               'Não existe o modelo de documento texto com nome de "Despacho Simples".')

            user = request.user
            assunto = f"Despacho para emissão de Portaria do Fiscal {servidor.nome} do Contrato {contrato.numero}"
            setor_dono = get_setor(user)

            documento_novo = DocumentoTexto.adicionar_documento_texto(usuario=user, setor_dono=setor_dono, assunto=assunto, modelo=modelo, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, corpo=html)
            # Cria vínculo entre o documento e o contrato
            documento_contrato = DocumentoTextoContrato()
            documento_contrato.documento = documento_novo
            documento_contrato.contrato = contrato
            documento_contrato.save()
            msg = 'Despacho gerado com sucesso!'

            return httprr(documento_novo.get_absolute_url(), msg, 'success')
    return locals()


@rtr()
def solicitacao_publicacao_portaria_fiscal(request, contrato_id):
    title = 'Geração de Ofício para Solicitação de Publicação de Portaria'
    campus = get_uo(request.user).nome
    if request.method == 'GET':
        form = SolicitacaoPublicacaoPortariaFiscalForm()
    else:
        form = SolicitacaoPublicacaoPortariaFiscalForm(request.POST)
        if form.is_valid():
            servidor = form.cleaned_data['servidor']
            contrato = get_object_or_404(Contrato, pk=contrato_id)
            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            hoje = datetime.today()
            dia = hoje.day
            mes = meses[hoje.month - 1]
            ano = hoje.year
            if contrato.processo:
                dia_processo = contrato.processo.data_cadastro.day
                mes_processo = meses[contrato.processo.data_cadastro.month - 1]
                ano_processo = contrato.processo.data_cadastro.year

            template = get_template('contratos/templates/memorando_portaria_fiscal.html')
            html = template.render(
                {'title': title, 'campus': campus, 'contrato': contrato, 'servidor': servidor, 'meses': meses, 'hoje': hoje, 'dia': dia, 'mes': mes, 'ano': ano})

            try:
                modelo = ModeloDocumento.objects.get(nome='Ofício de Solicitação de Publicação de Portaria')
            except Exception:
                messages.error(request,
                               'Não existe o modelo de documento texto com nome de "Ofício de Solicitação de Publicação de Portaria".')

            user = request.user
            assunto = f" Ofício para Solicitação de Portaria - Fiscal {servidor.nome} - Contrato {contrato.numero}"
            setor_dono = get_setor(user)

            documento_novo = DocumentoTexto.adicionar_documento_texto(usuario=user, setor_dono=setor_dono, assunto=assunto, modelo=modelo, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, corpo=html)
            # Cria vínculo entre o documento e o contrato
            documento_contrato = DocumentoTextoContrato()
            documento_contrato.documento = documento_novo
            documento_contrato.contrato = contrato
            documento_contrato.save()
            msg = 'Ofício gerado com sucesso!'
            return httprr(documento_novo.get_absolute_url(), msg, 'success')
    return locals()


@rtr()
def pendencias(request):
    notificador = Notificador()
    title = 'Pendências'
    count = 0

    if request.method == 'POST' and 'contrato_ids' in request.POST:
        for id in request.POST.getlist('contrato_ids'):
            contrato = Contrato.objects.get(pk=id)
            for fiscal in contrato.get_fiscais_atuais():
                titulo_dict = dict(numero_contrato=contrato.numero)
                mensagem_dict = dict(numero_contrato=contrato.numero, data_vencimento=contrato.data_vencimento.strftime('%d/%m/%Y'), campus=fiscal.campus.setor.nome)
                count = count + notificador.notificar(1, None, fiscal.servidor.email, titulo_dict, mensagem_dict)
        return httprr('/contratos/pendencias/', '{:d} notificações de vencimento de contrato enviadas com sucesso.'.format(count))

    if request.method == 'POST' and 'parcela_ids' in request.POST:
        for id in request.POST.getlist('parcela_ids'):
            parcela = Parcela.objects.get(pk=id)
            contrato = parcela.cronograma.contrato

            for fiscal in contrato.get_fiscais_atuais():
                data_prevista_fim = parcela.data_prevista_fim.strftime('%d/%m/%Y')
                data_prevista_inicio = parcela.data_prevista_inicio.strftime('%d/%m/%Y')
                titulo_dict = dict(numero_contrato=contrato.numero, data_prevista_fim=data_prevista_fim, data_prevista_inicio=data_prevista_inicio)
                mensagem_dict = dict(
                    numero_contrato=contrato.numero, data_prevista_fim=data_prevista_fim, data_prevista_inicio=data_prevista_inicio, campus=fiscal.campus.setor.nome
                )
                count = count + notificador.notificar(2, None, fiscal.servidor.email, titulo_dict, mensagem_dict)
        return httprr('/contratos/pendencias/', '{:d} notificações de medição de parcela atrasada enviadas com sucesso.'.format(count))

    form = RelatorioPendenciasForm(request.POST or None)
    if form.is_valid():
        uo = form.cleaned_data.get('campus')
        contratos = Contrato.objects.a_serem_aditivados().filter(campi=uo)
        total_contratos = len(contratos)
        parcelas = Parcela.get_parcelas_nao_medidas(uo=uo)

    return locals()


@rtr()
@verificar_fiscal()
def registrar_ocorrencia(request, contrato_id):
    title = 'Registro de Ocorrência'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    fiscal = contrato.get_fiscal(request.user.get_relacionamento())
    if request.method == 'POST':
        form = OcorrenciaForm(request.POST or None, contrato=contrato)
        if form.is_valid():
            form.instance.contrato = contrato
            form.instance.fiscal = fiscal
            form.save()
            return httprr('..', 'Ocorrência registrada com sucesso.')
    else:
        form = OcorrenciaForm(contrato=contrato)
    return locals()


@verificar_fiscal(modelo=Ocorrencia)
@rtr()
def editar_ocorrencia(request, ocorrencia_id):
    title = 'Editar Ocorrência'
    ocorrencia = get_object_or_404(Ocorrencia, pk=ocorrencia_id)
    contrato = get_object_or_404(Contrato, pk=ocorrencia.contrato.id)
    fiscal = contrato.get_fiscal(request.user.get_relacionamento())
    if fiscal != ocorrencia.fiscal:
        return httprr('..', 'Você não cadastrou essa ocorrência. Portanto, não pode editá-la.')
    if request.method == 'POST':
        form = OcorrenciaForm(request.POST, instance=ocorrencia)
        if form.is_valid():
            form.save()
            return httprr('..', 'Ocorrência editada com sucesso.')
    else:
        form = OcorrenciaForm(instance=ocorrencia)
    return locals()


@rtr()
def rol_responsabilidade_fiscais(request):
    title = 'Responsabilidades dos Fiscais'
    return locals()


@rtr()
def situacao_contratos(request):
    title = 'Situação dos Contratos'
    form = SituacaoContratosForm(request.POST or None)
    if form.is_valid():
        uo = form.cleaned_data['campus']
        eh_continuado = form.cleaned_data['eh_continuado']
        eh_concluido = form.cleaned_data['eh_concluido']
        data_inicio = form.cleaned_data['data_inicio']
        data_fim = form.cleaned_data['data_fim']
        contratos = Contrato.objects.all().order_by('data_inicio')
        relatorio = []
        if data_inicio and data_fim:
            # TODO: para data fim deverá ser considerado TODOS os aditivos
            contratos = contratos.filter(data_inicio__gt=data_inicio, data_fim__lt=data_fim)

            # selecionou campus?
            if uo:
                contratos = contratos.filter(campi=uo.pk)

            # continuado?
            if eh_continuado:
                contratos = contratos.filter(continuado=True)

            # concluídos?
            if eh_concluido:
                contratos = contratos.filter(concluido=True)

            # itera contratos e adiciona propriedades em uma lista
            for contrato in contratos:
                contratada = contrato.pessoa_contratada
                cpf_cnpj = contrato.pessoa_contratada.get_cpf_ou_cnpj()
                objeto = contrato.objeto
                numero_contrato = contrato.numero
                valor_contrato = contrato.valor
                vigencia_inicio = contrato.data_inicio
                vigencia_fim = contrato.data_fim
                continuado = contrato.continuado
                concluido = contrato.concluido

                # lista último termo aditivo de prazo
                qs_ultimo_ta_prazo = contrato.aditivos_set.all().filter(de_prazo=True)
                ultimo_ta_prazo = None
                if qs_ultimo_ta_prazo:
                    ultimo_ta_prazo = qs_ultimo_ta_prazo.order_by('-data_fim')[0]

                # valor global do contrato (valor inicial + aditivos -> os aditivos serão somados no ultimo_ta_valor)
                valor_global = valor_contrato

                # lista último termo aditivo de valor
                qs_ultimo_ta_valor = contrato.aditivos_set.all().filter(de_valor=True)
                ultimo_ta_valor = None
                if qs_ultimo_ta_valor:
                    ultimo_ta_valor = qs_ultimo_ta_valor.order_by('-id')[0]

                    # soma os aditivos de valor e joga resultado em valor_global (valor + aditivos)
                    for soma_ta_valor in qs_ultimo_ta_valor:
                        if soma_ta_valor.valor:  # tratando valor None em contratos antigos
                            valor_global = valor_global + soma_ta_valor.valor

                # lista empenhos referente ao contrato
                empenho = contrato.empenho

                # fiscais
                fiscais_nomes = ""
                for fiscais in contrato.fiscais_set.all():
                    fiscais_nomes = fiscais_nomes + fiscais.servidor.nome + " / "

                # adiciona a lista
                relatorio.append(
                    dict(
                        id=contrato.id,
                        contratada=contratada,
                        cpf_cnpj=cpf_cnpj,
                        objeto=objeto,
                        numero_contrato=numero_contrato,
                        valor_contrato=valor_contrato,
                        vigencia_inicio=vigencia_inicio,
                        vigencia_fim=vigencia_fim,
                        ultimo_ta_prazo=ultimo_ta_prazo,
                        ultimo_ta_valor=ultimo_ta_valor,
                        valor_global=valor_global,
                        empenho=empenho,
                        fiscais_nomes=fiscais_nomes,
                        continuado=continuado,
                        concluido=concluido,
                    )
                )

            return render('relatorio_situacao_contratos.html', locals())

    return locals()


@rtr()
def relatorio_pendencias_dados(request):
    title = 'Relatório de Pendências'
    form = RelatorioPendenciasForm(request.POST or None)
    contratos_pendentes = {}
    if form.is_valid():
        contratos_pendentes = Contrato.get_pendencias(form.cleaned_data['campus'])
        return render('relatorio_pendencias.html', locals())

    return locals()


@rtr()
def contrato_publico(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    data_vencimento = contrato.data_vencimento
    vence_nos_proximos_90_dias = False
    hoje = datetime.now().date()
    if data_vencimento and data_vencimento > hoje and (data_vencimento < (hoje + timedelta(days=90))):
        vence_nos_proximos_90_dias = True

    aditivos = contrato.get_aditivos()
    apostilamentos = contrato.apostilamentos_set.all()
    garantias = contrato.garantias_set.all()
    maosdeobra = contrato.maodeobra_set.all()
    ocorrencias = contrato.ocorrencia_set.all().order_by('data')
    title = 'Contrato {}'.format(contrato.numero)
    return locals()


@rtr()
def listar_contratos(request):
    title = 'Consulta Pública de Contratos'
    category = 'Consultas'
    icon = 'file-contract'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = FiltroContratoForm(request.POST or None)
    contratos = Contrato.objects.all().order_by('-data_vencimento')
    if form.is_valid():
        busca = form.cleaned_data.get('busca')
        if busca:
            or_queries = [Q(**{'{}__icontains'.format(field_name): busca}) for field_name in Contrato.SEARCH_FIELDS]
            contratos = contratos.filter(reduce(or_, or_queries))

        tipo_licitacao = form.cleaned_data.get('tipo_licitacao')
        if tipo_licitacao:
            contratos = contratos.filter(tipo_licitacao=tipo_licitacao)

        concluido = form.cleaned_data.get('concluido')
        if concluido:
            contratos = contratos.filter(concluido=concluido)

        cancelado = form.cleaned_data.get('cancelado')
        if cancelado:
            contratos = contratos.filter(concluido=cancelado)

        periodo_data_inicio = form.cleaned_data.get('periodo_data_inicio')
        if [_f for _f in periodo_data_inicio if _f]:
            contratos = contratos.filter(data_inicio__range=periodo_data_inicio)

        periodo_data_vencimento = form.cleaned_data.get('periodo_data_vencimento')
        if [_f for _f in periodo_data_vencimento if _f]:
            contratos = contratos.filter(data_vencimento__range=periodo_data_vencimento)

    custom_fields = dict(
        numero=LinkColumn('contrato_publico', kwargs={'contrato_id': Accessor('pk')}, verbose_name='Número do Contrato'),
        data_inicio=DateColumn(format="d/m/Y"),
        data_vencimento=DateColumn(format="d/m/Y"),
    )
    fields = ('numero', 'campi', 'pessoa_contratada', 'concluido', 'cancelado', 'data_inicio', 'data_vencimento')
    sequence = ['numero', 'data_inicio', 'data_vencimento']
    table = get_table(queryset=contratos, fields=fields, custom_fields=custom_fields, per_page_field=20, sequence=sequence, to_export=False)
    return locals()


@rtr()
def exportacao(request):
    def p(valor):
        if type(valor) is bool:
            return valor and "Sim" or "Não"
        return valor and valor or ""

    title = 'Exportação de dados de contrato'
    form = ExportacaoForm(request.POST or None)
    if form.is_valid():
        tipo = form.cleaned_data.get('tipo', None)
        data_inicio_periodo = form.cleaned_data.get('data_inicio_periodo', None)
        campi = form.cleaned_data.get('campi', None)
        status = form.cleaned_data.get('status', None)
        quadros = form.cleaned_data.get('quadros', [])

        quadro_publicacao = ExportacaoForm.QUADRO_PUBLICACAO in quadros
        quadro_cronograma = ExportacaoForm.QUADRO_CRONOGRAMA in quadros

        contratos = Contrato.objects.filter(campi__in=form.cleaned_data['campi'])

        if tipo is not None:
            contratos = contratos.filter(tipo=tipo)

        if status is not None:
            if status == ExportacaoForm.STATUS_CONCLUIDO:
                contratos = contratos.filter(concluido=True)
            elif status == ExportacaoForm.STATUS_CANCELADOS:
                contratos = contratos.filter(cancelado=True)
            elif status == ExportacaoForm.STATUS_ANDAMENTO:
                contratos = contratos.exclude(Q(concluido=True) | Q(cancelado=True))

        if data_inicio_periodo is not None and data_inicio_periodo[0] != '':
            contratos = contratos.filter(data_inicio__range=data_inicio_periodo)

        wb = xlwt.Workbook(encoding='iso8859-1')
        sheet = wb.add_sheet('Contratos')

        # Escreve cabeçalho geral
        linha = 0
        sheet.write(linha, 0, 'Número')
        sheet.write(linha, 1, 'Tipo')
        sheet.write(linha, 2, 'Subtipo')
        sheet.write(linha, 3, 'Valor do Contrato')
        sheet.write(linha, 4, 'Valor Executado')
        sheet.write(linha, 5, 'Valor Total')
        sheet.write(linha, 6, 'Início')
        sheet.write(linha, 7, 'Final')
        sheet.write(linha, 8, 'Vencimento')
        sheet.write(linha, 9, 'Objeto')
        sheet.write(linha, 10, 'Continuado?')
        sheet.write(linha, 11, 'Processo')
        sheet.write(linha, 12, 'Empenho')
        sheet.write(linha, 13, 'Contratada')
        sheet.write(linha, 14, 'Qtd Parcelas')
        sheet.write(linha, 15, 'Tipo da Licitação')
        sheet.write(linha, 16, 'Pregão')
        sheet.write(linha, 17, 'Estimativa para Início')
        sheet.write(linha, 18, 'Concluído?')
        sheet.write(linha, 19, 'Motivo de Conclusão')
        sheet.write(linha, 20, 'Cancelado')
        sheet.write(linha, 21, 'Motivo de Cancelamento')
        sheet.write(linha, 22, 'Data/Hora Cancelamento')
        sheet.write(linha, 23, 'Número Processo')
        sheet.write(linha, 24, 'Números de Empenhos')

        for c in contratos:
            linha += 1
            sheet.write(linha, 0, f'{p(c.numero)}')
            sheet.write(linha, 1, f'{p(c.tipo)}')
            sheet.write(linha, 2, f'{p(c.subtipo)}')
            sheet.write(linha, 3, f'{p(c.valor)}')
            sheet.write(linha, 4, f'{p(c.valor_executado)}')
            sheet.write(linha, 5, f'{p(c.valor_total)}')
            sheet.write(linha, 6, f'{p(c.data_inicio)}')
            sheet.write(linha, 7, f'{p(c.data_fim)}')
            sheet.write(linha, 8, f'{p(c.data_vencimento)}')
            sheet.write(linha, 9, f'{p(c.objeto)}')
            sheet.write(linha, 10, f'{p(c.continuado)}')
            sheet.write(linha, 11, f'{p(c.processo)}')
            sheet.write(linha, 12, f'{p(c.empenho)}')
            sheet.write(linha, 13, f'{p(c.pessoa_contratada)}')
            sheet.write(linha, 14, f'{p(c.qtd_parcelas)}')
            sheet.write(linha, 15, f'{p(c.tipo_licitacao)}')
            sheet.write(linha, 16, f'{p(c.pregao)}')
            sheet.write(linha, 17, f'{p(c.estimativa_licitacao)}')
            sheet.write(linha, 18, f'{p(c.concluido)}')
            sheet.write(linha, 19, f'{p(c.motivo_conclusao)}')
            sheet.write(linha, 20, f'{p(c.cancelado)}')
            sheet.write(linha, 21, f'{p(c.motivo_cancelamento)}')
            sheet.write(linha, 22, f'{p(c.dh_cancelamento)}')
            sheet.write(linha, 23, f'{p(c.numero_processo)}')
            sheet.write(linha, 24, f'{p(c.numero_empenho)}')

            if quadro_publicacao:
                publicacoes = c.get_publicacoes()
                if publicacoes.exists():
                    linha += 1
                    sheet.write(linha, 2, 'Tipo')
                    sheet.write(linha, 3, 'Número')
                    sheet.write(linha, 4, 'Data Publicação')

                    for pub in publicacoes:
                        linha += 1
                        sheet.write(linha, 1, 'Publicações')
                        sheet.write(linha, 2, f'{p(pub.tipo)}')
                        sheet.write(linha, 3, f'{p(pub.numero)}')
                        sheet.write(linha, 4, f'{p(pub.data)}')

            if quadro_cronograma:
                if c.cronograma_set.exists():
                    linha += 1
                    sheet.write(linha, 2, 'Número do Cronograma')
                    sheet.write(linha, 3, 'Nota de Lançamento')
                    sheet.write(linha, 4, 'Registro de Contrato')

                    for cronograma in c.cronograma_set.all():
                        linha += 1
                        sheet.write(linha, 1, 'Cronograma')
                        sheet.write(linha, 2, f'{p(cronograma.numero)}')
                        sheet.write(linha, 3, f'{p(cronograma.nl)}')
                        sheet.write(linha, 4, f'{p(cronograma.rc)}')

                        if cronograma.parcelas_set.exists():
                            linha += 1
                            sheet.write(linha, 2, 'Início Previsto')
                            sheet.write(linha, 3, 'Final Previsto')
                            sheet.write(linha, 4, 'Valor Previsto')
                            sheet.write(linha, 5, 'Valor Executado')
                            sheet.write(linha, 6, 'Sem Medição')
                            for parcela in cronograma.parcelas_set.all():
                                linha += 1
                                # Adiciona dados
                                sheet.write(linha, 2, f'{p(parcela.data_prevista_inicio)}')
                                sheet.write(linha, 3, f'{p(parcela.data_prevista_fim)}')
                                sheet.write(linha, 4, f'{p(parcela.valor_previsto)}')
                                sheet.write(linha, 5, f'{p(parcela.valor_executado_parcela())}')
                                sheet.write(linha, 6, f'{p(parcela.sem_medicao)}')

        # Salva e envia a planilha
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Contratos.xls'

        wb.save(response)
        return response

    return locals()


@rtr('processo_eletronico/templates/listar_documentos_adicionar.html')
@group_required('Gerente de Contrato')
def listar_documentos_adicionar_contrato(request, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)

    if not 'documento_eletronico' in settings.INSTALLED_APPS:
        raise Exception("A aplicação Documento Eletrônico não está instalada, no entanto, não será possível vincular documentos")

    if not request.user.has_perm('contratos.pode_adicionar_anexo'):
        return httprr(
            reverse_lazy('contrato', current_app='contratos', kwargs={'contrato_id': contrato.id}),
            'Você não tem permissão para vincular documentos ao contrato.'
        )

    # Usado no template para mostrar conteudo especifico do contrato
    is_contrato = True

    title = 'Documentos que podem ser vinculados ao contrato {}'.format(contrato.numero)
    setor = get_setor(request.user)
    initial = dict(campus=setor.uo_id, setor=setor.pk, ano=datetime.today().year)
    form = ListarDocumentosTextoForm(request.GET or initial, request=request)
    documentos, documentos_compartilhados, params, order_str = form.processar()

    # Exclusao e ordenacao dos documentos que podem ser adcionados
    documentos_ja_vinculados_ids = DocumentoTextoContrato.objects.filter(contrato=contrato).values_list(
        'documento__id', flat=True)
    documentos_finalizados_ids = DocumentoTexto.objects.filter(status=DocumentoStatus.STATUS_FINALIZADO).values_list(
        'id', flat=True)
    documentos = documentos.exclude(id__in=documentos_ja_vinculados_ids).filter(id__in=documentos_finalizados_ids)
    documentos = documentos.order_by('-data_criacao', 'identificador_tipo_documento_sigla', 'identificador_numero',
                                     'identificador_ano', 'identificador_setor_sigla')

    return locals()


@rtr()
@group_required("Gerente de Contrato")
def vincular_documento_contrato(request, contrato_id, documento_id):
    # View para adicionar um documento a um contrato

    contrato = get_object_or_404(Contrato, pk=contrato_id)
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)

    if not request.user.has_perm('contratos.pode_adicionar_anexo'):
        return httprr(
            reverse_lazy('contrato', current_app='contratos', kwargs={'contrato_id': contrato.id}),
            'Você não tem permissão para vincular documentos ao contrato.'
        )

    if documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
        raise PermissionDenied

    if not documento.estah_finalizado:
        raise PermissionDenied

    documento_contrato = DocumentoTextoContrato()
    documento_contrato.documento = documento
    documento_contrato.contrato = contrato
    documento_contrato.save()

    return httprr(
        reverse_lazy('contrato', current_app='contratos', kwargs={'contrato_id': contrato.id}), 'Documento vinculado com sucesso ao contrato.'
    )


@rtr()
@group_required('Gerente de Contrato', 'Operador de Contrato')
def adicionar_arrecadacao_receita(request, contrato_id):
    title = "Adicionar Valor Concessão"
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    arrecadacao = ArrecadacaoReceita()
    arrecadacao.contrato = contrato
    if request.method == 'POST':
        form = ArrecadacaoReceitaForm(request.POST, instance=arrecadacao)
        if form.is_valid():
            form.instance.contrato = contrato
            form.save()
            return httprr('..', 'Garantia adicionado com sucesso.')
    else:
        form = ArrecadacaoReceitaForm(instance=arrecadacao)
    return locals()


@rtr()
@group_required('Gerente de Contrato', 'Operador de Contrato')
def editar_arrecadacao(request, arrecadacao_id):
    title = "Editar Valor de Concessão"
    arrecadacao = get_object_or_404(ArrecadacaoReceita, pk=arrecadacao_id)
    if request.method == 'POST':
        form = ArrecadacaoReceitaForm(request.POST, instance=arrecadacao)
        if form.is_valid():
            form.save()
            return httprr("/contratos/contrato/{}/".format(arrecadacao.contrato.id), 'Valor de Concessão editado com sucesso.')
    else:
        form = ArrecadacaoReceitaForm(instance=arrecadacao)
    return locals()


@rtr()
@group_required('Gerente de Contrato', 'Operador de Contrato')
def excluir_arrecadacao(request, arrecadacao_id):
    arrecadacao = get_object_or_404(ArrecadacaoReceita, pk=arrecadacao_id)
    contrato_id = arrecadacao.contrato.id
    arrecadacao.delete()
    return httprr("/contratos/contrato/{}/".format(contrato_id), 'Valor da Concessão excluído com sucesso.')


@rtr()
@group_required('Fiscal de Contrato', 'Gerente de Contrato')
def receber_definitivamente_medicao(request, medicao_id):
    title = "Receber Definitivamente"
    medicao = get_object_or_404(Medicao, pk=medicao_id)
    contrato = medicao.parcela.cronograma.contrato

    if not in_group(request.user, 'Gerente de Contrato') and not contrato.eh_gestor_contrato(request.user.get_relacionamento()):
        raise PermissionDenied("Você não é Gestor deste contrato.")

    qtd_documentos = medicao.medicaotipodocumentocomprobatorio_set.filter(medicao__id=medicao.id, confirmacao_fiscal=MedicaoTipoDocumentoComprobatorio.CONFIRMADO).exclude(recebido_gerente="Recebido").count()

    if qtd_documentos > 0 or not medicao.medicaotipodocumentocomprobatorio_set.exists():
        initial = list()
        for reg in medicao.medicaotipodocumentocomprobatorio_set.filter(medicao__id=medicao.id, confirmacao_fiscal=MedicaoTipoDocumentoComprobatorio.CONFIRMADO).exclude(recebido_gerente="Recebido"):
            initial.append({'medicao': reg.medicao, 'tipo_documento_comprobatorio': reg.tipo_documento_comprobatorio,
                            'confirmacao_fiscal': reg.confirmacao_fiscal})
    else:
        return httprr("/contratos/contrato/{}/?tab=cronograma".format(contrato.id), 'Existem documentos pendentes de confirmação pelo Fiscal: {}.'.format(medicao.fiscal.servidor.nome), tag='warning')

    if medicao.medicaotipodocumentocomprobatorio_set.exists():
        MedicaoDocumentoComprobatorioSet = formset_factory(MedicaoTipoDocumentoComprobatorioForm, extra=qtd_documentos)
    else:
        return httprr('..', 'Medição ainda não possui nenhum documento comprobatório.', 'error')

    formset = MedicaoDocumentoComprobatorioSet(request.POST or None, request.FILES or None)
    for subform, data in zip(formset.forms, initial):
        subform.initial = data
        subform.fields['tipo_documento_comprobatorio'].widget.attrs['readonly'] = True
        subform.fields['confirmacao_fiscal'].widget.attrs['readonly'] = True
        subform.fields['recebido_gerente'].widget.attrs['required'] = True

    if formset.is_valid():
        tem_pendencias = False
        for form in formset.forms:
            if form.cleaned_data.get('recebido_gerente') and form.cleaned_data['recebido_gerente'] == "Pendente":
                tem_pendencias = True
                form.cleaned_data['confirmacao_fiscal'] = MedicaoTipoDocumentoComprobatorio.NAO_SE_APLICA
            form.save(commit=False)
            if 'tipo_documento_comprobatorio' in form.cleaned_data and form.cleaned_data.get('tipo_documento_comprobatorio'):
                instance = medicao.medicaotipodocumentocomprobatorio_set.get(tipo_documento_comprobatorio=form.cleaned_data['tipo_documento_comprobatorio'])
                instance.confirmacao_fiscal = form.cleaned_data['confirmacao_fiscal']
                instance.tipo_documento_comprobatorio = form.cleaned_data['tipo_documento_comprobatorio']
                instance.recebido_gerente = form.cleaned_data['recebido_gerente']
                instance.parecer_gerente = form.cleaned_data['parecer_gerente']
                instance.avaliador_gerente = request.user
                instance.data_avaliacao = datetime.now()
                instance.save()
        if tem_pendencias:
            Notificar.informar_pendencias_na_medicao_ao_fiscal(medicao)
            return httprr("/contratos/contrato/{}/".format(contrato.id),
                          'Recebimento Definitivo realizado. Foi enviada uma notificação para o Fiscal com as pendências informadas.')
        else:
            return httprr("/contratos/contrato/{}/".format(contrato.id), 'Recebimento Definitivo realizado com sucesso.')
    return locals()


@group_required('Fiscal de Contrato', 'Gerente de Contrato')
def gerar_termo_definitivo_documentotexto(request, medicao_id, contrato_id):
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    medicao = get_object_or_404(Medicao, pk=medicao_id)

    if not in_group(request.user, 'Gerente de Contrato') and not contrato.eh_gestor_contrato(request.user.get_relacionamento()):
        raise PermissionDenied("Você não é Gestor deste contrato.")

    # Instanciar modelo de documento texto
    modelo = None
    try:
        modelo = ModeloDocumento.objects.get(nome='Termo Circunstanciado de Recebimento Definitivo')
    except Exception:
        messages.error(request, 'Não existe o modelo de documento texto com nome de "Termo Circunstanciado de Recebimento Definitivo".')

    user = request.user

    assunto = "Termo referente ao contrato nº {} - medição de {} até {}".format(contrato.numero, medicao.data_inicio.strftime("%d/%m/%Y"), medicao.data_fim.strftime("%d/%m/%Y"))
    setor_dono = get_setor(user)

    # def get_lista_documentos_display():
    docs_medicao = medicao.medicaotipodocumentocomprobatorio_set.filter(recebido_gerente="Recebido")
    tabela_documentos_comprobatorios = '''<table border="1" style="border:1px solid #000000; width:100%">
    <tbody>
        <tr>
            <td rowspan="1" style="background-color:#7f7f7f">
            <p style="text-align:left"><span style="color:#ffffff"><span style="font-family:Calibri,serif"><span style="font-size:small"><strong>ITENS (Cadastrados pelo Gestor)</strong></span></span></span></p>
            </td>
            <td colspan="1" style="background-color:#7f7f7f">
            <p style="text-align:left"><span style="color:#ffffff"><span style="font-family:Calibri,serif"><span style="font-size:small"><strong>REVISADO?</strong></span></span></span></p>
    '''
    for doc in docs_medicao:
        tabela_documentos_comprobatorios += "<tr><td>{}</td><td>{}</td></tr>".format(doc.tipo_documento_comprobatorio.descricao, doc.confirmacao_fiscal_display)

    tabela_documentos_comprobatorios += "</tbody> </table >"
    # Tags do modelo
    variaveis = dict()
    variaveis['cidade_campus_fiscal'] = contrato.campi.first().municipio
    variaveis['numero_processo_medicao_ou_contrato'] = medicao.processo if medicao.processo else contrato.processo
    variaveis['contrato_numero'] = contrato.numero
    variaveis['contrato_objeto'] = contrato.objeto
    variaveis['medicao_numero_nota_fiscal'] = medicao.numero_documento
    variaveis['medicao_data_inicial'] = medicao.data_inicio.strftime('%d/%m/%Y')
    variaveis['medicao_data_final'] = medicao.data_fim.strftime('%d/%m/%Y')
    variaveis['nome_contratada'] = contrato.pessoa_contratada.nome
    variaveis['cnpj_contratada'] = contrato.pessoa_contratada.get_cpf_ou_cnpj()
    variaveis['campus_pluralize'] = "dos Campi" if contrato.campi.all().count() > 1 else "do Campus"
    variaveis['contrato_sigla_campi'] = contrato.get_uos_as_string()
    variaveis['medicao_parcela_cronograma'] = medicao.parcela.cronograma.numero
    variaveis['instituicao_sigla'] = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    variaveis['medicao_valor'] = format_money(medicao.valor_executado)
    variaveis['medicao_valor_por_extenso'] = por_extenso(medicao.valor_executado)
    variaveis['medicao_parcela_valor_previsto'] = format_money(medicao.parcela.valor_previsto)
    variaveis['contrato_nome_fiscal'] = medicao.fiscal.servidor.nome
    variaveis['contrato_matricula_fiscal'] = medicao.fiscal.servidor.matricula
    variaveis['tabela_documentos_comprobatorios'] = tabela_documentos_comprobatorios

    variaveis_correntes = get_variaveis(
        documento_identificador=None, estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO, usuario=user, setor_dono=setor_dono
    )

    def gerar_documento():
        hipotese_legal = HipoteseLegal.objects.filter(pk=6).first()
        documento_novo = DocumentoTexto.adicionar_documento_texto(
            usuario=user, setor_dono=setor_dono, modelo=modelo, assunto=assunto, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, hipotese_legal=hipotese_legal, variaveis=variaveis)
        # Vincula o documento digital criado a medição do contrato
        medicao.termo_definitivo_documentotexto = documento_novo
        medicao.save()
        return documento_novo

    documento_novo = None
    msg = ''

    if not medicao.termo_definitivo_documentotexto:
        documento_novo = gerar_documento()
        msg = 'Termo Circunstanciado de Recebimento Definitivo gerado com sucesso.'
    elif medicao.termo_definitivo_documentotexto.estah_em_rascunho or medicao.termo_definitivo_documentotexto.estah_concluido:
        documento_novo = medicao.termo_definitivo_documentotexto
        variaveis_correntes.update(variaveis)
        documento_novo.corpo = processar_template_ckeditor(texto=modelo.corpo_padrao, variaveis=variaveis_correntes)
        if medicao.termo_definitivo_documentotexto.estah_concluido:
            documento_novo.editar_documento()
        documento_novo.save()
        msg = 'Termo Circunstanciado de Recebimento Definitivo atualizado com sucesso.'
    elif medicao.termo_definitivo_documentotexto.estah_assinado or medicao.termo_definitivo_documentotexto.estah_finalizado:
        documento_novo = medicao.termo_definitivo_documentotexto
        msg = 'Este documento está na situação {} que não permite edição. Para gerar um novo despacho favor cancelar este documento: {}'.format(
            documento_novo.get_status(), documento_novo.identificador)
    elif medicao.termo_definitivo_documentotexto.estah_cancelado:
        documento_antigo = medicao.termo_definitivo_documentotexto
        documento_novo = gerar_documento()
        # tipo vinculo - retificação
        tipo_vinculo = TipoVinculoDocumento.objects.get(descricao='Retificação')
        # Vincula documentos
        vinculo_documentos = VinculoDocumentoTexto()
        vinculo_documentos.tipo_vinculo_documento = tipo_vinculo
        vinculo_documentos.documento_texto_base = documento_novo
        vinculo_documentos.documento_texto_alvo = documento_antigo
        vinculo_documentos.usuario_criacao = user
        vinculo_documentos.save()
        # Atualiza referencia da objeto de Medicao
        medicao.termo_definitivo_documentotexto = documento_novo
        medicao.save()
        msg = 'Termo Circunstanciado de Recebimento Definitivo substituído com sucesso.'

    if documento_novo and msg:
        return httprr(documento_novo.get_absolute_url(), msg)
    else:
        return httprr('..', 'Erro ao tentar gerar termo definitivo.', 'error')


@rtr()
@login_required()
def relatorio_valores_executados(request, contrato_id):
    title = 'Demonstrativo de Valores Executados por Campus'
    contrato = get_object_or_404(Contrato, pk=contrato_id)
    cronograma = contrato.get_cronograma()
    lista_valores_executados = []
    infos_sem_campus = dict()
    if cronograma:
        total_contrato = Decimal('0')
        pks_uos_contrato = Contrato.objects.filter(pk=contrato.id).values_list('campi', flat=True)
        for uo in UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato):
            infos = dict()
            total = Decimal('0')
            for parcela in cronograma.parcelas_set.all():
                for medicao in parcela.medicoes_set.filter(campus=uo):
                    total += medicao.valor_executado
            total_contrato += total

            infos['uo'] = uo.sigla
            infos['total_executado'] = total
            lista_valores_executados.append(infos)
    total_sem_campus_definido = contrato.get_valor_executado() - total_contrato
    infos_sem_campus['uo'] = 'Sem campus definido'
    infos_sem_campus['total_executado'] = total_sem_campus_definido
    lista_valores_executados.append(infos_sem_campus)
    return locals()
