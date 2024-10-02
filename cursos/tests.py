# -*- coding: utf-8 -*-

from comum.tests import SuapTestCase

# from decimal import Decimal
# from django.apps import apps

# Group = apps.get_model('auth', 'group')
# Curso = apps.get_model('cursos', 'curso')
# #HorasPermitidas = apps.get_model('cursos', 'horaspermitidas')
# Atividade = apps.get_model('cursos', 'atividade')
# #CotaAnualServidor = apps.get_model('cursos', 'cotaanualservidor')
# #HorasTrabalhadas = apps.get_model('cursos', 'horastrabalhadas')
# Ano = apps.get_model('comum', 'ano')


class CursosTestCase(SuapTestCase):
    def setUp(self):
        super(CursosTestCase, self).setUp()

        # #Obtendo um usuário para realizar as operações
        # self.servidor_b.user.groups.add(Group.objects.get(name='Operador de Cursos e Concursos'))
        # self.servidor_b.save()
        # #Efetuando o login do usuário operador
        # retorno = self.client.login(username = self.servidor_b.user.username,
        #                   password = '123')
        #
        # self.assertEquals(retorno, True)
        #
        # #Obtendo o ano de realização para os cursos/concursos
        # self.ano = Ano(ano=2011)
        # self.ano.save()
        #
        # #Criando atividades para o curso
        # self.atividade_a = Atividade(descricao  = u'Atividade A',
        #                      valor_hora = Decimal(str(50.0)))
        # self.atividade_a.save()
        #
        # self.atividade_b = Atividade(descricao  = u'Atividade B',
        #                      valor_hora = Decimal(str(100.0)))
        # self.atividade_b.save()
        #
        # self.atividade_c = Atividade(descricao  = u'Atividade C',
        #                      valor_hora = Decimal(str(200.0)))
        # self.atividade_c.save()
        #
        # # carrega campus e setor
        # unidadeorganizacional = self.setor_a0_suap.uo
        #
        # #Criando um Curso
        # self.curso = Curso(
        #     ano_pagamento = self.ano,
        #     descricao = u'Reciclagem',
        #     campus=unidadeorganizacional,
        #     tipo=1
        #     )
        # self.curso.save()
        #
        # #Criando novo Curso
        # self.curso_novo = Curso(ano_pagamento = self.ano,
        #                         descricao = u'Oratória',
        #                         campus=unidadeorganizacional,
        #                         tipo=1)
        # self.curso_novo.save()
        #
        # #Criando limite de horas
        # self.horas_permitidas_a = HorasPermitidas(
        #     qtd_horas=120.0,
        #     default=True)
        # self.horas_permitidas_a.save()
        #
        # self.horas_permitidas_b = HorasPermitidas(
        #     qtd_horas=240.0,
        #     default=False)
        # self.horas_permitidas_b.save()
        #
        # #Criando uma Cota Anual de Horas para o Servidor
        # self.cotaanualservidor_a = CotaAnualServidor(
        #     pessoa=self.servidor_a,
        #     ano_pagamento=self.ano,
        #     horas_permitidas=self.horas_permitidas_a)
        # self.cotaanualservidor_a.save()
        #
        # self.cotaanualservidor_b = CotaAnualServidor(
        #     pessoa=self.servidor_b,
        #     ano_pagamento=self.ano,
        #     horas_permitidas=self.horas_permitidas_b)
        # self.cotaanualservidor_b.save()

    # def test_cadastrar_horas_trabalhadas(self):
    #
    #     cota_1 = CotaAnualServidor.objects.get(id=self.cotaanualservidor_a.id)
    #
    #     ht_a = cota_1.qtd_horas_trabalhadas
    #
    #     # Cadastrando horas trabalhadas
    #     response = self.client.post('/cursos/adicionar_horas/%s/' % self.curso.id,
    #         dict(servidor      = self.servidor_a.pk,
    #              atividade     = self.atividade_a.pk,
    #              mes_pagamento = '1',
    #              qtd_horas     = '80.0',
    #              curso         = self.curso.id))
    #
    #     # Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #
    #     cota_2 = CotaAnualServidor.objects.get(id=self.cotaanualservidor_a.id)
    #     ht_a_depois = cota_2.qtd_horas_trabalhadas
    #     hr_a_depois = cota_2.qtd_horas_restantes
    #
    #     # Testando se agora há as horas trabalhadas cadastradas
    #     self.assertEquals(ht_a_depois, ht_a + 80.0)
    #
    #     # Testando se as horas restantes são calculadas corretamente
    #     self.assertEquals(hr_a_depois, self.cotaanualservidor_a.horas_permitidas.qtd_horas - 80.0)
    #
    # def test_remover_horas_trabalhadas(self):
    #     # Cadastrando horas trabalhadas para um curso
    #     response = self.client.post('/cursos/adicionar_horas/%s/' % self.curso.id,
    #         dict(servidor      = self.servidor_a.pk,
    #              atividade     = self.atividade_b.pk,
    #              mes_pagamento = '2',
    #              qtd_horas     = '30.0',
    #              curso         = self.curso.id))
    #     # Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #     # Cadastrando mais algumas horas trabalhadas para o curso
    #     response = self.client.post('/cursos/adicionar_horas/%s/' % self.curso.id,
    #         dict(servidor      = self.servidor_a.pk,
    #              atividade     = self.atividade_c.pk,
    #              mes_pagamento = '3',
    #              qtd_horas     = '10.0',
    #              curso         = self.curso.id))
    #
    #     # Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #     hr_antes = CotaAnualServidor.objects.get(id=self.cotaanualservidor_a.id).qtd_horas_restantes
    #     ht_antes = CotaAnualServidor.objects.get(id=self.cotaanualservidor_a.id).qtd_horas_trabalhadas
    #
    #     ht_queryset = self.curso.horastrabalhadas_set.filter(qtd_horas=30.0)
    #
    #     ht = ht_queryset[0]
    #
    #     # Removendo o primeiro item cadastrado de horas trabalhadas
    #     response = self.client.get('/cursos/horastrabalhadas/%s/remover/' % ht.id)
    #
    #     # Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #     ht_depois = CotaAnualServidor.objects.get(id=self.cotaanualservidor_a.id).qtd_horas_trabalhadas
    #
    #     # Testando se as horas trabalhadas foram realmente removidas
    #     self.assertEquals(ht_depois, ht_antes-30.0)
    #
    #     hr_depois = CotaAnualServidor.objects.get(id=self.cotaanualservidor_a.id).qtd_horas_restantes
    #
    #     # Testando se as horas restantes foram calculadas corretamente
    #     self.assertEquals(hr_depois, hr_antes + 30)
    #
    # def test_cadastrar_horas_excedentes(self):
    #     # Cadastrando horas trabalhadas dentro do limite do servidor
    #     response = self.client.post('/cursos/adicionar_horas/%s/' % self.curso.id,
    #                             dict(servidor      = self.servidor_b.pk,
    #                                  atividade     = self.atividade_a.pk,
    #                                  mes_pagamento = '1',
    #                                  qtd_horas     = '80.0',
    #                                  curso         = self.curso.id))
    #
    #     # Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #     # O cadastramento das horas trabalhadas para o servidor_a
    #     ht_antes = CotaAnualServidor.objects.get(id=self.cotaanualservidor_b.id).qtd_horas_trabalhadas
    #
    #     # Cadastrando horas para ultrapassar a cota do servidor
    #     response = self.client.post('/cursos/curso/%s/' % self.curso_novo.id,
    #                                 dict(servidor      = self.servidor_b.pk,
    #                                      atividade     = self.atividade_b.pk,
    #                                      mes_pagamento = '2',
    #                                      qtd_horas     = '180.0',
    #                                      curso         = self.curso_novo.id))
    #
    #     #Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #     #Obtendo horas trabalhadas cadastradas até o momento
    #     ht_depois = CotaAnualServidor.objects.get(id=self.cotaanualservidor_b.id).qtd_horas_trabalhadas
    #
    #     #Verificando se a app realmente impediu cadastramento de horas além da cota
    #     self.assertEquals(ht_antes, ht_depois)
    #
    #
    # def test_valor_hora(self):
    #     #Cadastrando horas para o servidor na atividade_a
    #     response = self.client.post('/cursos/adicionar_horas/%s/' % self.curso.id,
    #                             dict(servidor      = self.servidor_a.pk,
    #                                  atividade     = self.atividade_a.pk,
    #                                  mes_pagamento = '1',
    #                                  qtd_horas     = '80.0',
    #                                  curso         = self.curso.id))
    #
    #     #Testando se não houve erro do servidor
    #     self.assertNotEquals(response.status_code, 500)
    #
    #     # Alterando valor da hora trabalhada da atividade
    #     self.atividade_a.valor_hora = Decimal(str(80.0))
    #     self.atividade_a.save()
    #
    #     # Verificando manutenção do valor antigo da hora trabalhada para a única atividade cadastrada
    #     ht = HorasTrabalhadas.objects.get(atividade=self.atividade_a)
    #     self.assertNotEquals(ht.atividade_valor_hora, self.atividade_a.valor_hora)
