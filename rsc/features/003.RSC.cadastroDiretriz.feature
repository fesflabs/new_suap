# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades ligadas ao cadastro de diretriz

      Cenário: Adicionando os usuários necessários para os testes
        Dado os dados básicos para RSC
          E os seguintes usuários
                | Nome           | Matrícula      | Setor | Lotação | Email             | CPF            | Senha | Grupo           |
                | Membro         | 7777100        | A0    | A0      | pla01@ifrn.edu.br | 667.473.410-15 | abcd  | Membro CPPD     |
                | Presidente     | 8888100        | A0    | A0      | pla02@ifrn.edu.br | 645.433.195-40 | abcd  | Presidente CPPD |


      @do_document
      Cenário: Criar uma Diretriz
          Dado acesso a página "/"
        Quando realizo o login com o usuário "7777100" e senha "abcd"
             E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Docentes::RSC::Cadastros::Diretrizes"
         Então vejo a página "Diretrizes"
             E vejo o botão "Adicionar Diretriz"
        Quando clico no botão "Adicionar Diretriz"
         Então vejo a página "Adicionar Diretriz"

        Quando preencho o formulário com os dados
               | Campo                | Tipo          | Valor              |
               | Tipo rsc             | Autocomplete  |  RSC     |
               | Nome                 | Texto         |  Diretriz qualquer |
               | Descricao            | Textarea      |  Prova             |
               | Valor do peso        | Texto         |  2                 |
               | Teto                 | Texto         |  10                |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."




      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
