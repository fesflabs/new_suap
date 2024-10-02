
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cursos_matr_comp-uc307: 

UC 307 - Gerir Configurações de AACCs <v0.1>
============================================

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
   * - 28/04/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Cadastrar, alterar, remove ou listar Configuração de Atividade Acadêmica Científico Cultural.

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

Casos de Uso Impactados
-----------------------

    #. :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc305` - Vincular matriz ao curso.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Configurações de AACCs``
    #. O sistema exibe a lista de configurações de AACCs
      
       #. Visualizar configuração AACC (PE_.1)
    


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Cadastrar (FN_.2 )
""""""""""""""""""""""""

    #. O usuário aciona a opção ``Cadastrar Configuração de AACCs`` 
    #. O sistema exibe um formulário de entrada de dados para cadastro da nova **Configuração de AACCs**: 
    
       #. Dados Gerais (Descrição do conjunto de atividades ) 
       #.  Atividades (Descrição da atividade, Pontuação máxima 
           por semestre, Pontuação máxima por curso, Fator de conversão(peso))
    #. O usuário informa novos valores para os dados (RIN2_) 
    #. O usuário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_.
    #. O sistema apresenta a listagem do passo FN_.2 
    
.. _FA1:

FA2 - Editar (FN_.2 )
"""""""""""""""""""""

    #. O usuário aciona a opção ``Editar`` de uma das AACCs da listagem de AACCs do passo FN_.2 
    #. O sistema exibe um formulário já preenchido com os dados de uma **Configuração de AACCs**
    #. O usuário informa novos valores para os dados (RIN2_) 
    #. O usuário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M2_.
    #. O sistema apresenta a listagem do passo FN_.2 
    
.. _FA3:

FA3 - Excluir (FN_.2 )
""""""""""""""""""""""

    #. O usuário aciona a opção ``Editar`` de uma das AACCs da listagem de AACCs do passo FN_.2 
    #. O sistema exibe um formulário já preenchido com os dados de uma **Configuração de AACCs**
    #. O usuário finaliza o caso de uso selecionando a opção ``Apagar``
    #. O sistema exibe a mensagem M3_.
    #. O sistema apresenta a listagem do passo FN_.2 




Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN3 (FA1_-4)
""""""""""""""""""""""""""""""""""""""

FE2 – Exclusão fere Regra RN1 (FA3_-1)
""""""""""""""""""""""""""""""""""""""

FE3 – Exclusão fere Regra RN1 (FA5_-1)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^


RI1 – Exibição de uma matriz curricular
"""""""""""""""""""""""""""""""""""""""


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^


.. _RIN1:

.. _suap-artefatos-edu-ensino-cursos_matri_comp-uc307-RIN1:

RIN1 – Campos para listagem de Configurações de AACCs
"""""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida dividida em abas conforme especificadas abaixo:

- ``Qualquer``: exibe todas as AACCs
- ``Vinculadas a um curso``: exibe apenas as AACCs vinculadas a algum curso
- ``Não vinculadas a um curso``: exibe apenas as AACCs desvinculadas a cursos

     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Código
     - Descrição
   * - Ordenação
     - Não
     - Sim
     - Sim
   * - Filtro
     - Não
     - Não
     - Não
   * - Busca
     - Não
     - Sim
     - Sim
   * - Observações
     - 
     - 
     -


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
     - É um nome para a configuração sendo cadastrada
   * - Descrição da AACC
     - Texto
     - 
     - 
     - 
     - É um nome para a AACC sendo cadastrada
   * - Pontuação máxima no Período
     - Inteiro
     - 
     - 
     - 
     - 
   * - Pontuação máxima no curso
     - Inteiro
     - 
     - 
     - 
     - 
   * - Fator de conversão(Peso)
     - Flutuante
     - 
     - 
     - 
     - 
  

A `Figura 1`_ exibe um esboço do formulário de cadastro de uma AACC.
     
Regras de Negócio
^^^^^^^^^^^^^^^^^
.. list-table:: 
   :widths: 10 80
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | O sistema só permite a exclusão de uma Configuração de Atividades se não houver dependência dessas atividades no sistema. Ou seja, aluno que utilizou de alguma dessas atividades.
       | mensagem: A remoção da Configuração de Atividades Acadêmica Científico Cultural fere a integridade de relacionamento do sistema, os seguintes objetos teriam que ser excluídos:
   * - RN2
     - | Caso a edição da Configuração de Atividade resulte na exclusão de uma atividade, esta só poderá ser excluída se não houver nenhuma dependência desta atividade no sistema, ou seja,
         aluno que utilizou a referida atividade.
   * - RN3
     - | Ao submeter o cadastro ou edição de uma Configuração de Atividade o sistema exige do usuário que os dados obrigatórios sejam preenchidos permitindo que os dados faltantes
         sejam preenchidos.
   * - RN4
     - | Qualquer alteração numa das atividades da Configuração de AACC deverá reexecutar o fluxo de situação de matrícula para os alunos atingidos.
     

  
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
     - Cadastro realizado com sucesso.
   * - M2
     - Atualização realizada com sucesso.
   * - M3
     - Você tem certeza que quer remover a configuração de AACC "<descrição da configuração>"? Todos os seguintes itens relacionados serão removidos:   
   * - M4
     - Você tem certeza que quer remover o tipo "<descrição do tipo>" de atividade complementar desta configuração de AACCs "<descrição da configuração>"? Todos os seguintes alunos já fizeram uso e passaram a tê-la como atividade extracurricular. 
  
.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    




.. _PE:

Ponto de Extensão
-----------------

   #. :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc308` 


Questões em Aberto
------------------


Esboço de Protótipo
-------------------


.. _`Figura 1`:


    .. figure:: media/tela_uc307_gerir_configuracao_de_aaccs.png
       :align: center
       :scale: 100 %
       :alt: protótipo de tela.
       :figclass: align-center
       
       Figura 1: Protótipo de tela gestão de configurações de AACCs.


Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.