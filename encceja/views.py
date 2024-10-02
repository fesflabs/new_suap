# -*- coding: utf-8 -*-
import datetime

from django.conf import settings
from django.shortcuts import get_object_or_404
from sentry_sdk import capture_exception

from djtools import layout
from djtools.utils import rtr, httprr, permission_required
from comum.models import RegistroEmissaoDocumento
from edu.models import SolicitacaoCertificadoENEM
from encceja.forms import ImportarForm, FiltroQuantitativoForm, CancelamentoSolicitacaoForm
from encceja.models import Solicitacao


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()

    servicos_anonimos.append(dict(categoria='Relatórios', url="/encceja/quantitativo/", icone="certificate", titulo='Certificação ENCCEJA / ENEM'))

    return servicos_anonimos


@permission_required('encceja.add_solicitacao')
@rtr()
def solicitacao(request, pk):
    obj = get_object_or_404(Solicitacao.objects, pk=pk)
    motivo_certificacao_negada = obj.get_motivo_certificacao_negada()
    title = str(obj)
    if 'imprimir' in request.GET:
        try:
            com_timbre = 'timbre' in request.GET
            return obj.imprimir_certificacao(request.user, com_timbre=com_timbre)
        except Exception as e:
            if settings.DEBUG:
                raise e
            capture_exception(e)
            return httprr('/encceja/solicitacao/{}/'.format(pk), 'Ocorreu um erro ao gerar o certificado. Verifique se o modelo de certificado está cadastrado corretamente e tente novamente.', 'error')
    return locals()


@permission_required('encceja.add_solicitacao')
@rtr()
def cancelar_solicitacao(request, pk):
    obj = Solicitacao.objects.get(pk=pk)
    title = str(obj)
    form = CancelamentoSolicitacaoForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        form.instance.cancelada = True
        form.instance.data_cancelamento = datetime.date.today()
        form.instance.responsavel_cancelamento = request.user
        form.save()
        RegistroEmissaoDocumento.objects.filter(tipo='ENCCEJA', modelo_pk=obj.pk).delete()
        return httprr('..', 'Cancelamento realizado com sucesso.')
    return locals()


@permission_required('encceja.add_configuracao')
@rtr()
def importar_resultado(request):
    title = 'Importar Resultado'
    form = ImportarForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        try:
            form.processar()
        except Exception:
            return httprr('..', 'Formato da Planilha inválido, por favor verifique os dados da planilha novamente.')
        return httprr('..', 'Importação realizada com sucesso.')
    return locals()


@rtr()
def quantitativo(request):
    title = 'Ensino Médio - Quantitativo de Certificados e Declarações Emitidos'
    category = 'Relatórios'
    icon = 'certificate'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = FiltroQuantitativoForm(data=request.GET or None)
    primeira_solicitacao = SolicitacaoCertificadoENEM.objects.order_by('data_solicitacao').first()
    if primeira_solicitacao:
        primeira_solicitacao = primeira_solicitacao.data_solicitacao
    else:
        primeira_solicitacao = Solicitacao.objects.order_by('data_emissao').first()
        if primeira_solicitacao:
            primeira_solicitacao = primeira_solicitacao.data_emissao
    if form.is_valid():
        registros = form.processar()
    else:
        registros = form.get_registros()
    return locals()
