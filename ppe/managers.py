from django.db import models

class SetorManager(models.Manager):
    def suap(self):
        return self.get_queryset().suap()

    def suap_ativos(self):
        return self.get_queryset().suap_ativos()

    def get_queryset(self):
        return SetorQuery(self.model, using=self._db)
class SetoresSuapAtivosManager(SetorManager):
    def get_queryset(self):
        return SetorQuery(self.model, using=self._db).suap_ativos()


class SetoresSuapManager(SetorManager):
    def get_queryset(self):
        return SetorQuery(self.model, using=self._db).suap()


class CursoObjectsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().distinct()


class FormacaoPPEQuery(models.QuerySet):
    def vazias(self):
        return self.exclude(cursoformacaoppe__isnull=False)

    def incompletas(self):
        return self.filter(inconsistente=True)


class FormacaoPPEManager(models.Manager):
    def get_queryset(self):
        return FormacaoPPEQuery(self.model, using=self._db)

    def vazias(self):
        return self.get_queryset().vazias()

    def incompletas(self):
        return self.get_queryset().incompletas()


class TurmaQuery(models.QuerySet):

    def em_andamento(self):
        # from edu.models import Diario
        #
        # return self.filter(diario__in=Diario.locals.em_andamento()).order_by('id').distinct()
        return self.all()


class TurmaPPEManager(models.Manager):
    def get_queryset(self):
        return TurmaQuery(self.model, using=self._db)

    def em_andamento(self):
        return self.get_queryset().em_andamento()


class AtendimentoPsicossocialManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)

class ContinuidadeAperfeicoamentoProfissionalManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)

class AmpliacaoPrazoCursoManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)

class RealocacaoManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)

class VisitaTecnicaUnidadeManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)