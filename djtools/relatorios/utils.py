# -*- coding: utf-8 -*-
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, TableStyle
from reportlab.platypus.tables import LongTable
try:
    from html import escape
except ImportError:
    from cgi import escape


estilos = getSampleStyleSheet()

data_assinatura = '%(cidade)s, ______ de ____________________ de __________'


def montar_paragrafo(texto, alinhamento='left', estilo='BodyText', tamanho=None, negrito=False, autoescape=True):
    """
    Cria um parágrafo no padrão ReportLAB.

    Args:
        texto (string): texto do parágrafo;
        alinhamento (string): estilo do alinhamento;
        estilo (string): estilo do texto do parágrafo;
        tamanho (string): tamanho do texto;
        negrito (bool): indica que o texto deve estar em negrito;
        autoescape (bool): indica se deve-se realizar o '*escape*' do texto.

    Returns:
        Paragraph com base nos argumentos passados.
    """
    if autoescape and isinstance(texto, str) and '<br/>' not in texto:
        texto = escape(texto)
    template = '<para alignment=%(alinhamento)s %(fontSize)s>%(texto)s</para>'
    fontSize = tamanho and 'fontSize=%s' % (tamanho) or ''
    if negrito:
        texto = '<b>%s</b>' % (texto)
    contexto = dict(fontSize=fontSize, alinhamento=alinhamento, texto=texto)

    return Paragraph(template % (contexto), estilos[estilo])


def montar_paragrafo_html(texto):
    """
    Cria um parágrafo **HTML**.

    Args:
        texto (string): texto do parágrafo.

    Returns:
        String contendo o *HTML* do parágrafo.
    """
    return '<p style="clear: both;">%s</p>' % texto


def montar_tabela_html(tabela, css='results', alternar=['row1', 'row2'], destacar_ultima=False):
    """
    Cria uma tabela **HTML** com base na tabela (**dict**) passado.

    Args:
        tabela (dict): dicionário com os dados para montar a tabela;
        css (string): classe **CSS** para a tabela;
        alternar (list): classes que serão utilizads na montagem das linhas, alternado os valores;
        destacar_ultima (bool): indica se é para destacar a última linha da tabela.

    Examples:
        Entrada::

            {'cabecalhos': [
                [{'valor': 'item', 'largura': 20, 'colspan': 2}],
                [{'valor': 'id', 'largura': 10, 'colspan': 1, 'alinhamento': 'right'},
                 {'valor': 'nome', 'largura': 10, 'colspan': 1, 'alinhamento': 'left'}]
             ],
             'dados': [
                [1, 'bola de futebol'],
             ]
            }

        Saída::

            <table class="results">
                <thead>
                    <tr><th colspan="2">item</th></tr>
                    <tr><th colspan="1">id</th><th colspan="1">nome</th></tr>
                </thead>
                <tbody>
                    <tr>
                        <td align="right">1</td>
                        <td align="left">bola de futebol</td>
                    </tr>
                </tbody>
            </table>

        Returns:
            String com o código **HTML** da tabela.
    """
    html = ['<table>']

    # Montando o THEAD
    cabecalhos = tabela['cabecalhos']
    html.append('<thead>')
    for c in cabecalhos:
        html.append('<tr>')
        for i in c:
            html.append('<th colspan="%s" align="%s">%s</th>' % (i.get('colspan', 1), i.get('alinhamento', 'center'), i['valor']))
        html.append('</tr>')
    html.append('</thead>')

    # Montando o TBODY
    html.append('<tbody>')
    ultima_linha_eh_total = '' in tabela['dados'][-1]
    posicao_ultima_linha = len(tabela['dados']) - 1

    for index, d in enumerate(tabela['dados']):
        css_classes = alternar[index % 2]
        if ultima_linha_eh_total and index == posicao_ultima_linha:
            css_classes += ' total'
        html.append('<tr class="%s">' % css_classes)
        for index, item in enumerate(d):
            alinhamento = c[index]['alinhamento']
            html.append('<td align="%s">%s</td>' % (alinhamento, item))
        html.append('</tr>')

    html.append('</tbody></table>')

    return ''.join(html)


def montar_elementos_html(elementos):
    """
    Cria um elemento **HTML**.

    Args:
        elementos (list): lista com os elementos a serem montados.

    Returns:
        String com o elemento rendereizado em **HTML**
    """
    html = []
    for e in elementos:
        if isinstance(e, dict):
            html.append(montar_tabela_html(e))
        elif isinstance(e, str):
            html.append(montar_paragrafo_html(e))
    return ''.join(html)


def montar_tabela_pdf(tabela):
    """
    Cria uma tabela, no formato do ReportLAB, com os dados passados.

    Args:
        tabela (dict): dicionário com os dados para montagem da tabela.

    Returns:
        LongTable com os dados passados.
    """
    # Saída: lista de tabelas; uma para cada cabeçalho e uma para os dados.

    tabelas = []
    cabecalhos = tabela['cabecalhos']
    dados = tabela['dados']

    # Montar as tabelas para cada cabeçalho
    for c in cabecalhos:
        item = []
        larguras = []
        for col in c:
            item.append(montar_paragrafo(col['valor'], alinhamento='center', negrito=True))
            larguras.append(col['largura'])
        tabela = LongTable([item], [i * mm for i in larguras])
        tabela.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black), ('BOX', (0, 0), (-1, -1), 0.25, colors.black)]))
        tabelas.append(tabela)

    # Montar a tabela do corpo
    for linha in dados:
        for i, coluna in enumerate(linha):
            coluna = str(coluna)
            coluna = len(coluna) > 600 and coluna[:600] + '...' or coluna
            linha[i] = montar_paragrafo(coluna, alinhamento=c[i]['alinhamento'])

    tabela = LongTable(dados, [i * mm for i in larguras])
    tabela.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black), ('BOX', (0, 0), (-1, -1), 0.25, colors.black)]))

    tabelas.append(tabela)
    return tabelas
