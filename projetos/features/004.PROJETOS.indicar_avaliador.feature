# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Indicação de Avaliadores do Projeto de Extensão

      @do_document
      Cenário: Indicação de Avaliadores do Projeto
      Dentre todos os avaliadores cadastrados na comissão de avaliação do edital, é necessário, para cada projeto pré-selecionado, indicar quais irão avaliar cada projeto.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"

        Quando realizo o login com o usuário "110001" e senha "abcd"
             E a data do sistema for "16/01/2018"
             E acesso o menu "Extensão::Projetos::Indicar Avaliador"
         Então vejo a página "Editais em Avaliação"
         Quando olho a linha "Nome do edital"
         E clico no ícone de exibição
         Então vejo a página "Selecionar Avaliadores dos Projetos do Nome do edital"
        Quando olho a linha "Título do projeto"
         Então vejo o botão "Selecionar Avaliadores"
        Quando clico no botão "Selecionar Avaliadores"
            E olho para o popup
            Então vejo a página "Indicar Avaliadores do Projeto Título do projeto"
        Quando seleciono o item "Avaliador Extensão A" da lista
             E seleciono o item "Avaliador Extensão B" da lista

           E clico no botão "Enviar"
           Então vejo mensagem de sucesso "Avaliadores cadastrados com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
