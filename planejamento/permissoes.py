# -*- coding: utf-8 -*-

TIPO_PERMISSAO = ['add', 'change', 'delete']

gp = dict()


def get_lista_permissao(lista, permissoes):
    retLista = []
    for item in lista:
        if item[0] in permissoes:
            retLista.append(item[1])

    return retLista


def planejamento_permissoes(gp):
    # Listas de perfis de permissão
    gp_administrador = []
    gp_gerente_sistemico = []
    gp_gerente_campus = []

    # Listas de permissões por modelo
    configuracao = [[i, 'planejamento.configuracao.%s_configuracao' % (i)] for i in TIPO_PERMISSAO]
    dimensao = [[i, 'planejamento.dimensao.%s_dimensao' % (i)] for i in TIPO_PERMISSAO]
    origemrecurso = [[i, 'planejamento.origemrecurso.%s_origemrecurso' % (i)] for i in TIPO_PERMISSAO]
    unidade_administrativa = [[i, 'planejamento.unidadeadministrativa.%s_unidadeadministrativa' % (i)] for i in TIPO_PERMISSAO]
    unidade_medida = [[i, 'planejamento.unidademedida.%s_unidademedida' % (i)] for i in TIPO_PERMISSAO]
    natureza_despesa = [[i, 'planejamento.naturezadespesa.%s_naturezadespesa' % (i)] for i in TIPO_PERMISSAO]
    objetivo_estrategico = [[i, 'planejamento.objetivoestrategico.%s_objetivoestrategico' % (i)] for i in TIPO_PERMISSAO]
    meta = [[i, 'planejamento.meta.%s_meta' % (i)] for i in TIPO_PERMISSAO]
    meta_unidade = [[i, 'planejamento.metaunidade.%s_metaunidade' % (i)] for i in TIPO_PERMISSAO]
    meta_unidade_acao_proposta = [[i, 'planejamento.metaunidadeacaoproposta.%s_metaunidadeacaoproposta' % (i)] for i in TIPO_PERMISSAO]
    acao_proposta = [[i, 'planejamento.acaoproposta.%s_acaoproposta' % (i)] for i in TIPO_PERMISSAO]
    acao = [[i, 'planejamento.acao.%s_acao' % (i)] for i in TIPO_PERMISSAO]
    acaoextrateto = [[i, 'planejamento.acaoextrateto.%s_acaoextrateto' % (i)] for i in TIPO_PERMISSAO]
    atividade = [[i, 'planejamento.atividade.%s_atividade' % (i)] for i in TIPO_PERMISSAO]

    # Cria permissoes para Administrador de acordo com o ticket #533
    #     - Cadastro de Configuracoes
    #     - Cadastro de Dimensoes
    #     - Cadastro de Unidades Administrativas
    #     - Cadastro de Unidades de Medida
    gp_administrador += get_lista_permissao(configuracao, ['add', 'change'])
    gp_administrador += get_lista_permissao(dimensao, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(origemrecurso, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(unidade_administrativa, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(unidade_medida, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(natureza_despesa, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(objetivo_estrategico, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(meta, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(meta_unidade, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(acao_proposta, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(meta_unidade_acao_proposta, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(acao, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(acaoextrateto, ['add', 'change', 'delete'])
    gp_administrador += get_lista_permissao(atividade, ['add', 'change', 'delete'])

    # Cria permissoes para Gerente Sistêmico de acordo com o ticket #533
    #     - Cadastro de Objetivos Estratégicos
    #     - Cadastro de Metas
    #     - Cadastro de Ações Propostas
    #     - Cadastro de Ações
    #     - Cadastro de Atividades
    gp_gerente_sistemico += get_lista_permissao(objetivo_estrategico, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(meta, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(meta_unidade, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(acao_proposta, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(meta_unidade_acao_proposta, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(acao, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(acaoextrateto, ['add', 'change', 'delete'])
    gp_gerente_sistemico += get_lista_permissao(atividade, ['add', 'change', 'delete'])

    # Cria permissoes para Gerente Campus de acordo com o ticket #533
    #     - Cadastro de Ações
    #     - Cadastrp de Atividades
    gp_gerente_campus += get_lista_permissao(meta_unidade, ['change'])
    gp_gerente_campus += get_lista_permissao(acao, ['add', 'change', 'delete'])
    gp_gerente_campus += get_lista_permissao(acao_proposta, ['add', 'change', 'delete'])
    gp_gerente_campus += get_lista_permissao(acaoextrateto, ['add', 'change', 'delete'])
    gp_gerente_campus += get_lista_permissao(atividade, ['add', 'change', 'delete'])

    # Faz a associacao com o dicionário de grupos e permissões
    gp["Administrador de Planejamento"] = gp_administrador
    gp["Coordenador de Planejamento Sistêmico"] = gp_gerente_sistemico
    gp["Coordenador de Planejamento"] = gp_gerente_campus
