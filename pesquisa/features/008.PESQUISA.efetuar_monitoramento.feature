# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Monitoramento do Projeto de Pesquisa

      @do_document
      Cenário: Validação das Atividades
      Cada registro de execução de atividade deve ser validado pelo supervisor do projeto. Por padrão, o supervisor do projeto
      será o coordenador de pesquisa que fez a pré-seleção. O supervisor do projeto poderá ser alterado no menu Pesquisa -> Projeto -> Gerenciar Supervisores.
      Ação executada pelo Supervisor do Projeto (servidor).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108002" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Monitoramento"
         Então vejo a página "Monitoramento"
         Quando olho a linha "Título do projeto"
             Então vejo o botão "Acompanhar Validação"
         Quando clico no botão "Acompanhar Validação"
            Então vejo a página "Validar Execução"
         Quando clico na aba "Metas"
            E olho a linha "Descrição da Atividade 1"
            Então vejo o botão "Aprovar"
         Quando clico no botão "Aprovar"
            Então vejo mensagem de sucesso "Execução de atividade validada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Validação dos Gastos
      Cada registro de gasto deve ser validado pelo supervisor do projeto. Por padrão, o supervisor do projeto
      será o coordenador de pesquisa que fez a pré-seleção. O supervisor do projeto poderá ser alterado no menu Pesquisa -> Projeto -> Gerenciar Supervisores.
      Ação executada pelo Supervisor do Projeto (servidor).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108002" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Monitoramento"
         Então vejo a página "Monitoramento"
         Quando olho a linha "Título do projeto"
             Então vejo o botão "Acompanhar Validação"
         Quando clico no botão "Acompanhar Validação"
            Então vejo a página "Validar Execução"
         Quando clico na aba "Gastos"
            E olho a linha "Obs sobre o registro do gasto"
            Então vejo o botão "Aprovar"
         Quando clico no botão "Aprovar"
            Então vejo mensagem de sucesso "Gasto validado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"












