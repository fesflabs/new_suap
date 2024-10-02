# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from edu.diploma_digital.rap import AssinadorDigital
from edu.models import AssinaturaDigital


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        a = AssinaturaDigital.objects.filter(registro_emissao_diploma__aluno__matriz__isnull=False).last()
        print(a.registro_emissao_diploma.aluno)
        assinador_digital = AssinadorDigital()
        # assinador_digital.enviar_documentacao_academica(a, apenas_validacao=True)
        # assinador_digital.enviar_dados_diploma(a, apenas_validacao=True)
        assinador_digital.enviar_representacao_diploma(a, apenas_validacao=True)
