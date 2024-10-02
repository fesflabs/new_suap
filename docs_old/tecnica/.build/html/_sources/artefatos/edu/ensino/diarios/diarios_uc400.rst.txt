
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-diarios-uc400: 

UC 400 - Gerir alunos em turmas <v0.3>
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
   * - 30/04/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
   * - 14/04/2014
     - 0.2
     - Ajustes no protótipo de tela, regas de negócio e fluxos conforme sugerido por Alessandro. 
     - Jailton Carlos
   * - 15/04/2014
     - 0.3
     - Inclusão da regra de negócio RN5_ e ajustes na RN4_. 
     - Jailton Carlos

Objetivo
--------

Inclusão e remoção de alunos em turmas.


Atores
------

Principais
^^^^^^^^^^

Secretário, diretor acadêmico ou administrador: gerencia a inclusão e remoção de alunos em turmas.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Deve existir ao menos uma turma.

Pós-condições
-------------

- Matricular alunos em turmas (FN_)

  - A turma em questão será definido como turma atual do aluno para o período;
  - Aluno matriculado em todos os diários da turma (ver RN4_)
  
- Remover alunos da turma (FA1_)

  - Aluno sem turma.


Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Turmas e Diários`` > ``Turmas``
    #. O sistema exibe a lista de turmas (ver RIN1 do caso de uso :ref:`suap-artefatos-edu-ensino-diarios-uc401`)
    #. O secretário aciona a opção ``Ver`` dentre uma das turmas disponíveis na listagem
    #. O sistema exibe informações da turma (ver RI1 do caso de uso :ref:`suap-artefatos-edu-ensino-diarios-uc401`)
    #. O secretário aciona a aba ``Alunos``
    #. O sistema exibe os alunos da turma e os alunos aptos a serem matriculados (RIN1_)
    #. O secretário seleciona um ou mais alunos da lista de alunos ``Alunos sem Turma`` e aciona a opção ``Matricular Alunos Selecionados``
    #. O sistema apresenta a listagem do passo FN_.6 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Remover alunos da turma (FN_.6)
"""""""""""""""""""""""""""""""""""""

	#. O secretário seleciona um ou mais alunos da lista de alunos ``Alunos da Turma`` e aciona a opção ``Remover Alunos Selecionados``
	#. O sistema exibe a mensagem M1_
	#. O secretário aciona a opção "Sim, tenho certeza"
	#. O sistema apresenta a listagem do passo FN_.6 
	
FA2 - Filtrar (FN_.6)
"""""""""""""""""""""

	#. O secretário restringe a lista usando o filtro e/ou busca (RIN2_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior


Fluxo de Exceção
^^^^^^^^^^^^^^^^

.. _FE1:

FE1 – Há notas lançadas (FA1_-3)
""""""""""""""""""""""""""""""""

	#. O sistema exibe a mensagem M2_
	#. O secretário confirma a remoção
	#. O sistema apresenta a listagem do passo FN_.6 


FE1 – Exclusão fere Regra RN5_ (FE1_-2)
"""""""""""""""""""""""""""""""""""""""


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

.. _RIN1:
     
RIN1 – Campos para listagem de alunos
"""""""""""""""""""""""""""""""""""""
 
A listagem é exibida dividida em duas caixas ( ver `Figura 1`_ ) :

- ``Alunos da Turma``: exibe todos os alunos matriculados na turma selecionada; 
     
	.. list-table:: 
	   :header-rows: 1
	   :stub-columns: 1
	
	   * - 
	     - #
	     - Matricula
	     - Nome
	     - Há notas lançadas	       	      	         
	   * - Ordenação
	     - Não
	     - Sim
	     - Sim, padrão ascendente
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
	     
 	.. note:: 
 	   A coluna ``Há notas lançadas`` segue a regra de negócio RN1_.
 	       

- ``Alunos sem Turmas``: exibe todos alunos habilitados para serem matriculados na turma selecionada (RN3_).

	.. list-table:: 
	   :header-rows: 1
	   :stub-columns: 1
	
	   * - 
	     - #
	     - Matricula
	     - Nome
	   * - Ordenação
	     - Não
	     - Sim
	     - Sim, padrão ascendente
	   * - Filtro
	     - Não
	     - Não
	     - Não
	   * - Busca
	     - Não
	     - Não
	     - Não
	     
.. _RIN2:

RIN2 – Campos para Filtro
"""""""""""""""""""""""""

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
   * - Turno*
     - Seleção simples
     - 
     - Turno da turma selecionada previamente
     - 
     -       
     
     
A `Figura 1`_ exibe um esboço de como esses campos poderiam está dispostos no formulário.
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Caso exista aluno matriculado na turma selecionada no qual há diários com notas lançadas e/ou faltas registradas, informar "Sim" na coluna
         ``Há notas lançadas``, caso contrário informar "Não".
       | Mensagem: Não há. 
   * - RN2
     - | Remoção de aluno no qual há diários com notas lançadas e/ou faltas registradas deverá ser duplamente confirmada.
       | Mensagem: M2_
   * - RN3
     - | Critério para exibição de alunos sem turmas: são todos os alunos que não estão matriculados em turmas (encontra-se em nenhuma turma),
         possui o período atual igual a turma que está sendo visualizada e o turno igual ao turno selecionado.
       | Mensagem: não há.
   * - RN4
     - | Regra para inclusão de alunos em diários: aluno será matriculado em todos os diários da turma cujos componentes 
         ele ainda não tenha sido aprovado e cujos pré-requisitos ele já tenha cursado.
       | Nota: ao dizer "não tenha sido aprovado", entende-se que o aluno precisará cursar o componente, exclui portanto
         os componentens aprovados por nota, dispensados, aproveitamento de estudo, certificação de conhecimento, etc. 
       | Mensagem: não há.
   * - RN5
     - | Regra para exclusão de diários do aluno na turma: não excluir o diário do aluno se a situação do diário for diferente de "CURSANDO".
       | Mensagem: O diário <código do diário>.<nome do componente> do aluno <nome do aluno> não foi excluído, pois a situação do 
         diário é <situação do diário>.


.. _RN1: `Regras de Negócio`_   
.. _RN2: `Regras de Negócio`_   
.. _RN3: `Regras de Negócio`_   
.. _RN4: `Regras de Negócio`_       
   
   
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
     - Você tem certeza que quer remover o(s) aluno(s) selecionado(s) da turma "<campo codigo>"?
   * - M2
     - Há aluno(s) selecionado(s) com notas lançadas e/ou faltas registradas, tem certeza que deseja continuar?   
     
.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_


Ponto de Extensão
-----------------
	
Não há.

Questões em Aberto
------------------

Não há.
  

Esboço de Protótipo
-------------------

.. _`Figura 1`:

.. figure:: media/tela_uc29.png
   :align: center
   :scale: 70 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para gerir alunos em turma.

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------
Não há.