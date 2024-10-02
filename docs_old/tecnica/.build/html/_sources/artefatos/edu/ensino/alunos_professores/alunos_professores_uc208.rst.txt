
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-alunos_professores-uc208: 

UC 208 - Gerir Professor <v0.1>
==============================

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
   * - 21/05/2014
     - 0.1
     - Início do Documento
     - Hugo Tácito Azevedo de Sena

Objetivo
--------

Listar e visualizar dados de professores.

Atores
------

Principais
^^^^^^^^^^

Secretário, Administrador, Coordenador, Diretor Geral e Acadêmico: podem listar e visualizar dados do professor


Interessado
^^^^^^^^^^^

Secretário.

Pré-condições
-------------

O professor deve estar cadastrado no sistema.

Pós-condições
-------------

Não há.

Casos de Uso Impactados
-----------------------

	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc209` - Adiciona o botão de "Editar Foto" na aba de dados pessoais do professor.
	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc210` - Adiciona o botão de "Cadastrar Professor Convidado" apenas na aba de listagem de professores convidados.
	#. :ref:`suap-artefatos-edu-ensino-alunos_professores-uc211` - Adiciona o botão de "Editar NCE/Matéria Disciplina" na aba de dados funcionais do professor.
	#. :ref:`suap-artefatos-edu-ensino-diarios-uc402` - Adiciona duas aba na visualização mostrando os diários do professor e os horários de aula.
	
Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Alunos e Professores`` > ``Professores``
    #. O sistema exibe a lista de professores (RIN1_)

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:	

FA1 - Listar (FN_.2)
""""""""""""""""""""

	#. O Secretário restringe a lista usando o filtro e/ou busca e/ou aba (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _suap-artefatos-edu-ensino-alunos_professores-uc208-FA2:

FA2 - Visualizar Professor (FN_.2)
""""""""""""""""""""""""""""""""""

	#. O Secretário aciona a opção ``Ver`` do professor que se deseja exibir mais informações dentre um dos professores
	   disponíveis na listagem
	#. O sistema exibe informações do professor (RI1_)
    	
    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

Não há.

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RI1 – Exibição do professor 
"""""""""""""""""""""""""""""""""""""

Os dados do professor são exibidos dentro de abas, são eles:

- ``Dados Gerais``: Exibe informações gerais sobre o professor.
- ``Dados funcionais``: Exibe informações funcionais sobre o professor.
- ``Períodos/Disciplinas``: Exibe as disciplinas que o professor já lecionou.
- ``Horários``: Exibe os horários das aulas do professor.
- ``Férias``: Exibe as férias que o servidor já adquiriu.

Na aba ``Dados Gerais`` são exibidas as informações a seguir:

- ``Foto``: Exibe a foto do professor
- ``Editar``: Edita a foto do professor (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc209`)
- ``Nome``: Exibe o nome do professor
- ``CPF``: Exibe o CPF do professor
- ``RG``: Exibe o número e orgão emissor do RG do professor
- ``Data de Nascimento``: Exibe a data de nascimento do professor
- ``Estado Civil``: Exibe a data de nascimento do professor
- ``Filiação``: Exibe o nome da mãe e/ou do pai do professor
- ``Endereço``: Exibe a Rua, o número, o bairro e os complementos do professor
- ``CEP``: Exibe o CEP do endereço do professor
- ``Cidade/Estado``: Exibe a cidade/estado do endereço do professor
- ``Telefones``: Exibe os telefones do professor
- ``E-mails``: Exibe os emails do professor

Na aba ``Dados Funcionais`` são exibidas as informações a seguir:

- ``Matrícula SIAPE``: Exibe a matrícula institucional do professor cadastrado no SIAPE
- ``Situação``: Exibe a situação institucional do professor
- ``Cargo``: Exibe o cargo do professor cadastrado no SIAPE
- ``Jornada de Trabalho``: Exibe a jornada de trabalho do professor
- ``Classe do Cargo``: Exibe a classe do cargo do professor
- ``Grupo do Cargo``: Exibe o grupo do cargo do professor
- ``Código da Vaga``: Exibe o código da vaga do professor
- ``Titulação``: Exibe a última titulação do professor
- ``Setor SUAP``: Exibe o setor do professor junto dentro do sistema
- ``Lotação SIAPE``: Exibe a lotação do professor cadastrada no SIAPE
- ``Exercício SIAPE``: Exibe o local de exercício do professor junto ao SIAPE
- ``Início do Exercício``: Exibe a data de início do exercício do professor
- ``Tempo de Serviço``: Exibe quanto tempo de serviço o professor já cumpriu
- ``Padrão``: Exibe o padrão do professor
- ``Matéria Disciplina``: Exibe a matéria disciplina do professor
- ``NCE``: Exibe o núcleo central estruturante do professor
- ``Editar Matricula Disciplina/NCE``: Edita a Matrícula Disciplina/NCE do professor (:ref:`suap-artefatos-edu-ensino-alunos_professores-uc211`)

Na aba ``Períodos/Disciplinas`` são exibidas as informações de acordo com o RIN2_.

Na aba ``Horários`` são exibidas as informações de acordo com o RIN3_.

Na aba ``Férias`` são exibidas as informações de acordo com o RIN4_.

A `Figura 1`_ exibe um esboço de como esses dados serão exibidos.

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:

.. _suap-artefatos-edu-ensino-alunos_professores-uc208-RIN1:

RIN1 – Campos para listagem de professores
""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida dividida em abas conforme especificadas abaixo:

- ``Qualquer``: exibe todos os professores
- ``Docentes``: exibe apenas professores com status de Docente
- ``Técnicos Administrativos``: exibe apenas professores com status de Técnico Administrativo
- ``Convidados``: exibe apenas professores com status de Convidados

     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Foto
     - Dados Gerais (Nome/Setor/E-mail)
     - Matrícula
     - Câmpus
   * - Ordenação
     - Não
     - Não
     - Sim
     - Sim
     - Sim
   * - Filtro
     - Não
     - Não
     - Não
     - Não
     - Sim
   * - Busca
     - Não
     - Não
     - Sim (Nome)
     - Sim
     - Não
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
     - 
     -
     -
     -   

.. _RIN2:
     
RIN2 – Campos para listagem de disciplinas
""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida conforme especificada abaixo:
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Diário
     - Disciplina
     - Tipo de Professor
     - Período/Ano
   * - Ordenação
     - Não
     - Não
     - Sim
     - Não
     - Não
   * - Filtro
     - Não
     - Não
     - Não
     - Não
     - Sim
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
     - 
     -
     -
     - Não exibir
     
.. _RIN3:
     
RIN3 – Campos para listagem de horários
""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida conforme especificada abaixo:
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - Horário/Dia
     - Segunda
     - Terça
     - Quarta
     - Quinta
     - Sexta
     - Sábado
     - Domingo
     - Ano/Período Letivo
   * - Ordenação
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Sim
   * - Filtro
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Sim
   * - Observações
     -
     - 
     -
     -
     -
     - 
     -
     -  Não exibir

.. _RIN4:
     
RIN4 – Campos para listagem de férias
""""""""""""""""""""""""""""""""""""""""""""""""""
 
A listagem é exibida conforme especificada abaixo:
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Exercício
     - Período 1
     - Período 2
     - Período 3
   * - Ordenação
     - Não
     - Sim
     - Não
     - Não
     - Não
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Ver
     - 
     -
     -
     -  
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - Somente exibe o botão "Cadastrar Professor Convidado" e a ação de "Editar" quando a aba Convidados estiver selecionada.
   * - RN2
     - Somente Administradores, Coordenadores, Secretários, Diretores Gerais e Acadêmicos podem editar a foto do professor.
   * - RN3
     - Somente Administradores podem editar a Matrícula Diario/NCE (Núcleo Central Estruturante) do professor, cujo botão 
       só aparece na aba de dados funcionais.
   * - RN4
     - Todos os diários podem ser exibidos, ou apenas os diários de um período selecionado.
   * - RN5
     - Os horários só são exibidos após o secretário selecionar um período.
   * - RN6
     - A paginação deve exibir apenas 10 registro para evitar rolagem da tela.
   * - RN7
     - Todas as telas de listagem (professor, disciplinas, horários, férias) devem permitir que o usuário possa exportar 
       a listagem para um arquivo no formato XLS.
     
.. _RN1: `Regras de Negócio`_  
.. _RN2: `Regras de Negócio`_  
.. _RN3: `Regras de Negócio`_  
.. _RN4: `Regras de Negócio`_  
.. _RN5: `Regras de Negócio`_  
.. _RN6: `Regras de Negócio`_  

Mensagens
^^^^^^^^^

Não há.
    
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

.. figure:: media/tela_uc208_01.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para listagem e visualização de professores.	   

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.