
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cursos_matr_comp-uc308: 

UC 308 - Visualizar Configuração de AACCs <v0.1>
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
   * - 18/07/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Visualizar Configuração de Atividade Acadêmica Científico Cultural.

Atores
------

Principais
^^^^^^^^^^

Administrador

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Estar logado no sistema.

Pós-condições
-------------

Não há.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Configurações de AACCs``
    #. O sistema exibe a lista de configurações de AACCs
    #. O usuário aciona a opção ``Visualizar`` de uma das AACCs da listagem de AACCs
    #. O sistema exibe uma visão da Configuração de AACC escolhida 


Fluxos Alternativos
^^^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Replicar Configuração de AACCs (FN_.2 )
"""""""""""""""""""""""""""""""""""""""""""""

    #. O usuário aciona a opção ``Replicar Configuração de AACCs`` da visão exibida do passo FN_.4
    #. O sistema exibe um formulário de entrada de dados ``Replicação da Configuração de AACCs``
    #. O usuário entra com uma descrição para o conjunto de atividades
    #. O usuário finaliza o caso de uso selecionando a opção ``Replicar Configuração de AACCs``
    #. O sistema apresenta a visão referente à AACC recém criada e exibe a mensagem M1_.
    
.. _FA2:

.. _FA1:

FA2 - Vincular Matriz a uma Configuração de AACCs (FN_.2 )
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

    #. O usuário aciona a aba ``Matrizes Vinculadas`` da visão exibida do passo FN_.4
    #. O sistema exibe uma tabela com as Matrizes vinculadas a esta Configuração de AACCs
    #. O usuário aciona o botão ``Vincular Matriz``
    #. O sistema mostra um formulário onde o usuário deve selecionar uma Matriz
    #. O usuário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema atualiza a tabela de Matriz vinculadas a esta Configuração de AACCs e exibe a mensagem M2_.



Fluxo de Exceção
^^^^^^^^^^^^^^^^

Não há.

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

.. _suap-artefatos-edu-ensino-cursos_matri_comp-uc307-RIN1:

RIN1 – Informações exibidas de uma Configurações de AACCs
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""
 
A visão de uma Configuração de AACC mostra as informações abaixo:

- ``Descrição``: exibe a descrição da configuração de AACC.
- Uma aba ``Atividades Acadêmicas Curriculares-Acadêmico-Cultural``: exibe uma tabela com informações de cada Atividade Acadêmico-Científico-Cultural conforme a seguir:
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - Columa
     - Tipo

   * - Descrição
     - Texto

   * - Pontuação Máxima no Período
     - Inteiro

   * - Pontuação Máxima no Curso
     - Inteiro
  
   * - Fator de Conversao
     - Flutuante

- Uma aba ``Matrizes Vinculadas`` que mostra a lista das Matrizes vinculadas a esta configuração de AACCs: 

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - Columa
     - Tipo

   * - Ações
     - Link/Ação

   * - Código
     - Inteiro

   * - Descrição
     - Texto
  
   * - Ativa
     - Booleano
   * - Curso
     - Curso
    
.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 5 5 5 5 20
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Descrição da configuração
     - Texto
     - 
     - 
     - 
     - É um nome para a configuração sendo cadastrada.
   

Regras de Negócio
^^^^^^^^^^^^^^^^^
.. list-table:: 
   :widths: 10 80
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Uma Matriz só pode ser desvinculada da Configuração de AACCs se não houverem dependências no sistema. Por exemplo alunos que
         adquiriram uma das atividades da Configuração de AACCs.
       | mensagem: Você não pode excluir esta vinculação pois a configuração de AACCs é referenciada pelos seguintes objetos: 
   * - RN2
     - | Caso uma Matriz já esteja vinculada a uma Configuração de AACCs o sistema não permite a nova vinculação.
       | mensagem: A Matriz ``X`` já está vinculada a configuração de AACCs ``Y``. Caso deseje vincular a outra configuração de AACCs
         primeiro exclua o vinculo anterior.

  
.. _RN1: `Regras de Negócio`_  

   
Mensagens
^^^^^^^^^

.. _M:

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Código
     - Descrição
   * - M1    
     - AACC replicada com sucesso.
   * - M2
     - A matriz foi vinculada com sucesso.
  
.. _M1: `Mensagens`_     

.. _M2: `Mensagens`_    


.. _PE:

Ponto de Extensão
-----------------



Questões em Aberto
------------------


Esboço de Protótipo
-------------------


.. _`Figura 1`:


    .. figure:: media/tela_uc308_visualizar_configuracao_de_aacc.png
       :align: center
       :scale: 100 %
       :alt: protótipo de tela.
       :figclass: align-center
       
       Figura 1: Protótipo de tela para visualizar uma configuração de AACCs.


Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.