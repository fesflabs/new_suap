# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Registros Administrativos
  Permite o cadastro dos registros administrativos

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  @do_document
  Cenário: Adicionar Registros Administrativos
  Cadastrar novos registros administrativos.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Registros Administrativos"
    E clico no botão "Adicionar Registro Administrativo"
    E preencho o formulário com os dados
      | Campo     | Tipo     | Valor                        |
      | Descrição | Textarea | Novo Registro Administrativo |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Registros Administrativos
  Editar registro administrativo existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Registros Administrativos"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo     | Valor                        |
      | Descrição | Textarea | Novo Registro Administrativo |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Visualizar Registros Administrativos
  Listar registros administrativos cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Registros Administrativos"
    Então vejo a página "Registros Administrativos"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário: Buscar Registros Administrativos
  Buscar registros administrativos
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Registros Administrativos"
    E olho para os filtros
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                        |
      | Texto | Texto | Novo Registro Administrativo |
    E clico no botão "Filtrar"
    Então vejo a linha "Novo Registro Administrativo"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

