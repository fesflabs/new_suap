# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades ligadas ao cadastro de tipo de rsc

      Cenário: Adicionando os usuários necessários para os testes
          Dado os seguintes usuários
               | Nome           | Matrícula      | Setor | Lotação | Email             | CPF            | Senha | Grupo           |
               | Membro         | 7777100        | A0    | A0      | pla01@ifrn.edu.br | 667.473.410-15 | abcd  | Membro CPPD     |
               | Presidente     | 8888100        | A0    | A0      | pla02@ifrn.edu.br | 645.433.195-40 | abcd  | Presidente CPPD |

      @do_document
      Cenário: Criar um Tipo de RSC
          Dado acesso a página "/"
        Quando realizo o login com o usuário "7777100" e senha "abcd"
             E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Docentes::RSC::Cadastros::Tipos de RSC"
         Então vejo a página "Tipos de Rsc"
             E vejo o botão "Adicionar Tipo de Rsc"
        Quando clico no botão "Adicionar Tipo de Rsc"
         Então vejo a página "Adicionar Tipo de Rsc"
             E vejo os seguintes campos no formulário
               | Campo           | Tipo  |
               | Nome            | Texto |
               | Categoria       | Texto |
             E vejo o botão "Salvar"
        Quando clico no botão "Salvar"
         Então vejo os seguintes erros no formulário
               | Campo              | Tipo  | Mensagem           |
               | Nome               | Texto | Este campo é obrigatório  |
               | Categoria          | Texto | Este campo é obrigatório |
        Quando preencho o formulário com os dados
               | Campo              | Tipo  | Valor  |
               | Nome               | Texto |  Prova |
               | Categoria          | Texto |  Prova |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
