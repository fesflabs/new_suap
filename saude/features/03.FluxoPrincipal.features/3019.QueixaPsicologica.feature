# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Queixas
  Permite o cadastro de queixas que podem ser indicados nos registros de atendimentos de psicologia

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Queixas
  Cadastrar novas queixas psicológicas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Psicologia::Queixa"
    E clico no botão "Adicionar Queixa"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor       |
      | Descrição | Texto | Nova Queixa |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Queixas
  Editar queixa psicológica existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Psicologia::Queixa"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor       |
      | Descrição | Texto | Nova Queixa |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Queixas
  Listar queixas psicológicas cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Psicologia::Queixa"
    Então vejo a página "Queixas"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela



  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

