# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Operações em demandas nos demais status
   Serão realizados os testes para os seguintes status: Em desenvolvimento, Em homologação, Homologada, Em implantação e
   Concluída.

  @do_document
  Cenário: Retira o desenvolvedor da demanda
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    E clico no ícone de edição
    Então vejo a página "Editar Demanda 1: Consolidação da Demanda 1"
    Quando removo o item "Desenvolvedor" no autocomplete "Desenvolvedores"
    Então nao vejo o item "Desenvolvedor" no autocomplete "Desenvolvedores"
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: O analista muda o status da demanada pra Em desenvolvimento
    Quando acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    E clico no ícone de exibição
    Então vejo o status "Aprovada"
    Quando clico no botão "Alterar Etapa"
    E clico no botão "Desenvolver"
    Então vejo os seguintes campos no formulário
      | Campo           | Tipo                  |
      | Comentário      | TextArea              |
      | Previsão        | Data                  |
      | Desenvolvedores | Autocomplete Multiplo |
    Quando preencho o formulário com os dados
      | Campo           | Tipo                  | Valor                  |
      | Comentário      | TextArea              | Comentário da Situação |
      | Previsão        | Data                  | 01/01/2018             |
      | Desenvolvedores | Autocomplete Multiplo |                 105003 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Em desenvolvimento"
    Quando acesso o menu "Sair"

  Esquema do Cenário: Verifica a visibilidade do <Papel> após mudança de Status
    Dado acesso a página "/"
    Quando realizo o login com o usuário "<Papel>" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Consolidação da Demanda 1"
    E vejo o status "Em desenvolvimento"
    E vejo a aba "Consolidação"
    Quando acesso o menu "Sair"

    Exemplos:
      | Papel  |
      | 105001 |
      | 105003 |

  @do_document
  Cenário: Realiza a mudança o status para Em homologação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    E clico no botão "Alterar Etapa"
    E clico no botão "Homologar"
    Então vejo os seguintes campos no formulário
      | Campo                              | Tipo     |
      | Comentário                         | TextArea |
      | Conclusão                          | Data     |
      | Previsão                           | Data     |
      | URL para Ambiente de Homologação   | Texto    |
      | Senha para Ambiente de Homologação | Texto    |
    Quando clico no botão "Enviar"
    Então vejo os seguintes erros no formulário
      | Campo    | Tipo | Mensagem                  |
      | Previsão | Data | Este campo é obrigatório. |
    Quando preencho o formulário com os dados
      | Campo                              | Tipo     | Valor             |
      | Comentário                         | TextArea | Comentário        |
      | Conclusão                          | Data     | 02/01/2018        |
      | Previsão                           | Data     | 01/01/2018        |
      | URL para Ambiente de Homologação   | Texto    | http://localhost/ |
      | Senha para Ambiente de Homologação | Texto    |              1234 |
    E clico no botão "Enviar"
    Então vejo os seguintes erros no formulário
      | Campo     | Tipo | Mensagem                                                              |
      | Conclusão | Data | A Data de Previsão não pode ser menor que a última Data de Conclusão. |
    Quando preencho o formulário com os dados
      | Campo                              | Tipo     | Valor             |
      | Comentário                         | TextArea | Comentário        |
      | Conclusão                          | Data     | 01/01/2018        |
      | Previsão                           | Data     | 01/01/2018        |
      | URL para Ambiente de Homologação   | Texto    | http://localhost/ |
      | Senha para Ambiente de Homologação | Texto    |              1234 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Em homologação"
    E vejo a aba "Homologação"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Verifica a visibilidade do Desenvolvedor após mudança para Em homologação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105003" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Consolidação da Demanda 1"
    E vejo o status "Em homologação"
    E vejo a aba "Homologação"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Verifica a visibilidade do Demandante após mudança para Em homologação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Consolidação da Demanda 1"
    E vejo o status "Em homologação"
    E vejo a aba "Homologação"
    Quando clico na aba "Homologação"
    E olho para a aba "Homologação"
    Então vejo o botão "Aprovar"
    E vejo o botão "Reprovar"
    Quando clico no botão "Reprovar"
    Então vejo a página "Reprovar Homologação"
    Quando preencho o formulário com os dados
      | Campo                | Tipo     | Valor  |
      | Senha para confirmar | senha    | abcd   |
      | Confirma a operação  | Checkbox | Marcar |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A homologação da demanda foi reprovada."
    E vejo o status "Em negociação"
    Quando forço o status da demanda "Demanda 1" para "Em homologação"
    E atualizo a página
    Então vejo o status "Em homologação"
    Quando clico na aba "Homologação"
    E olho para a aba "Homologação"
    E clico no botão "Aprovar"
    Então vejo a página "Aprovar Homologação"
    Quando preencho o formulário com os dados
      | Campo                | Tipo     | Valor  |
      | Senha para confirmar | senha    | abcd   |
      | Confirma a operação  | Checkbox | Marcar |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A homologação da demanda foi aprovada."
    E vejo o status "Homologada"
    E nao vejo a aba "Homologação"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Realiza a mudança o status para Em implantação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    E clico no ícone de exibição
    E clico no botão "Alterar Etapa"
    E clico no botão "Implantar"
    Então vejo os seguintes campos no formulário
      | Campo      | Tipo     |
      | Comentário | TextArea |
      | Previsão   | Data     |
    Quando preencho o formulário com os dados
      | Campo      | Tipo     | Valor      |
      | Comentário | TextArea | Comentário |
      | Previsão   | Data     | 01/01/2018 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Em implantação"

  @do_document
  Cenário: Realiza a mudança o status para Concluída
    Quando acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Consolidação da Demanda 1"
    E clico no ícone de exibição
    E clico no botão "Alterar Etapa"
    E clico no botão "Concluir"
    Então vejo os seguintes campos no formulário
      | Campo      | Tipo     |
      | Comentário | TextArea |
      | Conclusão  | Data     |
    Quando preencho o formulário com os dados
      | Campo      | Tipo     | Valor      |
      | Comentário | TextArea | Comentário |
      | Conclusão  | Data     | 01/01/2018 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Concluída"
    E nao vejo o botão "Alterar Etapa"
    E nao vejo o botão "Editar"
