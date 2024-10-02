# -*- coding: utf-8 -*-

from django.conf import settings
from djtools import pdf
from os.path import join
from django.apps import apps


def get_topo_com_titulo(titulo=''):
    # Deve ser utilizado com papel A4
    image_path = join(settings.STATIC_ROOT, 'comum/img/brasao_cinza.jpg')
    image = pdf.Image(image_path, width=15.96 * pdf.mm, height=17.4 * pdf.mm)
    instituicao = apps.get_model('comum', 'configuracao').get_valor_por_chave('comum', 'instituicao')
    para = pdf.para('{}<br/><b>{}</b>'.format(instituicao, titulo), align='center')
    tabela_imagem = pdf.table([[image, para]], w=[25, 165], grid=0)
    return [tabela_imagem, pdf.space(5)]


def rodape_data_e_assinatura(assinatura='Coordenação do Patrimonio'):
    """
    Retorna um rodapé para ser inserido em pdf do tipo:

    Natal, ___ de ______________________ de ______

    ______________________________________________
             Coordenação do Patrimônio

    """
    return {
        'height': 30,
        'story': [
            pdf.para('<font size=9>_______________________, ______ de __________________________ de ____________</font>', alignment='center'),
            pdf.space(7),
            pdf.para('_________________________________________________', alignment='center'),
            pdf.table([[assinatura]], grid=0, w=[145], a=['c'], blank=''),
        ],
    }


def rodape_data_e_duas_assinaturas(assinaturas=['Coordenação do Almoxarifado', 'Natercio Dias de Holanda']):
    """
    Retorna um rodapé para ser inserido em pdf do tipo:

                                     Natal, ___ de ______________________ de ______

    ______________________________________________                   ______________________________________________
             Coordenação do Patrimônio                                           Coordenação do Patrimônio

    """
    tabela_campos_assinaturas = [['___________________________________', ' ', '___________________________________']]
    tabela_assinaturas = [[assinaturas[0], '  ', assinaturas[1]]]
    return {
        'height': 50,
        'story': [
            pdf.para('<font size=9>Documento assinado digitalmente por meio de login e senha do SUAP</font>', alignment='center'),
            pdf.space(7),
            pdf.table(tabela_campos_assinaturas, w=[60, 40, 60], grid=0, a=['l', 'c', 'r']),
            pdf.table(tabela_assinaturas, w=[60, 40, 61], grid=0, a=['c', 'c', 'c']),
        ],
    }


def rodape_data_e_duas_assinaturas_almoxarifado(assinaturas=['Coordenação do Almoxarifado', 'Natercio Dias de Holanda']):
    tabela_dados_assinaturas = [['Fornecedor', ' ', 'Solicitante']]
    tabela_campos_assinaturas = [['___________________________________', ' ', '___________________________________']]

    if assinaturas[6] == 'user':
        tabela_mensagem = [['  ', '   ', '    ']]
    else:
        tabela_mensagem = [['Documento assinado digitalmente por meio de login e senha do SUAP.', ' ', ' ']]
    tabela_campus = [[assinaturas[4], ' ', assinaturas[5]]]
    tabela_matricula = [['Matrícula', assinaturas[1], ' ', 'Matrícula', assinaturas[3]]]
    tabela_assinaturas = [[assinaturas[0], '  ', assinaturas[2]]]
    return {
        'height': 50,
        'story': [
            pdf.table(tabela_dados_assinaturas, w=[60, 40, 60], grid=0, a=['l', 'c', 'l']),
            pdf.space(5),
            pdf.table(tabela_campos_assinaturas, w=[60, 40, 60], grid=0, a=['l', 'c', 'l']),
            pdf.table(tabela_assinaturas, w=[60, 40, 60], grid=0, a=['l', 'c', 'l']),
            pdf.table(tabela_campus, w=[60, 40, 60], grid=0, a=['l', 'l', 'l']),
            pdf.table(tabela_matricula, w=[17, 23, 60, 17, 43], grid=0, a=['l', 'l', 'l', 'l', 'l']),
            pdf.space(7),
            pdf.table(tabela_mensagem, w=[100, 40, 20], grid=0, a=['l', 'c', 'l']),
        ],
    }
