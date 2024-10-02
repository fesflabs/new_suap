#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Comando que gera uma pasta contendo todos menus e suas respectivas permissoes e grupos que as possuem

Obrigatório lib: markdown2
"""

import codecs
import json
import os
import xml.etree.ElementTree as ET

import markdown2
from djtools.management.commands import BaseCommandPlus
from django.conf import settings


def capturar_modulo(nome_modulo):
    """
        Retorna uma string contendo uma estrutura em markdown para um modulo informado
    """
    if os.path.isfile('{}/menu_enap.json'.format(nome_modulo)):
        menu = json.load(open(nome_modulo + '/menu_enap.yaml', 'r'))
    else:
        menu = json.load(open(nome_modulo + '/menu.yaml', 'r'))
    estrutura = {}
    for item in menu:
        if 'url' in item:
            if 'permissions_required' in item or 'groups_required' in item:
                menu_path = (item['hierarchy'] + '::permissions').split("::")
            else:
                menu_path = item['hierarchy'].split("::")
            seletor = estrutura
            for menu_elemento in menu_path:
                if menu_elemento not in seletor:
                    if menu_elemento == 'permissions':
                        seletor['permissions'] = []
                        seletor['groups'] = []
                        if 'permissions_required' in item:
                            seletor['permissions'].extend(item['permissions_required'])
                        if 'groups_required' in item:
                            seletor['groups'].extend(item['groups_required'])
                    else:
                        seletor[menu_elemento] = {}
                seletor = seletor[menu_elemento]
    markdown_completo = ""
    for item in estrutura:
        markdown_completo += escrever_md(estrutura, 1)
    return markdown_completo


def escrever_md(estrutura, nivel):
    """
        Função recursiva que retorna uma string formatada em markdown reunindo informações
        de permissoes, grupos e menus.
    """
    str_saida = ''
    for item in estrutura:
        if item:
            if not estrutura[item]:
                str_saida += '{} \n\n'.format(item)
            elif 'permissions' in estrutura[item]:
                str_saida += '{} __{}__'.format('>' * nivel, item)
                grupos = []
                if estrutura[item]['permissions']:
                    str_saida += '\n\n{} Permissão:\n\n'.format('>' * (nivel + 1))
                    for permission in estrutura[item]['permissions']:
                        str_saida += '{} * {}\n'.format('>' * (nivel + 1), permission)
                        grupos.extend(set(get_groups_permission(nome_permissao=permission)))
                if grupos or estrutura[item]['groups']:
                    str_saida += '\n\n{} Quem pode visualizar:\n\n'.format('>' * (nivel + 1))
                    for permission in grupos:
                        str_saida += '{} * {} \n'.format('>' * (nivel + 1), permission)

                    for permission in estrutura[item]['groups']:
                        str_saida += '{} * {} \n'.format('>' * (nivel + 1), permission)
                str_saida += '\n\n'
            else:
                str_saida += '{} {}\n\n'.format('>' * nivel, item)
                str_saida += escrever_md(estrutura[item], nivel + 1)
    return str_saida


def get_groups_permission(nome_permissao):
    """
        Com base em um modulo e no nome de uma permissão retorna todos os grupos que possuem a mesma
    """
    modulos = getattr(settings, 'INSTALLED_APPS_SUAP', ()) + getattr(settings, 'INSTALLED_APPS_LOCAL', ())
    retorno = []
    for modulo in modulos:
        if validar_pasta_modulo(modulo):
            tree = ET.parse('{}/permissions.xml'.format(modulo))
            root = tree.getroot()
            for grupo in root.findall('group'):
                cargos = grupo.find('name').text.replace('; ', ';').split(';')
                for permissao in grupo.iter('permission'):
                    try:
                        if permissao.text == nome_permissao.split('.')[1]:
                            retorno.extend(cargos)
                    except Exception:
                        pass
    return set(retorno)


def ensure_dir(file_path):
    if not os.path.exists(file_path):
        os.makedirs(file_path)


def validar_pasta_modulo(caminho_pasta):
    if not (os.path.isfile('{}/menu_enap.yaml'.format(caminho_pasta)) or os.path.isfile('{}/menu.yaml'.format(caminho_pasta))):
        return False
    elif not os.path.isfile('{}/permissions.xml'.format(caminho_pasta)):
        return False
    else:
        return True


class Command(BaseCommandPlus):  # 1099
    def handle(self, *args, **options):
        doc_folder = 'doc_menus'
        css = '<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css">'
        ensure_dir(doc_folder)
        doc_folder_pages = "{}/paginas".format(doc_folder)
        ensure_dir(doc_folder_pages)
        # print(getattr(settings, 'INSTALLED_APPS_LOCAL', None))
        modulos = getattr(settings, 'INSTALLED_APPS_SUAP', ()) + getattr(settings, 'INSTALLED_APPS_LOCAL', ())
        main_page = codecs.open('{}/index.html'.format(doc_folder), 'w', 'utf-8')
        main_page.write(css + markdown2.markdown('# Menus disponíveis:'))
        for modulo in modulos:
            if validar_pasta_modulo(modulo):
                module_folder = '{}/{}'.format(doc_folder_pages, modulo)
                file = codecs.open('{}.html'.format(module_folder), 'w', 'utf-8')
                file.write(css)
                file.write(markdown2.markdown('### [Main Page](../index.html)'))
                file.write(markdown2.markdown(capturar_modulo(nome_modulo=modulo), extras=['fenced-code-blocks', 'spoiler', 'smarty-pants']))
                file.close()
                main_page.write(markdown2.markdown('### [{}](paginas/{}.html)'.format(modulo.capitalize(), modulo)))
        main_page.close()
