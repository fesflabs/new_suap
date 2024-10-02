
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cursos_matr_comp-uc301: 

UC 301 - Manter Componente Curricular <v0.1>
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

Cadastrar, alterar, remove ou listar componente curricular.

Atores
------

Principais
^^^^^^^^^^

Administrador: permite gerir o cadastro de componentes curriculares. 

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------



Pós-condições
-------------



Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Componentes``
    #. O sistema exibe a lista de componente curricular (RIN1_)
    #. O administrador seleciona a opção ``Adicionar Componente``
    #. O administrador informa os dados (RIN2_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Editar (FN_.2 )
"""""""""""""""""""""

	#. O administrador aciona a opção ``Editar`` dentre um dos componentes curriculares disponíveis na listagem
	#. O sistema exibe o componente curricular com os dados (RIN2_) preenchidos
	#. O administrador informa novos valores para os dados (RIN2_) 
	#. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4

.. _FA3:

FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FA1_.3
	

FA4 - Listar (FN_.2)
""""""""""""""""""""

	#. O administrador restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA5:   

FA5 - Remover (FA1_.2) 
""""""""""""""""""""""

    #. O administrador aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M5_
    #. O administrador aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M6_
    #. O administrador confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2


FA6 - Visualizar (FN_.2)
""""""""""""""""""""""""

	#. O administrador aciona a opção ``Ver`` do componente curricular que se deseja visualizar dentre um dos 
	   componentes curriculares disponíveis na listagem
	#. O sistema exibe informações do componente curricular (RI1_)

FA7 - Visualizar matriz curricular (FA6_.2)
"""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Ver`` da matriz que se deseja visualizar dentre um das 
	   matrizes dosponíveis na listagem da caixa "Matrizes"
	#. O sistema exibe informações da matriz (ver fluxo FA6 do caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302`)


FA8 - Exportar para XLS (FN_.2)
"""""""""""""""""""""""""""""""
	#. O administrador aciona a opção ``Exportar para XLS`` 
	#. O sistema faz o download do arquivo com extensão .xls com as seguintes colunas (RIN1_) de acordo com a ordem existente na listagem


Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1 (FA5_-1)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RI1 – Exibição de uma componente curricular 
"""""""""""""""""""""""""""""""""""""""""""


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     
RIN1 – Campos para listagem de componente curricular
""""""""""""""""""""""""""""""""""""""""""""""""""""


.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Exclusão fere integridade relacional.
       | A remoção de Componente "<campo Descrição - campo Nível de ensino [campo Hora/relógio/Hora/aula]>" pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
  
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
     - Componente "<campo Descrição - campo Nível de ensino [campo Hora/relógio/Hora/aula]>" alterado com sucesso. Você pode adicionar um outro Componente Curricular abaixo.
   * - M4
     - Componente "<campo Descrição - campo Nível de ensino [campo Hora/relógio/Hora/aula]>" modificado com sucesso. Você pode editá-lo novamente abaixo. 
   * - M5
     - Você tem certeza que quer remover Componente <campo Descrição - campo Nível de ensino [campo Hora/relógio/Hora/aula]>"? Todos os seguintes itens relacionados serão removidos:
   * - M6
     - Tem certeza que deseja continuar?    

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_   
.. _M5: `Mensagens`_    
.. _M6: `Mensagens`_    

Ponto de Extensão
-----------------
	
Não há.

Questões em Aberto
------------------

- Nome componente no menu está em minúsculo.

Esboço de Protótipo 
-------------------

Não há.

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.