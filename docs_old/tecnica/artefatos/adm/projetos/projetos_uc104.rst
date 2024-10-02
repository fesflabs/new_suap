.. include:: header.rst

.. _suap-artefatos-adm-projetos-uc104:

UC104 - Manter plano de oferta <v0.1>
=====================================

.. contents:: Conteúdo
    :local:
    :depth: 4

Histórico da Revisão
--------------------

.. list-table:: **Histórico da Revisão**
   :widths: 10 5 30 15
   :header-rows: 1
   :stub-columns: 0

   * - Data
     - Versão
     - Descrição
     - Autor
   * - 19/02/2014
     - 0.1
     - Início do Documento
     - Kelson da Costa Medeiros

Objetivo
--------

.. _suap-artefatos-adm-projetos-uc101-objetivo:

Cadastrar e manter atualizados os editais de projetos educacionais.

Atores
------

Principais
^^^^^^^^^^
Gerente sistêmico

Interessado
^^^^^^^^^^^
Não se aplica.


Pré-condições
-------------
Não se aplica.


Pós-condições
-------------
Os editais estão prontos para receber projetos educacionais a partir da data determinada na definição do edital.


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado selecionando a opção ``EXTENSÃO`` > ``Projetos`` > ``Editais``
    #. O sistema apresenta a lista de editais já cadastrados (RIN01_):
    #. O ator seleciona a opção ``Adicionar edital``
    #. Na tela ``Adicionar edital`` o ator preenche os campos (RIN02_)
    #. O ator finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema apresenta a listagem do passo FN-2


Fluxos Alternativos
^^^^^^^^^^^^^^^^^^^

FA1 – Editar (FN_-2)
""""""""""""""""""""

#. O ator seleciona a opção ``Editar`` de uma das linhas da listagem de editais já cadastrados
#. Na tela ``Editar <nome do edital>`` o ator altera os campos (RIN02_), os dados do edital já virão preenchidos
#. O ator finaliza o caso de uso selecionando a opção ``Salvar``
#. O sistema apresenta a listagem do passo FN-2


FA2 – Salva e adicionar novo (FN_-4, FA1.2)
"""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Salvar e adicionar outro(a)`` ao invés da opção ``Salvar``
#. Após salvar o edital o caso de uso reinicia no passo FN-3


FA3 – Salvar e continuar editando (FN_-4, FA1.2)
""""""""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Salvar e continuar editando`` ao invés da opção ``Salvar``
#. Após salvar o edital o caso de uso reinicia no FA1.2


FA4 – Remover (FN_-2)
"""""""""""""""""""""

#. O ator seleciona a opção ``Remover`` de uma das linhas da listagem de editais já cadastrados
#. Na tela ``Remover Edital`` o sistema apresenta uma lista todos os registros filhos relacionados ao edital
#. O ator seleciona a opção ``Sim, tenho certeza`` para confirma que deseja remover este edital
#. O sistema apresenta a listagem do passo FN-2


FA5 – Visualizar (FN_-2)
""""""""""""""""""""""""

#. O ator seleciona a opção ``Remover`` de uma das linhas da listagem de editais já cadastrados
#. Na tela ``Remover Edital`` o sistema apresenta uma lista todos os registros filhos relacionados ao edital
#. O ator seleciona a opção ``Sim, tenho certeza`` para confirma que deseja remover este edital
#. O sistema apresenta a listagem do passo FN-2


Fluxos de Exceção
^^^^^^^^^^^^^^^^^

FE1 – Cancelar remoção de edital (FA4.2)
""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Cancelar`` na tela ``Remover Edital`` 
#. O sistema apresenta a listagem do passo FN-2


Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.


Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

Não há.


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN01:

RIN01 – Campos para listagem de editais
"""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Título
     - Tipo
     - Máscara
     - Ordenação
   * - Opções
     - Opções
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Visualizar
          Editar
          Remover
     - Não
   * - Título
     - Texto
     - 
     - Sim (padrão, ascendente)
   * - Descrição
     - Texto Longo
     - 
     - Não
   * - Início das inscrições
     - Data/Hora
     - 
     - Sim
   * - Fim das inscrições
     - Data/Hora
     - 
     - Sim


.. _RIN02:

RIN02 – Campos para cadastros de editais (incluir e editar)
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio
     - Máscara
   * - Título*
     - Texto
     - 255
     - 
     - 
     - 
   * - Tipo de edital*
     - Seleção (Combobox)
     - 
     - 
     - 
       .. csv-table::
          :header: "Cód", "Rótulo"
          :widths: 10 90

          E, Extensão
          I, Inovação
          P, Pesquisa
     - 
   * - Descrição*
     - Texto Longo
     - 
     - 
     - 
     - 
   * - Início das inscrições*
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Fim das inscrições*
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Início da pré-seleção*
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Início da seleção*
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Divulgação da seleção*
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Participa aluno?
     - Checkbox
     - 
     - 
     - 
     - 
   * - Participa servidor?
     - Checkbox
     - 
     - 
     - 
     - 


Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   

Mensagens
^^^^^^^^^

Não há.
  
     
Ponto de Extensão
-----------------

Não há.


Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

Diagrama de domínio do caso de uso
----------------------------------

Não há.


Diagrama de Fluxo de Operação
-----------------------------

Não há.


Cenário de Testes
-----------------

.. note:: Falta construir os cebnários de teste.

.. comment
  Objetivos
  ^^^^^^^^^

  O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
  de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
  esperados que visam validar esse caso de uso.

  Casos e Registros de Teste
  ^^^^^^^^^^^^^^^^^^^^^^^^^^

  Fluxo de Exceção FE1
  """"""""""""""""""""

  .. list-table:: 
     :widths: 10 50
     :stub-columns: 1

     * - Objetivo
       - 
     * - Dados de Entrada
       - 
     * - Resultado Esperado
       - 
     
