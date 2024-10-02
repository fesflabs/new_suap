#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import re
import sys


def format(param):
    param = re.sub(r' *<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">', '', param)
    param = re.sub(r' *<TR><TD COLSPAN="2" CELLPADDING="4" ALIGN="CENTER">', '', param)
    param = re.sub(r' *<FONT FACE="Helvetica Bold" COLOR="Black" POINT-SIZE="12">', '', param)
    param = re.sub(r' *<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0">', '', param)
    param = re.sub(r' *<TR><TD COLSPAN="2" CELLPADDING="4" ALIGN="CENTER">', '', param)
    param = re.sub(r' *<FONT FACE="Helvetica Bold" COLOR="Black" POINT-SIZE="12">', '', param)
    param = re.sub(r' *<TABLE BGCOLOR="palegoldenrod" BORDER="0" CELLBORDER="0" CELLSPACING="0">', '', param)
    param = re.sub(r' *<TR><TD COLSPAN="2" CELLPADDING="4" ALIGN="CENTER" BGCOLOR="olivedrab4">', '', param)
    param = re.sub(r' *<FONT FACE="Helvetica Bold" COLOR="white">', '', param)
    param = re.sub(r'<BR/>&lt;<FONT FACE="Helvetica Italic">.*</FONT>&gt;', '', param)
    param = re.sub(r' *</FONT></TD></TR>', '', param)
    param = re.sub('label=<', 'label=', param)
    param = re.sub(r'>]', ']', param)
    param = re.sub(r' *</FONT>', '', param)
    param = re.sub(r' *</TD></TR>', '', param)
    param = re.sub(r' *</TABLE>', '', param)
    return param


arquivo = ''
extensao = 'graphml'
ignore_string = ''
if len(sys.argv) < 2:
    print('Exemplos de uso:')
    print('./diagrama_classe_geral.py <aplicacao>.txt')
    print('./diagrama_classe_geral.py <aplicacao>')
    print('./diagrama_classe_geral.py <aplicacao> <png, jpg, pdf>')
    print('<aplicacao>.txt deve conter uma lista de classes a serem ignoradas separadas por vírgula sem espaços nem enters')
    exit()
elif len(sys.argv) > 2:
    aplicacao = sys.argv[1]
    extensao = sys.argv[2]
    arquivo = '| dot -T%s > %s.%s' % (extensao, aplicacao, extensao)
else:
    try:
        aplicacao, file_type = sys.argv[1].split('.')
    except Exception:
        aplicacao = sys.argv[1]
    try:
        with open(sys.argv[1], 'r') as f:
            ignore_string += f.read()
    except Exception:
        pass

read_data = ''
shell_string = '../../../../manage.py graph_models %s --disable-fields --layout dot --hide-relations-from-fields -X ModelPlus,LogModel,%s %s' % (aplicacao, ignore_string, arquivo)
if arquivo != '':
    os.system(shell_string)
else:
    with os.popen(shell_string) as f:
        read_data += format(f.read())

    file = open('cleaned.dot', 'w')
    file.write(read_data)
    file.close()

    os.popen('python dottoxml.py -s --at circle cleaned.dot %s.%s' % (aplicacao, extensao))
    os.remove('cleaned.dot')

print(('Gráfico %s.%s gerado com sucesso!' % (aplicacao, extensao)))
if extensao == 'graphml':
    print('Para utilizá-lo, abra-o no aplicativo yED.')
    print('Para organizar o tamanho dos nós clique em Tools > Fit node to label.')
    print('Para organizar o posicionamento das classes, escolha uma das opções disponíveis no menu Layout.')
