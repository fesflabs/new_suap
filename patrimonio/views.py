import io
import json
from datetime import datetime, timedelta, date
from decimal import Decimal

import qrcode
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum, Count, OuterRef, Exists
from django.dispatch import receiver
from django.http import HttpResponse, Http404
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from djtools.utils.response import render_to_string
from django.views.decorators.csrf import csrf_exempt

from comum.models import Sala, Configuracao
from comum.utils import get_uo, somar_data, data_normal, OPERADOR_ALMOXARIFADO_OU_PATRIMONIO, OPERADOR_PATRIMONIO
from djtools import layout
from djtools.templatetags.filters import format_datetime
from djtools.utils import rtr, render, httprr, group_required, to_ascii, permission_required, generate_autocomplete_dict, calendario
from djtools.utils import send_mail
from patrimonio import tasks
from patrimonio.forms import (
    FormTotalizacaoEdPeriodo,
    InventarioBuscaFormFactory,
    CargaFiltroForm,
    CautelaInventarioForm,
    InventariosEditarEmLoteFormFactory,
    InventarioEditarFormFactory,
    BaixaFormFactory,
    ServidorCargaFormFactory,
    CargaFormFactory,
    BaixaInventarioFormFactory,
    RequisicaoInventarioUsoPessoalForm,
    FotoInventarioForm,
    RequisicaoTransferenciaForm,
    IndeferirRequisicaoForm,
    DeferirRequisicaoForm,
    AvaliarInventariosForm,
    ReavaliacaoInventarioForm,
    AjusteInventarioForm,
    InformarPAOrigemForm,
    EdicaoPAOrigemForm,
    InformarPADestinoForm,
    EdicaoPADestinoForm,
    InconsistenciaFormFactory,
    RequisicaoTransferenciaColetorFormFactory,
    CampusFiltroInconsistenteForm,
)
from patrimonio.models import (
    FotoInventario,
    Inventario,
    InventarioRotulo,
    Baixa,
    Cautela,
    CautelaInventario,
    MovimentoPatrim,
    Requisicao,
    DescricaoInventario,
    InventarioTipoUsoPessoal,
    RequisicaoInventarioUsoPessoal,
    ConferenciaSala,
    ConferenciaItem,
    InventarioReavaliacao,
    RequisicaoHistorico,
    EntradaPermanente,
    RequisicaoItem,
    InventarioValor)
from patrimonio.relatorio import totalizacaoCategoriaPeriodo, totalizacaoPlanoContasPeriodo
from rh.models import UnidadeOrganizacional, Servidor
from rh.views import rh_servidor_view_tab


@layout.info()
def index_infos(request):
    infos = list()

    # Inventário de Uso pessoal (netbooks, notebooks, entre outros cedidos pela instituição)
    inventarios_uso_pessoal = RequisicaoInventarioUsoPessoal.tipos_uso_pessoal_permitidos(request.user)
    for invs in inventarios_uso_pessoal:
        infos.append(dict(url='patrimonio/requisicao_inventario_uso_pessoal/{}'.format(invs.pk), titulo='Requisitar {}.'.format(invs.descricao)))

    return infos


@layout.alerta()
def index_alertas(request):
    alertas = list()
    uo = get_uo(request.user)
    if request.user.groups.filter(name__in=['Operador de Patrimônio', 'Coordenador de Patrimônio', 'Coordenador de Patrimônio Sistêmico']).exists():
        if request.user.has_perm('patrimonio.pode_alterar_carga_contabil_do_campus') and Inventario.get_carga_contabil_inconsistentes(request.user).exists():
            alertas.append(
                dict(url='/patrimonio/listar_inventarios_carga_contabil_inconsistentes/', titulo='Há inventário(s) com carga contábil diferente do campus do responsável.')
            )
        if Inventario.get_pendentes(uo=uo).exists():
            alertas.append(dict(url='/patrimonio/inventarios_pendentes/', titulo='Há inventário(s) sem carga.'))
        if Inventario.existe_servidores_inativos_com_carga(uo=uo):
            alertas.append(dict(url='/patrimonio/servidores_com_carga/?ativos=3&com_funcao=1&unidade_organizacional={}'.format(uo.id), titulo='Há servidores inativos com carga.'))

    return alertas


@layout.quadro('Patrimônio', icone='building')
def index_quadros(quadro, request):

    if request.user.has_perm('comum.is_coordenador_de_patrimonio'):
        requisicoes_campus_aguardando_destino = Requisicao.get_requisicoes_campus_aguardando_destino(request.user)
        if requisicoes_campus_aguardando_destino.exists():
            qtd = requisicoes_campus_aguardando_destino.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Requisiç{pluralize(qtd, "ão,ões")} de Transferência',
                    subtitulo='Aguardando aprovação',
                    qtd=qtd,
                    url='/admin/patrimonio/requisicao/?campus_origem__id__exact={}&status__exact=1'.format(get_uo(request.user).pk),
                )
            )

    if request.user.eh_servidor:
        requisicoes_aguardando_aprovacao_servidor = Requisicao.get_aguardando_aprovacao_servidor(request.user)
        if requisicoes_aguardando_aprovacao_servidor.exists():
            qtd = requisicoes_aguardando_aprovacao_servidor.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Requisiç{pluralize(qtd, "ão,ões")} de Transferência',
                    subtitulo='Aguardando sua aprovação',
                    qtd=qtd,
                    url='/admin/patrimonio/requisicao/?tab=tab_aguardando_aprovacao_servidor',
                )
            )

        if request.user.has_perm('comum.is_contador_de_patrimonio'):
            requisicoes_aguardando_informacao_pa_origem = Requisicao.get_qs_aguardando_informacao_pa_origem(request.user)
            requisicoes_aguardando_informacao_pa_destino = Requisicao.get_qs_aguardando_informacao_pa_destino(request.user)
            if requisicoes_aguardando_informacao_pa_origem.exists():
                qtd = requisicoes_aguardando_informacao_pa_origem.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Requisiç{pluralize(qtd, "ão,ões")} de Transferência',
                        subtitulo='Aguardando PA Campus Origem',
                        qtd=qtd,
                        url='/admin/patrimonio/requisicao/?tab=tab_aguardando_informacao_pa_origem',
                    )
                )

            if requisicoes_aguardando_informacao_pa_destino.exists():
                qtd = requisicoes_aguardando_informacao_pa_destino.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Requisiç{pluralize(qtd, "ão,ões")} de Transferência',
                        subtitulo='Aguardando PA Campus Destino',
                        qtd=qtd,
                        url='/admin/patrimonio/requisicao/?tab=tab_aguardando_informacao_pa_destino',
                    )
                )

    return quadro


@rtr()
@group_required(OPERADOR_PATRIMONIO)
def carga(request):
    title = 'Criar Requisição de Carga de Inventários Pendentes'
    FormClass = CargaFormFactory(request)
    form_carga = FormClass(request.POST or None)
    if form_carga.is_valid():
        form_carga.save()
        return httprr('.', 'Requisição criada com sucesso!')

    inventarios = None
    if request.GET:
        form_filtro = CargaFiltroForm(request.GET)
        if form_filtro.is_valid():
            inventarios = Inventario.get_pendentes(uo=form_filtro.cleaned_data['campus'])
            for descricao in form_filtro.cleaned_data['descricao'].replace("'", " ").split():
                inventarios = inventarios.filter(descricao__unaccent__icontains=descricao)
        elif form_filtro.is_bound:
            inventarios = Inventario.pendentes.all()
            form_filtro = CargaFiltroForm()
    else:
        uo_user = get_uo()
        inventarios = Inventario.get_pendentes(uo=uo_user)

        form_filtro = CargaFiltroForm({"campus": uo_user.id})

    inventarios = inventarios.select_related('entrada_permanente', 'entrada_permanente__categoria', 'entrada_permanente__entrada__uo')

    requisicoes = Requisicao.get_qs_aguardando().filter(itens__inventario__id=OuterRef('id'))
    inventarios = inventarios.annotate(requisicoes=Exists(requisicoes)).filter(requisicoes=False)

    inventarios_ids = [int(i) for i in request.POST.getlist('inventarios')]
    return locals()


@login_required
def exibir_inventarios_pendentes(request):
    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        return HttpResponseRedirect('/patrimonio/carga/?descricao=&campus=%s' % servidor.campus.id)

    raise PermissionDenied()


###########
# BAIXA   #
###########
@rtr()
@group_required(OPERADOR_PATRIMONIO)
def baixa(request, baixa_pk):
    """
    Tela para efetuar baixas
    """
    baixa = get_object_or_404(Baixa, pk=baixa_pk)
    itens = baixa.movimentopatrim_set.order_by('inventario__numero')
    resumo_ed = baixa.get_total_categoria()
    valor_total_inicial = baixa.get_valor_inicial()
    valor_total = baixa.get_valor()

    FormClass = BaixaInventarioFormFactory(request.user)
    form = FormClass(request.POST or None)

    if form.is_valid():
        if form.cleaned_data['tipo_baixa'] == 'inventario':
            Inventario.efetuar_baixa(baixa=baixa, inventarios=form.cleaned_data['inventario'])
            return httprr('.', 'Baixa efetuada com sucesso.')
        elif form.cleaned_data['tipo_baixa'] == 'rotulo':
            inventarios = Inventario.objects.filter(rotulos=form.cleaned_data['rotulo'])
            for inventario in inventarios:
                Inventario.efetuar_baixa(inventarios=inventario, baixa=baixa)
            return httprr('.', 'Baixa efetuada com sucesso.')
        elif form.cleaned_data['tipo_baixa'] == 'faixa':
            for inventario in form.cleaned_data['faixa']:
                Inventario.efetuar_baixa(inventarios=inventario, baixa=baixa)
            return httprr('.', 'Baixa efetuada com sucesso.')
    return locals()


@rtr('patrimonio/templates/baixa_adicionar.html')
@group_required(OPERADOR_PATRIMONIO)
def baixa_adicionar(request):
    """Tela para cadastrar baixas
    Redireciona para a tela da baixa cadastrada.
    """
    FormClass = BaixaFormFactory(get_uo(request.user))
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            baixa = Baixa.objects.create(
                tipo=form.cleaned_data['tipo'],
                data=form.cleaned_data['data'],
                numero=form.cleaned_data['numero'],
                observacao=form.cleaned_data['observacao'],
                processo=form.cleaned_data['processo'],
                uo=form.cleaned_data['uo'],
            )
            return httprr(url='/patrimonio/baixa/%s/' % (baixa.pk))
    else:
        form = FormClass()
    return locals()


@rtr('patrimonio/templates/baixa_editar.html')
@group_required(OPERADOR_PATRIMONIO)
def baixa_editar(request, baixa_pk):
    """
    Tela para editar baixas
    """
    baixa = get_object_or_404(Baixa, pk=baixa_pk)

    # campus do usuário logado
    uo = get_uo(request.user)

    # não permite alterar baixas que não são do seu campus
    if uo.id != baixa.uo_id:
        return httprr('/admin/patrimonio/baixa/', 'Você não pode editar baixas que não são do seu campus.', 'error')

    FormClass = BaixaFormFactory(uo, instance=baixa)
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            baixa.tipo = form.cleaned_data['tipo']
            baixa.data = form.cleaned_data['data']
            baixa.numero = form.cleaned_data['numero']
            baixa.observacao = form.cleaned_data['observacao']
            baixa.processo = form.cleaned_data['processo']
            baixa.uo = form.cleaned_data['uo']
            baixa.save()
            return httprr('/admin/patrimonio/baixa/', 'Baixa editada com sucesso')
    else:
        form = FormClass()
    return locals()


@rtr()
def baixa_remover(request, baixa_pk):
    baixa = get_object_or_404(Baixa, pk=baixa_pk)

    # campus do usuário logado
    uo = get_uo(request.user)

    # não permite alterar baixas que não são do seu campus
    if uo.id != baixa.uo_id:
        return httprr('/patrimonio/baixa/%s/' % baixa_pk, 'Você não pode excluir baixas que não são do seu campus.', 'error')

    baixa.delete()
    return httprr('/admin/patrimonio/baixa/', 'Baixa removida com sucesso')


@rtr()
@permission_required('patrimonio.delete_baixa')
def baixa_remover_item(request, baixa_pk, movimentopatrim_pk):
    baixa = Baixa.objects.get(id=baixa_pk)
    baixa.delete_item(movimentopatrim_pk)
    return httprr('/patrimonio/baixa/%s/' % (baixa_pk), 'Item de Baixa removida com sucesso')


###############
# INVENTÁRIOS #
###############


def filtrar_inventarios(dados):
    """
    Realiza o filter do queryset que retorna o resultado da busca de inventários por
    meio do InventarioBuscaForm.
    """
    numero = dados.get('numero')
    valor = dados.get('valor')
    descricao = dados.get('descricao')
    status = dados.get('status')
    rotulo = dados.get('rotulos')
    sala = dados.get('sala')
    campus_sala = dados.get('campus_sala')
    responsavel = dados.get('responsavel')
    setor = dados.get('setor_responsavel')
    recursivo = dados.get('recursivo')
    data_final = dados.get('data_final')
    campus = dados.get('campus')
    data_inicial = dados.get('data_inicial')
    fornecedor = dados.get('fornecedor')
    numero_serie = dados.get('numero_serie')
    elemento_despesa = dados.get('elemento_despesa')
    estado_conservacao = dados.get('estado_conservacao')
    numero_transferencia = dados.get('numero_transferencia')

    inventarios = Inventario.objects.all()

    if numero:
        if '-' in numero:
            faixa = numero.split('-')
            a = int(faixa[0])
            b = int(faixa[1])
            if a < b:
                inventarios = inventarios.filter(numero__gte=a, numero__lte=b)
            else:
                inventarios = inventarios.filter(numero__gte=b, numero__lte=a)
        elif ',' in numero:
            faixa = numero.split(',')
            inventarios = inventarios.filter(numero__in=faixa)
        else:
            inventarios = inventarios.filter(numero=numero)

    if valor:
        valor = valor.replace(',', '.')
        if valor.count('=') == 1:
            valor = valor.replace('=', '')
            valor_em_decimal = None
            try:
                valor_em_decimal = Decimal(valor[1:])
            except Exception:
                pass
            if valor_em_decimal and '<' in valor:
                inventarios = inventarios.filter(valor__lte=valor_em_decimal)
            elif valor_em_decimal and '>' in valor:
                inventarios = inventarios.filter(valor__gte=valor_em_decimal)
        else:
            valor_em_decimal = None
            try:
                valor_em_decimal = Decimal(valor[1:])
            except Exception:
                pass
            if valor_em_decimal and '<' in valor:
                inventarios = inventarios.filter(valor__lt=valor_em_decimal)
            elif valor_em_decimal and '>' in valor:
                inventarios = inventarios.filter(valor__gt=valor_em_decimal)
            else:
                try:
                    inventarios = inventarios.filter(valor=Decimal(valor))
                except Exception:
                    pass

    if descricao:
        tokens = descricao.split()
        for token in tokens:
            inventarios = inventarios.filter(campo_busca__icontains=token)

    if status:
        inventarios = inventarios.filter(status=status)
    if rotulo:
        inventarios = inventarios.filter(rotulos=rotulo)
    if numero_serie:
        inventarios = inventarios.filter(numero_serie__icontains=numero_serie)
    if elemento_despesa:
        inventarios = inventarios.filter(entrada_permanente__categoria=elemento_despesa)
    if numero_transferencia:
        inventarios = inventarios.filter(id__in=RequisicaoItem.objects.filter(requisicao__id=numero_transferencia).values_list('inventario__id', flat=True))
    if sala:
        inventarios = inventarios.filter(sala=sala)
    if campus_sala:
        sala_uo = Sala.ativas.filter(predio__uo=campus_sala)
        if sala_uo:
            inventarios = inventarios.filter(responsavel_vinculo__setor__uo=campus_sala)
    if responsavel:
        inventarios = inventarios.filter(responsavel_vinculo=responsavel.get_vinculo())

    if setor:
        if recursivo:
            id_setor_pai = setor.id
            lista_ids_setores_descendentes = [id_setor for id_setor in setor.ids_descendentes]
            filtro_recursivo = [id_setor_pai] + lista_ids_setores_descendentes
            inventarios = inventarios.filter(responsavel_vinculo__setor__id__in=filtro_recursivo)
        else:
            inventarios = inventarios.filter(responsavel_vinculo__setor=setor)
    if campus:
        inventarios = inventarios.filter(carga_contabil__campus=campus)

    if data_inicial:
        inventarios = inventarios.filter(entrada_permanente__entrada__data__gte=data_inicial)
    if data_final:
        inventarios = inventarios.filter(entrada_permanente__entrada__data__lte=data_final)
    if fornecedor:
        inventarios = inventarios.filter(entrada_permanente__entrada__vinculo_fornecedor=fornecedor.get_vinculo())

    if estado_conservacao:
        inventarios = inventarios.filter(estado_conservacao=estado_conservacao)

    inventarios = inventarios.order_by('numero')

    return inventarios


@rtr()
def inventario_busca(request):
    """
    Exibe e processa o Form de busca de inventários.
    Exporta resultados da busca para formatos XLS e CSV.
    Aplica rótulo, sala e estado de conservação a inventários selecionados da
    listagem de resultados retornada da busca.

    """
    title = 'Busca de Inventários'

    if not request.user.has_perm('patrimonio.ver_inventarios') and not request.user.has_perm('patrimonio.pode_ver_propria_carga'):
        raise PermissionDenied()

    user_pode_editar = request.user.has_perm('patrimonio.editar_todos') or request.user.has_perm('patrimonio.editar_do_meu_campus')

    FormClass = InventarioBuscaFormFactory(request.user)
    form = FormClass(request.GET or None)
    if form.is_valid():
        inventarios = filtrar_inventarios(form.cleaned_data)
        url_base = request.path + '?' + request.GET.urlencode()
        url_csv = url_base + '&format=csv'
        url_xls = url_base + '&format=xls'
        if request.method == "GET":
            formato = request.GET.get('format')
            if formato in ['xls', 'csv']:
                return tasks.inventario_dados_exportacao(inventarios, formato)

        ver_sala = form.cleaned_data['ver_sala']
        ver_responsavel = form.cleaned_data['ver_responsavel']
        ver_elemento_despesa = form.cleaned_data['ver_elemento_despesa']
        ver_situacao = form.cleaned_data['ver_situacao']
        ver_rotulo = form.cleaned_data['ver_rotulo']
        ver_numeroserie = form.cleaned_data['ver_numeroserie']
        ver_estado_conservacao = form.cleaned_data['ver_estado_conservacao']
        ver_data_entrada = form.cleaned_data['ver_data_entrada']
        ver_data_carga = form.cleaned_data['ver_data_carga']
        ver_fornecedor = form.cleaned_data['ver_fornecedor']
        ver_valor = form.cleaned_data['ver_valor']
        ver_valor_inicial = form.cleaned_data['ver_valor_inicial']
        ver_ultima_requisicao = form.cleaned_data['ver_ultima_requisicao']
        ver_ultima_conferencia = form.cleaned_data['ver_ultima_conferencia']
        try:
            opcao_visualizacao = int(form.cleaned_data['opcoes_visualizacao'])
        except Exception:
            opcao_visualizacao = 50

        form_edicao_lote = None
        if request.user.has_perm('patrimonio.editar_todos') and form.cleaned_data['campus']:
            form_edicao_lote = True
        elif request.user.has_perm('patrimonio.editar_do_meu_campus') and get_uo() == form.cleaned_data['campus']:
            form_edicao_lote = True
        if form_edicao_lote:
            campus = form.cleaned_data['campus']
            FormClass = InventariosEditarEmLoteFormFactory(campus=campus)
            form_rotulo_sala = FormClass(auto_id='%s_id')
    return locals()


@rtr()
@transaction.atomic()
def inventario_editar(request, inventario_id):
    # Checando se o usuário pode ver esta view
    if not request.user.has_perm('patrimonio.ver_inventarios') and not request.user.has_perm('patrimonio.pode_ver_propria_carga'):
        raise PermissionDenied()

    inventario = get_object_or_404(Inventario, pk=inventario_id)
    title = 'Inventário {}'.format(inventario.numero)

    if inventario.responsavel_vinculo and inventario.responsavel_vinculo.user != request.user and not request.user.has_perm('patrimonio.ver_inventarios'):
        raise PermissionDenied()

    if inventario.user_pode_editar():
        FormClass = InventarioEditarFormFactory(request.user, instance=inventario)
        if request.method == 'POST':
            form = FormClass(request.POST, instance=inventario)
            if form.is_valid():
                form.save()
                if 'elemento_despesa' in form.changed_data:
                    entrada_permanente = EntradaPermanente.objects.get(id=inventario.entrada_permanente.id)
                    entrada_permanente.categoria = form.cleaned_data['elemento_despesa']
                    entrada_permanente.save()
                if 'descricao' in form.changed_data:
                    DescricaoInventario.objects.create(inventario=inventario, descricao=form.cleaned_data['descricao'])

                return httprr('/patrimonio/inventario/{}/'.format(inventario.numero), 'Inventário salvo com sucesso.')
        else:
            form = FormClass(instance=inventario)

    return locals()


@rtr()
@login_required()
def inventario(request, inventario_numero):
    inventario = get_object_or_404(Inventario, numero=inventario_numero)
    title = f'Inventário {inventario.numero}'
    historico_requisicao = Requisicao.objects.filter(itens__inventario=inventario).order_by('-id')
    reavaliacao = InventarioReavaliacao.objects.filter(inventario=inventario).order_by('data')
    depreciacao = InventarioValor.objects.filter(inventario=inventario).order_by('data')
    percentual_residual = int(inventario.entrada_permanente.categoria.percentual_residual * 100)

    return locals()


def inventario_adicionar_rotulo_sala(request):
    try:
        rotulo_id = request.POST['rotulo'].strip('[').strip(']')
        if rotulo_id:
            rotulo = InventarioRotulo.objects.get(id=int(rotulo_id))
        else:
            rotulo = None
    except (InventarioRotulo.DoesNotExist, KeyError):
        rotulo = None

    try:
        sala_id = request.POST['sala'].strip('[').strip(']')
        if sala_id:
            sala = Sala.objects.get(id=int(sala_id))
        else:
            sala = None
    except (Sala.DoesNotExist, KeyError):
        sala = None

    conservacao = None
    if 'conservacao' in request.POST:
        conservacao = request.POST['conservacao'].strip('[').strip(']')
    remove_rotulo = None
    if 'exclusao_rotulo' in request.POST:
        remove_rotulo = request.POST['exclusao_rotulo'].strip('[').strip(']')

    ids_inventarios = request.POST.getlist('marcados')
    inventarios = [Inventario.objects.get(id=i) for i in ids_inventarios]

    uso_pessoal = None
    if 'tipo_uso_pessoal' in request.POST and request.POST['tipo_uso_pessoal']:
        uso_pessoal = InventarioTipoUsoPessoal.objects.get(pk=request.POST['tipo_uso_pessoal'])

    msg = 'Modificações realizadas com sucesso.'
    fotos = None
    if request.FILES:
        fotos = request.FILES.getlist('fotos')
    for inventario in inventarios:
        if rotulo:
            inventario.rotulos.add(rotulo)
        if remove_rotulo:
            for r in inventario.rotulos.all():
                inventario.rotulos.remove(r)
        if sala:
            inventario.sala = sala
        if conservacao:
            inventario.estado_conservacao = conservacao

        if uso_pessoal:
            inventario.tipo_uso_pessoal = uso_pessoal
        if fotos:
            if not request.POST['descricao_fotos'] or not request.POST['data_fotos']:
                return httprr(request.META.get('HTTP_REFERER', '..'), 'Informe a descrição e a data das fotos', tag='error')

            for foto in fotos:
                nova_foto = FotoInventario()
                nova_foto.inventario = inventario
                nova_foto.descricao = request.POST['descricao_fotos']
                nova_foto.data = request.POST['data_fotos']
                nova_foto.foto = foto
                nova_foto.save()

        inventario.save()
    return httprr(request.META.get('HTTP_REFERER', '/patrimonio/inventario_busca/'), msg)


###
# Servidores
###


@rtr()
@group_required(OPERADOR_PATRIMONIO)
def servidores_com_carga(request):
    """
    Exibe tela com filtros para a busca.
    Exibe resultados separados por campus.

    """
    title = 'Servidores com carga'
    servidores = Inventario.get_servidores_com_carga(ativo=None, tem_funcao=None, uo=get_uo(request.user))
    FormClass = ServidorCargaFormFactory(request.user)
    if request.GET:
        form = FormClass(request.GET)
        if form.is_valid():
            ativo = form.cleaned_data['ativos']
            tem_funcao = form.cleaned_data['com_funcao']
            unidade_organizacional = request.GET['unidade_organizacional']
            servidores = Inventario.get_servidores_com_carga(ativo=ativo, tem_funcao=tem_funcao, uo=unidade_organizacional)
    else:
        form = FormClass()
    lista_campus = []
    ids_campus = {s.setor.uo.id for s in servidores if s.setor and s.setor.uo}
    for id_campus in ids_campus:
        campus = dict()
        campus['nome_campus'] = str(UnidadeOrganizacional.objects.suap().get(id=id_campus))
        campus['servidores'] = servidores.filter(setor__uo__id=id_campus)
        lista_campus.append(campus)
    serv_nenhum = servidores.filter(setor__uo__isnull=True)
    if serv_nenhum:
        lista_campus.append({'nome_campus': 'Nenhum', 'servidores': servidores.filter(setor__uo__isnull=True)})
    return locals()


###
# Cautela
###


@rtr()
@group_required(OPERADOR_PATRIMONIO)
def cautela(request, cautela_pk):
    """Tela de detalhes da cautela, com opções para adicionar itens."""
    cautela = Cautela.objects.get(pk=cautela_pk)

    link_editar = "/admin/patrimonio/cautela/%d/change/" % cautela.id

    if request.method == 'POST':
        form = CautelaInventarioForm(request.POST)
        form.instance.cautela = cautela
        if form.is_valid():
            form.save()
            return httprr('.', 'Item da Cautela cadastrado com sucesso.')
    else:
        form = CautelaInventarioForm()

    return locals()


def cautelainventario_remover(request, id_cautelainventario):
    cautelainventario = CautelaInventario.objects.select_related('inventario').get(id=id_cautelainventario)
    cautelainventario.delete()
    return httprr(cautelainventario.cautela.get_absolute_url(), 'Item removido com sucesso!')


@rtr()
@group_required(OPERADOR_PATRIMONIO)
def cautela_adicionar(request):
    title = 'Efetuar Cautela'
    if request.method == 'POST':
        form = CautelaInventarioForm(request.POST)
        if form.is_valid():
            cautela = Cautela(
                responsavel=str(form.cleaned_data['responsavel']),
                data_inicio=form.cleaned_data['data_inicio'],
                data_fim=form.cleaned_data['data_fim'],
                descricao=form.cleaned_data['descricao'],
            )
            cautela.save()
            for inventario in form.cleaned_data['inventarios']:
                cautela_inventario = CautelaInventario(inventario=inventario, cautela=cautela)
                cautela_inventario.save()
            msg = 'Cautela efetuada com sucesso.'
            return httprr('/admin/patrimonio/cautela/', msg)
    else:
        form = CautelaInventarioForm()
    return locals()


@rtr()
@group_required(OPERADOR_PATRIMONIO)
def tela_cautela_detalhe(request, cautela_id):
    cautela = Cautela.objects.get(id=cautela_id)
    ci = CautelaInventario.objects.filter(cautela=cautela)
    objeto = {}
    resposta = []
    for i in ci:
        objeto['numero'] = i.inventario.numero
        objeto['descricao'] = i.inventario.entrada_permanente.descricao
        resposta.append(objeto)
        objeto = {}
    return dict(resposta=resposta, cautela=cautela)


###
# Relatórios
###


@group_required(OPERADOR_ALMOXARIFADO_OU_PATRIMONIO)
@rtr()
def totalizacao_ed_periodo(request):
    title = 'Totalização por Elemento de Despesa por Período de Entrada'
    form = FormTotalizacaoEdPeriodo(request.GET or None)
    if form.is_valid():
        resposta, total = totalizacaoCategoriaPeriodo(form.cleaned_data['ano'], int(form.cleaned_data['mes']), form.cleaned_data['doacoes'])
        request.session['resposta'] = {
            'resposta': resposta,
            'total': total,
            'ano': form.cleaned_data['ano'],
            'mes': calendario.getNomeMes(int(form.cleaned_data['mes'])),
            'doacoes_inclusas': form.cleaned_data['doacoes'],
        }
        return render('patrimonio/templates/relatorio/totalizacao_ed_Periodo.html', request.session['resposta'])
    else:
        return locals()


@group_required(OPERADOR_PATRIMONIO)
def telarelatoriobaixa(request):
    return render('patrimonio/templates/relatorio/baixa.html', {})


# O relatório a seguir apresenta as movimentações patrimoniais agrupadas por data e responsável.
# Serão exibidos apenas as movimentações ocorridas nos últimos sete dias (de movimentação efetiva) anteriores à data limite.
@rtr()
def inventarios_cargas(request):
    movimentos = []
    limite_inferior = datetime.today()
    limite_superior = datetime.today()

    if 'limite' in request.GET:
        limite_inferior = datetime.strptime(request.GET['limite_inferior'], '%d/%m/%Y')
        limite_superior = datetime.strptime(request.GET['limite_superior'], '%d/%m/%Y')
        if request.GET['limite'] == 'superior':
            datas = MovimentoPatrim.objects.filter(vinculo__isnull=False, data__gt=limite_superior).dates('data', 'day', order='DESC')[:7]
        else:
            datas = MovimentoPatrim.objects.filter(vinculo__isnull=False, data__lt=limite_inferior).dates('data', 'day', order='DESC')[:7]
    else:
        datas = MovimentoPatrim.objects.filter(vinculo__isnull=False).dates('data', 'day', order='DESC')[:7]

    for dia in datas:
        depois = dia + timedelta(days=1)
        registros = MovimentoPatrim.objects.filter(vinculo__isnull=False, data__gt=dia, data__lt=depois).order_by('-data', 'vinculo')[:5]
        for registro in registros:
            movimentos.append(registro)

    if len(datas) > 0:
        limite_superior = datas[0]  # primeira data da lista
    if len(datas) > 1:
        limite_inferior = datas[len(datas) - 1]  # ultima data da lista
    if len(datas) == 1:
        limite_inferior = limite_superior

    # formata os objetos do tipo data para string
    limite_inferior = data_normal(limite_inferior)
    limite_superior_mais_um = data_normal(somar_data(limite_superior, 1))
    limite_superior = data_normal(limite_superior)

    return render(
        'patrimonio/templates/inventarios_carga.html',
        {'movimentos': movimentos, 'limite_superior': limite_superior, 'limite_superior_mais_um': limite_superior_mais_um, 'limite_inferior': limite_inferior},
    )


@rtr()
def adicionar_foto_inventario(request, inventario_id):
    title = "Adicionar foto"
    inventario = Inventario.objects.get(id=inventario_id)
    form = FotoInventarioForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        i = form.save(False)
        i.inventario = inventario
        i.save()
        return httprr('..', 'Foto adicionada com sucesso')

    return locals()


def remover_foto_inventario(request, inventario_numero, foto_id):
    fotoinventario = FotoInventario.objects.filter(id=foto_id).first()
    if fotoinventario is None:
        return httprr("/patrimonio/inventario/{}/".format(inventario_numero), "Foto não localizada.", 'error')
    else:
        fotoinventario.delete()
        return httprr("/patrimonio/inventario/{}/".format(inventario_numero), "Foto removida com sucesso.")


def visualizar_foto_inventario(request, foto_id):
    fotoinventario = FotoInventario.objects.get(pk=foto_id)
    return HttpResponse(fotoinventario.foto.read(), content_type="image/png")


def requisicao_enviar_email(requisicao):
    titulo = "[SUAP] Comprovante de Inscrição para Recebimento de {} (Matrícula: {})".format(requisicao.tipo_uso_pessoal.descricao, requisicao.vinculo.relacionamento.matricula)
    texto = '''
        <h1>Patrimônio</h1>
        <p>A inscrição do servidor {}, matrícula {}, foi realizada com sucesso.</p>
        <dl>
            <dt>Item Solicitado:</dt><dd>{}</dd>
            <dt>Data/Hora da Inscrição:</dt><dd>{}</dd>
        </dl>'''.format(
        requisicao.vinculo.pessoa.nome,
        requisicao.vinculo.relacionamento.matricula,
        requisicao.tipo_uso_pessoal.descricao,
        calendario.datetimeToStr(requisicao.horario),
    )

    email_destino = [requisicao.vinculo.pessoa.email]

    # enviar e-mail com cópia?
    if len(requisicao.tipo_uso_pessoal.enviar_email_copia) > 0:
        email_destino.append(requisicao.tipo_uso_pessoal.enviar_email_copia)

    return send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, email_destino)


@login_required()
@rtr()
def requisicao_inventario_uso_pessoal(request, pk):
    # verifica novamente se usuário logado tem permissão (ou se já respondeu a requisição)
    if int(pk) in RequisicaoInventarioUsoPessoal.tipos_uso_pessoal_permitidos(request.user).values_list('pk', flat=True):
        tipo_uso_pessoal = InventarioTipoUsoPessoal.objects.get(pk=pk)
        form = RequisicaoInventarioUsoPessoalForm(request.POST or None)
        if form.is_valid():
            if form.cleaned_data['confirmacao']:
                r = RequisicaoInventarioUsoPessoal()
                r.vinculo = request.user.get_vinculo()
                r.tipo_uso_pessoal = tipo_uso_pessoal
                r.save()

                # envia e-mail
                if r.tipo_uso_pessoal.enviar_email_inscrito:
                    requisicao_enviar_email(r)

                return httprr(
                    '/patrimonio/requisicao_inventario_uso_pessoal_listar/',
                    'Requisição cadastrada com sucesso. Acesse Administração -> Patrimônio -> ' 'Requisição de Equipamentos para acompanhar.',
                )
            else:
                return httprr('/', 'A sua requisição não foi cadastrada.')

        return locals()


@rtr()
@login_required()
def requisicao_inventario_uso_pessoal_listar(request):
    title = 'Requisições de Equipamentos'
    requisicoes = RequisicaoInventarioUsoPessoal.objects.filter(vinculo=request.user.get_vinculo())

    return locals()


@rtr()
@login_required()
def remover_rotulo(request, inventario_id, rotulo_id):
    inventario = get_object_or_404(Inventario, pk=inventario_id)
    if not inventario.rotulos.filter(pk=rotulo_id).exists():
        raise Http404

    rotulo = inventario.rotulos.get(pk=rotulo_id)
    inventario.rotulos.remove(rotulo)
    return HttpResponse('Rótulo removido com sucesso.')


@rtr()
@group_required('Operador de Patrimônio, Coordenador de Patrimônio, Coordenador de Patrimônio Sistêmico')
def autorizar_coletor(request, conferencia_id):
    title = 'QRCode para Leitura'
    conferencia = get_object_or_404(ConferenciaSala, pk=conferencia_id)

    return locals()


@group_required('Operador de Patrimônio, Coordenador de Patrimônio, Coordenador de Patrimônio Sistêmico')
def conferencia_visualizar_qrcode(request, conferencia_id):
    conferencia = get_object_or_404(ConferenciaSala, pk=conferencia_id)

    # gerando qrcode
    qrcode_texto = str(conferencia.id) + '|' + to_ascii(conferencia.sala.nome.replace("|", "/")) + '|' + format_datetime(conferencia.dh_criacao) + "|" + conferencia.token
    img = qrcode.make(qrcode_texto)
    fp = io.BytesIO()
    img.save(fp, 'png')

    return HttpResponse(fp.getvalue(), content_type="image/png")


@rtr()
@permission_required('patrimonio.change_conferenciasala')
def conferenciasala(request, conferencia_id):
    title = 'Detalhes da Conferência'
    conferencia = get_object_or_404(ConferenciaSala, pk=conferencia_id)

    conferencias_itens = conferencia.conferenciaitem_set.all()
    q_conferencias = request.GET.get('q_conferencias_itens', '')
    if q_conferencias:
        conferencias_itens = conferencias_itens.filter(inventario__campo_busca__icontains=q_conferencias)
    conferencia_total = conferencias_itens.aggregate(total=Sum('inventario__entrada_permanente__valor'), qtd=Count('inventario'))

    ids = ConferenciaItem.objects.filter(conferencia=conferencia).values_list('inventario', flat=True)
    inventarios_nao_coletados = Inventario.objects.filter(sala=conferencia.sala).exclude(pk__in=ids)
    q_inventarios_nao_coletados = request.GET.get('q_inventarios_nao_coletados', '')
    if q_inventarios_nao_coletados:
        inventarios_nao_coletados = inventarios_nao_coletados.filter(campo_busca__icontains=q_inventarios_nao_coletados)

    inventarios_erros = conferencia.conferenciaitemerro_set.all()
    q_inventarios_erros = request.GET.get('q_inventarios_erros', '')
    if q_inventarios_erros:
        inventarios_erros = inventarios_erros.filter(inventario__icontains=q_inventarios_erros)
    return locals()


@rtr()
@group_required('Operador de Patrimônio, Coordenador de Patrimônio, Coordenador de Patrimônio Sistêmico')
def imprimir_conferencia(request, conferencia_id):
    title = 'Detalhes da Conferência'
    conferencia = get_object_or_404(ConferenciaSala, pk=conferencia_id)
    conferencia_total = conferencia.conferenciaitem_set.aggregate(total=Sum('inventario__entrada_permanente__valor'), qtd=Count('inventario'))

    FormClass = RequisicaoTransferenciaColetorFormFactory(request)
    form_requisicao = FormClass(request.POST or None)
    if form_requisicao.is_valid():
        form_requisicao.save()
        return httprr('/admin/patrimonio/requisicao/', 'Requisição criada com sucesso.')
    ids = ConferenciaItem.objects.filter(conferencia=conferencia).values_list('inventario', flat=True)
    inventarios_nao_coletados = Inventario.objects.filter(sala=conferencia.sala).exclude(pk__in=ids)
    return locals()


@rtr()
@group_required('Coordenador de Patrimônio, Coordenador de Patrimônio Sistêmico')
def reavaliar_inventario(request, inventario_id):
    title = 'Reavaliar Inventário'
    inventario = get_object_or_404(Inventario, pk=inventario_id)
    vida_util_anos_do_inventario = inventario.entrada_permanente.categoria.vida_util_em_anos
    percentual_residual_do_inventario = inventario.entrada_permanente.categoria.percentual_residual
    valor_entrada = inventario.entrada_permanente.valor
    valor_residual = Decimal('%.2f' % (float(valor_entrada) * percentual_residual_do_inventario / 100))
    valor_depreciavel = valor_entrada - valor_residual
    valor_depreciavel_mensal = float(valor_depreciavel) / (vida_util_anos_do_inventario * 12)

    form = ReavaliacaoInventarioForm(request.POST or None, initial={'inventario': inventario})

    if form.is_valid():
        valor_inventario = form.cleaned_data['valor'] + inventario.valor
        InventarioReavaliacao.objects.create(
            percentual_residual=percentual_residual_do_inventario,
            vida_util_em_anos=vida_util_anos_do_inventario,
            inventario_id=inventario.id,
            data=datetime.today(),
            valor=valor_inventario,
            tipo=InventarioReavaliacao.MANUAL_REAVALIACAO,
            motivo=form.cleaned_data['motivo'],
            valor_anterior=Decimal('%.2f' % (inventario.valor)),
        )
        valor_novo = form.cleaned_data['valor'] + inventario.valor
        inventario.valor = valor_novo
        inventario.save()

        return httprr('..', 'Inventário reavaliado com sucesso.')
    return locals()


@rtr()
@group_required('Coordenador de Patrimônio, Coordenador de Patrimônio Sistêmico')
def ajustar_valor_inventario(request, inventario_id):
    title = 'Ajustar Valor Recuperável Inventário'
    inventario = get_object_or_404(Inventario, pk=inventario_id)
    vida_util_anos_do_inventario = inventario.entrada_permanente.categoria.vida_util_em_anos
    percentual_residual_do_inventario = inventario.entrada_permanente.categoria.percentual_residual
    valor_entrada = inventario.entrada_permanente.valor
    valor_residual = Decimal('%.2f' % (float(valor_entrada) * percentual_residual_do_inventario / 100))
    valor_depreciavel = valor_entrada - valor_residual
    valor_depreciavel_mensal = float(valor_depreciavel) / (vida_util_anos_do_inventario * 12)

    form = AjusteInventarioForm(request.POST or None, initial={'inventario': inventario})

    if form.is_valid():
        valor_inventario = inventario.valor - form.cleaned_data['valor']
        InventarioReavaliacao.objects.create(
            percentual_residual=percentual_residual_do_inventario,
            vida_util_em_anos=vida_util_anos_do_inventario,
            inventario_id=inventario.id,
            data=datetime.today(),
            valor=valor_inventario,
            tipo=InventarioReavaliacao.MANUAL_AJUSTE_VALOR_RECUPERAVEL,
            motivo=form.cleaned_data['motivo'],
            valor_anterior=inventario.valor,
        )
        inventario.valor = valor_inventario
        inventario.save()

        return httprr('..', 'Ajuste do valor recuperável realizado com sucesso.')
    return locals()


@rtr()
@login_required
def requisitar_transferencia(request):
    title = 'Requisitar Transferência'
    if not request.user.has_perm('patrimonio.change_requisicao'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = RequisicaoTransferenciaForm(request.POST or None, request=request)
    if form.is_valid():
        form.save()
        return httprr('/admin/patrimonio/requisicao/', 'Requisição de transferência de patrimônio efetuada com sucesso.')
    return locals()


@rtr()
@login_required
def detalhar_requisicao(request, id_requisicao):
    title = f'Requisição de Transferência #{id_requisicao}'
    dia_inicio_bloqueio = Configuracao.get_valor_por_chave('patrimonio', 'dia_inicio_bloqueio')
    requisicao = get_object_or_404(Requisicao, pk=id_requisicao)

    if not requisicao.pode_visualizar():
        return httprr('..', 'Você não tem permissão para visualizar esta Requisição de Transferência.', 'error')

    itens = requisicao.itens.all().order_by('situacao', 'inventario__entrada_permanente__categoria__nome')
    soma_itens = itens.aggregate(total=Sum('inventario__valor'))['total']
    despesas = (
        itens.values(
            'inventario__entrada_permanente__categoria__codigo',
            'inventario__entrada_permanente__categoria__nome',
            'inventario__entrada_permanente__categoria__plano_contas__codigo',
        )
        .annotate(total=Sum('inventario__entrada_permanente__valor'))
        .order_by('inventario__entrada_permanente__categoria__nome')
    )
    total_despesas = despesas.aggregate(total_despesas=Sum('total'))
    historicorequisicao = RequisicaoHistorico.objects.filter(requisicao=requisicao)
    form = AvaliarInventariosForm(request.POST or None, instance=requisicao, request=request)
    form.fields['itens'].queryset = itens
    if form.is_valid():
        form.save()
        return httprr('.', 'Inventários avaliados com sucesso. Para prosseguir, você deve Deferir/Indeferir esta requisição.')

    return locals()


@rtr()
@login_required
def cancelar_requisicao(request, requisicao_id):
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    if not requisicao.pode_cancelar():
        raise PermissionDenied()

    requisicao.cancelar_requisicao(request.user)
    return httprr('..', 'Requisição cancelada com sucesso.')


@rtr()
@login_required
def indeferir_requisicao(request, requisicao_id):
    title = 'Indeferir Requisição'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    if not requisicao.pode_avaliar():
        raise PermissionDenied()

    form = IndeferirRequisicaoForm(request.POST or None, instance=requisicao, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'Requisição indeferida com sucesso.')

    return locals()


@rtr()
@login_required
def deferir_requisicao(request, requisicao_id):
    title = 'Localização dos Itens'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    dia_inicio_bloqueio = Configuracao.get_valor_por_chave('patrimonio', 'dia_inicio_bloqueio')
    if not requisicao.pode_avaliar() or (date.today().day >= int(dia_inicio_bloqueio) and requisicao.tipo == Requisicao.TIPO_DIFERENTES_CAMPI):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = DeferirRequisicaoForm(request.POST or None, instance=requisicao, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'Transferência deferida com sucesso.')

    return locals()


@rtr()
@login_required
def informar_pa_origem_requisicao(request, requisicao_id):
    title = 'PA campus de origem da Requisição'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    if not requisicao.pode_informar_pa_origem():
        raise PermissionDenied()

    form = InformarPAOrigemForm(request.POST or None, instance=requisicao, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'O número da PA foi cadastrado com sucesso.')

    return locals()


@rtr()
@login_required
def editar_pa_origem_requisicao(request, requisicao_id):
    title = 'Editar PA de Campus Origem da Requisição'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    if not requisicao.pode_editar_pa_origem():
        raise PermissionDenied()

    form = EdicaoPAOrigemForm(request.POST or None, requisicao=requisicao, request=request)
    if form.is_valid():
        requisicao.numero_pa_origem = form.cleaned_data['numero_pa_origem']
        requisicao.save()
        return httprr('..', 'O número da PA foi editado com sucesso. Transferência finalizada.')

    return locals()


@rtr()
@login_required
def informar_pa_destino_requisicao(request, requisicao_id):
    title = 'PA campus de destino da Requisição'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    if not requisicao.pode_informar_pa_destino():
        raise PermissionDenied()

    form = InformarPADestinoForm(request.POST or None, instance=requisicao, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'O número da PA foi cadastrado com sucesso.')

    return locals()


@rtr()
@login_required
def editar_pa_destino_requisicao(request, requisicao_id):
    title = 'Editar PA de campus destino da Requisição'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    if not requisicao.pode_editar_pa_destino():
        raise PermissionDenied()

    form = EdicaoPADestinoForm(request.POST or None, requisicao=requisicao, request=request)
    if form.is_valid():
        requisicao.numero_pa_destino = form.cleaned_data['numero_pa_destino']
        requisicao.save()
        return httprr('..', 'O número da PA foi editado com sucesso.')

    return locals()


@rtr()
@permission_required('patrimonio.pode_alterar_carga_contabil')
def listar_inventarios_carga_contabil_inconsistentes(request):
    title = 'Listagem de Inventários com Carga Contábil Diferente do Campus do Responsável'
    FormClass = InconsistenciaFormFactory(request)
    form_inconsistente = FormClass(request.POST or None)
    if form_inconsistente.is_valid():
        form_inconsistente.save()
        return httprr('/admin/patrimonio/requisicao/', 'Requisição criada com sucesso.')
    form_filtro = CampusFiltroInconsistenteForm(request.GET or None)
    inventarios_inconsistentes = Inventario.get_carga_contabil_inconsistentes(request.user)
    inventarios_inconsistentes_campus = Inventario.get_carga_contabil_inconsistentes_campus(request.user)
    ids = list(inventarios_inconsistentes.values_list('id', flat=True))
    inventarios = inventarios_inconsistentes.exclude(id__in=Requisicao.get_qs_aguardando().filter(itens__inventario__id__in=ids).values_list('itens__inventario'))
    if form_filtro.is_valid():
        if form_filtro.cleaned_data['campus']:
            inventarios = inventarios.filter(responsavel_vinculo__setor__uo=form_filtro.cleaned_data['campus'])
        if form_filtro.cleaned_data['servidor']:
            inventarios = inventarios.filter(responsavel_vinculo=form_filtro.cleaned_data['servidor'].get_vinculo())
    inventarios_pendentes = inventarios_inconsistentes.filter(id__in=Requisicao.get_qs_aguardando().filter(itens__inventario__id__in=ids).values_list('itens__inventario'))
    return locals()


@rtr()
def historico_movimentacao_inventario(request, inventario_numero):
    inventario = get_object_or_404(Inventario, numero=inventario_numero)
    title = 'Histórico de Movimentações do Inventário {}'.format(inventario.numero)

    return locals()


@rtr()
@permission_required('patrimonio.pode_alterar_carga_contabil')
def corrigir_carga_contabil(request, inventario_id):
    inventario = get_object_or_404(Inventario, pk=inventario_id)
    if not Inventario.get_carga_contabil_inconsistentes(request.user).filter(id=inventario_id).exists():
        raise PermissionDenied

    inventario.corrigir_carga_contabil(request.user)
    return httprr('/patrimonio/listar_inventarios_carga_contabil_inconsistentes/', 'Inventário corrigido com sucesso.')


@rtr()
def totalizacao_ed_periodo_planocontas(request):
    title = 'Totalização por Elemento de Despesa por Período de Entrada'
    form = FormTotalizacaoEdPeriodo(request.GET or None)
    if form.is_valid():
        resposta, total = totalizacaoPlanoContasPeriodo(form.cleaned_data['ano'], int(form.cleaned_data['mes']), form.cleaned_data['doacoes'])
        request.session['resposta'] = {
            'resposta': resposta,
            'total': total,
            'ano': form.cleaned_data['ano'],
            'mes': calendario.getNomeMes(int(form.cleaned_data['mes'])),
            'doacoes_inclusas': form.cleaned_data['doacoes'],
        }
        return render('patrimonio/templates/relatorio/totalizacao_ed_periodoplanocontas.html', request.session['resposta'])
    else:
        return locals()


# View que se conecta a view rh.views.servidor
@receiver(rh_servidor_view_tab)
def servidor_view_tab_signal(sender, request, servidor, verificacao_propria, eh_chefe, **kwargs):
    inventarios = Inventario.objects.filter(responsavel_vinculo=servidor.get_vinculo())

    if inventarios.exists():
        return render_to_string(template_name='patrimonio/templates/servidor_view_tab.html',
                                context={"lps_context": {"nome_modulo": "patrimonio"}, 'servidor': servidor, 'inventarios': inventarios}, request=request)
    return False


@permission_required('patrimonio.change_requisicao')
@csrf_exempt
def filtra_inventario_transferencia(request):
    data = []

    def get_ext_combo_template(obj):
        data = obj.descricao
        data = (data[:75] + '..') if len(data) > 75 else data
        return '{} - {}'.format(obj.numero, data)

    if request.method == 'POST':
        filter_pks = json.loads(request.POST.get('filter_pks', ''))
        if filter_pks and filter_pks['servidor_origem']:
            servidor_obj = Servidor.objects.get(id=filter_pks['servidor_origem'])
            lista_resultado = Inventario.ativos.filter(responsavel_vinculo=servidor_obj.get_vinculo()).exclude(
                requisicaoitem__requisicao__status=Requisicao.STATUS_AGUARDANDO_APROVACAO_SERVIDOR_DESTINO
            )
        else:
            lista_resultado = Inventario.ativos.exclude(requisicaoitem__requisicao__status=Requisicao.STATUS_AGUARDANDO_APROVACAO_SERVIDOR_DESTINO)

        if request.POST.get('q'):
            lista_resultado = lista_resultado.filter(campo_busca__icontains=request.POST.get('q'))
        data = generate_autocomplete_dict(lista_resultado, int(request.POST.get('page', 1)), ext_combo_template_text=get_ext_combo_template)
    return HttpResponse(json.dumps(data), content_type='application/json')
