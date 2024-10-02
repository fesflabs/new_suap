.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Nome do Subsistema** 

.. include:: ../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-mapa_tempo_servico-uc04:

UC 04 - Exibir histórico do servidor <v0.1>
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
   * - 05/05/2014
     - 0.1
     - Início do Documento
     - George Carvalho 
   * - 06/05/2014
     - 0.1
     - Início do Documento
     - Esdras Valentim 
    

Objetivo
--------

Exibe o histórico funcional do servidor (averbações e serviços especiais serão mostrados em formato resumido).

Atores
------

Principais
^^^^^^^^^^

Operador do RH


Interessado
^^^^^^^^^^^

Servidor


Pré-condições
-------------

O Servidor e as averbações devem estar cadastradas no sistema.

Pós-condições
-------------

O histórico, com a vida funcional do Servidor, é exibido.

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção ``Gestão de Pessoas`` > ``Mapa de tempo de serviço`` > ``Histórico do servidor`` (RI1_)
    #. O operador do RH entra com a matrícula ou nome do servidor
    #. O operador do RH finaliza o caso de uso acessando sua ficha cadastral e selecionando a guia/aba ``Histórico funcional`` 
    #. O sistema exibe o histórico funcional do servidor


Fluxo Alternativo
^^^^^^^^^^^^^^^^^


FA1 – Nome do fluxo alternativo (FN_.1)
"""""""""""""""""""""""""""""""""""""""

.. note::
    Sempre que for descrever uma fluxo alternativo, use está subseção como exemplo. Aqui temos:
    Identificação do fluxo -  Nome do Evento (identificação do passo do fluxo normal)
    
    Exemplos:
    
    FA1 – Editar (FN_.2 )
    """""""""""""""""""""

	   #. O administrador aciona a opção ``Editar`` de uma das diretoria acadêmica disponíveis na listagem
	   #. O sistema exibe a diretoria acadêmica com os dados (RIN2_) preenchidos
	   #. O administrador informa novos valores para os dados (RIN2_) 
	   #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
	   #. O sistema exibie a mensagem M2_.
	   #. O sistema apresenta a listagem do passo FN_.2 
    

Fluxo de Exceção
^^^^^^^^^^^^^^^^

.. note::
    Neste tópico, devem ser descritas todas as exceções, isto é, todas as circunstâncias ou situações que se 
    não for devidamente tratado impede o prosseguimetno do caso de uso. Como, por exemplo, uma exclusão que 
    não pode acontecer. 

    Quando a exceção acontecer em um fluxo alternativo, indicar o passo específico em que pode ocorrer

    .. warning::
        Foi definido que para as regras de negócio na qual possui apenas um passo (o sistema exibe a mensagem M1_) 
        não será necessário criar um fluxo de exceção.

    Exemplo: 
    
FE1 – Nome do fluxo de exceção (FN_.2)
""""""""""""""""""""""""""""""""""""""

.. note::
    Sempre que for descrever uma exceção, use está subseção como exemplo. Aqui temos:
    Identificação do fluxo -  Nome do Evento (identificação do passo do fluxo normal/alternativo)

Especificação suplementares
---------------------------

.. note::
    Informe as regras de negócio, requisitos não funcionais: requisitos de hardware e software, requisitos de 
    desempenho, requisitos de segurança, dentre outros.

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    Informe os requisitos de padrão, requisitos de hardware e software, requisitos de desempenho (tempo de 
    resposta), requisitos de segurança, dentre outros requisitos não-funcionais.  
    
    Ver :ref:`suap-models-recnaofuncionais-categoria`)
    
    Para cada tipo de requisito será criada uma subseção.
    

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. note::
    Neste tópico é possível registrar alguma particularidade sobre a interface quando solicitada pelo cliente. 
    Por exemplo:  
    RI1 – Exibição do calendário
    Destacar no calendário a cor vemelha nos dias de indisponibilização da sala.
	
	RI1 – Exibição do campo XXX
	Se um determinado campo for selecionado, então o campo XXX deve ser desabilitado.

    Procure sempre utilizar os padrões de usabiliade definidos para o SUAP.


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

RIN1 – Campos para listagem
"""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Coluna 1
     - Coluna 2
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

.. note:: 
    Liste aqui somente os campos que possuem uma certa particularidade, como por exempo:máscara específica, 
    domínio não conhecido, oculto para o usuário, possui valor inicial, tamanho bem definido. 
    Pode ser necessário especifiar tipo, tamanhao, obrigatoriedade, valor inicial, máscara, 
    oculto [S/N], domínio.
    
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
   * - Nome campo*
       .. note:: * -> campo obrigatório
     - 
       .. note::
       
          - use "texto autocompletar simples" para ForeignKeyPlus e 
          - texto "autocompletar multiplo" para MultipleModelChoiceFieldPlus
          - texto longo para Textarea
          - text
          - seleção
          - seleção multipla 
          - Data/Hora
          - texto (somente leitura)
          
     - 
     - 
     - 
     - 
       .. note::
          Em observação pode se incluir o texto que aparece logo abaixo do campo como dica.
          
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. note:: 
    Descreva aqui as regras de negócio e para cada uma a mensagem que será exibida ao ator.

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Nome da regra
       | Mensagem 
   
Mensagens
^^^^^^^^^

.. note:: 
    Neste tópico são descritas todas as mensagens que o sistema apresenta ao ator, exceto as mensagens descritas nas regras de negócio.

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Código
     - Descrição
   * - M1    
     - 
     
.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_        
     
.. _PE:
     
Ponto de Extensão
-----------------
- :ref:`Diagrama de caso de uso <diagramaUC>`

.. note:: 
    Neste tópico são descritos a(s) referência(s) ao(s) diagrama(s) de caso de uso que possuem relacionamento 
    de extensão.
    
    O caso de uso base pode ser executado mesmo sem a extensão.

Questões em Aberto
------------------

.. note:: 
    Registre aqui as dúvidas encontradas que precisam da presença do cliente para serem sanadas. No final da 
    fase de análise espera-se que todas as questões em aberto tenham sido resolvidas e incorporadas ao resultado
    da análise, ou seja, à descrição do caso de uso expandido.

Esboço de Protótipo
-------------------

.. note:: 
    Se melhorar a clareza, use protótipo de interface de usuário.
    Esta seção define um esboço inicial da interface deste caso de uso, sem definir tecnologia, ferramentas, 
    etc., mas somente um desenho de linhas e textos representando menus, botões, campos e outros. Esse esboço 
    pode ser feito pelo próprio cliente (usuário). Caso esse protótipo já tenha sido feito em outro documento, 
    basta fazer uma referência ao mesmo.

Diagrama de domínio do caso de uso
----------------------------------
- :ref:`Diagrama de domínio <diagramaDominio>`

.. note::  
    Um diagrama de domínio pode ser representado por um diagrama de classe conceitual, isto é, uma representação
    das informações trocadas entre o ator e o sistema definidas no fluxo de eventos. Ele é independente de 
    implementação (linguagem).

    Recomenda incluir nas classes somente os atributos que sofreram alterações decorrentes do caso de uso, para 
    as demais especificar apenas os relacionamentos.

Diagrama de Fluxo de Operação
-----------------------------

.. note::  
    Se um diagrama de fluxo for útil para apresentar um processo de decisão complexo, use-o. Similarmente para 
    um comportamento dependente de estado, um diagrama de transição de estados frequentemente esclarece melhor 
    do que páginas e páginas de texto. Use a melhor forma para representar o seu problema, mas cuidado para não 
    usar terminologia, notação ou figura que sua audiência não possa compreender. Lembre-se de que sua finalidade
    é esclarecer, não confundir.

Cenário de Testes
-----------------

Objetivos
^^^^^^^^^

O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
esperados que visam validar esse caso de uso.

Casos e Registros de Teste
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note::   
    Identifique (Tipo de Teste) se o teste é relativo a um fluxo alternativo, de exceção, regra de negócio, 
    permissão.

Fluxo de Exceção FE1
""""""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Texto com o objetivo do teste
   * - Dados de Entrada
     - Texto descrevendo os dados de entrada
   * - Resultado Esperado
     - Texto descrevendo o resultado esperado.
