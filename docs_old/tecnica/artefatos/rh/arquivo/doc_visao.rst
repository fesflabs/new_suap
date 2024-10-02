
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Arquivo** 

.. include:: ../../header.rst
   :start-after: docvisao-start
   :end-before: docvisao-end

.. _suap-artefatos-rh-ponto-visao:

Documento de Visão do Subsistema Ponto <v0.1>
=============================================

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

.. note::  
    Descrever a finalidade do sistema.    


Motivações, necessidades e problemas
------------------------------------

.. note::  
    Identifique e descreva as possíveis motivações, necessidades e problemas.
    
    Dicas para descrever as necessidades:
    
    - Descrição da necessidade;
    - Qual a solução utilizada atualmente para o atendimento desta necessidade;
    - Qual seria uma solução proposta para o atendimetno desta necessidade.
    
    Dicas para descrever o problema:
    
    - Descrição do problema levantado;
    - Quais são os interessados afetados pelo problema;
    - Qual o impacto do problema;
    - Qual seria uma solução proposta para o problema apresentado.

Projeto da solução
------------------
.. note::
   Descreva aqui os elementos do modelo de projeto, que são importantes para a arquitetura, a estrutura de camadas e componentes do
   projeto, os relacionamentos com outros módulos e a integração com outros sistemas. 

Descrição dos papeis
--------------------

Papel das partes interessadas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Esta seção fornece as desrições de todas as partes interessadas no desenvolvimento da solução, considerando-se os papéis
   e responsabilidades. Entende-se como partes interessadas, os envolvidos que podem contribuir de várias maneiras para o 
   desenvolvimento da solução, bem como os que influenciam ou são influenciados pela solução.
   
   
.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Representante
     - Responsabilidades
   * - <Identifique o(s) envolvido(s) (nome do cargo, departamento) que representa(m) o papel.>. 
     - <Descreve brevemente o que o papel representa com relação ao desenvolvimento da solução>
   
Papel dos atores
^^^^^^^^^^^^^^^^   

.. list-table:: 
   :widths: 10, 90
   :header-rows: 1
   :stub-columns: 0

   * - Ator
     - Descrição
   * - <Preencher com o nome do ator.>
     - <Descrição das responsabilidades do ator em relação ao sistema.>      

Visão geral do produto
----------------------

Modelagem de processos de negócio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Cole aqui um diagrama de atividade para representar os processos de negócio (conjunto de atividades que ocorrem em algum negócio 
   com o objetivo de gerar um produto ou serviço, alcançando determinado objetivo). Esse diagrama fornece o entendimento de como são
   realizadas as diversas atividades contidas em cada processo.

Requisitos
^^^^^^^^^^
.. note::
   Descreva os requisitos funcionais e não funcionais do produto. 
   Foi decidido que não haverá divisão entre requisitos funcionais e não funcionais.
   
   :ref:`suap-models-recnaofuncionais-categoria` 

.. list-table:: 
   :widths: 10 60 30
   :header-rows: 1
   :stub-columns: 0

   * - Cód
     - Descrição
     - Categoria
   * - <identificador único do requisito, use R<numero_sequencial>, exemplo R01, R02>
     - <descrição>
     - <Categoria do requisito>  	
     
Casos de uso
^^^^^^^^^^^^

.. note::
   Listar e descrever resumidamente as funcionalidades que se espera encontrar no produto. Funcionalidades são capacidades que o 
   produto deve ter para atender a uma necessidade de usuário (ator). Cada funcionalidades descreve um serviço percebido pelo usuário 
   e que tipicamente requer entradas para alcançar o resultado desejado. À medida que o modelo de casos de uso for desenvolvido, 
   atualize a descrição para fazer referência aos casos de uso. Cada funcionalidade será descrita mais detalhadamente no modelo de 
   casos de uso. É recomendado ordernar os casos de uso por ordem de decrescente de prioridade.     

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
     - :ref:`suap-artefatos-rh-ponto-uc01` 
     - 
     - 
     -                

Diagrama de caso de uso
^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Cole aqui o diagrama de caso de uso
     
Diagrama de modelagem de domínio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Cole aqui o diagrama de classe domínio.

Questões em aberto
------------------

.. note::
   Descrever as anotações técnicas para informações adicionais a serem trabalhadas no futuro ou lembretes, e questões pendentes 
   que devam ser esclarecidas durante a especificação de requisitos.
