"""
Comando que coleta valores atualizados das variaveis do edu.
"""
import datetime
from _functools import reduce
import operator
from django.db import transaction
from django.db.models import Q

from djtools.management.commands import BaseCommandPlus
from edu.models.alunos import Aluno
from edu.models.cadastros_gerais import Modalidade, SituacaoMatriculaPeriodo
from edu.models.historico import MatriculaPeriodo
from plan_estrategico.models import VariavelCampus, Variavel as VariavelPDI, PeriodoPreenchimentoVariavel, \
    VariavelTrimestralCampus
from rh.models import UnidadeOrganizacional
from gestao import util


class Command(BaseCommandPlus):
    def get_periodo_referencia_ano_atual(self, user=None):
        from gestao.models import PeriodoReferencia

        periodo_referencia = PeriodoReferencia()
        periodo_referencia.ano = datetime.date.today().year
        if PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date=datetime.date.today()).exists():
            periodo_referencia.ano = PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date=datetime.date.today()).first().ano.ano
        periodo_referencia.data_base = datetime.date(periodo_referencia.ano, 1, 1)
        periodo_referencia.data_limite = datetime.date(periodo_referencia.ano, 12, 31)
        return periodo_referencia

    util.get_periodo_referencia = get_periodo_referencia_ano_atual

    def processar_variaveis(self, ano_inicio, ano_fim, modalidades_id, uos_id, uo_id=None, curso_id=None):
        REPROVADOS = [SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA]

        RETIDOS = [
            SituacaoMatriculaPeriodo.REPROVADO,
            SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA,
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
        ]

        FINALIZADOS = [
            SituacaoMatriculaPeriodo.TRANCADA,
            SituacaoMatriculaPeriodo.CANCELADA,
            SituacaoMatriculaPeriodo.AFASTADO,
            SituacaoMatriculaPeriodo.TRANSF_EXTERNA,
            SituacaoMatriculaPeriodo.TRANSF_INSTITUICAO,
            SituacaoMatriculaPeriodo.TRANSF_TURNO,
            SituacaoMatriculaPeriodo.TRANSF_CURSO,
            SituacaoMatriculaPeriodo.JUBILADO,
            SituacaoMatriculaPeriodo.EVASAO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
            SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
        ]

        qs = MatriculaPeriodo.objects.exclude(aluno__turmaminicurso__gerar_matricula=False)
        qs = qs.filter(aluno__curso_campus__modalidade_id__in=modalidades_id)
        qs = qs.filter(aluno__curso_campus__diretoria__setor__uo_id=uos_id)

        if uo_id:
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo_id=uo_id)

        if curso_id:
            qs = qs.filter(aluno__curso_campus_id=curso_id)

        qs = qs.select_related('ano_letivo')
        mp = dict()
        mp['CONTINUADOS_RETIDOS'] = dict()
        mp['CONTINUADOS_REGULARES'] = dict()
        mp['RETIDOS'] = dict()
        mp['ATENDIDOS'] = dict()
        mp['CONCLUIDOS'] = dict()
        mp['CONCLUIDOS_PRAZO'] = dict()
        mp['EVADIDOS'] = dict()
        mp['FINALIZADOS'] = dict()
        mp['REPROVADOS'] = dict()
        mp['PREVISTOS'] = dict()
        mp['CONCLUIDOS_NEE'] = dict()
        mp['CONTINUADOS_REGULARES_NEE'] = dict()
        mp['ATENDIDOS_NEE'] = dict()

        for ano in range(ano_inicio, ano_fim + 1):
            # filtrando apenas alunos com matrícula período no ano de análise
            tmp = qs.filter(ano_letivo__ano=ano, periodo_letivo=2)
            qs_atendidos = tmp | qs.filter(ano_letivo__ano=ano, periodo_letivo=1).exclude(aluno__in=tmp.values_list('aluno__id', flat=True))
            # obtendo os que já tiveram ao menos uma reprovação até o período de análise
            qs_alunos_retidos = qs.filter(ano_letivo__ano__gt=2000, ano_letivo__ano__lte=ano, situacao__in=RETIDOS).values_list('aluno_id', flat=True)
            # filtrando os alunos que continuam ativos
            qs_continuadas = qs_atendidos.exclude(aluno__ano_conclusao=ano).exclude(situacao__in=FINALIZADOS)
            # filtrando os alunos que concluíram no ano de análise
            qs_finalizadas_com_exito = qs_atendidos.filter(aluno__ano_conclusao=ano)
            # filtrando os alunos que se deixaram o instituto sem concluir o curso
            qs_finalizadas_sem_exito = qs_atendidos.filter(situacao__in=FINALIZADOS)
            # identificando os alunos que deixam o instituo
            qs_finalizados = qs_finalizadas_com_exito | qs_finalizadas_sem_exito
            # filtrando apenas os alunos que nunca reprovaram no período
            qs_continuadas_regulares = qs_continuadas.exclude(aluno__in=qs_alunos_retidos)
            # filtrando os alunos que já reprovaram ao menos um período
            qs_continuadas_retidos = qs_continuadas.filter(aluno__in=qs_alunos_retidos)
            # filtrando os alunos que concluíram no ano de análise e dentro do prazo previsto
            qs_finalizadas_com_exito_no_prazo = qs_finalizadas_com_exito.extra(where=["EXTRACT(YEAR FROM edu_aluno.dt_conclusao_curso) <= edu_aluno.ano_let_prev_conclusao"])
            qs_dentro_prazo = qs_atendidos.filter(aluno__ano_let_prev_conclusao=ano)
            qs_fora_prazo = qs_atendidos.filter(aluno__ano_let_prev_conclusao__lt=ano)
            # filtrando os alunos que reprovaram no período de análise
            qs_reprovados = qs_atendidos.filter(situacao__in=REPROVADOS)

            qs_nee = []
            qs_nee.append(Q(aluno__tipo_necessidade_especial__in=[a[0] for a in Aluno.TIPO_NECESSIDADE_ESPECIAL_CHOICES]))
            qs_nee.append(Q(aluno__tipo_transtorno__in=[a[0] for a in Aluno.TIPO_TRANSTORNO_CHOICES]))
            qs_nee.append(Q(aluno__superdotacao__in=[a[0] for a in Aluno.SUPERDOTACAO_CHOICES]))

            qs_atendidos_nee = qs_atendidos.filter(reduce(operator.or_, qs_nee)).distinct()
            qs_continuados_regulares_nee = qs_continuadas_regulares.filter(reduce(operator.or_, qs_nee)).distinct()
            qs_concluidos_nee = qs_finalizadas_com_exito.filter(reduce(operator.or_, qs_nee)).distinct()

            mp['ATENDIDOS'][ano] = qs_atendidos.values_list('aluno_id', flat=True).count()
            mp['RETIDOS'][ano] = qs_fora_prazo.values_list('aluno_id', flat=True).count()
            mp['EVADIDOS'][ano] = qs_finalizadas_sem_exito.values_list('aluno_id', flat=True).count()
            mp['FINALIZADOS'][ano] = qs_finalizados.values_list('aluno_id', flat=True).count()
            mp['CONCLUIDOS'][ano] = qs_finalizadas_com_exito.values_list('aluno_id', flat=True).count()
            mp['REPROVADOS'][ano] = qs_reprovados.values_list('aluno_id', flat=True).count()
            mp['CONTINUADOS_REGULARES'][ano] = qs_continuadas_regulares.values_list('aluno_id', flat=True).count()
            mp['CONTINUADOS_RETIDOS'][ano] = qs_continuadas_retidos.values_list('aluno_id', flat=True).count()
            mp['CONCLUIDOS_PRAZO'][ano] = qs_finalizadas_com_exito_no_prazo.values_list('aluno_id', flat=True).count()
            mp['PREVISTOS'][ano] = qs_dentro_prazo.values_list('aluno_id', flat=True).count()
            mp['CONCLUIDOS_NEE'][ano] = qs_concluidos_nee.values_list('aluno_id', flat=True).count()
            mp['CONTINUADOS_REGULARES_NEE'][ano] = qs_continuados_regulares_nee.values_list('aluno_id', flat=True).count()
            mp['ATENDIDOS_NEE'][ano] = qs_atendidos_nee.values_list('aluno_id', flat=True).count()

        return mp

    @transaction.atomic
    def handle(self, *args, **options):
        if PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date=datetime.date.today()).exists():
            ano = PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date=datetime.date.today()).first().ano.ano

            uos = [uo.pk for uo in UnidadeOrganizacional.objects.uo().all()]
            modalidades = [campo.pk for campo in Modalidade.objects.all()]

            data_inicio = ano
            data_fim = ano

            for uo in uos:
                variaveis_edu = self.processar_variaveis(data_inicio, data_fim, modalidades, uo)
                for variavel_edu in list(variaveis_edu.keys()):
                    try:
                        variavel_pdi = VariavelPDI.objects.get(sigla=variavel_edu)
                        variavel = VariavelCampus.objects.get(variavel=variavel_pdi, uo=uo, ano=ano)
                        variavel.valor_real = list(variaveis_edu.get(variavel_edu).values())[0]
                        variavel.data_atualizacao = datetime.datetime.now()
                        variavel.save()
                        trimestre = PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date=datetime.date.today()).first().trimestre
                        variavel_trimestral = VariavelTrimestralCampus.objects.get_or_create(variavel=variavel, ano=variavel.ano, trimestre=trimestre)[0]
                        variavel_trimestral.valor = variavel.valor_real
                        variavel_trimestral.save()

                    except VariavelPDI.DoesNotExist:
                        pass
            print('Váriáveis do Edu Importadas')
