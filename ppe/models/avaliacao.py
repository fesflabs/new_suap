import datetime

from comum.models import Ano
from djtools.db import models
from ppe.models import FormacaoTecnica

class TipoAvaliacao(models.ModelPlus):
    titulo = models.CharFieldPlus('Título', max_length=255)
    descricao = models.CharFieldPlus('Descrição', max_length=2000)
    sigla = models.CharFieldPlus('Sigla', max_length=10)
    ativo = models.BooleanField('Ativo', default=True)
    pre_requisito = models.ForeignKeyPlus("self", null=True, blank=True, verbose_name="Pré-requisito",
                                     on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Tipo de Avaliação'
        verbose_name_plural = 'Tipos de Avaliação'

    def __str__(self):
        return self.titulo

class PerguntaAvaliacao(models.ModelPlus):
    UNICA_ESCOLHA = 'Única Escolha'
    MULTIPLA_ESCOLHA = 'Múltipla Escolha'
    TEXTO = 'Texto'
    PARAGRAFO = 'Parágrafo'
    NUMERO = 'Número'
    SIM_NAO = 'Sim/Não'
    SIM_NAO_NA = 'Sim/Não/NA'
    ESCALA_0_5 = 'Escala 0 a 5'
    ESCALA_0_5_COMPETENCIA = 'Escala 0 a 5 COMPETÊNCIA'
    TEXTO_AVALIACAO = 'Texto de Avaliação'

    TIPO_RESPOSTA_CHOICES = ((TEXTO, TEXTO), (TEXTO_AVALIACAO, TEXTO_AVALIACAO), (PARAGRAFO, PARAGRAFO), (NUMERO, NUMERO), (SIM_NAO, SIM_NAO), (SIM_NAO_NA, SIM_NAO_NA), (ESCALA_0_5, ESCALA_0_5), (ESCALA_0_5_COMPETENCIA, ESCALA_0_5_COMPETENCIA), (UNICA_ESCOLHA, UNICA_ESCOLHA), (MULTIPLA_ESCOLHA, MULTIPLA_ESCOLHA))

    tipo_avaliacao = models.ForeignKeyPlus(TipoAvaliacao, related_name='pergunta_tipoavaliacao', verbose_name='Tipo de avaliação', on_delete=models.CASCADE)

    formacao_tecnica = models.ForeignKeyPlus(FormacaoTecnica, related_name='pergunta_formacaotecnica', verbose_name='Formação técnica',
                                           on_delete=models.CASCADE, null=True)
    pergunta = models.CharFieldPlus('Pergunta', max_length=2000)
    tipo_resposta = models.CharFieldPlus('Tipo de Resposta', max_length=100, choices=TIPO_RESPOSTA_CHOICES)
    obrigatoria = models.BooleanField('Resposta Obrigatória', default=True)
    ordem = models.IntegerField('Ordem', null=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['ordem']
        verbose_name = 'Pergunta da Avaliação'
        verbose_name_plural = 'Perguntas da Avaliação'

    def __str__(self):
        return self.pergunta


class OpcaoRespostaAvaliacao(models.ModelPlus):
    pergunta = models.ForeignKeyPlus(PerguntaAvaliacao, related_name='pergunta_avaliacao', verbose_name='Pergunta', on_delete=models.CASCADE)
    valor = models.CharFieldPlus('Opção de Resposta', max_length=400)
    pontuacao = models.CharFieldPlus('Pontuação', max_length=200, null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        ordering = ['id']
        verbose_name = 'Opção de Resposta da Avaliação'
        verbose_name_plural = 'Opções de Respostas das Avaliações'

    def __str__(self):
        return f'({self.pontuacao}) {self.valor} '

class Avaliacao(models.ModelPlus):
    AUTOAVALIACAO = 1
    AVALIACAO_CHEFIA = 2

    TIPO_AUTOAVALIACAO_CHOICES = ((AUTOAVALIACAO, "AUTOAVALIAÇÃO"), (AVALIACAO_CHEFIA, "AVALIAÇÃO DA CHEFIA"),)

    tipo_avaliacao = models.ForeignKeyPlus(TipoAvaliacao, verbose_name='avaliacao_tipoavalaicao', on_delete=models.CASCADE)
    trabalhador_educando = models.ForeignKeyPlus('ppe.TrabalhadorEducando', verbose_name='Trabalhador Educando', on_delete=models.CASCADE)
    papel_avalidor = models.IntegerFieldPlus('Tipo de Avaliação',  choices=TIPO_AUTOAVALIACAO_CHOICES, default=1, null=True, blank=True)
    atualizado_por = models.ForeignKeyPlus(
        'comum.Vinculo', null=True, verbose_name='Atualizado Por', related_name='avaliacao_atualizado_por',
        on_delete=models.CASCADE
    )
    data_atualizacao = models.DateFieldPlus(verbose_name='Data de Atualização', null=True, blank=True)
    data_validacao = models.DateFieldPlus(verbose_name='Data de Validação pelo Supervidor', null=True, blank=True)
    supervisor = models.ForeignKeyPlus('comum.User', verbose_name='Supervisor', null=True, blank=True)
    aprovada = models.BooleanField(verbose_name='Aprovada', null=True, blank=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        unique_together = ('tipo_avaliacao', 'trabalhador_educando', 'papel_avalidor')

    def save(self, *args, **kwargs):
        self.data_atualizacao = datetime.date.today()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"/ppe/avaliacao_trabalhador_educando_confirmacao/{self.id}/"

    def get_respostas(self):
        respostas = RespostaAvaliacao.objects.filter(avaliacao=self).order_by('pergunta__ordem')
        ids_respostas = list()
        ids_perguntas = list()
        for resposta in respostas:
            if resposta.pergunta_id not in ids_perguntas:
                ids_perguntas.append(resposta.pergunta_id)
                ids_respostas.append(resposta.id)

        return respostas.filter(id__in=ids_respostas)


    def pode_ser_avaliada_chefia(self):
        qs_avaliacao = Avaliacao.objects.filter(tipo_avaliacao=self.tipo_avaliacao,
                                                papel_avalidor=Avaliacao.AVALIACAO_CHEFIA)
        if qs_avaliacao.exists() and self.papel_avalidor == Avaliacao.AUTOAVALIACAO:
            return False
        return True




class RespostaAvaliacao(models.ModelPlus):
    avaliacao = models.ForeignKeyPlus(Avaliacao, related_name='resposta_avaliacao', verbose_name='Avaliação', on_delete=models.CASCADE)
    pergunta = models.ForeignKeyPlus(PerguntaAvaliacao, related_name='resposta_pergunta_avaliacao', verbose_name='Pergunta', on_delete=models.CASCADE)
    resposta = models.ForeignKeyPlus(OpcaoRespostaAvaliacao, related_name='resposta_escolhida', verbose_name='Resposta', on_delete=models.CASCADE, null=True)
    valor_informado = models.TextField('Resposta', null=True, blank=True)

    class Meta:
        verbose_name = 'Resposta da Avaliacão'
        verbose_name_plural = 'Respostas da Avaliacão'

    def __str__(self):
        return 'Resposta da Pergunta {}'.format(self.pergunta)

    def get_resposta(self):
        if self.pergunta.tipo_resposta == PerguntaAvaliacao.MULTIPLA_ESCOLHA:
            return ', '.join(RespostaAvaliacao.objects.filter(avaliacao=self.avaliacao, pergunta=self.pergunta).values_list('resposta__valor', flat=True))
        else:
            return self.resposta or self.valor_informado

    def eh_multipla_escolha(self):
        return self.pergunta.tipo_resposta == PerguntaAvaliacao.MULTIPLA_ESCOLHA





class ConfiguracaoMonitoramento(models.ModelPlus):
    ano = models.ForeignKeyPlus(Ano, verbose_name='Ano', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Configuração Monitoramento'
        verbose_name_plural = 'Configurações Monitoramento'

    def __str__(self):
        return f'Configuração Monitoramento {self.ano}'


class EtapaMonitoramento(models.ModelPlus):

    configuracao = models.ForeignKeyPlus(ConfiguracaoMonitoramento, verbose_name='etata_configuracao',
                                           on_delete=models.CASCADE)
    tipo_avaliacao = models.ForeignKeyPlus(TipoAvaliacao, verbose_name='Instrumento  de monitoramento', on_delete=models.CASCADE)
    data_inicio = models.DateFieldPlus(verbose_name='Data de Início', null=False, blank=False)

    class Meta:
        verbose_name = 'Etapa Monitoramento'
        verbose_name_plural = 'Etapas Monitoramento'

    def __str__(self):
        return f'Etapa de Monitoramento {self.tipo_avaliacao}'

