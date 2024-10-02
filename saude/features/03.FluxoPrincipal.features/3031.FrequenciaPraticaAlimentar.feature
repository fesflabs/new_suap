# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Alimento/Bebida para Frequência de Prática Alimentar
  Permite o cadastro de alimentos/bebidas e frequência que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Frequência de Prática Alimentar
  Cadastrar frequência de práticas alimentares.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Alimento/Bebida para Frequência de Prática Alimentar"
    E clico no botão "Adicionar Alimento/Bebida para Frequência de Prática Alimentar"
    E preencho o formulário com os dados
      | Campo             | Tipo  | Valor       |
      | Descrição         | Texto | Nome Comida |
      | Valor Recomendado | Texto | 3           |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Frequência de Prática Alimentar
  Editar frequência de prática alimentar.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Alimento/Bebida para Frequência de Prática Alimentar"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo             | Tipo  | Valor       |
      | Descrição         | Texto | Nome Comida |
      | Valor Recomendado | Texto | 3           |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Frequência de Prática Alimentar
  Listar frequência de práticas alimentares.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Alimento/Bebida para Frequência de Prática Alimentar"
    Então vejo a página "Alimentos/Bebidas para Frequência de Prática Alimentar"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

