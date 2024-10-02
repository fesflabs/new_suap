# -*- coding: utf-8 -*-

import datetime
from datetime import timedelta

from djtools.management.commands import BaseCommandPlus
from projetos.models import Projeto, ProjetoCancelado
from django.conf import settings
from djtools.utils import send_notification
from dateutil.relativedelta import relativedelta


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        hoje = datetime.datetime.now()
        projetos_cancelados = ProjetoCancelado.objects.filter(cancelado=True).values_list('projeto', flat=True)
        projetos_em_execucao = Projeto.objects.filter(
            pre_aprovado=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, edital__divulgacao_selecao__lt=hoje
        ).exclude(id__in=projetos_cancelados)
        dispara_email_atraso = hoje.day == 1
        for projeto in projetos_em_execucao:
            if projeto.vinculo_coordenador:
                coordenador = projeto.vinculo_coordenador
            else:
                coordenador = projeto.get_responsavel()

            if dispara_email_atraso and projeto.tem_atividade_com_prazo_expirado():
                titulo = '[SUAP] Projeto de Extensão: Atividades em Atraso'
                texto = (
                    '<h1>Projeto de Extensão</h1>'
                    '<h2>Projeto: "{}"</h2>'
                    '<p>Olá, {}. O projeto {}, sob sua coordenação, possui atividades em atraso. Acesse o SUAP para mais detalhes.</p>'
                    ''.format(projeto.titulo, coordenador.pessoa.nome, projeto.titulo)
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [coordenador])

            if (hoje.date() + timedelta(15)) == projeto.fim_execucao:
                titulo = '[SUAP] Projeto de Extensão: Proximidade da data final de execução'
                texto = (
                    '<h1>Projeto de Extensão</h1>'
                    '<h2>Projeto: "{}"</h2>'
                    '<p>Olá, {}. A finalização do projeto {}, sob sua coordenação, está prevista para daqui 15 dias. Acesse o SUAP para mais detalhes.</p>'
                    ''.format(projeto.titulo, coordenador.pessoa.nome, projeto.titulo)
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [coordenador])
            if (projeto.inicio_execucao + relativedelta(years=2)) == (hoje.date()):

                titulo = '[SUAP] Projeto de Extensão: Projeto em execução há dois anos'
                texto = []
                texto.append('<h1>Projeto de Extensão</h1>')
                texto.append('<h2>Projeto: "{}"</h2>'.format(projeto.titulo))
                texto.append(
                    '<p>Olá, {1}. O projeto {0} se encontra em execução há mais de dois anos e poderá ser inativado pelo Coordenador de Extensão.'.format(
                        projeto.titulo, coordenador.pessoa.nome
                    )
                )
                texto.append('<p>--</p>')
                texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(projeto.get_visualizar_projeto_url()))
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [coordenador])
