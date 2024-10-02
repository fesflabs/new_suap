# -*- coding: utf-8 -*-

from comum.tests import SuapTestCase
from django.apps.registry import apps
from almoxarifado.forms import EmpenhoForm

PlanoContasAlmox = apps.get_model('almoxarifado', 'planocontasalmox')
CategoriaMaterialConsumo = apps.get_model('almoxarifado', 'categoriamaterialconsumo')
Empenho = apps.get_model('almoxarifado', 'empenho')
EmpenhoConsumo = apps.get_model('almoxarifado', 'empenhoconsumo')
Entrada = apps.get_model('almoxarifado', 'entrada')
EntradaTipo = apps.get_model('almoxarifado', 'entradatipo')
Group = apps.get_model('auth', 'group')
MaterialConsumo = apps.get_model('almoxarifado', 'materialconsumo')
MaterialTipo = apps.get_model('almoxarifado', 'MaterialTipo')
MovimentoAlmoxEntrada = apps.get_model('almoxarifado', 'movimentoalmoxentrada')
MovimentoAlmoxEntradaTipo = apps.get_model('almoxarifado', 'movimentoalmoxentradatipo')
MovimentoAlmoxSaidaTipo = apps.get_model('almoxarifado', 'movimentoalmoxsaidatipo')
Processo = apps.get_model('protocolo', 'processo')
RequisicaoAlmoxUO = apps.get_model('almoxarifado', 'requisicaoalmoxuo')
RequisicaoAlmoxUOMaterial = apps.get_model('almoxarifado', 'requisicaoalmoxuomaterial')
RequisicaoAlmoxUser = apps.get_model('almoxarifado', 'requisicaoalmoxuser')
RequisicaoAlmoxUserMaterial = apps.get_model('almoxarifado', 'requisicaoalmoxusermaterial')
Servidor = apps.get_model('rh', 'servidor')


class AlmoxarifadoTestCase(SuapTestCase):
    def setUp(self):
        super(AlmoxarifadoTestCase, self).setUp()

        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Almoxarifado'))
        self.servidor_b.user.groups.add(Group.objects.get(name='Coordenador de Almoxarifado'))

        self.planocontas = PlanoContasAlmox.objects.create(codigo='01', descricao='Plano Contas 01')

        self.ed_mat_cons = CategoriaMaterialConsumo.objects.create(codigo='01', nome='Categoria 01', plano_contas=self.planocontas)

        # cadastra mat1 e testa o código
        self.mat1 = MaterialConsumo.objects.create(categoria=self.ed_mat_cons, nome='Material para consumir')
        self.assertEqual(self.mat1.codigo, str(self.mat1.id).zfill(6))

        # cadastra mat2 e testa o código
        self.mat2 = MaterialConsumo.objects.create(categoria=self.ed_mat_cons, nome='Mais material de consumo')
        self.assertEqual(self.mat2.codigo, str(self.mat2.id).zfill(6))

        # Cadastra um processo do Protocolo
        self.processo = Processo.objects.create(vinculo_cadastro=self.servidor_a.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_a.setor)

        MovimentoAlmoxEntradaTipo.objects.create(nome='entrada')
        MovimentoAlmoxEntradaTipo.objects.create(nome='requisicao_uo_material')
        MovimentoAlmoxSaidaTipo.objects.create(nome='requisicao_user_material')
        MovimentoAlmoxSaidaTipo.objects.create(nome='requisicao_uo_material')

    def test_cadastrar_empenho(self):
        """
        Testa o cadastro de empenho de consumo e a adição de itens.

        Empenho 2012NE999999
            - mat1 qtd:10 valor:10,00
            - mat2 qtd:10 valor:20,00
        """

        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        # Cadastrando o empenho de pessoa juridica
        empenho_count = Empenho.objects.count()
        self.client.post(
            '/admin/almoxarifado/empenho/add/',
            dict(
                numero='2012NE999999',
                processo=self.processo.pk,
                tipo_material=MaterialTipo.CONSUMO().pk,
                tipo_pessoa=EmpenhoForm.TIPO_PESSOA_JURIDICA,
                pessoa_juridica=self.pessoa_juridica.pk,
            ),
        )

        # Verificando se empenho foi cadastrado e que não tem itens ainda
        self.assertEqual(Empenho.objects.count(), empenho_count + 1)
        empenho = Empenho.objects.latest('id')
        self.assertEqual(empenho.get_itens().count(), 0)

        # Cadastrando itens para o empenho
        self.client.post('/almoxarifado/empenho/{}/'.format(empenho.pk), dict(material=self.mat1.pk, qtd_empenhada='10', valor='10,00'))
        self.client.post('/almoxarifado/empenho/{}/'.format(empenho.pk), dict(material=self.mat2.pk, qtd_empenhada='10', valor='20,00'))

        # Verificando cadastro de itens
        self.assertEqual(empenho.get_itens().count(), 2)
        self.assertEqual(len(EmpenhoConsumo.get_pendentes(empenho)), 2)
        self.emp_item_1, self.emp_item_2 = empenho.get_itens()
        self.assertEqual(self.emp_item_1.qtd_adquirida, 0)
        self.assertEqual(self.emp_item_2.qtd_adquirida, 0)

        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        # Cadastrando o empenho de pessoa fisica
        empenho_count = Empenho.objects.count()
        self.client.post(
            '/admin/almoxarifado/empenho/add/',
            dict(
                numero='2012NE999999',
                processo=self.processo.pk,
                tipo_material=MaterialTipo.CONSUMO().pk,
                tipo_pessoa=EmpenhoForm.TIPO_PESSOA_FISICA,
                pessoa_fisica=self.prestador_1.get_vinculo().id,
            ),
        )

        # Verificando se empenho foi cadastrado e que não tem itens ainda
        self.assertEqual(Empenho.objects.count(), empenho_count + 1)
        empenho = Empenho.objects.latest('id')
        self.assertEqual(empenho.get_itens().count(), 0)

        # Cadastrando itens para o empenho
        self.client.post('/almoxarifado/empenho/{}/'.format(empenho.pk), dict(material=self.mat1.pk, qtd_empenhada='10', valor='10,00'))
        self.client.post('/almoxarifado/empenho/{}/'.format(empenho.pk), dict(material=self.mat2.pk, qtd_empenhada='10', valor='20,00'))

        # Verificando cadastro de itens
        self.assertEqual(empenho.get_itens().count(), 2)
        self.assertEqual(len(EmpenhoConsumo.get_pendentes(empenho)), 2)
        self.emp_item_1, self.emp_item_2 = empenho.get_itens()
        self.assertEqual(self.emp_item_1.qtd_adquirida, 0)
        self.assertEqual(self.emp_item_2.qtd_adquirida, 0)

    def test_cadastrar_entrada(self):
        """
        Testa o cadastro de entradas NF em diferentes campi.

        Entrada NF campus A
            - mat1 qtd:5
            - mat2 qtd:10

        Entrada NF campus B
            - mat1 qtd:5
        """
        self.test_cadastrar_empenho()

        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        # Recuperando o empenho de consumo cadastrado em `test_cadastrar_empenho`
        # e verificando itens pendentes.
        empenho = Empenho.objects.latest('id')
        self.assertEqual(len(EmpenhoConsumo.get_pendentes(empenho)), 2)

        # Testando acesso à página de cadastramento de entradas
        response = self.client.get('/almoxarifado/entrada_compra/')
        self.assertContains(response, 'Efetuar Entrada de Compra', status_code=200)

        # Cadastrando a entrada no campus 'A'
        self.client.post(
            '/almoxarifado/entrada_realizar/',
            {
                'data_entrada': '01/01/2012',
                'empenho_hidden': empenho.pk,
                'fornecedor_hidden': self.pessoa_juridica.pk,
                'numero_nota': '001',
                'data_nota': '01/01/2012',
                'empenho_itens': [self.emp_item_1.pk, self.emp_item_2.pk],
                'qtds': [5, 10],
            },
        )

        # Verificando o total de entradas
        self.assertEqual(empenho.get_entradas().count(), 1)

        # Verificando quantidade de itens adquiridos e pendentes
        self.assertEqual(empenho.empenhoconsumo_set.order_by("id")[0].qtd_adquirida, 5)
        self.assertEqual(empenho.empenhoconsumo_set.order_by("id")[1].qtd_adquirida, 10)
        self.assertEqual(len(EmpenhoConsumo.get_pendentes(empenho)), 1)

        # Testar estoques dos itens (campus A)
        # mat1 entrada
        self.assertEqual(self.mat1.get_estoque_atual(), 5)
        mat1_entrada_normal = self.mat1.entrada_normal(uo_id=self.campus_a_suap.pk)
        self.assertEqual([mat1_entrada_normal['qtd'], mat1_entrada_normal['valor']], [5, 5 * self.emp_item_1.valor])
        mat1_entrada_transferencia = self.mat1.entrada_transferencia(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat1_entrada_transferencia.values()), [0, 0])
        mat1_entrada = self.mat1.entrada(uo_id=self.campus_a_suap.pk)
        self.assertEqual([mat1_entrada['qtd'], mat1_entrada['valor']], [5, 5 * self.emp_item_1.valor])
        # mat1 saida (tudo zero)
        mat1_saida_normal = self.mat1.saida_normal(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat1_saida_normal.values()), [0, 0])
        mat1_saida_transferencia = self.mat1.saida_transferencia(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat1_saida_transferencia.values()), [0, 0])
        mat1_saida = self.mat1.saida(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat1_saida.values()), [0, 0])
        # mat2 entrada
        self.assertEqual(self.mat2.get_estoque_atual(), 10)
        mat2_entrada_normal = self.mat2.entrada_normal(uo_id=self.campus_a_suap.pk)
        self.assertEqual([mat2_entrada_normal['qtd'], mat2_entrada_normal['valor']], [10, 10 * self.emp_item_2.valor])
        mat2_entrada_transferencia = self.mat2.entrada_transferencia(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat2_entrada_transferencia.values()), [0, 0])
        mat2_entrada = self.mat2.entrada(uo_id=self.campus_a_suap.pk)
        self.assertEqual([mat2_entrada['qtd'], mat2_entrada['valor']], [10, 10 * self.emp_item_2.valor])
        # mat2 saida (tudo zero)
        mat2_saida_normal = self.mat2.saida_normal(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat2_saida_normal.values()), [0, 0])
        mat2_saida_transferencia = self.mat2.saida_transferencia(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat2_saida_transferencia.values()), [0, 0])
        mat2_saida = self.mat2.saida(uo_id=self.campus_a_suap.pk)
        self.assertEqual(list(mat2_saida.values()), [0, 0])

        # Testar cadastro de entrada de outro usuário
        # Efetuar login com o servidor b do campus B
        self.client.logout()
        self.client.login(username=self.servidor_b.user.username, password='123')

        # Testando acesso à página de cadastramento de entradas
        response = self.client.get('/almoxarifado/entrada_compra/')
        self.assertContains(response, 'Efetuar Entrada de Compra', status_code=200)

        # Cadastrando a entrada no campus 'B'
        self.client.post(
            '/almoxarifado/entrada_realizar/',
            {
                'data_entrada': '01/01/2012',
                'empenho_hidden': empenho.pk,
                'fornecedor_hidden': self.pessoa_juridica.pk,
                'numero_nota': '002',
                'data_nota': '01/01/2012',
                'empenho_itens': [self.emp_item_1.pk],
                'qtds': [5],
            },
        )

        # Verificando o total de entradas
        self.assertEqual(empenho.get_entradas().count(), 2)

        # Verificando quantidade de itens adquiridos e pendentes
        self.assertEqual(empenho.empenhoconsumo_set.order_by("id")[0].qtd_adquirida, 10)  # + 5
        self.assertEqual(empenho.empenhoconsumo_set.order_by("id")[1].qtd_adquirida, 10)  # continua 10
        self.assertEqual(len(EmpenhoConsumo.get_pendentes(empenho)), 0)

        # Testar estoques dos itens (campus B)
        # mat1 entrada
        self.assertEqual(self.mat1.get_estoque_atual(), 5)
        mat1_entrada_normal = self.mat1.entrada_normal(uo_id=self.campus_b_suap.pk)
        self.assertEqual([mat1_entrada_normal['qtd'], mat1_entrada_normal['valor']], [5, 5 * self.emp_item_1.valor])
        mat1_entrada_transferencia = self.mat1.entrada_transferencia(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat1_entrada_transferencia.values()), [0, 0])
        mat1_entrada = self.mat1.entrada(uo_id=self.campus_b_suap.pk)
        self.assertEqual([mat1_entrada['qtd'], mat1_entrada['valor']], [5, 5 * self.emp_item_1.valor])
        # mat1 saida (tudo zero)
        mat1_saida_normal = self.mat1.saida_normal(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat1_saida_normal.values()), [0, 0])
        mat1_saida_transferencia = self.mat1.saida_transferencia(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat1_saida_transferencia.values()), [0, 0])
        mat1_saida = self.mat1.saida(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat1_saida.values()), [0, 0])
        # mat2 entrada
        self.assertEqual(self.mat2.get_estoque_atual(), 0)
        mat2_entrada_normal = self.mat2.entrada_normal(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat2_entrada_normal.values()), [0, 0])
        mat2_entrada_transferencia = self.mat2.entrada_transferencia(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat2_entrada_transferencia.values()), [0, 0])
        mat2_entrada = self.mat2.entrada(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat2_entrada.values()), [0, 0])
        # mat2 saida (tudo zero)
        mat2_saida_normal = self.mat2.saida_normal(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat2_saida_normal.values()), [0, 0])
        mat2_saida_transferencia = self.mat2.saida_transferencia(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat2_saida_transferencia.values()), [0, 0])
        mat2_saida = self.mat2.saida(uo_id=self.campus_b_suap.pk)
        self.assertEqual(list(mat2_saida.values()), [0, 0])

    def test_requisicao_consumo(self):
        """
        Testa o cadastro de requisição para consumo de algum servidor. 
        Valida também se o campus fornecedor tem quantidade em estoque 
        suficiente. Valida-se também a quantidade em estoque antes e após a 
        avaliação da requisição.
        """
        self.test_cadastrar_entrada()

        # Efetuar login com o servidor a do campus A
        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        # Testar estoque de itens
        self.assertEqual(self.mat1.get_estoque_atual(uo=self.campus_a_suap), 5)
        self.assertEqual(list(self.mat1.saida(uo_id=self.campus_a_suap.pk).values()), [0, 0])
        self.assertEqual(list(self.mat1.saida_normal(uo_id=self.campus_a_suap.pk).values()), [0, 0])
        self.assertEqual(list(self.mat1.saida_transferencia(uo_id=self.campus_a_suap.pk).values()), [0, 0])
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_a_suap), 10)
        self.assertEqual(list(self.mat2.saida(uo_id=self.campus_a_suap.pk).values()), [0, 0])
        self.assertEqual(list(self.mat2.saida_normal(uo_id=self.campus_a_suap.pk).values()), [0, 0])
        self.assertEqual(list(self.mat2.saida_transferencia(uo_id=self.campus_a_suap.pk).values()), [0, 0])

        # Quantidade de requisições pendentes
        qtd_pendentes = len(RequisicaoAlmoxUser.get_pendentes(self.servidor_a.user))

        # Testando acesso à página de cadastramento de requisições
        response = self.client.get('/almoxarifado/form_requisicao_usuario_pedido/')
        self.assertContains(response, 'Requisição de Saída de Material para Consumo', status_code=200)

        # Cadastrando requisição
        self.client.post(
            '/almoxarifado/requisicao_usuario_pedido/',
            {'uo_id': self.servidor_a.setor.uo.pk, 'solicitante_hidden': self.servidor_a.pk, 'itens_hidden': [self.mat1.pk, self.mat2.pk], 'quantidades': [2, 20]},
        )

        # Verificando o total de requisições pendentes
        self.assertEqual(len(RequisicaoAlmoxUser.get_pendentes(self.servidor_a.user)), qtd_pendentes + 1)

        # Recuperando requisição criada
        requisicao = RequisicaoAlmoxUser.objects.latest("id")

        # Testando acesso à página de requisições pendentes
        response = self.client.get('/almoxarifado/requisicoes_pendentes/')
        self.assertEqual(str('/almoxarifado/requisicao_detalhe/user/{}/'.format(requisicao.id)) in response.content.decode(), True)

        # Responder requisições
        response = self.client.get('/almoxarifado/requisicao_detalhe/user/{}/'.format(requisicao.id))
        self.assertContains(response, 'Responder Requisição', status_code=200)

        # Quantidade maior que a apresentada em estoque
        response = self.client.post(
            '/almoxarifado/requisicao_resposta/user/{}/'.format(requisicao.id),
            {'idRequisicoesMaterial': [requisicao.item_set.all().order_by("id")[1]], 'quantidadesAceitas': [20]},
            follow=True,
        )
        self.assertContains(response, 'A quantidade solicitada (20) é maior que a disponível (10).', status_code=200)

        # Verifica se a requisicao continua pendente
        self.assertEqual(len(RequisicaoAlmoxUser.get_pendentes(self.servidor_a.user)), qtd_pendentes + 1)
        # Verifica se o estoque do material não foi alterado
        self.assertEqual(requisicao.item_set.all().order_by("id")[1].material.get_estoque_atual(uo=self.campus_a_suap), 10)

        # Resposta possível
        response = self.client.post(
            '/almoxarifado/requisicao_resposta/user/{}/'.format(requisicao.id),
            {'idRequisicoesMaterial': [requisicao.item_set.all().order_by("id")[0], requisicao.item_set.all().order_by("id")[1]], 'quantidadesAceitas': [1, 5]},
            follow=True,
        )
        self.assertContains(response, 'Saída de Material Realizada. Detalhes:', status_code=200)

        # Verificar que a requisição saiu da lista de pendentes
        self.assertEqual(len(RequisicaoAlmoxUser.get_pendentes(self.servidor_a.user)), qtd_pendentes)

        # Verifica se os estoques correspondem as atualizações
        self.assertEqual(self.mat1.get_estoque_atual(uo=self.campus_a_suap), 4)
        self.assertEqual(list(self.mat1.saida(uo_id=self.campus_a_suap.pk).values()), [1, 1 * self.emp_item_1.valor])
        self.assertEqual(list(self.mat1.saida_normal(uo_id=self.campus_a_suap.pk).values()), [1, 1 * self.emp_item_1.valor])
        self.assertEqual(list(self.mat1.saida_transferencia(uo_id=self.campus_a_suap.pk).values()), [0, 0])
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_a_suap), 5)
        self.assertEqual(list(self.mat2.saida(uo_id=self.campus_a_suap.pk).values()), [5, 5 * self.emp_item_2.valor])
        self.assertEqual(list(self.mat2.saida_normal(uo_id=self.campus_a_suap.pk).values()), [5, 5 * self.emp_item_2.valor])
        self.assertEqual(list(self.mat2.saida_transferencia(uo_id=self.campus_a_suap.pk).values()), [0, 0])

    def test_requisicao_transferencia(self):
        """Testa o cadastro de requisição para transferência para outro campus.
        Valida também se o campus fornecedor tem quantidade em estoque 
        suficiente. Valida-se também a quantidade em estoque antes e após a 
        avaliação da requisição para cada campus envolvido."""

        self.test_cadastrar_entrada()
        """ Após rodar o método `test_cadastrar_entrada`:
        Campus A: mat1: 5; mat2: 10;
        Campus B: mat1: 5; mat2: 0;"""

        # Testando estoques
        # Campus A
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_a_suap), 10)
        self.assertEqual(self.mat2.saida(uo_id=self.campus_a_suap.pk)['qtd'], 0)
        self.assertEqual(self.mat2.saida_normal(uo_id=self.campus_a_suap.pk)['qtd'], 0)
        self.assertEqual(self.mat2.saida_transferencia(uo_id=self.campus_a_suap.pk)['qtd'], 0)

        # Campus B
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_b_suap), 0)
        self.assertEqual(self.mat2.entrada(uo_id=self.campus_b_suap.pk)['qtd'], 0)
        self.assertEqual(self.mat2.entrada_normal(uo_id=self.campus_b_suap.pk)['qtd'], 0)
        self.assertEqual(self.mat2.entrada_transferencia(uo_id=self.campus_b_suap.pk)['qtd'], 0)

        # Quantidade de requisições pendentes
        self.assertEqual(len(RequisicaoAlmoxUO.get_pendentes(self.servidor_a.user)), 0)

        # Testando acesso à página de cadastramento de requisições
        response = self.client.get('/almoxarifado/form_requisicao_uo_pedido/')
        self.assertContains(response, 'Requisição de Transferência de Material de Consumo Intercampi', status_code=200)

        # Cadastrando requisição
        self.client.post('/almoxarifado/requisicao_uo_pedido/', {'uo_id': self.servidor_a.setor.uo.pk, 'itens_hidden': [self.mat2.pk], 'quantidades': [5]})  # fornecedor

        # Verificando o total de requisições pendentes
        self.assertEqual(len(RequisicaoAlmoxUO.get_pendentes(self.servidor_a.user)), 1)

        # Recuperando requisição criada
        requisicao = RequisicaoAlmoxUO.objects.latest("id")

        # Efetuar login com o servidor a do campus A
        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        # Testando que a requisição criada está sendo apresentada na página de reqs pendentes
        response = self.client.get('/almoxarifado/requisicoes_pendentes/')
        self.assertTrue(str('/almoxarifado/requisicao_detalhe/uo/{}/'.format(requisicao.id)) in response.content.decode())

        # Responder requisições
        response = self.client.get('/almoxarifado/requisicao_detalhe/uo/{}/'.format(requisicao.id))
        self.assertContains(response, 'Responder Requisição', status_code=200)

        # Quantidade maior que a apresentada em estoque
        response = self.client.post(
            '/almoxarifado/requisicao_resposta/uo/{}/'.format(requisicao.id),
            {'idRequisicoesMaterial': [requisicao.item_set.all().order_by("id")[0]], 'quantidadesAceitas': [20]},
            follow=True,
        )

        self.assertContains(response, ' A quantidade solicitada (20) é maior que a disponível (10).', status_code=200)
        # Verifica se a requisicao continua pendente
        self.assertEqual(len(RequisicaoAlmoxUO.get_pendentes(self.servidor_a.user)), 1)

        # Verifica se o estoque do material não foi alterado
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_a_suap), 10)

        # Responder requisições
        response = self.client.get('/almoxarifado/requisicao_detalhe/uo/{}/'.format(requisicao.id))
        self.assertContains(response, 'Responder Requisição', status_code=200)

        # Resposta possível
        response = self.client.post(
            '/almoxarifado/requisicao_resposta/uo/{}/'.format(requisicao.id),
            {'idRequisicoesMaterial': [requisicao.item_set.all().order_by("id")[0]], 'quantidadesAceitas': [5]},
            follow=True,
        )
        self.assertContains(response, 'Saída de Material Realizada. Detalhes:', status_code=200)

        # Verificar que a requisição saiu da lista de pendentes
        self.assertEqual(len(RequisicaoAlmoxUO.get_pendentes(self.servidor_a.user)), 0)

        # Testando estoques
        # Campus A
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_a_suap), 5)

        # verificando se "saida" (filtra por UO) ou "saida_normal" (todos os UOs) continuam com estoque
        # zerado já que esse processo não é de entrada comum, e sim de TRANSFERÊNCIA
        self.assertEqual(self.mat2.saida(uo_id=self.campus_a_suap.pk)['qtd'], 0)
        self.assertEqual(self.mat2.saida_normal(uo_id=self.campus_a_suap.pk)['qtd'], 0)

        # verifica se a transferência foi realizada (compara estoque)
        self.assertEqual(self.mat2.saida_transferencia(uo_id=self.campus_a_suap.pk)['qtd'], 5)

        # Campus B
        self.assertEqual(self.mat2.get_estoque_atual(uo=self.campus_b_suap), 5)

        # mesmo caso da SAIDA (como se trata de uma transferência, o estoque via "entrada" ou "entrada_normal"
        # devem permanecer inalterados
        self.assertEqual(self.mat2.entrada(uo_id=self.campus_b_suap.pk)['qtd'], 0)
        self.assertEqual(self.mat2.entrada_normal(uo_id=self.campus_b_suap.pk)['qtd'], 0)

        # verifica se a entrada foi realizada (transferência)
        self.assertEqual(self.mat2.entrada_transferencia(uo_id=self.campus_b_suap.pk)['qtd'], 5)

    def test_remocao_entrada(self):
        """
        Testa a remoção de uma entrada.
        """
        # A última entrada cadastrada foi para o campus B
        self.test_cadastrar_entrada()

        # Recuperando empenho cadastrado e a quantidade de entradas do empenho
        empenho = Empenho.objects.latest("id")
        qtd_entradas = empenho.get_entradas().count()

        # Recuperando entrada cadastrada
        entrada = Entrada.objects.latest("id")

        # Testando acesso à página com o botão de remoção
        response = self.client.get('/almoxarifado/entrada/{}/'.format(entrada.id))
        self.assertContains(response, '/almoxarifado/entrada/{}/remover/'.format(entrada.id), status_code=200)

        # Testando acesso à página com o botão de remoção
        self.client.get('/almoxarifado/entrada/{}/remover/'.format(entrada.id))

        # Testando a remoção da entrada
        self.assertEqual(empenho.get_entradas().count(), qtd_entradas - 1)

    def test_remocao_itens_empenho_sem_entrada(self):
        """
        Testa a remoção dos itens de empenho. Verifica se 
        após a exclusão de todos os itens o empenho
        também será removido.
        """
        self.test_cadastrar_empenho()

        # Recuperando empenho cadastrado
        empenho = Empenho.objects.latest("id")

        # Verificando quantidade de empenhos cadastrados
        qtd_empenhos = Empenho.objects.count()

        # Verificando itens do empenho
        qtd_itens = empenho.get_itens().count()

        # Testando acesso à página de empenho
        response = self.client.get('/almoxarifado/empenho/{}/'.format(empenho.id))
        self.assertContains(response, '/almoxarifado/empenhoconsumo/{}/remover/'.format(empenho.empenhoconsumo_set.order_by("id")[0].id), status_code=200)
        # Removendo item 1
        self.client.get('/almoxarifado/empenhoconsumo/{}/remover/'.format(empenho.empenhoconsumo_set.order_by("id")[0].id))

        # Verificando quantidade de itens de empenho
        self.assertEqual(empenho.get_itens().count(), qtd_itens - 1)

        # Removendo item 1 e consequetemente o empenho
        self.client.get('/almoxarifado/empenhoconsumo/{}/remover/'.format(empenho.empenhoconsumo_set.order_by("id")[0].id))

        # Verificando se o empenho foi removido
        self.assertEqual(Empenho.objects.count(), qtd_empenhos - 1)

    def test_remocao_itens_empenho_com_entrada(self):
        """
        Testa a remoção dos itens de empenho. Verifica se depois
        de cadastrada uma entrada, um item fica impossibilitado
        de ser removido.
        """
        # cadastrar empenho, cadastrar 2 itens, cadastrar entrada para o primeiro item, remover o segundo item do empenho, remover o primeiro item (nao deve ser permitido)
        # quando tiver sido cadastrado uma entrada
        self.test_cadastrar_empenho()

        # Recuperando empenho cadastrado
        empenho = Empenho.objects.latest("id")

        # Verificando quantidade de empenhos cadastrados
        qtd_empenhos = Empenho.objects.count()

        # Verificando itens do empenho
        qtd_itens = empenho.get_itens().count()

        # Quantidade de entradas no empenho
        qtd_entradas = empenho.get_entradas().count()

        # Testando acesso à página de cadastramento de entradas
        response = self.client.get('/almoxarifado/entrada_compra/')
        self.assertContains(response, 'Efetuar Entrada de Compra', status_code=200)

        # Cadastrando a entrada
        self.client.post(
            '/almoxarifado/entrada_realizar/',
            {
                'data_entrada': '01/01/2012',
                'empenho_hidden': empenho.pk,
                'fornecedor_hidden': self.pessoa_juridica.pk,
                'numero_nota': '001',
                'data_nota': '01/01/2012',
                'empenho_itens': [empenho.empenhoconsumo_set.order_by("id")[0].pk],
                'qtds': [5],
            },
        )

        # Verificando o total de entradas
        self.assertEqual(empenho.get_entradas().count(), qtd_entradas + 1)

        # Verificando que não existe o ícone de remoção do item de empenho
        response = self.client.get('/almoxarifado/empenho/{}/'.format(empenho.id))
        self.assertNotContains(response, '/almoxarifado/empenhoconsumo/{}/remover/'.format(empenho.empenhoconsumo_set.order_by("id")[0].id), status_code=200)

        # Removendo item 2
        self.client.get('/almoxarifado/empenhoconsumo/{}/remover/'.format(empenho.empenhoconsumo_set.order_by("id")[1].id))

        # Verificando quantidade de itens de empenho
        self.assertEqual(empenho.get_itens().count(), qtd_itens - 1)

        # Verificando que o empenho não foi removido
        self.assertEqual(Empenho.objects.count(), qtd_empenhos)

        # Recuperando entrada cadastrada
        entrada = Entrada.objects.latest("id")

        # Testando acesso à página com o botão de remoção
        response = self.client.get('/almoxarifado/entrada/{}/'.format(entrada.id))
        self.assertContains(response, '/almoxarifado/entrada/{}/remover/'.format(entrada.id), status_code=200)

        # Testando a remoção da entrada
        self.client.get('/almoxarifado/entrada/{}/remover/'.format(entrada.id))

        # Confirmando a remoção da entrada
        self.assertEqual(empenho.get_entradas().count(), qtd_entradas)

        # Removendo item 1 e consequetemente o empenho
        self.client.get('/almoxarifado/empenhoconsumo/{}/remover/'.format(empenho.empenhoconsumo_set.order_by("id")[0].id))

        # Verificando se o empenho foi removido
        self.assertEqual(Empenho.objects.count(), qtd_empenhos - 1)
