from django.conf import settings
from hashlib import sha1
from random import choice


def generate_safe_pk(self):
    def wrapped(self):
        while 1:
            skey = getattr(settings, 'SECRET_KEY', 'asidasdas3sfvsanfja242aako;dfhdasd&asdasi&du7')
            pk = sha1('{}{}'.format(skey, ''.join([choice('0123456789') for i in range(11)])).encode()).hexdigest()

            try:
                self.__class__.objects.get(pk=pk)
            except Exception:
                return pk

    return wrapped
