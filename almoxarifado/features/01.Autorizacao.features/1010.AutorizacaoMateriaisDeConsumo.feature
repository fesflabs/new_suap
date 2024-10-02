## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Materiais de Consumo
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Materiais de Consumo: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#        |   GereDeMateDoAlmo    |
#
#    Esquema do Cenário: Materiais de Consumo: Verifica se o <Papel> não tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   AdminiDePlanej      |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  
#        #|   ContadordePatrimonio  |
#        #|   AdminiDeOrcame      |
#        #|   CoordDePatriSiste   |
#        #|   ContaDePatriSiste   |
#        #|   GereDoCataDeMate    |
#        #|   ContadorSistemico   |
#
#    Esquema do Cenário: Verifica o <Papel> pode Adicionar Material de Consumo
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Adicionar Material de Consumo"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   GereDeMateDoAlmo    |
#
#
#    Esquema do Cenário: Verifica o <Papel> NÃO ver o botão Adicionar Material de Consumo
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E nao vejo o botão "Adicionar Material de Consumo"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             |
#          
#
#    Esquema do Cenário: Verifica o <Papel> pode Exportar para CSV
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Exportar para CSV"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#        |   GereDeMateDoAlmo    |
#
#    Esquema do Cenário: Verifica o <Papel> pode Exportar para XLS
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Exportar para XLS"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#        |   GereDeMateDoAlmo    |
#
#    Esquema do Cenário: Verifica o <Papel> pode Gerar Etiquetas
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/materialconsumo/?tab=tab_estoque_atual"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Gerar Etiquetas"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#        |   GereDeMateDoAlmo    |
#
