# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Finalização do Projeto de Pesquisa

      @do_document
      Cenário: Finalizar o Projeto
      Caso o projeto não possua mais pendências, o mesmo pode ser finalizado pelo coordenador do projeto.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
        Quando clico na aba "Conclusão"
         Então vejo o botão "Finalizar Conclusão"
         Quando clico no botão "Finalizar Conclusão"
             Então vejo mensagem de sucesso "Conclusão finalizada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"