# -*- coding: utf-8 -*-

from comum.models import Configuracao
from comum.utils import data_extenso
from djtools import pdf


def get_rodape_termos(nome=''):

    sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')

    elementos = [pdf.space(8)]
    elementos.append(
        pdf.para(
            'Declaro pelo presente documento de responsabilidade que recebi o material '
            'acima especificado e que sou responsável direto pelo mesmo e devo observar '
            'normas sobre o controle e zelo do material permanente, equipamentos e instalações '
            'pertencentes ao %s.' % sigla,
            align='center',
        )
    )
    elementos.append(pdf.space(8))
    elementos.append(pdf.para('_______________________, ______ de ______________________ de __________', align='center'))
    elementos.append(pdf.space(8))
    elementos.append(
        pdf.table(
            [
                [
                    pdf.para('________________________________________<br/>Coordenador de Patrimônio', align='center'),
                    pdf.para('________________________________________<br/>%s' % nome, align='center'),
                ]
            ],
            w=[95, 95],
            grid=0,
        )
    )
    return elementos


def get_corpo_nada_consta(vinculo):
    elementos = [pdf.space(30)]
    elementos.append(
        pdf.para(
            'Declaramos, para devidos fins, que <strong>%s</strong>, com matrícula <strong>%s</strong>, '
            'não possui nenhum bem patrimonial em sua carga/responsabilidade.' % (vinculo, vinculo.relacionamento.matricula),
            align='justify',
        )
    )
    elementos.append(pdf.space(30))
    elementos.append(pdf.para('{}'.format(data_extenso()), align='center'))
    elementos.append(pdf.space(20))
    elementos.append(pdf.para('______________________________________________', align='center'))
    elementos.append(pdf.para(' Coordenador de Patrimônio', align='center'))
    return elementos


def get_corpo_nada_consta_inventario_uso_pessoal(usuario_logado, vinculo='', uso_pessoal=[]):
    elementos = [pdf.space(30)]

    elementos.append(
        pdf.para(
            'Declaramos, para devidos fins, que <strong>%s</strong>, com matrícula <strong>%s</strong>, '
            'não possui nenhum bem patrimonial em sua carga/responsabilidade, exceto os seguintes inventários de uso pessoal:'
            % (vinculo.pessoa.nome, vinculo.relacionamento.matricula),
            align='justify',
        )
    )
    elementos.append(pdf.space(10))

    # tabela com elementos de uso pessoal
    dados = [['#', 'Número', 'Descrição', 'Valor']]
    for index, item in enumerate(uso_pessoal):
        dados.append([index + 1, item['numero'], item['descricao'], item['entrada_permanente__valor']])

    widths = [10, 15, 142, 20]
    tabela_dados = pdf.table(dados, head=1, zebra=1, w=widths, count=0, a=['r', 'c', 'c', 'r'])
    elementos.append(tabela_dados)

    elementos.append(pdf.space(30))
    elementos.append(pdf.para('{}'.format(data_extenso()), align='center'))
    elementos.append(pdf.space(20))
    elementos.append(pdf.para('________________________________________________', align='center'))
    elementos.append(pdf.para(' Coordenador de Patrimônio', align='center'))
    return elementos
