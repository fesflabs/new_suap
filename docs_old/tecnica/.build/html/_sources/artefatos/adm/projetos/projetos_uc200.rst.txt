.. include:: header.rst

.. _suap-artefatos-adm-projetos-uc200:

UC200 - Cadastrar projeto <v0.1>
================================

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

Possibilitar que o servidor (Docente, Pesquisador, Empreendedor) cadastre e submeta seu projeto para avaliação.


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
O edital ao qual o projeto será submetido já estar cadastrado e com o período de inscrição aberto.


Pós-condições
-------------
Projeto pronto para pré-avaliação.


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^
.. _FN:

    #. O caso de uso é iniciado selecionando a opção ``Projetos de extensão`` > ``Cadastrar projeto`` na ``Home``
    #. O sistema apresenta a lista de ``Editais abertos`` (RIN01_):
    #. O ator seleciona a opção ``Submeter projeto``
    #. Na tela ``Cadastrar projeto`` o ator preenche os campos (RIN02_)
    #. O ator submete o projeto selecionando a opção ``Salvar``
    #. O caso de uso é encerrado quando o sistema executa o fluxo principal do caso de uso extendido (PDE_ 1)

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

Não há.


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

Não há.


Requisitos de Informação
^^^^^^^^^^^^^^^^^^^^^^^^

.. _RIN01:

RIN01 – Listagem de projetos
""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 1

   * - 
     - Título
     - Descrição
     - Arquivo digitalizado
     - Início das inscrições
     - Fim das inscrições
     - Campus
     - Opções
   * - Ordenação
     - Sim (padrão, ascendente)
     - Sim
     - Não
     - Sim
     - Sim
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
   * - Busca
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
     - Não
   * - Observações
     - 1
     - 2
     - 3 
     - 4
     - 5
     - 6
     -
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Submeter projeto


.. _RIN02:

RIN02 – Formulário de projeto
"""""""""""""""""""""""""""""

.. list-table:: 
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio/Máscara
     - Observações
   * - Edital*
     - Texto (somente leitura)
     - 255
     - 
     - 
     - 
   * - Campus*
     - Seleção (Combobox)
     - 
     - 
     - 
     - 
   * - Dados do projeto
     - Grupo
     - 
     - 
     - 
     - 
   * - Título do projeto*
     - Texto
     - 255
     - 
     - 
     - 
   * - Área do conhecimento
     - Seleção (Combobox)
     - 
     - 
     - 
     - 
   * - Área temática
     - Seleção (Combobox)
     - 
     - 
     - 
     - 
   * - Tema
     - Seleção (Combobox)
     - 
     - 
     - 
     - 
   * - Foco tecnológico*
     - Seleção (Combobox)
     - 
     - 
     - 
     - **Dica ao usuário:** O foco tecnológico do projeto deve coincidir com um dos focos tecnológicos de seu respectivo campus. Em caso de dúvida, consultar o edital.
   * - Público alvo*
     - Seleção (Combobox)
     - 
     - 
     - 
     - 
   * - Justificativa*
     - Texto longo
     - 1500
     - 
     - 
     - **Dica ao usuário:** A justificativa deve responder: Por que executar o projeto? Por que ele deve ser aprovado e implementado? Aqui deve ficar claro que o projeto é uma resposta a um determinado problema percebido e identificado pela comunidade ou pelo proponente. 1.500 caracteres).
   * - Resumo*
     - Texto longo
     - 1500
     - 
     - 
     - **Dica ao usuário:** Sua função é dar uma idéia geral do que se trata, seus objetivos, duração e custo, dentre outros. Escrever um bom resumo é extremamente importante, pois este tem que cativar o leitor a aprofundar-se no projeto e descobrir o quanto ele é importante, bem intencionado e efetivo. O resumo deverá ser uma das últimas seções a ser redigida, pois então teremos maior intimidade com o projeto. (espaço máximo de 1.500 caracteres).
   * - Objetivo Geral*
     - Texto longo
     - 500
     - 
     - 
     - **Dica ao usuário:** O objetivo geral deve expressar o que se quer alcançar na região a longo prazo, ultrapassando inclusive o tempo de duração do projeto. Geralmente o objetivo geral está vinculado à estratégia global da instituição. (espaço máximo de 500 caracteres).
   * - Metodologia da execução do projeto*
     - Texto longo
     - Sem limite
     - 
     - 
     - **Dica ao usuário:** A metodologia deve descrever as formas e técnicas que serão utilizadas para executar as atividades previstas, devendo explicar passo a passo a realização de cada atividade e não apenas repetir as atividades. Deve levar em conta que as atividades tem início, meio e fim, detalhando o plano de trabalho. Um projeto pode ser considerado bem elaborado quando tem metodologia bem definida e clara. É a metodologia que vai dar aos avaliadores/pareceristas, a certeza de que os objetivos/metas do projeto realmente tem condições de serem alcançados.
   * - Acompanhamento e avaliação do projeto durante a execução*
     - Texto longo
     - Sem limite
     - 
     - 
     - 
   * - Disseminação dos resultados*
     - Texto longo
     - Sem limite
     - 
     - 
     - **Dica ao usuário:** A divulgação das experiências bem sucedidas é de fundamental importância, tanto para a continuidade do projeto, quanto para o impacto positivo que o projeto pretende deixar na comunidade. As ações de disseminação dos resultados também precisam ser pensadas dentro de cada projeto. As propostas de divulgação poderão ser planejadas em nível local ou regional, incluindo os seguintes itens: Definição do que será objeto de divulgação (metodologias, técnicas, experiências); Definição dos produtos por meio dos quais será feita a divulgação (livros, artigos para revistas/jornais, vídeos, seminários, propriedades piloto); Definição das atividades de divulgação (palestras, reuniões); Definição da abrangência da divulgação (local ou regional); Definição do público que se pretende atingir (outras populações com características semelhantes às dos beneficiários do projeto, órgãos públicos, setores acadêmicos, organizações não governamentais, etc.
   * - Início da execução*
     - Data/Hora
     - 
     - 
     - 
     - 
   * - Término da execução*
     - Data/Hora
     - 
     - 
     - 
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

#. :ref:`suap-artefatos-adm-projetos-uc400`


Questões em Aberto
------------------

Não há.


Esboço de Protótipo 
-------------------

Não há.


Diagrama de domínio do caso de uso
----------------------------------

Não há.


Diagrama de Fluxo de Operação
-----------------------------

Não há.


Cenário de Testes
-----------------

Não foram definidos.

