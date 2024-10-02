import json
import datetime
import requests
from bs4 import BeautifulSoup
from django.apps import apps
from os.path import join
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.aggregates import Sum
from django.conf import settings
from django.dispatch import Signal
from comum.models import Ano
from comum.utils import get_uo, tl
from djtools.db import models
from djtools.templatetags.filters import in_group
from djtools.utils import years_between
from edu.managers import FiltroUnidadeOrganizacionalManager, FiltroDiretoriaManager
from edu.models import CursoCampus, Aluno, Matriz, MatrizCurso, LogModel, LinhaPesquisa
from rh.models import PessoaFisica, Servidor
from rh.models import UnidadeOrganizacional
import zlib
import xmltodict


ausencia_candidato_sinal = Signal()   # providing_args=["candidato_vaga_id"]
matricula_candidato_sinal = Signal()  # providing_args=["candidato_vaga_id"]
inaptidao_candidato_sinal = Signal()  # providing_args=["candidato_vaga_id"]


class Edital(LogModel):
    configuracao_migracao_vagas = models.ForeignKeyPlus(
        'processo_seletivo.ConfiguracaoMigracaoVaga', verbose_name='Configuração de Migração de Vagas', null=True, blank=True, on_delete=models.CASCADE
    )
    codigo = models.IntegerField('Código')
    descricao = models.CharFieldPlus('Descrição')
    ano = models.ForeignKeyPlus(Ano, verbose_name='Ano', on_delete=models.CASCADE)
    semestre = models.IntegerField('Semestre')
    data_encerramento = models.DateField(verbose_name='Data de Encerramento', null=True, blank=True)

    # Novos atributos
    sisu = models.BooleanField('Sisu?', default=False)
    qtd_vagas = models.IntegerField('Quantidade de Vagas')
    qtd_inscricoes = models.IntegerField('Quantidade de Inscrições')
    qtd_inscricoes_confirmadas = models.IntegerField('Quantidade de Inscrições Confirmadas')

    detalhamento_por_campus = models.TextField('Detalhamento por Campus')
    '''
    Abaixo temos um exemplo do valor presente dentro do atributo "detalhamento_por_campus". Para rotinar internas no
    SUAP, tomar com chave apenas o suap_unidade_organizacional_id. Essa chave é que indica para qual campus do SUAP deverá
    ser atribuído o detalhamento. Isso é necessário porque no SGC há campus que não usam o mesmo padrão de nomeclatura da
    sigla e também há campus que não existem no SUAP, como por exemplo os "Pólos", que são unidades EAD existesntes no
    SGC. Nesse caso específico, todos os valores deverão ser atribuídos ao campus EAD do SUAP.

    {"qtd_inscricoes": 125, "suap_unidade_organizacional_id": "14", "campus": "EaD", "qtd_inscricoes_confirmadas": 18, "qtd_vagas": 30}, {"qtd_inscricoes": 28, "suap_unidade_organizacional_id": "14", "campus": "Polo SC", "qtd_inscricoes_confirmadas": 6, "qtd_vagas": 30}]
    '''

    remanescentes = models.BooleanField('Vagas Remanescentes?', default=False)
    matricula_no_polo = models.BooleanField('Matrícula no Polo?', default=False)
    webservice = models.ForeignKeyPlus('processo_seletivo.WebService', verbose_name='WebService', null=True, blank=True, default=None, on_delete=models.CASCADE)

    matricula_online = models.BooleanField('Matrícula Online', default=False)

    objects = models.Manager()
    locals = FiltroDiretoriaManager('ofertavagacurso__curso_campus__diretoria')

    class Meta:
        verbose_name = 'Edital'
        verbose_name_plural = 'Editais'
        permissions = (
            ("pode_ausentar_candidatos", "Pode Ausentar Candidatos"),
            ("pode_liberar_periodos", "Pode Liberar Periodos"),
            ("pode_matricular_proitec", "Pode Matricular Alunos Proitec")
        )

    def __str__(self):
        return '{}'.format(self.descricao)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_pendencias(self):
        pendencias = []
        if self.lista_set.filter(forma_ingresso__isnull=True).exists():
            pendencias.append('As formas de ingresso de todas as listas ainda não foram definidas para este edital')
        if self.configuracao_migracao_vagas_id:
            if self.configuracao_migracao_vagas.is_sisu and not self.sisu:
                pendencias.append('Este edital não é SISU, mas uma configuração de migração de vagas SISU foi definida para ele')
            if self.sisu and not self.configuracao_migracao_vagas.is_sisu:
                pendencias.append('Este edital é SISU, mas uma configuração de migração de vagas que não é SISU foi definida para ele')
            precedencia_matricula = []
            for i in range(1, 16):
                rotulo_lista = getattr(self.configuracao_migracao_vagas, 'lista_{}'.format(i))
                if rotulo_lista:
                    precedencia_matricula.append(rotulo_lista.nome)
            for lista in self.lista_set.all():
                if lista.descricao not in precedencia_matricula:
                    pendencias.append('A lista "{}" não consta na precedência de matrícula da configuração de migração de vagas definida para este edital'.format(lista.descricao))
                if lista.descricao != 'Geral' and not self.configuracao_migracao_vagas.precedenciamigracao_set.filter(origem__nome=lista.descricao).exists():
                    pendencias.append('A lista "{}" não consta na precedência de migração da configuração de migração de vagas definida para este edital'.format(lista.descricao))
        return pendencias

    def get_absolute_url(self):
        return '/processo_seletivo/edital/%d/' % self.pk

    def get_detalhamento_por_campus_sgc_agrupado_por_suap_unidade_organizacional_id(self, campus_id):
        campus = ''
        qtd_inscricoes_total = 0
        qtd_inscricoes_confirmadas_total = 0
        qtd_vagas_total = 0
        id_campus_localizado = False

        if self.detalhamento_por_campus:
            json_dict_list = json.loads(self.detalhamento_por_campus)
            for json_dict in json_dict_list:
                # Os campus do SGC (Sistema Gerenciador de Concursos) não necessariamente serão os mesmos do SUAP.
                # No caso, podem haver dois ou mais campus do SGC apontando para um mesmo campus do SUAP, ou seja,
                # usando o mesmo valor para o atributo "suap_unidade_organizacional_id".
                if int(json_dict['suap_unidade_organizacional_id']) == campus_id:
                    id_campus_localizado = True
                    if campus:
                        campus += '; ' + json_dict['campus']
                    else:
                        campus += json_dict['campus']

                    qtd_inscricoes_total += json_dict['qtd_inscricoes'] or 0
                    qtd_inscricoes_confirmadas_total += json_dict['qtd_inscricoes_confirmadas'] or 0
                    qtd_vagas_total += json_dict['qtd_vagas'] or 0

            if id_campus_localizado:
                return {
                    'suap_unidade_organizacional_id': campus_id,
                    'campus': campus,
                    'qtd_inscricoes': qtd_inscricoes_total,
                    'qtd_inscricoes_confirmadas': qtd_inscricoes_confirmadas_total,
                    'qtd_vagas': qtd_vagas_total,
                }

        return None

    def em_periodo_avaliacao(self, campus=None):
        periodo_liberacao = EditalPeriodoLiberacao.objects.filter(edital=self)

        if campus is not None:
            periodo_liberacao = periodo_liberacao.filter(uo=campus)

        if not periodo_liberacao.exists():
            return False

        periodo_liberacao = periodo_liberacao.latest('id')

        if periodo_liberacao.data_fim_matricula and periodo_liberacao.data_limite_avaliacao:
            if periodo_liberacao.data_fim_matricula < datetime.datetime.now() <= periodo_liberacao.data_limite_avaliacao:
                return True
        return False

    def em_periodo_matricula(self, campus=None):
        now = datetime.datetime.now()
        periodo_liberacao = EditalPeriodoLiberacao.objects.filter(edital=self)

        if campus is not None:
            periodo_liberacao = periodo_liberacao.filter(uo=campus)

        if not periodo_liberacao.exists():
            return False

        periodo_liberacao = periodo_liberacao.latest('id')

        if periodo_liberacao.data_inicio_matricula is None or periodo_liberacao.data_fim_matricula is None:
            return False

        return periodo_liberacao.data_inicio_matricula <= now <= periodo_liberacao.data_fim_matricula

    def possui_curso_proitec(self):
        return self.get_ids_cursos_proitec().exists()

    def get_ids_cursos_proitec(self):
        return OfertaVagaCurso.objects.filter(edital=self, curso_campus__matrizcurso__matriz__estrutura__proitec=True).values_list('curso_campus__id', flat=True).distinct()

    def get_matrizes_pronatec(self):
        ids = MatrizCurso.objects.filter(curso_campus__id__in=self.get_ids_cursos_proitec()).values_list('matriz__id', flat=True)
        return Matriz.objects.filter(id__in=ids).distinct()

    def possui_aluno_matriculado(self):
        return Aluno.objects.filter(candidato_vaga__oferta_vaga__oferta_vaga_curso__edital=self).exists()

    def formas_ingresso_estao_configuradas(self):
        return not self.lista_set.filter(forma_ingresso__isnull=True).exists()

    def get_uos(self):
        pks_uos_edital = OfertaVagaCurso.locals.filter(edital=self).values_list('curso_campus__diretoria__setor__uo', flat=True)
        uos = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_edital)
        return uos

    def get_quantidade_vagas(self):
        return OfertaVaga.objects.filter(oferta_vaga_curso__edital=self).aggregate(Sum('qtd')).get('qtd__sum')

    def get_quantidade_vagas_ofertadas(self):
        return not self.remanescentes and self.get_quantidade_vagas() or 0

    def get_quantidade_candidatos(self):
        return self.candidato_set.count()

    def importar_caracterizacoes(self):
        xml = self.webservice.caracterizacoes(self.codigo)
        response = xmltodict.parse(xml)
        if response.get('edital').get('caracterizacoes'):
            Caracterizacao = apps.get_model('ae.Caracterizacao')
            return Caracterizacao.importar_caracterizacao(response)
        return 0, 0

    def expirar_candidatos_chamada(self, chamada):
        numero_processado = 0
        candidatos_vaga = CandidatoVaga.objects.filter(
            candidato__edital=self,
            convocacao=chamada
        )

        for candidato in candidatos_vaga:
            candidato.registrar_ausencia()
            numero_processado += 1

        return numero_processado

    def pode_ausentar(self, user, uo=None):
        if not user.has_perm('processo_seletivo.pode_ausentar_candidatos'):
            return False
        now = datetime.datetime.now()
        periodo_liberacao = EditalPeriodoLiberacao.objects.filter(edital=self, data_limite_avaliacao__lt=now)

        if uo:
            periodo_liberacao = periodo_liberacao.filter(uo=uo)

        if periodo_liberacao.exists():
            candidatos_vaga = CandidatoVaga.objects.filter(
                candidato__edital=self,
                convocacao__isnull=False
            ).filter(Q(situacao__isnull=True) | Q(situacao=CandidatoVaga.AUSENTE))
            if uo:
                candidatos_vaga = candidatos_vaga.filter(
                    candidato__curso_campus__diretoria__setor__uo=uo
                )
            return candidatos_vaga.exists()

        return False

    def can_change(self, user):
        return in_group(user, 'Administrador Acadêmico')


class EditalPeriodoLiberacao(models.ModelPlus):
    edital = models.ForeignKeyPlus(Edital)
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional')
    usuario = models.ForeignKeyPlus('comum.User', null=True)
    data_inicio_matricula = models.DateTimeFieldPlus('Data de início das matrículas', null=True, blank=True)
    data_fim_matricula = models.DateTimeFieldPlus('Data de fim das matrículas', null=True, blank=True)
    data_limite_avaliacao = models.DateTimeFieldPlus('Data limite para avaliação', null=True, blank=True)

    class Meta:
        verbose_name = 'Período de Liberação Matrícula'
        verbose_name_plural = 'Períodos de Liberação Matrícula'

    def __str__(self):
        return f'{self.uo}: {self.data_inicio_matricula}/{self.data_fim_matricula}'

    def save(self, *args, **kwargs):
        usuario = kwargs.pop('user', tl.get_user())
        anterior = None

        if self.pk is not None:
            anterior = EditalPeriodoLiberacao.objects.get(pk=self.pk)
        else:
            self.usuario = usuario

        super().save(*args, **kwargs)

        salvar_historico = False

        if anterior:  # Alteração de dados
            if self.data_inicio_matricula and anterior.data_inicio_matricula and self.data_inicio_matricula != anterior.data_inicio_matricula:
                salvar_historico = True
            else:
                if self.data_limite_avaliacao and anterior.data_limite_avaliacao and self.data_limite_avaliacao != anterior.data_limite_avaliacao:
                    salvar_historico = True

        if salvar_historico:
            periodo = EditalPeriodoLiberacaoHistorico()
            periodo.periodo_liberacao = self
            periodo.usuario = anterior.usuario
            periodo.data_inicio_matricula = anterior.data_inicio_matricula
            periodo.data_fim_matricula = anterior.data_fim_matricula
            periodo.data_limite_avaliacao = anterior.data_limite_avaliacao
            periodo.save()

    def pode_editar(self, user):
        return user.has_perm('processo_seletivo.add_edital') or (self.uo == get_uo(user) and user.has_perm('processo_seletivo.pode_liberar_periodos'))


class EditalPeriodoLiberacaoHistorico(models.ModelPlus):
    periodo_liberacao = models.ForeignKeyPlus(EditalPeriodoLiberacao)
    usuario = models.ForeignKeyPlus('comum.User', null=True)
    data_inicio_matricula = models.DateTimeFieldPlus('Data de início das matrículas', null=True, blank=True)
    data_fim_matricula = models.DateTimeFieldPlus('Data de fim das matrículas', null=True, blank=True)
    data_limite_avaliacao = models.DateTimeFieldPlus('Data limite para avaliação', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        verbose_name = 'Histórico de Liberação de Matrícula'
        verbose_name_plural = 'Histórico de Liberações de Matrícula'


class Lista(LogModel):
    codigo = models.CharFieldPlus('Código')
    descricao = models.TextField('Descrição')
    forma_ingresso = models.ForeignKeyPlus('edu.FormaIngresso', verbose_name='Forma de Igresso', null=True, blank=True, on_delete=models.CASCADE)
    edital = models.ForeignKeyPlus(Edital, verbose_name='Edital', null=True, blank=False, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Lista'
        verbose_name_plural = 'Listas'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class OfertaVagaCurso(models.ModelPlus):
    edital = models.ForeignKeyPlus(Edital)
    curso_campus = models.ForeignKeyPlus(CursoCampus)
    linha_pesquisa = models.ForeignKeyPlus(LinhaPesquisa, null=True, on_delete=models.CASCADE)
    turno = models.ForeignKeyPlus('edu.Turno', verbose_name='Turno', null=True, on_delete=models.CASCADE)
    qtd_inscritos = models.IntegerField(verbose_name='Quantidade de Inscritos', default=0)
    campus_polo = models.CharFieldPlus(verbose_name='Campus/Polo', default='')

    objects = models.Manager()
    locals = FiltroDiretoriaManager('curso_campus__diretoria')

    class Meta:
        verbose_name = 'Oferta de Vaga em Curso'
        verbose_name_plural = 'Ofertas de Vagas em Curso'
        ordering = ('curso_campus',)

    def get_ofertas_vaga(self):
        ofertas_vaga = []
        if self.edital.configuracao_migracao_vagas_id:
            nomes_listas = self.edital.configuracao_migracao_vagas.get_nomes_listas_ordenadas_por_restricao()
            for nome_lista in nomes_listas:
                oferta_vaga = self.ofertavaga_set.filter(lista__descricao=nome_lista).first()
                if oferta_vaga:
                    ofertas_vaga.append(oferta_vaga)
        else:
            ofertas_vaga.extend(list(self.ofertavaga_set.all()))
        return ofertas_vaga

    def get_candidatos_aguardando_convocacao(self):
        return CandidatoVaga.objects.filter(convocacao__isnull=True, situacao__isnull=True, oferta_vaga__oferta_vaga_curso_id=self.pk).values_list('candidato', flat=True).distinct()

    def is_processamento_encerrado(self):
        return not CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso_id=self.pk, situacao__isnull=True).exists()

    def get_total_vagas(self, incluir_vagas_extras=False):
        qtd = sum(self.ofertavaga_set.values_list('qtd', flat=True))
        if incluir_vagas_extras:
            qtd += sum(CriacaoVagaRemanescente.objects.filter(oferta_vaga__oferta_vaga_curso=self).values_list('qtd', flat=True))
        return qtd

    def get_total_matriculados(self):
        return CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso_id=self.pk, situacao=CandidatoVaga.MATRICULADO).count()

    def get_percentual_matriculados(self):
        total_vagas = self.get_total_vagas()
        total_matriculados = self.get_total_matriculados()
        return int(total_matriculados * 100 / total_vagas)

    def get_numero_ultima_chamada(self):
        qs = CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso_id=self.pk, convocacao__isnull=False).values_list('convocacao', flat=True).order_by('-convocacao')
        return qs.first() or 0

    def pode_cancelar_ultima_chamada(self):
        numero_ultima_chamada = self.get_numero_ultima_chamada()
        if numero_ultima_chamada > 1:
            qs = CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso_id=self.pk, convocacao=numero_ultima_chamada)
            return qs.exists() and not qs.filter(situacao__isnull=False).exists()
        return False

    @transaction.atomic()
    def cancelar_ultima_chamada(self):
        if self.pode_cancelar_ultima_chamada():
            numero_ultima_chamada = self.get_numero_ultima_chamada()
            CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso=self, convocacao=numero_ultima_chamada).update(convocacao=None, vaga=None)
            if numero_ultima_chamada > 1:
                numero_ultima_chamada -= 1
                qs_candidato_vaga = CandidatoVaga.objects.filter(
                    oferta_vaga__oferta_vaga_curso=self, convocacao=numero_ultima_chamada, vaga__isnull=True, situacao__in=[CandidatoVaga.AUSENTE, CandidatoVaga.INAPTO]
                )
                for cv in qs_candidato_vaga:
                    vaga = Vaga.objects.filter(candidatovaga__isnull=True, oferta_vaga=cv.oferta_vaga).first()
                    cv.vaga = vaga
                    cv.save()

    def pode_realizar_nova_chamada(self):
        return not CandidatoVaga.objects.filter(oferta_vaga__oferta_vaga_curso_id=self.pk, convocacao__isnull=False, situacao__isnull=True).exists()

    @transaction.atomic()
    def realizar_nova_chamada(self, importacao_edital=False):
        convocados = []
        if importacao_edital and self.get_numero_ultima_chamada() == 1:
            numero_chamada = 1
        else:
            numero_chamada = self.get_numero_ultima_chamada() + 1
        vagas = []
        if self.edital.configuracao_migracao_vagas_id:
            precedencias = self.edital.configuracao_migracao_vagas.get_precedencias(apenas_descricao=True)
        else:
            precedencias = [[lista.descricao, []] for lista in self.edital.lista_set.all()]

        if numero_chamada == 1:
            ofertas_vaga = self.get_ofertas_vaga()
            for oferta_vaga in ofertas_vaga:
                for convocado in oferta_vaga.realizar_nova_chamada(numero_chamada):
                    convocados.append(convocado)

        elif numero_chamada > 1:
            for origem, destinos in precedencias:
                oferta_vaga_origem = self.ofertavaga_set.filter(lista__descricao=origem).first()
                if oferta_vaga_origem:
                    oferta_vaga_origem.realizar_nova_chamada(numero_chamada)
                    vagas = vagas + oferta_vaga_origem.get_vagas_disponiveis()
                    if vagas:
                        for destino in destinos:
                            while vagas:
                                oferta_vaga_destino = self.ofertavaga_set.filter(lista__descricao=destino).first()
                                if oferta_vaga_destino:
                                    vaga = vagas.pop()
                                    convocado = oferta_vaga_destino.convocar_proximo_candidato(vaga, numero_chamada)
                                    if convocado:
                                        convocados.append(convocado)
                                    else:
                                        vagas.append(vaga)
                                        break
                                else:
                                    break
        return convocados

    def get_numeros_chamadas(self):
        return list(range(1, self.get_numero_ultima_chamada() + 1))


class OfertaVaga(models.ModelPlus):
    oferta_vaga_curso = models.ForeignKeyPlus(OfertaVagaCurso, null=True)
    lista = models.ForeignKeyPlus(Lista, on_delete=models.CASCADE)
    qtd = models.IntegerField('Quantidade', null=True, default=0)

    objects = models.Manager()
    locals = FiltroDiretoriaManager('oferta_vaga_curso__curso_campus__diretoria')

    class Meta:
        verbose_name = 'Oferta de Vaga'
        verbose_name_plural = 'Ofertas de Vagas'
        ordering = ('oferta_vaga_curso__curso_campus', 'lista__descricao')

    def __str__(self):
        return '{}, {}, {}'.format(self.oferta_vaga_curso.edital, self.oferta_vaga_curso.curso_campus.descricao_historico, self.lista.descricao)

    def get_absolute_url(self):
        return '/processo_seletivo/oferta_vaga/%d/' % self.pk

    def get_candidatos_inaptos_ausentes(self):
        return self.candidatovaga_set.filter(convocacao__isnull=False, situacao__in=(CandidatoVaga.AUSENTE, CandidatoVaga.INAPTO))

    def get_candidatos_classificados(self):
        return self.candidatovaga_set.filter(eliminado=False)

    def get_candidatos_aprovados(self):
        return self.get_candidatos_classificados().filter(aprovado=True)

    def get_candidatos_convocados(self):
        return self.candidatovaga_set.filter(convocacao__isnull=False)

    def get_candidatos_convocados_aguardando_matricula(self):
        return self.candidatovaga_set.filter(convocacao__isnull=False, situacao__isnull=True)

    def get_candidatos_aguardando_convocacao(self):
        return self.candidatovaga_set.filter(convocacao__isnull=True, situacao__isnull=True)

    def get_candidatos_matriculados(self):
        return self.candidatovaga_set.filter(situacao=CandidatoVaga.MATRICULADO)

    def vagas_pode_ser_migradas(self):
        is_sisu = self.oferta_vaga_curso.edital.configuracao_migracao_vagas and self.oferta_vaga_curso.edital.configuracao_migracao_vagas.is_sisu
        return is_sisu or self.get_candidatos_matriculados().count() >= self.qtd or not self.get_candidatos_classificados().filter(situacao__isnull=True).exists()

    def get_vagas_usadas_de_migracao(self):
        return Vaga.objects.filter(candidatovaga__oferta_vaga=self).exclude(oferta_vaga_id=self.pk)

    def get_info_vagas_usadas_de_migracao(self):
        lista = []
        for item in self.get_vagas_usadas_de_migracao().values('oferta_vaga__lista__descricao').annotate(dcount=Count('pk')):
            lista.append('{} : {}'.format(item['oferta_vaga__lista__descricao'], item['dcount']))
        return '\n'.join(lista)

    def get_vagas_usadas_em_migracao(self):
        return self.vaga_set.filter(candidatovaga__isnull=False).exclude(candidatovaga__oferta_vaga_id=self.pk)

    def get_info_vagas_usadas_em_migracao(self):
        lista = []
        for item in self.get_vagas_usadas_em_migracao().values('candidatovaga__oferta_vaga__lista__descricao').annotate(dcount=Count('pk')):
            lista.append('{} : {}'.format(item['candidatovaga__oferta_vaga__lista__descricao'], item['dcount']))
        return '\n'.join(lista)

    def get_vagas_ocupadas(self):
        return self.vaga_set.filter(candidatovaga__situacao=CandidatoVaga.MATRICULADO)

    def is_lista_fechada(self):
        return not self.candidatovaga_set.filter(situacao__isnull=True).exists()

    def is_lista_aprovado_fechada(self):
        return not self.candidatovaga_set.filter(situacao__isnull=True, aprovado=True).exists()

    def get_percentual_matriculados(self):
        if self.qtd:
            percentual = int(self.get_candidatos_matriculados().count() * 100 / self.qtd)
            return percentual > 100 and 100 or percentual
        else:
            return 100

    def get_total_vagas_ocupadas(self):
        if self.oferta_vaga_curso.curso_campus.matrizcurso_set.filter(matriz__estrutura__proitec=True).exists():
            return self.get_candidatos_convocados().count()
        else:
            return self.vaga_set.filter(candidatovaga__situacao=CandidatoVaga.MATRICULADO).count()

    def get_percentual_ocupacao(self):
        total_vagas = self.qtd
        total_vagas_ocupadas = self.get_total_vagas_ocupadas()
        return total_vagas and int(total_vagas_ocupadas * 100 / total_vagas) or 0

    def get_candidatos_processados(self):
        return self.get_candidatos_convocados().filter(situacao__isnull=False)

    def get_percentual_convocados_matriculados(self):
        total_convocados = self.get_candidatos_convocados().count()
        total_convocados_processados = self.get_candidatos_processados().count()
        return total_convocados and int(total_convocados_processados * 100 / total_convocados) or 0

    def get_proximo_candidato_apto_convocacao(self, numero_chamada):
        qs = self.get_candidatos_classificados().filter(convocacao__isnull=True, situacao__isnull=True)
        if numero_chamada == 1:
            qs = qs.filter(aprovado=True)
        return qs.order_by('classificacao').first()

    def convocar_proximo_candidato(self, vaga, numero_chamada):
        CandidatoVaga.objects.filter(vaga=vaga).update(vaga=None)
        candidato_vaga = self.get_proximo_candidato_apto_convocacao(numero_chamada)
        if candidato_vaga:
            candidato_vaga.convocacao = numero_chamada
            candidato_vaga.vaga = vaga
            candidato_vaga.save()
            candidato_vaga.get_participacoes_em_outras_listas().update(situacao=CandidatoVaga.JA_CONVOCADO)
            return candidato_vaga
        return None

    def get_vagas_disponiveis(self):
        vagas = []
        situacoes = (
            CandidatoVaga.INAPTO,
            CandidatoVaga.AUSENTE,
            CandidatoVaga.MATRICULA_CANCELADA,
            CandidatoVaga.TRANSFERIDO,
            CandidatoVaga.JA_MATRICULADO,
            CandidatoVaga.EVADIDO,
            CandidatoVaga.JA_CONVOCADO,
        )
        for vaga in self.vaga_set.filter(candidatovaga__isnull=True) | self.vaga_set.filter(candidatovaga__situacao__in=situacoes):
            vagas.append(vaga)
        return vagas

    def get_qtd_vagas_extras(self):
        return sum(self.criacaovagaremanescente_set.values_list('qtd', flat=True))

    def realizar_nova_chamada(self, numero_chamada):
        convocados = []
        if numero_chamada == 1 and not self.vaga_set.exists():
            for i in range(0, self.qtd):
                Vaga.objects.create(oferta_vaga=self)
        for vaga in self.get_vagas_disponiveis():
            convocado = self.convocar_proximo_candidato(vaga, numero_chamada)
            if convocado:
                convocados.append(convocado)
        return convocados


class Vaga(models.ModelPlus):
    oferta_vaga = models.ForeignKeyPlus(OfertaVaga)

    class Meta:
        verbose_name = 'Vaga'
        verbose_name_plural = 'Vagas'

    def __str__(self):
        return self.oferta_vaga.lista.descricao


class Candidato(models.ModelPlus):
    edital = models.ForeignKeyPlus(Edital, verbose_name='Edital')
    inscricao = models.CharField(max_length=255, verbose_name='Nº da Inscrição')
    cpf = models.CharField(max_length=250, verbose_name='CPF')
    nome = models.CharField(max_length=255, verbose_name='Nome')
    email = models.CharField(max_length=255, verbose_name='E-mail', null=True)
    telefone = models.CharField(max_length=255, verbose_name='Telefone', null=True)
    curso_campus = models.ForeignKeyPlus(CursoCampus, verbose_name='Curso', null=True)
    turno = models.ForeignKeyPlus('edu.Turno', verbose_name='Turno', null=True, on_delete=models.CASCADE)
    campus_polo = models.CharFieldPlus(verbose_name='Campus/Polo', default='')

    objects = models.Manager()
    locals = FiltroUnidadeOrganizacionalManager('edital__ofertavaga__curso_campus__diretoria__setor__uo')

    class Meta:
        verbose_name_plural = 'Candidato'
        verbose_name = 'Candidatos'

    def __str__(self):
        return 'Candidato {}'.format(self.inscricao)

    def get_lista_candidato(self):
        return ', '.join('%s' % (candidatovaga.oferta_vaga.lista) for candidatovaga in self.candidatovaga_set.all())

    get_lista_candidato.short_description = 'Lista'

    def get_absolute_url(self):
        return '/processo_seletivo/candidato/%d/' % self.pk


class CandidatoVaga(models.ModelPlus):
    MATRICULADO = '1'
    AUSENTE = '2'
    INAPTO = '3'
    JA_MATRICULADO = '4'
    MATRICULA_CANCELADA = '5'
    EVADIDO = '6'
    JA_CONVOCADO = '7'
    TRANSFERIDO = '8'

    SITUACAO_CHOICES = [
        [MATRICULADO, 'Matriculado'],
        [AUSENTE, 'Ausente'],
        [INAPTO, 'Inapto'],
        [JA_MATRICULADO, 'Já Matriculado'],
        [MATRICULA_CANCELADA, 'Matrícula Cancelada'],
        [EVADIDO, 'Evadido'],
        [JA_CONVOCADO, 'Já Convocado'],
        [TRANSFERIDO, 'Transferido'],
    ]

    candidato = models.ForeignKeyPlus(Candidato, verbose_name='Candidato')
    oferta_vaga = models.ForeignKeyPlus(OfertaVaga, verbose_name='Oferta de Vaga')
    vaga = models.ForeignKeyPlus(Vaga, verbose_name='Vaga', null=True)
    classificacao = models.IntegerField('Classificação')
    aprovado = models.BooleanField('Aprovado', default=False)
    eliminado = models.BooleanField('Eliminado', default=False)

    situacao = models.CharFieldPlus('Situação', choices=SITUACAO_CHOICES, null=True)
    migracao = models.ForeignKeyPlus(OfertaVaga, verbose_name='Migração', null=True, related_name='migracao_set')

    convocacao = models.IntegerField(verbose_name='Chamada da Convocação', null=True)

    objects = models.Manager()
    locals = FiltroUnidadeOrganizacionalManager('oferta_vaga__curso_campus__diretoria__setor__uo')

    class Meta:
        verbose_name_plural = 'Vaga Concorrida'
        verbose_name = 'Vaga Concorrida'
        ordering = ('classificacao',)

    def __str__(self):
        if self.classificacao:
            return '{} - {}º Lugar ({})'.format(self.oferta_vaga.lista, self.classificacao, self.oferta_vaga.oferta_vaga_curso.curso_campus)
        else:
            return '%s - Classificação indefinida' % self.oferta_vaga.lista

    @property
    def campus(self):
        return self.candidato.curso_campus.diretoria.setor.uo

    def is_matriculado(self):
        return Aluno.objects.filter(candidato_vaga__candidato=self.candidato, curso_campus=self.oferta_vaga.oferta_vaga_curso.curso_campus).exists()

    def get_aluno(self):
        return Aluno.objects.filter(candidato_vaga__candidato=self.candidato).first()

    def get_situacao_matricula(self):
        qs_aluno = Aluno.objects.filter(candidato_vaga=self)
        return qs_aluno.exists() and qs_aluno[0].situacao or ''

    def utilizou_vaga_migrada(self):
        return self.vaga_id and self.vaga.oferta_vaga != self.oferta_vaga

    def get_participacoes_em_outras_listas(self):
        return CandidatoVaga.objects.filter(candidato=self.candidato, oferta_vaga__oferta_vaga_curso=self.oferta_vaga.oferta_vaga_curso).exclude(pk=self.pk)

    def get_status(self):
        status = {'1': 'success', '2': 'alert', '3': 'error', '4': 'info', '5': 'fechado', '6': 'fechado', '7': 'info', None: 'info'}
        descricao = self.get_situacao_display()
        data_matricula = ''
        if self.situacao in (CandidatoVaga.JA_CONVOCADO, CandidatoVaga.JA_MATRICULADO):
            candidato_vaga = self.get_participacoes_em_outras_listas().exclude(situacao=self.situacao).first()
            if candidato_vaga:
                descricao = '{} - {}'.format(descricao, candidato_vaga.oferta_vaga.lista)
        if self.situacao == CandidatoVaga.MATRICULADO:
            data_matricula = Aluno.objects.filter(candidato_vaga__candidato=self.candidato).values_list('data_matricula', flat=True).first()
            data_matricula = data_matricula and data_matricula.strftime('%d/%m/%Y as %H:%M') or ''
        return descricao, status[self.situacao], data_matricula

    def registrar_matricula(self):
        self.situacao = CandidatoVaga.MATRICULADO
        self.save()
        self.get_participacoes_em_outras_listas().update(situacao=CandidatoVaga.JA_MATRICULADO)
        matricula_candidato_sinal.send(sender=CandidatoVaga, candidato_vaga_id=self.pk)

    def registrar_ausencia(self):
        self.situacao = CandidatoVaga.AUSENTE
        self.save()
        self.get_participacoes_em_outras_listas().update(situacao=CandidatoVaga.AUSENTE)
        ausencia_candidato_sinal.send(sender=CandidatoVaga, candidato_vaga_id=self.pk, desfazer=False)

    def registrar_inaptidao(self):
        self.situacao = CandidatoVaga.INAPTO
        self.save()
        self.get_participacoes_em_outras_listas().update(situacao=CandidatoVaga.INAPTO)
        inaptidao_candidato_sinal.send(sender=CandidatoVaga, candidato_vaga_id=self.pk, desfazer=False)

    # Todo: Verificar com Agugusto - Método criado para permitir retornar as solicitações indeferidas do catalogo digital para o status EM_ANALISE
    def retornar_para_apto(self):
        if self.situacao == CandidatoVaga.MATRICULADO:
            matricula_candidato_sinal.send(sender=CandidatoVaga, candidato_vaga_id=self.pk, desfazer=True)
        if self.situacao == CandidatoVaga.AUSENTE:
            ausencia_candidato_sinal.send(sender=CandidatoVaga, candidato_vaga_id=self.pk, desfazer=True)
        if self.situacao == CandidatoVaga.INAPTO:
            inaptidao_candidato_sinal.send(sender=CandidatoVaga, candidato_vaga_id=self.pk, desfazer=True)
        self.situacao = None
        self.save()
        self.get_participacoes_em_outras_listas().update(situacao=None)

    def simular_matricula(self):
        aluno = Aluno.objects.filter(candidato_vaga__isnull=True, situacao_id=1)[0]
        aluno.candidato_vaga = self
        aluno.save()
        self.situacao = CandidatoVaga.MATRICULADO
        self.save()
        self.get_participacoes_em_outras_listas().update(situacao=CandidatoVaga.JA_MATRICULADO)

    def desfazer_procedimento(self):
        if self.vaga is None and self.convocacao == self.oferta_vaga.oferta_vaga_curso.get_numero_ultima_chamada():
            vagas = self.oferta_vaga.get_vagas_disponiveis()
            self.vaga = vagas and vagas[0] or None
        for aluno in Aluno.objects.filter(candidato_vaga=self):
            if aluno.pode_ser_excluido():
                aluno.delete()
        for candidato_vaga in self.get_participacoes_em_outras_listas():
            candidato_vaga.situacao = None
            if candidato_vaga.convocacao and candidato_vaga.oferta_vaga.candidatovaga_set.filter(convocacao__gt=candidato_vaga.convocacao).exists():
                candidato_vaga.convocacao = None
            for aluno in Aluno.objects.filter(candidato_vaga=candidato_vaga):
                if aluno.pode_ser_excluido():
                    aluno.delete()
            candidato_vaga.save()
        self.retornar_para_apto()

    def get_lista_matriculada(self):
        if self.situacao == CandidatoVaga.MATRICULADO:
            if self.migracao:
                return self.migracao.lista
            else:
                return self.oferta_vaga.lista
        elif self.situacao == CandidatoVaga.JA_MATRICULADO:
            return CandidatoVaga.objects.get(
                candidato=self.candidato, oferta_vaga__curso_campus=self.oferta_vaga.curso_campus, situacao=CandidatoVaga.MATRICULADO
            ).oferta_vaga.lista
        return None

    def get_outra_convocacao(self):
        qs = CandidatoVaga.objects.filter(candidato=self.candidato, oferta_vaga__curso_campus=self.oferta_vaga.curso_campus)
        if self.oferta_vaga.turno:
            qs = qs.filter(oferta_vaga__turno=self.oferta_vaga.turno)
        qs = qs.filter(convocacao__isnull=False).exclude(pk=self.pk)
        return qs.exists() and qs.first() or None

    def get_convocacao_em_lista_menos_restritiva(self):
        if self.oferta_vaga.edital.configuracao_migracao_vagas:
            rotulos_lista = []
            for i in range(1, 16):
                rotulo_lista = getattr(self.oferta_vaga.edital.configuracao_migracao_vagas, 'lista_{}'.format(i))
                if rotulo_lista:
                    if rotulo_lista.nome == self.oferta_vaga.lista.descricao:
                        break
                    else:
                        rotulos_lista.append(rotulo_lista)
                else:
                    break
            for rotulo_lista in rotulos_lista:
                qs_oferta_vaga = OfertaVaga.objects.filter(
                    edital=self.oferta_vaga.edital, curso_campus=self.oferta_vaga.curso_campus, turno=self.oferta_vaga.turno, lista__descricao=rotulo_lista.nome
                )
                if qs_oferta_vaga.exists():
                    oferta_vaga = qs_oferta_vaga[0]
                    for tmp in oferta_vaga.get_candidatos_atualmente_convocados():
                        if tmp.candidato == self.candidato:
                            return tmp
        return None

    @classmethod
    def matricula_online_disponibilidade(cls, cpf, campus=None, niveis_ensino=None):
        now = datetime.datetime.now()
        ret_value = list()

        # Tratamento para editais em período de matrícula --------------------------------------------------------------
        periodos_liberacao = EditalPeriodoLiberacao.objects.filter(
            data_inicio_matricula__lte=now,
            data_fim_matricula__gte=now
        )

        if campus is not None:
            periodos_liberacao = periodos_liberacao.filter(uo=campus)

        for periodo_liberacao in periodos_liberacao:
            # Avaliar consulta com e sem exclude
            candidaturas_periodo_matricula = CandidatoVaga.objects.filter(candidato__edital=periodo_liberacao.edital)
            candidaturas_periodo_matricula = candidaturas_periodo_matricula.filter(candidato__cpf=cpf, convocacao__isnull=False, situacao__isnull=True)

            if niveis_ensino is not None:
                candidaturas_periodo_matricula = candidaturas_periodo_matricula.filter(candidato__curso_campus__modalidade__nivel_ensino_id__in=niveis_ensino)

            for cand in candidaturas_periodo_matricula:
                if not cand.is_matriculado() and cand.campus == periodo_liberacao.uo:
                    ret_value.append({
                        'edital_codigo': cand.candidato.edital.codigo,
                        'edital_id': cand.candidato.edital.id,
                        'candidato_vaga_id': cand.pk,
                        'edital_descricao': cand.candidato.edital.descricao,
                        'modalidade_id': cand.candidato.curso_campus.modalidade.pk,
                        'em_periodo_matricula': True
                    })

        # Tratamento para editais fora de período, mas, em período de correção  ----------------------------------------
        periodos_liberacao = EditalPeriodoLiberacao.objects.filter(
            data_fim_matricula__lt=now,
            data_limite_avaliacao__gte=now
        )

        if campus is not None:
            periodos_liberacao = periodos_liberacao.filter(uo=campus)

        for periodo_liberacao in periodos_liberacao:
            # Avaliar consulta com e sem exclude
            candidaturas_periodo_avaliacao = CandidatoVaga.objects.filter(candidato__edital=periodo_liberacao.edital)
            candidaturas_periodo_avaliacao = candidaturas_periodo_avaliacao.filter(candidato__cpf=cpf, convocacao__isnull=False, situacao__isnull=True)

            if niveis_ensino is not None:
                candidaturas_periodo_avaliacao = candidaturas_periodo_avaliacao.filter(candidato__curso_campus__modalidade__nivel_ensino_id__in=niveis_ensino)

            for cand in candidaturas_periodo_avaliacao:
                if not cand.is_matriculado() and cand.campus == periodo_liberacao.uo:
                    ret_value.append({
                        'edital_codigo': cand.candidato.edital.codigo,
                        'edital_id': cand.candidato.edital.id,
                        'candidato_vaga_id': cand.pk,
                        'edital_descricao': cand.candidato.edital.descricao,
                        'modalidade_id': cand.candidato.curso_campus.modalidade.pk,
                        'em_periodo_matricula': False
                    })

        return ret_value

    @classmethod
    def matricula_online_dados_candidato(cls, candidato_vaga_id):
        # Fechar no SGC V2 para testes
        candidato_vaga = CandidatoVaga.objects.get(pk=candidato_vaga_id)
        ws = candidato_vaga.candidato.edital.webservice

        ret_values = ws.candidato(codigo_edital=candidato_vaga.candidato.edital.codigo, codigo_candidato=candidato_vaga.candidato.inscricao)

        soap = BeautifulSoup(ret_values, 'xml')
        # Adicionando dados das listas
        lista = soap.new_tag('lista')
        lista_codigo = soap.new_tag('codigo')
        lista_codigo.append(f'{candidato_vaga.oferta_vaga.lista.codigo}')
        lista_nome = soap.new_tag('nome')
        lista_nome.append(f'{candidato_vaga.oferta_vaga.lista.descricao}')
        # Configuração das listas
        lista_etinia = soap.new_tag('criterio_etnico')
        lista_pessoa_deficiencia = soap.new_tag('criterio_deficiencia')
        lista_escola_publica = soap.new_tag('criterio_escola_publica')
        lista_social = soap.new_tag('criterio_social')
        lista_outros = soap.new_tag('criterio_outros')

        if candidato_vaga.oferta_vaga.lista.forma_ingresso:
            lista_etinia.append(f'{candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_etinico}')
            lista_pessoa_deficiencia.append(f'{candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_pessoa_deficiencia}')
            lista_escola_publica.append(f'{candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_escola_publica}')
            lista_social.append(f'{candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_social}')
            lista_outros.append(f'{candidato_vaga.oferta_vaga.lista.forma_ingresso.programa_vaga_outros}')

        lista.append(lista_codigo)
        lista.append(lista_nome)
        lista.append(lista_etinia)
        lista.append(lista_pessoa_deficiencia)
        lista.append(lista_escola_publica)
        lista.append(lista_social)
        lista.append(lista_outros)

        soap.find('inscricao').append(lista)

        return str(soap.contents[0])

    def is_inconsistente(self):
        result = False
        if CandidatoVaga.objects.filter(
            id=self.id, convocacao__isnull=False, vaga__isnull=True, eliminado=False, situacao__isnull=True, oferta_vaga_id=self.oferta_vaga.id
        ).exists():
            result = len(self.oferta_vaga.get_vagas_disponiveis()) > 0
        return result

    def vincular_vaga(self):
        if self.is_inconsistente():
            vaga = self.oferta_vaga.get_vagas_disponiveis()[0]
            self.vaga = vaga
            self.save()


class WebService(LogModel):
    descricao = models.CharFieldPlus('Descrição')
    url_editais = models.CharFieldPlus('Url Editais', help_text='Endereço do webservice para listagem de editais.Ex: http://ingresso.ifrn.edu.br/ws/editais/')
    url_edital = models.CharFieldPlus('Url Edital', help_text='Endereço do webservice para importação de edital. Ex: http://ingresso.ifrn.edu.br/ws/edital/%s/')
    url_candidato = models.CharFieldPlus('Url Candidato', help_text='Endereço do webservice para importação de candidato. Ex: http://ingresso.ifrn.edu.br/ws/candidato/%s/')
    url_caracterizacoes = models.CharFieldPlus(
        'Url Caracterizações',
        help_text='Endereço do webservice para importação de todas as caracterizações socio-econômicas dos candidatos. Ex: http://ingresso.ifrn.edu.br/ws/caracterizacoes/%s/',
        null=True,
    )

    token = models.CharFieldPlus('Token de Autorização', help_text='Token passado no cabeçalho da requisição (Authorization: XXXXX)', null=True, blank=True)
    is_zipped = models.BooleanField('É compactado', default=False)

    class Meta:
        verbose_name = 'Web Service'
        verbose_name_plural = 'Web Services'

    def _executar(self, url, zipped=True):
        headers = {'Authorization': 'Token {}'.format(self.token or '')}
        response = requests.get(url, headers=headers)
        if self.is_zipped and zipped:
            return zlib.decompress(response.content).decode('utf-8')
        else:
            if response.encoding == 'ISO-8859-1':
                return response.text.encode('ISO-8859-1').decode('utf-8')
            else:
                return response.text

    def editais(self):
        if self.url_editais.startswith('file://'):
            with open(join(settings.BASE_DIR, self.url_editais.replace('file://', ''))) as f:
                content = f.read()
            return content
        else:
            return self._executar(self.url_editais, False)

    def edital(self, codigo_edital):
        if self.url_edital.startswith('file://'):
            with open(join(settings.BASE_DIR, self.url_edital.replace('file://', ''))) as f:
                content = f.read()
            return content
        else:
            url = self.url_edital.format(codigo_edital)
            return self._executar(url)

    def candidato(self, codigo_edital, codigo_candidato, compactado=False):
        if self.url_candidato.startswith('file://'):
            with open(join(settings.BASE_DIR, self.url_candidato.replace('file://', ''))) as f:
                content = f.read()
            return content
        else:
            url = self.url_candidato.format(codigo_edital, codigo_candidato)
            return self._executar(url)

    def caracterizacoes(self, codigo_edital):
        if self.url_edital.startswith('file://'):
            with open(join(settings.BASE_DIR, self.url_caracterizacoes.replace('file://', ''))) as f:
                content = f.read()
            return content
        else:
            url = self.url_caracterizacoes.format(codigo_edital)
            return self._executar(url, zipped=True)


class TipoEditalAdesao(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', max_length=255, unique=True, blank=False, null=False)

    class Meta:
        verbose_name = 'Tipo do Edital de Adesão'
        verbose_name_plural = 'Tipos de Edital de Adesão'

    def __str__(self):
        return "%s" % self.nome


class EditalAdesao(models.ModelPlus):
    nome = models.CharField('Nome', max_length=255)
    descricao = models.TextField('Descrição', blank=True)
    tipo = models.ForeignKeyPlus(TipoEditalAdesao)
    ano_edital = models.PositiveIntegerField('Ano do Edital', help_text='Ano do Edital', null=True)
    numero_edital = models.PositiveIntegerField('Número do Edital', help_text='Numeração do Edital', null=True)

    data_inicio_adesao = models.DateTimeFieldPlus('Data de início da adesão', null=False, blank=False)
    data_limite_adesao = models.DateTimeFieldPlus('Data limite para adesão', help_text='Data limite para adesão ao edital pelos campi', null=False, blank=False)
    criado_por = models.ForeignKeyPlus('comum.User', related_name='edital_adesao_criado_por', null=False, blank=False, editable=False, on_delete=models.CASCADE)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Edital de Adesão"
        verbose_name_plural = "Editais de Adesão"
        unique_together = ('nome', 'numero_edital', 'ano_edital')

    def __str__(self):
        return "{} {}/{}".format(self.nome, self.numero_edital, self.ano_edital)


class EditalAdesaoCampus(models.ModelPlus):
    nome = models.CharField('Nome', max_length=255)
    edital_regulador = models.ForeignKeyPlus(EditalAdesao)
    numero_edital = models.PositiveIntegerField('Número do Edital', help_text='Numeração do Edital do campus', null=True)
    ano_edital = models.PositiveIntegerField('Ano do Edital', help_text='Ano do Edital do campus', null=True)
    data_inicio_inscricoes = models.DateTimeFieldPlus('Data da inscrição', null=False, blank=False)
    data_encerramento_inscricoes = models.DateTimeFieldPlus('Data de encerramento', help_text='Data limite para encerramento das inscrições', null=False, blank=False)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, related_name='edital_adesao_campus_campus', null=False, blank=False)
    responsavel = models.ForeignKeyPlus('comum.User', related_name='edital_adesao_campus_responsavel_por', null=False, blank=False, editable=False, on_delete=models.CASCADE)
    idade_minima = models.BooleanField(default=False)
    data_aplicacao_prova = models.DateTimeFieldPlus(null=True, blank=True)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('edital_regulador', 'campus')
        verbose_name = "Edital de Adesão Campus"
        verbose_name_plural = "Editais de Adesão Campus"
        permissions = (("pode_ver_todos_editais", "Pode ver todos os editais de adesão"), ("pode_ver_edital_campus", "pode ver edital os editais de adesão do campus"))

    def __str__(self):
        return "{} {}/{}-{}".format(self.nome, self.numero_edital, self.ano_edital, self.campus)

    @classmethod
    def editais_abertos(cls, user):
        now = datetime.datetime.now()
        return EditalAdesaoCampus.objects.filter(data_inicio_inscricoes__lte=now, data_encerramento_inscricoes__gte=now, campus=get_uo(user))


class InscricaoFiscal(models.ModelPlus):
    TIPO_ALUNO = 'ALUNO'
    TIPO_SERVIDOR = 'SERVIDOR'
    TIPO_CHOICES = [[TIPO_ALUNO, 'Aluno'], [TIPO_SERVIDOR, 'Servidor']]

    TIPO_CONTA_CORRENTE = 'CORRENTE'
    TIPO_CONTA_POUPANCA = 'POUPANCA'
    TIPO_CONTA_CHOICES = [[TIPO_CONTA_CORRENTE, 'Conta Corrente'], [TIPO_CONTA_POUPANCA, 'Conta Poupança']]

    edital = models.ForeignKeyPlus(EditalAdesaoCampus)
    pessoa_fisica = models.ForeignKeyPlus(PessoaFisica, related_name='processo_seletivo_inscricaofiscal_set', verbose_name="Fiscal", on_delete=models.CASCADE)
    tipo = models.CharField(verbose_name="Vínculo", max_length=50, choices=TIPO_CHOICES)
    matricula = models.CharField('Matrícula', max_length=50)
    telefones = models.CharField(max_length=255)
    banco = models.CharField(max_length=50, null=True)
    numero_agencia = models.CharField('Número da Agência', max_length=50, null=True)
    tipo_conta = models.CharField(max_length=50, verbose_name='Tipo da Conta', choices=TIPO_CONTA_CHOICES, null=True)
    numero_conta = models.CharField('Número da Conta', max_length=50, null=True)
    operacao = models.CharField('Operação', max_length=50, null=True, blank=True)
    pis_pasep = models.CharField('PIS/PASEP', max_length=20, null=True, blank=True)
    outros_processos = models.IntegerField("Já Participou de outros processos? Quantos?", help_text="Ex.: 0", default=0)
    aceito_termos = models.BooleanField(
        verbose_name='Termo de Compromisso',
        help_text='Declaro junto à Comissão do Concurso Público o meu interesse ' 'em trabalhar como fiscal, bem como a veracidade dos dados acima.',
        default=False,
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inscrição para Fiscal'
        verbose_name_plural = 'Inscrições para Fiscal'

    def set_user(self, user):
        pessoa_fisica = user.get_profile()
        servidor = Servidor.objects.efetivos().filter(pk=pessoa_fisica.pk, excluido=False).first()
        if servidor:
            self.tipo = self.TIPO_SERVIDOR
            self.matricula = servidor.matricula
            self.pessoa_fisica = servidor
            return True
        else:
            aluno = Aluno.objects.filter(pessoa_fisica__pk=pessoa_fisica.pk, situacao__ativo=True).first()
            if aluno:
                self.tipo = self.TIPO_ALUNO
                self.matricula = aluno.matricula
                self.pessoa_fisica = aluno.pessoa_fisica
                return True
        return False

    def idade_no_dia_prova(self):
        if self.edital.idade_minima and self.edital.data_aplicacao_prova:
            return years_between(self.pessoa_fisica.nascimento_data, self.edital.data_aplicacao_prova)
        return "-"

    @classmethod
    def calcular_idade(cls, user, edital):
        pessoa_fisica = user.get_profile()
        nasc = pessoa_fisica.nascimento_data
        return years_between(nasc, edital.data_aplicacao_prova)

    @classmethod
    def pode_efetuar_inscricao(cls, user, edital):

        if datetime.datetime.now() > edital.data_encerramento_inscricoes:
            return False, "o prazo de inscrições para o edital corrente expirou."

        pessoa_fisica = user.get_profile()

        if InscricaoFiscal.objects.filter(pessoa_fisica__cpf=pessoa_fisica.cpf, edital=edital).exists():
            return False, "o CPF {} já possui uma inscrição.".format(pessoa_fisica.cpf)

        if edital.campus != get_uo(user):
            return False, "o edital não permite inscrições vínculadas ao seu campus."

        matricula_valida = (
            Servidor.objects.efetivos().filter(pk=pessoa_fisica.pk, excluido=False).exists() or Aluno.objects.filter(pessoa_fisica__pk=pessoa_fisica.pk, situacao__ativo=True).exists()
        )
        if not matricula_valida:
            return matricula_valida, "matrícula inválida."

        if edital.idade_minima and edital.data_aplicacao_prova:
            idade_minima = InscricaoFiscal.calcular_idade(user, edital) >= 18
            if not idade_minima:
                return False, "não você preenche o requisito de idade mínima previsto no edital."

        return True, "Inscrição realizada com sucesso."


class RotuloLista(models.ModelPlus):
    SEARCH_FIELDS = ['nome', 'descricao']
    nome = models.TextField(verbose_name='Nome')
    descricao = models.TextField(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Rótulo de Lista'
        verbose_name_plural = 'Rótulos de Lista'

    def __str__(self):
        return self.nome


class ConfiguracaoMigracaoVaga(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    is_sisu = models.BooleanField(default=False, verbose_name='SISU?')
    listas = models.ManyToManyFieldPlus(RotuloLista, verbose_name='Listas')
    ativo = models.BooleanField(default=True)

    lista_1 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 1', null=True, blank=True, related_name='p1')
    lista_2 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 2', null=True, blank=True, related_name='p2')
    lista_3 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 3', null=True, blank=True, related_name='p3')
    lista_4 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 4', null=True, blank=True, related_name='p4')
    lista_5 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 5', null=True, blank=True, related_name='p5')
    lista_6 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 6', null=True, blank=True, related_name='p6')
    lista_7 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 7', null=True, blank=True, related_name='p7')
    lista_8 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 8', null=True, blank=True, related_name='p8')
    lista_9 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 9', null=True, blank=True, related_name='p9')
    lista_10 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 10', null=True, blank=True, related_name='p10')
    lista_11 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 11', null=True, blank=True, related_name='p11')
    lista_12 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 12', null=True, blank=True, related_name='p12')
    lista_13 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 13', null=True, blank=True, related_name='p13')
    lista_14 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 14', null=True, blank=True, related_name='p14')
    lista_15 = models.ForeignKeyPlus(RotuloLista, verbose_name='Prioridade 15', null=True, blank=True, related_name='p15')

    class Meta:
        verbose_name = 'Configuração de Migração de Vaga'
        verbose_name_plural = 'Configurações de Migração de Vagas'

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/processo_seletivo/configuracaomigracaovaga/{}/'.format(self.pk)

    def get_nomes_listas_ordenadas_por_restricao(self):
        nomes = []
        for i in range(1, 16):
            rotulo_lista = getattr(self, 'lista_{}'.format(i))
            if rotulo_lista:
                nomes.append(rotulo_lista.nome)
        return nomes

    def get_precedencias(self, apenas_descricao=False):
        precedencias = []
        qs = PrecedenciaMigracao.objects.filter(configuracao=self)
        for nome_lista in self.get_nomes_listas_ordenadas_por_restricao():
            origem = self.listas.filter(nome=nome_lista).first()
            destinos = []
            if origem:
                for rotulo_pk in qs.filter(origem=origem).values_list('destino', flat=True).order_by('precedencia'):
                    rotulo_lista = RotuloLista.objects.get(pk=rotulo_pk)
                    destinos.append(apenas_descricao and rotulo_lista.nome or rotulo_lista)
                precedencias.append((apenas_descricao and nome_lista or origem, destinos))
        return precedencias


class PrecedenciaMigracao(models.ModelPlus):
    configuracao = models.ForeignKeyPlus(ConfiguracaoMigracaoVaga, verbose_name='Configuração', on_delete=models.CASCADE)
    origem = models.ForeignKeyPlus(RotuloLista, verbose_name='Lista de Origem')
    destino = models.ForeignKeyPlus(RotuloLista, verbose_name='Lista de Destino', related_name='precedenciamigracao_set2')
    precedencia = models.IntegerField(verbose_name='Precedência')

    class Meta:
        verbose_name = 'Precedência'
        verbose_name_plural = 'Precedências'

    def __str__(self):
        return '{} - {} - {}'.format(self.origem, self.destino, self.precedencia)


class CriacaoVagaRemanescente(models.ModelPlus):
    oferta_vaga = models.ForeignKeyPlus(OfertaVaga, verbose_name='Oferta de Vaga')
    qtd = models.IntegerField(verbose_name='Quantidade')
    responsavel = models.CurrentUserField(verbose_name='Responsável')
    data = models.DateTimeFieldPlus(verbose_name='Data', auto_now=True)
    justificativa = models.TextField(verbose_name='Justificativa')

    class Meta:
        verbose_name = 'Criação de Vaga Remanescente'
        verbose_name_plural = 'Criações de Vaga Remanescente'

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        pk = self.pk
        super().save(*args, **kwargs)
        if pk is None:
            numero_chamada = self.oferta_vaga.oferta_vaga_curso.get_numero_ultima_chamada()
            for i in range(0, self.qtd):
                vaga = Vaga.objects.create(oferta_vaga=self.oferta_vaga)
                self.oferta_vaga.convocar_proximo_candidato(vaga, numero_chamada)
