# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Configurar Curso

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado os cadastros da funcionalidade 001
    E acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"
    E a data do sistema for "10/03/2019"

  @do_document
  Cenário: Cadastrar Estrutura de Curso
    Uma estrutura de curso define os critérios para aprovação no curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Estrutura de Curso" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Estrutura de Curso"
    Então vejo a página "Estruturas de Curso"
    Quando clico no botão "Adicionar Estrutura de Curso"
    E preencho o formulário com os dados
      | Campo                                                       | Tipo     | Valor                                                    |
      | Descrição                                                   | texto    | Especialização e Aperfeiçoamento                         |
      | Está Ativa                                                  | checkbox | marcar                                                   |
      | Tipo de Avaliação                                           | radio    | Seriado                                                  |
      | Número Máximo de Reprovações para Aprovação por Dependência | texto    |                                                       10 |
      | Critério de Avaliação                                       | radio    | Nota                                                     |
      | Média para passar sem prova final                           | texto    |                                                       60 |
      | Média para não reprovar direto                              | texto    |                                                       20 |
      | Média para aprovação após avaliação final                   | texto    |                                                       60 |
      | Percentual Mínimo de Frequência                             | texto    |                                                       75 |
      | Forma de Cálculo                                            | radio    | Média dos componentes pela carga horária dos componentes |
      | Número Máximo de Matrículas em Períodos                     | texto    |                                                        4 |
      | Número Máximo de Reprovações no Mesmo Período               | texto    |                                                        0 |
      | Número Máximo de Reprovações na Mesma Disciplina            | texto    |                                                        0 |
      | Número Máximo de Trancamentos                               | texto    |                                                        2 |
      | Número Máximo de Certificações por Período                  | texto    |                                                        4 |
      | Média para Certificação                                     | texto    |                                                       60 |
    E olho e clico no botão "Salvar"
    E olho para a página
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Matriz Curricular
    Define o quantitativo de carga horária exigido para cada tipo de componente e outras configurações. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Matrizes Curriculares" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Matrizes Curriculares"
    Então vejo a página "Matrizes Curriculares"
    Quando clico no botão "Adicionar Matriz Curricular"
    E preencho o formulário com os dados
      | Campo                                         | Tipo         | Valor                                   |
      | Descrição                                     | texto        | Especialização em Educação Profissional |
      | Ano Criação                                   | Autocomplete |                                    2019 |
      | Período Criação                               | lista        |                                       1 |
      | Nível de Ensino                               | Autocomplete | Pós-graduação                           |
      | Ativa                                         | checkbox     | marcar                                  |
      | Data de início                                | data         | 15/03/2019                              |
      | PPP                                           | arquivo      | arquivo.pdf                             |
      | Quantidade de Períodos Letivos                | lista        |                                       2 |
      | Estrutura                                     | Autocomplete | Especialização e Aperfeiçoamento        |
      | Componentes obrigatórios                      | texto        |                                      90 |
      | Componentes optativos                         | texto        |                                       0 |
      | Componentes eletivos                          | texto        |                                       0 |
      | Seminários                                    | texto        |                                       0 |
      | Prática Profissional                          | texto        |                                       0 |
      | Trabalho de Conclusão de Curso                | texto        |                                      30 |
      | Exige TCC                                     | checkbox     | marcar                                  |
      | Atividades complementares                     | texto        |                                       0 |
      | Atividades Teórico-Práticas de Aprofundamento | texto        |                                       0 |
      | Atividades de Extensão                        | texto        |                                       0 |
      | Prática como Componente Curricular            | texto        |                                       0 |
      | Visita Técnica/Aula de Campo                  | texto        |                                       0 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Matriz cadastrada com sucesso. Por favor, vincule os componentes à matriz."

  @do_document
  Cenário: Cadastrar Tipo de Componente
    Utilizado para indicar o tipo de um componente. Ação executada pelo perfil Administrador Acadêmico.

    Dado os cadastros iniciais de tipo de componente
    Quando pesquiso por "Tipos de Componente" e acesso o menu "Ensino::Cadastros Gerais::Tipos de Componente"
    E clico no botão "Adicionar Tipo de Componente"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor |
      | Descrição | Texto | POS   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Componente
    Um componente possui a configuração padrão de uma disciplina. Ação executada pelo perfil Administrador Acadêmico.

    Dado os cadastros iniciais de componente
    Quando pesquiso por "Componentes" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Componentes"
    Então vejo a página "Componentes"
    Quando clico no botão "Adicionar Componente"
    E preencho o formulário com os dados
      | Campo                            | Tipo         | Valor                                   |
      | Descrição                        | texto        | Leitura e Produção de Textos Acadêmicos |
      | Descrição no Diploma e Histórico | texto        | Leitura e Produção de Textos Acadêmicos |
      | Abreviatura                      | texto        | LPTA                                    |
      | Tipo do Componente               | Autocomplete | POS                                     |
      | Diretoria                        | Autocomplete | DIAC/CEN                                |
      | Nível de ensino                  | Autocomplete | Pós-graduação                           |
      | Está ativo                       | checkbox     | marcar                                  |
      | Hora/relógio                     | texto        |                                      45 |
      | Hora/aula                        | texto        |                                      60 |
      | Qtd. de créditos                 | texto        |                                       3 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Núcleo
    Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Núcleos" e acesso o menu "Ensino::Cadastros Gerais::Núcleos"
    E clico no botão "Adicionar Núcleo"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor    |
      | Descrição | Texto | Formação |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Vincular Componente à Matriz Curricular
    Associa os componentes que farão parte da matriz curricular criada. Um componente associado a uma matriz é chamado de componente curricular. Ação executada pelo perfil Administrador Acadêmico.

    Dado os cadastros iniciais de componente curricular
    Quando pesquiso por "Matrizes Curriculares" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Matrizes Curriculares"
    Então vejo a página "Matrizes Curriculares"
    Quando olho a linha "Especialização em Educação Profissional"
    E clico no ícone de exibição
    Então vejo a página "1 - Especialização em Educação Profissional"
    Quando clico na aba "Componentes Curriculares"
    E clico no botão "Vincular Componente"
    Então vejo a página "Vincular Componente de matriz"
    Quando preencho o formulário com os dados
      | Campo           | Tipo         | Valor    |
      | Componente      | autocomplete | POS.0003 |
      | Periodo letivo  | lista        |        1 |
      | Tipo            | lista        | Regular  |
      | Qtd. Avaliações | lista        | Uma      |
      | Núcleo          | Autocomplete | Formação |
    E clico no botão "Vincular Componente"
    Então vejo mensagem de sucesso "Componente de matriz adicionado com sucesso."

  @do_document
  Cenário: Cadastrar Natureza de Participação
    Define a forma como os alunos participam de um curso, por exemplo, presencial ou EAD. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Naturezas de Participação" e acesso o menu "Ensino::Cadastros Gerais::Naturezas de Participação"
    E clico no botão "Adicionar Natureza de Participação"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor      |
      | Descrição | Texto | Presencial |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Área Capes
    Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Áreas Capes" e acesso o menu "Ensino::Cadastros Gerais::Áreas Capes"
    Então vejo a página "Áreas Capes"
    Quando clico no botão "Adicionar Área Capes"
    Então vejo os seguintes campos no formulário
      | Campo     | Tipo  |
      | Descrição | Texto |
    Quando preencho o formulário com os dados
      | Campo     | Tipo  | Valor    |
      | Descrição | Texto | Educação |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Curso
    Cadastro de dados básicos do curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Cursos" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Cursos"
    Então vejo a página "Cursos"
    Quando clico no botão "Adicionar Curso"
    E preencho o formulário com os dados
      | Campo                                   | Tipo         | Valor                                   |
      | Descrição                               | texto        | Especialização em Educação Profissional |
      | Descrição no Diploma e Histórico        | texto        | Especialização em Educação Profissional |
      | Ano letivo                              | Autocomplete |                                    2019 |
      | Período letivo                          | lista        |                                       1 |
      | Data início                             | data         | 15/03/2019                              |
      | Ativo                                   | checkbox     | marcar                                  |
      | Código                                  | texto        |                                   10101 |
      | Natureza de participação                | Autocomplete | Presencial                              |
      | Modalidade de Ensino                    | Autocomplete | Especialização                          |
      | Exige Plano de Ensino                   | checkbox     | marcar                                  |
      | Área Capes                              | Autocomplete | Educação                                |
      | Periodicidade                           | lista        | Semestral                               |
      | Diretoria                               | Autocomplete | DIAC/CEN                                |
      | Certificado/Diploma Emitido pelo Campus | checkbox     | marcar                                  |
      | Fator de Esforço de Curso (FEC)         | texto        |                                       1 |
      | Masculino                               | texto        | Especialista em Educação Profissional   |
      | Feminino                                | texto        | Especialista em Educação Profissional   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Curso cadastrado com sucesso. Por favor, vincule a(s) matriz(es) ao curso."

  @do_document
  Cenário: Vincular Matriz ao Curso
    Vincula uma matriz e seus componentes curriculares a um curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Cursos" e acesso o menu "Ensino::Cursos, Matrizes e Componentes::Cursos"
    E olho a linha "10101"
    E clico no ícone de exibição
    Então vejo a página "10101 - Especialização em Educação Profissional (Campus Central)"
    Quando clico no botão "Vincular Matriz"
    E olho para o popup
    Então vejo a página "Adicionar Matriz"
    Quando preencho o formulário com os dados
      | Campo                | Tipo         | Valor                                                  |
      | Matriz               | autocomplete | Especialização em Educação Profissional                |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Matriz adicionada com sucesso."
