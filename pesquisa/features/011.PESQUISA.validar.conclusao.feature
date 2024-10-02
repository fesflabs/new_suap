# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Validação da Conclusão do Projeto de Pesquisa

      @do_document
      Cenário: Validar Conclusão
      O registro da conclusão do projeto precisa ser validado pelo supervisor do mesmo.
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
        Quando clico na aba "Conclusão do Projeto"
            Então vejo o botão "Emitir parecer"
        Quando clico no botão "Emitir parecer"
            E olho para o popup
            Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Aprovado                                                   | checkbox |
               | Observação                                                 | TextArea |
            E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                       |
               | Aprovado                                                   | checkbox | marcar                      |
               | Observação                                                 | TextArea | Obs sobre a finalização     |


             E clico no botão "Enviar"

         Então vejo mensagem de sucesso "Conclusão do projeto registrada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
