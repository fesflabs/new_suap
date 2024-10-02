# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Avaliações do Projeto de Pesquisa


      @do_document
      Cenário: Primeira Avaliação do Projeto
      O avaliador indicado realiza a avaliação do projeto.
      Ação executada pelo Avaliador do Projeto (servidor ou avaliador externo à instituição).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108005" e senha "abcd"
             E a data do sistema for "16/01/2018"
             E acesso o menu "Pesquisa::Avaliações::Avaliar Projetos"
         Então vejo a página "Editais em Avaliação"
         Quando olho a linha "Nome do edital"
         E clico no link "Nome do edital"
         Então vejo a página "Seleção de Projetos"
        Quando olho a linha "Título do projeto"
         Então vejo o botão "Avaliar"
        Quando clico no botão "Avaliar"
        Então vejo o botão "Avaliar Projeto"
        Quando clico no botão "Avaliar Projeto"
        Então vejo a página "Avaliar Projeto - Título do projeto"
        Quando preencho o formulário com os dados
               | Campo                               | Tipo                 | Valor                  |
               | Parecer                             | TextArea             | Parecer do avaliador 1 |

           E clico no botão "Enviar"
           Então vejo mensagem de sucesso "Projeto avaliado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Segunda Avaliação do Projeto
      O avaliador indicado realiza a avaliação do projeto.
      Ação executada pelo Avaliador do Projeto (servidor ou avaliador externo à instituição).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108006" e senha "abcd"
             E a data do sistema for "16/01/2018"
             E acesso o menu "Pesquisa::Avaliações::Avaliar Projetos"
         Então vejo a página "Editais em Avaliação"
         Quando olho a linha "Nome do edital"
         E clico no link "Nome do edital"
         Então vejo a página "Seleção de Projetos"
        Quando olho a linha "Título do projeto"
         Então vejo o botão "Avaliar"
        Quando clico no botão "Avaliar"
        Então vejo o botão "Avaliar Projeto"
        Quando clico no botão "Avaliar Projeto"
        Então vejo a página "Avaliar Projeto - Título do projeto"
        Quando preencho o formulário com os dados
               | Campo                               | Tipo                 | Valor                  |
               | Parecer                             | TextArea             | Parecer do avaliador 2 |

           E clico no botão "Enviar"
           Então vejo mensagem de sucesso "Projeto avaliado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
