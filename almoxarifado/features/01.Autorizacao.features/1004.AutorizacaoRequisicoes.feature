## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu -> Administração::Almoxarifado::Requisições
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Saída de Material para Consumo: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/form_requisicao_usuario_pedido/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Saída de Material para Consumo: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/form_requisicao_usuario_pedido/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        #|   GereDeMateDoAlmo    | Mensagem: "Página não encontrada"
#        |   AdminiDePlanej      |
#        |   Auditor             |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   | Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   | Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema
#    
#    Esquema do Cenário: Saída de Material para Consumo: Verifica o o <Papel> ver o botão Adicionar Material
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/form_requisicao_usuario_pedido/"
#        Então vejo o botão "Adicionar Material"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Transferência de Material Intercampi: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/form_requisicao_uo_pedido/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Transferência de Material Intercampi: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/form_requisicao_uo_pedido/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        #|   GereDeMateDoAlmo    | Mensagem: "Página não encontrada"
#        |   AdminiDePlanej      |
#        |   Auditor             |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   | Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   | Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema
#
#    Esquema do Cenário: Transferência de Material Intercampi: Verifica o o <Papel> ver o botão Adicionar Material
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/form_requisicao_uo_pedido/"
#        Então vejo o botão "Adicionar Material"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Buscar Requisições: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/requisicao_busca/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Buscar Requisições: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/requisicao_busca/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   | Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   | Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema
#
#    Esquema do Cenário: Buscar Requisições: Verifica se o <Papel> ver o botão enviar
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/requisicao_busca/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Requisições Pendentes: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/tela_requisicoes_pendentes/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#       #|   Auditor             | Falha no teste: Não possui acesso ao menu
#
#    Esquema do Cenário: Requisições Pendentes: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/tela_requisicoes_pendentes/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        #|   GereDeMateDoAlmo    | Mensagem: "Página não encontrada"
#        #|   AdminiDePlanej      | Mensagem: "Página não encontrada"
#        #|   ContadorAdministra  | Mensagem: "Página não encontrada"
#        #|   Contador            | Mensagem: "Página não encontrada"
#        #|   CoordeDePatrim      | Mensagem: "Página não encontrada"
#        #|   OperadordePatrimonio| Mensagem: Erro no sistema
#        #|   ContadordePatrimonio| Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   | Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   | Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema