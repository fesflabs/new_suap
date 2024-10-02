from django.apps import apps
from django.db import models
from django.conf import settings


class UnidadeOrganizacionalQuery(models.QuerySet):

    '''
        Exibe todas unidades organizacionais com código(SIAPE) e que estejam ativas
    '''

    def siape(self):
        eh_setor_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        return self.filter(setor__codigo__isnull=False, setor__excluido=False) if eh_setor_suap else self.filter(setor__excluido=False)

    '''
        Quando a configuração de setores for SUAP:
        - Exibe as unidades organizacionais que não tem código vinculado e estão ativas
        Quando a configuração doas setores for SIAPE:
        - Exibe todas unidades organizacionais ativas
    '''

    def suap(self):
        eh_setor_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        return self.filter(setor__codigo__isnull=True, setor__excluido=False) if eh_setor_suap else self.filter(setor__excluido=False)

    '''
        Exibe as Unidades Organizacionais ativas dos tipos EAD, Campus Produtivo e Campus não produtivos, ou seja, exclui
        Conselhos/Comissões e Reitoria
    '''

    def campi(self):
        UnidadeOrganizacional = apps.get_model('rh', 'unidadeorganizacional')
        return self.suap().filter(tipo__in=[UnidadeOrganizacional.TIPO_CAMPUS_EAD, UnidadeOrganizacional.TIPO_CAMPUS_NAO_PRODUTIVO, UnidadeOrganizacional.TIPO_CAMPUS_PRODUTIVO])

    '''
        Exibe as Unidades Organizacionais ativas dos tipos EAD, Campus Produtivo, Campus não produtivos e Reitoria, ou
        seja, exclui Conselhos/Comissões
    '''

    def uo(self):
        UnidadeOrganizacional = apps.get_model('rh', 'unidadeorganizacional')
        eh_setor_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        choices_uo = [
            UnidadeOrganizacional.TIPO_CAMPUS_EAD,
            UnidadeOrganizacional.TIPO_CAMPUS_NAO_PRODUTIVO,
            UnidadeOrganizacional.TIPO_CAMPUS_PRODUTIVO,
            UnidadeOrganizacional.TIPO_REITORIA,
        ]
        return self.suap().filter(tipo__in=choices_uo) if eh_setor_suap else self.filter()


class UnidadeOrganizacionalManager(models.Manager):
    def siape(self):
        return self.get_queryset().siape()

    def suap(self):
        return self.get_queryset().suap()

    def campi(self):
        return self.get_queryset().campi()

    def uo(self):
        return self.get_queryset().uo()

    def get_queryset(self):
        return UnidadeOrganizacionalQuery(self.model, using=self._db)


class SetorQuery(models.QuerySet):

    '''
        Exibe todos os setores com código(SIAPE) e que estejam ativas
    '''

    def siape(self):
        eh_setor_siape = settings.TIPO_ARVORE_SETORES == 'SIAPE'
        return self.filter() if eh_setor_siape else self.filter(codigo__isnull=False)

    '''
        Quando a configuração de setores for SUAP:
        - Exibe os setores que não tem código vinculado e estão ativas
        Quando a configuração doas setores for SIAPE:
        - Exibe todos setores ativas
    '''

    def suap(self):
        eh_setor_siape = settings.TIPO_ARVORE_SETORES == 'SIAPE'
        return self.filter() if eh_setor_siape else self.filter(codigo__isnull=True)

    def suap_ativos(self):
        return self.suap().filter(excluido=False)


class SetorManager(models.Manager):
    def siape(self):
        return self.get_queryset().siape()

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


class SetoresSiapeManager(SetorManager):
    def get_queryset(self):
        return SetorQuery(self.model, using=self._db).siape()


class PessoaQueryset(models.QuerySet):
    def servidores(self):
        return self.pessoas_fisicas().filter(pessoafisica__eh_servidor=True)

    def prestadores(self):
        return self.pessoas_fisicas().filter(pessoafisica__eh_prestador=True)

    def alunos(self):
        return self.pessoas_fisicas().filter(pessoafisica__eh_aluno=True)

    def com_usuario(self):
        return self.pessoas_fisicas().filter(vinculo__user__isnull=False)

    def pessoas_fisicas(self):
        return self.filter(pessoafisica__isnull=False)

    def pessoas_juridicas(self):
        return self.filter(pessoajuridica__isnull=False)


class PessoaManager(models.Manager):
    def get_queryset(self):
        return PessoaQueryset(self.model, using=self._db)

    def servidores(self):
        return self.get_queryset().servidores()

    def prestadores(self):
        return self.get_queryset().prestadores()

    def alunos(self):
        return self.get_queryset().alunos()

    def pessoas_fisicas(self):
        return self.get_queryset().pessoas_fisicas()

    def pessoas_com_usuario(self):
        return self.get_queryset().com_usuario()

    def pessoas_juridicas(self):
        return self.get_queryset().pessoas_juridicas()


class ServidorQueryset(models.QuerySet):
    def vinculados(self):
        return self.filter(excluido=False)

    def aposentados(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo=Situacao.APOSENTADOS)

    def ativos(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo__in=Situacao.SITUACOES_ATIVOS)

    def inativos(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().exclude(situacao__codigo__in=Situacao.SITUACOES_ATIVOS)

    def ativos_permanentes(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo=Situacao.ATIVO_PERMANENTE)

    def cedidos(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo=Situacao.ATIVO_EM_OUTRO_ORGAO)

    def efetivos(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo__in=Situacao.SITUACOES_EFETIVOS)

    def em_exercicio(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo__in=Situacao.SITUACOES_EM_EXERCICIO_NO_INSTITUTO)

    def estagiarios(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.vinculados().filter(situacao__codigo__in=Situacao.situacoes_siape_estagiarios())

    def tecnicos_administrativos(self):
        return self.vinculados().filter(eh_tecnico_administrativo=True)

    def docentes(self):
        return self.vinculados().filter(eh_docente=True)

    def substitutos(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.docentes().filter(situacao__codigo=Situacao.CONT_PROF_SUBSTITUTO)

    def substitutos_ou_temporarios(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.docentes().filter(situacao__codigo__in=Situacao.SITUACOES_SUBSTITUTOS_OU_TEMPORARIOS)

    def visitantes(self):
        Situacao = apps.get_model('rh', 'situacao')
        return self.docentes().filter(situacao__codigo=Situacao.CONTR_PROF_VISITANTE)

    def docentes_permanentes(self):
        return self.docentes().ativos_permanentes()

    def docentes_cedidos(self):
        return self.docentes().cedidos()


class AreaConhecimentoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('superior')


class FuncaoQuery(models.QuerySet):
    def usadas(self):
        return self.filter(servidorfuncaohistorico__isnull=False).distinct()

    def ativos(self):
        return self.filter(excluido=False)

    def siape(self):
        return self.filter(funcao_suap=False)

    def suap(self):
        return self.filter(funcao_suap=True)


class FuncaoManager(models.Manager):
    def usadas(self):
        return self.get_queryset().usadas()

    def ativos(self):
        return self.get_queryset().ativos()

    def siape(self):
        return self.get_queryset().siape()

    def suap(self):
        return self.get_queryset().suap()

    def get_queryset(self):
        return FuncaoQuery(self.model, using=self._db)
