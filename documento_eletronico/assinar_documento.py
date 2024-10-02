# -*- coding: utf-8 -*-
import re
import string
from binascii import hexlify, unhexlify
from datetime import datetime as dt
from datetime import tzinfo, timedelta

from OpenSSL import crypto
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtensionOID
from django.conf import settings

from djtools.security.signature import create_signature


def get_chave_secreta():
    return settings.DOC_SECRET_KEY


def get_chave(pessoa_fisica):
    return '{}:{}'.format(get_chave_secreta(), pessoa_fisica.id)


def gerar_assinatura_documento_senha(documento, pessoa_fisica):
    chave = get_chave(pessoa_fisica)
    # print (u'>>> ')
    # print (u'>>> ASSINATURA DO DOCUMENTO: {} ||| por {}'.format(documento, pessoa_fisica))
    # print (u'>>> >>> {}'.format(chave))
    # print (u'>>> >>> {}'.format(documento.hash_conteudo))
    # print (u'>>> ')

    return create_signature(chave, documento.hash_conteudo).decode('utf-8')


def verificar_assinatura_senha(documento, pessoa_fisica, assinatura_hmac):
    return gerar_assinatura_documento_senha(documento, pessoa_fisica) == assinatura_hmac


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


def verfica_assinatura_token(cert, assinatura, hash):
    st_cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
    signature_algorithm = st_cert.get_signature_algorithm()
    crypto.verify(st_cert, unhexlify(assinatura), hash, signature_algorithm)


class DateRange:
    def __init__(self, begin_date, end_date):
        self._begin = DateRange.convert_to_utc(begin_date)
        self._end = DateRange.convert_to_utc(end_date)

    @staticmethod
    def convert_to_utc(timestamp):
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=GMT())
        else:
            return timestamp.astimezone(GMT())

    def begin(self):
        return self._begin

    def end(self):
        return self._end

    @property
    def has_now(self):
        gmt = dt.utcnow()
        gmt = gmt.replace(tzinfo=GMT())
        return self.begin() <= gmt <= self.end()

    def has_data(self, date):
        return self.begin() <= date <= self.end()

    def __str__(self):
        return '\n\t{}\n\t{}'.format(self._begin, self._end)


class GMT(tzinfo):
    """GMT"""

    def utcoffset(self, date_time):
        return timedelta(seconds=0)

    def tzname(self, date_time):
        return 'GMT'

    def dst(self, date_time):
        return timedelta(seconds=0)


def get_attributes_for_oid(obj, oid):
    res = []
    for attr in obj.get_attributes_for_oid(oid):
        res.append(attr.value)
    return res and ",".join(res)


class SignerException(Exception):
    pass


class CertificadoICPBrasil(object):
    # list of OID http://baxincc.cc/questions/954199/table-of-oids-for-certificates-subject

    @staticmethod
    def unicode_to_string(raw_cert):
        import unicodedata

        return unicodedata.normalize('NFKD', raw_cert).encode('ascii', 'ignore')

    def __init__(self, cert):
        self.raw_cert = cert
        self.cert = CertificadoICPBrasil.unicode_to_string(cert)
        self.openssl_cert = x509.load_pem_x509_certificate(self.cert, default_backend())
        self.validate()
        # O certificado é valido, logo vamos preencher os dados especificos do A3
        self.pki_brazil = dict()
        self.process_pki_brazil()
        self.data_range = DateRange(self.openssl_cert.not_valid_before, self.openssl_cert.not_valid_after)
        self.fingerprint = hexlify(self.openssl_cert.fingerprint(hashes.SHA256())).decode()

    # Assinaturas digitais geradas segundo esta Política de Assinatura
    # deverão ser criadas com chave privada associada ao certificado
    # ICP-Brasil * tipo A1 (do OID 2.16.76.1.2.1.1 ao OID
    # 2.16.76.1.2.1.100), tipo A2 (do OID 2.16.76.1.2.2.1 ao OID
    # 2.16.76.1.2.2.100), do tipo A3 (do OID 2.16.76.1.2.3.1 ao OID
    # 2.16.76.1.2.3.100) e do tipo A4 (do OID 2.16.76.1.2.4.1 ao OID
    # 2.16.76.1.2.4.100), conforme definido em DOC-ICP-04.
    # 2.16.76.1.3 -     Identificação de atributos de certificados (uso obrigatório)
    # 2.16.76.1.3.1 -   campo otherName em certificado de pessoa física, contento os dados
    #                   do titular (data de nascimento, CPF, PIS/PASEP/CI, RG);
    def validate(self):
        policies = self.openssl_cert.extensions.get_extension_for_oid(ExtensionOID.CERTIFICATE_POLICIES)
        policy = policies.value[0]
        identificador = policy.policy_identifier.dotted_string
        #
        eh_uma_politica_cert = (
            identificador.startswith("2.16.76.1.2.1.")
            or identificador.startswith("2.16.76.1.2.2.")
            or identificador.startswith("2.16.76.1.2.3.")
            or identificador.startswith("2.16.76.1.2.4.")
        )
        #
        if not eh_uma_politica_cert:
            raise SignerException("O OID não corresponde a uma Política de Certificado: {}.".format(identificador))
        #
        sufixo = int(identificador.split('.')[-1])
        if sufixo < 1 or sufixo > 100:
            raise SignerException("O certificado deve ser do tipo A1, A2, A3 ou A4.")
        #
        # Certificado ICP-Brasil
        return True

    def get_subject(self,):
        return get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.COMMON_NAME)

    def process_pki_brazil(self):
        escape = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]')
        for oid in self.openssl_cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME).value:
            printable = set(string.printable)
            value = re.sub(escape, "", [x for x in oid.value if x in printable])
            # Os campos do tipo RFC822 possuem um email.
            if isinstance(oid, x509.general_name.RFC822Name):
                self.rfc822Name([x for x in oid.value if x in printable])
            # Os demais possuem informações diversas de acordo com o tipo
            if isinstance(oid, x509.general_name.OtherName):
                try:
                    method_name = "OID_" + oid.type_id.dotted_string.replace(".", "_")
                    method = getattr(self, method_name)
                    # Invoca o metodo de tratamento adequado.
                    method(value)
                except Exception as e:
                    print(e)

    # OID = 2.16.76.1.3.1 Has some "ICP-BRASIL Pessoa Fisica" attributes<br>
    #   1 - nas primeiras 8 (oito) posições, a data de nascimento do titular, no formato ddmmaaaa;
    #   2 - nas 11 posições subseqüentes, o Cadastro de Pessoa Física (CPF) do titular;
    #   3 - nas 11 posições subseqüentes, o número de Identificação Social - NIS (PIS, PASEP ou CI);
    #   4 - nas 15 posições subseqüentes, o número do Registro Geral - RG do titular;
    #   5 - nas 6 posições subseqüentes, as siglas do órgão expedidor do RG e respectiva UF.
    def OID_2_16_76_1_3_1(self, extension):
        self.pki_brazil.update(
            {
                'tipo': extension[0],
                'data_nascimento': extension[1:9],
                'CPF': extension[9:20],
                'NIS': extension[20:31],
                'rg_numero': extension[31:46],
                'rg_emissor': extension[46:51],
                'rg_emissor_uf': extension[50:52],
            }
        )

    #
    # OID = 2.16.76.1.3.3 e conteúdo = nas 14 (quatorze) posições o número do
    # Cadastro Nacional de Pessoa Jurídica (CNPJ) da pessoa jurídica titular do
    # certificado
    def OID_2_16_76_1_3_3(self, extension):
        self.pki_brazil.update({'CNPJ': extension})

    # OID = 2.16.76.1.3.5 e conteúdo =
    #   1 - nas primeiras 12(doze) posições, o número de inscrição do Título de Eleitor
    #   2 - nas 3(três) posições subsequentes, a Zona Eleitoral;
    #   3 - nas 4(quatro) posições seguintes a Seção;
    #   4 - nas 22(vinte e duas) posições subsequentes, o município e a UF do Título de Eleitor.

    def OID_2_16_76_1_3_5(self, extension):
        self.pki_brazil.update({'titulo_eleitor': extension[0:12], 'zona_eleitoral': extension[12:15], 'secao': extension[15:19], 'municipio_uf': extension[19:]})

    # OID = 2.16.76.1.3.6 e conteúdo = nas 12(doze) posições o número
    # do Cadastro Especifico do INSS(CEI) da pessoa física titular do
    # certificado
    def OID_2_16_76_1_3_6(self, extension):
        self.pki_brazil.update({'CEI': extension})

    # OID = 1.3.6.1.4.1.311.20.2.3 e conteúdo = Nome Principal que contém o domínio de login em estações de trabalho
    def OID_1_3_6_1_4_1_311_20_2_3(self, extension):
        self.pki_brazil.update({'UPN': extension})

    def get_formated_cpf(self,):
        cpf = self.pki_brazil.get('CPF', None)
        if cpf:
            return "{}.{}.{}-{}".format(cpf[0:3], cpf[3:6], cpf[6:9], cpf[9:11])
        return None

    @property
    def email(self,):
        return self.pki_brazil.get('email', None)

    def rfc822Name(self, extension):
        self.pki_brazil.update({'email': extension})

    def get_extensions(self,):
        for _ in self.openssl_cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME):
            pass

    def get_public_key(self,):
        from cryptography.hazmat.primitives import serialization

        key = self.openssl_cert.public_key()
        return key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.PKCS1)

    @property
    def serial_number(self,):
        return '{0:x}'.format(int(self.openssl_cert.serial))

    def serial_from_int(self):
        i = int(self.openssl_cert.serial)
        s = hex(i)[2:].upper()
        return ':'.join(a + b for a, b in zip(s[::2], s[1::2]))

    def dump(self):
        print(("Versão:\t{}".format(self.openssl_cert.version)))
        print(("Número de Serie:\t{}".format(self.openssl_cert.serial)))
        print(("SHA256 Fingerprint:\t{}".format(hexlify(self.openssl_cert.fingerprint(hashes.SHA256())).decode())))
        print(("Data de inicio da validade:\t{}".format(self.openssl_cert.not_valid_before)))
        print(("Data de fim da validade:\t{}".format(self.openssl_cert.not_valid_after)))
        print("Dados do emisor:")
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.issuer, x509.NameOID.ORGANIZATION_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.issuer, x509.NameOID.ORGANIZATIONAL_UNIT_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.issuer, x509.NameOID.COUNTRY_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.issuer, x509.NameOID.STATE_OR_PROVINCE_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.issuer, x509.NameOID.LOCALITY_NAME))))

        print("Dados da entidade vínculada:")
        print(("Nome:\t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.COMMON_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.ORGANIZATION_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.ORGANIZATIONAL_UNIT_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.COUNTRY_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.STATE_OR_PROVINCE_NAME))))
        print(("\t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.LOCALITY_NAME))))

        print(("Email: \t{}".format(get_attributes_for_oid(self.openssl_cert.subject, x509.NameOID.EMAIL_ADDRESS))))


def hash_bytestr_iter(bytesiter, hasher, ashexstr=True):
    for block in bytesiter:
        hasher.update(block)
    return hasher.hexdigest() if ashexstr else hasher.digest()


def assinar_documento_com_token(documento, cert, icpbrasil, sig, pessoa_fisica, papel):
    verfica_assinatura_token(cert, sig, documento.hash_conteudo)
    documento.assinar_via_token(icpbrasil, sig, pessoa_fisica, papel)
