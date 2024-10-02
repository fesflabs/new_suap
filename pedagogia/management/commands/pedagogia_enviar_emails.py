# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from pedagogia.models import QuestionarioMatriz
from django.utils import termcolors


class Command(BaseCommand):
    def handle(self, *args, **options):
        verbose = options.get('verbosity', '0') != '0'
        for questionario in QuestionarioMatriz.objects.all():
            emails_enviados = questionario.enviar_email()
            if verbose:
                print((termcolors.make_style(fg='blue', opts=('bold',))('Questionário %s enviou %d emails' % (questionario.descricao, emails_enviados))))
