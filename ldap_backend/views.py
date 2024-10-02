# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse

from django.contrib.auth.decorators import permission_required, login_required
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from djtools import layout
from djtools.utils import rtr, httprr
from comum.models import Configuracao, Vinculo
#
from .forms import SearchForm, ChangePasswordForm, SelecaoEmailForm
from .models import LdapConf, LdapGroup, LdapUser
from .utils import get_tipos_email_disponiveis


@layout.info()
def index_infos(request):
    infos = list()
    for tipo, label in list(get_tipos_email_disponiveis(request.user).items()):
        url = '/ldap_backend/escolher_email/{0}/'.format(tipo)
        titulo = 'Escolha seu email {0}.'.format(label)
        infos.append(dict(url=url, titulo=titulo))
    return infos


@rtr()
@permission_required('ldap_backend.view_ldap_user')
def search(request, pk):
    form = SearchForm(request.POST or None)
    if form.is_valid():
        objects = form.search()
        return locals()
    return locals()


@rtr()
@permission_required('ldap_backend.view_ldap_user')
def show_object(request, username):
    ldap_conf = LdapConf.get_active()
    vinculo = Vinculo.objects.filter(user__username=username).first()
    if not vinculo:
        return httprr('..', 'Usuário inexistente', 'error')
    pf = vinculo.pessoa.pessoafisica
    obj = ldap_conf.get_user(username)
    keys = sorted(obj.keys())
    title = 'Usuário %s (%s)' % (username, ldap_conf.get_solucao_display())
    return locals()


@rtr()
@permission_required('ldap_backend.sync_ldap_user')
def sync_user(request, username):
    try:
        ldap_conf = LdapConf.get_active()
        vinculo = Vinculo.objects.filter(user__username=username).first()
        if vinculo:
            ldap_conf.sync_ou(vinculo.setor, test_mode=False)
            ldap_conf.sync_user(username)
        else:
            return httprr('..', 'Usuário inexistente.', 'error')
        return httprr(request.META.get('HTTP_REFERER', '..'), 'Usuário sincronizado com sucesso.')
    except Exception as e:
        return httprr('..', str(e), 'error')


@rtr()
def change_password(request, username):
    ldap_conf = LdapConf.get_active()
    if not ldap_conf.can_change_user_password(request.user, username):
        raise PermissionDenied()

    title = 'Definir senha para usuário %s (%s)' % (username, ldap_conf.get_solucao_display())
    form = ChangePasswordForm(request.POST or None, username=username)
    if form.is_valid():
        return httprr('..', 'Senha modificada com sucesso!')
    return locals()


@rtr()
@login_required
def escolher_email(request, tipo):
    tipos_email_disponiveis = get_tipos_email_disponiveis(request.user)
    if tipo not in tipos_email_disponiveis:
        raise PermissionDenied()

    instance = request.user.get_profile().sub_instance()
    title = 'Escolha seu E-mail %s' % tipos_email_disponiveis[tipo]
    form = SelecaoEmailForm(request.user.get_profile(), tipo, data=request.POST or None)
    if form.is_valid():
        # Atribuindo o email de acordo com o tipo do domínio selecionado
        setattr(instance, 'email_%s' % tipo, form.cleaned_data['email'])
        instance.save()
        return httprr('..', 'O email "%s" foi definido com sucesso e estará disponível para uso em 2 horas.' % form.cleaned_data['email'])
    return locals()


@rtr()
@login_required
def redirecionar_google_classroom(request):
    relacionamento = request.user.get_relacionamento()
    if not relacionamento.email_google_classroom or (request.user.eh_prestador and not request.user.groups.filter(name='Usuários do Google Classroom').exists()):
        return httprr('..', 'Você não tem permissão para isso.', 'error')
    utilizar_saml2idp_outra_maquina = Configuracao.get_valor_por_chave('ldap_backend', 'utilizar_saml2idp_outra_maquina')
    dominio_google_classroom = Configuracao.get_valor_por_chave('ldap_backend', 'dominio_google_classroom')
    url_saml2idp = Configuracao.get_valor_por_chave('ldap_backend', 'url_saml2idp')
    email_usuario = request.user.get_profile().sub_instance().email_google_classroom
    SAMLRequest = request.GET.get('SAMLRequest')
    RelayState = request.GET.get('RelayState')

    if utilizar_saml2idp_outra_maquina:
        if not SAMLRequest:
            return httprr('https://accounts.google.com/AccountChooser?hd=%s&continue=https://classroom.google.com' % (dominio_google_classroom))
        else:
            url_params = dict(SAMLRequest=SAMLRequest, RelayState=RelayState, email_usuario=email_usuario)

            try:
                resposta_saml2idp = json.loads(urllib.request.urlopen(url_saml2idp + '?' + urllib.parse.urlencode(url_params)).read())
                response_url = resposta_saml2idp['response_url']
                saml_response = resposta_saml2idp['SAMLResponse']
                token = resposta_saml2idp['RelayState']

                return locals()
            except Exception:
                return HttpResponse('Não foi possível processar a requisição.')
    else:
        if not SAMLRequest:
            return httprr('https://accounts.google.com/AccountChooser?hd=%s&continue=https://classroom.google.com' % (dominio_google_classroom))
        else:
            return redirect('/saml2idp/?SAMLRequest=%s&RelayState=%s' % (urllib.parse.quote_plus(SAMLRequest), urllib.parse.quote_plus(RelayState)))


@login_required
def logout_google_classroom(request):
    if 'autenticou_google_sso' in request.session:
        del request.session['autenticou_google_sso']
        return httprr('/', 'Você foi desconectado do Google Sala de Aula com sucesso.')
    else:
        return httprr('/')


@rtr('ldap_backend/templates/groups/change.html')
@login_required
def ldap_group_change_view(request, group_name):
    #
    group = LdapGroup.objects.get(cn=group_name)
    form = SearchForm(request.POST or None)
    if form.is_valid():
        objects = form.search()
        for object in objects:
            object.is_member = group.is_member(object)
    #
    return locals()


@rtr()
@login_required
def ldap_add_member_view(request, gid, uid):
    ldap_group = get_object_or_404(LdapGroup, cn=gid)
    ldap_user = get_object_or_404(LdapUser, uid=uid)
    ldap_group.add_member(ldap_user)
    return httprr('..', f'Usuário {ldap_user} adicionado ao grupo {ldap_group.name} com sucesso.')


@rtr()
@login_required
def ldap_remove_member_view(request, gid, uid):
    #
    ldap_group = get_object_or_404(LdapGroup, cn=gid)
    ldap_user = get_object_or_404(LdapUser, uid=uid)
    ldap_group.remove_member(ldap_user)
    return httprr('..', f'Usuário {ldap_user} removido do grupo {ldap_group.name} com sucesso.')
