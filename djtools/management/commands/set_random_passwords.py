# -*- coding: utf-8 -*-
from comum.models import User
from djtools.management.commands import BaseCommandPlus
from djtools.utils import randomic
from django.contrib.auth.hashers import get_hasher, make_password


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        hasher = get_hasher()
        raw_password = randomic(10)
        password = make_password(raw_password, '', hasher)
        result = self.style.SQL_COLTYPE('%d passwords changed to "%s"' % (User.objects.update(password=password), raw_password))
        print(result)
        try:
            text_file = open("deploy/random_password.txt", "w")
            text_file.write(str(raw_password))
            text_file.close()
        except Exception:
            print("Can't save the output on filesystem.")
