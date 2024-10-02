# -*- coding: utf-8 -*-
from djtools.utils import send_notification
from django.conf import settings
from djtools.management.commands import BaseCommandPlus
from edu.models import Diretoria
from comum.models import UsuarioGrupo, Configuracao
import datetime


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        if datetime.datetime.today().weekday() > 4:
            return
        diretorias = Diretoria.objects.all()
        for diretoria in diretorias:
            membros_secretaria = UsuarioGrupo.objects.filter(group__name='Secretário Acadêmico', setores__id=diretoria.setor.pk)
            if membros_secretaria.exists():
                texto = (
                    '<h1>Ensino</h1>'
                    '<h2>Notificação de Pendências</h2>'
                    '<p>Caro(a) Secretário(a),</p>'
                    '<p>Existem algumas pendências relacionadas à diretoria {}.</p>'
                    '<br /><dl>'.format(diretoria.setor)
                )
                enviar_email = False
                ano = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or datetime.date.today().year)
                periodo = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)
                if diretoria.possui_pendencias(ano, periodo):
                    enviar_email = enviar_email or True
                    texto += '<dt>No período letivo {}.{}:</dt>'.format(ano, periodo)
                    secretarios = []
                    pendencias = diretoria.get_pendencias(ano, periodo)
                    for secretario in membros_secretaria:
                        secretarios.append(secretario.user.get_vinculo())
                    for pendencia in pendencias:
                        if not 'url' in pendencia:
                            pendencia['url'] = ''
                        texto += '<dd>* {}: <a href="{}{}">{}</a></dd>'.format(pendencia['nome'], settings.SITE_URL, pendencia['url'], pendencia['quantidade'])
                texto += '</dl>'
                if enviar_email:
                    titulo = '[SUAP] Notificação de Pendências: {}.'.format(diretoria.setor)
                    try:
                        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, secretarios, categoria='Ensino: Notificação de Pendências')
                    except Exception:
                        continue
