## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Relatórios::Saídas por Setor
#  Essa funcionalidade é para testar se de acordo com as autorizações o usuário pode acessar apenas os itens permitidos
#
#  Cenário: Adiciona os usuários necessários para esse teste
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#	Cenário: Pesquisar Saída por Setor
#		Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/relatorio/consumo_setor/"
#    Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo                |
#      | Data inicial                    | Data                |
#      | Data final                      | Data                |
#      | Opcao exibir                    | Checkbox Multiplo   |
#    Quando clico no botão "Enviar"
#		Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
#    E vejo os seguintes erros no formulário
#      | Campo                           | Mensagem            			|
#      | Data inicial                    | Este campo é obrigatório	|
#      | Data final                      | Este campo é obrigatório  |
#			| Opcao exibir                    | Este campo é obrigatório	|
#
#	Cenário: Pesquisar Saída por Setor
# 		Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/relatorio/consumo_setor/"
#		E preencho o formulário com os dados
#      | Campo					| Tipo    						| Valor 					|
#      | Data inicial  | Data                | 01/05/2019			|	
#      | Data final    | Data                |	21/05/2019			|
#			| Opcao exibir  | Checkbox Multiplo   |	Todas as Saídas	|
#    E clico no botão "Enviar"
#		Então nao vejo mensagem de erro "Por favor, corrija os erros abaixo."
#
#	# Aparece uma mensagem de erro informando que um email será enviado
