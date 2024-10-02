# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Vacinas
  Cadastro da lista de vacinas podem ser indicadas nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  @do_document
  Cenário: Adicionar Vacinas
  Cadastrar novas vacinas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Vacinas"
    E clico no botão "Adicionar Vacina"
    Quando preencho o formulário com os dados
      | Campo           | Tipo  | Valor      |
      | Nome            | Texto | Vacina ABC |
      | Número de Doses | Texto | 2          |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Vacinas
  Editar vascinas existentes.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Vacinas"
    Quando clico no ícone de edição
    E preencho o formulário com os dados
      | Campo           | Tipo  | Valor      |
      | Nome            | Texto | Vacina ABC |
      | Número de Doses | Texto | 2          |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Visualizar Vacinas
  Listar vascinas já cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Vacinas"
    Então vejo a página "Vacinas"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"