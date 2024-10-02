# -*- coding: utf-8 -*-


from django.shortcuts import get_object_or_404

from integracao_wifi.forms import RenovacaoAutorizacaoDispositivoForm
from integracao_wifi.models import AutorizacaoDispositivo
from djtools.utils import httprr, rtr, permission_required
from integracao_wifi.forms import GerarTokensWifiForm


@rtr()
@permission_required('integracao_wifi.change_tokenwifi')
def gerar_tokens_wifi(request):
    title = 'Gerar Tokens Wifi'
    form = GerarTokensWifiForm(data=request.POST or None, request=request)
    if form.is_valid():
        tokens = form.processar()
        form = None
    return locals()


@rtr()
@permission_required('integracao_wifi.change_autorizacaodispositivo')
def renovar_autorizacao(request, pk):
    title = 'Renovar Autorização de Dispositivo IoT'
    obj = get_object_or_404(AutorizacaoDispositivo, pk=pk)

    if not request.user.groups.filter(name='Administradores de Dispositivos IoT').exists() and obj.vinculo_solicitante != request.user.get_vinculo():
        return httprr('..', 'Você não possui permissão para acessar a página solicitada.', 'error')

    form = RenovacaoAutorizacaoDispositivoForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Autorização renovada com sucesso.')
    return locals()


@permission_required('integracao_wifi.change_autorizacaodispositivo')
def revogar_autorizacao(request, pk):
    obj = get_object_or_404(AutorizacaoDispositivo, pk=pk)

    if not request.user.groups.filter(name='Administradores de Dispositivos IoT').exists() and obj.vinculo_solicitante != request.user.get_vinculo():
        return httprr('..', 'Você não possui permissão para acessar a página solicitada.', 'error')

    obj.revogar_autorizacao()
    return httprr('..', 'Autorização revogada com sucesso.')


@permission_required('integracao_wifi.change_autorizacaodispositivo')
def cancelar_autorizacao(request, pk):
    obj = get_object_or_404(AutorizacaoDispositivo, pk=pk)

    if not request.user.groups.filter(name='Administradores de Dispositivos IoT').exists() and obj.vinculo_solicitante != request.user.get_vinculo():
        return httprr('..', 'Você não possui permissão para acessar a página solicitada.', 'error')

    obj.cancelar_autorizacao()
    return httprr('..', 'Autorização excluída com sucesso.')
