## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Relatórios::Materiais Transferidos
#  Essa funcionalidade é para testar se de acordo com as autorizações o usuário pode acessar apenas os itens permitidos
#
#  Cenário: Adiciona os usuários necessários para esse teste
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#	Cenário: Pesquisar Materiais Transferidos
#		Dado acesso a página "/"
#		Quando acesso a página "/almoxarifado/materiais_transferidos/"
#    Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo  				|
#      | Solicitante                     | Autocomplete 	|
#      | Data inicial                    | Data  				|
#      | Data final                      | Data 					|
#    Quando clico no botão "Enviar"
#		Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
#    E vejo os seguintes erros no formulário
#      | Campo                           | Mensagem            			|
#			| Solicitante                     | Este campo é obrigatório	|
#      | Data inicial                    | Este campo é obrigatório	|
#      | Data final                      | Este campo é obrigatório  |
#
#	Cenário: Pesquisar Saída por Setor
# 		Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/materiais_transferidos/"
#		E preencho o formulário com os dados
#      | Campo					| Tipo    						| Valor 					|
#      | Solicitante   | Autocomplete				|	01							|
#      | Data inicial  | Data                | 01/05/2019			|	
#      | Data final    | Data                |	21/05/2019			|
#    E clico no botão "Enviar"
#		Então nao vejo mensagem de erro "Por favor, corrija os erros abaixo."
