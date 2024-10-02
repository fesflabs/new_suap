# -*- coding: utf-8 -*-
import hashlib
import hmac
import base64
from binascii import unhexlify
from OpenSSL import crypto


def to_string_bytes(value) -> bytes:
    if isinstance(value, str):
        return value.encode('utf-8')

    if isinstance(value, bytes):
        return value
    #
    raise Exception('Data type not supported (Text only).')


def hash_bytestr_iter(bytesiter, hasher, ashexstr=True):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest() if ashexstr else hasher.digest()


def verify_chain_of_trust(cert_pem, trusted_cert_pems):
    # http://www.iti.gov.br/noticias/188-atualizacao/4530-ac-raiz

    certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cert_pem)

    # Create and fill a X509Sore with trusted certs
    store = crypto.X509Store()
    for trusted_cert_pem in trusted_cert_pems:
        trusted_cert = crypto.load_certificate(crypto.FILETYPE_PEM, trusted_cert_pem)
        store.add_cert(trusted_cert)

    # Create a X590StoreContext with the cert and trusted certs
    # and verify the the chain of trust
    store_ctx = crypto.X509StoreContext(store, certificate)
    # Returns None if certificate can be validated
    result = store_ctx.verify_certificate()

    if result is None:
        return True
    else:
        return False


def verify_signature_cert(cert, signature, hash):
    st_cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
    signature_algorithm = st_cert.get_signature_algorithm()
    crypto.verify(st_cert, unhexlify(signature), hash, signature_algorithm)


def create_signature(secret_key, message):
    message_to_sign = to_string_bytes(message)
    signature = hmac.new(to_string_bytes(secret_key), message_to_sign, hashlib.sha512)
    return base64.b64encode(signature.digest())


def verify_signature(secret_key, hmac, message):
    return create_signature(secret_key, message) == hmac
