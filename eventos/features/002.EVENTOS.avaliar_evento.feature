# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Avaliação do Evento
      @do_document
      Cenário: Avaliar Evento
      Ação executada por membros dos grupos de avaliadores locais das dimensões ou dos grupos de avaliadores sistêmicos.
          Dado acesso a página "/"
        Quando a data do sistema for "01/01/2020"
             E realizo o login com o usuário "155002" e senha "abcd"
             E acesso o menu "Comunicação Social::Eventos"
         Então vejo a página "Eventos"
        Quando clico na aba "Aguardando Minha Aprovação"
         E olho a linha "Nome do Evento"
		 E clico no ícone de exibição
         Então vejo a página "Nome do Evento"
             E vejo o botão "Avaliar"
        Quando clico no botão "Avaliar"
         Então vejo o botão "Deferir"
        Quando clico no botão "Deferir"
         Então vejo mensagem de sucesso "O evento foi deferido."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
