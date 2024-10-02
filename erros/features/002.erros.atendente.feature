# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades ligadas ao módulo de Erros
  Essa funcionalidade demonstra o fluxo de erros do ponto de vista do atendente e do interessado.

  @do_document
  Cenário: Um atendente altera a situação de um erro
    Dado acesso a página "/"
    Quando realizo o login com o usuário "103011" e senha "abcd"
    E acesso a página "/erros/erro/1/"
    Então vejo o botão "Assumir"
    Quando clico no botão "Assumir"
    Então vejo mensagem de sucesso "Você agora é o Atendente Principal deste erro."
    E vejo o status "Em análise" acima do título
    E vejo o botão "Devolver"
    Quando clico no botão "Editar Situação"
    E clico no botão "Em correção"
    Então vejo mensagem de sucesso "Situação alterada com sucesso."
    E vejo o status "Em correção" acima do título

  @do_document
  Cenário: Um atendente edita a URL do erro
    Quando clico no botão "Opções"
    E clico no botão "Editar URL do Erro"
    E olho para o popup
    Então vejo a página "Alterar URL do Erro 1"
    Quando preencho o formulário com os dados
      | Campo            | Tipo  | Valor                  |
      | Nova URL do Erro | Texto | http://localhost:8000/ |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "URL do erro alterada com sucesso."
