# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Fluxo básico do Processo Eletrônico

  Cenário: Adicionando os usuários necessários para os testes PROCESSO ELETRONICO
    Dado os seguintes usuários
      | Nome                   | Matrícula | Setor | Lotação | Email                 | CPF            | Senha | Grupo                           |
      | Operador de Processo 1 | 128001    | A1    | A1      | operador@ifrn.edu.br  | 645.433.195-40 | abcd  | Operador de Processo Eletrônico |
      | Chefe de Setor         | 128002    | A1    | A1      | chefe@ifrn.edu.br     | 723.739.490-83 | abcd  | Chefe de Setor                  |
      | Operador de Processo 2 | 128003    | A2    | A2      | operador2@ifrn.edu.br | 249.102.450-06 | abcd  | Operador de Processo Eletrônico |
      | Chefe de Setor 2       | 128004    | A2    | A2      | chefe2@ifrn.edu.br    | 881.532.800-90 | abcd  | Chefe de Setor                  |

    E os usuários do processo eletronico

  Cenário: Acesso a criação de processo eletrônico pra quem não pode
  Testa acesso a criação de processo eletrônico pra quem não pode
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128001" e senha "abcd"
    Então vejo o item de menu "Documentos/Processos::Processos Eletrônicos::Processos"
    Quando acesso a página "/admin/processo_eletronico/processo/"
    Então vejo a página "Processos Eletrônicos"
    E nao vejo o botão "Adicionar Processo Eletrônico"
    Quando acesso o menu "Sair"


  Cenário: Acesso a criação de processo eletrônico pra quem pode
  Testa acesso a criação de processo eletrônico pra quem pode
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128002" e senha "abcd"
    Então vejo o item de menu "Documentos/Processos::Processos Eletrônicos::Processos"
    Quando acesso a página "/admin/processo_eletronico/processo/"
    Então vejo a página "Processos Eletrônicos"
    E vejo o botão "Adicionar Processo Eletrônico"
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Gerenciar Permissões do Processo Eletrônico
  Adiciona permissão para criar processo eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128002" e senha "abcd"
    E acesso o menu "Documentos/Processos::Permissões"
    Então vejo a página "Permissões para Documentos e Processos Eletrônicos"
    Quando clico na aba "Processos Eletrônicos"
    E preencho o formulário com os dados
      | Campo                                                                                         | Tipo                  | Valor                  |
      | Servidores/Prestadores de Serviço que podem adicionar e operar processos eletrônicos do(a) A1 | autocomplete multiplo | Operador de Processo 1 |

    E clico no botão "Enviar"

    Então vejo mensagem de sucesso "Operação realizada com sucesso"

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Quando a data do sistema for "22/08/2019"
    Quando acesso a página "/"
    E realizo o login com o usuário "128001" e senha "abcd"

  @do_document
  Cenario: Adicionar Processo Eletrônico
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
    E clico no botão "Adicionar Processo Eletrônico"
    E clico no botão "Buscar"
    E seleciono o item "Acesso à Informação: Demanda do e-SIC" da lista
    E clico no botão "Confirmar"
    E preencho o formulário com os dados
      | Campo            | Tipo                  | Valor                  |
      | Interessados     | autocomplete multiplo | Operador de Processo 1 |
      | Assunto          | TextArea              | Assunto do processo    |
      | Nível de Acesso  | Lista                 | Público                |
#               | Hipótese Legal                                | Lista    |                       |
      | Setor de Criação | Lista                 | A1                     |
#               | Classificações                                | Lista    |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  @do_document
  Cenário: Editar Conteúdo do Processo Eletrônico
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
    E olho para a listagem
    E olho a linha "23001.000001.2019-68"
    E clico no ícone de exibição
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico no botão "Nível de Acesso"
    E clico no botão "Editar Nível de Acesso"
    Então vejo a página "Alterar Nível de Acesso do Processo 23001.000001.2019-68"
    Quando preencho o formulário com os dados
      | Campo          | Tipo  | Valor               |
      | Para           | Lista | Restrito            |
      | Hipótese Legal | Lista | Informação Restrita |
      | Senha          | senha | abcd                |
    E clico no botão "Enviar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "Nível de Acesso alterado com sucesso."


  @do_document
  Cenário: Encaminhar Processo Eletrônico Sem Despacho
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
    E olho para a listagem
    E olho a linha "23001.000001.2019-68"
    E clico no ícone de exibição
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico no botão "Encaminhar"
    E clico no botão "Sem despacho"
    Então vejo a página "Encaminhar Processo 23001.000001.2019-68"
    Quando preencho o formulário com os dados
      | Campo                       | Tipo         | Valor          |
      | Buscar setor de destino por | Radio        | Autocompletar |
      | Setor de Destino            | Autocomplete | A2             |
    E clico no botão "Salvar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "Processo encaminhado com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"

  Cenário: Gerenciar Permissões do Processo Eletrônico
  Adiciona permissão para criar processo eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128004" e senha "abcd"
    E acesso o menu "Documentos/Processos::Permissões"
    Então vejo a página "Permissões para Documentos e Processos Eletrônicos"
    Quando clico na aba "Processos Eletrônicos"
    E preencho o formulário com os dados
      | Campo                                                                                     | Tipo                      | Valor                  |
      | Servidores/Prestadores de Serviço que podem adicionar e operar processos eletrônicos do(a) A2 | autocomplete multiplo | Operador de Processo 2 |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Operação realizada com sucesso"


  Cenário: Sai do sistema
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Receber processo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128003" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "A Receber"
    E clico no botão "Receber"
    Entao vejo mensagem de sucesso "Processo recebido com sucesso"

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Editar Conteúdo do Processo Eletrônico
    Dado os cadastros de documentos eletronicos
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128003" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "A Encaminhar"
    E clico no link "23001.000001.2019-68"
    Então vejo a página "Processo 23001.000001.2019-68"

    Quando clico no botão "Editar Dados"
    E clico no botão "Interessados"

    E olho para o popup
    Então vejo a página "Editar Interessados do Processo 23001.000001.2019-68"
    Quando preencho o formulário com os dados
      | Campo          | Tipo                  | Valor                   |
      | Interessados   | autocomplete multiplo | Operador de Processo 2  |
      | Justificativa  | textarea | Teste behave |
      | Senha          | senha | abcd                |
    E clico no botão "Enviar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "Os interessados do processo foram alterados com sucesso."


    Quando clico no botão "Editar Dados"
    E clico no botão "Nível de Prioridade"

    Então vejo a página "Nível de prioridade do processo 0000439.00000001/2019-79"
    Quando preencho o formulário com os dados
      | Campo          | Tipo     | Valor        |
      | Prioridade     | radio | Baixa |
      | Justificativa  | textarea | Teste behave |
    E clico no botão "Salvar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "O nível de prioridade foi atualizado com sucesso."
    Quando clico na aba "Documentos"
    E clico no botão "Adicionar Documento"
    Quando clico na aba "Documentos Internos"
    E clico no botão "Adicionar ao Processo"
    Então vejo a página "Processo 23001.000001.2019-68"
    Então vejo mensagem de sucesso "Documento adicionado com sucesso."
    Quando clico na aba "Documentos"

    E clico no botão "Upload de Documento Externo"
    Então vejo a página "Upload de Documento Externo"
    # Quando clico no botão "Buscar"
    # E seleciono o item "Ofício" da lista
    # E clico no botão "Confirmar"
    Quando preencho o formulário com os dados
     | Campo                       | Tipo          | Valor                |
     | Tipo                        | autocomplete  |  Ofício              |
     | Arquivo                     | arquivo real  | arquivo.pdf          |
     | Tipo de Conferência         | Lista         | Cópia Simples        |
     | Assunto                     | texto         | Teste behave         |
     | Nível de Acesso:            | Lista         | Público              |
#     | Setor Dono                 | Lista         | A2                   |
#     | Responsável pelo Documento | autocomplete  | Operador de Processo 2 |
#     | Tipo de Assinatura         | radio         | Assinatura Por Senha |
     E clico no botão "Salvar"
     Então vejo a página "Upload de Documento Externo"
     Quando preencho o formulário com os dados
     | Campo                      | Tipo          | Valor         |
     | Perfil                     | Lista         | Cargo A       |
     | Senha                      | senha         | abcd          |
    E clico no botão "Assinar Documento"
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico na aba "Comentários"
    E clico no link "Adicionar Comentário"
    E olho para o popup
    Então vejo a página "Adicionar Comentário"
    Quando preencho o formulário com os dados
      | Campo                                    | Tipo      | Valor                             |
      | Comentário                               | textarea  | Adiciona um comentário no processo|
    E clico no botão "Salvar"
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico no botão "Solicitar"
    E clico no botão "Despacho"
    Então vejo a página "Solicitação de despacho do 0000439.00000001/2019-79"
    Quando preencho o formulário com os dados
      | Campo                                    | Tipo      | Valor                    |
      | Corpo                                    | textarea  | Autorizo encaminhar para |
      | Solicitar Assinatura a                   | autocomplete | Operador de Processo 1   |
      | Senha                                    | senha |   abcd         |
      | Setor de Destino do Trâmite (Buscar por) | radio| Autocompletar  |
      | Especificar Setor | autocomplete | A1  |
    E clico no botão "Salvar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "A solicitação de despacho foi efetuada com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Deferir Despacho
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128001" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "A Despachar"
    E clico no link "23001.000001.2019-68"
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico na aba "Solicitações"
    E clico no link "Analisar"
    Então vejo a página "Solicitação de Despacho do Processo 0000439.00000001/2019-79"
    Quando preencho o formulário com os dados
    | Campo                      | Tipo      | Valor         |
    | Perfil                     | Lista     | Cargo A       |
    | Senha                      | senha     | abcd          |
    E clico no botão "Deferir e Encaminhar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "Processo encaminhado com sucesso."

    Cenário: Sai do sistema
    Quando acesso o menu "Sair"


#      @do_document
#  Cenário: Solicitar juntada de documento
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128001" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    Quando clico na aba "A Receber"
#    E clico no botão "Receber"
#    Entao vejo mensagem de sucesso "Processo recebido com sucesso"
##    E clico no link "23001.000001.2019-68"
#    Então vejo a página "Processo 23001.000001.2019-68"
##    E clico no botão "Receber"
##    E vejo a mensagem de sucesso "Processo recebido com sucesso."
#    Quando clico na aba "Solicitações"
#    E clico no link "Solicitar Documento"
#    Então vejo a página "Adicionar Solicitação de Juntada de Documentos"
#    Quando preencho o formulário com os dados
#    | Campo                      | Tipo            | Valor                     |
#    | Solicitados                | checkbox popup  | Operador de Processo 2    |
#    | Motivação                  | textarea     |  Você precisa adicionar o comprovante do renda no seu processo.         |
#    | Data Limite                | Data      |   30/08/2020                                                               |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    E vejo mensagem de sucesso "Solicitações de Juntada de Documentos adicionadas com sucesso."
#
#
#  Cenário: Sai do sistema
#    Quando acesso o menu "Sair"
#
#
#    @do_document
#    Cenário: Adicionar documentos solicitados por juntada e concluir juntada
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128003" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
#    E olho para a listagem
#    E olho a linha "23001.000001.2019-68"
#    E clico no ícone de exibição
#    Então vejo a página "Processo 23001.000001.2019-68"
#    Quando clico na aba "Solicitações"
#    E clico no link "Realizar Upload de Documento"
#    Então vejo a página "Adicionar Documento Externo à Solicitação de Juntada"
#    Quando clico no botão "Buscar"
#    E seleciono o item "Ofício" da lista
#    E clico no botão "Confirmar"
#    Quando preencho o formulário com os dados
#     | Campo                      | Tipo          | Valor        |
#     | Arquivo                    | arquivo       | arquivo.pdf            |
#     | Tipo de Conferência        | Lista         | Cópia Simples          |
#     | Assunto                    | texto         | Teste behave           |
#     | Nível de Acesso            | Lista         | Público                |
#     | Motivação da Juntada       | textarea      | Esta juntada será realizada para comprovar renda no processo     |
#     E clico no botão "Salvar"
#     Então vejo a página "Adicionar Documento Externo à Solicitação de Juntada"
#     Quando preencho o formulário com os dados
#     | Campo                      | Tipo          | Valor        |
#     | Perfil                     | Lista         | Cargo A       |
#     | Senha                      | senha         | abcd          |
#    E clico no botão "Assinar Documento"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    Quando clico na aba "Solicitações"
#    E clico no link "Concluir Solicitação"
#    Então vejo a página "Declaração de Conclusão de Juntada de Documento ao processo 23001.000001.2019-68"
#    Quando preencho o formulário com os dados
#     | Campo                      | Tipo          | Valor        |
#     | Concluir Solicitação       |  checkbox     | marcar |
#     | Senha                      |  senha         | abcd          |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000001.2019-68"
#
#
#  Cenário: Sai do sistema
#  Quando acesso o menu "Sair"
#
##Todo: Problema ao avaliar a juntada
#  @do_document
#  Cenário: Validar juntada de documento
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128001" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    Quando clico na aba "Aguardando Validação de Juntada"
#    E clico no link "23001.000001.2019-68"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    Quando clico na aba "Solicitações"
#    E vejo a aba "Solicitações de Juntada de Documentos"
#    Quando clico no botão de ação "Avaliar"
#    Então vejo a página "Avaliar solicitacão de juntada do documento Teste ao processo 23001.000001.2019-68"
#    E clico no botão "Deferir"
#    Entao vejo a página "Deferir Juntada do documento Teste ao processo 23001.000001.2019-68"
#    Quando preencho o formulário com os dados
#    | Campo                      | Tipo      | Valor         |
#    | Justificativa                  | textarea     |  Documento aceito         |
#    | Senha                | senha     | abcd                                        |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    E vejo mensagem de sucesso "Solicitação deferida com sucesso."
#
#
#  Cenário: Sai do sistema
#  Quando acesso o menu "Sair"

  Cenário: Solicitar ciência em processo eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128001" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "A Receber"
    E clico no botão "Receber"
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico na aba "Solicitações"
    E clico no link "Solicitar Ciência"
    Então vejo a página "Solicitar Ciência - Processo: 23001.000001.2019-68"
    Quando preencho o formulário com os dados
    | Campo                         | Tipo             | Valor                                    |
    | Interessados                  | checkbox popup   |  Operador de Processo 2                  |
    | Data Limite da Ciência        | Data             |  31/08/2020                              |
    | Justificativa da Solicitação  | textarea         |  Solicitando ciência aos interessados    |
    | Tipo da Ciência               | radio            |  Notificação                             |
    E clico no botão "Enviar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "Solicitações de ciência adicionadas com sucesso."


  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


    @do_document
    Cenário: Dar ciência em processo eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128003" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
    E olho para a listagem
    E olho a linha "23001.000001.2019-68"
    E clico no ícone de exibição
    Então vejo a página "Dar Ciência ao Processo 23001.000001.2019-68"
    Quando preencho o formulário com os dados
     | Campo                      | Tipo          | Valor        |
     | Perfil                     | Lista         | Cargo A       |
     | Declaro-me ciente          |  checkbox     | marcar |
     | Senha                      |  senha         | abcd          |
    E clico no botão "Assinar"
    Então vejo a página "Processo 23001.000001.2019-68"

    Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Encaminhar Processo Eletrônico Com Despacho
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128001" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
    E olho para a listagem
    E olho a linha "23001.000001.2019-68"
    E clico no ícone de exibição
    Então vejo a página "Processo 23001.000001.2019-68"
    Quando clico no botão "Encaminhar"
    E clico no botão "Com despacho"
    Então vejo a página "Encaminhar Processo 23001.000001.2019-68"
    Quando preencho o formulário com os dados
      | Campo                       | Tipo         | Valor                       |
      | Despacho                    | TextArea     | Esse é um despacho de teste |
      | Buscar setor de destino por | Radio        | Autocompletar              |
      | Setor de Destino            | Autocomplete | A2                          |
      | Perfil                      | Lista        | Cargo A       |
      | Senha                       | senha        | abcd          |
    E clico no botão "Salvar"
    Então vejo a página "Processo 23001.000001.2019-68"
    E vejo mensagem de sucesso "Processo encaminhado com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Receber processo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128003" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "A Receber"
    E clico no botão "Receber"
    Entao vejo mensagem de sucesso "Processo recebido com sucesso"

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"



    @do_document
  Cenario: Adicionar Processo Eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128003" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Processos"
    E clico no botão "Adicionar Processo Eletrônico"
    E clico no botão "Buscar"
    E seleciono o item "Acesso à Informação: Demanda do e-SIC" da lista
    E clico no botão "Confirmar"
    E preencho o formulário com os dados
      | Campo            | Tipo                  | Valor                  |
      | Interessados     | autocomplete multiplo | Operador de Processo 1 |
      | Assunto          | TextArea              | Assunto do processo    |
      | Nível de Acesso  | Lista                 | Público                |
      | Setor de Criação | Lista                 | A2                     |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

     Cenário: Sai do sistema
    Quando acesso o menu "Sair"

    @do_document
    Cenário: Adicionar Interesse em Processo Eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128004" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "Sem Tramitação"
    E clico no link "23001.000002.2019-11"
    Então vejo a página "Processo 23001.000002.2019-11"
    Quando clico no botão "Adicionar Interesse"
    Então vejo a página "Processo 23001.000002.2019-11"

    Cenário: Sai do sistema
    Quando acesso o menu "Sair"

    @do_document
    Cenário: Remover Interesse em Processo Eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128004" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "Sem Tramitação"
    E clico no link "23001.000002.2019-11"
    Então vejo a página "Processo 23001.000002.2019-11"
    Quando clico no botão "Remover Interesse"
    Então vejo a página "Processo 23001.000002.2019-11"


    Cenário: Sai do sistema
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Remover Último Trâmite
    Dado acesso a página "/"
    Quando realizo o login com o usuário "128004" e senha "abcd"
    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
    Então vejo a página "Seleção de Caixa de Processos"
    Quando clico no botão "Visualizar Todos os Setores"
    Então vejo a página "Caixa de Processos"
    Quando clico na aba "Sem Tramitação"
    E clico no link "23001.000002.2019-11"
    Então vejo a página "Processo 23001.000002.2019-11"
    Quando clico no botão "Encaminhar"
    E clico no botão "Sem despacho"
    Então vejo a página "Encaminhar Processo 23001.000002.2019-11"
    Quando preencho o formulário com os dados
      | Campo                       | Tipo         | Valor          |
      | Buscar setor de destino por | Radio        | Autocompletar |
      | Setor de Destino            | Autocomplete | A1             |
    E clico no botão "Salvar"
    Então vejo a página "Processo 23001.000002.2019-11"
    Quando clico no botão "Remover Último Trâmite"
    Então vejo a página "Processo 23001.000002.2019-11"
    E vejo mensagem de sucesso "Último trâmite removido com sucesso."


  Cenário: Sai do sistema
    Quando acesso o menu "Sair"

#
#   @do_document
#    Cenário: Apensar processos
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128004" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    Quando clico na aba "Sem Tramitação"
#    E clico no link "23001.000002.2019-11"
#    Então vejo a página "Processo 23001.000002.2019-11"
#    Quando clico na aba "Processos Apensados, Anexados e Relacionados"
#    E clico no botão "Apensar Processo"
#    E preencho o formulário com os dados
#      | Campo                   | Tipo                  | Valor                  |
#      | Processos a Apensar     | autocomplete multiplo | 23001.000001.2019-68   |
#      | Justificativa           | TextArea              | Apensando processos    |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000002.2019-11"
#
#
#    Cenário: Sai do sistema
#    Quando acesso o menu "Sair"
#
#
#   @do_document
#    Cenário: Desapensar processos
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128004" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    Quando clico na aba "Sem Tramitação"
#     #Todo: Erro ao desapensar - não aceita o comando da linha 561
#    E clico no link h4 "23001.000001.2019-68"
#    Então vejo a página "Processo 23001.000001.2019-68"
#    Quando clico na aba "Processos Apensados, Anexados e Relacionados"
#    E clico no botão "Desapensar Processo"
#    E preencho o formulário com os dados
#      | Campo                   | Tipo                  | Valor                  |
#      | Justificativa           | TextArea              | Desapensando processos |
#    E clico no botão "Enviar"
#    Então vejo a página "Processo 23001.000001.2019-68"
#
#    Cenário: Sai do sistema
#    Quando acesso o menu "Sair"
#
#
#   @do_document
#    Cenário: Relacionar processos
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128004" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    Quando clico na aba "Sem Tramitação"
#    E clico no link "23001.000002.2019-11"
#    Então vejo a página "Processo 23001.000002.2019-11"
#    E clico na aba "Processos Apensados, Anexados e Relacionados"
#    Quando clico no botão de ação "Relacionar Processo"
#    Entao vejo a página "Processos que podem ser relacionados ao processo 23001.000002.2019-11"
#    E olho para a listagem
#    E olho a linha "23001.000001.2019-68"
#    #TODO: Erro ao relacionar processos
#    E clico no botão de ação "Relacionar ao Processo"
#    Então vejo a página "Processo 23001.000002.2019-11"
#    E vejo a mensagem de sucesso "Relacionamento criado com sucesso."
#
#    Cenário: Sai do sistema
#    Quando acesso o menu "Sair"
#
#   @do_document
#    Cenário: Remover Relacionamento de processos
#    Dado acesso a página "/"
#    Quando realizo o login com o usuário "128004" e senha "abcd"
#    E acesso o menu "Documentos/Processos::Processos Eletrônicos::Caixa de Processos"
#    Então vejo a página "Caixa de Processos"
#    E clico na aba "Sem Tramitação"
#    Quando clico no link h4 "23001.000002.2019-11"
#    Então vejo a página "Processo 23001.000002.2019-11"
#    Quando clico na aba "Processos Apensados, Anexados e Relacionados"
#    E vejo a caixa de informações "Processos Relacionados"
#    E olho para a listagem
#    E olho a linha "23001.000001.2019-68"
#    E clico no ícone de remoção
#    Então vejo a página "Processo 23001.000002.2019-11"
#    E vejo a mensagem de sucesso "Relacionamento removido com sucesso."
#
#    Cenário: Sai do sistema
#    Quando acesso o menu "Sair"
