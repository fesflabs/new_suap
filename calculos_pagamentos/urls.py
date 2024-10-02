# -*- coding: utf-8 -*

from django.urls import path

from . import views

urlpatterns = [
    # IFMA/Tássio
    path('get_valores/', views.get_valores),
    # path('gerar_documentocalculosubstituicao/<int:pk>/', views.gerar_documentocalculosubstituicao),
    path('calculosubstituicao/<int:pk>/', views.calculosubstituicao),
    path('calculoprogressao/<int:pk>/', views.calculoprogressao),
    path('calculopericulosidade/<int:pk>/', views.calculopericulosidade),
    path('calculoinsalubridade/<int:pk>/', views.calculoinsalubridade),
    path('calculort/<int:pk>/', views.calculort),
    path('calculorsc/<int:pk>/', views.calculorsc),
    path('calculoiq/<int:pk>/', views.calculoiq),
    path('', views.calculos),
    path('calculomudancaregime/<int:pk>/', views.calculomudancaregime),
    path('calculotransporte/<int:pk>/', views.calculotransporte),
    path('calculopermanencia/<int:pk>/', views.calculopermanencia),
    path('calculonomeacaocd/<int:pk>/', views.calculonomeacaocd),
    path('calculoexoneracaocd/<int:pk>/', views.calculoexoneracaocd),
    path('calculodesignacaofg/<int:pk>/', views.calculodesignacaofg),
    path('calculodispensafg/<int:pk>/', views.calculodispensafg),
    path('criar_pagamento_substituicao/<int:pk>/', views.criar_pagamento_substituicao),
    path('pagamento/<int:pk>/', views.pagamento),
    path('gerar_arquivo_nao_processados/', views.gerar_arquivo_nao_processados),
    path('relatorio_detalhado/<int:pk>/', views.relatorio_detalhado),
    path('arquivo_aceitos/', views.arquivo_aceitos),
    path('arquivo_rejeitados/', views.arquivo_rejeitados),
    path('lancado_manualmente_substituicao/', views.lancado_manualmente_substituicao),
    path('regerar_arquivo/<int:pk>/', views.regerar_arquivo),
    path('calculoterminocontratoprofsubs/<int:pk>/', views.calculoterminocontrato),
    path('calculoterminocontratointerplibras/<int:pk>/', views.calculoterminocontrato),
    path('informar_irpf/<int:pk>/', views.informar_irpf),
    path('excluir_calculo/', views.excluir_calculo),
    path('excluir_pagamento/', views.excluir_pagamento),
    path('desfazer_pagamento/', views.desfazer_pagamento),
    path('alterar_para_lancado_manualmente/', views.alterar_para_lancado_manualmente),
    path('lancar_pagamento_manualmente/<int:calculo_id>/<int:calculo>/', views.lancar_pagamento_manualmente),
    path('criar_pagamento/<int:calculo_id>/<int:calculo>/', views.criar_pagamento),
]
