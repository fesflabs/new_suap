# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Diagnóstico Nutricional
  Permite o cadastro de diagnósticos nutricionais que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Diagnósticos Nutricionais
  Cadastrar diagnósticos nuticionais.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Diagnóstico Nutricional"
    E clico no botão "Adicionar Diagnóstico Nutricional"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                        |
      | Descrição | Texto | Novo Diagnóstico Nutricional |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Diagnósticos Nutricionais
  Editar diagnóstico nuticional existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Diagnóstico Nutricional"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                        |
      | Descrição | Texto | Novo Diagnóstico Nutricional |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Diagnósticos Nutricionais
  Listar diagnósticos nuticionais cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Diagnóstico Nutricional"
    Então vejo a página "Diagnósticos Nutricionais"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário: Buscar Diagnósticos Nutricionais
  Buscar diagnósticos nutricionais cadastrados.
    Dado  acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Diagnóstico Nutricional"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                        |
      | Texto | Texto | Novo Diagnóstico Nutricional |
    E clico no botão "Filtrar"
    Então vejo a linha "Novo Diagnóstico Nutricional"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

