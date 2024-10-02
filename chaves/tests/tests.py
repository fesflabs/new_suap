# -*- coding: utf-8 -*-

from django.contrib.auth.models import Group

from comum.tests import SuapTestCase
from django.apps import apps

Chave = apps.get_model('chaves', 'chave')

Predio = apps.get_model('comum', 'predio')
Sala = apps.get_model('comum', 'sala')

UnidadeOrganizacional = apps.get_model('rh', 'unidadeorganizacional')


class UrlsTest(SuapTestCase):
    def setUp(self):
        super(UrlsTest, self).setUp()

        self.client.login(username=self.servidor_a.user.username, password='123')

        self.grupos = {}
        self.grupos['chaves_operador'] = Group.objects.get(name='Operador de Chaves')

        self.predio = Predio.objects.create(id=1, uo=self.campus_a_suap)
        self.sala = Sala.objects.create(id=1, predio=self.predio)

        self.sala.avaliadores_de_agendamentos.add(self.servidor_a.user)

    def _test_get_chaves(self):
        response = self.client.get('/admin/chaves/chave/')
        self.assertEqual(response.status_code, 403)

        self.servidor_a.user.groups.add(self.grupos['chaves_operador'])
        response = self.client.get('/admin/chaves/chave/')
        self.assertEqual(response.status_code, 200)

    def test_salvar_chaves(self):
        self.assertEqual(Chave.objects.filter(identificacao='T1').count(), 0)
        self.servidor_a.user.groups.add(self.grupos['chaves_operador'])
        response = self.client.post('/admin/chaves/chave/add/', dict(identificacao='T1', sala=self.sala.id))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Chave.objects.filter(identificacao='T1').count(), 1)
