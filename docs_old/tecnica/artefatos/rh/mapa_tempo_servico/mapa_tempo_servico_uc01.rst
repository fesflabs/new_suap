.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Mapa de Tempo de Serviço** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-mapa_tempo_servico-uc01:

UC 01 - Cadastrar averbação  <v0.1>
===================================

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
     - 

Objetivo
--------
Cadastra as averbações dos serviços anteriores do servidor.

Atores
------


Principais
^^^^^^^^^^

Interessado
^^^^^^^^^^^

Pré-condições
-------------


Pós-condições
-------------


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado acionando a opção “ ” (RI1_)
    #. ...  

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Fluxo alternativo 1 (FN_.1)
"""""""""""""""""""""""""""""""""

Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Nome do fluxo de exceção (FN_.2)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

RIN1 – Campos para listagem
"""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Coluna 1
     - Coluna 2
   * - Ordenação
     - Não
     - Sim
     - Não
   * - Filtro
     - Não
     - Não
     - Sim
   * - Busca
     - Não
     - Sim
     - Não   
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
          Editar
     - 
     -   

.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

.. note:: 
    Liste aqui somente os campos que possuem uma certa particularidade, como por exempo:máscara específica, 
    domínio não conhecido, oculto para o usuário, possui valor inicial, tamanho bem definido. 
    Pode ser necessário especifiar tipo, tamanhao, obrigatoriedade, valor inicial, máscara, 
    oculto [S/N], domínio.
    
.. list-table:: 
   :widths: 10 20 5 5 5 5
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Nome campo*
       .. note:: * -> campo obrigatório
     - 
       .. note::
       
          - use "texto autocompletar simples" para ForeignKeyPlus e 
          - texto "autocompletar multiplo" para MultipleModelChoiceFieldPlus
          - texto longo para Textarea
          - text
          - seleção
          - seleção multipla 
          - Data/Hora
          - texto (somente leitura)
          
     - 
     - 
     - 
     - 
       .. note::
          Em observação pode se incluir o texto que aparece logo abaixo do campo como dica.
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. note:: 
    Descreva aqui as regras de negócio e para cada uma a mensagem que será exibida ao ator.

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Nome da regra
       | Mensagem 
   
Mensagens
^^^^^^^^^

.. note:: 
    Neste tópico são descritas todas as mensagens que o sistema apresenta ao ator, exceto as mensagens descritas nas regras de negócio.

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Código
     - Descrição
   * - M1    
     - 
     
.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_        
     
.. _PE:
     
Ponto de Extensão
-----------------

Questões em Aberto
------------------

Esboço de Protótipo
-------------------

Diagrama de domínio do caso de uso
----------------------------------

Diagrama de Fluxo de Operação
-----------------------------

Cenário de Testes
-----------------

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
     - Texto com o objetivo do teste
   * - Dados de Entrada
     - Texto descrevendo os dados de entrada
   * - Resultado Esperado
     - Texto descrevendo o resultado esperado.
     