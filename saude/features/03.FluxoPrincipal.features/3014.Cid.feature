# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de CID
  Permite o cadastro dos CID's que podem ser indicados nos registros de atendimentos de saúde

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar CID
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::CID"
    E clico no botão "Adicionar Doença"
    E preencho o formulário com os dados
      | Campo       | Tipo  | Valor                            |
      | Código      | Texto | ABC123                           |
      | Denominação | Texto | Nova Denominação de Procedimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar CID
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::CID"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo       | Tipo  | Valor                            |
      | Código      | Texto | ABC123                           |
      | Denominação | Texto | Nova Denominação de Procedimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar CID
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::CID"
    Então vejo a página "Doenças"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"