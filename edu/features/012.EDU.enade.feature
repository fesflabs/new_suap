# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: ENADE
  Demonstra o fluxo para convocação de alunos para o ENADE e registro da situação deles no exame. 
  Perfis 'Operador ENADE' e 'Diretor de Avaliação e Regulação do Ensino'.

  Cenário: Autenticar como Diretor de Avaliação e Regulação do Ensino
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100009" e senha "abcd"
    E a data do sistema for "10/03/2019"

  @do_document
  Cenário: Cadastrar Justificativas de Dispensa do ENADE
    Cria justificativas para dispensar aluno da participação no ENADE. Ação executada pelo Diretor de Avaliação e Regulação do Ensino

    Quando pesquiso por "Justificativas de Dispensa do ENADE" e acesso o menu "Ensino::Cadastros Gerais::Justificativas de Dispensa do ENADE"
    E clico no botão "Adicionar Justif. de Dispensa do ENADE"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                                                                   |
      | Descrição | texto | Estudante dispensado de realização do ENADE, por razão de ordem pessoal |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Autenticar como Operador ENADE
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100008" e senha "abcd"

  @do_document
  Cenário: Cadastrar Convocação
    Cria uma convocação do ENADE para alunos ingressantes e concluintes de cursos selecionados na convocação

    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E clico no botão "Adicionar Convocação do ENADE"
    E preencho o formulário com os dados
      | Campo                                   | Tipo                  | Valor                                                           |
      | Ano letivo                              | autocomplete          |                                                            2019 |
      | Descrição                               | texto                 | Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019 |
      | Cursos                                  | autocomplete multiplo | Geografia                                                       |
      | Percentual Mínimo (%) para Ingressantes | texto                 |                                                               0 |
      | Percentual Máximo (%) para Ingressantes | texto                 |                                                              25 |
      | Percentual Mínimo (%) para Concluintes  | texto                 |                                                              80 |
      | Percentual Máximo (%) para Concluintes  | texto                 |                                                             100 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Convocar alunos
    Realiza a convocação dos alunos aptos para o ENADE

    Quando olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de exibição
    E clico no botão "Processar Lista de Convocados"
    E clico no botão "Todos os Cursos"
    E clico no botão "Continuar"
    E olho para o quadro "Quadro de Convocados"
    E olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    E clico no quadro "Ingressantes"
    Então vejo a linha "Maria Pereira"

  @do_document
  Cenário: Definir data de realização do ENADE
    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo                       | Tipo | Valor      |
      | Data de Realização da Prova | data | 02/04/2019 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Lançar situação (Ausente)
    Dado acesso a página "/"
    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de exibição
    E olho para o quadro "Quadro de Convocados"
    E olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    E clico no quadro "Ingressantes"
    E clico no link "20191201010001"
    E clico na aba "ENADE"
    E clico no botão "Lançar Situação"
    E preencho o formulário com os dados
      | Campo    | Tipo  | Valor   |
      | Situação | lista | Ausente |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Lançamento do ENADE realizado com sucesso."

  @do_document
  Cenário: Editar Situação
    Dado acesso a página "/"
    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de exibição
    E olho para o quadro "Quadro de Convocados"
    E olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    E clico no quadro "Ingressantes"
    E clico no link "20191201010001"
    E clico na aba "ENADE"
    E clico no botão "Editar Situação"
    E preencho o formulário com os dados
      | Campo                     | Tipo  | Valor                                                                   |
      | Situação                  | lista | Dispensado                                                              |
      | Justificativa de Dispensa | lista | Estudante dispensado de realização do ENADE, por razão de ordem pessoal |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Lançamento do ENADE realizado com sucesso."

  @do_document
  Cenário: Remover Situação
    Dado acesso a página "/"
    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de exibição
    E olho para o quadro "Quadro de Convocados"
    E olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    E clico no quadro "Ingressantes"
    E clico no link "20191201010001"
    E clico na aba "ENADE"
    E clico no botão "Remover Situação"
    Então vejo mensagem de sucesso "Situação do ENADE removida com sucesso."

  @do_document
  Cenário: Lançar situação (Regular)
    Lança a situação do aluno no ENADE em que ele foi convocado

    Dado acesso a página "/"
    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de exibição
    E olho para o quadro "Quadro de Convocados"
    E olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    E clico no quadro "Ingressantes"
    E clico no link "20191201010001"
    E clico na aba "ENADE"
    E clico no botão "Lançar Situação"
    E preencho o formulário com os dados
      | Campo    | Tipo  | Valor   |
      | Situação | lista | Regular |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Lançamento do ENADE realizado com sucesso."

  @do_document
  Cenário: Consultar registro de alterações
    Exibe as alterações realizadas no registro de convocação ENADE do aluno

    Dado acesso a página "/"
    Quando pesquiso por "Convocações do ENADE" e acesso o menu "Ensino::Procedimentos de Apoio::Convocações do ENADE"
    E olho a linha "Licenciaturas - Portaria Normativa No 8, de 26 de Março de 2019"
    E clico no ícone de exibição
    E olho para o quadro "Quadro de Convocados"
    E olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    E clico no quadro "Ingressantes"
    E clico no link "20191201010001"
    E clico na aba "ENADE"
    E clico no botão "Log de Alterações"
    E olho para o popup
    Então vejo o texto "Registro de Convocação ENADE"

  Cenário: Dispensar aluno do ENADE
    Para o aluno que cumpre todos os requisitos, exceto ENADE e colação de grau, o sistema permite 
    o cadastro de dispensa do aluno da participação do ENADE

    # TODO: pendente cumprir os requisitos do aluno para habilitar funcionalidade dispensa do ENADE
    Dado acesso a página "/"
