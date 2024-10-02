# -*- coding: utf-8 -*-
import io
import json
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from urllib.parse import urlparse

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.core.handlers.wsgi import WSGIRequest
from django.http import SimpleCookie
from django.test.client import FakePayload, RequestFactory
from django.urls import reverse
from django.utils.http import urlencode

from arquivo.models import Arquivo, TipoArquivo
from arquivo.views import upload_handler
from comum.tests import SuapTestCase
# models usados
from djtools.storages import cache_file

User = apps.get_model('comum', 'user')
Permission = apps.get_model('auth', 'permission')
Servidor = apps.get_model('rh', 'Servidor')
Situacao = apps.get_model('rh', 'Situacao')
GrupoCargoEmprego = apps.get_model('rh', 'GrupoCargoEmprego')
JornadaTrabalho = apps.get_model('rh', 'JornadaTrabalho')
CargoEmprego = apps.get_model('rh', 'CargoEmprego')
Setor = apps.get_model('rh', 'Setor')
UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')


def create_request(path, data={}, method="GET", stream=None, content_length=0, headers=None):
    parsed = urlparse(path)
    environ = {
        'HTTP_REFERER': '..',
        'HTTP_COOKIE': SimpleCookie().output(header='', sep='; '),
        'REMOTE_ADDR': '127.0.0.1',
        'SCRIPT_NAME': '',
        'SERVER_NAME': 'testserver',
        'SERVER_PORT': '80',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.errors': None,
        'wsgi.multiprocess': True,
        'wsgi.multithread': True,
        'wsgi.run_once': False,
        'CONTENT_TYPE': 'application/octet-stream',
        'CONTENT_LENGTH': content_length,
        'PATH_INFO': urllib.parse.unquote(parsed[2]),
        'QUERY_STRING': urlencode(data, doseq=True) or parsed[4],
        'REQUEST_METHOD': method,
        'wsgi.input': BytesIO(stream) or FakePayload(''),
    }
    if headers:
        environ.update(headers)
    return WSGIRequest(environ)


# teste arquivo/views
class ArquivoViewsTestCase(SuapTestCase):
    def __init__(self, *args, **kwargs):
        super(ArquivoViewsTestCase, self).__init__(*args, **kwargs)
        self.filename = 'tmp/123.pdf'
        default_storage.save(self.filename, io.BytesIO(b'\xc4\xe8'))

    def setUp(self):
        super(ArquivoViewsTestCase, self).setUp()
        permission_a = Permission.objects.get(codename='pode_identificar_arquivo')
        permission_b = Permission.objects.get(codename='pode_validar_arquivo')
        permission_c = Permission.objects.get(codename='pode_fazer_upload_arquivo')

        self.servidor_a.user.user_permissions.add(permission_a)
        self.servidor_a.user.user_permissions.add(permission_b)
        self.servidor_a.user.user_permissions.add(permission_c)

        self.servidor_b.user.user_permissions.add(permission_a)
        self.servidor_b.user.user_permissions.add(permission_b)
        self.servidor_b.user.user_permissions.add(permission_c)

        self.factory = RequestFactory()

    def create_mock(self, status=Arquivo.STATUS_PENDENTE):
        novo_arquivo = Arquivo()
        novo_arquivo.nome = '123.pdf'
        novo_arquivo.objeto = self.servidor_a
        novo_arquivo.object_id = self.servidor_a.id
        novo_arquivo.upload_por = self.servidor_a.user
        novo_arquivo.content_type = ContentType.objects.get_for_model(self.servidor_a.__class__)
        novo_arquivo.file.save('123.pdf', io.BytesIO(b'\xc4\xe8'))
        novo_arquivo.status = status
        novo_arquivo.save()
        return novo_arquivo

    def test_arquivos_excluir(self):
        self.client.login(username='1111111', password='123')

        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        status = Arquivo.STATUS_PENDENTE
        arquivos_prev = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()
        novo_arquivo = self.create_mock(status)  # cria um arquivo
        arquivos = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        arquivo_temporario = cache_file(self.filename)
        self.assertEqual(arquivos, arquivos_prev + 1)
        url = reverse('arquivos_pendentes_servidor_excluir', kwargs={'servidor_matricula': self.servidor_a.matricula, 'arquivo_id': novo_arquivo.encrypted_pk})

        resp = self.client.post(url, follow=True)
        self.assertContains(resp, 'Arquivo removido com sucesso!')
        default_storage.save(self.filename, open(arquivo_temporario, 'rb'))

        arquivos = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()
        self.assertEqual(arquivos, arquivos_prev)

    def test_index(self):
        # testa a navegacao até o formulário de submissão

        self.client.login(username='1111111', password='123')

        url = reverse('selecionar_servidor')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(reverse('selecionar_servidor'), kwargs={'servidor_matricula': '1111111'})
        self.assertEqual(resp.status_code, 200)

        url = reverse('arquivos_upload', kwargs={'servidor_matricula': '1111111'})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_uploads(self):
        self.client.login(username='1111111', password='123')

        nome_arquivo = '123.pdf'
        arquivo = default_storage.open(self.filename)
        arquivo_content = arquivo.read()
        arquivo.close()
        url = reverse('arquivos_upload', kwargs={'servidor_matricula': '1111111'})
        request = create_request(url, {'servidor': 1111111, 'qqfile': nome_arquivo}, method='POST', stream=arquivo_content, content_length=len(arquivo_content), headers={'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        request.user = self.servidor_a.user

        numero_arquivos = Arquivo.objects.count()
        response = upload_handler(request)
        json_data = json.loads(response.content)
        self.assertTrue(json_data['success'] == True)

        # sanity test
        self.assertTrue(Arquivo.objects.count() == numero_arquivos + 1)  # foi adicionado um arquivo?
        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=Arquivo.STATUS_PENDENTE, nome=nome_arquivo)
        self.assertTrue(arquivos)

    def test_arquivos_pendentes(self):
        self.client.login(username='1111111', password='123')

        nome_arquivo = '123.pdf'
        arquivo = default_storage.open(self.filename)
        arquivo_content = arquivo.read()
        arquivo.close()
        url = reverse('arquivos_upload', kwargs={'servidor_matricula': '1111111'})
        request = create_request(url, {'servidor': 1111111, 'qqfile': nome_arquivo}, method='POST', stream=arquivo_content, content_length=len(arquivo_content), headers={'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        request.user = self.servidor_a.user

        numero_arquivos = Arquivo.objects.count()
        response = upload_handler(request)
        json_data = json.loads(response.content)
        self.assertTrue(json_data['success'])

        # sanity test
        self.assertTrue(Arquivo.objects.count() == numero_arquivos + 1)  # foi adicionado um arquivo?
        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivo_qs = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=Arquivo.STATUS_PENDENTE, nome=nome_arquivo)
        self.assertTrue(arquivo_qs)

        url = reverse('arquivos_pendentes')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        found = False
        # o arquivo adicionado existe e o seu dono é
        # o servidor corrente?
        for arq in Arquivo.objects.all():
            if self.servidor_a.id == arq.dono().id:
                found = True
                break
        self.assertTrue(found)

    def test_arquivos_pendentes_servidor(self):
        self.client.login(username='1111111', password='123')

        novo_arquivo = self.create_mock()  # criando um arquivo pendente
        url = reverse('arquivos_pendentes_servidor', kwargs={'servidor_matricula': self.servidor_a.matricula})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        found = False
        for arquivo in resp.context['arquivos_pendentes_identificar_servidor']:
            if arquivo.nome == novo_arquivo.nome:
                found = True
        self.assertTrue(found)

    def test_arquivos_identificar(self):
        self.client.login(username='1111111', password='123')

        novo_arquivo = self.create_mock()  # criando um arquivo pendente

        tipo_arquivo = TipoArquivo()
        tipo_arquivo.descricao = 'Carteira de motorista'
        tipo_arquivo.save()

        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos_prev_identificados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=Arquivo.STATUS_IDENTIFICADO).count()

        # identificando o arquivo
        url = reverse('arquivos_pendentes_servidor_identificar', kwargs={'servidor_matricula': self.servidor_a.matricula, 'arquivo_id': novo_arquivo.encrypted_pk})
        resp = self.client.post(url, {'acao': '1', 'tipo_arquivo': tipo_arquivo.id})
        self.assertEqual(resp.status_code, 302)

        arquivos_identificados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=Arquivo.STATUS_IDENTIFICADO).count()
        self.assertEqual(arquivos_identificados, arquivos_prev_identificados + 1)

    def test_arquivos_validar(self):
        self.client.login(username='1', password='123')

        novo_arquivo = self.create_mock(status=Arquivo.STATUS_IDENTIFICADO)  # criando um arquivo identificado

        tipo_arquivo = TipoArquivo()
        tipo_arquivo.descricao = 'Carteira de motorista'
        tipo_arquivo.save()

        status = Arquivo.STATUS_VALIDADO
        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos_prev_validados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        # validando o arquivo
        url = reverse('arquivos_pendentes_servidor_validar', kwargs={'servidor_matricula': self.servidor_a.matricula, 'arquivo_id': novo_arquivo.encrypted_pk})
        resp = self.client.post(url, {'acao': '2', 'tipo_arquivo': tipo_arquivo.id})
        self.assertEqual(resp.status_code, 302)

        arquivos_validados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()
        self.assertEqual(arquivos_validados, arquivos_prev_validados + 1)

    def test_arquivos_rejeitar_pendente(self):
        self.client.login(username='1', password='123')

        # cria um arquivo pendente
        status = Arquivo.STATUS_PENDENTE
        novo_arquivo = self.create_mock(status)

        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos_prev_pendentes = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        # rejeitando o arquivo pendente
        url = reverse('arquivos_pendentes_servidor_identificar', kwargs={'servidor_matricula': self.servidor_a.matricula, 'arquivo_id': novo_arquivo.encrypted_pk})
        resp = self.client.post(url, {'acao': '3', 'tipo_arquivo': '', 'justificativa_rejeicao': 'justificativa da rejeicao'})
        self.assertEqual(resp.status_code, 302)

        arquivos_pendentes = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        # um arquivo pendente foi rejeitado, logo o numero de pendentes caiu
        self.assertEqual(arquivos_pendentes + 1, arquivos_prev_pendentes)

    def test_arquivos_rejeitar_identificado(self):
        self.client.login(username='1111111', password='123')

        # cria um arquivo identificado
        status = Arquivo.STATUS_IDENTIFICADO
        novo_arquivo = self.create_mock(status)

        # identifica o arquivo
        tipo_arquivo = TipoArquivo()
        tipo_arquivo.descricao = 'Carteira de motorista'
        tipo_arquivo.save()
        novo_arquivo.tipo_arquivo = tipo_arquivo
        novo_arquivo.save()

        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos_prev_identificados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        # rejeitando o arquivo identificado
        url = reverse('arquivos_pendentes_servidor_validar', kwargs={'servidor_matricula': self.servidor_a.matricula, 'arquivo_id': novo_arquivo.encrypted_pk})
        resp = self.client.post(url, {'acao': '3', 'tipo_arquivo': tipo_arquivo.id, 'justificativa_rejeicao': 'justificativa da rejeicao'})
        self.assertEqual(resp.status_code, 302)

        arquivos_identificados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        # um arquivo identificado foi rejeitado, logo o numero de identificados caiu
        self.assertEqual(arquivos_identificados + 1, arquivos_prev_identificados)

        # verifica o sucesso ao requisitar arquivos rejeitados do servidor
        url = reverse('arquivos_rejeitados_servidor', kwargs={'servidor_matricula': self.servidor_a.matricula})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        # verifica se o arquivo rejeitado está mesmo na lista dos rejeitados
        arquivos_rejeitados = resp.context['arquivos_rejeitados_servidor']
        found = False
        for arquivo in arquivos_rejeitados:
            if arquivo.nome == novo_arquivo.nome:
                found = True
        self.assertTrue(found)

    def test_arquivos_servidor(self):
        self.client.login(username='1111111', password='123')

        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos_prev = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status__in=[Arquivo.STATUS_IDENTIFICADO, Arquivo.STATUS_VALIDADO]).count()

        self.create_mock(Arquivo.STATUS_IDENTIFICADO)  # cria um arquivo identificado
        self.create_mock(Arquivo.STATUS_VALIDADO)  # cria um arquivo validado

        # testa sucesso ao requisitar os arquivos do servidor
        url = reverse('arquivos_servidor', kwargs={'servidor_matricula': self.servidor_a.matricula})
        arquivos = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status__in=[Arquivo.STATUS_IDENTIFICADO, Arquivo.STATUS_VALIDADO]).count()
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # verifica se houve um aumento de 2 arquivos
        self.assertEqual(arquivos, arquivos_prev + 2)

    def test_arquivos_rejeitados(self):
        self.client.login(username='1111111', password='123')

        status = Arquivo.STATUS_IMAGEM_REJEITADA

        self.create_mock(status)  # cria um arquivo rejeitado

        tipo_dono = ContentType.objects.get_for_model(self.servidor_a.__class__)
        arquivos_prev_rejeitados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()

        # testa sucesso ao requisitar os arquivos rejeitados do servidor
        url = reverse('arquivos_rejeitados')
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        arquivos_rejeitados = Arquivo.objects.filter(content_type=tipo_dono, object_id=self.servidor_a.id, status=status).count()
        self.assertEqual(arquivos_rejeitados, arquivos_prev_rejeitados)

        servidores = resp.context['servidores']
        found = False
        for servidor in servidores:
            if servidor.id == self.servidor_a.id:
                found = True
        self.assertTrue(found)
