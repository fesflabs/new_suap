.. include:: header.rst

.. _suap-artefatos-adm-centralservicos-uc101:

UC101 - Manter Grupo de Atendimento <v0.1>
==========================================

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
   * - 03/07/2014
     - 0.1
     - Início do Documento
     - Rafael Pinto

Objetivo
--------

.. _suap-artefatos-adm-centralservicos-uc101-objetivo:

Cadastrar e manter atualizados os grupos de atendimento da central de serviços.


Atores
------

Principais
^^^^^^^^^^
Chefe da Equipe de Suporte

Interessado
^^^^^^^^^^^
Chefe da Equipe de Suporte


Pré-condições
-------------
Cadastro de Campus.


Pós-condições
-------------


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Grupo de Atendimento``
    #. O sistema apresenta uma árvore hierárquica de grupo de sistemas já cadastrados (RIN01_):
    #. O ator seleciona a opção ``Adicionar grupo de atendimento``
    #. Na tela ``Adicionar grupo de atendimento`` o ator preenche os campos (RIN02_)
    #. O ator finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema apresenta a listagem do passo FN-2


Fluxos Alternativos
^^^^^^^^^^^^^^^^^^^

FA1 – Editar (FN_-2, FA5.2)
"""""""""""""""""""""""""""

#. O ator seleciona a opção ``Editar`` de uma das linhas da listagem de grupo de atendimento já cadastrados
#. Na tela ``Editar <nome do grupo de atendimento>`` o ator altera os campos (RIN02_), os dados do grupo de atendimento já virão preenchidos
#. O ator finaliza o caso de uso selecionando a opção ``Salvar``
#. O sistema apresenta a listagem do passo FN-2


FA2 – Salva e adicionar novo (FN_-4, FA1.2)
"""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Salvar e adicionar outro(a)`` ao invés da opção ``Salvar``
#. Após salvar o grupo de atendimento o caso de uso reinicia no passo FN-3


FA3 – Salvar e continuar editando (FN_-4, FA1.2)
""""""""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Salvar e continuar editando`` ao invés da opção ``Salvar``
#. Após salvar o grupo de atendimento o caso de uso reinicia no FA1.2


FA4 – Remover (FN_-2, FA1.2)
""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Remover`` de uma das linhas da listagem de grupo de atendimento já cadastrados
#. Na tela ``Remover grupo de atendimento`` o sistema apresenta uma lista todos os registros filhos relacionados ao grupo de atendimento
#. O ator seleciona a opção ``Sim, tenho certeza`` para confirma que deseja remover este grupo de atendimento
#. O sistema apresenta a listagem do passo FN-2


FA5 – Visualizar (FN_-2)
""""""""""""""""""""""""

#. O ator seleciona a opção ``Visualizar`` de uma das linhas da listagem de grupo de atendimento já cadastrados
#. Na tela ``Visualizar grupo de atendimento`` o sistema:

   #) Apresenta os campos (RIN02)


Fluxos de Exceção
^^^^^^^^^^^^^^^^^

FE1 – Cancelar remoção de grupo de atendimento (FA4.2)
""""""""""""""""""""""""""""""""""""""""""""""""""""""

#. O ator seleciona a opção ``Cancelar`` na tela ``Remover grupo de atendimento`` 
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


RIN01 – Campos para listagem de grupo de atendimento
""""""""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Opções
     - Nome
     - Campus
     - Tipo
   * - Ordenação
     - Não
     - Não
     - Não
     - Não
   * - Filtro
     - Não
     - Não
     - Não
     - Não
   * - Busca
     - Não
     - Não
     - Não
     - Não
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Visualizar
          Editar

     - 
     - 
     - 


.. _RIN02:

RIN02 – Campos para cadastros de grupo de atendimento (incluir, editar e visualizar)
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio
     - Máscara
   * - Grupo de Atendimento Pai
     - Seleção (Árvore Hierárquica)
     - 
     - 
     - Grupo de Atendimento 
     - 
   * - Campus*
     - Seleção (Autocomplete)
     - 
     - 
     - Campus
     -
   * - Tipo*
     - Seleção (Combobox)
     - 
     - 
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Local
          Sistêmico     
     -     
   * - Nome*
     - Texto
     - 60
     - 
     - 
     -      
   * - Responsável*
     - Seleção (Autocomplete)
     - 
     - 
     - Pessoa Fisica 
     - 


Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   

Mensagens
^^^^^^^^^

Não há.
  

.. _pde:

Ponto de Extensão
-----------------

Não há.


Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

Tela de cadastro de serviços
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. image:: imagens/tela-cadastro-grupo-atendimento.png

Diagrama de domínio do caso de uso
----------------------------------

Não há.


Diagrama de Fluxo de Operação
-----------------------------

Não há.


Cenário de Testes
-----------------

.. note:: Falta construir os cenários de teste.

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
     
