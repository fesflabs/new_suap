from datetime import datetime, timedelta

from demandas.models import AmbienteHomologacao
from demandas.utils import Notificar
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):

    def handle(self, *args, **options):
        '''
        Notifica os desenvolvedores de ambiente que com data de expiração para próximo dia
        Remove os ambientes de homologação com data de expiração inferior a data atual
        '''
        # Envia notificações para ambiente que irão expirar em 2 dias
        ambientes_homologacao_a_expirar_em_2_dias = AmbienteHomologacao.objects.filter(ativo=True, data_expiracao=(datetime.now() + timedelta(days=1)).date())
        print(f"{ambientes_homologacao_a_expirar_em_2_dias.count()} a expirar em dois dias!")
        for ambiente in ambientes_homologacao_a_expirar_em_2_dias:
            try:
                Notificar.ambiente_homologacao_expira_em_1_dia(ambiente)
            except Exception:
                continue

        # Exclui ambientes expirados
        ambientes_homologacao_expirados = AmbienteHomologacao.objects.filter(data_expiracao__lt=datetime.now())
        print(f"{ambientes_homologacao_expirados.count()} serão excluídos!")
        for ambiente in ambientes_homologacao_expirados:
            try:
                ambiente.destruir()
            except Exception:
                continue
