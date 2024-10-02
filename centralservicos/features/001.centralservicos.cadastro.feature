# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades ligadas à Central de Serviços
  Essa funcionalidade realiza os cadastros básicos para funcionamento da central de serviços.


  Cenário: Adicionando os usuários necessários para os testes central de serviços
    Dado os seguintes usuários
      | Nome                               | Matrícula | Setor      | Lotação      | Email           | CPF            | Senha | Grupo                              |
      | Administrador da Central           | 104001    | DIAC/CZN   | DIAC/CZN     | d01@ifrn.edu.br | 435.655.546-57 | abcd  | centralservicos Administrador      |
      | Gestor da Central                  | 104002    | DIAC/CZN   | DIAC/CZN     | d01@ifrn.edu.br | 647.115.806-89 | abcd  | Gestor da Central de Serviços      |
      | Responsável Grupo Atendimento      | 104003    | DIAC/CZN   | DIAC/CZN     | d02@ifrn.edu.br | 134.443.481-93 | abcd  | Atendente da Central de Serviços   |
      | Supervisor da Base de Conhecimento | 104004    | DIAC/CZN   | DIAC/CZN     | d02@ifrn.edu.br | 476.733.452-77 | abcd  | Supervisor da Base de Conhecimento |
      | Atendente da Central               | 104005    | DIAC/CZN   | DIAC/CZN     | d02@ifrn.edu.br | 735.785.191-54 | abcd  | Atendente da Central de Serviços   |
      | Servidor da Central                | 104006    | DIAC/CZN   | DIAC/CZN     | d03@ifrn.edu.br | 824.587.211-33 | abcd  | Servidor                           |

  @do_document
  Cenário: O Administrador da Central de Serviços cria uma nova área de atuação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "104001" e senha "abcd"
    E acesso o menu "Administração::Cadastros::Áreas de Atuação"
    Então vejo a página "Áreas de Atuação"
    E vejo mensagem de alerta "Nenhum Área de Atuação encontrado."
    Quando clico no botão "Adicionar Área de Atuação"
    Então vejo a página "Adicionar Área de Atuação"
    E vejo os seguintes campos no formulário
      | Campo   | Tipo     |
      | Nome    | Texto    |
      | Ícone   | Texto    |
      | Ativo?  | Checkbox |
    E vejo o botão "Salvar"
    Quando clico no botão "Salvar"
    Então vejo mensagem de erro "Por favor corrija o erro abaixo"
    E vejo os seguintes erros no formulário
      | Campo   | Tipo     | Mensagem                 |
      | Nome    | Texto    | Este campo é obrigatório |
    Quando preencho o formulário com os dados
      | Campo   | Tipo     | Valor                       |
      | Nome    | Texto    | Tecnologia da Informação    |
      | Ícone   | Texto    | list                        |
      | Ativo?  | Checkbox | Marcar                      |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: O Administrador da Central de Serviços vincula a área ao gestor
    Dado acesso a página "/"
    Quando acesso o menu "Central de Serviços::Cadastros::Gestores das Áreas de Serviços"
    Então vejo a página "Gestores das Áreas dos Serviços"
    E vejo mensagem de alerta "Nenhum Gestor da Área do Serviço encontrado."
    Quando clico no botão "Adicionar Gestor da Área do Serviço"
    Então vejo a página "Adicionar Gestor da Área do Serviço"
    Quando preencho o formulário com os dados
      | Campo               | Tipo            | Valor                         |
      | Gestor              | Autocomplete    | 104002                        |
      | Área do Serviço     | Autocomplete    | Tecnologia da Informação      |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: O Gestor da Central de Serviços cria uma categoria de serviço
    Dado acesso a página "/"
    Quando realizo o login com o usuário "104002" e senha "abcd"
    E acesso o menu "Central de Serviços::Cadastros::Serviços::Categorias de Serviço"
    Então vejo a página "Categorias de Serviço"
    E vejo mensagem de alerta "Nenhum Categoria de Serviço encontrado."
    Quando clico no botão "Adicionar Categoria de Serviço"
    Então vejo a página "Adicionar Categoria de Serviço"
    Quando preencho o formulário com os dados
      | Campo               | Tipo         | Valor                       |
      | Nome                | Texto        | Equipamentos                |
      | Área do Serviço     | Autocomplete | Tecnologia da Informação    |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: O Gestor da Central de Serviços cria um grupo de serviço
    Dado acesso a página "/"
    Quando acesso o menu "Central de Serviços::Cadastros::Serviços::Grupos de Serviço"
    Então vejo a página "Grupos de Serviço"
    E vejo mensagem de alerta "Nenhum Grupo de Serviço encontrado."
    Quando clico no botão "Adicionar Grupo de Serviço"
    Então vejo a página "Adicionar Grupo de Serviço"
    Quando preencho o formulário com os dados
      | Campo            | Tipo                  | Valor                                              |
      | Nome             | Texto                 | Impressora / Scanner                               |
      | Detalhamento     | TextArea              | Serviço de impressão e digitalização de documentos |
      | Categorias       | Autocomplete Multiplo | Equipamentos                                       |
      | Ícone            | Texto                 | list                                               |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: O Gestor da Central de Serviços cria um Centro de Atendimento
    Dado acesso a página "/"
    Quando acesso o menu "Central de Serviços::Cadastros::Atendimento::Centros de Atendimento"
    Então vejo a página "Centros de Atendimento"
    E vejo mensagem de alerta "Nenhum Centro de Atendimento encontrado."
    Quando clico no botão "Adicionar Centro de Atendimento"
    Então vejo a página "Adicionar Centro de Atendimento"
    Quando preencho o formulário com os dados
      | Campo                         | Tipo            | Valor                     |
      | Nome                          | Texto           | Local                     |
      | Centro de Atendimento Local?  | Checkbox        | Marcar                    |
      | Área do Serviço               | Autocomplete    | Tecnologia da Informação  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: O Gestor da Central de Serviços cria um Grupo de Atendimento
    Dado acesso a página "/"
    Quando acesso o menu "Central de Serviços::Cadastros::Atendimento::Grupos de Atendimento"
    Então vejo a página "Grupos de Atendimento"
    E vejo mensagem de alerta "Nenhum Grupo de Atendimento encontrado."
    Quando clico no botão "Adicionar Grupo de Atendimento"
    Então vejo a página "Adicionar Grupo de Atendimento"
    Quando preencho o formulário com os dados
      | Campo                          | Tipo                  | Valor                      |
      | Campus                         | AutoComplete          | RAIZ                         |
      | Centro de Atendimento          | Autocomplete          | Local                      |
      | Nome                           | Texto                 | COINRE - Nível 1 - Suporte |
      | Responsáveis                   | Autocomplete Multiplo | 104003                     |
      | Atendentes Vinculados ao Grupo | Autocomplete Multiplo | 104005                     |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  Esquema do Cenário: Adiciona <Login> como atendente vinculados ao Grupo de Atendimento Local
    Dada a atual página
    Quando clico no link "Editar"
    Então vejo a página "Editar COINRE - Nível 1 - Suporte"
    Quando preencho o formulário com os dados
      | Campo                          | Tipo                    | Valor                        |
      | Atendentes Vinculados ao Grupo | Autocomplete Multiplo   | <Login>                      |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."
    Exemplos:
      | Login  |
      | 104002 |
      | 104004 |

  @do_document
  Cenário: O Gestor da Central de Serviços cria um Serviço
    Dado acesso a página "/"
    Quando acesso o menu "Central de Serviços::Cadastros::Serviços::Serviços"
    Então vejo a página "Serviços"
    E vejo mensagem de alerta "Nenhum Serviço encontrado."
    Quando clico no botão "Adicionar Serviço"
    Então vejo a página "Adicionar Serviço"
    Quando preencho o formulário com os dados
      | Campo                                     | Tipo         | Valor                                                             |
      | Nome                                      | Texto        | Informar problema de Impressora/Scanner                           |
      | Tipo                                      | Lista        | Incidente                                                         |
      | Área do Serviço                           | Lista        | Tecnologia da Informação                                          |
      | Centros de Atendimento                    | Autocomplete Multiplo        | Local                                                             |
      | Grupo de Serviço                          | Autocomplete | Impressora / Scanner                                              |
      | Informações para preenchimento do chamado | TextArea     | Por favor, informar o número do equipamento impresso na etiqueta. |
      | SLA (em horas)                            | Texto        | 12                                                                |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Servidor abre um chamado na Central de Serviços
    Dado acesso a página "/"
    Quando realizo o login com o usuário "104006" e senha "abcd"
    E acesso o menu "Central de Serviços::Abrir Chamado"
    Então vejo a página "Listar Áreas do Serviço"
    Quando clico no link "Tecnologia da Informação" na listagem das áreas
    Então vejo a página "Abrir Chamado para Tecnologia da Informação"
    Quando clico no link "Informar problema de Impressora/Scanner"
    Então vejo a página "Informar problema de Impressora/Scanner"
    E vejo os seguintes campos no formulário
      | Campo                 | Tipo         |
      | Descrição             | TextArea     |
      | Campus                | Lista        |
      | Centro de Atendimento | Radio        |
    E vejo o botão "Confirmar"
    Quando clico no botão "Confirmar"
    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
    E vejo os seguintes erros no formulário
      | Campo                 | Tipo         | Mensagem                 |
      | Descrição             | TextArea     | Este campo é obrigatório |
    Quando preencho o formulário com os dados
      | Campo         | Tipo        | Valor                                              |
      | Descrição     | TextArea    | Impressora da sala dos servidores com problema.    |
    E clico no botão "Confirmar"
    Então vejo mensagem de sucesso "Chamado aberto com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: O Gestor da Central de Serviços cria um artigo para a Base de Conhecimento
    Dado acesso a página "/"
    Quando realizo o login com o usuário "104002" e senha "abcd"
    E acesso o menu "Central de Serviços::Base de Conhecimentos"
    Então vejo a página "Listar Áreas do Serviço"
    Quando clico no link "Tecnologia da Informação" na listagem das áreas
    Então vejo a página "Base de Conhecimentos: Tecnologia da Informação"
    E vejo mensagem de alerta "Nenhum registro foi encontrado."
    Quando clico no botão "Visualizar Todos"
    Então vejo a página "Bases de Conhecimento"
    E vejo mensagem de alerta "Nenhum Base de Conhecimento encontrado."
    Quando clico no botão "Adicionar Base de Conhecimento"
    Então vejo a página "Adicionar Base de Conhecimento"
    Quando preencho o formulário com os dados
      | Campo           | Tipo     | Valor                                                                |
      | Área do Serviço | Lista    | Tecnologia da Informação                                             |
      | Título          | Texto    | Atolamento de papel                                                  |
      | Resumo          | TextArea | Usuário reclama que a impressora está indicando atolamento de papel. |
      | Ativo?          | Checkbox | Marcar                                                               |
      | Visibilidade    | Lista    | Privada                                                            |
      | Solução         | Texto Rico | Verificar e remover o papel atolado da impressora.                 |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: O Atendente da Central de Serviços Atende um Chamado
    Dado acesso a página "/"
    Quando realizo o login com o usuário "104005" e senha "abcd"
    E acesso o menu "Central de Serviços::Dashboard"
    Então vejo a página "Dashboard"
        E vejo o indicador "Não Atribuídos" com o valor "1"
    Quando clico no indicador "Não Atribuídos"
    Então vejo a página "Chamados"
    Quando clico no link "INC #1"
    Então vejo a página "Chamado 1"
    Quando clico no botão "Assumir"
    Então vejo mensagem de sucesso "Atribuição realizada com sucesso."
    Quando clico no botão "Alterar para Em Atendimento"
    Então vejo mensagem de sucesso "Alteração de situação realizada com sucesso."
    Quando clico na aba "Artigos Relacionados"
    E seleciono o custom checkbox "Atolamento de papel"
    E preencho o formulário com os dados
      | Campo           | Tipo     | Valor                                                                |
      | Comentário      | TextArea | Chamado resolvido com a remoção do papel preso na bandeja            |
    E olho para a aba "Artigos Relacionados"
    E clico no botão "Alterar para Resolvido"
    Então vejo mensagem de sucesso "Alteração de situação realizada com sucesso."
