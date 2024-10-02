## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Categoria Material de Consumo
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Categoria Material de Consumo: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel             |
#        |   ContadorSistemico |
#        |   Contador            |
#        |   ContadorAdministra  |
#        |   Auditor             |
#        |   CoordeDeAlmoxa      |
#        |   CoordDeAlmoxSiste   |  
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Categoria Material de Consumo: Verifica se o <Papel> não tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        | Papel             |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  | Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      |   Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   |   Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   |   Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    |   Mensagem: Erro no sistema
#
#    Esquema do Cenário: Verifica se o <Papel> pode Adicionar Elemento de Despesa de Mat. de Consumo
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Adicionar Elemento de Despesa de Mat. de Consumo"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        | Papel             |
#        #| ContadorSistemico | Não consegue visualizar o botão