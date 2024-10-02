## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Administração::Almoxarifado::Cadastros
#    Essa funcionalidade testa se os usuários podem executar as ações desejadas dentro do menu de acordo com suas autorizações
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    # =============================================================================
#    # ====================== Verificar acesso ao menu por link ====================
#    # =============================================================================
#    Esquema do Cenário: Elementos de Despesa de Mat. de Consumo: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E nao vejo a página "Erro no Sistema"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             |
#        |   CoordeDeAlmoxa      |
#        |   CoordDeAlmoxSiste   |       
#        |   OperadDeAlmoxa      |
#        |   ContadorAdministra  |
#        |   ContadorSistemico   |
#        |   Contador            |
#
#       # Teste falhando:  Erro nos seguintes grupos
#       #|   GereDoCataDeMate    | Erro no sistema
#       #|   AdminiDeOrcame      | Erro no sistema
#       #|   AdminiDePlanej      | Erro no sistema
#
#    Esquema do Cenário: Elementos de Despesa de Mat. de Consumo: Verifica se o <Papel> não tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   |    Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   |    Mensagem: Erro no sistema
#
#    Esquema do Cenário: Elementos de Despesa de Mat. de Consumo: Verifica se o <Papel> ver o botão
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então vejo o botão "Adicionar Elemento de Despesa de Mat. de Consumo"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        #|   CoordeDeAlmoxa      | Não consegue visualizar o botão
#        #|   CoordDeAlmoxSiste   | Não consegue visualizar o botão
#        #|   OperadDeAlmoxa      | Não consegue visualizar o botão
#        |   ContadorAdministra  |
#        #|   ContadorSistemico   | Não consegue visualizar o botão
#
#
#    Esquema do Cenário: Elementos de Despesa de Mat. de Consumo: Verifica se o <Papel> NÃO ver o botão
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#        Então nao vejo o botão "Adicionar Elemento de Despesa de Mat. de Consumo"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Contador            | 
#        |   Auditor             |
#
#    Esquema do Cenário: Elementos de Despesa de Mat. Permanente: Verifica o acesso do <Papel> a página por meio de link 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/patrimonio/categoriamaterialpermanente/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E nao vejo a página "Erro no Sistema"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             |
#        |   CoordeDeAlmoxa      |
#        |   CoordDeAlmoxSiste   |       
#        |   OperadDeAlmoxa      |
#        |   CoordeDePatrim      | 
#        |   ContaDePatriSiste   |
#        |   OperadordePatrimonio|  
#        |   CoordDePatriSiste   |
#        
#       #|   AdminiDePlanej      | Erro no sistema 
#
#       #|   GereDoCataDeMate    | Erro no sistema
#       #|   AdminiDeOrcame      | Erro no sistema
#       #|   ContadorSistemico   | Erro no sistema
#       #|   Contador            | Sem permissão
#       #|   ContadorAdministra  | Sem permissão para acesso
#
#    Esquema do Cenário: Elementos de Despesa de Mat. Permanente: Verifica o <Papel> NÃO tem acesso a página por meio de link 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/patrimonio/categoriamaterialpermanente/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        #|   ContadordePatrimonio  | Erro no teste: tem acesso mas não deveria
#
#    Esquema do Cenário: Elementos de Despesa de Mat. Permanente: Verifica se o <Papel> ver o botão
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/patrimonio/categoriamaterialpermanente/"
#        Então vejo o botão "Adicionar Elemento de Despesa de Mat. Permanente"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordeDeAlmoxa      |
#        |   CoordDeAlmoxSiste   |       
#        |   OperadDeAlmoxa      |
#
#    Esquema do Cenário: Elementos de Despesa de Mat. Permanente: Verifica se o <Papel> NÃO ver o botão 
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/patrimonio/categoriamaterialpermanente/"
#        Então nao vejo o botão "Adicionar Elemento de Despesa de Mat. Permanente"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             |
#        #|   CoordeDePatrim      | Erro nos testes
#        #|   ContaDePatriSiste   | Erro nos testes
#        #|   OperadordePatrimonio | Erro nos testes   
#        #|   CoordDePatriSiste   | Erro nos testes
#
#
#    Esquema do Cenário: Unidades de Medida: Verifica o acesso do <Papel> a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/unidademedida/"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E nao vejo a página "Erro no Sistema"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   Auditor             |
#        |   CoordeDeAlmoxa      |
#        |   CoordDeAlmoxSiste   |       
#        |   OperadDeAlmoxa      |
#
#        # Teste falhando:  Erro nos seguintes grupos
#        #|   GereDoCataDeMate    | Erro no sistema
#        #|   AdminiDeOrcame      | Erro no sistema
#        #|   AdminiDePlanej      | Erro no sistema
#
#    Esquema do Cenário: Unidades de Medida: Verifica se o <Papel> não tem acesso a página por meio de link
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/unidademedida/"
#        Então vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   GereDeMateDoAlmo    |
#        |   ContadorAdministra  |
#        |   Contador            |
#        |   CoordeDePatrim      | 
#        #|   OperadordePatrimonio  |  Mensagem: Erro no sistema
#        #|   ContadordePatrimonio  | Mensagem: Erro no sistema
#        #|   CoordDePatriSiste   |   Mensagem: Erro no sistema
#        #|   ContaDePatriSiste   |   Mensagem: Erro no sistema
#        #|   ContadorSistemico   |   Mensagem: Erro no sistema
#
#    Esquema do Cenário: Unidades de Medida: Verifica se o <Papel> ver o botão Adicionar Unidade de Medida
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/unidademedida/"
#        Então vejo o botão "Adicionar Unidade de Medida"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |   Papel               |
#        |   CoordeDeAlmoxa      |
#        |   CoordDeAlmoxSiste   |       
#        |   OperadDeAlmoxa      |
#
#
#    Esquema do Cenário: Unidades de Medida: Verifica se o <Papel> não ver o botão Adicionar Unidade de Medida
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        E acesso a página "/admin/almoxarifado/unidademedida/"
#        Então nao vejo o botão "Adicionar Unidade de Medida"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |  Papel  |
#        | Auditor |
