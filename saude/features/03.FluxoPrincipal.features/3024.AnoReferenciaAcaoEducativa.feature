# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Ano de Referência
  Permite o cadastro de anos de referências que podem ser indicados nos registros de ações educativas

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Anos de Referências
  Cadastrar novos anos de referências.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Ano de Referência"
    E clico no botão "Adicionar Ano de Referência"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor |
      | Ano   | Texto | 2030  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Anos de Referências
  Editar ano de referência existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Ano de Referência"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor |
      | Ano   | Texto | 2030  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Anos de Referências
  Listar anos de referências cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Ano de Referência"
    Então vejo a página "Anos de Referências"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

