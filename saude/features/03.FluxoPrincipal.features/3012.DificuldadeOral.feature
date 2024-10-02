# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Dificuldades Orais
  Permite o cadastro de dificuldades orais que podem ser indicados nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  @do_document
  Cenário: Adicionar Dificuldades Orais
  Cadastrar novas dificuldades orais.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Dificuldades Orais"
    E clico no botão "Adicionar Dificuldade Oral"
    E preencho o formulário com os dados
      | Campo            | Tipo  | Valor                  |
      | Dificuldade Oral | Texto | Nova Dificuldade Orais |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Dificuldades Orais
  Editar dificuldade oral existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Dificuldades Orais"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo            | Tipo  | Valor                  |
      | Dificuldade Oral | Texto | Nova Dificuldade Orais |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Dificuldades Orais
  Listar dificuldades orais cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Dificuldades Orais"
    Então vejo a página "Dificuldades Orais"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"