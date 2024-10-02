## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Relatórios::Balancete::Elemento de Despesa Detalhado
#  Essa funcionalidade é para testar se de acordo com as autorizações o usuário pode acessar apenas os itens permitidos
#
#  Cenário: Adiciona os usuários necessários para esse teste
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#    # Cenário falha porque usuário não consegue visualizar botão "Adicionar Elemento de Despesa de Mat. de Consumo"
#
##	Cenário: Adicionar Elementos de Despesa de Mat. de Consumo
##    Dado acesso a página "/"
##    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
##    E clico no botão "Adicionar Elemento de Despesa de Mat. de Consumo"
##    Quando preencho o formulário com os dados
##      | Campo                           | Tipo                | Valor         |
##      | Código                          | Texto               | 01            |
##      | Nome                            | Texto               | Teste         |
##    E clico no botão "Salvar"
##    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
#
#	Cenário: Pesquisar Balancete Elemento de Despesa Detalhado
#      Dado acesso a página "/"
#      Quando acesso a página "/almoxarifado/balancete_ed_detalhado/"
#      Então vejo os seguintes campos no formulário
#        | Campo                           | Tipo  				|
#        | Elemento de despesa             | Lista             	|
#        | Data inicial                    | Data  				|
#        | Data final                      | Data 				|
#      Quando clico no botão "Enviar"
#      Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
#      E vejo os seguintes erros no formulário
#        | Campo                           | Mensagem            		|
#        | Elemento de despesa             | Este campo é obrigatório	|
#        | Data inicial                    | Este campo é obrigatório	|
#        | Data final                      | Este campo é obrigatório    |
#
##  Cenário falha porque teste não consegue preencher o formulário
##
##	Cenário: Pesquisar Saída por Setor
##      Dado acesso a página "/"
##      Quando acesso a página "/almoxarifado/balancete_ed_detalhado/"
##      Então vejo a página "Balancete Elemento de Despesa Detalhado"
##      Quando preencho o formulário com os dados
##        | Campo						| Tipo    		      | Valor 				|
##        | Elemento de despesa  	    | Lista        		  | Teste	   		    |
##        | Data inicial  			| Data                | 01/05/2019			|
##        | Data final    			| Data                |	21/05/2019			|
##      E clico no botão "Enviar"
##      Então nao vejo mensagem de erro "Por favor, corrija os erros abaixo."
