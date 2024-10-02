## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Entradas
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Entradas: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"       
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#
#    Esquema do Cenário: Entradas: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então vejo a página "Você não tem permissão para acessar essa página"       
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   ContadorAdministra  |
#        |   Contador            |
#        #|   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   | Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   | Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema
#
#    Esquema do Cenário:  Verifica se o <Papel> ver o botão enviar  
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Enviar"  
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário:  Verifica se o <Papel> ver o botão Adicionar compra
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Então vejo o botão "Adicionar Compra"  
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário:  Verifica se o <Papel> NÃO ver o botão Adicionar compra
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Então nao vejo o botão "Adicionar Compra"  
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel     |
#        |   Auditor   |
#  
#
#    Esquema do Cenário:  Verifica se o <Papel> ver o botão Adicionar Doação
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Então vejo o botão "Adicionar Doação"  
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário:  Verifica se o <Papel> NÃO ver o botão Adicionar Doação
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Então nao vejo o botão "Adicionar Doação"  
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             | 