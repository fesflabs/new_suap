# -*- coding: utf-8 -*-
# language: pt
#
#Funcionalidade: Fluxo de edição do Processo Eletrônico
#
#  @do_document
#  Cenário: Editar Conteúdo do Processo Eletrônico
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128003" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
#    E olho para a listagem
#    E olho a linha "23001.000001.2019-68"
#    E clico no ícone de exibição
#    Então vejo a página "Processo 23001.000001.2019-68"
#    Quando clico no botão "Editar"
#    E clico no botão "Interessados"
#    Então vejo a página "Editar Interessados do Processo 23001.000001.2019-68"
#    Quando preencho o formulário com os dados
#      | Campo          | Tipo  | Valor               |
#      | Interessados   | autocomplete | Servidor A   |
#      | Justificativa  | textarea | Teste behave |
#      | Senha          | senha | abcd                |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    E vejo mensagem de sucesso "Os interessados do processo foram alterados com sucesso."
#    Quando clico no botão "Editar"
#    E clico no botão "Nível de Prioridade"
#    Então vejo a página "Nível de prioridade ao processo 23001.000001.2019-68"
#    Quando preencho o formulário com os dados
#      | Campo          | Tipo  | Valor        |
#      | Prioridade     | radio | Alta |
#      | Justificativa  | textarea | Teste behave |
#      | Senha          | senha | abcd                |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    E vejo mensagem de sucesso "O nível de prioridade foi atualizado com sucesso. "
#
#  Cenário: Sai do sistema
#    Quando acesso o menu "Sair"

#  @do_document
#  Cenário: Receber processo
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128003" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    Quando clico na aba "A Receber"
#    E clico no botão "Receber"
#    Entao vejo mensagem de sucesso "Processo recebido com sucesso"
#
#  Cenário: Sai do sistema
#    Quando acesso o menu "Sair"
#
#

