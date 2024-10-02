# -*- coding: utf-8 -*-

from django.contrib.auth.models import Group

from comum.tests import SuapTestCase, SuapClient


class RHTestCase(SuapTestCase):
    def setUp(self):
        super(RHTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get_or_create(name='Coordenador de Gestão de Pessoas Sistêmico')[0])

    def test_ver_e_editar_servidor(self):
        client_servidor = SuapClient()
        client_servidor.login(username=self.servidor_a.user.username, password='123')

        res_ver = client_servidor.get('/rh/servidor/{}/'.format(self.servidor_a.matricula))
        self.assertContains(res_ver, self.servidor_a.matricula, status_code=200)

        res_editar = client_servidor.get('/admin/rh/servidor/{:d}/change/'.format(self.servidor_a.pk))
        self.assertContains(res_editar, self.servidor_a.matricula, status_code=200)
