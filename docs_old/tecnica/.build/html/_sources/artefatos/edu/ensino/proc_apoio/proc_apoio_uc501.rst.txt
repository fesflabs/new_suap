
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-proc_apoio-uc501: 

UC 501 - Abonar Faltas de Alunos <v0.2>
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
   * - 30/04/2014
     - 0.1
     - Início do Documento
     - Hugo Tácito
   * - 13/04/2014
     - 0.2
     - Mudanças do Cliente
     - Hugo Tácito

Objetivo
--------

Cadastrar ou remover o abono de faltas de alunos dentro de um período pré-definido.

Atores
------

Principais
^^^^^^^^^^

Administrador, Secretário, Diretor Acadêmico: permite gerir os abonos de faltas de alunos.

Interessado
^^^^^^^^^^^

Aluno.

Pré-condições
-------------

Devem existir alunos cadastrados.

Pós-condições
-------------

As faltas do aluno no período de tempo cadastrado serão marcadas como abonadas.

Casos de Uso Impactados
-----------------------

	#. :ref:`suap-artefatos-edu-ensino-proc_apoio-uc503` - O fechamento de período ignora as faltas de alunos marcadas como abonadas
	#. :ref:`suap-artefatos-edu-ensino-meus-diarios-uc402` - Exibe os abonos cadastrados
	#. :ref:`suap-artefatos-edu-ensino-diarios-uc403` - Altera a marcação de falta abonada

Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Procedimentos de Apoio`` > ``Abonar Faltas``
    #. O sistema exibe a lista de Abonos de Alunos (RIN1_)
    #. O secretário seleciona a opção ``Adicionar ``Abonos de Faltas````
    #. O secretário informa os dados (RIN2_) para identificar o Cadastro de Abono de Alunos
    #. Para cada Abono de Aluno que se deseja adicionar, o secretário deve informar os dados (RIN2_)  
    #. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Editar (FN_.2 )
"""""""""""""""""""""

	#. O secretário aciona a opção ``Editar`` dentre um dos abonos disponíveis na listagem
	#. O sistema exibe o Abono do Aluno com os dados (RIN3_) preenchidos
	#. O secretário informa novos valores para os dados (RIN2_) 
	#. Para cada Abono de Aluno que se deseja alterar, o secretário deve informar novos valores para os dados (RIN2_)  
	#. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
FA2 - Salvar e adicionar outro(a) (FN_.5)
"""""""""""""""""""""""""""""""""""""""""

	#. O secretário aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FN_.5 

.. _FA3:

FA3 - Salvar e continuar editando (FA1_.4)
""""""""""""""""""""""""""""""""""""""""""

	#. O secretário aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M5_.
	#. O caso de uso volta para o passo FA1_.4 	

.. _FA4:

FA4 – Listar (FN_.2)
""""""""""""""""""""

	#. O secretário restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA5:

FA5 - Visualizar um abono de aluno (FA4_.2)
""""""""""""""""""""""""""""""""""""""""""""

    #. O secretário aciona a opção ``Visualizar`` dentre um dos abonos disponíveis na listagem
    #. O sistema exibe as informações referentes ao abono de um aluno (RIN3_)
    
.. _FA6: 
 
FA6 - Excluir um abono de um aluno (FA5_.2)
""""""""""""""""""""""""""""""""""""""""""""

    #. O secretário aciona a opção ``Excluir`` disponível no início da exibição do ``Abonos de Faltas``
       para excluir um determinado abono de um aluno.
    #. O sistema exibe uma tela de confirmação exibindo a mensagem M6_.
    #. O secretário confirma.
    #. O sistema exclui o abono e exibe a mensagem M7_.

Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Cadastro fere Regra RN2_ (FN_-1)
"""""""""""""""""""""""""""""""""""""""

	#. O sistema exibe a mensagem M3_.


Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

Não há.

Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     
RIN1 – Campos para Listagem
""""""""""""""""""""""""""""
     
.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Ações
     - Aluno
     - Data de início
     - Data de Fim
   * - Ordenação
     - Não
     - Sim
     - Sim
     - Sim
   * - Filtro
     - Não
     - Não
     - Sim
     - Sim
   * - Busca
     - Não
     - Sim
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

.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

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
   * - Aluno*
     - Texto
     - 
     - 
     - RN8_
     - Autocompletar
   * - Data de Início*
     - Data
     - 
     - Dia atual
     - DD/MM/AAAA
     - 
   * - Data de Fim*
     - Data
     - 
     - Dia atual
     - DD/MM/AAAA
     - 
   * - Justificativa*
     - Texto
     - 
     - 
     - 
     - 
   * - Anexo
     - Arquivo
     - 
     - 
     - 
     - 

.. _RIN3:
     
RIN3 – Campos para Exibição
"""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 30
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
   * - Aluno
     - Texto (rótulo)
   * - Data de Início
     - Texto (rótulo)
   * - Data de Fim
     - Texto (rótulo)
   * - Justificativa
     - Texto (rótulo)
   * - Anexo
     - Arquivo
   * - Ações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Excluir	     

Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - O secretário e o diretor só podem criar, editar, excluir e visualizar abonos de alunos de seu próprio campus.  
   * - RN2
     - A Data de Fim deve ser maior que a Data de Início.
   * - RN3
     - Ao cadastrar um abono, todas as faltas cadastradas do aluno entre a Data de Início e a 
       Data de Fim tem seu estado alterado para abonada. 
   * - RN4
     - Ao excluir um abono, todas as faltas cadastradas do aluno entre a Data de Início e a
       Data de Fim tem seu estado alterado para não abonada.
   * - RN5
     - Durante o caso de uso de fechamento de período só serão computadas as faltas que não
       tiverem o estado de abonada.
   * - RN6
     - Apenas alunos cujo período letivo encontra-se aberto (matriculado) podem ter faltas abonadas ou rejeitadas.
   * - RN7
     - Durante o caso de uso de Lançar Falta (:ref:`suap-artefatos-edu-ensino-diarios-uc403`), as faltas para o aluno e período especificados, serão automaticamente abonadas.
   * - RN8
     - Somente alunos com período aberto podem ser acessados e com o mesmo campus do secretário ou diretor devem ser manipulados.
       
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
     - Cadastro de abono de faltas realizado com sucesso.
   * - M2
     - Atualização de abono de faltas realizada com sucesso.
   * - M3
     - A data de início deve ser menor que a data de fim do abono.
   * - M4
     - Abono do Aluno <campo Nome do Aluno> adicionado com sucesso. Você pode adicionar um outro Abono de Faltas abaixo.
   * - M5
     - Abono do Aluno <campo Nome do Aluno> modificado com sucesso. Você pode editá-lo novamente abaixo.
   * - M6
     - Tem certeza que deseja excluir?
   * - M7
     - Abono de falta de aluno excluído com sucesso.
   * - M8
     - Você não tem permissão para realizar isso.
   * - M9
     - O período de cadastro dos abonos do aluno <campo Nome do Aluno> deve estar aberto.

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_   
.. _M5: `Mensagens`_   
.. _M6: `Mensagens`_   
.. _M7: `Mensagens`_
.. _M8: `Mensagens`_
.. _M9: `Mensagens`_

Ponto de Extensão
-----------------
	
Não há.

Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

.. _`Figura 1`:

.. figure:: media/tela_uc28.png
   :align: center
   :scale: 70 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela.	

Diagrama de domínio do caso de uso
----------------------------------

.. _`Figura 2`:

.. figure:: media/cd_28.png
   :align: center
   :scale: 70 %
   :alt: diagrama de classe.
   :figclass: align-center
   
   Figura 2: Diagrama de classe.	

Diagrama de Fluxo de Operação
-----------------------------

.. _`Figura 3`:

.. figure:: media/fl_uc28.png
   :align: center
   :scale: 70 %
   :alt: diagrama de fluxo.
   :figclass: align-center
   
   Figura 3: Diagrama de fluxo.	

Cenário de Testes
-----------------

.. _TC01:

Fluxo Normal
^^^^^^^^^^^^

.. list-table:: 
   :header-rows: 0
   :stub-columns: 1
   :widths: 15 85

   * - Objetivo
     - Testar se está cadastrando um abono de aluno com período aberto
   * - Dados de Entrada
     - Aluno com o período aberto, Data de Início menor igual a Data de Fim e Justificativa
   * - Resultado Esperado
     - #. Uma abono de falta é cadastrado com os dados informados.
       #. Mensagem M1_.

Fluxo de Exceção 01
^^^^^^^^^^^^^^^^^^^

.. list-table:: 
   :header-rows: 0
   :stub-columns: 1
   :widths: 15 85

   * - Objetivo
     - Testar se a data de início é maior que a data de fim (RN2_) 
   * - Dados de Entrada
     - Aluno, Data de Início maior que a Data de Fim e Justificativa
   * - Resultado Esperado
     - #. Nenhum abono de falta é cadastrado.
       #. Mensagem M3_.

Regra de Negócio 01
^^^^^^^^^^^^^^^^^^^

.. list-table:: 
   :header-rows: 0
   :stub-columns: 1
   :widths: 15 85

   * - Objetivo
     - Testar se o secretário e o diretor estão no mesmo campus do aluno (RN1_)
   * - Dados de Entrada
     - Aluno com período ativo de campus diferente do campus do secretário, Data de Início maior que a Data de Fim e Justificativa
   * - Resultado Esperado
     - #. Nenhum abono de falta é cadastrado.
       #. Mensagem M8_.

Regra de Negócio 08
^^^^^^^^^^^^^^^^^^^

.. list-table:: 
   :header-rows: 0
   :stub-columns: 1
   :widths: 15 85

   * - Objetivo
     - Testar se está localizando apenas alunos no período em aberto (RN8_)
   * - Dados de Entrada
     - | Matricule os alunos João Paulo e João Marcos no período 2014.1
	   | Matricule João da Silva no periodo 2014.2
	   | Feche o período 2014.1
	   | Busca aluno João
   * - Resultado Esperado
     - Trazer a lista com apenas João da Silva
     
