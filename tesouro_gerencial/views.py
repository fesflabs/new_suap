from collections import OrderedDict
from datetime import datetime

from djtools import layout
from djtools.templatetags.filters import in_group
from djtools.utils import rtr, httprr, group_required
from rh.models import UnidadeOrganizacional
from tesouro_gerencial.forms import VariavelFom, ImportacaoTesouroGerencial, CampiFom
from tesouro_gerencial.models import Variavel, DocumentoEmpenhoEspecifico, DocumentoEmpenho, NotaCredito, RAP, \
    TipoDocumentoEmpenhoEspecifico


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()
    if in_group(request.user, 'Gestor do Tesouro Gerencial'):
        ano = datetime.now().year
        for tipo in TipoDocumentoEmpenhoEspecifico.objects.all():
            documentos_especificos = DocumentoEmpenhoEspecifico.objects.filter(documento_empenho__data_emissao__year=ano, tipo=tipo)
            if not documentos_especificos.exists():
                inscricoes.append(
                    dict(
                        url=f'/admin/tesouro_gerencial/documentoempenhoespecifico/add/?tipo={tipo.id}',
                        titulo=f'Adicionar o Documento de Empenho de <strong>{tipo}</strong>.',
                    )
                )
    return inscricoes


@layout.alerta()
def index_alertas(request):
    alertas = list()
    if in_group(request.user, 'Gestor do Tesouro Gerencial'):
        ano = datetime.now().year
        documento_empenho_ano_corrente = DocumentoEmpenho.objects.filter(data_emissao__year=ano)
        nota_credito_ano_corrente = NotaCredito.objects.filter(data_emissao__year=ano)
        restos_a_pagar_ano_corrente = RAP.objects.filter(ano=ano)
        if not (documento_empenho_ano_corrente.exists() and nota_credito_ano_corrente.exists() and restos_a_pagar_ano_corrente.exists()):
            alertas.append(
                dict(
                    url='https://tesourogerencial.tesouro.gov.br/',
                    titulo='Atualizar os relatório do <strong>Tesouro Gerencial.</strong></a>'
                )
            )
    return alertas


@rtr()
@group_required('Gestor do Tesouro Gerencial')
def variaveis(request):
    title = 'Relatório de Variáveis por Campus'
    form = VariavelFom(request.GET or None)
    variaveis = list()
    if form.is_valid():
        campus = form.cleaned_data.get('campus')
        ano = form.cleaned_data.get('ano')
        funcoes = OrderedDict()
        funcoes['DEST_EXEC'] = 'get_DEST_EXEC'
        funcoes['LOA_EXEC'] = 'get_LOA_EXEC'
        funcoes['RECCAPT'] = 'get_RECCAPT'
        funcoes['20RL_LOA'] = 'get_20RL_LOA'
        funcoes['GCC'] = 'get_GCC'
        funcoes['GTO_LOA'] = 'get_GTO_LOA'
        funcoes['fGPE'] = 'get_fGPE'
        funcoes['fGTO'] = 'get_fGTO'
        funcoes['fGOC'] = 'get_fGOC'
        funcoes['fGCI'] = 'get_fGCI'
        funcoes['fGCO'] = 'get_fGCO'
        for nome_variavel, funcao in funcoes.items():
            variavel = {}
            variavel['nome'] = nome_variavel
            qs = getattr(Variavel, f'{funcao}_qs')(campus, ano)
            itens = []
            if qs:
                for sublist in qs:
                    if hasattr(sublist, 'all'):
                        for val in sublist:
                            item = dict()
                            item["numero"] = val
                            item["valor"] = val.get_valor()
                            if isinstance(val, DocumentoEmpenho):
                                item["valor"] = val.get_valor_liquidado()
                            itens.append(item)
                    elif isinstance(sublist, list):
                        item = dict()
                        item["numero"] = sublist[0]
                        item["valor"] = sublist[1]
                        itens.append(item)
                    else:
                        item = dict()
                        item["numero"] = sublist
                        item["valor"] = sublist.get_valor()
                        itens.append(item)

            variavel['itens'] = itens
            variavel['valor'] = getattr(Variavel, funcao)(campus, ano)
            variaveis.append(variavel)

    return locals()


@rtr()
@group_required('Gestor do Tesouro Gerencial')
def campi(request):
    title = 'Relatório de Campi por Variável'
    form = CampiFom(request.GET or None)
    campi = list()
    if form.is_valid():
        variavel = form.cleaned_data.get('variavel')
        ano = form.cleaned_data.get('ano')
        funcoes = OrderedDict()
        funcoes['DEST_EXEC'] = 'get_DEST_EXEC'
        funcoes['LOA_EXEC'] = 'get_LOA_EXEC'
        funcoes['RECCAPT'] = 'get_RECCAPT'
        funcoes['20RL_LOA'] = 'get_20RL_LOA'
        funcoes['GCC'] = 'get_GCC'
        funcoes['GTO_LOA'] = 'get_GTO_LOA'
        funcoes['fGPE'] = 'get_fGPE'
        funcoes['fGTO'] = 'get_fGTO'
        funcoes['fGOC'] = 'get_fGOC'
        funcoes['fGCI'] = 'get_fGCI'
        funcoes['fGCO'] = 'get_fGCO'
        for campus in UnidadeOrganizacional.objects.uo().order_by('codigo_ugr'):
            campus_dict = {}
            campus_dict['nome'] = "{} {}".format(campus.codigo_ugr, campus.nome)
            qs = getattr(Variavel, f'{funcoes[variavel]}_qs')(campus, ano)
            itens = []
            if qs:
                for sublist in qs:
                    if hasattr(sublist, 'all'):
                        for val in sublist:
                            item = dict()
                            item["numero"] = val
                            item["valor"] = val.get_valor()
                            if isinstance(val, DocumentoEmpenho):
                                item["valor"] = val.get_valor_liquidado()
                            itens.append(item)
                    elif isinstance(sublist, list):
                        item = dict()
                        item["numero"] = sublist[0]
                        item["valor"] = sublist[1]
                        itens.append(item)
                    else:
                        item = dict()
                        item["numero"] = sublist
                        item["valor"] = sublist.get_valor()
                        itens.append(item)

            campus_dict['itens'] = itens
            campus_dict['valor'] = getattr(Variavel, funcoes[variavel])(campus, ano)
            campi.append(campus_dict)

    return locals()


@rtr()
@group_required('Gestor do Tesouro Gerencial')
def importacao(request):
    title = 'Importação dos dados do Tesouro Gerencial'
    form = ImportacaoTesouroGerencial(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.processar()
        return httprr('.', 'Dados importados com sucesso.')
    return locals()
