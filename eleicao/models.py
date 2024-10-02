from datetime import date
import datetime

from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.db.models import Q

from comum.models import PrestadorServico, Vinculo
from djtools.db import models
from djtools.db.models import ModelPlus
from djtools.utils import anonimizar_cpf
from edu.models import Aluno
from rh.models import Servidor


class Edital(ModelPlus):
    descricao = models.CharFieldPlus('Descrição', blank=False)
    # Período para inscrição de candidatos/chapa
    data_inscricao_inicio = models.DateTimeFieldPlus('Início das Inscrições', help_text='Período em que os candidatos podem se inscrever.')
    data_inscricao_fim = models.DateTimeFieldPlus('Fim das Inscrições')
    # Período de validação das inscrições
    data_validacao_inicio = models.DateTimeFieldPlus('Início da Validação', help_text='Período de validação das candidaturas por parte dos Coordenadores.')
    data_validacao_fim = models.DateTimeFieldPlus('Fim da Validação')
    # Período da campanha
    data_campanha_inicio = models.DateTimeFieldPlus('Início da Campanha', help_text='Período em que os candidatos são tornados públicos na tela inicial.')
    data_campanha_fim = models.DateTimeFieldPlus('Fim da Campanha')
    # Período de votação
    data_votacao_inicio = models.DateTimeFieldPlus('Início da Votação', help_text='Período em que usuários habilitados podem votar.')
    data_votacao_fim = models.DateTimeFieldPlus('Fim da Votação')
    # Período de homologação dos votos
    data_homologacao_inicio = models.DateTimeFieldPlus(
        'Início da Homologação', help_text='Período em que os coordenadores podem invalidar os votos em caso de descumprimento do edital.'
    )
    data_homologacao_fim = models.DateTimeFieldPlus('Fim da Homologação')
    # Período do resultado preliminar
    data_pre_resultado_inicio = models.DateTimeFieldPlus(
        'Início do Resultado Preliminar', null=True, blank=True, help_text='Período em que o resultado preliminar é exibido ao público.'
    )
    data_pre_resultado_fim = models.DateTimeFieldPlus('Fim do Resultado Preliminar', null=True, blank=True)
    # Data para publicação do resultado final
    data_resultado_final = models.DateTimeFieldPlus('Data para Resultado Final', help_text='O resultado final é exibido somente aos coordenadores.')
    vinculos_coordenadores = models.ManyToManyFieldPlus('comum.Vinculo', related_name='vinculos_coordenadores_editais', verbose_name='Coordenador(es)')

    class Meta:
        verbose_name = 'Edital'
        verbose_name_plural = 'Editais'

    def clean(self):
        errors = dict()
        if (self.data_inscricao_inicio or self.data_inscricao_fim) and self.data_inscricao_fim <= self.data_inscricao_inicio:
            errors['data_inscricao_inicio'] = ['A data final de inscrição deve ser maior que a data de início.']

        if (self.data_validacao_inicio or self.data_validacao_fim) and self.data_validacao_fim <= self.data_validacao_inicio:
            errors['data_validacao_inicio'] = ['A data final de validação deve ser maior que a data de início.']

        if (self.data_campanha_inicio or self.data_campanha_fim) and self.data_campanha_fim <= self.data_campanha_inicio:
            errors['data_campanha_inicio'] = ['A data final da campanha deve ser maior que a data de início.']

        if (self.data_votacao_inicio or self.data_votacao_fim) and self.data_votacao_fim <= self.data_votacao_inicio:
            errors['data_votacao_inicio'] = ['A data final de votação deve ser maior que a data de início.']

        if (self.data_homologacao_inicio or self.data_homologacao_fim) and self.data_homologacao_fim <= self.data_homologacao_inicio:
            errors['data_homologacao_inicio'] = ['A data final de homologação deve ser maior que a data de início.']

        # Falta validar as datas entre si
        # A sequencia seria:
        # inscricao < validacao < campanha < votacao < homologacao < pre_resultado < recurso < final
        if errors:
            raise ValidationError(errors)

    def eh_coordenador(self, vinculo):
        return self.vinculos_coordenadores.filter(id=vinculo.id).exists()

    def eh_periodo_inscricao(self):
        return self.data_inscricao_inicio <= datetime.datetime.now() <= self.data_inscricao_fim

    def eh_periodo_validacao(self):
        return self.data_validacao_inicio <= datetime.datetime.now() <= self.data_validacao_fim

    def eh_periodo_campanha(self):
        return self.data_campanha_inicio <= datetime.datetime.now() <= self.data_campanha_fim

    def eh_periodo_votacao(self):
        return self.data_votacao_inicio <= datetime.datetime.now() <= self.data_votacao_fim

    def eh_periodo_homologacao(self):
        return self.data_homologacao_inicio <= datetime.datetime.now() <= self.data_homologacao_fim

    def eh_periodo_resultado_preliminar(self):
        return (
            self.data_pre_resultado_inicio
            and self.data_pre_resultado_inicio <= datetime.datetime.now()
            and (datetime.datetime.now() <= self.data_pre_resultado_fim or self.data_pre_resultado_fim is None)
        )

    def eh_periodo_resultado_final(self):
        return self.data_resultado_final <= datetime.datetime.now()

    def pode_ver_resultado(self, vinculo):
        return self.eh_periodo_resultado_final() and (self.eh_coordenador(vinculo) or vinculo.user.is_superuser)


class Eleicao(ModelPlus):
    TIPO_INDIVIDUAL = 'Individual'
    TIPO_CHAPA = 'Chapa'
    TIPO_CHOICES = ((TIPO_INDIVIDUAL, TIPO_INDIVIDUAL), (TIPO_CHAPA, TIPO_CHAPA))

    tipo = models.CharFieldPlus('Tipo', choices=TIPO_CHOICES, blank=False)
    descricao = models.CharFieldPlus('Descrição')
    publico = models.ForeignKey('comum.Publico', verbose_name='Público', on_delete=models.CASCADE, null=True, blank=True)
    campi = models.ManyToManyField('rh.UnidadeOrganizacional', blank=True)
    pessoas_relacionadas_eleicao = models.ManyToManyFieldPlus(
        'rh.Servidor', blank=True, verbose_name='Servidores Relacionados à Eleição', related_name='pessoas_relacionadas_eleicao'
    )
    alunos_relacionados_eleicao = models.ManyToManyFieldPlus('edu.Aluno', blank=True, verbose_name='Alunos Relacionadas à Eleição', related_name='alunos_relacionados_eleicao')
    caracteres_campanha = models.PositiveIntegerField('Número de Caracteres para a Campanha', default=2000)
    caracteres_recurso = models.PositiveIntegerField('Número de Caracteres para Recurso', default=2000)
    edital = models.ForeignKeyPlus('eleicao.Edital', verbose_name='Edital', blank=False, on_delete=models.CASCADE)
    votacao_global = models.BooleanField('Votação Global', default=False, help_text='Não marcando esta opçãp, um eleitor de um campus somente poderá votar em candidatos do seu próprio campus')
    resultado_global = models.BooleanField('Resultado Global', default=False, help_text='O resultado dessa eleição será exibido de forma global entre os campi selecionados, ou seja, sem separar os votos por campus')
    obs_voto = models.TextField('Observação para Votação', help_text='Esta observação será visível para o eleitor no momento da votação', blank=True)
    vinculo_publico_eleicao = models.ManyToManyFieldPlus('comum.Vinculo', blank=True, verbose_name='Público da Eleição', related_name='publico_eleicao')

    class Meta:
        ordering = ['-edital__data_resultado_final']
        verbose_name = 'Eleição'
        verbose_name_plural = 'Eleições'

    def __str__(self):
        return '{} ({})'.format(self.descricao, self.edital)

    def save(self, *args, **kargs):
        if self.pk:
            self.vinculo_publico_eleicao.set(self.get_publicos())
        super().save(*args, **kargs)

    def pode_inscrever(self, vinculo):
        return self.edital.eh_periodo_inscricao() and self.eh_parte_publico(vinculo) and not self.candidato_set.filter(candidato_vinculo=vinculo).exists()

    def pode_validar(self, vinculo):
        return self.edital.eh_periodo_validacao() and (self.edital.eh_coordenador(vinculo) or vinculo.user.is_superuser)

    def pode_votar(self, vinculo):
        return self.edital.eh_periodo_votacao() and self.eh_parte_publico(vinculo) and not Voto.get_por_eleicao_eleitor(self, vinculo)

    def pode_votar_em(self, vinculo, candidato):
        return self.pode_votar(vinculo) and self.get_candidatos_validos(vinculo).filter(id=candidato.id).exists()

    def pode_ver_resultado_preliminar(self, vinculo):
        return self.edital.eh_periodo_resultado_preliminar() and (self.eh_parte_publico(vinculo) or self.edital.eh_coordenador(vinculo) or vinculo.user.is_superuser)

    def pode_homologar(self, vinculo):
        return self.edital.eh_periodo_homologacao() and (self.edital.eh_coordenador(vinculo) or vinculo.user.is_superuser)

    def pode_ver_resultado_final(self, vinculo):
        return self.edital.eh_periodo_resultado_final() and (self.edital.eh_coordenador(vinculo) or vinculo.user.is_superuser)

    def get_candidatos_validos(self, vinculo):
        candidatos = self.candidato_set.filter(status=Candidato.STATUS_DEFERIDO)
        publico = self.vinculo_publico_eleicao
        if not self.votacao_global:
            # Eleitor somente poderá votar em candidato do seu campus
            # Eleitor aluno somente poderá votar em candidato aluno
            # Eleitor servidor ou prestador de serviço somente poderá votar em candidato servidor ou prestador de serviço
            campus_id = []
            sub_instance = vinculo.relacionamento
            if isinstance(sub_instance, Aluno):
                campus_id.append(sub_instance.curso_campus.diretoria.setor.uo_id)
            elif isinstance(sub_instance, PrestadorServico):
                campus_id.append(sub_instance.setor.uo_id)
            elif isinstance(sub_instance, Servidor):
                if sub_instance.campus_lotacao_siape:
                    campus_id.append(sub_instance.campus_lotacao_siape.equivalente_id)
                elif sub_instance.campus_exercicio_siape:
                    campus_id.append(sub_instance.campus_exercicio_siape.equivalente_id)
                elif sub_instance.campus:
                    campus_id.append(sub_instance.campus.equivalente_id)

            campi = self.campi.filter(id__in=campus_id)
            if isinstance(sub_instance, Aluno):
                filtro = Q(alunos__curso_campus__diretoria__setor__uo__id__in=campi)
            else:
                filtro = Q(servidores__setor_lotacao__uo__equivalente__id__in=campi) | Q(prestadores__setor_lotacao__uo__equivalente__id__in=campi)

            publico = publico.filter(filtro).distinct()

        return candidatos.filter(candidato_vinculo__id__in=publico.values_list('id', flat=True))

    def get_publicos(self):
        qs1 = list(self.pessoas_relacionadas_eleicao.values_list('vinculo__id', flat=True))
        qs2 = list(self.alunos_relacionados_eleicao.values_list('vinculos__id', flat=True))

        qs = Vinculo.objects.filter(id__in=qs1 + qs2).distinct()
        if self.publico:
            qs = qs | self.publico.get_queryset_vinculo(self.campi.all()).distinct()
        return qs

    def eh_parte_publico(self, vinculo):
        return self.vinculo_publico_eleicao.filter(id=vinculo.id).exists()

    def obter_votos_validos(self):
        return self.voto_set.filter(valido=True)

    def obter_candidatos_validos(self):
        return self.candidato_set.filter(status=Candidato.STATUS_DEFERIDO)

    def obter_resultados_por_campus(self):
        votos = self.obter_votos_validos()
        candidatos = self.obter_candidatos_validos().order_by('candidato_vinculo__pessoa__nome')
        campi = self.campi.all()
        for campus in campi:
            if self.edital.id == 43 and campus.id == 14:
                continue

            campus.candidatos = []
            qtd_votos_geral = votos.filter(campus=campus).count()
            # A exibição do resultado é por campus mas a votação é global
            if self.votacao_global:
                qtd_votos_geral = votos.count()
            else:
                # A exibição do resultado e votação é por campus
                if self.edital.id == 43 and campus.id == 1:
                    qtd_votos_geral = votos.filter(campus__in=[1, 14]).count()
                else:
                    qtd_votos_geral = votos.filter(campus=campus).count()

            if self.edital.id == 43 and campus.id == 1:
                query = Q(campus__in=[1, 14])
            else:
                query = Q(campus=campus)
            for candidato in candidatos.filter(query):
                qtd_votos = 0
                percentual_votos = 0
                if qtd_votos_geral:
                    qtd_votos = candidato.voto_set.filter(valido=True).distinct().count()
                    # Calculo da porcentagem utilizando 4 casas decimais
                    percentual_votos = round(float(qtd_votos) / qtd_votos_geral * 100, 4)
                    # arredondamento para o inteiro mais próximo (0,5 = 1)
                    if self.edital.id != 43:
                        percentual_votos = int(round(percentual_votos))

                candidato.qtd_votos = qtd_votos
                candidato.percentual_votos = percentual_votos
                if self.edital.id != 43:
                    candidato.percentual_votos_label = "{:d}%".format(percentual_votos)
                else:
                    candidato.percentual_votos_label = "{}%".format(percentual_votos)
                campus.candidatos.append(candidato)

            # Caso tenha empate ordena os candidatos pela idade
            campus.candidatos = sorted(campus.candidatos, key=lambda c: c.get_idade(), reverse=True)
            # Caso tenha empate ordena os candidatos pelo tempo na instituição
            campus.candidatos = sorted(campus.candidatos, key=lambda c: c.get_tempo_na_instituicao().days, reverse=True)
            # ordenando os candidatos pelo percentual de votos em ordem decrescente
            campus.candidatos = sorted(campus.candidatos, key=lambda c: c.percentual_votos, reverse=True)

        return campi

    def obter_resultados(self):
        votos = self.obter_votos_validos()
        candidatos = self.obter_candidatos_validos().order_by('candidato_vinculo__pessoa__nome')
        qtd_votos_geral = votos.count()
        for candidato in candidatos:
            # A exibição do resultado e a votação é global
            if self.votacao_global:
                qtd_votos = candidato.voto_set.filter(valido=True).distinct().count()
            else:
                # A exibição do resultado é global mas a votação é por campus
                qtd_votos = candidato.voto_set.filter(valido=True, campus=candidato.campus).distinct().count()

            percentual_votos = 0
            if qtd_votos_geral:
                # Calculo da porcentagem utilizando 4 casas decimais
                percentual_votos = round(float(qtd_votos) / qtd_votos_geral * 100, 4)
                # arredondamento para o inteiro mais próximo (0,5 = 1)
                percentual_votos = int(round(percentual_votos))

            candidato.qtd_votos = qtd_votos
            candidato.percentual_votos = percentual_votos
            candidato.percentual_votos_label = "{:d}%".format(percentual_votos)

        # Caso tenha empate ordena os candidatos pela idade
        candidatos = sorted(candidatos, key=lambda c: c.get_idade(), reverse=True)
        # Caso tenha empate ordena os candidatos pelo tempo na instituição
        candidatos = sorted(candidatos, key=lambda c: c.get_tempo_na_instituicao().days, reverse=True)
        # ordenando os candidatos pelo percentual de votos em ordem decrescente
        candidatos = sorted(candidatos, key=lambda c: c.percentual_votos, reverse=True)
        return candidatos

    @staticmethod
    def get_abertas(usuario=None):
        hoje = datetime.datetime.now()
        eleicoes_abertas = Eleicao.objects.filter(edital__data_inscricao_inicio__lte=hoje, edital__data_resultado_final__gte=hoje)
        if usuario:
            vinculo = usuario.get_vinculo()
            eleicoes_abertas = eleicoes_abertas.filter(vinculo_publico_eleicao__id=vinculo.id)
        return eleicoes_abertas

    @staticmethod
    def get_inscricao_aberta(usuario=None):
        hoje = datetime.datetime.now()
        eleicoes_inscricao_aberta = Eleicao.objects.filter(edital__data_inscricao_inicio__lte=hoje, edital__data_inscricao_fim__gte=hoje)
        if usuario:
            vinculo = usuario.get_vinculo()
            eleicoes_inscricao_aberta = eleicoes_inscricao_aberta.filter(vinculo_publico_eleicao__id=vinculo.id).exclude(candidato__candidato_vinculo_id=vinculo.id)
        return eleicoes_inscricao_aberta

    @staticmethod
    def get_em_campanha(usuario=None):
        hoje = datetime.datetime.now()
        eleicoes_em_campanha = Eleicao.objects.filter(edital__data_campanha_inicio__lte=hoje, edital__data_campanha_fim__gte=hoje)
        if usuario:
            vinculo = usuario.get_vinculo()
            eleicoes_em_campanha = eleicoes_em_campanha.filter(vinculo_publico_eleicao__id=vinculo.id)
        return eleicoes_em_campanha

    @staticmethod
    def get_em_votacao(usuario):
        vinculo = usuario.get_vinculo()
        hoje = datetime.datetime.now()
        eleicoes_em_votacao = []
        todas_eleicoes_em_votacao = Eleicao.objects.filter(edital__data_votacao_inicio__lte=hoje, edital__data_votacao_fim__gte=hoje, vinculo_publico_eleicao__id=vinculo.id)
        for eleicao_em_votacao in todas_eleicoes_em_votacao:
            if eleicao_em_votacao.vinculo_publico_eleicao.filter(id=vinculo.id).exists():
                eleicoes_em_votacao.append(eleicao_em_votacao)

        return eleicoes_em_votacao


class Chapa(ModelPlus):
    STATUS_DEFERIDO = 'Deferido'
    STATUS_INDEFERIDO = 'Indeferido'
    STATUS_PENDENTE = 'Pendente'
    STATUS_CHOICES = ((STATUS_DEFERIDO, STATUS_DEFERIDO), (STATUS_INDEFERIDO, STATUS_INDEFERIDO), (STATUS_PENDENTE, STATUS_PENDENTE))

    eleicao = models.ForeignKeyPlus('eleicao.Eleicao', verbose_name='Eleição', on_delete=models.CASCADE)
    nome = models.CharFieldPlus('Nome')
    descricao = models.TextField('Descrição')
    status = models.CharFieldPlus('Parecer', choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    justificativa_parecer = models.TextField('Justificativa do Parecer', blank=True)

    class Meta:
        unique_together = ('eleicao', 'nome')
        verbose_name = 'Chapa'
        verbose_name_plural = 'Chapas'
        permissions = (('validar_chapa', 'Pode validar chapa'),)

    def clean(self):
        errors = dict()

        if len(self.descricao) > self.eleicao.caracteres_campanha:
            errors['descricao'] = ['O número de caracteres é maior que o permitido.']

        if errors:
            raise ValidationError(errors)

    def pode_ser_validado(self):
        return self.status == Candidato.STATUS_PENDENTE

    def __str__(self):
        return self.nome

    def get_numero_votos(self):
        return self.voto_set.filter(valido=True).count()


class Candidato(ModelPlus):
    STATUS_DEFERIDO = 'Deferido'
    STATUS_INDEFERIDO = 'Indeferido'
    STATUS_PENDENTE = 'Pendente'
    STATUS_NAO_APLICADO = 'Não aplicado'
    STATUS_CHOICES = ((STATUS_DEFERIDO, STATUS_DEFERIDO), (STATUS_INDEFERIDO, STATUS_INDEFERIDO), (STATUS_PENDENTE, STATUS_PENDENTE), (STATUS_NAO_APLICADO, STATUS_NAO_APLICADO))

    eleicao = models.ForeignKeyPlus('eleicao.Eleicao', verbose_name='Eleição', null=True, on_delete=models.CASCADE)
    chapa = models.ForeignKeyPlus('eleicao.Chapa', null=True, on_delete=models.CASCADE)
    candidato_vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Candidato')
    descricao = models.TextField('Texto de Apresentação', blank=True)
    status = models.CharFieldPlus('Parecer', choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    justificativa_parecer = models.TextField('Justificativa do Parecer', blank=True)
    campus = models.ForeignKeyPlus("rh.UnidadeOrganizacional", verbose_name='Campus do Candidato no Momento da Inscrição', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('eleicao', 'candidato_vinculo')
        verbose_name = 'Candidato'
        verbose_name_plural = 'Candidatos'
        permissions = (('validar_candidato', 'Pode validar candidato'),)

    def __str__(self):
        return self.candidato_vinculo.pessoa.nome

    def clean(self):
        errors = dict()

        if (self.eleicao and self.chapa) or (self.eleicao is None and self.chapa is None):
            errors[NON_FIELD_ERRORS] = ['Não é possível associar um candidato a uma chapa e a uma eleição ao mesmo tempo.']
        else:
            import re

            qtd_caracteres = len(re.sub('[\r\n]', '', self.descricao.strip()))
            if self.eleicao:
                if qtd_caracteres > 0 and self.eleicao.tipo == Eleicao.TIPO_CHAPA:
                    errors['descricao'] = ['A descrição não se aplica a esse tipo de eleição.']
                if qtd_caracteres > self.eleicao.caracteres_campanha:
                    errors['descricao'] = ['O número de caracteres é maior que o permitido.']
                if self.candidato_vinculo_id and not self.eleicao.eh_parte_publico(self.candidato_vinculo) and self.status == Candidato.STATUS_DEFERIDO:
                    errors['candidato_vinculo'] = ['O candidato não faz parte do público.']
            else:
                if qtd_caracteres > 0 and self.chapa.eleicao.tipo == Eleicao.TIPO_CHAPA:
                    errors['descricao'] = ['A descrição não se aplica a esse tipo de eleição.']

                if qtd_caracteres > self.chapa.eleicao.caracteres_campanha:
                    errors['descricao'] = ['O número de caracteres é maior que o permitido.']

        if errors:
            raise ValidationError(errors)

        return super().clean()

    def save(self, *args, **kwargs):
        self.candidato_id = self.candidato_vinculo.pessoa_id
        if not self.campus_id:
            self.campus = self.candidato_vinculo.relacionamento.setor.uo
        super().save(*args, **kwargs)

    def get_numero_votos(self):
        return self.voto_set.filter(valido=True).count()

    def pode_ser_validado(self):
        eleicao = self.eleicao
        if self.chapa:
            eleicao = self.chapa.eleicao

        return self.status == Candidato.STATUS_PENDENTE and eleicao.eh_parte_publico(self.candidato_vinculo)

    def get_foto(self):
        vinculo = self.candidato_vinculo
        return '<img src="{}" alt="Foto de {}"/>'.format(vinculo.relacionamento.pessoa_fisica.get_foto_75x100_url(), vinculo.relacionamento.pessoa_fisica.nome_usual)

    def get_info_principal(self):
        subinstance = self.candidato_vinculo.relacionamento
        perfil = subinstance.__class__._meta.verbose_name
        return '''
        <div class="photo-circle small">
            {foto}
        </div>
        <h4><strong>{nome}</strong> ({perfil})</h4>
        '''.format(
            foto=self.get_foto(), nome=subinstance.pessoa_fisica.nome, perfil=perfil
        )

    def get_info_auxilar(self):
        subinstance = self.candidato_vinculo.relacionamento
        out = []
        if isinstance(subinstance, Aluno):
            out.append('<dl><dt>Matrícula:</dt><dd>{}</dd></dl>'.format(subinstance.matricula))
            out.append('<dl><dt>Curso:</dt><dd>{}</dd></dl>'.format(subinstance.curso_campus))
            out.append('<dl><dt>Situação:</dt><dd>{}</dd></dl>'.format(subinstance.situacao))
            out.append('<dl><dt>Período Letivo:</dt><dd>{}</dd></dl>'.format(subinstance.periodo_letivo))
            out.append('<dl><dt>Ano Letivo:</dt><dd>{}</dd></dl>'.format(subinstance.ano_letivo))

        elif isinstance(subinstance, Servidor):
            out.append('<dl><dt>Matrícula:</dt><dd>{}</dd></dl>'.format(subinstance.matricula))
            if subinstance.setor:
                telefones_institucionais = ', '.join(subinstance.setor.setortelefone_set.values_list('numero', flat=True))
                if telefones_institucionais:
                    out.append('<dl><dt>Telefones institucionais:</dt><dd>{}</dd></dl>'.format(telefones_institucionais))
            if subinstance.email:
                out.append('<dl><dt>E-mail:</dt><dd><a href="mailto:{email}">{email}</a></dd></dl>'.format(email=subinstance.email))
            if subinstance.cargo_emprego:
                out.append('<dl><dt>Cargo:</dt><dd>{}</dd></dl>'.format(subinstance.cargo_emprego.nome))
            if subinstance.funcao:
                out.append('<dl><dt>Atividade:</dt><dd>{}</dd></dl>'.format(subinstance.atividade.nome))
            if subinstance.setor:
                out.append('<dl><dt>Setor SUAP:</dt><dd>{}</dd></dl>'.format(subinstance.setor.sigla))

        elif isinstance(subinstance, PrestadorServico):
            out.append('<dl><dt>CPF:</dt><dd>{}</dd></dl>'.format(anonimizar_cpf(subinstance.cpf)))
            out.append('<dl><dt>E-mail:</dt><dd><a href="mailto:{email}">{email}</a></dd></dl>'.format(email=subinstance.email))
            if subinstance.setor:
                out.append('<dl><dt>Setor:</dt><dd>{}</dd></dl>'.format(subinstance.setor.sigla))

        return ''.join(out)

    def get_tempo_na_instituicao(self):
        subinstance = self.candidato_vinculo.relacionamento
        if isinstance(subinstance, Aluno):
            return date.today() - subinstance.data_matricula.date()

        elif isinstance(subinstance, Servidor):
            return subinstance.tempo_servico_na_instituicao_via_pca()

        elif isinstance(subinstance, PrestadorServico):
            pass

    def get_idade(self):
        return self.candidato_vinculo.relacionamento.pessoa_fisica.idade


class VotosValidosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(valido=True)


class Voto(ModelPlus):
    eleicao = models.ForeignKeyPlus('eleicao.Eleicao', verbose_name='Eleição', null=True, on_delete=models.CASCADE)
    chapa = models.ForeignKeyPlus('eleicao.Chapa', null=True, on_delete=models.CASCADE)
    candidato = models.ForeignKeyPlus('eleicao.Candidato', null=True, on_delete=models.CASCADE)
    eleitor = models.CurrentUserField()
    data_voto = models.DateTimeFieldPlus('Data do Voto', auto_now_add=True)
    ip = models.GenericIPAddressField('IP da Origem do Voto')
    campus = models.ForeignKeyPlus("rh.UnidadeOrganizacional", verbose_name='Campus do Eleitor no Momento do Voto', on_delete=models.CASCADE)
    hash = models.CharFieldPlus('Hash', blank=True)
    string_hash = models.TextField('String formadora do hash', blank=True)
    valido = models.BooleanField('Ativo', default=True)
    justificativa_avaliacao = models.TextField('Justificativa da Avaliação', blank=True)

    objects = models.Manager()
    validos = VotosValidosManager()

    class Meta:
        verbose_name = 'Voto'
        verbose_name_plural = 'Votos'
        permissions = (('validar_voto', 'Pode validar voto'),)

    def clean(self):
        errors = dict()

        if self.chapa and self.candidato:
            errors[NON_FIELD_ERRORS] = ['Voto inválido. Não é possível vorar em uma chapa e em um candidato ao mesmo tempo.']

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        if self.chapa:
            return self.chapa
        return self.candidato.candidato_vinculo.pessoa.nome

    @staticmethod
    def get_por_eleicao_eleitor(eleicao, vinculo):
        if Voto.objects.filter(eleicao=eleicao, eleitor__vinculo=vinculo).exists():
            return Voto.objects.filter(eleicao=eleicao, eleitor__vinculo=vinculo).latest('id')

        return None

    def get_foto_eleitor(self):
        pessoa_fisica = self.eleitor.get_profile()
        return '<img src="{}" alt="Foto de {}" />'.format(pessoa_fisica.get_foto_75x100_url(), pessoa_fisica.nome_usual)

    def get_info_principal_eleitor(self):
        subinstance = self.eleitor.get_relacionamento()
        perfil = subinstance.__class__._meta.verbose_name
        if isinstance(subinstance, Aluno):
            out = '''
                    <dl>
                        <dt class="hidden">Nome:</dt><dd class="negrito">{nome}</dd>
                        <dt class="hidden">Perfil:</dt><dd>{perfil}</dd>
                        <dt>Matrícula:</dt><dd>{matricula}</dd>
                        <dt>Curso:</dt><dd>{curso}</dd>
                        <dt>Situação:</dt><dd>{situacao}</dd>
                    </dl>
                '''.format(
                nome=subinstance.pessoa_fisica.nome, perfil=perfil, matricula=subinstance.matricula, curso=subinstance.curso_campus, situacao=subinstance.situacao
            )

        elif isinstance(subinstance, Servidor):
            show_telefones, show_email = '', ''
            if subinstance.setor:
                telefones_institucionais = ', '.join(subinstance.setor.setortelefone_set.values_list('numero', flat=True))
                if telefones_institucionais:
                    show_telefones = '<dt>Telefones institucionais:</dt><dd>{}</dd>'.format(telefones_institucionais)
            if subinstance.email:
                show_email = '<a href="mailto:{}">{}</a>'.format(subinstance.email, subinstance.email)
            out = '''
            <dl>
                <dt class="hidden">Nome:</dt><dd class="negrito">{nome}</dd>
                <dt class="hidden">Perfil:</dt><dd>{perfil}</dd>
                <dt class="hidden">E-mail:</dt><dd>{show_email} </dd>
                <dt>Matrícula:</dt><dd>{matricula}</dd>
                {show_telefones}
            </dl>
            '''.format(
                nome=subinstance.pessoa_fisica.nome, perfil=perfil, matricula=subinstance.matricula, show_telefones=show_telefones, show_email=show_email
            )

        else:
            out = '''
            <dl>
                <dt class="hidden">Nome:</dt><dd class="negrito">{nome}</dd>
                <dt class="hidden">Perfil:</dt><dd>{perfil}</dd>
                <dt>CPF:</dt><dd>{cpf}</dd>
                <dt class="hidden">E-mail:</dt><dd><a href="mailto:{email}">{email}</a></dd>
            </dl>
            '''.format(
                nome=subinstance.pessoa_fisica.nome, perfil=perfil, cpf=anonimizar_cpf(subinstance.pessoa_fisica.cpf), email=subinstance.email
            )
        return out

    def get_info_auxilar_eleitor(self):
        subinstance = self.eleitor.get_relacionamento()
        out = ['<dl>']
        if isinstance(subinstance, Aluno):
            out.append('<dt>Período Letivo:</dt><dd>{}</dd>'.format(subinstance.periodo_letivo))
            out.append('<dt>Ano Letivo:</dt><dd>{}</dd>'.format(subinstance.ano_letivo))

        elif isinstance(subinstance, Servidor):
            if subinstance.cargo_emprego:
                out.append('<dt>Cargo:</dt><dd>{}</dd>'.format(subinstance.cargo_emprego.nome))
            if subinstance.funcao:
                out.append('<dt>Atividade:</dt><dd>{}</dd>'.format(subinstance.atividade.nome))
            if subinstance.setor:
                out.append('<dt>Setor SUAP:</dt><dd>{}</dd>'.format(subinstance.setor.sigla))

        elif isinstance(subinstance, PrestadorServico):
            if subinstance.setor:
                out.append('<dt>Setor:</dt><dd>{}</dd>'.format(subinstance.setor.sigla))

        out.append('</dl>')
        return ''.join(out)
