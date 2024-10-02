# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Operações em demandas em negociação
    Essa funcionalidade verifica as funcionalidades da demanda no Status "Em negociação". No final
    desse teste a demanda passará do estado "Em negociação" para "Aprovada"

  @do_document
  Cenário: Verifica se o Demandante consegue visualizar as informações da demanda
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Demanda 1"
    E vejo o status "Em negociação"
    Quando acesso o menu "Sair"

  Esquema do Cenário: Verifica se o <Papel> consegue visualizar as informações da demanda
    Dado acesso a página "/"
    Quando realizo o login com o usuário "<Papel>" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Demanda 1"
    E vejo o status "Em negociação"
    E vejo a aba "Consolidação"
    Quando acesso o menu "Sair"

    Exemplos:
      | Papel  |
      | 105003 |
      | 105002 |

  @do_document
  Cenário: O analista realiza o cadastro de uma consolidação para a demanda
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    E clico no ícone de exibição
    E clico na aba "Consolidação"
    E clico no botão "Adicionar Especificação"
    Então vejo a página "Adicionar Especificação"
    Quando preencho o formulário com os dados
      | Campo        | Tipo       | Valor                |
      | Nome         | Texto      | Especificação 1      |
      | Atividade(s) | Texto Rico | Esta é uma atividade |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "A especificação foi adicionada."
    Quando clico no botão "Alterar Etapa"
    E clico no link "Analisar"
    Então vejo mensagem de erro "Não é possível alterar uma demanda para Em Análise caso ela não tenha Consolidação"
    Quando clico na aba "Consolidação"
    E olho para a aba "Consolidação"
    E clico no botão "Editar"
    Então vejo os seguintes campos no formulário
      | Campo                         | Tipo     |
      | Descrição                     | Texto    |
      | Grupos de Usuários Envolvidos | TextArea |
    E vejo o botão "Salvar"
    Quando clico no botão "Salvar"
    Então vejo os seguintes erros no formulário
      | Campo                         | Tipo     | Mensagem                 |
      | Descrição                     | Texto    | Este campo é obrigatório |
      | Grupos de Usuários Envolvidos | TextArea | Este campo é obrigatório |
    Quando preencho o formulário com os dados
      | Campo                         | Tipo     | Valor                     |
      | Descrição                     | Texto    | Consolidação da Demanda 1 |
      | Grupos de Usuários Envolvidos | TextArea | Grupos Envolvidos         |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "A demanda foi atualizada."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Verifica a visibilidade do demandante
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Consolidação da Demanda 1"
    E vejo o status "Em negociação"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Atualiza o status da demanda
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Consolidação da Demanda 1"
    E vejo o status "Em negociação"
    E vejo a aba "Consolidação"
    Quando clico na aba "Consolidação"
    E clico no botão "Alterar Etapa"
    E clico no link "Analisar"
    Então vejo os seguintes campos no formulário
      | Campo      | Tipo     |
      | Comentário | TextArea |
      | Previsão   | Data     |
    E vejo o botão "Enviar"
    Quando clico no botão "Enviar"
    Então vejo os seguintes erros no formulário
      | Campo    | Tipo | Mensagem                 |
      | Previsão | Data | Este campo é obrigatório |
    Quando preencho o formulário com os dados
      | Campo      | Tipo     | Valor                  |
      | Comentário | TextArea | Comentário da Situação |
      | Previsão   | Data     | 01/01/2018             |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Em análise"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Verifica a visibilidade do demandante após mudança de Status
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Consolidação da Demanda 1"
    E vejo o status "Em análise"
    E vejo a aba "Consolidação"
    Quando clico na aba "Consolidação"
    E olho para a aba "Consolidação"
    Então vejo o botão "Aprovar"
    E vejo o botão "Reprovar"

  @do_document
  Cenário: O demandante rejeita uma consolidação, com isso, a demanda volta para o status "Em negociação"
    Quando clico no botão "Reprovar"
    Então vejo a página "Reprovar Demanda"
    Quando preencho o formulário com os dados
      | Campo                | Tipo     | Valor  |
      | Senha para confirmar | senha    | abcd   |
      | Confirma a operação  | Checkbox | Marcar |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A consolidação da demanda foi reprovada."
    E vejo o status "Em negociação"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Retorna a demanda para o status Em análise
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    E clico no ícone de exibição
    E clico na aba "Consolidação"
    E clico no botão "Alterar Etapa"
    E clico no link "Analisar"
    E preencho o formulário com os dados
      | Campo      | Tipo     | Valor                  |
      | Comentário | TextArea | Comentário da Situação |
      | Previsão   | Data     | 01/01/2018             |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Em análise"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O demandante aceita a consolidação, com isso, a demanda volta para o status "Aprovada"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    E clico no ícone de exibição
    E clico na aba "Consolidação"
    E olho para a aba "Consolidação"
    E clico no botão "Aprovar"
    Então vejo a página "Aprovar Demanda"
    Quando preencho o formulário com os dados
      | Campo                | Tipo     | Valor  |
      | Senha para confirmar | senha    | abcd   |
      | Confirma a operação  | Checkbox | Marcar |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A consolidação da demanda foi aprovada."
    E vejo o status "Aprovada"
