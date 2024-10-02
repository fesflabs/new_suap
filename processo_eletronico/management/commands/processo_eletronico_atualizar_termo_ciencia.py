# -*- coding: utf-8 -*-
import datetime

from django.apps import apps
from django.db import transaction
from django.db.models import Q

from djtools.management.commands import BaseCommandPlus
from documento_eletronico.status import NivelAcesso


class Command(BaseCommandPlus):
    @transaction.atomic()
    def handle(self, *args, **options):
        ini = datetime.datetime.now()

        title = 'Processo Eletronico - Command que atualiza o nivel de acesso dos termos de ciencias publicos para restritos.'
        print('')
        print(('- ' * len(title)))
        print(('{}'.format(title)))
        print(('- ' * len(title)))

        DocumentoDigitalizadoProcesso = apps.get_model("processo_eletronico", "DocumentoDigitalizadoProcesso")

        docs_digitalizados = DocumentoDigitalizadoProcesso.objects.filter(
            Q(documento__nivel_acesso=NivelAcesso.NIVEL_ACESSO_PUBLICO) & Q(documento__assunto__icontains="Termo de Ciência: Conhecimento/Notifição")
        ).order_by('processo__numero_protocolo_fisico')
        qtd_docs_digitalizados = docs_digitalizados.count()

        title = 'Quantidade de Documentos'
        print('')
        print(('- ' * len(title)))
        print(('{}'.format(title)))
        print(('- ' * len(title)))
        print(("Termos de Ciencias a serem atualizados: {}".format(qtd_docs_digitalizados)))
        print(('- ' * len(title)))
        print('')

        if docs_digitalizados.exists():
            title = 'Lista de Documentos'
            print(('- ' * len(title)))
            print(('{}'.format(title)))
            print(('- ' * len(title)))
            for doc_digital in docs_digitalizados:
                print(("{} #{} - {}".format(doc_digital.documento, str(doc_digital.documento.id).ljust(5), doc_digital.processo)))
                doc_digital.documento.nivel_acesso = NivelAcesso.NIVEL_ACESSO_RESTRITO
                doc_digital.documento.save()
            print(('- ' * len(title)))

        fim = datetime.datetime.now()
        print('')
        print(('- ' * len(title)))
        print(('Início: {} - Final: {}'.format(ini, fim)))
        print(("Total de documentos atualizados para o nível de acesso restrito: {}.".format(qtd_docs_digitalizados)))
        print(('- ' * len(title)))
