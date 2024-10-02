# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Tipo de Exame Laboratorial
  Permite o cadastro de tipos de exames que podem ser indicados nos registros de exames laboratoriais

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E as seguintes categorias de exames
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Tipos de Exames Laboratoriais
  Cadastrar tipos de exames laboratoriais.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Tipo de Exame Laboratorial"
    E clico no botão "Adicionar Tipo de Exame Laboratorial"
    E preencho o formulário com os dados
      | Campo                 | Tipo         | Valor                                        |
      | Categoria             | Autocomplete | Perfil Glicêmico                             |
      | Nome                  | Texto        | Nova Tipo de Exame Laboratorial              |
      | Unidade de Medida     | Texto        | Nova Unidade de Medida de Exame Laboratorial |
      | Valores de Referência | Texto Rico   | Valores de Referência                        |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Tipos de Exames Laboratoriais
  Editar tipo de exame laboratorial existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Tipo de Exame Laboratorial"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor                                        |
      | Categoria         | Autocomplete | Perfil Glicêmico                             |
      | Nome              | Texto        | Nova Tipo de Exame Laboratorial              |
      | Unidade de Medida | Texto        | Nova Unidade de Medida de Exame Laboratorial |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Tipos de Exames Laboratoriais
  Listar tipos de exames laboratoriais cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Tipo de Exame Laboratorial"
    Então vejo a página "Tipos de Exames Laboratoriais"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

