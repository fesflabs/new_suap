# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Plano de Contas
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "ContadorAdministra" e senha "abcd"
#
#  @do_document
#  Cenario: Adicionar Plano de Contas
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
#    E clico no botão "Adicionar Plano de Contas"
#    E preencho o formulário com os dados
#        | Campo          | Tipo     | Valor           |
#        | Código         | Texto    | 3014            |
#        | Descrição      | Texto    | Plano de Contas |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"
#
#  @do_document
#  Cenario: Visualizar Plano de Contas
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/planocontasalmox/"
#    Então vejo mais de 0 resultados na tabela
#
#  @do_document
#  Cenario: Editar Plano de Contas
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/planocontasalmox/"
#    Quando clico no ícone de edição
#    E preencho o formulário com os dados
#        | Campo          | Tipo     | Valor                |
#        | Código         | Texto    | Novo3014             |
#        | Descrição      | Texto    | Novo Plano de Contas |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Atualização realizada com sucesso"
#
#  @do_document
#  Cenario: Apagar Plano de Contas
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
#    E olho a linha "Novo Plano de Contas"
#    E clico no ícone de edição
#    E clico no link "Apagar"
#    Quando preencho o formulário com os dados
#        | Campo             | Tipo         | Valor       |
#        | Senha             | Texto        | abcd        |
#    E clico no botão "Sim, remova"
#    Então vejo mensagem de sucesso "excluído com sucesso"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
