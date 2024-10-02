import operator
from functools import reduce
#
from djtools.db import models
from django.db.models import Q
from django.urls import reverse
from djtools.utils import get_datetime_now
#
from agendamento.models import SolicitacaoAgendamento
from agendamento.calendario import programacao_atual
from comum.models import Vinculo
from edu.models import Diario
from labvirtual.tasks import criar_agendamento
from ldap_backend.services import adicionar_membros_ldap_group, adicionar_membro_ldap_group, remover_membero_ldap_group
from ldap_backend.models import LdapGroup
#
from labvirtual.helpers import extrair_matriculas_no_diario
from labvirtual.perms import pode_gerenciar_solicitacao_labvirtual
from .agendamento import AgendamentoLabVirtual
from .vdi import DesktopPool


class SolicitacaoLabVirtual(SolicitacaoAgendamento):
    laboratorio = models.ForeignKeyPlus(DesktopPool, verbose_name="Laboratório Físico", on_delete=models.CASCADE)
    diario = models.ForeignKeyPlus(Diario, null=True, blank=True, verbose_name="Diário", on_delete=models.CASCADE)
    membros = models.ManyToManyFieldPlus(Vinculo, verbose_name="Membros", related_name='%(app_label)s_%(class)s_membros')

    class Meta:
        verbose_name = 'Solicitação de Agendamento'
        verbose_name_plural = 'Solicitações de Agendamento'
        permissions = (
            ('pode_avaliar_solicitacao_labvirtual', 'Pode avaliar solicitação reserva de Laboratório Virtual'),
        )

    class AgendamentoMeta:
        agendamento_model = AgendamentoLabVirtual
        reserva_model = DesktopPool
        reserva_field = "laboratorio"

    def get_absolute_url(self):
        return reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.pk})

    @property
    def ldap_group_name(self):
        return f"{self.laboratorio.name}_{self.pk}"

    def get_ldap_group(self):
        return LdapGroup.objects.filter(sAMAccountName=self.ldap_group_name).first()

    def __sincronizar_ldap_group(self, membros):
        defaults = {'name': self.ldap_group_name, 'cn': self.ldap_group_name}
        ldap_group, _ = LdapGroup.objects.get_or_create(sAMAccountName=self.ldap_group_name, defaults=defaults)
        adicionar_membros_ldap_group(ldap_group, membros)

    # def __sincronizar_vdi(self, membros):
    #     horizon = VMWareHorizonService.from_settings()
    #     horizon.assign_user_or_group_to_desktop_pool(self.ldap_group_name, self.laboratorio.desktop_pool_id)

    def _remover_ldap_group(self):
        LdapGroup.objects.filter(sAMAccountName=self.ldap_group_name).delete()

    def programacao(self, exibir_pendentes=True):
        return programacao_laboratorio(laboratorio=self.laboratorio, exibir_pendentes=exibir_pendentes)

    def tem_permissao_avaliar(self, user):
        tem_permissao = user.has_perm('labvirtual.pode_avalicar_solicitacao_labvirtual')
        return tem_permissao or pode_gerenciar_solicitacao_labvirtual(user, self.laboratorio)

    def pode_editar_membros(self):
        hoje = get_datetime_now()
        return not (self.finalizada or self.cancelada) and self.deferida and self.data_hora_fim > hoje

    def agendar_tarefas(self):
        for agendamento in self.get_agendamentos():
            criar_agendamento(agendamento)

    def deferir(self):
        membros = list(extrair_matriculas_no_diario(self.diario))
        membros.append(self.solicitante.username)
        # Sincronizando os labatorórios
        self.__sincronizar_ldap_group(membros)
        #
        super().deferir()
        self.agendar_tarefas()

    def cancelar(self):
        if self.pode_cancelar():
            self._remover_ldap_group()
            super().cancelar()

    def finalizar(self):
        if self.pode_finalizar():
            self._remover_ldap_group()
            super().finalizar()

    def adicionar_membro(self, membro):
        adicionar_membro_ldap_group(self.get_ldap_group(), membro)

    def remover_membro(self, membro):
        remover_membero_ldap_group(self.get_ldap_group(), membro)


def programacao_laboratorio(laboratorio, solicitacao_atual=None, exibir_pendentes=True):
    if exibir_pendentes:
        qs_solicitacoes = SolicitacaoLabVirtual.objects.pendentes().filter(laboratorio=laboratorio)
    else:
        qs_solicitacoes = SolicitacaoLabVirtual.objects.none()
    #
    qs_reservas = AgendamentoLabVirtual.objects.filter(solicitacao__laboratorio=laboratorio)
    return programacao_atual(solicitacao_atual, qs_solicitacoes, qs_reservas)


def reservas_laboratorio(laboratorio, data_inicio, data_fim):
    """
        Retornas reservas (provinientes de uma solicitações atendidas ou de uma indisponibilização)
        que conflitam com os parâmetros passados
    """
    reservas = SolicitacaoLabVirtual.objects.deferidas().filter(laboratorio=laboratorio)
    q_filters = [
        # Remove as reservas que a data_fim vem antes da data_inicio da pesquisa
        Q(data_fim__lt=data_inicio) | Q(data_fim=data_inicio, hora_fim__lt=data_inicio.time()),
        Q(hora_fim__lt=data_inicio.time()),
        # Remove as reservas que a data_inicio vem depois da data_fim da pesquisa
        Q(data_inicio__gt=data_fim) | Q(data_inicio=data_fim, hora_inicio__gt=data_fim.time()),
        Q(hora_inicio__gt=data_fim.time())
    ]
    reservas = reservas.exclude(reduce(operator.or_, q_filters))
    return reservas
