# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Drogas
  Permite o cadastro de drogas que podem ser indicadas nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  @do_document
  Cenário: Adicionar Drogas
  Cadastrar nova droga.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Drogas"
    E clico no botão "Adicionar Droga"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor     |
      | Nome  | Texto | Droga ABC |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Drogas
  Editar droga existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Drogas"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor     |
      | Nome  | Texto | Droga ABC |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Drogas
  Listar drogas cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Drogas"
    Então vejo a página "Drogas"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"