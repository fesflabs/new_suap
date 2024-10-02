
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Comum** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-adm-agendamento_salas-uc07: 

UC 06 - Indeferir solicitações fora de prazo <v0.1>
===================================================

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
   * - 07/05/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
     
.. comentário
   07/05 - início do documento
   08/05


Objetivo
--------

Todas as solicitações de reservas não avaliadas fora de prazo, isto é, data final maior que data atual, serão automaticamente
indeferidas.

Atores
------

Principais
^^^^^^^^^^

Avaliador: usuário autenticado pertecente ao grupo "Servidores" e que seja avaliador em ao menos uma sala.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

- Deve existir ao menos uma solicitação de reserva de sala.
- Usuário corrente dever ser avaliador de pelo menos uma sala.

Pós-condições
-------------

- É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
- É excluído no Painel de Notificação do avaliador o aviso de que existem agendamentos pendentes de avaliação.
  
  .. note::
     Ver RN4_
     

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ADMINISTRAÇÃO`` > ``Reservas de Salas`` > ``Acompanhamentos``
    #. O sistema exibe as solicitações de reservas disponíveis para reservas RIN1_
    #. O servidor seleciona a opção ``Solicitar Reserva`` 
    #. O servidor informa os dados (RIN2_)
    #. O servidor finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Editar (FN_.2 )
"""""""""""""""""""""

	#. O servidor aciona a opção ``Editar`` de uma das **ucs** disponíveis na listagem
	#. O sistema exibe a **uc** com os dados (RIN2_) preenchidos
	#. O servidor informa novos valores para os dados (RIN2_) 
	#. O servidor finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O servidor aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4 


FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O servidor aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo F1_.3 
	

FA4 - Listar (FN_.2)
""""""""""""""""""""

	#. O servidor restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior


FA5 - Visualizar (FN_.2)
""""""""""""""""""""""""

	#. O servidor aciona a opção ``Ver`` da **uc** que se deseja realizar o vínculo dentre uma das 
	   **ucs** disponíveis na listagem
	#. O sistema exibe informações da **uc** (RI1_)


.. _FA6:
	
FA6 - Remover (FA1_.2)
""""""""""""""""""""""

    #. O servidor aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M5_
    #. O servidor aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M6_
    #. O servidor confirma a exclusão.
    #. O sistema apresenta a listagem do passo FN_.2 
    	
    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1 (FA6_.1)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RIN1 – Campos para listagem de solicitações de reservas
"""""""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida dividida em abas conforme especificadas abaixo:

- Aba ``Qualquer``: lista todas as solicitações de reservas independente se foram avaliadas ou não.
- Aba ``Minhas reservas pendentes``: lista todas as solicitações de reservas que não foram avaliadas
- Aba ``Minhas reservas atendidas``: lista todas as solicitações de reservas avaliadas (deferidas/indeferidas)
- Aba ``Minhas avaliações pendentes``: lista todas as solicitações de reservas de salas na qual o usuário corrente
  é avaliador e que ainda não foram avaliadas
- Aba ``Minhas avaliações atendidas``: lista todas as solicitações de reservas de salas na qual o usuário corrente
  é avaliador e que já foram avaliadas.

     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Sala solicitada
     - Período solicitado
     - Deferido
     - Avaliação
   * - Ordenação
     - Não
     - Sim
     - Sim
     - Não
   * - Filtro
     - Não
     - Não
     - Sim
     - Não
   * - Busca
     - Não
     - Não
     - Não   
     - Não
   * - Observações
     - Ver RN5_
     
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
          Excluir
     - 
     -  Sim, Não
     -  Ver RN3_ e RN4_
     
        .. csv-table::
          :header: "Rótulo"
          :widths: 100

          ``Fechar Solicitação (perdeu prazo)``
          ``Avaliar Solicitação de reserva``
          
          
          

A `Figura 1`_ exibe um esboço de como esses dados serão exibidos.

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     
RIN1 – Campos para listagem
"""""""""""""""""""""""""""

É exibido a mesma lista definido no :ref:`suap-artefatos-adm-agendamento_salas-uc01-rin1` do caso de uso :ref:`suap-artefatos-adm-agendamento_salas-uc01`

.. note::
   Listar somente as salas disponíveis (ver :ref:`suap-artefatos-adm-agendamento_salas-uc01-rn1` do caso de uso :ref:`suap-artefatos-adm-agendamento_salas-uc01` ).

 
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
   * - Data/Hora inicial*
     - Calendário
     - 
     - 
     - | Data: dd/mm/yyyy
       | Hora: HH:MM
     - Dois campos, uma para a data e outro para a hora.
   * - Data/Hora final*
     - Calendário
     - 
     - 
     - | Data: dd/mm/yyyy
       | Hora: HH:MM
     - Dois campos, uma para a data e outro para a hora.
   * - Justificativa*
     - Texto longo
     - 
     - 
     - 
     - 
     
     
     
A `Figura 2`_ exibe um esboço do formulário de cadastro.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^
   
.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Critério para exibição das abas ``Minhas avaliações pendentes`` e `Minhas avaliações atendidas``: disponível apenas para o avaliador. 
       | mensagem: não há.
   * - RN2
     - | Critério para exibição da opção ``Avaliar Solicitação de reserva``:  essa opção só estará disponível para  avaliador e se a data final da 
       | solicitação seja menor ou igual a data atual.
       | mensagem: não há.  
   * - RN3
     - | Critério para exibição da opção ``Fechar Solicitação (perdeu prazo)``:  essa opção só estará disponível para o avaliador e se data final
       | da solicitação seja maior que a data atual.
       | mensagem: não há.  
   * - RN4
     - | O aviso de que existem agendamentos pendentes de avaliação disponível no Painel de Notificação só será excluído se não existir mais solicitações
       | de reservas a serem avaliadas.
       | mensagem: não há.   
   * - RN5
     - | Critério para exibição da opção excluir: essa opção só estará disponível se a solicitação de reserva ainda não foi avaliada.
       | de reservas a serem avaliadas.
       | mensagem: não há.    
 
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
     - **UC** <campo nome1> alterado com sucesso. Você pode adicionar um outro Diretoria Acadêmica abaixo.
   * - M4
     - **UC** <campo nome1> modificado com sucesso. Você pode editá-lo novamente abaixo.
   * - M5
     - Você tem certeza que quer remover **UC** "<campo nome1>"? Todos os seguintes itens relacionados serão removidos:    
   * - M6
     - Tem certeza que deseja continuar?       

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_    
.. _M5: `Mensagens`_
.. _M6: `Mensagens`_

    
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

.. comentário para usar o exemplo abaixo, basta recuar a margem.

	.. figure:: media/tela_uc**numero**_exibir.png
	   :align: center
	   :scale: 100 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 1: Protótipo de tela para exibição de **ucs**.
	   
	   
.. _`Figura 2`:

.. comentário para usar o exemplo abaixo, basta recuar a margem.
	   
	.. figure:: media/tela_uc**numero**.png
	   :align: center
	   :scale: 70 %
	   :alt: protótipo de tela.
	   :figclass: align-center
	   
	   Figura 2: Protótipo de tela para cadastro de **ucs**.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.