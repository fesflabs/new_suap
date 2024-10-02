# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Cadastros::Elementos de Despesa de Mat. de Consumo
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "admin" e senha "abc"
#
#  @do_document
#  Cenario: Adicionar Elemento de Despesa de Mat. de Consumo
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#    E clico no botão "Adicionar Elemento de Despesa de Mat. de Consumo"
#    Quando preencho o formulário com os dados
#        | Campo         | Tipo         | Valor                      |
#        | Código        | Texto        | 3002                       |
#        | Nome          | Texto        | Teste Elemento             |
#        | Plano contas  | Autocomplete | ALMOXARIFADO               |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"
#
#  @do_document
#  Cenario: Visualizar Elemento de Despesa de Mat. de Consumo
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#    Então vejo mais de 0 resultados na tabela
#
#  @do_document
#  Cenario: Editar Elemento de Despesa de Mat. de Consumo
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#    Quando clico no ícone de edição
#    E preencho o formulário com os dados
#        | Campo         | Tipo         | Valor                              |
#        | Código        | Texto        | 30021                              |
#        | Nome          | Texto        | Novo Teste Elemento                |
#        | Plano contas  | Autocomplete | MATERIAIS DE CONSUMO               |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Atualização realizada com sucesso"
#
#  @do_document
#  Cenario: Apagar Elemento de Despesa de Mat. de Consumo
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
#    Quando clico no ícone de edição
#    E clico no link "Apagar"
#    Quando preencho o formulário com os dados
#        | Campo             | Tipo         | Valor       |
#        | Senha             | Texto        | abc         |
#    E clico no botão "Sim, remova"
#    Então vejo mensagem de sucesso "excluído com sucesso"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
