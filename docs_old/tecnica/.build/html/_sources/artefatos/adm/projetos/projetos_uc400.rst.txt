.. include:: header.rst

.. _suap-artefatos-adm-projetos-uc400:

UC400 - Visualizar projeto <v0.1>
===============================

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
   * - 22/04/2014
     - 0.1
     - Início do Documento
     - Kelson da Costa Medeiros

Objetivo
--------

Visualizar os dados do projeto, tanto dos dados principais quanto dos dados filhos.

Atores
------

Principais
^^^^^^^^^^
* Servidor

Interessado
^^^^^^^^^^^
* Gerente sistêmico
* Pré-avaliador
* Avaliador


Pré-condições
-------------
O projeto já estar cadastrado.


Pós-condições
-------------
Não há.


Fluxo de Eventos
----------------


.. _FN:

Fluxo Normal
^^^^^^^^^^^^

.. note:: 

   Normalmente um caso de uso tem um ponto de inicialização definido de forma clara e única, entretanto,
   este caso é um `caso de uso extensor` que é originado a partir de pontos diferentes do sistema
   (e está correto neste comportamento), assim, o `ponto de inicialização` abaixo é apenas a forma
   escolhida para indicar se realizar estes caso de uso.

   .. important::

      Outros `ponto de inicialização`:

      Ainda não anotado.


#. O caso de uso é iniciado selecionando a opção ``EXTENSÃO`` > ``Projetos`` > ``Projetos``, então o ator escolhe um
   projeto da lista de projeto já cadastrados (RIN01_) e seleciona a opção ``Visualizar``
#. O sistema apresenta o formulário de visualização de projeto (RIN02_)


Fluxos Alternativos
^^^^^^^^^^^^^^^^^^^

FA1 – ??? (???)
"""""""""""""""""""""""""""

#. ?????


Fluxos de Exceção
^^^^^^^^^^^^^^^^^

FE1 – ???? (???)
""""""""""""""""""""""""""""""""""""""

#. ?????


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

.. _RIN01:

.. include:: projetos_uc200.rst
   :start-after: .. _RIN01
   :end-before: .. _RIN02


.. _RIN02:

RIN02 – Visualização do projeto
"""""""""""""""""""""""""""""""

* Todos os campos são somente para leitura.
* A visualização do projeto é composta pela RIN03_, RIN04_, RIN05_, RIN06_.


.. _RIN03:

RIN03 – Dados do edital
"""""""""""""""""""""""

* Deverá estar em uma caixa cujo título é ``Dados do edital``

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0
   :name: asdf

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observações
   * - Edital
     - Texto
     - 
     - 
     - 
     - 
   * - Descrição
     - Texto
     - 
     - 
     - 
     - 
   * - Início das inscrições
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Fim das inscrições
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Tipos de participantes
     - Listagem
     - 
     - 
     - 
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Alunos
          Professores
     - 
   * - Arquivo digitalizado
     - URL (download)
     - 
     - 
     - 
     - 
   * - Anexos
     - Listagem
     - 
     - 
     - 
     - A listagem será em *lista não ordenada* conforme: ``Nome do arquivo anexo``-``Nome do tipo de anexo``. O ``Nome do arquivo anexo`` deverá permitir que o usuário baixe o arquivo.


.. _RIN04:

RIN04 – Dados do projeto
""""""""""""""""""""""""

* Deverá estar em uma caixa cujo título é ``Dados do projeto``

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0
   :name: asdf

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observações
   * - Título do projeto
     - Texto
     - 
     - 
     - 
     - 
   * - Área do conhecimento
     - Texto
     - 
     - 
     - 
     - 
   * - Área temática/tema
     - Texto
     - 
     - 
     - 
     - 
   * - Foco tecnológico  
     - Texto
     - 
     - 
     - 
     - 
   * - Público-alvo
     - Texto
     - 
     - 
     - 
     - 
   * - Objetivo geral
     - Texto
     - 
     - 
     - 
     - 
   * - Justificativa
     - Texto
     - 
     - 
     - 
     - 
   * - Resumo
     - Texto
     - 
     - 
     - 
     - 
   * - Metodologia
     - Texto
     - 
     - 
     - 
     - 
   * - Acompanhamento e avaliação do projeto durante a execução
     - Texto
     - 
     - 
     - 
     - 
   * - Disseminação dos resultados
     - Texto
     - 
     - 
     - 
     - 
   * - Início da execução
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Fim da execução
     - Data/Hora
     - 
     - 
     - 
     - 


.. _RIN05:

RIN05 – Dados da pré-seleção
""""""""""""""""""""""""""""

* Deverá estar em uma caixa cujo título é ``Dados da pré-seleção``

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0
   :name: asdf

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observações
   * - Data da pré-seleção
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Pré-selecionado
     - Sim/Não
     - 
     - 
     - 
       .. csv-table::
          :header: "Status", "Rótulo"
          :widths: 20, 80
      
          "Sim", "Sim"
          "Não", "Aguardando divulgação"
     - 


.. _RIN06:

RIN06 – Dados da seleção
""""""""""""""""""""""""

* Deverá estar em uma caixa cujo título é ``Dados da seleção``

.. csv-table:: Listagem de avaliações
   :header: "", "Data da avaliação", "Pontuação por critério", "Pontuação parcial", "Parecer"

   "Tipo", "Data/Hora", "Número", "Número", "Texto"
   "Ordenação", "Não", "Não", "Não", "Não"
   "Filtro", "Não", "Não", "Não", "Não"
   "Busca", "Não", "Não", "Não", "Não"
   "Observações", "", "", "", ""

.. list-table:: Formulário com resultado das avaliações
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observações
   * - Pontuação total
     - Número
     - 
     - 
     - 
     - É a soma da ``pontuação parcial`` das avaliações que constam na listagem acima
   * - Data da divulgação
     - Sim/Não
     - 
     - 
     - 
     - 
   * - Selecionado
     - Sim/Não
     - 
     - 
     - 
       .. csv-table::
          :header: "Status", "Rótulo"
          :widths: 20, 80
      
          "Sim", "Sim"
          "Não", "Aguardando divulgação"
     -


Regras de Negócio
^^^^^^^^^^^^^^^^^

Não há.
   

Mensagens
^^^^^^^^^

Não há.
  

.. _pde:

Ponto de Extensão
-----------------
#. :ref:`suap-artefatos-adm-projetos-uc4000??`


Questões em Aberto
------------------

Não há.

Esboço de Protótipo 
-------------------

Diagrama de domínio do caso de uso
----------------------------------

Não há.


Diagrama de Fluxo de Operação
-----------------------------

Não há.


Cenário de Testes
-----------------

.. note:: Falta construir os cenários de teste.

.. comment

  Objetivos
  ^^^^^^^^^

  O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
  de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
  esperados que visam validar esse caso de uso.

  Casos e Registros de Teste
  ^^^^^^^^^^^^^^^^^^^^^^^^^^

  Fluxo de Exceção FE1
  """"""""""""""""""""

  .. list-table:: 
     :widths: 10 50
     :stub-columns: 1

     * - Objetivo
       - 
     * - Dados de Entrada
       - 
     * - Resultado Esperado
       - 
     
