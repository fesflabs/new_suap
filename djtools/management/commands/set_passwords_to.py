# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from comum.models import User
from django.contrib.auth.hashers import get_hasher, make_password


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        parser.add_argument('raw_password', nargs='+', type=str)

    def handle(self, *args, **options):
        hasher = get_hasher()
        raw_password = options['raw_password'][0]
        password = make_password(raw_password, '', hasher)
        result = self.style.SQL_COLTYPE('%d passwords changed to "%s"' % (User.objects.update(password=password), raw_password))
        print(result)
        try:
            text_file = open("deploy/random_password.txt", "w")
            text_file.write(str(raw_password))
            text_file.close()
        except Exception:
            print("Can't save the output on filesystem.")
