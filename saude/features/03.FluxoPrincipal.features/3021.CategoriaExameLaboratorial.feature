# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Categorias de Exames Laboratoriais
  Permite o cadastro de categorias de exames que podem ser indicados nos registros de exames laboratoriais

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Categorias de Exames Laboratoriais
  Cadastrar novas categorias de exames laboratoriais.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Categorias de Exame Laboratorial"
    E clico no botão "Adicionar Categoria de Exame Laboratorial"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                                |
      | Nome  | Texto | Nova Categoria de Exame Laboratorial |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Categorias de Exames Laboratoriais
  Editar categoria de exame laboratorial existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Categorias de Exame Laboratorial"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                                |
      | Nome  | Texto | Nova Categoria de Exame Laboratorial |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Categorias de Exames Laboratoriais
  Listar categorias de exames laboratoriais existentes.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Categorias de Exame Laboratorial"
    Então vejo a página "Categorias de Exames Laboratoriais"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

