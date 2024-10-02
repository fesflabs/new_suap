
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cad_gerais-uc114:

UC 114 - Gerir Diretorias Acadêmicas <v0.1>
===========================================

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
   * - 22/04/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Cadastrar, alterar e listar diretorias acadêmicas, bem como possibilita a inclusão/remoção de diretor geral, diretor acadêmico, 
coordenador de curso, secretários e pedagogos.

Atores
------

Principais
^^^^^^^^^^

Administrador: tem acesso geral ao sistema. Responsável por realizar todos os cadastros básicos necessários para o 
bom funcionamento do sistema, isto é, para que seja possível gerenciar turmas, diários, matriculas, notas de aulas, etc.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Deve existir ao menos um setor ativo na qual a diretoria acadêmica será vinculada.

Pós-condições
-------------

Diretoria acadêmica disponível para cadastro de cursos.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cadastros Gerais`` > ``Diretorias Acadêmicas``
    #. O sistema exibe a lista de diretorias acadêmicas (RIN1_)
    #. O administrador seleciona a opção ``Adicionar Diretoria Acadêmica`` 
    #. O administrador informa os dados (RIN2_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Editar (FN_.2 )
"""""""""""""""""""""

	#. O administrador aciona a opção ``Editar`` de uma das diretoria acadêmica disponíveis na listagem
	#. O sistema exibe a diretoria acadêmica com os dados (RIN2_) preenchidos
	#. O administrador informa novos valores para os dados (RIN2_) 
	#. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	

FA2 – Listar (FN_.2)
""""""""""""""""""""

	#. O administrador restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA3:

FA3 – Visualizar (FN_.2)
""""""""""""""""""""""""

	#. O administrador aciona a opção ``Ver`` da diretoria acadêmica que se deseja realizar o vínculo dentre uma das 
	   diretorias acadêmicas disponíveis na listagem
	#. O sistema exibe informações da diretoria acadêmica (RI1_)
	#. O sistema exibe informações sobre os vínculos dentro de suas respectivas caixas:	
	   
	   #. "Diretor Geral" (PE_.1)
	   #. "Diretor Acadêmico" (PE_.2)
	   #. "Coordenadores de Curso" (PE_.3)
	   #. "Secretários" (PE_.4)
	   #. "Pedagogos" (PE_.5)


FA4 - Desvincular (FA3_.2)
""""""""""""""""""""""""""

    #. O administrador aciona a opção ``Remover`` disponível em cada carta do servidor (RIN3_) do vínculo 
       ("Diretor Geral", "Diretor Acadêmico", "Coordenadores de Curso", "Secretários" ou "Pedagogos") que se
       deseja realizar a desassociação
    #. O caso de uso volta para o passo FA3_.2
    

FA5 - Definir Títular (FA3_.2)
""""""""""""""""""""""""""""""

    #. O administrador aciona a opção ``Definir como Títular`` disponível em cada carta do servidor (RIN3_) do vínculo 
       ("Diretor Geral" ou "Diretor Acadêmico") que se deseja tornar o diretor como títular    
    #. O caso de uso volta para o passo FA3_.2


FA6 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FN_.4 

FA7 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M5_.
	#. O caso de uso volta para o passo F1_.3 
	
FA8 - Remover (FA1_.2) 
""""""""""""""""""""""

    #. O administrador aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M6_
    #. O administrador aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M7_
    #. O administrador confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2
    	
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

RI1 – Exibição da diretoria acadêmica 
"""""""""""""""""""""""""""""""""""""

Os dados da diretória acadêmica é exibida dentro de uma caixa de nome "Dados da Diretoria", são eles:

- ``Setor``: nome do setor;
- ``Campus``: nome do campus o qual o setor está localizado;
- ``Diretor Geral``: Nome (matricula) do diretor geral definido como titular;
- ``Diretor Acadêmico``: Nome (matricula) do diretor acadêmico definido como titular;

Além da caixa "Dados da Diretoria" é exibido uma caixa para cada vínculo, com os seguintes nome:
- "Diretor Geral" (PE_.1)
- "Diretor Acadêmico" (PE_.2)
- "Coordenadores de Curso" (PE_.3)
- "Secretários" (PE_.4)
- "Pedagogos" (PE_.5)

Se a caixa estiver vazia, é exibida a mensagem M3_, caso contrário, uma carta com informações do servidor é exibida (RIN3_). 

A figura abaixo esboça um protótipo de tela para exibição de uma diretoria acadêmica.

.. figure:: media/tela_visualizar_diretoria.png
   :align: center
   :scale: 30 %
   :alt: protótipo exibição de diretoria acadêmica.
   :figclass: align-center
   
   Protótipo de tela para exibição de diretoria acadêmica.

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^
.. _RIN1:
     
RIN1 – Campos para listagem de Diretoria Acadêmica
""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida dividida em abas conforme especificadas abaixo:

- ``Qualquer``: exibe todas as diretorias acadêmicas;
- ``Sem Diretores``: exibe somente as diretorias acadêmicas em que não há diretores (geral, acadêmico) definidos;
- ``Sem Secretários``: exibe someente as diretorias acadêmicas em que não há secretários definidos;
- ``Sem Coordenadores``: exibe someente as diretorias acadêmicas em que não há coordenadores de cursos definidos;
- ``Sem Pedagogos``: exibe somente as diretorias acadêmicas em que não há pedagogos definidos.
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Setor
     - Campus
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
   * - Setor*
     - Seleção (ComboBox)
     - 
     - 
     - 
     - 

.. _RIN3:
     
RIN3 – Campos para exibição da carta do servidor
""""""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 30
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
   * - Nome
     - Texto (rótulo)
   * - Matrícula
     - Texto (rótulo)
   * - Setor de Lotação
     - Texto (rótulo)
   * - Email
     - Texto (rótulo)
   * - Ações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Remover
          Definir como Títular
          .. note:: disponível apenas para "Diretor Geral" e "Diretor Acadêmico"
          Definir Cursos
          .. note:: disponível apenas para "Coordenadores de Curso"	     

     
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
       | A remoção de Componente "<campo descrição>" pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
  
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
     - Nenhum servidor cadastrado com esse perfil.
   * - M4
     - Diretoria Acadêmica <campo setor> alterado com sucesso. Você pode adicionar um outro Diretoria Acadêmica abaixo.
   * - M5
     - Diretoria Acadêmica <campo Setor> modificado com sucesso. Você pode editá-lo novamente abaixo.
   * - M6
     - Você tem certeza que quer remover Diretoria Acadêmica "<campo Descrição>"? Todos os seguintes itens relacionados serão removidos:    
   * - M7
     - Tem certeza que deseja continuar?       

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_    
.. _M5: `Mensagens`_
.. _M6: `Mensagens`_
.. _M7: `Mensagens`_

    
.. _PE:

Ponto de Extensão
-----------------

	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc116` 
	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc117` 
	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc118` 
	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc119` 
	#. :ref:`suap-artefatos-edu-ensino-cad_gerais-uc20` 

Questões em Aberto
------------------

Não há.

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