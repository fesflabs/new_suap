# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Saídas
    Registrar Saída

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do Almoxarifado
    Quando acesso a página "/"
    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"

  @do_document
  Cenario: Visualizar Requisição de Saída de Material para Consumo
    Dado acesso a página "/"
    Quando acesso a página "/almoxarifado/form_requisicao_usuario_pedido"
    Dado o cadastro de requisicao
    Então vejo a página "Requisição de Saída de Material para Consumo"

  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"
