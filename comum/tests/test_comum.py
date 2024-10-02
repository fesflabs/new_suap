# -*- coding: utf-8 -*-

from comum.models import User
from comum.tests import SuapClient, SuapTestCase


class ComumTestCase(SuapTestCase):
    def test_setup(self):
        self.assertEqual(self.setor_a0_suap.uo, self.campus_a_suap)
        self.assertEqual(self.setor_a1_suap.uo, self.campus_a_suap)
        self.assertEqual(self.setor_a2_suap.uo, self.campus_a_suap)
        self.assertEqual(self.setor_b0_suap.uo, self.campus_b_suap)
        self.assertEqual(self.setor_b1_suap.uo, self.campus_b_suap)
        self.assertEqual(self.setor_b2_suap.uo, self.campus_b_suap)
        self.assertTrue(User.objects.get(id=self.servidor_a.user.id).is_active)
        self.assertTrue(User.objects.get(id=self.servidor_a.user.id).is_staff)
        self.assertTrue(User.objects.get(id=self.servidor_b.user.id).is_active)
        self.assertTrue(User.objects.get(id=self.servidor_b.user.id).is_staff)
        self.assertTrue(User.objects.get(id=self.servidor_c.user.id).is_active)
        self.assertTrue(User.objects.get(id=self.servidor_c.user.id).is_staff)

    def test_index(self):

        # Usuário anônimo
        client_anonimo = SuapClient()
        response = client_anonimo.get('/')
        self.assertNotEqual(response.status_code, 500)

        # Usuário servidor
        client_servidor = SuapClient()
        client_servidor.login(username=self.servidor_a.user.username, password='123')
        response = client_servidor.get('/')
        self.assertContains(response, self.servidor_a.user.username, status_code=200)

        # Usuário prestador
        client_prestador = SuapClient()
        client_prestador.login(username=self.prestador_1.user.username, password='123')
        response = client_prestador.get('/')
        self.assertContains(response, self.prestador_1.user.get_profile().nome_usual, status_code=200)
