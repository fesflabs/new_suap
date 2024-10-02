# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Configurar Turmas e Diários

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado os cadastros da funcionalidade 001
    E os cadastros da funcionalidade 002
    E acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"
    E a data do sistema for "10/03/2019"

  @do_document
  Cenário: Pré-Cadastro: Turno
    Cadastra os turnos de aula da institição. Ação executada pelo perfil Administrador Acadêmico.

    Dado os cadastros iniciais de turno
    Quando pesquiso por "Turnos" e acesso o menu "Ensino::Cadastros Gerais::Turnos"
    E clico no botão "Adicionar Turno"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor   |
      | Descrição | Texto | Noturno |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Pré-Cadastro: Horário do Campus
    Cadastra os horários de aula de um campus. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Horário do Campus" e acesso o menu "Ensino::Procedimentos de Apoio::Horário do Campus"
    E clico no botão "Adicionar Horário do Campus"
    Quando preencho o formulário com os dados
      | Campo          | Tipo         | Valor                       |
      | Descrição      | Texto        | Horário Padrão [Aula 45min] |
      | Campus         | Autocomplete | CEN                         |
      | Ativo          | Checkbox     | marcar                      |
      | Horário Padrão | Checkbox     | marcar                      |
    E preencho as linhas do quadro "Horários das Aulas" com os dados
      | Número:lista | Turno:lista | Início:texto | Término:texto |
      |            1 | Matutino    | 7:00         | 7:45          |
      |            2 | Matutino    | 7:50         | 8:35          |
      |            3 | Matutino    | 8:40         | 9:25          |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Pré-Cadastro: Tipo de Professor
    Cadastra os tipos de vínculo que um professor pode ter no diário. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Tipos de Professor em Diário" e acesso o menu "Ensino::Cadastros Gerais::Tipos de Professor em Diário"
    E clico no botão "Adicionar Tipo de Professor em Diário"
    Então vejo os seguintes campos no formulário
      | Campo     | Tipo  |
      | Descrição | Texto |
    Quando preencho o formulário com os dados
      | Campo     | Tipo  | Valor     |
      | Descrição | Texto | Principal |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Autenticar como Secretário Acadêmico
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100002" e senha "abcd"

  @do_document
  Cenário: Cadastrar Calendário Acadêmico
    Cadastra os eventos acadêmicos de um período/ano letivo de um campus podendo existir mais de um calendário por campus. Ação executada pelo perfil Secretário Acadêmico.

    Dado os cadastros iniciais de calendário acadêmico
    Quando pesquiso por "Calendários Acadêmicos" e acesso o menu "Ensino::Procedimentos de Apoio::Calendários Acadêmicos"
    E clico no botão "Adicionar Calendário Acadêmico"
    E preencho o formulário com os dados
      | Campo                         | Tipo              | Valor                                      |
      | Descrição                     | texto             | Calendário Acadêmico Especialização 2019.1 |
      | Campus                        | lista             | CEN                                        |
      | Diretoria                     | lista             | DIAC/CEN                                   |
      | Tipo                          | lista             | Semestral                                  |
      | Ano letivo                    | Autocomplete      |                                       2019 |
      | Período letivo                | lista             |                                          1 |
      | Início das Aulas              | data              | 20/03/2019                                 |
      | Término das Aulas             | data              | 18/07/2019                                 |
      | Data de Fechamento do Período | data              | 19/07/2019                                 |
      | Qtd etapas                    | checkbox multiplo | Etapa Única                                |
    E olho para o quadro "Primera Etapa"
    E preencho o formulário com os dados
      | Campo  | Tipo | Valor      |
      | Início | data | 20/03/2019 |
      | Fim    | data | 18/07/2019 |
    E olho para a página
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Gerar Turmas e Diários
    Cria as turmas de um curso para um período letivo de um campus. Ação executada pelo perfil Secretário Acadêmico.

    Quando pesquiso por "Turmas" e acesso o menu "Ensino::Turmas e Diários::Turmas"
    E clico no botão "Gerar Turmas"
    Quando preencho o formulário com os dados
      | Campo                | Tipo         | Valor                                   |
      | Ano Letivo           | lista        |                                    2019 |
      | Período Letivo       | lista        |                                       1 |
      | Tipo dos Componentes | lista        | Obrigatório                             |
      | Matriz/Curso         | autocomplete | Especialização em Educação Profissional |
    E clico no botão "Continuar"
    E olho para o quadro "1º Período"
    E preencho o formulário com os dados
      | Campo        | Tipo  | Valor    |
      | Nº de Turmas | lista |        1 |
      | Turno        | lista | Matutino |
      | Nº de Vagas  | texto |       10 |
    E olho para a página
    E clico no botão "Continuar"
    E olho para o quadro "Horário/Calendário e Componentes"
    E preencho o formulário com os dados
      | Campo                | Tipo  | Valor                                                       |
      | Horário do Campus    | lista | Horário Padrão [Aula 45min] (CEN)                           |
      | Calendário Acadêmico | lista | [3] Calendário Acadêmico Especialização 2019.1 - CEN/2019.1 |
    E olho para o quadro "Seleção de Componentes"
    E seleciono o item "POS.0003 - Leitura e Produção de Textos Acadêmicos - Pós-graduação [45 h/60 Aulas]" da lista
    E seleciono o item "POS.0001 - Didática da Educação Profissional - Pós-graduação [45 h/60 Aulas]" da lista
    E olho para a página
    E clico no botão "Continuar"
    Então vejo o texto "As seguintes turmas e diários serão criados/atualizados ao final da operação. Caso tenha certeza que deseja criá-los/atualizá-los, marque o checkbox de confirmação no final da página e submeta o formulário."
    Quando preencho o formulário com os dados
      | Campo       | Tipo     | Valor  |
      | Confirmação | checkbox | marcar |
    E clico no botão "Finalizar"
    Então vejo mensagem de sucesso "Turmas geradas com sucesso."

  @do_document
  Cenário: Configurar Diário
    Na configuração do diário é informado local e horário da aula e o(s) professor(es) que ministrarão as aulas. Ação executada pelo perfil Secretário Acadêmico.

    Dado os cadastros iniciais de prédio
    E os cadastros iniciais de sala
    E as configurações iniciais de diário
    Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
    E olho a linha "POS.0001"
    E clico no ícone de exibição
    Então vejo a página "Diário (1) - POS.0001"
    Quando clico na aba "Dados Gerais"
    E olho e clico no botão "Definir Local"
    E olho para o popup
    Então vejo a página "Definir Local de Aula"
    Quando preencho o formulário com os dados
      | Campo | Tipo         | Valor    |
      | Sala  | autocomplete | Sala 101 |
    E clico no botão "Salvar"
    E olho para a página
    Então vejo mensagem de sucesso "Local definido com sucesso."
    Quando clico na aba "Dados Gerais"
    Dado os horários de aula "1M1,1M2" do diário "1"
    Quando olho e clico no botão "Definir Horário"
    E olho para o popup
    Então vejo a página "Definir Horário de Aula"
    Quando clico no botão "Salvar"
    E olho para a página
    Então vejo mensagem de sucesso "Horário definido com sucesso."
    Quando clico na aba "Dados Gerais"
    E olho e clico no botão "Adicionar Professor"
    E olho para o popup
    Então vejo a página "Adicionar Professor"
    Quando preencho o formulário com os dados
      | Campo                       | Tipo         | Valor      |
      | Professor                   | autocomplete | 100007     |
      | Tipo                        | autocomplete | Principal  |
      | Percentual da Carga Horária | texto        |        100 |
    E clico no botão "Salvar"
    E olho para a página
    Então vejo mensagem de sucesso "Professor adicionado/atualizado com sucesso."
