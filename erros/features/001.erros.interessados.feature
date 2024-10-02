# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades ligadas ao módulo de Erros
  Essa funcionalidade demonstra o fluxo de erros do ponto de vista do atendente e do interessado.


  Cenário: Adicionando os usuários necessários para os testes central de serviços
    Dado os cadastros de usuários do módulo de erros

  @do_document
  Cenário: Um usuário cadastra um erro em uma página existente
    Dado acesso a página "/"
    Quando realizo o login com o usuário "103013" e senha "abcd"
    E olho para a página
    E clico no link "Reportar Erro"
    Então vejo a página "Reportar Erro no SUAP"
    Quando preencho o formulário com os dados
      | Campo                                                                                                                | Tipo        | Valor                                     |
      | Descreva a operação que você estava realizando antes de ocorrer o erro e a mensagem de erro que o sistema apresentou | Textarea    | O quadro de erros não está sendo exibido. |
    E clico no botão "Enviar"
    Então vejo a página "Erro 1: Comum"

  @do_document
  Cenário: Um usuário lista os erros
    Dado acesso a página "/"
    Quando acesso o menu "Tec. da Informação::Desenvolvimento::Erros"
    Então vejo a página "Erros"
    Quando olho para a página
    E olho para o quadro "Escolher Área"
    E clico no link "Comum" na listagem das áreas
    Então vejo a página "Área Comum"
    Quando olho para o quadro "Escolher Módulo"
    E clico no link "Comum" na listagem das áreas
    Então vejo a página "Erros"
    Quando olho para a aba "Reportados"
    E clico no link "Erro 1"
    Então vejo a página "Erro 1: Comum"

  @do_document
  Cenário: Um usuário interessado comenta e desconsidera o comentário no Erro
    Dado acesso a página "/erros/erro/1"
    Quando olho para a textarea "Adicionar Interação" e preencho com "Erro ao tentar acessar a página inicial do suap"
    E clico no botão "Adicionar Interação"
    Então vejo mensagem de sucesso "Comentário cadastrado com sucesso."
    E vejo mensagem na timeline "Erro ao tentar acessar a página inicial do suap"
    Quando clico no ícone de configuração
    E clico no botão "Desconsiderar Comentário"
    Então vejo mensagem de sucesso "Comentário desconsiderado com sucesso."

  @do_document
  Cenário: Um usuário interessado adiciona um anexo ao Erro
    Quando olho para a página
    E clico na aba "Anexos"
    Então vejo mensagem de alerta "Nenhum anexo cadastrado."
    Quando clico no botão "Adicionar Anexo"
    E olho para o popup
    Então vejo a página "Adicionar Anexo ao Erro 1"
    Quando preencho o formulário com os dados
      | Campo     | Tipo    | Valor                       |
      | Descrição | Texto   | Problema no quadro de Erros |
      | Arquivo   | Arquivo | arquivo.jpg                 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Anexo adicionado com sucesso."
    Quando olho para a aba "Anexos"
    E olho para a tabela
    Então vejo a linha "Problema no quadro de Erros"
