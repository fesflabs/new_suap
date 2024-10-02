import logging
from datetime import datetime
import os

import sys
from django.conf import settings
import ldap
from django.apps import apps
from django.db.models import Q

from comum.models import Log, EmailBlockList
from djtools.management.commands import BaseCommandPlus
from edu.models.cadastros_gerais import SituacaoMatricula


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*', type=str)
        parser.add_argument(
            '--qtd', action='store', dest='qtd', default=0, type=int, help='Informe a quantidade de registros que você que inativar no AD.'
        )

    def handle(self, *args, **options):
        Aluno = apps.get_model('edu', 'Aluno')
        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        conf = LdapConf.get_active()
        ano_atual = datetime.today().year
        qtd = 500
        if int(options['qtd']):
            qtd = options['qtd']

        situacoes = [
            SituacaoMatricula.CANCELADO, SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
            SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO, SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatricula.CONCLUIDO, SituacaoMatricula.EVASAO, SituacaoMatricula.FORMADO,
            SituacaoMatricula.JUBILADO, SituacaoMatricula.NAO_CONCLUIDO, SituacaoMatricula.TRANSFERIDO_EXTERNO,
            SituacaoMatricula.TRANSFERIDO_INTERNO
        ]

        # Exclui situações ativas e também o aluno trancado
        alunos = Aluno.objects.filter(situacao_id__in=situacoes).exclude(Q(email_academico='') & Q(email_google_classroom='')).exclude(ano_let_prev_conclusao=ano_atual).order_by('ano_let_prev_conclusao')[:qtd]
        arquivo = os.path.join(settings.BASE_DIR, 'deploy/logs/alunos_limpar_emails.txt')
        txt_file = open(arquivo, 'w')
        [txt_file.write(str(aluno) + ', ' + aluno.email_academico + ', ' + aluno.email_google_classroom + '\n') for aluno in alunos]
        txt_file.close()
        valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
        opcao = ''
        while True:
            sys.stdout.write('Deseja apagar os emails dos alunos e inativa-los no AD? [y/n]')
            choice = input().lower()
            if choice == "":
                opcao = valid['no']
                break
            elif choice in valid:
                opcao = valid[choice]
                break
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")
        if opcao:
            msg = []
            for aluno in alunos:
                email_academico = aluno.email_academico
                email_google_classroom = aluno.email_google_classroom
                aluno.email_academico = ''
                aluno.email_google_classroom = ''
                aluno.save()
                try:
                    # Vai retirar do usuário do google classroom e do academico
                    conf.limpar_emails_academico_e_google(aluno)
                    if email_academico:
                        EmailBlockList.objects.get_or_create(email=email_academico)
                    if email_google_classroom:
                        EmailBlockList.objects.get_or_create(email=email_google_classroom)
                    msg.append(f'{aluno} - Success')
                except ldap.LDAPError:
                    logging.error('LDAPError ao sincronizar aluno {}'.format(aluno))
                    msg.append(f'{aluno} - LDAPError')
                except Exception:
                    logging.error('Erro ao sincronizar aluno {}'.format(aluno))
                    msg.append(f'{aluno} - Error')

            Log.objects.create(titulo='Command Ldap Limpar emails academico e google Alunos Inativos',
                               texto=f'{", ".join(msg)}',
                               app='edu')
        else:
            print('Operação cancelada')
