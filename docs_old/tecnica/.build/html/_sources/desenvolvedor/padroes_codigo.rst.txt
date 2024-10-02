Padrões de código
=================

.. contents:: Conteúdo
    :local:
    :depth: 4
    
    
Padrões externos
----------------

* PEP8_
* `Django coding style`_

.. _PEP8: http://www.python.org/dev/peps/pep-0008/
.. _`Django coding style`: https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/

Imports
-------

* Usar preferencialmente o **Aptana**, organizar imports com ``ctrl+shift+o`` e remover imports desnecessários. Algumas regras sobre imports:

.. code:: python

   from modulo import * # não use import *
   from modulo import utils # indique o que você vai usar

   from suap.app.models import Classe # não use from suap
   from app.models import Classe # indique a app que você vai usar
   from django.conf import settings # se for importar o settings do suap, use de django.conf


Models
------

* Usar **id** como chave primária (padrão do django - não especificar a chave primária na declaração da classe de modelo)
* Preferir usar ORM a sql puro, mas quando for o jeito formatar sql com http://sqlformat.org/
* Campos ``CharField`` e ``TextField`` não devem ser ``null=True`` (https://docs.djangoproject.com/en/dev/ref/models/fields/#django.db.models.Field.null)
* Uma classe que trata "ocorrências de servidor" (e tem ForeignKey para classe Servidor) deve se chamar **ServidorOcorrencia**, e não OcorrenciaServidor.
* Validações sobre instância do modelo devem ser feitas no método clean_ , e não em forms.
* Padrão para referenciar classes em campos ```ForeignKey```:


.. _clean: https://docs.djangoproject.com/en/1.5/ref/models/instances/#django.db.models.Model.clean


.. code:: python

   chave_estrangeira = models.ForeignKey('app.ClasseTal') # evita erro de import circular; evita importar a classe de modelo


Usar choices ou uma nova tabela?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* **choices**: usar quando são dados de sistema e que o usuário não poderia cadastrar um novo dado. Ex: status de inventário, tipo de entrada etc. Nota: prefira usar choices com campo do tipo PositiveIntegerField para que seja mais fácil mudar o "label" quando for preciso; exceções são tipos bem conhecidos ou pré-determinados, como sexo ('F' e 'M') e estados brasileiros ('RN', 'RJ', 'RS'...).

.. code:: python

    # retirado de https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/
	class MyModel(models.Model):
	    DIRECTION_UP = 'U'
	    DIRECTION_DOWN = 'D'
	    DIRECTION_CHOICES = (
	        (DIRECTION_UP, 'Up'),
	        (DIRECTION_DOWN, 'Down'),
	    )


* **nova tabela**: usar quando são dados de usuário e que podem ser livremente editados. Ex: categoria de material, área de cursos acadêmicos etc

Forms
-----

* Usar django.forms sempre que possível (evitar escrever <form> no braço)
* Todo form deve estar no arquivo forms.py
* Todo form deve acabar com "Form" ou "FormFactory": ```AlgumaCoisaForm``` ou ```AlgumaCoisaFormFactory```
* Preferir usar atributo `fields` a `exclude`.

Views
-----


* Usar ```@rtr``` sempre que possível, Só criar template quando precisar (forms simples são renderizados pelo djtools/form.html)
* Preferir ```@permission_required``` a ```@group_required```


Templates
---------

* Não referenciar URLs no braço, usar o templatetag url_
* Tratar permissões com uso da variável perms_
* Preferir usar template filter ``format`` para exibir informações


.. _url: https://docs.djangoproject.com/en/1.3/ref/templates/builtins/#url
.. _perms: https://docs.djangoproject.com/en/1.5/topics/auth/default/#permissions


Admin
-----

* Usar admin sempre que possível (especialmente para CRUDs)
* Todo ModelAdmin deve estar em admin.py e deve herdar de ``ModelAdminPlus`` (não de django.contrib.ModelAdmin)
* Todo admin deve se chamar AlgumaCoisaAdmin
* Faça uso das `permissões default`_ do Django (add, change e delete).

.. _`permissões default`: https://docs.djangoproject.com/en/1.5/topics/auth/default/#default-permissions

Exemplos
--------

Exemplo: Funcionalidade de **visualização** de objeto da classe **Classe**:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code:: python

    ## models.py

	class Classe(models.Model):
	    ...
	    def get_absolute_url(self):
	        return '/app/classe/%d/' % self.pk # apontar para a URL de visualização do objeto
	
	## urls.py
	
	
	(r'^classe/(?P<pk>\d+)/$', 'classe'),
	
	## views.py
	
	
	@permission_required('app.change_classe')
	@rtr()
	def classe(request, pk):
	    obj = get_object_or_404(Classe, pk) # evita exceção DoesNotExist
	    title = unicode(obj) # o ``title`` é utilizado no breadcrumbs
	    return locals()

	## template
	
	# deve se chamar `classe.html` (se houver)



Exemplo: Ação **acao_um** sobre um objeto da classe **Classe**
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. code:: python

    ## models.py

	class Classe(models.Model):
	    ...
	    def acao_um(self):
	        ...
	
	## urls.py
	
	
	(r'^classe_acao_um/(?P<pk>\d+)/$', 'classe_acao_um'),
	
	## views.py
	
	
	@permission_required('app.change_classe')
	def classe_acao_um(request, pk):
	    obj = get_object_or_404(Classe, pk) # evita exceção DoesNotExist
	    obj.acao_um()
	    return httprr(obj.get_absolute_url(), 'Operação realizada com sucesso!')
	
	## template
	
	
	# deve se chamar `classe_acao_um.html` (se houver)


Misc
----


* Não usar palavras reservadas ou nomes de funções globais do python como vars, dir, id
* Nomes de variáveis e métodos devem estar em português: não usar **is**, usar **eh** ou **estah**; não usar **has**, usar **tem**.
* Formatação de dicionários ou parâmetros nomeados (alinhar o sinal de "="):

.. code:: python

	dict(atributo1 = 1,
	     at2       = 23,
	     atsds1    = 766)
	
	MinhaClasse.objects.filter(atributo1 = 1,
	                           at2       = 23,
	                           atsds1    = 766)


* Cabeçalho de arquivos python: 

.. code:: python

   # -*- coding: utf-8 -*-


* http://www.python.org/dev/peps/pep-0008/#other-recommendations
* https://docs.djangoproject.com/en/1.5/ref/models/options/#ordering