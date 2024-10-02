from django.urls import path

from rest_framework_simplejwt.views import token_refresh, token_verify

from . import services

urlpatterns = [
    # OAuth apps
    path('applications/', services.ApplicationViewSet.as_view({'get': 'list', 'post': 'create'}), name='aplicacaooauth2-list'),
    path('applications/<int:pk>/', services.ApplicationViewSet.as_view({'get': 'retrieve', 'delete': 'destroy', 'put': 'update'}), name='aplicacaooauth2-detail'),
    # Novas URLs, serviços consumidos em nome do usuário
    path('eu/', services.eu),
    path('eu/grupos/', services.meus_grupos),
    # client-credentials (for application access without a user present)
    path('campi/', services.CampiViewSet.as_view({'get': 'list'})),
    path('servidores/', services.list_servidores),
    path('contracheques/', services.list_contracheques),
    # client-credentials (for application access without a user present) - Escope Integra
    path('servidores_integra/', services.list_servidores_integra),

    # TODO: Retirar JWT quando tiver login só via OAuth
    path('v2/autenticacao/token/', services.obtem_token_jwt, name="obtain_jwt_token"),
    path('v2/autenticacao/token/refresh/', token_refresh, name="refresh_jwt_token"),
    path('v2/autenticacao/token/verify/', token_verify, name="verify_jwt_token"),
    path('v2/autenticacao/acesso_responsaveis/', services.obtem_token_acesso_responsaveis, name="obtem_token_acesso_responsaveis"),
    # URLs legadas - principalmente SUAP mobile
    path('v2/eventos/banners/ativos/', services.obtem_banners_ativos_v2),
    path('v2/rh/unidades-organizacionais/', services.CampiViewSet.as_view({'get': 'list'})),
    path('v2/rh/servidores/', services.ServidoresViewSet.as_view({'get': 'list'})),
    path('v2/rh/setores/', services.SetorViewSet.as_view({'get': 'list'})),
    path('v2/minhas-informacoes/meus-dados/', services.obtem_meus_dados_v2),
    path('v2/minhas-informacoes/meu-historico-funcional/', services.obtem_historico_funcional_v2),
    path('v2/minhas-informacoes/minhas-frequencias/', services.obtem_frequencias_v2),
    path('v2/minhas-informacoes/minhas-ferias/', services.obtem_ferias_v2),
    path('v2/minhas-informacoes/ocorrencias-afastamentos/', services.obtem_ocorrencias_afastamentos_servidor_v2),
    path('v2/minhas-informacoes/participacoes-projetos/', services.obtem_participacoes_projeto_v2),
    path('v2/minhas-informacoes/meus-processos/', services.MeusProcessosViewSet.as_view({'get': 'list'})),
    path('v2/minhas-informacoes/meus-processos/<int:pk>/', services.DetalheProcessoViewSet.as_view({'get': 'retrieve'})),
    path('v2/minhas-informacoes/contracheques/', services.obtem_meus_contracheques_v2),
    path('v2/minhas-informacoes/contracheques/<int:ano>/<int:mes>/', services.obtem_detalhes_contracheque_v2),
    path('v2/minhas-informacoes/meus-periodos-letivos/', services.obtem_meus_periodos_letivos_v2),
    path('v2/minhas-informacoes/turma-virtual/<int:pk>/', services.turma_virtual_v2),
    path('v2/minhas-informacoes/turmas-virtuais/<int:ano_letivo>/<int:periodo_letivo>/', services.turmas_virtuais_v2),
    path('v2/minhas-informacoes/proximas-avaliacoes/', services.minhas_avaliacoes_v2),
    path('v2/minhas-informacoes/boletim/<int:ano_letivo>/<int:periodo_letivo>/', services.meu_boletim_v2),
    path('v2/minhas-informacoes/meus-diarios/<int:ano_letivo>/<int:periodo_letivo>/', services.meus_diarios_v2),
]
