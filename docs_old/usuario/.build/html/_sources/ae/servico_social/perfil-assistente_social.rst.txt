.. _suap-ae-servico_social-perfil-assistente_social:

Serviço Social - Assistente Social de Campus
============================================

.. contents:: Conteúdo
    :local:
    :depth: 4


Introdução
----------

Finalidade
^^^^^^^^^^

Permite gerenciar todos os programas e alunos do seu campus.

..
   Fluxograma de Operação
   ----------------------

   .. note::
      Cole aqui um diagrama de atividade para representar o fluxo de operação por perfil.

.. include:: ../glossario.rst


Módulo Atendimentos
-------------------

.. _suap-ae-servico_social-funcionalidade-adicionar_atendimento:

Adicionar Atendimento para Aluno
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. |adicionar-atendimento| image:: ../images/adicionar-atendimento.png

#. Acesse Atividades Estudantis > Serviço Social > Atendimentos
#. Clique em "Adicionar Atendimento para Aluno"
#. O sistema exibirá a seguinte tela para que o usuário informe os dados necessários: 
   |adicionar-atendimento|
#. Clique em "Salvar"


Módulo Ofertas
--------------

.. _suap-ae-servico_social-funcionalidade-adicionar_oferta_refeicao:

Adicionar Oferta de Refeição
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. |oferta-refeicao| image:: ../images/oferta-refeicao.png

#. Acesse Atividades Estudantis > Ofertas > Refeições
#. Clique em "Adicionar Oferta de Refeições"
#. O sistema exibirá a seguinte tela para que o usuário informe os dados necessários: 
   |oferta-refeicao|
#. Clique em "Salvar"

.. _suap-ae-servico_social-funcionalidade-adicionar_oferta_bolsa:

Adicionar Oferta de Bolsa de Iniciação Profissional
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. |oferta-bolsa| image:: ../images/oferta-bolsa.png

#. Acesse Atividades Estudantis > Ofertas > Bolsa de Iniciação Profissional
#. Clique em "Adicionar Oferta de Bolsa de Iniciação Profissional"
#. O sistema exibirá a seguinte tela para que o usuário informe os dados necessários:
   |oferta-bolsa|
#. Clique em "Salvar"

.. _suap-ae-servico_social-funcionalidade-adicionar_oferta_turma:

Adicionar Oferta de Turma de Idiomas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. |oferta-turma| image:: ../images/oferta-turma.png

#. Acesse Atividades Estudantis > Ofertas > Turmas de Idioma
#. Clique em "Adicionar Oferta de Turma de Idioma"
#. O sistema exibirá a seguinte tela para que o usuário informe os dados necessários: 
   |oferta-turma|
#. Clique em "Salvar"


Módulo Inscrições
-----------------

Situações de Inscrição
^^^^^^^^^^^^^^^^^^^^^^

A seguir são exibidas as possíveis situações de inscrição de um discente em um programa:

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Situação
     - Descrição
   * - Ativa
     - Informa que a inscrição ainda está passível de ser participante em algum programa.
   * - Documentada
     - Informa que o aluno entregou a documentação referente à inscrição do programa.
   * - Prioritária
     - Informa que o aluno possui prioridade em receber o benefício do programa.
   * - Participante
     - Informa que o aluno está atualmente recebendo o benefício do programa.
   * - Suspensa
     - Informa que o aluno está temporariamente impedido de receber o benefício do programa.

Confira as possíveis situações de um aluno, quando cadastrado em um programa, de acordo com a ação realizada:

.. list-table::
   :widths: 50 10 10 10 10 10
   :header-rows: 1
   :stub-columns: 0

   * - Ação / Situação
     - Ativa
     - Documentada
     - Prioritária
     - Participante
     - Suspensa
   * - Aluno inscrito no programa.
     - Sim
     - Não
     - Não
     - Não
     - Não
   * - Aluno entrega documentação.
     - Sim
     - Sim
     - Não
     - Não
     - Não
   * - Aluno é selecionado como prioridade no programa.
     - Sim
     - Sim
     - Sim
     - Não
     - Não 
   * - Aluno é selecionado como participante de um programa
     - Sim
     - Sim
     - Sim/Não
     - Sim
     - Não 
   * - Aluno é desligado de um programa.
     - Sim
     - Sim
     - Sim/Não
     - Não
     - Não 
   * - Aluno é suspenso de um programa.
     - Sim
     - Sim
     - Sim/Não
     - Sim
     - Sim
   * - Aluno é selecionado como inativo em um programa.
     - Não
     - Sim/Não
     - Sim/Não
     - Não
     - Não   

.. _suap-ae-servico_social-funcionalidade-abrir_periodo_inscricao:

Abrir Período de Inscrição
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. |abrir-periodo-inscricao| image:: ../images/abrir-periodo-inscricao.png

Para realizar a abertura de um período de inscrição para posterior adesão da comunidade acadêmica, faça o seguinte:

#. Acesse Atividades Estudantis > Serviço Social > Períodos de Inscrição
#. No formulário de "Abrir Período de Inscrição", informe os dados necessários conforme:
   |abrir-periodo-inscricao|
#. Clique em "Enviar Dados"

.. _suap-ae-servico_social-funcionalidade-efetuar_inscricao:

Efetuar Inscrição
^^^^^^^^^^^^^^^^^

.. |efetuar-inscricao| image:: ../images/efetuar-inscricao.png
.. |detalhamento-inscricao| image:: ../images/detalhamento-inscricao.png

#. Acesse Atividades Estudantis > Serviço Social > Inscrições
#. Clique em "Efetuar Inscrição"
#. Em Identificação (ver tela abaixo), preencha o formulário com os dados necessários:
   |efetuar-inscricao|
#. Clique em "Enviar Dados"
#. Em Caracterização, confira os dados do aluno e clique em "Confirmar"
#. Em Detalhamento (ver tela abaixo), preencha o formulário com os dados necessários:
   |detalhamento-inscricao|
#. Clique em "Enviar Dados"

.. _suap-ae-servico_social-funcionalidade-gerenciar_inscricoes:

Gerenciar Inscrições
^^^^^^^^^^^^^^^^^^^^

#. Acesse Atividades Estudantis > Serviço Social > Inscrições
#. No aluno desejado, clique no ícone Checkbox*
#. Em Ação, selecione a ação desejada
#. Clique em "Aplicar"

.. note::
   para realizar uma ação para mais de um aluno, basta marcar as caixas respectivas aos demais 
   alunos e prosseguir com o processo descrito anteriormente.

Documentar Inscrição
""""""""""""""""""""

Para que um aluno possa se tornar participante de um programa, o Serviço Social deve validar os dados financeiros do aluno, 
através da verificação da documentação apresentada pelo aluno. Esse processo deve ser realizado da seguinte forma:

#. Acesse Atividades Estudantis > Serviço Social > Inscrições
#. No aluno desejado, clique no ícone Checkbox*
#. Em Ação, selecione a opção "Registrar entrega de documentação"
#. Clique em "Aplicar"


Módulo Programas
----------------

.. _suap-ae-servico_social-funcionalidade-gerenciar_participacoes:

Gerenciar Participações
^^^^^^^^^^^^^^^^^^^^^^^

.. |adicionar-participacao| image:: ../images/adicionar-participacao.png

#. Acesse Atividades Estudantis > Serviço Social > Programas
#. No programa desejado, clique no ícone Visualizar*
#. Clique em "Gerenciar Participações"
#. Localize o aluno desejado e clique em "Adicionar Participação", a seguinte tela será exibida:
   |adicionar-participacao|
#. Clique em "Salvar"

.. note::
   - Para realizar este processo, o aluno deverá estar com a documentação entregue.

   