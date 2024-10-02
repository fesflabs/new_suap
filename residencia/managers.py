from django.db import models


class CursoResidencasQuery(models.QuerySet):
    def sem_coordenadores(self):
        return self.filter(coordenador__isnull=True, ativo=True)

    def com_coordenadores(self):
        return self.filter(coordenador__isnull=False)

    def sob_coordenacao_de(self, funcionario):
        return self.filter(coordenador=funcionario)




class CursoResidenciaManager(models.Manager):
    def get_queryset(self):
        return CursoResidencasQuery(self.model, using=self._db)

    def sem_coordenadores(self):
        return self.get_queryset().sem_coordenadores()

    def com_coordenadores(self):
        return self.get_queryset().com_coordenadores()

    def sob_coordenacao_de(self, funcionario):
        return self.get_queryset().sob_coordenacao_de(funcionario)


class MatrizQuery(models.QuerySet):
    def vazias(self):
        return self.exclude(componentecurricular__id__isnull=False)

    def incompletas(self):
        return self.filter(inconsistente=True)


class MatrizManager(models.Manager):
    def get_queryset(self):
        return MatrizQuery(self.model, using=self._db)

    def vazias(self):
        return self.get_queryset().vazias()

class SolicitacaoUsuarioManager(models.Manager):
       def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)


class SolicitacaoDesligamentosManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)

class SolicitacaoFeriasManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)

class SolicitacaoLicencasManager(models.Manager):
    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)