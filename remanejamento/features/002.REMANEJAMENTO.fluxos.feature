# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Fluxos

  @do_document
  Cenário: Interpor Recurso ao Edital
  Ação executada por servidores que são alvo do edital de remanejamento.

    Dado acesso a página "/"
    Quando a data do sistema for "05/05/2020"
    Quando realizo o login com o usuário "7114156" e senha "abcd"
    E clico no link "Recurso ao Edital Novo Edital de Remanejamento"
    Então vejo a página "Recurso ao Novo Edital de Remanejamento"
    Quando preencho o formulário com os dados
      | Campo   | Tipo  | Valor   |
      | Recurso | textarea | Recurso |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Recurso cadastrado com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Responder Recurso ao Edital
  Ação executada pela comissão de remanejamento.

    Dado acesso a página "/"
    Quando a data do sistema for "05/05/2020"
    Quando realizo o login com o usuário "7114145" e senha "abcd"
    E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Remanejamento::Recursos ao Edital"
    Então vejo a página "Recursos ao Edital"
    Quando olho a linha "Novo Edital de Remanejamento"
    E clico no ícone de exibição
    Então vejo a página "Recurso ao Novo Edital de Remanejamento"
    Quando preencho o formulário com os dados
      | Campo    | Tipo  | Valor                |
      | Resposta | textarea | Resposta ao Recurso |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Resposta ao Recurso cadastrada com sucesso."
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Realizar Inscrição no Remanejamento
  Ação executada por servidores que são alvo do edital de remanejamento.

    Dado acesso a página "/"
    Quando a data do sistema for "14/06/2020"
    Quando realizo o login com o usuário "7114156" e senha "abcd"
    E clico no link "Inscrever-se para Remanejamento: Novo Edital de Remanejamento"
    Então vejo a página "Inscrição para Edital de Remanejamento"
    E vejo os seguintes campos no formulário
      | Campo                                           | Tipo   |
      | Disciplina                                      | Lista  |
      | Classificação no concurso para ingresso no IFRN | Numero |
      | Número                                          | Texto  |
      | Data                                            | Data   |
      | Página                                          | Texto  |
      | Seção                                           | Texto  |
      | Campus Zona Norte                               | Numero |
    E vejo o botão "Salvar"

    Quando preencho o formulário com os dados
      | Campo                                           | Tipo   | Valor                   |
      | Disciplina                                      | Lista  | descricao da disciplina |
      | Classificação no concurso para ingresso no IFRN | Texto  | 5                       |
      | Número                                          | Texto  | 12                      |
      | Data                                            | Data   | 02/02/2019              |
      | Página                                          | Texto  | 2                       |
      | Seção                                           | Texto  | 2                       |
      | Campus Zona Norte                               | Texto  | 1                       |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Inscrição realizada com sucesso."


  @do_document
  Cenário: Interpor Recursos ao Resultado Parcial
  Ação executada por servidores inscritos no edital de remanejamento.

    Dado acesso a página "/"
    Quando a data do sistema for "16/06/2020"
    E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Remanejamento::Inscrições"
    Então vejo a página "Inscrições"
    Quando olho a linha "Servidor Remanejamento (7114156)"
    E clico no ícone de exibição
    Quando preencho o formulário com os dados
      | Campo                                           | Tipo  | Valor                   |
      | Texto do Recurso                                | textarea | Recurso Resultado       |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Recurso ao resultado cadastrado com sucesso."
    Quando acesso o menu "Sair"
  
  
  @do_document
  Cenário: Responder Recursos ao Resultado Parcial
  Ação executada pela comissão do edital de remanejamento.

    Dado acesso a página "/"
    Quando a data do sistema for "20/06/2020"
    E realizo o login com o usuário "7114145" e senha "abcd"
    E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Remanejamento::Inscrições"
    Então vejo a página "Inscrições"
    Quando olho a linha "Servidor Remanejamento (7114156)"
    E clico no ícone de exibição
    Quando preencho o formulário com os dados
      | Campo                                           | Tipo  | Valor                   |
      | Resposta ao recurso                             | textarea | Recurso Indeferido      |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Resposta ao recurso do resultado parcial cadastrado com sucesso."
