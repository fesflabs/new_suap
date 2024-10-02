from djtools.management.commands import BaseCommandPlus
from comum.models import User


class Command(BaseCommandPlus):

    help = 'Impede que usuários autentiquem com django.contrib.auth.backends.ModelBackend, ' 'deixando a senha como um hash inatingível: "!".'

    def handle(self, *args, **options):
        User.objects.update(password='!', skip_history=True)
        print(self.style.SQL_COLTYPE('%d password hashes changed to "!"' % User.objects.count()))
