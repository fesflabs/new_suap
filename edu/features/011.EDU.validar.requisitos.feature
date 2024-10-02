# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Validar Pré e Co Requisitos

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado a matrícula do aluno regime de crédito
    E acesso a página "/"
    Quando realizo o login com o usuário "100002" e senha "abcd"
    E a data do sistema for "22/07/2019"

  # pendencias:
  #  - matricular aluno nos diarios validando pre/co requisitos
  #  - testar matricular em diário fora da matriz e fora do componente
  #  - testar matricular em diário fora da matriz do mesmo componente
  @do_document
  Cenário: Gerar Diários Obrigatórios
    Cria as turmas de um curso para um período letivo de um campus. Ação executada pelo perfil Secretário Acadêmico.

    Quando pesquiso por "Turmas" e acesso o menu "Ensino::Turmas e Diários::Turmas"
    E clico no botão "Gerar Turmas"
    Quando preencho o formulário com os dados
      | Campo                | Tipo         | Valor                     |
      | Ano Letivo           | lista        |                      2019 |
      | Período Letivo       | lista        |                         2 |
      | Tipo dos Componentes | lista        | Obrigatório               |
      | Matriz/Curso         | autocomplete | Licenciatura em Geografia |
    E clico no botão "Continuar"
    E olho para o quadro "1º Período"
    E preencho o formulário com os dados
      | Campo        | Tipo  | Valor    |
      | Nº de Turmas | lista |        1 |
      | Turno        | lista | Matutino |
      | Nº de Vagas  | texto |       10 |
    E olho para a página
    E olho para o quadro "2º Período"
    E preencho o formulário com os dados
      | Campo        | Tipo  | Valor    |
      | Nº de Turmas | lista |        1 |
      | Turno        | lista | Matutino |
      | Nº de Vagas  | texto |       10 |
    E olho para a página
    E clico no botão "Continuar"
    E olho para o quadro "Horário/Calendário e Componentes"
    E preencho o formulário com os dados
      | Campo                | Tipo  | Valor                                                   |
      | Horário do Campus    | lista | Horário Padrão [Aula 45min] (CEN)                       |
      | Calendário Acadêmico | lista | [2] Calendário Acadêmico Licenciatura 2019.2 - CEN/2019.2 |
    E olho para o quadro "Seleção de Componentes"
    E seleciono o item "LIC.0001 - Matemática Aplicada à Geografia - Graduação [30 h/40 Aulas]" da lista
    E seleciono o item "LIC.0002 - Estatística Básica - Graduação [30 h/40 Aulas]" da lista
    E seleciono o item "LIC.0003 - Fundamentos da Educação - Graduação [60 h/80 Aulas]" da lista
    E olho para a página
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo       | Tipo     | Valor  |
      | Confirmação | checkbox | marcar |
    E clico no botão "Finalizar"
    Então vejo mensagem de sucesso "Turmas geradas com sucesso."

  @do_document
  Cenário: Gerar Diários Optativo
    Cria as turmas de um curso para um período letivo de um campus. Ação executada pelo perfil Secretário Acadêmico.

    Quando pesquiso por "Turmas" e acesso o menu "Ensino::Turmas e Diários::Turmas"
    E clico no botão "Gerar Turmas"
    Quando preencho o formulário com os dados
      | Campo                | Tipo         | Valor                     |
      | Ano Letivo           | lista        |                      2019 |
      | Período Letivo       | lista        |                         2 |
      | Tipo dos Componentes | lista        | Optativo                  |
      | Matriz/Curso         | autocomplete | Licenciatura em Geografia |
    E clico no botão "Continuar"
    E clico no botão "Continuar"
    E olho para o quadro "Horário/Calendário e Componentes"
    E preencho o formulário com os dados
      | Campo                | Tipo  | Valor                                                   |
      | Horário do Campus    | lista | Horário Padrão [Aula 45min] (CEN)                       |
      | Calendário Acadêmico | lista | [2] Calendário Acadêmico Licenciatura 2019.2 - CEN/2019.2 |
    E olho para o quadro "Seleção de Componentes"
    E seleciono o item "LIC.0004 - Elaboração de Material Didático em Geografia - Graduação [60 h/80 Aulas]" da lista
    E olho para a página
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo       | Tipo     | Valor  |
      | Confirmação | checkbox | marcar |
    E clico no botão "Finalizar"
    Então vejo mensagem de sucesso "Turmas geradas com sucesso."
