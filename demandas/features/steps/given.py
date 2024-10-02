from behave import given


@given('os cadastros básicos do módulo de demandas')
def step_cadastros_do_modulo_demandas(context):
    from comum.models import AreaAtuacao, User
    from demandas.models import AreaAtuacaoDemanda, Tag

    area, _ = AreaAtuacao.objects.get_or_create(nome='Tecnologia da Informação')
    tag1, _ = Tag.objects.get_or_create(nome='Tag Especial')
    demandante, _ = User.objects.get_or_create(username='105001')
    area_atuacao = AreaAtuacaoDemanda.objects.get_or_create(area=area, )[0]
    area_atuacao.demandante_responsavel = demandante
    area_atuacao.recebe_sugestoes = True
    area_atuacao.save()
    area_atuacao.tags_relacionadas.set([tag1])
