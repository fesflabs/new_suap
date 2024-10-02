from django.views.generic.base import View
from django.views.generic import DetailView, CreateView, UpdateView
from django.views.generic.edit import FormView
from django.db import transaction
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, HttpResponseRedirect
from django.core.exceptions import ValidationError

#
from djtools.utils import httprr
from ldap_backend.forms import SearchForm
from ldap_backend.models import LdapUser
#
from .models import DesktopPool, SolicitacaoLabVirtual, AgendamentoLabVirtual
from .forms import SolicitacaoLabVirtualForm, IndeferirSolicitacaoLabVirtualForm, CancelarSolicitacaoLabVirtualForm
from .services import VMWareHorizonService
from .helpers import DictObj


class SyncDesktopPoolsView(LoginRequiredMixin, View):
    #
    def get_success_url(self) -> str:
        app_label = DesktopPool._meta.app_label
        model_name = DesktopPool._meta.model_name
        return reverse(f'admin:{app_label}_{model_name}_changelist')

    #
    def get(self, request, *args, **kwargs):
        #
        vmware_horizon = VMWareHorizonService.from_settings()
        desktop_pools = vmware_horizon.get_desktop_pools()
        for desktop_pool in desktop_pools:
            defaults = {
                'name': desktop_pool['name'],
                'description': desktop_pool['display_name'],
                # TODO: Perguntar a Cadeu se o numero de máquinas no pool pode variar.
                # 'capacidade': desktop_pool['pattern_naming_settings']['number_of_spare_machines']
            }
            DesktopPool.objects.update_or_create(desktop_pool_id=desktop_pool['id'], defaults=defaults)
        #
        url = self.get_success_url()
        return httprr(url, "Sincronização realizada com sucesso")


sync_desktop_pools_view = SyncDesktopPoolsView.as_view()


class DesktopPoolDetailView(LoginRequiredMixin, DetailView):

    model = DesktopPool
    slug_field = "pk"
    slug_url_kwarg = "pk"
    template_name = 'vdi/desktop_pool.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        object = self.get_object()
        #
        vmware_horizon = VMWareHorizonService.from_settings()
        desktop_pool = vmware_horizon.get_desktop_pool(desktop_pool_id=object.desktop_pool_id)
        ad_groups = vmware_horizon.get_ad_groups_from_desktop_pool(object.desktop_pool_id)
        machines = vmware_horizon.get_machines_from_desktop_pool(object.desktop_pool_id)
        context["desktop_pool"] = DictObj(desktop_pool)
        context["machines"] = [DictObj(machine) for machine in machines]
        context["groups"] = [DictObj(group) for group in ad_groups]
        return context


desktop_pool_detail_view = DesktopPoolDetailView.as_view()


##################################################
# Solicitacao
##################################################

class SolicitacaoAgendamentoCreateView(LoginRequiredMixin, CreateView):
    title = 'Solicitar Agendamento'
    model = SolicitacaoLabVirtual
    form_class = SolicitacaoLabVirtualForm
    template_name = 'labvirtual/solicitar_agendamento.html'

    def get_success_url(self) -> str:
        app_label = SolicitacaoLabVirtual._meta.app_label
        model_name = SolicitacaoLabVirtual._meta.model_name
        return reverse(f'admin:{app_label}_{model_name}_changelist')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.solicitante = self.request.user
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['laboratorio_pk'] = self.kwargs['pk']
        return kwargs


solicitacao_agendamento_create_view = SolicitacaoAgendamentoCreateView.as_view()


class SolicitacaoAgendamentoDetailView(LoginRequiredMixin, DetailView):
    model = SolicitacaoLabVirtual
    slug_field = "pk"
    slug_url_kwarg = "pk"
    template_name = 'labvirtual/solicitacao_agendamento.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitacao = self.get_object()
        context['calendario'] = solicitacao.programacao()
        return context


solicitacao_agendamento_detail_view = SolicitacaoAgendamentoDetailView.as_view()


class DeferirSolicitacaoAgendamentoView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        object = get_object_or_404(SolicitacaoLabVirtual, pk=kwargs['pk'])
        url = reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})
        try:
            with transaction.atomic():
                object.deferir()
                object.save()
            return httprr(url, 'Solicitação deferida com sucesso.')
        except ValidationError as e:
            return httprr(url, 'Não foi possível realizar o indeferimento: {}'.format(e.messages[0]), 'error')


deferir_solicitacao_agendamento_view = DeferirSolicitacaoAgendamentoView.as_view()


class IndeferirSolicitacaoAgendamentoView(LoginRequiredMixin, UpdateView):
    model = SolicitacaoLabVirtual
    form_class = IndeferirSolicitacaoLabVirtualForm
    template_name = 'labvirtual/indeferir_solicitacao_agendamento.html'

    def form_valid(self, form):
        try:
            form.save()
            url = reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})
            return httprr(url, 'Indeferimento realizado com sucesso.')
        except ValidationError as e:
            url = reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})
            return httprr(url, 'Não foi possível realizar o indeferimento: {}'.format(e.messages[0]), 'error')

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})


indeferir_solicitacao_agendamento_view = IndeferirSolicitacaoAgendamentoView.as_view()


class CancelarSolicitacaoAgendamentoView(LoginRequiredMixin, UpdateView):
    model = SolicitacaoLabVirtual
    form_class = CancelarSolicitacaoLabVirtualForm
    template_name = 'labvirtual/indeferir_solicitacao_agendamento.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        try:
            form.save()
            url = reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})
            return httprr(url, 'Cancalmento realizado com sucesso.')
        except ValidationError as e:
            url = reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})
            return httprr(url, 'Não foi possível realizar o cancelamento: {}'.format(e.messages[0]), 'error')

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse('labvirtual:solicitacao_agendamento', kwargs={"pk": self.kwargs['pk']})


cancelar_solicitacao_agendamento_view = CancelarSolicitacaoAgendamentoView.as_view()


class AgendamentoLabVirtualDetailView(LoginRequiredMixin, DetailView):
    model = AgendamentoLabVirtual
    slug_field = "pk"
    slug_url_kwarg = "pk"
    template_name = 'labvirtual/agendamento_labvirtual.html'


agendamento_labvirtual_detail_view = AgendamentoLabVirtualDetailView.as_view()


class DesktopPoolKillSessions(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            Desktop_pool = get_object_or_404(DesktopPool, pk=kwargs['pk'])
            return httprr('..', f'Sessões do {Desktop_pool} finalizadas com sucesso.')
        except ValidationError as e:
            return httprr('..', 'Não foi possível finalizar as sessões d0 {}: {}'.format(Desktop_pool, e.messages[0]), 'error')


desktop_pool_kill_sessions_view = DesktopPoolKillSessions.as_view()


class AgendamentoSyncView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        object = get_object_or_404(AgendamentoLabVirtual, pk=kwargs['pk'])
        url = '..'
        try:
            with transaction.atomic():
                object.ativar()
                object.save()
            return httprr(url, f'Laboratório {object.laboratorio} liberado.')
        except ValidationError as e:
            return httprr(url, 'Não foi possível liberar o laboratório {0}: {1}'.format(object.laboratorio, e.messages[0]), 'error')


agendamento_sync_view = AgendamentoSyncView.as_view()


class AgendamentoShutdownView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        object = get_object_or_404(AgendamentoLabVirtual, pk=kwargs['pk'])
        url = '..'
        try:
            with transaction.atomic():
                object.inativar()
                object.save()
            return httprr(url, f'Laboratório {object.laboratorio} fechado.')
        except ValidationError as e:
            return httprr(url, 'Não foi possível encerrar o laboratório {0}: {1}'.format(object.laboratorio, e.messages[0]), 'error')


agendamento_shutdown_view = AgendamentoShutdownView.as_view()


class ProcurarUsuarioView(LoginRequiredMixin, FormView):
    template_name = 'labvirtual/procurar_form.html'
    form_class = SearchForm
    model = None
    fields = None
    allowed_methods = ['GET', 'POST']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitacao = get_object_or_404(SolicitacaoLabVirtual, pk=self.kwargs['pk'])
        context["group"] = solicitacao.get_ldap_group()
        return context

    def form_valid(self, form):
        solicitacao = get_object_or_404(SolicitacaoLabVirtual, pk=self.kwargs['pk'])
        group = solicitacao.get_ldap_group()
        users_list = form.search()
        for object in users_list:
            object.is_member = group.is_member(object)
        #
        return self.render_to_response(self.get_context_data(form=form, users_list=users_list, group=group.cn, object=solicitacao))


procurar_usuario_view = ProcurarUsuarioView.as_view()


class AdicionarMembroView(LoginRequiredMixin, View):

    #
    def get(self, request, *args, **kwargs):
        #
        ldap_user = get_object_or_404(LdapUser, uid=self.kwargs['uid'])
        solicitacao = get_object_or_404(SolicitacaoLabVirtual, pk=self.kwargs['pk'])
        solicitacao.adicionar_membro(ldap_user.sAMAccountName)
        msg = f'Usuário {ldap_user} adicionado ao grupo {solicitacao.get_ldap_group()} com sucesso.'
        return httprr(solicitacao.get_absolute_url(), msg)


adicionar_membro_view = AdicionarMembroView.as_view()


class RemoverMembroView(LoginRequiredMixin, View):
    #
    def get(self, request, *args, **kwargs):
        #
        ldap_user = get_object_or_404(LdapUser, uid=self.kwargs['uid'])
        solicitacao = get_object_or_404(SolicitacaoLabVirtual, pk=self.kwargs['pk'])
        solicitacao.remover_membro(ldap_user)
        msg = f'Usuário {ldap_user} adicionado ao grupo {solicitacao.get_ldap_group()} com sucesso.'
        return httprr(solicitacao.get_absolute_url(), msg)


remover_membro_view = RemoverMembroView.as_view()
