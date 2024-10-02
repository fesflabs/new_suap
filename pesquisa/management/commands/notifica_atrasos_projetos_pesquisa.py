# -*- coding: utf-8 -*-

import datetime
from djtools.management.commands import BaseCommandPlus
from pesquisa.models import Projeto
from django.conf import settings
from djtools.utils import send_notification


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        hoje = datetime.datetime.now().date()
        projetos_em_execucao = Projeto.objects.filter(
            pre_aprovado=True, projetocancelado__isnull=True, aprovado=True, registroconclusaoprojeto__dt_avaliacao__isnull=True, edital__divulgacao_selecao__lt=hoje
        )

        for projeto in projetos_em_execucao:
            if projeto.vinculo_coordenador:
                coordenador = projeto.vinculo_coordenador
            else:
                coordenador = projeto.get_responsavel().vinculo_pessoa

            if projeto.tem_metas_vencendo_em(dias=7, envia_email=True):
                titulo = '[SUAP] Projeto de Pesquisa: Meta expirando nos próximos sete dias'
                texto = []
                texto.append('<h1>Projeto de Pesquisa</h1>')
                texto.append('<h2>Projeto: "{}"</h2>'.format(projeto.titulo))
                texto.append('<p>Olá, {1}. O projeto {0} possui meta com prazo de expiração nos próximos sete dias.'.format(projeto.titulo, coordenador.pessoa.nome))
                texto.append('<p>--</p>')
                texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(projeto.get_visualizar_projeto_url()))
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [coordenador])

            if projeto.tem_metas_vencendo_em(envia_email=True):
                titulo = '[SUAP] Projeto de Pesquisa: Projeto com meta expirando hoje'
                texto = []
                texto.append('<h1>Projeto de Pesquisa</h1>')
                texto.append('<h2>Projeto: "{}"</h2>'.format(projeto.titulo))
                texto.append('<p>Olá, {1}. O projeto {0} possui meta com prazo de expiração previsto para hoje.'.format(projeto.titulo, coordenador.pessoa.nome))
                texto.append('<p>--</p>')
                texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(projeto.get_visualizar_projeto_url()))
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [coordenador])

            if projeto.tem_data_fim_execucao_em(dias=15, envia_email=True):
                titulo = '[SUAP] Projeto de Pesquisa: Proximidade da data final de execução'
                texto = []
                texto.append('<h1>Projeto de Pesquisa</h1>')
                texto.append('<h2>Projeto: "{}"</h2>'.format(projeto.titulo))
                texto.append('<p>A finalização do projeto {0}, sob sua coordenação, está prevista para os próximos 15 dias.'.format(projeto.titulo))
                texto.append('<p>--</p>')
                texto.append('<p>Para mais informações, acesse: <a href="{0}?tab=pendencias">{0}?tab=pendencias</a></p>'.format(projeto.get_visualizar_projeto_url()))
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [coordenador])

            if projeto.tem_data_fim_execucao_em(envia_email=True):
                titulo = '[SUAP] Projeto de Pesquisa: Data limite da execução'
                texto = []
                texto.append('<h1>Projeto de Pesquisa</h1>')
                texto.append('<h2>Projeto: "{}"</h2>'.format(projeto.titulo))
                texto.append('<p>A finalização do projeto {0}, sob sua coordenação, está prevista para hoje.'.format(projeto.titulo))
                texto.append('<p>--</p>')
                texto.append('<p>Para mais informações, acesse: <a href="{0}?tab=pendencias">{0}?tab=pendencias</a></p>'.format(projeto.get_visualizar_projeto_url()))
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [coordenador])
