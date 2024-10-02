
.. _suap-models-recnaofuncionais-categoria:

Classificação dos Requisitos Não Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requisitos não funcionais são as características e aspectos internos do sistema, eles mapeiam os aspectos qualitativos de um software, por exemplo: performance (tempo de resposta); 
segurança (restrições de acesso, privilégios); perspectiva do usuário (padrão das cores, disposição dos objetivos na tela); 
comunicabilidade (e-mail, VoIP, Browser); usabilidade e portabilidade (a aplicação deve rodar em vários tipos de aplicativos: 
móveis, desktop, note).  Este grupo é de suma importância e não deve ser desprezado durante o processo de produção de software. 
Como qualquer outro tipo de requisito, ele deve ser levantado, analisado, especificado e validado. Uma dificuldade indentificar
esse tipo de requisito é que eles não são explicitamente expostos pelo cliente, mas devem ser implicitamente compreendidos pelo desenvolvedor.

.. note::

	.. list-table:: **Catogira de requisitos**
	   :widths: 10 90
	   :header-rows: 1
	   :stub-columns: 0
	
	   * - Categoria
	     - O que descrever
	   * - Requisitos de Padrão
	     - Liste todos os padrões com os quais o produto deverá estar em conformidade. Entre eles, poderão estar incluídos
	       padrões legais, padrões de comunicações, padrões de qualidade e de segurança.
	   * - Requisitos de Sistema
	     - Defina todos os requisitos de sistema, no que se refere a hardware e software, necessários para o desenvolvimento,
	       suporte e uso do aplicativo. Entre eles, poderão estar incluídos os sistemas operacionais, as plataformas de rede
	       suportadas, linguagem de programação, configurações de hardware, etc.
	   * - Requisitos de Desempenho
	     - Descreva os requisitos de desempenho. Itens referentes a carga do usuário, largura de banda, taxa de transferência,
	       confiabilidade e tempos de resposta podem ser abordados nesta subseção. Exemplo: a solução deverá suportar ate
	       500 acessos simultâneos.
	   * - Requisitos de Usabilidade e Acessibilidade
	     - Informe os requisitos referentes à usabilidade e acessibilidade do produto. Exemplo: um usuário inexperiente no uso
	       de tecnologias deve executar a tarefa X em até 10 minutos; o usuário deve ter a opção de aumentar o tamanho da
	       fonte no portal.
	   * - Requisitos de Confiabilidade
	     - Descreva os requisitos de confiabilidade acordados com o cliente. Devem ser incluídos nesta subseção requisitos que
	       tratem sobre possibilidade de recuperação, tempo médio entre falhas, frequência e gravidade de falha, dentre outros.
	       Exemplo: o tempo médio entre falhas do sistema deve ser menor que X horas.
	   * - Requisitos de Suportabilidade
	     - Defina os requisitos referentes à suportabilidade do produto. Nesta subseção devem ser descritos requisitos que se
	       referem à possibilidade de teste, adaptabilidade, manutenibilidade, compatibilidade, possibilidade de instalação, etc.>
	   * - Requisitos de Segurança
	     - Informe os requisitos de segurança do produto, referentes a aspectos como: integridade, confidencialidade,
	       autenticidade, etc. Exemplo: apenas o administrador do sistema pode alterar as permissões de acesso ao sistema.>
	   * - Requisitos de Interface
	     - Liste os requisitos referentes à interface do sistema. Um requisito de interface especifica com o que o sistema deve
	       interagir e quais as restrições de formatos ou outros fatores para essa interação. Interface de usuário, hardware,
	       comunicação e software são alguns dos tipos de interface que podem ser abordados nesta subseção.>
	   * - Requisitos Ambientais
	     - Descreva os requisitos ambientais quando necessário. Para aplicativos de software, os fatores ambientais podem
	       incluir condições de uso, ambiente do usuário, disponibilidade de recursos, entre outros.>
	   * - Requisitos de Documentação
	     - Esta subseção descreve a documentação que deverá ser desenvolvida para suportar a implantação bem-sucedida do
	       produto. Manual do Usuário, Ajuda On-line, Guias de Instalação e de Configuração, e Arquivo Leiame são alguns
	       exemplos de documentos que podem ser abordados nesta subseção. Para os documentos listados, devem ser
	       abordados, dentre outros, aspectos referentes à finalidade, conteúdo, organização e restrições de formatação e
	       impressão, se for o caso.
	   * - Requisitos de Treinamento
	     - Descreva os requisitos de treinamento. Devem ser abordados nesta subseção questões como necessidade de
	       treinamento aos usuários, bem como metodologia e duração.
	   * - Requisitos de Intraestrutura
	     - Descreva os requisitos de intraestrutura. Devem ser abordados nesta subseção questões como necessidade de
	       infraestrutura no âmbito de software, hardware, redes, telecomunicações, infraestrutura física quando aplicável,
	       dentre outras.
	   * - Requisitos de Sustentação
	     - Descreva os requisitos de sustentação. Devem ser abordados nesta subseção questões como necessidade de
	       suporte/atendimento, requisitos de gestão de conteúdo e requisitos de níveis de serviço.

.. list-table:: 
   :widths: 10 30 40 20
   :header-rows: 1
   :stub-columns: 0

   * - Cód
     - Nome
     - Descrição
     - Categoria 
   * - <identificador único do requisito, use NF<numero_sequencial>, exemplo NF01, NF02>
     - <Nome do requisito não funcional>
     - <Descrição do que o requisito faz>
     - <Categoria do requisito>
