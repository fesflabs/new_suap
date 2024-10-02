from almoxarifado.models import MaterialTipo, EntradaTipo, Empenho, Entrada
from comum.models import Configuracao
from comum.tests import SuapTestCase
from django.apps import apps
from django.contrib.auth.models import Group
from almoxarifado.forms import EmpenhoForm
from patrimonio.forms import RequisicaoTransferenciaForm
from patrimonio.models import CategoriaMaterialPermanente, EntradaPermanente, Inventario, InventarioStatus, EmpenhoPermanente, Baixa, BaixaTipo, Requisicao
from patrimonio.relatorio import RelatorioTermosPDF
from protocolo.models import Processo
from rh.models import Servidor
import datetime

Predio = apps.get_model('comum', 'predio')
Sala = apps.get_model('comum', 'sala')

GRUPO_COORDENADOR_SISTEMICO = 'Coordenador de Patrimônio Sistêmico'
GRUPO_COORDENADOR_CAMPUS = 'Coordenador de Patrimônio'
GRUPO_OPERADOR_CAMPUS = 'Operador de Patrimônio'
GRUPO_AUTIDOR = 'Auditor'
GRUPO_SERVIDOR = 'Servidor'
GRUPO_CONTADOR = 'Contador de Patrimônio'


class PatrimonioTestCase(SuapTestCase):
    def setUp(self):
        super().setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Patrimônio'))
        self.servidor_b.user.groups.add(Group.objects.get(name='Coordenador de Patrimônio Sistêmico'))
        self.servidor_a.user.groups.add(Group.objects.get(name='Operador de Almoxarifado'))
        self.servidor_b.user.groups.add(Group.objects.get(name='Operador de Almoxarifado'))
        self.servidor_c.user.groups.add(Group.objects.get(name='Coordenador de Patrimônio Sistêmico'))
        self.servidor_d.user.groups.add(Group.objects.get(name='Coordenador de Patrimônio Sistêmico'))
        self.client.login(user=self.servidor_b.user)
        self.ed_01 = CategoriaMaterialPermanente.objects.create(codigo='01', nome='Categoria 01')

        self.servidor_a3 = Servidor.objects.create(
            nome='Servidor A3',
            matricula='3000',
            setor=self.setor_a2_suap,
            template=b'30',
            situacao=self.situacao_ativo_permanente,
            cpf='890.324.635-78',
            cargo_emprego=self.cargo_emprego_b,
        )

        self.predio_a = Predio.objects.get_or_create(nome='Prédio Teste', uo=self.servidor_a.setor.uo, ativo=True)[0]
        self.sala_a = Sala.objects.get_or_create(nome='Sala Teste', ativa=True, predio=self.predio_a)[0]

        self.predio_b = Predio.objects.get_or_create(nome='Prédio Teste', uo=self.servidor_b.setor.uo, ativo=True)[0]
        self.sala_b = Sala.objects.get_or_create(nome='Sala Teste', ativa=True, predio=self.predio_b)[0]

        Configuracao.objects.get_or_create(app='patrimonio', chave='dia_inicio_bloqueio', valor='26')

    def test_empenho(self):
        """
        Testa o cadastro de empenho de material permanente
        """

        # Cadastrar um empenho

        self.assertEqual(Empenho.objects.count(), 0)

        # Criando um processo
        self.processo = Processo.objects.create(vinculo_cadastro=self.servidor_a.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_a.setor)

        # Acessando a página de cadastro
        self.assertEqual(self.client.get('/admin/almoxarifado/empenho/add/').status_code, 200)
        self.client.post(
            '/admin/almoxarifado/empenho/add/',
            dict(
                numero='1423NE162534',
                processo=self.processo.pk,
                tipo_material=MaterialTipo.PERMANENTE().pk,
                tipo_pessoa=EmpenhoForm.TIPO_PESSOA_JURIDICA,
                pessoa_juridica=self.pessoa_juridica.get_vinculo().pk,
            ),
        )
        self.assertEqual(Empenho.objects.count(), 1)

        # Obtendo o empenho
        empenho = Empenho.objects.latest('id')
        self.assertEqual(empenho.get_itens().count(), 0)

        # Cadastrando itens do empenho
        # Testando acesso à página de cadastramento de itens de empenho
        response = self.client.get('/almoxarifado/empenho/%s/' % empenho.pk)
        self.assertContains(response, 'Empenhar Novo Item', status_code=200)

        # Cadastrando itens para o empenho
        response = self.client.post(
            '/almoxarifado/empenho/%s/' % empenho.pk, {'categoria': self.ed_01.pk, 'descricao': 'Material permanente 01', 'qtd_empenhada': '100', 'valor': '100,00'}
        )
        self.assertEqual(empenho.get_itens().count(), 1)

        self.client.post('/almoxarifado/empenho/%s/' % empenho.pk, {'categoria': self.ed_01.pk, 'descricao': 'Material permanente 02', 'qtd_empenhada': '50', 'valor': '100,00'})
        self.assertEqual(empenho.get_itens().count(), 2)

    def test_entrada_compra(self):

        self.test_empenho()
        """
        Testa o cadastro de uma entrada do tipo compra
        """
        # Não existe nenhuma entrada
        self.assertEqual(Entrada.objects.count(), 0)

        # Verificando se empenho foi cadastrado

        empenho = Empenho.objects.latest('id')
        self.assertEqual(len(EmpenhoPermanente.get_pendentes(empenho)), 2)
        empenhopermanente = EmpenhoPermanente.get_pendentes(empenho)
        for i in empenhopermanente:
            if i.get_qtd_pendente() == 50:
                self.assertEqual(i.get_qtd_pendente(), 50)
            else:
                self.assertEqual(i.get_qtd_pendente(), 100)

        # Dando o get para ver o form
        url = '/almoxarifado/entrada_compra/'
        response = self.client.get(url)
        self.assertContains(response, 'Efetuar Entrada de Compra', status_code=200)

        self.client.post(
            '/almoxarifado/entrada_realizar/',
            {
                'csrfmiddlewaretoken': '%s' % response.context['csrf_token'],
                'data_entrada': '01/01/2012',
                'empenho_hidden': empenho.pk,
                'fornecedor_hidden': self.pessoa_juridica.get_vinculo().pk,
                'numero_nota': '001',
                'data_nota': '01/01/2012',
                'empenho_itens': [empenho.empenhopermanente_set.order_by("id")[0].pk, empenho.empenhopermanente_set.order_by("id")[1].pk],
                'qtds': [50, 50],
            },
        )

        self.assertEqual(empenho.empenhopermanente_set.order_by("id")[0].qtd_adquirida, 50)
        self.assertEqual(empenho.empenhopermanente_set.order_by("id")[1].qtd_adquirida, 50)

        self.assertEqual(Entrada.objects.count(), 1)

        for i in empenho.empenhopermanente_set.order_by("id"):
            if i.get_qtd_pendente() == 50:
                self.assertEqual(i.get_qtd_pendente(), 50)
            else:
                self.assertEqual(i.get_qtd_pendente(), 0)

        # Recuperando os inventários cadastrados
        invs = Inventario.objects.all()
        # Verificando se 2 inventários foram cadastrados
        self.assertEqual(invs.count(), 100)

        # Verificando campos dos inventários
        for i in invs:
            self.assertEqual(i.status, InventarioStatus.PENDENTE())
            self.assertEqual(i.responsavel_vinculo, None)

    def test_entrada_doacao(self):
        """
        Testa o cadastro de uma entrada do tipo doação.
        """
        # Não existe nenhuma entrada
        self.assertEqual(Entrada.objects.count(), 0)

        # Dando o get para ver o form
        url = '/almoxarifado/entrada_doacao/'
        response = self.client.get(url)
        self.assertContains(response, 'Efetuar Entrada de Doação', status_code=200)

        # Submetendo o form
        self.client.post(
            url,
            {
                'data': '01/01/2011',
                'data_time': '08:00:00',
                'uo': self.servidor_a.setor.uo.pk,
                'tipo_entrada': EntradaTipo.DOACAO().pk,
                'tipo_material': MaterialTipo.PERMANENTE().pk,
                'vinculo_fornecedor': self.pessoa_juridica.get_vinculo().pk,
            },
        )

        # Existe uma entrada
        self.assertEqual(Entrada.objects.count(), 1)

    def test_entrada_doacao_adicionar_itens(self):
        """
        Teste de adição de itens a uma entrada de doação
        """
        qtd_invs_antes = Inventario.objects.count()
        # Verificando que não há inventários cadastrados
        self.assertEqual(qtd_invs_antes, 0)
        # Cadastrando a doação que vai conter os itens
        self.client.post(
            '/almoxarifado/entrada_doacao/',
            {
                'data': '01/01/2011',
                'data_time': '09:00:00',
                'uo': self.servidor_a.setor.uo.pk,
                'tipo_entrada': EntradaTipo.DOACAO().pk,
                'tipo_material': MaterialTipo.PERMANENTE().pk,
                'vinculo_fornecedor': self.pessoa_juridica.get_vinculo().pk,
            },
        )

        # Recuperando a entrada cadastrada
        pk_entrada = Entrada.objects.all()[0].pk

        # Verificando acesso à página para adição de itens
        response = self.client.get('/almoxarifado/entrada/%s/' % pk_entrada)

        self.assertContains(response, 'Adicionar Item', status_code=200)

        # Adicionando um item
        response = self.client.post(
            '/almoxarifado/entrada/%s/adicionar_item/' % pk_entrada, {'categoria': self.ed_01.pk, 'descricao': 'A forma de tal', 'qtd': '2', 'valor': '20,00'}
        )
        # Recuperando a entrada permanente gerada
        ep = EntradaPermanente.objects.get(entrada__pk=pk_entrada)
        # Recuperando os inventários cadastrados
        invs = Inventario.objects.all()
        # Verificando se 2 inventários foram cadastrados
        self.assertEqual(invs.count(), qtd_invs_antes + 2)

        # Verificando campos dos inventários
        for i in invs:
            self.assertEqual(i.entrada_permanente.pk, ep.pk)
            self.assertEqual(i.status, InventarioStatus.PENDENTE())
            self.assertEqual(i.responsavel_vinculo, None)

    def test_carga(self):
        self.test_entrada_compra()
        """
        Testa a carga de inventarios
        """
        inventarios = Inventario.objects.all()[:10]

        # Verifica acesso à página
        url = '/patrimonio/carga/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        qtd_requisicoes = Requisicao.objects.count()

        response = self.client.post(
            url, {'servidor_destino': self.servidor_b.pk, 'inventarios': [i.id for i in inventarios], 'estado_conservacao': Inventario.CONSERVACAO_BOM, 'sala': self.sala_b.pk}
        )
        self.assertEqual(qtd_requisicoes + 1, Requisicao.objects.count())
        requisicao = Requisicao.objects.latest('id')

        response = self.deferir_requisicao(requisicao)
        requisicao = Requisicao.objects.latest('id')

        # Após deferida muda o status
        self.assertEqual(requisicao.status, Requisicao.STATUS_DEFERIDA)

        # Verificando se a carga foi efetuada para o servidor
        for i in Inventario.objects.all()[:10]:
            self.assertEqual(i.status, InventarioStatus.ATIVO())
            self.assertEqual(i.responsavel_vinculo.pk, self.servidor_b.pk)

    def verificar_envio_email(self, to, subject):
        from django.core import mail
        if type(to) is list:
            emails = []
            for _ in to:
                email = mail.outbox.pop()
                emails.extend(email.to)
        else:
            email = mail.outbox.pop()
            emails = email.to

        # Verify that the subject of the first message is correct.
        self.assertEqual(email.subject, subject)
        self.assertEqual(set(emails), set(to))
        mail.outbox = list()

    def test_transferencia(self):
        """
        Testa a transferência de inventarios de mesmo campus e diferentes campus
        """
        # Teste para transferência de inventarios do mesmo campus

        # Teste de carga
        self.test_carga()
        # Verifica acesso à  página de transferência
        response = self.client.get('/patrimonio/requisitar_transferencia/')
        self.assertContains(response, 'Requisitar Transferência', status_code=200)

        # Transferencia de inventarios do mesmo campus
        inventario = Inventario.objects.all()[3]
        response = self.client.post(
            '/patrimonio/requisitar_transferencia/',
            {
                'servidor_origem': self.servidor_b.pk,
                'servidor_destino': self.servidor_d.pk,
                'tipo_transferencia': RequisicaoTransferenciaForm.TIPO_TRANSFERENCIA_INVENTARIOS,
                'inventarios': inventario.id,
            },
            follow=True,
        )

        self.assertContains(response, 'Requisição de transferência de patrimônio efetuada com sucesso', status_code=200)
        # É enviado um email para o servidor de destino avisando da criação
        self.verificar_envio_email([self.servidor_d.email], '[SUAP] Patrimônio: Envio de Requisição de Transferência')

        requisicao = Requisicao.objects.latest('id')
        if requisicao.ver_periodo_deferimento() is True:
            response = self.deferir_requisicao(requisicao)
        # Dá erro de permissão porque o sevidor logado, servidor b, não é o servidor destino
        self.assertEqual(response.status_code, 302)

        self.client.logout()
        self.client.login(username=self.servidor_d.user.username, password='123')

        qtd_carga_contabeis = inventario.cargas_contabeis.count()
        carga_contabil = inventario.cargas_contabeis.latest('id')
        response = self.deferir_requisicao(requisicao)
        requisicao = Requisicao.objects.latest('id')
        inventario = Inventario.objects.all()[3]
        # Após deferida muda o status
        self.assertEqual(requisicao.status, Requisicao.STATUS_DEFERIDA)
        # Como é do mesmo campus não cria carga contábil
        self.assertEqual(qtd_carga_contabeis, inventario.cargas_contabeis.count())
        # A carga contábil continua sendo a mesma
        self.assertEqual(carga_contabil.campus, inventario.cargas_contabeis.latest('id').campus)
        # É enviado um email para o servidor de origem e os coordenadores de patrimônio
        self.verificar_envio_email([self.servidor_b.email], '[SUAP] Patrimônio: Deferimento da Requisição de Transferência #%s' % requisicao.id)

        # Transferência de inventários de campus diferentes
        response = self.client.post(
            '/patrimonio/requisitar_transferencia/',
            {'servidor_origem': self.servidor_d.pk, 'servidor_destino': self.servidor_a.pk, 'tipo_transferencia': 'inventarios', 'inventarios': inventario.id},
            follow=True,
        )

        self.assertContains(response, 'Requisição de transferência de patrimônio efetuada com sucesso', status_code=200)
        # É enviado um email para o servidor de destino avisando da criação
        self.verificar_envio_email([self.servidor_a.email], '[SUAP] Patrimônio: Envio de Requisição de Transferência')

        requisicao = Requisicao.objects.latest('id')
        response = self.deferir_requisicao(requisicao)
        # Dá erro de permissão porque o sevidor logado, servidor b, não é o servidor destino
        self.assertEqual(response.status_code, 302)

        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        qtd_carga_contabeis = inventario.cargas_contabeis.count()
        carga_contabil = inventario.cargas_contabeis.latest('id')
        response = self.deferir_requisicao(requisicao)
        requisicao = Requisicao.objects.latest('id')
        inventario = Inventario.objects.all()[3]
        if requisicao.ver_periodo_deferimento() is True:
            # Após deferida muda o status
            self.assertEqual(requisicao.status, Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_ORIGEM)
            # Como é de campus diferentes cria carga contábil
            self.assertEqual(qtd_carga_contabeis + 1, inventario.cargas_contabeis.count())
            # A carga contábil muda para a do servidor_a
            self.assertNotEqual(carga_contabil.campus, inventario.cargas_contabeis.latest('id').campus)
            self.assertEqual(self.servidor_a.setor.uo, inventario.cargas_contabeis.latest('id').campus)
            # É enviado um email para o servidor de origem e os coordenadores de patrimônio
            self.verificar_envio_email([self.servidor_a.email, self.servidor_d.email], '[SUAP] Patrimônio: Deferimento da Requisição de Transferência #%s' % requisicao.id)
        else:
            self.assertEqual(requisicao.status, Requisicao.STATUS_AGUARDANDO_APROVACAO_SERVIDOR_DESTINO)

        # Transferencia de inventarios do mesmo campus com transferencia da carga
        self.client.logout()
        self.client.login(username=self.servidor_b.user.username, password='123')
        qtd_requisicoes = Requisicao.objects.count()
        response = self.client.post(
            '/patrimonio/requisitar_transferencia/',
            {'servidor_origem': self.servidor_b.pk, 'servidor_destino': self.servidor_d.pk, 'tipo_transferencia': RequisicaoTransferenciaForm.TIPO_TRANSFERENCIA_CARGA},
            follow=True,
        )

        self.assertEqual(qtd_requisicoes + 1, Requisicao.objects.count())
        self.assertContains(response, 'Requisição de transferência de patrimônio efetuada com sucesso', status_code=200)
        # É enviado um email para o servidor de destino avisando da criação
        self.verificar_envio_email([self.servidor_d.email], '[SUAP] Patrimônio: Envio de Requisição de Transferência')
        requisicao = Requisicao.objects.latest('id')
        # Como foi transferência de carga todos os inventários devem estar na requisição
        self.assertFalse(self.servidor_b.get_vinculo().inventario_set.exclude(id__in=Inventario.objects.filter(requisicaoitem__requisicao=requisicao)).exists())

        self.client.logout()
        self.client.login(username=self.servidor_d.user.username, password='123')

        qtd_carga_contabeis = inventario.cargas_contabeis.count()
        carga_contabil = inventario.cargas_contabeis.latest('id')
        # Aprova transferência de todos os inventários
        response = self.client.post('/patrimonio/detalhar_requisicao/%d/' % requisicao.pk, {'itens': requisicao.itens.values_list('id', flat=True)})
        response = self.client.post('/patrimonio/indeferir_requisicao/%s/' % requisicao.pk, {'observacao': 'batata'})

        requisicao = Requisicao.objects.latest('id')
        # Após deferida muda o status
        self.assertEqual(requisicao.status, Requisicao.STATUS_INDEFERIDA)
        # É enviado um email para o servidor de origem
        self.verificar_envio_email([self.servidor_b.email], '[SUAP] Patrimônio: Indeferimento da Requisição de Transferência #%s' % requisicao.id)

    def test_baixa(self):
        """
        Testa a baixa de inventários
        """

        # Efetuar carga
        self.test_carga()

        qtd_baixa = Baixa.objects.count()
        # Verificando se a baixa foi cadastrada
        self.assertEqual(qtd_baixa, 0)

        # Verifica acesso à página
        url = '/admin/patrimonio/baixa/add/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Cadastrando uma baixa que conterá os itens baixados
        response = self.client.post(
            '/admin/patrimonio/baixa/add/',
            {
                'data': '23/09/2011',
                'data_time': ' 08:00:00',
                'tipo': BaixaTipo.objects.all()[0].pk,
                'uo': self.campus_a_suap.pk,
                'numero': '123',
                'observacao': 'cadastro de baixa',
            },
        )
        # Verificando se a baixa foi cadastrada
        self.assertEqual(Baixa.objects.count(), qtd_baixa + 1)

        baixa = Baixa.objects.all()[0].pk

        response = self.client.get('/patrimonio/baixa/%s/#' % baixa)
        self.assertContains(response, 'Baixar Novo Inventário', status_code=200)

        invs = Inventario.ativos_gerenciaveis.filter(responsavel_vinculo=self.servidor_c.get_vinculo().pk)[:10]

        # Adicionando inventários para a baixa
        self.client.post('/patrimonio/baixa/%s/#' % baixa, dict(tipo_baixa='inventario', inventario=[i.id for i in invs]))
        for i in invs:
            self.assertEqual(i.status, InventarioStatus.BAIXADO())
            self.assertEqual(i.responsavel_vinculo, None)

    def test_relatorio_termos_responsabilidade(self):
        """
        Testa o relatório de termos
        """
        # Tipo de Termo: Responsabilidade
        # Testar que servidor não tem  nada para exibir
        url = '/patrimonio/termos/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {'servidor': self.servidor_b.id, 'tipo': 'responsabilidade'}, follow=True)

        self.assertContains(response, 'Nenhum inventário a ser exibido.', status_code=200)

        # Adicionar carga
        self.test_carga()

        response = self.client.get('/patrimonio/termos/', {'servidor': self.servidor_b.id, 'tipo': 'responsabilidade'})

        # Testar que o servidor tem algo a exibir
        self.assertContains(response, 'Material permanente', status_code=200)

    def test_relatorio_termos_recebimento(self):
        """
        Testa o relatório do Termo de Recebimento
        """
        # Tipo de Termo: Recebimento
        # Testar que servidor não tem  nada para exibir
        url = '/patrimonio/termos/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            url,
            {
                'servidor': self.servidor_b.id,
                'tipo': 'recebimento',
                'periodo_de_movimento_ini': '01/01/2000',
                'periodo_de_movimento_fim': '18/12/%s' % (datetime.date.today().year + 1),
            },
            follow=True,
        )

        self.assertContains(response, 'Nenhum inventário a ser exibido.', status_code=200)

        # Adicionar carga
        self.test_carga()

        response = self.client.get(
            '/patrimonio/termos/',
            {
                'servidor': self.servidor_b.id,
                'tipo': 'recebimento',
                'periodo_de_movimento_ini': '01/01/2000',
                'periodo_de_movimento_fim': '18/12/%s' % (datetime.date.today().year + 1),
            },
        )

        # Testar que o servidor tem algo a exibir
        self.assertContains(response, 'Material permanente', status_code=200)

    def test_relatorio_nada_consta(self):
        """
        Testa se o nada consta não pode ser emitido para servidores com carga
        Servidores desligados ou remanejados
        """
        url = '/patrimonio/termos/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(url, {'servidor': self.servidor_b.id, 'tipo': 'nada_consta_desligamento'}, follow=True)
        response = response.get('Content-type')
        self.assertEqual(response, 'application/pdf')

        # Adicionar carga
        self.test_carga()

        response = self.client.get(url, {'servidor': self.servidor_b.id, 'tipo': 'nada_consta_desligamento'}, follow=True)

        # Testar que o servidor não pode emitir o nada consta,pois possui carga
        self.assertContains(response, 'Não é possível emitir nada consta, pois servidor tem carga.', status_code=200)

    def deferir_requisicao(self, requisicao):
        # Aprova transferência de todos os inventários
        self.client.post('/patrimonio/detalhar_requisicao/%d/' % requisicao.id, {'itens': requisicao.itens.values_list('id', flat=True)})

        # recuperando a sala e o predio do campus que a servidor destino está lotada
        predio = Predio.objects.get(uo=requisicao.vinculo_destino.setor.uo)
        sala = Sala.objects.get(predio=predio)
        return self.client.post('/patrimonio/deferir_requisicao/%s/' % requisicao.id, {'predio': predio.id, 'sala': sala.id})


class RequisicaoTransferenciaPatrimonialTestCase(PatrimonioTestCase):
    def setUp(self):
        super().setUp()

    def get_dados(self, **params):
        dados = dict(
            servidor_origem=self.servidor_b.id, servidor_destino=self.servidor_a.id, tipo_transferencia=RequisicaoTransferenciaForm.TIPO_TRANSFERENCIA_CARGA, inventarios=[]
        )
        dados.update(params)
        return dados

    def criar_inventarios(self):
        """
        Testa o cadastro de empenho de material permanente
        """
        # Criando um processo
        self.processo = Processo.objects.create(vinculo_cadastro=self.servidor_a.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_a.setor)

        # Acessando a página de cadastro
        self.client.post(
            '/admin/almoxarifado/empenho/add/',
            dict(
                numero='1423NE162534',
                processo=self.processo.pk,
                tipo_material=MaterialTipo.PERMANENTE().pk,
                tipo_pessoa=EmpenhoForm.TIPO_PESSOA_JURIDICA,
                pessoa_juridica=self.pessoa_juridica.get_vinculo().pk,
            ),
        )

        # Obtendo o empenho
        empenho = Empenho.objects.latest('id')
        # Cadastrando itens do empenho
        # Testando acesso à página de cadastramento de itens de empenho
        # Cadastrando itens para o empenho
        self.client.post('/almoxarifado/empenho/%s/' % empenho.pk, {'categoria': self.ed_01.pk, 'descricao': 'Material permanente 01', 'qtd_empenhada': '100', 'valor': '100,00'})

        self.client.post('/almoxarifado/empenho/%s/' % empenho.pk, {'categoria': self.ed_01.pk, 'descricao': 'Material permanente 02', 'qtd_empenhada': '50', 'valor': '100,00'})
        """
        Testa o cadastro de uma entrada do tipo compra
        """
        # Verificando se empenho foi cadastrado
        empenho = Empenho.objects.latest('id')
        EmpenhoPermanente.get_pendentes(empenho)

        # Dando o get para ver o form
        url = '/almoxarifado/entrada_compra/'
        response = self.client.get(url)
        self.client.post(
            '/almoxarifado/entrada_realizar/',
            {
                'csrfmiddlewaretoken': '%s' % response.context['csrf_token'],
                'data_entrada': '01/01/2012',
                'empenho_hidden': empenho.pk,
                'fornecedor_hidden': self.pessoa_juridica.get_vinculo().pk,
                'numero_nota': '001',
                'data_nota': '01/01/2012',
                'empenho_itens': [empenho.empenhopermanente_set.order_by("id")[0].pk, empenho.empenhopermanente_set.order_by("id")[1].pk],
                'qtds': [50, 50],
            },
        )

    def dar_carga_para_o_servidor(self, servidor):
        requisicao = self.criar_requisicao(servidor)
        self.deferir_requisicao_do_usuario(requisicao)

    def criar_requisicao(self, servidor):
        inventarios = Inventario.objects.filter(responsavel_vinculo__isnull=True)[:10]
        # Verifica acesso à página
        url = '/patrimonio/carga/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        qtd_requisicoes = Requisicao.objects.count()
        response = self.client.post(
            url, {'servidor_destino': servidor.pk, 'inventarios': [i.id for i in inventarios], 'estado_conservacao': Inventario.CONSERVACAO_BOM, 'sala': self.sala_b.pk}
        )
        self.assertEqual(qtd_requisicoes + 1, Requisicao.objects.count())
        return Requisicao.objects.latest('id')

    def deferir_requisicao_do_usuario(self, requisicao):
        user = self.client.user
        self.client.logout()
        self.client.login(user=requisicao.vinculo_destino.user)
        qtd_requisicoes = Requisicao.objects.filter(status=Requisicao.STATUS_DEFERIDA).count()
        if requisicao.ver_periodo_deferimento() is True:
            self.deferir_requisicao(requisicao)
            self.assertEqual(qtd_requisicoes + 1, Requisicao.objects.filter(status=Requisicao.STATUS_DEFERIDA).count())
            self.client.logout()
            self.client.login(user=user)

    def _test_requisitar_transferencia(self):
        """
        Requisitar transferencia de item da sua carga para outro servidor
        """
        perfis_corretos = [GRUPO_COORDENADOR_SISTEMICO, GRUPO_COORDENADOR_CAMPUS, GRUPO_OPERADOR_CAMPUS, GRUPO_SERVIDOR, GRUPO_CONTADOR]
        perfis_errados = []
        # Verificação do defaul que é a aba "qualquer"
        url = '/admin/patrimonio/requisicao/'
        self.verificar_perfil_status(url, perfis_corretos=perfis_corretos, perfis_errados=perfis_errados)

        url_cadastro = '/patrimonio/requisitar_transferencia/'
        self.verificar_perfil_status(url_cadastro, perfis_corretos=perfis_corretos, perfis_errados=perfis_errados)

        dados = self.get_dados()
        self.criar_inventarios()
        self.dar_carga_para_o_servidor(self.servidor_b)
        Requisicao.objects.all().delete()

        def modificou():
            requisicao = Requisicao.objects.latest('id')
            ids_inventarios_origem = list(requisicao.vinculo_origem.inventario_set.values_list('id', flat=True))
            return not requisicao.itens.exclude(inventario__id__in=ids_inventarios_origem).exists()

        def desmodificar():
            Requisicao.objects.all().delete()

        # testar criação de requisição de todos os inventários
        perfis_corretos = [GRUPO_COORDENADOR_SISTEMICO, GRUPO_COORDENADOR_CAMPUS, GRUPO_OPERADOR_CAMPUS, GRUPO_SERVIDOR, GRUPO_CONTADOR]
        perfis_errados = [GRUPO_AUTIDOR]
        self.verificar_perfil_submit(
            url_cadastro,
            dados,
            Requisicao.objects,
            perfis_corretos=perfis_corretos,
            perfis_errados=perfis_errados,
            after_submit=desmodificar,
            modificou=modificou,
            success_status_code=302,
        )

        # testar criação de requisição com servidor origem diferente do logado que TENHA permissão
        # testar criação de requisição com servidor origem diferente do logado que NÃO tenha permissão
        dados['servidor_origem'] = self.servidor_d.id
        self.dar_carga_para_o_servidor(self.servidor_d)
        Requisicao.objects.all().delete()
        perfis_corretos = [GRUPO_COORDENADOR_SISTEMICO, GRUPO_COORDENADOR_CAMPUS]
        perfis_errados = [GRUPO_OPERADOR_CAMPUS, GRUPO_SERVIDOR, GRUPO_CONTADOR, GRUPO_AUTIDOR]
        self.verificar_perfil_submit(
            url_cadastro,
            dados,
            Requisicao.objects,
            perfis_corretos=perfis_corretos,
            perfis_errados=perfis_errados,
            after_submit=desmodificar,
            success_status_code=302,
            error_status_code=[302, 200, 403],
        )

        # testar criação de requisição de inventário que NÃO esteja na carga
        dados['servidor_origem'] = self.servidor_b.id
        dados['inventarios'] = self.servidor_d.get_vinculo().inventario_set.values_list('id', flat=True)
        dados['tipo_transferencia'] = RequisicaoTransferenciaForm.TIPO_TRANSFERENCIA_INVENTARIOS
        perfis_corretos = []
        perfis_errados = [GRUPO_COORDENADOR_SISTEMICO, GRUPO_COORDENADOR_CAMPUS]
        self.verificar_perfil_submit(
            url_cadastro,
            dados,
            Requisicao.objects,
            perfis_corretos=perfis_corretos,
            perfis_errados=perfis_errados,
            after_submit=desmodificar,
            success_status_code=302,
            contains_text_perfis_errados="Pelo menos um dos itens não pertence ao servidor de origem. Por favor verifique e ajuste os itens.",
            verificar_sem_perfil=False,
        )
        # Não sei porque só funciona assim
        perfis_corretos = []
        perfis_errados = [GRUPO_OPERADOR_CAMPUS, GRUPO_SERVIDOR, GRUPO_CONTADOR, GRUPO_AUTIDOR]
        self.verificar_perfil_submit(
            url_cadastro,
            dados,
            Requisicao.objects,
            perfis_corretos=perfis_corretos,
            perfis_errados=perfis_errados,
            after_submit=desmodificar,
            success_status_code=302,
            contains_text_perfis_errados="Pelo menos um dos itens não pertence ao servidor de origem. Por favor verifique e ajuste os itens.",
            verificar_sem_perfil=False,
        )

        # testar criação de requisição de inventário que ESTEJA na carga
        dados['servidor_origem'] = self.servidor_b.id
        dados['inventarios'] = self.servidor_b.get_vinculo().inventario_set.values_list('id', flat=True)
        perfis_corretos = [GRUPO_COORDENADOR_SISTEMICO, GRUPO_COORDENADOR_CAMPUS, GRUPO_OPERADOR_CAMPUS, GRUPO_SERVIDOR, GRUPO_CONTADOR]
        perfis_errados = [GRUPO_AUTIDOR]
        self.verificar_perfil_submit(
            url_cadastro, dados, Requisicao.objects, perfis_corretos=perfis_corretos, perfis_errados=perfis_errados, after_submit=desmodificar, success_status_code=302
        )


def rel(request):
    from django.http import HttpResponse

    dados = dict(
        cabecalho=dict(orgao=Configuracao.get_valor_por_chave('comum', 'instituicao'), uo='Unidade Organizacional Alpha', setor='DRH - Diretoria de Recursos Humanos'),
        data='9 de Agosto de 2008',
        titulo='Termo de Responsabilidade',
        elementos=[
            '<b>Responsável:</b> Túlio de Paiva',
            {
                'cabecalhos': [
                    [{'valor': 'item', 'largura': 20, 'colspan': 2}],
                    [{'valor': 'id', 'largura': 10, 'colspan': 1, 'alinhamento': 'right'}, {'valor': 'nome', 'largura': 10, 'colspan': 1, 'alinhamento': 'left'}],
                ],
                'dados': [[1, 'bola de futebol']],
            },
        ],
        rodape='Estou ciente deste material em minha carga.',
        cidade='Natal',
        assinatura_1='Coordenação do Patrimônio',
        assinatura_2='Túlio de Paiva',
    )
    doc = RelatorioTermosPDF(dados)
    x = doc.montar()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename=relatorio.pdf'
    response.write(x)
    return response
