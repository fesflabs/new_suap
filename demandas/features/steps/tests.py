# -*- coding: utf-8 -*-

from comum.models import User, AreaAtuacao
from demandas.forms import SugestaoMelhoriaAddForm
from demandas.models import AreaAtuacaoDemanda, SugestaoMelhoria


def sugestao_melhoria_adicionar():
    area, _ = AreaAtuacao.objects.get_or_create(nome='Área de Atuação')
    area_demanda, _ = AreaAtuacaoDemanda.objects.get_or_create(area=area)
    requisitante, _ = User.objects.get_or_create(username='Requisitante')
    tags_relacionadas = area_demanda.tags_relacionadas.all()

    form = SugestaoMelhoriaAddForm(
        {
            'requisitante_info': '{}'.format(requisitante),
            'area_atuacao_info': '{}'.format(area_demanda),
            'tags_info': '{}'.format(', '.join('{}'.format(_) for _ in tags_relacionadas)),
            'titulo': 'Sugestão de Teste 1',
            'descricao': 'Detalhamento da Sugestão de Teste 1'
        },
        area_atuacao=area_demanda,
        tags=tags_relacionadas,
        user_requisitante=requisitante
    )

    form.is_valid() and form.save()

    return "Ok" if SugestaoMelhoria.objects.filter(titulo='Sugestão de Teste 1').exists() else "Teste falhou!"


def sugestao_melhoria_permissoes():
    area, _ = AreaAtuacao.objects.get_or_create(nome='Área de Atuação')
    area_demanda, _ = AreaAtuacaoDemanda.objects.get_or_create(area=area)

    demandante, _ = User.objects.get_or_create(username='Demandante')
    demandante2, _ = User.objects.get_or_create(username='Demandante2')
    requisitante, _ = User.objects.get_or_create(username='Requisitante')
    responsavel, _ = User.objects.get_or_create(username='Responsável')

    area_demanda.demandantes.add(responsavel)
    area_demanda.save()

    sugestao_melhoria = SugestaoMelhoria(
        area_atuacao=area_demanda,
        requisitante=requisitante,
        titulo='Teste',
        descricao='Teste',
        responsavel=responsavel
    )
    sugestao_melhoria.save()

    result = (
        sugestao_melhoria.pode_editar_todos_dados(demandante) is True
        and sugestao_melhoria.pode_editar_todos_dados(demandante2) is False
        and sugestao_melhoria.pode_editar_todos_dados(requisitante) is False
        and sugestao_melhoria.pode_editar_todos_dados(responsavel) is True
        and sugestao_melhoria.pode_editar_dados_basicos(requisitante) is True
        and sugestao_melhoria.pode_visualizar(demandante) is True
        and sugestao_melhoria.pode_gerar_demanda(demandante) is False
        and sugestao_melhoria.pode_gerar_demanda(responsavel) is False
        and sugestao_melhoria.pode_registrar_comentario(requisitante) is True
    )

    sugestao_melhoria.situacao = SugestaoMelhoria.SITUACAO_DEFERIDA
    sugestao_melhoria.save()

    result = (
        result
        and sugestao_melhoria.pode_gerar_demanda(demandante) is False
        and sugestao_melhoria.pode_gerar_demanda(responsavel) is True
        and sugestao_melhoria.pode_registrar_comentario(requisitante) is False
    )

    return "Ok" if result else "Teste falhou!"


def sugestao_melhoria_demanda_gerada():
    area, _ = AreaAtuacao.objects.get_or_create(nome='Área de Atuação')
    area_demanda, _ = AreaAtuacaoDemanda.objects.get_or_create(area=area)

    requisitante, _ = User.objects.get_or_create(username='Requisitante')
    responsavel2, _ = User.objects.get_or_create(username='Responsável2')
    responsavel3, _ = User.objects.get_or_create(username='Responsável3')

    area_demanda.demandantes.add(responsavel2)
    area_demanda.save()

    sugestao_melhoria = SugestaoMelhoria(
        area_atuacao=area_demanda,
        requisitante=requisitante,
        titulo='Teste',
        descricao='Teste',
        responsavel=responsavel2,
        situacao=SugestaoMelhoria.SITUACAO_DEFERIDA
    )
    sugestao_melhoria.save()

    result = (
        sugestao_melhoria.pode_gerar_demanda(responsavel2) is True
        and sugestao_melhoria.pode_gerar_demanda(responsavel3) is False
    )

    sugestao_melhoria.gerar_demanda(responsavel2)

    result = (
        result
        and sugestao_melhoria.pode_gerar_demanda(responsavel2) is False
        and sugestao_melhoria.pode_excluir_demanda_gerada(responsavel2) is True
        and sugestao_melhoria.pode_excluir_demanda_gerada(responsavel3) is False
    )

    return "Ok" if result else "Teste falhou!"
