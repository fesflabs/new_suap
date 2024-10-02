# -*- coding: utf-8 -*-
import datetime

from django.conf import settings

from comum.models import Configuracao
from djtools.assincrono import task
from djtools.utils import send_notification


@task('Enviando Emails de Oferta de Estágio')
def enviar_emails(obj, task=None):
    if obj.data_fim >= datetime.date.today():
        contador = 0
        for curso in obj.cursos.all():
            contador += curso.aluno_set.count()
        task.start_progress(contador)
        for curso in obj.cursos.all():
            for aluno in task.iterate(curso.aluno_set.all()):
                if obj in aluno.get_ofertas_pratica_profissional():
                    url_servidor = Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')
                    titulo = '[SUAP] Oferta de Estágio ou Jovem Aprendiz para seu Curso Cadastrada'
                    assunto = (
                        '<h1>Oferta de Estágio ou Jovem Aprendiz para seu Curso Cadastrada</h1>'
                        '<p>Uma oferta de estágio ou jovem aprendiz para o curso {} foi cadastrada no SUAP. Para visualizá-la acesse o sistema ou acesse: '
                        '<a href="{}/estagios/oferta_pratica_profissional/{}/">Ofertas de Estágios ou Jovem Aprendiz</a>.</p>'.format(curso, url_servidor, obj.pk)
                    )

                    send_notification(titulo, assunto, settings.DEFAULT_FROM_EMAIL, [aluno.get_vinculo()])
    task.finalize('Emails enviados com sucesso.', obj.get_absolute_url())
