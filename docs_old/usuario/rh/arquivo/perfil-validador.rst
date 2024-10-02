.. _suap-rh-arquivo-perfil-validador:

Arquivos - Validador
====================

.. contents:: Conteúdo
    :local:
    :depth: 4

Introdução
----------

Finalidade
^^^^^^^^^^

Servidor cujo perfil de acesso possua permissão para **validar** arquivos. Esse perfil também pode **enviar** e **identificar** arquivos.

Glossário
^^^^^^^^^

.. include:: glossario.rst


.. 
   Fluxograma de Operação
   ----------------------

   .. note::
      Cole aqui um diagrama de atividade para representar o fluxo de operação por perfil.


Módulo Upload (Envio) de Arquivos
---------------------------------

.. include:: perfil-uploader.rst
   :start-after: Módulo Upload (Envio) de Arquivos
   :end-before: Regras relacionadas
   
   
Módulo Tratamento de Arquivos Pendentes
---------------------------------------

.. include:: perfil-identificador.rst
   :start-after: Módulo Tratamento de Arquivos Pendentes
   :end-before: Regras relacionadas

.. _suap-rh-arquivo-validar_arquivo:

Validar Arquivo
^^^^^^^^^^^^^^^

#. Acesse Gestão de Pessoas > Arquivos > Arquivos Pendentes
#. A tela "Arquivos Pendentes" é exibida.

   A seção **Servidores com Arquivos Pendentes** exibe uma lista com todos os servidores 
   que possuem arquivos que ainda não foram tratados (identificados e validados). Selecione 
   o servidor desejado através do ícone *visualizar*, localizado na coluna *Ações*, à esquerda. 

   .. note:: 
      Para mostrar apenas os servidores de um campus específico, selecione o campus desejado na seção "Filtrar por Campus" e confirme.
      
      
#. A tela "Arquivos Pendentes do Servidor" é exibida. Ela possui três abas/guias: "Arquivos a Identificar", "Arquivos a Validar" e 
   "Arquivos Rejeitados".

 - A aba/guia **Arquivos a Identificar** mostra uma lista com os arquivos pendentes do servidor. Selecione o arquivo através 
   do ícone *visualizar*, localizado na coluna *Ações*, à esquerda, ou clique sobre o nome do arquivo.
     
   .. note::
      É possível excluir o arquivo através do ícone *remover*, localizado também na coluna *Ações*.

   A tela "Identificar Arquivo" é exibida. Ela possui duas seções: "Identificação do Arquivo" e "Visualização do Arquivo". 
   
   A seção **Identificação do Arquivo** é utilizada para identificar ou rejeitar o arquivo (rejeitar imagem). A opção "Identificar" 
   deve ser marcada quando o tipo do arquivo é reconhecido, podendo ser selecionado através do campo "Tipo de Arquivo". A opção 
   "Rejeitar Imagem" deve ser marcada com o objetivo de rejeitar o arquivo. O motivo da rejeição pode ser registrado no campo 
   "Justificativa da Rejeição". Para confirmar a identificação ou rejeição do arquivo, finalize pressionando o botão "Salvar".
   
   A seção **Visualização do arquivo**, como o próprio nome diz, exibe o conteúdo do arquivo.
   
 - A aba/guia **Arquivos a Validar** mostra uma lista com os arquivos que já foram identificados. Selecione o arquivo através 
   do ícone *visualizar*, localizado na coluna *Ações*, à esquerda, ou clique sobre o nome do arquivo. 
   
   A tela "Validar Arquivo" é exibida. Ela possui duas seções: "Validação do Arquivo" e "Visualização do Arquivo". 
   
   A seção **Validação do Arquivo** é usada para validar ou rejeitar o arquivo (rejeitar imagem). A opção "Validar Arquivo" 
   deve ser marcada quando o arquivo é então validado, podendo confirmar o seu tipo através do campo "Tipo do arquivo". A opção 
   "Rejeitar imagem" deve ser marcada para rejeitar o arquivo por algum motivo, o qual pode ser registrado no campo 
   "Justificativa da Rejeição". Para confirmar a validação ou rejeição do arquivo, pressione o botão "Salvar". 

   A seção **Visualização do arquivo** exibe o conteúdo do arquivo.  
   
 - A aba/guia **Arquivos Rejeitados** mostra uma lista com os arquivos que foram rejeitados. Para visualizar o conteúdo 
   do arquivo que foi rejeitado, acesse o ícone *visualizar*, localizado na coluna *Ações*, à esquerda. A coluna 
   "Justificativa da rejeição" mostra o motivo pelo qual o documento foi rejeitado.

..
   Regras relacionadas
   """""""""""""""""""

   - Regra 1
   - Regra 2
   - Regra 3

   Manuais Relacionados
   --------------------
   