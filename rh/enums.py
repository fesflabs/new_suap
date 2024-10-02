# -*- coding: utf-8 -*-


class Nacionalidade:
    BRASILEIRO_NATO = 1
    BRASILEIRO_NATZ = 2
    EQUIPARADO = 3
    ESTRANGEIRO = 4

    NACIONALIDADE_DICT = {
        BRASILEIRO_NATO: 'Brasileiro Nato',
        BRASILEIRO_NATZ: 'Brasileiro Naturalizado',
        EQUIPARADO: 'Equiparado',
        ESTRANGEIRO: 'Estrangeiro'
    }

    @classmethod
    def get_choices(cls):
        return [[x, y] for x, y in cls.NACIONALIDADE_DICT.items()]
