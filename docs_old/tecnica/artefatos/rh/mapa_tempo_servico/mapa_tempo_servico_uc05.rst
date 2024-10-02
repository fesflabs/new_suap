.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Nome do Subsistema** 

.. include:: ../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-rh-mapa_tempo_servico-uc05:

UC 05 - Simular tempo de serviço <v0.1>
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
   * - 05/05/2014
     - 0.1
     - Início do Documento
     - George Carvalho 
    

Objetivo
--------

Simula o tempo de serviço do servidor para fins de aposentadoria.

Atores
------

.. note::
   Os atores que interagem com este caso de uso são listados aqui.São atores pessoas, sistemas, dispositivos 
   que fornecem ou recebem estímulos (fornecem ou recebem informações) do sistema sob  análise.   

Principais
^^^^^^^^^^

.. note::
   Ator principal é aquele que interage com o sistema (fornece, altera, excluí informações no sistema)

Interessado
^^^^^^^^^^^

.. note::
   Ator interessado é aquele (alguém ou algo) com interesse no comportamento do sistema. Nem sempre só os atores
   são interessados no caso de uso. Um setor de contabilidade pode estar interessado nas vendas da empresa ou 
   o estoque pode querer saber quais produtos foram vendidos.

Pré-condições
-------------

.. note::
    Nesta seção, é definido o que deve ser verdade antes do início da execução do caso de uso. É a condição 
    essencial para que o caso de uso possa ser realizado. Devem ser listadas as assertivas e condições validadas 
    antes de entrar no caso de uso. Como exemplo, pode-se citar que, se esta condição não for verdadeira, um 
    cadastro não poderá ser efetuado ou nem mesmo o fluxo do caso de uso poderá ser iniciado. Representa o 
    estado em que um outro caso de uso anterior deixa o sistema para que o caso de uso em questão possa ser 
    iniciado

Pós-condições
-------------

.. note::
    Aqui deve ser descrito o que deve ser verdadeiro quando o processo terminar com sucesso, mostrando o resultado 
    após a execução do caso de uso. Deve-se colocar as criações de objetos, alterações de valores de atributos, 
    associações formadas ou desfeitas, ou destruições de objetos. Verificar se os fluxos alternativos levam a 
    diferentes pós-condições.

Fluxo de Eventos
----------------

.. note::
    Este caso de uso começa quando o ator faz algo ou quando é chegada a hora de algo ser feito (no caso de 
    processamento batch). O caso de uso deve descrever o que o ator faz e o que o sistema faz como resposta, 
    mas não como ou porquê, evite descrever processos internos ao sistema. Deve ter o formato de um diálogo 
    entre o ator e o sistema e deve apresentar uma linguagem simples e de fácil entendimento por todos os 
    envolvidos. Se há troca de informação, seja específico sobre o que é passado para o sistema e vice-versa.

    Evite mencionar componentes de tela como botão, combo e outros. Por exemplo: Não é muito esclarecedor 
    dizer que o ator clica no botão “Gerar Turma”, é melhor dizer que o ator inicia o caso de uso acionando 
    a opção “Gerar Turma”;

    .. warning::
        Foi definido que quando for uma seleção, evite descrevê-la em dois passos, por exemplo: 1. “O sistema exibe 
        os Horários de Câmpus”;  2.“O ator seleciona o Horário do câmpus. Apenas o útlimo passo é necessário.

        Ao passar a informação, foi definido colocar entre aspas duplas (“ ”) o nome do campo e este será 
        usado como rótulo na tela, se o campo for obrigatório, incluir um asterisco (*) depois do nome. Se 
        for necessário relacionar o passo com alguma regra de negócio (RN), requisito de interface (RI), etc, 
        incluir no final do passo entre parênteses. Exemplo: O ator seleciona o “Período Letivo*” (RN1, RI1, etc).

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção ``Gestão de Pessoas`` > ``Mapa de tempo de serviço`` > ``Simulação`` (RI1_)
    #. O operador do RH entra com a matrícula ou nome do servidor e uma data de referência para simulação
    #. O sistema exibe o tempo efetivo de serviço até a data de referência, considerando os tempos limites para aposentadoria 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. note::
    Aqui serão tratados todos os fluxos que não obedecem à forma normal de execução, isto é, são eventos 
    alternativos do caso de uso, configurando cenários diferentes ou tratando outras funcionalidades, como, 
    por exemplo, uma alteração ou uma exclusão. Quando o fluxo alternativo ou de exceção termina, nem sempre 
    os eventos do fluxo original são retomados no mesmo ponto. Sendo assim, é necessário indicar o ponto de 
    retomada do fluxo, que pode ser: retorna, avança ao passo x do fluxo normal.

    Pode haver, e normalmente haverá, um certo número de fluxos alternativos em um caso de uso. Mantenha cada um 
    separado para melhorar a clareza. O uso de fluxos alternativos melhora a legibilidade do caso de uso e previne 
    que eles sejam decompostos em hierarquias. Caso perceba que seu caso de uso está tendo muitos fluxos alternativos, 
    talvez isso indique que o caso de uso respectivo deve ser particionado em mais casos de uso. Isso tornará a 
    escrita e entendimento do caso de uso mais fácil.


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
