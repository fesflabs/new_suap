# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Distribuição das Bolsas Entre os Projetos de Pesquisa

      @do_document
      Cenário: Distribuição das Bolsas
      Permite definir quais projetos serão aprovados a partir da distribuição de bolsas previstas no edital. A funcionalidade gerá uma distribuição automática
      que poderá ser confirmada ou alterada pelo responsável pela distribuição.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108001" e senha "abcd"
             E a data do sistema for "18/01/2018"
             E acesso o menu "Pesquisa::Editais::Distribuir Bolsas"
         Então vejo a página "Distribuição de Bolsas dos Projetos de Pesquisa"
         Quando olho a linha "Nome do edital"
         E clico no link "CZN"
         Então vejo a página "Gerenciamento de Bolsas dos Projetos de Pesquisa"
           E vejo o botão "Salvar"
         Quando clico no botão "Salvar"
         Então vejo mensagem de sucesso "Bolsas salvas com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


