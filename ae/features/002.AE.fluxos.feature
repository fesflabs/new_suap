# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Fluxos

  @do_document
  Cenário: Realizar da Caracterização Socioeconômica do Aluno
    Para se inscrever em um Programa, o aluno precisa ter a sua caracterização socioeconômica realizada. Esta caracterização pode ser feita pelo próprio aluno ou pelo(a) Assistente Social.
    Ação executada pelo Assistente Social ou pelo próprio aluno.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "20191101011031" e senha "abcd"
    E a data do sistema for "01/11/2019"
    E acesso o menu "Atividades Estudantis::Serviço Social::Caracterização Socioeconômica"
    Então vejo a página "Caracterização Social"
    Quando preencho o formulário com os dados
      | Campo                                                          | Tipo              | Valor                        |
      | Etnia/Raça/Cor                                                 | Autocomplete      | Parda                        |
      | Estado Civil                                                   | Autocomplete      | Solteiro(a)                  |
      | Serviço de Saúde que você mais utiliza                         | Autocomplete      | Sistema Único de Saúde - SUS |
      | Ano de conclusão do Ensino Fundamental                         | Texto             |                         2017 |
      | Tipo de escola que cursou o Ensino Fundamental                 | Autocomplete      | Somente em escola pública    |
      | Situação de Trabalho                                           | Autocomplete      | Não está trabalhando         |
      | Meio de transporte que você utiliza/utilizará para se deslocar | checkbox multiplo | Bicicleta, Moto              |
      | Contribuintes da Renda Familiar                                | checkbox multiplo | Pai, Mãe, Parentes           |
      | Principal Responsável Financeiro                               | checkbox multiplo | Pai, Mãe                     |
      | Situação de Trabalho do Principal Responsável Financeiro       | Lista             | Autônomo                     |
      | Nível de Escolaridade do Principal Responsável Financeiro      | Autocomplete      | Ensino médio completo        |
      | Nível de escolaridade do pai                                   | Autocomplete      | Ensino médio completo        |
      | Nível de escolaridade da mãe                                   | Autocomplete      | Ensino médio completo        |
      | Renda Bruta Familiar R$                                        | Texto             |                     2.500,00 |
      | Companhia domiciliar                                           | checkbox multiplo | Pai, Mãe                     |
      | Número de pessoas no domicílio                                 | texto             |                            1 |
      | Tipo de Imóvel                                                 | Autocomplete      | Financiado                   |
      | Tipo de Área Residencial                                       | Autocomplete      | Urbana                       |
      | Frequência de Acesso à Internet                                | Autocomplete      | Diariamente                  |
      | Quantidade de Computadores Desktop que possui                  | texto             |                            1 |
      | Quantidade de Notebooks que possui                             | texto             |                            1 |
      | Quantidade de Smartphones que possui                           | texto             |                            1 |
      | Quantidade de Netbooks que possui                              | texto             |                            0 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Caracterização realizada com sucesso."

  @do_document
  Cenário: Inscrever Aluno no Programa
    Ação executada pelo Assistente Social ou pelo próprio aluno.

    Dado acesso a página "/"
    Quando clico no link "Inscrever-se em"
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor           |
      | Código            | texto        | 123456          |
    E clico no botão "Autenticar"
    Então vejo a página "Inscrição para Alimentação Estudantil (CZN): Caracterização Socioeconômica"
    Quando clico no botão "Continuar"
    Então vejo a página "Inscrição para Alimentação Estudantil (CZN): Caracterização do Grupo Familiar"
    Quando preencho o formulário com os dados
      | Campo                                                   | Tipo         | Valor  |
      | Situação de moradia do principal responsável financeiro | Autocomplete | Outro  |
      | Valor gasto com transporte por dia                      | Texto        | 500,20 |
      | Renda do Estudante                                      | Texto        | 430,00 |
    E clico no botão "Continuar"
    Então vejo a página "Inscrição para Alimentação Estudantil (CZN): Documentação"
    E vejo o botão "Continuar"
    Quando preencho o formulário com os dados
      | Campo                         | Tipo    | Valor                         |
      | Comprovante de Residência     | Arquivo | comprovante.png               |
    E clico no botão "Continuar"
    Então vejo mensagem de sucesso "Informe as refeições que você deseja obter."
    E vejo a página "Inscrição para Alimentação Estudantil (CZN): Detalhamento"
    E vejo os seguintes campos no formulário
      | Campo                 | Tipo     |
      | Motivo da Solicitação | TextArea |
      | Segunda               | Checkbox |
    E vejo o botão "Continuar"
    Quando preencho o formulário com os dados
      | Campo                 | Tipo     | Valor               |
      | Motivo da Solicitação | TextArea | descrição do motivo |
      | Segunda               | Checkbox | marcar              |
    E clico no botão "Continuar"
    Então vejo mensagem de sucesso "Inscrição realizada com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Registrar da Entrega da Documentação do Aluno
    Para o aluno ser adicionado em um programa, é preciso registrar que a documentação dele foi entregue.
    O assistente social visualiza os arquivos na aba 'Atividades Estudantis' na tela do aluno e, estando tudo correto, registra que a documentação foi entregue.
    Ação executada pelo Assistente Social.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "103002" e senha "abcd"
    E a data do sistema for "01/11/2019"
    E acesso o menu "Atividades Estudantis::Serviço Social::Programas::Inscrições"
    Então vejo a página "Inscrições"
    Quando seleciono o item "20191101011031" da lista
    Então vejo os seguintes campos no formulário
      | Campo | Tipo  |
      | Ação  | Lista |
    Quando preencho o formulário com os dados
      | Campo | Tipo  | Valor                             |
      | Ação  | Lista | Registrar entrega de documentação |
    E clico no botão de ação "Aplicar"
    Então vejo a página "Informar Data de Entrega da Documentação"
    E vejo os seguintes campos no formulário
      | Campo | Tipo  |
      | Data  | Data  |
    E vejo o botão "Enviar"
    Quando preencho o formulário com os dados
      | Campo | Tipo  | Valor      |
      | Data  | Data  | 10/01/2019 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Entrega de documentação realizada com sucesso."

  @do_document
  Cenário: Incluir do Aluno como Participante do Programa
    Ação executada pelo Assistente Social.

    Quando acesso o menu "Atividades Estudantis::Serviço Social::Programas::Programas"
    Então vejo a página "Programas"
    Quando olho a linha "Alimentação Estudantil"
    E clico no ícone de exibição
    Então vejo a página "Programa: Alimentação Estudantil (CZN)"
    Quando clico no botão "Gerenciar Participações"
    Então vejo a página "Gerenciar Participações"
    E vejo o botão "Adicionar Participação"
    Quando clico no botão "Adicionar Participação"
    E olho para o popup
    Então vejo a página "Adicionar Participação"
    Quando preencho o formulário com os dados
      | Campo             | Tipo              | Valor                             |
      | Data de Entrada   | Data              | 15/01/2018                        |
      | Motivo de Entrada | TextArea          | motivo da entrada da participação |
      | Café da Manhã     | checkbox multiplo | Segunda, Terça                    |
      | Categoria         | Autocomplete      | AS                                |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Participação adicionada com sucesso."
