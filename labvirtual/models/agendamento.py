from djtools.db import models
from django.urls import reverse
#
from agendamento.models import Agendamento
from agendamento.status import AgendamentoStatus
#
#
from .vdi import DesktopPool
from labvirtual.services import VMWareHorizonService


class AgendamentoLabVirtual(Agendamento):
    solicitacao = models.ForeignKey('labvirtual.SolicitacaoLabVirtual', null=False, blank=False, on_delete=models.CASCADE)
    laboratorio = models.ForeignKey(DesktopPool, null=False, blank=False, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Agendamento de Laboratório Virtual'
        verbose_name_plural = 'Agendamentos de Laboratórios Virtuais'

    @property
    def diario(self):
        return self.solicitacao.diario

    @property
    def ldap_group_name(self):
        return self.solicitacao.ldap_group_name

    def get_ldap_group(self):
        return self.solicitacao.get_ldap_group()

    def get_absolute_url(self):
        return reverse('labvirtual:agendamento_labvirtual', kwargs={"pk": self.pk})

    #
    def possui_permissao(self):
        return True

    @property
    def api(self) -> VMWareHorizonService:
        return VMWareHorizonService.from_settings()

    #
    def ativar(self):
        self.api.assign_user_or_group_to_desktop_pool(self.ldap_group_name, self.laboratorio.desktop_pool_id)
        super().ativar()

    def enviar_notificacao(self, msg=None):
        msg = "A sua sessão vai expirar em 5 minutos. Salve o seu trabalho." or msg
        self.api.send_message_to_desktop_pool(self.laboratorio.desktop_pool_id, msg)

    def inativar(self):
        self.api.disconnect_sessions_from_desktop_pool(self.laboratorio.desktop_pool_id)
        self.api.remove_user_or_group_from_desktop_pool(self.ldap_group_name, self.laboratorio.desktop_pool_id)
        super().inativar()

    def _finalizar_solicitacao(self):
        qs = AgendamentoLabVirtual.objects.filter(solicitacao=self.solicitacao)
        agendamentos = qs.exclude(id=self.id, status=AgendamentoStatus.STATUS_FINALIZADO)
        if not agendamentos.exists():
            self.solicitacao.finalizar()
            self.solicitacao.save()

    #
