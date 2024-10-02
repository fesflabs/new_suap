from django.contrib.admin.filters import SimpleListFilter
from djtools.utils.response import render_to_string

from comum.models import Ano
from djtools.utils import normalizar_nome_proprio
from edu.models import CursoCampus, Modalidade, Polo
from rh.models import UnidadeOrganizacional


def metadata(objeto):
    lista = []
    box = []
    methods_aux = []
    methods = []
    # Navega pelos atributos do objeto escolhido

    lista_fields_name = []
    for field in objeto._meta.fields:
        lista_fields_name.append(field.name)

    for field in objeto._meta.fields:
        field_name_aux = False
        box_name_aux = 'Dados Gerais'
        if hasattr(objeto, 'fieldsets'):
            dict_fieldsets = dict(objeto.fieldsets)
            for t1, t2 in list(dict_fieldsets.items()):
                for t3 in list(t2.values()):
                    for t4 in t3:
                        if t4 == field.name:
                            field_name_aux = True
                            box_name_aux = t1
                        else:
                            if not t4 in lista_fields_name and not t4 in methods_aux:
                                methods_aux.append(t4)
                                methods.append({t1: t4})

        if not hasattr(objeto, 'fieldsets') or field_name_aux:
            url = ''

            # Recupera o valor do atributo
            if field.choices:
                valor = getattr(objeto, 'get_{}_display'.format(field.name))()
            elif field.__class__.__name__ == 'ImageWithThumbsField':
                imagem = objeto.__getattribute__(field.name)
                try:
                    valor = hasattr(imagem, 'url') and '<img heigth="200" width="150" src="{}" alt="Imagem de {}"/>'.format(imagem.url, objeto) or ''
                except Exception:
                    valor = ''
            else:
                valor = objeto.__getattribute__(field.name)

            # Verifica se o campo é estrangeiro
            if hasattr(field, 'related') and valor:
                url = ''
                # Verifica se o objeto possui o método get_absolute_url
                if hasattr(valor, 'get_absolute_url'):
                    url = str(valor.get_absolute_url())
                # O objeto estrangeiro precisa ser uma classe para gerar a url
                else:
                    app = valor._meta.app_label
                    modelo = valor.__class__.__name__
                    url = '/edu/visualizar/{}/{}/{}/'.format(app, modelo, valor.pk)
            if not box_name_aux in box:
                box.append(box_name_aux)

            lista.append((normalizar_nome_proprio(field.verbose_name), valor, url, box_name_aux))

    for dict_methods in methods:
        for box_name, method_name in list(dict_methods.items()):
            if type(method_name) == str:
                method = getattr(objeto, method_name)
                lista.append((method_name.replace('get_', '').replace('_', ' ').capitalize(), method, '', box_name))
            elif type(method_name) == list or type(method_name) == tuple:
                for m in method_name:
                    method = getattr(objeto, m)
                    lista.append((m.replace('get_', '').replace('_', ' ').capitalize(), method, '', box_name))

            if not box_name in box:
                box.append(box_name)

    lista.append(box)
    return lista

