# -*- coding: utf-8 -*-
# pylint: skip-file
import base64

from Crypto.Cipher import AES
from django.conf import settings
from django.db.models.manager import Manager  # NOQA

__all__ = ['EncryptedPKModelManager', 'decrypt_val']


class EncryptedPKModelManager(Manager):
    """This manager allows models to be identified based on their encrypted_pk value."""

    def get(self, *args, **kwargs):
        encrypted_pk = kwargs.pop('encrypted_pk', None)
        if encrypted_pk:
            kwargs['pk'] = decrypt_val(encrypted_pk)
        return super(EncryptedPKModelManager, self).get(*args, **kwargs)


def decrypt_val(cipher_text):
    dec_secret = AES.new(settings.SECRET_KEY[:32].encode(), mode=AES.MODE_ECB)
    unhex = bytearray.fromhex(cipher_text).decode()
    raw_decrypted = dec_secret.decrypt(base64.b64decode(unhex))
    clear_val = raw_decrypted.decode().rstrip("\0")
    return clear_val
