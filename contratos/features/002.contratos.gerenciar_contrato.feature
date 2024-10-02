# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Gerenciar Contratos
  O gerenciamento dos contratos é realizado pelo perfil "Gerente de contrato".
  Estes serão os responsáveis por:
      - Cadastrar os contratos
      - Geração e gerenciamento do cronograma de execução do contrato
      - Inclusão das parcelas do contrato
      - Inclusão dos físcais de contrato.

  Cenário: Efetuar login no sistema
    Quando a data do sistema for "10/01/2020"
    E realizo o login com o usuário "996623" e senha "abcd"


  @do_document
  Cenário: Cadastrar Contratos
    Quando pesquiso por "Contratos" e acesso o menu "Administração::Contratos::Contratos"
    E clico no botão "Adicionar Contrato"
    E preencho o formulário com os dados
      | Campo                  | Tipo                   | Valor                                                                        |
      | Tipo                   | Lista                  | Contrato                                                                     |
      | Subtipo                | Lista                  | Serviço Continuado sem Dedicação Exclusiva de Mão de Obra - Energia Elétrica |
      | Número                 | Texto                  | 01/2020                                                                      |
      | Valor                  | Texto                  | 100.000,00                                                                   |
      | Data de Início         | Data                   | 01/01/2020                                                                   |
      | Data de Término        | Data                   | 31/12/2020                                                                   |
      | Objeto de Contrato     | Textarea               | Contrato de Energia                                                          |
      | Processo               | Autocomplete           | Assunto do Contrato                                                       |
      | Campi                  | FilteredSelectMultiple | CZN, A0                                                                      |
      | Contratada             | Autocomplete           | 45.006.424/0001-00                                                           |
      | Quantidade de Parcelas | Texto                  | 2                                                                            |
      | Arquivo do Contrato    | Arquivo Real           | Arquivo.pdf                                                                  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Gerar Cronograma
    Quando clico no ícone de exibição
    """
    Procure o contrato que você vai gerenciar o cronograma e clique o icone da lupa.
    """
    Então vejo a página "01/2020"
    """
    Verifique sempre se esse é o contrato que você quer gerenciar.
    """
    Quando clico na aba "Cronograma"
    E clico no botão "Criar Cronograma"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo                | Tipo  | Valor |
      | Número do Cronograma | Texto | 1     |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Número de cronograma definido com sucesso. As parcelas necessitam ser geradas."


  @do_document
  Cenário: Gerar Parcelas
    Quando clico na aba "Cronograma"
    E clico no botão "Gerar Várias Parcelas"
    E clico no botão "Gerar Parcelas"
    Então vejo mensagem de sucesso "Parcelas geradas com sucesso."
    E vejo a aba "Cronograma"
    """
    Confira o valor e a quantidade de parcelas para o seu contrato.
    """

  @do_document
  Cenário: Adicionar fiscais
    Quando clico na aba "Fiscais"
    E clico no botão "Adicionar Fiscal"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo                  | Tipo         | Valor              |
      | Tipo                   | Autocomplete | Titular            |
      | Servidor               | Autocomplete | Fiscal de Contrato |
      | Portaria               | Texto        | 01/2020            |
      | Campi                  | Autocomplete | CZN                |
      | Data da Nomeação       | Data         | 01/01/2020         |
      | Data Final da Vigência | Data         | 31/12/2020         |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Fiscal adicionado com sucesso."
    E vejo a aba "Fiscais"
