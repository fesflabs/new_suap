:orphan:

.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-subdiretorio-uc123: 

UC 123 - Manter Membros da Banca <v0.1>
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
   * - 14/07/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos

Objetivo
--------

Este caso de uso permite cadastrar um membro da banca, o qual pode ser um co-orientador externo um um examinador externo à Instituição

Cadastrar, alterar, remove ou listar membros da banca.

Atores
------

Principais
^^^^^^^^^^

Secretário, diretores acadêmicos ou administradores do sistema.

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

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cadastros Gerais`` > `` Membros da Banca``
    #. O sistema exibe a lista de Membros da Banca (RIN1_)
    #. O secretário seleciona a opção ``Adicionar Membros da Banca``
    #. O secretário informa os dados (RIN2_)
    #. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Editar (FN_.2 )
"""""""""""""""""""""

	#. O secretário aciona a opção ``Editar`` dentre um dos membros da banca disponíveis na listagem
	#. O sistema exibe o membro da banca com os dados (RIN2_) preenchidos
	#. O secretário informa novos valores para os dados (RIN2_) 
	#. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O secretário aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4

.. _FA3:

FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O secretário aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FA1_.3
	

FA4 – Listar (FN_.2)
""""""""""""""""""""

	#. O secretário restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA5:   

FA5 - Remover (FA1_.2)
""""""""""""""""""""""

    #. O secretário aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M5_
    #. O secretário aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M6_
    #. O secretário confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2


Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1_ (FA5_-1)
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
     
RIN1 – Campos para listagem de Núcleo Membro da Banca
"""""""""""""""""""""""""""""""""""""""""""""""""""""
     
    
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Nome
     - Instituição
     - Formação
   * - Ordenação
     - Não
     - Sim
     - Não
     - Não
   * - Filtro
     - Não
     - Não
     - Sim
     - Não
   * - Busca
     - Não
     - Sim
     - Não  
     - Não 
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Editar
     - 
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
   * - Nome*
     - Texto
     - 
     - 
     - 
     - 
   * - Sexo*
     - Seleção
     - 
     - 
     - Masculino, Feminino
     -      
   * - Instituição
     - Texto
     - 
     - 
     - 
     - 
   * - Formação
     - Seleção
     - 
     - 
     - Graduação, Especialização, Mestrado, Doutorado, Pós-doutorado
     - 
   * - email
     - Texto
     - 
     - 
     - 
     - Usar tipo que valida o email
     
     
        
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
       | mensagem: A remoção do Membro da Banca "<campo nome>" pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
   
  
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
     - NCE <campo nce> alterado com sucesso. Você pode adicionar um outro NCE abaixo.
   * - M4
     - NCE <campo nce> modificado com sucesso. Você pode editá-lo novamente abaixo.
   * - M5
     - Você tem certeza que quer remover Membro da banca "<campo nome>"? Todos os seguintes itens relacionados serão removidos:    
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