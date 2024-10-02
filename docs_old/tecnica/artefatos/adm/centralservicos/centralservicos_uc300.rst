.. include:: header.rst

.. _suap-artefatos-adm-centralservicos-uc300:

UC300 - Atendimento de Chamados <v0.1>
======================================

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
   * - 07/07/2014
     - 0.1
     - Início do Documento
     - Rafael Pinto

Objetivo
--------

.. _suap-artefatos-adm-centralservicos-uc300-objetivo:

Realizar o atendimento dos chamados dos usuários.


Atores
------

Principais
^^^^^^^^^^
Suporte/Atendimento

Interessado
^^^^^^^^^^^



Pré-condições
-------------
Cadastro do chamado.


Pós-condições
-------------


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^

FN1 – Encaminhar Solicitação de Autorização
"""""""""""""""""""""""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator seleciona a opção ``Encaminhar Solicitação de Autorização``
#. Na tela ``Encaminhar Solicitação de Autorização`` o ator preenche o campo ``Texto Livre``, com alguma informação adicional, caso deseje
#. O ator finaliza o caso de uso selecionando a opção ``Enviar``

FN2 – Adicionar Comentário
""""""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator seleciona algum chamado, visualizando seus detalhes
#. O ator clica no botão ``Adicionar Comentário``
#. Na tela ``Adicionar Comentário`` o ator preenche o campo ``Texto``
#. O ator finaliza o caso de uso selecionando a opção ``Salvar``

FN3 – Adicionar Nota Interna
""""""""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator seleciona algum chamado, visualizando seus detalhes
#. O ator clica no botão ``Adicionar Nota Interna``
#. Na tela ``Adicionar Nota Interna`` o ator preenche o campo ``Texto``
#. O ator finaliza o caso de uso selecionando a opção ``Salvar``

FN4 – Assumir Chamado
""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator clica no botão ``Assumir``
#. A atribuição é realizada e a listagem de chamados é atualizada com o nome do Ator na coluna de atribuição

FN5 – Escalar Chamado
"""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator clica no botão ``Escalar`` do referido chamado
#. O chamado é direcionado para o nível de atendimento imediatamente superior, o campo ``Atribuído Para`` torna-se vazio (disponível para nova atribuição)
#. A listagem de chamados é atualizada com as informações do chamado escalado

FN6 – Retornar Chamado
""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator clica no botão ``Retornar`` do referido chamado
#. O chamado é direcionado para o nível de atendimento imediatamente inferior, o campo ``Atribuído Para`` torna-se vazio (disponível para nova atribuição)
#. A listagem de chamados é atualizada com as informações do chamado escalado


FN7 – Atribuir Chamado
""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Chamados``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator clica no botão ``Atribuir``
#. Na tela ``Atribuir Chamado`` o ator preenche o campo ``Atribuído para``
#. O ator finaliza o caso de uso selecionando a opção ``Salvar`` registrando para quem o chamado está sendo atribuído

FN8 – Atualizar Status
""""""""""""""""""""""

#. O caso de uso é iniciado selecionando a opção ``Central de Serviços`` > ``Atendimento``
#. O sistema apresenta uma listagem de chamados, com opções de pesquisa por: ID, período, status, grupo de atendimento, atribuições (a quem está atribuído)
#. O ator seleciona algum chamado, visualizando seus detalhes
#. O ator clica no botão ``Alterar para <status>``
#. O status é atualizado


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


RIN01 – Campos para listagem de chamados
""""""""""""""""""""""""""""""""""""""""

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * -
     - Opções
     - Serviço
     - Em Nome De
     - Requisitante
     - Atribuído a
     - Aberto Em
     - Tempo Restante
     - Status
     - Autorizado
   * - Ordenação
     - Não
     - Sim
     - Sim
     - Sim
     - Sim
     - Sim
     - Não
     - Não
     - Não
   * - Filtro
     - Não
     - Sim
     - Sim
     - Sim
     - Sim
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
   * - Observações
     -
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

          Visualizar

     -
     -
     -
     -
     -
     -
     -
     -


.. _RIN02:

RIN02 – Campos para Atendimento do Chamado
""""""""""""""""""""""""""""""""""""""""""

.. list-table::
   :header-rows: 1
   :stub-columns: 0

   * - Informação
     - Tipo
     - Tamanho
     - Valor Inicial
     - Domínio
     - Máscara
   * - Serviço
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Em Nome De
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Requisitante
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Email do Requisitante
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Campus do Requisitante
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Cargo do Requisitante
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Telefone do Requisitante
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Ramal do Requisitante
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Data/Hora de Abertura
     - Data/Hora (Desabilitado)
     -
     -
     -
     -
   * - Tempo de Atendimento
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Status do Chamado
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Solução Aplicada
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Tipo Autorização
     - Texto (Desabilitado)
     -
     -
     -
       .. csv-table::
          :header: "Opções"
          :widths: 100

		  Não necessita
		  Chefe imediato do interessado
		  Diretor Admin. do Campus do interessado
		  Diretor Geral do Campus do interessado
		  Coordenador de TI do Campus
		  DIGTI
		  EAD
		  Designado pelo Suporte

     -
   * - Autorizado Por
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Atribuído à
     - Texto (Desabilitado)
     -
     -
     -
     -
   * - Comentários
     - Tabela
     -
     -
     -
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

		  Contato
		  Comentário
		  Data/Hora

     -
   * - Notas Internas
     - Tabela
     -
     -
     -
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

		  Contato
		  Nota
		  Data/Hora

     -
   * - Log de Operações
     - Tabela
     -
     -
     -
       .. csv-table::
          :header: "Rótulo"
          :widths: 100

		  Data/Hora
		  Texto

     -

Regras de Negócio
^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN01
     - | Ao atualizar o status do chamado para "Resolvido", o usuário deverá informar a solução aplicada utilizando a "Base de Conhecimento". Sempre que o status for atualizado, deverá ser enviado um email ao interessado informando o ocorrido.
   * - RN02
     - | Ao adicionar um "Comentário", deverá ser enviado um email informando o fato ao destinatário interessado (caso seja um comentário do atendente) ou ao atendente (caso seja um comentário do interessado).
   * - RN03
     - | A listagem de "Comentário" ou "Nota Interna", deverá ser ordenada por data (decrescente).
   * - RN04
     - | Apenas o responsável pelo Suporte (cadastrado no grupo de atendimento), poderá atribuir um chamado a determinado Atendente do Suporte.
   * - RN05
     - | Apenas poderá manipular o Chamado aberto, o Atendente do Suporte cujo chamado está atribuído.
   * - RN06
     - | Ao atribuir um chamado, o atendente deverá receber um email com a notificação da atribuição.
   * - RN07
     - | Ao escalar um chamado (para um nível superior), deverá ficar registrado (histórico), a quais grupos de atendimento o chamado foi atribuído, bem como data/hora, quem atribuiu. Ao Escalar, o chamado 'sobe' de nível, mas não fica atribuído a nenhum atendente.
   * - RN08
     - | Ao retornar um chamado (para um nível inferior), deverá ficar registrado (histórico), a quais grupos de atendimento o chamado foi atribuído, bem como data/hora, quem atribuiu. Ao Escalar, o chamado 'sobe' de nível, mas não fica atribuído a nenhum atendente.

.. _RN1: `Regras de Negócio`_



Mensagens
^^^^^^^^^

Não há.


.. _pde:

Ponto de Extensão
-----------------

Não há.


Questões em Aberto
------------------

Não há.

Esboço de Protótipo
-------------------

Tela de cadastro de serviços
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. image:: imagens/tela-atendimento-de-chamados.png

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

