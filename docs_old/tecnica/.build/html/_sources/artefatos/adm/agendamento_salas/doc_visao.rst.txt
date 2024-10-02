
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Agendamento de Salas** 

.. include:: ../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-models-docvisao-produto-template:

Documento de Visão do Subsistema |titulo| <v0.1>
================================================

.. contents:: Conteúdo
    :local:
    :depth: 4    

Histórico da revisão
--------------------

.. list-table:: **Histórico da Revisão**
   :widths: 10 5 30 15
   :header-rows: 1
   :stub-columns: 0

   * - Data
     - Versão
     - Descrição
     - Autor
   * - 08/04/2014
     - 0.1
     - Início do Documento
     - |Jailton Carlos


Introdução
----------

Finalidade do documento
^^^^^^^^^^^^^^^^^^^^^^^

A finalidade deste documento é especificar os requisitos relevantes do usuários, assim como os limites e restrições evidentes que 
dão uma visão geral. Essa visão viabiliza a identificação e a produção de documentos e requisitos mais técnicos, assim como do 
próprio sistema. A visão serve como forma de permitir a compreensão, pelos participantes do projeto, do "o quê e por quê" o projeto 
existe e provê uma estratégia a partir da qual todas as futuras decisões podem ser validadas. 

Finalidade do sistema
^^^^^^^^^^^^^^^^^^^^^
.. finalidade_start

A finalidade do subsistema Gerenciamento de Salas é prover funcionalidades que permitam um melhor controle do gerenciamento de salas
dos diversos campi do IFRN.  

.. finalidade_end

Análise de contexto
-------------------

Cenário
^^^^^^^

Não se aplica.

Motivações, necessidades e problemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Não se aplica.
      
Escopo do produto
-----------------

Declaração do escopo do produto
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Espera-se obter com uso do sistema, um maior controle da agenda da sala:

 - O servidor terá conhecimento da agenda de uma determinada sala;
 - O agendamento da sala só será efetivo após uma aprovação previa por um avaliador;
 - Todos os envolvidos no agendamento receberam emails com informações sobre a agenda; 
 - Evitação de conflitos de agendas, não será possível agendar uma sala previamente agendada.
 
    
Não faz parte do escopo
^^^^^^^^^^^^^^^^^^^^^^^

- O sistema não fará o controle de utilização de chaves das salas.
   
Descrição dos papeis
--------------------

Papel das partes interessadas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

   
.. list-table:: 
   :widths: 50 50
   :header-rows: 1
   :stub-columns: 0

   * - Representante
     - Responsabilidades
   * - | Von Klaus Dantas Bezerra 
       | (SECRETARIO EXECUTIVO (PCIFE)/IFRN → RE → GABIN/RE → SEC/RE) 
     - Fornecedor de Requisitos: fornecer informações sobre o domínio do sistema; testar funcionalidades.
   
Papel dos atores
^^^^^^^^^^^^^^^^   

.. list-table:: 
   :widths: 10, 20, 70
   :header-rows: 1
   :stub-columns: 0

   * - Ator
     - Sinônimo
     - Descrição
   * - Servidor
     - 
     - Solicita reserva de salas, acompanha solicitações.     
   * - Operador de Chaves
     - chaves_operador
     - Informa se a sala está disponível para agenda e informa quais são os avaliadores de uma determinada sala.
   * - Avaliador
     - 
     - Servidor que está associado como avaliador de uma sala, defere ou indefere solicitações de reservas.      
      

Visão geral do produto
----------------------

Modelagem de processos de negócio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Projeto da solução
^^^^^^^^^^^^^^^^^^

Não se aplica.
   
   
Perspectiva do produto
^^^^^^^^^^^^^^^^^^^^^^ 
   
Integração com outros sistemas
""""""""""""""""""""""""""""""

Não há.

Relacionamentos com outros subsistemas
""""""""""""""""""""""""""""""""""""""

- Integra-se com o subsistema de Gestão de Pessoa para obter os dados do servidor;
- Integra-se com o subistema de Patrimônio para obter os dados da sala.


Requisitos
^^^^^^^^^^


.. list-table:: 
   :widths: 10 60 30
   :header-rows: 1
   :stub-columns: 0

   * - Cód
     - Descrição
     - Categoria
   * - R01
     - O sistema deve permitir compartilhar uma agenda com outros servidores
     - Especificação  	
   * - R02
     - O sistema deve permitir reservar salas na mesma data e hora, nesse caso a reserva entrará em uma fila de reservas;
     - Especificação
   * - R03
     - Solicitações fora do prazo serão indeferidas automáticamente
     - Especificação   
   * - R04
     - O sistema deve enviar emails para os solicitantes de reserva de sala após uma avaliação, independente se deferida ou não
     - Especificação        
   * - R05
     - Um email deve ser enviado para o avaliador a cada solicitação de sala, caso ele seja o responsável por avaliar aquela sala
     - Especificação        
   * - R06
     - O sistema deve permitir informar se a sala está disponível para agenda e também quais são os seus respectivos avaliadores
     - Especificação        
   * - R07
     - O sistema deverá permitir indisponibilizar uma sala por um determinado período.
     - Especificação        
   * - R08
     - Uma solicitação de reserva de sala só será entrar em vigor (entrar na agenda da sala) após ser deferida por um avaliador. 
     - Especificação               
   * - R09
     - O servidor poderá consultar a agenda atual da sala. Destacar na agenda a cor:
     
       - Amarela: para solicitações de reserva;
       - Verde: para agenda deferida
       - Vermelho: para sala indisponível.
     - Especificação    
   * - R10
     - O sistema deve permitir que um servidor acompanhe as suas solicitações de reservas
     - Especificação                   
   * - R11
     - O sistema deve permitir que um avaliador acompanhe todas as solicitações de reservas de salas na qual ele é responsável
     - Especificação  
   * - R12
     - O sistema deve permitir que um avaliador cancela uma agenda (solicitação de reserva deferida)
     - Especificação     
   * - R13
     - O sistema deve permitir que um servidor cancele uma solicitação de reserva apenas quando a mesma não tiver sido avaliada
     - Especificação     
   * - R14
     - Um email será enviado para todos os envolvidos quando uma agenda é cancelada.
     - Especificação     
 
     
               
Casos de uso
^^^^^^^^^^^^


.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-adm-agendamento_salas-uc01` 
     - 
       .. include:: agendamento_salas_uc01.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R6
   * - :ref:`suap-artefatos-adm-agendamento_salas-uc02` 
     - 
       .. include:: agendamento_salas_uc02.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R1, R2, R5, R09, R10, R13
   * - :ref:`suap-artefatos-adm-agendamento_salas-uc03` 
     - 
       .. include:: agendamento_salas_uc03.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R07
   * - :ref:`suap-artefatos-adm-agendamento_salas-uc04` 
     - 
       .. include:: agendamento_salas_uc04.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R4, R08
   * - :ref:`suap-artefatos-adm-agendamento_salas-uc06` 
     - 
       .. include:: agendamento_salas_uc06.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R09, R11, R13



Diagrama de caso de uso
^^^^^^^^^^^^^^^^^^^^^^^

Lengenda:

- Cor azul: Em produção e documentado
- Cor amarelo: Em produção e não documentado
- Cor verde: Novos e documentado
- Cor Vermelho: Novos e não documentados

.. _`Figura 1`:

.. figure:: media/diagrama_casos_uso.png
   :align: center
   :scale: 70 %
   :alt: Diagrama caso de uso.
   :figclass: align-center
   
   Figura 1: Diagrama de caso de uso.	   
     
Diagrama de modelagem de domínio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Não há.

Metas gerenciais
----------------

Não há.


Questões em aberto
------------------

Não ha.  
   
Encerramento de Projetos
------------------------

Não se aplica.