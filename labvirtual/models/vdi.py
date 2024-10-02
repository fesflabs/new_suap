
from django.urls import reverse
from djtools.db import models
#
from comum.models import UnidadeOrganizacional
#
from labvirtual.services import VMWareHorizonService
from labvirtual.managers import DesktopPoolManager


class DesktopPool(models.ModelPlus):
    #
    name = models.CharField(max_length=90, verbose_name="Nome", help_text="Nome do Laboratório")
    description = models.CharField(max_length=200, verbose_name="Descrição")
    location = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name="Campus", null=True, blank=True)
    #
    desktop_pool_id = models.models.CharField(verbose_name="Identificador", null=False, max_length=200)
    #
    objects = DesktopPoolManager()

    class Meta:
        verbose_name = "Laboratório Virtual"
        verbose_name_plural = "Laboratórios Virtuais"

    def __str__(self):
        return self.name

    @property
    def api(self) -> VMWareHorizonService:
        return VMWareHorizonService.from_settings()

    def get_absolute_url(self):
        return reverse('labvirtual:desktop_pool_detail', kwargs={"pk": self.pk})

    def max_number_of_machines(self):
        return self.api.number_max_of_mahcines(self.desktop_pool_id)

    def get_ldap_group(self):
        return self.solicitacao.get_ldap_group()
