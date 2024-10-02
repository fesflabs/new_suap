
.. |logo| image:: ../../../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Ensino** 

.. include:: ../../../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-edu-ensino-cursos_matr_comp-uc300: 

UC 300 - Manter Estrutura de curso <v0.1>
=========================================

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
   * - 28/04/2014
     - 0.1
     - Início do Documento
     - 

Objetivo
--------

Cadastrar, alterar, remove ou listar estrutura de curso.

Atores
------

Principais
^^^^^^^^^^

Administrador: permite gerir o cadastro de estrutura de cursos. 

Interessado
^^^^^^^^^^^

Não se aplica.

Pré-condições
-------------



Pós-condições
-------------



Fluxo de Eventos
----------------

Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção  ``ENSINO`` > ``Cursos, Matrizes e Componentes`` > ``Estrutura de Curso``
    #. O sistema exibe a lista de estruturas de curso (RIN1_)
    #. O administrador seleciona a opção ``Adicionar Estrutura de Curso``
    #. O administrador informa os dados (RIN2_)
    #. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
    #. O sistema exibe a mensagem M1_
    #. O sistema apresenta a listagem do passo FN_.2 

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

.. _FA1:

FA1 – Editar (FN_.2 )
"""""""""""""""""""""

	#. O administrador aciona a opção ``Editar`` dentre uma das estruturas de cursos disponíveis na listagem
	#. O sistema exibe a estrutura de curso com os dados (RIN2_) preenchidos
	#. O administrador informa novos valores para os dados (RIN2_) 
	#. O administrador finaliza o caso de uso selecionando a opção ``Salvar``
	#. O sistema exibe a mensagem M2_.
	#. O sistema apresenta a listagem do passo FN_.2 
	
FA2 - Salvar e adicionar outro(a) (FN_.4)
"""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e adicionar outro(a)``
	#. O sistema exibe a mensagem M3_.
	#. O caso de uso volta para o passo FN_.4

.. _FA3:

FA3 - Salvar e continuar editando (FA1_.3)
""""""""""""""""""""""""""""""""""""""""""

	#. O administrador aciona a opção ``Salvar e continuar editando``
	#. O sistema exibe a mensagem M4_.
	#. O caso de uso volta para o passo FA1_.3
	

FA4 – Listar (FN_.2)
""""""""""""""""""""

	#. O administrador restringe a lista usando o filtro e/ou busca (RIN1_)
	#. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior

.. _FA5:   

FA5 - Remover (FA1_.2) 
""""""""""""""""""""""

    #. O administrador aciona a opção ``Apagar`` 
    #. O sistema exibe a mensagem M5_
    #. O administrador aciona a opção "Sim, tenho certeza"
    #. O sistema exibe a mensagem M6_
    #. O administrador confirma a exclusão.
    #. O caso de uso volta para o passo FN_.2


FA6 – Visualizar (FN_.2)
""""""""""""""""""""""""

	#. O administrador aciona a opção ``Ver`` da estrutura de curso que se deseja visualizar dentre uma das 
	   estruturas de cursos disponíveis na listagem
	#. O sistema exibe informações da estrutura do curso (RI1_)

FA7 - Exportar para XLS (FN_.2)
"""""""""""""""""""""""""""""""
	#. O administrador aciona a opção ``Exportar para XLS`` 
	#. O sistema faz o download do arquivo com extensão .xls com as seguintes colunas (RIN1_) de acordo com a ordem existente na listagem


Fluxo de Exceção
^^^^^^^^^^^^^^^^

FE1 – Exclusão fere Regra RN1 (FA5_-1)
""""""""""""""""""""""""""""""""""""""

Especificação suplementares
---------------------------

Requisitos Não-Funcionais
^^^^^^^^^^^^^^^^^^^^^^^^^ 

Não há.

Requisitos de Interface
^^^^^^^^^^^^^^^^^^^^^^^

.. _RI1:

RI1 – Exibição de uma estrutura de curso 
""""""""""""""""""""""""""""""""""""""""


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN1:
     
RIN1 – Campos para listagem de estrutura de Curso
"""""""""""""""""""""""""""""""""""""""""""""""""


.. _RIN2:

RIN2 – Campos para Cadastros
""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 5 5 5 5 10
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observação
   * - Dados Gerais
     - 
     - 
     - 
     - 
     -
   * - **Descrição***
     - Texto
     - 
     - 
     - 
     - 
   * - Está Ativa
     - Boleano
     - 
     - 
     - 
     - 
   * - Aproveitamento de Disciplinas
     - 
     - 
     - 
     - 
     - 
   * - Max de Aproveitamentos
     - Inteiro
     - 
     - 
     - 
     - 
   * - Num Max de Certificações
     - Inteiro
     - 
     - 
     - 
     - 
   * - Média para Certificação
     - Inteiro
     - 
     - 
     - 
     - 
   * - Critérios de Apuração de Resultados por Período
     - 
     - 
     - 
     - 
     - 
   * - **Tipo de Avaliação***
     - Opção
     - 
     - 
     - Crédito/Seriado/Modular
     - 
   * - Qtd. Min. Disciplinas
     - Inteiro
     - 
     - 
     - 
     - Quantidade mínima de disciplinas por período letivo, mostrado apenas no regime de crédito.
   * - Num. Disciplinas a mais Permitidas do Período
     - Inteiro
     - 
     - 
     - 
     - Número máximo de disciplinas a mais do que há no período de referência. Só aparece para o Crédito.
   * - Qtd. máxima de períodos subsequentes ao período de referência para cursar disciplinas.
     - Inteiro
     - 
     - 
     - 
     - Dado o menor período no qual o aluno tem disciplina pendente igual a N, o aluno só poderá pagar disciplinas dos X períodos subsequentes informado neste campo. Só aparece para o Crédito.
   * - Número máximo de cancelamentos por Disciplina  
     - Inteiro
     - 
     - 
     - 
     - Dada uma disciplina X o aluno só poderá cancela-la N vezes ao longo do curso. Só aparece para o Crédito.
   * - Limite de Reprovações
     - Inteiro
     - 
     - 
     - 
     - Limite de reprovações que permite ficar em dependência, mostrado apenas no regime seriado.
   * - Critérios de Avaliação por Disciplinas
     - 
     - 
     - 
     - 
     - 
   * - **Critério de Avaliação***
     - Opção
     - 
     - 
     - Nota/Frequência
     - 
   * - Média para passar sem prova final
     - Inteiro
     - 
     - 
     - 
     - Mostrado apenas quando o critério de avaliação é por nota.
   * - Média para não reprovar direto
     - Inteiro
     - 
     - 
     - 
     - Mostrado apenas quando o critério de avaliação é por nota.
   * - Média para aprovação após avaliação final:
     - Inteiro
     - 
     - 
     - 
     - Mostrado apenas quando o critério de avaliação é por nota.
   * - Critérios de Apuração de Frequência
     - 
     - 
     - 
     - 
     - 
   * - **Percentual (%) de Frequência Mínimo para não Reprovar no Período***
     - Inteiro
     - 
     - 
     - 
     - É obrigatório sempre. * * * Mudança na regra. 
   * - Índice de Rendimento Acadêmico (I.R.A)
     - 
     - 
     - 
     - 
     - 
   * - **Forma de Cálculo***
     - Opção 
     - 
     - 
     - Média aritmética das Notas Finais/Média dos componentes pela carga horária dos componentes
     - 

   * - Critérios de Jubilamento
     - 
     - 
     - 
     - 
     - 
   * - **Qtd Max de Períodos***
     - Inteiro
     - 
     - 
     - 
     - **já existe e deve ser deslocado de Dados Gerais para Critérios de Jubilamento.** É um campo obrigatório.
   * - **Qtd Max de Reprovações no mesmo Período**
     - Inteiro
     - 
     - 
     - 
     - **Nova funcionalidade para implementação.** Este é um campo de preencimento opcional. Habilitado somente para o Regime de Crédito.
   * - **Qtd Max de Reprovações na mesma Disciplina**
     - Inteiro
     - 
     - 
     - 
     - **Nova funcionalidade para implementação** Este é um campo de preenchimento opcional.

   * - Representação Conceitual **Nova funcionalidade para implementação**
     - 
     - 
     - 
     - 
     - 
   * - 1º Conceito
     - Conceito
     - 
     - 
     - 
     - Um conceito é um texto e uma faixa de numérica de inteiros.
   * - 2º Conceito
     - Conceito
     - 
     - 
     - 
     - Um conceito é um texto e uma faixa de numérica de inteiros.
   
     
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
       | A remoção de Estrutura de Curso "<campo Descrição>" pode resultar na remoção de objetos relacionados, mas sua conta não tem a permissão para remoção dos seguintes tipos de objetos: 
   
.. _RN1: `Regras de Negócio`_   
   
   
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
     - Estrutura de Curso "<campo Descrição>" alterado com sucesso. Você pode adicionar um outro Estrutura de Curso abaixo.
   * - M4
     - Estrutura de Curso "<campo Descrição>" modificado com sucesso. Você pode editá-lo novamente abaixo. 
   * - M5
     - Você tem certeza que quer remover Estrutura de Curso "<campo Descrição>"? Todos os seguintes itens relacionados serão removidos:
   * - M6
     - Tem certeza que deseja continuar?        

.. _M1: `Mensagens`_     
.. _M2: `Mensagens`_
.. _M3: `Mensagens`_    
.. _M4: `Mensagens`_   
.. _M5: `Mensagens`_    
.. _M6: `Mensagens`_   


Ponto de Extensão
-----------------
	
Não há.

Questões em Aberto
------------------

- Ao editar, o campo "Percentual de Frequência" não está vindo preenchido.

Esboço de Protótipo 
-------------------

.. _`Figura 1`:

.. figure:: media/tela_uc300_manter_estrutura_de_curso.png
   :align: center
   :scale: 100 %
   :alt: protótipo de tela.
   :figclass: align-center
   
   Figura 1: Protótipo das novas informações no cadastro da estrutura de curso.

Diagrama de domínio do caso de uso
----------------------------------

Não há.

Diagrama de Fluxo de Operação
-----------------------------

Não há.

Cenário de Testes
-----------------

Não há.