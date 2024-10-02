Fluxo de trabalho no Gitlab / git
=================================

.. contents:: Conteúdo
    :local:
    :depth: 4

O gerenciador de repositório do IFRN é o Gitlab ( `Sítio oficial`_ e Livro_ )

.. _`Sítio oficial`: https://about.gitlab.com/
.. _Livro: http://www.packtpub.com/gitlab-repository-management/book

Configuração global do git
--------------------------

::

   $ git config --global user.name "Túlio de Paiva"
   $ git config --global user.email "tulio.paiva@ifrn.edu.br"
   $ git config --global color.ui true



.. note::
   usar email institucional.
   as configurações refletem no arquivo *~/.gitconfig*

Fluxo do desenvolvedor IFRN
---------------------------

Cada **milestone** será um **branch**, então para criar um branch do suap relacionado ao milestone *branch-1*:

::

   $ git clone git@gitlab.ifrn.edu.br:cosinf/suap.git ou git clone http://gitlab.ifrn.edu.br/cosinf/suap.git
   $ cd suap
   $ git checkout -b branch-1



Docs: `Getting a Git Repository`_ e `Git Branching`_

.. _`Getting a Git Repository`: http://git-scm.com/book/en/Git-Basics-Getting-a-Git-Repository
.. _`Git Branching`: http://git-scm.com/book/en/Git-Branching-What-a-Branch-Is


Depois faça alterações, dê commit e mande para o Gitlab:

::

   $ git add <algum_arquivo>.<ext>
   $ git commit -m "[app] mensagem"
   $ git push origin branch-1




Docs: `Recording Changes to the Repository`_

.. _`Recording Changes to the Repository`: http://git-scm.com/book/en/Git-Basics-Recording-Changes-to-the-Repository


Trabalhar num branch que existe remotamente chamado *branch-remoto* (mas não localmente)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   $ git clone git@gitlab.ifrn.edu.br:cosinf/suap.git
   $ cd suap
   $ git checkout branch-remoto



Fazer pull request
^^^^^^^^^^^^^^^^^^

Antes de fazer um pull request, faça um merge de seu branch de trabalho com o HEAD do master:


::

   $ git pull origin master



Certifique-se que você não quebrou nenhum teste:


::

   $ ./manage.py test_suap


Depois que finalizar o branch pode fazer um **New Merge Request** (botão no próprio Gitlab)

Fluxo do colaborador externo
----------------------------

Colaboradores externos têm permissão somente de leitura nos repositórios do IFRN. Caso queira contribuir com código, deve ser feito um **Fork repository** (botão no próprio Gitlab) do projeto. **OBS: o fork deve ser feito pelo usuário do TIME.**

