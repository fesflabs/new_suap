from djtools.management.commands import BaseCommandPlus
from django.core.management.base import CommandError
from comum.models import User
from uuid import getnode as get_mac
from django.contrib.auth.hashers import get_hasher, make_password
import socket


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        teresina_mac = 345052484161
        forbidden_hostname = ['teresina']
        #
        current_mac = get_mac()
        current_hostname = socket.gethostname()
        if current_hostname in forbidden_hostname or current_mac == teresina_mac:
            raise CommandError('Esta operação não é permitida na máquina atual.')
        else:
            updates = 0
            hasher = get_hasher()
            password = make_password('123', '', hasher)
            updates = User.objects.update(password=password, skip_history=True)
            print(self.style.SQL_COLTYPE('%d passwords changed to "123"' % updates))
            self.stdout.write('Successfully %d passwords changed to 123"' % updates)
