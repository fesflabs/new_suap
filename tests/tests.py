# -*- coding: utf-8 -*-

from django.apps.registry import apps
from django.test.testcases import TestCase


Configuracao = apps.get_model('comum', 'configuracao')

Setor = apps.get_model('rh', 'setor')
Situacao = apps.get_model('rh', 'situacao')
UnidadeOrganizacional = apps.get_model('rh', 'unidadeorganizacional')

Servidor = apps.get_model('rh', 'servidor')


class ServidorTest(TestCase):
    def cria_arvore_suap(self):
        self.setor_suap_1_campus_1 = Setor.todos.create(nome='Setor SUAP 1 - Campus 1', sigla='SUAP11')
        self.setor_suap_2_campus_1 = Setor.todos.create(nome='Setor SUAP 2 - Campus 1', sigla='SUAP21', superior=self.setor_suap_1_campus_1)
        self.setor_suap_3_campus_2 = Setor.todos.create(nome='Setor SUAP 3 - Campus 2', sigla='SUAP32')

        self.uo_suap_1 = UnidadeOrganizacional.objects.suap().create(setor=self.setor_suap_1_campus_1)
        self.uo_suap_2 = UnidadeOrganizacional.objects.suap().create(setor=self.setor_suap_3_campus_2)

    def cria_arvore_siape(self):
        self.setor_siape_1_campus_1 = Setor.todos.create(codigo='1', nome='Setor SIAPE - Campus 1', sigla='SIAPE11')
        self.setor_siape_3_campus_1 = Setor.todos.create(codigo='3', nome='Setor SIAPE - Campus 1', sigla='SIAPE31', superior=self.setor_siape_1_campus_1)
        self.setor_siape_2_campus_2 = Setor.todos.create(codigo='2', nome='Setor SIAPE - Campus 2', sigla='SIAPE22')

        self.uo_siape_1 = UnidadeOrganizacional.objects.suap().create(setor=self.setor_siape_1_campus_1, equivalente=self.uo_suap_1)
        self.uo_siape_2 = UnidadeOrganizacional.objects.suap().create(setor=self.setor_siape_2_campus_2, equivalente=self.uo_suap_2)

    def recarregar(self):
        # Recarregando os objetos com valores que foram definidos nos save's
        self.setor_suap_1_campus_1 = Setor.todos.get(id=self.setor_suap_1_campus_1.id)
        self.setor_suap_2_campus_1 = Setor.todos.get(id=self.setor_suap_2_campus_1.id)
        self.setor_suap_3_campus_2 = Setor.todos.get(id=self.setor_suap_3_campus_2.id)
        self.setor_siape_1_campus_1 = Setor.todos.get(id=self.setor_siape_1_campus_1.id)
        self.setor_siape_3_campus_1 = Setor.todos.get(id=self.setor_siape_3_campus_1.id)
        self.setor_siape_2_campus_2 = Setor.todos.get(id=self.setor_siape_2_campus_2.id)

    def setUp(self):
        self.cria_arvore_suap()
        self.cria_arvore_siape()
        self.recarregar()

    def test_servidor_save(self):
        """ Testa o método Servidor.save
            Regras:
            1) servidor.username deverá ser a matricula do servidor
            2) Se a árvore de setores for SIAPE, então setor será o setor de exercício (que sempre será o setor do SIAPE)
                senão (a árvore de setores é SUAP) se a UO do setor for diferente da UO do setor de exercicio 
                (isso ocorrerá quando o servidor for novo ou mudar de UO), então o setor será nulo
            3) ...
        """
        setores = Configuracao.objects.get_or_create(app='comum', chave='setores', valor='SUAP')[0]
        servidor = Servidor.objects.get_or_create(matricula='1000001', setor_exercicio=self.setor_siape_1_campus_1, situacao=Situacao.objects.create(codigo='02'))[0]
        self.assertEqual(servidor.username, servidor.matricula)

        setores.valor = 'SUAP'
        setores.save()
        servidor.save()
        self.assertEqual(servidor.setor, None)  # Quando a árvore for SUAP, mas o setor for um setor SIAPE, invariavelmente o setor será nulo
        self.assertEqual(servidor.setor_exercicio, self.setor_siape_1_campus_1)

        # Atribuindo setor do campus para um setor em UO equivalente ao UO de setor de exercicío
        servidor.setor = self.setor_suap_1_campus_1
        servidor.save()
        self.assertEqual(servidor.setor_exercicio, self.setor_siape_1_campus_1)
        self.assertEqual(servidor.setor, self.setor_suap_1_campus_1)

        # Mudando o setor de exercicio para outro setor da mesma UO
        servidor.setor_exercicio = self.setor_siape_3_campus_1
        servidor.save()
        self.assertEqual(servidor.setor_exercicio, self.setor_siape_3_campus_1)
        self.assertEqual(servidor.setor, self.setor_suap_1_campus_1)

        # Mudando o servidor de UO
        servidor.setor_exercicio = self.setor_siape_2_campus_2
        servidor.save()
        self.assertEqual(servidor.setor, None)
        self.assertEqual(servidor.setor_exercicio, self.setor_siape_2_campus_2)

        # Testando servidor sem setor_exercicio
        servidor.setor_exercicio = None
        servidor.save()
        self.assertEqual(servidor.setor, None)
        self.assertEqual(servidor.setor_exercicio, None)
