## -*- coding: utf-8 -*-
## language: pt
#
#Funcionalidade: Testando a exibição do menu
#    Essa funcionalidade é para testar se de acordo com as autorizações o usuario pode acessar os menus visiveis
#
#    Cenário: Adiciona os usuários necessários para esse teste
#        Dado os usuarios do Almoxarifado
#
#    Esquema do Cenário: Verifica o acesso pelo <Papel>
#        Dado acesso a página "/"
#        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        E nao vejo a página "Página não encontrada"
#        Quando acesso o menu "Sair"
#        Exemplos:
#            |   Papel               |
#            |   CoordeDeAlmoxa      |
#            |   GereDeMateDoAlmo    |
#            |   AdminiDePlanej      |
#            |   OperadDeAlmoxa      |
#            |   Auditor             |
#            |   ContadorAdministra  |
#            |   Contador            |
#            |   CoordeDePatrim      | 
#            |   OperadordePatrimonio  |  
#            |   ContadordePatrimonio  |
#            |   AdminiDeOrcame      |
#            |   CoordDePatriSiste   |
#            |   ContaDePatriSiste   |
#            |   GereDoCataDeMate    |
#            |   ContadorSistemico   |
#            |   CoordDeAlmoxSiste   |       
#
#    Esquema do Cenario: Verifica os menus do Coordenador de Almoxarifado
#        Dado acesso a página "/"
#        Quando olho para a página
#        E realizo o login com o usuário "CoordeDeAlmoxa" e senha "abcd"
#        E acesso o menu "<Menu>"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |Menu|
#        |Administração::Almoxarifado::Entradas |
#        |Administração::Almoxarifado::Requisições::Saída de Material para Consumo|
#        |Administração::Almoxarifado::Requisições::Transferência de Material Intercampi|
#        |Administração::Almoxarifado::Requisições::Buscar Requisições|
#        |Administração::Almoxarifado::Requisições::Requisições Pendentes|
#        |Administração::Almoxarifado::Empenhos|
#        |Administração::Almoxarifado::Relatórios::Saídas por Setor|
#        |Administração::Almoxarifado::Relatórios::Materiais Transferidos|
#        |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa|
#        |Administração::Almoxarifado::Relatórios::Balancete::Material de Consumo|
#        |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa Detalhado|
#        |Administração::Almoxarifado::Relatórios::Total por ED Permanente|
#        |Administração::Almoxarifado::Controle de Estoque Crítico|
#        |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#        |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#        |Administração::Almoxarifado::Cadastros::Unidades de Medida|
#        |Administração::Almoxarifado::Materiais de Consumo|
#
#    Esquema do Cenario: Verifica os menus do Operador de Almoxarifado
#        Dado acesso a página "/"
#        Quando olho para a página
#        E realizo o login com o usuário "OperadDeAlmoxa" e senha "abcd"
#        E acesso o menu "<Menu>"
#        Então nao vejo a página "Você não tem permissão para acessar essa página"
#        Quando acesso o menu "Sair"
#        Exemplos:
#        |Menu|
#        |Administração::Almoxarifado::Entradas |
#        |Administração::Almoxarifado::Requisições::Saída de Material para Consumo|
#        |Administração::Almoxarifado::Requisições::Transferência de Material Intercampi|
#        |Administração::Almoxarifado::Requisições::Buscar Requisições|
#        |Administração::Almoxarifado::Requisições::Requisições Pendentes|
#        |Administração::Almoxarifado::Empenhos|
#        |Administração::Almoxarifado::Materiais de Consumo|
#        |Administração::Almoxarifado::Relatórios::Saídas por Setor|
#        |Administração::Almoxarifado::Relatórios::Materiais Transferidos|
#        |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa|
#        |Administração::Almoxarifado::Relatórios::Balancete::Material de Consumo|
#        |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa Detalhado|
#        |Administração::Almoxarifado::Relatórios::Total por ED Permanente|
#        |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#        |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#        |Administração::Almoxarifado::Cadastros::Unidades de Medida|
#
#    Esquema do Cenario: Verifica os menus do Gerenciador do Catálogo de Materiais
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "GereDeMateDoAlmo" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Materiais de Consumo|
#
#    Esquema do Cenario: Verifica os menus do Administrador de Planejamento
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "AdminiDePlanej" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            # O grupo não consegue acessar os seguintes menus
#            # |Administração::Almoxarifado::Cadastros::Unidades de Medida|
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Auditor
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "Auditor" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Entradas|
#            |Administração::Almoxarifado::Requisições::Buscar Requisições|
#            |Administração::Almoxarifado::Relatórios::Saídas por Setor|
#            |Administração::Almoxarifado::Relatórios::Materiais Transferidos|
#            |Administração::Almoxarifado::Relatórios::Balancete::Material de Consumo|
#            |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa Detalhado|
#            |Administração::Almoxarifado::Controle de Estoque Crítico|
#            |Administração::Almoxarifado::Plano de Contas|
#            |Administração::Almoxarifado::Cadastros::Unidades de Medida|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#            # O grupo não consegue acessar os seguintes menus
#            #|Administração::Almoxarifado::Relatórios::Total por ED Permanente|
#            #|Administração::Almoxarifado::Requisições::Requisições Pendentes|
#
#    Esquema do Cenario: Verifica os menus do Contador
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "Contador" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Plano de Contas|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            # O grupo não consegue acessar os seguintes menus
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Coordenador de Patrimônio
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "CoordeDePatrim" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Contador Administrador
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "ContadorAdministra" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Plano de Contas|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            # O grupo não consegue acessar os seguintes menus
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Operador de Patrimônio      
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "OperadordePatrimonio" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            | Menu |
#            | Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Contador de Patrimônio     
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "ContadordePatrimonio" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            | Menu |
#            | Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#
#    Esquema do Cenario: Verifica os menus do Administrador de Orçamento    
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "AdminiDeOrcame" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            # O grupo não tem acesso aos seguintes menus
#            # |Administração::Almoxarifado::Cadastros::Unidades de Medida|
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Coordenador de Patrimônio Sistêmico    
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "CoordDePatriSiste" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Contador de Patrimônio Sistêmico     
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "ContaDePatriSiste" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#
#    Esquema do Cenario: Verifica os menus do Gerenciador do Catálogo de Materiais     
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "GereDoCataDeMate" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            
#            # O grupo não possui acesso aos seguintes menus
#            # |Administração::Almoxarifado::Cadastros::Unidades de Medida|
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            # |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#    Esquema do Cenario: Verifica os menus do Contador Sistêmico      
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "ContadorSistemico" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Plano de Contas|
#            |Administração::Almoxarifado::Categoria Material de Consumo|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            
#            # O grupo não tem acesso a esse menu
#            #|Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|
#
#
#    Esquema do Cenario: Verifica os menus do Coordenador de Almoxarifado Sistêmico      
#            Dado acesso a página "/"
#            Quando olho para a página
#            E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#            E acesso o menu "<Menu>"
#            Então nao vejo a página "Você não tem permissão para acessar essa página"
#            Quando acesso o menu "Sair"
#            Exemplos:
#            |Menu|
#            |Administração::Almoxarifado::Entradas|
#            |Administração::Almoxarifado::Requisições::Saída de Material para Consumo|
#            |Administração::Almoxarifado::Requisições::Transferência de Material Intercampi|
#            |Administração::Almoxarifado::Requisições::Buscar Requisições|
#            |Administração::Almoxarifado::Requisições::Requisições Pendentes|
#            |Administração::Almoxarifado::Empenhos|
#            |Administração::Almoxarifado::Relatórios::Saídas por Setor|
#            |Administração::Almoxarifado::Relatórios::Materiais Transferidos|
#            |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa|
#            |Administração::Almoxarifado::Relatórios::Balancete::Material de Consumo|
#            |Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa Detalhado|
#            |Administração::Almoxarifado::Relatórios::Total por ED Permanente|
#            |Administração::Almoxarifado::Controle de Estoque Crítico|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo|
#            |Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. Permanente|