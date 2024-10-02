
.. _suap-artefatos-edu-ensino-cenario_testes-c100:


Cenário 100 - Curso técnico em Informática para Internet
========================================================

.. contents:: Conteúdo
    :local:
    :depth: 4
    
    
Objetivo
--------

Cenário de teste criado para simular situações de testes referente ao curso de regime seriado. Ver
`Projeto Pedagógico do Curso Técnico de Nível Médio em Informática para Internet na forma Integrada, presencial`_

.. _`Projeto Pedagógico do Curso Técnico de Nível Médio em Informática para Internet na forma Integrada, presencial`: http://portal.ifrn.edu.br/ensino/cursos/cursos-tecnicos-de-nivel-medio/tecnico-integrado/tecnico-em-informatica-para-internet/at_download/coursePlanPrev



Cadastros
---------

.. _C1:

C1 - Cadastros Gerais
^^^^^^^^^^^^^^^^^^^^^

Prédios
"""""""

| **Nome**: DIATINF
| **Campus**: CNAT
| **Ativo**: Sim
| Acesso ``ADMINISTRAÇÃO`` > ``Cadastros`` > ``Prédios``


Salas
"""""

| **Nome**: DIATINF - LAB07
| **Campus**: DIATINF (CNAT)
| **Ativo**: Sim
| **Capacidade da sala (em número de pessoas)**: 20
|
|
| **Nome**: DIATINF - LAB11
| **Campus**: DIATINF (CNAT)
| **Ativo**: Sim
| **Capacidade da sala (em número de pessoas)**: 20
|
|
| **Nome**: DIATINF - LAB13
| **Campus**: DIATINF (CNAT)
| **Ativo**: Sim
| **Capacidade da sala (em número de pessoas)**: 20
| Acesso ``ADMINISTRAÇÃO`` > ``Cadastros`` > ``Salas``


.. _C1:

C2 - Cadastros EDU
^^^^^^^^^^^^^^^^^^

Tipos de Componentes
""""""""""""""""""""

| **Descrição**: TIN 
| Ver :ref:`suap-artefatos-edu-ensino-cad_gerais-uc104`             


Niveis de Ensino
""""""""""""""""

| **Descrição**: Médio 
| Ver :ref:`suap-artefatos-edu-ensino-cad_gerais-uc105`


Naturezas de Participação
"""""""""""""""""""""""""

| **Descrição**: Presencial 
| Ver :ref:`suap-artefatos-edu-ensino-cad_gerais-uc101`


Diretorias Acadêmicas
"""""""""""""""""""""

| **Setor**: DG/CNAT 
| Ver :ref:`suap-artefatos-edu-ensino-cad_gerais-uc114`


Núcleos
"""""""

| **Descrição**: Tecnológico
| Ver :ref:`suap-artefatos-edu-ensino-cad_gerais-uc110`


.. _C3:

C3 - Estrutura de curso
^^^^^^^^^^^^^^^^^^^^^^^

| **Dados Gerais**
| **Descrição**: Curso técnico integrado regular 
| **Ativa**: Sim
| **Qtd. Max. de períodos**: 4
|
| **Critérios de Apuração de Resultados por Período**
| **Tipo de Avaliação**: Seriado
| **Limite de Reprovações**: 3
|
| **Critérios de Avaliação por Disciplinas**
| **Critério de Avaliação**: Nota
| **Média para passar sem prova final**: 60
| **Média para não reprovar direto**: 60
| **Média para aprovação após avaliação final**: 60
|
| **Critérios de Apuração de Frequência**
| **Percentual de Frequência**: 75
|
| **Índice de Rendimento Acadêmico (I.R.A)**
| **Forma de Cálculo**: Média aritmética das Notas Finais
|
| **Campos novos** oriundo do caso de uso :ref:`suap-artefatos-edu-ensino-alunos_professores-uc212`
| **Número máximo de cancelamento de diário**: 1
| **Número máximo de disciplinas além do período letivo**: 2
| **Número mínimo de disciplinas por período letivo**: 3
|
| **Campos novos** oriundo do caso de uso :ref:`suap-artefatos-edu-ensino-alunos_professores-uc207`
| **Média para certificação de conhecimento**: 60
| **Número máximo de certificação de conhecimento por período**: 3
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc300`

.. _C4:

C4 - Matrizes Curriculares
^^^^^^^^^^^^^^^^^^^^^^^^^^
| **Dados Gerais**
| **Descrição**: Técnico de Nível Médio em Informática para Internet
| **Ano Criação**: 2012
| **Período Criação**: 1
| **Nível de Ensino**: Médio
| **Ativa**: Sim
| **Data de início**: 01/01/2014
| **Data de fim**:
| **PPP**:
| **Qtd periodos letivos**: 4
|
| **Carga Horária**
| **Componentes obrigatórios**: 3.540 
| **Componentes optativos**: 0
| **Componentes eletivos**: 0
| **Seminários**: 70
| **Prática profissional**: 400
| **Atividades complementares**: 0

|
| **Ato Normativo**
| **Resolução de criação**:  Resolução No 38/2012-CONSUP/IFRN,
| **Data da resolução**: 26/03/2012
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302`


C5 - Componentes
^^^^^^^^^^^^^^^^


TIN.111.0001 - Princípios de Design e Projeto Gráfico
"""""""""""""""""""""""""""""""""""""""""""""""""""""

| **Dados Gerais**
| **Descrição**: TIN.111.0001 - Princípios de Design e Projeto Gráfico
| **Descrição no Diploma e Histórico**:
| **Tipo do Componente**: TIN 
| **Diretoria**: RE
| **Nível de ensino**: Médio 
| **Está ativo**: Sim
|
| **Carga Horária**
| **Hora/relógio**: 60
| **Hora/aula**: 80
| **Qtd. de créditos**:0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc301`


Vincular Componente de matriz
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Dados Gerais**
| **Componente**: TIN.111.0001 - Princípios de Design e Projeto Gráfico
| **Período**: 1
| **Tipo**: Regular
| **Optativo**: Não
| **Qtd. Avaliações**: 4
| **Núcleo**: Tecnológico
|
| **Carga Horária**
| **Teórica (Hora-Relógio)**: 60
| **Prática (Hora-Relógio)**: 0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc303`


TIN.111.0002 - Design Web e Arquitetura da Informação
"""""""""""""""""""""""""""""""""""""""""""""""""""""

| **Dados Gerais**
| **Descrição**: TIN.111.0002 - Design Web e Arquitetura da Informação
| **Descrição no Diploma e Histórico**:
| **Tipo do Componente**: TIN 
| **Diretoria**: RE
| **Nível de ensino**: Médio 
| **Está ativo**: Sim
|
| **Carga Horária**
| **Hora/relógio**: 120
| **Hora/aula**: 160
| **Qtd. de créditos**:0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc301`


Vincular Componente de matriz
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Dados Gerais**
| **Componente**: TIN.111.0002 - Design Web e Arquitetura da Informação
| **Período**: 2
| **Tipo**: Regular
| **Optativo**: Não
| **Qtd. Avaliações**: 4
| **Núcleo**: Tecnológico
|
| **Carga Horária**
| **Teórica (Hora-Relógio)**: 120
| **Prática (Hora-Relógio)**: 0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc303`


TIN.111.004 - Banco de dados
""""""""""""""""""""""""""""

| **Dados Gerais**
| **Descrição**: TIN.111.004 - Banco de dados
| **Descrição no Diploma e Histórico**:
| **Tipo do Componente**: TIN 
| **Diretoria**: RE
| **Nível de ensino**: Médio 
| **Está ativo**: Sim
|
| **Carga Horária**
| **Hora/relógio**: 120
| **Hora/aula**: 160
| **Qtd. de créditos**:0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc301`


Vincular Componente de matriz
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Dados Gerais**
| **Componente**: TIN.111.004 - Banco de dados
| **Período**: 3
| **Tipo**: Regular
| **Optativo**: Não
| **Qtd. Avaliações**: 4
| **Núcleo**: Tecnológico
|
| **Carga Horária**
| **Teórica (Hora-Relógio)**: 120
| **Prática (Hora-Relógio)**: 0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc303`


TIN.111.0007 - Projeto de interface do Usuário
""""""""""""""""""""""""""""""""""""""""""""""

| **Dados Gerais**
| **Descrição**: TIN.111.0007 - Projeto de interface do Usuário
| **Descrição no Diploma e Histórico**:
| **Tipo do Componente**: TIN 
| **Diretoria**: RE
| **Nível de ensino**: Médio 
| **Está ativo**: Sim
|
| **Carga Horária**
| **Hora/relógio**: 90
| **Hora/aula**: 120
| **Qtd. de créditos**:0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc301`


Vincular Componente de matriz
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| **Dados Gerais**
| **Componente**: TIN.111.0007 - Projeto de interface do Usuário
| **Período**: 4
| **Tipo**: Regular
| **Optativo**: Não
| **Qtd. Avaliações**: 4
| **Núcleo**: Tecnológico
|
| **Carga Horária**
| **Teórica (Hora-Relógio)**: 90
| **Prática (Hora-Relógio)**: 0
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc303`


C6 - Cursos
^^^^^^^^^^^

| **Identificação**
| **Descrição**: Técnico em Informática para Internet
| **Descrição no Diploma e Histórico**: Técnico em Informática para Internet
|
| **Dados da Criação**
| **Ano letivo**: 2011
| **Período letivo**: 1
| **Data início**: 09/09/2011
| **Data fim**:
| **Ativo**: Sim
|
| **Coordenação**
| **Coordenador**:
|
| **Dados Gerais**
| **Código**:1111
| **Natureza de participação**: Presencial
| **Modalidade**: Integrado
| **Área**: Ciências, Matemática e Computação
| **Estrutura**: Curso técnico integrado regular 
| **Periodicidade**: Anual
| **Diretoria**: DG/CNAT
| **Exige enade**:
| **Exige colação de grau**: Sim
| **Certificado/Diploma Emitido pelo Campus**: Sim
|
| **Ato Normativo**
| **Resolução de criação**: Projeto aprovado pela Resolução No 38/2012-CONSUP/IFRN,
| **Data da resolução**: 26/03/2012
|
| **Ato de Reconhecimento**
| **Descrição**:
| **Data**:
|
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc304`


Vincular matriz ao curso
""""""""""""""""""""""""

| **Matriz**: Técnico de Nível Médio em Informática para Internet 
| Ver :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc305`


C7 - Horário do Campus
^^^^^^^^^^^^^^^^^^^^^^

| **Dados Gerais**
| **Descrição**: Horário Tec. Integ. Info. - CNAT
| **Campus**: CNAT

.. list-table:: **Horário das Aulas**
   :header-rows: 1
   :stub-columns: 0

   * - Número
     - Turno
     - Início
     - Término
   * - 1
     - Matutino
     - 7:00
     - 07:44 
   * - 2
     - Matutino
     - 7:45
     - 08:30 
   * - 3
     - Matutino
     - 08:50
     - 09:34 
   * - 4
     - Matutino
     - 09:35
     - 10:20 
   * - 5
     - Matutino
     - 10:30
     - 11:14
   * - 6
     - Matutino
     - 11:15
     - 12:00 
   * - 1
     - Vespetino
     - 13:00
     - 13:44 
   * - 2
     - Vespetino
     - 13:45
     - 14:29 
   * - 3
     - Vespetino
     - 14:40
     - 15:24
   * - 4
     - Vespetino
     - 15:25
     - 16:09
   * - 5
     - Vespetino
     - 16:30
     - 17:14
   * - 6
     - Vespetino
     - 17:15
     - 18:00

|
| Ver :ref:`suap-artefatos-edu-ensino-proc_apoio-uc500`


C8 - Calendários Acadêmicos
^^^^^^^^^^^^^^^^^^^^^^^^^^^

| **Dados Gerais**
| **Descrição**: CALENDÁRIO ACADÊMICO INSTITUCIONAL CAMPUS NATAL - CENTRAL 2015
| **Tipo**:Anual	
| **Campus**:CNAT
| **Ano letivo**: 2015
| **Período letivo**: 1
|
| **Datas**
| **Início das Aulas**: 01/02/2015
| **Término das Aulas**: 01/11/2015
| **Data de Fechamento do Período**: 10/11/2015
| **Qtd etapas**: Quatro Etapas
|
| **Primera Etapa**
| **Início**: 01/02/2015
| **Fim**: 01/04/2015
|
| **Segunda Etapa**
| **Início**: 02/04/2015
| **Fim**: 02/06/2015
|
| **Tereceira Etapa**
| **Início**: 15/06/2015
| **Fim**: 15/08/2015
|
| **Quarta Etapa**
| **Início**: 16/08/2015
| **Fim**: 16/10/2015
|
| Ver :ref:`suap-artefatos-edu-ensino-proc_apoio-uc503`


C9 -  Gerar Turmas
^^^^^^^^^^^^^^^^^^

| **Passo 1 de 4**
| **Dados do Curso**
| **Ano Letivo**: 2015
| **Período Letivo**: 1
| **Matriz/Curso**: Técnico de Nível Médio em Informática para Internet - 1111 - Técnico em Informática para Internet (CAMPUS NATAL - CENTRAL)
|
|
| **Passo 2 de 4**
| **1º Período**
| **Nº de Turmas**: 1
| **Turno**: Matutino
| **Nº de Vagas**: 10
|
| **2º Período**
| **Nº de Turmas**: 1
| **Turno**: Matutino
| **Nº de Vagas**: 10
|
| **3º Período**
| **Nº de Turmas**: 1
| **Turno**: Matutino
| **Nº de Vagas**: 10
|
| **4º Período**
| **Nº de Turmas**: 1
| **Turno**: Matutino
| **Nº de Vagas**: 10
|
|
| **Passo 3 de 4**
| **Horário/Calendário e Componentes**
| **Horário do Campus**: Horário Tec. Integ. Info. - CNAT
| **Calendário Acadêmico**: CALENDÁRIO ACADÊMICO INSTITUCIONAL CAMPUS NATAL - CENTRAL 2015
|
| **Seleção de Componentes**
| **Componente**: 
| 1	TIN.0001 - Princípios de Design e Projeto Gráfico - Médio [60 Hs/80 Aulas]	
| 2	TIN.0002 - Design Web e Arquitetura da Informação - Médio [120 Hs/160 Aulas]	
| 3	TIN.0003 - Banco de dados - Médio [120 Hs/160 Aulas]	
| 4	TIN.0004 - Projeto de interface do Usuário - Médio [90 Hs/120 Aulas]

.. note::
   Serão criadas 4 turmas:
    
   - 20151.1.1111.1M
     
     - 1	TIN.0001 - Princípios de Design e Projeto Gráfico - Médio [80 Hs/60 Aulas]	
     
   - 20151.2.1111.1M
   
     - 2	TIN.0002 - Design Web e Arquitetura da Informação - Médio [120 Hs/160 Aulas]
     
   - 20151.3.1111.1M
   
     - 3	TIN.0003 - Banco de dados - Médio [120 Hs/160 Aulas]	
      
   - 20151.4.1111.1M
   
     - 4	TIN.0004 - Projeto de interface do Usuário - Médio [90 Hs/120 Aulas]
     
|
| Ver :ref:`suap-artefatos-edu-ensino-diarios-uc401`


     
C1 - Configurar Diários
^^^^^^^^^^^^^^^^^^^^^^^

TIN.0001 - Princípios de Design e Projeto Gráfico - Médio [60 Hs/80 Aulas]
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

Definir Local de Aula
~~~~~~~~~~~~~~~~~~~~~

| **Sala**:  DIATINF - LAB07 - DIATINF (CNAT)

Definir Horário de Aula
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :stub-columns: 0

   * - Matutino
     - Segunda
     - Quarta
   * - 07:45 - 08:30
     - | X
     -  
   * - 08:50 - 09:34
     - | X
     -  
   * - 08:50 - 09:34
     - 
     -  
   * - 09:35 - 10:20
     - 
     -           
   * - 10:30 - 11:14
     - 
     - | X 
   * - 11:15 - 12:00
     - 
     - | X 

| **Horário**: 2M12 / 4M56


TIN.0002 - Design Web e Arquitetura da Informação - Médio [120 Hs/160 Aulas]
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""	

Definir Local de Aula
~~~~~~~~~~~~~~~~~~~~~

| **Sala**:  DIATINF - LAB07 - DIATINF (CNAT)

Definir Horário de Aula
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :stub-columns: 0

   * - Matutino
     - Segunda
     - Quarta
   * - 07:45 - 08:30
     - | X
     -  
   * - 08:50 - 09:34
     - | X
     -  
   * - 08:50 - 09:34
     - 
     -  
   * - 09:35 - 10:20
     - 
     -           
   * - 10:30 - 11:14
     - 
     - | X 
   * - 11:15 - 12:00
     - 
     - | X 

| **Horário**: 2M12 / 4M56

TIN.0003 - Banco de dados - Médio [120 Hs/160 Aulas]
""""""""""""""""""""""""""""""""""""""""""""""""""""
	
TIN.0004 - Projeto de interface do Usuário - Médio [90 Hs/120 Aulas]
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

