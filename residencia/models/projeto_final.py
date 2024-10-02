import uuid
import datetime
from django.conf import settings
from comum.models import Sala
from comum.utils import tl
from djtools.db import models
from djtools.utils import send_mail
from rh.models import Servidor, PessoaFisica
from residencia.models import LogResidenciaModel, MatriculaPeriodo

PERIODO_LETIVO_CHOICES = settings.PERIODO_LETIVO_CHOICES

class ProjetoFinalResidencia(LogResidenciaModel):
    TIPO_PROJETO_CHOICES = [
        ['Memorial de Formação','Memorial de Formação'],
        ['Relato de Experiência','Relato de Experiência'],
        ['Orientação do Trabalho de Conclusão de Residência','Orientação do Trabalho de Conclusão de Residência']
    ]

    SITUACAO_APROVADO = 1
    SITUACAO_REPROVADO = 2
    SITUACAO_CHOICES = [[SITUACAO_APROVADO, 'Aprovado'], [SITUACAO_REPROVADO, 'Reprovado']]

    # Dados Gerais
    matricula_periodo = models.ForeignKeyPlus(MatriculaPeriodo)
    titulo = models.CharFieldPlus('Título do Trabalho', null=False, blank=False)
    resumo = models.TextField('Resumo do Trabalho', null=False, blank=False)
    tipo = models.CharFieldPlus(choices=TIPO_PROJETO_CHOICES, verbose_name='Tipo de Trabalho', null=False, blank=False)
    informacao_complementar = models.TextField('Informações Complementares', null=True, blank=True)
    documento = models.FileFieldPlus('Arquivo Digitalizado do Projeto', upload_to='residencia/projeto_final/', null=True, blank=True)
    documento_final = models.FileFieldPlus('Arquivo Final Digitalizado do Projeto', upload_to='residencia/projeto_final/', null=True, blank=True)

    # Dados da Orientação
    orientador = models.ForeignKeyPlus(Servidor, limit_choices_to={'user__groups__name': "Preceptor(a)"}, related_name='orientador_set', verbose_name='Orientador', null=True, blank=True)
    coorientadores = models.ManyToManyFieldPlus(PessoaFisica, related_name='coorientadores_residencia_set', verbose_name='Coorientadores Residencia', blank=True)

    # Dados da Defesa
    data_defesa = models.DateTimeFieldPlus('Data da Apresentação', null=True, blank=True)
    data_deposito = models.DateTimeFieldPlus('Data de Depósito ', null=True, blank=True)
    local_defesa = models.ForeignKeyPlus(Sala, verbose_name='Local', null=True, blank=True)
    defesa_online = models.BooleanField(verbose_name='Defesa Online', default=False, blank=True, help_text='Marque essa opção caso os membros da banca tenham acompanhado ou acompanharão a defesa virtualmente.')

    # Dados da Banca
    presidente = models.ForeignKeyPlus(Servidor, limit_choices_to={'user__groups__name': "Preceptor(a)"}, related_name='presidente_set', verbose_name='Presidente', null=True, blank=True)
    examinador_interno = models.ForeignKeyPlus(PessoaFisica, related_name='examinador_interno_residencia_set', verbose_name='Examinador Interno', null=True, blank=True)
    examinador_externo = models.ForeignKeyPlus(PessoaFisica, related_name='examinador_externo_residencia_set', verbose_name='Segundo Examinador', null=True, blank=True)
    is_examinador_externo = models.BooleanField('Externo', default=True, help_text='Marque essa opção caso o segundo examinador seja externo.')

    terceiro_examinador = models.ForeignKeyPlus(PessoaFisica, related_name='terceiro_examinador_residencia_set', verbose_name='Terceiro Examinador', null=True, blank=True)
    is_terceiro_examinador_externo = models.BooleanField('Externo', default=True, help_text='Marque essa opção caso o terceiro examinador seja externo.')

    suplente_interno = models.ForeignKeyPlus(PessoaFisica, related_name='suplente_interno_residencia_set', verbose_name='Suplente Interno', null=True, blank=True)
    suplente_externo = models.ForeignKeyPlus(PessoaFisica, related_name='suplente_externo_residencia_set', verbose_name='Segundo Suplente', null=True, blank=True)
    is_suplente_externo = models.BooleanField('Externo', default=True, help_text='Marque essa opção caso o segundo suplente seja externo.')

    terceiro_suplente = models.ForeignKeyPlus(PessoaFisica, related_name='terceiro_suplente_residencia_set', verbose_name='Terceiro Suplente', null=True, blank=True)
    is_terceiro_suplente_externo = models.BooleanField('Externo', default=True, help_text='Marque essa opção caso o terceiro suplente seja externo.')
    # Dados Resultado
    resultado_data = models.DateTimeFieldPlus('Data da Defesa', null=True, blank=True)
    nota = models.NotaField(null=True, blank=True)
    situacao = models.PositiveIntegerField("Situação", choices=SITUACAO_CHOICES, null=True, blank=True)

    ata = models.FileFieldPlus('Ata da Defesa', upload_to='residencia/projeto_final_ata/', null=True, blank=True)
    documento_url = models.CharFieldPlus('Link para Arquivo Digitalizado do Projeto', null=True, blank=True)
    documento_final_url = models.CharFieldPlus('Link Final para Arquivo Digitalizado do Projeto', null=True, blank=True)

    class Meta:
        verbose_name = 'Trabalho de Conclusão de Residência'
        verbose_name_plural = 'Trabalhos de Conclusão de Residência'

    def get_absolute_url(self):
        return '/residencia/visualizar_projeto_final/{}/'.format(self.pk)

    def get_residente(self):
        return self.matricula_periodo.residente

    def get_nome_documento(self):
        return self.documento.name.split('/')[-1]

    def get_nome_ata(self):
        return self.ata and self.ata.name.split('/')[-1] or ''

    def get_ano_periodo_letivo(self):
        return '{}.{}'.format(self.matricula_periodo.ano_letivo, self.matricula_periodo.periodo_letivo)

    def get_titulo_participante(self, participante='orientador'):
        pessoa = getattr(self, participante, None)
        if participante == 'orientador' or participante == 'presidente':
            pessoa = pessoa.vinculo.relacionamento.pessoa_fisica
        sexo = pessoa and pessoa.sexo or 'M'

        if participante == 'examinador_interno':
            participacao = 'Examinador Interno'
            if sexo == 'F':
                participacao = 'Examinadora Interna'

        elif participante == 'examinador_externo':
            if self.is_examinador_externo:
                participacao = 'Examinador Externo'
                if sexo == 'F':
                    participacao = 'Examinadora Externa'
            else:
                participacao = 'Examinador Interno'
                if sexo == 'F':
                    participacao = 'Examinadora Interna'

        elif participante == 'terceiro_examinador':
            if self.is_terceiro_examinador_externo:
                participacao = 'Examinador Externo'
                if sexo == 'F':
                    participacao = 'Examinadora Externa'
            else:
                participacao = 'Examinador Interno'
                if sexo == 'F':
                    participacao = 'Examinadora Interna'

        elif participante == 'suplente_interno':
            participacao = 'Examinador Suplente Interno'
            if sexo == 'F':
                participacao = 'Examinadora Suplente Interna'

        elif participante == 'suplente_externo':
            if self.is_suplente_externo:
                participacao = 'Examinador Suplente Externo'
                if sexo == 'F':
                    participacao = 'Examinadora Suplente Interna'
            else:
                participacao = 'Examinador Suplente Interno'
                if sexo == 'F':
                    participacao = 'Examinadora Suplente Interna'

        elif participante == 'terceiro_suplente':
            if self.is_terceiro_suplente_externo:
                participacao = 'Examinador Suplente Externo'
                if sexo == 'F':
                    participacao = 'Examinadora Suplente Interna'
            else:
                participacao = 'Examinador Suplente Interno'
                if sexo == 'F':
                    participacao = 'Examinadora Suplente Interna'

        elif participante == 'presidente':
            participacao = 'Presidente'

        else:
            participacao = 'Orientador'
            if sexo == 'F':
                participacao = 'Orientadora'
        if self.coorientadores.filter(pk=pessoa.pk).exists():
            participacao = 'Coorientador{} e {}'.format('a' if sexo == 'F' else '', participacao)
        return sexo, participacao, pessoa

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.resultado_data:
            self.matricula_periodo.residente.atualizar_situacao('Lançamento de Projeto Final')

    def delete(self, *args, **kwargs):
        if not self.matricula_periodo.residente.is_concluido() or tl.get_user().is_superuser:
            super().delete(*args, **kwargs)
            if self.resultado_data:
                self.matricula_periodo.residente.atualizar_situacao('Exclusão de Projeto Final')
        else:
            raise Exception('Impossível excluir projeto final de Residente concluído.')

    def get_url_ata(self):
        ata_eletronica = self.ataeletronica_set.first()
        if ata_eletronica:
            return '/residencia/visualizar_ata_eletronica/{}/'.format(ata_eletronica.pk)
        else:
            return '/residencia/ata_projeto_final_pdf/{}/'.format(self.pk)

    def get_assinaturas_eletronicas_pendentes(self):
        return AssinaturaAtaEletronicaResidencia.objects.filter(ata__projeto_final=self, data__isnull=True)

    def get_ata_eletronica(self):
        return None

    def pode_ser_editado(self):
        ata_eletronica = self.get_ata_eletronica()
        return ata_eletronica is None or not ata_eletronica.assinaturaataeletronica_set.filter(data__isnull=False).exists()


class MembroBancaResidencia(LogResidenciaModel):
    nome = models.CharFieldPlus('Nome')
    email = models.EmailField('Email')
    sexo = models.CharField(max_length=1, null=True, choices=[['M', 'Masculino'], ['F', 'Feminino']])
    instituicao = models.CharFieldPlus('Instituição')
    formacao = models.ForeignKeyPlus('edu.Modalidade', verbose_name='Formação', null=False, blank=False, on_delete=models.CASCADE)

    fieldsets = (('Dados Gerais', {'fields': ('nome', 'email', 'sexo', 'instituicao', 'formacao')}),)

    class Meta:
        verbose_name = 'Membro da Banca'
        verbose_name_plural = 'Membros da Banca'

    def get_absolute_url(self):
        return '/residencia/visualizar/residencia/membrobancaresidencia/{:d}/'.format(self.pk)


class AtaEletronicaResidencia(models.ModelPlus):
    projeto_final = models.ForeignKeyPlus(ProjetoFinalResidencia, verbose_name='Projeto Final')
    consideracoes = models.TextField(verbose_name='Considerações')

    class Meta:
        verbose_name = 'Ata Eletrônica'
        verbose_name_plural = 'Atas Eletrônicas'

    def __str__(self):
        return 'Ata - {}'.format(self.projeto_final)

    def get_assinaturas(self):
        return self.assinaturaataeletronica_set.all()

    def criar_assinaturas(self):
        qs = ProjetoFinalResidencia.objects.filter(pk=self.projeto_final.pk).values(
            'presidente__vinculo__pessoa', 'examinador_interno', 'examinador_externo',
            'terceiro_examinador', 'suplente_interno', 'suplente_externo', 'terceiro_suplente'
        )
        pks = set()
        for item in qs:
            for pk in item.values():
                if pk:
                    pks.add(pk)
        for pk in pks:
            if not AssinaturaAtaEletronicaResidencia.objects.filter(ata=self, pessoa_fisica_id=pk).exists():
                AssinaturaAtaEletronicaResidencia.objects.get_or_create(ata=self, pessoa_fisica_id=pk)
        AssinaturaAtaEletronicaResidencia.objects.filter(ata=self, data__isnull=True).exclude(pessoa_fisica_id__in=pks).delete()


class AssinaturaAtaEletronicaResidencia(models.ModelPlus):
    ata = models.ForeignKeyPlus(AtaEletronicaResidencia, verbose_name='Ata Eletrônica')
    pessoa_fisica = models.ForeignKeyPlus(PessoaFisica, verbose_name='Pessoa', null=True, blank=True)
    data = models.DateTimeFieldPlus(verbose_name='Data da Assinatura', null=True)
    chave = models.CharFieldPlus(verbose_name='Chave', null=True)

    class Meta:
        verbose_name = 'Assinatura de Ata Eletrônica'
        verbose_name_plural = 'Assinaturas de Atas Eletrônicas'

    def __str__(self):
        return 'Assinatura de {} da ata  {}'.format(self.pessoa_fisica, self.ata.projeto_final)

    def assinar(self):
        self.data = datetime.datetime.now()
        self.chave = uuid.uuid1().hex
        self.save()

    def enviar_email(self):
        titulo = '[SUAP] Solicitação de Assinatura de Ata'
        url = '<a href="{}/admin/residencia/ataeletronicaresidencia/?tab=tab_pendentes">{}/admin/residencia/ataeletronica/</a>'.format(
            settings.SITE_URL, settings.SITE_URL
        )
        texto = 'Uma solicitação de asssinatura de ata eletrônica foi endereçada a você. Para assiná-la, acesse {}.'.format(url)
        email_destino = [self.pessoa_fisica.email, self.pessoa_fisica.email_secundario]
        return send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, email_destino)

    def save(self, *args, **kwargs):
        if not self.pk:
            self.enviar_email()
        super().save(*args, **kwargs)
