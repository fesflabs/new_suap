
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-diarios-uc401: 

UC 401 - Gerir Turmas <v0.1>
============================

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
   * - 30/04/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Permite gerar, listar e visualizar turmas, bem como possibilita a inclusão/remoção de alunos em turmas.


Atores
------

Secretário: tem acesso a gerenciar a criação de turmas.

Principais
^^^^^^^^^^

Secretário

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

- Deve exitir uma Matriz/Curso disponível (RN4_)
- Deve existir ao menos um turno
- Deve existir um horário de campus disponível (RN8_)
- Deve existir um calendário acadêmico disponível (RN6_)

Pós-condições
-------------

- É criado uma turma com código (RN5_) e descrição (RN7_) gerados automáticamentes
- É criado um diário e vinculado a turma para cada componente curricular do curso/matriz
- 

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Turmas e Diários`` > ``Turmas``
    #. O sistema exibe a lista de turmas (RIN1_)
    #. O secretário seleciona a opção `Gerar Turmas``
    #. O secretário informa ano letivo, período letivo e matriz/curso (RIN2_.1)
    #. O secretário informa nº de turmas, turno e nº de vagas (RIN2_.2)
    #. O sistema exibe a lista de componentes disponíveis (RN3_) da matriz/curso informado no passo 4
    #. O secretário informa horário do campus, calendário acadêmico (RIN2_.3) e seleciona ao menos um componente da listagem
    #. O sistema exibe um resumo da operação (RI2_)
    #. O secretário confirma a criação da turma.

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Editar (FN_.2 )
"""""""""""""""""""""

	#. O secretário aciona a opção ``Editar`` dentre um das turmas disponíveis na listagem
	#. O sistema exibe o código da turma preenchidos
	#. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	

FA2 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O secretário aciona a opção ``Salvar e continuar editando``
	#. O sistema exib3 a mensagem M3_.
	#. O caso de uso volta para o passo FA1_.3 	

FA3 - Listar (FN_.2)
""""""""""""""""""""

	#. O secretário restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

FA4 - Remover (FA1_.2) 
""""""""""""""""""""""

    #. O secretário aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M4_
    #. O secretário aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M5_
    #. O secretário confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2


FA5 - Exportar para XLS (FN_.2)
"""""""""""""""""""""""""""""""
	#. O secretário aciona a opção ``Exportar para XLS`` 
	#. O sistema faz o download do arquivo com extensão .xls com as seguintes colunas (RIN1_) de acordo com a ordem existente na listagem


FA6 - Visualizar (FN_.2)
""""""""""""""""""""""""

	#. O secretário aciona a opção ``Ver`` da turma que se deseja exibir
	#. O sistema exibe informações da turma (RI1_)
	#. O sistema exibe informações sobre os diário (ver RI1_) e os alunos matriculados (ver RIN1 do caso de uso PE_.1):	
	   

Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1_ (FA4_-1)
"""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RI1 – Exibição de uma turma 
"""""""""""""""""""""""""""

Os dados da turma é exibida dentro de uma caixa de nome "Dados Gerais", são eles:

- ``Descricao``: <campo descricao> 
- ``Codigo``: <campo codigo>
- ``Ano/Período Letivo``: < campo ano_letivo>/<campo periodo_letivo>
- ``Curso``: <nome do curso com link para exibição (ver caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc304`)
- ``Matriz``: <nome da matriz com link para exibição (ver caso de uso :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc32`)
- ``Calendário Acadêmico``: <nome do calendário acadêmico com link para exibição (ver caso de uso :ref:`suap-artefatos-edu-ensino-proc_apoio-uc33`)
- ``Período na Matriz``: <campo periodo_matriz>

Além da caixa "Dados Gerais" é exibida duas abas, uma com os diários e outra com os alunos matriculados:

- aba Diários

	.. list-table:: 
	   :header-rows: 1
	   :stub-columns: 1
	
	   * - 
	     - Ações
	     - Código
	     - Componente
	     - Percentual Mínimo (CH)
	     - Quantidade de Vagas
	     - Carga Horária Ministrada (%)
	   * - Ordenação
	     - Não
	     - Não
	     - Não
	     - Não
	     - Não
	     - Não	     
	   * - Filtro
	     - Não
	     - Não
	     - Não
	     - Não
	     - Não
	     - Não
	   * - Busca
	     - Não
	     - Não
	     - Não
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
	     - A carga horária ministrada será exibida em uma barra de progressão, a qual é baseada conforme regra de negócio RN2_

- Aba Alunos

  Ver RIN1 do caso de uso PE_.1

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     
RIN1 – Campos para listagem de turmas
""""""""""""""""""""""""""""""""""""""
 
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Código
     - Descrição
     - Ano Letivo
     - Período Letivo
     - Campus
   * - Ordenação
     - Não
     - Sim
     - Sim
     - Sim
     - Sim
     - Não    
   * - Filtro
     - Não
     - Não
     - Sim
     - Sim
     - Sim
     - Não  
   * - Busca
     - Não
     - Sim
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
          Editar
     - 
     - 
     -
     -  
     -

.. note::
   Além dos campos descritos na tabela acima disponíveis para filtro, há também o campo ``Filtrar por Curso`` do tipo 
   texto autocompletar simples, o qual restringe a lista para exibir somente as turmas referente ao curso informado no filtro.

.. _RIN2:

RIN2 – Exibição do resumo apra gerar turmas 
""""""""""""""""""""""""""""""""""""""""""""

.. _RIN2:


RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

	#. Passo 1 de 4

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
		   * - Ano Letivo*
		     - Seleção
		     - 
		     - 
		     - 
		     - 
		   * - Período Letivo*
		     - Seleção
		     - 
		     - 
		     - 1 e 2
		     -      
		   * - Matriz / Curso*
		     - Texto autocompletar simples
		     - 
		     - 
		     - RN4_
		     - 

	#. Passo 2 de 4

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
		   * - Número de Turmas*
		     - Seleção
		     - 
		     - 
		     - 1, 2, 3 e 4
		     - 
		   * - Turno*
		     - Seleção
		     - 
		     - 
		     - 
		     -      
		   * - Nº de Vagas*
		     - Texto númerico
		     - 
		     - 
		     - 
		     - 	       
		        
	#. Passo 3 de 4

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
		   * - Horário do Campus*
		     - Seleção
		     - 
		     - 
		     - RN8_
		     - 
		   * - Calendário Acadêmico*
		     - Seleção
		     - 
		     - 
		     - RN5_ 
		     -       
     

.. list-table:: Listagem de campos ocultos
   :widths: 10 20 5 5 5 5
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - codigo*
     - 
     - 
     - 
     - RN6_
     - Oculto
   * - Descrição*
     - Seleção
     - 
     - 
     - RN7_ 
     - Oculto          

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Exclusão fere integridade relacional.
       | mensagem: A remoção de Horário do Campus pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
   * - RN2
     - | Critério para calcular a progressão da barra de progressão ``Carga Horária Ministrada``: 
       | mensagem: não há.
   * - RN3
     - | Critério para exibição de componentes: 
       | mensagem: não há.
   * - RN4
     - | Critério para exibição de matriz/curso: lista os cursos/matrizes ativas e que possuem as mesmas diretorias na qual o usuário logado possui vínculo, ano letivo maior que a data de criação da matriz e ter ao menos um horário de campus e um calendário acadêmico cadastrado no campus 
       | mensagem: não há. 
   * - RN5
     - | Critério para exibição de calendário acadêmico: listar os calendários acadêmicos do campus na qual a unidade organizacional seja igual a ditoria do curso 
       | mensagem: não há.         
   * - RN6
     - | Critério para geração do código da turma: é a junção dos campos separados por "." (ponto): <ano_letivo.ano>.<periodo_letivo>.<periodo_matriz>.<curso_campus.codigo>.<sequencial>.<turno.descricao>
       | mensagem: não há.   
   * - RN7
     - | Critério para geração da descrição da turma: é a junção dos campos separados por "." (ponto): <curso_campus.descricao_historico>.<cuso_campus.modalidade.descricao>.<periodo_letivo>.<turno.descricao>.<ano_letivo.ano>
       | mensagem: não há.   
   * - RN8
     - | Critério para exibição de horário do campus: listar os horários dos campi onde a unidade organizacional seja igual diretoria do curso.
       | mensagem: não há.    

.. _RN1: `Regras de Negócio`_
.. _RN2: `Regras de Negócio`_
.. _RN3: `Regras de Negócio`_
.. _RN4: `Regras de Negócio`_
.. _RN5: `Regras de Negócio`_
.. _RN6: `Regras de Negócio`_
.. _RN7: `Regras de Negócio`_
.. _RN8: `Regras de Negócio`_

   
Mensagens
^^^^^^^^^

.. _M:

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Código
     - Descrição
   * - M1    
     - As seguintes turmas e diários serão criados/atualizados ao final da operação. Caso tenha certeza que deseja criá-los/atualizá-los,
       marque o checkbox de confirmação no final da página e submeta o formulário.
   * - M2
     - Atualização realizada com sucesso.       
   * - M3
     - Turma <campo codigo> modificado com sucesso. Você pode editá-lo novamente abaixo.
   * - M4
     - Você tem certeza que quer remover Turma "<campo codigo>"? Todos os seguintes itens relacionados serão removidos:    
   * - M5
     - Tem certeza que deseja continuar?                   

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_   
.. _M5: `Mensagens`_   
.. _M6: `Mensagens`_   


.. _PE:

Ponto de Extensão
-----------------
	
	#. :ref:`suap-artefatos-edu-ensino-diarios-uc400` 

Questões em Aberto
------------------

- É possível criar uma turma de ano anterior ? Por quê?
- A listagem de matriz/curso do passo 1-4 deveria listar os cursos/matrizes que possuem as mesmas diretoria do 
  secretário (ver vincular diretoria), ano letivo maior que a data de criação da matriz!? Posso tratar horário do campus e calendário acadêmico 
  como pré-condição ou um fluxo de exceção:
  
  - pré-condição: listar somente as matrizes/curso em que há ao menos um horário de campus e um calendário acadêmico cadastrado no campus
  
  - fluxo de exceção: gerar uma exceção caso o ator tenha selecionado uma matriz/curso com horário do campus vazio ou calendário acadêmico vazio.
  
- Ao gerar os diários, verificar se a quanitidade suportada pela sala é compatível com o número de vaga informado no 
  passo 2-4;
- Número de vagas (2-4) deveria ser obrigatório? Até esse ponto não tempo como identificar se o curso será prsencial ou EAD?
- Número de turma, por que a opção 0 (zero)? Se selecionar zero, ocorre o erro "UnboundLocalError at /edu/gerar_turmas/" ao final
- Listar os calendários acadêmicos somente do período selecionado !? 
- Quantidade de Vagas representa o quê? Inicialmente pensei que fosse o número de vagas informado no passo 2-4.
- Por que listar os componentes que já foram vinculados em uma turma no mesmo período? O sistema detecta e ao final dos passos
  informa que já existe a turma e o(s) componente(s) previamente selecionado(s).


Esboço de Protótipo 
-------------------

Não há.

Diagrama de domínio do caso de uso
----------------------------------

Definições:

| Azul: instâncias e associações criadas;
| Verde: classes exibidas em listagens;
| Amarelo: classes relacionadas direta ou indiretamente.

.. _`Figura 1`:

.. figure:: media/gerar_turmas_diagrama_classes.png
   :align: center
   :scale: 70 %
   :alt: diagrama de classe
   :figclass: align-center
   
   Figura 1: Diagrama de classe de domínio

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.