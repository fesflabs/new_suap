
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Nome subistema** 

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
   * - 25/04/2014
     - 0.1
     - Início do Documento
     - 

.. note::
    Os textos que aparecem em azul e entre colchetes são explicações para ajudar no preenchimento de cada seção e 
    devem ser apagados no documento final.

    Preencha nesta página inicial o nome do produto (subsistema). Mantenha o histórico de registros sempre 
    atualizado, indicando a versão atual do documento. As seções que não forem preenchidas, por qualquer motivo, não 
    devem ser removidas. Deve-se acrescentar o texto ``Não há`` ou ``Não se aplica``.

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

.. note::  
    Descrever a finalidade do sistema.    

.. finalidade_end

Análise de contexto
-------------------

Cenário
^^^^^^^

.. note:: 
   Seção utilizada para documentar novos produtos.
   
   Forneça uma descrição do cenário atual, apresentando o contexto e os macroprocessos como são hoje, que possam motivar o 
   desenvolvimento de uma solução.
    
   .. warning::
      Caso esteja documentando um produto já existente incluir o texto "Não se aplica."

Motivações, necessidades e problemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::  
    A partir do cenário descrito acima, identifique e descreva as possíveis motivações, necessidades e problemas.
    
    Dicas para descrever as necessidades:
    
    - Descrição da necessidade;
    - Qual a solução utilizada atualmente para o atendimento desta necessidade;
    - Qual seria uma solução proposta para o atendimetno desta necessidade.
    
    Dicas para descrever o problema:
    
    - Descrição do problema levantado;
    - Quais são os interessados afetados pelo problema;
    - Qual o impacto do problema;
    - Qual seria uma solução proposta para o problema apresentado.

   .. warning::
      Caso esteja documentando um produto já existente, pode-se incluir o texto "Não se aplica." nesta seção.
      
Escopo do produto
-----------------

Declaração do escopo do produto
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: 
   Seção utilizada para documentar novos produtos.  
   
   Forneça a declaração do escopo do produto, descrevendo as características do produto, serviço ou resultado que se
   deseja obter com a execução do projeto.

   .. warning::
      Caso esteja documentando um produto já existente incluir o texto "Não se aplica."
   
Não faz parte do escopo
^^^^^^^^^^^^^^^^^^^^^^^

.. note:: 
   Seção utilizada para documentar novos produtos.
   
   Descreva de forma explícita as características que não fazem parte do produto. Em muitos casos, é mais fácil declarar que
   certos comportamentos nunca poderão ocorrer. Exemplo:
   
   - O sistema não fará controle financeiro;
   - O sistema não fará estatísticas mensais.

   .. warning::
      Caso esteja documentando um produto já existente incluir o texto "Não se aplica."
   
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
   :widths: 10, 20, 70
   :header-rows: 1
   :stub-columns: 0

   * - Ator
     - Sinônimo
     - Descrição
   * - <Preencher com o nome do ator.>
     - Se o nome do papel for diferente do nome do grupo do SUAP, coloque aqui o nome do grupo no SUAP que representa esse papel.
       As vezes quando se tem vários clientes, pode ocorrer divergência de nomes entre eles, para evitar confusão, coloque aqui
       os diferentes nomes (sinônimos) 
     - <Descrição das responsabilidades do ator em relação ao sistema.>      

Visão geral do produto
----------------------

Modelagem de processos de negócio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Cole aqui um diagrama de atividade para representar os processos de negócio (conjunto de atividades que ocorrem em algum negócio 
   com o objetivo de gerar um produto ou serviço, alcançando determinado objetivo). Esse diagrama fornece o entendimento de como são
   realizadas as diversas atividades contidas em cada processo.

Projeto da solução
^^^^^^^^^^^^^^^^^^

.. note::
   Descreva aqui os elementos do modelo de projeto, que são importantes para a arquitetura, a estrutura de camadas e componentes do
   projeto.
   
   
Perspectiva do produto
^^^^^^^^^^^^^^^^^^^^^^ 
   
Integração com outros sistemas
""""""""""""""""""""""""""""""

.. note::
   Descreva aqui as interfaces de software com outros componentes do sistema de software. Poderão se componentes comparados, 
   componentes reutilizados de outro aplicativo ou componentes que estão sendo desenvolvidos para subsistemas fora do escopo desta,
   mas com os quais esse aplicativo de software deve interagir
   Identificam-se aqui as interfaces com outros produtos de software, tais como aplicativos que recebem dados do produto ou 
   enviam dados para ele, seja on-line, através de arquivos ou através de banco de dados. Não incluir componentes normais 
   do ambiente operacional, como bibliotecas e plataformas.
   Ao descrever as interfaces de software, informe o nome do componente/sistema, a descrição, a forma de entrada de dados 
   e/ou a forma de saída de dados.

Relacionamentos com outros subsistemas
""""""""""""""""""""""""""""""""""""""

.. note::
   Nesta subseção apresente a relação que o produto tem com outros produtos e o ambiente do usuário. Informe se o
   produto é independente e autossuficiente. Se o produto for um componente de um sistema maior, descreva como
   esses sistemas interagem e quais as interfaces relevantes entre os sistemas. Se o produto possuir vários módulos, 
   estes deverão ser listados nesta subseção.


Requisitos
^^^^^^^^^^

.. note::
   Descreva os requisitos funcionais e não funcionais do produto. 
   Foi decidido que não haverá divisão entre requisitos funcionais e não funcionais.
   
   Para requisitos funcionais, pode-se categorizar como "Especificação"
      

.. list-table:: 
   :widths: 10 60 30
   :header-rows: 1
   :stub-columns: 0

   * - Cód
     - Descrição
     - Categoria
   * - <identificador único do requisito, use R<numero_sequencial>, exemplo R01, R02>
     - <descrição>
     - <Categoria do requisito (ver :ref:`suap-models-recnaofuncionais-categoria`)>  	
     
Casos de uso
^^^^^^^^^^^^

.. note::
   Listar e descrever resumidamente as funcionalidades que se espera encontrar no produto. Funcionalidades são capacidades que o 
   produto deve ter para atender a uma necessidade de usuário (ator). Cada funcionalidades descreve um serviço percebido pelo usuário 
   e que tipicamente requer entradas para alcançar o resultado desejado. À medida que o modelo de casos de uso for desenvolvido, 
   atualize a descrição para fazer referência aos casos de uso. Cada funcionalidade será descrita mais detalhadamente no modelo de 
   casos de uso. É recomendado ordernar os casos de uso por ordem de decrescente de prioridade.     


.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-sistema-subsistema-uc01` 
     - 
       .. include:: subsistema_uc01.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R01

Diagrama de caso de uso
^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Cole aqui o diagrama de caso de uso
     
Diagrama de modelagem de domínio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Cole aqui o diagrama de classe domínio.


Metas gerenciais
----------------

.. note::
   Exemplo: O projeto deverá ser executado até o mês de Agosto de 2014.
   
   .. warning::
      Caso esteja documentando um produto já existente incluir o texto "Não se aplica."

Questões em aberto
------------------

.. note::
   Descrever as anotações técnicas para informações adicionais a serem trabalhadas no futuro ou lembretes, e questões pendentes 
   que devam ser esclarecidas durante a especificação de requisitos.   
   
Encerramento de Projetos
------------------------

.. note::
   Esta seção visa além de formalizar o término do projeto discutir como foi o mesmo e coletar lições aprendidas. No processo de 
   gerenciamento de projetos ele é o documento final. Durante o encerramento é interessante tratar assuntos como:
   
   - Os produtos previstos no projeto foram concluídos
   - O objetivo final do projeto foi alcançado
   - O resultado alcançado está coerente com a justificativa apresentada
   - Quais os principais problemas do projeto
   - Discutir sobre as lições aprendidas
   - Registrar na base de conhecimento da organização   
   
   .. warning::
      Caso esteja documentando um produto já existente incluir o texto "Não se aplica."   