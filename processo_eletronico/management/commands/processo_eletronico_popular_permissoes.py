# -*- coding: utf-8 -*-
from datetime import datetime

from django.apps import apps
from django.db import transaction
from django.db.models import Q

from comum.utils import get_todos_setores
from djtools.management.commands import BaseCommandPlus
from djtools.utils import imprimir_percentual
from rh.models import Setor


class Command(BaseCommandPlus):
    def get_setores_pe(self, user, setores_compartilhados=True):
        setores = get_todos_setores(user, setores_compartilhados=setores_compartilhados)
        if user.eh_servidor:
            servidor = user.get_relacionamento()
            setores_adicionais_ids = servidor.papeis_ativos.values_list('setor_suap', flat=True)
            setores_adicionais = Setor.objects.filter(id__in=setores_adicionais_ids)
            setores = setores | setores_adicionais
        return setores.distinct()

    @transaction.atomic()
    def handle(self, *args, **options):
        print('>>> Novas permissoes do processo eletronico')

        Servidor = apps.get_model("rh", "Servidor")
        Processo = apps.get_model("processo_eletronico", "Processo")

        CompartilhamentoProcessoEletronicoSetorPessoa = apps.get_model("processo_eletronico", "CompartilhamentoProcessoEletronicoSetorPessoa")
        CompartilhamentoProcessoEletronicoPoderDeChefe = apps.get_model("processo_eletronico", "CompartilhamentoProcessoEletronicoPoderDeChefe")
        CompartilhamentoProcessoEletronicoLog = apps.get_model("processo_eletronico", "CompartilhamentoProcessoEletronicoLog")
        CompartilhamentoProcessoEletronicoSetorSetor = apps.get_model("processo_eletronico", "CompartilhamentoProcessoEletronicoSetorSetor")

        CompartilhamentoProcessoEletronicoSetorPessoa.objects.all().delete()
        CompartilhamentoProcessoEletronicoPoderDeChefe.objects.all().delete()
        CompartilhamentoProcessoEletronicoLog.objects.all().delete()
        CompartilhamentoProcessoEletronicoSetorSetor.objects.all().delete()

        # Gera as permissoes iniciais dos usuarios para o novo padrao de permissoes do django
        # Gera a lista de setores que uma pessoa pode trabalhar nos processos eletronicos
        # Gera a lista de setores que um setor pode trabalhar nos processos eletronicos

        # >>> Processo.PERMISSAO_OPERAR_PROCESSO:
        # Equivalente ao grupo "Tramitador de Processos Eletrônicos" e "setores_compartilhados=True"
        #   permission "pode_tramitar_processos_eletronicos"
        # Equivalente a chamada get_todos_setores(self.request.user, setores_compartilhados=True)
        # Serah chamado pelo Tramite.get_todos_setores(user, deve_poder_criar_processo=False)

        # >>> Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO:
        # Equivalente ao grupo "Operador de Processo Eletrônico" e "setores_compartilhados=False"
        # Equivalente a chamada get_todos_setores(self.request.user, setores_compartilhados=False)
        # Serah chamado pelo Tramite.get_todos_setores(user, deve_poder_criar_processo=True)

        # ==============================================================================================================

        # --------------------------
        # PERMISSOES PARA SERVIDORES
        # --------------------------
        # - Lista os SERVIDORES nao excluidos ativos e que estejam no grupo "Tramitador de Processos Eletrônicos" ou
        #   "Operador de Processo Eletrônico"
        #   - Apenas eles podem receber permissoes de "Processo.PERMISSAO_OPERAR_PROCESSO" ou "Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO"

        servidores = Servidor.objects.ativos().filter(Q(user__groups__name='Tramitador de Processos Eletrônicos') | Q(user__groups__name='Operador de Processo Eletrônico'))

        for servidor in imprimir_percentual(servidores):

            # Lista de setores que o servidor podera operar processos
            setores_que_posso_operar = self.get_setores_pe(servidor.user, True)

            # Lista de setores que o servidor podera criar processos
            setores_que_posso_criar = self.get_setores_pe(servidor.user, False)

            # Recebem a permissao ***"Processo.PERMISSAO_OPERAR_PROCESSO"*** nos seguintes setores
            if (
                servidor.user.groups.filter(name='Tramitador de Processos Eletrônicos').exists()
                and not servidor.user.groups.filter(name='Operador de Processo Eletrônico').exists()
            ):

                for setor in setores_que_posso_operar.all():
                    c = CompartilhamentoProcessoEletronicoSetorPessoa()
                    c.setor_dono = setor
                    c.pessoa_permitida = servidor
                    c.nivel_permissao = Processo.PERMISSAO_OPERAR_PROCESSO
                    c.data_criacao = datetime.today()
                    c.usuario_criacao = None
                    c.save()

            # Recebem a permissao ***"Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO"*** nos seguintes setores
            if servidor.user.groups.filter(name='Chefe de Setor').exists() or servidor.user.groups.filter(name='Operador de Processo Eletrônico').exists():

                for setor in setores_que_posso_criar.all():
                    c = CompartilhamentoProcessoEletronicoSetorPessoa()
                    c.setor_dono = setor
                    c.pessoa_permitida = servidor
                    c.nivel_permissao = Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO
                    c.data_criacao = datetime.today()
                    c.usuario_criacao = None
                    c.save()

        print('FIM')
