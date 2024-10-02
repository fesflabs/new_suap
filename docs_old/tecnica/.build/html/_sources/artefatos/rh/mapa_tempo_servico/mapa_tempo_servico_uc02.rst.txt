.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Mapa de Tempo de Serviço** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-mapa_tempo_servico-uc02:

UC 02 - Obter tempo de serviço  <v0.1>
======================================

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
   * - 05/05/2014
     - 0.1
     - Início do Documento
     - Esdras Valentim

Objetivo
--------

Obtém o tempo de serviço atual do servidor no órgão que estar lotado no momento. Este caso de uso é uma inclusão do caso de uso base 
chamado Exibir histórico do servidor.


Atores
------

Principais
^^^^^^^^^^
Operador do RH

Interessado
^^^^^^^^^^^
Servidor

Pré-condições
-------------

- O Servidor deve está cadastrado no sistema
- O servidor tem que ter histórico funcional na instituição


Pós-condições
-------------

- O sistema mostrará o tempo de serviço atual do servidor 

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado acionando a opção ``Gestão de Pessoas`` > ``Mapa de tempo de serviço`` > ``Tempo de serviço atual`` (RI1_)
    #. O operador do RH entra com a matrícula ou nome do servidor
    #. O operador do RH finaliza o caso de uso selecionando a opção ``Obter tempo de serviço`` 
    #. O sistema exibe o tempo de serviço **atual** do servidor

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Fluxo alternativo 1 (FN_1)
""""""""""""""""""""""""""""""""

Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1 [FN_.2)
"""""""""""""""""""""""""""""""""""""

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

Fluxo normal
""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Testar a funcionalidade de obter o tempo de serviço de um regime jurídico
   * - Dados de Entrada
     - Data início e data fim do regime jurídico
   * - Resultado Esperado
     - Retornar um numero não negativo de dias
     
Fluxo normal
""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1
   
   * - Objetivo
     - Testar a funcionalidade de obter o tempo de serviço ficto de um PCA
   * - Dados de Entrada
     - Regimes jurídicos associados ao PCA
   * - Resultado Esperado
     - Retornar um número não negativo de dias, considerando o fator de ajuste para cada regime jurídico
     