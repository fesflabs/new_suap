# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Cadastros::Unidades de Medida
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "admin" e senha "abc"
#
#  @do_document
#  Cenario: Adicionar Unidade de Medida
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/unidademedida/"
#    E clico no botão "Adicionar Unidade de Medida"
#    Quando preencho o formulário com os dados
#        | Campo    | Tipo         | Valor                    |
#        | Nome     | Texto        | Teste Unidade de Medida  |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"
#
#  @do_document
#  Cenario: Visualizar Unidade de Medida
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/unidademedida/"
#    Então vejo mais de 0 resultados na tabela
#
#  @do_document
#  Cenario: Editar Unidade de Medida
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/unidademedida/"
#    Quando clico no link "Teste Unidade de Medida"
#    E preencho o formulário com os dados
#        | Campo       | Tipo         | Valor                    |
#        | Nome        | Texto        | Nova Unidade de Medida   |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Atualização realizada com sucesso"
#
#  @do_document
#  Cenario: Apagar Unidade de Medida
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/unidademedida/"
#    E clico no link "Nova Unidade de Medida"
#    E clico no link "Apagar"
#    Quando preencho o formulário com os dados
#        | Campo             | Tipo         | Valor       |
#        | Senha             | Texto        | abc         |
#    E clico no botão "Sim, remova"
#    Então vejo mensagem de sucesso "excluído com sucesso"
#
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"

