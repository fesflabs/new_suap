# -*- coding: utf-8 -*-

from datetime import datetime

from django.apps import apps
from django.conf import settings

from comum.models import Configuracao
from djtools.management.commands import BaseCommandPlus
from rh.importador_ws import ImportadorWs
from rh.models import Servidor

Log = apps.get_model('comum', 'log')


def atualizar_servidor(importador, servidor):
    erro_importacao = False
    erro_atualizacao_afastamento = False
    if settings.DEBUG:
        print(('Servidor {}'.format(servidor)))
    try:
        # serv, criado = importador.importacao_servidor(servidor.cpf, False)
        serv, criado = importador.importacao_servidor(servidor.cpf, False, False)[0]
        importador.atualizar_ferias_afastamentos(servidor.cpf, ano_inicio=1990)
    except Exception as ex:
        if settings.DEBUG:
            print('Erro Importar Servidor {}: {}'.format(servidor, ex))
        erro_importacao = True
    try:
        importador.atualizar_ferias_afastamentos(servidor.cpf, ano_inicio=1990)
    except Exception:
        if settings.DEBUG:
            print('Erro Atualizar Afastamento Férias Servidor {}'.format(servidor))
        erro_atualizacao_afastamento = True

    Servidor.objects.filter(id=servidor.id).update(
        data_posse_na_instituicao=servidor.calcula_posse_na_instituicao,
        data_posse_no_cargo=servidor.calcula_posse_no_cargo,
        data_fim_servico_na_instituicao=servidor.calcula_fim_servico_na_instituicao,
    )
    return erro_importacao, erro_atualizacao_afastamento


class Command(BaseCommandPlus):
    help = 'Atualização Servidor'

    def add_arguments(self, parser):
        parser.add_argument('--completo', action='store_true', help='Roda importação/atualizacao completa do servidor levando como consideração data de inicio de exercício.')

    def handle(self, *args, **options):

        tem_ws_configuracao = Configuracao.get_valor_por_chave('rh', 'urlProducaoWS')
        if settings.DEBUG:
            print('Iniciando importação WEBSERVICE {}'.format(datetime.now().strftime('%d/%m/%Y %H:%m:%S')))
        if tem_ws_configuracao:
            importador = ImportadorWs()
            erros_importacao = []
            erros_atualizacao_afastamento = []
            for servidor in Servidor.objects.ativos().order_by('data_ultima_atualizacao_webservice'):
                try:
                    serv, criado = importador.importacao_servidor(servidor.cpf, False, False)[0]
                except Exception:
                    serv = None
                    erros_importacao.append(str(servidor))
                try:
                    importador.atualizar_ferias_afastamentos(servidor.cpf, ano_inicio=1990)
                except Exception:
                    erros_atualizacao_afastamento.append(str(servidor))
                if serv:
                    Servidor.objects.filter(id=serv.id).update(
                        data_posse_na_instituicao=serv.calcula_posse_na_instituicao,
                        data_posse_no_cargo=serv.calcula_posse_no_cargo,
                        data_fim_servico_na_instituicao=serv.calcula_fim_servico_na_instituicao,
                    )
            if erros_importacao:
                Log.objects.create(app='rh', titulo='Webservice Erro', texto='Erro ao importar servidores: {}'.format(','.join(erros_importacao)))
            if erros_atualizacao_afastamento:
                Log.objects.create(
                    app='rh', titulo='Webservice Erro - Afastamento/Férias', texto='Erro ao Afastamentos/Férias dos servidores: {}'.format(','.join(erros_atualizacao_afastamento))
                )

        else:
            for servidor in Servidor.objects.all():
                if settings.DEBUG:
                    print(('Servidor {}'.format(servidor)))

                Servidor.objects.filter(id=servidor.id).update(
                    data_inicio_servico_publico=servidor.calcula_inicio_no_servico_publico,
                    data_inicio_exercicio_na_instituicao=servidor.calcula_inicio_exercicio_na_instituicao,
                    data_posse_na_instituicao=servidor.calcula_posse_na_instituicao,
                    data_posse_no_cargo=servidor.calcula_posse_no_cargo,
                    data_inicio_exercicio_no_cargo=servidor.calcula_inicio_exercicio_no_cargo,
                    data_fim_servico_na_instituicao=servidor.calcula_fim_servico_na_instituicao,
                )

        if settings.DEBUG:
            print(('Finalizada importação WEBSERVICE {}'.format(datetime.now().strftime('%d/%m/%Y %H:%m:%S'))))
