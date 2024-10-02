## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Plano de Contas
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Plano de Contas: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/planocontasalmox/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        #|   CoordDeAlmoxSiste   |
#        #|   CoordeDeAlmoxa      |
#        #|   OperadDeAlmoxa      |
#        |   Auditor             |
#        |   ContadorSistemico   |
#        |   ContadorAdministra  |
#        |   Contador            |
#
#        # Os seguintes grupos não possuem acesso ao menu
#        #|   CoordDeAlmoxSiste   |
#        #|   CoordeDeAlmoxa      |
#        #|   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Plano de Contas: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/planocontasalmox/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      |    Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   |    Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   |    Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    |    Mensagem: Erro no sistema
#
#    Esquema do Cenário: Verifica se o <Papel> pode Adicionar Plano de Contas
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/planocontasalmox/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E vejo o botão "Adicionar Plano de Contas"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   ContadorSistemico   |
#        |   ContadorAdministra  |
#        |   Contador            |
#
#        # Os seguintes grupos não possuem acesso ao menu
#        #|   CoordDeAlmoxSiste   |
#        #|   CoordeDeAlmoxa      |
#        #|   OperadDeAlmoxa      |
#
#
#    Esquema do Cenário: Verifica se o <Papel> NÂO pode ver o botão Adicionar Plano de Contas
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/planocontasalmox/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E nao vejo o botão "Adicionar Plano de Contas"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             |
#
#        # Os seguintes grupos não possuem acesso ao menu
#        #|   CoordDeAlmoxSiste   |
#        #|   CoordeDeAlmoxa      |
#        #|   OperadDeAlmoxa      |
#
#
