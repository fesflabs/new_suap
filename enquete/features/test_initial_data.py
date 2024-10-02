# -*- coding: utf-8 -*-


def initial_data():
    from comum.models import Publico

    # Criando Público Alvo
    Publico.get_or_create(nome="Servidores", modelo_base=Publico.BASE_SERVIDOR, filtro='{"excluido": false}', filtro_exclusao='{"excluido": true}')
