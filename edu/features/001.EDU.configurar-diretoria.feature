# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Configurar Diretoria Acadêmica

  Cenário: Configuração inicial para execução dos cenários do edu
    Quando a data do sistema for "10/03/2019"
    Dado os seguintes usuários
      | Nome                    | Matrícula | Setor    | Lotação  | Email                               | CPF            | Senha | Grupo                   |
      | Administrador Acadêmico |    100001 | DIAC/CEN | DIAC/CEN | administrador_academico@ifrn.edu.br | 730.378.660-04 | abcd  | Administrador Acadêmico |
      | Servidor SA             |    100002 | DIAC/CEN | DIAC/CEN | secretario_academico@ifrn.edu.br    | 601.382.290-58 | abcd  | Servidor                |
      | Servidor DG             |    100003 | DIAC/CEN | DIAC/CEN | diretor_geral@ifrn.edu.br           | 940.209.400-88 | abcd  | Servidor                |
      | Servidor DA             |    100004 | DIAC/CEN | DIAC/CEN | diretor_academico@ifrn.edu.br       | 923.941.200-02 | abcd  | Servidor                |
      | Servidor CC             |    100005 | DIAC/CEN | DIAC/CEN | coordenador_curso@ifrn.edu.br       | 156.763.530-07 | abcd  | Servidor                |
      | Servidor CRA            |    100006 | DIAC/CEN | DIAC/CEN | cra@ifrn.edu.br                     | 153.888.030-07 | abcd  | Servidor                |
      | Servidor P              |    100007 | DIAC/CEN | DIAC/CEN | professor@ifrn.edu.br               | 475.849.400-21 | abcd  | Servidor                |
      | Servidor Op Enade       |    100008 | RAIZ     | RAIZ     | op.enade@ifrn.edu.br                | 330.384.680-45 | abcd  | Servidor                |
      | Servidor DARE           |    100009 | RAIZ     | RAIZ     | dare@ifrn.edu.br                    | 921.158.970-30 | abcd  | Servidor                |
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"

  @do_document
  Cenário: Cadastrar Diretoria Acadêmica
    O cadastro de uma diretoria acadêmica ocorre quando um setor existente no suap é associado como diretoria. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Diretorias Acadêmicas" e acesso o menu "Ensino::Cadastros Gerais::Diretorias Acadêmicas"
    E clico no botão "Adicionar Diretoria Acadêmica"
    E preencho o formulário com os dados
      | Campo                          | Tipo         | Valor              |
      | Setor                          | Autocomplete | DIAC/CEN           |
      | Autoridade Máxima (M)          | texto        | Reitor             |
      | Autoridade Máxima (F)          | texto        | Reitora            |
      | Responsável pela Unidade (M)   | texto        | Diretor Geral      |
      | Responsável pela Unidade (F)   | texto        | Diretora Geral     |
      | Responsável pela Diretoria (M) | texto        | Diretor Acadêmico  |
      | Responsável pela Diretoria (F) | texto        | Diretora Acadêmico |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Vincular Diretor Geral
    Atribui permissões de Diretor Geral a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Quando olho a linha "DIAC/CEN"
    E clico no ícone de exibição
    Então vejo a página "Diretoria Acadêmica - DIAC/CEN"
    Quando clico na aba "Direção"
    E clico no botão "Adicionar Diretor Geral"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo   | Tipo         | Valor       |
      | Usuário | autocomplete | Servidor DG |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Usuário adicionado com sucesso."

  @do_document
  Cenário: Vincular Diretor Acadêmico
    Atribui permissões de Diretor Acadêmico a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Dado a atual página
    Quando clico no botão "Adicionar Diretor Acadêmico"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo   | Tipo         | Valor       |
      | Usuário | autocomplete | Servidor DA |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Usuário adicionado com sucesso."

  @do_document
  Cenário: Vincular Coordenador de Curso
    Atribui permissões de Coordenador de Curso a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Dado a atual página
    Quando clico na aba "Coordenação Acadêmica"
    E clico no botão "Adicionar Coordenador de Curso"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo   | Tipo         | Valor       |
      | Usuário | autocomplete | Servidor CC |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Usuário adicionado com sucesso."

  @do_document
  Cenário: Vincular Secretário Acadêmico
    Atribui permissões de Secretário Acadêmico a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Dado a atual página
    Quando clico na aba "Secretaria Acadêmica"
    E clico no botão "Adicionar Secretário Acadêmico"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo   | Tipo         | Valor       |
      | Usuário | autocomplete | Servidor SA |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Usuário adicionado com sucesso."

  @do_document
  Cenário: Vincular Coordenador de Registros Acadêmicos
    Atribui permissões de Emissor de Diploma a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Dado a atual página
    Quando clico na aba "Formatura/Diplomas"
    E clico no botão "Adicionar Coordenador de Registros Acadêmicos"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo              | Tipo         | Valor        |
      | Servidor           | autocomplete | Servidor CRA |
      | Número da Portaria | texto        | 123/2019     |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Responsável pela Emissão do Diploma cadastrado/atualizado com sucesso."

  @do_document
  Cenário: Cadastrar Diretoria Sistêmica
    Diretoria do tipo Retoria habilita perfis sistêmicos com acesso a todos os campi

    Quando pesquiso por "Diretorias Acadêmicas" e acesso o menu "Ensino::Cadastros Gerais::Diretorias Acadêmicas"
    E clico no botão "Adicionar Diretoria Acadêmica"
    E preencho o formulário com os dados
      | Campo | Tipo         | Valor    |
      | Setor | Autocomplete | RAIZ     |
      | Tipo  | lista        | Sistêmica |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Vincular Diretor de Avaliação e Regulação do Ensino
    Atribui permissões de Diretor de Avaliação e Regulação do Ensino a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Quando olho a linha "RAIZ"
    E clico no ícone de exibição
    Então vejo a página "Sistêmica - RAIZ"
    Quando clico na aba "Direção"
    E clico no botão "Adicionar Diretor de Avaliação e Regulação do Ensino"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo   | Tipo         | Valor         |
      | Usuário | autocomplete | Servidor DARE |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Usuário adicionado com sucesso."

  @do_document
  Cenário: Vincular Operador ENADE
    Atribui permissões de Emissor de Diploma a um usuário. Ação executada pelo perfil Administrador Acadêmico.

    Dado a atual página
    Quando clico na aba "Outras Atividades"
    E clico no botão "Adicionar Operador ENADE"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo   | Tipo         | Valor       |
      | Usuário | autocomplete | Servidor Op |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Usuário adicionado com sucesso."
