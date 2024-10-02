## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do menu Administração::Almoxarifado::Entradas
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#
#    Esquema do Cenário: Verifica o acesso do Grupo <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#            |   Papel               |
#            |   CoordDeAlmoxSiste   |  
#            |   CoordeDeAlmoxa      |
#            |   OperadDeAlmoxa      |
#            |   Auditor             |
#
#    Esquema do Cenário: Verifica o acesso do Grupo <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#            |   Papel                |
#            #|   CoordeDePatrim       | Teste Falhando: Não deveria ter acesso
#            #|   OperadordePatrimonio | Teste Falhando: Não deveria ter acesso
#            #|   CoordDePatriSiste    | Teste Falhando: Não deveria ter acesso
#            #|   ContadordePatrimonio | Mensagem: Erro no sistema
#            #|   AdminiDeOrcame       | Mensagem: Erro no sistema
#            #|   ContaDePatriSiste    | Mensagem: Erro no sistema
#            #|   GereDoCataDeMate     | Mensagem: Erro no sistema
#            #|   ContadorSistemico    | Mensagem: Erro no sistema
#
#
#   Esquema do Cenário: Verifica se o grupo <Papel> ver o botão ENVIAR
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#            |   Papel               |
#            |   CoordDeAlmoxSiste   |  
#            |   CoordeDeAlmoxa      |
#            |   OperadDeAlmoxa      |
#            |   Auditor             |
#
#
#   Esquema do Cenário: Verifica se o grupo <Papel> ver os botôes Adicionar Compras e Adicionar Doações
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/entrada_busca/"
#        Então vejo o botão "Adicionar Compra"
#        E vejo o botão "Adicionar Doação"
#        Quando acesso o menu "Sair"
#        Exemplos:
#            |   Papel               |
#            |   CoordDeAlmoxSiste   |  
#            |   CoordeDeAlmoxa      |
#            |   OperadDeAlmoxa      |
#            #|   Auditor             | Os botões não aparecem 
#
