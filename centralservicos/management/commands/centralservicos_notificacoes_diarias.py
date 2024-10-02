# -*- coding: utf-8 -*-

from datetime import datetime

from centralservicos.models import Chamado, StatusChamado
from centralservicos.utils import Notificar
from comum.models import User
from djtools.db import models
from djtools.management.commands import BaseCommandPlus

"""
python manage.py centralservicos_notificacoes_diarias
"""


class Command(BaseCommandPlus):
    def chamados_resolvidos(self):
        """
        Notificar o interessado que existe(m) chamado(s) resolvido(s)
        que deve(m) ser fechado(s)
        """
        chamados = list()
        interessado = None
        for chamado in Chamado.objects.filter(status=StatusChamado.get_status_resolvido()).order_by('interessado'):
            """ Se houver interessado e ele for diferente do interessado atual, envia o email """
            if interessado and chamado.interessado != interessado:
                Notificar.chamados_resolvidos(interessado, chamados)
                chamados = list()

            interessado = chamado.interessado
            chamados.append(chamado)

    def notificar_chamados_com_sla_estourado(self):
        """
            Notificar atendente e responsavel pelo atendimento
            que chamados estão com SLA estourados
        """
        import time

        qs = Chamado.get_chamados_com_sla_estourado().filter(notificacao_enviada=False)
        count = 0
        for chamado in qs:
            if count == 15:
                count = 0
                time.sleep(3)
            count += 1
            Notificar.responsavel_equipe_atendimento_sobre_sla_estourado(chamado)
            if chamado.get_atendimento_atribuicao_atual().atribuido_para and chamado.get_atendimento_atribuicao_atual().atribuido_para.email:
                Notificar.atendente_sobre_sla_estourado(chamado)
        qs.update(notificacao_enviada=True)

    def fechar_chamados_automaticamente(self):
        """
           Comando responsável por fechar automaticamente os chamados que estão com status "Resolvido"
           a mais de 90 dias.
        """
        agora = datetime.today()
        for chamado in Chamado.objects.filter(status=StatusChamado.get_status_resolvido()):
            tempo = agora - chamado.get_ultimo_historico_status().data_hora
            if tempo.days >= 90:
                atendente = chamado.get_atendente_do_chamado()
                chamado.fechar_chamado(usuario=atendente, fechado_automaticamente=True, observacao='Chamado fechado automaticamente pelo sistema.')

    def remover_atendentes_inativos(self):
        """ Remover o vinculo de atendente ou responsavel de
            todos os usuários INATIVOS vinculados ao GrupoAtendimento """
        usuarios_atendentes = User.objects.filter(is_active=False).filter(models.Q(atendentes_set__isnull=False) | models.Q(responsaveis_set__isnull=False)).distinct()
        for user in usuarios_atendentes:
            user.atendentes_set.clear()
            user.responsaveis_set.clear()

    def handle(self, *args, **options):
        self.notificar_chamados_com_sla_estourado()
        self.fechar_chamados_automaticamente()
        self.remover_atendentes_inativos()
        self.chamados_resolvidos()
