import os
import string
from decimal import Decimal

from datetime import date, datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models.aggregates import Sum
from django.shortcuts import get_object_or_404

from comum.models import User
from djtools.db import models
from djtools.db.models import ModelPlus
from django.template import defaultfilters

from comum.utils import tl
from djtools.storages import cache_file
from rh.models import UnidadeOrganizacional

# Modelos do PDI e Farol de Desempenho -------------------------------------------------------------------------------------------------------


class PDI(ModelPlus):
    qtd_anos = models.IntegerField(verbose_name='Duração em anos', null=True)
    ano_inicial_pdi = models.ForeignKeyPlus('comum.Ano', related_name='ano_inicial_pdi_plan_estrategico', verbose_name='Ano Inicial', help_text='Vigência inicial do PDI')
    ano_final_pdi = models.ForeignKeyPlus('comum.Ano', related_name='ano_final_pdi_plan_estrategico', verbose_name='Ano Final', help_text='Vigência final do PDI')
    documento = models.FileFieldPlus(upload_to='plan_estrategico/anexos/', max_length=255, verbose_name='Documento PDI')
    mapa_estrategico = models.FileFieldPlus(upload_to='plan_estrategico/anexos/', max_length=255, verbose_name='Mapa Estratégico', null=True, blank=True)
    manual = models.FileFieldPlus(upload_to='plan_estrategico/anexos/', max_length=255, verbose_name='Manual de Indicadores', null=True, blank=True)
    valor_faixa_verde = models.DecimalField(verbose_name='Valor Inicial da Faixa Verde', max_digits=12, decimal_places=2, default=0)
    valor_faixa_amarela = models.DecimalField(verbose_name='Valor Inicial da Faixa Amarela', max_digits=12, decimal_places=2, default=0)
    valor_faixa_vermelha = models.DecimalField(verbose_name='Valor Inicial da Faixa Vermelha ', max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'PDI'
        verbose_name_plural = 'PDIs'
        unique_together = ('ano_inicial_pdi', 'ano_final_pdi')

    def __str__(self):
        return f'De {self.ano_inicial_pdi} até {self.ano_final_pdi}'


class Perspectiva(ModelPlus):
    SEARCH_FIELDS = ['sigla', 'nome']

    sigla = models.CharFieldPlus('Sigla')
    nome = models.CharFieldPlus('Nome')
    descricao = models.TextField('Descrição', blank=True)

    class Meta:
        verbose_name = 'Perspectiva'
        verbose_name_plural = 'Perspectivas'

    def __str__(self):
        return self.nome


class PDIPerspectiva(ModelPlus):
    pdi = models.ForeignKey(PDI, related_name="perspectivas", verbose_name='PDI', on_delete=models.CASCADE)
    perspectiva = models.ForeignKey('Perspectiva', verbose_name='Perspectiva', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Perspectiva do PDI'
        verbose_name_plural = 'Perspectivas do PDI'

        unique_together = ('pdi', 'perspectiva')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.perspectiva.sigla}'


class UnidadeGestora(ModelPlus):
    SEARCH_FIELDS = ['setor_equivalente']
    TIPO_DIRETORIA = 'Diretoria Sistêmica'
    TIPO_PRO_REITORIA = 'Pró-Reitoria'
    TIPO_CAMPUS = 'Campus'
    TIPO_CHOICES = ((TIPO_DIRETORIA, TIPO_DIRETORIA), (TIPO_PRO_REITORIA, TIPO_PRO_REITORIA), (TIPO_CAMPUS, TIPO_CAMPUS))
    pdi = models.ForeignKey(PDI, on_delete=models.CASCADE)
    setor_equivalente = models.ForeignKey('rh.Setor', verbose_name='Setor Equivalente', related_name='unidadegestora_setor', on_delete=models.CASCADE)
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES)
    codigo_projeto = models.CharFieldPlus(verbose_name='Código para Projeto', max_length=1, null=True, blank=True)
    recurso_total = models.BooleanField('Pode Alocar 100% do Recurso na Etapa Especial?', default=False)

    class Meta:
        verbose_name = 'Unidade Gestora'
        verbose_name_plural = 'Unidades Gestoras'

        ordering = ('tipo', 'setor_equivalente__nome')
        unique_together = ('pdi', 'setor_equivalente')

    def __str__(self):
        return f'{self.setor_equivalente.sigla} - {self.setor_equivalente.nome}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def participa_planoatividade(self):
        if UnidadeGestoraEtapa.objects.filter(unidade_gestora=self).exists():
            return True
        return False


class ObjetivoEstrategico(ModelPlus):
    sigla = models.CharFieldPlus('Sigla')
    descricao = models.TextField('Descrição')

    class Meta:
        verbose_name = 'Objetivo Estratégico'
        verbose_name_plural = 'Objetivos Estratégicos'

    def __str__(self):
        return f'{self.descricao}'


class PDIObjetivoEstrategico(ModelPlus):
    pdi = models.ForeignKey(PDI, on_delete=models.CASCADE)
    pdi_perspectiva = models.ForeignKey(PDIPerspectiva, verbose_name='Perspectiva', on_delete=models.CASCADE)
    objetivo = models.ForeignKey(ObjetivoEstrategico, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Objetivo Estratégico do PDI'
        verbose_name_plural = 'Objetivos Estratégicos do PDI'
        unique_together = (('pdi', 'objetivo'),)

    def __str__(self):
        return f'{self.objetivo.sigla} - {self.objetivo.descricao}'

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.pdi = self.pdi_perspectiva.pdi
        super().save(*args, **kwargs)

    def get_objetivo_valor_meta(self, uo=None, ano_base=None):
        total_relevancia = 0
        total = 0
        for ind in ObjetivoIndicador.objects.filter(objetivo_estrategico=self).exclude(indicador__indicador__indicador_acompanhamento=True):
            if ind.indicador.verificar_variavel_ideal_vazia(uo, ano_base):
                return 'Indicadores com Variáveis não Informadas.'
            total += ind.indicador.get_metaindicador_valor(uo, ano_base) * ind.relevancia
            total_relevancia += ind.relevancia
        if total_relevancia == 0:
            total = total
        else:
            total = total / total_relevancia
        if total_relevancia != 100:
            return 'Relevância Diferente de 100%'
        return total

    def get_objetivo_valor_real(self, uo=None, ano_base=None):
        total_relevancia = 0
        total = 0
        for ind in ObjetivoIndicador.objects.filter(objetivo_estrategico=self).exclude(indicador__indicador__indicador_acompanhamento=True):
            if ind.indicador.verificar_variavel_real_vazia(uo, ano_base) or ind.indicador.verificar_variavel_ideal_vazia(uo, ano_base):
                return 'Indicadores com variáveis não informadas.'

            if ind.indicador.get_porcentagem_alcancada(uo, ano_base) < 100:
                total += ind.indicador.get_porcentagem_alcancada(uo, ano_base) * ind.relevancia
            else:
                total += ind.relevancia * 100

            total_relevancia += ind.relevancia
        if total_relevancia == 0:
            total = total
        else:
            total = total / total_relevancia
        if total_relevancia != 100:
            return 'Relevância diferente de 100%'
        return total

    def get_status_farol_objetivo(self, uo=None, ano_base=None):
        porcentagem = self.get_objetivo_valor_real(uo, ano_base)
        if not type(porcentagem) is str:
            if self.pdi.valor_faixa_verde <= porcentagem:
                return 'Alcançado'
            elif self.pdi.valor_faixa_amarela <= porcentagem < self.pdi.valor_faixa_verde:
                return 'Parcialmente'
            elif self.pdi.valor_faixa_vermelha <= porcentagem < self.pdi.valor_faixa_amarela:
                return 'Não Alcançado'
        return 'Não Informado'


class ProjetoEstrategico(ModelPlus):
    TIPO_ROTINEIRO = 'Rotineiro'
    TIPO_ESTRATEGICO = 'Estratégico'

    TIPO_PROJETO = ((TIPO_ROTINEIRO, TIPO_ROTINEIRO), (TIPO_ESTRATEGICO, TIPO_ESTRATEGICO))

    codigo = models.CharField(verbose_name='Código', max_length=2, null=True)
    pdi = models.ForeignKey(PDI, verbose_name='PDI', on_delete=models.CASCADE)
    nome = models.CharField(max_length=100, verbose_name='Nome do Projeto')
    descricao = models.TextField('Descrição')
    objetivo_estrategico = models.ManyToManyField(PDIObjetivoEstrategico, verbose_name='Objetivo Estratégico')
    unidade_gestora = models.ForeignKey(UnidadeGestora, verbose_name='Unidade Gestora', on_delete=models.CASCADE)
    recurso_total = models.DecimalFieldPlus('Recurso Total')
    meta_projeto = models.DecimalFieldPlus('Meta do Projeto', help_text='Resultado esperado do projeto')
    unidade_medida = models.CharField(max_length=50, verbose_name='Unidade de Medida', help_text='Unidade de medida da meta')
    data_inicio = models.DateField(verbose_name='Data Inicial')
    data_fim = models.DateField(verbose_name='Data Final')
    tipo = models.CharFieldPlus('Tipo', choices=TIPO_PROJETO, default=TIPO_ESTRATEGICO)
    anexo = models.FileFieldPlus(upload_to='plan_estrategico/anexos/', max_length=255, verbose_name='Projeto Estratégico')

    class Meta:
        verbose_name = 'Projeto Estratégico'
        verbose_name_plural = 'Projetos Estratégicos'

    def pode_editar_projeto(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if (
            usuario.has_perm('plan_estrategico.change_projetoestrategico')
            and self.unidade_gestora.setor_equivalente == get_setor_unidade_gestora(user=usuario)
            and not self.projetoplanoatividade_set.all().exists()
        ):
            return True
        return False

    def pode_excluir_projeto(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if (
            usuario.has_perm('plan_estrategico.delete_projetoestrategico')
            and self.unidade_gestora.setor_equivalente == get_setor_unidade_gestora(user=usuario)
            and not self.projetoplanoatividade_set.all().exists()
        ):
            return True
        return False

    def save(self, *args, **kwargs):
        if self.codigo is None:
            codigos_disponiveis = list(string.ascii_uppercase)
            codigos_usados = []

            for projeto in ProjetoEstrategico.objects.filter(unidade_gestora=self.unidade_gestora):
                codigos_usados.append(projeto.codigo[1])

            for codigo_usado in codigos_usados:
                codigos_disponiveis.remove(codigo_usado)

            if self.unidade_gestora.codigo_projeto:
                self.codigo = self.unidade_gestora.codigo_projeto + codigos_disponiveis[0]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.codigo}-{self.nome}'

    def get_valor_total_etapas(self):
        total = Decimal('0')
        if self.etapaprojeto_set.all().exists():
            for etapa in EtapaProjeto.objects.filter(projeto=self):
                total += etapa.valor_etapa
        return total

    def get_saldo_projeto(self):
        return self.recurso_total - self.get_valor_total_etapas()


class EtapaProjeto(ModelPlus):
    codigo = models.IntegerField(verbose_name='Código da Etapa', null=True)
    projeto = models.ForeignKey(ProjetoEstrategico, verbose_name='Projeto Estratégico', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=100, verbose_name='Descrição')
    data_inicio = models.DateField(verbose_name='Data Inicial')
    data_fim = models.DateField(verbose_name='Data Final')
    objetivo_etapa = models.CharField(max_length=100, verbose_name='Objetivo', null=True)
    responsaveis_etapa = models.CharField(max_length=100, verbose_name='Setores Responsáveis', null=True)
    meta_etapa = models.CharField(max_length=50, verbose_name='Meta da Etapa', null=True)
    unidade_medida = models.CharField(max_length=50, verbose_name='Unidade de Medida', null=True)
    valor_etapa = models.DecimalFieldPlus('Valor Etapa', null=True)

    class Meta:
        verbose_name = 'Etapa do Projeto'
        verbose_name_plural = 'Etapas dos Projetos'

    def __str__(self):
        return f'{self.descricao}'

    def pode_editar_etapa(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if (
            usuario.has_perm('plan_estrategico.change_etapaprojeto')
            and self.projeto.unidade_gestora.setor_equivalente == get_setor_unidade_gestora(user=usuario)
            and not self.etapaprojetoplanoatividade_set.all().exists()
        ):
            return True
        return False

    def pode_excluir_etapa(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if (
            usuario.has_perm('plan_estrategico.delete_etapaprojeto')
            and self.projeto.unidade_gestora.setor_equivalente == get_setor_unidade_gestora(user=usuario)
            and not self.etapaprojetoplanoatividade_set.all().exists()
        ):
            return True
        return False


class Indicador(ModelPlus):
    DECIMAL_0 = 0
    DECIMAL_1 = 1
    DECIMAL_2 = 2
    DECIMAL_3 = 3
    DECIMAL_4 = 4

    DECIMAL_CHOICES = ((DECIMAL_0, DECIMAL_0), (DECIMAL_1, DECIMAL_1), (DECIMAL_2, DECIMAL_2), (DECIMAL_3, DECIMAL_3), (DECIMAL_4, DECIMAL_4))

    DIRECAO_ALTA = 'Quanto mais melhor'
    DIRECAO_BAIXA = 'Quanto menos melhor'
    DIRECAO_CHOICES = ((DIRECAO_ALTA, DIRECAO_ALTA), (DIRECAO_BAIXA, DIRECAO_BAIXA))

    TIPO_PERCENTUAL = 'Percentual'
    TIPO_ABSOLUTO = 'Absoluto'
    TIPO_VALOR = ((TIPO_PERCENTUAL, TIPO_PERCENTUAL), (TIPO_ABSOLUTO, TIPO_ABSOLUTO))

    sigla = models.CharFieldPlus('Sigla')
    descricao = models.CharFieldPlus('Descrição')
    finalidade = models.TextField('Finalidade', blank=True)
    forma_calculo = models.CharField('Forma de Cálculo', max_length=100)
    casas_decimais = models.PositiveIntegerField('Casas decimais', choices=DECIMAL_CHOICES, default=DECIMAL_0)
    tendencia = models.CharField('Tendência', max_length=20, choices=DIRECAO_CHOICES, default=DIRECAO_ALTA)
    tipo = models.CharFieldPlus('Tipo de Exibição', choices=TIPO_VALOR, default=TIPO_ABSOLUTO)
    calcular_media = models.BooleanField('Calcular Média', default=False, help_text='Ao marcar esta opção, o valor Hoje exibido para o valor da instituição será consolidado pela média dos resultados das unidades, excluindo-se zeros.')
    indicador_acompanhamento = models.BooleanField('Indicador de acompanhamento', default=False, help_text='Ao marcar esta opção, não haverá comparação Hoje X Meta, nem cor no farol.')
    sem_escalonamento_trimestral = models.BooleanField('Sem Escalonamento Trimestral', default=False, help_text='Ao marcar esta opção, a meta trimestral fica igual à meta anual.')

    class Meta:
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'

    def __str__(self):
        return f'{self.descricao}'

    def clean(self):
        errors = dict()
        if len(self.get_variaveis()) != 1 and self.calcular_media:
            errors['calcular_media'] = ['A média só pode ser aplicada quando se trabalha com apenas uma variável.']

        if errors:
            raise ValidationError(errors)

        return super().clean()

    def get_variaveis(self):
        variaveis = []
        for token in self.forma_calculo.replace(' ', '').replace(')', '').replace('(', '').replace('*', ':').replace('/', ':').replace('+', ':').replace('-', ':').split(':'):
            if not token.isdigit():
                try:
                    variavel = Variavel.objects.get(sigla=token)
                except Variavel.DoesNotExist:
                    return []
                variaveis.append(variavel)
        return variaveis

    def get_formula_valor(self, uo=None, ano_base=None):
        index = None
        if uo:
            uo = get_object_or_404(UnidadeOrganizacional, pk=uo.id)
            index = uo.sigla

        if hasattr(self, 'formula_valorada'):
            if index in self.formula_valorada:
                return self.formula_valorada[index]
        else:
            self.formula_valorada = {}
        formula = ' {} '.format(
            self.forma_calculo.replace(' ', '').replace(')', ' ) ').replace('(', ' ( ').replace('*', ' * ').replace('/', ' / ').replace('+', ' + ').replace('-', ' - ')
        )
        for variavel in self.get_variaveis():
            # O ajuste '{}.0' garante que as divisões internas não serão truncadas.
            # Ex: Com o referido ajuste, a fórmula '(  (1053+187)  * 1 )  +  (  (33+39)  / 2 )  +  (23/ 4 )  ) tem
            # como valor final 1281.75, já sem esse ajuste seria exibido 1281.
            somatorio_variavel = variavel.get_valor(uo=uo, ano_base=ano_base)
            if self.calcular_media and not uo:
                qtd_variaveis_com_valor = VariavelCampus.objects.filter(variavel=variavel, ano=ano_base, valor_real__gt=0).count()
                if qtd_variaveis_com_valor:
                    somatorio_variavel = somatorio_variavel / qtd_variaveis_com_valor
                else:
                    somatorio_variavel = 0

            formula = formula.replace(f' {variavel.sigla} ', f' {somatorio_variavel}')

        try:
            self.formula_valorada[index] = eval(formula)
        except Exception:
            return 0

        try:
            return round(self.formula_valorada[index], self.casas_decimais)
        except Exception:
            return 0

    get_formula_valor.short_description = 'Fórmula Valorada'

    def get_formula_valor_meta(self, uo=None, ano_base=None, force=True):
        index = None
        if uo:
            uo = get_object_or_404(UnidadeOrganizacional, pk=uo.id)
            index = uo.sigla

        if hasattr(self, 'formula_valorada_meta'):
            if index in self.formula_valorada_meta and not force:
                return self.formula_valorada_meta[index]
        else:
            self.formula_valorada_meta = {}
        formula = ' {} '.format(
            self.forma_calculo.replace(' ', '').replace(')', ' ) ').replace('(', ' ( ').replace('*', ' * ').replace('/', ' / ').replace('+', ' + ').replace('-', ' - ')
        )

        for variavel in self.get_variaveis():
            # O ajuste '{}.0' garante que as divisões internas não serão truncadas.
            # Ex: Com o referido ajuste, a fórmula '(  (1053+187)  * 1 )  +  (  (33+39)  / 2 )  +  (23/ 4 )  ) tem
            # como valor final 1281.75, já sem esse ajuste seria exibido 1281.
            somatorio_variavel = variavel.get_valor_meta_variavel(uo=uo, ano_base=ano_base)
            if self.calcular_media and not uo:
                qtd_variaveis_com_valor = VariavelCampus.objects.filter(variavel=variavel, ano=ano_base, valor_ideal__gt=0).count()
                if qtd_variaveis_com_valor:
                    somatorio_variavel = somatorio_variavel / qtd_variaveis_com_valor
                else:
                    somatorio_variavel = 0

            formula = formula.replace(f' {variavel.sigla} ', f' {somatorio_variavel}')

        try:
            self.formula_valorada_meta[index] = eval(formula)
        except Exception:
            return 0.0

        try:
            return round(self.formula_valorada_meta[index], self.casas_decimais)

        except Exception:
            return 0.0

    get_formula_valor.short_description = 'Fórmula Valorada Meta'


class PDIIndicador(ModelPlus):

    TIPO_PERCENTUAL = 'Percentual'
    TIPO_INTEIRO = 'Inteiro'
    TIPO_DECIMAL = 'Decimal'

    TIPO_VALOR = ((TIPO_PERCENTUAL, TIPO_PERCENTUAL), (TIPO_INTEIRO, TIPO_INTEIRO), (TIPO_DECIMAL, TIPO_DECIMAL))

    pdi = models.ForeignKey('PDI', on_delete=models.CASCADE)
    indicador = models.ForeignKey('Indicador', on_delete=models.CASCADE)
    tipo = models.CharFieldPlus('Tipo', choices=TIPO_VALOR, default=TIPO_PERCENTUAL)
    valor_referencia = models.DecimalFieldPlus('Valor Referência', decimal_places=4, null=True)

    objetivos = models.ManyToManyField('PDIObjetivoEstrategico')

    class Meta:
        verbose_name = 'Indicador no PDI'
        verbose_name_plural = 'Indicadores no PDI'
        unique_together = ('pdi', 'indicador')

    def __str__(self):
        return f'{self.indicador.sigla} - {self.indicador.descricao}'

    def save(self, *args, **kwargs):
        edit_indicador = self.pk
        super().save(*args, **kwargs)

        data_inicial = self.pdi.ano_inicial_pdi.ano
        data_final = self.pdi.ano_final_pdi.ano

        if not edit_indicador:
            while data_inicial <= data_final:
                meta = MetaIndicador()
                meta.indicador = self
                meta.ano = data_inicial
                meta.save()
                data_inicial += 1

    @property
    def casas_decimais(self):
        return self.indicador.casas_decimais

    def get_valor_referencia(self):
        return defaultfilters.floatformat(self.valor_referencia, self.casas_decimais)

    def verificar_variavel_real_vazia(self, uo=None, ano_base=None):
        variaveis = self.indicador.get_variaveis()
        if variaveis:
            if uo:
                return VariavelCampus.objects.filter(uo=uo.id, variavel__in=self.indicador.get_variaveis(), ano=ano_base, valor_real__isnull=True).exists()
            else:
                return VariavelCampus.objects.filter(variavel__in=self.indicador.get_variaveis(), ano=ano_base, valor_real__isnull=True).exists()
        else:
            return True

    def verificar_variavel_ideal_vazia(self, uo=None, ano_base=None):
        variaveis = self.indicador.get_variaveis()
        if variaveis:
            if uo:
                return VariavelCampus.objects.filter(uo=uo.id, variavel__in=self.indicador.get_variaveis(), ano=ano_base, valor_ideal__isnull=True).exists()
            else:
                return VariavelCampus.objects.filter(variavel__in=self.indicador.get_variaveis(), ano=ano_base, valor_ideal__isnull=True).exists()
        else:
            return True

    def verificar_variavel_vazia(self, uo=None, ano_base=None):
        return self.verificar_variavel_real_vazia(uo, ano_base) or self.verificar_variavel_ideal_vazia(uo, ano_base)

    def get_metaindicador_valor(self, uo=None, ano_base=None):
        variavel_ideal = 0
        for variavel in self.indicador.get_variaveis():
            if uo:
                var_ideal = VariavelCampus.objects.filter(uo=uo.id, variavel=variavel, ano=ano_base)
                variavel_ideal += var_ideal[0].valor_ideal
            else:
                var_ideal = VariavelCampus.objects.filter(variavel=variavel, ano=ano_base).aggregate(total=Sum('valor_ideal'))
                variavel_ideal += var_ideal['total'] or 0
        return variavel_ideal

    def get_porcentagem_alcancada(self, uo=None, ano_base=None, valor_real=None):
        trimestre_atual = int((date.today().month - 1) / 3 + 1)
        valor_meta = self.indicador.get_formula_valor_meta(uo, ano_base)
        if not valor_real:
            valor_real = self.indicador.get_formula_valor(uo, ano_base)

        if ano_base and int(ano_base) == date.today().year:
            if self.indicador.tendencia == Indicador.DIRECAO_ALTA and not self.indicador.sem_escalonamento_trimestral:
                if trimestre_atual == 1:
                    valor_meta = valor_meta / 4
                else:
                    valor_meta = (valor_meta / 4.0) * (trimestre_atual - 1)

        if not (valor_real == 0 or valor_meta == 0):
            porcentagem = float(valor_real * 100) / float(valor_meta * 100) * 100
            if self.indicador.tendencia == Indicador.DIRECAO_BAIXA:
                porcentagem = (float(valor_meta) * 100 / float(valor_real * 100)) * 100
            return porcentagem
        else:
            if (valor_meta == 0 and self.indicador.tendencia == Indicador.DIRECAO_ALTA) or (valor_real == 0 and self.indicador.tendencia == Indicador.DIRECAO_BAIXA):
                return 100
            else:
                return 0

    def get_status_farol(self, uo=None, ano_base=None, valor_real=None):
        if not self.indicador.indicador_acompanhamento:
            if not self.verificar_variavel_vazia(uo, ano_base):
                valor_meta = self.indicador.valor_meta
                if not valor_real:
                    valor_real = self.indicador.valor_real
                if not (valor_real == 0 and valor_meta == 0):
                    porcentagem = self.get_porcentagem_alcancada(uo, ano_base, valor_real)
                    if self.pdi.valor_faixa_verde <= porcentagem:
                        return 'Alcançado'
                    elif self.pdi.valor_faixa_amarela <= porcentagem < self.pdi.valor_faixa_verde:
                        return 'Parcialmente'
                    elif self.pdi.valor_faixa_vermelha <= porcentagem < self.pdi.valor_faixa_amarela:
                        return 'Não Alcançado'
                else:
                    return 'Não se Aplica'
            else:
                return 'Não informado'
        else:
            return 'Indicador de Acompanhamento'


class TematicaVariavel(ModelPlus):
    nome = models.CharFieldPlus('Nome da Temática', unique=True)

    class Meta:
        verbose_name = 'Temática da variável'
        verbose_name_plural = 'Temáticas das variáveis'

        ordering = ('nome',)


class Variavel(models.ModelPlus):
    sigla = models.CharField(max_length=50, help_text='A sigla é utilizada na fórmula dos indicadores')
    nome = models.CharField(max_length=100)
    descricao = models.TextField('Descrição', max_length=1000)
    fonte = models.CharField(max_length=255, help_text='Origem do dado')
    tematica = models.ForeignKeyPlus('TematicaVariavel', verbose_name='Temática', null=True, blank=True)

    class Meta:
        verbose_name = 'Variável'
        verbose_name_plural = 'Variáveis'
        ordering = ('sigla',)

    def __unicode__(self):
        return f'{self.sigla}: {self.descricao}'

    def get_absolute_url(self):
        return f'/plan_estrategico/variavel/{self.id}/visualizar/'

    def get_valor(self, uo=None, ano_base=None):
        if uo:
            variavelcampus = VariavelCampus.objects.filter(uo=uo.id, variavel=self, ano=ano_base)
            return variavelcampus[0].valor_real
        else:
            variavelcampus = VariavelCampus.objects.filter(variavel=self, ano=ano_base).aggregate(total=Sum('valor_real'))
            return variavelcampus['total']

    def get_valor_meta_variavel(self, uo=None, ano_base=None):
        if uo:
            variavelcampus = VariavelCampus.objects.filter(uo=uo.id, variavel=self, ano=ano_base)
            return variavelcampus[0].valor_ideal
        else:
            variavelcampus = VariavelCampus.objects.filter(variavel=self, ano=ano_base).aggregate(total=Sum('valor_ideal'))
            return variavelcampus['total']

    def get_indicadores_variavel(self):
        indicadores = []
        for i in Indicador.objects.all():
            formula = ' {} '.format(
                i.forma_calculo.replace(' ', '').replace(')', ' ) ').replace('(', ' ( ').replace('*', ' * ').replace(
                    '/', ' / ').replace('+', ' + ').replace('-', ' - '))
            siglas = [x for x in formula.replace(' ', '').replace(')', '').replace('(', '').replace('*', ':').replace('/',
                                                                                                                      ':').replace(
                '+', ':').replace('-', ':').split(':') if x and not x.isdigit()]
            if self.sigla in siglas:
                indicadores.append(i)
        return indicadores

    def save(self, *args, **kwargs):
        edit_variavel = self.pk
        super().save(*args, **kwargs)
        pdi = PDI.objects.all()[0]
        data_inicial = pdi.ano_inicial_pdi.ano
        data_final = pdi.ano_final_pdi.ano
        if not edit_variavel:
            while data_inicial <= data_final:
                for uo in UnidadeOrganizacional.objects.uo().all():
                    if not VariavelCampus.objects.filter(uo=uo, variavel=self, ano=data_inicial).exists():
                        VariavelCampus.objects.create(variavel=self, uo=uo, ano=data_inicial)
                data_inicial += 1


class VariavelCampus(models.ModelPlus):
    ATIVA = 1
    NAO_SE_APLICA = 2

    SITUACAO_CHOICES = ((ATIVA, 'Ativa'), (NAO_SE_APLICA, 'Não se aplica'),)

    variavel = models.ForeignKeyPlus('Variavel', verbose_name='Variavel')
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Unidade Administrativa')
    valor_ideal = models.DecimalField('Valor Meta', max_digits=15, decimal_places=4, null=True)
    valor_real = models.DecimalField('Valor Real', max_digits=15, decimal_places=4, null=True)
    valor_trimestral = models.DecimalField('Valor Acumulado', max_digits=15, decimal_places=4, null=True)
    ano = models.PositiveIntegerField('Ano')
    data_atualizacao = models.DateTimeFieldPlus(null=True, verbose_name='Data da Importação')
    situacao = models.PositiveIntegerField('Situação', choices=SITUACAO_CHOICES, default=ATIVA)

    class Meta:
        verbose_name = 'Variável Campus/Ano'
        verbose_name_plural = 'Variáveis Campus/Ano'
        ordering = ('variavel__sigla',)

    def __unicode__(self):
        return f'{self.variavel}: {self.uo}'

    def get_absolute_url(self):
        return f'/plan_estrategico/variavel/{self.variavel.id}/visualizar/'

    def get_valor(self, uo=None, ano_base=None):

        uo = get_object_or_404(UnidadeOrganizacional, pk=uo)
        try:
            return VariavelCampus.objects.filter(uo=uo, ano=ano_base)[0]
        except Exception:
            return Decimal('0')

    get_valor.short_description = 'Valor'


class PeriodoPreenchimentoVariavel(models.ModelPlus):
    choices_trimestres = ((1, '1º Trimestre'), (2, '2º Trimestre'), (3, '3º Trimestre'), (4, '4º Trimestre'))
    pdi = models.ForeignKey('PDI', verbose_name='PDI', on_delete=models.CASCADE)
    ano = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano do Período')
    trimestre = models.PositiveIntegerField('Trimestre', choices=choices_trimestres)
    data_inicio = models.DateTimeFieldPlus('Data de Início')
    data_termino = models.DateTimeFieldPlus('Data de Término')

    class Meta:
        verbose_name = 'Período de preenchimento de variável'
        verbose_name_plural = 'Períodos de preenchimento de variáveis'
        unique_together = ('pdi', 'ano', 'trimestre')

    @classmethod
    def get_em_periodo_de_preenchimento(cls):
        agora = datetime.now()
        return cls.objects.filter(data_inicio__lte=agora, data_termino__gte=agora)


class IndicadorTrimestralCampus(models.ModelPlus):
    choices_trimestres = ((1, '1º Trimestre'), (2, '2º Trimestre'), (3, '3º Trimestre'), (4, '4º Trimestre'))
    indicador = models.ForeignKey('PDIIndicador', verbose_name='Indicador', on_delete=models.CASCADE)
    ano = models.PositiveIntegerField('Ano')
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Unidade Administrativa', null=True)
    valor = models.DecimalField('Valor Real', max_digits=15, decimal_places=4, null=True)
    trimestre = models.PositiveIntegerField('Trimestre', choices=choices_trimestres)

    class Meta:
        verbose_name = 'Valor Trimestral do Indicador'
        verbose_name_plural = 'Valores Trimestrais do Indicador'
        unique_together = ('indicador', 'ano', 'uo', 'trimestre')


class MetaIndicador(ModelPlus):
    indicador = models.ForeignKey('PDIIndicador', verbose_name='Indicador', on_delete=models.CASCADE)
    ano = models.PositiveIntegerField('Ano')
    meta = models.DecimalFieldPlus('Meta do Ano', null=True, decimal_places=4)

    class Meta:
        verbose_name = 'Meta'
        verbose_name_plural = 'Metas'
        ordering = ['ano']

    def __str__(self):
        return f'{self.meta}'

    @property
    def casas_decimais(self):
        return self.indicador.casas_decimais

    def get_valor_meta(self):
        if self.meta:
            return Decimal(self.meta, self.casas_decimais)
        else:
            return 0


class ObjetivoIndicador(ModelPlus):
    indicador = models.ForeignKey('PDIIndicador', verbose_name='Indicador', on_delete=models.CASCADE)
    objetivo_estrategico = models.ForeignKey('PDIObjetivoEstrategico', verbose_name='Objetivo Estratégico', on_delete=models.CASCADE)
    relevancia = models.PositiveIntegerField('Relevância', default=0)

    class Meta:
        verbose_name = 'Relevância'
        verbose_name_plural = 'Relevâncias'

    def __str__(self):
        return f'{self.objetivo_estrategico}'


def atualizar_metas(self):
    pdi = PDI.objects.latest('id')
    pdi_inicial = pdi.ano_inicial_pdi.ano
    indicadores = PDIIndicador.objects.filter(pdi=pdi)
    while pdi_inicial <= pdi.ano_final_pdi.ano:
        for pdi_indicador in indicadores:
            meta = MetaIndicador.objects.get_or_create(indicador=pdi_indicador, ano=pdi_inicial)[0]
            meta.meta = pdi_indicador.indicador.get_formula_valor_meta(uo=None, ano_base=pdi_inicial, force=True)
            meta.save()
        pdi_inicial += 1


def importar_metas(self):
    def set_linha(linha):
        self.linha = linha

    def get_valor(numero_celula):
        return self.arquivo.cell_value(self.linha, numero_celula)

    def add_valor(valor, file):
        if valor == '' or valor == 0.0:
            valor = ''
        else:
            valor = f'{valor:.2f}'.replace('.', '')

        file.write('%s|' % valor)

    import xlrd
    local_filename = cache_file(self.arquivo.name)
    workbook = xlrd.open_workbook(local_filename)
    os.unlink(local_filename)
    self.arquivo = workbook.sheet_by_index(0)
    for i in range(1, self.arquivo.nrows):
        set_linha(i)
        sigla = get_valor(0).strip()
        nome_variavel = get_valor(1).strip()
        fonte = get_valor(3).strip()
        try:
            variavel = Variavel.objects.get(sigla=sigla)
        except Variavel.DoesNotExist:
            variavel = Variavel.objects.create(sigla=sigla, nome=nome_variavel, descricao=nome_variavel, fonte=fonte)
        campus = get_valor(2).strip()
        campus = UnidadeOrganizacional.objects.suap().get(sigla=campus)
        pdi = PDI.objects.latest('id')
        pdi_inicial = pdi.ano_inicial_pdi.ano
        coluna_ideal = 4
        while pdi_inicial <= pdi.ano_final_pdi.ano:
            variavel_campus = VariavelCampus.objects.get(variavel=variavel, uo=campus.id, ano=pdi_inicial)
            if get_valor(coluna_ideal) == '':
                variavel_campus.valor_ideal = None
            else:
                variavel_campus.valor_ideal = get_valor(coluna_ideal)
            variavel_campus.save()
            coluna_ideal += 1
            pdi_inicial += 1
    atualizar_metas(self)


class ArquivoMeta(ModelPlus):
    data_importacao = models.DateTimeFieldPlus(null=True, auto_now_add=True, verbose_name='Data da Importação')
    arquivo = models.FileFieldPlus('Arquivo', upload_to='plan_estrategico/arquivometa', max_length=255)
    usuario = models.CurrentUserField(verbose_name='Usuário')

    class Meta:
        verbose_name = 'Arquivo Meta e Real'
        verbose_name_plural = 'Arquivo de Metas e Reais'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        importar_metas(self)


class TotalizadorIndicador(ModelPlus):
    INDICADOR_ALCANCADO = 'Indicador Alcançado'
    INDICADOR_PARCIALMENTE_ALCANCADO = 'Indicador Parcialmente Alcançado'
    INDICADOR_NAO_ALCANCADO = 'Indicador Não Alcançado'

    TIPO_STATUS = (
        (INDICADOR_ALCANCADO, INDICADOR_ALCANCADO),
        (INDICADOR_PARCIALMENTE_ALCANCADO, INDICADOR_PARCIALMENTE_ALCANCADO),
        (INDICADOR_NAO_ALCANCADO, INDICADOR_NAO_ALCANCADO),
    )

    ano = models.PositiveIntegerField('Ano')
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Unidade Administrativa', null=True)
    total_indicadores = models.PositiveIntegerField('Total Campus', null=True)
    status = models.CharFieldPlus('Status', choices=TIPO_STATUS)


class VariavelTrimestralCampus(models.ModelPlus):
    choices_trimestres = ((1, '1º Trimestre'), (2, '2º Trimestre'), (3, '3º Trimestre'), (4, '4º Trimestre'))
    variavel = models.ForeignKey(VariavelCampus, verbose_name='Variavel Campus', on_delete=models.CASCADE)
    ano = models.PositiveIntegerField('Ano')
    valor = models.DecimalField('Valor Real', max_digits=15, decimal_places=4, null=True)
    trimestre = models.PositiveIntegerField('Trimestre', choices=choices_trimestres)

    class Meta:
        verbose_name = 'Valor Trimestral da Variável Campus'
        verbose_name_plural = 'Valores Trimestrais das Variáveis Campus'


# Modelos do Plano de Atividade ----------------------------------------------------------------------------------------


class PlanoAtividade(ModelPlus):

    pdi = models.ForeignKeyPlus('plan_estrategico.PDI', on_delete=models.CASCADE)
    ano_base = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Base')

    projetos = models.ManyToManyField(ProjetoEstrategico, through='ProjetoPlanoAtividade')

    # vigência do plano de atividade
    data_geral_inicial = models.DateFieldPlus('Início da Vigência')
    data_geral_final = models.DateFieldPlus('Fim da Vigência')

    # data para adição de dados orcamentários
    data_orcamentario_preloa_inicial = models.DateFieldPlus('Início do Cadastro Orçamentário Pré-LOA')
    data_orcamentario_preloa_final = models.DateFieldPlus('Fim do Cadastro Orçamentário Pré-LOA')

    # data para importação de projetos estratégicos do PDI
    data_projetos_preloa_inicial = models.DateFieldPlus('Início do Cadastro de Projetos Pré-LOA')
    data_projetos_preloa_final = models.DateFieldPlus('Fim do Cadastro de Projetos Pré-LOA')

    # data para adição de atividades pela UA
    data_atividades_preloa_inicial = models.DateFieldPlus('Início do Cadastro de Atividades Pré-LOA')
    data_atividades_preloa_final = models.DateFieldPlus('Fim do Cadastro de Atividades Pré-LOA')

    # data pada adicao de valores orçamentários
    data_orcamentario_posloa_inicial = models.DateFieldPlus('Início do Cadastro Orçamentário Pós-LOA')
    data_orcamentario_posloa_final = models.DateFieldPlus('Fim do Cadastro Orçamentário Pós-LOA')

    # data para gerenciar recursos nos projetos
    data_projetos_posloa_inicial = models.DateFieldPlus('Início do Cadastro de Projeto Pós-LOA')
    data_projetos_posloa_final = models.DateFieldPlus('Fim do Cadastro de Projeto Pós-LOA')

    # data para gerenciar recursos das etapas/atividades
    data_atividades_posloa_inicial = models.DateFieldPlus('Início do Cadastro de Atividades Pós-LOA')
    data_atividades_posloa_final = models.DateFieldPlus('Fim do Cadastro de Atividades Pós-LOA')

    percentual_reserva_tecnica = models.IntegerField(verbose_name='Percentual da Reserva Técnica', null=True)

    class Meta:
        verbose_name = 'Plano de Atividade'
        verbose_name_plural = 'Planos de Atividades'

        ordering = ('ano_base',)
        unique_together = ('pdi', 'ano_base')

    def __str__(self):
        return str(self.ano_base)

    @property
    def em_periodo_orcamentario_preloa(self):
        hoje = date.today()
        return self.data_orcamentario_preloa_inicial <= hoje <= self.data_orcamentario_preloa_final

    @property
    def em_periodo_orcamentario_posloa(self):
        hoje = date.today()
        return self.data_orcamentario_posloa_inicial <= hoje <= self.data_orcamentario_posloa_final

    @property
    def em_periodo_projeto_preloa(self):
        hoje = date.today()
        return self.data_projetos_preloa_inicial <= hoje <= self.data_projetos_preloa_final

    @property
    def em_periodo_projeto_posloa(self):
        hoje = date.today()
        return self.data_projetos_posloa_inicial <= hoje <= self.data_projetos_posloa_final

    @property
    def em_periodo_atividades_posloa(self):
        hoje = date.today()
        return self.data_atividades_posloa_inicial <= hoje <= self.data_atividades_posloa_final

    # Se pode incluir plano de atividade é um administrador de projeto estratégico
    def pode_incluir(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.add_planoatividade'):
            return True
        return False

    @property
    def em_periodo_atividade_preloa(self):
        hoje = date.today()
        return self.data_atividades_preloa_inicial <= hoje <= self.data_atividades_preloa_final

    @property
    def concluido(self):
        hoje = date.today()
        return hoje > self.data_atividades_posloa_final


class OrigemRecurso(ModelPlus):
    plano_atividade = models.ForeignKeyPlus('PlanoAtividade', on_delete=models.CASCADE)
    acao_financeira = models.ForeignKeyPlus('financeiro.AcaoAno', verbose_name='Ação Orçamentária', related_name='origemrecurso_acaofinanceira', on_delete=models.CASCADE)
    gnd = models.ForeignKeyPlus('financeiro.GrupoNaturezaDespesa', verbose_name='Grupo Elemento de Despesa', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Origem do Recurso'
        verbose_name_plural = 'Origens dos Recursos'

        unique_together = ('acao_financeira', 'gnd')

    def __str__(self):
        return f'{self.acao_financeira.acao.codigo_acao}.{self.acao_financeira.ptres}.{self.gnd.codigo}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_codigo(self):
        return f'{self.acao_financeira.acao.codigo_acao}.{self.acao_financeira.ptres}.{self.gnd.codigo}'

    @classmethod
    def pode_incluir(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.add_origemrecurso') and (plano_atividade.em_periodo_orcamentario_preloa):
            return True
        return False

    @classmethod
    def pode_alterar(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.change_origemrecurso') and (plano_atividade.em_periodo_orcamentario_preloa):
            return True
        return False

    @classmethod
    def pode_excluir(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.delete_origemrecurso') and (plano_atividade.em_periodo_orcamentario_preloa):
            return True
        return False

    @classmethod
    def pode_incluir_dados_orcamentarios(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.add_origemrecurso') and (plano_atividade.em_periodo_orcamentario_preloa or plano_atividade.em_periodo_orcamentario_posloa):
            return True
        return False

    def valor_total(self):
        if self.gnd.codigo == '4':
            return self.acao_financeira.valor_capital
        else:
            return self.acao_financeira.valor_custeio


class NaturezaDespesaPlanoAtividade(ModelPlus):
    SEARCH_FIELDS = ['natureza_despesa__codigo', 'natureza_despesa__nome']

    plano_atividade = models.ForeignKeyPlus('PlanoAtividade', verbose_name='Plano de Atividade')
    natureza_despesa = models.ForeignKeyPlus('financeiro.NaturezaDespesa', verbose_name='Natureza de Despesa')

    class Meta:
        verbose_name = 'Natureza de Despesa do Plano de Atividade'
        verbose_name_plural = 'Naturezas de Despesa do Plano de Atividade'

    def __str__(self):
        return f'{self.natureza_despesa.codigo} - {self.natureza_despesa.nome}'

    @classmethod
    def pode_gerenciar(cls, usuario, plano_atividade):
        if usuario.has_perm('financeiro.add_naturezadespesa') and (plano_atividade.em_periodo_orcamentario_preloa):
            return True
        return False

    @classmethod
    def pode_excluir(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.delete_naturezadespesaplanoatividade') and (plano_atividade.em_periodo_orcamentario_preloa):
            return True
        return False


class ProjetoPlanoAtividade(ModelPlus):
    etapas_projeto_plano_atividade = models.ManyToManyField(EtapaProjeto, through='EtapaProjetoPlanoAtividade')
    OrigensRecurso = models.ManyToManyField(OrigemRecurso, through='OrigemRecursoProjeto')
    projeto = models.ForeignKey('ProjetoEstrategico', verbose_name='Projeto Estratégico', on_delete=models.CASCADE)
    plano_atividade = models.ForeignKey('PlanoAtividade', verbose_name='Plano de Atividade', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Projetos do plano de Atividade'
        verbose_name_plural = 'Projetos do Plano de Atividade'

        unique_together = ('projeto', 'plano_atividade')

    def __str__(self):
        return f'{self.projeto}'

    @classmethod
    def pode_incluir(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.add_projetoplanoatividade') and (plano_atividade.em_periodo_projeto_preloa):
            return True
        return False

    @classmethod
    def eh_administrador(cls, usuario):
        if usuario.has_perm('plan_estrategico.add_pdi'):
            return True
        return False

    @classmethod
    def eh_gestor(cls, usuario):
        if usuario.has_perm('plan_estrategico.add_projetoplanoatividade'):
            return True
        return False

    @classmethod
    def eh_coordenador(cls, usuario):
        if usuario.has_perm('plan_estrategico.add_atividadeetapa'):
            return True
        return False

    def get_valor_total_origem_recurso(self):
        total = Decimal('0')
        if self.origemrecursoprojeto_set.all().first():
            for origem in OrigemRecursoProjeto.objects.filter(projeto_plano_atividade=self):
                if origem.valor:
                    total += origem.valor
        return total

    def get_valor_disponivel_origem_recurso(self):
        total = Decimal('0')
        if self.origemrecursoprojeto_set.all().first():
            for origem in OrigemRecursoProjeto.objects.filter(projeto_plano_atividade=self):
                if origem.get_valor_distribuido():
                    total += origem.get_valor_distribuido()
        return total

    def eh_dono(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if ProjetoPlanoAtividade.objects.filter(pk=self.id, projeto__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=usuario)):
            return True
        return False

    def tem_atividade(self):
        if AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade=self):
            return True
        return False


class OrigemRecursoProjeto(ModelPlus):
    valor = models.DecimalFieldPlus('Valor do Projeto', null=True)
    projeto_plano_atividade = models.ForeignKeyPlus('ProjetoPlanoAtividade', verbose_name='Projeto do plano de atividade', on_delete=models.CASCADE)
    origem_recurso = models.ForeignKeyPlus('OrigemRecurso', verbose_name='Origem de recurso do projeto do plano de atividade', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Origem de recurso do projeto'
        verbose_name_plural = 'Origens de recursos do projeto'

        unique_together = ('projeto_plano_atividade', 'origem_recurso')

    def __str__(self):
        return f'{self.projeto_plano_atividade.projeto.codigo}.{self.origem_recurso}'

    @classmethod
    def pode_incluir_valor(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.add_origemrecurso') and (plano_atividade.em_periodo_orcamentario_posloa):
            return True
        return False

    @classmethod
    def pode_ratear_valor(cls, plano_atividade):
        if plano_atividade.em_periodo_projeto_posloa:
            return True
        return False

    @classmethod
    def pode_ratear_valor_atividade(cls, usuario, plano_atividade):
        if usuario.has_perm('plan_estrategico.view_atividadeetapa') and (plano_atividade.em_periodo_atividades_posloa):
            return True
        return False

    @classmethod
    def valor_executado(self, plano_atividade):
        valor_executado = OrigemRecursoProjeto.objects.filter(projeto_plano_atividade__plano_atividade=plano_atividade).aggregate(Sum('valor')).values()[0] or 0
        return valor_executado

    def get_valor_distribuido(self):
        return OrigemRecursoProjetoEtapa.objects.filter(origem_recurso_projeto=self).aggregate(total=Sum('valor'))['total'] or 0

    def get_valor(self):
        return self.valor or 0


class EtapaProjetoPlanoAtividade(ModelPlus):
    projeto_plano_atividade = models.ForeignKey('ProjetoPlanoAtividade', verbose_name='Projeto Estratégico', on_delete=models.CASCADE)
    etapa = models.ForeignKey('EtapaProjeto', verbose_name='Etapa do projeto do plano de atividade', on_delete=models.CASCADE)
    origens_recurso_projeto_etapa = models.ManyToManyField(OrigemRecursoProjeto, through='OrigemRecursoProjetoEtapa')
    tipo_especial = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Etapa do projeto'
        verbose_name_plural = 'Etapas do projeto'

        unique_together = ('projeto_plano_atividade', 'etapa')

    def __str__(self):
        return f'{self.projeto_plano_atividade} | {self.etapa}'

    def etapa_dono(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if EtapaProjetoPlanoAtividade.objects.filter(pk=self.id, projeto_plano_atividade__projeto__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=usuario)):
            return True
        return False

    def eh_especial(self):
        if self.tipo_especial is True:
            return True
        return False

    def tem_unidade_adm(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=self, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(usuario)).exists():
            return True
        return False

    def tem_atividades(self, unidade=None):
        if AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=self, unidade_gestora=unidade).exists():
            return True
        return False

    def get_unidades_etapa(self):
        total_unidades_etapa = list()
        unidades_etapa = list()
        for unidade in UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=self):
            unidades_etapa.append(unidade.unidade_gestora.setor_equivalente.sigla)
        total_unidades_etapa.append({'campi': ', '.join(unidades_etapa)})
        return total_unidades_etapa

    def tem_valor_rateado_unidades(self):
        origens_recurso = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self).exists()
        if origens_recurso:
            for origem in OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self):
                if UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=origem, valor__isnull=False).exists():
                    return True
        return False


class OrigemRecursoProjetoEtapa(ModelPlus):
    SEARCH_FIELDS = ['origem_recurso_projeto']
    etapa_projeto_plano_atividade = models.ForeignKeyPlus(
        'EtapaProjetoPlanoAtividade', verbose_name='Etapa do projeto do plano de atividade', related_name='origens_recurso_etapa', on_delete=models.CASCADE
    )
    origem_recurso_projeto = models.ForeignKeyPlus('OrigemRecursoProjeto', verbose_name='Origem de recurso do projeto do plano de atividade', on_delete=models.CASCADE)
    valor = models.DecimalFieldPlus('Valor Solicitado', null=True, blank=True)
    tipo_especial = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Origem de recurso da etapa do projeto'
        verbose_name_plural = 'Origens de recurso da etapa do projeto'

        unique_together = ('etapa_projeto_plano_atividade', 'origem_recurso_projeto')

    def __str__(self):
        return f'{self.origem_recurso_projeto}'

    def get_valor(self):
        return self.valor or 0

    def get_valor_unidade(self):
        from plan_estrategico.utils import get_setor_unidade_gestora

        usuario = tl.get_user()
        valor = 0

        if UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=self, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=usuario)).exists():
            valor = UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=self, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=usuario))[
                0
            ].valor
        return valor

    def tem_valor_distribuido(self):
        if AtividadeEtapa.objects.filter(origem_recurso_etapa=self, valor_rateio__isnull=False).exists():
            return True
        return False

    def tem_valor_especial_distribuido(self):
        if AtividadeEtapa.objects.filter(origem_recurso_etapa=self, valor_reserva_tecnica__isnull=False).exists():
            return True
        return False


class UnidadeGestoraEtapa(ModelPlus):
    etapa_projeto_plano_atividade = models.ForeignKeyPlus(
        'EtapaProjetoPlanoAtividade', verbose_name='Etapa do projeto do plano de atividade', related_name="unidades_gestoras", on_delete=models.CASCADE
    )
    unidade_gestora = models.ForeignKey('UnidadeGestora', verbose_name='Unidade gestora da etapa', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Unidade gestora da etapa'
        verbose_name_plural = 'Unidades gestoras da etapa'
        ordering = ["unidade_gestora__setor_equivalente"]
        unique_together = ('etapa_projeto_plano_atividade', 'unidade_gestora')

    def __str__(self):
        return f'{self.etapa_projeto_plano_atividade} | {self.unidade_gestora}'


class UnidadeOrigemEtapa(ModelPlus):
    origem_recurso_etapa = models.ForeignKeyPlus('OrigemRecursoProjetoEtapa', verbose_name='Origem Recurso da Etapa', on_delete=models.CASCADE)
    unidade_gestora = models.ForeignKey('UnidadeGestoraEtapa', verbose_name='Unidade gestora da etapa', on_delete=models.CASCADE)
    valor = models.DecimalFieldPlus('Valor', null=True, blank=True)

    class Meta:
        verbose_name = 'Unidade gestora da etapa'
        verbose_name_plural = 'Unidades gestoras da etapa'
        ordering = ["unidade_gestora__unidade_gestora__setor_equivalente"]
        unique_together = ('origem_recurso_etapa', 'unidade_gestora')

    def __str__(self):
        return f'{self.origem_recurso_etapa} | {self.unidade_gestora}'

    def get_total_valor_rateado(self):
        total = 0
        atividades = AtividadeEtapa.objects.filter(
            origem_recurso_etapa=self.origem_recurso_etapa,
            etapa_projeto_plano_atividade=self.origem_recurso_etapa.etapa_projeto_plano_atividade,
            unidade_gestora=self.unidade_gestora.unidade_gestora,
        )
        if atividades:
            total = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
        return total

    def get_total_valor_reserva_tecnica(self):
        total = 0
        atividades = AtividadeEtapa.objects.filter(
            origem_recurso_etapa=self.origem_recurso_etapa,
            etapa_projeto_plano_atividade=self.origem_recurso_etapa.etapa_projeto_plano_atividade,
            unidade_gestora=self.unidade_gestora.unidade_gestora,
        )
        if atividades:
            total = atividades.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
        return total

    def get_total_valor_proposto(self):
        total = 0
        atividades = AtividadeEtapa.objects.filter(
            origem_recurso_etapa=self.origem_recurso_etapa,
            etapa_projeto_plano_atividade=self.origem_recurso_etapa.etapa_projeto_plano_atividade,
            unidade_gestora=self.unidade_gestora.unidade_gestora,
        )
        if atividades:
            total = atividades.aggregate(total=Sum('valor'))['total'] or 0
        return total

    def get_total_unidade(self):
        return self.get_total_valor_rateado() + self.get_total_valor_reserva_tecnica()


class AtividadeEtapa(ModelPlus):
    etapa_projeto_plano_atividade = models.ForeignKeyPlus('EtapaProjetoPlanoAtividade', verbose_name='Etapa do projeto do plano de atividade', on_delete=models.CASCADE)
    origem_recurso_etapa = models.ForeignKeyPlus('OrigemRecursoProjetoEtapa', verbose_name='Origem de Recurso da Etapa', blank=True, on_delete=models.CASCADE, null=True)
    naturezadespesa = models.ForeignKeyPlus('NaturezaDespesaPlanoAtividade', verbose_name='Natureza de Despesa', blank=True, on_delete=models.CASCADE, null=True)
    valor = models.DecimalFieldPlus('Valor Proposto', default=0)
    nome = models.CharField(max_length=100, verbose_name='Nome da Atividade')
    descricao = models.TextField('Descrição', max_length=1500)
    unidade_gestora = models.ForeignKey('UnidadeGestora', verbose_name='Unidade gestora da atividade', on_delete=models.CASCADE, null=True, blank=True)
    valor_rateio = models.DecimalFieldPlus('Valor Rateio', null=True, blank=True)
    valor_reserva_tecnica = models.DecimalFieldPlus('Valor Rateio', null=True, blank=True)
    origem_recurso_reserva_tecnica = models.ForeignKeyPlus(
        'OrigemRecursoProjetoEtapa', related_name='origem_especial', verbose_name='Origem Reserva Técnica', blank=True, on_delete=models.CASCADE, null=True
    )

    class Meta:
        verbose_name = 'Atividade da Etapa'
        verbose_name_plural = 'Atividades da Etapa'

    def __str__(self):
        return f'{self.etapa_projeto_plano_atividade} | {self.nome}'

    @classmethod
    def pode_editar_atividade(self, usuario=None, plano_atividade=None):
        if not usuario:
            usuario = tl.get_user()
        if usuario.has_perm('plan_estrategico.change_atividadeetapa') and plano_atividade.em_periodo_atividade_preloa:
            return True
        return False

    @classmethod
    def pode_incluir_atividade(self, usuario=None, plano_atividade=None):
        if not usuario:
            usuario = tl.get_user()
        if usuario.has_perm('plan_estrategico.add_atividadeetapa') and plano_atividade.em_periodo_atividade_preloa:
            return True
        return False

    @classmethod
    def pode_excluir_atividade(self, usuario=None, plano_atividade=None):
        if not usuario:
            usuario = tl.get_user()
        if usuario.has_perm('plan_estrategico.delete_atividadeetapa') and plano_atividade.em_periodo_atividade_preloa:
            return True
        return False

    @classmethod
    def eh_coordenadorUA(cls, usuario):
        if usuario.has_perm('plan_estrategico.add_atividadeetapa'):
            return True
        return False

    @classmethod
    def pode_ver_atividade(self, usuario=None, plano_atividade=None):
        if not usuario:
            usuario = tl.get_user()
        if usuario.has_perm('plan_estrategico.view_atividadeetapa') and (plano_atividade.em_periodo_atividade_preloa or plano_atividade.em_periodo_atividades_posloa):
            return True
        return False

    def eh_dono(self, usuario=None):
        from plan_estrategico.utils import get_setor_unidade_gestora

        if not usuario:
            usuario = tl.get_user()
        if AtividadeEtapa.objects.filter(pk=self.id, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=usuario)).exists():
            return True
        return False

    @classmethod
    def pode_ver_todas_atividades(self, usuario=None, plano_atividade=None):
        if not usuario:
            usuario = tl.get_user()
        if (usuario.groups.filter(name='Gestor de Projeto').exists() or usuario.groups.filter(name='Administrador de Planejamento Estratégico').exists()) and (
            plano_atividade.em_periodo_atividade_preloa
            or plano_atividade.em_periodo_orcamentario_posloa
            or plano_atividade.em_periodo_projeto_posloa
            or plano_atividade.em_periodo_atividades_posloa
        ):
            return True
        return False

    def get_total(self):
        return (self.valor_rateio or 0) + (self.valor_reserva_tecnica or 0)

    def get_valor_rateio(self):
        return self.valor_rateio or 0

    def get_valor_reserva_tecnica(self):
        return self.valor_reserva_tecnica or 0


class CompartilhamentoPoderdeGestorUA(models.ModelPlus):
    setor_dono = models.ForeignKeyPlus('rh.Setor')

    pessoa_permitida = models.ForeignKeyPlus('rh.Pessoa', verbose_name='Pessoa com Poder de Gestor de UA', null=True)

    data_criacao = models.DateTimeFieldPlus('Data de Criação', editable=False, null=True, blank=True)
    usuario_criacao = models.ForeignKeyPlus(User, verbose_name='Usuário de Criação', editable=False, null=True, blank=True)

    class Meta:
        verbose_name = 'Configuração de Compartilhamento de Poder de Gestor de Unid. Administrativa'
        verbose_name_plural = 'Configurações de Compartilhamento Poder de Gestor de Unid. Administrativa'
        permissions = (('pode_gerenciar_permissoes_da_ua', 'Pode gerenciar permissoes da Unidade'),)

    def __str__(self):
        return f'Poder de Gestor de UA no setor {self.setor_dono} para {self.pessoa_permitida}'

    @staticmethod
    def atualizar_poder_gestor(usuario_criacao, setor_dono, pessoas_poder_de_gestor):
        for po in pessoas_poder_de_gestor:
            comp = CompartilhamentoPoderdeGestorUA()
            comp.setor_dono = setor_dono
            comp.pessoa_permitida = po
            comp.data_criacao = date.today()
            comp.usuario_criacao = usuario_criacao
            comp.save()
            po.user.save()
        grupo_tem_poder_gestor = Group.objects.get(name='Coordenador de UA')
        for pessoa in CompartilhamentoPoderdeGestorUA.objects.filter(setor_dono=setor_dono):
            if pessoa.pessoa_permitida.pessoafisica not in pessoas_poder_de_gestor:
                pessoa.pessoa_permitida.pessoafisica.user.groups.remove(grupo_tem_poder_gestor)
                pessoa.delete()
        return True

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self):
        super().delete()
