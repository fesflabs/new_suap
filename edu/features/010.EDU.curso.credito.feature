# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Configurar Curso no Regime de Crédito

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado os cadastros da funcionalidade 001
    E acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"
    E a data do sistema for "22/07/2019"

  @do_document
  Cenário: Cadastrar Estrutura de Curso
    Uma estrutura de curso define os critérios para aprovação no curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Estrutura de Curso" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Estrutura de Curso"
    Então vejo a página "Estruturas de Curso"
    Quando clico no botão "Adicionar Estrutura de Curso"
    E preencho o formulário com os dados
      | Campo                                                               | Tipo     | Valor                                                    |
      | Descrição                                                           | texto    | Licenciatura                                             |
      | Está Ativa                                                          | checkbox | marcar                                                   |
      | Tipo de Avaliação                                                   | radio    | Crédito                                                  |
      | Número Mínimo de Disciplinas por Período                            | texto    |                                                        1 |
      | Número Máximo de Disciplinas extras por Período                     | texto    |                                                        2 |
      | Número Máximo de Períodos Subsequentes para Matrícula em Disciplina | texto    |                                                       10 |
      | Número Máximo de Cancelamentos de Disciplinas                       | texto    |                                                        1 |
      | Critério de Avaliação                                               | radio    | Nota                                                     |
      | Média para passar sem prova final                                   | texto    |                                                       60 |
      | Média para não reprovar direto                                      | texto    |                                                       20 |
      | Média para aprovação após avaliação final                           | texto    |                                                       60 |
      | Percentual Mínimo de Frequência                                     | texto    |                                                       75 |
      | Forma de Cálculo                                                    | radio    | Média dos componentes pela carga horária dos componentes |
      | Número Máximo de Matrículas em Períodos                             | texto    |                                                       16 |
      | Número Máximo de Reprovações no Mesmo Período                       | texto    |                                                        0 |
      | Número Máximo de Reprovações na Mesma Disciplina                    | texto    |                                                        0 |
      | Número Máximo de Trancamentos                                       | texto    |                                                        2 |
      | Percentual Máximo de Aproveitamento                                 | texto    |                                                       50 |
      | Número Máximo de Certificações por Período                          | texto    |                                                        4 |
      | Média para Certificação                                             | texto    |                                                       60 |
    E olho e clico no botão "Salvar"
    E olho para a página
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Configuração de ATPA
    Define as Atividades Teórico-Práticas de Aprofundamento

    Quando pesquiso por "Configurações ATPAs" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Configurações ATPAs"
    Então vejo a página "Configurações de ATPA"
    Quando clico no botão "Adicionar Configuração de ATPA"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                   |
      | Descrição | texto | ATPA Licenciaturas 2018 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Configuração cadastrada com sucesso. Adicione os tipos de atividades."

  @do_document
  Cenário: Cadastrar Matriz Curricular
    Define o quantitativo de carga horária exigido para cada tipo de componente e outras configurações. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Matrizes Curriculares" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Matrizes Curriculares"
    Então vejo a página "Matrizes Curriculares"
    Quando clico no botão "Adicionar Matriz Curricular"
    E preencho o formulário com os dados
      | Campo                                         | Tipo         | Valor                     |
      | Descrição                                     | texto        | Licenciatura em Geografia |
      | Ano Criação                                   | Autocomplete |                      2019 |
      | Período Criação                               | lista        |                         1 |
      | Nível de Ensino                               | Autocomplete | Graduação                 |
      | Ativa                                         | checkbox     | marcar                    |
      | Data de início                                | data         | 15/03/2019                |
      | PPP                                           | arquivo      | arquivo.pdf               |
      | Quantidade de Períodos Letivos                | lista        |                         8 |
      | Estrutura                                     | Autocomplete | Licenciatura              |
      | Componentes obrigatórios                      | texto        |                      1920 |
      | Componentes optativos                         | texto        |                       180 |
      | Componentes eletivos                          | texto        |                         0 |
      | Seminários                                    | texto        |                       244 |
      | Prática Profissional                          | texto        |                       800 |
      | Trabalho de Conclusão de Curso                | texto        |                         0 |
      | Atividades complementares                     | texto        |                         0 |
      | Atividades Teórico-Práticas de Aprofundamento | texto        |                       200 |
      | Atividades de Extensão                        | texto        |                         0 |
      | Prática como Componente Curricular            | texto        |                         0 |
      | Visita Técnica/Aula de Campo                  | texto        |                         0 |
      | Configuração de ATPA                          | Autocomplete | ATPA Licenciaturas 2018   |
      | Exige TCC                                     | checkbox     | marcar                    |
      | Período Mínimo para Estágio Obrigatório       | lista        |                         1 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Matriz cadastrada com sucesso. Por favor, vincule os componentes à matriz."

  @do_document
  Cenário: Vincular Componente à Matriz Curricular
    Associa os componentes que farão parte da matriz curricular criada. Um componente associado a uma matriz é chamado de componente curricular. Ação executada pelo perfil Administrador Acadêmico.

    Dado os cadastros iniciais de componente curricular
    Quando pesquiso por "Matrizes Curriculares" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Matrizes Curriculares"
    Então vejo a página "Matrizes Curriculares"
    Quando olho a linha "Licenciatura em Geografia"
    E clico no ícone de exibição
    Então vejo a página "2 - Licenciatura em Geografia"
    Quando clico na aba "Componentes Curriculares"
    E clico no botão "Vincular Componente"
    Então vejo a página "Vincular Componente de matriz"
    Quando preencho o formulário com os dados
      | Campo           | Tipo         | Valor    |
      | Componente      | autocomplete | LIC.0001 |
      | Periodo letivo  | lista        |        1 |
      | Tipo            | lista        | Regular  |
      | Qtd. Avaliações | lista        | Duas     |
      | Núcleo          | Autocomplete | Formação |
    E clico no botão "Vincular Componente"
    Então vejo mensagem de sucesso "Componente de matriz adicionado com sucesso."

  @do_document
  Cenário: Cadastrar Pré e Co Requisitos
    Quando clico na aba "Pré/Co-Requisitos"
    E olho para o quadro "Pré/Co-Requisitos"
    E olho a linha "LIC.0002"
    E clico no ícone de "edição"
    E olho para o popup
    E olho para o quadro "Pré-requisitos"
    E seleciono o item "LIC.0001" da lista
    E olho para a página
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Requisitos definidos com sucesso."
    Quando clico na aba "Pré/Co-Requisitos"
    E olho para o quadro "Pré/Co-Requisitos"
    E olho a linha "LIC.0003"
    E clico no ícone de "edição"
    E olho para o popup
    E olho para o quadro "Co-requisitos"
    E seleciono o item "LIC.0002" da lista
    E olho para a página
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Requisitos definidos com sucesso."
    Quando clico na aba "Pré/Co-Requisitos"
    E olho para o quadro "Pré/Co-Requisitos"
    E olho a linha "LIC.0004"
    E clico no ícone de "edição"
    E olho para o popup
    E olho para o quadro "Co-requisitos"
    E seleciono o item "LIC.0001" da lista
    E olho para a página
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Requisitos definidos com sucesso."

  @do_document
  Cenário: Cadastrar Área de Curso
    Cadastro de dados básicos para cadastro de curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Áreas de Cursos" e acesso o menu "Ensino::Cadastros Gerais::Áreas de Cursos"
    Então vejo a página "Áreas de Cursos"
    Quando clico no botão "Adicionar Área de Curso"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor            |
      | Descrição | texto | Ciências Humanas |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Curso
    Cadastro de dados básicos do curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Cursos" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Cursos"
    Então vejo a página "Cursos"
    Quando clico no botão "Adicionar Curso"
    E preencho o formulário com os dados
      | Campo                                   | Tipo         | Valor                     |
      | Descrição                               | texto        | Licenciatura em Geografia |
      | Descrição no Diploma e Histórico        | texto        | Licenciatura em Geografia |
      | Formação de Professores                 | checkbox     | marcar                    |
      | Ano letivo                              | Autocomplete |                      2019 |
      | Período letivo                          | lista        |                         1 |
      | Data início                             | data         | 15/03/2019                |
      | Ativo                                   | checkbox     | marcar                    |
      | Código                                  | texto        |                     20101 |
      | Natureza de participação                | Autocomplete | Presencial                |
      | Modalidade de Ensino                    | Autocomplete | Licenciatura              |
      | Área                                    | Autocomplete | Ciências Humanas          |
      | Periodicidade                           | lista        | Semestral                 |
      | Diretoria                               | Autocomplete | DIAC/CEN                  |
      | Exige enade                             | checkbox     | marcar                    |
      | Exige colação de grau                   | checkbox     | marcar                    |
      | Certificado/Diploma Emitido pelo Campus | checkbox     | marcar                    |
      | Fator de Esforço de Curso (FEC)         | texto        |                         1 |
      | Masculino                               | texto        | Licenciado em Geografia   |
      | Feminino                                | texto        | Licenciada em Geografia   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Curso cadastrado com sucesso. Por favor, vincule a(s) matriz(es) ao curso."

  @do_document
  Cenário: Vincular Matriz ao Curso
    Vincula uma matriz e seus componentes curriculares a um curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Cursos" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Cursos"
    E olho a linha "20101"
    E clico no ícone de exibição
    Então vejo a página "20101 - Licenciatura em Geografia (Campus Central)"
    Quando clico na aba "Matrizes"
    E clico no botão "Vincular Matriz"
    E olho para o popup
    Então vejo a página "Adicionar Matriz"
    Quando preencho o formulário com os dados
      | Campo                | Tipo         | Valor                                                  |
      | Matriz               | autocomplete | Licenciatura em Geografia                              |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Matriz adicionada com sucesso."
