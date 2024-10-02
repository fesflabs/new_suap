import datetime
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models.aggregates import Max, Sum
from django.shortcuts import get_object_or_404
from django.utils import html
from reportlab.lib.units import mm
from reportlab.platypus import Frame

from comum.models import Configuracao
from comum.relatorios import get_topo_com_titulo, rodape_data_e_assinatura, rodape_data_e_duas_assinaturas
from comum.utils import OPERADOR_PATRIMONIO, data_extenso, data_normal, extrair_periodo, get_setor, get_topo_pdf, get_uo
from djtools import db, pdf
from djtools.relatorios.relatorio_pdf import RelatorioPDF
from djtools.relatorios.utils import montar_elementos_html, montar_paragrafo
from djtools.templatetags.filters import format_money
from djtools.utils import group_required, httprr, mask_money, render, rtr, calendario
from djtools.utils.response import PDFResponse
from patrimonio import tasks
from patrimonio.forms import (
    FormDepreciacaoPlanoContabilNovo,
    FormInventarioDepreciacao,
    FormRelatorioTotal,
    FormRelatorioTotalPeriodo,
    TermosFormFactory,
)
from patrimonio.models import (
    Baixa,
    CategoriaMaterialPermanente,
    Cautela,
    CautelaInventario,
    EntradaPermanente,
    HistoricoCatDepreciacao,
    Inventario,
    InventarioCargaContabil,
    InventarioValor,
    MovimentoPatrim,
    MovimentoPatrimTipo,
    RelatorioPatrim,
    Requisicao,
    RequisicaoHistorico,
    RequisicaoItem,
)
from patrimonio.pdf import get_corpo_nada_consta, get_corpo_nada_consta_inventario_uso_pessoal
from rh.models import UnidadeOrganizacional


@rtr()
def termos(request):
    """
    Cria termos de responsabilidade, recebimento, anual e nada consta
    """
    title = 'Termos'
    usuario = request.user
    if not usuario.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')

    FormClass = TermosFormFactory(usuario)

    if request.GET:
        form = FormClass(request.GET)
        if form.is_valid():
            return termos_processar(request, form.cleaned_data, usuario)
    else:
        form = FormClass()
        if usuario.eh_servidor:
            form.initial = dict(servidor=usuario.get_relacionamento(), tipo='responsabilidade')
        else:
            form.initial = dict(tipo='responsabilidade')
    return locals()


@rtr('patrimonio/templates/relatorio/termo_relatorio.html')
def termos_processar(request, cleaned_data, user):
    """
    Referente aos termos de responsabilidade, recebimento e anual.
    Guarda o dicionário de dados na sessão.
    """
    servidor = cleaned_data.get('servidor')
    tipo_termo = cleaned_data.get("tipo")
    data_ini = cleaned_data.get('periodo_de_movimento_ini')
    data_fim = cleaned_data.get('periodo_de_movimento_fim')
    ano = cleaned_data.get('ano')
    pessoa_logada = user.get_profile()

    # Argumentos que serão passados para Inventario.get_inventarios_carga_user
    args = dict(tipo=tipo_termo)

    if tipo_termo == 'responsabilidade':
        titulo = 'Termo de Responsabilidade'
        data_ini = ''
        data_fim = ''

    elif tipo_termo == 'recebimento':
        titulo = 'Termo de Recebimento (%s)' % (extrair_periodo(data_ini, data_fim))
        datas = [data_ini, data_fim]
        args['datas'] = datas
        data_ini = data_normal(data_ini)
        data_fim = data_normal(data_fim)

    elif tipo_termo == 'anual':
        ano_anterior = ano
        titulo = 'Termo Anual (%s)' % ano_anterior
        args['ano'] = ano_anterior
        args['orderby'] = 'descricao'
        data_ini = ''
        data_fim = ''

    elif tipo_termo == 'nada_consta_desligamento' or tipo_termo == 'nada_consta_remanejamento':
        titulo = 'Termo de Nada Consta'
        data_ini = ''
        data_fim = ''

    # lista cargas
    dados = Inventario.get_inventarios_carga_user(servidor, **args)
    if not dados['inventarios'] and tipo_termo != 'nada_consta_desligamento' and tipo_termo != 'nada_consta_remanejamento':
        return httprr('.', 'Nenhum inventário a ser exibido.', 'error')

    if tipo_termo == 'anual':
        cabecalhos_tabela = [
            [
                dict(valor='#', alinhamento='center', largura=10, colspan=1),
                dict(valor='Número', alinhamento='right', largura=20, colspan=1),
                dict(valor='Descrição', alinhamento='left', largura=85, colspan=1),
                dict(valor='Valor', alinhamento='right', largura=20, colspan=1),
            ]
        ]

    elif tipo_termo == 'nada_consta_desligamento':
        if dados['inventarios'].exists():
            return httprr('.', 'Não é possível emitir nada consta, pois servidor tem carga.', 'error')
        else:
            return httprr(
                '/patrimonio/relatorio/termos_pdf?'
                + urllib.parse.urlencode({'servidor': servidor.id, 'tipo': tipo_termo, 'periodo_de_movimento_ini': data_ini, 'periodo_de_movimento_fim': data_fim})
            )

    elif tipo_termo == 'nada_consta_remanejamento':
        if dados['inventarios'].filter(tipo_uso_pessoal__isnull=True).exists():
            return httprr('.', 'Não é possível emitir nada consta, pois servidor tem carga.', 'error')

        return httprr(
            '/patrimonio/relatorio/termos_pdf?'
            + urllib.parse.urlencode({'servidor': servidor.id, 'tipo': tipo_termo, 'periodo_de_movimento_ini': data_ini, 'periodo_de_movimento_fim': data_fim})
        )

    else:
        cabecalhos_tabela = [
            [
                dict(valor='#', alinhamento='center', largura=10, colspan=1),
                dict(valor='Número', alinhamento='right', largura=15, colspan=1),
                dict(valor='Descrição', alinhamento='left', largura=75, colspan=1),
                dict(valor='Est. Conservação', alinhamento='center', largura=25, colspan=1),
                dict(valor='Lotação', alinhamento='center', largura=30, colspan=1),
                dict(valor='Sala', alinhamento='center', largura=30, colspan=1),
                dict(valor='Valor', alinhamento='right', largura=20, colspan=1),
            ]
        ]

        # demanda 709
        if tipo_termo == 'responsabilidade':
            cabecalhos_tabela[0] += [dict(valor='Situação', alinhamento='center', largura=30, colspan=1)]

    dados_tabela = []
    valor_total = 0
    if tipo_termo == 'anual':
        index = 0
        descricoes = dados['descricoes']
        for item in dados['inventarios']:
            valor = item['valor']
            numero = item['numero']
            id = item['id']
            descricao = descricoes[id] if id in descricoes else item['entrada_permanente__descricao']
            url = "/patrimonio/inventario/%i/" % numero
            dados_tabela.append([index + 1, '<a href={}>{}</a>'.format(url, numero), descricao, valor])
            index += 1
            valor_total += float(valor)
        dados_tabela.append(['', '', '', mask_money(valor_total or '0')])

    else:
        descricoes = dados['descricoes']
        for index, item in enumerate(dados['inventarios']):
            valor = item['valor'] or 0
            numero = item['numero']
            id = item['id']
            url = "/patrimonio/inventario/%i/" % numero
            descricao = descricoes[id] if id in descricoes else item['entrada_permanente__descricao']
            lotacao = item['responsavel_vinculo__setor__uo__setor__sigla']
            sala = item['sala__nome']

            dado_tabela = [index + 1, '<a href={}>{}</a>'.format(url, numero), descricao, item['estado_conservacao'] or '-', lotacao, sala, mask_money(valor)]

            # demanda 709
            if tipo_termo == 'responsabilidade':
                # será necessário consultar novamente o item e chamar o atributo 'situacao', que é calculado
                inventario_obj = Inventario.objects.get(id=item['id'])
                dado_tabela += ['{}'.format(inventario_obj.get_situacao_display())]

            dados_tabela.append(dado_tabela)

            valor_total += float(valor)

        totais_tabela = ['', '', '', '', '', mask_money(valor_total or '0')]

        # demanda 709
        if tipo_termo == 'responsabilidade':
            totais_tabela += ['']  # referente à coluna 'Situação'

        dados_tabela.append(totais_tabela)

    tabela = dict(cabecalhos=cabecalhos_tabela, dados=dados_tabela)

    dados = dict(
        cabecalho=dict(orgao=Configuracao.get_valor_por_chave('comum', 'instituicao'), uo=str(get_uo(user)), setor=str(get_setor(user))),
        data=data_extenso(),
        titulo=titulo,
        elementos=['<dl><dt>Responsável:</dt><dd>{} ({})</dd></dl>'.format(servidor.nome, servidor.setor if servidor.setor else "sem setor"), tabela],
        cidade=user.get_vinculo().setor.uo.municipio,
        assinatura_1='Coordenação do Patrimônio',
        assinatura_2=servidor.nome,
    )

    title = dados['titulo']
    titulo = dados['titulo']
    tabela = montar_elementos_html(dados['elementos'])
    if tipo_termo == 'anual':
        link_pdf = '/patrimonio/relatorio/termos_pdf?' + urllib.parse.urlencode({'servidor': servidor.id, 'tipo': tipo_termo, 'ano': ano})
    else:
        link_pdf = '/patrimonio/relatorio/termos_pdf?' + urllib.parse.urlencode(
            {'servidor': servidor.id, 'tipo': tipo_termo, 'periodo_de_movimento_ini': data_ini, 'periodo_de_movimento_fim': data_fim}
        )

    return locals()


def termos_pdf(request):
    usuario = request.user
    if not usuario.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')

    FormClass = TermosFormFactory(request.user)
    form = FormClass(request.GET)
    titulo = ''
    if form.is_valid():
        servidor = form.cleaned_data.get('servidor')
        tipo_termo = form.cleaned_data.get("tipo")
        data_ini = form.cleaned_data.get('periodo_de_movimento_ini')
        data_fim = form.cleaned_data.get('periodo_de_movimento_fim')
        ano = form.cleaned_data.get('ano')
        args = dict(tipo=tipo_termo)

        if tipo_termo == 'responsabilidade':
            titulo = 'Termo de Responsabilidade'
            data_ini = ''
            data_fim = ''

        elif tipo_termo == 'recebimento':
            titulo = 'Termo de Recebimento (%s)' % (extrair_periodo(data_ini, data_fim))
            datas = [data_ini, data_fim]
            args['datas'] = datas
            data_ini = data_normal(data_ini)
            data_fim = data_normal(data_fim)

        elif tipo_termo == 'anual':
            titulo = 'Termo Anual (%s)' % ano
            args['ano'] = ano
            args['orderby'] = 'descricao'
            data_ini = ''
            data_fim = ''

        elif tipo_termo == 'nada_consta_desligamento' or tipo_termo == 'nada_consta_remanejamento':
            titulo = 'Termo de Nada Consta'
            data_ini = ''
            data_fim = ''

        dados_inv = Inventario.get_inventarios_carga_user(servidor, **args)
        topo = get_topo_com_titulo(titulo)
        if tipo_termo == 'nada_consta_desligamento':
            body_nada_consta = topo + get_corpo_nada_consta(servidor.get_vinculo())
            return PDFResponse(pdf.PdfReport(body=body_nada_consta, header_args=None, paper='A4', creation_date=True).generate())

        elif tipo_termo == 'nada_consta_remanejamento':
            uso_pessoal = []
            for invs in dados_inv['inventarios']:
                if invs['tipo_uso_pessoal']:
                    descricao = Inventario.objects.get(id=invs['id']).get_descricao()
                    invs['descricao'] = descricao
                    uso_pessoal.append(invs)

            # se tem inventário de tipo uso pessoal os mesmos devem ser listados no NADA CONSTA
            body_nada_consta = topo
            if uso_pessoal:
                body_nada_consta += get_corpo_nada_consta_inventario_uso_pessoal(request.user, servidor.get_vinculo(), uso_pessoal)
            # se não tem, chama  mesmo relatório utilizado no "nada consta desligamento"
            else:
                body_nada_consta += get_corpo_nada_consta(servidor.get_vinculo())

            return PDFResponse(pdf.PdfReport(body=body_nada_consta, header_args=None, paper='A4', creation_date=True).generate())

        else:
            return tasks.exportar_relatorio_termos_pdf(servidor, args, titulo)

    else:
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')


# TOTALIZAÇÃO POR PERÍODO
def totalizacaoPeriodo(ano):
    meses = []
    for mes in range(1, 13):
        di_mes = datetime.date(ano, mes, 1)
        df_mes = calendario.getUltimoDiaMes(mes, ano)
        meses.append(
            {
                'nome': calendario.getNomeMes(mes),
                'entrada': format_money(RelatorioPatrim.valor_entrada([di_mes, df_mes])),
                'saida': format_money(RelatorioPatrim.valor_saida([di_mes, df_mes])),
                'acumulado': format_money(RelatorioPatrim.valor_acumulado(df_mes)),
            }
        )
    di_ano = datetime.date(ano, 1, 1)
    df_ano = datetime.date(ano, 12, 31)
    ano = {
        'nome': ano,
        'entrada': format_money(RelatorioPatrim.valor_entrada([di_ano, df_ano])),
        'saida': format_money(RelatorioPatrim.valor_saida([di_ano, df_ano])),
        'acumulado': format_money(RelatorioPatrim.valor_acumulado(df_ano)),
    }
    return meses, ano


def totalizacao_periodo_pdf(request):
    if not request.user.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')
    meses, ano = totalizacaoPeriodo(request.session['ano'])
    tabela = [['Período', 'Total Entrada', 'Total Saída', 'Acumulado']]
    for mes in meses:
        tabela.append([mes['nome'], mes['entrada'], mes['saida'], mes['acumulado']])
    tabela.append(['<b>Ano de %s</b>' % ano['nome'], '<b>' + ano['entrada'] + '</b>', '<b>' + ano['saida'] + 'u</b>', '<b>' + ano['acumulado'] + '</b>'])
    cabecalho = pdf.para('Ano: %s' % ano['nome'], alignment='left', style='h2')
    tabela = pdf.table(tabela, w=[45, 45, 45, 45], a=['c', 'c', 'c', 'c'], head=1, zebra=1)
    corpo = get_topo_com_titulo('Totalização por Período') + [cabecalho, pdf.space(10), tabela]
    footer = rodape_data_e_assinatura()
    return PDFResponse(pdf.PdfReport(body=corpo, footer_args=footer).generate())


# TOTALIZAÇÃO POR ELEMENTO DE DESPESA
def total_ed_acumulado_ateh_periodo(mes, ano):
    data_limite = calendario.getUltimoDiaMes(mes, ano)
    categorias = []
    for categoria in CategoriaMaterialPermanente.objects.filter(omitir=False).order_by('codigo'):
        categorias.append(
            {
                'codigo': categoria.codigo,
                'plano_contas': categoria.plano_contas.codigo,
                'nome': categoria.nome,
                'total': format_money(RelatorioPatrim.valor_acumulado(data_limite, categoria.id)),
            }
        )
    valor_acumulado = format_money(RelatorioPatrim.valor_acumulado(data_limite))
    return categorias, valor_acumulado, '{}/{}'.format(calendario.getNomeMes(mes), ano)


def total_ed_acumulado_ateh_periodo_html(request, mes, ano):
    # URLS com valores unicode para mes e ano
    mes = int(mes)
    ano = int(ano)
    if not request.user.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')
    categorias, total_geral, periodo = total_ed_acumulado_ateh_periodo(mes, ano)
    request.session['mes'] = mes
    request.session['ano'] = ano
    return render(
        'patrimonio/templates/relatorio/totalizacaoCategoria.html',
        {'periodo': periodo, 'categorias': categorias, 'total_geral': total_geral, 'title': 'Totalização por Elemento de Despesa'},
    )


def total_ed_acumulado_ateh_periodo_pdf(request):  # refazer!
    if not request.user.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')
    categorias, total_geral, periodo = total_ed_acumulado_ateh_periodo(request.session['mes'], request.session['ano'])
    data = pdf.para('<font size=8.5>' + calendario.getDataExtenso() + '</font>', align='right')
    titulo = get_topo_com_titulo('Totalização por Elemento de Despesa - %s' % periodo)
    tabela = [['Código ED', 'Conta Contábil', 'Nome ED', 'Total']]
    for categoria in categorias:
        tabela.append([categoria['codigo'], categoria['plano_contas'], html.escape(categoria['nome']), categoria['total']])
    tabela.append(['-', '-', 'Todas as Categorias', total_geral])
    tabela = pdf.table(tabela, w=[20, 30, 90, 30], head=1, zebra=1, a=['c', 'c', 'c', 'r'])
    corpo = [data] + titulo + [tabela]
    return PDFResponse(pdf.PdfReport(body=corpo).generate())


# TOTAL POR PERÍODO
@group_required(OPERADOR_PATRIMONIO)
def telaRelatorioTotalizacaoCategoriaPeriodo(request):
    return render('patrimonio/templates/relatorio/totalizacaoCategoriaPeriodo.html', {})


@rtr()
def total_periodo(request):
    title = 'Totalização por Período'
    if not request.user.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')
    if request.GET:
        form = FormRelatorioTotalPeriodo(request.GET)
        if form.is_valid():
            ano = form.cleaned_data['ano']
            request.session['ano'] = ano
            meses, ano = totalizacaoPeriodo(ano)
            return render('patrimonio/templates/relatorio/totalizacaoPeriodo2.html', {'ano': ano, 'meses': meses, 'title': 'Totalização por Período'})
    else:
        form = FormRelatorioTotalPeriodo()
    return locals()


@rtr('patrimonio/templates/relatorio/total_atual_por_campus.html')
def total_atual_por_campus(request):

    title = 'Relatório de Totalização por Campus'
    url = request.META.get('HTTP_REFERER', '.')
    if not request.user.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')

    form = FormRelatorioTotal(request.GET or None)
    if form.is_valid():
        queryset = CategoriaMaterialPermanente.objects.all()
        campus = form.cleaned_data['campus']
        ano = form.cleaned_data['ano']
        mes = form.cleaned_data['mes']
        return tasks.gerar_relatorio_totalizacao_campus(request, queryset, campus, ano, mes)
    return locals()


@rtr()
@login_required()
def total_atual_por_campus_html(request, id_):

    dados = request.session.get(id_)
    if dados:
        campus = dados['campus']
        categorias = dados['categorias']
        total_geral = dados['total_geral']
        data_final = dados['data_final']
        return render('patrimonio/templates/relatorio/totalizacao_campus.html', {'campus': campus, 'categorias': categorias, 'total_geral': total_geral, 'data_final': data_final})
    else:
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')


@rtr()
def total_atual_categoria(request, categoria, campus, data_final):
    categoria = get_object_or_404(CategoriaMaterialPermanente, id=categoria)
    campus = get_object_or_404(UnidadeOrganizacional, pk=campus)
    data_final = datetime.datetime.strptime(data_final, "%Y-%m-%d")
    baixados = Inventario.baixados.filter(entrada_permanente__categoria=categoria,
                                          movimentopatrim__tipo__id=MovimentoPatrimTipo.BAIXA().pk,
                                          movimentopatrim__data__lte=data_final)
    invs_baixa = []
    for b in baixados:
        if MovimentoPatrim.objects.filter(inventario=b, tipo__id=MovimentoPatrimTipo.BAIXA().pk, data__lte=data_final):
            invs_baixa.append(b.id)

    depreciaveis = Inventario.objects.filter(entrada_permanente__categoria=categoria, cargas_contabeis__campus=campus,
                                             cargas_contabeis__data__lte=data_final)
    ids = list()
    for i in depreciaveis:
        cc = InventarioCargaContabil.objects.filter(inventario=i, data__lte=data_final).order_by('-data', '-id')
        if cc.exists():
            if cc[0].campus != campus:
                ids.append(cc[0].inventario.id)
    ids = list(set(ids) | set(invs_baixa))

    inventarios = (
        Inventario.objects.exclude(id__in=ids)
        .filter(entrada_permanente__categoria=categoria, cargas_contabeis__campus=campus, cargas_contabeis__data__lte=data_final)
        .annotate(max=Max('cargas_contabeis__data'))
    )

    total = list(inventarios.aggregate(Sum('entrada_permanente__valor')).values())[0] or 0
    if not request.user.has_perm('patrimonio.pode_ver_relatorios'):
        return httprr('/', 'Você não tem permissão para fazer isso.', 'error')
    return render(
        'patrimonio/templates/relatorio/detalhamento_categoria.html', {'inventarios': inventarios, 'title': 'Relatório de Detalhamento por Campus', 'campus': campus, 'total': total}
    )


def relatorio_categoria_campi(campus, data_final, processo):
    queryset = CategoriaMaterialPermanente.objects.filter(codigo=30).order_by('codigo')
    categorias = []
    total = Decimal("0.0")
    for elem in queryset:
        if processo:
            next(processo)
        invs_baixa = Inventario.baixados.filter(entrada_permanente__categoria=elem, cargas_contabeis__campus=campus, movimentopatrim__tipo__id=MovimentoPatrimTipo.BAIXA().pk, movimentopatrim__data__lte=data_final).values_list('id', flat=True)

        depreciaveis = Inventario.objects.filter(entrada_permanente__categoria=elem, cargas_contabeis__campus=campus, cargas_contabeis__data__lte=data_final)
        ids = list()
        for i in depreciaveis:
            cc = InventarioCargaContabil.objects.filter(inventario=i, data__lte=data_final).annotate(max=Max('data')).order_by('-data', '-id')

            if cc.exists():
                if cc[0].campus != campus:
                    ids.append(cc[0].inventario.id)
        ids = list(set(ids) | set(invs_baixa))

        total_categoria = (
            Inventario.objects.exclude(id__in=ids)
            .filter(entrada_permanente__categoria=elem, cargas_contabeis__campus=campus, cargas_contabeis__data__lte=data_final)
            .annotate(max=Max('cargas_contabeis__data'))
            .aggregate(total=Sum('entrada_permanente__valor'))
        )
        categorias.append(
            {
                "codigo": elem.codigo,
                "nome": elem.nome,
                "id": elem.id,
                "plano_contas": elem.plano_contas.codigo,
                "total": format_money(total_categoria['total'] or 0),
            }
        )
        total += total_categoria['total'] or 0
    total_geral = total
    return categorias, total_geral


@group_required(OPERADOR_PATRIMONIO)
def baixa_pdf(request, baixa_id):  # PDF
    baixa = get_object_or_404(Baixa, id=baixa_id)
    data = pdf.para('<font size=8.5> ' + calendario.getDataExtenso() + '</font>', align='right')
    titulo = get_topo_pdf('Relatório de Baixa')
    cabecalho = [
        ['<b>Número da Portaria:</b>', baixa.numero],
        ['<b>Data da Baixa:</b>', baixa.get_data()],
        ['<b>Motivo da Baixa:</b>', baixa.tipo],
        ['<b>Observação:</b>', baixa.observacao],
    ]
    cabecalho = pdf.table(cabecalho, a=['r', 'l'], grid=0)
    tabela_categorias = [['Código', 'Conta Contábil', 'Descrição', 'Valor Inicial', 'Valor Contábil']]
    for i in baixa.get_total_categoria():
        tabela_categorias.append([i.codigo, i.plano_contas.codigo, i.nome, i.total_inicial, i.total])
    tabela_categorias = pdf.table(tabela_categorias, w=[16, 20, 110, 18, 20], a=['c', 'c', 'l', 'r', 'r'], head=1, zebra=1)
    total_categoria = [['Total', baixa.get_valor_inicial(), baixa.get_valor()]]
    total_categoria = pdf.table(total_categoria, w=[146, 18, 20], a=['c', 'r', 'r'], head=1, zebra=1)
    tabela_inventarios = [['Número', 'Elemento de Despesa', 'Descrição', 'Valor Inicial', 'Valor Atual']]
    total = 0
    total_valor_inicial = 0
    for m in baixa.movimentopatrim_set.all().order_by('inventario__numero'):
        i = m.inventario
        tabela_inventarios.append([i.numero, i.entrada_permanente.categoria.codigo, i.get_descricao(), format_money(i.entrada_permanente.valor), i.get_valor()])
        valor = i.get_valor().replace('.', '')
        total += Decimal(valor.replace(',', '.'))
        total_valor_inicial += i.entrada_permanente.valor

    tabela_total = [['Total', format_money(total_valor_inicial), total]]
    tabela_total = pdf.table(tabela_total, w=[145, 20, 20], a=['c', 'r', 'r'], head=1, zebra=1)

    tabela_inventarios = pdf.table(tabela_inventarios, count=1, w=[15, 15, 105, 20, 20], a=['c', 'c', 'c', 'r', 'r'], head=1, zebra=1)
    corpo = [data] + titulo + [cabecalho, pdf.space(5), tabela_categorias, total_categoria, pdf.space(5), tabela_inventarios, tabela_total]
    return PDFResponse(pdf.PdfReport(body=corpo).generate())


@group_required(OPERADOR_PATRIMONIO)
def termo_cautela_PDF(request, cautela_id):
    cautela = Cautela.objects.get(id=cautela_id)
    cautelainventarios = CautelaInventario.objects.filter(cautela=cautela)
    servidor = request.user.get_relacionamento()
    matricula = servidor.matricula

    data = pdf.para('<font size=8.5>' + calendario.getDataExtenso() + '</font>', align='right')
    titulo = get_topo_pdf('CAUTELA')
    texto1 = pdf.para(
        'Recebi do '
        + Configuracao.get_valor_por_chave('comum', 'instituicao')
        + ', através do servidor {} com matrícula {}, o material abaixo discriminado.'.format(servidor.nome, matricula)
    )
    texto2 = pdf.para('Entendo que o referido material ficará sob a minha responsabilidade até a sua devolução a essa Coordenação.')
    tabela = [['Descrição do Material', 'Nº Patrimônio']]
    for item in cautelainventarios:
        numero = item.inventario.numero
        descricao = item.inventario.get_descricao()
        tabela.append([descricao, numero])
    tabela = pdf.table(tabela, w=[135, 25], head=1, count=1, zebra=1, a=['l', 'c'])
    corpo = [data] + titulo + [texto1, texto2, pdf.space(10), tabela]
    footer = rodape_data_e_duas_assinaturas([Configuracao.get_valor_por_chave('comum', 'instituicao'), cautela.responsavel])
    return PDFResponse(pdf.PdfReport(body=corpo, footer_args=footer).generate())


def totalizacaoCategoriaPeriodo(ano, mes, incluir_doacao):
    # SERVE PARA HTML E PDF
    data_inicial = datetime.date(ano, mes, 1)
    data_final = datetime.date(ano, mes, calendario.getUltimoDia(mes, ano))
    queryset = EntradaPermanente.objects

    if not incluir_doacao:
        queryset = queryset.exclude(entrada__tipo_entrada=2)

    result = (
        queryset.filter(entrada__data__range=[data_inicial, data_final])
        .values('categoria__codigo', 'categoria__plano_contas__codigo', 'categoria__nome')
        .annotate(total=Sum('valor', field='valor *qtd'))
        .order_by('categoria__codigo', 'categoria__plano_contas__codigo', 'categoria__nome')
    )

    total = Decimal("0.0")
    resposta = []
    for item in result:
        total += Decimal(item['total'])
        resposta.append(
            {"codigo": item['categoria__codigo'], "planocontas": item["categoria__plano_contas__codigo"], "nome": item["categoria__nome"], "total": format_money(item["total"])}
        )
    return resposta, format_money(total)


def totalizacaoPlanoContasPeriodo(ano, mes, incluir_doacao):  # SERVE PARA HTML E PDF
    data_inicial = datetime.date(ano, mes, 1)
    data_final = datetime.date(ano, mes, calendario.getUltimoDia(mes, ano))
    query = []
    query.append(
        "select plan.codigo, plan.descricao, sum(emp.valor*emp.qtd) from entrada e, entradapermanente emp, categoriamaterialpermanente cmp, patrimonio_planocontas plan where e.id = emp.entrada_id and emp.categoria_id = cmp.id and cmp.plano_contas_id = plan.id and cmp.omitir = 'False' "
    )
    if not incluir_doacao:
        query.append("and e.tipoentrada_id != 2 ")
    query.append("and e.data between '{}' and '{}' group by plan.codigo, plan.descricao order by plan.codigo, plan.descricao".format(data_inicial, data_final))
    resposta = []
    total = Decimal("0.0")
    for item in db.get_list("".join(query)):
        total += item[2]
        resposta.append({"codigo": item[0], "nome": item[1], "total": format_money(item[2])})
    return resposta, format_money(total)


def get_total_ed_pdf(setores, resposta):
    assinatura1 = 'Coordenaçao do Almoxarifado'
    assinatura2 = 'Direçao do DAP'
    tabela_data = [['&nbsp;', calendario.getDataExtenso()]]
    titulo = pdf.para('Totalização por Elemento de Despesa por Período', style='h1', align='c')
    tabela_info = [['Período:', '<b>' + resposta['mes'] + '/' + str(resposta['ano']) + '</b>']]
    tabela_registros = [['Código', 'Plano de Contas', 'Total']]
    for elem in resposta['resposta']:
        row = [elem['codigo'], elem['nome'], elem['total']]
        tabela_registros.append(row)
    tabela_info = pdf.table(tabela_info, grid=0, w=[20, 150], a=['r', 'l'])
    tabela_data = pdf.table(tabela_data, grid=0, w=[20, 140], a=['l', 'r'])
    tabela_registros = pdf.table(tabela_registros, head=1, zebra=1, w=[20, 110, 30], a=['c', 'l', 'r'])
    tabela_total = [['Total: ', '<b>' + resposta['total'] + '</b>']]
    tabela_total = pdf.table(tabela_total, grid=0, w=[110, 40], a=['r', 'r'])
    setores = pdf.para(str(setores[0]) + '<br />' + str(setores[1]), style='Normal', align='c')
    tabela_cargos = [[assinatura1, assinatura2]]
    tabela_cargos = pdf.table(tabela_cargos, grid=0, w=[80, 80], a=['c', 'c'])
    local = pdf.para('Natal, ______ de ____________________ de __________', align='c')
    linha_assinaturas = pdf.para(
        '<table><tr><td>__________________________________________________</td>'
        '<td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td>'
        '<td>___________________________________________</td></tr>',
        align='c',
    )
    return get_topo_pdf() + [
        setores,
        tabela_data,
        pdf.space(8),
        titulo,
        pdf.space(8),
        tabela_info,
        pdf.space(8),
        tabela_registros,
        tabela_total,
        pdf.space(46),
        local,
        pdf.space(6),
        linha_assinaturas,
        tabela_cargos,
    ]


@group_required(OPERADOR_PATRIMONIO)
def totalizacao_ed_PeriodoPDF(request):
    resposta = request.session['resposta']
    setor = get_setor()
    unidade = get_uo().setor
    setores = [unidade, setor]

    body = get_total_ed_pdf(setores, resposta)
    return PDFResponse(pdf.PdfReport(body=body).generate())


def get_inv_depreciacao(inventarios, mes, ano):
    titulo = pdf.para('Relatório de Depreciação por Itens ', style='h1', align='c')
    data = pdf.para('Período: {}/{}'.format(mes, ano), style='h5', align='c')
    tabela_registros = [['Número', 'Descrição', 'Data Aquisição', 'Data Início de Uso', 'Valor Bruto', 'Valor Depreciado', 'Valor Líquido', 'Valor Depreciado Mês']]
    for elem in inventarios:
        # Valor Liquido
        try:
            valor_depreciavel_inv = InventarioValor.objects.get(inventario=elem, data__month=mes, data__year=ano).valor
            try:
                valor_mensal = InventarioValor.objects.get(inventario=elem, data__month=int(mes) + 1, data__year=ano).valor
                valor_mensal = valor_depreciavel_inv - valor_mensal
            except Exception:
                try:
                    valor_mensal = InventarioValor.objects.get(inventario=elem, data__month=int(mes) - 1, data__year=ano).valor
                    valor_mensal = valor_mensal - valor_depreciavel_inv
                except Exception:
                    valor_mensal = elem.valor - valor_depreciavel_inv

        except Exception:
            valor_depreciavel_inv = 0
        if valor_depreciavel_inv > 0:
            valor_depreciado = elem.entrada_permanente.valor - valor_depreciavel_inv
        else:
            valor_depreciado = 0

        row = [
            elem.numero,
            elem.entrada_permanente.descricao,
            elem.entrada_permanente.entrada.data.date(),
            elem.get_data_carga().date(),
            elem.entrada_permanente.valor,
            valor_depreciado,
            valor_depreciavel_inv,
            valor_mensal,
        ]
        tabela_registros.append(row)
    tabela_registros = pdf.table(tabela_registros, head=1, zebra=1, w=[18, 110, 22, 22, 22, 22, 22, 22], a=['c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'])

    return get_topo_pdf() + [titulo, data, pdf.space(8), tabela_registros]


def get_depreciacao_planocontabil_atual(mes, ano, campus):
    planocontabil = CategoriaMaterialPermanente.objects.all().order_by('plano_contas__codigo')
    total_valor_bruto = 0
    total_valor_liquido = 0
    uo = UnidadeOrganizacional.objects.suap().get(pk=campus.id)
    for elem in planocontabil:
        total_valor_bruto = Inventario.depreciaveis.filter(entrada_permanente__categoria=elem, carga_contabil__campus=uo).aggregate(total=Sum('entrada_permanente__valor'))

        invs = Inventario.depreciaveis.filter(entrada_permanente__categoria=elem, carga_contabil__campus=uo)
        valor_total_mensal = 0
        for inv in invs:
            valor_mensal = 0
            try:
                valor_depreciavel_inv = InventarioValor.objects.get(inventario=inv, data__month=mes, data__year=ano).valor
                try:
                    mes_depreciacao = mes
                    ano_depreciacao = ano
                    if mes == 12:
                        mes_depreciacao = 0
                        ano_depreciacao = ano + 1
                    valor_mensal = InventarioValor.objects.get(inventario=inv, data__month=int(mes_depreciacao) + 1, data__year=ano_depreciacao).valor
                    valor_mensal = valor_depreciavel_inv - valor_mensal
                except Exception:
                    try:
                        mes_depreciacao = int(mes) - 1
                        ano_depreciacao = ano
                        if mes == 1:
                            mes_depreciacao = 12
                            ano_depreciacao = ano - 1

                        valor_mensal = InventarioValor.objects.get(inventario=inv, data__month=int(mes_depreciacao), data__year=ano_depreciacao).valor
                        valor_mensal = valor_mensal - valor_depreciavel_inv
                    except Exception:
                        valor_mensal = inv.entrada_permanente.valor - valor_depreciavel_inv
            except Exception:
                valor_mensal = 0
                valor_depreciavel_inv = 0
            valor_total_mensal += valor_mensal
        total_valor_bruto = total_valor_bruto['total'] or 0
        total_valor_liquido = total_valor_bruto - valor_total_mensal
        HistoricoCatDepreciacao.objects.get_or_create(categoria=elem, mes=mes, ano=ano, campus=uo, defaults=dict(valor_bruto=total_valor_bruto, valor_liquido=total_valor_liquido, valor_depreciado=valor_total_mensal))

    return


def get_depreciacao_planocontabil(mes, ano, campus):
    titulo = pdf.para('Relatório de Depreciação por Contas Contábeis', style='h1', align='c')
    data = pdf.para('Período: {}/{}'.format(mes, ano), style='h5', align='c')
    tabela_registros = [['Conta Contábil', 'Plano de Contas', 'Valor Bruto', 'Valor Líquido', 'Valor Depreciado Mensal']]
    planocontabil = CategoriaMaterialPermanente.objects.all().order_by('plano_contas__codigo')
    totalizador_valor_bruto = 0
    totalizador_valor_liquido = 0
    totalizador_valor_depreciado = 0
    uo = UnidadeOrganizacional.objects.suap().get(pk=campus.id)
    campus = pdf.para('Campus: %s' % (uo), style='h5', align='c')
    for elem in planocontabil:
        categoria = HistoricoCatDepreciacao.objects.filter(categoria=elem, mes=mes, ano=ano, campus=uo).first()
        codigo = '-'
        if elem.plano_contas is not None:
            codigo = elem.plano_contas.codigo
        if categoria:
            row = [codigo, elem.nome, format_money(categoria.valor_bruto), format_money(categoria.valor_liquido), format_money(categoria.valor_depreciado)]
            tabela_registros.append(row)
            totalizador_valor_bruto += categoria.valor_bruto
            totalizador_valor_liquido += categoria.valor_liquido
            totalizador_valor_depreciado += categoria.valor_depreciado
    totalizador = ['-', 'Todas as Categorias', format_money(totalizador_valor_bruto), format_money(totalizador_valor_liquido), format_money(totalizador_valor_depreciado)]
    tabela_registros.append(totalizador)
    tabela_registros = pdf.table(tabela_registros, head=1, zebra=1, w=[23, 113, 41, 41, 42], a=['l', 'l', 'r', 'r', 'r'])
    return get_topo_pdf() + [titulo, data, campus, pdf.space(8), tabela_registros]


@rtr()
@login_required()
def inventario_depreciacao(request):
    title = 'Relatório de Depreciação por Itens'
    form = FormInventarioDepreciacao(request.GET or None)
    if form.is_valid():
        inventarios = Inventario.objects.filter(entrada_permanente__descricao=form.cleaned_data['inventario'].entrada_permanente.descricao)
        body = get_inv_depreciacao(inventarios, form.cleaned_data['mes'], form.cleaned_data['ano'])
        return PDFResponse(pdf.PdfReport(body=body, paper='-A4').generate())
    return locals()


@rtr()
@login_required()
def inventario_depreciacao_planocontabil_novo(request):
    title = 'Relatório de Depreciação por Contas Contábeis'
    form = FormDepreciacaoPlanoContabilNovo(request.GET or None)
    if form.is_valid():
        mes = form.cleaned_data['mes']
        ano = form.cleaned_data['ano']
        campus = form.cleaned_data['campus']
        return tasks.exportar_relatorio_depreciacao_pdf(mes, ano, campus)
    return locals()


def termo_transferencia(request, requisicao_id):
    titulo = 'Termo de Transferência'
    requisicao = get_object_or_404(Requisicao, pk=requisicao_id)
    dados = [['Número', 'Descrição', 'Conservação', 'Lotação', 'Valor']]
    total = 0

    if requisicao.tipo == Requisicao.TIPO_MESMO_CAMPI:
        data_transferencia = RequisicaoHistorico.objects.filter(requisicao=requisicao.id).latest('alterado_em')
    else:
        if requisicao.status == Requisicao.STATUS_DEFERIDA:
            data_transferencia = RequisicaoHistorico.objects.get(requisicao=requisicao.id, status=Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_ORIGEM)
        else:
            data_transferencia = RequisicaoHistorico.objects.filter(requisicao=requisicao.id).latest('alterado_em')

    for item in requisicao.itens.filter(situacao=RequisicaoItem.APROVADO):
        dados.append(
            [
                item.inventario.numero,
                item.inventario.get_descricao_para_pdf(),
                item.inventario.estado_conservacao and item.inventario.get_estado_conservacao_display() or '-',
                item.inventario.sala,
                item.inventario.get_valor(),
            ]
        )
        total = total + (item.inventario.valor)
    total = format_money(total)
    info_total = [['', '', '', '', total]]
    widths = [15, 100, 22, 38, 18]
    tabela_total = pdf.table(info_total, w=widths)
    tabela_dados = pdf.table(dados, head=1, zebra=1, w=widths, count=0, a=['c', 'l', 'c', 'c', 'r'])
    topo = get_topo_com_titulo(titulo)
    servidor_origem = pdf.para('Servidor Origem: %s' % (requisicao.vinculo_origem.relacionamento))
    servidor_destino = pdf.para('Servidor Destino: %s' % (requisicao.vinculo_destino.relacionamento))
    dados_transferencia = pdf.para('Transferência realizada em: %s' % (calendario.datetimeToStr(data_transferencia.alterado_em)))
    body = topo + [servidor_origem, servidor_destino, dados_transferencia, pdf.space(5), tabela_dados, tabela_total, pdf.space(10)]
    return PDFResponse(pdf.PdfReport(body=body, header_args=None, paper='A4', creation_date=True).generate())


class RelatorioTermosPDF(RelatorioPDF):

    def __init__(self, dados):
        RelatorioPDF.__init__(self, dados)
        self.margem_inferior = 60 * mm
        self.rodape = 'Declaro pelo presente documento de responsabilidade que recebi o material acima especificado e que sou responsável direto pelo mesmo e devo observar normas sobre o controle e zelo do material permanente, equipamentos e instalações pertencentes ao Instituto Federal de Educação, Ciência e Tecnologia do RN.'

    def montar_rodape(self, canvas):
        f = Frame(20 * mm, 40 * mm, 170 * mm, 15 * mm, leftPadding=1 * mm, bottomPadding=1 * mm, rightPadding=1 * mm, topPadding=1 * mm, showBoundary=0)
        # NOTA: se o paragrafo não couber no frame, ele não será mostrado.
        f.addFromList([montar_paragrafo(self.rodape)], canvas)
        canvas.setFont('Times-Roman', 9)
        canvas.drawCentredString(105 * mm, 33 * mm, self.data_assinatura)
        canvas.setFont('Times-Roman', 7)
        canvas.setLineWidth(0.1 * mm)
        canvas.line(20 * mm, 24 * mm, 89 * mm, 24 * mm)
        canvas.drawCentredString(54.5 * mm, 21 * mm, self.assinatura_1)
        canvas.line(120 * mm, 24 * mm, 189 * mm, 24 * mm)
        canvas.drawCentredString(154.5 * mm, 21 * mm, self.assinatura_2)
