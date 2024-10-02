.. _suap-ae-servico_social-index:

Serviço Social
==============

.. contents:: Conteúdo
    :local:
    :depth: 4

Introdução
----------

Finalidade
^^^^^^^^^^

O subsistema do Serviço Social gerencia e registra as atividades dos discentes em diversos âmbitos da instituição.

.. 
   Convenções
   ^^^^^^^^^^
   Para melhor apreensão deste manual, serão adotadas algumas convenções de conceitos e exibição de informações.

   Conceitos, termos e abreviações
   """""""""""""""""""""""""""""""

   .. include:: glossario.rst

Perfis envolvidos
-----------------

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Perfil
     - Finalidade
   * - :ref:`Aluno <suap-ae-servico_social-perfil-aluno>`
     - Permite preencher a Caracterização Socioeconômica e realizar inscrição para os programas do Serviço Social.
   * - :ref:`Assistente Social de Campus <suap-ae-servico_social-perfil-assistente_social>`
     - Permite gerenciar todos os programas e alunos do seu campus.
   * - :ref:`Coordenador de Atividades Estudantis <suap-ae-servico_social-perfil-coordenador_ae>`
     - Permite o controle financeiro das atividades do setor.
   * - :ref:`Bolsista do Serviço Social <suap-ae-servico_social-perfil-bolsista>`
     - Realiza os registros operacionais do Serviço Social.
   * - :ref:`Nutricionista <suap-ae-servico_social-perfil-nutricionista>`
     - Gerencia as atividades relacionadas ao programa de Alimentação.

Integração com outros Sistemas
------------------------------

Terminal do Refeitório
^^^^^^^^^^^^^^^^^^^^^^

O subsistema Atividades Estudantis integra-se com o Sistema Terminal do Refeitório no sentido de controlar qual aluno tem direito
à refeição no dia determinado. 

Relacionamento com outros Subsistemas
-------------------------------------

EDU
^^^

A integração com o subsistema EDU permite o acesso a todos as informações dos alunos da instituição.
	
Módulo Caracterização Socioeconômica
------------------------------------

Permite preencher o questionário de Caracterização Socioeconômica.

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade
   * - :ref:`suap-ae-servico_social-funcionalidade-caracterizacao`
     - Preenche/Edita questionário.
     
Módulo Atendimentos
-------------------

Registra diariamente os atendimentos concedidos pelo setor do Serviço Social ao aluno, como material didático, refeições, fardamento escolar,
visitas domiciliares, etc.

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade
   * - :ref:`suap-ae-servico_social-funcionalidade-adicionar_atendimento`
     - Registro o atendimento do setor a um aluno.

Módulo Ofertas
--------------

Registra as ofertas necessárias para os funcionamentos dos programas.

.. list-table::
   :widths: 40 60
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade
   * - :ref:`suap-ae-servico_social-funcionalidade-adicionar_oferta_refeicao`
     - Permite gerenciar as ofertas de Refeições para o campus.
   * - :ref:`suap-ae-servico_social-funcionalidade-adicionar_oferta_bolsa`
     - Permite gerenciar as ofertas de Bolsas de Iniciação Profissional para o campus.
   * - :ref:`suap-ae-servico_social-funcionalidade-adicionar_oferta_turma`
     - Permite gerenciar as ofertas de Turmas de Idiomas para o campus.

Módulo Inscrições
-----------------

Permite realizar e gerenciar as inscrições dos discentes nos programas de assistência estudantil.

.. list-table::
   :widths: 40 60 
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade     
   * - :ref:`suap-ae-servico_social-funcionalidade-abrir_periodo_inscricao`
     - Permite abrir período de inscrições para os programas de assistência estudantil.
   * - :ref:`suap-ae-servico_social-funcionalidade-efetuar_inscricao`
     - Permite que o discente efetue a sua inscrição nos programas de assistência estudantil.
   * - :ref:`suap-ae-servico_social-funcionalidade-gerenciar_inscricoes`
     - Permite gerenciar as inscrições realizadas.

Módulo Programas
----------------

Gerencia os programas de assistência estudantil.

.. list-table::
   :widths: 40 60 
   :header-rows: 1
   :stub-columns: 0

   * - Operação
     - Finalidade
   * - :ref:`suap-ae-servico_social-funcionalidade-gerenciar_participacoes`
     - Permite gerenciar as participações dos alunos nos programas de assistências estudantil.

