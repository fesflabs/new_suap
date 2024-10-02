
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Progressão Funcional** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-progressoes-uc03:

UC 03 - Preencher formulário de avaliação <v0.1>
================================================

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
   * - 16/07/2014
     - 0.1
     - Início do Documento
     - Esdras Valentim
    

Objetivo
--------

Esse caso de uso descreve o preenchimento dos formuláros de avaliação por parte dos servidores.

Atores
------

- Servidor 
- RH

Principais
^^^^^^^^^^

- Servidor

Interessado
^^^^^^^^^^^

- Servidor
- RH

Pré-condições
-------------

- O Servidor terá que ser setado previamente como avaliador pelo RH, conforme foi descrito no caso de uso UC03
- A avaliação é persistida no banco

Pós-condições
-------------

- O total de pontos desta avaliação é mostrado na tela
 

Fluxo de Eventos
----------------

- O caso de uso se inicia com uma mensagem recebida, pelo servidor, na tela de início
- O servidor seleciona um dos servidores a serem avaliados 
- O sistema exibe o formulário de avaliação com 10 perguntas
- O servidor preenche as 10 perguntas com notas de 0 a 10
- O sistema vai mostrando a soma dos pontos automaticamente
- O caso de uso é finalizado quando o servidor seleciona a opção ``Enviar avaliação``


Fluxo Normal
^^^^^^^^^^^^

.. _FN:
   
    #. O caso de uso é iniciado acionando a opção  ``INÍCIO``
    #. O sistema exibe a mensagem de que existe servidores a serem avaliados
    #. O servidor seleciona a mensagem 
    #. O sistema exibe uma lista de servidores que deverão ser avaliados
    #. O servidor seleciona um dos servidores
    #. O sistema mostra o formulário de avaliação
    #. O servidor preenche os dados de todas as notas
    #. O sistema calcula a soma das notas
    #. O servidor seleciona a opção ``Enviar avaliação``    


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Editar avaliação (FN_.1)
""""""""""""""""""""""""""""""
   
    FA1 – Editar (FN_.1 )
    """""""""""""""""""""

      #. O servidor aciona a opção ``Avaliações`` >> ``Editar``
      #. O servidor seleciona uma dos servidores
      #. O sistema mostra o formulário de avaliação
      #. O servidor informa novos valores para as notas 
      #. O sistema calcula a soma das notas
      #. O servidor seleciona a opção ``Reenviar avaliação``
    

Fluxo de Exceção
^^^^^^^^^^^^^^^^
    
FE1 – Validar campos notas (FN_.1)
""""""""""""""""""""""""""""""""""

      #. No passo 7 do fluxo normal o servidor preenche um ou mais campos com nota superior a 10 ou inferior a 0
      #. O sistema exibe a mensagem: nota inválida
      #. O sistema desabilita a opção ``Enviar avaliação`` até que a nota seja corrigida
      #. O servidor corrige a nota
      #. O sistema calcula a soma das notas
      #. O sistema habilita a opção ``Enviar avaliação``
      #. O servidor finaliza o caso de uso de execeção selecionando a opção ``Enviar avaliação``


Especificação suplementares
---------------------------

- O formulário de avaliação exibe perguntas diferentes quando o servidor tem função administrativa
- O sistema precisa identificar se o servidor tem função ou não e redirecionar para o formulário de avaliação adequado

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^

``Não se Aplica``    

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^
- Notas inferiores a 6.0 serão mostradas na cor vermelha
- Notas superiores a 6.0 serão mostradas na cor azul


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

RIN1 – Campos para listagem
"""""""""""""""""""""""""""

``Não se Aplica``

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

``Não se Aplica``
          
Regras de Negócio
^^^^^^^^^^^^^^^^^

``Não se Aplica``
   
Mensagens
^^^^^^^^^

``Não se Aplica``
     
Ponto de Extensão
-----------------

``Não se Aplica``

Questões em Aberto
------------------

- Qual o menu para alterar a avaliação?

Esboço de Protótipo
-------------------

``Não se Aplica``

Diagrama de domínio do caso de uso
----------------------------------

``Não se aplica``

Diagrama de Fluxo de Operação
-----------------------------

``Não se aplica``

Cenário de Testes
-----------------

Objetivos
^^^^^^^^^

O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
esperados que visam validar esse caso de uso.

Casos e Registros de Teste
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::   
    Identifique (Tipo de Teste) se o teste é relativo a um fluxo alternativo, de exceção, regra de negócio, 
    permissão.

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
