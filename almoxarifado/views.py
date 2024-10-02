import io
from collections import OrderedDict
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django.template.defaultfilters import truncatechars
from django.utils import html
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

from almoxarifado.forms import (
    EmpenhoConsumoForm,
    EmpenhoPermanenteForm,
    EntradaEditarForm,
    EntradaDoacaoForm,
    EntradaBuscaForm,
    EntradaDoacaoItemConsumoForm,
    EntradaDoacaoItemPermanenteForm,
    BuscaEmpenhoForm,
    RequisicaoBuscaFormFactory,
    GetBalanceteEdForm,
    BalanceteMaterialFormFactory,
    ConfiguracaoEstoqueForm,
    BalanceteEDDetalhadoFormFactory,
    NotasFornecimentoFormFactory,
    TipoEtiquetaForm,
    DevolucaoItemFormFactory,
    RelatorioSaldoAtualEDForm)
from almoxarifado.models import (
    EmpenhoConsumo,
    MaterialTipo,
    EntradaTipo,
    Empenho,
    Entrada,
    RequisicaoAlmox,
    RequisicaoAlmoxUO,
    RequisicaoAlmoxUser,
    MaterialConsumo,
    RequisicaoAlmoxUserMaterial,
    RequisicaoAlmoxUOMaterial,
    ConfiguracaoEstoque,
    MovimentoAlmoxEntrada,
    CategoriaMaterialConsumo,
    MaterialEstoque,
    DevolucaoMaterial,
    calcula_valor_medio_atual,
    ajusta_entradas_de_transferencias,
    MovimentoAlmoxSaida)
from almoxarifado.relatorio import historico_movimentacao, relatorio_balancete_material, \
    relatorio_balancete_ed_detalhado
from comum.models import Configuracao, Vinculo
from comum.relatorios import rodape_data_e_assinatura, get_topo_com_titulo
from comum.utils import (
    get_topo_pdf,
    get_uo,
    somar_data,
    data_extenso,
    data_normal,
    extrair_periodo,
    somar_indice,
    OPERADOR_ALMOXARIFADO_OU_PATRIMONIO,
    OPERADOR_ALMOXARIFADO,
    TODOS_GRUPOS_ALMOXARIFADO,
)
from djtools import layout
from djtools import pdf
from djtools.etiquetas.labels import factory
from djtools.relatorios.utils import montar_tabela_html
from djtools.templatetags.filters import format_money
from djtools.templatetags.filters import in_group
from djtools.utils import (
    permission_required,
    str_to_dateBR,
    to_ascii,
    rtr,
    render,
    httprr,
    dict_from_keys_n_values,
    group_required,
    login_required,
    user_has_one_of_perms,
    mask_money,
    calendario,
)
from djtools.utils.response import JsonResponse, PDFResponse
from patrimonio.models import EmpenhoPermanente, EntradaPermanente
from rh.models import PessoaJuridica, Servidor, UnidadeOrganizacional


@layout.quadro('Almoxarifado', icone='table')
def index_quadros(quadro, request):
    if request.user.groups.filter(name__in=['Coordenador de Almoxarifado', 'Operador de Almoxarifado', 'Coordenador de Almoxarifado Sistêmico']).exists():
        qtd_requisicoes_usuario = len(RequisicaoAlmoxUser.get_pendentes(request.user))
        qtd_requisicoes_uo = len(RequisicaoAlmoxUO.get_pendentes(request.user))
        qtd_requisicoes = qtd_requisicoes_usuario + qtd_requisicoes_uo
        if qtd_requisicoes:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Requisiç{} pendente{}'.format((pluralize(qtd_requisicoes, 'ão,ões')), pluralize(qtd_requisicoes)),
                    subtitulo='Do almoxarifado',
                    qtd=qtd_requisicoes,
                    url='/almoxarifado/requisicoes_pendentes/',
                )
            )

        qtd_materiais_criticos = len(ConfiguracaoEstoque.get_materiais_criticos())
        if qtd_materiais_criticos:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Materia{} com Estoque Crítico'.format(pluralize(qtd_materiais_criticos, 'l,is')),
                    subtitulo='Do almoxarifado',
                    qtd=qtd_materiais_criticos,
                    url='/almoxarifado/situacao_estoque/',
                )
            )

        hoje = datetime.now()
        prazo_15_dias = hoje.date() + timedelta(days=15)
        empenhos_entrega_15_dias = (
            Empenho.get_sem_atraso().filter(Q(status='nao_iniciado') | Q(status='iniciado')).filter(data_prazo__gte=hoje.date(), data_prazo__lte=prazo_15_dias).count()
        )
        if empenhos_entrega_15_dias > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Empenho{}'.format(pluralize(empenhos_entrega_15_dias)),
                    subtitulo='Com prazo de entrega nos próximos 15 dias',
                    qtd=empenhos_entrega_15_dias,
                    url='/almoxarifado/empenhos/?prazo_15dias=Sim&status=nao_concluido&situacao=sem_atraso&buscaempenho_form=Aguarde...',
                )
            )

    return quadro


def servidor(request, input):
    """
    Retorna servidores que estão na mesma UO do usuário logado.
    --
    Usado somente em /almoxarifado/form_requisicao_usuario_pedido/
    """
    lista = []
    uo = get_uo(request.user)
    if uo:
        for s in Servidor.objects.filter(nome__istartswith=input, excluido=False, setor__id__in=uo.setor.ids_descendentes):
            lista.append('{} [<strong>{}</strong>]|{}\n'.format(s.nome, s.matricula, s.get_vinculo().pk))
    return HttpResponse(''.join(lista))


def fornecedor(request, input):
    """
    Usado somente em /entrada_compra/
    """
    lista = []
    fornecedores = PessoaJuridica.objects.filter(nome__istartswith=input) | PessoaJuridica.objects.filter(cnpj__istartswith=input)
    for f in fornecedores[:10]:
        lista.append("{} [<strong>{}</strong>]|{}\n".format(f.nome, f.cnpj, f.get_vinculo().pk))
    return HttpResponse("".join(lista))


def material_consumo_estoque_uo(request, uo_id, input):
    """
    Retorna materiais que têm estoque na UO passada
    --
    Usado em /almoxarifado/form_requisicao_usuario_pedido/ e
             /almoxarifado/form_requisicao_uo_pedido/
    """
    return HttpResponse(''.join(MaterialConsumo.buscar(palavras=input, com_estoque_em=uo_id, limite=10, autocomplete=True, user=request.user)))


def empenho_todos(request, input):
    """
    Usado somente em /entrada_compra/
    """
    lista = []
    empenhos = Empenho.objects.filter(numero__icontains=input)
    if not in_group(request.user, ['Coordenador de Almoxarifado Sistêmico']):
        empenhos = empenhos.filter(uo=get_uo(request.user))
    for empenho in empenhos:
        if empenho.pendente:
            lista.append("{} (UG: {})|{}\n".format(empenho.numero, empenho.uo and empenho.uo or '?', empenho.id))
        if len(lista) == 10:
            break
    return HttpResponse(''.join(lista))


###########
# Empenho #
###########


@rtr()
def empenho(request, empenho_pk):
    """Tela de detalhes do empenho, com opção para adicionar itens."""
    empenho = get_object_or_404(Empenho, pk=empenho_pk)
    title = 'Empenho {}'.format(empenho.numero)
    if not empenho.pode_ver():
        raise PermissionDenied()

    resumo_ed = empenho.get_categoria_empenho()
    total = empenho.get_valor_total_categoria()

    link_editar = "/admin/almoxarifado/empenho/{:d}/".format(empenho.id)
    link_excluir = "/admin/almoxarifado/empenho/{:d}/delete/".format(empenho.id)

    continuar_cadastrando = int(request.GET.get('continuar_cadastrando', 0)) == 1
    if empenho.tipo_material.nome == 'consumo':
        if request.method == 'POST':
            form = EmpenhoConsumoForm(request.POST)
            form.instance.empenho = empenho
            if form.is_valid():
                continuar_cadastrando = form.cleaned_data['continuar_cadastrando']
                form.save()

                if continuar_cadastrando:
                    return httprr('./?continuar_cadastrando=1', 'Item de Empenho cadastrada com sucesso.')
                else:
                    return httprr('.', 'Item de Empenho cadastrada com sucesso.')

        else:
            form = EmpenhoConsumoForm()

    elif empenho.tipo_material.nome == 'permanente':
        if request.method == 'POST':
            form = EmpenhoPermanenteForm(request.POST)
            form.instance.empenho = empenho
            if form.is_valid():
                continuar_cadastrando = form.cleaned_data['continuar_cadastrando']
                form.save()

                if continuar_cadastrando:
                    return httprr('./?continuar_cadastrando=1', 'Item de Empenho cadastrada com sucesso.')
                else:
                    return httprr('.', 'Item de Empenho cadastrada com sucesso.')
        else:
            form = EmpenhoPermanenteForm()

    return locals()


@permission_required('patrimonio.delete_empenhopermanente')
def empenhopermanente_remover(request, id_empenhopermanente):
    empenhopermanente = get_object_or_404(EmpenhoPermanente, pk=id_empenhopermanente)
    empenho_pk = empenhopermanente.empenho_id
    numero = empenhopermanente.empenho.numero
    if empenhopermanente.can_delete():
        empenhopermanente.delete()
        if len(Empenho.objects.filter(id=empenho_pk)) > 0:
            # forca execucao do AtualizaInformacoes (se for ultimo item pendente, altera status para "Concluído")
            Empenho.objects.get(id=empenho_pk).atualizar_informacoes()

            # avisa sobre remocao do item
            return httprr(empenhopermanente.empenho.get_absolute_url(), 'Item removido com sucesso!')
        else:
            return httprr('/admin/almoxarifado/empenho/', 'O empenho de número {} foi removido porque possuia apenas um item!'.format(numero))
    raise PermissionDenied()


@permission_required('almoxarifado.delete_empenhoconsumo')
def empenhoconsumo_remover(request, id_empenhoconsumo):
    empenhoconsumo = get_object_or_404(EmpenhoConsumo, pk=id_empenhoconsumo)
    empenho_pk = empenhoconsumo.empenho_id
    numero = empenhoconsumo.empenho.numero
    if empenhoconsumo.can_delete():
        empenhoconsumo.delete()
        if len(Empenho.objects.filter(id=empenho_pk)) > 0:
            # forca execucao do AtualizaInformacoes (se for ultimo item pendente, altera status para "Concluído")
            Empenho.objects.get(id=empenho_pk).atualizar_informacoes()

            # avisa sobre remocao do item
            return httprr(empenhoconsumo.empenho.get_absolute_url(), 'Item removido com sucesso!')
        else:
            return httprr('/admin/almoxarifado/empenho/', 'O empenho de número {} foi removido porque possuia apenas um item!'.format(numero))
    raise PermissionDenied()


@rtr()
@permission_required('almoxarifado.view_empenho')
def empenhos(request):
    title = 'Empenhos'
    form = BuscaEmpenhoForm(request.GET or None)
    if form.is_valid():
        empenhos = Empenho.objects.all()

        # situação do Empenho
        if form.cleaned_data['situacao'] == 'atrasados':
            empenhos = Empenho.get_atrasados_pendentes()
        elif form.cleaned_data['situacao'] == 'sem_atraso':
            empenhos = Empenho.get_sem_atraso()
        elif form.cleaned_data['situacao'] == 'pendentes':
            empenhos = Empenho.get_pendentes()
        elif form.cleaned_data['situacao'] == 'concluidos_atraso':
            empenhos = Empenho.get_concluidos_com_atraso()

        if request.GET.get('prazo_15dias'):
            hoje = datetime.now()
            prazo_15_dias = hoje.date() + timedelta(days=15)
            empenhos = empenhos.filter(data_prazo__gte=hoje.date(), data_prazo__lte=prazo_15_dias)

        # filtro por Tipo Material?
        if form.cleaned_data['tipo_material']:
            empenhos = empenhos.filter(tipo_material=form.cleaned_data['tipo_material'])

        # filtro por Tipo Licitação?
        if form.cleaned_data['tipo_licitacao']:
            empenhos = empenhos.filter(tipo_licitacao=form.cleaned_data['tipo_licitacao'])

        # filtro por Status
        if form.cleaned_data['status'] == 'nao_concluido':
            empenhos = empenhos.filter(Q(status='nao_iniciado') | Q(status='iniciado'))
        elif form.cleaned_data['status'] != 'todos':
            empenhos = empenhos.filter(status=form.cleaned_data['status'])

        # filtro por UG
        if form.cleaned_data['ug_emitente']:
            empenhos = empenhos.filter(uo=form.cleaned_data['ug_emitente'])

        # busca por Número do Empenho
        if form.cleaned_data['numero_empenho']:
            empenhos = empenhos.filter(numero__icontains=form.cleaned_data['numero_empenho'])

        # busca por Número do Processo
        if form.cleaned_data['numero_processo']:
            empenhos = empenhos.filter(processo=form.cleaned_data['numero_processo'])

        # busca por Fornecedor
        if form.cleaned_data['vinculo_fornecedor']:
            empenhos = empenhos.filter(vinculo_fornecedor=form.cleaned_data['vinculo_fornecedor'])

        # busca por Número da Licitação
        if form.cleaned_data['numero_licitacao']:
            empenhos = empenhos.filter(numero_pregao__icontains=form.cleaned_data['numero_licitacao'])

        # busca por Empenhos com Elemento de Despesa Permanente
        if form.cleaned_data['elemento_despesa']:
            empenhos = empenhos.filter(empenhopermanente__categoria=form.cleaned_data['elemento_despesa'])
        # busca por Empenhos com Elemento de Despesa Consumo
        if form.cleaned_data['elemento_despesa_consumo']:
            empenhos = empenhos.filter(empenhoconsumo__material__categoria=form.cleaned_data['elemento_despesa_consumo'])
        # descrição do item
        if form.cleaned_data['descricao_item']:
            empenhos = empenhos.filter(
                Q(empenhopermanente__descricao__unaccent__icontains=form.cleaned_data['descricao_item'])
                | Q(empenhoconsumo__material__search__contains=to_ascii(form.cleaned_data['descricao_item']).upper())
            )

        # remove duplicados e ordena
        empenhos = empenhos.distinct().order_by("-numero")

    return locals()


@csrf_exempt
@group_required(OPERADOR_ALMOXARIFADO_OU_PATRIMONIO)
def get_itens_empenho(request):
    """
    Utilizado na entrada de nota fiscal (suap/templates/form_entrada.html)
    """
    # FIXME: implementar método get_itens_pendentes na classe Empenho.
    empenho = Empenho.objects.get(id=request.POST['empenho_id'])
    if empenho.tipo_material.nome == 'consumo':
        empenho_itens = EmpenhoConsumo.get_pendentes(empenho)
    else:
        empenho_itens = EmpenhoPermanente.get_pendentes(empenho)
    if not empenho_itens:
        return JsonResponse({'valid': False, 'html': 'O EMPENHO não tem itens pendentes'.decode('utf-8')})
    html = render('empenho_itens.html', {'tipo_material': empenho.tipo_material.nome, 'empenho_itens': empenho_itens})
    vinculo_fornecedor = empenho.vinculo_fornecedor
    vinculo_fornecedor_json = dict(id=vinculo_fornecedor.id, nome=vinculo_fornecedor.pessoa.nome)
    return JsonResponse(dict(itens=html.content.decode(), vinculo_fornecedor=vinculo_fornecedor_json))


@csrf_exempt
@group_required(OPERADOR_ALMOXARIFADO)
def info_solicitante(request):
    funcionario = Vinculo.objects.get(pk=request.POST["solicitante_id"])
    unidade = funcionario.setor.uo
    setor = '{} - {} ({})'.format(funcionario.setor.sigla, funcionario.setor.nome, unidade)
    return JsonResponse({'matricula': funcionario.relacionamento.matricula, 'setor': setor})


###########
# Entrada #
###########


@rtr()
def entrada(request, entrada_id):
    entrada = get_object_or_404(Entrada, id=entrada_id)

    title = str(entrada)

    if not entrada.pode_ver():
        raise PermissionDenied()

    resumo_ed = entrada.get_elem_despesa_entrada()
    total = entrada.get_valor_total()
    total = "{:,}".format(total)
    total = total.replace('.', ';')
    total = total.replace(',', '.')
    total = total.replace(';', ',')

    return locals()


@rtr()
@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def entrada_editar(request, entrada_id):
    entrada = get_object_or_404(Entrada, id=entrada_id)
    title = 'Editar {}'.format(entrada)
    if request.method == "POST":
        form = EntradaEditarForm(request.POST, instance=entrada)
        if form.is_valid():
            form.save()
            return httprr(entrada.get_absolute_url(), '{} alterada!'.format(form.instance))
    else:
        form = EntradaEditarForm(instance=entrada)
    return locals()


@rtr()
@group_required('Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def entrada_remover(request, entrada_id):
    entrada = get_object_or_404(Entrada, id=entrada_id)
    entrada.delete()
    return httprr('/almoxarifado/entrada_busca/', 'Entrada NF removida com sucesso')


@rtr()
def adicionar_item(request, entrada_id):
    title = 'Adicionar Item'
    entrada = get_object_or_404(Entrada, pk=entrada_id)

    form = None
    if request.method == 'POST':
        if entrada.tipo_material == MaterialTipo.CONSUMO():
            form = EntradaDoacaoItemConsumoForm(request.POST)
            if form.is_valid():
                # efetua registro em MovimentoAlmoxEntrada
                material = form.cleaned_data['material']
                qtd = form.cleaned_data['qtd']
                valor = form.cleaned_data['valor']
                entrada.efetuar_entrada_material_consumo(material, qtd, valor)
                return httprr('..', 'Item adicionado com sucesso.')

        elif entrada.tipo_material == MaterialTipo.PERMANENTE():
            form = EntradaDoacaoItemPermanenteForm(request.POST)
            form.instance.entrada = entrada
            if form.is_valid():
                form.save()
                return httprr('..', 'Item adicionado com sucesso.')

    else:
        if entrada.tipo_material == MaterialTipo.CONSUMO():
            form = EntradaDoacaoItemConsumoForm()
        elif entrada.tipo_material == MaterialTipo.PERMANENTE():
            form = EntradaDoacaoItemPermanenteForm()

    return locals()


@rtr()
def entrada_busca(request):
    """
    View que exibe tanto o formulário para busca de entradas como também o resultado da busca.
    """
    title = 'Busca de Entradas'
    # Restrição de acesso à busca e/ou visualização de Entradas.
    if not request.user.has_perm('almoxarifado.pode_ver_entrada'):
        raise PermissionDenied()

    form = EntradaBuscaForm(request.GET or None)
    if form.is_valid():
        uo = form.cleaned_data['uo']
        vinculo_fornecedor = form.cleaned_data['vinculo_fornecedor']
        tipo_material = form.cleaned_data['tipo_material']
        tipo_entrada = form.cleaned_data['tipo_entrada']
        empenho = form.cleaned_data['empenho']
        processo = form.cleaned_data['processo']
        numero_nota_fiscal = form.cleaned_data['numero_nota_fiscal']
        data_inicial = form.cleaned_data['data_inicial']
        data_final = form.cleaned_data['data_final']
        descricao_material = form.cleaned_data['descricao_material']

        entradas = Entrada.objects.all()
        if uo:
            entradas = entradas.filter(uo=uo)
        if vinculo_fornecedor:
            entradas = entradas.filter(vinculo_fornecedor=vinculo_fornecedor)
        if numero_nota_fiscal:
            entradas = entradas.filter(numero_nota_fiscal__icontains=numero_nota_fiscal)
        if empenho:
            entradas = entradas.filter(Q(movimentoalmoxentrada__empenho_consumo__empenho=empenho) | Q(entradapermanente__empenho_permanente__empenho=empenho))
        if processo:
            entradas = entradas.filter(
                Q(entradapermanente__empenho_permanente__empenho__processo=processo) | Q(movimentoalmoxentrada__empenho_consumo__empenho__processo=processo) | Q(processo=processo)
            )
        if tipo_material:
            entradas = entradas.filter(tipo_material=tipo_material)
            if descricao_material:
                if tipo_material == MaterialTipo.PERMANENTE():
                    entradas = entradas.filter(entradapermanente__descricao__unaccent__icontains=descricao_material)
                elif tipo_material == MaterialTipo.CONSUMO():
                    entradas = entradas.filter(movimentoalmoxentrada__material__nome__unaccent__icontains=descricao_material)
        if tipo_entrada:
            entradas = entradas.filter(tipo_entrada=tipo_entrada)
        if data_inicial:
            entradas = entradas.filter(data__gte=data_inicial)
        if data_final:
            entradas = entradas.filter(data__lte=data_final)
        entradas = entradas.order_by('-data').distinct()

        # soma por ELEMENTO DE DESPESA
        elementos_despesas, total_entradas = Entrada.total_elementos_despesas(
            uo, vinculo_fornecedor, tipo_material, tipo_entrada, empenho, processo, numero_nota_fiscal, data_inicial, data_final, descricao_material
        )
    parametros = request.GET.urlencode()
    return locals()


def entrada_pdf(request, entrada_id):
    """ Gera PDF de detalhes da entrada."""
    # Bloqueio de acesso à visualização da entrada com base na permissão do usuários
    if not request.user.has_perm('almoxarifado.pode_ver_entrada'):
        raise PermissionDenied()

    entrada = get_object_or_404(Entrada, pk=entrada_id)
    fields = []

    if entrada.tipo_entrada.nome == 'compra':
        assinatura = 'Coordenação de Almoxarifado'
    else:
        assinatura = 'Coordenação de Patrimônio'

    tipo_entrada = entrada.tipo_entrada.nome

    fields.append(['<b>Campus de Entrada:</b> {}'.format(entrada.uo), '<b>Data de Entrada</b>: {}'.format(entrada.get_data())])

    if tipo_entrada == "doacao":
        fields.append(['<b>Tipo de Entrada:</b>:', entrada.tipo_entrada.nome.capitalize() + ' - ' + entrada.tipo_material.nome.capitalize()])

    else:
        empenho = entrada.get_empenho()
        processo = ""
        status = ""
        licitacao = ""
        if empenho:
            status = entrada.get_info_prazo()
            processo = empenho.processo or ""
            tipo_licitacao = empenho.tipo_licitacao
            if tipo_licitacao:
                licitacao = tipo_licitacao.nome + ' - ' + (empenho.numero_pregao or "")
            fields.append(
                [
                    '<b>Tipo de Entrada:</b> {}'.format(entrada.tipo_entrada.nome.capitalize() + ' - ' + entrada.tipo_material.nome.capitalize()),
                    '<b>Situação da Entrada:</b> {}'.format(status),
                ]
            )
            fields.append(['<b>Licitação:</b> {}'.format(licitacao), '<b>Empenho:</b> {}'.format(empenho)])

            fields.append(['<b>Processo do Empenho:</b> {}'.format(processo), '<b>Data de Recebimento do Empenho:</b> {}'.format(data_normal(empenho.data_recebimento_empenho))])
            fields.append(['<b>Observação:</b>', empenho.observacao])

    fields.append(['<b>Número Nota Fiscal:</b> {}'.format(entrada.numero_nota_fiscal or '-'), '<b>Data Nota Fiscal:</b> {}'.format(entrada.get_data_nota_fiscal())])
    telefones = entrada.vinculo_fornecedor.pessoa.telefones
    fields.append(
        [
            '<b>Fornecedor:</b> {}'.format(html.escape(entrada.vinculo_fornecedor.pessoa.nome)),
            '<b>CPF/CNPJ Fornecedor:</b> {}'.format(html.escape(entrada.vinculo_fornecedor.pessoa.get_cpf_ou_cnpj())),
        ]
    )

    fields.append(['<b>E-mail Fornecedor:</b> {}'.format(entrada.vinculo_fornecedor.pessoa.email or ""), '<b>Fone Fornecedor:</b> {}'.format(telefones)])

    tabela_dados = [['Código', 'Material', 'Cód. ED', 'Conta Contábil', 'Qtd.', 'Valor Unitário', 'Valor Total']]

    for index, item in enumerate(entrada.get_itens()):
        valor_unit = item.get_valor_unitario()
        valor_unit = valor_unit.replace('.', '')
        valor_unit = valor_unit.replace(',', '.')

        valor_unitario = Decimal(valor_unit)

        valor_unitario = "{:,}".format(valor_unitario)
        valor_unitario = valor_unitario.replace('.', ';')
        valor_unitario = valor_unitario.replace(',', '.')
        valor_unitario = valor_unitario.replace(';', ',')

        val = item.get_valor()
        val = val.replace('.', '')
        val = val.replace(',', '.')

        valor = Decimal(val)
        valor = "{:,}".format(valor)
        valor = valor.replace('.', ';')
        valor = valor.replace(',', '.')
        valor = valor.replace(';', ',')

        material = item.get_material()
        codigo = ''
        if entrada.tipo_material == MaterialTipo.CONSUMO():
            material = item.get_material().nome
            codigo = item.get_material().codigo
        planocontas = None
        if item.get_categoria().plano_contas:
            planocontas = item.get_categoria().plano_contas.codigo
        row = [codigo, truncatechars(html.escape(material), 3743), item.get_categoria().codigo, planocontas, item.qtd, item.get_valor_unitario(), item.get_valor()]
        tabela_dados.append(row)

    tabela_info = pdf.table(fields, w=[95, 95])
    tabela_dados = pdf.table(tabela_dados, head=1, zebra=1, w=[15, 90, 10, 25, 10, 20, 20], count=1, a=['l', 'l', 'c', 'c', 'r', 'r', 'r'])
    p1 = 'Dados da Entrada'
    p2 = 'Itens da Entrada'

    tot = entrada.get_valor()
    tot = tot.replace('.', '')
    tot = tot.replace(',', '.')

    total = "{:,}".format(Decimal(tot))
    total = total.replace('.', ';')
    total = total.replace(',', '.')
    total = total.replace(';', ',')
    p3 = 'Valor Total: {}'.format(total)

    body = (
        get_topo_com_titulo('Detalhamento de Entrada')
        + [pdf.para(p1, style='h2', align='left')]
        + [pdf.space(4), tabela_info, pdf.space(8)]
        + [pdf.para(p2, style='h2', align='left'), pdf.space(4), tabela_dados]
        + [pdf.space(4), pdf.para(p3, align='right')]
    )

    return PDFResponse(pdf.PdfReport(body=body, footer_args=rodape_data_e_assinatura(assinatura)).generate())


def entrada_inventarios_pdf(request, entrada_id):
    """ Gera PDF de detalhes da entrada."""
    # Bloqueio de acesso à visualização da entrada com base na permissão do usuários
    entrada = get_object_or_404(Entrada, pk=entrada_id)
    fields = []

    if not request.user.has_perm('almoxarifado.pode_ver_entrada') and not entrada.tipo_material == MaterialTipo.PERMANENTE():
        raise PermissionDenied()

    if entrada.tipo_entrada.nome == 'compra':
        assinatura = 'Coordenação de Almoxarifado'
    else:
        assinatura = 'Coordenação de Patrimônio'

    tipo_entrada = entrada.tipo_entrada.nome

    fields.append(['<b>Campus de Entrada:</b> {}'.format(entrada.uo), '<b>Data de Entrada</b>: {}'.format(entrada.get_data())])

    if tipo_entrada == "doacao":
        fields.append(['<b>Tipo de Entrada:</b>:', entrada.tipo_entrada.nome.capitalize() + ' - ' + entrada.tipo_material.nome.capitalize()])

    else:
        empenho = entrada.get_empenho()
        processo = ""
        status = ""
        licitacao = ""
        if empenho:
            status = entrada.get_info_prazo()
            processo = empenho.processo or ""
            tipo_licitacao = empenho.tipo_licitacao
            if tipo_licitacao:
                licitacao = tipo_licitacao.nome + ' - ' + (empenho.numero_pregao or "")
            fields.append(
                [
                    '<b>Tipo de Entrada:</b> {}'.format(entrada.tipo_entrada.nome.capitalize() + ' - ' + entrada.tipo_material.nome.capitalize()),
                    '<b>Situação da Entrada:</b> {}'.format(status),
                ]
            )
            fields.append(['<b>Licitação:</b> {}'.format(licitacao), '<b>Empenho:</b> {}'.format(empenho)])

            fields.append(['<b>Processo do Empenho:</b> {}'.format(processo), '<b>Data de Recebimento do Empenho:</b> {}'.format(data_normal(empenho.data_recebimento_empenho))])
            fields.append(['<b>Observação:</b>', empenho.observacao])

    fields.append(['<b>Número Nota Fiscal:</b> {}'.format(entrada.numero_nota_fiscal or '-'), '<b>Data Nota Fiscal:</b> {}'.format(entrada.get_data_nota_fiscal())])

    telefones = entrada.vinculo_fornecedor.pessoa.telefones
    fields.append(
        [
            '<b>Fornecedor:</b> {}'.format(html.escape(entrada.vinculo_fornecedor.pessoa.nome)),
            '<b>CPF/CNPJ Fornecedor:</b> {}'.format(html.escape(entrada.vinculo_fornecedor.pessoa.get_cpf_ou_cnpj())),
        ]
    )

    fields.append(['<b>E-mail Fornecedor:</b> {}'.format(entrada.vinculo_fornecedor.pessoa.email or ""), '<b>Fone Fornecedor:</b> {}'.format(telefones)])

    tabela_dados = [['Número', 'Material', 'Cód. ED', 'Conta Contábil', 'Valor']]

    for index, item in enumerate(entrada.get_inventarios()):
        plano_contas = None
        if item.entrada_permanente.categoria.plano_contas is not None:
            plano_contas = item.entrada_permanente.categoria.plano_contas.codigo
        row = [
            item.numero,
            truncatechars(html.escape(item.get_descricao()), 1000),
            item.entrada_permanente.categoria.codigo,
            plano_contas,
            item.get_valor(),
        ]
        tabela_dados.append(row)

    tabela_info = pdf.table(fields, w=[95, 95])
    tabela_dados = pdf.table(tabela_dados, head=1, zebra=1, w=[15, 100, 20, 20, 25], count=1, a=['l', 'l', 'c', 'c', 'r'])
    p1 = 'Dados da Entrada'
    p2 = 'Inventários da Entrada'

    body = (
        get_topo_com_titulo('Inventários da Entrada')
        + [pdf.para(p1, style='h2', align='left')]
        + [pdf.space(4), tabela_info, pdf.space(8)]
        + [pdf.para(p2, style='h2', align='left'), pdf.space(4), tabela_dados]
    )

    return PDFResponse(pdf.PdfReport(body=body, footer_args=rodape_data_e_assinatura(assinatura)).generate())


@rtr()
@group_required(OPERADOR_ALMOXARIFADO_OU_PATRIMONIO)
def entrada_doacao(request):
    title = 'Efetuar Entrada de Doação'
    uo = request.user.get_vinculo().setor.uo
    if not uo:
        raise PermissionDenied()
    if request.method == 'POST':
        form = EntradaDoacaoForm(request.POST)
        if form.is_valid():
            form.save()
            return httprr(form.instance.get_absolute_url(), "Entrada realizada com sucesso.")
    else:
        form = EntradaDoacaoForm()
    return locals()


@rtr()
@group_required(OPERADOR_ALMOXARIFADO_OU_PATRIMONIO)
def entrada_compra(request):
    """Exibe o formulário para efetuar entradas e efetua as entradas.
    """
    try:
        uo = request.user.get_vinculo().setor.uo
    except AttributeError:
        uo = None
    if not uo:
        raise PermissionDenied()
    return dict(uo=uo, title='Efetuar Entrada de Compra')


@group_required(OPERADOR_ALMOXARIFADO_OU_PATRIMONIO)
def entrada_realizar(request):
    # COMPRA (cada item entrado corresponde a um item empenhado)
    if not 'empenho_hidden' in request.POST:
        return httprr('..', 'Erro ao realizar entrada.')
    empenho = Empenho.objects.get(id=request.POST['empenho_hidden'])
    if empenho.tipo_material.nome == 'consumo':
        tipo_material = MaterialTipo.CONSUMO()
    else:
        tipo_material = MaterialTipo.PERMANENTE()

    entrada = Entrada(
        data=str_to_dateBR(request.POST['data_entrada']),
        tipo_entrada=EntradaTipo.COMPRA(),
        tipo_material=tipo_material,
        numero_nota_fiscal=request.POST['numero_nota'],
        data_nota_fiscal=str_to_dateBR(request.POST['data_nota']),
        uo=request.user.get_vinculo().setor.uo,
        vinculo_fornecedor=Vinculo.objects.get(pk=request.POST['fornecedor_hidden']),
    )
    entrada.save()

    empenho_itens = request.POST.getlist('empenho_itens')
    qtds = request.POST.getlist('qtds')

    # Material de consumo
    if tipo_material.nome == 'consumo':
        for index, id_ in enumerate(empenho_itens):
            qtd_adquirida = int(qtds[index])
            empenho_consumo = EmpenhoConsumo.objects.get(pk=int(id_))
            empenho_consumo.efetuar_entrada(entrada, qtd_adquirida)

    # Material permanente
    else:
        for index, id_ in enumerate(empenho_itens):
            qtd_adquirida = int(qtds[index])
            empenho_permanente = EmpenhoPermanente.objects.get(pk=int(id_))
            empenho_permanente.qtd_adquirida += qtd_adquirida
            empenho_permanente.save()
            entrada_permanente = EntradaPermanente(
                entrada=entrada,
                empenho_permanente=empenho_permanente,
                categoria=empenho_permanente.categoria,
                descricao=empenho_permanente.descricao,
                qtd=qtd_adquirida,
                valor=empenho_permanente.valor,
            )
            entrada_permanente.save(user=request.user)
    empenho.atualizar_informacoes()

    return httprr(entrada.get_absolute_url(), 'Entrada realizada com sucesso.')


def entrada_item_estornar(request, tipo_entrada, item_id):
    """Estorna `MovimentoAlmoxEntrada` ou `EntradaPermanente`."""
    Classe = dict(consumo=MovimentoAlmoxEntrada, permanente=EntradaPermanente)[tipo_entrada]
    item = get_object_or_404(Classe, pk=item_id)
    if not item.can_delete():
        raise PermissionDenied()
    if item.entrada.tipo_material == MaterialTipo.CONSUMO():
        material_a_atualizar = MaterialEstoque.objects.get(material=item.material, uo=item.entrada.uo)
        quantidade_atual = material_a_atualizar.quantidade - item.qtd
        valor_medio = 0
        if quantidade_atual != 0:
            valor_medio = (
                (material_a_atualizar.quantidade * material_a_atualizar.valor_medio) - (item.qtd * Decimal(item.get_valor_unitario().replace(',', '.')))
            ) / quantidade_atual
        material_a_atualizar.valor_medio = valor_medio
        material_a_atualizar.quantidade = quantidade_atual
        material_a_atualizar.save()
    item.delete()
    entrada_removida = not Entrada.objects.filter(pk=item.entrada.id).count()
    url = entrada_removida and '/almoxarifado/entrada_busca/' or '/almoxarifado/entrada/{}/'.format(item.entrada.id)
    return httprr(url, 'Item de entrada estornado com sucesso!')


@rtr()
def detalhar_elemento_despesa(request, elemento_despesa_id):
    title = 'Detalhamento de Elemento de Despesa'

    uo = request.GET.get('uo')
    vinculo_fornecedor = request.GET.get('vinculo_fornecedor')
    numero_nota_fiscal = request.GET.get('numero_nota_fiscal')
    empenho = request.GET.get('numero_nota_fiscal')
    processo = request.GET.get('processo')
    tipo_material = request.GET.get('tipo_material')
    descricao_material = request.GET.get('descricao_material')
    tipo_entrada = request.GET.get('tipo_entrada')
    data_inicial = datetime.strptime(request.GET.get('data_inicial'), "%Y-%m-%d").date() if request.GET.get('data_inicial') else None
    data_final = datetime.strptime(request.GET.get('data_final'), "%Y-%m-%d").date() if request.GET.get('data_final') else None

    entradas = Entrada.objects.all()
    if uo:
        entradas = entradas.filter(uo=uo)
    if vinculo_fornecedor:
        entradas = entradas.filter(vinculo_fornecedor=vinculo_fornecedor)
    if numero_nota_fiscal:
        entradas = entradas.filter(numero_nota_fiscal__icontains=numero_nota_fiscal)
    if empenho:
        entradas = entradas.filter(Q(movimentoalmoxentrada__empenho_consumo__empenho=empenho) | Q(entradapermanente__empenho_permanente__empenho=empenho))
    if processo:
        entradas = entradas.filter(
            Q(entradapermanente__empenho_permanente__empenho__processo=processo) | Q(movimentoalmoxentrada__empenho_consumo__empenho__processo=processo) | Q(processo=processo)
        )
    if tipo_material:
        entradas = entradas.filter(tipo_material=tipo_material)
        if descricao_material:
            if tipo_material == MaterialTipo.PERMANENTE():
                entradas = entradas.filter(entradapermanente__descricao__unaccent__icontains=descricao_material)
            elif tipo_material == MaterialTipo.CONSUMO():
                entradas = entradas.filter(movimentoalmoxentrada__material__nome__unaccent__icontains=descricao_material)
    if tipo_entrada:
        entradas = entradas.filter(tipo_entrada=tipo_entrada)

    if data_inicial:
        entradas = entradas.filter(data__gte=data_inicial)
    if data_final:
        entradas = entradas.filter(data__lte=data_final)
    entradas = entradas.order_by('-data').distinct()

    total = 0
    itens = []
    for entrada in entradas:
        for i in entrada.get_itens():
            if int(i.get_categoria().codigo) == elemento_despesa_id:
                valor = i.get_valor().replace('.', '')
                total += Decimal(valor.replace(',', '.'))
                itens.append(i)
    return locals()


def capa_pagamento_pdf(request, entrada_id):
    """ Gera PDF para capa de pagamento."""

    # Bloqueio de acesso à visualização da entrada com base na permissão do usuários
    if not request.user.has_perm('almoxarifado.pode_ver_entrada'):
        raise PermissionDenied()

    entrada = get_object_or_404(Entrada, pk=entrada_id)
    resumo_ed = entrada.get_elem_despesa_entrada()
    total = entrada.get_valor_total()
    fields = []

    if entrada.tipo_entrada.nome == 'doacao':
        raise PermissionDenied()
    else:
        assinatura = 'Coordenação de Almoxarifado'

        empenho = entrada.get_empenho()

        fields.append(['<b>Interessado:</b>', (entrada.vinculo_fornecedor)])

        fields.append(['<b>Número Nota Fiscal:</b>', '<p align="left"> {} </p>'.format(html.escape(entrada.numero_nota_fiscal))])

        fields.append(['<b>Natureza:</b>:', entrada.tipo_material.nome.capitalize()])

        fields.append(['<b>Empenho:</b>', empenho])

        fields.append(['<b>Valor:</b>', '<p align="left"> {} </p>'.format(entrada.get_valor())])

        tabela_info = pdf.table(fields, w=[60, 130])

        protocolo = 'Documentação referente ao processo de compra protocolado sob o número: <b> {} </b>'.format(empenho.processo)

    p1 = 'Protocolo'
    p2 = 'Documento'
    p3 = 'Total por elemento de despesa'

    tabela_ed = [['Código', 'Conta Contábil', 'Descrição', 'Valor']]

    for ed in resumo_ed:
        codigo = ed['codigo']
        contacontabil = ed['planocontas']
        categoria = ed['categoria']
        valor = ed['valor']

        linha = [codigo, contacontabil, categoria, valor]

        tabela_ed.append(linha)

    total_ajustado = total
    total_ajustado = "{:,}".format(total_ajustado)
    total_ajustado = total_ajustado.replace('.', ';')
    total_ajustado = total_ajustado.replace(',', '.')
    total_ajustado = total_ajustado.replace(';', ',')

    total = ['', '', 'TOTAL', total_ajustado]
    tabela_ed.append(total)

    tabela_ed = pdf.table(tabela_ed, head=1, zebra=1, w=[15, 30, 120, 25], a=['c', 'c', 'r', 'r'])

    body = (
        get_topo_com_titulo('Capa de Pagamento')
        + [pdf.para(p1, style='h2', align='left')]
        + [pdf.para(protocolo, align='left')]
        + [pdf.para(p2, style='h2', align='left'), pdf.space(4), tabela_info]
        + [pdf.space(4)]
        + [pdf.para(p3, style='h2', align='left')]
        + [pdf.space(4), tabela_ed]
    )

    return PDFResponse(pdf.PdfReport(body=body, footer_args=rodape_data_e_assinatura(assinatura)).generate())


@group_required(TODOS_GRUPOS_ALMOXARIFADO)
@rtr()
def balancete_ed_detalhado(request):
    """
    Exibe formulário para geração de relatório de Elemento de Despesa detalhado.
    """
    title = 'Balancete Elemento de Despesa Detalhado'
    FormClass = BalanceteEDDetalhadoFormFactory(request.user)
    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            return relatorio_balancete_ed_detalhado(form.cleaned_data, request)
    else:
        form = FormClass()
    return locals()


###
# Requisições
###


@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
@rtr()
def form_requisicao_usuario_pedido(request):
    return dict(uos=UnidadeOrganizacional.objects.suap().all(), title='Requisição de Saída de Material para Consumo')


@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def requisicao_usuario_pedido(request):
    if not request.POST.get('uo_id'):
        return httprr('/almoxarifado/form_requisicao_usuario_pedido/', 'Campus não Informado.', 'error')

    uo_fornecedora = UnidadeOrganizacional.objects.suap().get(id=int(request.POST['uo_id']))

    if in_group(request.user, OPERADOR_ALMOXARIFADO):
        vinculo_solicitante = Vinculo.objects.get(id=int(request.POST['solicitante_hidden']))
    else:
        vinculo_solicitante = request.user.get_vinculo()

    setor_solicitante = vinculo_solicitante.setor
    observacoes = request.POST.get('obs')
    materiais_id = request.POST.getlist('itens_hidden')
    quantidades = request.POST.getlist('quantidades')
    if observacoes and len(observacoes) > 255:
        return httprr('/almoxarifado/form_requisicao_usuario_pedido/', 'O campo Observações está muito grande. Por favor resuma para até 255 caracteres.', 'error')

    requisicao = RequisicaoAlmoxUser(
        uo_fornecedora=uo_fornecedora, vinculo_solicitante=vinculo_solicitante, setor_solicitante=setor_solicitante, data=datetime.now(), avaliada=False, observacoes=observacoes
    )

    dict_materiais = {}

    for i in range(len(materiais_id)):
        chave = materiais_id[i]
        if chave not in list(dict_materiais.keys()):
            dict_materiais[chave] = int(quantidades[i])
        else:
            dict_materiais[chave] += int(quantidades[i])
    try:
        with transaction.atomic():
            requisicao.save()
            for i in list(dict_materiais.items()):
                RequisicaoAlmoxUserMaterial(requisicao=requisicao, material=MaterialConsumo.objects.get(id=i[0]), qtd=int(i[1])).save()
    except Exception:
        return httprr('/almoxarifado/requisicoes_pendentes/', 'Erro ao tentar processar requisição. Por favor verifique os itens e tente novamente.', 'error')
    return httprr('/almoxarifado/requisicoes_pendentes/', 'Requisição efetuada com sucesso.')


@rtr()
@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def form_requisicao_uo_pedido(request):
    id_uo_usuario_logado = request.user.get_vinculo().setor.uo.id
    uos = UnidadeOrganizacional.objects.suap().exclude(id=id_uo_usuario_logado)
    return dict(uos=uos, title='Requisição de Transferência de Material de Consumo Intercampi')


@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def requisicao_uo_pedido(request):
    materiais_id = request.POST.getlist('itens_hidden')
    quantidades = request.POST.getlist('quantidades')
    requisicao = RequisicaoAlmoxUO(
        uo_fornecedora=UnidadeOrganizacional.objects.suap().get(id=int(request.POST['uo_id'])),
        vinculo_solicitante=request.user.get_vinculo(),
        uo_solicitante=request.user.get_vinculo().setor.uo,
        data=datetime.now(),
        avaliada=False,
    )
    requisicao.save()
    for i in range(len(materiais_id)):
        RequisicaoAlmoxUOMaterial(requisicao=requisicao, material=MaterialConsumo.objects.get(id=materiais_id[i]), qtd=int(quantidades[i])).save()
    return httprr('/almoxarifado/requisicoes_pendentes/', 'Requisição efetuada com sucesso.')


@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
@rtr()
def requisicoes_pendentes(request):
    title = 'Requisições Pendentes'
    requisicoes_user = RequisicaoAlmoxUser.get_pendentes(request.user)
    requisicoes_uo = RequisicaoAlmoxUO.get_pendentes(request.user)

    return locals()


@login_required()
def requisicao_detalhe(request, tipo, objeto_id):
    """
    Retorna o detalhamento da requisição selecionada ou formulário para responder
    a requisição.
    """
    requisicao = RequisicaoAlmox.get(tipo, objeto_id)
    pode_remover = requisicao.user_can_delete(request.user)
    pode_responder = requisicao.user_pode_responder(request.user)
    pode_ver = requisicao.user_pode_ver(request.user)
    pode_devolver = requisicao.user_pode_devolver_item(request.user)
    itens_devolvidos = DevolucaoMaterial.objects.filter(requisicao_user=requisicao) if requisicao.tipo == 'user' else DevolucaoMaterial.objects.filter(requisicao_uo=requisicao)
    url = 'almoxarifado/templates/requisicao_detalhe.html'
    dicionario = dict(requisicao=requisicao, pode_remover=pode_remover, pode_responder=pode_responder, pode_devolver=pode_devolver)
    if pode_responder:
        url = 'almoxarifado/templates/form_requisicao_resposta.html'
    elif not pode_ver or (pode_ver and requisicao.avaliada):
        dicionario['itens_devolvidos'] = itens_devolvidos

    return render(url, dicionario)


@group_required('Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def requisicao_remover(request, tipo, requisicao_id):
    requisicao = RequisicaoAlmox.get(tipo, requisicao_id)
    if requisicao.user_can_delete(request.user):
        requisicao.delete()
        return httprr('/almoxarifado/requisicao_busca/', 'Remoção de Requisição realizada com sucesso.')
    else:
        raise PermissionDenied()


@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
def requisicao_resposta(request, tipo, objeto_id):
    try:
        requisicao = RequisicaoAlmox.get(tipo, objeto_id)
    except Exception:
        raise PermissionDenied()
    itens_id = request.POST.getlist('idRequisicoesMaterial')
    try:
        quantidades_aceitas = [int(i) for i in request.POST.getlist('quantidadesAceitas')]
        respostas = dict_from_keys_n_values(itens_id, quantidades_aceitas)
        requisicao.avaliar(respostas, request)
    except Exception as e:
        return httprr('/almoxarifado/requisicoes_pendentes/', str(e), 'error')
    msg = 'Saída de Material Realizada. Detalhes: <a href="/almoxarifado/requisicao_detalhe/{}/{}/">HTML</a> | <a href="/almoxarifado/relatorio/nota_fornecimento_pdf/{}/{}/">PDF</a>'.format(
        tipo, objeto_id, tipo, objeto_id
    )
    return httprr(
        '/almoxarifado/requisicoes_pendentes/',
        mark_safe(msg),
    )


@permission_required('almoxarifado.pode_ver_todas_requisicoes_usuario, almoxarifado.pode_ver_requisicoes_usuario_do_campus')
@rtr()
def requisicao_busca(request):
    """
    Retorna e processa o formulário para busca de requisições e exibe o resultado.

    """
    title = 'Buscar Requisição'
    usuario = request.user

    uo_usuario = usuario.get_vinculo().setor.uo
    FormClass = RequisicaoBuscaFormFactory(usuario)

    if request.method == 'GET' and len(request.GET):
        form = FormClass(request.GET)
        if form.is_valid():
            # Verificação de tipos de requisições que podem ser buscadas pelo usuário
            cleaned_data = form.cleaned_data.copy()

            tipo = cleaned_data.pop('tipo')
            requisicoes = None

            if tipo == 'usuario' and (
                usuario.has_perm('almoxarifado.pode_ver_requisicoes_usuario_do_campus') or usuario.has_perm('almoxarifado.pode_ver_todas_requisicoes_usuario')
            ):
                requisicoes = RequisicaoAlmoxUser.objects.all()
                requisicoes = requisicoes.filter(uo_fornecedora=uo_usuario)
            elif tipo == 'uo' and usuario.has_perm('almoxarifado.pode_ver_requisicoes_uo_do_campus'):
                requisicoes = RequisicaoAlmoxUO.objects.all()
                requisicoes = requisicoes.filter(Q(uo_fornecedora=uo_usuario.id) | Q(uo_solicitante=uo_usuario.id))

            dict_filtros = dict()

            recursivo = cleaned_data.pop('recursivo')
            material = cleaned_data.pop('material')

            for campo, valor in list(cleaned_data.items()):
                if valor is None:
                    continue

                if campo == 'campus_fornecedor':
                    dict_filtros['uo_fornecedora'] = valor
                elif campo == 'data_inicial':
                    dict_filtros['data__gt'] = valor
                elif campo == 'data_final':
                    dict_filtros['data__lt'] = somar_data(valor, 1)
                elif campo == 'solicitante':
                    dict_filtros['vinculo_solicitante'] = valor
                elif campo == 'setor':
                    if recursivo:
                        lista = []
                        if tipo == 'usuario':
                            lista.append(valor.id)
                            for id in valor.ids_descendentes:
                                lista.append(id)
                            dict_filtros['setor_solicitante__id__in'] = lista
                        else:
                            lista = []
                            for descendente in valor.descendentes:
                                lista.append(descendente.uo and descendente.uo.id or None)
                            dict_filtros['uo_solicitante__id__in'] = lista
                    else:
                        if tipo == 'usuario':
                            requisicoes = requisicoes.filter(setor_solicitante__id=valor.id)
                        else:
                            requisicoes = requisicoes.filter(uo_solicitante__id=valor.uo and valor.uo.id or None)
                else:
                    dict_filtros[campo] = valor

            requisicoes = requisicoes.filter(**dict_filtros)

            if material:
                requisicoes = requisicoes.filter(item_set__material=material, item_set__movimentoalmoxsaida__qtd__gt=0)
    else:
        form = FormClass()

    return locals()


@group_required(TODOS_GRUPOS_ALMOXARIFADO)
@rtr()
def material_historico(request, material_id, uo_id=None):
    title = 'Histórico de Movimentação de Material'
    material = get_object_or_404(MaterialConsumo, pk=material_id)

    if uo_id:
        uos = [UnidadeOrganizacional.objects.suap().get(pk=uo_id)]
    else:
        uos = UnidadeOrganizacional.objects.suap().order_by('setor__sigla')

    historicos = OrderedDict()
    for uo in uos:
        movimentos = historico_movimentacao(material, uo)
        if movimentos:
            historicos[str(uo)] = movimentos
        try:
            materialestoque = MaterialEstoque.objects.get(material=material, uo=uo)
        except Exception:
            materialestoque = MaterialEstoque.objects.create(material=material, uo=uo, valor_medio=0, quantidade=0)
        valor_medio = materialestoque.valor_medio
        estoque = materialestoque.quantidade
    return locals()


@rtr()
@login_required()
def balancete_material(request):
    """
    Exibe formulário a ser preenchido com dados para obter o balancete de material de consumo.

    Exibe relatório do balancete de material de consumo e link para geração do PDF correspondente.
    """
    title = 'Balancete de Material de Consumo'

    # Bloqueio do acesso à funcionalidade com base nas permissões do usuário.
    if not user_has_one_of_perms(request.user, ['almoxarifado.pode_ver_relatorios_todos', 'almoxarifado.pode_ver_relatorios_do_campus']):
        raise PermissionDenied()

    FormClass = BalanceteMaterialFormFactory(request.user)

    if request.method == 'POST':
        form = FormClass(request.POST)
        if form.is_valid():
            data_ini = form.cleaned_data['faixa'][0]
            data_fim = form.cleaned_data['faixa'][1]
            uo = form.cleaned_data['uos']
            estoque = form.cleaned_data['estoque']
            return relatorio_balancete_material(data_ini, data_fim, uo, estoque, request)
    else:
        form = FormClass()

    return locals()


@group_required('Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico, Auditor')
@rtr()
def situacao_estoque(request):
    uo = request.user.get_vinculo().setor.uo
    title = "Situação do Estoque " '{}'.format(uo)
    configuracoes = ConfiguracaoEstoque.objects.all().filter(uo=uo).order_by('material__nome')
    return locals()


@group_required('Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico, Auditor')
@rtr()
def configuracao_estoque(request):
    title = "Controle de Estoque de Materiais"
    uo = request.user.get_vinculo().setor.uo
    if request.method == 'POST':
        if 'ids' in request.POST:
            form = ConfiguracaoEstoqueForm(None, initial={'uo': uo})
            ids = request.POST.getlist('ids')
            for id in ids:
                ce = ConfiguracaoEstoque.objects.get(id=id)
                ce.delete()
        else:
            form = ConfiguracaoEstoqueForm(request.POST, initial={'uo': uo})

            if form.is_valid():
                if form.cleaned_data.get('categoria'):  # filtro por categoria
                    categoria = form.cleaned_data['categoria']
                    intervalo_aquisicao = form.cleaned_data['intervalo_aquisicao']
                    tempo_aquisicao = form.cleaned_data['tempo_aquisicao']
                    for material in categoria.materialconsumo_set.all():
                        if MovimentoAlmoxEntrada.objects.filter(uo=uo).filter(material=material).exists():
                            if not ConfiguracaoEstoque.objects.filter(uo=uo).filter(material=material).exists():
                                ce = ConfiguracaoEstoque()
                                ce.material = material
                                ce.intervalo_aquisicao = intervalo_aquisicao
                                ce.tempo_aquisicao = tempo_aquisicao
                                ce.uo = uo
                                ce.save()
                else:  # filtro por produto
                    intervalo_aquisicao = form.cleaned_data['intervalo_aquisicao']
                    tempo_aquisicao = form.cleaned_data['tempo_aquisicao']
                    material = form.cleaned_data['material']

                    ce = None
                    try:  # material existente
                        ce = ConfiguracaoEstoque.objects.get(uo=uo, material=material)
                    except ConfiguracaoEstoque.DoesNotExist:  # material novo
                        ce = ConfiguracaoEstoque()

                    ce.material = material
                    ce.intervalo_aquisicao = intervalo_aquisicao
                    ce.tempo_aquisicao = tempo_aquisicao
                    ce.uo = uo
                    ce.save()
    else:
        form = ConfiguracaoEstoqueForm(None, initial={'uo': uo})
    configuracaoes = ConfiguracaoEstoque.objects.all().filter(uo=uo).order_by('material__nome')

    return locals()


@group_required('Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico')
@rtr()
def relatorio_compra(request):
    uo = request.user.get_vinculo().setor.uo
    title = 'Lista de Compras ' '{}'.format(uo)
    registros = []
    total = 0
    if 'id' in request.GET:
        id_list = request.GET.getlist('id')
        for id in id_list:
            sufixo = str(id)
            material = MaterialConsumo.objects.all().get(pk=id)
            try:
                valor = (request.GET['valor' + sufixo]).replace(',', '.')
                valor = float(valor)
                qtd = float(request.GET['qtd' + sufixo])
            except (ValueError, KeyError):
                return httprr('..', 'Valores escolhidos inválidos.', 'error')
            parcial = valor * qtd
            total += parcial
            title = "Situação do Estoque " '{}'.format(uo)
            registro = {"material": material, "valor": format_money('{}'.format(valor)), "qtd": qtd, "parcial": format_money('{}'.format(parcial))}
            registros.append(registro)
        total = format_money('{}'.format(total))
    if 'pdf' in request.GET and request.GET['pdf'] == '1':
        return relatorio_compra_pdf(request, registros, total)
    else:
        return locals()


def relatorio_compra_pdf(request, registros, total):
    uo = request.user.get_vinculo().setor.uo
    topo = get_topo_pdf('Relatório de Compras')
    servidor = request.user.get_relacionamento()
    info = [["UO", uo], ["Servidor", servidor], ["Data", datetime.today().strftime("%d/%m/%Y")], ["Total", f'R$ {total}']]
    dados = [['Material', 'Valor (R$)', 'Quantidade', 'Parcial (R$)']]
    for registro in registros:
        dados.append([registro['material'], registro['valor'], registro['qtd'], registro['parcial']])
    tabela_info = pdf.table(info, grid=0, w=[30, 100])
    tabela_dados = pdf.table(dados, head=1, zebra=1, w=[90, 20, 20, 20], count=1)
    body = topo + [tabela_info, pdf.space(8), tabela_dados]
    return PDFResponse(pdf.PdfReport(body=body).generate())


@group_required(TODOS_GRUPOS_ALMOXARIFADO)
@rtr()
def materiais_transferidos(request):
    """
    Retorna e processa o formulário para busca de itens solicitados por pessoa em determinado periodo.
    """
    title = "Materiais Transferidos"
    usuario = request.user
    FormClass = NotasFornecimentoFormFactory(usuario)
    total = ''
    if request.method == 'GET' and len(request.GET):
        form = FormClass(request.GET)
        if form.is_valid():
            requisicoes = RequisicaoAlmoxUO.objects.all()
            data_inicio = form.cleaned_data.get('data_inicial')
            data_fim = form.cleaned_data.get('data_final')
            vinculo_solicitante = form.cleaned_data.get('vinculo_solicitante')
            data_fim_mais_um_dia = somar_data(data_fim, 1)
            requisicoes = requisicoes.filter(vinculo_solicitante=vinculo_solicitante, data__gt=data_inicio, data__lt=data_fim_mais_um_dia)
            total_requisicoes = 0
            contador_itens = 0
            for requisicao in requisicoes:
                for item in requisicao.get_itens_aceitos():
                    total_requisicoes += item.valor()
                    contador_itens += 1
    else:
        form = FormClass()

    return locals()


@rtr()
@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico, Auditor')
def balancete_ed(request):
    title = 'Balancete de Elemento de Despesa'
    formClass = GetBalanceteEdForm(request)
    if request.method == 'POST':
        form = formClass(request.POST)
        if form.is_valid():
            return relatorio_balancete_ed(form.cleaned_data, request)
    else:
        form = formClass()

    return locals()


@rtr()
def saldo_ed(request):
    title = 'Relatório Saldo Atual por Elemento de Despesa'
    lista_campi = []
    form = RelatorioSaldoAtualEDForm(request.POST or None, request=request)
    uos = UnidadeOrganizacional.objects.uo().all()
    total_geral = 0

    def format(m):
        if isinstance(m, MovimentoAlmoxSaida):
            m.valor = -m.valor
            m.qtd = -m.qtd
        m.total = abs(m.valor) * m.qtd
        return m

    if form.is_valid():
        uo = form.cleaned_data['campus']
        lista_ed = []
        for c in CategoriaMaterialConsumo.objects.exclude(codigo='63').order_by('codigo'):
            total = 0
            materiais = MaterialConsumo.objects.com_estoque_por_uo(uo=uo)
            materiais = materiais.filter(categoria=c)
            for material in materiais:
                e = [(m.data, m.id, format(m)) for m in material.movimentoalmoxentrada_set.filter(uo=uo)]
                s = [(m.data, m.id, format(m)) for m in material.movimentoalmoxsaida_set.filter(uo=uo)]
                movimentos = e + s
                movimentos.sort()
                movimentos = [i[2] for i in movimentos]
                total += sum(i.total for i in movimentos)
            infos = dict()
            infos['categoria'] = c
            infos['saldo'] = total
            total_geral += total
            lista_ed.append(infos)
    return locals()


def montar_tabela_elemento_despesa(user, metodo_entrada, metodo_saida, uo_id, data_ini, data_fim):
    datas = [data_ini, data_fim]
    data_anterior = calendario.somarDias(data_ini, -1)

    cabecalhos_tabela = [
        [
            dict(valor='Material', alinhamento='center', largura=90, colspan=2),
            dict(valor='Estoque em', alinhamento='center', largura=90, colspan=1),
            dict(valor='Entradas', alinhamento="center", largura=60, colspan=5),
            dict(valor='Saídas', alinhamento='center', largura=60, colspan=3),
            dict(valor='Estoque em', alinhamento='center', largura=20, colspan=1),
        ],
        [
            dict(valor='Cod.', alinhamento='center', largura=10, colspan=1),
            dict(valor='Nome', alinhamento='left', largura=80, colspan=1),
            dict(valor='Estoque {}'.format(data_anterior.strftime('%d/%m/%Y')), alinhamento='right', largura=20, colspan=1),
            dict(valor='Compra', alinhamento="right", largura=20, colspan=1),
            dict(valor='Transf.', alinhamento="right", largura=20, colspan=1),
            dict(valor='Doação', alinhamento="right", largura=20, colspan=1),
            dict(valor='Devolução', alinhamento="right", largura=20, colspan=1),
            dict(valor='Total', alinhamento='right', largura=20, colspan=1),
            dict(valor='Consumo', alinhamento='right', largura=20, colspan=1),
            dict(valor='Transf.', alinhamento='right', largura=20, colspan=1),
            dict(valor='Total', alinhamento='right', largura=20, colspan=1),
            dict(valor='Estoque {}'.format(datas[1].strftime('%d/%m/%Y')), alinhamento='right', largura=20, colspan=1),
        ],
    ]

    corpo_tabela = []
    # XXX: A categoria 63 é excluída do relatório de forma hard-coded porque a categoria
    #      é uma gambiarra para empenhos do tipo serviço. Os servços não devem aparecer
    #      no balancete ED. O balancete material considera a categoria 63.

    for c in CategoriaMaterialConsumo.objects.exclude(codigo='63').order_by('codigo'):
        estoque_anterior = c.estoque(data=data_anterior, uo_id=uo_id)
        estoque_fim_periodo = c.estoque(data=datas[1], uo_id=uo_id)

        # entrada
        c.__getattribute__(metodo_entrada)(datas, uo_id)
        entrada_transferencia = c.__getattribute__('entrada_transferencia')(datas, uo_id)
        entrada_compra = c.__getattribute__('entrada_normal')(datas, uo_id)
        entrada_doacao = c.__getattribute__('entrada_doacao')(datas, uo_id)
        devolucao = c.__getattribute__('devolucao')(datas, uo_id)

        # saída
        saida_consumo = c.__getattribute__('saida_normal')(datas, uo_id)
        saida_transferencia = c.__getattribute__('saida_transferencia')(datas, uo_id)
        c.__getattribute__(metodo_saida)(datas, uo_id)

        corpo_tabela.append(
            [
                c.codigo,
                c.nome,
                mask_money(estoque_anterior.get('valor')),  # estoque (1 período)
                mask_money(entrada_compra.get('valor')),  # Ent. Compra
                mask_money(entrada_transferencia.get('valor')),  # Ent. Transf
                mask_money(entrada_doacao.get('valor')),  # Ent. Doação
                mask_money(devolucao.get('valor')),  # Ent. Doação
                mask_money(entrada_compra.get('valor') + entrada_transferencia.get('valor') + entrada_doacao.get('valor') + devolucao.get('valor')),  # Ent. Total
                mask_money(saida_consumo.get('valor')),  # Saída Consumo
                mask_money(saida_transferencia.get('valor')),  # Saída Transf
                mask_money(saida_consumo.get('valor') + saida_transferencia.get('valor')),  # Saida Total
                mask_money(estoque_fim_periodo.get('valor')),  # estoque (2 período)
            ]
        )
    linha_total = [
        '-',
        'Todos os Elementos de Despesa',
        mask_money(somar_indice(corpo_tabela, 2)),
        mask_money(somar_indice(corpo_tabela, 3)),
        mask_money(somar_indice(corpo_tabela, 4)),
        mask_money(somar_indice(corpo_tabela, 5)),
        mask_money(somar_indice(corpo_tabela, 6)),
        mask_money(somar_indice(corpo_tabela, 7)),
        mask_money(somar_indice(corpo_tabela, 8)),
        mask_money(somar_indice(corpo_tabela, 9)),
        mask_money(somar_indice(corpo_tabela, 10)),
        mask_money(somar_indice(corpo_tabela, 11)),
    ]
    corpo_tabela.append(linha_total)

    tabela = dict(cabecalhos=cabecalhos_tabela, dados=corpo_tabela)
    uo = uo_id and UnidadeOrganizacional.objects.suap().get(id=uo_id) or 'Todas as Unidades Organizacionais'

    periodo = 'Unidade Organizacional: {}<br/>Período: {}'.format(uo, extrair_periodo(data_ini, data_fim))

    setor_pessoa_logada = user.get_vinculo().setor
    uo_pessoa_logada = setor_pessoa_logada.uo

    dados = dict(
        cabecalho=dict(orgao=Configuracao.get_valor_por_chave('comum', 'instituicao'), uo=uo_pessoa_logada.__str__(), setor=setor_pessoa_logada.__str__()),
        data=data_extenso(),
        titulo='Balancete Elemento de Despesa de Material de Consumo',
        elementos=[periodo, tabela],
        cidade=uo_pessoa_logada.municipio,
    )

    return {'titulo': dados['titulo'], 'periodo': periodo, 'tabela': tabela}


def obtem_transferencias(categoria_material_consumo, datas, uo_id):
    transferencias = MovimentoAlmoxEntrada.objects.filter(material__in=categoria_material_consumo.materialconsumo_set.all(), requisicao_uo_material__isnull=False)
    if datas:
        if len(datas) == 1:
            transferencias = transferencias.filter(data__lt=calendario.somarDias(datas[0], 1))
        else:
            data_inicial = datas[0]
            data_inicial = datetime(data_inicial.year, data_inicial.month, data_inicial.day, 0, 0, 0)

            data_final = datas[1]
            data_final = datetime(data_final.year, data_final.month, data_final.day, 23, 59, 59)

            transferencias = transferencias.filter(data__range=[data_inicial, data_final])
    if uo_id:
        transferencias = transferencias.filter(Q(uo__id=uo_id) | Q(movimento_saida__uo__id=uo_id))

    return transferencias


def processar_transferenicas(corpo_tabela, categoria_material_consumo, entradas):
    total = 0
    for entrada in entradas:
        valor = float(entrada.qtd * entrada.valor)
        corpo_tabela.append(
            [
                '<a href="{}">Ver Requisição</a>'.format(entrada.requisicao_uo_material.requisicao.get_absolute_url()),
                '{}'.format(categoria_material_consumo),
                entrada.requisicao_uo_material.requisicao.uo_fornecedora,
                entrada.requisicao_uo_material.requisicao.uo_solicitante,
                mask_money("{}".format(valor)),
            ]
        )
        total += valor
    return total


def montar_tabela_agrupar_elemento_despesa(user, metodo_entrada, metodo_saida, uo_id, data_ini, data_fim):
    # Período: 01/06/2015 até 01/08/2015
    datas = [data_ini, data_fim]
    calendario.somarDias(data_ini, -1)
    cabecalhos_tabela = [
        [
            dict(valor='Requisição', alinhamento='center', largura=90, colspan=1),
            dict(valor='Elemento de Despesa', alinhamento='center', largura=90, colspan=1),
            dict(valor='Campus Fornecedor', alinhamento='center', largura=90, colspan=1),
            dict(valor='Campus Solicitante', alinhamento="center", largura=60, colspan=1),
            dict(valor='Valor', alinhamento='center', largura=60, colspan=1),
        ]
    ]
    corpo_tabela = []
    total_geral = 0
    for categoria_material_consumo in CategoriaMaterialConsumo.objects.exclude(codigo='63').order_by('codigo'):
        # entrada
        transferencias = obtem_transferencias(categoria_material_consumo, datas, uo_id)
        total = processar_transferenicas(corpo_tabela, categoria_material_consumo, transferencias)
        if total > 0:
            total_geral += total
            corpo_tabela.append(['-', 'Total de transferências com {}'.format(categoria_material_consumo), '-', '-', mask_money(total)])
    # OK - Monte a tabela para apresentacao.
    linha_total = ['-', 'Valor total movimentado', '-', '-', mask_money(total_geral)]
    corpo_tabela.append(linha_total)
    tabela = dict(cabecalhos=cabecalhos_tabela, dados=corpo_tabela)
    uo = uo_id and UnidadeOrganizacional.objects.suap().get(id=uo_id) or 'Todas as Unidades Organizacionais'
    periodo = 'Unidade Organizacional: {}<br/>Período: {}'.format(uo, extrair_periodo(data_ini, data_fim))

    return {'titulo': 'Agrupar por elemento de despesa', 'periodo': periodo, 'tabela': tabela}


def relatorio_balancete_ed(cleaned_data, request):
    user = request.user
    data_ini = cleaned_data['faixa'][0]
    data_fim = cleaned_data['faixa'][1]
    uo = cleaned_data['uos']
    if in_group(user, 'Coordenador de Almoxarifado Sistêmico, Auditor'):
        # Gerente sistêmico e Auditor pode escolher a Unidade Organizacional.
        uo_id = (uo and uo.id) or None
    else:
        uo_id = uo.id

    if uo_id:
        metodo_entrada = 'entrada'
        metodo_saida = 'saida'
    else:
        # Todas as UO's devem desconsiderar transferência entre elas.
        metodo_entrada = 'entrada_normal'
        metodo_saida = 'saida_normal'

    tabela_balancete_ed = montar_tabela_elemento_despesa(request.user, metodo_entrada, metodo_saida, uo_id, data_ini, data_fim)
    tabela_agrupar_elemento_depesa = montar_tabela_agrupar_elemento_despesa(request.user, metodo_entrada, metodo_saida, uo_id, data_ini, data_fim)
    #
    title = 'Balancete Elemento de Despesa de Material de Consumo'
    tabela_balancete_ed['tabela'] = montar_tabela_html(tabela_balancete_ed['tabela'], destacar_ultima=True)
    tabela_agrupar_elemento_depesa['tabela'] = montar_tabela_html(tabela_agrupar_elemento_depesa['tabela'], destacar_ultima=True)
    return render(
        'relatorio/relatorio_balancete_ed.html', {'title': title, 'tabela_balancete_ed': tabela_balancete_ed, 'tabela_agrupar_elemento_depesa': tabela_agrupar_elemento_depesa}
    )


@rtr()
@login_required
def gerar_etiquetas(request):
    title = 'Gerar Etiquetas'
    form = TipoEtiquetaForm(request.POST or None)
    if form.is_valid():
        if request.GET.get('tab') == 'tab_estoque_atual':
            materiais = MaterialConsumo.objects.com_estoque_por_uo(get_uo(request.user))
        elif request.GET.get('tab') == 'tab_teve_estoque_em_meu_campus':
            materiais = MaterialConsumo.objects.teve_estoque_por_uo(get_uo(request.user))
        else:
            materiais = MaterialConsumo.objects.all()
        if 'categoria__id__exact' in list(request.GET.keys()):
            materiais = materiais.filter(categoria__id__exact=request.GET.get('categoria__id__exact'))
        if 'q' in list(request.GET.keys()):
            materiais = materiais.filter(search__icontains=to_ascii(request.GET.get('q')))
        rows = []
        for obj in materiais:
            row = [obj.codigo, obj.nome]
            rows.append(row)
        labels = factory("Pimaco", form.data['tipoetiqueta'])
        f = io.BytesIO()
        labels.generate(rows, f)
        f.seek(0)
        return PDFResponse(f.read(), nome='Etiquetas.pdf')
    return locals()


@rtr()
@login_required
def devolver_item(request, tipo, uo, requisicao):
    title = 'Devolver Item'
    try:
        requisicao = RequisicaoAlmox.get(tipo, requisicao)
    except Exception:
        raise PermissionDenied()

    FormClass = DevolucaoItemFormFactory(requisicao)
    form = FormClass(request.POST or None, uo=uo)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return httprr('..', 'Itens devolvidos com sucesso.')
    return locals()


@rtr()
@login_required()
def atualizar_valor_medio(request, uo_sigla, material):
    uo = UnidadeOrganizacional.objects.suap().get(sigla=uo_sigla)
    calcula_valor_medio_atual(uo, material)

    return httprr(request.META.get('HTTP_REFERER', '..'), 'Atualização realizada.')


@rtr()
@login_required()
def atualizar_movimentacoes(request, uo_sigla, material):
    uo = UnidadeOrganizacional.objects.suap().get(sigla=uo_sigla)
    ajusta_entradas_de_transferencias(uo, material)

    return httprr(request.META.get('HTTP_REFERER', '..'), 'Atualização realizada.')
