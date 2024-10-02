# -*- coding: utf-8 -*-
from django.conf import settings

from djtools.utils import send_notification
from djtools.management.commands import BaseCommandPlus
from edu.models import ConfiguracaoCertificadoENEM


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        qs_configuracoes_certificaco_enem = ConfiguracaoCertificadoENEM.objects.all()

        for configuracao_certificado_enem in qs_configuracoes_certificaco_enem:
            qtd_solicitacoes_pendentes = configuracao_certificado_enem.solicitacaocertificadoenem_set.filter(data_avaliacao__isnull=True).count()
            responsaveis = configuracao_certificado_enem.responsaveis.all()

            if qtd_solicitacoes_pendentes > 0:
                titulo = '[SUAP] Notificação de Solicitações de Certificado ENEM não avaliadas'
                texto = (
                    '<h1>Ensino</h1>'
                    '<h2>Notificação de Solicitações de Certificado ENEM não avaliadas</h2>'
                    '<p>Atenção: existem {} {} de Certificado ENEM aguardando sua avaliação.</p>'.format(
                        qtd_solicitacoes_pendentes, 'Solicitações' if qtd_solicitacoes_pendentes > 1 else 'Solicitação'
                    )
                )
                vinculos = []
                for r in responsaveis:
                    vinculos.append(r.get_vinculo())

                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, vinculos)
