import datetime

from djtools.management.commands import BaseCommandPlus
from pesquisa.models import AvaliadorIndicado


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        for avaliador in AvaliadorIndicado.objects.filter(prazo_para_aceite__isnull=False, rejeitado=False):
            if (not avaliador.aceito_em and datetime.datetime.now() > avaliador.prazo_para_aceite and not avaliador.ja_avaliou()) or (avaliador.aceito_em and datetime.datetime.now() > avaliador.prazo_para_avaliacao and not avaliador.ja_avaliou()):
                avaliador.rejeitado = True
                avaliador.rejeitado_em = datetime.datetime.now()
                avaliador.rejeitado_automaticamente = True
                avaliador.save()
