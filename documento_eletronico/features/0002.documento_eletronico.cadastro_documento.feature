# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Fluxo criação de documentos eletrônicos

  Cenário: Configuração inicial para execução dos cenários do documento eletronico
    Dado os cadastros básicos do documento eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "200002" e senha "abcd"

  @do_document
  Cenário: Definir Permissões de Documento Eletrônico
    Essa funcionalidade define as permissões de acesso para o documento/processo eletrônico. Ação executada pelo perfil Chefe de Setor.

    Quando acesso o menu "Documentos/Processos::Permissões"
    E clico na aba "Documentos Eletrônicos"
    E preencho o formulário com os dados
      | Campo                                                                                         | Tipo                  | Valor                       |
      | Servidores/Prestadores de Serviço que podem adicionar, operar e ler documentos do(a) DIDE/CEN | autocomplete multiplo | Servidor Documento Operador |
      | Servidores/Prestadores de Serviço que podem ler documentos do(a) DIDE/CEN                     | autocomplete multiplo | Servidor Documento Leitor   |

  @do_document
  Cenário: Cadastrar Documento Eletrônico
    Quando a data do sistema for "08/01/2020"
    E acesso o menu "Documentos/Processos::Documentos Eletrônicos::Documentos"
    E clico no botão "Adicionar Documento de Texto"
    E preencho o formulário com os dados
      | Campo             | Tipo     | Valor                 |
      | Tipo do Documento | lista    | Memorando             |
      | Modelo            | lista    | Interrupção de Férias |
      | Nível de Acesso   | lista    | Público               |
      | Setor Dono        | lista    | DIDE/CEN              |
      | Assunto           | textarea | Teste                 |
    E clico no botão "Salvar"

  @do_document
  Cenário: Editar Conteúdo do Documento Eletrônico
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Documentos"
    E olho para a listagem
    E olho a linha "DIDE/CEN"
    E clico no ícone de exibição
    Então vejo a página "Documento"
    Quando clico no botão "Editar"
    E clico no botão "Texto"
    Então vejo a página "Editar Documento"
    Quando clico no botão "Salvar e Visualizar"
    Então vejo a página "Documento"
    E vejo mensagem de sucesso "Edição realizada com sucesso."

  @do_document
  Cenário: Concluir Documento Eletrônico
    Quando clico no botão "Concluir"
    Então vejo mensagem de sucesso "Operação realizada com sucesso."
    E vejo a página "Documento"
    Quando olho para a página
    Então nao vejo o botão "Editar"

  @do_document
  Cenário: Retornar Documento Eletrônico para Rascunho
    Quando clico no botão "Retornar para Rascunho"
    Então vejo mensagem de sucesso "Operação realizada com sucesso."
    E vejo a página "Documento"
    Quando olho para a página
    Então vejo o botão "Editar"
    Quando clico no botão "Concluir"
    Então vejo mensagem de sucesso "Operação realizada com sucesso."
    E vejo a página "Documento"

  @do_document
  Cenário: Assinar Documento Eletrônico
    Quando a data do sistema for "08/01/2020"
    Quando clico no botão "Assinar"
    E clico no botão "Com Senha"
    Então vejo a página "Assinatura de Documento"
    Quando clico no botão "Definir Identificador"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor |
      | Senha | senha | abcd  |
    E clico no botão "Assinar Documento"
    Então vejo mensagem de sucesso "Documento assinado com sucesso."

  @do_document
  Cenário: Solicitar Assinatura de Documento Eletrônico
    Quando a data do sistema for "08/01/2020"
    E clico no botão "Solicitar"
    E clico no botão "Assinatura"
    Então vejo a página "Solicitações de Assinaturas"
    Quando preencho o formulário com os dados
      | Campo  | Tipo         | Valor                        |
      | Pessoa | autocomplete | Servidor Documento Gerente S |
    E clico no botão "Enviar solicitações"
    Então vejo mensagem de sucesso "Sua solicitação foi enviada com sucesso."
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "200001" e senha "abcd"
    E acesso a página "/admin/documento_eletronico/documentotexto/"
    Então vejo a página "Documentos de Texto"
    Quando olho para a listagem
    E olho a linha "MEMO 1/2020 - DIDE/CEN/RAIZ"
    E clico no ícone de exibição
    Então vejo a página "MEMO 1/2020 - DIDE/CEN/RAIZ"
    Quando clico no botão "Assinar"
    E clico no botão "Com Senha"
    Então vejo a página "Assinatura de Documento"
    Quando preencho o formulário com os dados
      | Campo | Tipo  | Valor |
      | Senha | senha | abcd  |
    E clico no botão "Assinar Documento"
    Então vejo mensagem de sucesso "Documento assinado com sucesso."
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "200002" e senha "abcd"
    E acesso a página "/admin/documento_eletronico/documentotexto/"
    Então vejo a página "Documentos de Texto"
    Quando olho para a listagem
    E olho a linha "MEMO 1/2020 - DIDE/CEN/RAIZ"
    E clico no ícone de exibição
    Então vejo a página "MEMO 1/2020 - DIDE/CEN/RAIZ"

  @do_document
  Cenário: Finalizar Documento Eletrônico
    Quando olho para a página
    E clico no botão "Finalizar Documento"
    Então vejo mensagem de sucesso "Documento finalizado com sucesso."

#   TODO: Verificar uma outra forma de testar esse imprimir documento
#  @do_document
#  Cenário: Imprimir Documento Eletrônico
#    Quando clico no botão "Ações"
#    E clico no botão "Imprimir em Carta"
#    Então nao vejo a página "Erro no Sistema"
#    Quando acesso a página "/documento_eletronico/visualizar_documento/1/"
#    E clico no botão "Ações"
#    E clico no botão "Imprimir em Paisagem"
#    Então nao vejo a página "Erro no Sistema"

  """
  # verificar em outro momento
  @do_document
  Cenário: Clonar Documento Eletrônico
    Então vejo mensagem de sucesso "Sua solicitação foi enviada com sucesso."
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "200001" e senha "abcd"
    Quando acesso a página "/documento_eletronico/visualizar_documento/1/"
    E clico no botão "Ações"
    E clico no botão "Clonar"
    Então vejo mensagem de sucesso "Documento foi clonado com sucesso. Para prosseguir com a clonagem informe o setor dono e assunto do documento."
    Quando preencho o formulário com os dados
      | Campo      | Tipo     | Valor   |
      | Setor Dono | lista    | CEN     |
      | Assunto    | textarea | Clonado |
    E clico no botão "Salvar"
    Então vejo a página "Documento 2"

  @do_document
  Cenário: Vincular Documento Eletrônico
    Quando clico no botão "Concluir"
    E clico no botão "Assinar"
    E clico no botão "Com Senha"
    E clico no botão "Definir Identificador"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor |
      | Senha | senha | abcd  |
    E clico no botão "Assinar Documento"
    E clico no botão "Finalizar Documento"
    E acesso a página "/documento_eletronico/visualizar_documento/1/"
    E clico no botão "Vincular Documento"
    E preencho o formulário com os dados
      | Campo           | Tipo         | Valor              |
      | Tipo de Vínculo | lista        | é um aditivo do(a) |
      | Documento Alvo  | autocomplete | MEMO 1             |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Vínculo criado com sucesso."
    """
