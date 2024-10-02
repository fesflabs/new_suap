## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Autorização do Menu: Administração::Almoxarifado::Relatórios
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Saídas por Setor: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/relatorio/consumo_setor/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Saídas por Setor: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/relatorio/consumo_setor/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  | Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      |   Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   |   Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   |   Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    |   Mensagem: Erro no sistema
#        #|   ContadorSistemico   |   Mensagem: Erro no sistema
#
#    Esquema do Cenário: Saídas por Setor: Verifica se o <Papel> ver o botão Enviar 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/relatorio/consumo_setor/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Materiais Transferidos: Verifica o acesso do <Papel> a página por meio de link 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/materiais_transferidos/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Materiais Transferidos: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/materiais_transferidos/"
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
#        #|   ContadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      |    Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   |    Mensagem: Erro no sistema   
#        #|   ContaDePatriSiste   |    Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema
#
#    Esquema do Cenário: Materiais Transferidos: Verifica se o <Papel> ver o botão Enviar 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/materiais_transferidos/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Balancete::Elemento de Despesa: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_ed/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#
#
#    Esquema do Cenário: Balancete::Elemento de Despesa: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_ed/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
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
#    Esquema do Cenário: Balancete::Elemento de Despesa: Verifica se o <Papel> ver o botão Enviar 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_ed/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        
#    Esquema do Cenário: Balancete::Material de Consumo: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_material/"
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
#    Esquema do Cenário: Balancete::Material de Consumo: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_material/"
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
#    Esquema do Cenário: Balancete::Material de Consumo: Verifica se o <Papel> ver o botão Enviar 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_material/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#
#    Esquema do Cenário: Balancete::Elemento de Despesa Detalhado: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_ed_detalhado/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Balancete::Elemento de Despesa Detalhado: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_ed_detalhado/"
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
#    Esquema do Cenário: Balancete::Elemento de Despesa Detalhado: Verifica se o <Papel> ver o botão Enviar 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/almoxarifado/balancete_ed_detalhado/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        |   Auditor             |
#
#    Esquema do Cenário: Total por ED Permanente: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/patrimonio/total_ed_periodo/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        #|   Auditor             | Falha no teste: Não possui acesso ao menu
#
#    Esquema do Cenário: Total por ED Permanente: Verifica se o <Papel> NÃO tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/patrimonio/total_ed_periodo/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   AdminiDePlanej      |
#        |   ContadorAdministra  |
#        |   Contador            |
#        #|   CoordeDePatrim      | Tem acesso mas não deveria
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   AdminiDeOrcame      | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   | Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   | Mensagem: Erro no sistema
#        #|   GereDoCataDeMate    | Mensagem: Erro no sistema
#        #|   ContadorSistemico   | Mensagem: Erro no sistema
#
#    Esquema do Cenário: Total por ED Permanente: Verifica se o <Papel> ver o botão Enviar 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/patrimonio/total_ed_periodo/"
#        Então vejo o botão "Enviar"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordDeAlmoxSiste   |
#        |   CoordeDeAlmoxa      |
#        |   OperadDeAlmoxa      |
#        #|   Auditor             | Falha no teste: Não possui acesso ao menu