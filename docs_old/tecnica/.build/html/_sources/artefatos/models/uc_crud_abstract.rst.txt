
.. |logo| image:: ../../_static/images/logo_ifrn.png

.. |titulo| replace:: **Comum** 

.. include:: ../header.rst
   :start-after: uc-start
   :end-before: uc-end

.. _suap-artefatos-modelos-uccrudabstract:

Caso de Uso Abstrato para CRUD <v0.2>
=====================================  

.. contents:: Conteúdo
    :local:
    :depth: 4

Histórico da Revisão
---------------------

.. list-table:: **Histórico da Revisão**
   :widths: 10 5 30 15
   :header-rows: 1
   :stub-columns: 0

   * - Data
     - Versão
     - Descrição
     - Autor
   * - 14/02/2014
     - 0.1
     - Início do Documento
     - Jailton Carlos
   * - 17/02/2014
     - 0.0
     - Refinamento do Documento
     - Jailton Carlos

Objetivo
--------

Este caso de uso descreve as funcionalidades báscias de Incluir, Excluir, Alterar, Listar e Visualizar uma entidade.

Via de regra todos os caso de uso do tipo CRUD irão especializar este caso de uso.

As referencias aos Requisito de Interface (RI), Requisito de Informação (RIN) serão descritos no caso de uso especialista.


Pré-condições
-------------

O ator precisa está autenticado no sistema.


Fluxo de Eventos
----------------


Fluxo Normal
^^^^^^^^^^^^

.. _FN:

    #. O caso de uso é iniciado acionando a opção “ ” RI1    
    #. O sistema exibe a lista de entidades cadastradas conforme RIN1.
    #. O ator filtra (RIN1-3) a lista de entidades.
    #. O sistema exibe uma lista que satisfaça aos critérios informados no passo anterior.

Fluxo Alternativo
^^^^^^^^^^^^^^^^^

FA1 – Cadastrar Entidade
""""""""""""""""""""""""

   #. Incluir passos  1 e 2 do `Fluxo Normal`_.  
   #. O ator seleciona a opção Cadastrar definido em RI2.
   #. O ator informa os dados definidos em RIN2 (RN1_).
   #. O sistema exibe a mensagem M1_.
   #. O caso de uso retorna para o passo 2 do `Fluxo Normal`_.
   
.. _M1: `Mensagens`_  

FA2 - Alterar Entidade
""""""""""""""""""""""

   #. Incluir passos 1 e 2 do `Fluxo Normal`_.
   #. O ator aciona a opção Editar (padrão definido no SUAP).
   #. O sistema exibe a entidade com os dados preenchido.
   #. O ator informa novos valores para os dados definidos em RIN2 (RN1_).
   #. O sistema exibe a mensagem M2_.

.. _M2: `Mensagens`_   

FA3 - Excluir Entidade
""""""""""""""""""""""

O padrão adotado pelo SUAP é não disponibilizar essa opção ao ator. Se for necessário disponibilizá-la, deve descrever os fluxos no caso de uso especialista.

FA4 – Visualizar entidade
"""""""""""""""""""""""""

O padrão adotado pelo SUAP é não disponibilizar essa opção ao ator. Se for necessário disponibilizá-la, deve descrever os fluxos no caso de uso especialista.


Fluxo de Exceção
^^^^^^^^^^^^^^^^

Implícito na seção `Regras de Negócio`_.

Especificação suplementares
---------------------------
     
Regras de Negócio
^^^^^^^^^^^^^^^^^

.. _RN1 :

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Regra
     - Descrição / Mensagem
   * - RN1
     - | Entidade já existe (RIN4)
       | Mensagem: M3
   * - RN2
     - | Exclusão não permitida.
       | Mensagem: não se aplica.       
  
Mensagens
^^^^^^^^^

.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   :stub-columns: 0

   * - Código
     - Descrição
   * - M1    
     - Cadastro realizado com sucesso!
   * - M2    
     - Atualização realizada com sucesso!
   * - M3    
     - Definido no caso de uso especialista.       
     
Cenário de Testes
-----------------

Objetivos
^^^^^^^^^

O objetivo desde Caso de Testes é identificar o maior número possível de cenários e variações dos requisitos 
de software desde Caso de Uso. É dado um conjunto de dados de entradas, condições de execução, resultados 
esperados que visam validar esse caso de uso.

Casos e Registros de Teste
^^^^^^^^^^^^^^^^^^^^^^^^^^

Permissão Negada
""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Testar se o servidor negou o acesso ao usuário autenticado (grupo não definido).
   * - Dados de Entrada
     - 
   * - Resultado Esperado
     - 403 Forbidden     

Fluxo Alternativo `FA1 – Cadastrar Entidade`_
"""""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Testar se o cadastro é realizado com sucesso.
   * - Dados de Entrada
     - | Incluir o usuário previamente autenticado ao seu respectivo grupo.
       | Preencher os campos (RIN1) com valores válidos.
   * - Resultado Esperado
     - M1_

Fluxo Alternativo `FA2 - Alterar Entidade`_
"""""""""""""""""""""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Testar se a alteração ocorre com com sucesso.
   * - Dados de Entrada
     - | Incluir o usuário previamente autenticado ao seu respectivo grupo.
       | Preencher os campos (RIN1) com valores válidos.
   * - Resultado Esperado
     - M2_     

`Regras de Negócio`_ RN1
""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Testar cadastro em duplicidade.
   * - Dados de Entrada
     - | Incluir o usuário previamente autenticado ao seu respectivo grupo.
       | Preencher os campos (RIN1) com valores válidos e os campos (RIN3) com valores existentes em cadastros anteriores.
   * - Resultado Esperado
     - M3_

.. _M3: `Mensagens`

`Regras de Negócio`_ RN2
""""""""""""""""""""""""

.. list-table:: 
   :widths: 10 50
   :stub-columns: 1

   * - Objetivo
     - Testar se usuário tem acesso a exclusão
   * - Dados de Entrada
     - 
       .. warning::
             O que escrever aqui!
   * - Resultado Esperado
     - 403 Forbidden