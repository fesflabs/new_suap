# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro dos Motivos da Chegada
  Permite o cadastro de motivos de chegada que podem ser indicados nos registros de atendimentos de psicologia

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Motivos da Chegada
  Cadastrando novo motivo da chegada ao setor de psicologia.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Psicologia::Motivo da Chegada"
    E clico no botão "Adicionar Motivo da Chegada"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor               |
      | Descrição | Texto | Novo Motivo Chegada |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Motivos da Chegada
  Editar motivo da chegada ao setor de psicologia.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Psicologia::Motivo da Chegada"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor               |
      | Descrição | Texto | Novo Motivo Chegada |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Motivos da Chegada
  Listar motivos da chegada ao setor de psicologia.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Psicologia::Motivo da Chegada"
    Então vejo a página "Motivos da Chegada"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"