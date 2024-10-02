# -*- coding: utf-8 -*-
# Adaptado de https://github.com/openstack/magnum

from comum.tests import SuapTestCase

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509 as c_x509
from cryptography.x509.oid import NameOID
import six

# ./manage.py test comum.tests.X509TestCase.test_generate_client_revoked_certificate --keepdb --verbosity=2
# ./manage.py test comum.tests.X509TestCase --keepdb --verbosity=2
from comum.x509_operations import CACertificate, CertificateRequest, Key


class X509TestCase(SuapTestCase):
    def setUp(self):
        super(X509TestCase, self).setUp()
        self.issuer_name = six.u("fake-issuer")
        self.subject_name = six.u("fake-subject")
        self.ca_encryption_password = six.b("fake-ca-password")
        self.encryption_password = six.b("fake-password")

    def _load_pems(self, keypairs, encryption_password):
        private_key = serialization.load_pem_private_key(keypairs['private_key'], password=encryption_password, backend=default_backend())
        certificate = c_x509.load_pem_x509_certificate(keypairs['certificate'], default_backend())

        return certificate, private_key

    def _generate_ca_certificate(self, issuer_name=None):
        issuer_name = issuer_name or self.issuer_name
        ca_cert = CACertificate(issuer_name)
        ca_cert.generate_x509_root(self.ca_encryption_password)
        return ca_cert.cert_signed, ca_cert.key.private

        # keypairs = {
        #     'private_key': key_pem,
        #     'certificate': sign(
        #         csr,
        #         issuer_name,
        #         ca_key,
        #         ca_key_password=ca_key_password,
        #         skip_validation=True),
        # }

        # keypairs = generate_ca_certificate(
        #     issuer_name, encryption_password=self.ca_encryption_password)
        #
        # return self._load_pems(keypairs, self.ca_encryption_password)

    def _generate_client_certificate(self, issuer_name, subject_name):
        issuer_name = issuer_name or self.issuer_name
        subject_name = subject_name or self.issuer_name

        ca_cert = CACertificate(issuer_name)
        ca_cert.generate_x509_root(self.ca_encryption_password)

        ca_csr = CertificateRequest(subject_name, ca_cert)
        c_cert = ca_csr.generate_sign_client_certificate(self.encryption_password)
        return c_cert.cert_signed, c_cert.key.private

        # ca = generate_ca_certificate(
        #     self.issuer_name, encryption_password=self.ca_encryption_password)
        # keypairs = generate_client_certificate(
        #     self.issuer_name,
        #     self.subject_name,
        #     ca['private_key'],
        #     encryption_password=self.encryption_password,
        #     ca_key_password=self.ca_encryption_password,
        # )
        #
        # return self._load_pems(keypairs, self.encryption_password)

    def _generate_client_revoked_certificate(self, issuer_name, subject_name):
        issuer_name = issuer_name or self.issuer_name
        subject_name = subject_name or self.issuer_name

        ca_cert = CACertificate(issuer_name)
        ca_cert.generate_x509_root(self.ca_encryption_password)

        ca_csr = CertificateRequest(subject_name, ca_cert)
        c_cert = ca_csr.generate_sign_client_certificate(self.encryption_password)
        certificate = ca_cert.revoke(c_cert)
        return certificate.cert_signed, certificate.key.private

    def _public_bytes(self, public_key):
        return public_key.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)

    def _private_bytes(self, private_key):
        return private_key.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption())

    def _generate_private_key(self):
        return Key._generate_private_key()

    def _build_csr(self, private_key):
        csr = c_x509.CertificateSigningRequestBuilder()
        csr = csr.subject_name(c_x509.Name([c_x509.NameAttribute(NameOID.COMMON_NAME, self.subject_name)]))

        return csr.sign(private_key, hashes.SHA256(), default_backend())

    def assertHasPublicKey(self, keypairs):
        key = keypairs[1]
        cert = keypairs[0]

        self.assertEqual(self._public_bytes(key.public_key()), self._public_bytes(cert.public_key()))

    def assertHasSubjectName(self, cert, subject_name):
        actual_subject_name = cert.subject.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)
        actual_subject_name = actual_subject_name[0].value

        self.assertEqual(subject_name, actual_subject_name)

    def assertHasIssuerName(self, cert, issuer_name):
        actual_issuer_name = cert.issuer.get_attributes_for_oid(c_x509.NameOID.COMMON_NAME)
        actual_issuer_name = actual_issuer_name[0].value

        self.assertEqual(issuer_name, actual_issuer_name)

    def assertInClientExtensions(self, cert):
        key_usage = c_x509.KeyUsage(True, False, True, False, False, False, False, False, False)
        key_usage = c_x509.Extension(key_usage.oid, True, key_usage)
        extended_key_usage = c_x509.ExtendedKeyUsage([c_x509.OID_CLIENT_AUTH])
        extended_key_usage = c_x509.Extension(extended_key_usage.oid, False, extended_key_usage)
        basic_constraints = c_x509.BasicConstraints(ca=False, path_length=None)
        basic_constraints = c_x509.Extension(basic_constraints.oid, True, basic_constraints)

        self.assertIn(key_usage, cert.extensions)
        self.assertIn(extended_key_usage, cert.extensions)
        self.assertIn(basic_constraints, cert.extensions)

    def test_generate_ca_certificate_with_bytes_issuer_name(self):
        issuer_name = six.b("bytes-issuer-name")
        cert, _ = self._generate_ca_certificate(issuer_name)

        issuer_name = issuer_name.decode('utf-8')
        self.assertHasSubjectName(cert, issuer_name)
        self.assertHasIssuerName(cert, issuer_name)

    def test_generate_ca_certificate_has_publickey(self):
        keypairs = self._generate_ca_certificate(self.issuer_name)

        self.assertHasPublicKey(keypairs)

    def test_generate_ca_certificate_set_subject_name(self):
        cert, _ = self._generate_ca_certificate(self.issuer_name)

        self.assertHasSubjectName(cert, self.issuer_name)

    def test_generate_ca_certificate_set_issuer_name(self):
        cert, _ = self._generate_ca_certificate(self.issuer_name)

        self.assertHasIssuerName(cert, self.issuer_name)

    def test_generate_ca_certificate_set_extentions_as_ca(self):
        cert, _ = self._generate_ca_certificate(self.issuer_name)

        key_usage = c_x509.KeyUsage(False, False, False, False, False, True, False, False, False)
        key_usage = c_x509.Extension(key_usage.oid, True, key_usage)
        basic_constraints = c_x509.BasicConstraints(ca=True, path_length=0)
        basic_constraints = c_x509.Extension(basic_constraints.oid, True, basic_constraints)

        self.assertIn(key_usage, cert.extensions)
        self.assertIn(basic_constraints, cert.extensions)

    def test_generate_client_certificate_has_publickey(self):
        keypairs = self._generate_client_certificate(self.issuer_name, self.subject_name)

        self.assertHasPublicKey(keypairs)

    def test_generate_client_certificate_set_subject_name(self):
        cert, _ = self._generate_client_certificate(self.issuer_name, self.subject_name)

        self.assertHasSubjectName(cert, self.subject_name)

    def test_generate_client_certificate_set_issuer_name(self):
        cert, key = self._generate_client_certificate(self.issuer_name, self.subject_name)

        self.assertHasIssuerName(cert, self.issuer_name)

    def test_generate_client_certificate_set_extentions_as_client(self):
        cert, key = self._generate_client_certificate(self.issuer_name, self.subject_name)

        self.assertInClientExtensions(cert)

    def test_generate_client_revoked_certificate(self):
        certificate, private_key = self._generate_client_revoked_certificate(self.issuer_name, self.subject_name)
        self.assertHasPublicKey((certificate, private_key))

    def test_load_pem_private_key_with_bytes_private_key(self):
        private_key = self._generate_private_key()
        private_key = self._private_bytes(private_key)

        self.assertIsInstance(private_key, six.binary_type)
        private_key = Key._load_pem_private_key(private_key)
        self.assertIsInstance(private_key, rsa.RSAPrivateKey)

    def test_load_pem_private_key_with_unicode_private_key(self):
        private_key = self._generate_private_key()
        private_key = self._private_bytes(private_key)
        private_key = six.text_type(private_key.decode('utf-8'))

        self.assertIsInstance(private_key, six.text_type)
        private_key = Key._load_pem_private_key(private_key)
        self.assertIsInstance(private_key, rsa.RSAPrivateKey)

    # @mock.patch('cryptography.x509.load_pem_x509_csr')
    # @mock.patch('six.b')
    # def test_sign_with_unicode_csr(self, mock_six, mock_load_pem):
    # def test_sign_with_unicode_csr(self):
    #     ca_key = self._generate_private_key()
    #     private_key = self._generate_private_key()
    #     csr_obj = self._build_csr(private_key)
    #     csr = csr_obj.public_bytes(serialization.Encoding.PEM)
    #     csr = six.text_type(csr.decode('utf-8'))
    #
    #     # mock_load_pem.return_value = csr_obj
    #     ca_key_password = None
    #     sign(csr, self.issuer_name, ca_key, ca_key_password,
    #                     skip_validation=True)
    #     # mock_six.assert_called_once_with(csr)

    # def test_sign_with_invalid_csr(self):
    #     class InvalidCsr(Exception):
    #         pass
    #         # message = _("Received invalid csr %(csr)s.")
    #
    #     ca_key = self._generate_private_key()
    #     csr = 'test'
    #     csr = six.u(csr)
    #
    #     self.assertRaises(InvalidCsr,
    #                       sign,
    #                       csr, self.issuer_name, ca_key, skip_validation=True)
