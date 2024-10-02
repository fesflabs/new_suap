# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Métodos Contraceptivos
  Permite o cadastro de métodos contraceptivos que podem ser indicados nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Métodos Contraceptivos
  Cadastrar de novo método contraceptivo.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Métodos Contraceptivos"
    E clico no botão "Adicionar Método Contraceptivo"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                     |
      | Nome  | Texto | Novo Método Contraceptivo |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Métodos Contraceptivos
  Editar método contraceptivo existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Métodos Contraceptivos"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                     |
      | Nome  | Texto | Novo Método Contraceptivo |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Métodos Contraceptivos
  Listar métodos contraceptivos cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Métodos Contraceptivos"
    Então vejo a página "Métodos Contraceptivos"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"