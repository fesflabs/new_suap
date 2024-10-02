# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Doenças
  Cadastro das doenças que podem ser indicadas nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  @do_document
  Cenário: Adicionar Doença
  Cadastrar novas doenças.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Doenças"
    E clico no botão "Adicionar Doença"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor      |
      | Nome  | Texto | Doença ABC |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Doença
  Editar doença existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Doenças"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor      |
      | Nome  | Texto | Doença ABC |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Doença
  Visualizar a lista de doenças existentes.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Doenças"
    Então vejo a página "Doenças"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"