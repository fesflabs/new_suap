
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Cursos** 

.. include:: ../../header.rst
   :start-after: docvisao-start
   :end-before: docvisao-end

.. _suap-artefatos-rh-cursos-visao:

Documento de Visão do Subsistema Cursos <v0.1>
==============================================

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
   * - 18/03/2014
     - 0.1
     - Início do Documento
     - 
    

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

A finalidade do sistema é controlar a carga horária trabalhada pelos servidores em cursos e concursos. As horas trabalhadas serão remuneradas em contra-cheque na rubrica 66 e, por definição, existe um limite de 240 horas trabalhadas por ano para cada servidor.    


Motivações, necessidades e problemas
------------------------------------

A motivação para o desenvolvimento do módulo foi a dificuldade para controlar manualmente, em planilhas eletrônicas, a carga horária trabalhada por cada servidor e, muitas vezes, o controle não era suficiente para evitar que os servidores trabalhassem mais de 240 horas num ano. Sem o devido controle, os servidores poderiam ser remunerados em mais de 240 horas ou os servidores trabalhavam num curso/concurso e o pagamento não era autorizado.

Projeto da solução
------------------

Não se aplica.

Descrição dos papeis
--------------------

Papel das partes interessadas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   
.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Representante
     - Responsabilidades
   * - Raul Aleixandre (DIGPE)
     - Fornecer requisitos; testar o software.
   
Papel dos atores
^^^^^^^^^^^^^^^^ 

.. list-table:: 
   :widths: 10, 90
   :header-rows: 1
   :stub-columns: 0

   * - Ator
     - Descrição
   * - Visualizador de Cursos e Concursos
     - Servidor comum que apenas pode visualizar as próprias horas trabalhadas.
   * - cursos_auditor
     - Esse perfil tem a permissão de visualizar todas as informações, mas sem poder alterá-las.
   * - Operador de Cursos e Concursos
     - Responsável por alimentar o sistema.

Visão geral do produto
----------------------

Modelagem de processos de negócio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: images/atividade.png

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
     - A quantidade de horas trabalhadas por um servidor num ano não pode exceder 240 horas.
     - Especificação
   * - R02
     - Um servidor não deve visualizar as horas trabalhadas de um outro servidor.
     - Segurança
     
Casos de uso
^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód
     - Nome
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - UC01
     - :ref:`suap-artefatos-rh-cursos-uc01` 
     - 
     - Baixa
     -      
   * - UC02
     - :ref:`suap-artefatos-rh-cursos-uc02` 
     - 
     - Baixa
     -      
   * - UC03
     - :ref:`suap-artefatos-rh-cursos-uc03` 
     - 
     - Média
     -      
   * - UC04
     - :ref:`suap-artefatos-rh-cursos-uc04` 
     - 
     - Média
     - R01
   * - UC05
     - :ref:`suap-artefatos-rh-cursos-uc05` 
     - 
     - Baixa
     -      
   * - UC06
     - :ref:`suap-artefatos-rh-cursos-uc06` 
     - 
     - Baixa
     -      
   * - UC07
     - :ref:`suap-artefatos-rh-cursos-uc07`  
     - 
     - Baixa
     -      
   * - UC08
     - :ref:`suap-artefatos-rh-cursos-uc08` 
     - 
     - Baixa
     - R01
   * - UC09
     - :ref:`suap-artefatos-rh-cursos-uc09`  
     - 
     - Baixa
     -      
   * - UC10
     - :ref:`suap-artefatos-rh-cursos-uc10` 
     - 
     - Baixa
     -      
   * - UC11
     - :ref:`suap-artefatos-rh-cursos-uc11` 
     - 
     - Média
     - R02           

Diagrama de caso de uso
^^^^^^^^^^^^^^^^^^^^^^^

.. image:: images/cursos_operador.png

.. image:: images/cursos_auditor.png

.. image:: images/cursos_comum.png
     
Diagrama de modelagem de domínio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. image:: images/diagram_classe.png

Questões em aberto
------------------

Não se aplica.
