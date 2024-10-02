# -*- coding: utf-8 -*-
from datetime import date, datetime

from django.core.cache import cache
from django.core.exceptions import PermissionDenied

from almoxarifado import tasks
from almoxarifado.forms import ConsumoSetorForm
from almoxarifado.models import MovimentoAlmoxSaida, RequisicaoAlmox, RequisicaoAlmoxUO, \
    MaterialEstoque
from comum.models import Configuracao
from comum.relatorios import get_topo_com_titulo, rodape_data_e_duas_assinaturas_almoxarifado
from comum.utils import somar_data, data_extenso, extrair_periodo, somar_indice
from djtools import pdf
from djtools.relatorios.relatorio_pdf import RelatorioPDF
from djtools.relatorios.utils import montar_tabela_html
from djtools.utils import render, httprr, randomic, group_required, login_required, rtr, mask_money, calendario
from djtools.utils.response import PDFResponse
from rh.models import Setor, UnidadeOrganizacional


###
# CONSUMO SETOR
###


@rtr()
@group_required('Operador de Almoxarifado, Coordenador de Almoxarifado, Coordenador de Almoxarifado Sistêmico, Auditor')
def consumo_setor(request):
    title = "Saída por Setor"
    if request.method == 'POST':
        form = ConsumoSetorForm(request.POST)
        if form.is_valid():
            dic = consumo_setor_processar(form.cleaned_data, request.user)
            id_ = randomic()
            request.session[id_] = dic
            return httprr('/almoxarifado/relatorio/consumo_setor_html/{}/'.format(id_))

    else:
        form = ConsumoSetorForm()
    return locals()


def consumo_setor_processar(cleaned_data, user):
    data_ini = cleaned_data.get('data_inicial') or date.today()
    data_fim = cleaned_data.get('data_final') or date.today()
    setor = cleaned_data.get('setor')
    setor_id = None

    uo_id = user.get_vinculo().setor.uo.id
    if setor and setor.uo:
        setor_id = setor.id
        setor = Setor.objects.get(id=setor_id)
        uo_id = setor.uo.id
        if cleaned_data.get('incluir'):
            lista_setor = setor.ids_descendentes
            setor = "{} e subsetores.".format(setor)
        else:
            lista_setor = [setor_id]
    else:
        lista_setor = Setor.objects.get(sigla=Configuracao.get_valor_por_chave('comum', 'instituicao_sigla'), excluido=False).ids_descendentes
        setor = "Todos os Setores"

    if cleaned_data.get("opcao_exibir") == "materiais":
        cabecalhos_tabela = [
            [
                dict(valor='#', alinhamento='center', largura=6, colspan=1),
                dict(valor='Cód', alinhamento='left', largura=20, colspan=1),
                dict(valor='Material', alinhamento='left', largura=80, colspan=1),
                dict(valor='Setor', alinhamento='left', largura=30, colspan=1),
                dict(valor='Qtd.', alinhamento='right', largura=20, colspan=1),
                dict(valor='Valor Total', alinhamento='right', largura=30, colspan=1),
            ]
        ]

        corpo_tabela = []
        cont = 0
        for setor_id in lista_setor:
            solicitante = None
            for material, dados in list(MovimentoAlmoxSaida.get_consumo_setor(data_ini, data_fim, setor_id, uo_id).items()):
                # evita busca de solicitante a cada iteracao
                if not solicitante:
                    solicitante = Setor.objects.get(id=setor_id).sigla

                codigo = material.codigo
                material = material.nome
                qtd = dados['qtd']
                valortot = dados['valor']
                cont += 1
                corpo_tabela.append([cont, codigo, material, solicitante, qtd, mask_money(valortot)])

        linha_total = ['', '', '', '', '', mask_money(somar_indice(corpo_tabela, 4))]
        corpo_tabela.append(linha_total)

    elif cleaned_data.get("opcao_exibir") == "totais":
        cabecalhos_tabela = [
            [
                dict(valor='#', alinhamento='center', largura=6, colspan=1),
                dict(valor='Setor', alinhamento='left', largura=124, colspan=1),
                dict(valor='Valor', alinhamento='right', largura=30, colspan=1),
            ]
        ]

        corpo_tabela = []
        cont = 0
        for setor_id in lista_setor:
            valortot = 0

            for material, dados in list(MovimentoAlmoxSaida.get_consumo_setor(data_ini, data_fim, setor_id, uo_id).items()):
                valortot += dados['valor']

            if valortot > 0:
                solicitante = Setor.objects.get(id=setor_id)
                cont += 1
                corpo_tabela.append([cont, solicitante, mask_money(valortot)])
        linha_total = ['', '', mask_money(somar_indice(corpo_tabela, 2))]
        corpo_tabela.append(linha_total)

    else:
        cabecalhos_tabela = [
            [
                dict(valor='#', alinhamento='center', largura=10, colspan=1),
                dict(valor='Req.', alinhamento='left', largura=20, colspan=1),
                dict(valor='Solicitante', alinhamento='left', largura=40, colspan=1),
                dict(valor='Data', alinhamento='left', largura=30, colspan=1),
                dict(valor='Cód', alinhamento='left', largura=20, colspan=1),
                dict(valor='Material', alinhamento='left', largura=80, colspan=1),
                dict(valor='Qtd.', alinhamento='right', largura=15, colspan=1),
                dict(valor='Valor Unit', alinhamento='right', largura=15, colspan=1),
                dict(valor='Valor Total', alinhamento='right', largura=20, colspan=1),
            ]
        ]

        corpo_tabela = []
        cont = 0
        for setor_id in lista_setor:
            for movimento in MovimentoAlmoxSaida.get_saidas_setor(data_ini, data_fim, setor_id, uo_id):
                requisicao = movimento.requisicao_user_material.requisicao.id
                solicitante = "{} ({})".format(
                    movimento.requisicao_user_material.requisicao.vinculo_solicitante.pessoa.nome, movimento.requisicao_user_material.requisicao.setor_solicitante.sigla
                )
                data = movimento.data.strftime("%d/%m/%Y")
                codigo = movimento.requisicao_user_material.material.codigo
                material = movimento.requisicao_user_material.material.nome
                qtd = movimento.qtd
                valorunit = movimento.valor
                valortot = qtd * valorunit
                cont += 1
                corpo_tabela.append([cont, requisicao, solicitante, data, codigo, material, qtd, mask_money(valorunit), mask_money(valortot)])

        linha_total = ['', '', '', '', '', '', '', '', mask_money(somar_indice(corpo_tabela, 8))]
        corpo_tabela.append(linha_total)

    tabela = dict(cabecalhos=cabecalhos_tabela, dados=corpo_tabela)
    p = 'Setor: {} <br/>Período: {}'.format(setor, extrair_periodo(data_ini, data_fim))

    dados = dict(
        cabecalho=dict(orgao=Configuracao.get_valor_por_chave('comum', 'instituicao'), uo=user.get_vinculo().setor.uo.__str__(), setor=user.get_vinculo().setor.__str__()),
        data=data_extenso(),
        titulo='Relatório de Saídas do Almoxarifado',
        elementos=[p, tabela],
        cidade=user.get_vinculo().setor.uo.municipio,
    )

    return dados


def consumo_setor_html(request, id_):
    dados = request.session.get(id_)
    if dados:
        titulo = dados['titulo']
        p, tabela = dados['elementos']
        tabela = montar_tabela_html(tabela, destacar_ultima=True)
        link_pdf = '/almoxarifado/relatorio/consumo_setor_pdf/{}/'.format(id_)
        return render('relatorio.html', {'title': titulo, 'p': p, 'tabela': tabela, 'id_': id_, 'link_pdf': link_pdf})
    else:
        raise PermissionDenied


def consumo_setor_pdf(request, id_):
    dados = request.session.get(id_)
    if dados:
        return PDFResponse(RelatorioPDF(dados, paisagem=True).montar())
    else:
        raise PermissionDenied


def relatorio_balancete_material(data_ini, data_fim, uo, estoque, request):
    return tasks.gerar_balancete_material(data_ini, data_fim, uo, estoque, request)


def balancete_material_pdf(request):
    data_ini = datetime.strptime(request.GET['dt_ini'], "%Y-%m-%d")
    data_fim = datetime.strptime(request.GET['dt_fim'], "%Y-%m-%d")
    uo = UnidadeOrganizacional.objects.suap().filter(pk=request.GET['uo']).first()
    estoque = request.GET['estoque'] == "True"
    return tasks.exportar_balancete_material_pdf(data_ini, data_fim, uo, estoque, request)


def relatorio_balancete_ed_detalhado(cleaned_data, request):
    return tasks.relatorio_balancete_ed_detalhado(cleaned_data, request)


def balancete_ed_detalhado_html(request, id_):
    """
    Exibe relatório e link para geração do PDF correspondente.
    """
    dados = cache.get(id_)

    if not dados:
        return httprr('..', 'Identificador de balancete inválido.', 'error')
    titulo = dados['titulo']
    p, tabela = dados['elementos']
    tabela = montar_tabela_html(tabela, destacar_ultima=True)
    link_pdf = '/almoxarifado/relatorio/balancete_ed_detalhado_pdf/{}/'.format(id_)

    return render('relatorio.html', {'title': titulo, 'p': p, 'tabela': tabela, 'id_': id_, 'link_pdf': link_pdf})


def balancete_ed_detalhado_pdf(request, id_):

    dados = cache.get(id_)
    if not dados:
        return httprr('..', 'Identificador de balancete inválido.', 'error')
    return tasks.balancete_ed_detalhado_pdf(dados)


@rtr()
@login_required
def nota_fornecimento_pdf(request, requisicao_tipo=None, requisicao_id=None, solicitante_id=None, data_inicio=None, data_fim=None):
    """
    Gera nota de fornecimento a partir da tela de detalhes de uma requisição.
    """

    if requisicao_tipo:
        requisicao = RequisicaoAlmox.get(requisicao_tipo, requisicao_id)

    if solicitante_id:
        data_fim_mais_um_dia = somar_data(datetime.strptime(data_fim, "%Y-%m-%d"), 1)
        requisicoes = RequisicaoAlmoxUO.objects.filter(vinculo_solicitante=solicitante_id, data__range=(data_inicio, data_fim_mais_um_dia))
        total_requisicoes = 0
        for requisicao in requisicoes:
            for item in requisicao.get_itens_aceitos():
                total_requisicoes += item.valor()

        if not requisicoes:
            raise PermissionDenied('Requisição sem itens aceitos.')

    # Bloqueio de acesso decorrente da permissão para visualização da requisição
    assinatura1_nome = ''

    solicitante = requisicao.vinculo_solicitante.relacionamento
    if requisicao_tipo == 'user':
        if requisicao.vinculo_fornecedor:
            assinatura1_nome = requisicao.vinculo_fornecedor.pessoa.nome
    else:
        assinatura1_nome = request.user.get_profile().nome

    try:
        assinatura1_matricula = requisicao.vinculo_fornecedor.relacionamento.matricula
    except Exception:
        assinatura1_matricula = ''
    assinatura2_nome = solicitante.nome
    assinatura2_matricula = solicitante.matricula or ''
    tabela_itens = [['ED', 'COD', 'MATERIAL', 'Qtd.', 'Subtotal']]
    tabela_devolucao = [['ED', 'COD', 'MATERIAL', 'Qtd.']]
    tem_devolucao = False
    observacoes = '-'
    if requisicao_tipo == 'user':
        observacoes = requisicao.observacoes
        if not observacoes:
            observacoes = '-'

    if requisicao_tipo:
        cabecalho = [
            ['<b>Código de Requisição:</b>', requisicao.id],
            ['<b>Data da Requisição:</b>', requisicao.get_data()],
            ['<b>Observações:</b>', '{}'.format(observacoes)],
            ['<b>Servidor Origem:</b>', '{0} - {1}'.format(assinatura1_nome, assinatura1_matricula)],
            ['<b>Setor Solicitante:</b>', '{}'.format(solicitante.setor)],
            ['<b>Servidor Destino:</b>', '{0} - {1}'.format(solicitante.nome, solicitante.matricula)],
            ['<b>Realizada em:</b>', '{0}'.format(requisicao.data_avaliacao_fornecedor)],
        ]
        cabecalho = pdf.table(cabecalho, a=['l', 'l'], w=[32, 138], grid=0)

        for item in requisicao.get_itens_aceitos():
            tabela_itens.append([item.material.categoria.codigo, item.material.codigo, item.material.nome, item.saida()['qtd'], item.valor_unitario()])

        for item in requisicao.get_itens_devolvidos():
            tabela_devolucao.append([item.material.categoria.codigo, item.material.codigo, item.material.nome, item.quantidade])
            tem_devolucao = True
        valor_total = pdf.para('<b>Valor Total: {}</b>'.format(requisicao.get_total()), align='right')

    if solicitante_id:
        lista_inicio = data_inicio.split('-')
        lista_fim = data_fim.split('-')
        data_inicio = date(int(lista_inicio[0]), int(lista_inicio[1]), int(lista_inicio[2]))
        data_fim = date(int(lista_fim[0]), int(lista_fim[1]), int(lista_fim[2]))
        cabecalho = [
            ['<b>Período:</b>', 'De {} a {}'.format(data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y"))],
            ['<b>Solicitante:</b>', '{} ({})'.format(solicitante.nome, solicitante.matricula)],
            ['<b>Setor:</b>', '{}'.format(solicitante.setor)],
        ]
        cabecalho = pdf.table(cabecalho, a=['l', 'l'], w=[32, 138], grid=0)
        tabela_itens = [['ED', 'COD', 'MATERIAL', 'Qtd.', 'Subtotal']]
        for requisicao in requisicoes:
            for item in requisicao.get_itens_aceitos():
                tabela_itens.append([item.material.categoria.codigo, item.material.codigo, item.material.nome, item.saida()['qtd'], item.valor_unitario()])
            for item in requisicao.get_itens_devolvidos():
                tabela_devolucao.append([item.material.categoria.codigo, item.material.codigo, item.material.nome, item.quantidade])
                tem_devolucao = True
        valor_total = pdf.para('<b>Valor Total: {}</b>'.format(total_requisicoes), align='right')

    data = pdf.para('<font size=8.5>' + calendario.getDataExtenso() + '</font>', align='right')
    titulo = get_topo_com_titulo('Nota de Fornecimento')
    tabela_itens = pdf.table(tabela_itens, count=1, w=[10, 15, 131, 10, 17], a=['c', 'c', 'l', 'c', 'r'], head=1, zebra=1)

    tabela_devolucao = pdf.table(tabela_devolucao, count=1, w=[10, 15, 146, 15], a=['c', 'c', 'l', 'r'], head=1, zebra=1)
    titulo_devolucao = pdf.para('<b>Materiais devolvidos</b>', align='center')

    corpo = [data] + titulo + [cabecalho, pdf.space(10), tabela_itens, valor_total]

    if tem_devolucao:
        corpo += [pdf.space(10), titulo_devolucao, pdf.space(5), tabela_devolucao]
    campus_fornecedor = requisicao.uo_fornecedora.nome
    campus_solicitante = requisicao.uo_fornecedora.nome
    if requisicao_tipo == 'uo':
        campus_fornecedor = requisicao.uo_fornecedora.nome
        campus_solicitante = requisicao.uo_solicitante.nome
    footer = rodape_data_e_duas_assinaturas_almoxarifado(
        [assinatura1_nome, assinatura1_matricula, assinatura2_nome, assinatura2_matricula, campus_fornecedor, campus_solicitante, requisicao_tipo]
    )

    return PDFResponse(pdf.PdfReport(body=corpo, footer_args=footer).generate())


def historico_movimentacao(material, uo):
    def format(m):
        if isinstance(m, MovimentoAlmoxSaida):
            m.valor = -m.valor
            m.qtd = -m.qtd
        m.total = abs(m.valor) * m.qtd
        return m

    def get_movimentos(material, uo):
        e = [(m.data, m.id, format(m)) for m in material.movimentoalmoxentrada_set.filter(uo=uo)]
        s = [(m.data, m.id, format(m)) for m in material.movimentoalmoxsaida_set.filter(uo=uo)]
        movimentos = e + s
        movimentos.sort()
        movimentos = [i[2] for i in movimentos]
        total = {}
        total['qtd'] = sum(i.qtd for i in movimentos)
        total['total'] = sum(i.total for i in movimentos)
        try:
            material = MaterialEstoque.objects.get(material=material, uo=uo)
        except Exception:
            material = MaterialEstoque.objects.create(material=material, uo=uo, valor_medio=0, quantidade=0)
        total['valor_medio'] = material.valor_medio
        total['estoque_atual'] = material.quantidade
        movimentos.append(total)
        return movimentos

    return get_movimentos(material, uo)
