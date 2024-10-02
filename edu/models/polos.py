# -*- coding: utf-8 -*-
import datetime

from dateutil.parser import parse
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from comum.models import UsuarioGrupo
from djtools.db import models
from edu.managers import FiltroPoloManager
from edu.models.cadastros_gerais import Turno
from edu.models.logs import LogModel
from rh.models import Funcionario


class Polo(LogModel):
    descricao = models.CharFieldPlus('Descrição do Polo')
    sigla = models.CharFieldPlus('Sigla')
    cidade = models.ForeignKeyPlus('edu.Cidade', verbose_name='Cidade', null=True)
    codigo_academico = models.IntegerField('Código Acadêmico', null=True)
    codigo_censup = models.CharFieldPlus('Código CENSUP', default='', blank=True)
    estrutura_disponivel = models.TextField('Estrutura Disponível', null=True, blank=True)
    # endereco
    logradouro = models.CharFieldPlus('Logradouro', max_length=255, null=True, blank=True)
    numero = models.CharFieldPlus('Número', max_length=255, null=True, blank=True)
    complemento = models.CharFieldPlus('Complemento', max_length=255, null=True, blank=True)
    bairro = models.CharFieldPlus('Bairro', max_length=255, null=True, blank=True)
    cep = models.CharFieldPlus('CEP', max_length=255, null=True, blank=True)
    # dados específicos
    do_municipio = models.BooleanField('Polo do Município', default=False)
    diretoria = models.ForeignKeyPlus('edu.Diretoria', verbose_name='Diretoria Acadêmica', null=True, blank=False)
    # telefones
    telefone_principal = models.CharFieldPlus('Telefone Principal', max_length=255, null=True, blank=True)
    telefone_secundario = models.CharFieldPlus('Telefone Secundário', max_length=255, null=True, blank=True)
    campus_atendimento = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus de Atendimento', null=True, blank=True)

    objects = models.Manager()
    locals = FiltroPoloManager('diretoria')

    class Meta:
        verbose_name = 'Polo EAD'
        verbose_name_plural = 'Polos EAD'

    def get_coordenador_titular(self):
        qs = self.coordenadorpolo_set.filter(titular=True)
        return qs and qs[0] or None

    def get_proximas_atividades(self):
        return self.atividadepolo_set.filter(data_inicio__gte=datetime.datetime.now()).order_by('data_inicio').order_by('data_fim')

    def definiu_horario(self):
        return self.horariofuncionamentopolo_set.exists()

    def get_tutores(self, curso_campus):
        return self.tutorpolo_set.filter(cursos=curso_campus)

    def get_cursos_ofertados(self):
        from edu.models import CursoCampus

        return CursoCampus.objects.filter(aluno__polo=self).distinct()

    def get_endereco(self):
        if self.logradouro:
            return '{}, {}, {}, {}, {}, {}'.format(self.logradouro or '-', self.numero or '-', self.complemento or '-', self.bairro or '-', self.cep or '-', self.cidade or '-')
        else:
            return None

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/edu/polo/{}'.format(self.id)

    def get_horarios_por_turno(self, turno=None):
        if turno:
            turnos_ids = [turno.pk]
        else:
            if self.horariofuncionamentopolo_set.exists():
                turnos_ids = HorarioFuncionamentoPolo.objects.filter(polo=self).values_list('turno__id', flat=True).distinct()
            else:
                turnos_ids = []
        dias_semana = HorarioTutorPolo.DIA_SEMANA_CHOICES
        turnos = Turno.objects.filter(id__in=turnos_ids).order_by('-id')

        for turno in turnos:
            turno.horarios = []
            turno.dias_semana = dias_semana
            for horario in turno.horariofuncionamentopolo_set.filter(polo=self):
                horario.dias_semana = []
                for dia_semana in dias_semana:
                    numero = dia_semana[0]
                    nome = dia_semana[1]
                    qs = self.horariopolo_set.filter(dia_semana=dia_semana[0], horario_funcionamento=horario)
                    marcado = qs.count()
                    tutores = HorarioTutorPolo.objects.filter(horario_funcionamento=horario, dia_semana=dia_semana[0]).values_list(
                        'tutor__funcionario__pessoafisica_ptr__nome', flat=True
                    )
                    coordenadores = HorarioCoordenadorPolo.objects.filter(horario_funcionamento=horario, dia_semana=dia_semana[0]).values_list(
                        'coordenador__funcionario__pessoafisica_ptr__nome', flat=True
                    )
                    if qs.exists():
                        qs = qs[0]
                    else:
                        qs = None
                    horario.dias_semana.append(dict(numero=numero, nome=nome, marcado=marcado, horario_aula_diario=qs, tutores=tutores, coordenadores=coordenadores))
                turno.horarios.append(horario)
        return turnos


class AtividadePolo(LogModel):
    polo = models.ForeignKeyPlus('edu.Polo', verbose_name='Polo', null=False, blank=False, on_delete=models.CASCADE)
    nome = models.CharFieldPlus('Nome')
    descricao = models.TextField('Descrição', null=True, blank=True)
    sala = models.ForeignKeyPlus('comum.Sala', null=True, blank=True)
    data_inicio = models.DateTimeFieldPlus('Data de Início', null=False, blank=False)
    data_fim = models.DateTimeFieldPlus('Data de Término', null=False, blank=False)
    user = models.CurrentUserField(verbose_name='Agendador')
    confirmada = models.BooleanField('Confirmada', default=False, null=False, blank=False)

    objects = models.Manager()
    locals = FiltroPoloManager('polo__diretoria', 'polo')

    class Meta:
        verbose_name = 'Atividade do Polo'
        verbose_name_plural = 'Atividades do Polo'

    def __str__(self):
        return self.nome

    def get_situacao(self, data=None):
        if not data:
            data = datetime.datetime.now()
        if data > self.data_inicio:
            if data < self.data_fim:
                return 'Acontecendo'
            else:
                return 'Vencido'
        else:
            return 'Novo'


class HorarioFuncionamentoPolo(LogModel):
    HORARIO_1 = 1
    HORARIO_2 = 2
    HORARIO_3 = 3
    HORARIO_4 = 4
    HORARIO_5 = 5
    HORARIO_6 = 6
    HORARIO_CHOICES = [[HORARIO_1, '1'], [HORARIO_2, '2'], [HORARIO_3, '3'], [HORARIO_4, '4'], [HORARIO_5, '5'], [HORARIO_6, '6']]
    polo = models.ForeignKeyPlus('edu.Polo', on_delete=models.CASCADE)
    numero = models.PositiveIntegerField(choices=HORARIO_CHOICES)
    turno = models.ForeignKeyPlus('edu.Turno', on_delete=models.CASCADE)
    inicio = models.CharFieldPlus('Início', max_length=5)
    termino = models.CharFieldPlus('Término', max_length=5)

    class Meta:
        verbose_name = 'Horário de Funcionamento'
        verbose_name_plural = 'Horários de Funcionamento'

    def __str__(self):
        return '{} - {}'.format(self.inicio, self.termino)

    def preencher_zeros(self, horario):
        if len(horario) < 5 and len(horario.split(':')) == 2:
            hora, minuto = horario.split(':')
            horario = '{}:{}'.format(hora.zfill(2), minuto.zfill(2))
        return horario

    def clean(self):
        self.inicio = self.preencher_zeros(self.inicio)
        self.termino = self.preencher_zeros(self.termino)

        try:
            parse('01/01/2012 {}:00'.format(self.inicio), dayfirst=True)
        except Exception:
            raise ValidationError('Hora de início inválida: {}.'.format(self.inicio))

        try:
            parse('01/01/2012 {}:00'.format(self.termino), dayfirst=True)
        except Exception:
            raise ValidationError('Hora de término inválida: {}.'.format(self.termino))


class TutorPolo(LogModel):
    SEARCH_FIELDS = ['funcionario__nome', 'funcionario__username']

    polo = models.ForeignKeyPlus('edu.Polo', verbose_name='Polo', null=False, blank=False)
    funcionario = models.ForeignKeyPlus('rh.Funcionario', verbose_name='Tutor', null=False, blank=False)
    cursos = models.ManyToManyFieldPlus('edu.CursoCampus', verbose_name='Cursos', blank=False, related_name='tutor_set2')

    def __str__(self):
        return self.funcionario.nome

    def get_horario(self):
        output = []
        horarios = HorarioTutorPolo.objects.filter(tutor=self, horario_funcionamento__polo=self.polo).order_by('dia_semana')
        turnos_ids = horarios.values_list('horario_funcionamento__turno', flat=True).distinct()
        for turno in Turno.objects.filter(id__in=turnos_ids):
            dias_semana = self.horariotutorpolo_set.filter(horario_funcionamento__turno=turno).order_by('dia_semana').values_list('dia_semana', flat=True).distinct()
            for dia_semana in dias_semana:
                if output:
                    output.append(' / ')
                numeros = []
                for numero in (
                    self.horariotutorpolo_set.filter(horario_funcionamento__turno=turno, dia_semana=dia_semana).values_list('horario_funcionamento__numero', flat=True).distinct()
                ):
                    if numero not in numeros:
                        numeros.append(str(numero))
                numeros.sort()
                output.append('{}{}{}'.format(dia_semana + 1, turno.descricao[0], ''.join(numeros)))
        return ''.join(output)

    def get_horarios_por_turno(self, turno=None):
        if turno:
            turnos_ids = [turno.pk]
        else:
            turnos_ids = HorarioFuncionamentoPolo.objects.filter(polo=self.polo).values_list('turno__id', flat=True).distinct()

        dias_semana = HorarioTutorPolo.DIA_SEMANA_CHOICES
        turnos = Turno.objects.filter(id__in=turnos_ids).order_by('-id')
        for turno in turnos:
            turno.horarios = []
            turno.dias_semana = dias_semana
            for horario in turno.horariofuncionamentopolo_set.filter(polo=self.polo):
                horario.dias_semana = []
                for dia_semana in dias_semana:
                    numero = dia_semana[0]
                    nome = dia_semana[1]
                    qs = self.horariotutorpolo_set.filter(dia_semana=dia_semana[0], horario_funcionamento=horario)
                    marcado = qs.count()
                    if qs.exists():
                        qs = qs[0]
                    else:
                        qs = None
                    horario.dias_semana.append(dict(numero=numero, nome=nome, marcado=marcado, horario_aula_diario=qs))
                turno.horarios.append(horario)
        return turnos

    def delete(self, *args, **kwargs):
        super(TutorPolo, self).delete(*args, **kwargs)
        if not self.funcionario.tutorpolo_set.exists():
            grupo = Group.objects.get(name='Tutor de Polo EAD')
            UsuarioGrupo.objects.filter(user=self.funcionario.user, group=grupo).delete()


class HorarioPolo(LogModel):
    DIA_SEMANA_SEG = 1
    DIA_SEMANA_TER = 2
    DIA_SEMANA_QUA = 3
    DIA_SEMANA_QUI = 4
    DIA_SEMANA_SEX = 5
    DIA_SEMANA_SAB = 6
    DIA_SEMANA_DOM = 7
    DIA_SEMANA_CHOICES = [
        [DIA_SEMANA_SEG, 'Segunda'],
        [DIA_SEMANA_TER, 'Terça'],
        [DIA_SEMANA_QUA, 'Quarta'],
        [DIA_SEMANA_QUI, 'Quinta'],
        [DIA_SEMANA_SEX, 'Sexta'],
        [DIA_SEMANA_SAB, 'Sábado'],
        [DIA_SEMANA_DOM, 'Domingo'],
    ]

    polo = models.ForeignKeyPlus('edu.Polo', on_delete=models.CASCADE)
    dia_semana = models.PositiveIntegerField(choices=DIA_SEMANA_CHOICES)
    horario_funcionamento = models.ForeignKeyPlus('edu.HorarioFuncionamentoPolo', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Horário do Polo'
        verbose_name_plural = 'Horários do Polo'

    def __str__(self):
        return str(self.pk)

    @staticmethod
    def get_dias_semana_seg_a_sex():
        dias_semana = []
        for dia in HorarioTutorPolo.DIA_SEMANA_CHOICES:
            if dia[0] < 6:
                dias_semana.append(dia)
        return dias_semana


class HorarioTutorPolo(LogModel):
    DIA_SEMANA_SEG = 1
    DIA_SEMANA_TER = 2
    DIA_SEMANA_QUA = 3
    DIA_SEMANA_QUI = 4
    DIA_SEMANA_SEX = 5
    DIA_SEMANA_SAB = 6
    DIA_SEMANA_DOM = 7
    DIA_SEMANA_CHOICES = [
        [DIA_SEMANA_SEG, 'Segunda'],
        [DIA_SEMANA_TER, 'Terça'],
        [DIA_SEMANA_QUA, 'Quarta'],
        [DIA_SEMANA_QUI, 'Quinta'],
        [DIA_SEMANA_SEX, 'Sexta'],
        [DIA_SEMANA_SAB, 'Sábado'],
        [DIA_SEMANA_DOM, 'Domingo'],
    ]

    tutor = models.ForeignKeyPlus('edu.TutorPolo', on_delete=models.CASCADE)
    dia_semana = models.PositiveIntegerField(choices=DIA_SEMANA_CHOICES)
    horario_funcionamento = models.ForeignKeyPlus('edu.HorarioFuncionamentoPolo', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Horário do Tutor'
        verbose_name_plural = 'Horários do Tutor'

    def __str__(self):
        return str(self.pk)

    @staticmethod
    def get_dias_semana_seg_a_sex():
        dias_semana = []
        for dia in HorarioTutorPolo.DIA_SEMANA_CHOICES:
            if dia[0] < 6:
                dias_semana.append(dia)
        return dias_semana


class CoordenadorPolo(LogModel):
    polo = models.ForeignKeyPlus('edu.Polo', verbose_name='Polo', null=False, blank=False)
    funcionario = models.ForeignKeyPlus(Funcionario, verbose_name='Funcionário', null=False, blank=False)
    titular = models.BooleanField('Titular', default=False)

    def __str__(self):
        return self.funcionario.nome

    def get_horario(self):
        output = []
        horarios = HorarioCoordenadorPolo.objects.filter(coordenador=self, horario_funcionamento__polo=self.polo).order_by('dia_semana')
        turnos_ids = horarios.values_list('horario_funcionamento__turno', flat=True).distinct()
        for turno in Turno.objects.filter(id__in=turnos_ids):
            dias_semana = self.horariocoordenadorpolo_set.filter(horario_funcionamento__turno=turno).order_by('dia_semana').values_list('dia_semana', flat=True).distinct()
            for dia_semana in dias_semana:
                if output:
                    output.append(' / ')
                numeros = []
                for numero in (
                    self.horariocoordenadorpolo_set.filter(horario_funcionamento__turno=turno, dia_semana=dia_semana)
                    .values_list('horario_funcionamento__numero', flat=True)
                    .distinct()
                ):
                    if numero not in numeros:
                        numeros.append(str(numero))
                numeros.sort()
                output.append('{}{}{}'.format(dia_semana + 1, turno.descricao[0], ''.join(numeros)))
        return ''.join(output)

    def get_horarios_por_turno(self, turno=None):
        if turno:
            turnos_ids = [turno.pk]
        else:
            turnos_ids = HorarioFuncionamentoPolo.objects.filter(polo=self.polo).values_list('turno__id', flat=True).distinct()

        dias_semana = HorarioCoordenadorPolo.DIA_SEMANA_CHOICES
        turnos = Turno.objects.filter(id__in=turnos_ids).order_by('-id')

        for turno in turnos:
            turno.horarios = []
            turno.dias_semana = dias_semana
            for horario in turno.horariofuncionamentopolo_set.filter(polo=self.polo):
                horario.dias_semana = []
                for dia_semana in dias_semana:
                    numero = dia_semana[0]
                    nome = dia_semana[1]
                    qs = self.horariocoordenadorpolo_set.filter(dia_semana=dia_semana[0], horario_funcionamento=horario)
                    marcado = qs.count()
                    if qs.exists():
                        qs = qs[0]
                    else:
                        qs = None
                    horario.dias_semana.append(dict(numero=numero, nome=nome, marcado=marcado, horario_aula_diario=qs))
                turno.horarios.append(horario)
        return turnos

    def delete(self, *args, **kwargs):
        super(CoordenadorPolo, self).delete(*args, **kwargs)
        if not self.funcionario.coordenadorpolo_set.exists():
            grupo = Group.objects.get(name='Coordenador de Polo EAD')
            UsuarioGrupo.objects.filter(user=self.funcionario.user, group=grupo).delete()


class HorarioCoordenadorPolo(LogModel):
    DIA_SEMANA_SEG = 1
    DIA_SEMANA_TER = 2
    DIA_SEMANA_QUA = 3
    DIA_SEMANA_QUI = 4
    DIA_SEMANA_SEX = 5
    DIA_SEMANA_SAB = 6
    DIA_SEMANA_DOM = 7
    DIA_SEMANA_CHOICES = [
        [DIA_SEMANA_SEG, 'Segunda'],
        [DIA_SEMANA_TER, 'Terça'],
        [DIA_SEMANA_QUA, 'Quarta'],
        [DIA_SEMANA_QUI, 'Quinta'],
        [DIA_SEMANA_SEX, 'Sexta'],
        [DIA_SEMANA_SAB, 'Sábado'],
        [DIA_SEMANA_DOM, 'Domingo'],
    ]

    coordenador = models.ForeignKeyPlus('edu.CoordenadorPolo', on_delete=models.CASCADE)
    dia_semana = models.PositiveIntegerField(choices=DIA_SEMANA_CHOICES)
    horario_funcionamento = models.ForeignKeyPlus('edu.HorarioFuncionamentoPolo', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Horário do Coordenador do Polo'
        verbose_name_plural = 'Horários do Coordenador do Polo'

    def __str__(self):
        return str(self.pk)

    @staticmethod
    def get_dias_semana_seg_a_sex():
        dias_semana = []
        for dia in HorarioCoordenadorPolo.DIA_SEMANA_CHOICES:
            if dia[0] < 6:
                dias_semana.append(dia)
        return dias_semana
