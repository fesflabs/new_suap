# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Formar Aluno

  Cenário: Configuração inicial para execução dos cenários do EDU
    Dado os cadastros da funcionalidade 001
    E os cadastros da funcionalidade 002
    E os cadastros da funcionalidade 003
    E os cadastros da funcionalidade 004
    E os cadastros da funcionalidade 005
    E os cadastros da funcionalidade 006
    E os cadastros da funcionalidade 007

  Cenário: Autenticar como Secretário Acadêmico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100002" e senha "abcd"
    E a data do sistema for "22/07/2019"

  Cenário: Configurar Diário 3
    Na configuração do diário é informado local e horário da aula e o(s) professor(es) que ministrarão as aulas. Ação executada pelo perfil Secretário Acadêmico.

    Dado acesso a página "/"
    Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
    E olho a linha "POS.0002"
    E clico no ícone de exibição
    Então vejo a página "Diário (4) - POS.0002"
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
    E olho e clico no botão "Definir Horário"
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

  Cenário: Alterar Posse do Diário 2
    Dado acesso a página "/"
    Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
    E olho a linha "POS.0002"
    E clico no ícone de exibição
    E clico no link "Transferir para o Registro"
    Então vejo mensagem de sucesso "Posse transferida com sucesso."
    Quando olho para a página
    E clico no link "Transferir para o Registro"
    Então vejo mensagem de sucesso "Posse transferida com sucesso."

  Cenário: Registrar Aula (Em posse do registro) 2
    Dado acesso a página "/"
    Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
    E olho a linha "POS.0002"
    E clico no ícone de exibição
    E clico no link "Registrar Aula/Falta"
    Quando clico no botão "Adicionar Aula"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo      | Tipo     | Valor                      |
      | Quantidade | texto    |                         45 |
      | Etapa      | lista    | Primeira                   |
      | Data       | Data     | 21/08/2019                 |
      | Conteúdo   | textarea | Apresentação da disciplina |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Aula cadastrada/atualizada com sucesso."

  Cenário: Lançar Nota (Em posse do registro) 2
    Dado acesso a página "/"
    Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
    E olho a linha "POS.0002"
    E clico no ícone de exibição
    E clico na aba "Registro de Notas/Conceitos"
    Dado acesso a página "/edu/registrar_nota_ajax/5/75"
    Dado acesso a página "/"

  @do_document
  Cenário: Cadastrar TCC
    Dado acesso a página "/"
    Quando pesquiso por "Alunos" e acesso o menu "Ensino::Alunos e Professores::Alunos"
    E olho a linha "20191101010001"
    E clico no ícone de exibição
    E clico na aba "TCC / Relatórios"
    E olho para o quadro "Trabalhos de Conclusão de Curso / Relatórios"
    E clico no botão "Adicionar"
    E preencho o formulário com os dados
      | Campo              | Tipo         | Valor       |
      | Ano Letivo         | lista        |        2019 |
      | Período Letivo     | lista        |           2 |
      | Título do Trabalho | texto        | Meu TCC Pós |
      | Resumo do Trabalho | textarea     | lorem lorem |
      | Tipo de Trabalho   | lista        | Monografia  |
      | Orientador         | autocomplete | 100007      |
      | Presidente         | autocomplete | 100007      |
      | Defesa Online      | checkbox     | marcar      |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "TCC / Relatório adicionado com sucesso."

  Cenário: Sair do sistema
    Quando acesso o menu "Sair"

  Cenário: Autenticar como Aluno
    Dado acesso a página "/"
    Quando realizo o login com o usuário "20191101010001" e senha "123"

  @do_document
  Cenário: Consultar Dados Acadêmicos
    Dado acesso a página "/"
    Quando clico no link "João Silva"
    E clico na aba "Requisitos de Conclusão"
    E clico na aba "Histórico"
    E clico na aba "Boletins"
    E clico na aba "Dados Acadêmicos"

  Cenário: Sair do sistema
    Quando acesso o menu "Sair"

  Cenário: Autenticar como Administrador Acadêmico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"

  @do_document
  Cenário: Cadastrar Modelo de Documento
    Dado acesso a página "/"
    Quando pesquiso por "Modelos de Documentos" e acesso o menu "Ensino::Diplomas e Certificados::Modelos de Documentos"
    E clico no botão "Adicionar Modelo de Documento"
    E preencho o formulário com os dados
      | Campo                | Tipo         | Valor               |
      | Descrição            | Texto        | Diploma Pós         |
      | Tipo                 | Lista        | DIPLOMA/CERTIFICADO |
      | Modalidade de Ensino | autocomplete | Especialização      |
      | Template             | Arquivo      | diploma-pos.docx    |
      | Ativo                | Checkbox     | marcar              |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Configurar Livro
    Dado acesso a página "/"
    Quando pesquiso por "Configurar Livros" e acesso o menu "Ensino::Diplomas e Certificados::Configurar Livros"
    E clico no botão "Adicionar Configuração de Livro de Registros"
    E preencho o formulário com os dados
      | Campo                 | Tipo                  | Valor                 |
      | Descrição             | texto                 | Livro de Registro Pós |
      | Campus                | autocomplete          | CEN                   |
      | Modalidades de Ensino | autocomplete multiplo | Especialização        |
      | Nº do Livro Atual     | texto                 |                     1 |
      | Folhas por Livro      | texto                 |                   200 |
      | Nº da Folha Atual     | texto                 |                     1 |
      | Nº do Registro Atual  | texto                 |                     1 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Fechar Período
    Dado acesso a página "/"
    Quando pesquiso por "Fechar Período" e acesso o menu "Ensino::Procedimentos de Apoio::Fechar Período"
    E preencho o formulário com os dados
      | Campo          | Tipo              | Valor            |
      | Ano Letivo     | lista             |             2019 |
      | Período Letivo | lista             |                2 |
      | Tipo           | checkbox multiplo | Por Turma        |
      | Turma          | autocomplete      | 20192.2.10101.1M |
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo      | Tipo     | Valor  |
      | Confirmado | checkbox | marcar |
    E clico no botão "Finalizar"
    Então vejo mensagem de sucesso "Período fechado com sucesso."

  Cenário: Sair do sistema
    Quando acesso o menu "Sair"

  Cenário: Autenticar como Coordenador de Registros Acadêmicos
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100006" e senha "abcd"

  @do_document
  Cenário: Emitir Registro de Emissão de Diploma
    Dado acesso a página "/"
    Quando pesquiso por "Emitir Diploma" e acesso o menu "Ensino::Diplomas e Certificados::Emitir Diploma"

  #        E preencho o formulário com os dados
  #            | Campo | Tipo         | Valor |
  #            | Aluno | autocomplete | 20191101010001 |
  #		E clico no botão "Continuar"
  #		E preencho o formulário com os dados
  #           | Campo | Tipo         | Valor |
  #            | Nome da Pasta | autocomplete | Livro |
  #        E clico no botão "Salvar"
  #        Então vejo mensagem de sucesso "Registro de emissão de diploma cadastrado com sucesso."
  @do_document
  Cenário: Imprimir Diploma
    Dado acesso a página "/"
    Quando pesquiso por "Registros de Emissão" e acesso o menu "Ensino::Diplomas e Certificados::Registros de Emissão"
