# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades ligadas ao cadastro de grupo de indicadores

      Cenário: Adicionando os usuários necessários para os testes
          Dado os seguintes usuários
               | Nome           | Matrícula      | Setor | Lotação | Email             | CPF            | Senha | Grupo           |
               | Membro         | Membro         | A0    | A0      | pla01@ifrn.edu.br | 645.433.195-40 | abcd  | Membro CPPD     |
               | Presidente     | Presidente     | A0    | A0      | pla01@ifrn.edu.br | 645.433.195-40 | abcd  | Presidente CPPD |

      @do_document
      Cenário: Criar grupo de indicadores
          Dado acesso a página "/"
        Quando realizo o login com o usuário "Membro" e senha "abcd"
             E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Docentes::Professor Titular::Cadastros::Grupos de Indicadores"
         Então vejo a página "Grupos de indicadores"
             E vejo o botão "Adicionar Grupo de indicadores"
        Quando clico no botão "Adicionar Grupo de indicadores"
         Então vejo a página "Adicionar Grupo de indicadores"

        Quando preencho o formulário com os dados
               | Campo                 | Tipo          | Valor  |
               | Nome                  | Texto         |  B     |
               | Percentual            | Texto         |  10    |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
