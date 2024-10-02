
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc213:

UC 213 - Requisitos de Conclusão <v0.1>
=======================================

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
   * - 11/07/2014
     - 0.1
     - Início do Documento
     - Ibanêz Cavalcanti Ferreira

Objetivo
--------

Permite aos usuários visualizar o andamento do curso em relação aos requisitos exigidos pela grade curricular e os já cumpridos pelo aluno.

Atores
------

Principais
^^^^^^^^^^

Administradores do sistema, Diretores, Coordenadores, Pedagogos e Secretários.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Aluno cadastrado no sistema.

Pós-condições
-------------

Não se aplica.

Casos de Uso Impactados
-----------------------

Não se aplica.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado a partir do passo FN.2 do caso de uso :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202`, ao 
       acionar a  opção ``ENSINO`` > ``Alunos e Professores`` > ``Alunos``,  em seguida, selecionando a opção ``Ver``
       do aluno dentre um dos alunos disponíveis na listagem, depois acionar a aba ``Requisitos para conclusão``
    #. O sistema muda de aba exibindo os ``Requisitos para conclusão``: de curso: CH Disciplinas Obrigatórias, 
       Ch Disciplinas Optativas, CH Disciplinas Eletivas, CH Seminários, CH Prática Profissional, CH Projeto Final, 
       CH Atividades Complementares, Colação de Grau e ENADE.


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Atualizar requisitos de conclusão (FN_.2 )
""""""""""""""""""""""""""""""""""""""""""""""""

	#. O usuário aciona a opção ``Atualizar Requisitos``
	#. O sistema atualiza a página com os dados
	
	
    	
    	
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

Não há.

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     

RIN1 – Campos para listagem neste caso de uso
"""""""""""""""""""""""""""""""""""""""""""""
     
.. list-table:: 
   :widths: 5 5 5 5 5 10
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Icone*
     - Figura
     - 
     - 
     - 
     - Deve estar conforme o status da informação: Cumprido(ok), Não cumprido(não ok), Não informado(alerta)
   * - Grupo de requisitos*
     - Texto
     - 
     - 
     - 
     - 
   * - Status*
     - Texto
     - 
     - 
     - 
     -      
   * - CH Prevista
     - Inteiro
     - 
     - 
     - 
     - 
   * - CH Cumprida
     - Inteiro
     - 
     - 
     - 
     -  
   * - Componentes Pendentes*
     - Inteiro
     - 
     - 
     - 
     -       
            

.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

Não há.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Para cada requistos de conclusão que possui carga horária o sistema deve informar a 
     	 situação (Cumpriu/Pendente), a CH Prevista, a CH Cumprida e a quantidade de componentes
     	 pendentes.
       | mensagem: não há. 
  
.. _RN1: `Regras de Negócio`_  
   
Mensagens
^^^^^^^^^

Não há.

    
.. _PE:

Ponto de Extensão
-----------------

Não há.

Questões em Aberto
------------------

Não há.

Esboço de Protótipo
-------------------

.. _`Figura 1`:


	.. figure:: media/tela_uc213.png
	   :align: center
	   :scale: 100 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 1: Protótipo de tela para exibição de requisitos de conclusão.
	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.