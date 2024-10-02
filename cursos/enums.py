# -*- coding: utf-8 -*-


class TipoCurso:
    CONCURSO = 1
    CURSO = 2
    ATIVIDADE_EXTERNA = 3

    @classmethod
    def get_choices(cls):
        return [[cls.CONCURSO, 'Concurso'], [cls.CURSO, 'Curso'], [cls.ATIVIDADE_EXTERNA, 'Atividade Externa']]


class SituacaoCurso:
    NAO_INICIADO = 0
    INICIADO = 1
    FINALIZADO = 2
    AGUARDANDO_CADASTRO_EM_FOLHA = 3
    CADASTRADO_EM_FOLHA = 4

    @classmethod
    def get_choices(cls):
        return [
            [cls.NAO_INICIADO, 'Não iniciado'],
            [cls.INICIADO, 'Iniciado'],
            [cls.FINALIZADO, 'Finalizado'],
            [cls.AGUARDANDO_CADASTRO_EM_FOLHA, 'Aguardando cadastro em Folha'],
            [cls.CADASTRADO_EM_FOLHA, 'Cadastrado em Folha'],
        ]


class SituacaoParticipante:
    LIBERADO = 0
    NAO_LIBERADO = 1
    AGUARDANDO_LIBERACAO = 2
    PENDENTE = 3

    @classmethod
    def get_choices(cls):
        return [
            [cls.LIBERADO, 'Liberado pela Chefia'],
            [cls.NAO_LIBERADO, 'Não Liberado pela Chefia'],
            [cls.AGUARDANDO_LIBERACAO, 'Aguardando Liberação'],
            [cls.PENDENTE, 'Pendente'],
        ]
