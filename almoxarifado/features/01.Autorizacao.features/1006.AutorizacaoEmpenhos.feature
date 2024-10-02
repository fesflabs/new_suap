## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Empenhos
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Empenhos: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/empenhos/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   Auditor             |
#        |   OperadDeAlmoxa      |
#        |   CoordeDeAlmoxa      |
#
#    Esquema do Cenário: Empenhos: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/empenhos/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
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
#    Esquema do Cenário: Verifica se o <Papel> pode enviar
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/empenhos/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   Auditor             |
#        |   OperadDeAlmoxa      |
#        |   CoordeDeAlmoxa      |
#
#    Esquema do Cenário: Verifica se o <Papel> pode adicionar empenho
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/empenhos/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Adicionar Empenho"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   Auditor             | 
#        |   OperadDeAlmoxa      |
#        |   CoordeDeAlmoxa      |
#        
## Auditor ver o botão mas ele não tem acesso a página