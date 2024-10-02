# -*- coding: utf-8 -*-

from django.conf import settings
from django.db import models
from django.db.models import Subquery

from comum.utils import tl, get_sigla_reitoria


class FiltroUnidadeOrganizacionalQuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        self.key = kwargs.pop('key', None)
        super(FiltroUnidadeOrganizacionalQuerySet, self).__init__(*args, **kwargs)

    def get_filtered_queryset(self):
        eh_setor_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        if not self.key:
            if eh_setor_suap:
                self = self.filter(setor__codigo__isnull=True)
            else:
                self = self.filter()
        ids = self.get_ids()
        if ids:
            if self.key:
                filtro = {'{}__id__in'.format(self.key): ids}
            else:
                filtro = {'id__in': ids}
            self = self.filter(**filtro)
        return self

    def get_ids(self):
        from comum.models import UsuarioGrupoSetor
        from rh.models import UnidadeOrganizacional

        user = tl.get_user()
        ids = []
        if user and user.groups.filter(name='etep Administrador').exists():
            return ids
        elif user and user.pk:
            groups = ['Membro ETEP', 'Interessado ETEP']
            ids = UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=groups).values_list('setor__uo', flat=True)

        qs = UnidadeOrganizacional.objects.suap().filter(sigla=get_sigla_reitoria())
        if qs.exists() and qs[0].pk in ids:
            return []
        return ids


class SolicitacaoAcompanhamentoQueryset(FiltroUnidadeOrganizacionalQuerySet):
    def em_acompanhamento(self):
        from etep.models import Acompanhamento

        return self.filter(acompanhamento__situacao__in=[Acompanhamento.EM_ACOMPANHAMENTO, Acompanhamento.ACOMPANHAMENTO_PRIORITARIO]).order_by('-id')

    def finalizados(self):
        from etep.models import Acompanhamento

        return self.filter(acompanhamento__situacao=Acompanhamento.ACOMPANHAMENTO_FINALIZADO).order_by('-id')

    def pendentes(self):
        return self.exclude(avaliador__id__isnull=False)

    def interessados(self):
        user = tl.get_user()
        return self.em_acompanhamento().filter(acompanhamento__interessado__vinculo__user=user, acompanhamento__interessado__ativado=True).exclude(solicitante=user)


class SolicitacaoAcompanhamentoManager(models.Manager):
    def get_queryset(self):
        from etep.models import Interessado, SolicitacaoAcompanhamento

        user = tl.get_user()
        lista_interessados = Interessado.objects.filter(vinculo__user=user, ativado=True).values('pk')
        qs = SolicitacaoAcompanhamentoQueryset(self.model, key='aluno__curso_campus__diretoria__setor__uo', using=self._db).get_filtered_queryset()
        if user and not user.groups.filter(name__in=['etep Administrador', 'Membro ETEP']).exists() and not user.is_superuser:
            qs = qs.filter(acompanhamento__interessado__in=Subquery(lista_interessados)) | SolicitacaoAcompanhamento.objects.filter(solicitante=user)
            qs = qs.distinct()
        return qs

    def em_acompanhamento(self):
        return self.get_queryset().em_acompanhamento()

    def finalizados(self):
        return self.get_queryset().finalizados()

    def pendentes(self):
        return self.get_queryset().pendentes()

    def interessados(self):
        return self.get_queryset().interessados()


class AcompanhamentoQueryset(FiltroUnidadeOrganizacionalQuerySet):
    def em_acompanhamento(self):
        from etep.models import Acompanhamento

        return self.filter(situacao=Acompanhamento.EM_ACOMPANHAMENTO)

    def prioritarios(self):
        from etep.models import Acompanhamento

        return self.filter(situacao=Acompanhamento.ACOMPANHAMENTO_PRIORITARIO)

    def finalizados(self):
        from etep.models import Acompanhamento

        return self.filter(situacao=Acompanhamento.ACOMPANHAMENTO_FINALIZADO)

    def nao_finalizados(self):
        from etep.models import Acompanhamento

        return self.exclude(situacao=Acompanhamento.ACOMPANHAMENTO_FINALIZADO)


class AcompanhamentoManager(models.Manager):
    def get_queryset(self):
        from etep.models import Interessado

        user = tl.get_user()
        qs = AcompanhamentoQueryset(self.model, key='aluno__curso_campus__diretoria__setor__uo', using=self._db).get_filtered_queryset()
        if user.is_anonymous:
            return qs.none()
        if user and not user.groups.filter(name__in=['etep Administrador', 'Membro ETEP']).exists() and not user.is_superuser:
            interessados = Interessado.locals.ativos().filter(vinculo__user__id=user.id)
            qs = qs.filter(interessado__in=interessados.values('pk'))
        return qs

    def em_acompanhamento(self):
        return self.get_queryset().em_acompanhamento()

    def prioritarios(self):
        return self.get_queryset().prioritarios()

    def finalizados(self):
        return self.get_queryset().finalizados()

    def nao_finalizados(self):
        return self.get_queryset().nao_finalizados()


class RegistroAcompanhamentoQueryset(FiltroUnidadeOrganizacionalQuerySet):
    def ciencia_pendente(self, user):
        return self.filter(registroacompanhamentointeressado__interessado__vinculo__user=user, registroacompanhamentointeressado__data_ciencia__isnull=True).distinct()


class RegistroAcompanhamentoManager(models.Manager):
    def get_queryset(self):
        from etep.models import Interessado

        user = tl.get_user()
        qs = RegistroAcompanhamentoQueryset(self.model, key='acompanhamento__aluno__curso_campus__diretoria__setor__uo', using=self._db).get_filtered_queryset()
        if user and user.is_anonymous:
            return qs.none()
        if user and not user.groups.filter(name__in=['etep Administrador', 'Membro ETEP']).exists() and not user.is_superuser:
            interessados = Interessado.locals.ativos().filter(vinculo__user__id=user.id)
            qs_interessados = qs.filter(registroacompanhamentointeressado__interessado__in=interessados)
            qs = qs_interessados | qs.filter(usuario=user) | qs.filter(situacao__isnull=False)
            qs = qs.distinct()
        return qs

    def ciencia_pendente(self, user):
        return self.get_queryset().ciencia_pendente(user)


class InteressadoQueryset(models.QuerySet):
    def ativos(self):
        return self.filter(ativado=True)


class InteressadoManager(models.Manager):
    def get_queryset(self):
        return InteressadoQueryset(self.model, using=self._db)

    def ativos(self):
        return self.get_queryset().ativos()


class AtividadeManager(models.Manager):
    def get_queryset(self):
        from etep.models import Atividade

        user = tl.get_user()
        qs = FiltroUnidadeOrganizacionalQuerySet(model=self.model, key='usuario__pessoafisica__funcionario__setor__uo', using=self._db).get_filtered_queryset()
        if user and not user.groups.filter(name__in=['etep Administrador']).exists() and not user.is_superuser:
            qs = qs | Atividade.objects.filter(visibilidade=True)
            qs = qs.distinct()
        return qs


class DocumentoManager(models.Manager):
    def get_queryset(self):
        from etep.models import Documento

        user = tl.get_user()
        qs = FiltroUnidadeOrganizacionalQuerySet(model=self.model, key='atividade__usuario__pessoafisica__funcionario__setor__uo', using=self._db).get_filtered_queryset()
        if user and not user.groups.filter(name__in=['etep Administrador']).exists() and not user.is_superuser:
            qs = qs | Documento.objects.filter(atividade__visibilidade=True)
            qs = qs.distinct()
        return qs
