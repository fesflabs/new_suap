# -*- coding: utf-8 -*-

from comum.tests import SuapTestCase
from datetime import datetime, timedelta
from django.apps.registry import apps
from functools import reduce

User = apps.get_model('comum', 'user')
Group = apps.get_model('auth', 'group')
Permission = apps.get_model('auth', 'permission')
Configuracao = apps.get_model('comum', 'configuracao')
Setor = apps.get_model('rh', 'setor')
UnidadeOrganizacional = apps.get_model('rh', 'unidadeorganizacional')
Servidor = apps.get_model('rh', 'servidor')
Processo = apps.get_model('protocolo', 'processo')
Tramite = apps.get_model('protocolo', 'tramite')


class ProtocoloTestCase(SuapTestCase):
    @classmethod
    def setUpClass(cls):
        super(ProtocoloTestCase, cls).setUpClass()

    def setUp(self):
        super(ProtocoloTestCase, self).setUp()
        self.servidor_b.cargo_emprego = self.cargo_emprego_b
        # Atribuindo a um servidor de teste a permissão para cadastrar/receber processos
        self.servidor_b.user.groups.add(Group.objects.get(name='Cadastrador de processos'))
        self.servidor_b.save()

        # PERMISSÃO A = "pode_editar_processo_em_tramite"
        # PERMISSÃO C =  "pode_editar_processo_sem_tramite_completo"
        permissao_a = Permission.objects.get(codename='pode_editar_processo_em_tramite')
        permissao_c = Permission.objects.get(codename='pode_editar_processo_sem_tramite_completo')

        # Atribuindo as permissões a usuários de teste
        SuapTestCase.limpar_cache_permission()
        self.servidor_a.user.user_permissions.add(permissao_a)
        self.servidor_a.user.save()
        self.assertTrue(self.servidor_a.user.has_perm('protocolo.pode_editar_processo_em_tramite'))

        self.servidor_c.user.user_permissions.add(permissao_c)
        self.servidor_c.user.save()

        # Logando o servidor_b como usuário
        # print("logging %s with %s" % (self.servidor_b.user.username, self.servidor_b.cargo_emprego))
        self.client.login(username=self.servidor_b.user.username, password='123')

        # Criando um processo para ser usado nos testes
        self.processo_a = Processo(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)
        self.processo_a.save()

    def _test_cadastrar_processo(self):
        # Obtendo a quantidade inicial de processos cadastrados
        processos_qtd = Processo.objects.count()

        # Cadastrando um processo
        response = self.client.post(
            '/admin/protocolo/processo/add/',
            dict(numero_documento='123', assunto='Assunto Tal', tipo='1', palavras_chave='assunto teste', tipo_encaminhamento_primeira_tramitacao='nenhum'),
        )

        # Testando se não houve erro do servidor
        self.assertNotEqual(response.status_code, 500)

        # Testando se agora tem-se um processo a mais cadastrado
        self.assertEqual(Processo.objects.count(), processos_qtd)

    def test_gerar_capa(self):
        # Criando um trâmite para o processo cadastrado
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.setor_a1_suap,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
        )

        # Gerando a capa desse processo
        response = self.client.get('/protocolo/capa_processo/{}/'.format(self.processo_a.pk))

        # Testando sucesso do request
        self.assertEqual(response.status_code, 200)

    def test_primeiro_tramite(self):
        # Verificando se o processo já tem trâmite
        self.assertEqual(Tramite.objects.filter(processo=self.processo_a).count(), 0)

        # Encaminhando o processo
        self.client.post(
            '/protocolo/processo_encaminhar_primeiro_tramite/{}/interno/'.format(self.processo_a.pk),
            dict(processo=self.processo_a.pk, observacao_encaminhamento="", orgao_interno_recebimento=self.setor_b1_suap.pk),
        )

        # Testando se agora tem-se um trâmite
        self.assertEqual(Tramite.objects.filter(processo=self.processo_a).count(), 1)

        # Chamando a view de caixa de entrada e saída
        response = self.client.get('/protocolo/caixa_entrada_saida/')

        # Testando sucesso do request
        self.assertEqual(response.status_code, 200)

        # Obtendo o trâmite
        tramite = self.processo_a.get_ultimo_tramite()

        # Testando se os dados conferem: a pessoa que encaminhou e o órgão interno de encaminhamento
        self.assertEqual(tramite.orgao_interno_encaminhamento, tramite.vinculo_encaminhamento.setor)

    def test_encaminhar_um_tramite(self):
        # Criando o primeiro trâmite,
        # encaminhando-o
        # e recebendo-o
        tramite = Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            tipo_encaminhamento=Tramite.TIPO_ENCAMINHAMENTO_INTERNO,
            orgao_interno_encaminhamento=self.servidor_b.setor,
            vinculo_encaminhamento=self.servidor_b.get_vinculo(),
            data_encaminhamento=datetime.now(),
            data_recebimento=datetime.today(),
            vinculo_recebimento=self.servidor_c.get_vinculo(),
            orgao_interno_recebimento=self.setor_a2_suap,
        )

        self.client.logout()

        # Atribuindo a outro servidor de teste as permissões para cadastrar/receber processos
        self.servidor_c.user.groups.add(Group.objects.get(name='Cadastrador de processos'))
        self.servidor_c.save()

        # Fazendo login do usuário que recebeu e que encaminhará o trâmite
        self.client.login(username=self.servidor_c.user.username, password='123')

        # Encaminhando um trâmite que não é o primeiro
        self.client.post(
            '/protocolo/processo_encaminhar/{}/interno/'.format(tramite.pk),
            dict(processo=self.processo_a.pk, observacao_encaminhamento="", orgao_interno_recebimento=self.servidor_c.setor.pk),
        )

        # Chamando a view de caixa de entrada e saída
        response = self.client.get('/protocolo/caixa_entrada_saida/')

        # Testando sucesso do request
        self.assertEqual(response.status_code, 200)

        # Obtendo o último trâmite
        tramite = self.processo_a.get_ultimo_tramite()

        # Testando se os dados conferem: a pessoa que encaminhou e o órgão interno de encaminhamento
        self.assertEqual(tramite.vinculo_encaminhamento.id, self.servidor_c.get_vinculo().id)
        self.assertEqual(tramite.orgao_interno_encaminhamento, self.servidor_c.setor)

    def test_receber_processo(self):
        # Criando o primeiro trâmite e encaminhando-o
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            tipo_encaminhamento=Tramite.TIPO_ENCAMINHAMENTO_INTERNO,
            orgao_interno_encaminhamento=self.servidor_b.setor,
            vinculo_encaminhamento=self.servidor_b.get_vinculo(),
            data_encaminhamento=datetime.now(),
            orgao_interno_recebimento=self.setor_a2_suap,
        )

        # Fazendo o logout da pessoa que encaminha o trâmite
        self.client.logout()

        # Atribuindo a outro servidor de teste as permissões para cadastrar/receber processos
        self.servidor_c.user.groups.add(Group.objects.get(name='Cadastrador de processos'))
        self.servidor_c.save()

        # Logando a pessoa que recebe o trâmite
        self.client.login(username=self.servidor_c.user.username, password='123')

        # Obtendo o último trâmite do processo
        tramite = self.processo_a.get_ultimo_tramite()

        # Recebendo o trâmite
        self.client.post('/protocolo/processo_receber/{}/'.format(tramite.pk))

        # Chamando a view de caixa de entrada e saída
        response = self.client.get('/protocolo/caixa_entrada_saida/')

        # Testando sucesso do request
        self.assertEqual(response.status_code, 200)

        # Obtendo o último trâmite do processo
        tramite = self.processo_a.get_ultimo_tramite()

        # Testando se dados conferem: pessoa que recebeu o trâmite e o órgão interno de recebimento
        self.assertEqual(tramite.vinculo_recebimento.setor, tramite.orgao_interno_recebimento)

    def test_permissao_edicao(self):
        # Criando um processo com tramite completo
        processo_b = Processo.objects.create(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)

        Tramite.objects.create(
            processo=processo_b,
            ordem=1,
            orgao_interno_encaminhamento=self.setor_b1_suap,
            vinculo_encaminhamento=self.servidor_b.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_a2_suap,
            data_recebimento=datetime.today(),
        )

        # Criando um processo com trâmite não completo
        processo_c = Processo.objects.create(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)

        Tramite.objects.create(
            processo=processo_c,
            ordem=1,
            orgao_interno_encaminhamento=self.setor_b1_suap,
            vinculo_encaminhamento=self.servidor_b.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_a2_suap,
        )

        # Criando o processo finalizado
        processo_d = Processo.objects.create(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)

        Tramite.objects.create(
            processo=processo_d,
            ordem=1,
            orgao_interno_encaminhamento=self.setor_b1_suap,
            vinculo_encaminhamento=self.servidor_b.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_a2_suap,
            data_recebimento=datetime.today(),
        )

        processo_d.status = Processo.STATUS_FINALIZADO
        processo_d.save()

        # Testando se usuário com PERMISSÃO A pode editar um processo novo sem trâmite
        self.assertTrue(self.processo_a.pode_editar_processo(self.servidor_c.user))

        # Testando se usuário com PERMISSÃO C pode editar um processo novo sem trâmite
        self.assertTrue(self.processo_a.pode_editar_processo(self.servidor_c.user))

        # Testando se usuário com PERMISSÃO A pode editar um processo com trâmite completo
        self.assertTrue(processo_b.pode_editar_processo(self.servidor_a.user))

        # Testando se usuário com PERMISSÃO C pode editar um processo com trâmite completo
        self.assertFalse(processo_b.pode_editar_processo(self.servidor_c.user))

        # Testando se usuário com PERMISSÃO A pode editar um processo com trâmite nõo completo
        self.assertTrue(processo_c.pode_editar_processo(self.servidor_a.user))

        # Testando se usuário com PERMISSÃO C pode editar um processo com trâmite nõo completo
        self.assertTrue(processo_c.pode_editar_processo(self.servidor_c.user))

        # Testando se usuário com PERMISSÃO A pode editar um processo finalizado
        self.assertFalse(processo_d.pode_editar_processo(self.servidor_a.user))

        # Testando se usuário com PERMISSÃO C pode editar um processo finalizado
        self.assertFalse(processo_d.pode_editar_processo(self.servidor_c.user))

    def test_geracao_numero_protocolo(self):
        def calcula_digito_verificador(numero):
            dv1 = (11 - (reduce(lambda x, y: x + y, [int(numero[::-1][x - 2]) * x for x in range(16, 1, -1)]) % 11)) % 10
            numero2 = numero + str(dv1)
            dv2 = (11 - (reduce(lambda x, y: x + y, [int(numero2[::-1][x - 2]) * x for x in range(17, 1, -1)]) % 11)) % 10
            return '%d%d' % (dv1, dv2)

        contador = 11 - Processo.objects.all().count()
        for i in range(contador):
            Processo.objects.create(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)

        # Testa se o digito verificador está correto
        for processo in Processo.objects.all():
            numero = processo.numero_processo[:-3].replace('.', '')
            dv = processo.numero_processo[-2:]
            self.assertTrue(dv == calcula_digito_verificador(numero))


class ProcessoAtrasadoTest(SuapTestCase):
    def _setUp(self):
        super(ProcessoAtrasadoTest, self).setUp()

        # Atribuindo a um servidor de teste a permissão para cadastrar/receber processos
        self.servidor_b.user.groups.add(Group.objects.get(name='Cadastrador de processos'))
        self.servidor_b.save()

        # Logando o servidor_b como usuário
        self.client.login(username=self.servidor_b.user.username, password='123')

        # Criando um processo para ser usado nos testes
        self.processo_a = Processo(vinculo_cadastro=self.servidor_b.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_b.setor)
        self.processo_a.save()

    def _test_processo_novo(self):
        # Um processo sem trâmite não está atrasado
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_tramite_mesmo_campus_sem_conf(self):
        # Processo encaminhado agora
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_a2_suap,
        )
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_tramite_mesmo_campus_nao_atrasado(self):
        # Criando a configuração
        Configuracao.objects.create(app='protocolo', chave='tempo_tramite_mesmo_campus', valor=12)
        # Processo encaminhado agora
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_a2_suap,
        )
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_tramite_mesmo_campus_atrasado(self):
        # Criando a configuração
        Configuracao.objects.create(app='protocolo', chave='tempo_tramite_mesmo_campus', valor=12)
        # Processo encaminhado ontem
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now() - timedelta(1),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_a2_suap,
        )
        self.assertTrue(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 1)

    def _test_tramite_outro_campus_sem_conf(self):
        # Processo encaminhado agora
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
        )
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_tramite_outro_campus_nao_atrasado(self):
        # Criando a configuração
        Configuracao.objects.create(app='protocolo', chave='tempo_tramite_diferentes_campi', valor=12)
        # Processo encaminhado agora
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
        )
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_tramite_outro_campus_atrasado(self):
        # Criando a configuração
        Configuracao.objects.create(app='protocolo', chave='tempo_tramite_diferentes_campi', valor=12)
        # Processo encaminhado ontem
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now() - timedelta(1),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
        )
        self.assertTrue(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 1)

    def _test_analise_sem_conf(self):
        # Processo em análise desde agora
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
            data_recebimento=datetime.now(),
            vinculo_recebimento=self.servidor_a.get_vinculo(),
            observacao_recebimento='Recebi',
        )
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_analise_nao_atrasado(self):
        # Criando a configuração
        Configuracao.objects.create(app='protocolo', chave='tempo_analise', valor=12)
        # Processo em análise desde agora
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now(),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
            data_recebimento=datetime.now(),
            vinculo_recebimento=self.servidor_a.get_vinculo(),
            observacao_recebimento='Recebi',
        )
        self.assertFalse(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 0)

    def _test_analise_atrasado(self):
        # Criando a configuração
        Configuracao.objects.create(app='protocolo', chave='tempo_analise', valor=12)
        # Processo em análise desde ontem
        Tramite.objects.create(
            processo=self.processo_a,
            ordem=1,
            orgao_interno_encaminhamento=self.servidor_a.setor,
            vinculo_encaminhamento=self.servidor_a.get_vinculo(),
            data_encaminhamento=datetime.now() - timedelta(1),
            observacao_encaminhamento='Despachei',
            orgao_interno_recebimento=self.setor_b1_suap,
            data_recebimento=datetime.now() - timedelta(1),
            vinculo_recebimento=self.servidor_a.get_vinculo(),
            observacao_recebimento='Recebi',
        )
        self.assertTrue(self.processo_a.is_atrasado())
        # XXX: A próxima linha funcionará apenas com o Postgres 8.4
        # Enquanto não atualizarmos o servidor, o método retorna queryset vazia.
        # self.assertEquals(Processo.get_atrasados().filter(id=self.processo_a.id).count(), 1)
