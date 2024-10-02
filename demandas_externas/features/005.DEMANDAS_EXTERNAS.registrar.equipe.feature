# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Indicar Responsável pela Execução da Demanda

      @do_document
      Cenário: Indicar Responsável pela Execução da Demanda
      É preciso indicar o servidor responsável pela realização da demanda. Os próprios servidores do campus de atendimento também podem assumir a demanda.
      Ação executada pelo Gerente de Demandas Externas ou Coordenador de Demandas Externas.
         Dado acesso a página "/"
         Quando realizo o login com o usuário "120003" e senha "abcd"
         E acesso o menu "Extensão::Demandas Externas::Demandas"
         Então vejo a página "Demandas Externas"
         Quando clico na aba "Em Atendimento"
         E olho a linha "Nome do Cidadão"
         E clico no ícone de exibição
         Então vejo a página "Visualizar Demanda"
         Quando clico na aba "Equipe"
         Então vejo o botão "Adicionar Membro"
         Quando clico no botão "Adicionar Membro"
         Então vejo a página "Adicionar Membro na Equipe"
         E vejo os seguintes campos no formulário
               | Campo                             | Tipo                        |
               | Participantes                     | Autocomplete Multiplo       |
             E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
               | Campo                             | Tipo                        | Valor    |
               | Participantes                     | Autocomplete Multiplo       | 120004   |
             E clico no botão "Enviar"
         Então vejo mensagem de sucesso "Membro da equipe cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
