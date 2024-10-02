# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Procedimentos de Odontologia
  Permite o cadastro de procedimentos de odontologia que podem ser indicados nos registros de atendimentos odontológicos

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Visualizar Procedimentos de Odontologia
  Visualizar detalhes de procedimento odontológico existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos Odontológicos"
    Então vejo a página "Procedimentos de Odontologia"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário: Editar Procedimentos de Odontologia
  Editar procedimento odontológico existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos Odontológicos"
    E clico no ícone de edição
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"