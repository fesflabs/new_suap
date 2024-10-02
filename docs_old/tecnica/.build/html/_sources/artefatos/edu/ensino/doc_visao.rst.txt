
.. |logo| image:: ../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **SUAP EDU** 

.. include:: ../../header.rst
   :start-after: docvisao-start
   :end-before: docvisao-end

.. _suap-artefatos-edu-ensino-visao:

Documento de Visão do sistema SUAP EDU <v0.1>
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
   * - 17/04/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos


.. comentário
   - inclusão do UC 35 [Fernando]
   - inclusão do UC 28, 36, 37, 38 [Hugo]
   - inclusão do UC 29, 30, 31, 32, 33 [Jailton]
     Definições, Acrônimos e Abreviações



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

A finalidade do SUAP EDU é atender as necessidades acadêmicas através de operações que otimizem o gerenciamento dos cursos, às 
atividades de alunos e docentes dos diversos Campi que ofertam tais cursos.

.. finalidade_end

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

Não se aplica

Descrição dos papeis
--------------------

Papel das partes interessadas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^  
   
.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Representante
     - Responsabilidades
   * - Alessandro José de Souza (DIAAC/PROEN/RE/IFRN)
     - Fornecedor de Requisitos: fornecer informações sobre o domínio do sistema; valida requisitos.
   * - Francisco Emiliano Gurgel (PROEN/RE/IFRN)
     - Fornecedor de Requisitos: fornecer informações sobre o domínio do sistema; testar funcionalidades.
   * - Matheus Gomes Amorim (PROEN/RE/IFRN)
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
   * - Administrador
     - Administrador EDU
     - Tem acesso geral ao sistema, faz todos os cadastros necessários para que uma turma possa ser iniciada. 
   * - Secretário 
     - Secretário EDU
     - Gerencia cursos -- gera turmas, efetua matriculas dos alunos, fecha e abre período, emiti históricos e diplomas.
   * - Professor 
     - Professor EDU
     - Lança notas de aulas, faltas e notas; fecha diário. 
   * - Aluno
     - 
       .. warning::
          Falta criar o grupo para o aluno.
     - Acompanha aulas, acompanha notas e visualiza histórico.
   * - Coordenador de curso
     - 
     - 
       .. warning::
          quais são as atribuições desse papel?
   * - Diretor acadêmico
     - 
     - 
       .. warning::
          quais são as atribuições desse papel?
   * - Pedagogo
     - 
     - 
       .. warning::
          quais são as atribuições desse papel?
          
     
Visão geral do produto
----------------------

Modelagem de processos de negócio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _`Figura 1`:

.. figure:: media/fluxo.png
   :align: center
   :scale: 80 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Modelagem de processo de negócio.	
   

Perspectiva do produto
^^^^^^^^^^^^^^^^^^^^^^

.. note::
   Nesta subseção apresente a relação que o produto tem com outros produtos e o ambiente do usuário. Informe se o
   produto é independente e autossuficiente. Se o produto for um componente de um sistema maior, descreva como
   esses sistemas interagem e quais as interfaces relevantes entre os sistemas. Se o produto possuir vários módulos, 
   estes deverão ser listados nesta subseção.
   
   Descreva também as interfaces de software com outros componentes do sistema de software. Poderão se componentes comparados, 
   componentes reutilizados de outro aplicativo ou componentes que estão sendo desenvolvidos para subsistemas fora do escopo desta,
   mas com os quais esse aplicativo de software deve interagir
   Identificam-se aqui as interfaces com outros produtos de software, tais como aplicativos que recebem dados do produto ou 
   enviam dados para ele, seja on-line, através de arquivos ou através de banco de dados. Não incluir componentes normais 
   do ambiente operacional, como bibliotecas e plataformas.
   Ao descrever as interfaces de software, informe o nome do componente/sistema, a descrição, a forma de entrada de dados 
   e/ou a forma de saída de dados.


Integração com outros sistemas
""""""""""""""""""""""""""""""

- Q-Acadêmico: integra-se com o sistema Q-Acadêmico para importar os alunos ativos.
- SGC (Sistema de Gerenciamento de Concursos): importa dados relativos a ofertas de vagas e dados (cpf, nome, telefone, etc) dos candidatos.

  .. warning::
     A princípio, me parece, que a integração com o SGC só existe no subsistema Pós-graduação, correto ?

Relacionamentos com outros subsistemas
""""""""""""""""""""""""""""""""""""""

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
     - O sistema deve permitir informar a nutureza de participação do curso (EaD, Presencial, Semipresencial, Tempo Integral.
     - Especificação
   * - R02
     - O sistema deve permitir infomar o Turno no qual o curso será ofertado, a saber: Livre, Matutino, Noturno, Vespertino.
     - Especificação  	
   * - R03
     - O sistema deve permitir identificar qual foi a forma de ingresso do aluno no curso, a saber: intercâmbio, matrícula direta, processo seletivo, tranferência externa.
     - Especificação
   * - R04
     - O sistema deve permitir informar o tipo de componente do componente.
     - Especificação
   * - R05
     - O sistema deve permitir informar o nível de ensino (Fundamental, Graduação, Médio, Pós-graduação) do componente.
     - Especificação
   * - R06
     - O sistema deve permitir especificar a modalidade do curso, tais como FIC, Graduação Tecnológica, Técnico integrado, etc.
     - Especificação
   * - **R07**
     - .. warning::
          Áreas dos Cursos: acho que não se aplica a esse subsitema, mas sim, o de Pós-graduação.
     - Especificação
   * - R08
     - O sistema deve permitir especificar o eixo tecnológico no qual o curso está inserido, assim como discriminado no Catálogo Nacional de Cursos Técnicos (http://pronatec.mec.gov.br/cnct/eixos_tecnologicos.php) 
     - Especificação
   * - R09
     - .. warning::
          Convênios: onde será usado?
     - Especificação
   * - R10
     - De acordo com as definições do Catálogo Nacional de Cursos Técnicos, as matrizes curriculares devem está organizadas em núcleos
       politécnicos, tais como Articulador, Fundamental, Tecnológico, etc.
       Deve ser informado ao vincular um componente a uma matriz.
     - Especificação
   * - R11
     - Um diário pode ter mais de um professor, sendo assim, é necessário informar o tipo, a saber, formador, principal, tutor.
     - Especificação
   * - R12
     - .. warning::
          Situação de matricula: onde será usado?
     - Especificação
   * - R13
     - .. warning::
           Situação de Matricula no Período: onde será usado?
     - Especificação
   * - R14
     - O sistema deve permitir informar em qual diretoria o curso será ofertado.  
     - Especificação
   * - R15
     - .. warning::
            Modelos de Documentos: onde será usado?
     - Especificação
   * - R16
     - Se uma matriz currícular de um curso será ofertado em vários campi, o curso deve ser cadastrado na diretoria Reitoria, mas, 
       caso o campus específico ofereça o mesmo curso com uma matriz diferente, deve-se cadastrar o curso no espectivo campus.
     - Especificação        
   * - R17
     - O sistema deve permitir defir parâmetros de estrutura do curso, tais como média para passar, quantidade máximo de períodos,
       tipo de avaliação (crédito, seriado, modular), etc.
     - Especificação 
   * - R18
     - O componente será identificado por um código único gerado pelo sistema. O código será sequencial para cada tipo de componente.
     - Especificação
   * - R19
     - O sistema deve permitir informar o diretor geral para cada diretoria. No caso de mais de um diretor, será necessário especificar o titular.
     - Especificação
   * - R20
     - O sistema deve permitir informar o diretor acadêmico para cada diretoria. No caso de mais de um diretor, será necessário especificar o titular.
     - Especificação
   * - R21
     - O sistema deve permitir informar os coordenadores de cursos e seus respectivos cursos de cada diretoria.
     - Especificação
   * - R22
     - O sistema deve permitir informar os secretários de cursos para cada diretoria.
     - Especificação      
   * - R23
     - O sistema deve permitir informar os pedagogos de cada diretoria.
     - Especificação      
     
Casos de uso
^^^^^^^^^^^^   

Cadastros Gerais
""""""""""""""""

.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc101` 
     - 
       .. include:: cad_gerais/cad_gerais_uc101.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R01
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc102` 
     - 
       .. include:: cad_gerais/cad_gerais_uc102.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R02
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc103` 
     - 
       .. include:: cad_gerais/cad_gerais_uc103.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R03
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc104` 
     - 
       .. include:: cad_gerais/cad_gerais_uc104.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R04
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc105` 
     - 
       .. include:: cad_gerais/cad_gerais_uc105.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R05
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc106` 
     - 
       .. include:: cad_gerais/cad_gerais_uc106.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R06
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc107` 
     - 
       .. include:: cad_gerais/cad_gerais_uc107.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R07
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc108` 
     - 
       .. include:: cad_gerais/cad_gerais_uc108.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R08
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc109` 
     - 
       .. include:: cad_gerais/cad_gerais_uc109.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R09
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc110` 
     - 
       .. include:: cad_gerais/cad_gerais_uc110.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R10
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc111` 
     - 
       .. include:: cad_gerais/cad_gerais_uc111.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R11
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc112` 
     - 
       .. include:: cad_gerais/cad_gerais_uc112.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R12
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc113` 
     - 
       .. include:: cad_gerais/cad_gerais_uc113.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R13
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc114` 
     - 
       .. include:: cad_gerais/cad_gerais_uc114.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R14, R19, R20, R21, R22, R23
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc115` 
     - 
       .. include:: cad_gerais/cad_gerais_uc115.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R15
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc116` 
     - 
       .. include:: cad_gerais/cad_gerais_uc116.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R19
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc117` 
     - 
       .. include:: cad_gerais/cad_gerais_uc117.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R20
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc118` 
     - 
       .. include:: cad_gerais/cad_gerais_uc118.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R21
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc119` 
     - 
       .. include:: cad_gerais/cad_gerais_uc119.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R22
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc120` 
     - 
       .. include:: cad_gerais/cad_gerais_uc120.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R23	
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc121` 
     - 
       .. include:: cad_gerais/cad_gerais_uc121.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R23	
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc122` 
     - 
       .. include:: cad_gerais/cad_gerais_uc122.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R23	
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc123` 
     - 
       .. include:: cad_gerais/cad_gerais_uc123.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-cad_gerais-uc122` 
     - 
       .. include:: cad_gerais/cad_gerais_uc124.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     - 
     

Alunos e Professores
""""""""""""""""""""

.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc200` 
     - 
       .. include:: alunos_professores/alunos_professores_uc200.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -      
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc201` 
     - 
       .. include:: alunos_professores/alunos_professores_uc201.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202` 
     - 
       .. include:: alunos_professores/alunos_professores_uc202.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc203` 
     - 
       .. include:: alunos_professores/alunos_professores_uc203.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc204` 
     - 
       .. include:: alunos_professores/alunos_professores_uc204.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc205` 
     - 
       .. include:: alunos_professores/alunos_professores_uc205.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc206` 
     - 
       .. include:: alunos_professores/alunos_professores_uc206.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc207` 
     - 
       .. include:: alunos_professores/alunos_professores_uc207.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc208` 
     - 
       .. include:: alunos_professores/alunos_professores_uc208.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc209` 
     - 
       .. include:: alunos_professores/alunos_professores_uc209.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc210` 
     - 
       .. include:: alunos_professores/alunos_professores_uc210.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc211` 
     - 
       .. include:: alunos_professores/alunos_professores_uc211.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     -      
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc212` 
     - 
       .. include:: alunos_professores/alunos_professores_uc212.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     -      
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc213` 
     - 
       .. include:: alunos_professores/alunos_professores_uc213.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     -
   * - :ref:`suap-artefatos-edu-ensino-subdiretorio-uc214` 
     - 
       .. include:: alunos_professores/alunos_professores_uc214.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     -     
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc215` 
     - 
       .. include:: alunos_professores/alunos_professores_uc215.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     -   
   * - :ref:`suap-artefatos-edu-ensino-alunos_professores-uc215` 
     - 
       .. include:: alunos_professores/alunos_professores_uc215.rst
         :start-after: Objetivo
         :end-before: Atores
     - Normal
     -   
          
     
Cursos, Matrizes e Componentes
""""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc300` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc300.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - 
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc301` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc301.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -   
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc302.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -   
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc303` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc303.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -   
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc304` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc304.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -   
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc305` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc305.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -   
   * - :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc306` 
     - 
       .. include:: cursos_matr_comp/cursos_matri_comp_uc306.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     -      


Turmas e Diários
""""""""""""""""

.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-edu-ensino-diarios-uc400` 
     - 
       .. include:: diarios/diarios_uc400.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R 
   * - :ref:`suap-artefatos-edu-ensino-diarios-uc401` 
     - 
       .. include:: diarios/diarios_uc401.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R 
   * - :ref:`suap-artefatos-edu-ensino-diarios-uc402` 
     - 
       .. include:: diarios/diarios_uc402.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R
   * - :ref:`suap-artefatos-edu-ensino-diarios-uc403` 
     - 
       .. include:: diarios/diarios_uc403.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Alta
     - R           


     
Procedimentos de Apoio
""""""""""""""""""""""

.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados 
   * - :ref:`suap-artefatos-edu-ensino-proc_apoio-uc500` 
     - 
       .. include:: proc_apoio/proc_apoio_uc500.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R   
   * - :ref:`suap-artefatos-edu-ensino-proc_apoio-uc501` 
     - 
       .. include:: proc_apoio/proc_apoio_uc501.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R
   * - :ref:`suap-artefatos-edu-ensino-proc_apoio-uc502` 
     - 
       .. include:: proc_apoio/proc_apoio_uc502.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R
   * - :ref:`suap-artefatos-edu-ensino-proc_apoio-uc503` 
     - 
       .. include:: proc_apoio/proc_apoio_uc503.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Normal
     - R          
   
                   
     
Relatórios e Estatísticas
"""""""""""""""""""""""""

.. list-table:: 
   :widths: 30 40 10 10
   :header-rows: 1
   :stub-columns: 0
   
   * - Cód, Nome, Versão
     - Descrição
     - Complexidade
     - Requisitos relacionados
   * - :ref:`suap-artefatos-edu-ensino-relatorio_estatistica-uc600` 
     - 
       .. include:: relatorios_estatisticas/relatorio_estatistica_uc600.rst
	      :start-after: Objetivo
	      :end-before: Atores
     - Alta
     - R
     
Diplomas e Certificados
"""""""""""""""""""""""

     
Logs
""""

     

Diagrama de caso de uso
^^^^^^^^^^^^^^^^^^^^^^^    

.. note::
   Definições:
    
   - Cor azul: Em produção e documentado
   - Cor amarelo: Em produção e não documentado
   - Cor Laranja: Funcionalidades alteradas e documentado
   - Cor Vermelho: Funcionalidades novas e documentado


.. _`Figura 2`:

.. figure:: media/diagrama_uc_alunos_professores.png
   :align: center
   :scale: 80 %
   :alt: Diagrama de caso de uso
   :figclass: align-center
   
   Figura 2: Diagrama de caso de uso Alunos e professores.	
      
    
.. _`Figura 3`:

.. figure:: media/diagrama_uc_gerais.png
   :align: center
   :scale: 80 %
   :alt: Diagrama de caso de uso
   :figclass: align-center
   
   Figura 3: Diagrama de caso de uso cadastros gerais.	     


.. _`Figura 4`:

.. figure:: media/diagrama_uc_cursos_matr_comp.png
   :align: center
   :scale: 80 %
   :alt: Diagrama de caso de uso
   :figclass: align-center
   
   Figura 4: Diagrama de caso de uso Cursos, Matrizes e Compronentes.	
   

.. _`Figura 5`:

.. figure:: media/diagrama_uc_turmas_diarios.png
   :align: center
   :scale: 80 %
   :alt: Diagrama de caso de uso
   :figclass: align-center
   
   Figura 5: Diagrama de caso de uso Turmas e Diários.
   
      
.. _`Figura 6`:

.. figure:: media/diagrama_uc_proc_apoio.png
   :align: center
   :scale: 80 %
   :alt: Diagrama de caso de uso
   :figclass: align-center
   
   Figura 6: Diagrama de caso de uso Procedimentos de Apoio.	
   
   
        
Diagrama de modelagem de domínio
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Não há.

Questões em aberto
------------------

- Um curso pode ter mais de uma matriz currícular? O que ocorre quando no decorrer do curso a matriz sofrer alterações?
- Quais são os dados importados dos alunos do Q-Acadêmico? Quando ocorre a importação? É manual ou automática?
- Além do Q-Acadêmico, existem integração com outros sistemas externos?
- No cadastro de curso, existem os flags "Exige enade", "Exige colação de grau", "Certificado/Diploma Emitido pelo Campus".
  Quais são as regras de negócio relacionados a esses flags?
- Esse subsistema interage com outros subsistemas do SUAP, tipo Gestão de Pessoas, Cursos, etc?
- Acredito que o caso de uso 7 - Área dos Cursos, não faz parte desse subsitema, mas sim do subsistema Pós-graduação!? 
  Além dele, existem outros que foram listados neste documento ?
- Existe alguma regra de negócio relacionado ao tipo de professor diário (formador, principal, tutor) ?
- **No SUAP não existe a situacao de matrícula trancamento voluntário e portanto ainda não dá para calcular a quantidade de trancamentos
  voluntários, como isso será resolvido? Como serão tratados os dados da importação quando o aluno tiver trancamento voluntário.**
- **Alunos de cursos FIC podem ser reintegrados? Eu acho que não pois estes só possuem um período.**
- **Se o aluno estiver no último período ele pode ser reintegrado ou trancado? Como fica o seu último período após a reintegração 
  e ou trancamento?**
  
  
.. comentário::
   enviar documetação scp -r html/ breno@teresina:suap_docs
   
