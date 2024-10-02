# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Entradas
    Cadastro de Entrada Compra e Doação

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do Almoxarifado
    Quando acesso a página "/"
    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"

  @do_document
  Cenario: Efetuar Entrada de Compra
    Dado acesso a página "/"
    Quando pesquiso por "Entradas" e acesso o menu "Administração::Almoxarifado::Entradas"
    E clico no botão "Efetuar Entrada de Compra"
    Dado o cadastro de entrada de compra

  @do_document
  Cenario: Efetuar Entrada de Doação
    Dado acesso a página "/"
    Quando pesquiso por "Entradas" e acesso o menu "Administração::Almoxarifado::Entradas"
    E clico no botão "Efetuar Entrada de Doação"
    Dado o cadastro de entrada de doacao

  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"
