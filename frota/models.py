import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from django.utils import dateformat
from django.utils.safestring import mark_safe

from djtools.choices import Situacao
from djtools.db import models
from djtools.db.models import CurrentUserField
from djtools.templatetags.filters import in_group, mascara_dinheiro
from estacionamento.models import Veiculo, VeiculoCombustivel
from patrimonio.models import Inventario
from rh.models import Servidor, Setor


class ViaturaGrupo(models.ModelPlus):
    codigo = models.CharField(max_length=3, unique=True)
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.CharField(max_length=250, unique=True)

    class Meta:
        ordering = ['codigo', 'nome']
        verbose_name = 'Grupo da Viatura'
        verbose_name_plural = 'Grupos de Viaturas'

    def __str__(self):
        return self.nome


class ViaturaStatus(models.ModelPlus):
    descricao = models.CharField(max_length=15, unique=True)

    class Meta:
        ordering = ['descricao']
        verbose_name = 'Situação da Viatura'
        verbose_name_plural = 'Situações das Viaturas'

    def __str__(self):
        return self.descricao


class ViaturaManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset()


class ViaturaAtivasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)


class Viatura(Veiculo):
    grupo = models.ForeignKeyPlus(ViaturaGrupo, on_delete=models.CASCADE)
    patrimonio = models.ForeignKeyPlus(Inventario, on_delete=models.CASCADE, null=True)
    status = models.ForeignKeyPlus(ViaturaStatus, verbose_name='Situação', on_delete=models.CASCADE)
    ativo = models.BooleanField('Ativo', default=True)
    campus = models.ForeignKey('rh.UnidadeOrganizacional', verbose_name='Campus', on_delete=models.CASCADE, null=True)
    propria_instituicao = models.BooleanField('Pertence à Instituição', default=True)
    data_proxima_revisao = models.DateField('Data da Próxima Revisão', null=True)

    objects = ViaturaManager()
    ativas = ViaturaAtivasManager()

    class Meta:
        ordering = ['placa_codigo_atual', 'modelo']
        verbose_name = 'Viatura'
        verbose_name_plural = 'Viaturas'
        permissions = (
            ("tem_acesso_viatura_sistemico", "Tem acesso sistêmico as viaturas"),
            ("tem_acesso_viatura_campus", "Tem acesso por campus as viaturas"),
            ("tem_acesso_viatura_operador", "Tem acesso de operador as viaturas"),
        )

    def __str__(self):
        return '{} {}'.format(self.placa_codigo_atual, self.modelo)

    def get_uo(self):
        try:
            return self.campus.sigla
        except Exception:
            return '(Nenhum)'

    def get_responsavel(self):
        try:
            return self.patrimonio.responsavel.nome
        except Exception:
            return '-'

    def get_absolute_url(self):
        return '/frota/viatura/{}/'.format(self.id)

    def get_status(self):
        status = self.status
        if status == 'Disponível':
            return '<span class="status status-success">Disponível</span>'
        elif status == 'Em Trânsito':
            return '<span class="status status-alert">Em trânsito</span>'
        return status

    def get_combustiveis(self):
        combustiveis = ''
        for i, c in enumerate(self.combustiveis.all()):
            if i == 0:
                combustiveis += '{}'.format(c.nome)
            else:
                combustiveis += ' / {}'.format(c.nome)
        return mark_safe(combustiveis)

    get_combustiveis.short_description = 'Combustíveis'

    def get_ultima_revisao(self):
        if ManutencaoViatura.objects.filter(viatura=self, tipo_servico=ManutencaoViatura.MANUTENCAO_PERIODICA).exists():
            return ManutencaoViatura.objects.filter(viatura=self, tipo_servico=ManutencaoViatura.MANUTENCAO_PERIODICA).order_by('-data')[0]
        return False

    def get_data_ultima_revisao(self):
        ultima_revisao = self.get_ultima_revisao()
        return ultima_revisao and ultima_revisao.data

    def get_data_proxima_revisao(self):
        if self.data_proxima_revisao:
            return self.data_proxima_revisao
        ultima_data = self.get_data_ultima_revisao()
        if ultima_data:
            return ultima_data + relativedelta(months=+12)
        return False

    def tem_revisao_prevista(self):
        data_proxima = self.get_data_proxima_revisao()
        hoje = datetime.datetime.now().date()
        return data_proxima and data_proxima > hoje and data_proxima <= (hoje + relativedelta(days=+30))

    def tem_revisao_atraso(self):
        data_proxima = self.get_data_proxima_revisao()
        hoje = datetime.datetime.now().date()
        return data_proxima and data_proxima < hoje

    def tem_odometro_perto_10k(self):
        ultima_revisao = self.get_ultima_revisao()
        return ultima_revisao and self.odometro > (ultima_revisao.odometro + 9000) and self.odometro < (ultima_revisao.odometro + 10000)

    def get_odometro_ultima_revisao(self):
        ultima_revisao = self.get_ultima_revisao()
        return ultima_revisao and ultima_revisao.odometro


class MotoristaTemporario(models.ModelPlus):
    SEARCH_FIELDS = ['vinculo_pessoa__pessoa__nome']

    SERVIDOR = '1'
    TERCEIRIZADO = '2'
    CATEGORIA_CHOICES = ((SERVIDOR, 'Servidor'), (TERCEIRIZADO, 'Terceirizado'))

    TODOS = '1'
    DISPONIVEL = '2'
    EM_VIAGEM = '3'
    DISPONIBILIDADE_CHOICES = ((TODOS, 'Todos'), (DISPONIVEL, 'Disponíveis'), (EM_VIAGEM, 'Em Viagem'))

    vinculo_pessoa = models.ForeignKey('comum.Vinculo', on_delete=models.CASCADE, null=True)
    portaria = models.CharField(max_length=20, null=True, blank=True)
    ano_portaria = models.IntegerField(null=True, blank=True)
    validade_inicial = models.DateField('Data de Início')
    validade_final = models.DateField('Data Limite', null=True)
    obs = models.TextField('Observações', null=True, blank=True)
    arquivo = models.FileFieldPlus(max_length=255, upload_to='upload/frota/portarias/', null=True, blank=True)

    class Meta:
        ordering = ['vinculo_pessoa__pessoa__nome']
        verbose_name = 'Motorista Temporário'
        verbose_name_plural = 'Motoristas Temporários'

        unique_together = ('vinculo_pessoa', 'portaria')

    def __str__(self):
        return '{} ({})'.format(self.vinculo_pessoa.pessoa.nome, self.vinculo_pessoa.pessoa.pessoafisica.cpf)

    def is_servidor(self):
        return Servidor.objects.filter(vinculos=self.vinculo_pessoa).exists()

    def get_matricula_servidor(self):
        return Servidor.objects.get(vinculos=self.vinculo_pessoa).matricula

    def get_portarias(self):
        mostra_portarias = '<table><thead><tr><th>Portaria</th><th>Data Inicial</th><th>Data Final</th><th class="no-print">Opções</th></tr></thead><tbody>'
        registros = MotoristaTemporario.objects.filter(vinculo_pessoa=self.vinculo_pessoa).order_by('-validade_final')
        for registro in registros:
            if registro.arquivo:
                mostra_portarias = mostra_portarias + '<tr><td><a href="{}">{}</td><td>{}</td>'.format(
                    registro.arquivo.url, registro.portaria, dateformat.format(registro.validade_inicial, 'd/m/Y')
                )
            else:
                mostra_portarias = mostra_portarias + '<tr><td>{}</td><td>{}</td>'.format(registro.portaria, dateformat.format(registro.validade_inicial, 'd/m/Y'))

            if registro.validade_final:
                mostra_portarias = mostra_portarias + '<td>{}</td>'.format(dateformat.format(registro.validade_final, 'd/m/Y'))
            else:
                mostra_portarias = mostra_portarias + '<td>-</td>'

            mostra_portarias = mostra_portarias + '<td class="no-print"><a href="/admin/frota/motoristatemporario/{}/" class="primary btn">Editar</a></td></tr>'.format(registro.id)
        mostra_portarias = mostra_portarias + '</tbody></table>'

        return str(mostra_portarias)

    def portaria_mais_recente(self):
        registros = MotoristaTemporario.objects.filter(vinculo_pessoa=self.vinculo_pessoa).order_by('-validade_final')
        if registros.exists():
            return registros[0]

    def situacao(self):
        hoje = datetime.datetime.now()

        if Viagem.objects.filter(saida_data__lte=hoje, chegada_data__gte=hoje, motoristas=self.vinculo_pessoa).exists():
            return "<a href='/frota/viagem/{}/' class='btn'>Em Viagem</a>".format(
                Viagem.objects.filter(saida_data__lte=hoje, chegada_data__gte=hoje, motoristas=self.vinculo_pessoa)[0].id
            )
        else:
            return "<span class='status status-info'>Disponível</span>"


class ViagemAgendamento(models.ModelPlus):
    status = models.CharField('Situação', max_length=30, choices=Situacao.get_choices())
    vinculo_solicitante = models.ForeignKey('comum.Vinculo', on_delete=models.CASCADE, null=True, help_text='Pessoa solicitante da viagem; não necessariamente será passageiro.')
    objetivo = models.TextField()
    intinerario = models.TextField('Itinerário', null=False)
    data_saida = models.DateTimeField('Saída')
    data_chegada = models.DateTimeField('Chegada')
    setor = models.ForeignKeyPlus(Setor, null=True, blank=True, on_delete=models.CASCADE)
    vinculos_passageiros = models.ManyToManyField(
        'comum.Vinculo', related_name='vinculos_passageiros_agendamento_set', help_text='Caso o solicitante seja passageiro, ele deve ser especificado neste campo'
    )
    data_solicitacao = models.DateTimeField('Data da Solicitação', auto_now_add=True, editable=False)
    autor = CurrentUserField(null=True)
    local_saida = models.CharField(verbose_name='Local de Saída da Viatura', null=True, blank=True, max_length=500)
    quantidade_diarias = models.DecimalFieldPlus('Quantidade de Diárias', null=True, blank=True)
    vinculos_interessados = models.ManyToManyField('comum.Vinculo', related_name='vinculos_interessados_agendamento_set')
    nome_responsavel = models.CharFieldPlus('Nome do Responsável', help_text='Informe o nome da pessoa a ser contactada em caso de necessidade.', null=True, blank=True)
    telefone_responsavel = models.BrTelefoneField(
        'Telefone do Responsável', blank=True, max_length=15, help_text='Informe o telefone da pessoa a ser contactada em caso de necessidade.'
    )

    avaliado_por = models.ForeignKey(Servidor, null=True, related_name='frota_avaliador', on_delete=models.CASCADE)
    avaliado_em = models.DateTimeFieldPlus(null=True)
    aprovado = models.BooleanField('Aprovado', default=False)
    arquivo = models.FileFieldPlus('Documento de Comprovação', max_length=255, upload_to='upload/frota/comprovante_agendamento/', null=True, blank=True)

    class Meta:
        verbose_name = 'Agendamento de Viagem'
        verbose_name_plural = 'Agendamentos de Viagens'

        permissions = (
            ("pode_editar_mesmo_deferida", "Pode editar mesmo após deferimento"),
            ("tem_acesso_agendamento_sistemico", "Tem acesso sistêmico aos agendamentos"),
            ("tem_acesso_agendamento_campus", "Tem acesso por campus aos agendamentos"),
            ("tem_acesso_agendamento_operador", "Tem acesso de operador aos agendamentos"),
            ("tem_acesso_agendamento_agendador", "Tem acesso de agendador aos agendamentos"),
        )

    def __str__(self):
        return '#{}'.format(self.id)

    def get_absolute_url(self):
        return '/frota/agendamento/{}/'.format(self.id)

    def save(self, *args, **kwargs):
        if self.id is None:
            if not self.status:
                self.status = Situacao.PENDENTE
        self.setor = self.vinculo_solicitante.setor
        super().save(*args, **kwargs)

    def is_fora_do_prazo(self):
        return self.status == Situacao.PENDENTE and self.data_saida < datetime.datetime.now()

    def is_pendente(self):
        return self.status == Situacao.PENDENTE and not self.is_fora_do_prazo()

    def is_deferido(self):
        return self.status == Situacao.DEFERIDA

    def is_indeferido(self):
        return self.status == Situacao.INDEFERIDA

    def get_situacao(self, user):

        if self.is_fora_do_prazo():
            return '<span class="status status-error">Fora do Prazo</span>'
        elif not self.aprovado and self.avaliado_em:
            return '<span class="status status-error">Não Autorizado</span>'
        elif self.is_pendente():
            if in_group(user, ['Coordenador de Frota Sistêmico', 'Coordenador de Frota']):
                return '<a href="/frota/avaliar_agendamento_viagem/{}/" class="btn success">Avaliar</a>'.format(self.pk)
            return '<span class="status status-alert">Aguardando avaliação</span>'

        else:
            if self.is_deferido():
                return '<span class="status status-success">Deferido</span>'
            return '<span class="status status-error">Indeferido</span>'

    def get_autorizado(self, user):
        if not self.avaliado_em:
            if self.data_saida < datetime.datetime.now():
                return '<span class="status status-error">Fora do Prazo</span>'
            vinculo = user.get_vinculo()
            if vinculo.eh_servidor() and user.get_relacionamento().eh_chefe_do_setor_hoje(self.setor):
                return '''<ul class="action-bar">
                        <li><a class="btn success"  href="/frota/agendamento/{}/">Avaliar</a></li>
                        </ul>'''.format(
                    self.id
                )
            else:
                return '<span class="status status-alert">Aguardando</span>'
        else:
            if self.aprovado:
                return '<span class="status status-success">Sim</span>'
            return '<span class="status status-error">Não</span>'

    def viagem_finalizada(self):
        if self.viagemagendamentoresposta.viagem_set.exists():
            return self.viagemagendamentoresposta.viagem_set.all()[0].chegada_data
        return False

    def viagem_em_andamento(self):
        return self.viagemagendamentoresposta.viagem_set.exists()

    def get_dia_todo_list(self):
        dia_todo = []
        dias = (self.data_chegada - self.data_saida).days
        if dias == 1:
            dia_todo.append(self.data_saida + datetime.timedelta(1))
        else:
            for dia in range(1, dias):
                dia_todo.append(self.data_saida + datetime.timedelta(dia))

        return dia_todo

    def can_change(self, user):
        return user.has_perm('frota.tem_acesso_viagem_sistemico') or user.has_perm('frota.tem_acesso_viagem_campus') or self.vinculo_solicitante == user.get_vinculo()


class ViagemAgendamentoResposta(models.ModelPlus):
    agendamento = models.OneToOneField(ViagemAgendamento, on_delete=models.CASCADE)
    vinculo_responsavel = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE, null=True, related_name='vinculo_responsavel_agendamentoresposta')
    data = models.DateTimeField(verbose_name='Data')
    viatura = models.ForeignKeyPlus(Viatura, null=True, blank=True, on_delete=models.CASCADE)
    motoristas = models.ManyToManyFieldPlus('comum.Vinculo')
    obs = models.TextField(verbose_name='Observações', null=True, blank=True)
    data_avaliacao = models.DateTimeField(auto_now_add=True, editable=False)
    autor = CurrentUserField(null=True)

    class Meta:
        verbose_name = 'Resposta do Agendamento de Viagem'
        verbose_name_plural = 'Respostas dos Agendamentos de Viagens'

    def __str__(self):
        return '#{} - Solicitante: {}'.format(self.agendamento.id, self.agendamento.vinculo_solicitante.pessoa.nome)

    def get_motoristas(self):
        string = ''
        for motorista in self.motoristas.all():
            string += motorista.pessoa.nome + ', '
        return string[:-2]


class ViaturaOrdemAbastecimento(models.ModelPlus):
    viatura = models.ForeignKeyPlus(Viatura, on_delete=models.CASCADE)
    data = models.DateTimeField(verbose_name='Data')
    odometro = models.PositiveIntegerField('Odômetro', help_text='Quilometragem no momento do abastecimento', default=0)
    cupom_fiscal = models.CharField('Cupom Fiscal', max_length=10)
    combustivel = models.ForeignKeyPlus(VeiculoCombustivel, verbose_name='Combustível', on_delete=models.CASCADE)
    quantidade = models.DecimalFieldPlus()
    valor_unidade = models.DecimalFieldPlus('Valor da Unidade', null=True, blank=True)
    arquivo = models.FileFieldPlus(max_length=255, upload_to='upload/frota/nota_fiscal/', null=True, blank=True)
    valor_total_nf = models.DecimalFieldPlus('Valor Total da Nota Fiscal (R$)', default=Decimal("0.0"))

    class Meta:
        verbose_name = 'Ordem de Abastecimento de Viatura'
        verbose_name_plural = 'Ordens de Abastecimento de Viatura'

    def __str__(self):
        return 'Ordem de Abastecimento #{}'.format(self.pk)

    def get_valor_total(self, numerico=False):
        retorno = '0.00'
        if self.quantidade and self.valor_unidade:
            valor_total = self.quantidade * self.valor_unidade
            retorno = '{}.2f'.format(valor_total)
        return mark_safe(retorno)

    get_valor_total.short_description = 'Valor Total'

    def get_parcial(self):
        parcial = '0.00'
        if self.quantidade and self.valor_unidade:
            parcial = self.quantidade * self.valor_unidade
        return mascara_dinheiro('%0.2f' % parcial)

    def get_campus(self):
        return self.viatura.get_uo()


class Viagem(models.ModelPlus):
    agendamento_resposta = models.ForeignKeyPlus(ViagemAgendamentoResposta, on_delete=models.CASCADE)
    viatura = models.ForeignKeyPlus(Viatura, on_delete=models.CASCADE)
    motoristas = models.ManyToManyFieldPlus('comum.Vinculo')
    vinculos_passageiros = models.ManyToManyField('comum.Vinculo', related_name='vinculos_passageiros_set')

    saida_odometro = models.PositiveIntegerField()
    saida_data = models.DateTimeField('Data de Saída')
    saida_obs = models.TextField('Observações', null=True, blank=True)

    chegada_odometro = models.PositiveIntegerField(null=True, blank=True)
    chegada_data = models.DateTimeField('Data de Chegada', null=True, blank=True)
    chegada_obs = models.TextField('Observações', null=True, blank=True)

    data_cadastro = models.DateTimeField(auto_now_add=True, editable=False)
    autor = CurrentUserField(null=True)

    class Meta:
        ordering = ['saida_odometro']
        verbose_name = 'Viagem'
        verbose_name_plural = 'Viagens'
        permissions = (
            ("tem_acesso_viagem_sistemico", "Tem acesso sistêmico as viagens"),
            ("tem_acesso_viagem_campus", "Tem acesso por campus as viagens"),
            ("tem_acesso_viagem_operador", "Tem acesso de operador as viagens"),
            ("pode_cadastrar_viagem_retroativa", "Pode cadastrar viagem retroativa"),
            ("pode_gerenciar_viagem", "Pode registrar viagem"),
        )

    def get_absolute_url(self):
        return '/frota/viagem/{}/'.format(self.id)

    def __str__(self):
        return 'Viagem #{}'.format(self.agendamento_resposta.agendamento.id)

    def get_string_passageiros(self):
        nome = '<ul>'
        for item in self.vinculos_passageiros.all():
            nome = nome + '<li>' + item.pessoa.nome + '</li>'
        nome = nome + '</ul>'
        return nome

    def tem_descontinuidade(self):
        if self.chegada_data:
            viagem_seguinte = Viagem.objects.filter(viatura=self.viatura, saida_data__gte=self.chegada_data).order_by('saida_data')

            if viagem_seguinte.exists():
                if viagem_seguinte[0].saida_odometro != self.chegada_odometro:
                    return True

        return False

    def get_motoristas(self):
        string = ''
        for motorista in self.motoristas.all():
            string += motorista.pessoa.nome + ', '
        return string[:-2]

    def get_ordens_abastecimento(self):
        resultado = ViaturaOrdemAbastecimento.objects.filter(viatura=self.viatura, data__gte=self.saida_data)
        if self.chegada_data:
            resultado = resultado.filter(data__lte=self.chegada_data)
        return resultado


class ManutencaoViatura(models.ModelPlus):
    MANUTENCAO_PERIODICA = 'Manutenção Periódica'
    PROBLEMA_FUNCIONAMENTO = 'Problema de Funcionamento'
    ACIDENTE = 'Acidente'
    OUTRO = 'Outro'

    TIPO_SERVICO_CHOICES = ((MANUTENCAO_PERIODICA, 'Manutenção Periódica'), (PROBLEMA_FUNCIONAMENTO, 'Problema de Funcionamento'), (ACIDENTE, 'Acidente'), (OUTRO, 'Outro'))

    viatura = models.ForeignKeyPlus(Viatura, on_delete=models.CASCADE)
    data = models.DateField()
    odometro = models.PositiveIntegerField()
    tipo_servico = models.CharField('Tipo de Serviço', max_length=30, choices=TIPO_SERVICO_CHOICES)
    valor_total_pecas = models.DecimalFieldPlus('Valor Total da Nota Fiscal de Peças (R$)', default=Decimal("0.0"), null=True, blank=True)
    valor_total_servico = models.DecimalFieldPlus('Valor Total da Nota Fiscal de Serviços (R$)', default=Decimal("0.0"))
    arquivo_nf_pecas = models.FileFieldPlus(max_length=255, upload_to='upload/frota/notas_fiscais/', null=True, blank=True)
    arquivo_nf_servicos = models.FileFieldPlus(max_length=255, upload_to='upload/frota/notas_fiscais/', null=True, blank=True)
    obs = models.CharField('Observação', max_length=500)

    class Meta:
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'

    def __str__(self):
        return 'Serviço da Viatura %s' % self.viatura


class Maquina(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=500)
    patrimonio = models.ForeignKeyPlus(Inventario, verbose_name='Patrimônio', on_delete=models.CASCADE, null=True)
    combustiveis = models.ManyToManyField(VeiculoCombustivel)
    capacidade_tanque = models.PositiveSmallIntegerField(verbose_name='Capacidade do Tanque (em litros)', null=True, blank=True)
    consumo_anual_estimado = models.PositiveSmallIntegerField(verbose_name='Consumo Estimado por Ano (em litros)', null=True, blank=True)
    campus = models.ForeignKey('rh.UnidadeOrganizacional', on_delete=models.CASCADE, null=True, related_name='frota_maquina_campus')

    class Meta:
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'
        permissions = (
            ("tem_acesso_maquina_sistemico", "Tem acesso sistêmico as máquinas"),
            ("tem_acesso_maquina_campus", "Tem acesso por campus as máquinas"),
            ("tem_acesso_maquina_operador", "Tem acesso de operador as máquinas"),
        )

    def __str__(self):
        return self.descricao


class MaquinaOrdemAbastecimento(models.ModelPlus):
    maquina = models.ForeignKeyPlus(Maquina, verbose_name='Máquina', on_delete=models.CASCADE)
    data = models.DateField()
    cupom_fiscal = models.CharField('Cupom Fiscal', max_length=10)
    combustivel = models.ForeignKeyPlus(VeiculoCombustivel, verbose_name='Combustível', on_delete=models.CASCADE)
    quantidade = models.DecimalFieldPlus('Quantidade (em Litros)')
    valor_total_nf = models.DecimalFieldPlus('Valor Total da Nota Fiscal (R$)', default=Decimal("0.0"))
    arquivo_nf = models.FileFieldPlus('Arquivo da Nota Fiscal', max_length=255, upload_to='upload/frota/ordens_abastecimento/', null=True, blank=True)
    obs = models.CharField('Observação', max_length=500, null=True, blank=True)

    class Meta:
        verbose_name = 'Ordem de Abastecimento de Máquina'
        verbose_name_plural = 'Ordens de Abastecimentos de Máquina'

    def __str__(self):
        return 'Ordem de Abastecimento - %s' % self.maquina.descricao
