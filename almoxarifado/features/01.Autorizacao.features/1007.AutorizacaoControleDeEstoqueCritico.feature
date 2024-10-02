## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Controle de Estoque Crítico
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Controle de Estoque Crítico: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/situacao_estoque/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Controle de Estoque Crítico: Verifica se o <Papel> não pode acessar a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/situacao_estoque/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   OperadDeAlmoxa      |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Menssagem: Erro no Sistema
#        #|   ContadordePatrimonio  |  Menssagem: Erro no Sistema
#        #|   AdminiDeOrcame      |    Menssagem: Erro no Sistema
#        #|   CoordDePatriSiste   |    Menssagem: Erro no Sistema
#        #|   ContaDePatriSiste   |    Menssagem: Erro no Sistema
#        #|   GereDoCataDeMate    |    Menssagem: Erro no Sistema
#        #|   ContadorSistemico   |    Menssagem: Erro no Sistema
#
#    Esquema do Cenário: Verifica se o <Papel> ver o botão Adicionar Material Controlado
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/situacao_estoque/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Adicionar Material Controlado"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   Auditor             |
#
#
#    Esquema do Cenário: Verifica se o <Papel> vero o botão Gerar Lista de Compra em HTML
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/situacao_estoque/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão de ação "Gerar Lista de Compra em HTML"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Verifica se o <Papel> ver o botão Gerar Lista de Compra em PDF
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/situacao_estoque/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão de ação "Gerar Lista de Compra em PDF"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   Auditor             |
