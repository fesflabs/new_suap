
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-subdiretorio-uc214: 


UC 214 - Gerir Projeto Final <v0.1>
===================================

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
   * - /07/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
   * - 29/07/2014
     - 0.2
     - 
       - Ajustes no protótipo de tela de cadastro para remover os campos relativos ao resultado final e incluí-los em uma nova tela.
       - Remoção das regras de negócio 6 e 7, as quais tratavam sobre a exibição da ação "Registrar Resultado"
     - Jailton Carlos


Objetivo
--------


Esta funcionalidade permitirá o usuário registrar os trabalhos de conclusão de curso 
(TCC) que poderá ser do tipo monografia, dissertação, tese, artigo ou capítulo de livro.


Atores
------

Principais
^^^^^^^^^^

Secretário, diretores acadêmicos ou administradores do sistema.

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------

Aluno matriculado no período.

Pós-condições
-------------

   Atualizar matricula do aluno conforme fluxo.
   Refletir a nota informada no diário do aluno.

Casos de Uso Impactados
-----------------------

    #. :ref:`suap-artefatos-edu-ensino-proc_apoio-uc502` : influência no cálculo no IRA
    #. :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc302` : Incluir flag "Exige TCC" ao lado do campo carga horária prática profissional
    #. :ref:`suap-artefatos-edu-ensino-cursos_matr_comp-uc303` : inclusão do tipo ``Trabalho de Conclusão de Curso``


Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado a partir do passo FA5.2 do caso de uso :ref:`suap-artefatos-edu-ensino-alunos_professores-uc202`, ao 
       acionar a  opção ``ENSINO`` > ``Alunos e Professores`` > ``Alunos``,  em seguida, selecionando a opção ``Ver`` 
       do aluno dentre um dos alunos disponíveis na listagem
    #. O secretário aciona a opção ``Projetos Finais``   
    #. O sistema exibe a lista de projetos finais registrados (RIN1_)
    #. O secretário aciona a opção ``Adicionar Projeto Final`` 
    #. O secretário informa os dados (RIN2_)
    #. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.3 


Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 - Editar (FN_.3)
""""""""""""""""""""

	#. O secretário aciona a opção ``Editar`` de um dos registros de projeto final disponíveis na listagem
	#. O sistema exibe o registro de projeto final com os dados (RIN2_) preenchidos
	#. O secretário informa novos valores para os dados (RIN2_) 
	#. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.3
	

FA2 - Visualizar (FN_.3)
""""""""""""""""""""""""

	#. O secretário aciona a opção ``Visualizar`` de uma das linhas do registro de projeto final disponíveis na listagem
	#. O sistema exibe informações da registro de projeto final (RI1_)


.. _FA3:
	
FA3 - Remover (FA1_.2)
""""""""""""""""""""""

    #. O secretário aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M3_
    #. O secretário confirma a exclusão.
    #. O sistema apresenta a listagem do passo FN_.3 
    	

.. _FA4:
   
FA3 - Registrar Resultado (FN_.3)
"""""""""""""""""""""""""""""""""

    #. O secretário aciona a ``Registrar Resultado`` de um dos projetos finais disponíveis na listagem
    #. O secretário informa novos valores para os dados (RIN3_) 
    #. O secretário finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M2_.
    #. O sistema apresenta a listagem do passo FN_.3
 
    	
Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Inclusão fere regra RN3_ (FA3_.1)
"""""""""""""""""""""""""""""""""""""""

   #. Exibir a mensagem relatada na regra de negócio
    

Especificação suplementares
---------------------------

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

Não há

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
     - Data/Hora da apresentação
     - Diário
     - Tipo
     - Título
     - Orientador
     - Situação
     - Nota
     - Data da defesa
     - Ação
   * - Ordenação
     - Não
     - Não
     - Não
     - Não
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
     - Não
     - Não
     - Não
     - Não
   * - Observações
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          ``Ver``
          ``Editar``
     - 
     - 
     -
     -
     -
     -
     -
     -
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          ``Registrar Resultado``, ver RN7_
          
          
A `Figura 1`_ exibe um esboço da listagem de registros de projetos finais.     


.. _RIN2:

RIN2 – Campos para Cadastros do trabalho final
""""""""""""""""""""""""""""""""""""""""""""""

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
   * - Diário*
     - Seleção
     - 
     - 
     - RN1_
     - Esse campo ficará oculto caso a regra de negócio não seja RN1_ não seja cumprida.
   * - Título*
     - Texto
     - 
     - 
     - 
     - 
   * - Tesumo*
     - Texto longo
     - 
     - 
     - 
     - 
   * - Tipo*
     - Seleção
     - 
     - 
     - Monografia, Dissertação, Tese, Artigo Científico, Capítulo de Livro
     - 
     
   * - Informações complementáres 
     - Texto longo
     - 
     - 
     - 
     - 
   * - Documento*
     - Anexar arquivo
     - 
     - 
     - Formato PDF
     -     
   * - Orientador*
     - Texto autocompletar simples
     - 
     - 
     - 
     - Busca no cadastro de professores (interno, externo) 
   * - Co-orientado(res) interno(s)
     - Texto autocompletar multiplo
     - 
     - 
     - 
     - Busca no cadastro de professores (interno, externo)
   * - Co-orientado(res) externo(s)
     - Texto autocompletar multiplo
     - 
     - 
     - 
     - Busca no cadastro de  :ref:`suap-artefatos-edu-ensino-subdiretorio-uc123`
   * - Data/Hora* da apresentação
     - Calendário
     - 
     - 
     - 
     -  
   * - Local*
     - Texto
     - 
     - 
     - 
     -    
   * - Presidente*
     - Texto autocompletar simples
     - 
     - 
     - 
     - Busca no cadastro de professores (interno, externo)
   * - Examinado(res) interno(s)
     - Texto autocompletar multiplos
     - 
     - 
     - 
     - Busca no cadastro de professores (interno, externo)
   * - Examinado(res) externo(s)
     - Texto autocompletar multiplos
     - 
     - 
     - 
     - Busca no cadastro de :ref:`suap-artefatos-edu-ensino-subdiretorio-uc123`
           

A `Figura 2`_ exibe um esboço do formulário de cadastro.


.. _RIN2:

RIN2 – Campos para Cadastros do resultado final
"""""""""""""""""""""""""""""""""""""""""""""""

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
   * - Data*
     - Calendário
     - 
     - 
     - 
     - 
   * - Nota/Conceito*
     - Texto
     - 
     - 
     - 
     - 
           

A `Figura 2`_ exibe um esboço do formulário de cadastro.

     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Listar somente os diários do período letivo corrente cuja vinculação com a matriz do curso do aluno é do tipo ``Trabalho de Conclusão de Curso`` ou ``Prática Profissional``.
       | mensagem: não há 
   * - RN2
     - | A ação ``Adicionar Projeto Final`` só estará disponível caso exista ao menos um diário do período letivo corrente cuja vinculação com a matriz do curso do aluno é do tipo 
         ``Trabalho de Conclusão de Curso`` ou ``Prática Profissional``.
       | mensagem: Não há diário do tipo ``Trabalho de Conclusão de Curso`` ou ``Prática Profissional`` registrado para este aluno no período letivo atual.
   * - RN3
     - | Ao acionar a opção ``Registrar Resultado``, o sistema deverá verificar se a situação do aluno no diário é diferente de ``Cursando``, caso seja, emitir
         um alerta e não mais permitir registrar a nota.
       | mensagem: Registro de resultado final não permitido, pois o diário <identificaçaõ do diário> cadastrado como projeto final possui situação difente de 
       | ``Cursando``.
   * - RN4
     - | Após qualquer alteração (Inclusão, edição, exclusão) o sistema deverá verificar se o aluno concluiu o curso, para isso, 
         deverá ser executado o fluxograma de atualização de status do aluno de matrícula.
       | Ver fluxo na `Figura 3`_.
       | mensagem: não há      
   * - RN5
     - | Uma vez informada a nota, após qualquer alteração (Inclusão, edição, exclusão), o sistema deverá refletir o valor da nota no respectivo diário do aluno.
       | No caso da exclusão, deverá atualizar a nota do diário do aluno para Nulo.
       | mensagem: não há.        

        
.. _RN1: `Regras de Negócio`_  
.. _RN2: `Regras de Negócio`_
.. _RN3: `Regras de Negócio`_
.. _RN4: `Regras de Negócio`_
.. _RN5: `Regras de Negócio`_

   
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
     - Cadastro realizado com sucesso.
   * - M2
     - Atualização realizada com sucesso.
   * - M3
     - Tem certeza que deseja continuar?       

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
    
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

.. figure:: media/uc214_listar_projeto_final.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo de tela para listagem de projetos finais cadastrados.
	   
	   
.. _`Figura 2`:
	   
.. figure:: media/uc214_adicionar_projeto_final.png
   :align: center
   :scale: 70 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 2: Protótipo de tela para cadastro de projeto final.	   
   
   

Diagrama de Fluxo de Operação
-----------------------------

O diagrama abaixo representa o fluxo de atividades necessárias para verificar se o aluno concluiu ou não o curso.


.. _`Figura 3`:
      
.. figure:: ../media/edu_fluxo_atualiza_status_aluno.png
   :align: center
   :scale: 70 %
   :figclass: align-center
   
   Figura 3: fluxograma de atualização de status do aluno .   



Cenário de Testes
-----------------

Não há.