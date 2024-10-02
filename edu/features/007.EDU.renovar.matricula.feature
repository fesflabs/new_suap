# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Configurar Renovação de Matrícula

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado os cadastros da funcionalidade 001
    E os cadastros da funcionalidade 002
    E os cadastros da funcionalidade 003
    E os cadastros da funcionalidade 004
    E os cadastros da funcionalidade 005
    E os cadastros da funcionalidade 006
    E acesso a página "/"
    Quando realizo o login com o usuário "100002" e senha "abcd"
    E a data do sistema for "20/07/2019"

  Cenário: Gerar Turmas e Diários
    Cria as turmas de um curso para os períodos letivos de um campus. Ação executada pelo perfil Secretário Acadêmico.

    Quando pesquiso por "Turmas" e acesso o menu "Ensino::Turmas e Diários::Turmas"
    E clico no botão "Gerar Turmas"
    E preencho o formulário com os dados
      | Campo                | Tipo         | Valor                                   |
      | Ano Letivo           | lista        |                                    2019 |
      | Período Letivo       | lista        |                                       2 |
      | Tipo dos Componentes | lista        | Obrigatório                             |
      | Matriz/Curso         | autocomplete | Especialização em Educação Profissional |
    E clico no botão "Continuar"
    E olho para o quadro "1º Período"
    E preencho o formulário com os dados
      | Campo        | Tipo  | Valor    |
      | Nº de Turmas | lista |        1 |
      | Turno        | lista | Matutino |
      | Nº de Vagas  | texto |       10 |
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
      | Campo                | Tipo  | Valor                                                       |
      | Horário do Campus    | lista | Horário Padrão [Aula 45min] (CEN)                           |
      | Calendário Acadêmico | lista | [1] Calendário Acadêmico Especialização 2019.2 - CEN/2019.2 |
    E olho para o quadro "Seleção de Componentes"
    E seleciono o item "POS.0003 - Leitura e Produção de Textos Acadêmicos - Pós-graduação [45 h/60 Aulas]" da lista
    E seleciono o item "POS.0002 - Elaboração do Trabalho de Conclusão de Curso - Pós-graduação [30 h/45 Aulas]" da lista
    E olho para a página
    E clico no botão "Continuar"
    Então vejo o texto "As seguintes turmas e diários serão criados/atualizados ao final da operação. Caso tenha certeza que deseja criá-los/atualizá-los, marque o checkbox de confirmação no final da página e submeta o formulário."
    Quando preencho o formulário com os dados
      | Campo       | Tipo     | Valor  |
      | Confirmação | checkbox | marcar |
    E clico no botão "Finalizar"
    Então vejo mensagem de sucesso "Turmas geradas com sucesso."

  @do_document
  Cenário: Configurar Renovação de Matrícula
    Quando pesquiso por "Renovação de Matrícula" e acesso o menu "Ensino::Procedimentos de Apoio::Renovação de Matrícula"
    E clico no botão "Adicionar Renovação de Matrícula"
    E preencho o formulário com os dados
      | Campo          | Tipo              | Valor            |
      | Descrição      | texto             | Renovação 2019.2 |
      | Ano Letivo     | autocomplete      |             2019 |
      | Período Letivo | lista             |                2 |
      | Data de Início | Data             | 21/07/2019       |
      | Data de Fim    | Data             | 21/07/2019       |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso. Adicione os cursos para os quais os pedidos serão realizados."
    Quando clico na aba "Cursos"
    E clico no botão "Adicionar Cursos"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo        | Tipo                  | Valor |
      | Novos cursos | autocomplete multiplo | 10101 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Curso(s) adicionado(s) com sucesso."

  Cenário: Autenticar como Aluno
    Quando a data do sistema for "21/07/2019"
    E altero a senha do aluno "20191101010001" para "123"
    E acesso o menu "Sair"
    E realizo o login com o usuário "20191101010001" e senha "123"

  @do_document
  Cenário: Realizar Pedido de Matrícula
    Quando clico no link "Faça sua matrícula online"
    E seleciono o item "POS.0002" da lista
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Pedido de matrícula salvo com sucesso."

  Cenário: Autenticar como Secretário Acadêmico
    Quando a data do sistema for "22/07/2019"
    E acesso o menu "Sair"
    E realizo o login com o usuário "100002" e senha "abcd"

  @do_document
  Cenário: Processar Pedidos de Matrícula
    Quando pesquiso por "Renovação de Matrícula" e acesso o menu "Ensino::Procedimentos de Apoio::Renovação de Matrícula"
    E olho a linha "Renovação 2019.2"
    E clico no ícone de exibição
    E clico no botão "Processar Pedidos de Matrícula"
    Então vejo mensagem de sucesso "Pedidos de matrícula processados com sucesso."
    
    