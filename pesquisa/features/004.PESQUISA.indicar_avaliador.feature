# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Indicação de Avaliadores do Projeto de Pesquisa

        @do_document
        Cenário: Indicação de Avaliadores do Projeto
        Dentre todos os avaliadores cadastrados na comissão de avaliação do edital, é necessário, para cada projeto pré-selecionado, indicar quais irão avaliar cada projeto.
        Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"

        Quando realizo o login com o usuário "108001" e senha "abcd"
             E a data do sistema for "16/01/2018"
             E acesso o menu "Pesquisa::Avaliações::Indicar Avaliador por Projeto"
         Então vejo a página "Editais em Avaliação"
         Quando olho a linha "Nome do edital"
         E clico no ícone de exibição
         Então vejo a página "Selecionar Avaliadores dos Projetos do Nome do edital"
         Quando clico no botão "Enviar"
         E olho a linha "Título do projeto"
         Então vejo o botão "Selecionar Avaliadores"
        Quando clico no botão "Selecionar Avaliadores"

            Então vejo a página "Indicar Avaliadores do Projeto Título do projeto"
        Quando clico no botão "Enviar"
        E seleciono o item "Avaliador1 Pesquisa" da lista
             E seleciono o item "Avaliador2 Pesquisa" da lista
           E clico no botão "Salvar"
           Então vejo mensagem de sucesso "Avaliadores cadastrados com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


