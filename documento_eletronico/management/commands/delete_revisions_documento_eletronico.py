# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from reversion.models import Version

from djtools.management.commands import BaseCommandPlus
from documento_eletronico.models import DocumentoTexto, DocumentoStatus


class Command(BaseCommandPlus):
    """
    Command para deletar as revisões do documento texto quando: Finalizados e Cancelados; e
    Para deixar apenas 3 revisões dos documentos não finalizados e não cancelados

    """

    def handle(self, *args, **options):
        verbosity = int(options['verbosity'])
        # Apagar Revisões de documentos Finalizados
        Version.objects.using(None).get_for_model(DocumentoTexto).filter(
            content_type=ContentType.objects.get_for_model(DocumentoTexto),
            object_id__in=list(DocumentoTexto.objects.filter(status__in=[DocumentoStatus.STATUS_FINALIZADO, DocumentoStatus.STATUS_CANCELADO]).values_list('pk', flat=True)),
        ).delete()

        # KEEP 3 Revisions
        call_command('deleterevisions', keep=3, verbosity=verbosity)
