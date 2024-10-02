# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Executar Período Letivo
  Professor vinculado ao diário configura formas de avaliação do aluno e lança aulas, faltas e notas.

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado os cadastros da funcionalidade 001
    E os cadastros da funcionalidade 002
    E os cadastros da funcionalidade 003
    E os cadastros da funcionalidade 004
    E acesso a página "/"
    Quando realizo o login com o usuário "100007" e senha "abcd"
    E a data do sistema for "10/03/2019"
    E acesso a página "/"

  @do_document
  Cenário: Acessar Planos de Ensino
    O professor visualiza todos os seus planos de ensino agrupados.

    Quando olho para o quadro "Professores"
    E clico no botão "Planos de Ensino"
    Então vejo a página "Planos de Ensino"
    Quando olho a linha "POS.0001"
    E clico no ícone de edição
    Quando preencho o formulário com os dados
      | Campo                  | Tipo     | Valor                                                                                           |
      | Ementa                 | Textarea |A origem e a formação da língua portuguesa. O latim clássico e o latim vulgar.                   |
      | Justificativa          | Textarea |Análise dos efeitos das mudanças culturais, científicas e tecnológicas na Educação e na Didática.|
      | Objetivo Geral         | Textarea |A evolução fonológica, morfológica, sintática e semântica. A constituição do léxico.             |
      | Objetivos Específicos  | Textarea |A expansão da língua portuguesa.                                                                 |
      | Conteúdo Programático  | Textarea |Estudo da interdependência dos elementos constitutivos das situações de ensino e de aprendizagem.|
      | Metodologia            | Textarea |Estudo dos objetivos educacionais como norteadores da ação educativa.                            |
      | Informações Adicionais | Textarea |Apresentação da disciplina                                                                       |
    E preencho as linhas do quadro "Referências Bibliográfica Básica" com os dados
      | Referência:Texto | Disponível na Biblioteca:radio |
      | 82192            | Sim                            |
    E preencho as linhas do quadro "Referências Bibliográfica Complementar" com os dados
      | Referência:Texto | Disponível na Biblioteca:radio |
      | 93832            | Não                            |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Acessar Diários
    O professor visualiza todos os seus diários agrupados por período letivo.

    Quando pesquiso por "Meus Diários" e acesso o menu "Ensino::Turmas e Diários::Meus Diários"
    E olho para os filtros
    E preencho o formulário com os dados
      | Campo               | Tipo  | Valor  |
      | Filtrar por período | lista | 2019.1 |
    E olho para a página
    E clico no botão "Acessar Diário"
    Então vejo a página "POS.0001"

  @do_document
  Cenário: Configurar Forma de Avaliação
    O professor pode customizar a quantidade de avaliações e a forma de cálculo da média para cada etapa do diário.

    Quando clico no botão "Editar Configuração de Avaliação"
    E preencho as linhas do quadro "Horários das Aulas" com os dados
      | Tipo:lista | Sigla:texto | Descrição:texto | Data:data  |
      | Seminário  | S1          | Avaliação final | 20/07/2019 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Registrar Aula
    A quantidade de aulas registradas pelo professor é contabilizada no cálculo de carga horária exigido no componente curricular do diário.

    Quando a data do sistema for "21/03/2019"
    E clico na aba "Registro de Aulas"
    E olho e clico no botão "Adicionar Aula"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo      | Tipo     | Valor                      |
      | Quantidade | texto    |                         60 |
      | Etapa      | lista    | Primeira                   |
      | Data       | Data     | 20/03/2019                 |
      | Conteúdo   | textarea | Apresentação da disciplina |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Aula cadastrada/atualizada com sucesso."

  @do_document
  Cenário: Lançar Faltas
    A quantidade de faltas que pode ser lançada em um dia de aula é limitado pela quantidade de aulas cadastrada nesse dia.

    Quando clico na aba "Registro de Faltas"
    E olho para o quadro "Registro de Faltas"

  @do_document
  Cenário: Entregar Etapa sem Lançamento de Notas
    O sistema exige do professor a confirmação de que deseja entregar a etapa com alunos que ainda estão sem nota lançada.

    Quando clico no botão "Entregar Etapa 1"
    E olho para o popup
    E clico no botão "Confirmar Entrega"
    E olho para a página
    Então vejo mensagem de erro "A etapa só pode ser entregue quando todas as notas forem lançadas."
    Quando clico no botão "Entregar Etapa 1"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo                      | Tipo     | Valor  |
      | Confirmar entrega sem nota | checkbox | marcar |
    E clico no botão "Confirmar Entrega"
    E olho para a página
    Então vejo mensagem de sucesso "Etapa entregue com sucesso."

  @do_document
  Cenário: Solicitar Relançamento de Etapa
    O professor não pode modificar as aulas, faltas e notas lançadas após entrega da etapa. Para realizar alguma mudança é necessário solicitar o relançamento da etapa.

    Quando clico no botão "Solicitar Relançamento da Etapa 1"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo  | Tipo     | Valor                         |
      | Motivo | textarea | Faltou lançar a nota do aluno |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail."

  Cenário: Autenticar como secretário acadêmico
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100002" e senha "abcd"

  @do_document
  Cenário: Avaliar Solicitação de Relançamento de Etapa
    O secretário acadêmico é notificado da solicitação do professor e pode deferir ou indeferir a solicitação do relançamento.

    Quando pesquiso por "Solicitações de Usuários" e acesso o menu "Ensino::Procedimentos de Apoio::Solicitações de Usuários"
    E olho a linha "Relançamento da etapa 1"
    E clico no ícone de exibição
    E clico no botão "Deferir"
    Então vejo mensagem de sucesso "Solicitação deferida com sucesso."

  Cenário: Autenticar como professor
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100007" e senha "abcd"

  @do_document
  Cenário: Acessar diário (dashboard)
    Esta disponível na tela inicial do SUAP acesso rápido às principais funcionalidades utilizadas pelo professor.

    Quando olho para o quadro "Professores"
    E clico no botão "Meus Diários"
    E clico no botão "Acessar Diário"
    Então vejo a página "POS.0001"

  @do_document
  Cenário: Lançar Notas
    Dado a atual página
    Quando clico na aba "Registro de Notas/Conceitos"
    E olho para o quadro "Registro de Notas"
    Dado acesso a página "/edu/registrar_nota_ajax/1/70"

  @do_document
  Cenário: Entregar Etapa
    O professor, após concluir lançamento de notas, aulas e faltas, entrega a etapa do diário

    Quando a data do sistema for "20/07/2019"
    Dado acesso a página "/"
    Quando olho para o quadro "Professores"
    E clico no botão "Meus Diários"
    E clico no botão "Acessar Diário"
    E clico no botão "Entregar Etapa 1"
    E olho para o popup
    E clico no botão "Confirmar Entrega"
    E olho para a página
    Então vejo mensagem de sucesso "Etapa entregue com sucesso."
