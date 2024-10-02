# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Procedimentos de Enfermagem
  Permite o cadastro de procedimentos de enfermagem que podem ser indicados nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Procedimentos de Enfermagem
  Cadastrar novos procedimentos de enfermagem.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos de Enfermagem"
    E clico no botão "Adicionar Procedimento de Enfermagem"
    E preencho o formulário com os dados
      | Campo       | Tipo  | Valor                            |
      | Denominação | Texto | Nova Denominação de Procedimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Procedimentos de Enfermagem
  Editar procedimento de enfermagem existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos de Enfermagem"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo       | Tipo  | Valor                            |
      | Denominação | Texto | Nova Denominação de Procedimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Procedimentos de Enfermagem
  Listar procedimentos de enfermagem cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos de Enfermagem"
    Então vejo a página "Procedimentos de Enfermagem"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"