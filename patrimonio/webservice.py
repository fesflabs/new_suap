# -*- coding: utf-8 -*-

from datetime import datetime
from django.db import IntegrityError, transaction
from patrimonio.models import Inventario, ConferenciaSala, ConferenciaItem, ConferenciaItemErro
import json


def set_inventarios_coletor(conferencia_id, token, dump_json):
    try:
        conferencia = ConferenciaSala.objects.get(pk=conferencia_id)
    except ConferenciaSala.DoesNotExist:
        return "ERROR|Sala inexistente no SUAP."

    # token confere?
    if conferencia.token != token:
        return "ERROR|Coleta não autorizada para esta sala."

    # trata JSON
    obj = json.loads(dump_json)

    for inventario, conteudo in list(obj.items()):
        # convertendo data/hora para padrao do Python/Django
        data_hora = datetime.strptime(conteudo, '%d/%m/%Y %H:%M:%S')
        # verifica se inventário existe no SUAP
        try:
            i = Inventario.objects.get(numero=inventario)
            # grava na tabela de conferência
            try:
                with transaction.atomic():
                    ConferenciaItem.objects.create(conferencia=conferencia, inventario=i, dh_coleta=data_hora)
            except IntegrityError:
                # msg = 'O item {0} ja foi gravado anteriormente'.format(inventario)
                # print(msg)
                pass
        except Inventario.DoesNotExist:
            # msg = 'O item {0} nao existe'.format(inventario)
            # print(msg)
            # grava na tabela de inventários não encontrados
            try:
                with transaction.atomic():
                    ConferenciaItemErro.objects.create(conferencia=conferencia, inventario=inventario, dh_coleta=data_hora)
            except IntegrityError:
                # msg='O item {0} ja possui uma entrada no log de erro'.format(inventario)
                # print(msg)
                pass
        except Exception as e:
            return "ERROR|{}".format(e)
    #
    return "SUCCESS|Conferência gravada com sucesso."


exposed = [[set_inventarios_coletor, 'set_inventarios_coletor']]
