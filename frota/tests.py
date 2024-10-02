# -*- coding: utf-8 -*-

from decimal import Decimal
import datetime

from django.contrib.auth.models import Group
from django.apps import apps

from almoxarifado.models import MaterialTipo, EntradaTipo, Entrada
from comum.models import Municipio
from comum.tests import SuapTestCase
from estacionamento.models import VeiculoCombustivel, VeiculoCor, VeiculoEspecie, VeiculoMarca, VeiculoModelo, VeiculoTipo, VeiculoTipoEspecie
from frota.models import MotoristaTemporario, Viatura, Viagem, ViagemAgendamento, ViagemAgendamentoResposta, ViaturaGrupo, ViaturaStatus
from patrimonio.models import CategoriaMaterialPermanente, EntradaPermanente, Inventario, InventarioStatus
from rh.models import Setor, UnidadeOrganizacional, PessoaFisica, Servidor


Permission = apps.get_model('auth', 'permission')
User = apps.get_model('comum', 'user')


class FrotaTestCase(SuapTestCase):
    def setUp(self):
        super(FrotaTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Frota Sistêmico'))
        self.servidor_a.user.save()
        self.client.login(username=self.servidor_a.user.username, password='123')
        self.next_year = datetime.datetime.now().year + 1

    def test_cadastro_viatura(self):
        veiculomarca = VeiculoMarca.objects.get_or_create(nome='Ford')[0]
        veiculotipo = VeiculoTipo.objects.get_or_create(descricao='Utilitário')[0]
        veiculoespecie = VeiculoEspecie.objects.get_or_create(descricao='Comum')[0]
        veiculotipoespecie = VeiculoTipoEspecie.objects.get_or_create(tipo=veiculotipo, especie=veiculoespecie)[0]
        veiculomodelo = VeiculoModelo.objects.get_or_create(nome='Ranger', marca=veiculomarca, tipo_especie=veiculotipoespecie)[0]
        veiculocor = VeiculoCor.objects.get_or_create(nome='Branca')[0]
        municipio = Municipio.objects.get_or_create(nome='Natal', uf='RN', codigo='NAT')[0]
        viaturagrupo = ViaturaGrupo.objects.get_or_create(codigo='123', nome='Carro de Passeio', descricao='Carro para transporte de passageiro')[0]
        inventariostatus = InventarioStatus.objects.get_or_create(nome='Status')[0]
        setor = Setor.objects.get_or_create(sigla='DG/CNAT', nome='Campus Central')[0]
        unidadeorganizacional = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor)[0]
        entrada = Entrada.objects.get_or_create(data=datetime.datetime.now(), uo=unidadeorganizacional, tipo_entrada=EntradaTipo.DOACAO(), tipo_material=MaterialTipo.PERMANENTE())[
            0
        ]
        categoriamaterialpermanente = CategoriaMaterialPermanente.objects.get_or_create(codigo='0', nome='nome')[0]
        entradapermanente = EntradaPermanente.objects.get_or_create(entrada=entrada, categoria=categoriamaterialpermanente, descricao='descrição', qtd=1, valor=Decimal(10))[0]
        inventario = Inventario.objects.get_or_create(numero=0, status=inventariostatus, entrada_permanente=entradapermanente, campo_busca='0')[0]
        viaturastatus = ViaturaStatus.objects.get_or_create(descricao='Ativa')[0]
        veiculocombustivel = VeiculoCombustivel.objects.get_or_create(nome='Gasolina')[0]

        url = '/admin/frota/viatura/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Viatura', status_code=200)
        count = Viatura.objects.all().count()

        data = dict(
            modelo=veiculomodelo.pk,
            cor=veiculocor.pk,
            ano_fabric='2012',
            placa_municipio_atual=municipio.pk,
            placa_codigo_atual='MXY-0001',
            placa_municipio_anterior=municipio.pk,
            placa_codigo_anterior='MXY-0001',
            lotacao='10',
            odometro='1000',
            capacidade_tanque='150',
            capacidade_gnv='',
            chassi='11111111111111111',
            renavam='999999999',
            potencia='2',
            cilindrada='0',
            obs='Nenhuma observação',
            grupo=viaturagrupo.pk,
            patrimonio=inventario.pk,
            status=viaturastatus.pk,
            combustiveis=veiculocombustivel.pk,
            rendimento_estimado='9',
            ativo=True,
        )

        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(Viatura.objects.all().count(), count + 1)

    def test_cadastro_motoristatemporario(self):
        PessoaFisica.objects.get_or_create(nome='Carlos Breno Pereira Silva', defaults={'cpf': '359.221.769-00'})
        url = '/admin/frota/motoristatemporario/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Motorista Temporário', status_code=200)
        count = MotoristaTemporario.objects.all().count()
        data = dict(
            vinculo_pessoa=self.servidor_a.user.get_vinculo().pk,
            portaria='0',
            ano_portaria='2015',
            validade_inicial='01/02/2012',
            obs='Nenhuma observação cadastrada',
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(MotoristaTemporario.objects.all().count(), count + 1)

    def test_cadastro_viagemagendamento(self):
        funcionario = Servidor.objects.create(
            nome='Maria da Silva Santos',
            matricula='12',
            setor=SuapTestCase.dict_initial_data['setor_a1_suap'],
            template=b'12',
            cargo_emprego=SuapTestCase.dict_initial_data['cargo_emprego_b'],
            situacao=SuapTestCase.dict_initial_data['situacao_ativo_permanente'],
            email='servidor.a2@mail.gov',
            jornada_trabalho=SuapTestCase.dict_initial_data['jornada_trabalho'],
            cpf='549.220.264-28',
        )
        url = '/admin/frota/viagemagendamento/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Agendamento de Viagem', status_code=200)
        count = ViagemAgendamento.objects.all().count()
        data = dict(
            vinculo_solicitante=funcionario.get_vinculo().pk,
            objetivo='Apresentação dos módulos do suap',
            intinerario='Ida para Caicó por Currais Novos',
            data_saida='01/01/%s' % self.next_year,
            data_saida_time='08:00:00',
            data_chegada='10/01/%s' % self.next_year,
            data_chegada_time='08:00:00',
            vinculos_passageiros=self.servidor_a.user.get_vinculo().pk,
            local_saida='saindo do cnat',
            nome_responsavel='Nome do Responsável',
            telefone_responsavel='(84) 12346-7898',
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(ViagemAgendamento.objects.all().count(), count + 1)

    def test_cadastro_viagemagendamentoresposta(self):
        self.test_cadastro_viatura()
        viatura = Viatura.objects.filter(ativo=True)[0]
        self.test_cadastro_viagemagendamento()
        viagemagendamento = ViagemAgendamento.objects.all()[0]
        self.test_cadastro_motoristatemporario()
        motoristatemporario = MotoristaTemporario.objects.get(vinculo_pessoa__pessoa__nome='Servidor 1')

        url = '/frota/avaliar_agendamento_viagem/%d/' % viagemagendamento.pk
        response = self.client.get(url)
        self.assertContains(response, 'Avaliação de Agendamento', status_code=200)
        count = ViagemAgendamentoResposta.objects.all().count()
        data = dict(status='Deferida', vinculo_responsavel=self.prestador_1.get_vinculo().pk, viatura=viatura.pk, motoristas=motoristatemporario.vinculo_pessoa.pk, obs='Nenhuma observação', agendamento=viagemagendamento.pk)

        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(ViagemAgendamentoResposta.objects.all().count(), count + 1)

    def test_saida_viagem(self):
        self.test_cadastro_viagemagendamentoresposta()
        viagemagendamentoresposta = ViagemAgendamentoResposta.objects.all()[0]

        viatura = Viatura.objects.all()[0]
        motoristatemporario = MotoristaTemporario.objects.get(vinculo_pessoa__pessoa__nome='Servidor 1')
        url = '/frota/saida_viagem/%d/' % viagemagendamentoresposta.pk
        response = self.client.get(url)
        self.assertContains(response, 'Registrar Saída', status_code=200)
        count = Viagem.objects.all().count()
        data = dict(
            agendamento_resposta=viagemagendamentoresposta.pk,
            viatura=viatura.pk,
            motoristas=motoristatemporario.vinculo_pessoa.pk,
            saida_odometro='1000',
            saida_data='01/01/%s' % self.next_year,
            saida_data_time='08:00:00',
            saida_obs='',
            vinculos_passageiros=self.servidor_a.user.get_vinculo().pk,
        )
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(Viagem.objects.all().count(), count + 1)
        self.assertRedirects(response, '/frota/viagens_agendadas/', status_code=302)

    def test_chegada_viagem(self):

        self.test_saida_viagem()
        viagem = Viagem.objects.all()[0]

        url = '/frota/chegada_viagem/%d/' % viagem.pk
        response = self.client.get(url)
        self.assertContains(response, 'Formulário de Registro', status_code=200)
        count = Viagem.objects.filter(chegada_data__isnull=False).count()
        data = dict(chegada_odometro='1100', chegada_data='10/01/%s' % self.next_year, chegada_data_time='18:00:00')
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(Viagem.objects.filter(chegada_data__isnull=False).count(), count + 1)
        self.assertRedirects(response, '/frota/viagens_iniciadas/', status_code=302)
        # ...
