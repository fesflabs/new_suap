from datetime import date, datetime
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models.aggregates import Sum
from comum.utils import get_uo, somar_data
from djtools.db import models
from djtools.templatetags.filters import in_group
from rh.models import UnidadeOrganizacional, Setor, Servidor
from django.apps import apps
from comum.models import Vinculo
from django.core.exceptions import ValidationError


class Natureza(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=50)

    class Meta:
        verbose_name = 'Natureza de Eventos'
        verbose_name_plural = 'Naturezas de Eventos'

    def __str__(self):
        return self.descricao


class Dimensao(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=50)
    grupos_avaliadores_locais = models.ManyToManyFieldPlus('auth.Group', verbose_name='Grupos Avaliadores Locais', related_name='s1', blank=True)
    grupos_avaliadores_sistemicos = models.ManyToManyFieldPlus('auth.Group', verbose_name='Grupos Avaliadores Sistêmicos', related_name='s2', blank=True)

    class Meta:
        verbose_name = 'Dimensão'
        verbose_name_plural = 'Dimensões'

    def __str__(self):
        return self.descricao

    @classmethod
    def is_avaliador_sistemico(cls, user):
        grupos_avaliadores_sistemicos = cls.objects.values_list('grupos_avaliadores_sistemicos', flat=True)
        return user.groups.filter(pk__in=grupos_avaliadores_sistemicos).exists()

    @classmethod
    def is_avaliador_local(cls, user):
        grupos_avaliadores_locais = cls.objects.values_list('grupos_avaliadores_locais', flat=True)
        return user.groups.filter(pk__in=grupos_avaliadores_locais).exists()


class TipoEvento(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=50)

    class Meta:
        verbose_name = 'Tipo de Eventos'
        verbose_name_plural = 'Tipos de Eventos'

    def __str__(self):
        return self.descricao


class PorteEvento(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    detalhamento = models.TextField(verbose_name='Detalhamento')

    class Meta:
        verbose_name = 'Tipo de Atividade'
        verbose_name_plural = 'Tipos de Atividade'

    def __str__(self):
        return self.descricao


class SubtipoEvento(models.ModelPlus):
    tipo = models.ForeignKeyPlus(TipoEvento, verbose_name='Tipo')
    nome = models.CharField('Nome', max_length=50)
    detalhamento = models.TextField('Descrição')
    multiplas_atividades = models.BooleanField('Múltiplas Atividades', default=False)

    class Meta:
        verbose_name = 'Subtipo de Eventos'
        verbose_name_plural = 'Subtipos de Eventos'

    def __str__(self):
        return self.nome


class ClassificacaoEvento(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=50)
    detalhamento = models.TextField('Detalhamento', null=True, blank=True)

    class Meta:
        verbose_name = 'Classificação de Eventos'
        verbose_name_plural = 'Classificações de Eventos'

    def __str__(self):
        return self.descricao


class Espacialidade(models.ModelPlus):
    descricao = models.CharField('Descrição', max_length=50)

    class Meta:
        verbose_name = 'Espacialidade'
        verbose_name_plural = 'Espacialidades'

    def __str__(self):
        return self.descricao


class PublicoAlvoEvento(models.ModelPlus):

    ESTUDANTES = 1
    SERVIDORES = 2
    PAIS_E_RESPONSAVEIS = 3
    PUBLICO_EXTERNO = 4
    EMPRESARIOS = 5
    GESTORES = 6
    TERCEIRIZADOS = 7
    ESTAGIARIOS = 8
    BOLSISTAS = 9

    descricao = models.CharField('Descrição', max_length=50)

    class Meta:
        verbose_name = 'Público Alvo de Eventos'
        verbose_name_plural = 'Públicos Alvo de Eventos'

    def __str__(self):
        return self.descricao


class Evento(models.ModelPlus):
    nome = models.CharField(max_length=255, db_index=True)
    apresentacao = models.TextField('Apresentação', help_text='Espaço para que sejam falados os objetivos principais etc.')
    imagem = models.ImageFieldPlus('Imagem', blank=True, null=True, help_text="Logotipo ou algo que ilustre o evento")
    local = models.CharFieldPlus()
    data_inicio = models.DateFieldPlus('Data de Início')
    hora_inicio = models.TimeFieldPlus('Hora de Início')
    data_fim = models.DateFieldPlus('Data de Fim', null=True, blank=True)
    hora_fim = models.TimeFieldPlus('Hora de Fim', null=True, blank=True)
    data_inicio_inscricoes = models.DateFieldPlus('Início das Inscrições', null=True)
    hora_inicio_inscricoes = models.TimeFieldPlus('Hora de Início das Inscrições', null=True, blank=True)
    data_fim_inscricoes = models.DateFieldPlus('Fim das Inscrições', null=True)
    hora_fim_inscricoes = models.TimeFieldPlus('Hora de Fim das Inscrições', null=True, blank=True)
    carga_horaria_str = models.CharField('Carga Horária', null=True, blank=True, max_length=255, help_text='Carga-Horária total do evento')
    carga_horaria = models.IntegerField(verbose_name='Carga-Horária em segundos', null=True)
    coordenador = models.ForeignKeyPlus(Servidor, verbose_name='Coordenador', null=True, blank=True)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus do Coordenador', related_name='campus_responsavel', on_delete=models.CASCADE)
    setor = models.ForeignKeyPlus(Setor, verbose_name='Setor do Coordenador', null=True, blank=True, on_delete=models.CASCADE)
    natureza = models.ManyToManyField(Natureza, verbose_name='Natureza')
    dimensoes = models.ManyToManyField(Dimensao, verbose_name='Dimensões')
    classificacao = models.ForeignKeyPlus(ClassificacaoEvento, verbose_name='Localização', null=True, blank=True, on_delete=models.CASCADE)
    espacialidade = models.ForeignKeyPlus(Espacialidade, verbose_name='Espacialidade', null=True, blank=True, on_delete=models.CASCADE)
    porte = models.ForeignKeyPlus(PorteEvento, verbose_name='Porte', null=True)
    tipo = models.ForeignKeyPlus(TipoEvento, verbose_name='Tipo', null=True, on_delete=models.CASCADE)
    subtipo = models.ForeignKeyPlus(SubtipoEvento, verbose_name='Subtipo', null=True)
    servidores_envolvidos = models.PositiveIntegerField('Quantidade de Servidores Envolvidos na Organização', null=True, blank=True)
    qtd_participantes = models.PositiveIntegerField('Quantidade de Participantes', null=True, blank=True)
    publico_alvo = models.ManyToManyField(PublicoAlvoEvento, verbose_name='Público Alvo', blank=True)
    recursos = models.DecimalFieldPlus('Recursos Envolvidos', null=True, blank=True, help_text='Valor em R$ do total de recurso público destinado a realização do evento')
    site = models.CharFieldPlus(null=True, blank=True, verbose_name='Site', help_text='URL da página do evento')
    gera_certificado = models.BooleanField(
        'Gera Certificado?',
        blank=True,
        help_text='Marque essa opção caso deseje que certificados sejam emitidos e enviados por e-mail para os participantes após a realização do evento.',
    )
    submetido = models.BooleanField('Submetido?', default=True)
    deferido = models.BooleanField('Deferido?', null=True)
    motivo_indeferimento = models.TextField('Motivo do Indeferimento', null=True)
    data_emissao_certificado = models.DateTimeField(null=True, blank=True, verbose_name='Data de Emissão do Certificado')
    ativo = models.BooleanField('Ativo?', default=False)
    finalizado = models.BooleanField('Finalizado?', default=False)
    cancelado = models.BooleanField('Cancelado?', default=False)

    ultima_atualizacao_por = models.CurrentUserField()
    ultima_atualizacao_em = models.DateTimeFieldPlus(auto_now=True)

    inscricao_publica = models.BooleanField(
        verbose_name='Inscrição Online',
        default=False,
        help_text='Marque essa opção caso deseje que as inscrições sejam realizadas pelos próprios participantes através do link "Realizar Inscrição em Evento" na tela de login do SUAP.',
    )

    registrar_presenca_online = models.BooleanField(
        verbose_name='Registrar Presença Online',
        default=False,
        help_text='Marque essa opção caso deseje que os próprios inscritos possam registrar presença através de um e-mail enviado pelo coordenador/organizador.',
    )

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return f'/eventos/evento/{self.id}/'

    def save(self):
        if self.data_fim is None:
            self.data_fim = self.data_inicio
        super().save()

    def estah_em_periodo_realizacao(self):
        hoje = date.today()
        if self.hora_inicio and self.hora_fim:
            agora = datetime.now()
            data_hora_inicio = datetime.combine(self.data_inicio, self.hora_inicio)
            data_hora_fim = datetime.combine(self.data_fim, self.hora_fim)
            return data_hora_inicio <= agora <= data_hora_fim
        return self.data_inicio <= hoje <= self.data_fim

    def estah_realizado(self):
        hoje = date.today()
        if self.data_fim:
            if self.hora_fim:
                agora = datetime.now()
                data_hora_fim = datetime.combine(self.data_fim, self.hora_fim)
                return agora > data_hora_fim
            else:
                return hoje > self.data_fim
        elif hoje > self.data_inicio:
            return True
        return False

    def get_carga_horaria(self):
        return Participante.segundos_para_tempo(self.carga_horaria)

    def get_participacoes_inconsistentes(self):
        return self.participantes.filter(tipo__isnull=True)

    def get_programacao(self):
        programacao = []
        if self.data_inicio and self.data_fim:
            if self.data_fim >= self.data_inicio:
                dia = self.data_inicio
                while dia <= self.data_fim:
                    if self.atividadeevento_set.filter(data=dia).exists():
                        programacao.append((dia, self.atividadeevento_set.filter(data=dia).order_by('hora')))
                    dia = somar_data(dia, 1)
        return programacao

    def get_situacao(self):
        situacao = "Aguardando avaliação"
        if self.cancelado:
            situacao = "Cancelado"
        elif self.finalizado:
            situacao = "Finalizado"
        elif self.submetido and self.deferido is None:
            situacao = "Submetido"
        elif self.ativo:
            if self.deferido:
                situacao = "Deferido"
            else:
                situacao = "Ativo"
        elif not self.ativo:
            if not self.submetido and not self.deferido:
                situacao = "Devolvido"
            elif self.deferido:
                situacao = "Inativo"
            elif not self.deferido:
                situacao = "Indeferido"

        return situacao

    def get_url_inscricao(self):
        return self.inscricao_publica and f'{settings.SITE_URL}/eventos/inscricao_publica/{self.pk}/' or None

    def is_incricao_encerrada(self):
        hoje = date.today()
        if self.data_fim_inscricoes:
            if self.hora_fim_inscricoes:
                agora = datetime.now()
                data_hora_fim_inscricoes = datetime.combine(self.data_fim_inscricoes, self.hora_fim_inscricoes)
                return agora > data_hora_fim_inscricoes
            return hoje > self.data_fim_inscricoes
        return True

    def is_periodo_inscricao(self):
        hoje = date.today()
        if self.data_inicio_inscricoes and self.data_fim_inscricoes:
            if self.hora_inicio_inscricoes and self.hora_fim_inscricoes:
                agora = datetime.now()
                data_hora_inicio_inscricoes = datetime.combine(self.data_inicio_inscricoes, self.hora_inicio_inscricoes)
                data_hora_fim_inscricoes = datetime.combine(self.data_fim_inscricoes, self.hora_fim_inscricoes)
                return data_hora_inicio_inscricoes <= agora <= data_hora_fim_inscricoes
            return self.data_inicio_inscricoes <= hoje <= self.data_fim_inscricoes
        return True

    def pode_avaliar(self, user):
        grupos_avaliadores_sistemicos = self.dimensoes.values_list('grupos_avaliadores_sistemicos', flat=True)
        is_avaliador_sistemico = user.groups.filter(pk__in=grupos_avaliadores_sistemicos).exists()
        grupos_avaliadores_locais = self.dimensoes.values_list('grupos_avaliadores_locais', flat=True)
        is_avaliador_local = user.groups.filter(pk__in=grupos_avaliadores_locais).exists()
        return (is_avaliador_local and self.campus == user.get_vinculo().setor.uo) or is_avaliador_sistemico

    def pode_finalizar(self, user):
        return (self.pode_gerenciar(user) and self.ativo and self.submetido and self.deferido and not self.finalizado and self.estah_realizado())

    def pode_gerenciar(self, user):
        if in_group(user, 'Coordenador de Comunicação Sistêmico'):
            return True
        if in_group(user, 'Coordenador de Comunicação') and self.campus == get_uo(user):
            return True
        if not self.deferido:  # Impede que um evento indeferido possa ser editado pelo responsavel
            return False
        return (
            self.coordenador_id == user.get_vinculo().pessoa_id
            or Participante.objects.filter(evento=self.pk, tipo__tipo_participacao__descricao='Organizador', cpf=user.get_vinculo().pessoa.pessoafisica.cpf).exists()
        )

    def pode_enviar_certificado(self):
        return (self.subtipo and self.subtipo.multiplas_atividades) or self.carga_horaria

    def tem_vagas_disponiveis(self):
        tipo_participacao = TipoParticipacao.objects.get(descricao='Participante')
        tipo_participante = TipoParticipante.objects.filter(evento=self, tipo_participacao=tipo_participacao).first()
        if not tipo_participante:
            return False
        qtd_disponiveis_tipo_participante = tipo_participante.get_qtd_vagas_disponiveis()
        if qtd_disponiveis_tipo_participante is not None:
            return qtd_disponiveis_tipo_participante > 0

        if qtd_disponiveis_tipo_participante is None and not self.atividadeevento_set.exists():
            return True

        for atividadeevento in self.atividadeevento_set.all():
            qtd_disponiveis = atividadeevento.get_qtd_vagas_disponiveis()
            if qtd_disponiveis is None:
                return True
            else:
                if qtd_disponiveis > 0:
                    return True
        return False

    @transaction.atomic
    def submeter(self, user):
        self.submetido = True
        self.deferido = None
        self.ativo = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Submeteu o evento', user=user)

    @transaction.atomic
    def deferir(self, user):
        self.deferido = True
        self.ativo = True
        self.finalizado = False
        self.motivo_indeferimento = ''
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Deferiu o evento', user=user)

    @transaction.atomic
    def indeferir(self, motivo_indeferimento, user):
        self.motivo_indeferimento = motivo_indeferimento
        self.deferido = False
        self.ativo = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Indeferiu o evento', user=user)

    @transaction.atomic
    def ativar(self, justificativa, user):
        self.ativo = True
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao=f'Ativou o evento alegando: {justificativa}', user=user)

    @transaction.atomic
    def suspender(self, justificativa, user):
        self.ativo = False
        self.finalizado = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao=f'Suspendeu o evento alegando: {justificativa}', user=user)

    @transaction.atomic
    def cancelar_avaliacao(self, user):
        self.deferido = None
        self.ativo = False
        self.finalizado = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Cancelou a avaliação do evento', user=user)

    @transaction.atomic
    def devolver(self, justificativa, user):
        self.submetido = False
        self.ativo = False
        self.finalizado = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao=f'Devolveu o evento alegando: {justificativa}', user=user)

    @transaction.atomic
    def finalizar(self, user):
        self.finalizado = True
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Finalizou o evento', user=user)

    @transaction.atomic
    def cancelar(self, user):
        self.cancelado = True
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Cancelou o evento', user=user)

    @transaction.atomic
    def desfazer_cancelamento(self, user):
        self.cancelado = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Desfez cancelamento do evento', user=user)

    @transaction.atomic
    def desfazer_finalizacao(self, user):
        self.finalizado = False
        self.save()
        HistoricoEvento.objects.create(evento=self, descricao='Desfez finalização do evento', user=user)

    def finalizar_automaticamente(self):
        self.finalizado = True
        self.save()


class HistoricoEvento(models.ModelPlus):
    evento = models.ForeignKeyPlus(Evento)
    data = models.DateTimeField(auto_now_add=True, verbose_name='Data')
    user = models.ForeignKeyPlus(settings.AUTH_USER_MODEL, verbose_name='Usuário')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Histórico de Evento'
        verbose_name_plural = 'Históricos de Evento'

    def __str__(self):
        return self.descricao


class TipoParticipacao(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    modelo_certificado_padrao = models.FileFieldPlus(
        upload_to='eventos/modelo_certificado/',
        null=True,
        blank=True,
        verbose_name='Modelo de Certificado Padrão',
        filetypes=['docx'],
        help_text='O arquivo de modelo deve ser um arquivo .docx contendo as marcações #INSTITUICAO#, '
                  '#NOMEDOPARTICIPANTE#, #TIPODOPARTICIPANTE#, #TIPOPARTICIPACAO#, #PARTICIPANTE#, #CPF#, '
                  '#NOMEDOEVENTO#, #EVENTO#, #ATIVIDADES#, #LOCAL#, #CAMPUS#, #CARGAHORARIA#, '
                  '#DATAINICIALADATAFINAL#, #PERIODOREALIZACAO#, #SETORRESPONSAVEL#, #CIDADE#, #UF#, #DATAEMISSAO#, '
                  '#DATA#, #CODIGOVERIFICADOR#.',
    )
    ch_organizacao = models.BooleanField('Carga Horária de Organização', help_text='Adicional de 20% da carga horária total do evento', default=False)

    class Meta:
        verbose_name = 'Tipo de Participação'
        verbose_name_plural = 'Tipos de Participações'

    def get_modelo_certificado_padrao(self):
        modelo_certificado_padrao = self.modelo_certificado_padrao
        if not modelo_certificado_padrao:
            modelo_certificado_padrao = (
                TipoParticipacao.objects.filter(modelo_certificado_padrao__isnull=False).exclude(modelo_certificado_padrao='').latest('id').modelo_certificado_padrao
            )
        return modelo_certificado_padrao


class TipoParticipante(models.ModelPlus):
    SEARCH_FIELDS = ['tipo_participacao__descricao']
    evento = models.ForeignKeyPlus(Evento, related_name='tipos_participante')
    tipo_participacao = models.ForeignKeyPlus(TipoParticipacao, related_name='tipos_participante', verbose_name='Tipo de Participação')
    limite_inscricoes = models.IntegerField(verbose_name='Limite de Inscrições', null=True, blank=True)
    modelo_certificado = models.FileFieldPlus(
        upload_to='eventos/modelo_certificado/',
        null=True,
        blank=True,
        verbose_name='Modelo de Certificado',
        filetypes=['docx'],
        help_text='O arquivo de modelo deve ser um arquivo .docx contendo as marcações #INSTITUICAO#, '
                  '#NOMEDOPARTICIPANTE#, #TIPODOPARTICIPANTE#, #TIPOPARTICIPACAO#, #PARTICIPANTE#, #CPF#, '
                  '#NOMEDOEVENTO#, #EVENTO#, #ATIVIDADES#, #LOCAL#, #CAMPUS#, #CARGAHORARIA#, '
                  '#DATAINICIALADATAFINAL#, #PERIODOREALIZACAO#, #SETORRESPONSAVEL#, #CIDADE#, #UF#, #DATAEMISSAO#, '
                  '#DATA#, #CODIGOVERIFICADOR#. Não preencher caso deseje utilizar o modelo padrão.',
    )

    class Meta:
        verbose_name = 'Tipo de Participante'
        verbose_name_plural = 'Tipos de Participante'

    def __str__(self):
        return self.tipo_participacao.descricao

    def get_modelo_certificado(self):
        return self.modelo_certificado or self.tipo_participacao.get_modelo_certificado_padrao()

    def get_inscritos(self):
        return self.evento.participantes.filter(tipo__tipo_participacao=self.tipo_participacao)

    def get_qtd_vagas_disponiveis(self):
        if self.limite_inscricoes is None:
            return None
        qtd = self.limite_inscricoes - self.get_inscritos().count()
        return qtd if qtd > 0 else 0


class TipoAtividade(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Tipo de Atividade'
        verbose_name_plural = 'Tipos de Atividade'

    def __str__(self):
        return self.descricao


class AtividadeEvento(models.ModelPlus):
    evento = models.ForeignKeyPlus(Evento, verbose_name='Evento')
    tipo = models.ForeignKeyPlus(TipoAtividade, verbose_name='Tipo de Atividade')
    descricao = models.CharFieldPlus(verbose_name='Título')
    ch = models.IntegerField(verbose_name='Carga-Horária em segundos')
    data = models.DateFieldPlus('Data', null=True, blank=True)
    hora = models.TimeFieldPlus('Hora', null=True, blank=True)
    limite_inscricoes = models.IntegerField(verbose_name='Limite de Inscrições', null=True, blank=True)
    modelo_certificado = models.FileFieldPlus(
        upload_to='eventos/modelo_certificado_atividade/',
        null=True,
        blank=True,
        verbose_name='Modelo de Certificado',
        filetypes=['doc'],
        help_text='O arquivo de modelo deve ser uma arquivo .docx contendo as marcações #EVENTO#, #PARTICIPANTE#, #CPF#, #CAMPUS#, #CIDADE#, #UF#, #DATA#, #CODIGOVERIFICADOR#, #TIPOATIVIDADE#, #ATIVIDADE#, #CHATIVIDADE#. Não preencher caso deseje utilizar o modelo padrão.',
    )
    # Participantes inscritos e com presença confirmada
    participantes = models.ManyToManyFieldPlus('eventos.Participante', verbose_name='Participantes', blank=True)

    class Meta:
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'

    def __str__(self):
        return f'{self.descricao} ({self.tipo} de {self.get_ch()}h)'

    def get_responsaveis(self):
        return self.evento.participantes.filter(atividades=self).exclude(
            tipo__tipo_participacao__descricao='Participante'
        )

    def get_inscritos(self):
        return self.evento.participantes.filter(atividades=self)

    def get_qtd_vagas_disponiveis(self):
        if self.limite_inscricoes is None:
            return None
        qtd = self.limite_inscricoes - self.get_inscritos().count()
        return qtd if qtd > 0 else 0

    def get_ch(self):
        return Participante.segundos_para_tempo(self.ch)


class Participante(models.ModelPlus):
    evento = models.ForeignKeyPlus(Evento, verbose_name='Evento', related_name='participantes')
    nome = models.CharFieldPlus(verbose_name='Nome')
    cpf = models.BrCpfField(verbose_name='CPF', null=True)
    tipo = models.ForeignKeyPlus(TipoParticipante, verbose_name='Tipo', related_name='participantes', null=True)
    publico_alvo = models.ForeignKeyPlus(PublicoAlvoEvento, verbose_name='Perfil', null=True)
    email = models.EmailField(verbose_name='E-mail')
    telefone = models.BrTelefoneField(verbose_name='Telefone', null=True, blank=True, max_length=15)
    data_cadastro = models.DateTimeField(auto_now_add=True, verbose_name='Data do Cadastro')
    inscricao_validada = models.BooleanField(verbose_name='Inscrição Validada', default=True)
    presenca_confirmada = models.BooleanField(verbose_name='Presença Confirmada', default=False)
    certificado_enviado = models.BooleanField(verbose_name='Certificado Enviado', default=False)
    codigo_geracao_certificado = models.CharFieldPlus(max_length=16, null=True, verbose_name='Código de Validação')
    carga_horaria = models.CharField('Carga Horária', null=True, blank=True, max_length=25, help_text='Carga-Horária de participação no evento. Se não for preenchida, a carga-horária do evento será utilizada.')
    ch_extensao = models.IntegerField(verbose_name='Carga Horária de Extensão', null=True, blank=True, help_text='Carga horária total destinada a atividade curricular de extensão')

    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', null=True, blank=True)
    # Atividades que o participante se inscreveu
    atividades = models.ManyToManyFieldPlus(AtividadeEvento, verbose_name='Atividades', blank=True)

    class Meta:
        verbose_name = 'Participação em Evento'
        verbose_name_plural = 'Participações em Evento'

    def get_modelo_certificado(self):
        if self.tipo:
            return self.tipo.get_modelo_certificado()

    def get_url_download_certificado(self):
        return f'{settings.SITE_URL}/eventos/baixar_certificado/{self.evento.pk}/?hash={self.codigo_geracao_certificado}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        aluno = self.is_aluno_extensao()
        if aluno:
            self.vinculo = aluno.get_vinculo()
            is_organizador = self.tipo.tipo_participacao.descricao == 'Organizador'
            AtividadeCurricularExtensao = apps.get_model('edu', 'AtividadeCurricularExtensao')
            AtividadeCurricularExtensao.registrar(aluno, type(self), self.pk, is_organizador and self.ch_extensao or 0, self.evento.nome, self.presenca_confirmada or False)

    def is_aluno_extensao(self):
        if 'edu' in settings.INSTALLED_APPS:
            Aluno = apps.get_model('edu', 'Aluno')
            SituacaoMatricula = apps.get_model('edu', 'SituacaoMatricula')
            return Aluno.objects.filter(
                pessoa_fisica__cpf=self.cpf, matriz__ch_atividades_extensao__gt=0, situacao__in=(SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL)
            ).first()
        return None

    def delete(self, *args, **kwargs):
        aluno = self.is_aluno_extensao()
        if aluno:
            AtividadeCurricularExtensao = apps.get_model('edu', 'AtividadeCurricularExtensao')
            AtividadeCurricularExtensao.registrar(aluno, type(self), self.pk, 0, False)
        super().delete(*args, **kwargs)

    def checar_vinculo(self):
        self.vinculo = None
        if self.publico_alvo and self.publico_alvo.id in (
            PublicoAlvoEvento.ESTUDANTES,
            PublicoAlvoEvento.SERVIDORES,
            PublicoAlvoEvento.GESTORES,
            PublicoAlvoEvento.TERCEIRIZADOS,
            PublicoAlvoEvento.ESTAGIARIOS,
        ):
            for vinculo in Vinculo.objects.filter(pessoa__pessoafisica__cpf=self.cpf, pessoa__excluido=False):
                if self.publico_alvo.id == PublicoAlvoEvento.ESTUDANTES and vinculo.eh_aluno():
                    self.vinculo = vinculo
                    break
                if self.publico_alvo.id == PublicoAlvoEvento.SERVIDORES and vinculo.eh_servidor():
                    self.vinculo = vinculo
                    break
                if self.publico_alvo.id == PublicoAlvoEvento.GESTORES and vinculo.eh_servidor():
                    if vinculo.relacionamento.historico_funcao().filter(data_fim_funcao__isnull=True).exists():
                        self.vinculo = vinculo
                        break
                if self.publico_alvo.id == PublicoAlvoEvento.TERCEIRIZADOS and vinculo.eh_prestador():
                    self.vinculo = vinculo
                    break
                if self.publico_alvo.id == PublicoAlvoEvento.ESTAGIARIOS and vinculo.eh_servidor():
                    self.vinculo = vinculo
                    break
            if not self.vinculo:
                raise ValidationError(f'Nenhum vículo de "{self.publico_alvo}" localizado para o CPF: {self.cpf}.')

    def checar_publico_alvo(self):
        if self.vinculo.eh_aluno():
            self.publico_alvo_id = PublicoAlvoEvento.ESTUDANTES
        elif self.vinculo.eh_servidor() and self.vinculo.relacionamento.eh_estagiario:
            self.publico_alvo_id = PublicoAlvoEvento.ESTAGIARIOS
        elif self.vinculo.eh_servidor() and self.vinculo.relacionamento.historico_funcao().filter(data_fim_funcao__isnull=True).exists():
            self.publico_alvo_id = PublicoAlvoEvento.GESTORES
        elif self.vinculo.eh_servidor():
            self.publico_alvo_id = PublicoAlvoEvento.SERVIDORES
        elif self.vinculo.eh_prestador():
            self.publico_alvo_id = PublicoAlvoEvento.TERCEIRIZADOS

    def get_ch_inscrita(self):
        if self.evento.subtipo and self.evento.subtipo.multiplas_atividades:
            ch = self.atividades.aggregate(ch=Sum('ch')).get('ch') or 0
            ch = Participante.segundos_para_tempo(ch)
        else:
            ch = self.evento.carga_horaria
        if ch is None:
            return self.carga_horaria or 0
        return ch

    def get_ch_total(self, atividades=None):
        ch = 0
        if not atividades and self.tipo.tipo_participacao.ch_organizacao:
            if self.evento.carga_horaria:
                ch = int(self.evento.carga_horaria)
            else:
                atividades = self.evento.atividadeevento_set.all()
                ch = atividades.aggregate(ch=Sum('ch')).get('ch') or 0
            ch = ch * 1.2
        else:
            if self.evento.subtipo and self.evento.subtipo.multiplas_atividades:
                ch = self.get_atividades(atividades=atividades).aggregate(ch=Sum('ch')).get('ch') or 0
            else:
                ch = self.carga_horaria or self.evento.carga_horaria
        return Participante.segundos_para_tempo(ch)

    def get_atividades(self, atividades=None):
        qs = AtividadeEvento.objects.filter(evento=self.evento, participantes=self, participantes__tipo=self.tipo)
        if atividades:
            qs = qs.filter(id__in=atividades)
        return qs

    @staticmethod
    def segundos_para_tempo(segundos=0):
        if segundos:
            try:
                segundos = int(segundos)
            except Exception:
                return ''
            if segundos >= 0:
                minutos, segundos = divmod(segundos, 60)
                horas, minutos = divmod(minutos, 60)
                return f'{horas:.0f}:{minutos:02.0f}'
        return ''

    @staticmethod
    def tempo_para_segundos(tempo):
        if tempo:
            hora, minuto = tempo.split(':')
            return int(hora) * 60 * 60 + int(minuto) * 60
        return 0


class FotoEvento(models.ModelPlus):
    evento = models.ForeignKeyPlus(Evento, verbose_name='Evento')
    imagem = models.ImageFieldPlus(verbose_name='Imagem', upload_to='fotos_eventos')
    descricao = models.CharFieldPlus(verbose_name='Descrição', null=True, blank=True)

    class Meta:
        verbose_name = 'Foto de Evento'
        verbose_name_plural = 'Fotos de Evento'

    def __str__(self):
        return self.descricao


class AnexoEvento(models.ModelPlus):
    evento = models.ForeignKeyPlus(Evento, verbose_name='Evento')
    arquivo = models.FileFieldPlus(verbose_name='Arquivo', upload_to='anexos_eventos')
    descricao = models.CharFieldPlus(verbose_name='Descrição', null=True, blank=True)

    class Meta:
        verbose_name = 'Anexo de Evento'
        verbose_name_plural = 'Anexos de Evento'

    def __str__(self):
        return self.descricao


class Banner(models.ModelPlus):
    INICIO = 'Início'
    TIPO_CHOICES = ((INICIO, INICIO),)
    titulo = models.CharFieldPlus('Título', max_length=1000)
    imagem = models.FileFieldPlus('Imagem', upload_to='eventos/banner', max_length=255)
    tipo = models.CharFieldPlus('Tipo', max_length=100, choices=TIPO_CHOICES, default=INICIO)
    link = models.CharFieldPlus('Link', max_length=1000, null=True, blank=True)
    data_inicio = models.DateTimeField('Início da Publicação')
    data_termino = models.DateTimeField('Término da Publicação')

    class Meta:
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete('_cache_index_quadros_banners')


class TipoAtendimento(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Atendimento'
        verbose_name_plural = 'Tipos de Atendimentos'

    def __str__(self):
        return self.descricao


class MotivoAtendimento(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Motivo de Atendimento'
        verbose_name_plural = 'Motivos de Atendimentos'

    def __str__(self):
        return self.descricao


class AssuntoAtendimento(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Assunto de Atendimento'
        verbose_name_plural = 'Assuntos de Atendimentos'

    def __str__(self):
        return self.descricao


class PublicoAtendimento(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Público de Atendimento'
        verbose_name_plural = 'Públicos de Atendimentos'

    def __str__(self):
        return self.descricao


class SituacaoAtendimento(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Situação de Atendimento'
        verbose_name_plural = 'Situações de Atendimentos'

    def __str__(self):
        return self.descricao


class AtendimentoPublico(models.ModelPlus):
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus')
    tipo = models.ForeignKeyPlus(TipoAtendimento)
    motivo = models.ForeignKeyPlus(MotivoAtendimento)
    assunto = models.ForeignKeyPlus(AssuntoAtendimento)
    publico = models.ForeignKeyPlus(PublicoAtendimento, verbose_name='Público')
    situacao = models.ForeignKeyPlus(SituacaoAtendimento, verbose_name='Situação')
    data_cadastro = models.DateTimeField('Data/Hora do Cadastro', auto_now_add=True)

    class Meta:
        verbose_name = 'Atendimento ao Público'
        verbose_name_plural = 'Atendimentos ao Público'
