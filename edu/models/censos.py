from djtools.db import models
from edu.models.logs import LogModel
from rh.models import UnidadeOrganizacional


class RegistroEducacenso(LogModel):

    ano_censo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano do Censo', null=False, blank=False)
    numero_registro = models.CharFieldPlus(verbose_name='Número do Registro', null=False, blank=False)
    privado = models.BooleanField(verbose_name='Privado', default=True, help_text='O questionário ficará inacessível para repostas dos campi enquanto estiver privado.')

    class Meta:
        verbose_name = 'Registro Educacenso'
        verbose_name_plural = 'Registros Educacenso'

    def __str__(self):
        return f'Educacenso {self.ano_censo} - Registro {self.numero_registro}'

    def get_absolute_url(self):
        return f'/edu/registroeducacenso/{self.pk}/'

    def get_respostas_por_campus(self, sigla_campus=None):
        resultados = []
        qs_campi = UnidadeOrganizacional.objects.campi()
        if sigla_campus:
            campus = qs_campi.get(sigla=sigla_campus)
            resultados.extend(RespostaEducacenso.objects.filter(questao__registro_id=self.pk, campus_id=campus.id))
        else:
            campi = qs_campi.all()
            for uo in campi:
                qs = RespostaEducacenso.objects.filter(questao__registro_id=self.pk, campus_id=uo.id)
                resultados.append({uo.sigla: qs})
        return resultados

    def get_questoes_para_resposta(self, campus_id):
        return RespostaEducacenso.objects.filter(questao__registro_id=self.pk, campus_id=campus_id)

    def publicar(self):
        self.privado = False
        self.save()

    def fechar(self):
        self.privado = True
        self.save()


class QuestaoEducacenso(LogModel):

    TIPO_REPOSTA_SIM_NAO = '1'
    TIPO_RESPOSTA_NUMERICA = '2'
    TIPO_RESPOSTA = [[TIPO_REPOSTA_SIM_NAO, 'Sim/Não'], [TIPO_RESPOSTA_NUMERICA, 'Numérica']]

    TIPO_OBRIGATORIEDADE_OBRIGATORIO = '1'
    TIPO_OBRIGATORIEDADE_CONDICIONAL = '2'
    TIPO_OBRIGATORIEDADE_NAO_OBRIGATORIO = '3'
    TIPO_OBRIGATORIEDADE = [[TIPO_OBRIGATORIEDADE_OBRIGATORIO, 'Obrigatório'], [TIPO_OBRIGATORIEDADE_CONDICIONAL, 'Condicional'], [TIPO_OBRIGATORIEDADE_NAO_OBRIGATORIO, 'Não Obrigatório']]

    registro = models.ForeignKeyPlus('edu.RegistroEducacenso', verbose_name='Registro Educacenso', null=False, blank=False)
    numero_campo = models.PositiveIntegerField(verbose_name='Número do Campo', null=False, blank=False)
    nome_campo = models.CharFieldPlus(verbose_name='Nome do Campo', null=False, blank=False)
    resposta_privada = models.BooleanField(verbose_name='Resposta Privada', default=False, help_text='Marque esta opção caso este campo deva ser respondido somente pelo Administrador Acadêmico.')
    regra_resposta = models.TextField(verbose_name='Regra de Preenchimento', null=True, blank=True)
    tipo_resposta = models.CharFieldPlus(max_length=1, verbose_name='Tipo de Resposta', null=False, blank=False, choices=TIPO_RESPOSTA)
    tipo_obrigatoriedade = models.CharFieldPlus(max_length=1, verbose_name='Tipo de Obrigatoriedade', null=False, blank=False, choices=TIPO_OBRIGATORIEDADE)

    class Meta:
        verbose_name = 'Questão Educacenso'
        verbose_name_plural = 'Questões Educacenso'
        ordering = ('numero_campo',)

    def __str__(self):
        return f'{self.numero_campo} - {self.nome_campo}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for uo in UnidadeOrganizacional.objects.campi().all():
            RespostaEducacenso.objects.get_or_create(questao_id=self.id, campus_id=uo.id)


class RespostaEducacenso(LogModel):

    questao = models.ForeignKeyPlus('edu.QuestaoEducacenso', verbose_name='Questão', null=False, blank=False)
    campus = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus', null=False, blank=False)
    resposta = models.CharFieldPlus(verbose_name='Resposta', null=True, blank=True)

    class Meta:
        ordering = ('campus__sigla', 'questao__numero_campo')

    def __str__(self):
        return 'Resposta do Campus {} para a questão #{}: {}'.format(
            self.campus.sigla,
            self.questao.numero_campo,
            self.get_resposta_display(),
        )

    def get_resposta_display(self):
        return self.resposta == 'True' and 'Sim' or self.resposta == 'False' and 'Não' or self.resposta

    def get_resposta_layout_educacenso(self):
        return self.resposta == 'True' and '1' or self.resposta == '0' and 'Não' or self.resposta or ''

    # respondentes (secretario, diretor acad. e geral)
