# -*- coding: utf-8 -*-

import datetime

from django.db.models.aggregates import Count
from django.http import HttpResponse
from django.utils.text import get_valid_filename

from comum.models import Arquivo
from comum.utils import get_uo, get_sigla_reitoria
from convenios.forms import AditivoForm, AnexoForm, UploadArquivoForm, BuscaConvenioForm, CampusForm
from convenios.models import Convenio, Aditivo, AnexoConvenio
from djtools.html.graficos import PieChart
from djtools.templatetags.filters import in_group
from djtools.utils import group_required, rtr, httprr
from rh.models import UnidadeOrganizacional


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios', 'Visualizador de Convênios'])
def convenios(request):
    title = "Busca de Convênio"
    form = BuscaConvenioForm(request.POST or None, request=request)
    if form.is_valid():
        numero = form.cleaned_data['numero']
        conveniada = form.cleaned_data['conveniada']
        uo = form.cleaned_data['uo']
        situacao = form.cleaned_data['situacao']
        tipo = form.cleaned_data['tipo']
        interveniente = form.cleaned_data['interveniente']
        data_inicio = form.cleaned_data['data_inicio']
        data_fim = form.cleaned_data['data_fim']
        convenios = Convenio.objects.all()
        if numero:
            convenios = convenios.filter(numero=numero)
        if uo:
            convenios = convenios.filter(uo=uo)
        if situacao:
            convenios = convenios.filter(situacao=situacao)
        if tipo:
            convenios = convenios.filter(tipo=tipo)
        if interveniente:
            convenios = convenios.filter(interveniente=interveniente)
        if data_inicio:
            convenios = convenios.filter(data_inicio=data_inicio)
        if data_fim:
            convenios = convenios.filter(data_fim=data_fim)
        if conveniada:
            convenios = convenios.filter(vinculos_conveniadas__in=[conveniada])
        convenios = convenios.order_by('id')
    return locals()


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios', 'Visualizador de Convênios'])
def conveniados(request):
    title = 'Instituições Conveniadas'
    if in_group(request.user, ['Operador de Convênios']):
        sigla_reitoria = get_sigla_reitoria()
        if UnidadeOrganizacional.objects.suap().filter(sigla=sigla_reitoria).exists():
            reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
            uos = UnidadeOrganizacional.objects.suap().filter(id__in=[reitoria.id, get_uo(request.user).id])
        else:
            uos = UnidadeOrganizacional.objects.suap().filter(id=get_uo(request.user).id)
    else:
        uos = UnidadeOrganizacional.objects.suap().filter(id__in=Convenio.objects.values_list('uo', flat=True))

    form = CampusForm(request.POST or None, uos=uos)
    if request.POST and form.is_valid():
        if form.cleaned_data.get('uo'):
            uos = uos.filter(id=form.cleaned_data.get('uo').id)
        campi = []

        for uo in uos:
            convenios = Convenio.objects.filter(uo=uo)
            if convenios:
                uo.parceiros = []
                for convenio in convenios:
                    for pj in convenio.vinculos_conveniadas.filter(pessoa__pessoajuridica__isnull=False).order_by('pessoa__nome'):
                        if not pj in uo.parceiros:
                            uo.parceiros.append(pj)

                campi.append(uo)
    return locals()


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios', 'Visualizador de Convênios'])
def convenios_a_vencer(request):
    title = 'Convênios a Vencer'
    hoje = datetime.date.today()
    if in_group(request.user, ['Operador de Convênios']):
        sigla_reitoria = get_sigla_reitoria()
        if UnidadeOrganizacional.objects.suap().filter(sigla=sigla_reitoria).exists():
            reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
            queryset = Convenio.objects.filter(continuado=True, data_fim__gte=hoje, uo__in=[get_uo(request.user).id, reitoria.id]).order_by('-data_fim')
        else:
            queryset = Convenio.objects.filter(continuado=True, data_fim__gte=hoje, uo=get_uo(request.user)).order_by('-data_fim')
    else:
        queryset = Convenio.objects.filter(continuado=True, data_fim__gte=hoje).order_by('-data_fim')
    convenios = []
    for convenio in queryset:

        prazo_vencimento = convenio.get_data_vencimento() - hoje
        if prazo_vencimento.days <= 30:
            convenios.append(convenio)
    return locals()


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios', 'Visualizador de Convênios'])
def convenio(request, convenio_id):
    is_operador = in_group(request.user, ['Operador de Convênios Sistêmico', 'Operador de Convênios'])
    convenio = Convenio.objects.get(pk=convenio_id)
    title = 'Convênio {}'.format(convenio.numero)
    aditivos = convenio.get_aditivos()
    return locals()


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios'])
def adicionar_aditivo(request, convenio_id):
    title = 'Adicionar Aditivo'
    convenio = Convenio.objects.get(id=convenio_id)
    if request.method == 'POST':
        form = AditivoForm(data=request.POST)
        if form.is_valid():
            termo = form.save(commit=False)
            convenio.adicionar_termo_aditivo(termo)
            return httprr("/convenios/convenio/{}/".format(convenio.id), 'Aditivo adicionado com sucesso.')
    else:
        form = AditivoForm()
    return locals()


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios'])
def atualizar_aditivo(request, aditivo_id):
    title = 'Editar Aditivo'
    aditivo = Aditivo.objects.get(pk=aditivo_id)
    if request.method == 'POST':
        form = AditivoForm(data=request.POST)
        if form.is_valid():
            termo = form.save(commit=False)
            aditivo.objeto = termo.objeto
            aditivo.data = termo.data
            aditivo.data_inicio = termo.data_inicio
            aditivo.data_fim = termo.data_fim
            aditivo.save()
            return httprr("/convenios/convenio/{}/".format(aditivo.convenio.id), 'Aditivo atualizado com sucesso.')
    else:
        form = AditivoForm(instance=aditivo)
    return locals()


@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios'])
def excluir_aditivo(request, aditivo_id):
    aditivo = Aditivo.objects.get(pk=aditivo_id)
    convenio_id = aditivo.convenio.id
    aditivo.delete()
    return httprr("/convenios/convenio/{}/".format(convenio_id), 'Aditivo excluído com sucesso.')


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios'])
def adicionar_anexo(request, convenio_id):
    title = 'Adicionar Anexo'
    convenio = Convenio.objects.get(id=convenio_id)
    if request.method == 'POST':
        form = AnexoForm(data=request.POST)
        if form.is_valid():
            anexo = form.save(commit=False)
            convenio.adicionar_anexo(anexo)
            return httprr("/convenios/upload_anexo/{:d}/".format(anexo.pk), 'Anexo adicionado com sucesso. Submeta o arquivo digitalizado.')
    else:
        form = AnexoForm()
    return locals()


@rtr()
@group_required('Operador de Convênios Sistêmico')
def atualizar_anexo(request, anexo_id):
    title = 'Editar Anexo'
    anexo = AnexoConvenio.objects.get(pk=anexo_id)
    if request.method == 'POST':
        form = AnexoForm(data=request.POST)
        if form.is_valid():
            temp = form.save(commit=False)
            anexo.descricao = temp.descricao
            anexo.tipo = temp.tipo
            anexo.save()
            return httprr("/convenios/convenio/{}/".format(anexo.convenio.id), 'Anexo atualizado com sucesso.')
    else:
        form = AnexoForm(instance=anexo)
    return locals()


@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios'])
def excluir_anexo(request, anexo_id):
    anexo = AnexoConvenio.objects.get(pk=anexo_id)
    convenio_id = anexo.convenio.id
    anexo.delete()
    return httprr("/convenios/convenio/{}/".format(convenio_id), 'Anexo removido com sucesso.')


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios'])
def upload_anexo(request, anexo_id):
    title = 'Upload de Arquivo'
    anexo = AnexoConvenio.objects.get(id=anexo_id)
    convenio = anexo.convenio

    if request.method == 'POST':
        form = UploadArquivoForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo_up = request.FILES['arquivo']
            arquivo_up.seek(0)
            content = arquivo_up.read()
            nome = arquivo_up.name
            vinculo = request.user.get_vinculo()
            if anexo.arquivo:
                anexo.arquivo.delete()
            arquivo = Arquivo()
            arquivo.save(nome, vinculo)
            anexo.arquivo = arquivo
            anexo.save()
            arquivo.store(request.user, content)
            return httprr("/convenios/convenio/{}/".format(convenio.id), 'Anexo enviado com sucesso.')
    else:
        form = UploadArquivoForm()
    return locals()


@group_required(['Operador de Convênios Sistêmico', 'Operador de Convênios', 'Visualizador de Convênios'])
def visualizar_arquivo(request, id_arquivo):
    arquivo = Arquivo.objects.all().get(id=id_arquivo)
    content = arquivo.load(request.user)
    if content:
        response = HttpResponse(content, content_type=arquivo.get_content_type(content))
        response['Content-Disposition'] = f'inline; filename={get_valid_filename(arquivo.nome)}'
        return response
    else:
        return HttpResponse('O arquivo solicitado foi adulterado ou não existe.')


@rtr()
@group_required(['Operador de Convênios Sistêmico', 'Visualizador de Convênios'])
def estatisticas_convenios(request):
    title = 'Convênios - Estatísticas'
    # grafico 1
    series1 = Convenio.objects.all().values('uo__sigla').annotate(qtd=Count('uo__sigla')).order_by('uo__sigla')
    dados = list()
    for item in series1:
        dados.append([item['uo__sigla'], item['qtd']])
    if dados[-1][1] == 0:
        dados.pop()
    grafico1 = PieChart('grafico1', title='Convênios por Campus', subtitle='Total de convênios por campus', minPointLength=0, data=dados)

    series2 = Convenio.objects.all().values('vinculos_conveniadas__pessoa__nome').annotate(qtd=Count('vinculos_conveniadas__pessoa__nome')).order_by('vinculos_conveniadas__pessoa__nome')
    dados2 = list()
    for item in series2:
        dados2.append([item['vinculos_conveniadas__pessoa__nome'], item['qtd']])
    if dados2[-1][1] == 0:
        dados2.pop()
    grafico2 = PieChart('grafico2', title='Convênios por Conveniado', subtitle='Total de convênios por instituição conveniada', minPointLength=0, data=dados2)
    return locals()
