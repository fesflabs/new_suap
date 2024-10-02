# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Submissão de Obra para Publicação

      @do_document
      Cenário: Submissão da Obra
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108012" e senha "abcd"
            E a data do sistema for "08/01/2018"
            E acesso o menu "Pesquisa::Editora::Submissão de Obras::Submeter Obra"
         Então vejo a página "Editais Abertos para Submissão de Obras"
         Quando olho a linha "Edital para publicação"
             Então vejo o botão "Submeter Obra"
        Quando clico no botão "Submeter Obra"
         Então vejo a página "Submeter Obra: Edital para publicação"
             E vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Tipo                                                       | Lista    |
               | Biografia do Autor/Organizador                             | TextArea |
               | Telefone                                                   | Texto    |
               | Foto do Autor/Organizador                                  | Arquivo  |
               | Termo de Compromisso do Autor com a Editora                | Arquivo  |

               | Título                                                     | Texto    |
               | Sinopse para Catálogo                                      | TextArea |
               | Sinopse para Quarta Capa                                   | TextArea |

               | Linha Editorial                                            | Lista    |
               | Área                                                       | Lista    |
               | Núcleos de Pesquisa                                        | Texto    |

               | Tipo de Submissão                                          | Lista    |
               | Obra Completa                                              | Arquivo  |
               | Obra Sem Identificação                                     | Arquivo |
               | Declaro ter lido os seguintes documentos: Política editorial, Direitos Autorais e Autorização de publicação da obra | checkbox |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                 |
               | Tipo                                                       | Lista    | Autor                 |
               | Biografia do Autor/Organizador                             | TextArea | Descrição da biografia do autor |
               | Telefone                                                   | Texto    | (84) 91234-5678       |
               | Foto do Autor/Organizador                                  | Arquivo  | foto_autor.png        |
               | Termo de Compromisso do Autor com a Editora                | Arquivo  | termo_compromisso.png |
               | Título                                                     | Texto    | título da obra        |
               | Sinopse para Catálogo                                      | TextArea | sinospe da obra       |
               | Sinopse para Quarta Capa                                   | TextArea | sinospe para a quarta capa |
               | Linha Editorial                                            | Lista    | Linha Editorial 01    |
               | Área                                                       | Lista    | CIÊNCIAS EXATAS E DA TERRA |
               | Tipo de Submissão                                          | Lista    | Anais                      |
               | Obra Completa                                              | Arquivo  | obra_completa.png          |
               | Obra Sem Identificação                                     | Arquivo | obra_completa_sem_identificacao.png |
               | Declaro ter lido os seguintes documentos: Política editorial, Direitos Autorais e Autorização de publicação da obra | checkbox | marcar |
             E clico no botão "Salvar"

        Então vejo mensagem de sucesso "Obra submetida com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
