
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-proc_apoio-uc500: 

UC 500 - Configurar Horário do Campus <v0.1>
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
   * - 22/04/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Cadastrar, alterar, remover e listar Horário do Campus, bem como possibilita a inclusão/remoção horários de aulas.

Atores
------

Principais
^^^^^^^^^^

Administrador: permite gerir os horários dos campi.

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

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Procedimentos de Apoio`` > ``Horário do Campus``
    #. O sistema exibe a lista de Horários dos Campi (RIN1_)
    #. O administrador seleciona a opção ``Adicionar ``Horário do Campus````
    #. O administrador informa os dados (RIN2_) para identificar o Horário do Campus
    #. Para cada Horários de Aulas que se deseja adicionar, o administrador informar os dados (RIN3_)  
    #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Editar (FN_.2 )
"""""""""""""""""""""

	#. O administrador aciona a opção ``Editar`` dentre um dos horários dos campi disponíveis na listagem
	#. O sistema exibe o Horário do Campus com os dados (RIN2_ e RIN3_) preenchidos
	#. O administrador informa novos valores para os dados (RIN2_) 
	#. Para cada Horários de Aulas que se deseja alterar, o administrador informar novos valores para os dados (RIN3_)  
	#. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
FA2 - Salvar e adicionar outro(a) (FN_.5)
"""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FN_.5 

.. _FA3:

FA3 - Salvar e continuar editando (FA1_.4)
""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M5_.
	#. O caso de uso volta para o passo FA1_.4 	

FA4 – Listar (FN_.2)
""""""""""""""""""""

	#. O administrador restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA5:

FA5 - Remover um horário de aula (FA1_.2)
"""""""""""""""""""""""""""""""""""""""""

    #. Para cada horário de aula que se deseja remover, o administrador marca a caixa de seleção ``Apagar?``
    #. O caso de uso continua a partir do passo FA1_.5
    
 
FA6 - Adicionar outro(a) Horário De Aula (FA1_.2)
"""""""""""""""""""""""""""""""""""""""""""""""""

    #. O administrador aciona a opção ``Adicionar outro(a) Horário De Aula`` disponível no final da listagem ``Horários das Aulas``
       para incluir uma linha vazia na listagem.      

FA7 - Remover (FA1_.2) 
""""""""""""""""""""""

    #. O administrador aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M6_
    #. O administrador aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M7_
    #. O administrador confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2


FA8 - Exportar para XLS (FN_.2)
"""""""""""""""""""""""""""""""
	#. O administrador aciona a opção ``Exportar para XLS`` 
	#. O sistema faz o download do arquivo com extensão .xls com as seguintes colunas (RIN1_) de acordo com a ordem existente na listagem


Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1_ (FA6_-1)
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
       | A remoção de Horário do Campus pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 

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
     - Diretoria Acadêmica <campo Descrição> alterado com sucesso. Você pode adicionar um outro Diretoria Acadêmica abaixo.
   * - M5
     - Diretoria Acadêmica <campo Descrição> modificado com sucesso. Você pode editá-lo novamente abaixo.    ]
   * - M6
     - Você tem certeza que quer remover Horário do Campus <campo Descrição>? Todos os seguintes itens relacionados serão removidos:    

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