# coding: utf-8
from django.apps import apps
from django.db import transaction

from comum.models import Configuracao
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    @transaction.atomic
    def handle(self, *args, **options):

        User = apps.get_model('comum', 'User')
        PessoaFisica = apps.get_model('rh', 'PessoaFisica')
        Servidor = apps.get_model('rh', 'Servidor')
        Aluno = apps.get_model('edu', 'Aluno')
        Pessoa = apps.get_model('rh', 'Pessoa')

        #       Zerando todos os emails secundarios que forem institucionais
        dominios_institucionais = Configuracao.get_valor_por_chave("comum", "dominios_institucionais")
        if dominios_institucionais:
            for dominio in dominios_institucionais.split(";"):
                Pessoa.objects.filter(email_secundario__icontains=dominio).update(email_secundario='')

        # Atualizando emails do Servidor Caso não seja email institucional
        for pf_id, matricula, email_institucional, email_siape in Servidor.objects.values_list('pk', 'matricula', 'email_institucional', 'email_siape'):
            if email_siape and not Configuracao.eh_email_institucional(email_siape):
                Servidor.objects.filter(id=pf_id, email_secundario='').update(email_secundario=email_siape)
            Servidor.objects.filter(id=pf_id).update(email=email_institucional)
            User.objects.filter(username=matricula).update(email=email_institucional)

        # Atualizando emails do Aluno
        for pf_id, matricula, email_academico, email_qacademico in Aluno.objects.filter(situacao__ativo=True).values_list(
            'pessoa_fisica', 'matricula', 'email_academico', 'email_qacademico'
        ):
            if not Configuracao.eh_email_institucional(email_qacademico):
                PessoaFisica.objects.filter(id=pf_id, email_secundario='').update(email_secundario=email_qacademico)
            if email_academico:
                PessoaFisica.objects.filter(id=pf_id).update(email=email_academico)
                User.objects.filter(username=matricula).update(email=email_academico)
